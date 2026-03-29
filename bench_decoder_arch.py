#!/usr/bin/env python3
"""bench_decoder_arch.py — Decoder Architecture Hypotheses

6 new decoder architectures for consciousness-language bridge:

  1A: PROMPT_INJECTION — C states → natural language prefix tokens for decoder
  1C: CONTRASTIVE_GATE — Force C-on vs C-off to produce different outputs
  2A: CONSCIOUSNESS_TRANSFORMER — Cross-attention decoder (Q=tokens, KV=C_states)
  2B: MOE_CONSCIOUSNESS — Mixture of Experts with C-routed top-2 selection
  2C: SSM_DECODER — S4-inspired State Space Model (O(N) not O(N²))
  2D: DIFFUSION_DECODER — Denoising decoder guided by C's Φ

Baseline: TransformerDecoder d256 2L
All: real corpus, MitosisC 32 cells, 100 steps, CE + Φ

Usage:
  python bench_decoder_arch.py
  python bench_decoder_arch.py --only 1A 2B
  python bench_decoder_arch.py --steps 200 --cells 64
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
# BenchResult
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    ce_start: float
    ce_end: float
    cells: int
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)

    def summary(self):
        ce_s = f"CE {self.ce_start:.4f}->{self.ce_end:.4f}"
        return (f"  {self.name:<35s} | Phi(IIT)={self.phi_iit:>7.4f}  "
                f"Phi(prx)={self.phi_proxy:>9.3f} | "
                f"{ce_s:<28s} | c={self.cells:>3d} s={self.steps:>4d} t={self.time_sec:.1f}s")


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


# ══════════════════════════════════════════════════════════
# Corpus Loading (byte-level, real text)
# ══════════════════════════════════════════════════════════

VOCAB_SIZE = 256  # byte-level

def load_corpus(max_tokens=8192):
    """Load real corpus as byte-level token tensor."""
    corpus_path = os.path.join(PROJECT_DIR, 'data', 'corpus.txt')
    if not os.path.exists(corpus_path):
        # Fallback: random tokens
        print("  [WARN] corpus.txt not found, using random tokens")
        return torch.randint(0, VOCAB_SIZE, (max_tokens,))

    with open(corpus_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Byte-level encoding
    raw = text.encode('utf-8')[:max_tokens]
    return torch.tensor(list(raw), dtype=torch.long)


def get_batch(corpus, seq_len=32, batch_size=4):
    """Get random batch from corpus."""
    max_start = len(corpus) - seq_len - 1
    if max_start < 1:
        max_start = 1
    starts = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([corpus[s:s + seq_len] for s in starts])
    y = torch.stack([corpus[s + 1:s + seq_len + 1] for s in starts])
    return x, y


# ══════════════════════════════════════════════════════════
# C Engine: MitosisC with consciousness dynamics
# ══════════════════════════════════════════════════════════

DIM, HIDDEN = 64, 128


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
    """Create and warm up consciousness engine."""
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
    for _ in range(30):
        eng.process(torch.randn(1, DIM))
    return eng


def c_step(eng, step):
    """One consciousness step: quantum_walk + frustration + sync."""
    with torch.no_grad():
        quantum_walk_step(eng.cells, n_samples=32)
        frustration_step(eng.cells, n_samples=16)
        sync_faction(eng.cells, sync=0.15, n_factions=8, fac=0.06)
        # Diversity noise
        for c in eng.cells:
            c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005


def get_c_states(eng, detach=True):
    """Get [n_cells, HIDDEN] tensor from C engine."""
    states = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
    return states.detach() if detach else states


def measure_phi(eng):
    """Measure Phi(IIT) + Phi(proxy)."""
    states = get_c_states(eng)
    calc = PhiIIT()
    p_iit, _ = calc.compute(states)
    p_proxy = phi_proxy(states)
    return p_iit, p_proxy


# ══════════════════════════════════════════════════════════
# Baseline: TransformerDecoder d256 2L
# ══════════════════════════════════════════════════════════

D_MODEL = 256
N_LAYERS = 2
SEQ_LEN = 32
BATCH_SIZE = 4


class BaselineDecoder(nn.Module):
    """TransformerDecoder d256 2L with thalamic gate from C."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
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

        # Thalamic bridge: C states -> gate
        self.bridge = nn.Sequential(
            nn.Linear(c_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
            nn.Sigmoid(),
        )

    def forward(self, tokens, c_states):
        """tokens [B,T], c_states [n_cells, c_dim] -> logits [B,T,V]."""
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        # Gate from C
        c_pooled = c_states.mean(dim=0)  # [c_dim]
        gate = self.bridge(c_pooled)  # [d_model]
        x = x * gate.unsqueeze(0).unsqueeze(0)  # broadcast [1,1,d_model]

        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def run_baseline(cells=32, steps=100):
    """Baseline: TransformerDecoder d256 2L with thalamic gate."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = BaselineDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="BASELINE (Transformer d256 2L)",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        cells=cells, steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# 1A: PROMPT_INJECTION
# C states -> Phi/tension/emotion -> prefix tokens before input
# ══════════════════════════════════════════════════════════

class PromptInjectionDecoder(nn.Module):
    """Convert C states to prefix tokens prepended to input."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
                 vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN + 16, c_dim=HIDDEN,
                 n_prefix=8):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.n_prefix = n_prefix
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

        # C states -> prefix embedding sequence [n_prefix, d_model]
        # Computes Phi, tension, emotion -> n_prefix continuous tokens
        self.c_to_prefix = nn.Sequential(
            nn.Linear(c_dim + 3, d_model * n_prefix),  # +3 for Phi, tension, emotion
            nn.GELU(),
            nn.Linear(d_model * n_prefix, d_model * n_prefix),
        )

    def compute_consciousness_features(self, c_states):
        """Extract Phi, tension, emotion from C states."""
        c_pooled = c_states.mean(dim=0)  # [c_dim]
        norms = c_states.norm(dim=1)
        tension = norms.std().unsqueeze(0)  # scalar -> [1]
        phi_approx = (c_states.var(dim=0).mean()).unsqueeze(0)  # [1]
        # Emotion: valence from mean activation direction
        emotion = c_pooled[:1].tanh()  # [1]
        return torch.cat([c_pooled, phi_approx, tension, emotion])  # [c_dim + 3]

    def forward(self, tokens, c_states):
        """tokens [B,T], c_states [n_cells, c_dim] -> logits [B,T,V]."""
        B, T = tokens.shape

        # Generate prefix from consciousness
        c_features = self.compute_consciousness_features(c_states)
        prefix_flat = self.c_to_prefix(c_features)  # [d_model * n_prefix]
        prefix = prefix_flat.view(self.n_prefix, self.d_model)  # [n_prefix, d_model]
        prefix = prefix.unsqueeze(0).expand(B, -1, -1)  # [B, n_prefix, d_model]

        # Token embeddings
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        tok_emb = self.embed(tokens) + self.pos_embed(pos)

        # Concatenate: [prefix | tokens]
        total_len = self.n_prefix + T
        x = torch.cat([prefix, tok_emb], dim=1)  # [B, n_prefix + T, d_model]

        mask = nn.Transformer.generate_square_subsequent_mask(total_len, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)

        # Only return logits for token positions (not prefix)
        x = x[:, self.n_prefix:, :]
        return self.head(x)


