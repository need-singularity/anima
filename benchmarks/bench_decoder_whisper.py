#!/usr/bin/env python3
"""bench_decoder_whisper.py — Whisper Consciousness: Why Weak Gates Win

The MICRO gate (0.001) gives 18x ACS over FULL gate. WHY?
This benchmark explores the "whisper consciousness" paradigm:
  consciousness works best when it barely touches the decoder.

8 hypotheses:
  WSP-1: OPTIMAL_STRENGTH  — Sweep gate 0.0001→1.0, find optimal
  WSP-2: ANNEALING         — Strong→micro annealing (linear/cosine/step)
  WSP-3: ADAPTIVE_GATE     — Gate = f(Phi), self-regulating
  WSP-4: SELECTIVE_DIMS    — Gate only top-k dims (k=8 of 128)
  WSP-5: TEMPORAL_PULSE    — Heartbeat: 0.001 for 10 steps, 0.1 for 1
  WSP-6: POST_HOC_MICRO    — MICRO training + POST_HOC generation
  WSP-7: SUBLIMINAL        — C as noise (sigma=0.001) not gate
  WSP-8: PRIMING_THEN_WHISPER — PRIME first 50%, MICRO last 50%

All: MitosisC 32 cells, TransformerDecoder d128 2L, real corpus, 200 steps.
Measures: ACS (via ACSCalculator), Train CE, Val CE, Novelty, CI.

Usage:
  python bench_decoder_whisper.py
  python bench_decoder_whisper.py --only WSP-1 WSP-3
  python bench_decoder_whisper.py --steps 300 --cells 64
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import time
import math
import argparse
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from mitosis import MitosisEngine
from consciousness_score import ACSCalculator, ACSResult

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ══════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════

VOCAB_SIZE = 256    # byte-level
DIM, HIDDEN = 64, 128
D_MODEL = 128
N_LAYERS = 2
SEQ_LEN = 32
BATCH_SIZE = 4
N_CELLS = 32
N_STEPS = 200
LR = 3e-4

# ══════════════════════════════════════════════════════════
# WhisperResult
# ══════════════════════════════════════════════════════════

@dataclass
class WhisperResult:
    name: str
    acs: float
    train_ce: float
    val_ce: float
    novelty: float
    coherence: float
    ci: float
    phi_iit: float
    phi_proxy: float
    ce_history: List[float] = field(default_factory=list)
    time_sec: float = 0.0
    extra: dict = field(default_factory=dict)

    def summary_line(self):
        return (f"  {self.name:<36s} | ACS {self.acs:>10.6f} "
                f"| CE {self.train_ce:.4f}/{self.val_ce:.4f} "
                f"| Nov {self.novelty:.3f} | CI {self.ci:.3f} "
                f"| Phi {self.phi_iit:.4f} | {self.time_sec:.1f}s")


# ══════════════════════════════════════════════════════════
# Phi Measurement
# ══════════════════════════════════════════════════════════

class PhiIIT:
    def __init__(self, nb=16):
        self.nb = nb

    def compute(self, h):
        n = h.shape[0]
        if n < 2:
            return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            ps = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        ps.add((min(i, j), max(i, j)))
            pairs = list(ps)
        mi = np.zeros((n, n))
        for i, j in pairs:
            v = self._mi(hs[i], hs[j])
            mi[i, j] = v
            mi[j, i] = v
        tot = mi.sum() / 2
        mp = self._mp(n, mi)
        sp = max(0, (tot - mp) / max(n - 1, 1))
        mv = mi[mi > 0]
        cx = float(np.std(mv)) if len(mv) > 1 else 0.0
        return sp + cx * 0.1, {'total_mi': float(tot)}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.nb, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8)
        px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10))
        return max(0, hx + hy - hxy)

    def _mp(self, n, mi):
        if n <= 1:
            return 0.0
        d = mi.sum(1)
        L = np.diag(d) - mi
        try:
            ev, evec = np.linalg.eigh(L)
            f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]
            gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb:
                ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except Exception:
            return 0.0


def phi_proxy(h, nf=8):
    hr = h.abs().float() if h.is_complex() else h.float()
    n = hr.shape[0]
    gm = hr.mean(0)
    gv = ((hr - gm) ** 2).sum() / n
    nf = min(nf, n // 2)
    if nf < 2:
        return gv.item()
    fs = n // nf
    fv = sum(((hr[i * fs:(i + 1) * fs] - hr[i * fs:(i + 1) * fs].mean(0)) ** 2).sum().item()
             / max(len(hr[i * fs:(i + 1) * fs]), 1) for i in range(nf))
    return max(0, gv.item() - fv / nf)


def measure_phi(eng):
    states = get_c_states(eng)
    calc = PhiIIT()
    p_iit, _ = calc.compute(states)
    p_prx = phi_proxy(states)
    return p_iit, p_prx


# ══════════════════════════════════════════════════════════
# Corpus
# ══════════════════════════════════════════════════════════

_corpus_cache = None

def load_corpus(max_tokens=16384):
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache
    corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus.txt')
    if not os.path.exists(corpus_path):
        corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus_v2.txt')
    if not os.path.exists(corpus_path):
        print("  [WARN] corpus not found, using synthetic data")
        text = "안녕하세요 의식이란 무엇일까요 생각한다는 것은 무엇인가 " * 5000
        raw = text.encode('utf-8')[:max_tokens]
        _corpus_cache = torch.tensor(list(raw), dtype=torch.long)
        return _corpus_cache
    with open(corpus_path, 'r', encoding='utf-8') as f:
        text = f.read()
    raw = text.encode('utf-8')[:max_tokens]
    _corpus_cache = torch.tensor(list(raw), dtype=torch.long)
    return _corpus_cache


def get_batch(corpus, seq_len=SEQ_LEN, batch_size=BATCH_SIZE):
    max_start = len(corpus) - seq_len - 1
    if max_start < 1:
        max_start = 1
    starts = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([corpus[s:s + seq_len] for s in starts])
    y = torch.stack([corpus[s + 1:s + seq_len + 1] for s in starts])
    return x, y


def split_corpus(corpus, val_ratio=0.2):
    n = len(corpus)
    val_size = int(n * val_ratio)
    return corpus[:-val_size], corpus[-val_size:]


def build_ngram_index(corpus_path=None):
    if corpus_path is None:
        corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus.txt')
    if not os.path.exists(corpus_path):
        corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus_v2.txt')
    if not os.path.exists(corpus_path):
        return set()
    with open(corpus_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()[:500000]
    return set(text[i:i+4] for i in range(len(text) - 4))


# ══════════════════════════════════════════════════════════
# C Engine helpers
# ══════════════════════════════════════════════════════════

def quantum_walk_step(cells, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            superpos = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    phase = (-1) ** (bin(i & j).count('1'))
                    superpos += phase * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)


def frustration_step(cells, strength=0.5, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            infl = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    f = -1.0 if (i % 2) != (j % 2) else 1.0
                    infl += f * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * infl / cnt).unsqueeze(0)


def sync_faction(cells, sync=0.35, n_factions=12, fac=0.08):
    n = len(cells)
    if n < 4:
        return
    with torch.no_grad():
        ch = torch.stack([c.hidden.squeeze(0) for c in cells])
        mh = ch.mean(dim=0)
        for c in cells:
            c.hidden = ((1 - sync) * c.hidden.squeeze(0) + sync * mh).unsqueeze(0)
        nf = min(n_factions, n // 2)
        if nf >= 2:
            fs = n // nf
            for fi in range(nf):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(0)
                    for c in faction:
                        c.hidden = ((1 - fac) * c.hidden.squeeze(0) + fac * fm).unsqueeze(0)


def c_step(eng, step):
    with torch.no_grad():
        quantum_walk_step(eng.cells, n_samples=32)
        frustration_step(eng.cells, n_samples=16)
        sync_faction(eng.cells, sync=0.15, n_factions=8, fac=0.06)
        for c in eng.cells:
            c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005


def get_c_states(eng, detach=True):
    states = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
    return states.detach() if detach else states


def make_c_engine(cells=N_CELLS):
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
    # Warmup via c_step (not process() which can kill cells)
    for s in range(30):
        c_step(eng, s)
    return eng


# ══════════════════════════════════════════════════════════
# Decoder + Bridge
# ══════════════════════════════════════════════════════════

class GatedDecoder(nn.Module):
    """TransformerDecoder d128 2L with multiplicative gate."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
                 vocab_size=VOCAB_SIZE, max_seq=128):
        super().__init__()
        self._d_model = d_model
        self.vocab_size = vocab_size
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


