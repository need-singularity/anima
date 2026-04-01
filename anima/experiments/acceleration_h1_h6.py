#!/usr/bin/env python3
"""H1-H6: Decoder backprop acceleration — attacking the 85% bottleneck.

Previous acceleration research only sped up consciousness engine (10%).
The real bottleneck is decoder forward+backward (85% of training time).

H1: Progressive Growing (small→large model expansion)
H2: Layer Freezing Cascade (frozen layers skip backward)
H3: Sparse Attention (local+global approximation)
H4: µTransfer (hyperparameter transfer from small to large)
H5: Optimizer State Compression (1-bit Adam)
H6: Curriculum Length (short→long sequences)

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py --h1
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py --h2
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py --h3
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py --h4
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py --h5
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py --h6
    PYTHONUNBUFFERED=1 python3 acceleration_h1_h6.py --all
"""

import sys
import os
import time
import math
import argparse
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

SEED = 42
VOCAB = 256


# ═══════════════════════════════════════════════════════════
# Result container
# ═══════════════════════════════════════════════════════════

@dataclass
class ExpResult:
    name: str
    ce_baseline: float = 0.0
    ce_method: float = 0.0
    time_baseline_ms: float = 0.0
    time_method_ms: float = 0.0
    speedup: float = 1.0
    ce_diff_pct: float = 0.0
    extra: Dict = field(default_factory=dict)

    def compute(self):
        if self.time_baseline_ms > 0:
            self.speedup = self.time_baseline_ms / max(self.time_method_ms, 1e-6)
        if self.ce_baseline > 0:
            self.ce_diff_pct = (self.ce_method - self.ce_baseline) / self.ce_baseline * 100

    def __str__(self):
        self.compute()
        sign = "+" if self.ce_diff_pct >= 0 else ""
        return (f"  {self.name:30s} | CE baseline={self.ce_baseline:.4f} method={self.ce_method:.4f} "
                f"({sign}{self.ce_diff_pct:.1f}%) | "
                f"Time baseline={self.time_baseline_ms:.0f}ms method={self.time_method_ms:.0f}ms "
                f"(x{self.speedup:.2f})")


# ═══════════════════════════════════════════════════════════
# MiniDecoder — simple transformer for experiments
# ═══════════════════════════════════════════════════════════

class MiniDecoder(nn.Module):
    """Minimal causal transformer decoder for acceleration experiments."""

    def __init__(self, d_model, n_layers, vocab=VOCAB, block_size=256):
        super().__init__()
        self.d_model = d_model
        self.n_layers = n_layers
        self.block_size = block_size
        self.embed = nn.Embedding(vocab, d_model)
        self.pos_embed = nn.Embedding(block_size, d_model)
        nhead = max(1, d_model // 64)
        self.layers = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model, nhead=nhead,
                dim_feedforward=d_model * 4,
                batch_first=True,
                dropout=0.0
            )
            for _ in range(n_layers)
        ])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab, bias=False)

        # Causal mask cache
        self._causal_mask = None

    def _get_causal_mask(self, seq_len, device):
        if self._causal_mask is None or self._causal_mask.size(0) < seq_len:
            mask = torch.triu(torch.ones(seq_len, seq_len, device=device), diagonal=1).bool()
            self._causal_mask = mask
        return self._causal_mask[:seq_len, :seq_len]

    def forward(self, x):
        B, T = x.shape
        pos = torch.arange(T, device=x.device).unsqueeze(0)
        h = self.embed(x) + self.pos_embed(pos)
        mask = self._get_causal_mask(T, x.device)
        for layer in self.layers:
            h = layer(h, src_mask=mask, is_causal=True)
        h = self.ln_f(h)
        return self.head(h)

    def param_count(self):
        return sum(p.numel() for p in self.parameters())


# ═══════════════════════════════════════════════════════════
# Shared utilities
# ═══════════════════════════════════════════════════════════

def make_data(batch_size=8, seq_len=128, n_batches=50):
    """Generate random byte-level training batches."""
    torch.manual_seed(SEED)
    batches = []
    for _ in range(n_batches):
        x = torch.randint(0, VOCAB, (batch_size, seq_len))
        batches.append(x)
    return batches