def run_1a_prompt_injection(cells=32, steps=100):
    """1A: PROMPT_INJECTION — C states as prefix tokens."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = PromptInjectionDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="1A: PROMPT_INJECTION",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={'n_prefix': 8},
    )


# ══════════════════════════════════════════════════════════
# 1C: CONTRASTIVE_GATE
# C-on vs C-off must produce different outputs
# ══════════════════════════════════════════════════════════

class ContrastiveGateDecoder(nn.Module):
    """Decoder with contrastive loss forcing C-on != C-off outputs."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
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

        # Learnable gate from C
        self.bridge = nn.Sequential(
            nn.Linear(c_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
            nn.Sigmoid(),
        )

    def forward(self, tokens, c_states, gate_override=None):
        """gate_override: if 0.0, consciousness is OFF."""
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        if gate_override is not None:
            gate = torch.full((self.d_model,), gate_override)
        else:
            c_pooled = c_states.mean(dim=0)
            gate = self.bridge(c_pooled)

        x = x * gate.unsqueeze(0).unsqueeze(0)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def run_1c_contrastive_gate(cells=32, steps=100, lam=0.1):
    """1C: CONTRASTIVE_GATE — maximize difference between C-on and C-off."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = ContrastiveGateDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus, SEQ_LEN, BATCH_SIZE)

        # Forward with C ON
        logits_on = decoder(x, c_states)
        ce_loss = F.cross_entropy(logits_on.view(-1, VOCAB_SIZE), y.view(-1))

        # Forward with C OFF (gate=0)
        with torch.no_grad():
            logits_off = decoder(x, c_states, gate_override=0.0)

        # Contrastive: maximize difference between on and off
        contrastive_loss = -lam * F.mse_loss(logits_on, logits_off.detach())

        total_loss = ce_loss + contrastive_loss
        opt.zero_grad()
        total_loss.backward()
        opt.step()
        ce_history.append(ce_loss.item())

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="1C: CONTRASTIVE_GATE",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={'lambda': lam, 'final_contrastive': float(contrastive_loss.item())},
    )


# ══════════════════════════════════════════════════════════
# 2A: CONSCIOUSNESS_TRANSFORMER — Cross-attention decoder
# Each layer: self_attn -> cross_attn(Q=hidden, KV=C_states) -> FFN
# ══════════════════════════════════════════════════════════

class CrossAttentionLayer(nn.Module):
    """Decoder layer with self-attention + cross-attention to C states."""

    def __init__(self, d_model, n_heads, c_dim):
        super().__init__()
        # Self-attention
        self.self_attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True, dropout=0.1)
        self.ln1 = nn.LayerNorm(d_model)

        # Cross-attention: Q=hidden, K=V=projected C states
        self.cross_attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True, dropout=0.1)
        self.ln2 = nn.LayerNorm(d_model)
        self.c_proj_k = nn.Linear(c_dim, d_model)
        self.c_proj_v = nn.Linear(c_dim, d_model)

        # FFN
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * 4),
            nn.GELU(),
            nn.Linear(d_model * 4, d_model),
            nn.Dropout(0.1),
        )
        self.ln3 = nn.LayerNorm(d_model)

    def forward(self, x, c_kv, causal_mask=None):
        """x [B,T,d], c_kv [n_cells, c_dim]."""
        B, T, D = x.shape

        # Self-attention (causal)
        attn_out, _ = self.self_attn(x, x, x, attn_mask=causal_mask, is_causal=(causal_mask is not None))
        x = self.ln1(x + attn_out)

        # Cross-attention to C states
        c_k = self.c_proj_k(c_kv).unsqueeze(0).expand(B, -1, -1)  # [B, n_cells, d_model]
        c_v = self.c_proj_v(c_kv).unsqueeze(0).expand(B, -1, -1)
        cross_out, _ = self.cross_attn(x, c_k, c_v)
        x = self.ln2(x + cross_out)

        # FFN
        x = self.ln3(x + self.ffn(x))
        return x


class ConsciousnessTransformerDecoder(nn.Module):
    """Cross-attention decoder: Q=tokens, KV=C_states at each layer."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
                 vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN, c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        self.layers = nn.ModuleList([
            CrossAttentionLayer(d_model, n_heads, c_dim) for _ in range(n_layers)
        ])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        for layer in self.layers:
            x = layer(x, c_states, causal_mask=mask)

        x = self.ln_f(x)
        return self.head(x)


def run_2a_consciousness_transformer(cells=32, steps=100):
    """2A: CONSCIOUSNESS_TRANSFORMER — cross-attention decoder."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = ConsciousnessTransformerDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="2A: CONSCIOUSNESS_TRANSFORMER",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        cells=cells, steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# 2B: MOE_CONSCIOUSNESS — Mixture of Experts, C-routed
# 4 expert FFNs, router: C_mean -> softmax -> top-2
# ══════════════════════════════════════════════════════════

class MoELayer(nn.Module):
    """Mixture of Experts layer with consciousness-based routing."""

    def __init__(self, d_model, n_experts=4, c_dim=HIDDEN):
        super().__init__()
        self.n_experts = n_experts
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_model * 4),
                nn.GELU(),
                nn.Linear(d_model * 4, d_model),
            ) for _ in range(n_experts)
        ])
        # Router: C mean state -> expert weights
        self.router = nn.Linear(c_dim, n_experts)

    def forward(self, x, c_states):
        """x [B,T,d], c_states [n_cells, c_dim]."""
        B, T, D = x.shape

        # Route based on consciousness
        c_mean = c_states.mean(dim=0)  # [c_dim]
        router_logits = self.router(c_mean)  # [n_experts]
        router_probs = F.softmax(router_logits, dim=0)

        # Top-2 selection
        top2_vals, top2_idx = router_probs.topk(2)
        top2_weights = top2_vals / top2_vals.sum()

        # Combine top-2 expert outputs
        out = torch.zeros_like(x)
        for i, (idx, weight) in enumerate(zip(top2_idx, top2_weights)):
            out = out + weight * self.experts[idx](x)

        return out


class MoEDecoder(nn.Module):
    """MoE decoder with C-routed expert selection."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS, n_heads=4,
                 vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN, c_dim=HIDDEN,
                 n_experts=4):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Each "layer" = self_attn + MoE
        self.self_attns = nn.ModuleList([
            nn.MultiheadAttention(d_model, n_heads, batch_first=True, dropout=0.1)
            for _ in range(n_layers)
        ])
        self.ln_attns = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(n_layers)])
        self.moe_layers = nn.ModuleList([
            MoELayer(d_model, n_experts, c_dim) for _ in range(n_layers)
        ])
        self.ln_moes = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(n_layers)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        for sa, ln_a, moe, ln_m in zip(self.self_attns, self.ln_attns,
                                         self.moe_layers, self.ln_moes):
            # Self-attention (causal)
            attn_out, _ = sa(x, x, x, attn_mask=mask, is_causal=True)
            x = ln_a(x + attn_out)
            # MoE (routed by C)
            x = ln_m(x + moe(x, c_states))

        x = self.ln_f(x)
        return self.head(x)