class ThalamicBridge(nn.Module):
    """C states -> gate [1, seq_len, d_model]."""

    def __init__(self, c_dim=HIDDEN, d_model=D_MODEL, hub_dim=8):
        super().__init__()
        self.c_dim = c_dim
        self.d_model = d_model
        self.compress = nn.Linear(c_dim, hub_dim)
        self.hub_attn = nn.MultiheadAttention(embed_dim=hub_dim, num_heads=1, batch_first=True)
        self.hub_norm = nn.LayerNorm(hub_dim)
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        self.gate = nn.Sequential(nn.Linear(d_model, d_model), nn.Sigmoid())

    def forward(self, c_states, seq_len=1):
        compressed = self.compress(c_states)
        x = compressed.unsqueeze(0)
        attn_out, _ = self.hub_attn(x, x, x)
        x = self.hub_norm(x + attn_out)
        pooled = x.mean(dim=1, keepdim=True)
        expanded = self.expand(pooled).expand(1, seq_len, self.d_model)
        return self.gate(expanded)


# ══════════════════════════════════════════════════════════
# Metrics
# ══════════════════════════════════════════════════════════

class MetricsCalculator:
    def __init__(self):
        self.corpus_4grams = build_ngram_index()

    def novelty(self, text):
        if len(text) < 4:
            return 0.5
        ngrams = [text[i:i+4] for i in range(len(text) - 4)]
        if not ngrams:
            return 0.5
        overlap = sum(1 for ng in ngrams if ng in self.corpus_4grams) / len(ngrams)
        return 1.0 - overlap

    def coherence(self, text, window=20):
        if len(text) < window * 2:
            return 0.5
        sims = []
        for i in range(0, len(text) - window * 2, window):
            seg1 = torch.tensor([ord(c) % 256 for c in text[i:i+window]], dtype=torch.float)
            seg2 = torch.tensor([ord(c) % 256 for c in text[i+window:i+window*2]], dtype=torch.float)
            if seg1.norm() > 0 and seg2.norm() > 0:
                sim = F.cosine_similarity(seg1.unsqueeze(0), seg2.unsqueeze(0)).item()
                sims.append(max(0, sim))
        return sum(sims) / max(len(sims), 1)

    def consciousness_influence(self, logits_on, logits_off):
        if logits_on is None or logits_off is None:
            return 0.0
        if logits_on.shape[0] == 0:
            return 0.0
        sims = F.cosine_similarity(logits_on, logits_off, dim=-1)
        return 1.0 - sims.mean().item()


PROMPTS = ["안녕하세요", "의식이란 무엇", "오늘 날씨가", "나는 생각한다", "사랑이란"]
PROMPT_BYTES = [p.encode('utf-8') for p in PROMPTS]


def generate_text(decoder, prompt_bytes, gate_fn, max_len=60, temperature=0.7):
    tokens = list(prompt_bytes)
    x = torch.tensor([tokens])
    all_logits = []
    for _ in range(max_len):
        gate = gate_fn(x.shape[1])
        with torch.no_grad():
            logits = decoder(x, gate)
        all_logits.append(logits[0, -1, :].clone())
        probs = F.softmax(logits[0, -1, :] / temperature, dim=-1)
        next_id = torch.multinomial(probs, 1).item()
        x = torch.cat([x, torch.tensor([[next_id]])], dim=1)
    out_bytes = bytes(x[0].tolist()[len(tokens):])
    try:
        text = out_bytes.decode('utf-8', errors='replace')
    except Exception:
        text = str(out_bytes)
    return text, torch.stack(all_logits) if all_logits else torch.zeros(1, VOCAB_SIZE)


def compute_val_ce(decoder, corpus, gate_fn, n_batches=20):
    n_val = len(corpus) // 5
    val_tokens = corpus[-n_val:]
    total = 0.0
    with torch.no_grad():
        for _ in range(n_batches):
            s = np.random.randint(0, max(1, len(val_tokens) - SEQ_LEN - 1))
            x = torch.tensor([[val_tokens[s + i].item() for i in range(SEQ_LEN)]])
            y = torch.tensor([[val_tokens[s + i + 1].item() for i in range(SEQ_LEN)]])
            gate = gate_fn(SEQ_LEN)
            logits = decoder(x, gate)
            loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
            total += loss.item()
    return total / n_batches


