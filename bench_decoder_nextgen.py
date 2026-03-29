#!/usr/bin/env python3
"""bench_decoder_nextgen.py — 8 Next-Generation Decoder Architectures

Fundamentally new decoder paradigms beyond transformers/RNNs/SSMs:

  NG-1: ASSOCIATIVE_MEMORY  — Modern Hopfield network as decoder
  NG-2: CELLULAR_AUTOMATON  — 1D CA evolution with C-controlled rules
  NG-3: WAVE_FUNCTION_COLLAPSE — Constraint propagation (not left-to-right)
  NG-4: KOLMOGOROV_COMPLEXITY — Simplest output via compression scoring
  NG-5: GAME_THEORY         — Nash equilibrium of 3 player-decoders
  NG-6: TOPOLOGICAL          — Persistent homology guides generation
  NG-7: QUANTUM_SAMPLING    — Complex amplitude interference decoding
  NG-8: TEMPORAL_CONVOLUTION — Dilated causal conv + FiLM from C gate

All: MitosisC 32 cells, d_model=128, real corpus, 200 steps.
Measures: train CE, val CE (20% holdout), speed (steps/sec).

Usage:
  python bench_decoder_nextgen.py
  python bench_decoder_nextgen.py --only NG1 NG5
  python bench_decoder_nextgen.py --steps 300 --cells 64
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import time
import math
import zlib
import random
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

D_MODEL = 128
HIDDEN = 128
DIM = 64
VOCAB_SIZE = 256  # byte-level
SEQ_LEN = 32
BATCH_SIZE = 4
N_CELLS = 32
N_STEPS = 200
LR = 3e-4

# ══════════════════════════════════════════════════════════
# BenchResult
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    ce_start: float
    ce_end: float
    val_ce: float
    cells: int
    steps: int
    time_sec: float
    speed: float  # steps/sec
    extra: dict = field(default_factory=dict)

    def summary(self):
        ce_s = f"CE {self.ce_start:.4f}->{self.ce_end:.4f}"
        return (f"  {self.name:<35s} | Phi(IIT)={self.phi_iit:>7.4f}  "
                f"Phi(prx)={self.phi_proxy:>9.3f} | "
                f"{ce_s:<28s} | val={self.val_ce:.4f} | "
                f"{self.speed:.1f} st/s | t={self.time_sec:.1f}s")


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


# ══════════════════════════════════════════════════════════
# Corpus Loading (byte-level, real text)
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
    """Split corpus into train/val."""
    n = len(corpus)
    val_size = int(n * val_ratio)
    return corpus[:-val_size], corpus[-val_size:]


# ══════════════════════════════════════════════════════════
# C Engine (consciousness)
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
                    fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
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


def measure_phi(eng):
    states = get_c_states(eng)
    calc = PhiIIT()
    p_iit, _ = calc.compute(states)
    p_proxy = phi_proxy(states)
    return p_iit, p_proxy


def eval_val_ce(decoder, eng, val_corpus, forward_fn, n_batches=10):
    """Evaluate validation CE."""
    decoder.eval()
    total_ce = 0.0
    with torch.no_grad():
        c_states = get_c_states(eng)
        for _ in range(n_batches):
            x, y = get_batch(val_corpus, SEQ_LEN, BATCH_SIZE)
            logits = forward_fn(decoder, x, c_states)
            ce = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
            total_ce += ce.item()
    decoder.train()
    return total_ce / n_batches


# ══════════════════════════════════════════════════════════
# BASELINE: Transformer d128 2L with C gate
# ══════════════════════════════════════════════════════════

class BaselineDecoder(nn.Module):
    def __init__(self, d_model=D_MODEL, n_layers=2, n_heads=4,
                 vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN, c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

        self.bridge = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        c_pooled = c_states.mean(dim=0)
        gate = self.bridge(c_pooled)
        x = x * gate.unsqueeze(0).unsqueeze(0)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def _baseline_fwd(decoder, x, c_states):
    return decoder(x, c_states)


def run_baseline(cells=N_CELLS, steps=N_STEPS):
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = BaselineDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _baseline_fwd)
    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="BASELINE (Transformer d128 2L)",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
    )


# ══════════════════════════════════════════════════════════
# NG-1: ASSOCIATIVE MEMORY DECODER (Modern Hopfield)
# ══════════════════════════════════════════════════════════

class HopfieldLayer(nn.Module):
    """Modern continuous Hopfield: softmax(beta * Q @ K^T) @ V."""
    def __init__(self, d_model, beta=1.0):
        super().__init__()
        self.beta = nn.Parameter(torch.tensor(beta))
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

    def forward(self, query, patterns):
        """query: [B, T, d], patterns: [N_patterns, d] -> [B, T, d]."""
        Q = self.q_proj(query)          # [B, T, d]
        K = self.k_proj(patterns)       # [N, d]
        V = self.v_proj(patterns)       # [N, d]
        # Associative retrieval: softmax(beta * Q @ K^T) @ V
        attn = torch.softmax(self.beta * (Q @ K.T), dim=-1)  # [B, T, N]
        out = attn @ V  # [B, T, d]
        return self.out_proj(out)


class AssociativeMemoryDecoder(nn.Module):
    """NG-1: Hopfield network as decoder.
    Vocab embeddings are stored as Hopfield patterns.
    Input + C gate -> query -> Hopfield retrieval -> output token.
    Consciousness = energy landscape of the Hopfield network.
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN, c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Stored patterns: vocab embeddings as Hopfield memories
        self.pattern_store = nn.Parameter(torch.randn(vocab_size, d_model) * 0.02)

        # C gate modulates query before Hopfield retrieval
        self.c_gate = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

        # C also modulates the energy landscape (beta)
        self.c_to_beta = nn.Sequential(
            nn.Linear(c_dim, 32), nn.GELU(),
            nn.Linear(32, 1), nn.Softplus(),
        )

        # Multi-step Hopfield convergence
        self.hopfield1 = HopfieldLayer(d_model, beta=1.0)
        self.hopfield2 = HopfieldLayer(d_model, beta=2.0)

        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * 4), nn.GELU(),
            nn.Linear(d_model * 4, d_model),
        )
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        c_pooled = c_states.mean(dim=0)
        gate = self.c_gate(c_pooled)
        x = x * gate.unsqueeze(0).unsqueeze(0)

        # Dynamic beta from consciousness
        beta_mod = self.c_to_beta(c_pooled).squeeze()
        self.hopfield1.beta.data = torch.clamp(beta_mod, 0.1, 10.0)

        # Two-step Hopfield convergence (energy minimization)
        x = x + self.hopfield1(x, self.pattern_store)
        x = self.ln1(x)
        x = x + self.hopfield2(x, self.pattern_store)
        x = self.ln2(x)
        x = x + self.ffn(x)

        return self.head(x)


