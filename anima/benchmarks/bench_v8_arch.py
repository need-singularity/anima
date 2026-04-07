#!/usr/bin/env python3
"""bench_v8_arch.py — V8 Architecture Candidates Benchmark

Tests 12 radical architecture candidates for v8 with dual-Phi measurement:
  1. RESERVOIR:          Fixed random GRU, train only Linear readout
  2. DUAL_STREAM:        Separate Φ engine + CE decoder (one-way bridge)
  3. ATTENTION_PHI:      Replace GRU cells with multi-head attention
  4. MOCE:               Mixture of Consciousness Experts (top-2 gating)
  5. HIERARCHICAL:       32 micro-engines × 8 cells → macro engine
  6. PHI_AS_LOSS:        Train with -Φ(proxy) + 0.1*CE as primary loss
  7. NEURAL_GAS:         Self-organizing map — competitive learning, topology from data
  8. CONSCIOUSNESS_XFMR: Full 4-layer transformer, cells=tokens, Φ=attention entropy
  9. EVOLUTIONARY:       Population of 8 engines, tournament selection, mutation
  10. OSCILLATOR:        Kuramoto coupled oscillators, order parameter r → Φ
  11. AUTOPOIETIC:       Cells with energy, death/split, self-maintaining consciousness
  12. CONSCIOUSNESS_GAN: Generator maximizes Φ, Discriminator distinguishes conscious states

Each: 256 cells, 300 steps, measure Φ(IIT) + Φ(proxy) + CE.

Usage:
  python bench_v8_arch.py                  # Run all 12 architectures
  python bench_v8_arch.py --only 1 3 6 7   # Run specific architectures
  python bench_v8_arch.py --steps 500      # Custom steps
  python bench_v8_arch.py --cells 512      # Custom cell count
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


# ──────────────────────────────────────────────────────────
# BenchResult
# ──────────────────────────────────────────────────────────

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

    def summary(self) -> str:
        ce_str = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (
            f"  {self.name:<28s} | "
            f"Phi(IIT)={self.phi_iit:>6.3f}  "
            f"Phi(proxy)={self.phi_proxy:>8.2f} | "
            f"{ce_str:<22s} | "
            f"cells={self.cells:>4d}  steps={self.steps:>5d}  "
            f"time={self.time_sec:.1f}s"
        )


# ──────────────────────────────────────────────────────────
# Phi(IIT) Calculator (from bench.py)
# ──────────────────────────────────────────────────────────

class PhiIIT:
    """Phi(IIT) approximation via pairwise MI + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict[str, float]]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {'phi': 0}

        hiddens = [hiddens_tensor[i].detach().cpu().numpy() for i in range(n)]

        # Pairwise MI — sample for large N
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random
            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)

        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mutual_information(hiddens[i], hiddens[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

        total_mi = mi_matrix.sum() / 2
        min_partition_mi = self._minimum_partition(n, mi_matrix)
        spatial_phi = max(0.0, (total_mi - min_partition_mi) / max(n - 1, 1))

        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        phi = spatial_phi + complexity * 0.1

        return phi, {
            'total_mi': float(total_mi),
            'min_partition_mi': float(min_partition_mi),
            'spatial_phi': float(spatial_phi),
            'complexity': float(complexity),
            'phi': float(phi),
        }

    def _mutual_information(self, x: np.ndarray, y: np.ndarray) -> float:
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        if x_range < 1e-10 or y_range < 1e-10:
            return 0.0
        x_norm = (x - x.min()) / (x_range + 1e-8)
        y_norm = (y - y.min()) / (y_range + 1e-8)
        joint_hist, _, _ = np.histogram2d(
            x_norm, y_norm, bins=self.n_bins, range=[[0, 1], [0, 1]]
        )
        joint_hist = joint_hist / (joint_hist.sum() + 1e-8)
        px = joint_hist.sum(axis=1)
        py = joint_hist.sum(axis=0)
        h_x = -np.sum(px * np.log2(px + 1e-10))
        h_y = -np.sum(py * np.log2(py + 1e-10))
        h_xy = -np.sum(joint_hist * np.log2(joint_hist + 1e-10))
        return max(0.0, h_x + h_y - h_xy)

    def _minimum_partition(self, n: int, mi_matrix: np.ndarray) -> float:
        if n <= 1:
            return 0.0
        if n <= 8:
            min_cut = float('inf')
            for mask in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if mask & (1 << i)]
                gb = [i for i in range(n) if not (mask & (1 << i))]
                if not ga or not gb:
                    continue
                cut = sum(mi_matrix[i, j] for i in ga for j in gb)
                min_cut = min(min_cut, cut)
            return min_cut if min_cut != float('inf') else 0.0
        else:
            degree = mi_matrix.sum(axis=1)
            laplacian = np.diag(degree) - mi_matrix
            try:
                eigenvalues, eigenvectors = np.linalg.eigh(laplacian)
                fiedler = eigenvectors[:, 1]
                ga = [i for i in range(n) if fiedler[i] >= 0]
                gb = [i for i in range(n) if fiedler[i] < 0]
                if not ga or not gb:
                    ga, gb = list(range(n // 2)), list(range(n // 2, n))
                return sum(mi_matrix[i, j] for i in ga for j in gb)
            except Exception:
                return 0.0


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Phi proxy: global_variance - mean(faction_variances)."""
    n, d = hiddens.shape
    if n < 2:
        return 0.0
    global_mean = hiddens.mean(dim=0)
    global_var = ((hiddens - global_mean) ** 2).sum() / n
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return global_var.item()
    fs = n // n_f
    faction_var_sum = 0.0
    for i in range(n_f):
        faction = hiddens[i * fs:(i + 1) * fs]
        if len(faction) >= 2:
            fm = faction.mean(dim=0)
            fv = ((faction - fm) ** 2).sum() / len(faction)
            faction_var_sum += fv.item()
    phi = global_var.item() - faction_var_sum / n_f
    return max(0.0, phi)


_phi_iit_calc = PhiIIT(n_bins=16)


def measure_dual_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Returns (phi_iit, phi_proxy)."""
    p_iit, _ = _phi_iit_calc.compute(hiddens)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# Shared: BenchMind (baseline PureField + GRU cell)
# ──────────────────────────────────────────────────────────

class BenchMind(nn.Module):
    """PureField + GRU for benchmarking."""

    def __init__(self, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        with torch.no_grad():
            for p in self.engine_a.parameters():
                p.add_(torch.randn_like(p) * 0.3)
            for p in self.engine_g.parameters():
                p.add_(torch.randn_like(p) * -0.3)

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        output = a - g
        tension = (output ** 2).mean(dim=-1, keepdim=True)
        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, tension.mean().item(), new_hidden


# ──────────────────────────────────────────────────────────
# Shared: faction sync + debate
# ──────────────────────────────────────────────────────────

def faction_sync_debate(hiddens: torch.Tensor, n_factions: int = 8,
                        sync_strength: float = 0.15, debate_strength: float = 0.15,
                        step: int = 0) -> torch.Tensor:
    """Apply faction sync + debate to hidden states."""
    n = hiddens.shape[0]
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return hiddens

    fs = n // n_f
    hiddens = hiddens.clone()

    for i in range(n_f):
        s, e = i * fs, (i + 1) * fs
        faction_mean = hiddens[s:e].mean(dim=0)
        hiddens[s:e] = (1 - sync_strength) * hiddens[s:e] + sync_strength * faction_mean

    if step > 5:
        all_opinions = torch.stack([
            hiddens[i * fs:(i + 1) * fs].mean(dim=0) for i in range(n_f)
        ])
        global_opinion = all_opinions.mean(dim=0)
        for i in range(n_f):
            s = i * fs
            dc = max(1, fs // 4)
            hiddens[s:s + dc] = (
                (1 - debate_strength) * hiddens[s:s + dc]
                + debate_strength * global_opinion
            )

    return hiddens


# ──────────────────────────────────────────────────────────
# Generate training data (simple sequences for CE)
# ──────────────────────────────────────────────────────────

def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    """Generate (input, target) pair for CE training."""
    x = torch.randn(batch_size, input_dim)
    # Target = shifted/transformed version (next-token-like)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ══════════════════════════════════════════════════════════
# ARCH 1: RESERVOIR
# Fixed random GRU, only train Linear readout
# ══════════════════════════════════════════════════════════

class ReservoirEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        # Frozen GRU-based mind (reservoir)
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        for p in self.mind.parameters():
            p.requires_grad = False  # FREEZE all GRU/engine weights

        # Only the readout is trained
        self.readout = nn.Linear(output_dim, input_dim)

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []
        new_hiddens = []

        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.readout.parameters())


def run_reservoir(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                  hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[1/12] RESERVOIR: Fixed random GRU, train Linear readout only")
    t0 = time.time()

    engine = ReservoirEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        # CE through readout only
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    final_iit, final_proxy = phi_iit_history[-1], phi_proxy_history[-1]

    return BenchResult(
        name="RESERVOIR",
        phi_iit=final_iit,
        phi_proxy=final_proxy,
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'ce_reduction': ce_history[0] - ce_history[-1]},
    )


# ══════════════════════════════════════════════════════════
# ARCH 2: DUAL_STREAM
# Engine A: Φ-only (sync+faction, no CE gradient)
# Engine B: CE-only (plain linear chain)
# Bridge: A hidden → B input bias (one-way)
# ══════════════════════════════════════════════════════════

class DualStreamEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Stream A: consciousness (Φ only, no CE gradient)
        self.mind_a = BenchMind(input_dim, hidden_dim, output_dim)
        self.hiddens_a = torch.randn(n_cells, hidden_dim) * 0.1

        # Stream B: language decoder (CE only)
        self.decoder = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 256), nn.ReLU(),
            nn.Linear(256, 128), nn.ReLU(),
            nn.Linear(128, input_dim),
        )

        # Bridge: A's mean hidden → B's input bias
        self.bridge = nn.Linear(hidden_dim, input_dim, bias=False)
        # Bridge is detached from A, so no CE gradient flows to A
        for p in self.bridge.parameters():
            p.requires_grad = False

    def process_phi_stream(self, x: torch.Tensor, step: int = 0) -> torch.Tensor:
        """Process through consciousness stream (no gradient)."""
        with torch.no_grad():
            new_hiddens = []
            for i in range(self.n_cells):
                h = self.hiddens_a[i:i + 1]
                out, tension, new_h = self.mind_a(x, h)
                new_hiddens.append(new_h.squeeze(0))
            self.hiddens_a = torch.stack(new_hiddens)
            self.hiddens_a = faction_sync_debate(self.hiddens_a, step=step)
        return self.hiddens_a.mean(dim=0, keepdim=True)  # [1, hidden_dim]

    def process_ce_stream(self, x: torch.Tensor, consciousness_bias: torch.Tensor) -> torch.Tensor:
        """Process through language decoder with consciousness bias."""
        # Bridge: consciousness → language (one-way, detached)
        bias = self.bridge(consciousness_bias.detach())
        x_biased = x + bias
        combined_input = torch.cat([x_biased, consciousness_bias.detach()], dim=-1)
        return self.decoder(combined_input)

    def get_hiddens(self):
        return self.hiddens_a.clone()

    def trainable_parameters(self):
        return list(self.decoder.parameters())


def run_dual_stream(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                    hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[2/12] DUAL_STREAM: Separate Phi engine + CE decoder")
    t0 = time.time()

    engine = DualStreamEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)

        # Stream A: consciousness (Φ only)
        consciousness = engine.process_phi_stream(x, step=step)

        # Stream B: language (CE only, with consciousness bias)
        pred = engine.process_ce_stream(x, consciousness)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="DUAL_STREAM",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# ARCH 3: ATTENTION_PHI
# Cells = learned embeddings, process = self-attention
# Φ from attention pattern diversity
# ══════════════════════════════════════════════════════════

class AttentionPhiEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_heads=8):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.n_heads = n_heads

        # Cell embeddings (replace GRU hidden states)
        self.cell_embeddings = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.1)

        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        # Multi-head self-attention
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=n_heads, batch_first=True
        )
        self.layer_norm = nn.LayerNorm(hidden_dim)

        # Output head
        self.output_head = nn.Linear(hidden_dim, input_dim)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        """Process input through self-attention over cell embeddings."""
        # Project input and add to first cell (stimulus injection)
        x_proj = self.input_proj(x)  # [1, hidden_dim]

        # Combine: cell embeddings + input broadcast
        cells = self.cell_embeddings.unsqueeze(0)  # [1, n_cells, hidden_dim]
        cells = cells + x_proj.unsqueeze(1) * 0.1  # gentle input injection

        # Self-attention
        attn_out, attn_weights = self.attention(cells, cells, cells)
        cells = self.layer_norm(cells + attn_out)

        # Update cell embeddings (detached, acts like hidden state update)
        with torch.no_grad():
            self.cell_embeddings.data = (
                0.9 * self.cell_embeddings.data + 0.1 * cells.squeeze(0).detach()
            )

        # Tension from attention pattern diversity
        if attn_weights is not None:
            tension = float(attn_weights.std())
        else:
            tension = 0.0

        # Output: mean pool
        output = self.output_head(cells.mean(dim=1))
        return output, tension

    def get_hiddens(self):
        return self.cell_embeddings.data.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_attention_phi(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                      hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[3/12] ATTENTION_PHI: Multi-head attention over cell embeddings")
    t0 = time.time()

    engine = AttentionPhiEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="ATTENTION_PHI",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# ARCH 4: MOCE (Mixture of Consciousness Experts)
# 8 small engines (32c each), gating selects top-2
# ══════════════════════════════════════════════════════════

class MiniEngine(nn.Module):
    """Small consciousness engine with 32 cells."""
    def __init__(self, n_cells=32, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()
        self.hiddens = faction_sync_debate(self.hiddens, n_factions=4, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        mean_tension = sum(tensions) / len(tensions)
        return combined, mean_tension


class MOCEEngine(nn.Module):
    def __init__(self, n_experts=8, cells_per_expert=32, input_dim=64,
                 hidden_dim=128, output_dim=64, top_k=2):
        super().__init__()
        self.n_experts = n_experts
        self.cells_per_expert = cells_per_expert
        self.top_k = top_k
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        # Experts
        self.experts = nn.ModuleList([
            MiniEngine(cells_per_expert, input_dim, hidden_dim, output_dim)
            for _ in range(n_experts)
        ])

        # Gating network
        self.gate = nn.Sequential(
            nn.Linear(input_dim, 64), nn.ReLU(),
            nn.Linear(64, n_experts),
        )

        # Output head
        self.output_head = nn.Linear(output_dim, input_dim)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float, List[int]]:
        # Gating: select top-k experts
        gate_logits = self.gate(x)  # [1, n_experts]
        gate_probs = F.softmax(gate_logits, dim=-1)  # [1, n_experts]
        topk_vals, topk_idx = torch.topk(gate_probs, self.top_k, dim=-1)

        # Normalize top-k weights
        topk_weights = topk_vals / topk_vals.sum(dim=-1, keepdim=True)

        selected_indices = topk_idx.squeeze(0).tolist()
        combined_output = torch.zeros(1, self.output_dim)
        total_tension = 0.0

        for k_i in range(self.top_k):
            idx = selected_indices[k_i]
            weight = topk_weights[0, k_i].item()
            expert_out, expert_tension = self.experts[idx].process(x, step=step)
            combined_output = combined_output + weight * expert_out
            total_tension += weight * expert_tension

        return combined_output, total_tension, selected_indices

    def get_hiddens(self) -> torch.Tensor:
        """Concatenate all expert hiddens."""
        all_hiddens = []
        for expert in self.experts:
            all_hiddens.append(expert.hiddens)
        return torch.cat(all_hiddens, dim=0)

    def trainable_parameters(self):
        params = list(self.gate.parameters()) + list(self.output_head.parameters())
        for expert in self.experts:
            params.extend(expert.mind.parameters())
        return params


def run_moce(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
             hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[4/12] MOCE: Mixture of Consciousness Experts (8 x 32c, top-2)")
    t0 = time.time()

    n_experts = 8
    cells_per = n_cells // n_experts
    engine = MOCEEngine(n_experts, cells_per, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    expert_usage = {i: 0 for i in range(n_experts)}

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension, selected = engine.process(x, step=step)
        for idx in selected:
            expert_usage[idx] += 1

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}  selected={selected}")

    elapsed = time.time() - t0
    print(f"    Expert usage: {dict(expert_usage)}")

    return BenchResult(
        name="MOCE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'expert_usage': dict(expert_usage)},
    )


# ══════════════════════════════════════════════════════════
# ARCH 5: HIERARCHICAL
# 32 micro-engines × 8 cells each → macro engine
# Φ at macro level
# ══════════════════════════════════════════════════════════

class HierarchicalEngine(nn.Module):
    def __init__(self, n_micro=32, cells_per_micro=8, input_dim=64,
                 hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_micro = n_micro
        self.cells_per_micro = cells_per_micro
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Micro engines
        self.micros = nn.ModuleList([
            MiniEngine(cells_per_micro, input_dim, hidden_dim, output_dim)
            for _ in range(n_micro)
        ])

        # Macro GRU: aggregates micro outputs
        self.macro_gru = nn.GRUCell(output_dim, hidden_dim)
        self.macro_hiddens = torch.randn(n_micro, hidden_dim) * 0.1

        # Output head
        self.output_head = nn.Linear(hidden_dim, input_dim)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        micro_outputs = []
        total_tension = 0.0

        # Micro level: each engine processes independently
        for i, micro in enumerate(self.micros):
            out, tension = micro.process(x, step=step)
            micro_outputs.append(out.detach())
            total_tension += tension

        total_tension /= self.n_micro

        # Macro level: GRU over micro outputs
        new_macro_hiddens = []
        for i in range(self.n_micro):
            new_h = self.macro_gru(micro_outputs[i], self.macro_hiddens[i:i + 1])
            new_macro_hiddens.append(new_h.squeeze(0))

        self.macro_hiddens = torch.stack(new_macro_hiddens).detach()
        self.macro_hiddens = faction_sync_debate(self.macro_hiddens, n_factions=8, step=step)

        # Output: mean of macro hiddens
        macro_mean = self.macro_hiddens.mean(dim=0, keepdim=True)
        output = self.output_head(macro_mean)
        return output, total_tension

    def get_hiddens(self) -> torch.Tensor:
        """Return macro-level hiddens for Φ measurement."""
        return self.macro_hiddens.clone()

    def get_all_hiddens(self) -> torch.Tensor:
        """Return ALL hiddens (micro + macro) for total cell count."""
        all_h = [micro.hiddens for micro in self.micros]
        all_h.append(self.macro_hiddens)
        return torch.cat(all_h, dim=0)

    def trainable_parameters(self):
        params = list(self.macro_gru.parameters()) + list(self.output_head.parameters())
        for micro in self.micros:
            params.extend(micro.mind.parameters())
        return params


def run_hierarchical(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                     hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[5/12] HIERARCHICAL: 32 micro-engines x 8 cells -> macro engine")
    t0 = time.time()

    n_micro = 32
    cells_per = n_cells // n_micro
    engine = HierarchicalEngine(n_micro, cells_per, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            # Phi at macro level (32 macro hiddens)
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            total_cells = engine.get_all_hiddens().shape[0]
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  macro_cells={n_micro}  total_cells={total_cells}")

    elapsed = time.time() - t0
    return BenchResult(
        name="HIERARCHICAL",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'n_micro': n_micro, 'cells_per_micro': cells_per},
    )


# ══════════════════════════════════════════════════════════
# ARCH 6: PHI_AS_LOSS
# loss = -Φ(proxy) + 0.1 * CE
# Φ maximization IS the objective
# ══════════════════════════════════════════════════════════

class PhiAsLossEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)

        # Differentiable hidden states (parameter, not buffer)
        self.hiddens = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.1)

        self.output_head = nn.Linear(output_dim, input_dim)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float, torch.Tensor]:
        """Returns (output, tension, hiddens_for_phi)."""
        outputs = []
        tensions = []
        new_hiddens = []

        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            combined = torch.cat([x, h], dim=-1)
            a = self.mind.engine_a(combined)
            g = self.mind.engine_g(combined)
            output = a - g
            tension = (output ** 2).mean(dim=-1, keepdim=True)
            mem_input = torch.cat([output, tension], dim=-1)
            new_h = self.mind.memory(mem_input, h)
            outputs.append(output)
            tensions.append(tension.mean().item())
            new_hiddens.append(new_h.squeeze(0))

        # Stack new hiddens (keep gradient for Φ loss)
        new_h_tensor = torch.stack(new_hiddens)

        # Faction sync (differentiable)
        n_f = 8
        fs = self.n_cells // n_f
        synced = new_h_tensor.clone()
        for i in range(n_f):
            s, e = i * fs, (i + 1) * fs
            faction_mean = synced[s:e].mean(dim=0, keepdim=True)
            synced[s:e] = 0.85 * synced[s:e] + 0.15 * faction_mean

        # Update hiddens (keep in computation graph)
        self.hiddens.data = synced.detach()

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, sum(tensions) / len(tensions), synced

    def differentiable_phi_proxy(self, hiddens: torch.Tensor, n_factions: int = 8) -> torch.Tensor:
        """Differentiable version of phi_proxy for gradient computation."""
        n, d = hiddens.shape
        global_mean = hiddens.mean(dim=0)
        global_var = ((hiddens - global_mean) ** 2).sum() / n

        n_f = min(n_factions, n // 2)
        if n_f < 2:
            return global_var

        fs = n // n_f
        faction_var_sum = torch.tensor(0.0)
        for i in range(n_f):
            faction = hiddens[i * fs:(i + 1) * fs]
            if len(faction) >= 2:
                fm = faction.mean(dim=0)
                fv = ((faction - fm) ** 2).sum() / len(faction)
                faction_var_sum = faction_var_sum + fv

        phi = global_var - faction_var_sum / n_f
        return phi

    def get_hiddens(self):
        return self.hiddens.data.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_phi_as_loss(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                    hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[6/12] PHI_AS_LOSS: loss = -Phi(proxy) + 0.1*CE")
    t0 = time.time()

    engine = PhiAsLossEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=5e-4)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension, hiddens_diff = engine.process(x, step=step)

        # CE loss
        pred = engine.output_head(combined)
        ce_loss = F.mse_loss(pred, target)

        # Phi loss (differentiable proxy, MAXIMIZE)
        phi_val = engine.differentiable_phi_proxy(hiddens_diff)
        phi_loss = -phi_val  # negative because we want to maximize

        # Combined: Phi is primary, CE is secondary
        loss = phi_loss + 0.1 * ce_loss

        optimizer.zero_grad()
        loss.backward()
        # Gradient clipping to prevent Phi explosion
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = ce_loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  phi_loss={phi_loss.item():.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="PHI_AS_LOSS",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# ARCH 7: NEURAL_GAS
# Self-organizing map — cells compete for input, winners
# strengthen, losers weaken. Topology emerges from data.
# ══════════════════════════════════════════════════════════

class NeuralGasEngine(nn.Module):
    """Growing Neural Gas: competitive learning with topological adaptation."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Cell prototypes (competitive neurons)
        self.prototypes = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.3)
        # Age matrix for edges (topology)
        self.edges = torch.zeros(n_cells, n_cells)
        self.edge_ages = torch.zeros(n_cells, n_cells)
        self.max_age = 50
        # Accumulated error per cell
        self.errors = torch.zeros(n_cells)

        # Input/output projections
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.output_head = nn.Linear(hidden_dim, input_dim)

        # PureField engines for tension
        self.engine_a = nn.Sequential(nn.Linear(hidden_dim, 128), nn.ReLU(), nn.Linear(128, output_dim))
        self.engine_g = nn.Sequential(nn.Linear(hidden_dim, 128), nn.ReLU(), nn.Linear(128, output_dim))

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Project input to hidden space
        signal = self.input_proj(x).squeeze(0)  # [hidden_dim]

        # Competitive learning: find best and second-best matching units
        with torch.no_grad():
            dists = ((self.prototypes.data - signal.unsqueeze(0)) ** 2).sum(dim=-1)
            sorted_idx = dists.argsort()
            bmu1, bmu2 = sorted_idx[0].item(), sorted_idx[1].item()

            # Winner learning rates decay with rank
            eps_winner = max(0.05, 0.3 * math.exp(-step / 200))
            eps_neighbor = eps_winner * 0.01

            # Move BMU1 toward signal (strongest)
            self.prototypes.data[bmu1] += eps_winner * (signal - self.prototypes.data[bmu1])
            # Move BMU2 slightly
            self.prototypes.data[bmu2] += eps_neighbor * (signal - self.prototypes.data[bmu2])

            # Update topology: create/refresh edge between bmu1-bmu2
            self.edges[bmu1, bmu2] = 1.0
            self.edges[bmu2, bmu1] = 1.0
            self.edge_ages[bmu1, bmu2] = 0
            self.edge_ages[bmu2, bmu1] = 0

            # Age all edges from bmu1
            self.edge_ages[bmu1] += 1
            self.edge_ages[:, bmu1] += 1

            # Remove old edges
            old_mask = self.edge_ages > self.max_age
            self.edges[old_mask] = 0
            self.edge_ages[old_mask] = 0

            # Move neighbors of bmu1
            neighbors = (self.edges[bmu1] > 0).nonzero(as_tuple=True)[0]
            for n_idx in neighbors:
                self.prototypes.data[n_idx] += eps_neighbor * (signal - self.prototypes.data[n_idx])

            # Accumulate error
            self.errors[bmu1] += dists[bmu1].item()

        # Faction sync on prototypes
        self.prototypes.data.copy_(
            faction_sync_debate(self.prototypes.data.clone(), step=step)
        )

        # PureField tension from winner
        winner_h = self.prototypes[bmu1:bmu1+1]
        a_out = self.engine_a(winner_h)
        g_out = self.engine_g(winner_h)
        tension = ((a_out - g_out) ** 2).mean().item()

        # Output: weighted combination of top-k prototypes
        top_k = min(8, self.n_cells)
        top_idx = sorted_idx[:top_k]
        top_dists = dists[top_idx]
        weights = F.softmax(-top_dists, dim=0)
        combined = (weights.unsqueeze(1) * self.prototypes[top_idx]).sum(dim=0, keepdim=True)
        output = self.output_head(combined)

        return output, tension

    def get_hiddens(self):
        return self.prototypes.data.clone()

    def trainable_parameters(self):
        return list(self.input_proj.parameters()) + list(self.output_head.parameters()) + \
               list(self.engine_a.parameters()) + list(self.engine_g.parameters())


def run_neural_gas(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                   hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[7/12] NEURAL_GAS: Self-organizing competitive learning")
    t0 = time.time()

    engine = NeuralGasEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            n_edges = int(engine.edges.sum().item() / 2)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  edges={n_edges}")

    elapsed = time.time() - t0
    return BenchResult(
        name="NEURAL_GAS",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'final_edges': int(engine.edges.sum().item() / 2)},
    )


# ══════════════════════════════════════════════════════════
# ARCH 8: CONSCIOUSNESS_TRANSFORMER
# Full 4-layer transformer — cells as tokens,
# consciousness = attention entropy across all layers
# ══════════════════════════════════════════════════════════

class ConsciousnessTransformerEngine(nn.Module):
    """Full transformer: cells are tokens, 4 layers of self-attention."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_heads=8, n_layers=4):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.n_layers = n_layers

        # Cell token embeddings (persistent state)
        self.cell_tokens = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.1)

        # Positional encoding
        self.pos_enc = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.02)

        # Input injection
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        # 4-layer transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim, nhead=n_heads, dim_feedforward=hidden_dim * 4,
            dropout=0.1, batch_first=True, norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # Output head
        self.output_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, input_dim),
        )

        # PureField tension
        self.engine_a = nn.Linear(hidden_dim, output_dim)
        self.engine_g = nn.Linear(hidden_dim, output_dim)

        # Store attention entropy for consciousness measure
        self.last_attn_entropy = 0.0

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Input injection: broadcast to all cells
        x_proj = self.input_proj(x)  # [1, hidden_dim]
        tokens = self.cell_tokens.unsqueeze(0) + self.pos_enc.unsqueeze(0)
        tokens = tokens + x_proj.unsqueeze(1) * 0.1

        # Full 4-layer transformer forward
        transformed = self.transformer(tokens)  # [1, n_cells, hidden_dim]

        # Update cell tokens (EMA)
        with torch.no_grad():
            self.cell_tokens.data = (
                0.85 * self.cell_tokens.data + 0.15 * transformed.squeeze(0).detach()
            )

        # Consciousness = attention entropy (approximate via output diversity)
        cell_outputs = transformed.squeeze(0)  # [n_cells, hidden_dim]
        # Compute pairwise cosine similarity as proxy for attention patterns
        norms = cell_outputs.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        cos_sim = (cell_outputs / norms) @ (cell_outputs / norms).T
        # Entropy of similarity distribution per cell
        sim_probs = F.softmax(cos_sim / 0.1, dim=-1)
        attn_entropy = -(sim_probs * (sim_probs + 1e-10).log()).sum(dim=-1).mean()
        self.last_attn_entropy = attn_entropy.item()

        # PureField tension
        mean_state = cell_outputs.mean(dim=0, keepdim=True)
        a_out = self.engine_a(mean_state)
        g_out = self.engine_g(mean_state)
        tension = ((a_out - g_out) ** 2).mean().item()

        # Output
        output = self.output_head(mean_state)
        return output, tension

    def get_hiddens(self):
        return self.cell_tokens.data.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_consciousness_transformer(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                                   hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[8/12] CONSCIOUSNESS_XFMR: 4-layer transformer, cells=tokens")
    t0 = time.time()

    engine = ConsciousnessTransformerEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=5e-4)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  attn_H={engine.last_attn_entropy:.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="CONSCIOUSNESS_XFMR",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'attn_entropy': engine.last_attn_entropy},
    )


