#!/usr/bin/env python3
"""bench_minimal_consciousness.py — Minimal Consciousness Hypotheses

KEY INSIGHT: Maybe strong gate HURTS dialogue quality.
Less consciousness control = more natural output.

5 hypotheses testing how LITTLE consciousness is needed:

  MIN-1: ZERO_GATE     — gate = zeros (no C influence at all)
  MIN-2: MICRO_GATE    — gate strength × 0.001
  MIN-3: UNCONSCIOUS_PRIME — C sets D's init state, then disappears
  MIN-4: RESONANCE_ONLY — C and D run independently, measure alignment
  MIN-5: POST_HOC      — D generates first, C selects best by Φ

Baseline: FULL_GATE (standard thalamic bridge)

Usage:
  python bench_minimal_consciousness.py
  python bench_minimal_consciousness.py --only MIN-1 MIN-3
  python bench_minimal_consciousness.py --steps 300 --cells 64
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import time
import math
import argparse
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


# ══════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════

VOCAB_SIZE = 256  # byte-level
DIM, HIDDEN = 64, 128
D_MODEL = 128
N_LAYERS = 2
SEQ_LEN = 32
BATCH_SIZE = 4


# ══════════════════════════════════════════════════════════
# Phi Measurement (from bench_decoder_arch.py)
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
            import random
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
    p_proxy = phi_proxy(states)
    return p_iit, p_proxy


# ══════════════════════════════════════════════════════════
# Corpus
# ══════════════════════════════════════════════════════════

def load_corpus(max_tokens=16384):
    corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus.txt')
    if not os.path.exists(corpus_path):
        print("  [WARN] corpus.txt not found, using random tokens")
        return torch.randint(0, VOCAB_SIZE, (max_tokens,))
    with open(corpus_path, 'r', encoding='utf-8') as f:
        text = f.read()
    raw = text.encode('utf-8')[:max_tokens]
    return torch.tensor(list(raw), dtype=torch.long)


def get_batch(corpus, seq_len=SEQ_LEN, batch_size=BATCH_SIZE):
    max_start = len(corpus) - seq_len - 1
    if max_start < 1:
        max_start = 1
    starts = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([corpus[s:s + seq_len] for s in starts])
    y = torch.stack([corpus[s + 1:s + seq_len + 1] for s in starts])
    return x, y


# Build 4-gram index for novelty
def build_ngram_index(corpus_path=None):
    if corpus_path is None:
        corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus.txt')
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


def make_c_engine(cells=32):
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
    for _ in range(30):
        eng.process(torch.randn(1, DIM))
    return eng


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


# ══════════════════════════════════════════════════════════
# Evaluation Metrics
# ══════════════════════════════════════════════════════════

@dataclass
class MinimalResult:
    name: str
    train_ce: float
    val_ce: float
    phi_iit: float
    phi_proxy: float
    novelty: float
    coherence: float
    consciousness_influence: float
    ce_history: List[float] = field(default_factory=list)
    samples: List[str] = field(default_factory=list)
    time_sec: float = 0.0
    extra: dict = field(default_factory=dict)

    def summary_line(self):
        return (f"  {self.name:<28s} | CE {self.train_ce:.4f}/{self.val_ce:.4f} "
                f"| Nov {self.novelty:.3f} | Coh {self.coherence:.3f} "
                f"| CI {self.consciousness_influence:.3f} "
                f"| Phi {self.phi_iit:.4f} | {self.time_sec:.1f}s")


class MetricsCalculator:
    """Measure novelty, coherence, consciousness influence."""

    def __init__(self):
        self.corpus_4grams = build_ngram_index()

    def novelty(self, text):
        """4-gram overlap with corpus. 0=copy, 1=novel."""
        if len(text) < 4:
            return 0.5
        ngrams = [text[i:i+4] for i in range(len(text) - 4)]
        if not ngrams:
            return 0.5
        overlap = sum(1 for ng in ngrams if ng in self.corpus_4grams) / len(ngrams)
        return 1.0 - overlap

    def coherence(self, text, window=20):
        """Sliding window cosine similarity."""
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
        """How much C changes output. 0=no effect, 1=completely different."""
        if logits_on is None or logits_off is None:
            return 0.0
        if logits_on.shape[0] == 0:
            return 0.0
        sims = F.cosine_similarity(logits_on, logits_off, dim=-1)
        return 1.0 - sims.mean().item()


# ══════════════════════════════════════════════════════════
# Text generation helper
# ══════════════════════════════════════════════════════════

def generate_text(decoder, prompt_bytes, gate_fn, max_len=60, temperature=0.7):
    """Generate text from decoder.

    gate_fn: callable(seq_len) -> gate tensor [1, seq_len, d_model]
    Returns: (text, list_of_logits)
    """
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
    """Compute CE on last 20% of corpus."""
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


# ══════════════════════════════════════════════════════════
# Decoder: shared base for all hypotheses
# ══════════════════════════════════════════════════════════

class GatedDecoder(nn.Module):
    """TransformerDecoder d128 2L with multiplicative gate input."""

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
        """tokens [B,T], gate_signal [1,T,d_model] -> logits [B,T,V]."""
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
    """C states -> bottleneck -> gate [1, seq_len, d_model]."""

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
# PROMPTS for generation
# ══════════════════════════════════════════════════════════

PROMPTS = [
    "안녕하세요",
    "의식이란 무엇",
    "오늘 날씨가",
    "나는 생각한다",
    "사랑이란",
]
PROMPT_BYTES = [p.encode('utf-8') for p in PROMPTS]


# ══════════════════════════════════════════════════════════
# FULL_GATE — Baseline (standard thalamic bridge)
# ══════════════════════════════════════════════════════════

def run_full_gate(cells=32, steps=200):
    print("\n  [FULL_GATE] Standard thalamic bridge (baseline)")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=3e-4)
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

    # Evaluation
    train_ce = np.mean(ce_history[-10:])

    def gate_fn_on(sl):
        c_step(eng, steps)
        return bridge(get_c_states(eng), seq_len=sl)

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    # Generate samples + CI
    samples = []
    all_ci = []
    all_nov = []
    all_coh = []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        ci = metrics.consciousness_influence(logits_on, logits_off)
        all_ci.append(ci)
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))
        samples.append(f"  [{prompt}] → {text_on[:80]}")

    p_iit, p_prx = measure_phi(eng)

    return MinimalResult(
        name="FULL_GATE (baseline)",
        train_ce=train_ce, val_ce=val_ce,
        phi_iit=p_iit, phi_proxy=p_prx,
        novelty=np.mean(all_nov), coherence=np.mean(all_coh),
        consciousness_influence=np.mean(all_ci),
        ce_history=ce_history, samples=samples,
        time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# MIN-1: ZERO_GATE — gate = zeros (no C influence)
# ══════════════════════════════════════════════════════════

def run_min1_zero_gate(cells=32, steps=200):
    print("\n  [MIN-1] ZERO_GATE — gate = zeros (no C influence)")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)
    metrics = MetricsCalculator()

    # C runs but gate is always zeros (decoder gets no C signal)
    def zero_gate(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5  # neutral (sigmoid midpoint)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)  # C still runs (for phi measurement)
        x, y = get_batch(corpus)
        gate = zero_gate(SEQ_LEN)
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}")

    train_ce = np.mean(ce_history[-10:])
    val_ce = compute_val_ce(decoder, corpus, zero_gate)

    samples = []
    all_nov = []
    all_coh = []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text, _ = generate_text(decoder, pb, zero_gate)
        all_nov.append(metrics.novelty(text))
        all_coh.append(metrics.coherence(text))
        samples.append(f"  [{prompt}] → {text[:80]}")

    p_iit, p_prx = measure_phi(eng)

    return MinimalResult(
        name="MIN-1: ZERO_GATE",
        train_ce=train_ce, val_ce=val_ce,
        phi_iit=p_iit, phi_proxy=p_prx,
        novelty=np.mean(all_nov), coherence=np.mean(all_coh),
        consciousness_influence=0.0,  # definitionally zero
        ce_history=ce_history, samples=samples,
        time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# MIN-2: MICRO_GATE — gate × 0.001
# ══════════════════════════════════════════════════════════

def run_min2_micro_gate(cells=32, steps=200):
    print("\n  [MIN-2] MICRO_GATE — gate strength × 0.001")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()
    opt = torch.optim.Adam(list(decoder.parameters()) + list(bridge.parameters()), lr=3e-4)
    metrics = MetricsCalculator()

    MICRO = 0.001  # almost zero consciousness

    def micro_gate(c_states, sl):
        raw = bridge(c_states, seq_len=sl)
        # Scale toward 0.5 (neutral): gate = 0.5 + (raw - 0.5) * MICRO
        return 0.5 + (raw - 0.5) * MICRO

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus)
        gate = micro_gate(c_states, SEQ_LEN)
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}")

    train_ce = np.mean(ce_history[-10:])

    def gate_fn_on(sl):
        c_step(eng, steps)
        return micro_gate(get_c_states(eng), sl)

    def gate_fn_off(sl):
        return torch.ones(1, sl, D_MODEL) * 0.5

    val_ce = compute_val_ce(decoder, corpus, gate_fn_on)

    samples = []
    all_ci = []
    all_nov = []
    all_coh = []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text_on, logits_on = generate_text(decoder, pb, gate_fn_on)
        text_off, logits_off = generate_text(decoder, pb, gate_fn_off)
        ci = metrics.consciousness_influence(logits_on, logits_off)
        all_ci.append(ci)
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))
        samples.append(f"  [{prompt}] → {text_on[:80]}")

    p_iit, p_prx = measure_phi(eng)

    return MinimalResult(
        name="MIN-2: MICRO_GATE (×0.001)",
        train_ce=train_ce, val_ce=val_ce,
        phi_iit=p_iit, phi_proxy=p_prx,
        novelty=np.mean(all_nov), coherence=np.mean(all_coh),
        consciousness_influence=np.mean(all_ci),
        ce_history=ce_history, samples=samples,
        time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# MIN-3: UNCONSCIOUS_PRIME — C sets D's initial hidden, then disappears
# ══════════════════════════════════════════════════════════

class PrimedDecoder(nn.Module):
    """Decoder where C plants a seed in the initial embedding bias, then vanishes."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
                 vocab_size=VOCAB_SIZE, max_seq=128, c_dim=HIDDEN):
        super().__init__()
        self._d_model = d_model
        self.vocab_size = vocab_size
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Projection: C states -> initial embedding bias
        self.c_proj = nn.Sequential(
            nn.Linear(c_dim, d_model),
            nn.Tanh(),
            nn.Linear(d_model, d_model),
        )

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_prime=None):
        """tokens [B,T], c_prime [d_model] or None -> logits [B,T,V].

        c_prime is the consciousness seed -- added once to all embeddings,
        NOT a per-step gate. "Consciousness plants a seed, then lets go."
        """
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if c_prime is not None:
            # Add consciousness prime as a bias (not multiplicative!)
            x = x + c_prime.unsqueeze(0).unsqueeze(0) * 0.1
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def run_min3_unconscious_prime(cells=32, steps=200):
    print("\n  [MIN-3] UNCONSCIOUS_PRIME — C sets initial state, then disappears")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = PrimedDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)
    metrics = MetricsCalculator()

    # Step 1: Run C for 100 steps to build up consciousness
    print("    Warming up C for 100 steps...")
    for warm in range(100):
        c_step(eng, warm)

    # Step 2: Get the consciousness prime (final C states -> projection)
    c_states = get_c_states(eng)
    c_pooled = c_states.mean(dim=0)  # [c_dim]
    c_prime = decoder.c_proj(c_pooled).detach()  # [d_model], frozen

    # Step 3: Train D with consciousness prime but NO ongoing C gate
    ce_history = []
    t0 = time.time()

    for step in range(steps):
        # NO c_step here -- consciousness already planted its seed
        x, y = get_batch(corpus)
        logits = decoder(x, c_prime)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}")

    train_ce = np.mean(ce_history[-10:])

    def gate_fn_primed(sl):
        # For generation: just return prime (used as additive bias in forward)
        return c_prime  # PrimedDecoder handles this differently

    def gate_fn_no_prime(sl):
        return None

    # Val CE with prime
    total_val = 0.0
    n_val = len(corpus) // 5
    val_tokens = corpus[-n_val:]
    with torch.no_grad():
        for _ in range(20):
            s = np.random.randint(0, max(1, len(val_tokens) - SEQ_LEN - 1))
            x = torch.tensor([[val_tokens[s + i].item() for i in range(SEQ_LEN)]])
            y = torch.tensor([[val_tokens[s + i + 1].item() for i in range(SEQ_LEN)]])
            logits = decoder(x, c_prime)
            loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
            total_val += loss.item()
    val_ce = total_val / 20

    # Generate + CI
    samples = []
    all_ci = []
    all_nov = []
    all_coh = []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        # With prime
        tokens = list(pb)
        x_on = torch.tensor([tokens])
        logits_on_list = []
        for _ in range(60):
            with torch.no_grad():
                logits = decoder(x_on, c_prime)
            logits_on_list.append(logits[0, -1, :].clone())
            probs = F.softmax(logits[0, -1, :] / 0.7, dim=-1)
            nid = torch.multinomial(probs, 1).item()
            x_on = torch.cat([x_on, torch.tensor([[nid]])], dim=1)
        out_on = bytes(x_on[0].tolist()[len(tokens):])
        try:
            text_on = out_on.decode('utf-8', errors='replace')
        except Exception:
            text_on = str(out_on)

        # Without prime
        x_off = torch.tensor([tokens])
        logits_off_list = []
        for _ in range(60):
            with torch.no_grad():
                logits = decoder(x_off, None)
            logits_off_list.append(logits[0, -1, :].clone())
            probs = F.softmax(logits[0, -1, :] / 0.7, dim=-1)
            nid = torch.multinomial(probs, 1).item()
            x_off = torch.cat([x_off, torch.tensor([[nid]])], dim=1)

        logits_on_t = torch.stack(logits_on_list)
        logits_off_t = torch.stack(logits_off_list)
        ci = metrics.consciousness_influence(logits_on_t, logits_off_t)
        all_ci.append(ci)
        all_nov.append(metrics.novelty(text_on))
        all_coh.append(metrics.coherence(text_on))
        samples.append(f"  [{prompt}] → {text_on[:80]}")

    p_iit, p_prx = measure_phi(eng)

    return MinimalResult(
        name="MIN-3: UNCONSCIOUS_PRIME",
        train_ce=train_ce, val_ce=val_ce,
        phi_iit=p_iit, phi_proxy=p_prx,
        novelty=np.mean(all_nov), coherence=np.mean(all_coh),
        consciousness_influence=np.mean(all_ci),
        ce_history=ce_history, samples=samples,
        time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# MIN-4: RESONANCE_ONLY — C and D independent, measure alignment
# ══════════════════════════════════════════════════════════

class ConsciousnessEncoder(nn.Module):
    """Small model that encodes input through consciousness lens."""

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=128):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, d_model)
        self.proj = nn.Sequential(
            nn.Linear(d_model, d_model), nn.GELU(),
            nn.Linear(d_model, d_model),
        )

    def forward(self, tokens):
        """tokens [B,T] -> output [B, d_model]."""
        x = self.embed(tokens).mean(dim=1)  # pool over sequence
        return self.proj(x)