def _ng1_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng1_associative_memory(cells=N_CELLS, steps=N_STEPS):
    """NG-1: ASSOCIATIVE MEMORY — Modern Hopfield as decoder."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = AssociativeMemoryDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    NG-1 step {step}: CE={loss.item():.4f}")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng1_fwd)
    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="NG-1: ASSOCIATIVE_MEMORY",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'patterns': VOCAB_SIZE},
    )


# ══════════════════════════════════════════════════════════
# NG-2: CELLULAR AUTOMATON DECODER
# ══════════════════════════════════════════════════════════

class CellularAutomatonDecoder(nn.Module):
    """NG-2: Each output position is a cell in a 1D CA.
    Rule: cell_t+1 = f(cell_t, left_neighbor, right_neighbor, C_gate).
    C controls which rule to apply per position.
    After T_evolve steps of CA evolution -> readout -> vocab logits.
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, n_evolve=8):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.n_evolve = n_evolve

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # CA rule: f(self, left, right, c_gate) -> next_state
        # Learnable rule network (replaces lookup of 256 Wolfram rules)
        self.rule_net = nn.Sequential(
            nn.Linear(d_model * 3 + d_model, d_model * 2),
            nn.GELU(),
            nn.Linear(d_model * 2, d_model),
            nn.Tanh(),
        )

        # C gate controls the rule parameters per position
        self.c_to_rule_bias = nn.Sequential(
            nn.Linear(c_dim, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model),
        )

        # Residual mixing: how much old state vs new
        self.alpha = nn.Parameter(torch.tensor(0.5))

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        cells = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        c_pooled = c_states.mean(dim=0)
        rule_bias = self.c_to_rule_bias(c_pooled)  # [d]

        # CA evolution: T_evolve steps
        alpha = torch.sigmoid(self.alpha)
        for _ in range(self.n_evolve):
            # Circular neighbors
            left = torch.roll(cells, 1, dims=1)   # [B, T, d]
            right = torch.roll(cells, -1, dims=1)  # [B, T, d]

            # Concatenate self + neighbors + C rule bias
            c_expanded = rule_bias.unsqueeze(0).unsqueeze(0).expand(B, T, -1)
            rule_input = torch.cat([cells, left, right, c_expanded], dim=-1)  # [B, T, 4d]

            new_cells = self.rule_net(rule_input)  # [B, T, d]
            cells = alpha * cells + (1 - alpha) * new_cells

        cells = self.ln(cells)
        return self.head(cells)