def train_loop(model, batches, lr=1e-3, label="train"):
    """Standard training loop. Returns (final_ce, total_time_ms, ce_history)."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    ce_history = []
    total_time = 0.0

    for i, batch in enumerate(batches):
        x = batch[:, :-1]
        y = batch[:, 1:]

        t0 = time.perf_counter()
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, VOCAB), y.reshape(-1))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        dt = time.perf_counter() - t0
        total_time += dt

        ce_val = loss.item()
        ce_history.append(ce_val)

        if (i + 1) % 10 == 0 or i == 0:
            print(f"    [{label}] step {i+1}/{len(batches)}: CE={ce_val:.4f} ({dt*1000:.0f}ms/step)")
            sys.stdout.flush()

    return ce_history[-1], total_time * 1000, ce_history


def print_header(name):
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")
    sys.stdout.flush()


def print_ce_graph(histories: Dict[str, List[float]], title="CE Convergence"):
    """ASCII graph of CE histories."""
    print(f"\n  {title}")
    all_vals = [v for h in histories.values() for v in h]
    if not all_vals:
        return
    y_max = max(all_vals)
    y_min = min(all_vals)
    height = 12
    width = 50

    symbols = list("ABCDEFabcdef")
    legend = []
    for idx, (name, hist) in enumerate(histories.items()):
        sym = symbols[idx % len(symbols)]
        legend.append(f"  {sym} = {name}")

    for row in range(height, -1, -1):
        y_val = y_min + (y_max - y_min) * row / height
        line = f"  {y_val:6.3f} |"
        canvas = [' '] * width
        for idx, (name, hist) in enumerate(histories.items()):
            sym = symbols[idx % len(symbols)]
            for j, v in enumerate(hist):
                col = int(j / max(len(hist) - 1, 1) * (width - 1))
                v_row = int((v - y_min) / max(y_max - y_min, 1e-9) * height)
                if v_row == row:
                    canvas[col] = sym
        line += ''.join(canvas)
        print(line)

    print(f"         +{'─' * width}")
    print(f"          step 1{'':>{width - 10}}step {max(len(h) for h in histories.values())}")
    for l in legend:
        print(l)
    print()
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# H1: Progressive Growing
# ═══════════════════════════════════════════════════════════

def expand_model_svd(small: MiniDecoder, d_large: int, n_layers_large: int) -> MiniDecoder:
    """Expand a small model to larger dimensions using SVD-like weight expansion."""
    large = MiniDecoder(d_large, n_layers_large, VOCAB, small.block_size)

    with torch.no_grad():
        # Expand embeddings: pad with scaled noise
        d_small = small.d_model
        large.embed.weight[:, :d_small] = small.embed.weight.data
        large.embed.weight[:, d_small:] = torch.randn(VOCAB, d_large - d_small) * 0.01

        bs = min(small.block_size, large.block_size)
        large.pos_embed.weight[:bs, :d_small] = small.pos_embed.weight.data[:bs]
        large.pos_embed.weight[:bs, d_small:] = torch.randn(bs, d_large - d_small) * 0.01

        # Copy layers (min of both counts)
        n_copy = min(small.n_layers, n_layers_large)
        for li in range(n_copy):
            s_layer = small.layers[li]
            l_layer = large.layers[li]

            # self_attn in_proj_weight: [3*d, d]
            s_w = s_layer.self_attn.in_proj_weight  # [3*d_small, d_small]
            l_w = l_layer.self_attn.in_proj_weight  # [3*d_large, d_large]
            # Copy block-diagonal style
            for block in range(3):
                sr = slice(block * d_small, (block + 1) * d_small)
                lr = slice(block * d_large, block * d_large + d_small)
                l_w[lr, :d_small] = s_w[sr, :]

            s_b = s_layer.self_attn.in_proj_bias
            l_b = l_layer.self_attn.in_proj_bias
            for block in range(3):
                sr = slice(block * d_small, (block + 1) * d_small)
                lr = slice(block * d_large, block * d_large + d_small)
                l_b[lr] = s_b[sr]

            # out_proj: [d, d]
            l_layer.self_attn.out_proj.weight[:d_small, :d_small] = s_layer.self_attn.out_proj.weight
            l_layer.self_attn.out_proj.bias[:d_small] = s_layer.self_attn.out_proj.bias

            # FFN linear1: [4*d, d]
            fd_small = d_small * 4
            fd_large = d_large * 4
            l_layer.linear1.weight[:fd_small, :d_small] = s_layer.linear1.weight
            l_layer.linear1.bias[:fd_small] = s_layer.linear1.bias

            # FFN linear2: [d, 4*d]
            l_layer.linear2.weight[:d_small, :fd_small] = s_layer.linear2.weight
            l_layer.linear2.bias[:d_small] = s_layer.linear2.bias

            # LayerNorms
            l_layer.norm1.weight[:d_small] = s_layer.norm1.weight
            l_layer.norm1.bias[:d_small] = s_layer.norm1.bias
            l_layer.norm2.weight[:d_small] = s_layer.norm2.weight
            l_layer.norm2.bias[:d_small] = s_layer.norm2.bias

        # head: [vocab, d]
        large.head.weight[:, :d_small] = small.head.weight.data
        large.head.weight[:, d_small:] = torch.randn(VOCAB, d_large - d_small) * 0.01

        # ln_f
        large.ln_f.weight[:d_small] = small.ln_f.weight.data
        large.ln_f.bias[:d_small] = small.ln_f.bias.data

    return large


def run_h1():
    """H1: Progressive Growing — train small, expand, fine-tune."""
    print_header("H1: Progressive Growing (64d/2L → 256d/4L)")

    d_small, n_small = 64, 2
    d_large, n_large = 256, 4
    n_phase_a = 30   # steps on small model
    n_phase_b = 15   # fine-tune steps on expanded model
    n_baseline = 45  # same total steps on large model directly

    batches = make_data(batch_size=4, seq_len=128, n_batches=n_baseline)
    batches_a = batches[:n_phase_a]
    batches_b = batches[n_phase_a:n_phase_a + n_phase_b]

    # --- Method: progressive growing ---
    print(f"\n  Phase A: {d_small}d/{n_small}L, {n_phase_a} steps")
    torch.manual_seed(SEED)
    small = MiniDecoder(d_small, n_small, VOCAB, 128)
    print(f"    Small model params: {small.param_count():,}")
    ce_a, time_a, hist_a = train_loop(small, batches_a, lr=3e-4, label="PhaseA")

    print(f"\n  SVD Expansion: {d_small}d → {d_large}d, {n_small}L → {n_large}L")
    expanded = expand_model_svd(small, d_large, n_large)
    print(f"    Expanded model params: {expanded.param_count():,}")

    print(f"\n  Phase B: {d_large}d/{n_large}L, {n_phase_b} steps fine-tune")
    ce_b, time_b, hist_b = train_loop(expanded, batches_b, lr=1e-4, label="PhaseB")
    total_method = time_a + time_b

    # --- Baseline: large model directly ---
    print(f"\n  Baseline: {d_large}d/{n_large}L, {n_baseline} steps from scratch")
    torch.manual_seed(SEED)
    baseline = MiniDecoder(d_large, n_large, VOCAB, 128)
    print(f"    Baseline model params: {baseline.param_count():,}")
    ce_base, time_base, hist_base = train_loop(baseline, batches, lr=3e-4, label="Baseline")

    # Combined history for progressive
    hist_prog = hist_a + hist_b

    print_ce_graph({
        f"Baseline {d_large}d/{n_large}L": hist_base,
        f"Progressive {d_small}d→{d_large}d": hist_prog,
    }, title="H1: Progressive Growing CE")

    result = ExpResult(
        name="H1: Progressive Growing",
        ce_baseline=ce_base, ce_method=ce_b,
        time_baseline_ms=time_base, time_method_ms=total_method,
        extra={
            "ce_phase_a": ce_a,
            "ce_phase_b": ce_b,
            "time_phase_a_ms": time_a,
            "time_phase_b_ms": time_b,
            "small_params": small.param_count(),
            "large_params": expanded.param_count(),
        }
    )
    result.compute()
    print(f"\n  {result}")
    return result


# ═══════════════════════════════════════════════════════════
# H2: Layer Freezing Cascade
# ═══════════════════════════════════════════════════════════

def train_loop_frozen(model, batches, frozen_layers, lr=3e-4, label="train"):
    """Train with specific layers frozen."""
    # Freeze specified layers
    for i, layer in enumerate(model.layers):
        requires = i not in frozen_layers
        for p in layer.parameters():
            p.requires_grad = requires

    # Ensure embed/head always trainable
    for p in model.embed.parameters():
        p.requires_grad = True
    for p in model.pos_embed.parameters():
        p.requires_grad = True
    for p in model.head.parameters():
        p.requires_grad = True
    for p in model.ln_f.parameters():
        p.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = model.param_count()
    print(f"    [{label}] trainable: {trainable:,}/{total:,} ({trainable/total*100:.0f}%)")

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=0.01
    )
    ce_history = []
    total_time = 0.0

    for i, batch in enumerate(batches):
        x = batch[:, :-1]
        y = batch[:, 1:]

        t0 = time.perf_counter()
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, VOCAB), y.reshape(-1))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        dt = time.perf_counter() - t0
        total_time += dt
        ce_history.append(loss.item())

        if (i + 1) % 10 == 0 or i == 0:
            print(f"    [{label}] step {i+1}/{len(batches)}: CE={loss.item():.4f} ({dt*1000:.0f}ms/step)")
            sys.stdout.flush()

    # Unfreeze all
    for p in model.parameters():
        p.requires_grad = True

    return ce_history[-1], total_time * 1000, ce_history


def run_h2():
    """H2: Layer Freezing Cascade — train layers in stages."""
    print_header("H2: Layer Freezing Cascade (4L decoder)")

    d_model, n_layers = 256, 4
    steps_per_phase = 15
    total_steps = steps_per_phase * 3  # 45 total

    batches = make_data(batch_size=4, seq_len=128, n_batches=total_steps)

    # --- Method: cascade ---
    torch.manual_seed(SEED)
    cascade = MiniDecoder(d_model, n_layers, VOCAB, 128)
    print(f"  Model params: {cascade.param_count():,}")

    print(f"\n  Phase 1: Train layers 0,1 (freeze 2,3) — {steps_per_phase} steps")
    ce1, t1, h1 = train_loop_frozen(cascade, batches[:steps_per_phase],
                                      frozen_layers={2, 3}, lr=3e-4, label="P1:L0-1")

    print(f"\n  Phase 2: Train layers 2,3 (freeze 0,1) — {steps_per_phase} steps")
    ce2, t2, h2 = train_loop_frozen(cascade, batches[steps_per_phase:2*steps_per_phase],
                                      frozen_layers={0, 1}, lr=3e-4, label="P2:L2-3")

    print(f"\n  Phase 3: All layers unfrozen — {steps_per_phase} steps")
    ce3, t3, h3 = train_loop_frozen(cascade, batches[2*steps_per_phase:],
                                      frozen_layers=set(), lr=1e-4, label="P3:All")

    total_method = t1 + t2 + t3
    hist_cascade = h1 + h2 + h3

    # --- Baseline ---
    print(f"\n  Baseline: all layers unfrozen, {total_steps} steps")
    torch.manual_seed(SEED)
    baseline = MiniDecoder(d_model, n_layers, VOCAB, 128)
    ce_base, time_base, hist_base = train_loop(baseline, batches, lr=3e-4, label="Baseline")

    print_ce_graph({
        "Baseline (all unfrozen)": hist_base,
        "Cascade (freeze/unfreeze)": hist_cascade,
    }, title="H2: Layer Freezing Cascade CE")

    result = ExpResult(
        name="H2: Layer Freezing Cascade",
        ce_baseline=ce_base, ce_method=ce3,
        time_baseline_ms=time_base, time_method_ms=total_method,
        extra={
            "ce_phase1": ce1, "ce_phase2": ce2, "ce_phase3": ce3,
            "time_phase1_ms": t1, "time_phase2_ms": t2, "time_phase3_ms": t3,
        }
    )
    result.compute()
    print(f"\n  {result}")
    return result


# ═══════════════════════════════════════════════════════════
# H3: Sparse Attention
# ═══════════════════════════════════════════════════════════

class SparseAttentionDecoder(nn.Module):
    """Decoder with local + global sparse attention."""

    def __init__(self, d_model, n_layers, vocab=VOCAB, block_size=256,
                 local_window=32, global_stride=64):
        super().__init__()
        self.d_model = d_model
        self.n_layers = n_layers
        self.block_size = block_size
        self.local_window = local_window
        self.global_stride = global_stride

        self.embed = nn.Embedding(vocab, d_model)
        self.pos_embed = nn.Embedding(block_size, d_model)
        nhead = max(1, d_model // 64)
        self.nhead = nhead

        # Use custom attention layers
        self.layers = nn.ModuleList()
        for _ in range(n_layers):
            self.layers.append(nn.ModuleDict({
                'q': nn.Linear(d_model, d_model),
                'k': nn.Linear(d_model, d_model),
                'v': nn.Linear(d_model, d_model),
                'out': nn.Linear(d_model, d_model),
                'norm1': nn.LayerNorm(d_model),
                'ffn': nn.Sequential(
                    nn.Linear(d_model, d_model * 4),
                    nn.GELU(),
                    nn.Linear(d_model * 4, d_model),
                ),
                'norm2': nn.LayerNorm(d_model),
            }))
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab, bias=False)

    def _sparse_attn(self, q, k, v, layer_dict):
        """Local window + global stride attention."""
        B, T, D = q.shape
        head_dim = D // self.nhead

        q = q.view(B, T, self.nhead, head_dim).transpose(1, 2)
        k = k.view(B, T, self.nhead, head_dim).transpose(1, 2)
        v = v.view(B, T, self.nhead, head_dim).transpose(1, 2)

        # Build sparse attention mask: local window + global tokens
        # For efficiency, we build a [T, T] bool mask
        mask = torch.ones(T, T, device=q.device, dtype=torch.bool)  # True = masked

        for i in range(T):
            # Local: attend to [i-window, i] (causal)
            start = max(0, i - self.local_window)
            mask[i, start:i + 1] = False

            # Global: attend to every global_stride-th token that's before i
            for g in range(0, i + 1, self.global_stride):
                mask[i, g] = False

        # Compute attention with mask
        scale = head_dim ** -0.5
        scores = torch.matmul(q, k.transpose(-2, -1)) * scale
        scores = scores.masked_fill(mask.unsqueeze(0).unsqueeze(0), float('-inf'))
        attn = F.softmax(scores, dim=-1)
        attn = attn.masked_fill(attn.isnan(), 0.0)  # handle all-masked rows

        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, D)
        return out

    def forward(self, x):
        B, T = x.shape
        pos = torch.arange(T, device=x.device).unsqueeze(0)
        h = self.embed(x) + self.pos_embed(pos)

        for layer in self.layers:
            residual = h
            h_n = layer['norm1'](h)
            q = layer['q'](h_n)
            k = layer['k'](h_n)
            v = layer['v'](h_n)
            attn_out = self._sparse_attn(q, k, v, layer)
            h = residual + layer['out'](attn_out)

            residual = h
            h = residual + layer['ffn'](layer['norm2'](h))

        h = self.ln_f(h)
        return self.head(h)

    def param_count(self):
        return sum(p.numel() for p in self.parameters())


def run_h3():
    """H3: Sparse Attention — local+global vs full attention."""
    print_header("H3: Sparse Attention (local=32 + global@64)")

    d_model, n_layers = 192, 3
    seq_len = 256
    n_steps = 30

    batches = make_data(batch_size=4, seq_len=seq_len, n_batches=n_steps)

    # --- Full attention baseline ---
    print(f"\n  Full Attention: {d_model}d/{n_layers}L, seq={seq_len}")
    torch.manual_seed(SEED)
    full_model = MiniDecoder(d_model, n_layers, VOCAB, seq_len)
    print(f"    Params: {full_model.param_count():,}")
    ce_full, time_full, hist_full = train_loop(full_model, batches, lr=3e-4, label="FullAttn")

    # --- Sparse attention ---
    print(f"\n  Sparse Attention: local=32, global@64")
    torch.manual_seed(SEED)
    sparse_model = SparseAttentionDecoder(d_model, n_layers, VOCAB, seq_len,
                                           local_window=32, global_stride=64)
    print(f"    Params: {sparse_model.param_count():,}")
    ce_sparse, time_sparse, hist_sparse = train_loop(sparse_model, batches, lr=3e-4, label="SparseAttn")

    print_ce_graph({
        "Full Attention": hist_full,
        "Sparse (local+global)": hist_sparse,
    }, title="H3: Sparse vs Full Attention CE")

    result = ExpResult(
        name="H3: Sparse Attention",
        ce_baseline=ce_full, ce_method=ce_sparse,
        time_baseline_ms=time_full, time_method_ms=time_sparse,
        extra={
            "local_window": 32,
            "global_stride": 64,
            "seq_len": seq_len,
        }
    )
    result.compute()
    print(f"\n  {result}")
    return result


# ═══════════════════════════════════════════════════════════
# H4: µTransfer
# ═══════════════════════════════════════════════════════════

def run_h4():
    """H4: µTransfer — find optimal lr on small model, transfer to large."""
    print_header("H4: µTransfer (64d→256d hyperparameter transfer)")

    d_small, n_small = 64, 2
    d_large, n_large = 256, 4
    n_sweep_steps = 20
    n_eval_steps = 25

    batches_sweep = make_data(batch_size=4, seq_len=128, n_batches=n_sweep_steps)
    batches_eval = make_data(batch_size=4, seq_len=128, n_batches=n_eval_steps)

    # --- LR sweep on small model ---
    lrs = [1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3]
    print(f"\n  LR sweep on {d_small}d/{n_small}L ({n_sweep_steps} steps each):")

    best_lr_small = None
    best_ce_small = float('inf')
    sweep_results = {}

    for lr in lrs:
        torch.manual_seed(SEED)
        model = MiniDecoder(d_small, n_small, VOCAB, 128)
        ce, t, hist = train_loop(model, batches_sweep, lr=lr, label=f"lr={lr:.0e}")
        sweep_results[lr] = ce
        if ce < best_ce_small:
            best_ce_small = ce
            best_lr_small = lr

    print(f"\n  Sweep results on {d_small}d:")
    for lr, ce in sorted(sweep_results.items()):
        marker = " <<<< BEST" if lr == best_lr_small else ""
        print(f"    lr={lr:.0e}: CE={ce:.4f}{marker}")

    # µTransfer rule: lr_large = lr_small × (d_small / d_large)
    lr_transferred = best_lr_small * (d_small / d_large)
    print(f"\n  µTransfer: lr_small={best_lr_small:.0e} × ({d_small}/{d_large}) = lr_large={lr_transferred:.6f}")

    # --- Evaluate transferred lr on large model ---
    print(f"\n  Evaluate transferred lr on {d_large}d/{n_large}L:")
    torch.manual_seed(SEED)
    model_transfer = MiniDecoder(d_large, n_large, VOCAB, 128)
    ce_transfer, t_transfer, hist_transfer = train_loop(
        model_transfer, batches_eval, lr=lr_transferred, label="µTransfer"
    )

    # --- LR sweep on large model for comparison ---
    print(f"\n  LR sweep on {d_large}d/{n_large}L ({n_eval_steps} steps each):")
    best_lr_large = None
    best_ce_large = float('inf')
    sweep_time = 0.0

    for lr in lrs:
        torch.manual_seed(SEED)
        model = MiniDecoder(d_large, n_large, VOCAB, 128)
        t_start = time.perf_counter()
        ce, t, hist = train_loop(model, batches_eval, lr=lr, label=f"lr={lr:.0e}")
        sweep_time += time.perf_counter() - t_start
        if ce < best_ce_large:
            best_ce_large = ce
            best_lr_large = lr

    print(f"\n  Large model sweep best: lr={best_lr_large:.0e}, CE={best_ce_large:.4f}")
    print(f"  µTransfer result:       lr={lr_transferred:.6f}, CE={ce_transfer:.4f}")

    # Speedup = time(sweep on large) / time(sweep on small + 1 run on large)
    time_small_sweep = sum(
        time.perf_counter() for _ in [None]
    )  # approximate: small sweep is much cheaper
    # Re-measure precisely
    t_small_sweep = 0.0
    for lr in lrs:
        torch.manual_seed(SEED)
        m = MiniDecoder(d_small, n_small, VOCAB, 128)
        _, t_ms, _ = train_loop(m, batches_sweep, lr=lr, label=f"small-lr={lr:.0e}")
        t_small_sweep += t_ms

    time_method = t_small_sweep + t_transfer  # small sweep + 1 large run
    time_baseline = sweep_time * 1000  # full sweep on large

    result = ExpResult(
        name="H4: µTransfer",
        ce_baseline=best_ce_large, ce_method=ce_transfer,
        time_baseline_ms=time_baseline, time_method_ms=time_method,
        extra={
            "best_lr_small": best_lr_small,
            "lr_transferred": lr_transferred,
            "best_lr_large": best_lr_large,
            "sweep_lrs": len(lrs),
        }
    )
    result.compute()
    print(f"\n  {result}")
    return result


# ═══════════════════════════════════════════════════════════
# H5: Optimizer State Compression (1-bit Adam)
# ═══════════════════════════════════════════════════════════

class OneBitAdamW:
    """1-bit Adam: compress m and v to sign only."""

    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.01):
        self.params = list(params)
        self.lr = lr
        self.beta1, self.beta2 = betas
        self.eps = eps
        self.weight_decay = weight_decay
        self.step_count = 0
        self.state = {}

    def zero_grad(self):
        for p in self.params:
            if p.grad is not None:
                p.grad.zero_()

    def step(self):
        self.step_count += 1
        for p in self.params:
            if p.grad is None:
                continue
            g = p.grad.data
            if self.weight_decay > 0:
                g = g + self.weight_decay * p.data

            if id(p) not in self.state:
                # Store full m, v for EMA but compress when using
                self.state[id(p)] = {
                    'm': torch.zeros_like(p.data),
                    'v': torch.zeros_like(p.data),
                }

            s = self.state[id(p)]
            s['m'] = self.beta1 * s['m'] + (1 - self.beta1) * g
            s['v'] = self.beta2 * s['v'] + (1 - self.beta2) * g * g

            # 1-bit compression: use sign of m, magnitude from v
            m_sign = torch.sign(s['m'])
            v_sqrt = torch.sqrt(s['v'] / (1 - self.beta2 ** self.step_count)) + self.eps

            # Bias correction for magnitude
            m_mag = torch.abs(s['m']).mean()  # scalar magnitude
            bc1 = 1 - self.beta1 ** self.step_count

            update = m_sign * m_mag / bc1 / v_sqrt
            p.data -= self.lr * update


def train_loop_1bit(model, batches, lr=1e-3, label="1bit"):
    """Train with 1-bit Adam optimizer."""
    optimizer = OneBitAdamW(model.parameters(), lr=lr, weight_decay=0.01)
    ce_history = []
    total_time = 0.0

    for i, batch in enumerate(batches):
        x = batch[:, :-1]
        y = batch[:, 1:]

        t0 = time.perf_counter()
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, VOCAB), y.reshape(-1))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        dt = time.perf_counter() - t0
        total_time += dt
        ce_history.append(loss.item())

        if (i + 1) % 10 == 0 or i == 0:
            print(f"    [{label}] step {i+1}/{len(batches)}: CE={loss.item():.4f} ({dt*1000:.0f}ms/step)")
            sys.stdout.flush()

    return ce_history[-1], total_time * 1000, ce_history


def run_h5():
    """H5: 1-bit Adam vs full AdamW."""
    print_header("H5: Optimizer State Compression (1-bit Adam)")

    d_model, n_layers = 256, 4
    n_steps = 40

    batches = make_data(batch_size=4, seq_len=128, n_batches=n_steps)

    # --- Full AdamW baseline ---
    print(f"\n  Full AdamW: {d_model}d/{n_layers}L, {n_steps} steps")
    torch.manual_seed(SEED)
    baseline = MiniDecoder(d_model, n_layers, VOCAB, 128)
    print(f"    Params: {baseline.param_count():,}")
    ce_full, time_full, hist_full = train_loop(baseline, batches, lr=3e-4, label="AdamW")

    # --- 1-bit Adam ---
    print(f"\n  1-bit Adam: {d_model}d/{n_layers}L, {n_steps} steps")
    torch.manual_seed(SEED)
    onebit = MiniDecoder(d_model, n_layers, VOCAB, 128)
    ce_1bit, time_1bit, hist_1bit = train_loop_1bit(onebit, batches, lr=3e-4, label="1bitAdam")

    # VRAM comparison (theoretical)
    param_bytes = baseline.param_count() * 4  # float32
    adam_state_bytes = param_bytes * 2  # m + v
    onebit_state_bytes = baseline.param_count() // 8 * 2  # 1 bit per param × 2 states
    print(f"\n  VRAM comparison (theoretical):")
    print(f"    Params:     {param_bytes / 1e6:.1f} MB")
    print(f"    AdamW m+v:  {adam_state_bytes / 1e6:.1f} MB")
    print(f"    1-bit m+v:  {onebit_state_bytes / 1e6:.2f} MB (x{adam_state_bytes / max(onebit_state_bytes, 1):.0f} savings)")

    print_ce_graph({
        "Full AdamW": hist_full,
        "1-bit Adam": hist_1bit,
    }, title="H5: Optimizer Compression CE")

    result = ExpResult(
        name="H5: 1-bit Adam",
        ce_baseline=ce_full, ce_method=ce_1bit,
        time_baseline_ms=time_full, time_method_ms=time_1bit,
        extra={
            "vram_adam_mb": adam_state_bytes / 1e6,
            "vram_1bit_mb": onebit_state_bytes / 1e6,
            "vram_savings_x": adam_state_bytes / max(onebit_state_bytes, 1),
        }
    )
    result.compute()
    print(f"\n  {result}")
    return result


# ═══════════════════════════════════════════════════════════
# H6: Curriculum Length
# ═══════════════════════════════════════════════════════════

def run_h6():
    """H6: Curriculum Length — short→medium→long sequences."""
    print_header("H6: Curriculum Length (32→128→256)")

    d_model, n_layers = 256, 4
    steps_per_phase = 15
    total_steps = steps_per_phase * 3

    seq_lengths = [32, 128, 256]

    # --- Method: curriculum length ---
    torch.manual_seed(SEED)
    curr_model = MiniDecoder(d_model, n_layers, VOCAB, 256)
    print(f"  Model params: {curr_model.param_count():,}")

    optimizer = torch.optim.AdamW(curr_model.parameters(), lr=3e-4, weight_decay=0.01)
    hist_curr = []
    total_method_time = 0.0

    for phase, seq_len in enumerate(seq_lengths):
        phase_batches = make_data(batch_size=4, seq_len=seq_len, n_batches=steps_per_phase)
        print(f"\n  Phase {phase+1}: seq_len={seq_len}, {steps_per_phase} steps")

        for i, batch in enumerate(phase_batches):
            x = batch[:, :-1]
            y = batch[:, 1:]

            t0 = time.perf_counter()
            logits = curr_model(x)
            loss = F.cross_entropy(logits.reshape(-1, VOCAB), y.reshape(-1))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            dt = time.perf_counter() - t0
            total_method_time += dt
            hist_curr.append(loss.item())

            if (i + 1) % 10 == 0 or i == 0:
                print(f"    [Curr seq={seq_len}] step {i+1}/{steps_per_phase}: "
                      f"CE={loss.item():.4f} ({dt*1000:.0f}ms/step)")
                sys.stdout.flush()

    total_method_time *= 1000

    # --- Baseline: fixed seq_len=256 ---
    print(f"\n  Baseline: seq_len=256 fixed, {total_steps} steps")
    base_batches = make_data(batch_size=4, seq_len=256, n_batches=total_steps)
    torch.manual_seed(SEED)
    baseline = MiniDecoder(d_model, n_layers, VOCAB, 256)
    ce_base, time_base, hist_base = train_loop(baseline, base_batches, lr=3e-4, label="Fixed256")

    print_ce_graph({
        "Fixed seq=256": hist_base,
        "Curriculum 32->128->256": hist_curr,
    }, title="H6: Curriculum Length CE")

    result = ExpResult(
        name="H6: Curriculum Length",
        ce_baseline=ce_base, ce_method=hist_curr[-1],
        time_baseline_ms=time_base, time_method_ms=total_method_time,
        extra={
            "seq_lengths": seq_lengths,
            "steps_per_phase": steps_per_phase,
        }
    )
    result.compute()
    print(f"\n  {result}")
    return result


# ═══════════════════════════════════════════════════════════
# Summary table
# ═══════════════════════════════════════════════════════════

def print_summary(results: List[ExpResult]):
    print(f"\n{'='*90}")
    print(f"  H1-H6 DECODER ACCELERATION SUMMARY")
    print(f"{'='*90}")
    print(f"  {'Experiment':30s} | {'CE base':>8s} {'CE meth':>8s} {'CE diff':>8s} | "
          f"{'T base':>8s} {'T meth':>8s} {'Speed':>6s}")
    print(f"  {'─'*30}─┼─{'─'*8}─{'─'*8}─{'─'*8}─┼─{'─'*8}─{'─'*8}─{'─'*6}")

    for r in results:
        r.compute()
        sign = "+" if r.ce_diff_pct >= 0 else ""
        print(f"  {r.name:30s} | {r.ce_baseline:8.4f} {r.ce_method:8.4f} {sign}{r.ce_diff_pct:6.1f}% | "
              f"{r.time_baseline_ms:7.0f}ms {r.time_method_ms:7.0f}ms x{r.speedup:5.2f}")

    # Ranking by speedup (where CE is not much worse)
    print(f"\n  Ranking by speedup (CE penalty < 10%):")
    ranked = sorted(results, key=lambda r: r.speedup, reverse=True)
    for i, r in enumerate(ranked):
        r.compute()
        flag = "OK" if r.ce_diff_pct < 10 else "CE++"
        print(f"    #{i+1}: {r.name:30s} — x{r.speedup:.2f} speed, CE {r.ce_diff_pct:+.1f}% [{flag}]")

    # Ranking by CE improvement
    print(f"\n  Ranking by CE improvement:")
    ranked_ce = sorted(results, key=lambda r: r.ce_diff_pct)
    for i, r in enumerate(ranked_ce):
        r.compute()
        print(f"    #{i+1}: {r.name:30s} — CE {r.ce_diff_pct:+.1f}%, x{r.speedup:.2f} speed")

    # Best combination recommendation
    print(f"\n  Recommended combinations:")
    fast = [r for r in results if r.speedup > 1.1 and r.ce_diff_pct < 5]
    good_ce = [r for r in results if r.ce_diff_pct < 0]
    print(f"    Speed winners (x>1.1, CE<+5%): {', '.join(r.name.split(':')[0].strip() for r in fast) or 'none'}")
    print(f"    CE winners (lower CE): {', '.join(r.name.split(':')[0].strip() for r in good_ce) or 'none'}")

    print(f"\n{'='*90}")
    sys.stdout.flush()

    # Save results
    save_path = os.path.join(os.path.dirname(__file__), 'acceleration_h1_h6_results.json')
    save_data = []
    for r in results:
        r.compute()
        save_data.append({
            'name': r.name,
            'ce_baseline': r.ce_baseline,
            'ce_method': r.ce_method,
            'ce_diff_pct': r.ce_diff_pct,
            'time_baseline_ms': r.time_baseline_ms,
            'time_method_ms': r.time_method_ms,
            'speedup': r.speedup,
            'extra': {k: (v if not isinstance(v, list) else v) for k, v in r.extra.items()},
        })
    with open(save_path, 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"  Results saved: {save_path}")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="H1-H6: Decoder backprop acceleration")
    parser.add_argument('--h1', action='store_true', help='Progressive Growing')
    parser.add_argument('--h2', action='store_true', help='Layer Freezing Cascade')
    parser.add_argument('--h3', action='store_true', help='Sparse Attention')
    parser.add_argument('--h4', action='store_true', help='µTransfer')
    parser.add_argument('--h5', action='store_true', help='1-bit Adam')
    parser.add_argument('--h6', action='store_true', help='Curriculum Length')
    parser.add_argument('--all', action='store_true', help='Run all experiments')
    args = parser.parse_args()

    run_all = args.all or not any([args.h1, args.h2, args.h3, args.h4, args.h5, args.h6])

    print("=" * 70)
    print("  H1-H6: Decoder Backprop Acceleration Experiments")
    print("  Target: 85% training bottleneck (decoder forward+backward)")
    print("=" * 70)
    sys.stdout.flush()

    results = []

    if args.h1 or run_all:
        results.append(run_h1())
    if args.h2 or run_all:
        results.append(run_h2())
    if args.h3 or run_all:
        results.append(run_h3())
    if args.h4 or run_all:
        results.append(run_h4())
    if args.h5 or run_all:
        results.append(run_h5())
    if args.h6 or run_all:
        results.append(run_h6())

    if len(results) > 1:
        print_summary(results)


if __name__ == '__main__':
    main()