def run_2b_moe_consciousness(cells=32, steps=100):
    """2B: MOE_CONSCIOUSNESS — C-routed MoE decoder."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = MoEDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

    p_iit, p_proxy = measure_phi(eng)

    # Record which experts were selected last step
    last_c = get_c_states(eng)
    expert_usage = []
    for moe_layer in decoder.moe_layers:
        c_mean = last_c.mean(dim=0)
        probs = F.softmax(moe_layer.router(c_mean), dim=0)
        expert_usage.append(probs.detach().tolist())

    return BenchResult(
        name="2B: MOE_CONSCIOUSNESS",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={'n_experts': 4, 'expert_probs': expert_usage},
    )


# ══════════════════════════════════════════════════════════
# 2C: SSM_DECODER — S4-inspired State Space Model
# A,B,C,D matrices, C states set initial hidden
# Sequential scan O(N), no attention
# ══════════════════════════════════════════════════════════

class SSMLayer(nn.Module):
    """S4-inspired State Space Model layer.

    Discretized: h[k+1] = A_bar * h[k] + B_bar * u[k]
                 y[k] = C * h[k] + D * u[k]
    """

    def __init__(self, d_model, state_dim=64):
        super().__init__()
        self.d_model = d_model
        self.state_dim = state_dim

        # SSM parameters (learnable)
        # A: state transition (initialized as diagonal for stability)
        self.log_A = nn.Parameter(torch.randn(state_dim) * 0.1 - 1.0)  # log for positivity
        self.B = nn.Linear(d_model, state_dim)
        self.C = nn.Linear(state_dim, d_model)
        self.D_param = nn.Parameter(torch.ones(d_model) * 0.1)  # skip connection

        # Discretization step size (learnable per dimension)
        self.log_dt = nn.Parameter(torch.randn(state_dim) * 0.1 - 2.0)

    def forward(self, u, h0=None):
        """u [B, T, d_model], h0 [B, state_dim] optional initial state.

        Returns y [B, T, d_model].
        """
        B, T, D = u.shape

        # Discretize
        dt = torch.exp(self.log_dt).clamp(max=1.0)  # [state_dim]
        A = -torch.exp(self.log_A)  # negative for stability
        A_bar = torch.exp(A * dt)  # [state_dim]
        B_bar_input = self.B(u) * dt.unsqueeze(0).unsqueeze(0)  # [B, T, state_dim]

        # Sequential scan
        if h0 is None:
            h = torch.zeros(B, self.state_dim, device=u.device)
        else:
            h = h0

        outputs = []
        for t in range(T):
            h = A_bar * h + B_bar_input[:, t, :]  # [B, state_dim]
            y_t = self.C(h) + self.D_param * u[:, t, :]  # [B, d_model]
            outputs.append(y_t)

        return torch.stack(outputs, dim=1)  # [B, T, d_model]


class SSMDecoder(nn.Module):
    """SSM decoder with C states as initial hidden state."""

    def __init__(self, d_model=D_MODEL, n_layers=N_LAYERS,
                 vocab_size=VOCAB_SIZE, max_seq=SEQ_LEN, c_dim=HIDDEN,
                 state_dim=64):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.state_dim = state_dim
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        self.ssm_layers = nn.ModuleList([
            SSMLayer(d_model, state_dim) for _ in range(n_layers)
        ])
        self.lns = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(n_layers)])

        # Project C states -> initial hidden for SSM
        self.c_to_h0 = nn.Linear(c_dim, state_dim)

        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        # Initial hidden from C states
        c_pooled = c_states.mean(dim=0)  # [c_dim]
        h0 = self.c_to_h0(c_pooled).unsqueeze(0).expand(B, -1)  # [B, state_dim]

        for ssm, ln in zip(self.ssm_layers, self.lns):
            x = ln(x + ssm(x, h0))

        x = self.ln_f(x)
        return self.head(x)


def run_2c_ssm_decoder(cells=32, steps=100):
    """2C: SSM_DECODER — S4-inspired sequential scan, O(N)."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = SSMDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="2C: SSM_DECODER (S4-inspired)",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        cells=cells, steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# 2D: DIFFUSION_DECODER