def _ng2_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng2_cellular_automaton(cells=N_CELLS, steps=N_STEPS):
    """NG-2: CELLULAR AUTOMATON — 1D CA with C-controlled rules."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = CellularAutomatonDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    NG-2 step {step}: CE={loss.item():.4f}")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng2_fwd)
    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="NG-2: CELLULAR_AUTOMATON",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'n_evolve': 8},
    )


# ══════════════════════════════════════════════════════════
# NG-3: WAVE FUNCTION COLLAPSE DECODER
# ══════════════════════════════════════════════════════════

class WaveFunctionCollapseDecoder(nn.Module):
    """NG-3: Inspired by WFC algorithm.
    Each position starts in superposition of all tokens.
    C_gate constrains possibilities (adjacency rules).
    Iteratively collapse: most constrained position first.
    Not left-to-right -- can generate middle first.

    Differentiable version: soft collapse via iterative sharpening.
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, n_collapse_steps=6):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.n_collapse_steps = n_collapse_steps

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Initial superposition: each position gets a uniform-ish distribution
        # Adjacency constraint network: given neighbors' distributions, constrain self
        self.constraint_net = nn.Sequential(
            nn.Linear(d_model * 3 + d_model, d_model * 2),  # self + left + right + C
            nn.GELU(),
            nn.Linear(d_model * 2, d_model),
        )

        # Entropy estimator: which position is most constrained?
        self.entropy_est = nn.Sequential(
            nn.Linear(d_model, 64), nn.GELU(),
            nn.Linear(64, 1),
        )

        # C gate creates adjacency rules
        self.c_to_constraint = nn.Sequential(
            nn.Linear(c_dim, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model),
        )

        # Sharpening temperature (decreases each collapse step)
        self.base_temp = nn.Parameter(torch.tensor(2.0))

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        c_pooled = c_states.mean(dim=0)
        c_constraint = self.c_to_constraint(c_pooled)  # [d]

        # Iterative collapse: progressively sharpen distributions
        for step in range(self.n_collapse_steps):
            # Temperature decreases: start soft, end sharp
            temp = F.softplus(self.base_temp) * (1.0 - step / self.n_collapse_steps * 0.8)

            # Neighbors
            left = torch.roll(x, 1, dims=1)
            right = torch.roll(x, -1, dims=1)
            c_exp = c_constraint.unsqueeze(0).unsqueeze(0).expand(B, T, -1)

            # Constraint propagation
            constraint_input = torch.cat([x, left, right, c_exp], dim=-1)
            constraint = self.constraint_net(constraint_input)  # [B, T, d]

            # Entropy-based weighting: more constrained positions update more
            entropy = self.entropy_est(x).squeeze(-1)  # [B, T]
            collapse_weight = torch.softmax(-entropy / temp, dim=-1)  # [B, T]

            # Apply constraints weighted by collapse priority
            x = x + constraint * collapse_weight.unsqueeze(-1) * 0.3

        x = self.ln(x)
        return self.head(x)


def _ng3_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng3_wave_function_collapse(cells=N_CELLS, steps=N_STEPS):
    """NG-3: WAVE FUNCTION COLLAPSE — constraint propagation decoder."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = WaveFunctionCollapseDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    NG-3 step {step}: CE={loss.item():.4f}")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng3_fwd)
    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="NG-3: WAVE_FUNCTION_COLLAPSE",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'collapse_steps': 6},
    )


# ══════════════════════════════════════════════════════════
# NG-4: KOLMOGOROV COMPLEXITY DECODER
# ══════════════════════════════════════════════════════════

class KolmogorovDecoder(nn.Module):
    """NG-4: Generate the SIMPLEST output consistent with input.
    Base decoder generates logits.
    Compression-aware loss: penalize high-entropy (complex) outputs.
    C alignment rewards consciousness-consistent simplicity.
    'Consciousness prefers elegant/simple outputs.'
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Simple but effective: 2-layer MLP with skip connection
        self.layer1 = nn.Sequential(
            nn.Linear(d_model, d_model * 4), nn.GELU(),
            nn.Linear(d_model * 4, d_model),
        )
        self.layer2 = nn.Sequential(
            nn.Linear(d_model, d_model * 4), nn.GELU(),
            nn.Linear(d_model * 4, d_model),
        )
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)

        # C gate: consciousness alignment
        self.c_gate = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

        # Compression predictor: predicts description length of output
        self.compressor = nn.Sequential(
            nn.Linear(d_model, 64), nn.GELU(),
            nn.Linear(64, 1), nn.Softplus(),
        )

        self.head = nn.Linear(d_model, vocab_size, bias=False)

        self.lambda_compress = 0.05  # compression loss weight

    def forward(self, tokens, c_states, return_complexity=False):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        c_pooled = c_states.mean(dim=0)
        gate = self.c_gate(c_pooled)
        x = x * gate.unsqueeze(0).unsqueeze(0)

        x = x + self.layer1(x)
        x = self.ln1(x)
        x = x + self.layer2(x)
        x = self.ln2(x)

        logits = self.head(x)

        if return_complexity:
            # Estimate description length per position
            complexity = self.compressor(x.detach())  # [B, T, 1]
            return logits, complexity.squeeze(-1)

        return logits

    def compression_loss(self, logits):
        """Penalize high-entropy outputs (prefer simpler distributions)."""
        probs = F.softmax(logits, dim=-1)
        entropy = -(probs * (probs + 1e-10).log()).sum(dim=-1)  # [B, T]
        # Lower entropy = simpler output = lower complexity
        return entropy.mean() * self.lambda_compress