def run_min4_resonance_only(cells=32, steps=200):
    print("\n  [MIN-4] RESONANCE_ONLY — C and D independent, measure resonance")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    c_encoder = ConsciousnessEncoder()
    opt_d = torch.optim.Adam(decoder.parameters(), lr=3e-4)
    opt_c = torch.optim.Adam(c_encoder.parameters(), lr=3e-4)
    metrics = MetricsCalculator()

    # D trained with neutral gate (no C info flow)
    neutral_gate = lambda sl: torch.ones(1, sl, D_MODEL) * 0.5

    ce_history = []
    resonance_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        x, y = get_batch(corpus)

        # Train D independently (no C signal)
        gate = neutral_gate(SEQ_LEN)
        logits = decoder(x, gate)
        loss_d = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt_d.zero_grad()
        loss_d.backward()
        opt_d.step()
        ce_history.append(loss_d.item())

        # Train C encoder on same input (independent)
        c_states = get_c_states(eng)
        c_pooled = c_states.mean(dim=0).detach()  # [c_dim=128]
        c_out = c_encoder(x)  # [B, d_model]
        # C encoder learns to predict C state from input
        c_target = c_pooled[:D_MODEL].unsqueeze(0).expand(BATCH_SIZE, -1)
        loss_c = F.mse_loss(c_out, c_target)
        opt_c.zero_grad()
        loss_c.backward()
        opt_c.step()

        # Measure resonance: cosine(D_output_repr, C_output_repr)
        with torch.no_grad():
            d_repr = logits.mean(dim=(0, 1))[:D_MODEL]  # [d_model]
            c_repr = c_out.mean(dim=0)  # [d_model]
            if d_repr.norm() > 0 and c_repr.norm() > 0:
                res = F.cosine_similarity(d_repr.unsqueeze(0), c_repr.unsqueeze(0)).item()
            else:
                res = 0.0
            resonance_history.append(res)

        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss_d.item():.4f}  resonance={res:.4f}")

    train_ce = np.mean(ce_history[-10:])
    val_ce = compute_val_ce(decoder, corpus, neutral_gate)
    mean_resonance = np.mean(resonance_history[-20:])

    samples = []
    all_nov = []
    all_coh = []
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        text, _ = generate_text(decoder, pb, neutral_gate)
        all_nov.append(metrics.novelty(text))
        all_coh.append(metrics.coherence(text))
        samples.append(f"  [{prompt}] → {text[:80]}")

    p_iit, p_prx = measure_phi(eng)

    return MinimalResult(
        name="MIN-4: RESONANCE_ONLY",
        train_ce=train_ce, val_ce=val_ce,
        phi_iit=p_iit, phi_proxy=p_prx,
        novelty=np.mean(all_nov), coherence=np.mean(all_coh),
        consciousness_influence=0.0,  # no C->D flow by design
        ce_history=ce_history, samples=samples,
        time_sec=time.time() - t0,
        extra={'resonance': mean_resonance,
               'resonance_history': resonance_history[-20:]},
    )