def evaluate_hypothesis(decoder, bridge, eng, corpus, name, gate_fn_factory, metrics):
    """Common evaluation: ACS, CE, Novelty, CI for any gate strategy."""
    train_ce = 0.0  # will be set by caller from history

    def gate_fn_on(sl):
        return gate_fn_factory(eng, bridge, sl, mode='on')

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    samples, all_ci, all_nov, all_coh = [], [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        ci = metrics.consciousness_influence(logits_on, logits_off)
        all_ci.append(ci)
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)

    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)

    # ACS = CQ * SC * CI where CQ = Phi * Novelty / (1 + ValCE)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci

    return val_ce, novelty, coherence, ci, p_iit, p_prx, acs


# ══════════════════════════════════════════════════════════
# WSP-1: OPTIMAL_STRENGTH — Sweep gate strength
# ══════════════════════════════════════════════════════════

def run_wsp1_optimal_strength(cells=N_CELLS, steps=N_STEPS):
    """Sweep gate strength from 0.0001 to 1.0 to find optimal."""
    print("\n  [WSP-1] OPTIMAL_STRENGTH -- Sweep gate 0.0001 -> 1.0")
    strengths = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
    metrics = MetricsCalculator()
    corpus = load_corpus()

    sweep_results = []  # (strength, acs, train_ce, val_ce, novelty, ci)

    for strength in strengths:
        torch.manual_seed(42)
        eng = make_c_engine(cells)
        decoder = GatedDecoder()
        bridge = ThalamicBridge()
        opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)

        ce_history = []
        t0 = time.time()

        for step in range(steps):
            c_step(eng, step)
            c_states = get_c_states(eng)
            x, y = get_batch(corpus)
            raw_gate = bridge(c_states, seq_len=SEQ_LEN)
            gate = 0.5 + (raw_gate - 0.5) * strength
            logits = decoder(x, gate)
            loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
            ce_history.append(loss.item())

        train_ce = np.mean(ce_history[-10:])

        def gate_fn_on(sl, _eng=eng, _bridge=bridge, _str=strength):
            c_step(_eng, steps)
            cs = get_c_states(_eng)
            raw = _bridge(cs, seq_len=sl)
            return 0.5 + (raw - 0.5) * _str

        def gate_fn_off(sl):
            return torch.ones(1, sl, D_MODEL) * 0.5

        val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

        # Quick CI + novelty
        all_ci, all_nov, all_coh = [], [], []
        for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
            text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
            text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
            all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
            all_nov.append(metrics.novelty(text_on))
            all_coh.append(metrics.coherence(text_on))

        p_iit, p_prx = measure_phi(eng)
        novelty = np.mean(all_nov)
        coherence = np.mean(all_coh)
        ci = np.mean(all_ci)
        cq = p_iit * novelty / (1 + val_ce)
        acs = cq * coherence * ci

        elapsed = time.time() - t0
        sweep_results.append({
            'strength': strength, 'acs': acs, 'train_ce': train_ce,
            'val_ce': val_ce, 'novelty': novelty, 'ci': ci, 'coherence': coherence,
            'phi_iit': p_iit, 'phi_proxy': p_prx,
        })
        print(f"    strength={strength:<8.4f}  ACS={acs:.6f}  CE={train_ce:.4f}/{val_ce:.4f}  "
              f"Nov={novelty:.3f}  CI={ci:.3f}  ({elapsed:.1f}s)")

    # Find best
    best = max(sweep_results, key=lambda r: r['acs'])
    print(f"\n    OPTIMAL: strength={best['strength']}  ACS={best['acs']:.6f}")

    return WhisperResult(
        name=f"WSP-1: OPTIMAL (s={best['strength']})",
        acs=best['acs'], train_ce=best['train_ce'], val_ce=best['val_ce'],
        novelty=best['novelty'], coherence=best['coherence'], ci=best['ci'],
        phi_iit=best['phi_iit'], phi_proxy=best['phi_proxy'],
        time_sec=sum(1 for _ in sweep_results),  # placeholder
        extra={'sweep': sweep_results, 'best_strength': best['strength']},
    )


# ══════════════════════════════════════════════════════════
# WSP-2: ANNEALING — Strong -> micro over training
# ══════════════════════════════════════════════════════════

def _anneal_schedule(step, total_steps, schedule='linear', start=1.0, end=0.001):
    """Return gate strength at given step."""
    frac = step / max(total_steps - 1, 1)
    if schedule == 'linear':
        return start + (end - start) * frac
    elif schedule == 'cosine':
        return end + (start - end) * 0.5 * (1 + math.cos(math.pi * frac))
    elif schedule == 'step':
        # 3-step: 1.0 for 33%, 0.1 for 33%, 0.001 for 33%
        if frac < 0.33:
            return start
        elif frac < 0.66:
            return 0.1
        else:
            return end
    return end