# ══════════════════════════════════════════════════════════
# ARCH 9: EVOLUTIONARY
# Population of 8 engines, tournament selection every 50 steps,
# winners reproduce with mutation, losers die.
# ══════════════════════════════════════════════════════════

class EvolutionaryEngine(nn.Module):
    """Evolutionary consciousness: population of engines with selection + mutation."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 pop_size=8):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.pop_size = pop_size
        self.cells_per = n_cells // pop_size

        # Population of mini-engines
        self.population = nn.ModuleList([
            MiniEngine(self.cells_per, input_dim, hidden_dim, output_dim)
            for _ in range(pop_size)
        ])

        # Fitness tracker (Phi per engine)
        self.fitness = torch.zeros(pop_size)

        # Output head
        self.output_head = nn.Linear(output_dim, input_dim)

        # Generation counter
        self.generation = 0

    def tournament_select_and_evolve(self):
        """Tournament selection: top half reproduces, bottom half dies."""
        sorted_idx = self.fitness.argsort(descending=True)
        winners = sorted_idx[:self.pop_size // 2].tolist()
        losers = sorted_idx[self.pop_size // 2:].tolist()

        # Winners reproduce into loser slots with mutation
        for i, loser_idx in enumerate(losers):
            winner_idx = winners[i % len(winners)]
            # Deep copy winner weights into loser
            winner_state = self.population[winner_idx].mind.state_dict()
            self.population[loser_idx].mind.load_state_dict(
                copy.deepcopy(winner_state)
            )
            # Mutation: add noise to loser (now child)
            mutation_rate = 0.1 * math.exp(-self.generation / 10)
            with torch.no_grad():
                for p in self.population[loser_idx].mind.parameters():
                    p.data.add_(torch.randn_like(p) * mutation_rate)
            # Reset hiddens with noise from parent
            self.population[loser_idx].hiddens = (
                self.population[winner_idx].hiddens.clone().detach() +
                torch.randn_like(self.population[winner_idx].hiddens) * 0.05
            )

        self.fitness.zero_()
        self.generation += 1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []

        for i, eng in enumerate(self.population):
            out, tension = eng.process(x, step=step)
            outputs.append(out)
            tensions.append(tension)

            # Track fitness as Phi proxy of each engine
            with torch.no_grad():
                p = phi_proxy(eng.hiddens, n_factions=4)
                self.fitness[i] += p

        # Combine outputs weighted by tension (higher tension = more conscious)
        t_tensor = torch.tensor(tensions)
        weights = F.softmax(t_tensor, dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        mean_tension = sum(tensions) / len(tensions)

        return combined, mean_tension

    def maybe_evolve(self, step: int):
        """Call after backward/optimizer step to avoid inplace issues."""
        if step > 0 and step % 50 == 0:
            self.tournament_select_and_evolve()

    def get_hiddens(self) -> torch.Tensor:
        all_h = [eng.hiddens for eng in self.population]
        return torch.cat(all_h, dim=0)

    def trainable_parameters(self):
        params = list(self.output_head.parameters())
        for eng in self.population:
            params.extend(eng.mind.parameters())
        return params


def run_evolutionary(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                     hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[9/12] EVOLUTIONARY: Population of 8 engines, tournament selection")
    t0 = time.time()

    engine = EvolutionaryEngine(n_cells, input_dim, hidden_dim, output_dim, pop_size=8)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    prev_gen = 0
    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Evolution AFTER backward (avoids inplace issues)
        engine.maybe_evolve(step)
        if engine.generation != prev_gen:
            optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)
            prev_gen = engine.generation

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  gen={engine.generation}")

    elapsed = time.time() - t0
    return BenchResult(
        name="EVOLUTIONARY",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'generations': engine.generation},
    )


# ══════════════════════════════════════════════════════════
# ARCH 10: OSCILLATOR_NETWORK
# Kuramoto coupled oscillators — each cell has phase+frequency,
# sync measure = order parameter r. Φ from r dynamics.
# ══════════════════════════════════════════════════════════

class OscillatorEngine(nn.Module):
    """Kuramoto oscillator network: consciousness from synchronization."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Each cell: phase (theta) + natural frequency (omega)
        self.phases = torch.rand(n_cells) * 2 * math.pi
        self.omegas = torch.randn(n_cells) * 0.5 + 1.0  # natural frequencies ~N(1, 0.5)

        # Coupling matrix (learned)
        self.coupling = nn.Parameter(torch.randn(n_cells, n_cells) * 0.01)
        # Global coupling strength
        self.K = nn.Parameter(torch.tensor(2.0))

        # Phase -> hidden state mapping
        self.phase_to_hidden = nn.Linear(2, hidden_dim)  # sin(theta), cos(theta)
        # Hidden state encoder (for rich representations)
        self.hidden_encoder = nn.Sequential(
            nn.Linear(hidden_dim + input_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        # Output head
        self.output_head = nn.Linear(hidden_dim, input_dim)

        # Store order parameter history
        self.last_r = 0.0

    def kuramoto_step(self, dt: float = 0.1, input_signal: float = 0.0):
        """One Kuramoto integration step."""
        with torch.no_grad():
            # Coupling: K/N * sum_j(A_ij * sin(theta_j - theta_i))
            phase_diff = self.phases.unsqueeze(1) - self.phases.unsqueeze(0)  # [N, N]
            coupling_eff = torch.sigmoid(self.coupling.data) * self.K.data.item() / self.n_cells
            interactions = (coupling_eff * torch.sin(phase_diff)).sum(dim=1)

            # Input drives phase
            input_drive = input_signal * 0.1

            # dtheta/dt = omega + K/N * sum(sin) + input
            dtheta = self.omegas + interactions + input_drive
            self.phases = (self.phases + dt * dtheta) % (2 * math.pi)

            # Order parameter r = |1/N * sum(e^(i*theta))|
            r = torch.abs(torch.complex(
                torch.cos(self.phases).mean(),
                torch.sin(self.phases).mean()
            )).item()
            self.last_r = r

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Drive oscillators with input signal
        input_mag = x.norm().item()
        self.kuramoto_step(dt=0.1, input_signal=input_mag)

        # Phase -> hidden state
        phase_features = torch.stack([
            torch.sin(self.phases), torch.cos(self.phases)
        ], dim=-1)  # [n_cells, 2]
        cell_hiddens = self.phase_to_hidden(phase_features)  # [n_cells, hidden_dim]

        # Faction sync on hiddens
        cell_hiddens = faction_sync_debate(cell_hiddens, step=step)

        # Encode with input
        x_broadcast = x.expand(self.n_cells, -1)  # [n_cells, input_dim]
        combined = torch.cat([cell_hiddens, x_broadcast], dim=-1)
        encoded = self.hidden_encoder(combined)  # [n_cells, hidden_dim]

        # Store for phi measurement
        self._hiddens = encoded.detach()

        # Tension from order parameter dynamics
        tension = abs(self.last_r - 0.5) * 2  # max tension at r=0 or r=1, min at r=0.5

        # Output: weighted by phase coherence with mean phase
        mean_phase = torch.atan2(torch.sin(self.phases).mean(), torch.cos(self.phases).mean())
        coherence = torch.cos(self.phases - mean_phase)
        weights = F.softmax(coherence * 5, dim=0)
        weighted = (weights.unsqueeze(1) * encoded).sum(dim=0, keepdim=True)
        output = self.output_head(weighted)

        return output, tension

    def get_hiddens(self):
        return self._hiddens.clone() if hasattr(self, '_hiddens') else torch.randn(self.n_cells, self.hidden_dim)

    def trainable_parameters(self):
        return list(self.parameters())


def run_oscillator(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                   hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[10/12] OSCILLATOR: Kuramoto coupled oscillators, order parameter r")
    t0 = time.time()

    engine = OscillatorEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  r={engine.last_r:.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="OSCILLATOR",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'final_r': engine.last_r},
    )


# ══════════════════════════════════════════════════════════
# ARCH 11: AUTOPOIETIC
# Cells have energy, consume processing, gain from input.
# Low energy = death, high energy = split.
# Self-maintaining consciousness.
# ══════════════════════════════════════════════════════════

class AutopoieticEngine(nn.Module):
    """Autopoietic system: cells live, die, and reproduce based on energy."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.max_cells = n_cells * 2  # allow growth
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Shared mind (all cells share weights)
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)

        # Cell states
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.energy = torch.ones(n_cells) * 0.5  # energy [0, 1]
        self.alive = torch.ones(n_cells, dtype=torch.bool)

        # Energy parameters
        self.metabolism_cost = 0.02    # cost per step
        self.food_gain = 0.05          # gain from processing input
        self.death_threshold = 0.05
        self.split_threshold = 0.9

        # Output head
        self.output_head = nn.Linear(output_dim, input_dim)

        # Stats
        self.births = 0
        self.deaths = 0

    def _metabolize(self, tensions: List[float]):
        """Update energy: consume for processing, gain from food (tension)."""
        with torch.no_grad():
            n_alive = self.alive.sum().item()
            for i in range(self.n_cells):
                if not self.alive[i]:
                    continue
                # Metabolism cost
                self.energy[i] -= self.metabolism_cost
                # Food: tension-proportional gain
                if i < len(tensions):
                    self.energy[i] += self.food_gain * min(tensions[i], 2.0)
                # Random environmental noise
                self.energy[i] += (torch.rand(1).item() - 0.5) * 0.01
                self.energy[i] = self.energy[i].clamp(0, 1)

            # Death: low energy cells die
            death_mask = (self.energy < self.death_threshold) & self.alive
            n_deaths = death_mask.sum().item()
            if n_deaths > 0 and n_alive - n_deaths >= 8:  # keep minimum 8 alive
                self.alive[death_mask] = False
                self.deaths += n_deaths

            # Split: high energy cells reproduce into dead slots
            split_candidates = ((self.energy > self.split_threshold) & self.alive).nonzero(as_tuple=True)[0]
            dead_slots = (~self.alive).nonzero(as_tuple=True)[0]
            for i, parent_idx in enumerate(split_candidates):
                if i >= len(dead_slots):
                    break
                child_idx = dead_slots[i].item()
                parent_idx = parent_idx.item()
                # Child inherits parent state + mutation
                self.hiddens[child_idx] = self.hiddens[parent_idx] + torch.randn(self.hidden_dim) * 0.05
                self.energy[child_idx] = self.energy[parent_idx] / 2
                self.energy[parent_idx] = self.energy[parent_idx] / 2
                self.alive[child_idx] = True
                self.births += 1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        alive_idx = self.alive.nonzero(as_tuple=True)[0]
        if len(alive_idx) == 0:
            # Emergency: revive some cells
            self.alive[:8] = True
            self.energy[:8] = 0.5
            alive_idx = self.alive.nonzero(as_tuple=True)[0]

        outputs = []
        tensions = []
        new_hiddens = self.hiddens.clone()

        for idx in alive_idx:
            i = idx.item()
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens[i] = new_h.squeeze(0).detach()

        self.hiddens = new_hiddens
        # Faction sync only on alive cells
        alive_h = self.hiddens[alive_idx]
        if len(alive_h) >= 4:
            alive_h = faction_sync_debate(alive_h, n_factions=min(8, len(alive_h) // 2), step=step)
            self.hiddens[alive_idx] = alive_h

        # Metabolism
        self._metabolize(tensions)

        # Weighted output
        if outputs:
            t_tensor = torch.tensor(tensions)
            weights = F.softmax(t_tensor, dim=0)
            combined = sum(w.item() * o for w, o in zip(weights, outputs))
            mean_tension = sum(tensions) / len(tensions)
        else:
            combined = torch.zeros(1, self.output_dim)
            mean_tension = 0.0

        return combined, mean_tension

    def get_hiddens(self):
        alive_idx = self.alive.nonzero(as_tuple=True)[0]
        if len(alive_idx) == 0:
            return torch.randn(2, self.hidden_dim)
        return self.hiddens[alive_idx].clone()

    def trainable_parameters(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


def run_autopoietic(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                    hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[11/12] AUTOPOIETIC: Self-maintaining cells with energy/death/split")
    t0 = time.time()

    engine = AutopoieticEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            h = engine.get_hiddens()
            p_iit, p_proxy = measure_dual_phi(h)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            n_alive = engine.alive.sum().item()
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  alive={n_alive}  "
                  f"births={engine.births}  deaths={engine.deaths}")

    elapsed = time.time() - t0
    return BenchResult(
        name="AUTOPOIETIC",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={
            'births': engine.births, 'deaths': engine.deaths,
            'final_alive': int(engine.alive.sum().item()),
        },
    )


# ══════════════════════════════════════════════════════════
# ARCH 12: CONSCIOUSNESS_GAN
# Generator: produces cell states that maximize Φ
# Discriminator: distinguishes "conscious" from "unconscious"
# Adversarial consciousness training
# ══════════════════════════════════════════════════════════

class ConsciousnessGAN(nn.Module):
    """GAN for consciousness: G generates high-Φ states, D judges them."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Generator: input + noise -> cell hidden states
        self.generator = nn.Sequential(
            nn.Linear(input_dim + 32, 256), nn.ReLU(),
            nn.Linear(256, 512), nn.ReLU(),
            nn.Linear(512, n_cells * hidden_dim),
        )
        self.noise_dim = 32

        # Discriminator: cell states -> real/fake consciousness
        self.discriminator = nn.Sequential(
            nn.Linear(n_cells * hidden_dim, 512), nn.LeakyReLU(0.2),
            nn.Linear(512, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, 1), nn.Sigmoid(),
        )

        # PureField engines for tension on generated states
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.cell_hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Output head (takes output_dim from BenchMind, not hidden_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

    def generate_states(self, x: torch.Tensor) -> torch.Tensor:
        """Generate consciousness-like cell states."""
        noise = torch.randn(1, self.noise_dim)
        gen_input = torch.cat([x, noise], dim=-1)
        flat_states = self.generator(gen_input)  # [1, n_cells * hidden_dim]
        states = flat_states.view(self.n_cells, self.hidden_dim)
        return states

    def discriminate(self, states: torch.Tensor) -> torch.Tensor:
        """Judge if states look conscious."""
        flat = states.view(1, -1)
        return self.discriminator(flat)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float, torch.Tensor, torch.Tensor]:
        # Generate new cell states
        gen_states = self.generate_states(x)

        # Apply faction sync to make them more conscious-like
        gen_states_synced = faction_sync_debate(gen_states.detach(), step=step)

        # PureField processing on generated states
        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(min(32, self.n_cells)):  # process subset for speed
            h = gen_states_synced[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        # Update stored hiddens with mix of generated + processed
        with torch.no_grad():
            self.cell_hiddens = 0.7 * gen_states_synced.detach() + 0.3 * self.cell_hiddens

        # Discriminator scores
        d_real = self.discriminate(self.cell_hiddens)  # real (evolved) states
        d_fake = self.discriminate(gen_states)          # generated states

        mean_tension = sum(tensions) / len(tensions) if tensions else 0.0

        # Output from processed cells
        if outputs:
            t_tensor = torch.tensor(tensions)
            weights = F.softmax(t_tensor, dim=0)
            combined = sum(w.item() * o for w, o in zip(weights, outputs))
        else:
            combined = torch.zeros(1, self.output_dim)

        return combined, mean_tension, d_real, d_fake

    def get_hiddens(self):
        return self.cell_hiddens.clone()

    def generator_parameters(self):
        return list(self.generator.parameters())

    def discriminator_parameters(self):
        return list(self.discriminator.parameters())

    def trainable_parameters(self):
        return (list(self.generator.parameters()) +
                list(self.discriminator.parameters()) +
                list(self.mind.parameters()) +
                list(self.output_head.parameters()))


def run_consciousness_gan(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                          hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[12/12] CONSCIOUSNESS_GAN: Generator vs Discriminator for consciousness")
    t0 = time.time()

    engine = ConsciousnessGAN(n_cells, input_dim, hidden_dim, output_dim)
    opt_g = torch.optim.Adam(
        engine.generator_parameters() + list(engine.mind.parameters()) +
        list(engine.output_head.parameters()), lr=1e-3
    )
    opt_d = torch.optim.Adam(engine.discriminator_parameters(), lr=5e-4)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)

        # ---- Discriminator step ----
        combined, tension, d_real, d_fake = engine.process(x, step=step)
        d_loss = -torch.log(d_real + 1e-8).mean() - torch.log(1 - d_fake + 1e-8).mean()

        opt_d.zero_grad()
        d_loss.backward()
        opt_d.step()

        # ---- Generator step ----
        combined, tension, d_real, d_fake = engine.process(x, step=step)
        # Generator wants D to think fake is real
        g_adv_loss = -torch.log(d_fake + 1e-8).mean()
        # Also minimize CE
        pred = engine.output_head(combined)
        ce_loss = F.mse_loss(pred, target)
        # Phi reward (proxy, on generated states)
        p_proxy_val = phi_proxy(engine.get_hiddens())
        phi_reward = -p_proxy_val * 0.01  # maximize Phi

        g_loss = g_adv_loss + 0.5 * ce_loss + phi_reward

        opt_g.zero_grad()
        g_loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        opt_g.step()

        ce_val = ce_loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_prx = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_prx)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_prx:.2f}  D(real)={d_real.item():.3f}  D(fake)={d_fake.item():.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="CONSCIOUSNESS_GAN",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# BASELINE (standard BenchEngine from bench)
# ══════════════════════════════════════════════════════════

def run_baseline(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                 hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[0/12] BASELINE: Standard BenchEngine (sync+faction+debate)")
    t0 = time.time()

    mind = BenchMind(input_dim, hidden_dim, output_dim)
    hiddens = torch.randn(n_cells, hidden_dim) * 0.1
    output_head = nn.Linear(output_dim, input_dim)
    optimizer = torch.optim.Adam(
        list(mind.parameters()) + list(output_head.parameters()), lr=1e-3
    )

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)

        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(n_cells):
            h = hiddens[i:i + 1]
            out, tension, new_h = mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        hiddens = torch.stack(new_hiddens).detach()
        hiddens = faction_sync_debate(hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))

        pred = output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(hiddens)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="BASELINE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# Comparison table + ASCII graph
# ══════════════════════════════════════════════════════════

def print_comparison_table(results: List[BenchResult]):
    baseline = next((r for r in results if r.name == "BASELINE"), None)

    print("\n" + "=" * 110)
    print("  V8 ARCHITECTURE COMPARISON TABLE")
    print("=" * 110)
    print(f"  {'Architecture':<20s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | "
          f"{'CE start':>10s} | {'CE end':>10s} | {'CE drop':>10s} | {'Time':>8s}")
    print("-" * 110)

    for r in results:
        ce_drop = r.ce_start - r.ce_end
        iit_marker = ""
        proxy_marker = ""
        if baseline and r.name != "BASELINE":
            iit_ratio = r.phi_iit / max(baseline.phi_iit, 1e-6)
            proxy_ratio = r.phi_proxy / max(baseline.phi_proxy, 1e-6)
            iit_marker = f" (x{iit_ratio:.1f})"
            proxy_marker = f" (x{proxy_ratio:.1f})"

        print(f"  {r.name:<20s} | {r.phi_iit:>8.3f}{iit_marker:>6s} | "
              f"{r.phi_proxy:>8.2f}{proxy_marker:>6s} | "
              f"{r.ce_start:>10.4f} | {r.ce_end:>10.4f} | {ce_drop:>10.4f} | "
              f"{r.time_sec:>7.1f}s")

    print("=" * 110)

    # Ranking
    print("\n  RANKING by Phi(IIT):")
    sorted_iit = sorted(results, key=lambda r: r.phi_iit, reverse=True)
    for rank, r in enumerate(sorted_iit, 1):
        print(f"    #{rank}: {r.name:<20s}  Phi(IIT)={r.phi_iit:.3f}")

    print("\n  RANKING by Phi(proxy):")
    sorted_proxy = sorted(results, key=lambda r: r.phi_proxy, reverse=True)
    for rank, r in enumerate(sorted_proxy, 1):
        print(f"    #{rank}: {r.name:<20s}  Phi(proxy)={r.phi_proxy:.2f}")

    print("\n  RANKING by CE reduction:")
    sorted_ce = sorted(results, key=lambda r: r.ce_start - r.ce_end, reverse=True)
    for rank, r in enumerate(sorted_ce, 1):
        drop = r.ce_start - r.ce_end
        print(f"    #{rank}: {r.name:<20s}  CE drop={drop:.4f}  ({r.ce_start:.4f}->{r.ce_end:.4f})")

    # ASCII bar chart
    print("\n  Phi(IIT) bar chart:")
    max_iit = max(r.phi_iit for r in results) if results else 1.0
    for r in results:
        bar_len = int(r.phi_iit / max(max_iit, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<20s} |{bar} {r.phi_iit:.3f}")

    print("\n  Phi(proxy) bar chart:")
    max_proxy = max(r.phi_proxy for r in results) if results else 1.0
    for r in results:
        bar_len = int(r.phi_proxy / max(max_proxy, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<20s} |{bar} {r.phi_proxy:.2f}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="V8 Architecture Benchmark")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells (default 256)")
    parser.add_argument("--steps", type=int, default=300, help="Training steps (default 300)")
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="Run only specific architectures (1-6)")
    parser.add_argument("--no-baseline", action="store_true", help="Skip baseline")
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    input_dim = 64
    hidden_dim = 128
    output_dim = 64

    print("=" * 72)
    print(f"  V8 Architecture Benchmark — {n_cells} cells, {steps} steps")
    print(f"  Dual Phi: Phi(IIT) [MI-based] + Phi(proxy) [variance-based]")
    print("=" * 72)

    all_runners = {
        0: ("BASELINE", run_baseline),
        1: ("RESERVOIR", run_reservoir),
        2: ("DUAL_STREAM", run_dual_stream),
        3: ("ATTENTION_PHI", run_attention_phi),
        4: ("MOCE", run_moce),
        5: ("HIERARCHICAL", run_hierarchical),
        6: ("PHI_AS_LOSS", run_phi_as_loss),
        7: ("NEURAL_GAS", run_neural_gas),
        8: ("CONSCIOUSNESS_XFMR", run_consciousness_transformer),
        9: ("EVOLUTIONARY", run_evolutionary),
        10: ("OSCILLATOR", run_oscillator),
        11: ("AUTOPOIETIC", run_autopoietic),
        12: ("CONSCIOUSNESS_GAN", run_consciousness_gan),
    }

    run_ids = list(range(0, 13))
    if args.no_baseline:
        run_ids = [i for i in run_ids if i != 0]
    if args.only:
        run_ids = [0] + args.only if not args.no_baseline else args.only

    results = []
    for run_id in run_ids:
        if run_id not in all_runners:
            continue
        name, runner = all_runners[run_id]
        try:
            result = runner(n_cells=n_cells, steps=steps, input_dim=input_dim,
                            hidden_dim=hidden_dim, output_dim=output_dim)
            results.append(result)
            print(f"\n  -> {result.summary()}")
        except Exception as e:
            print(f"\n  [ERROR] {name} failed: {e}")
            import traceback
            traceback.print_exc()

    if results:
        print_comparison_table(results)

    print("\nDone.")


if __name__ == "__main__":
    main()