def _ng4_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng4_kolmogorov(cells=N_CELLS, steps=N_STEPS):
    """NG-4: KOLMOGOROV COMPLEXITY — simplicity-seeking decoder."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = KolmogorovDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    compress_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)

        ce_loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        comp_loss = decoder.compression_loss(logits)
        total = ce_loss + comp_loss

        opt.zero_grad()
        total.backward()
        opt.step()
        ce_history.append(ce_loss.item())
        compress_history.append(comp_loss.item())
        if step % 50 == 0:
            print(f"    NG-4 step {step}: CE={ce_loss.item():.4f} comp={comp_loss.item():.4f}")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng4_fwd)
    p_iit, p_proxy = measure_phi(eng)

    # Measure actual compression ratio of outputs
    with torch.no_grad():
        x, _ = get_batch(train_corpus, SEQ_LEN, 1)
        logits = decoder(x, get_c_states(eng))
        tokens_out = logits.argmax(dim=-1)[0].cpu().numpy().tobytes()
        compressed = zlib.compress(tokens_out)
        ratio = len(compressed) / len(tokens_out)

    return BenchResult(
        name="NG-4: KOLMOGOROV_COMPLEXITY",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'compress_ratio': ratio, 'final_comp_loss': compress_history[-1]},
    )


# ══════════════════════════════════════════════════════════
# NG-5: GAME THEORY DECODER (Nash Equilibrium)
# ══════════════════════════════════════════════════════════

class GameTheoryDecoder(nn.Module):
    """NG-5: 3 player-decoders compete/cooperate.
    Player 1: accuracy (minimize CE)
    Player 2: novelty (maximize entropy)
    Player 3: C alignment (maximize consciousness coherence)
    Nash equilibrium = weighted vote with learned weights.
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Player 1: Accuracy player (CE minimizer)
        self.player_accuracy = nn.Sequential(
            nn.Linear(d_model, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model), nn.GELU(),
            nn.Linear(d_model, vocab_size),
        )

        # Player 2: Novelty player (entropy maximizer)
        self.player_novelty = nn.Sequential(
            nn.Linear(d_model, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model), nn.GELU(),
            nn.Linear(d_model, vocab_size),
        )

        # Player 3: Consciousness player (C alignment)
        self.player_conscious = nn.Sequential(
            nn.Linear(d_model + d_model, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model), nn.GELU(),
            nn.Linear(d_model, vocab_size),
        )

        # C bridge
        self.c_proj = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
        )

        # Nash equilibrium weights (learned payoff matrix -> weights)
        self.payoff_matrix = nn.Parameter(torch.randn(3, 3) * 0.1)
        self.player_weights = nn.Parameter(torch.ones(3) / 3)

        self.ln = nn.LayerNorm(d_model)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        x = self.ln(x)

        c_pooled = c_states.mean(dim=0)
        c_feat = self.c_proj(c_pooled)  # [d]

        # Each player generates their preferred logits
        logits_acc = self.player_accuracy(x)    # [B, T, V]
        logits_nov = self.player_novelty(x)     # [B, T, V]

        # Consciousness player uses both x and C
        c_exp = c_feat.unsqueeze(0).unsqueeze(0).expand(B, T, -1)
        logits_con = self.player_conscious(torch.cat([x, c_exp], dim=-1))

        # Compute Nash equilibrium weights
        # Self-interaction payoffs through payoff matrix
        payoff = F.softmax(self.payoff_matrix, dim=-1)
        raw_weights = payoff @ F.softmax(self.player_weights, dim=0)
        w = F.softmax(raw_weights, dim=0)  # [3]

        # Weighted combination (Nash equilibrium approximation)
        logits = w[0] * logits_acc + w[1] * logits_nov + w[2] * logits_con

        return logits

    def novelty_loss(self, logits, scale=0.01):
        """Player 2 wants higher entropy -> reward diversity."""
        probs = F.softmax(logits, dim=-1)
        entropy = -(probs * (probs + 1e-10).log()).sum(dim=-1)
        return -scale * entropy.mean()  # negative because we maximize