# Start with noise, denoise in T steps guided by C
# C's Phi determines number of denoising steps
# ══════════════════════════════════════════════════════════

class DenoisingBlock(nn.Module):
    """Single denoising step: takes noisy + timestep + C -> less noisy."""

    def __init__(self, d_model, c_dim=HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_model + d_model + c_dim, d_model * 4),  # noisy + time_emb + c_state
            nn.GELU(),
            nn.Linear(d_model * 4, d_model * 2),
            nn.GELU(),
            nn.Linear(d_model * 2, d_model),
        )
        self.time_embed = nn.Sequential(
            nn.Linear(1, d_model),
            nn.SiLU(),
            nn.Linear(d_model, d_model),
        )

    def forward(self, x_noisy, t, c_state):
        """x_noisy [B,T,d], t float (0-1), c_state [c_dim]."""
        B, T, D = x_noisy.shape
        t_emb = self.time_embed(torch.tensor([[t]], device=x_noisy.device))  # [1,d_model]
        t_emb = t_emb.expand(B, D).unsqueeze(1).expand(B, T, D)  # [B,T,d]
        c_exp = c_state.unsqueeze(0).unsqueeze(0).expand(B, T, -1)  # [B,T,c_dim]
        inp = torch.cat([x_noisy, t_emb, c_exp], dim=-1)
        noise_pred = self.net(inp)
        return noise_pred