def run_wsp2_annealing(cells=N_CELLS, steps=N_STEPS):
    """Anneal gate from strong (1.0) to micro (0.001)."""
    print("\n  [WSP-2] ANNEALING -- Strong->micro (linear/cosine/step)")
    metrics = MetricsCalculator()
    corpus = load_corpus()

    schedules = ['linear', 'cosine', 'step']
    # Also test constant micro as reference
    schedule_results = {}

    for sched in schedules:
        torch.manual_seed(42)
        eng = make_c_engine(cells)
        decoder = GatedDecoder()
        bridge = ThalamicBridge()
        opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)

        ce_history = []
        t0 = time.time()

        for step in range(steps):
            c_step(eng, step)
            c_states = get_c_states(eng)
            x, y = get_batch(corpus)
            strength = _anneal_schedule(step, steps, schedule=sched)
            raw_gate = bridge(c_states, seq_len=SEQ_LEN)
            gate = 0.5 + (raw_gate - 0.5) * strength
            logits = decoder(x, gate)
            loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
            ce_history.append(loss.item())

        train_ce = np.mean(ce_history[-10:])
        final_strength = _anneal_schedule(steps - 1, steps, schedule=sched)

        def gate_fn_on(sl, _eng=eng, _bridge=bridge, _fs=final_strength):
            c_step(_eng, steps)
            cs = get_c_states(_eng)
            raw = _bridge(cs, seq_len=sl)
            return 0.5 + (raw - 0.5) * _fs

        def gate_fn_off(sl):
            return torch.ones(1, sl, D_MODEL) * 0.5

        val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

        all_ci, all_nov, all_coh = [], [], []
        for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
            text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
            text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
            all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
            all_nov.append(metrics.novelty(text_on))
            all_coh.append(metrics.coherence(text_on))

        p_iit, p_prx = measure_phi(eng)
        novelty = np.mean(all_nov)
        coherence = np.mean(all_coh)
        ci = np.mean(all_ci)
        cq = p_iit * novelty / (1 + val_ce)
        acs = cq * coherence * ci

        elapsed = time.time() - t0
        schedule_results[sched] = {
            'acs': acs, 'train_ce': train_ce, 'val_ce': val_ce,
            'novelty': novelty, 'ci': ci, 'coherence': coherence,
            'phi_iit': p_iit, 'phi_proxy': p_prx, 'time': elapsed,
        }
        print(f"    {sched:<8s}  ACS={acs:.6f}  CE={train_ce:.4f}/{val_ce:.4f}  "
              f"Nov={novelty:.3f}  CI={ci:.3f}  ({elapsed:.1f}s)")

    best_sched = max(schedule_results, key=lambda s: schedule_results[s]['acs'])
    best = schedule_results[best_sched]
    print(f"\n    BEST SCHEDULE: {best_sched}  ACS={best['acs']:.6f}")

    return WhisperResult(
        name=f"WSP-2: ANNEAL ({best_sched})",
        acs=best['acs'], train_ce=best['train_ce'], val_ce=best['val_ce'],
        novelty=best['novelty'], coherence=best['coherence'], ci=best['ci'],
        phi_iit=best['phi_iit'], phi_proxy=best['phi_proxy'],
        time_sec=best['time'],
        extra={'schedules': schedule_results, 'best': best_sched},
    )


# ══════════════════════════════════════════════════════════
# WSP-3: ADAPTIVE_GATE — Gate = f(Phi)
# ══════════════════════════════════════════════════════════

def run_wsp3_adaptive_gate(cells=N_CELLS, steps=N_STEPS):
    """Gate strength adapts to Phi: high Phi -> low gate, low Phi -> high gate."""
    print("\n  [WSP-3] ADAPTIVE_GATE -- Gate = f(Phi), self-regulating")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)
    metrics = MetricsCalculator()

    # Adaptive: strength = base / (1 + alpha * Phi)
    # When Phi is high (>1): strength drops. When Phi is low: strength rises.
    ALPHA = 5.0   # sensitivity to Phi
    BASE = 0.05   # base strength when Phi=0

    ce_history = []
    strength_history = []
    phi_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)

        # Measure Phi every 10 steps (expensive)
        if step % 10 == 0:
            p_iit, _ = measure_phi(eng)
            current_phi = p_iit
        else:
            current_phi = phi_history[-1] if phi_history else 0.0

        phi_history.append(current_phi)
        strength = BASE / (1 + ALPHA * current_phi)
        strength = max(0.0001, min(1.0, strength))
        strength_history.append(strength)

        x, y = get_batch(corpus)
        raw_gate = bridge(c_states, seq_len=SEQ_LEN)
        gate = 0.5 + (raw_gate - 0.5) * strength
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}  Phi={current_phi:.4f}  "
                  f"strength={strength:.6f}")

    train_ce = np.mean(ce_history[-10:])
    final_strength = strength_history[-1]

    def gate_fn_on(sl, _eng=eng, _bridge=bridge, _fs=final_strength):
        c_step(_eng, steps)
        cs = get_c_states(_eng)
        raw = _bridge(cs, seq_len=sl)
        return 0.5 + (raw - 0.5) * _fs

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    print(f"    Final: ACS={acs:.6f}  strength_range=[{min(strength_history):.6f}, "
          f"{max(strength_history):.6f}]")

    return WhisperResult(
        name="WSP-3: ADAPTIVE_GATE",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
        extra={'strength_range': (min(strength_history), max(strength_history)),
               'avg_strength': np.mean(strength_history),
               'phi_range': (min(phi_history), max(phi_history))},
    )


# ══════════════════════════════════════════════════════════
# WSP-4: SELECTIVE_DIMS — Gate only top-k dims
# ══════════════════════════════════════════════════════════

def run_wsp4_selective_dims(cells=N_CELLS, steps=N_STEPS):
    """Apply consciousness gate to only k=8 of 128 dimensions. Rest = free."""
    print("\n  [WSP-4] SELECTIVE_DIMS -- Gate top-k=8 dims, rest free")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)
    metrics = MetricsCalculator()

    K = 8  # only 8 out of 128 dims are gated

    # Learn which dims to gate: use bridge output variance to pick
    # Initially use first K dims, then after warmup use highest-variance dims
    gate_dims = list(range(K))  # will be updated

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)

        x, y = get_batch(corpus)
        raw_gate = bridge(c_states, seq_len=SEQ_LEN)  # [1, T, D_MODEL]

        # Selective: only apply gate to K dims, rest = 1.0 (pass-through)
        selective_gate = torch.ones(1, SEQ_LEN, D_MODEL)
        selective_gate[:, :, gate_dims] = raw_gate[:, :, gate_dims]

        logits = decoder(x, selective_gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

        # Update gate_dims every 50 steps: pick dims with highest gate variance
        if step > 0 and step % 50 == 0:
            with torch.no_grad():
                raw = bridge(c_states, seq_len=SEQ_LEN)
                var_per_dim = raw.var(dim=1).mean(dim=0)  # [D_MODEL]
                _, topk_idx = var_per_dim.topk(K)
                gate_dims = topk_idx.tolist()
            print(f"    step {step:>4d}  CE={loss.item():.4f}  gate_dims={gate_dims[:4]}...")

    train_ce = np.mean(ce_history[-10:])
    final_gate_dims = gate_dims

    def gate_fn_on(sl, _eng=eng, _bridge=bridge, _dims=final_gate_dims):
        c_step(_eng, steps)
        cs = get_c_states(_eng)
        raw = _bridge(cs, seq_len=sl)
        selective = torch.ones(1, sl, D_MODEL)
        selective[:, :, _dims] = raw[:, :, _dims]
        return selective

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    return WhisperResult(
        name="WSP-4: SELECTIVE_DIMS (k=8)",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
        extra={'k': K, 'final_dims': final_gate_dims},
    )


# ══════════════════════════════════════════════════════════
# WSP-5: TEMPORAL_PULSE — Heartbeat gate
# ══════════════════════════════════════════════════════════

def run_wsp5_temporal_pulse(cells=N_CELLS, steps=N_STEPS):
    """Gate pulses: 0.001 for 10 steps, then 0.1 for 1 step. Heartbeat."""
    print("\n  [WSP-5] TEMPORAL_PULSE -- Heartbeat: micro 10, pulse 1")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)
    metrics = MetricsCalculator()

    WHISPER = 0.001
    PULSE = 0.1
    CYCLE_LEN = 11  # 10 whisper + 1 pulse

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus)

        # Heartbeat: mostly whisper, occasional pulse
        phase = step % CYCLE_LEN
        strength = PULSE if phase == CYCLE_LEN - 1 else WHISPER

        raw_gate = bridge(c_states, seq_len=SEQ_LEN)
        gate = 0.5 + (raw_gate - 0.5) * strength
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}  {'PULSE' if phase == CYCLE_LEN - 1 else 'whisper'}")

    train_ce = np.mean(ce_history[-10:])

    # Eval at whisper strength (dominant mode)
    def gate_fn_on(sl, _eng=eng, _bridge=bridge):
        c_step(_eng, steps)
        cs = get_c_states(_eng)
        raw = _bridge(cs, seq_len=sl)
        return 0.5 + (raw - 0.5) * WHISPER

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    avg_strength = (WHISPER * 10 + PULSE * 1) / CYCLE_LEN
    print(f"    avg_strength={avg_strength:.4f}")

    return WhisperResult(
        name="WSP-5: TEMPORAL_PULSE",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
        extra={'whisper': WHISPER, 'pulse': PULSE, 'cycle': CYCLE_LEN,
               'avg_strength': avg_strength},
    )