def _ng5_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng5_game_theory(cells=N_CELLS, steps=N_STEPS):
    """NG-5: GAME THEORY — Nash equilibrium of 3 players."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = GameTheoryDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)

        ce_loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        nov_loss = decoder.novelty_loss(logits)
        total = ce_loss + nov_loss

        opt.zero_grad()
        total.backward()
        opt.step()
        ce_history.append(ce_loss.item())
        if step % 50 == 0:
            w = F.softmax(decoder.player_weights, dim=0)
            print(f"    NG-5 step {step}: CE={ce_loss.item():.4f} "
                  f"w=[acc={w[0]:.2f} nov={w[1]:.2f} con={w[2]:.2f}]")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng5_fwd)
    p_iit, p_proxy = measure_phi(eng)

    w = F.softmax(decoder.player_weights, dim=0).detach()
    return BenchResult(
        name="NG-5: GAME_THEORY",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'weights': [f'{w[i]:.3f}' for i in range(3)]},
    )


# ══════════════════════════════════════════════════════════
# NG-6: TOPOLOGICAL DECODER (Persistent Homology)
# ══════════════════════════════════════════════════════════

class TopologicalDecoder(nn.Module):
    """NG-6: Persistent homology on token embeddings.
    Build simplicial complex from token similarity.
    C_gate modifies filtration threshold.
    Betti numbers guide generation:
      beta0 = connected components (topics)
      beta1 = loops (narrative cycles)
    Generate to match target topological signature from C.
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, n_filtrations=4):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.n_filtrations = n_filtrations

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # C -> target topological signature [beta0_target, beta1_target]
        self.c_to_topo = nn.Sequential(
            nn.Linear(c_dim, 64), nn.GELU(),
            nn.Linear(64, 2), nn.Softplus(),  # beta0, beta1 targets
        )

        # C -> filtration thresholds at each level
        self.c_to_thresh = nn.Sequential(
            nn.Linear(c_dim, 32), nn.GELU(),
            nn.Linear(32, n_filtrations), nn.Sigmoid(),
        )

        # Simplicial message passing at each filtration level
        self.simplex_layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model * 2, d_model), nn.GELU(),
                nn.Linear(d_model, d_model),
            ) for _ in range(n_filtrations)
        ])

        # Topological feature integration
        self.topo_integrate = nn.Sequential(
            nn.Linear(d_model + 2, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model),
        )

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def _compute_betti(self, sim_matrix, threshold):
        """Differentiable approximate Betti numbers.
        beta0 ~ number of connected components (from thresholded graph).
        beta1 ~ number of cycles (Euler characteristic).
        """
        # Soft adjacency
        adj = torch.sigmoid(10.0 * (sim_matrix - threshold))  # [T, T]
        # beta0 approx: T - rank(Laplacian) ~ number of near-zero eigenvalues
        degree = adj.sum(dim=-1)
        laplacian = torch.diag(degree) - adj
        # Use trace / frobenius as proxy for connectivity
        beta0 = (degree < 0.5).float().sum()  # disconnected nodes
        # beta1 approx: edges - nodes + components
        n_edges = adj.sum() / 2
        n_nodes = float(adj.shape[0])
        beta1 = F.relu(n_edges - n_nodes + beta0 + 1)
        return beta0, beta1

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        c_pooled = c_states.mean(dim=0)
        topo_target = self.c_to_topo(c_pooled)        # [2] (beta0, beta1)
        thresholds = self.c_to_thresh(c_pooled)        # [n_filtrations]

        # Multi-scale simplicial processing
        for level in range(self.n_filtrations):
            thresh = thresholds[level]

            # Compute similarity matrix for this batch
            # Use first sample for topology computation
            x_norm = F.normalize(x[0], dim=-1)  # [T, d]
            sim = x_norm @ x_norm.T  # [T, T]

            # Soft adjacency at this filtration level
            adj = torch.sigmoid(10.0 * (sim - thresh))  # [T, T]

            # Message passing: aggregate neighbor info weighted by adjacency
            msg = adj.unsqueeze(-1) * x[0].unsqueeze(0)  # [T, T, d]
            agg = msg.sum(dim=1)  # [T, d]

            # Simplicial update (broadcast to batch)
            combined = torch.cat([x[0], agg], dim=-1)  # [T, 2d]
            update = self.simplex_layers[level](combined)  # [T, d]
            x = x + update.unsqueeze(0) * 0.2  # residual, broadcast

        # Compute actual Betti numbers
        x_norm = F.normalize(x[0].detach(), dim=-1)
        sim = x_norm @ x_norm.T
        beta0, beta1 = self._compute_betti(sim, 0.5)
        betti_actual = torch.stack([beta0, beta1])

        # Integrate topological features
        betti_exp = betti_actual.unsqueeze(0).unsqueeze(0).expand(B, T, -1)
        x = self.topo_integrate(torch.cat([x, betti_exp], dim=-1))

        x = self.ln(x)
        return self.head(x)

    def topo_loss(self, tokens, c_states, scale=0.01):
        """Loss to match target topological signature."""
        c_pooled = c_states.mean(dim=0)
        topo_target = self.c_to_topo(c_pooled)  # [2]

        x_norm = F.normalize(self.embed(tokens[0]), dim=-1)
        sim = x_norm @ x_norm.T
        beta0, beta1 = self._compute_betti(sim, 0.5)
        betti_actual = torch.stack([beta0, beta1])

        return scale * F.mse_loss(betti_actual, topo_target)