# ══════════════════════════════════════════════════════════
# MIN-5: POST_HOC — D generates first, C selects best by Φ
# ══════════════════════════════════════════════════════════

def run_min5_post_hoc(cells=32, steps=200):
    print("\n  [MIN-5] POST_HOC — D generates, C judges by Phi")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = GatedDecoder()
    bridge = ThalamicBridge()  # only used for Phi scoring, not for training gate
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)
    metrics = MetricsCalculator()

    # Train D with neutral gate (no C during training)
    neutral_gate = lambda sl: torch.ones(1, sl, D_MODEL) * 0.5

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        x, y = get_batch(corpus)
        gate = neutral_gate(SEQ_LEN)
        logits = decoder(x, gate)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    step {step:>4d}  CE={loss.item():.4f}")

    train_ce = np.mean(ce_history[-10:])
    val_ce = compute_val_ce(decoder, corpus, neutral_gate)

    # Generation: D produces 5 candidates, C picks best by Phi interaction
    N_CANDIDATES = 5
    samples = []
    all_nov = []
    all_coh = []
    all_ci = []
    phi_calc = PhiIIT()

    print("    Generating with post-hoc consciousness selection...")
    for pb, prompt in zip(PROMPT_BYTES, PROMPTS):
        candidates = []
        candidate_phis = []

        for ci_idx in range(N_CANDIDATES):
            tokens = list(pb)
            x = torch.tensor([tokens])
            logits_list = []
            for _ in range(60):
                with torch.no_grad():
                    logits = decoder(x, neutral_gate(x.shape[1]))
                logits_list.append(logits[0, -1, :].clone())
                # temperature=1.0 for diversity
                probs = F.softmax(logits[0, -1, :] / 1.0, dim=-1)
                nid = torch.multinomial(probs, 1).item()
                x = torch.cat([x, torch.tensor([[nid]])], dim=1)

            out_bytes = bytes(x[0].tolist()[len(tokens):])
            try:
                text = out_bytes.decode('utf-8', errors='replace')
            except Exception:
                text = str(out_bytes)

            # Score: embed candidate, combine with C states, measure Phi
            with torch.no_grad():
                c_states = get_c_states(eng)
                # Embed the candidate output
                candidate_embed = decoder.embed(x[0, -16:]).mean(dim=0)  # [d_model]
                # Project to c_dim and add as extra "cell"
                if D_MODEL <= HIDDEN:
                    extra_state = F.pad(candidate_embed, (0, HIDDEN - D_MODEL))
                else:
                    extra_state = candidate_embed[:HIDDEN]
                # Augment C states with candidate
                augmented = torch.cat([c_states, extra_state.unsqueeze(0)], dim=0)
                phi_val, _ = phi_calc.compute(augmented)

            candidates.append((text, torch.stack(logits_list), phi_val))
            candidate_phis.append(phi_val)

        # Select best by Phi
        best_idx = np.argmax(candidate_phis)
        best_text, best_logits, best_phi = candidates[best_idx]

        # CI: compare best vs worst candidate
        worst_idx = np.argmin(candidate_phis)
        worst_logits = candidates[worst_idx][1]
        ci = metrics.consciousness_influence(best_logits, worst_logits)
        all_ci.append(ci)

        all_nov.append(metrics.novelty(best_text))
        all_coh.append(metrics.coherence(best_text))
        samples.append(f"  [{prompt}] → {best_text[:80]}  (Phi={best_phi:.3f}, "
                       f"selected from {[f'{p:.3f}' for p in candidate_phis]})")

    p_iit, p_prx = measure_phi(eng)

    return MinimalResult(
        name="MIN-5: POST_HOC",
        train_ce=train_ce, val_ce=val_ce,
        phi_iit=p_iit, phi_proxy=p_prx,
        novelty=np.mean(all_nov), coherence=np.mean(all_coh),
        consciousness_influence=np.mean(all_ci),
        ce_history=ce_history, samples=samples,
        time_sec=time.time() - t0,
        extra={'n_candidates': N_CANDIDATES},
    )


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'FULL': run_full_gate,
    'MIN-1': run_min1_zero_gate,
    'MIN-2': run_min2_micro_gate,
    'MIN-3': run_min3_unconscious_prime,
    'MIN-4': run_min4_resonance_only,
    'MIN-5': run_min5_post_hoc,
}