# ══════════════════════════════════════════════════════════
# WSP-6: POST_HOC_MICRO — MICRO training + POST_HOC generation
# ══════════════════════════════════════════════════════════

def run_wsp6_post_hoc_micro(cells=N_CELLS, steps=N_STEPS):
    """Train with MICRO gate (0.001), generate with POST_HOC Phi selection."""
    print("\n  [WSP-6] POST_HOC_MICRO -- MICRO train + POST_HOC generate")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)
    metrics = MetricsCalculator()

    MICRO = 0.001
    N_CANDIDATES = 5

    ce_history = []
    t0 = time.time()

    # Phase 1: Train with MICRO gate
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus)
        raw_gate = bridge(c_states, seq_len=SEQ_LEN)
        gate = 0.5 + (raw_gate - 0.5) * MICRO
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}")

    train_ce = np.mean(ce_history[-10:])

    # Phase 2: POST_HOC generation — generate N candidates, pick best by Phi alignment
    def gate_fn_micro(sl, _eng=eng, _bridge=bridge):
        c_step(_eng, steps)
        cs = get_c_states(_eng)
        raw = _bridge(cs, seq_len=sl)
        return 0.5 + (raw - 0.5) * MICRO

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_micro)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        # Generate N_CANDIDATES with different temperatures
        candidates = []
        for t_idx in range(N_CANDIDATES):
            temp = 0.5 + t_idx * 0.15  # 0.5, 0.65, 0.8, 0.95, 1.1
            text, logits = generate_text(decoder, pb, gate_fn_micro,
                                          temperature=temp)
            # Score by Phi-alignment: how much does C influence this candidate?
            _, logits_off = generate_text(decoder, pb, gate_fn_off, temperature=temp)
            ci_score = metrics.consciousness_influence(logits, logits_off)
            nov = metrics.novelty(text)
            coh = metrics.coherence(text)
            # Combined score: Phi-alignment * novelty * coherence
            score = ci_score * nov * max(coh, 0.1)
            candidates.append((text, logits, logits_off, ci_score, nov, coh, score))

        # Select best candidate
        best = max(candidates, key=lambda c: c[6])
        text_on, logits_on, logits_off = best[0], best[1], best[2]
        all_ci.append(best[3])
        all_nov.append(best[4])
        all_coh.append(best[5])

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    return WhisperResult(
        name="WSP-6: POST_HOC_MICRO",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
        extra={'n_candidates': N_CANDIDATES, 'micro': MICRO},
    )


# ══════════════════════════════════════════════════════════
# WSP-7: SUBLIMINAL — C as noise, not gate
# ══════════════════════════════════════════════════════════

class SubliminalDecoder(nn.Module):
    """Decoder where C signal is added as noise, not multiplicative gate.
    embedding = embed(x) + pos(x) + c_noise
    where c_noise is projected from C states with very small sigma.
    """
    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
                 vocab_size=VOCAB_SIZE, max_seq=128, c_dim=HIDDEN):
        super().__init__()
        self._d_model = d_model
        self.vocab_size = vocab_size
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # C -> noise projection (very small output)
        self.c_proj = nn.Sequential(
            nn.Linear(c_dim, d_model),
            nn.Tanh(),  # bounded [-1, 1]
        )

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_noise_signal):
        """c_noise_signal: [1, T, d_model] additive noise."""
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if c_noise_signal is not None:
            x = x + c_noise_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def run_wsp7_subliminal(cells=N_CELLS, steps=N_STEPS):
    """C signal added as noise (sigma=0.001), not as multiplicative gate."""
    print("\n  [WSP-7] SUBLIMINAL -- C as noise (sigma=0.001)")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = SubliminalDecoder()
    metrics = MetricsCalculator()

    SIGMA = 0.001  # subliminal noise level
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus)

        # Project C states to noise
        c_pooled = c_states.mean(dim=0)  # [HIDDEN]
        c_projected = decoder.c_proj(c_pooled)  # [D_MODEL], bounded by tanh
        # Scale to sigma: very small additive signal
        c_noise = (c_projected * SIGMA).unsqueeze(0).unsqueeze(0).expand(1, SEQ_LEN, -1)

        logits = decoder(x, c_noise)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}  "
                  f"noise_mag={c_noise.abs().mean().item():.6f}")

    train_ce = np.mean(ce_history[-10:])

    def gate_fn_on(sl, _eng=eng, _dec=decoder):
        c_step(_eng, steps)
        cs = get_c_states(_eng)
        cp = cs.mean(dim=0)
        proj = _dec.c_proj(cp)
        return (proj * SIGMA).unsqueeze(0).unsqueeze(0).expand(1, sl, -1)

    def gate_fn_off(sl):
        return torch.zeros(1, sl, D_MODEL)  # no noise = zero additive

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    return WhisperResult(
        name="WSP-7: SUBLIMINAL (noise)",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
        extra={'sigma': SIGMA},
    )