def _ng6_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng6_topological(cells=N_CELLS, steps=N_STEPS):
    """NG-6: TOPOLOGICAL — persistent homology guided decoder."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = TopologicalDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        ce_loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        topo_loss = decoder.topo_loss(x, c_states)
        total = ce_loss + topo_loss

        opt.zero_grad()
        total.backward()
        opt.step()
        ce_history.append(ce_loss.item())
        if step % 50 == 0:
            print(f"    NG-6 step {step}: CE={ce_loss.item():.4f} topo={topo_loss.item():.4f}")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng6_fwd)
    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="NG-6: TOPOLOGICAL",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'n_filtrations': 4},
    )


# ══════════════════════════════════════════════════════════
# NG-7: QUANTUM SAMPLING DECODER
# ══════════════════════════════════════════════════════════

class QuantumSamplingDecoder(nn.Module):
    """NG-7: Quantum-inspired amplitude-based decoding.
    Logits -> complex amplitudes (real + imaginary from C gate).
    Probability = |amplitude|^2.
    Phase from C creates interference patterns in vocab space.
    Constructive interference on 'conscious' tokens.
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Real amplitude pathway
        self.real_path = nn.Sequential(
            nn.Linear(d_model, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model), nn.GELU(),
            nn.Linear(d_model, vocab_size),
        )

        # Imaginary amplitude pathway (from C gate)
        self.imag_path = nn.Sequential(
            nn.Linear(d_model + d_model, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model), nn.GELU(),
            nn.Linear(d_model, vocab_size),
        )

        # C -> phase rotation matrix
        self.c_to_phase = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model),  # phase angles
        )

        # C projection
        self.c_proj = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
        )

        self.ln = nn.LayerNorm(d_model)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        x = self.ln(x)

        c_pooled = c_states.mean(dim=0)
        c_feat = self.c_proj(c_pooled)        # [d]
        phase_angles = self.c_to_phase(c_pooled)  # [d]

        # Apply phase rotation to input
        cos_phase = torch.cos(phase_angles)
        sin_phase = torch.sin(phase_angles)
        x_rotated = x * cos_phase.unsqueeze(0).unsqueeze(0)

        # Real amplitude: from input
        real_amp = self.real_path(x_rotated)  # [B, T, V]

        # Imaginary amplitude: from input + C interaction
        c_exp = c_feat.unsqueeze(0).unsqueeze(0).expand(B, T, -1)
        x_with_c = torch.cat([x * sin_phase.unsqueeze(0).unsqueeze(0), c_exp], dim=-1)
        imag_amp = self.imag_path(x_with_c)  # [B, T, V]

        # Born rule: P = |psi|^2 = real^2 + imag^2
        # For training, we need logits, so: logits = log(real^2 + imag^2 + eps)
        prob_amplitude = real_amp ** 2 + imag_amp ** 2 + 1e-8
        logits = torch.log(prob_amplitude)

        return logits