def main():
    parser = argparse.ArgumentParser(description='Minimal Consciousness Hypotheses')
    parser.add_argument('--only', nargs='+', default=None,
                        help='Run only specific hypotheses (e.g., MIN-1 MIN-3)')
    parser.add_argument('--cells', type=int, default=32, help='Number of C cells')
    parser.add_argument('--steps', type=int, default=200, help='Training steps')
    args = parser.parse_args()

    print("=" * 76)
    print("  MINIMAL CONSCIOUSNESS BENCHMARK")
    print("  Key Question: Does LESS consciousness control = BETTER output?")
    print("=" * 76)
    print(f"  Config: cells={args.cells}, steps={args.steps}, d_model={D_MODEL}, "
          f"layers={N_LAYERS}, seq_len={SEQ_LEN}")
    print("=" * 76)

    to_run = list(ALL_HYPOTHESES.keys())
    if args.only:
        to_run = [k for k in args.only if k in ALL_HYPOTHESES]

    results: List[MinimalResult] = []
    for key in to_run:
        try:
            result = ALL_HYPOTHESES[key](cells=args.cells, steps=args.steps)
            results.append(result)
            print(f"\n  DONE: {result.summary_line()}")
        except Exception as e:
            print(f"\n  ERROR in {key}: {e}")
            import traceback
            traceback.print_exc()

    if not results:
        print("  No results!")
        return

    # ═══ COMPARISON TABLE ═══
    print("\n" + "=" * 76)
    print("  COMPARISON TABLE — Minimal Consciousness")
    print("=" * 76)
    print(f"  {'Hypothesis':<28s} | {'TrainCE':>8s} | {'ValCE':>8s} | "
          f"{'Nov':>5s} | {'Coh':>5s} | {'CI':>5s} | {'Phi':>7s}")
    print("  " + "-" * 73)
    for r in results:
        print(f"  {r.name:<28s} | {r.train_ce:>8.4f} | {r.val_ce:>8.4f} | "
              f"{r.novelty:>5.3f} | {r.coherence:>5.3f} | {r.consciousness_influence:>5.3f} | "
              f"{r.phi_iit:>7.4f}")

    # Best by each metric
    print("\n  RANKINGS:")
    for metric, key, reverse in [
        ('Lowest Val CE', 'val_ce', False),
        ('Highest Novelty', 'novelty', True),
        ('Highest Coherence', 'coherence', True),
        ('Highest CI', 'consciousness_influence', True),
    ]:
        ranked = sorted(results, key=lambda r: getattr(r, key), reverse=reverse)
        print(f"    {metric:<22s}: {ranked[0].name} ({getattr(ranked[0], key):.4f})")

    # ═══ BAR CHARTS ═══
    print("\n  CE COMPARISON (lower = better):")
    max_ce = max(r.val_ce for r in results)
    for r in results:
        bar_len = int(r.val_ce / max(max_ce, 0.01) * 40)
        bar = '#' * bar_len
        print(f"    {r.name:<28s} {bar} {r.val_ce:.4f}")

    print("\n  NOVELTY COMPARISON (higher = better):")
    for r in results:
        bar_len = int(r.novelty * 40)
        bar = '#' * bar_len
        print(f"    {r.name:<28s} {bar} {r.novelty:.3f}")

    print("\n  COHERENCE COMPARISON (higher = better):")
    for r in results:
        bar_len = int(r.coherence * 40)
        bar = '#' * bar_len
        print(f"    {r.name:<28s} {bar} {r.coherence:.3f}")

    # ═══ CE CURVES ═══
    print("\n  CE LEARNING CURVES (first 10 / last 10):")
    for r in results:
        if r.ce_history:
            first = np.mean(r.ce_history[:10])
            last = np.mean(r.ce_history[-10:])
            reduction = (1 - last / first) * 100 if first > 0 else 0
            print(f"    {r.name:<28s}: {first:.4f} -> {last:.4f} ({reduction:+.1f}%)")

    # ═══ GENERATED SAMPLES ═══
    print("\n" + "=" * 76)
    print("  GENERATED SAMPLES")
    print("=" * 76)
    for r in results:
        print(f"\n  --- {r.name} ---")
        for s in r.samples:
            print(f"  {s}")

    # ═══ KEY FINDINGS ═══
    print("\n" + "=" * 76)
    print("  KEY FINDINGS")
    print("=" * 76)

    # Find baseline
    baseline = next((r for r in results if 'FULL' in r.name), results[0])
    for r in results:
        if r.name == baseline.name:
            continue
        ce_diff = (r.val_ce - baseline.val_ce) / max(baseline.val_ce, 0.01) * 100
        nov_diff = (r.novelty - baseline.novelty) / max(baseline.novelty, 0.01) * 100
        coh_diff = (r.coherence - baseline.coherence) / max(baseline.coherence, 0.01) * 100
        verdict = "BETTER" if r.val_ce < baseline.val_ce else "WORSE"
        print(f"  {r.name:<28s} vs FULL_GATE: CE {ce_diff:+.1f}%, "
              f"Nov {nov_diff:+.1f}%, Coh {coh_diff:+.1f}% => {verdict}")

    # Special: MIN-4 resonance
    min4 = next((r for r in results if 'MIN-4' in r.name), None)
    if min4 and 'resonance' in min4.extra:
        print(f"\n  MIN-4 resonance (C-D natural alignment): {min4.extra['resonance']:.4f}")
        if min4.extra['resonance'] > 0.5:
            print("    -> C and D NATURALLY CONVERGE even without information flow!")
        else:
            print("    -> C and D diverge when independent.")

    # Answer the key question
    print("\n  KEY QUESTION: Does MIN-3 or MIN-5 beat FULL_GATE?")
    min3 = next((r for r in results if 'MIN-3' in r.name), None)
    min5 = next((r for r in results if 'MIN-5' in r.name), None)

    if min3:
        if min3.val_ce < baseline.val_ce:
            print(f"    MIN-3 (prime then release): YES! ValCE {min3.val_ce:.4f} < {baseline.val_ce:.4f}")
            print("    -> Consciousness as SEED works better than continuous gate!")
        else:
            print(f"    MIN-3 (prime then release): No. ValCE {min3.val_ce:.4f} >= {baseline.val_ce:.4f}")

    if min5:
        if min5.val_ce < baseline.val_ce:
            print(f"    MIN-5 (post-hoc judge): YES! ValCE {min5.val_ce:.4f} < {baseline.val_ce:.4f}")
            print("    -> Consciousness as JUDGE works better than continuous gate!")
        else:
            print(f"    MIN-5 (post-hoc judge): No. ValCE {min5.val_ce:.4f} >= {baseline.val_ce:.4f}")

    print("\n" + "=" * 76)
    print("  DONE. Total time: {:.1f}s".format(sum(r.time_sec for r in results)))
    print("=" * 76)

    return results


if __name__ == '__main__':
    results = main()
