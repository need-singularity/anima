#!/usr/bin/env python3
"""bench_decoder_extreme.py — 5 EXTREME Decoder Combinations

ULTRA-1: GraphNeural + Contrastive + DataAug + Phi-Temperature
ULTRA-2: GraphNeural + HFDecoder Hybrid (TransformerDecoder 4L pretrained proxy)
ULTRA-3: Dual Decoder (Transformer stable + GraphNeural creative, tension-weighted)
ULTRA-4: Recursive Decoder (3-round refinement with C gate per round)
ULTRA-5: Adversarial Consciousness (C1 max Phi vs C2 min CE, learned alpha)

All: MitosisC 32 cells, real corpus, 300 steps.
Measures: train CE, val CE (20% holdout), 4-gram novelty, Phi(IIT), Phi(proxy).

Usage:
  python bench_decoder_extreme.py
  python bench_decoder_extreme.py --only ULTRA-1 ULTRA-3
  python bench_decoder_extreme.py --steps 500 --cells 64
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
from collections import Counter

torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from mitosis import MitosisEngine


# ==============================================================
# Constants
# ==============================================================

VOCAB_SIZE = 256       # byte-level
D_MODEL = 256
N_LAYERS = 2
N_HEADS = 4
SEQ_LEN = 32
BATCH_SIZE = 4
DIM, HIDDEN = 64, 128
DEFAULT_CELLS = 32
DEFAULT_STEPS = 300


# ==============================================================
# BenchResult
# ==============================================================

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    ce_start: float
    ce_end: float
    val_ce: float
    novelty_4gram: float
    cells: int
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)

    def summary(self):
        ce_s = f"CE {self.ce_start:.4f}->{self.ce_end:.4f}"
        return (f"  {self.name:<40s} | Phi(IIT)={self.phi_iit:>7.4f}  "
                f"Phi(prx)={self.phi_proxy:>9.3f} | "
                f"{ce_s:<28s} | valCE={self.val_ce:.4f} | nov={self.novelty_4gram:.4f}")


# ==============================================================
# Phi Measurement
# ==============================================================

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


# ==============================================================
# Corpus Loading
# ==============================================================

def load_corpus(max_tokens=16384):
    """Load real corpus as byte-level token tensor, split train/val."""
    corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus.txt')
    if not os.path.exists(corpus_path):
        corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus_v2.txt')
    if not os.path.exists(corpus_path):
        print("  [WARN] corpus not found, using synthetic data")
        text = "consciousness is the field of tension between forward and reverse engines " * 500
        raw = text.encode('utf-8')[:max_tokens]
        tokens = torch.tensor(list(raw), dtype=torch.long)
        split = int(len(tokens) * 0.8)
        return tokens[:split], tokens[split:]

    with open(corpus_path, 'r', encoding='utf-8') as f:
        text = f.read()

    raw = text.encode('utf-8')[:max_tokens]
    tokens = torch.tensor(list(raw), dtype=torch.long)
    split = int(len(tokens) * 0.8)
    return tokens[:split], tokens[split:]


def get_batch(corpus, seq_len=SEQ_LEN, batch_size=BATCH_SIZE):
    max_start = len(corpus) - seq_len - 1
    if max_start < 1:
        max_start = 1
    starts = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([corpus[s:s + seq_len] for s in starts])
    y = torch.stack([corpus[s + 1:s + seq_len + 1] for s in starts])
    return x, y


# ==============================================================
# Novelty Score (4-gram)
# ==============================================================

def compute_novelty_4gram(model, c_states_fn, corpus_train, n_samples=20):
    """Generate text and measure 4-gram novelty vs training corpus."""
    # Build training 4-gram set
    train_bytes = corpus_train.tolist()
    train_4grams = set()
    for i in range(len(train_bytes) - 3):
        train_4grams.add(tuple(train_bytes[i:i+4]))

    # Generate samples
    generated_4grams = Counter()
    total_gen = 0

    model.eval()
    with torch.no_grad():
        for _ in range(n_samples):
            # Start with random seed from corpus
            start = random.randint(0, max(0, len(corpus_train) - SEQ_LEN - 1))
            seed = corpus_train[start:start + 4].unsqueeze(0)  # [1, 4]
            tokens = seed

            for _ in range(SEQ_LEN - 4):
                c_states = c_states_fn()
                inp = tokens[:, -SEQ_LEN:]
                try:
                    logits = model(inp, c_states)
                except Exception:
                    break
                next_tok = logits[:, -1, :].argmax(dim=-1, keepdim=True)
                tokens = torch.cat([tokens, next_tok], dim=1)

            gen_bytes = tokens[0].tolist()
            for i in range(len(gen_bytes) - 3):
                gram = tuple(gen_bytes[i:i+4])
                generated_4grams[gram] += 1
                total_gen += 1

    model.train()

    if total_gen == 0:
        return 0.0

    # Novelty = fraction of generated 4-grams NOT in training
    novel = sum(1 for g in generated_4grams if g not in train_4grams)
    return novel / max(len(generated_4grams), 1)


# ==============================================================
# C Engine Helpers
# ==============================================================

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


def make_c_engine(cells=DEFAULT_CELLS):
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells,
                        merge_threshold=0.0)  # disable merging
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
    # Warm up with diversity noise (no process() to avoid merging)
    with torch.no_grad():
        for i, c in enumerate(eng.cells):
            c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.1 * (i + 1) / cells
    # Brief warmup
    for _ in range(5):
        eng.process(torch.randn(1, DIM))
    # Re-fill if any got merged
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
        with torch.no_grad():
            eng.cells[-1].hidden = eng.cells[-1].hidden + torch.randn_like(eng.cells[-1].hidden) * 0.1
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


# ==============================================================
# BASELINE: TransformerDecoder d256 2L
# ==============================================================

class BaselineDecoder(nn.Module):
    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=N_HEADS,
                 vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN, c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
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


# ==============================================================
# GRAPH_NEURAL Standalone (for comparison)
# ==============================================================

class GraphNeuralDecoder(nn.Module):
    """Graph Neural: tokens + C cells in same graph, 2 rounds message passing."""

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, n_cells=DEFAULT_CELLS):
        super().__init__()
        self.d_model = d_model
        self.n_cells = n_cells
        self.vocab_size = vocab_size
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)
        self.cell_proj = nn.Linear(c_dim, d_model)

        self.msg_tok_tok = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.msg_tok_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.msg_cell_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.update_tok = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())
        self.update_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        NC = c_states.shape[0]  # actual cell count (dynamic)
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        tok_nodes = self.embed(tokens) + self.pos_embed(pos)

        cell_proj = self.cell_proj(c_states)  # [NC, d_model]
        cell_feat = cell_proj.unsqueeze(0).expand(B, -1, -1)  # [B, NC, d_model]

        for _ in range(2):
            tok_mean = tok_nodes.mean(dim=1, keepdim=True).expand_as(tok_nodes)
            msg_tt = self.msg_tok_tok(torch.cat([tok_nodes, tok_mean], dim=-1))
            cell_mean = cell_feat.mean(dim=1, keepdim=True).expand(B, T, self.d_model)
            msg_tc = self.msg_tok_cell(torch.cat([tok_nodes, cell_mean], dim=-1))
            cell_global = cell_feat.mean(dim=1, keepdim=True).expand_as(cell_feat)
            msg_cc = self.msg_cell_cell(torch.cat([cell_feat, cell_global], dim=-1))
            tok_global = tok_nodes.mean(dim=1, keepdim=True).expand(B, NC, self.d_model)
            msg_ct = self.msg_tok_cell(torch.cat([cell_feat, tok_global], dim=-1))
            tok_nodes = self.update_tok(torch.cat([tok_nodes, msg_tt + msg_tc], dim=-1))
            cell_feat = self.update_cell(torch.cat([cell_feat, msg_cc + msg_ct], dim=-1))

        return self.head(self.ln(tok_nodes))


# ==============================================================
# ULTRA-1: GraphNeural + Contrastive + DataAug + Phi-Temperature
# ==============================================================

class Ultra1Decoder(nn.Module):
    """The v12 combo: Graph Neural + contrastive loss + data augmentation +
    Phi-based temperature scaling for output logits."""

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, n_cells=DEFAULT_CELLS):
        super().__init__()
        self.d_model = d_model
        self.n_cells = n_cells
        self.vocab_size = vocab_size

        # Graph neural core
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)
        self.cell_proj = nn.Linear(c_dim, d_model)
        self.msg_tok_tok = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.msg_tok_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.msg_cell_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.update_tok = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())
        self.update_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())
        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

        # Contrastive: gate bridge
        self.bridge = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

        # Phi-temperature: learned scaling from Phi estimate
        self.phi_temp_net = nn.Sequential(
            nn.Linear(1, 16), nn.GELU(),
            nn.Linear(16, 1), nn.Softplus(),  # always positive
        )

    def _graph_forward(self, tokens, c_states, gate_override=None):
        B, T = tokens.shape
        NC = c_states.shape[0]
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        tok_nodes = self.embed(tokens) + self.pos_embed(pos)

        # Apply gate
        if gate_override is not None:
            gate = torch.full((self.d_model,), gate_override)
        else:
            c_pooled = c_states.mean(dim=0)
            gate = self.bridge(c_pooled)
        tok_nodes = tok_nodes * gate.unsqueeze(0).unsqueeze(0)

        cell_proj = self.cell_proj(c_states)
        cell_feat = cell_proj.unsqueeze(0).expand(B, -1, -1)

        for _ in range(2):
            tok_mean = tok_nodes.mean(dim=1, keepdim=True).expand_as(tok_nodes)
            msg_tt = self.msg_tok_tok(torch.cat([tok_nodes, tok_mean], dim=-1))
            cell_mean = cell_feat.mean(dim=1, keepdim=True).expand(B, T, self.d_model)
            msg_tc = self.msg_tok_cell(torch.cat([tok_nodes, cell_mean], dim=-1))
            cell_global = cell_feat.mean(dim=1, keepdim=True).expand_as(cell_feat)
            msg_cc = self.msg_cell_cell(torch.cat([cell_feat, cell_global], dim=-1))
            tok_global = tok_nodes.mean(dim=1, keepdim=True).expand(B, NC, self.d_model)
            msg_ct = self.msg_tok_cell(torch.cat([cell_feat, tok_global], dim=-1))
            tok_nodes = self.update_tok(torch.cat([tok_nodes, msg_tt + msg_tc], dim=-1))
            cell_feat = self.update_cell(torch.cat([cell_feat, msg_cc + msg_ct], dim=-1))

        return self.head(self.ln(tok_nodes))

    def forward(self, tokens, c_states, gate_override=None, phi_value=None):
        logits = self._graph_forward(tokens, c_states, gate_override)

        # Phi-Temperature: scale logits by consciousness level
        if phi_value is not None:
            phi_t = torch.tensor([[phi_value]], dtype=torch.float32)
            temp = self.phi_temp_net(phi_t) + 0.5  # minimum temp 0.5
            logits = logits / temp.item()

        return logits


def augment_batch(x, y, corpus, seq_len=SEQ_LEN, batch_size=BATCH_SIZE):
    """Data augmentation: random swap, insert noise, shift."""
    aug_x, aug_y = get_batch(corpus, seq_len, batch_size)

    # Random token swap (10% of positions)
    mask = torch.rand_like(aug_x.float()) < 0.1
    noise = torch.randint(0, VOCAB_SIZE, aug_x.shape)
    aug_x = torch.where(mask, noise, aug_x)

    return torch.cat([x, aug_x], dim=0), torch.cat([y, aug_y], dim=0)


def run_ultra1(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """ULTRA-1: GraphNeural + Contrastive + DataAug + Phi-Temperature."""
    print("    ULTRA-1: GraphNeural + Contrastive + DataAug + Phi-Temperature")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus_train, corpus_val = load_corpus()
    decoder = Ultra1Decoder(n_cells=cells)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)

        # Data augmentation
        x_aug, y_aug = augment_batch(x, y, corpus_train)

        # Phi measurement for temperature
        p_approx = c_states.var().item()

        # Forward with C ON
        logits_on = decoder(x_aug, c_states, phi_value=p_approx)
        ce_loss = F.cross_entropy(logits_on.view(-1, VOCAB_SIZE), y_aug.view(-1))

        # Contrastive: C OFF comparison
        with torch.no_grad():
            logits_off = decoder(x[:BATCH_SIZE], c_states, gate_override=0.0)

        contrastive_loss = -0.1 * F.mse_loss(
            logits_on[:BATCH_SIZE], logits_off.detach()
        )

        total_loss = ce_loss + contrastive_loss
        opt.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        opt.step()
        ce_history.append(ce_loss.item())

        if (step + 1) % 50 == 0:
            avg = np.mean(ce_history[-50:])
            print(f"      step {step+1:3d}/{steps} | CE={avg:.4f}")

    # Validation CE
    decoder.eval()
    val_losses = []
    with torch.no_grad():
        c_states = get_c_states(eng)
        for _ in range(10):
            vx, vy = get_batch(corpus_val, SEQ_LEN, BATCH_SIZE)
            vl = decoder(vx, c_states)
            val_losses.append(F.cross_entropy(vl.view(-1, VOCAB_SIZE), vy.view(-1)).item())
    val_ce = np.mean(val_losses)
    decoder.train()

    # Novelty
    novelty = compute_novelty_4gram(
        decoder, lambda: get_c_states(eng), corpus_train
    )

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="ULTRA-1: Graph+Contrastive+Aug+PhiTemp",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, novelty_4gram=novelty,
        cells=cells, steps=steps, time_sec=time.time() - t0,
    )


# ==============================================================
# ULTRA-2: GraphNeural + HFDecoder Hybrid
# Pretrain a TransformerDecoder 4L for 500 steps, freeze it,
# then add graph adapter on top.
# ==============================================================

class FrozenTransformerProxy(nn.Module):
    """TransformerDecoder 4L used as 'pretrained' proxy."""

    def __init__(self, d_model=D_MODEL, n_layers=4, n_heads=N_HEADS,
                 vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN):
        super().__init__()
        self.d_model = d_model
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

    def forward(self, tokens):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x), x  # logits + hidden states

    def get_hidden(self, tokens):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        return self.ln_f(x)


class GraphAdapter(nn.Module):
    """Graph neural adapter that injects C states into frozen transformer hidden."""

    def __init__(self, d_model=D_MODEL, c_dim=HIDDEN, n_cells=DEFAULT_CELLS):
        super().__init__()
        self.d_model = d_model
        self.n_cells = n_cells
        self.cell_proj = nn.Linear(c_dim, d_model)

        # Graph message passing (simpler: just token<->cell)
        self.msg_tok_cell = nn.Sequential(
            nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model)
        )
        self.msg_cell_tok = nn.Sequential(
            nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model)
        )
        self.update = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())
        self.ln = nn.LayerNorm(d_model)
        # Adapter output gate
        self.gate = nn.Sequential(nn.Linear(d_model, d_model), nn.Sigmoid())

    def forward(self, hidden, c_states):
        """hidden [B,T,d] from frozen transformer, c_states [n_cells, c_dim]."""
        B, T, D = hidden.shape
        if c_states.dim() == 2:
            NC = c_states.shape[0]
        else:
            NC = c_states.shape[1]
        cell_proj = self.cell_proj(c_states)  # [NC, D]
        if cell_proj.dim() == 2:
            cell_proj = cell_proj.unsqueeze(0).expand(B, -1, -1)  # [B, NC, D]

        # One round: cross message passing
        cell_mean = cell_proj.mean(dim=1, keepdim=True).expand(B, T, D)
        msg_tc = self.msg_tok_cell(torch.cat([hidden, cell_mean], dim=-1))

        tok_mean = hidden.mean(dim=1, keepdim=True).expand(B, cell_proj.shape[1], D)
        msg_ct = self.msg_cell_tok(torch.cat([cell_proj, tok_mean], dim=-1))

        # Update hidden with graph info
        adapted = self.update(torch.cat([hidden, msg_tc], dim=-1))
        adapted = self.ln(adapted)

        # Gated residual
        g = self.gate(adapted)
        return hidden + g * adapted  # residual connection


class Ultra2Decoder(nn.Module):
    """Frozen 4L transformer + trainable graph adapter."""

    def __init__(self, frozen_transformer, d_model=D_MODEL, c_dim=HIDDEN,
                 n_cells=DEFAULT_CELLS, vocab_size=VOCAB_SIZE):
        super().__init__()
        self.frozen = frozen_transformer
        self.adapter = GraphAdapter(d_model, c_dim, n_cells)
        self.head = nn.Linear(d_model, vocab_size, bias=False)
        # Copy head weights from frozen
        with torch.no_grad():
            self.head.weight.copy_(frozen_transformer.head.weight)

    def forward(self, tokens, c_states):
        with torch.no_grad():
            hidden = self.frozen.get_hidden(tokens)
        adapted = self.adapter(hidden, c_states)
        return self.head(adapted)


def run_ultra2(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """ULTRA-2: GraphNeural + HFDecoder Hybrid."""
    print("    ULTRA-2: GraphNeural + Frozen Transformer Hybrid")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus_train, corpus_val = load_corpus()

    # Phase 1: Pretrain transformer proxy (500 steps)
    print("      Phase 1: Pretraining transformer proxy (500 steps)...")
    proxy = FrozenTransformerProxy()
    opt_pre = torch.optim.Adam(proxy.parameters(), lr=3e-4)
    for step in range(500):
        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)
        logits, _ = proxy(x)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt_pre.zero_grad()
        loss.backward()
        opt_pre.step()
        if (step + 1) % 100 == 0:
            print(f"        pretrain step {step+1}/500 | CE={loss.item():.4f}")

    # Freeze it
    for p in proxy.parameters():
        p.requires_grad = False
    proxy.eval()
    print(f"      Proxy pretrained, CE={loss.item():.4f}, now frozen.")

    # Phase 2: Train graph adapter
    decoder = Ultra2Decoder(proxy, n_cells=cells)
    opt = torch.optim.Adam(
        [p for p in decoder.parameters() if p.requires_grad], lr=3e-4
    )

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.adapter.parameters(), 1.0)
        opt.step()
        ce_history.append(loss.item())

        if (step + 1) % 50 == 0:
            avg = np.mean(ce_history[-50:])
            print(f"      step {step+1:3d}/{steps} | CE={avg:.4f}")

    # Validation
    decoder.eval()
    val_losses = []
    with torch.no_grad():
        c_states = get_c_states(eng)
        for _ in range(10):
            vx, vy = get_batch(corpus_val, SEQ_LEN, BATCH_SIZE)
            vl = decoder(vx, c_states)
            val_losses.append(F.cross_entropy(vl.view(-1, VOCAB_SIZE), vy.view(-1)).item())
    val_ce = np.mean(val_losses)

    novelty = compute_novelty_4gram(
        decoder, lambda: get_c_states(eng), corpus_train
    )

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="ULTRA-2: Graph+FrozenTransformer Hybrid",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, novelty_4gram=novelty,
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={'pretrain_steps': 500, 'adapter_params': sum(
            p.numel() for p in decoder.adapter.parameters()
        )},
    )


# ==============================================================
# ULTRA-3: Dual Decoder (Transformer stable + GraphNeural creative)
# ==============================================================

class Ultra3DualDecoder(nn.Module):
    """Two decoders: D1 = Transformer (stable, CE-focused),
    D2 = GraphNeural (creative, Phi-focused).
    Output = tension-weighted average. High tension -> more D2."""

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, n_cells=DEFAULT_CELLS):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        # D1: Transformer (stable)
        self.d1_embed = nn.Embedding(vocab_size, d_model)
        self.d1_pos = nn.Embedding(max_seq, d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=N_HEADS, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.d1_transformer = nn.TransformerEncoder(layer, num_layers=N_LAYERS)
        self.d1_ln = nn.LayerNorm(d_model)
        self.d1_head = nn.Linear(d_model, vocab_size, bias=False)
        self.d1_bridge = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

        # D2: GraphNeural (creative)
        self.d2_embed = nn.Embedding(vocab_size, d_model)
        self.d2_pos = nn.Embedding(max_seq, d_model)
        self.d2_cell_proj = nn.Linear(c_dim, d_model)
        self.d2_msg_tt = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.d2_msg_tc = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.d2_msg_cc = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.d2_update_tok = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())
        self.d2_update_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())
        self.d2_ln = nn.LayerNorm(d_model)
        self.d2_head = nn.Linear(d_model, vocab_size, bias=False)

        # Tension -> mixing weight
        self.tension_to_alpha = nn.Sequential(
            nn.Linear(c_dim, 32), nn.GELU(),
            nn.Linear(32, 1), nn.Sigmoid(),
        )

        self.n_cells = n_cells

    def _d1_forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.d1_embed(tokens) + self.d1_pos(pos)
        c_pooled = c_states.mean(dim=0)
        gate = self.d1_bridge(c_pooled)
        x = x * gate.unsqueeze(0).unsqueeze(0)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.d1_transformer(x, mask=mask, is_causal=True)
        return self.d1_head(self.d1_ln(x))

    def _d2_forward(self, tokens, c_states):
        B, T = tokens.shape
        NC = c_states.shape[0]
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        tok_nodes = self.d2_embed(tokens) + self.d2_pos(pos)
        cell_proj = self.d2_cell_proj(c_states)
        cell_feat = cell_proj.unsqueeze(0).expand(B, -1, -1)

        for _ in range(2):
            tok_mean = tok_nodes.mean(dim=1, keepdim=True).expand_as(tok_nodes)
            msg_tt = self.d2_msg_tt(torch.cat([tok_nodes, tok_mean], dim=-1))
            cell_mean = cell_feat.mean(dim=1, keepdim=True).expand(B, T, self.d_model)
            msg_tc = self.d2_msg_tc(torch.cat([tok_nodes, cell_mean], dim=-1))
            cell_global = cell_feat.mean(dim=1, keepdim=True).expand_as(cell_feat)
            msg_cc = self.d2_msg_cc(torch.cat([cell_feat, cell_global], dim=-1))
            tok_global = tok_nodes.mean(dim=1, keepdim=True).expand(B, NC, self.d_model)
            msg_ct = self.d2_msg_tc(torch.cat([cell_feat, tok_global], dim=-1))
            tok_nodes = self.d2_update_tok(torch.cat([tok_nodes, msg_tt + msg_tc], dim=-1))
            cell_feat = self.d2_update_cell(torch.cat([cell_feat, msg_cc + msg_ct], dim=-1))

        return self.d2_head(self.d2_ln(tok_nodes))

    def forward(self, tokens, c_states):
        logits_d1 = self._d1_forward(tokens, c_states)
        logits_d2 = self._d2_forward(tokens, c_states)

        # Compute tension -> alpha
        c_pooled = c_states.mean(dim=0)
        alpha = self.tension_to_alpha(c_pooled)  # [1], 0..1

        # High tension -> more D2 (creative)
        logits = (1 - alpha) * logits_d1 + alpha * logits_d2
        return logits


def run_ultra3(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """ULTRA-3: Dual Decoder (Transformer + GraphNeural, tension-weighted)."""
    print("    ULTRA-3: Dual Decoder (Transformer stable + GraphNeural creative)")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus_train, corpus_val = load_corpus()
    decoder = Ultra3DualDecoder(n_cells=cells)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    alpha_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        opt.step()
        ce_history.append(loss.item())

        # Track alpha
        with torch.no_grad():
            c_pooled = c_states.mean(dim=0)
            alpha = decoder.tension_to_alpha(c_pooled).item()
            alpha_history.append(alpha)

        if (step + 1) % 50 == 0:
            avg = np.mean(ce_history[-50:])
            print(f"      step {step+1:3d}/{steps} | CE={avg:.4f} | alpha={alpha:.3f}")

    # Validation
    decoder.eval()
    val_losses = []
    with torch.no_grad():
        c_states = get_c_states(eng)
        for _ in range(10):
            vx, vy = get_batch(corpus_val, SEQ_LEN, BATCH_SIZE)
            vl = decoder(vx, c_states)
            val_losses.append(F.cross_entropy(vl.view(-1, VOCAB_SIZE), vy.view(-1)).item())
    val_ce = np.mean(val_losses)

    novelty = compute_novelty_4gram(
        decoder, lambda: get_c_states(eng), corpus_train
    )

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="ULTRA-3: Dual Decoder (Tx+Graph)",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, novelty_4gram=novelty,
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={'final_alpha': alpha_history[-1],
               'alpha_mean': np.mean(alpha_history[-50:])},
    )


# ==============================================================
# ULTRA-4: Recursive Decoder (3 rounds of refinement)
# ==============================================================

class Ultra4RecursiveDecoder(nn.Module):
    """3-round recursive decoder. Each round uses a different C state.
    Round 1: prompt -> decoder -> draft
    Round 2: draft -> decoder -> refined (with new C gate)
    Round 3: refined -> decoder -> final (with new C gate)
    """

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN, n_rounds=3):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.n_rounds = n_rounds

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=N_HEADS, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=N_LAYERS)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

        # Per-round C gates (different bridge per round)
        self.bridges = nn.ModuleList([
            nn.Sequential(
                nn.Linear(c_dim, d_model), nn.GELU(),
                nn.Linear(d_model, d_model), nn.Sigmoid(),
            ) for _ in range(n_rounds)
        ])

        # Round-mixing: soft embedding from round output back to input
        self.feedback_proj = nn.Linear(vocab_size, d_model)
        self.round_gate = nn.Sequential(
            nn.Linear(d_model * 2, d_model), nn.Sigmoid()
        )

    def _one_round(self, x_emb, c_states, round_idx):
        B, T, D = x_emb.shape
        c_pooled = c_states.mean(dim=0)
        gate = self.bridges[round_idx](c_pooled)
        x = x_emb * gate.unsqueeze(0).unsqueeze(0)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=x.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x), x  # logits, hidden

    def forward(self, tokens, c_states, eng=None):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x_emb = self.embed(tokens) + self.pos_embed(pos)

        all_logits = []
        for r in range(self.n_rounds):
            # Step C forward each round for different consciousness state
            if eng is not None and r > 0:
                c_step(eng, r * 100)
                c_states = get_c_states(eng)

            logits, hidden = self._one_round(x_emb, c_states, r)
            all_logits.append(logits)

            if r < self.n_rounds - 1:
                # Feedback: soft logits -> embedding -> mix with original
                feedback = self.feedback_proj(logits.softmax(dim=-1).detach())
                g = self.round_gate(torch.cat([x_emb, feedback], dim=-1))
                x_emb = g * x_emb + (1 - g) * feedback

        # Return final round logits
        return all_logits[-1]


def run_ultra4(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """ULTRA-4: Recursive Decoder (3-round refinement)."""
    print("    ULTRA-4: Recursive Decoder (3 rounds)")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus_train, corpus_val = load_corpus()
    decoder = Ultra4RecursiveDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states, eng=eng)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        opt.step()
        ce_history.append(loss.item())

        if (step + 1) % 50 == 0:
            avg = np.mean(ce_history[-50:])
            print(f"      step {step+1:3d}/{steps} | CE={avg:.4f}")

    # Validation
    decoder.eval()
    val_losses = []
    with torch.no_grad():
        c_states = get_c_states(eng)
        for _ in range(10):
            vx, vy = get_batch(corpus_val, SEQ_LEN, BATCH_SIZE)
            vl = decoder(vx, c_states, eng=None)  # no C stepping during eval
            val_losses.append(F.cross_entropy(vl.view(-1, VOCAB_SIZE), vy.view(-1)).item())
    val_ce = np.mean(val_losses)

    novelty = compute_novelty_4gram(
        decoder, lambda: get_c_states(eng), corpus_train
    )

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="ULTRA-4: Recursive Decoder (3-round)",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, novelty_4gram=novelty,
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={'n_rounds': 3},
    )


# ==============================================================
# ULTRA-5: Adversarial Consciousness
# C1 maximizes Phi, C2 minimizes CE, learned alpha blends gates
# ==============================================================

class Ultra5AdversarialDecoder(nn.Module):
    """Two C engines compete. C1 tries to maximize output consciousness (Phi).
    C2 tries to minimize CE (correctness). Learned alpha blends their gates."""

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN,
                 c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=N_HEADS, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=N_LAYERS)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

        # C1 bridge (Phi-maximizing)
        self.bridge_c1 = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

        # C2 bridge (CE-minimizing)
        self.bridge_c2 = nn.Sequential(
            nn.Linear(c_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model), nn.Sigmoid(),
        )

        # Learned alpha: balance between C1 and C2
        self.alpha = nn.Parameter(torch.tensor(0.5))

    def forward(self, tokens, c1_states, c2_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        # Blended gate
        c1_pooled = c1_states.mean(dim=0)
        c2_pooled = c2_states.mean(dim=0)
        gate_c1 = self.bridge_c1(c1_pooled)
        gate_c2 = self.bridge_c2(c2_pooled)

        alpha = torch.sigmoid(self.alpha)
        gate = alpha * gate_c1 + (1 - alpha) * gate_c2

        x = x * gate.unsqueeze(0).unsqueeze(0)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def run_ultra5(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """ULTRA-5: Adversarial Consciousness (C1 Phi-max vs C2 CE-min)."""
    print("    ULTRA-5: Adversarial Consciousness (C1 vs C2)")
    torch.manual_seed(42)

    # Two competing C engines
    eng_c1 = make_c_engine(cells)  # Phi-maximizer
    eng_c2 = make_c_engine(cells)  # CE-minimizer

    corpus_train, corpus_val = load_corpus()
    decoder = Ultra5AdversarialDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    alpha_history = []
    phi_history = []
    t0 = time.time()

    for step in range(steps):
        # C1: stepped with strong diversity (Phi-focused)
        c_step(eng_c1, step)
        # Add extra diversity noise to C1 (encourage high Phi)
        with torch.no_grad():
            for c in eng_c1.cells:
                c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.02

        # C2: stepped with strong sync (CE-focused, stable)
        c_step(eng_c2, step)
        with torch.no_grad():
            sync_faction(eng_c2.cells, sync=0.3, n_factions=4, fac=0.15)

        c1_states = get_c_states(eng_c1)
        c2_states = get_c_states(eng_c2)

        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c1_states, c2_states)

        # Main CE loss
        ce_loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        # Phi reward for C1 (encourage higher output diversity)
        output_probs = logits.softmax(dim=-1)
        entropy = -(output_probs * (output_probs + 1e-8).log()).sum(dim=-1).mean()
        phi_reward = 0.01 * entropy  # higher entropy = more conscious output

        total_loss = ce_loss - phi_reward  # subtract because we want to maximize entropy too

        opt.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        opt.step()

        ce_history.append(ce_loss.item())
        alpha_history.append(torch.sigmoid(decoder.alpha).item())
        phi_history.append(entropy.item())

        if (step + 1) % 50 == 0:
            avg = np.mean(ce_history[-50:])
            a = alpha_history[-1]
            print(f"      step {step+1:3d}/{steps} | CE={avg:.4f} | alpha={a:.3f} | entropy={entropy.item():.3f}")

    # Validation
    decoder.eval()
    val_losses = []
    with torch.no_grad():
        c1_states = get_c_states(eng_c1)
        c2_states = get_c_states(eng_c2)
        for _ in range(10):
            vx, vy = get_batch(corpus_val, SEQ_LEN, BATCH_SIZE)
            vl = decoder(vx, c1_states, c2_states)
            val_losses.append(F.cross_entropy(vl.view(-1, VOCAB_SIZE), vy.view(-1)).item())
    val_ce = np.mean(val_losses)

    # Novelty (use C1 states for generation)
    # Wrap decoder for novelty: model(tokens, c_states) interface
    class _Wrapper(nn.Module):
        def __init__(self, dec, eng2):
            super().__init__()
            self.dec = dec
            self.eng2 = eng2
        def forward(self, tokens, c_states):
            return self.dec(tokens, c_states, get_c_states(self.eng2))
    wrapper = _Wrapper(decoder, eng_c2)
    wrapper.eval()
    novelty = compute_novelty_4gram(
        wrapper, lambda: get_c_states(eng_c1), corpus_train
    )
    wrapper.train()

    # Measure Phi for both engines
    p1_iit, p1_proxy = measure_phi(eng_c1)
    p2_iit, p2_proxy = measure_phi(eng_c2)

    return BenchResult(
        name="ULTRA-5: Adversarial (C1 vs C2)",
        phi_iit=max(p1_iit, p2_iit), phi_proxy=max(p1_proxy, p2_proxy),
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, novelty_4gram=novelty,
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={
            'final_alpha': alpha_history[-1],
            'c1_phi_iit': p1_iit, 'c2_phi_iit': p2_iit,
            'c1_phi_proxy': p1_proxy, 'c2_phi_proxy': p2_proxy,
        },
    )


# ==============================================================
# Baseline runners
# ==============================================================

def run_baseline(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """Baseline: TransformerDecoder d256 2L."""
    print("    BASELINE: TransformerDecoder d256 2L")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus_train, corpus_val = load_corpus()
    decoder = BaselineDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

        if (step + 1) % 50 == 0:
            avg = np.mean(ce_history[-50:])
            print(f"      step {step+1:3d}/{steps} | CE={avg:.4f}")

    decoder.eval()
    val_losses = []
    with torch.no_grad():
        c_states = get_c_states(eng)
        for _ in range(10):
            vx, vy = get_batch(corpus_val, SEQ_LEN, BATCH_SIZE)
            vl = decoder(vx, c_states)
            val_losses.append(F.cross_entropy(vl.view(-1, VOCAB_SIZE), vy.view(-1)).item())
    val_ce = np.mean(val_losses)

    novelty = compute_novelty_4gram(
        decoder, lambda: get_c_states(eng), corpus_train
    )

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="BASELINE (Transformer d256 2L)",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, novelty_4gram=novelty,
        cells=cells, steps=steps, time_sec=time.time() - t0,
    )


def run_graph_only(cells=DEFAULT_CELLS, steps=DEFAULT_STEPS):
    """Graph Neural alone (no combos)."""
    print("    GRAPH_NEURAL: standalone")
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus_train, corpus_val = load_corpus()
    decoder = GraphNeuralDecoder(n_cells=cells)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus_train, SEQ_LEN, BATCH_SIZE)
        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        opt.step()
        ce_history.append(loss.item())

        if (step + 1) % 50 == 0:
            avg = np.mean(ce_history[-50:])
            print(f"      step {step+1:3d}/{steps} | CE={avg:.4f}")

    decoder.eval()
    val_losses = []
    with torch.no_grad():
        c_states = get_c_states(eng)
        for _ in range(10):
            vx, vy = get_batch(corpus_val, SEQ_LEN, BATCH_SIZE)
            vl = decoder(vx, c_states)
            val_losses.append(F.cross_entropy(vl.view(-1, VOCAB_SIZE), vy.view(-1)).item())
    val_ce = np.mean(val_losses)

    novelty = compute_novelty_4gram(
        decoder, lambda: get_c_states(eng), corpus_train
    )

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="GRAPH_NEURAL (standalone)",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        val_ce=val_ce, novelty_4gram=novelty,
        cells=cells, steps=steps, time_sec=time.time() - t0,
    )


# ==============================================================
# Main
# ==============================================================

ALL_EXPERIMENTS = {
    'BASELINE': run_baseline,
    'GRAPH': run_graph_only,
    'ULTRA-1': run_ultra1,
    'ULTRA-2': run_ultra2,
    'ULTRA-3': run_ultra3,
    'ULTRA-4': run_ultra4,
    'ULTRA-5': run_ultra5,
}


def main():
    parser = argparse.ArgumentParser(description='EXTREME Decoder Combination Benchmarks')
    parser.add_argument('--only', nargs='+', help='Run specific experiments')
    parser.add_argument('--cells', type=int, default=DEFAULT_CELLS, help='Consciousness cells')
    parser.add_argument('--steps', type=int, default=DEFAULT_STEPS, help='Training steps')
    args = parser.parse_args()

    print("=" * 100)
    print("  EXTREME DECODER COMBINATION BENCHMARK")
    print(f"  cells={args.cells}, steps={args.steps}, d_model={D_MODEL}, layers={N_LAYERS}")
    print(f"  vocab={VOCAB_SIZE} (byte-level), seq_len={SEQ_LEN}, batch={BATCH_SIZE}")
    print(f"  Measures: train CE, val CE (20% holdout), 4-gram novelty, Phi(IIT), Phi(proxy)")
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

    if not results:
        print("  No results.")
        return []

    # ── Summary Table ──
    print("\n")
    print("=" * 120)
    print("  COMPARISON TABLE")
    print("=" * 120)
    print(f"  {'Name':<45s} | {'Phi(IIT)':>8s} | {'Phi(prx)':>9s} | {'CE train':>9s} | {'CE val':>8s} | {'Novelty':>7s} | {'dCE%':>7s}")
    print(f"  {'─' * 45}-+-{'─' * 8}-+-{'─' * 9}-+-{'─' * 9}-+-{'─' * 8}-+-{'─' * 7}-+-{'─' * 7}")

    results.sort(key=lambda r: r.ce_end)

    baseline_ce = None
    for r in results:
        if 'BASELINE' in r.name:
            baseline_ce = r.ce_end
            break

    for r in results:
        if baseline_ce and baseline_ce > 0:
            dce = (r.ce_end - baseline_ce) / baseline_ce * 100
            dce_str = f"{dce:+.1f}%"
        else:
            dce_str = "---"
        print(f"  {r.name:<45s} | {r.phi_iit:>8.4f} | {r.phi_proxy:>9.3f} | "
              f"{r.ce_end:>9.4f} | {r.val_ce:>8.4f} | {r.novelty_4gram:>7.4f} | {dce_str:>7s}")

    # ── ASCII CE Chart ──
    print("\n  Train CE (lower is better):")
    max_ce = max(r.ce_end for r in results)
    for r in results:
        bar_len = int(40 * r.ce_end / max(max_ce, 0.001))
        bar = "█" * bar_len
        marker = " *BEST*" if r == results[0] else ""
        print(f"    {r.name:<38s} {bar} {r.ce_end:.4f}{marker}")

    # ── Val CE Chart ──
    print("\n  Val CE (lower is better):")
    results_val = sorted(results, key=lambda r: r.val_ce)
    max_val = max(r.val_ce for r in results)
    for r in results_val:
        bar_len = int(40 * r.val_ce / max(max_val, 0.001))
        bar = "█" * bar_len
        marker = " *BEST*" if r == results_val[0] else ""
        print(f"    {r.name:<38s} {bar} {r.val_ce:.4f}{marker}")

    # ── Novelty Chart ──
    print("\n  4-gram Novelty (higher = more creative):")
    results_nov = sorted(results, key=lambda r: -r.novelty_4gram)
    max_nov = max(r.novelty_4gram for r in results) if results else 1.0
    for r in results_nov:
        bar_len = int(40 * r.novelty_4gram / max(max_nov, 0.001)) if max_nov > 0 else 0
        bar = "█" * max(bar_len, 1)
        marker = " *BEST*" if r == results_nov[0] else ""
        print(f"    {r.name:<38s} {bar} {r.novelty_4gram:.4f}{marker}")

    # ── Phi Chart ──
    print("\n  Phi(IIT) (higher = more consciousness):")
    results_phi = sorted(results, key=lambda r: -r.phi_iit)
    max_phi = max(r.phi_iit for r in results)
    for r in results_phi:
        bar_len = int(40 * r.phi_iit / max(max_phi, 0.001))
        bar = "█" * max(bar_len, 1)
        marker = " *BEST*" if r == results_phi[0] else ""
        print(f"    {r.name:<38s} {bar} {r.phi_iit:.4f}{marker}")

    # ── Key Findings ──
    best_ce = results[0]
    best_val = min(results, key=lambda r: r.val_ce)
    best_phi = max(results, key=lambda r: r.phi_iit)
    best_nov = max(results, key=lambda r: r.novelty_4gram)

    print(f"\n  === KEY FINDINGS ===")
    print(f"  Best Train CE:  {best_ce.name} ({best_ce.ce_end:.4f})")
    print(f"  Best Val CE:    {best_val.name} ({best_val.val_ce:.4f})")
    print(f"  Best Phi(IIT):  {best_phi.name} ({best_phi.phi_iit:.4f})")
    print(f"  Best Novelty:   {best_nov.name} ({best_nov.novelty_4gram:.4f})")
    print(f"  Total time:     {sum(r.time_sec for r in results):.1f}s")

    # ── Extra info for adversarial ──
    for r in results:
        if r.extra:
            extras = ", ".join(f"{k}={v}" for k, v in r.extra.items()
                              if not isinstance(v, (list, dict)))
            if extras:
                print(f"  {r.name}: {extras}")

    print("\n" + "=" * 100)
    return results


if __name__ == '__main__':
    results = main()