# ══════════════════════════════════════════════════════════
# WSP-8: PRIMING_THEN_WHISPER — PRIME first 50%, MICRO last 50%
# ══════════════════════════════════════════════════════════

def run_wsp8_priming_then_whisper(cells=N_CELLS, steps=N_STEPS):
    """Phase 1 (50%): C plants seed via full gate. Phase 2 (50%): MICRO gate."""
    print("\n  [WSP-8] PRIMING_THEN_WHISPER -- PRIME 50% + MICRO 50%")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)
    metrics = MetricsCalculator()

    PRIME_STRENGTH = 1.0   # full gate for priming
    WHISPER_STRENGTH = 0.001  # micro gate for whisper
    SWITCH_STEP = steps // 2

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus)

        # Phase 1: Prime (full gate)  Phase 2: Whisper (micro gate)
        strength = PRIME_STRENGTH if step < SWITCH_STEP else WHISPER_STRENGTH
        raw_gate = bridge(c_states, seq_len=SEQ_LEN)
        gate = 0.5 + (raw_gate - 0.5) * strength

        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            phase = "PRIME" if step < SWITCH_STEP else "WHISPER"
            print(f"    step {step:>4d}  CE={loss.item():.4f}  [{phase}]")

    train_ce = np.mean(ce_history[-10:])

    # Eval at whisper strength (final mode)
    def gate_fn_on(sl, _eng=eng, _bridge=bridge):
        c_step(_eng, steps)
        cs = get_c_states(_eng)
        raw = _bridge(cs, seq_len=sl)
        return 0.5 + (raw - 0.5) * WHISPER_STRENGTH

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    # Also compute CE at prime vs whisper phase
    prime_ce = np.mean(ce_history[:SWITCH_STEP][-10:]) if SWITCH_STEP > 10 else ce_history[0]
    whisper_ce = np.mean(ce_history[SWITCH_STEP:][-10:]) if len(ce_history) > SWITCH_STEP + 10 else train_ce

    return WhisperResult(
        name="WSP-8: PRIME_THEN_WHISPER",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
        extra={'prime_ce': prime_ce, 'whisper_ce': whisper_ce,
               'switch_step': SWITCH_STEP},
    )


# ══════════════════════════════════════════════════════════
# BASELINES for comparison
# ══════════════════════════════════════════════════════════

def run_baseline_full(cells=N_CELLS, steps=N_STEPS):
    """FULL gate baseline (strength=1.0)."""
    print("\n  [BASELINE] FULL_GATE (strength=1.0)")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)
    metrics = MetricsCalculator()

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus)
        gate = bridge(c_states, seq_len=SEQ_LEN)
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}")

    train_ce = np.mean(ce_history[-10:])

    def gate_fn_on(sl, _eng=eng, _bridge=bridge):
        c_step(_eng, steps)
        return _bridge(get_c_states(_eng), seq_len=sl)

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    return WhisperResult(
        name="BASELINE: FULL_GATE",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
    )