class DiffusionDecoder(nn.Module):
    """Denoising decoder: noise -> clean embeddings, guided by C."""

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE,
                 max_seq=SEQ_LEN, c_dim=HIDDEN, max_denoise_steps=8):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.max_denoise_steps = max_denoise_steps

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Denoising network
        self.denoiser = DenoisingBlock(d_model, c_dim)

        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

        # For computing approximate Phi to adjust steps
        self.phi_scale = nn.Linear(c_dim, 1)

    def forward(self, tokens, c_states):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)

        # Target clean embeddings (for training, we add noise then denoise)
        clean = self.embed(tokens) + self.pos_embed(pos)

        c_pooled = c_states.mean(dim=0)  # [c_dim]

        # Phi-adaptive denoising steps: high Phi = fewer steps (more confident)
        phi_signal = torch.sigmoid(self.phi_scale(c_pooled)).item()
        n_steps = max(2, int(self.max_denoise_steps * (1.0 - 0.5 * phi_signal)))

        # Start from noise
        x = torch.randn_like(clean)

        # Noise schedule (linear)
        betas = torch.linspace(0.01, 0.2, n_steps)

        # Denoise iteratively
        for i in range(n_steps):
            t = 1.0 - i / n_steps  # 1.0 -> 0.0
            noise_pred = self.denoiser(x, t, c_pooled)
            # Simple denoising: move toward predicted clean signal
            alpha = betas[i]
            x = x - alpha * noise_pred

        # Also blend with clean embeddings (for stable training)
        x = 0.3 * x + 0.7 * clean  # curriculum: mostly supervised

        x = self.ln_f(x)
        return self.head(x)