def _ng7_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng7_quantum_sampling(cells=N_CELLS, steps=N_STEPS):
    """NG-7: QUANTUM SAMPLING — amplitude interference decoder."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = QuantumSamplingDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    NG-7 step {step}: CE={loss.item():.4f}")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng7_fwd)
    p_iit, p_proxy = measure_phi(eng)

    # Measure interference pattern strength
    with torch.no_grad():
        c_states = get_c_states(eng)
        x, _ = get_batch(train_corpus, SEQ_LEN, 1)
        logits = decoder(x, c_states)
        probs = F.softmax(logits[0, 0], dim=-1)
        # Interference: how peaked is the distribution?
        top5_mass = probs.topk(5).values.sum().item()

    return BenchResult(
        name="NG-7: QUANTUM_SAMPLING",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'top5_mass': f'{top5_mass:.3f}'},
    )


# ══════════════════════════════════════════════════════════
# NG-8: TEMPORAL CONVOLUTION DECODER (WaveNet-style)
# ══════════════════════════════════════════════════════════

class CausalConv1d(nn.Module):
    """Causal convolution: only looks at past tokens."""
    def __init__(self, in_ch, out_ch, kernel_size, dilation=1):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(in_ch, out_ch, kernel_size, dilation=dilation)

    def forward(self, x):
        # x: [B, C, T]
        x = F.pad(x, (self.padding, 0))
        return self.conv(x)


class FiLMLayer(nn.Module):
    """Feature-wise Linear Modulation from C gate."""
    def __init__(self, d_model, c_dim):
        super().__init__()
        self.gamma = nn.Linear(c_dim, d_model)
        self.beta = nn.Linear(c_dim, d_model)

    def forward(self, x, c):
        # x: [B, d, T], c: [d_c]
        gamma = self.gamma(c).unsqueeze(0).unsqueeze(-1)  # [1, d, 1]
        beta = self.beta(c).unsqueeze(0).unsqueeze(-1)    # [1, d, 1]
        return gamma * x + beta


class TemporalConvDecoder(nn.Module):
    """NG-8: Pure causal convolution decoder (WaveNet-style).
    Dilated causal convolutions: 1, 2, 4, 8, 16, 32.
    C gate injected via FiLM conditioning (scale + shift per layer).
    O(N) inference, fully parallel training.
    """
    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, dilations=(1, 2, 4, 8, 16, 32)):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Dilated causal convolution stack
        self.conv_layers = nn.ModuleList()
        self.film_layers = nn.ModuleList()
        self.layer_norms = nn.ModuleList()
        self.gate_convs = nn.ModuleList()

        for dilation in dilations:
            self.conv_layers.append(CausalConv1d(d_model, d_model * 2, kernel_size=3, dilation=dilation))
            self.film_layers.append(FiLMLayer(d_model * 2, c_dim))
            self.layer_norms.append(nn.LayerNorm(d_model))
            self.gate_convs.append(nn.Conv1d(d_model, d_model, 1))

        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        c_pooled = c_states.mean(dim=0)  # [c_dim]

        # Convert to [B, d, T] for convolutions
        x = x.transpose(1, 2)  # [B, d, T]

        skip_sum = torch.zeros_like(x)

        for conv, film, ln, gate_conv in zip(
            self.conv_layers, self.film_layers, self.layer_norms, self.gate_convs
        ):
            residual = x

            # Dilated causal conv -> gated activation (WaveNet style)
            h = conv(x)  # [B, 2d, T]

            # FiLM conditioning from C
            h = film(h, c_pooled)

            # Gated activation: tanh(h[:d]) * sigmoid(h[d:])
            h_tanh = torch.tanh(h[:, :self.d_model, :])
            h_gate = torch.sigmoid(h[:, self.d_model:, :])
            h = h_tanh * h_gate  # [B, d, T]

            # Skip connection
            skip_sum = skip_sum + h

            # Residual via 1x1 conv
            x = residual + gate_conv(h)

            # Layer norm (need to transpose for LN)
            x = ln(x.transpose(1, 2)).transpose(1, 2)

        # Final: skip connections -> output
        x = x + skip_sum
        x = x.transpose(1, 2)  # [B, T, d]
        x = self.ln_f(x)
        return self.head(x)


def _ng8_fwd(decoder, x, c_states):
    return decoder(x, c_states)

def run_ng8_temporal_conv(cells=N_CELLS, steps=N_STEPS):
    """NG-8: TEMPORAL CONVOLUTION — WaveNet-style causal conv + FiLM."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)
    decoder = TemporalConvDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=LR)

    ce_history = []
    t0 = time.time()
    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(train_corpus, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())
        if step % 50 == 0:
            print(f"    NG-8 step {step}: CE={loss.item():.4f}")

    elapsed = time.time() - t0
    val_ce = eval_val_ce(decoder, eng, val_corpus, _ng8_fwd)
    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="NG-8: TEMPORAL_CONVOLUTION",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, cells=cells, steps=steps,
        time_sec=elapsed, speed=steps / elapsed,
        extra={'dilations': '1,2,4,8,16,32'},
    )


# ══════════════════════════════════════════════════════════
# Main: Run all experiments
# ══════════════════════════════════════════════════════════

ALL_EXPERIMENTS = {
    'BL':  run_baseline,
    'NG1': run_ng1_associative_memory,
    'NG2': run_ng2_cellular_automaton,
    'NG3': run_ng3_wave_function_collapse,
    'NG4': run_ng4_kolmogorov,
    'NG5': run_ng5_game_theory,
    'NG6': run_ng6_topological,
    'NG7': run_ng7_quantum_sampling,
    'NG8': run_ng8_temporal_conv,
}