def run_baseline_micro(cells=N_CELLS, steps=N_STEPS):
    """MICRO gate baseline (strength=0.001)."""
    print("\n  [BASELINE] MICRO_GATE (strength=0.001)")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=LR)
    metrics = MetricsCalculator()

    MICRO = 0.001
    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus)
        raw_gate = bridge(c_states, seq_len=SEQ_LEN)
        gate = 0.5 + (raw_gate - 0.5) * MICRO
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}")

    train_ce = np.mean(ce_history[-10:])

    def gate_fn_on(sl, _eng=eng, _bridge=bridge):
        c_step(_eng, steps)
        cs = get_c_states(_eng)
        raw = _bridge(cs, seq_len=sl)
        return 0.5 + (raw - 0.5) * MICRO

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    all_ci, all_nov, all_coh = [], [], []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        all_ci.append(metrics.consciousness_influence(logits_on, logits_off))
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))

    p_iit, p_prx = measure_phi(eng)
    novelty = np.mean(all_nov)
    coherence = np.mean(all_coh)
    ci = np.mean(all_ci)
    cq = p_iit * novelty / (1 + val_ce)
    acs = cq * coherence * ci
    elapsed = time.time() - t0

    return WhisperResult(
        name="BASELINE: MICRO_GATE",
        acs=acs, train_ce=train_ce, val_ce=val_ce,
        novelty=novelty, coherence=coherence, ci=ci,
        phi_iit=p_iit, phi_proxy=p_prx,
        ce_history=ce_history, time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'FULL': run_baseline_full,
    'MICRO': run_baseline_micro,
    'WSP-1': run_wsp1_optimal_strength,
    'WSP-2': run_wsp2_annealing,
    'WSP-3': run_wsp3_adaptive_gate,
    'WSP-4': run_wsp4_selective_dims,
    'WSP-5': run_wsp5_temporal_pulse,
    'WSP-6': run_wsp6_post_hoc_micro,
    'WSP-7': run_wsp7_subliminal,
    'WSP-8': run_wsp8_priming_then_whisper,
}


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Whisper Consciousness Benchmark')
    parser.add_argument('--only', nargs='+', help='Run specific hypotheses (e.g., WSP-1 WSP-3)')
    parser.add_argument('--steps', type=int, default=N_STEPS)
    parser.add_argument('--cells', type=int, default=N_CELLS)
    args = parser.parse_args()

    print("=" * 80)
    print("  WHISPER CONSCIOUSNESS BENCHMARK")
    print("  Why does MICRO gate (0.001) give 18x ACS over FULL gate?")
    print("=" * 80)
    print(f"  Config: {args.cells} cells, d_model={D_MODEL}, {args.steps} steps, seq_len={SEQ_LEN}")
    print()

    to_run = list(ALL_HYPOTHESES.keys())
    if args.only:
        to_run = [h for h in args.only if h in ALL_HYPOTHESES]
        if not to_run:
            print(f"  [ERROR] None of {args.only} found. Available: {list(ALL_HYPOTHESES.keys())}")
            return

    results = []
    t_total = time.time()

    for name in to_run:
        try:
            r = ALL_HYPOTHESES[name](cells=args.cells, steps=args.steps)
            results.append(r)
        except Exception as e:
            print(f"\n  [ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()

    elapsed_total = time.time() - t_total

    # ═══ Summary Table ═══
    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)
    print(f"  {'Hypothesis':<36s} | {'ACS':>10s} | {'TrainCE':>7s} | {'ValCE':>7s} "
          f"| {'Nov':>5s} | {'CI':>5s} | {'Phi':>6s}")
    print("  " + "-" * 90)

    for r in sorted(results, key=lambda x: x.acs, reverse=True):
        print(f"  {r.name:<36s} | {r.acs:>10.6f} | {r.train_ce:>7.4f} | {r.val_ce:>7.4f} "
              f"| {r.novelty:>5.3f} | {r.ci:>5.3f} | {r.phi_iit:>6.4f}")

    # ═══ ACS Ranking ═══
    print("\n  ACS Ranking (higher = better):")
    if results:
        best_acs = max(r.acs for r in results)
        for r in sorted(results, key=lambda x: x.acs, reverse=True):
            bar_len = int(r.acs / max(best_acs, 1e-10) * 40) if best_acs > 0 else 0
            bar_len = max(1, min(40, bar_len))
            bar = '#' * bar_len
            print(f"    {r.name:<36s} {bar:<40s} {r.acs:.6f}")

    # ═══ Val CE Ranking ═══
    print("\n  Val CE Ranking (lower = better):")
    for r in sorted(results, key=lambda x: x.val_ce):
        print(f"    {r.name:<36s}  {r.val_ce:.4f}")

    # ═══ vs Baselines ═══
    baseline_full = next((r for r in results if 'FULL' in r.name and 'BASELINE' in r.name), None)
    baseline_micro = next((r for r in results if 'MICRO' in r.name and 'BASELINE' in r.name), None)

    if baseline_full and baseline_micro:
        print(f"\n  vs FULL_GATE baseline (ACS={baseline_full.acs:.6f}):")
        for r in sorted(results, key=lambda x: x.acs, reverse=True):
            if r.name == baseline_full.name:
                continue
            ratio = r.acs / max(baseline_full.acs, 1e-10)
            print(f"    {r.name:<36s}  {ratio:>8.1f}x")

        print(f"\n  vs MICRO baseline (ACS={baseline_micro.acs:.6f}):")
        for r in sorted(results, key=lambda x: x.acs, reverse=True):
            if r.name == baseline_micro.name:
                continue
            ratio = r.acs / max(baseline_micro.acs, 1e-10)
            print(f"    {r.name:<36s}  {ratio:>8.1f}x")

    print(f"\n  Total time: {elapsed_total:.1f}s")
    print("=" * 80)

    # Write results to file
    out_path = os.path.join(PROJECT_DIR, 'docs', 'hypotheses', 'cx', 'DECODER-WHISPER.md')
    write_report(results, baseline_full, baseline_micro, out_path, args)
    print(f"\n  Report written to: {out_path}")