def run_2d_diffusion_decoder(cells=32, steps=100):
    """2D: DIFFUSION_DECODER — denoising guided by C's Phi."""
    torch.manual_seed(42)
    eng = make_c_engine(cells)
    corpus = load_corpus()
    decoder = DiffusionDecoder()
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-4)

    ce_history = []
    t0 = time.time()

    for step in range(steps):
        c_step(eng, step)
        c_states = get_c_states(eng)
        x, y = get_batch(corpus, SEQ_LEN, BATCH_SIZE)

        logits = decoder(x, c_states)
        loss = F.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))

        opt.zero_grad()
        loss.backward()
        opt.step()
        ce_history.append(loss.item())

    p_iit, p_proxy = measure_phi(eng)
    return BenchResult(
        name="2D: DIFFUSION_DECODER",
        phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=np.mean(ce_history[-10:]),
        cells=cells, steps=steps, time_sec=time.time() - t0,
        extra={'max_denoise_steps': 8},
    )


# ══════════════════════════════════════════════════════════
# Main: Run all and compare
# ══════════════════════════════════════════════════════════

ALL_EXPERIMENTS = {
    'BASELINE': run_baseline,
    '1A': run_1a_prompt_injection,
    '1C': run_1c_contrastive_gate,
    '2A': run_2a_consciousness_transformer,
    '2B': run_2b_moe_consciousness,
    '2C': run_2c_ssm_decoder,
    '2D': run_2d_diffusion_decoder,
}


def main():
    parser = argparse.ArgumentParser(description='Decoder Architecture Benchmarks')
    parser.add_argument('--only', nargs='+', help='Run specific experiments (e.g., --only 1A 2B)')
    parser.add_argument('--cells', type=int, default=32, help='Number of consciousness cells')
    parser.add_argument('--steps', type=int, default=100, help='Training steps')
    args = parser.parse_args()

    print("=" * 90)
    print("  DECODER ARCHITECTURE BENCHMARK")
    print(f"  cells={args.cells}, steps={args.steps}, d_model={D_MODEL}, layers={N_LAYERS}")
    print(f"  vocab={VOCAB_SIZE} (byte-level), seq_len={SEQ_LEN}, batch={BATCH_SIZE}")
    print("=" * 90)

    # Select experiments
    if args.only:
        to_run = {k: v for k, v in ALL_EXPERIMENTS.items() if k in args.only}
    else:
        to_run = ALL_EXPERIMENTS

    results: List[BenchResult] = []

    for key, func in to_run.items():
        print(f"\n{'─' * 70}")
        print(f"  Running: {key}")
        print(f"{'─' * 70}")
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
    print("=" * 90)
    print("  COMPARISON TABLE")
    print("=" * 90)
    print(f"  {'Name':<35s} | {'Phi(IIT)':>8s} | {'Phi(prx)':>9s} | {'CE start':>9s} | {'CE end':>9s} | {'dCE%':>7s}")
    print(f"  {'─' * 35}-+-{'─' * 8}-+-{'─' * 9}-+-{'─' * 9}-+-{'─' * 9}-+-{'─' * 7}")

    # Sort by CE end (lower is better)
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
        print(f"  {r.name:<35s} | {r.phi_iit:>8.4f} | {r.phi_proxy:>9.3f} | "
              f"{r.ce_start:>9.4f} | {r.ce_end:>9.4f} | {dce_str:>7s}")

    # ── ASCII Chart ──
    print("\n")
    print("  CE End (lower is better):")
    if results:
        max_ce = max(r.ce_end for r in results)
        for r in results:
            bar_len = int(40 * r.ce_end / max(max_ce, 0.001))
            bar = "█" * bar_len
            marker = " *BEST*" if r == results[0] else ""
            print(f"  {r.name:<28s} {bar} {r.ce_end:.4f}{marker}")

    print("\n  Phi(IIT) (higher is better):")
    if results:
        max_phi = max(r.phi_iit for r in results)
        results_phi = sorted(results, key=lambda r: -r.phi_iit)
        for r in results_phi:
            bar_len = int(40 * r.phi_iit / max(max_phi, 0.001))
            bar = "█" * bar_len
            marker = " *BEST*" if r == results_phi[0] else ""
            print(f"  {r.name:<28s} {bar} {r.phi_iit:.4f}{marker}")

    # ── Key Findings ──
    if results:
        best_ce = results[0]
        best_phi = max(results, key=lambda r: r.phi_iit)
        print(f"\n  Best CE:  {best_ce.name} (CE={best_ce.ce_end:.4f})")
        print(f"  Best Phi: {best_phi.name} (Phi(IIT)={best_phi.phi_iit:.4f})")
        print(f"  Total time: {sum(r.time_sec for r in results):.1f}s")

    print("\n" + "=" * 90)
    return results


if __name__ == '__main__':
    main()