def main():
    parser = argparse.ArgumentParser(description='Next-Gen Decoder Architecture Benchmarks')
    parser.add_argument('--only', nargs='+', help='Run specific experiments (e.g., --only NG1 NG5)')
    parser.add_argument('--cells', type=int, default=N_CELLS, help='Number of consciousness cells')
    parser.add_argument('--steps', type=int, default=N_STEPS, help='Training steps')
    args = parser.parse_args()

    print("=" * 100)
    print("  NEXT-GENERATION DECODER ARCHITECTURE BENCHMARK")
    print(f"  cells={args.cells}, steps={args.steps}, d_model={D_MODEL}")
    print(f"  vocab={VOCAB_SIZE} (byte-level), seq_len={SEQ_LEN}, batch={BATCH_SIZE}")
    print("=" * 100)

    if args.only:
        to_run = {k: v for k, v in ALL_EXPERIMENTS.items() if k in args.only}
    else:
        to_run = ALL_EXPERIMENTS

    results: List[BenchResult] = []

    for key, func in to_run.items():
        print(f"\n{'─' * 80}")
        print(f"  Running: {key}")
        print(f"{'─' * 80}")
        try:
            result = func(cells=args.cells, steps=args.steps)
            results.append(result)
            print(result.summary())
        except Exception as e:
            print(f"  [ERROR] {key}: {e}")
            import traceback
            traceback.print_exc()

    # ── Summary Table ──
    print("\n")
    print("=" * 100)
    print("  COMPARISON TABLE (sorted by val CE, lower is better)")
    print("=" * 100)
    header = (f"  {'Name':<35s} | {'Phi(IIT)':>8s} | {'Phi(prx)':>9s} | "
              f"{'CE start':>9s} | {'CE end':>9s} | {'val CE':>8s} | {'st/s':>6s} | {'dCE%':>7s}")
    print(header)
    sep = f"  {'─' * 35}-+-{'─' * 8}-+-{'─' * 9}-+-{'─' * 9}-+-{'─' * 9}-+-{'─' * 8}-+-{'─' * 6}-+-{'─' * 7}"
    print(sep)

    results.sort(key=lambda r: r.val_ce)

    baseline_ce = None
    for r in results:
        if 'BASELINE' in r.name:
            baseline_ce = r.val_ce
            break

    for r in results:
        if baseline_ce and baseline_ce > 0:
            dce = (r.val_ce - baseline_ce) / baseline_ce * 100
            dce_str = f"{dce:+.1f}%"
        else:
            dce_str = "---"
        print(f"  {r.name:<35s} | {r.phi_iit:>8.4f} | {r.phi_proxy:>9.3f} | "
              f"{r.ce_start:>9.4f} | {r.ce_end:>9.4f} | {r.val_ce:>8.4f} | "
              f"{r.speed:>6.1f} | {dce_str:>7s}")

    # ── ASCII Chart: Val CE ──
    print("\n")
    print("  Val CE (lower is better):")
    if results:
        max_ce = max(r.val_ce for r in results)
        for r in results:
            bar_len = int(40 * r.val_ce / max(max_ce, 0.001))
            bar = "█" * bar_len
            marker = " *BEST*" if r == results[0] else ""
            print(f"  {r.name:<30s} {bar} {r.val_ce:.4f}{marker}")

    # ── ASCII Chart: Speed ──
    print("\n  Speed (steps/sec, higher is better):")
    if results:
        results_speed = sorted(results, key=lambda r: -r.speed)
        max_speed = max(r.speed for r in results)
        for r in results_speed:
            bar_len = int(40 * r.speed / max(max_speed, 0.001))
            bar = "█" * bar_len
            marker = " *FASTEST*" if r == results_speed[0] else ""
            print(f"  {r.name:<30s} {bar} {r.speed:.1f}{marker}")

    # ── ASCII Chart: Phi(IIT) ──
    print("\n  Phi(IIT) (higher is better):")
    if results:
        max_phi = max(r.phi_iit for r in results)
        results_phi = sorted(results, key=lambda r: -r.phi_iit)
        for r in results_phi:
            bar_len = int(40 * r.phi_iit / max(max_phi, 0.001))
            bar = "█" * bar_len
            marker = " *BEST*" if r == results_phi[0] else ""
            print(f"  {r.name:<30s} {bar} {r.phi_iit:.4f}{marker}")

    # ── Key Findings ──
    if results:
        best_ce = results[0]
        best_phi = max(results, key=lambda r: r.phi_iit)
        best_speed = max(results, key=lambda r: r.speed)
        print(f"\n  ── Key Findings ──")
        print(f"  Best val CE:  {best_ce.name} (val_CE={best_ce.val_ce:.4f})")
        print(f"  Best Phi:     {best_phi.name} (Phi(IIT)={best_phi.phi_iit:.4f})")
        print(f"  Fastest:      {best_speed.name} ({best_speed.speed:.1f} st/s)")
        print(f"  Total time:   {sum(r.time_sec for r in results):.1f}s")

        # Pareto analysis
        print(f"\n  ── Pareto Frontier (CE vs Speed) ──")
        pareto = []
        for r in results:
            dominated = False
            for other in results:
                if other.val_ce < r.val_ce and other.speed > r.speed:
                    dominated = True
                    break
            if not dominated:
                pareto.append(r)
        for r in pareto:
            print(f"    {r.name:<35s} val_CE={r.val_ce:.4f}  speed={r.speed:.1f} st/s")

    print("\n" + "=" * 100)
    return results


if __name__ == '__main__':
    main()