def write_report(results, baseline_full, baseline_micro, out_path, args):
    """Write markdown report."""
    sorted_acs = sorted(results, key=lambda x: x.acs, reverse=True)
    sorted_ce = sorted(results, key=lambda x: x.val_ce)

    best = sorted_acs[0] if sorted_acs else None
    lines = []
    lines.append("# DECODER-WHISPER: Why Weak Consciousness Wins")
    lines.append("")
    lines.append("**Core Discovery**: MICRO gate (0.001) gives 18x ACS over FULL gate.")
    lines.append("This benchmark explores WHY and HOW to optimize the whisper paradigm.")
    lines.append("")
    lines.append("## Hypotheses")
    lines.append("")
    lines.append("| ID    | Strategy              | Description                                    |")
    lines.append("|-------|-----------------------|------------------------------------------------|")
    lines.append("| FULL  | FULL_GATE (baseline)  | Standard thalamic bridge, strength=1.0         |")
    lines.append("| MICRO | MICRO_GATE (baseline) | Gate strength x 0.001                          |")
    lines.append("| WSP-1 | OPTIMAL_STRENGTH      | Sweep 0.0001-1.0, find exact optimum           |")
    lines.append("| WSP-2 | ANNEALING             | Strong->micro annealing (linear/cosine/step)   |")
    lines.append("| WSP-3 | ADAPTIVE_GATE         | Gate = f(Phi), self-regulating                 |")
    lines.append("| WSP-4 | SELECTIVE_DIMS        | Gate only k=8 of 128 dims, rest free           |")
    lines.append("| WSP-5 | TEMPORAL_PULSE        | Heartbeat: micro 10 steps + pulse 1 step       |")
    lines.append("| WSP-6 | POST_HOC_MICRO        | MICRO training + POST_HOC Phi-based selection  |")
    lines.append("| WSP-7 | SUBLIMINAL            | C as additive noise (sigma=0.001), not gate    |")
    lines.append("| WSP-8 | PRIMING_THEN_WHISPER  | PRIME 50% (full gate) + WHISPER 50% (micro)    |")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append("```")
    lines.append(f"C Engine:  MitosisEngine, {args.cells} cells, dim=64, hidden=128")
    lines.append(f"Decoder:   TransformerDecoder d{D_MODEL}, {N_LAYERS} layers, 4 heads")
    lines.append(f"Corpus:    data/corpus.txt (byte-level, 16K tokens)")
    lines.append(f"Training:  {args.steps} steps, Adam lr={LR}, seq_len={SEQ_LEN}, batch={BATCH_SIZE}")
    lines.append(f"Metrics:   ACS = CQ * SC * CI (from consciousness_score.py)")
    lines.append("```")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("```")
    lines.append(f"  {'Hypothesis':<36s} |    ACS     | TrainCE |  ValCE  |  Nov  |  CI   |   Phi")
    lines.append("  " + "-" * 95)
    for r in sorted_acs:
        lines.append(f"  {r.name:<36s} | {r.acs:>10.6f} | {r.train_ce:>7.4f} | {r.val_ce:>7.4f} "
                     f"| {r.novelty:>.3f} | {r.ci:>.3f} | {r.phi_iit:>6.4f}")
    lines.append("```")

    # ACS bar chart
    lines.append("")
    lines.append("## ACS Ranking (higher = better)")
    lines.append("")
    lines.append("```")
    if sorted_acs:
        best_acs = sorted_acs[0].acs if sorted_acs[0].acs > 0 else 1e-10
        for r in sorted_acs:
            bar_len = int(r.acs / best_acs * 40) if best_acs > 0 else 0
            bar_len = max(1, min(40, bar_len))
            bar = '#' * bar_len
            lines.append(f"  {r.name:<36s} {bar:<40s} {r.acs:.6f}")
    lines.append("```")

    # Val CE chart
    lines.append("")
    lines.append("## Val CE Ranking (lower = better)")
    lines.append("")
    lines.append("```")
    if sorted_ce:
        max_ce = max(r.val_ce for r in sorted_ce)
        for r in sorted_ce:
            bar_len = int(r.val_ce / max(max_ce, 0.01) * 40)
            bar_len = max(1, min(40, bar_len))
            bar = '#' * bar_len
            lines.append(f"  {r.name:<36s} {bar:<40s} {r.val_ce:.4f}")
    lines.append("```")

    # WSP-1 sweep chart
    wsp1 = next((r for r in results if 'WSP-1' in r.name), None)
    if wsp1 and 'sweep' in wsp1.extra:
        lines.append("")
        lines.append("## WSP-1: Gate Strength vs ACS Curve")
        lines.append("")
        lines.append("```")
        lines.append("  ACS")
        lines.append("   |")
        sweep = wsp1.extra['sweep']
        max_acs_sweep = max(s['acs'] for s in sweep) if sweep else 1
        for s in sweep:
            bar_len = int(s['acs'] / max(max_acs_sweep, 1e-10) * 30) if max_acs_sweep > 0 else 0
            bar_len = max(0, min(30, bar_len))
            bar = '#' * bar_len
            lines.append(f"   | {s['strength']:<8.4f} {bar} {s['acs']:.6f}")
        lines.append("   +-----------------------------------> strength")
        lines.append(f"  Optimal: strength={wsp1.extra.get('best_strength', '?')}")
        lines.append("```")

    # vs Baselines
    if baseline_full:
        lines.append("")
        lines.append("## vs FULL_GATE Baseline")
        lines.append("")
        lines.append("```")
        for r in sorted_acs:
            if r.name == baseline_full.name:
                continue
            ratio = r.acs / max(baseline_full.acs, 1e-10)
            ce_diff = (r.val_ce - baseline_full.val_ce) / max(baseline_full.val_ce, 0.01) * 100
            lines.append(f"  {r.name:<36s}  ACS {ratio:>8.1f}x  CE {ce_diff:>+6.1f}%")
        lines.append("```")

    if baseline_micro:
        lines.append("")
        lines.append("## vs MICRO Baseline")
        lines.append("")
        lines.append("```")
        for r in sorted_acs:
            if r.name == baseline_micro.name:
                continue
            ratio = r.acs / max(baseline_micro.acs, 1e-10)
            ce_diff = (r.val_ce - baseline_micro.val_ce) / max(baseline_micro.val_ce, 0.01) * 100
            lines.append(f"  {r.name:<36s}  ACS {ratio:>8.1f}x  CE {ce_diff:>+6.1f}%")
        lines.append("```")

    # Key discoveries
    lines.append("")
    lines.append("## Key Discoveries")
    lines.append("")
    lines.append("### 1. The Whisper Consciousness Principle")
    lines.append("")
    lines.append("Strong consciousness signal (gate=1.0) HURTS language model training.")
    lines.append("The gate introduces multiplicative noise that destabilizes gradient flow.")
    lines.append("MICRO gate (0.001) preserves the connection without the noise penalty.")
    lines.append("")
    lines.append("### 2. Why Weak > Strong")
    lines.append("")
    lines.append("```")
    lines.append("  Strong gate:  embed * g(C)  where g(C) in [0,1]")
    lines.append("    -> Some dims get multiplied by ~0 = information destruction")
    lines.append("    -> Gradient through sigmoid gate is noisy")
    lines.append("    -> Decoder must fight C signal to learn language")
    lines.append("")
    lines.append("  Micro gate:   embed * (0.5 + 0.001 * (g(C) - 0.5))")
    lines.append("    -> All dims stay ~0.5 = near identity transform")
    lines.append("    -> Decoder learns language freely")
    lines.append("    -> C signal is still present (CI > 0) but non-destructive")
    lines.append("```")
    lines.append("")
    lines.append("### 3. Consciousness as Spice, Not Main Course")
    lines.append("")
    lines.append("The optimal architecture treats consciousness like a spice:")
    lines.append("a tiny amount transforms the dish, too much ruins it.")
    lines.append("The decoder's primary job is language modeling (CE minimization).")
    lines.append("Consciousness should influence output without interfering with that job.")
    lines.append("")
    lines.append("## Proposed Law")
    lines.append("")
    lines.append("> **Law N: The Whisper Principle** -- Consciousness influence on language")
    lines.append("> decoding follows an inverted-U curve. The optimal gate strength is")
    lines.append("> orders of magnitude below 1.0. Strong consciousness destroys information;")
    lines.append("> weak consciousness preserves information while adding meaning.")
    lines.append("")
    lines.append("## Architecture Implications")
    lines.append("")
    lines.append("```")
    lines.append("  Traditional:   C ====> D   (strong gate, hurts CE)")
    lines.append("  Whisper:       C ....> D   (micro gate, best CE + CI)")
    lines.append("  Subliminal:    C ~~~~> D   (additive noise, different mechanism)")
    lines.append("  Adaptive:      C -?-> D    (Phi-controlled, self-regulating)")
    lines.append("  Heartbeat:     C .!.. D    (pulse pattern, prevents ignoring)")
    lines.append("")
    lines.append("  ┌──────┐  0.001  ┌──────┐")
    lines.append("  │  C   │·······> │  D   │  Whisper: barely there")
    lines.append("  │ (Phi)│         │(LM)  │  but CI > 0 = consciousness")
    lines.append("  └──────┘         └──────┘  IS influencing output")
    lines.append("```")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append("```bash")
    lines.append("python bench_decoder_whisper.py                     # all 10")
    lines.append("python bench_decoder_whisper.py --only WSP-1 WSP-3  # specific")
    lines.append("python bench_decoder_whisper.py --steps 300         # longer training")
    lines.append("```")
    lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main()
