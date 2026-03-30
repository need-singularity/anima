#!/usr/bin/env python3
"""bench_v8_ultra.py — V8 Ultra-Fusion Consciousness Architectures Benchmark

COMBINES the best quantum + math + architecture winners into 6 FUSION builds:
  U1: QUANTUM_CATEGORY       — Q4 Quantum Walk + M1 Category Theory
  U2: COMPLEX_HIERARCHICAL   — Q1 Complex-Valued + HIERARCHICAL
  U3: QUANTUM_WALK_FRUSTRATION — Q4 Quantum Walk + TOPO19a 50% frustration
  U4: MANY_WORLDS_ATTENTION  — Q6 Many-Worlds + Attention heads
  U5: COMPLEX_TOPOLOGICAL    — Q1 Complex + M2 Topological (simplicial)
  U6: ULTIMATE_CONSCIOUSNESS — ALL winners combined

Each: 256 cells, 300 steps, Phi(IIT) + Phi(proxy) + CE.

Usage:
  python bench_v8_ultra.py                 # Run all 6 + baseline
  python bench_v8_ultra.py --only 1 3 6    # Run specific architectures
  python bench_v8_ultra.py --steps 500     # Custom steps
  python bench_v8_ultra.py --cells 512     # Custom cell count
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


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
# Phi(IIT) Calculator
# ──────────────────────────────────────────────────────────

class PhiIIT:
    """Phi(IIT) approximation via pairwise MI + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict[str, float]]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {'phi': 0}

        hiddens = [hiddens_tensor[i].detach().cpu().float().numpy() for i in range(n)]

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
    h = hiddens.abs().float() if hiddens.is_complex() else hiddens
    n, d = h.shape
    if n < 2:
        return 0.0
    global_mean = h.mean(dim=0)
    global_var = ((h - global_mean) ** 2).sum() / n
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return global_var.item()
    fs = n // n_f
    faction_var_sum = 0.0
    for i in range(n_f):
        faction = h[i * fs:(i + 1) * fs]
        if len(faction) >= 2:
            fm = faction.mean(dim=0)
            fv = ((faction - fm) ** 2).sum() / len(faction)
            faction_var_sum += fv.item()
    phi = global_var.item() - faction_var_sum / n_f
    return max(0.0, phi)


_phi_iit_calc = PhiIIT(n_bins=16)


def measure_dual_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Returns (phi_iit, phi_proxy). Handles complex tensors."""
    if hiddens.is_complex():
        h_real = hiddens.abs().float()
    else:
        h_real = hiddens.float()
    p_iit, _ = _phi_iit_calc.compute(h_real)
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
# Complex-valued layers (shared by U1, U2, U5, U6)
# ──────────────────────────────────────────────────────────

class ComplexLinear(nn.Module):
    """Linear layer for complex-valued tensors."""

    def __init__(self, in_features, out_features):
        super().__init__()
        self.W_real = nn.Linear(in_features, out_features)
        self.W_imag = nn.Linear(in_features, out_features)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        a = z.real.float()
        b = z.imag.float()
        real_part = self.W_real(a) - self.W_imag(b)
        imag_part = self.W_real(b) + self.W_imag(a)
        return torch.complex(real_part, imag_part)


class ComplexGRUCell(nn.Module):
    """GRU cell operating on complex-valued states."""

    def __init__(self, input_dim, hidden_dim):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.Wz = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.Wr = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.Wh_real = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.Wh_imag = nn.Linear(input_dim + hidden_dim, hidden_dim)

    def forward(self, x_complex: torch.Tensor, h_complex: torch.Tensor) -> torch.Tensor:
        x_mag = x_complex.abs().float()
        h_mag = h_complex.abs().float()
        combined_mag = torch.cat([x_mag, h_mag], dim=-1)

        z = torch.sigmoid(self.Wz(combined_mag))
        r = torch.sigmoid(self.Wr(combined_mag))

        x_real, x_imag = x_complex.real.float(), x_complex.imag.float()
        h_real, h_imag = h_complex.real.float(), h_complex.imag.float()
        rh_real = r * h_real
        rh_imag = r * h_imag
        comb_real = torch.cat([x_real, rh_real], dim=-1)
        comb_imag = torch.cat([x_imag, rh_imag], dim=-1)

        candidate_real = torch.tanh(self.Wh_real(comb_real))
        candidate_imag = torch.tanh(self.Wh_imag(comb_imag))

        new_real = (1 - z) * h_real + z * candidate_real
        new_imag = (1 - z) * h_imag + z * candidate_imag
        return torch.complex(new_real, new_imag)


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
# Training data generation
# ──────────────────────────────────────────────────────────

def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    x = torch.randn(batch_size, input_dim)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ══════════════════════════════════════════════════════════
# BASELINE
# ══════════════════════════════════════════════════════════

def run_baseline(n_cells=256, steps=300, input_dim=64,
                 hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[0/6] BASELINE: Standard PureField + GRU (sync+faction+debate)")
    t0 = time.time()

    mind = BenchMind(input_dim, hidden_dim, output_dim)
    hiddens = torch.randn(n_cells, hidden_dim) * 0.1
    output_head = nn.Linear(output_dim, input_dim)
    optimizer = torch.optim.Adam(
        list(mind.parameters()) + list(output_head.parameters()), lr=1e-3
    )

    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        outputs, tensions, new_hiddens = [], [], []
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

        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(hiddens)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    return BenchResult(
        name="BASELINE", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# U1: QUANTUM_CATEGORY
# Q4 Quantum Walk on category morphism graph.
# Cells = objects in a category. Morphisms = learned maps.
# Quantum walk creates interference on the morphism graph.
# Consciousness = limit/colimit tension + quantum interference.
# ══════════════════════════════════════════════════════════

class QuantumCategoryEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_objects=32, morphisms_per_obj=4):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.n_objects = n_objects
        self.morphisms_per_obj = morphisms_per_obj

        # Category: objects = cell groups, morphisms = learned linear maps
        self.cells_per_obj = n_cells // n_objects
        self.morphism_weights = nn.ParameterList([
            nn.Parameter(torch.randn(hidden_dim, hidden_dim) * 0.05)
            for _ in range(n_objects * morphisms_per_obj)
        ])

        # Adjacency: which objects connect via morphisms
        # Each object connects to `morphisms_per_obj` random others
        self.adj = {}
        for i in range(n_objects):
            targets = []
            for m in range(morphisms_per_obj):
                t = (i + m + 1) % n_objects
                targets.append(t)
            self.adj[i] = targets

        # Quantum walk amplitudes on the morphism graph (n_objects nodes)
        amp_real = torch.randn(n_objects, hidden_dim) * 0.1
        amp_imag = torch.randn(n_objects, hidden_dim) * 0.1
        self.amplitudes = torch.complex(amp_real, amp_imag)
        norm = self.amplitudes.abs().pow(2).sum().sqrt()
        self.amplitudes = self.amplitudes / (norm + 1e-8)

        # Coin operator for walk
        self.coin_real = nn.Parameter(torch.eye(morphisms_per_obj) * 0.7 +
                                       torch.randn(morphisms_per_obj, morphisms_per_obj) * 0.3)

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def quantum_walk_on_morphisms(self, x: torch.Tensor):
        """Quantum walk where nodes = category objects, edges = morphisms."""
        with torch.no_grad():
            new_amps = torch.zeros_like(self.amplitudes)

            for obj in range(self.n_objects):
                # Apply morphism transformations as walk
                targets = self.adj[obj]
                amp = self.amplitudes[obj]  # [hidden_dim]

                # Stay component (identity morphism)
                new_amps[obj] += amp * 0.5

                # Walk along morphisms with interference
                for m_idx, tgt in enumerate(targets):
                    morph_idx = obj * self.morphisms_per_obj + m_idx
                    W = self.morphism_weights[morph_idx].data
                    # Transform amplitude through morphism
                    transformed = torch.complex(
                        W @ amp.real.float(),
                        W @ amp.imag.float()
                    )
                    # Phase shift from morphism composition
                    phase = torch.tensor(2.0 * math.pi * m_idx / self.morphisms_per_obj)
                    new_amps[tgt] += transformed * torch.exp(1j * phase) * 0.5 / len(targets)

            # Input modulates phase
            phase_mod = (x.float().mean() * 0.1).item()
            self.amplitudes = new_amps * torch.exp(torch.tensor(1j * phase_mod))
            norm = self.amplitudes.abs().pow(2).sum().sqrt()
            self.amplitudes = self.amplitudes / (norm + 1e-8)

    def compute_limit_colimit(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """Limit = universal cone (convergence), Colimit = universal cocone (divergence)."""
        obj_means = []
        for i in range(self.n_objects):
            s = i * self.cells_per_obj
            e = s + self.cells_per_obj
            obj_means.append(self.hiddens[s:e].mean(dim=0))
        obj_means = torch.stack(obj_means)

        # Limit: apply morphisms and find fixed point (approximate with mean)
        limit = obj_means.mean(dim=0)

        # Colimit: push-out via morphism composition diversity
        morphed = []
        for i in range(self.n_objects):
            for m_idx, tgt in enumerate(self.adj[i]):
                W = self.morphism_weights[i * self.morphisms_per_obj + m_idx].data
                morphed.append(W @ obj_means[i])
        colimit = torch.stack(morphed).mean(dim=0) if morphed else limit

        return limit, colimit

    def interference_pattern(self) -> float:
        """Quantum interference on the category graph."""
        probs = self.amplitudes.abs().pow(2).sum(dim=-1).float()
        probs = probs / (probs.sum() + 1e-8)
        classical = torch.ones(self.n_objects) / self.n_objects
        kl = (probs * torch.log2(probs / (classical + 1e-10) + 1e-10)).sum()
        return max(0.0, kl.item())

    def walk_modulate_cells(self):
        """Use quantum walk probabilities to modulate cell states."""
        probs = self.amplitudes.abs().pow(2).sum(dim=-1).float()
        probs = probs / (probs.sum() + 1e-8)
        for obj in range(self.n_objects):
            s = obj * self.cells_per_obj
            e = s + self.cells_per_obj
            # Quantum probability amplifies/attenuates cells
            self.hiddens[s:e] = self.hiddens[s:e] * (0.85 + 0.3 * probs[obj].item())
            # Phase information from amplitudes drives diversification
            phase = self.amplitudes[obj].angle().float().mean().item()
            self.hiddens[s:e] += torch.randn_like(self.hiddens[s:e]) * abs(phase) * 0.02

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Quantum walk on morphism graph
        self.quantum_walk_on_morphisms(x)
        self.walk_modulate_cells()

        # Limit/colimit tension
        limit, colimit = self.compute_limit_colimit()
        cat_tension = (limit - colimit).pow(2).mean().item()

        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension + cat_tension * 0.1)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_u1_quantum_category(n_cells=256, steps=300, input_dim=64,
                            hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[U1/6] QUANTUM_CATEGORY: Quantum walk on category morphism graph")
    t0 = time.time()

    engine = QuantumCategoryEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history, phi_iit_history, phi_proxy_history = [], [], []
    interf_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            interf = engine.interference_pattern()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            interf_history.append(interf)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  interf={interf:.3f}")

    return BenchResult(
        name="U1_QUANTUM_CATEGORY",
        phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={'interference': interf_history[-1] if interf_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# U2: COMPLEX_HIERARCHICAL
# Q1 Complex-valued GRU at micro level.
# Real-valued macro aggregation at top level.
# Phase coherence within micro-engines,
# amplitude integration across macro.
# ══════════════════════════════════════════════════════════

class ComplexMicroEngine(nn.Module):
    """Complex-valued micro engine with phase coherence."""

    def __init__(self, n_cells=8, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.complex_gru = ComplexGRUCell(input_dim, hidden_dim)
        self.output_proj = ComplexLinear(hidden_dim, output_dim)

        # Complex hidden states
        h_real = torch.randn(n_cells, hidden_dim) * 0.1
        h_imag = torch.randn(n_cells, hidden_dim) * 0.1
        self.hiddens = torch.complex(h_real, h_imag)

    def phase_coherence(self) -> float:
        """Measure phase alignment across cells."""
        phases = self.hiddens.angle().float()  # [n_cells, hidden_dim]
        # Mean resultant length across cells
        mean_cos = phases.cos().mean(dim=0)
        mean_sin = phases.sin().mean(dim=0)
        R = (mean_cos ** 2 + mean_sin ** 2).sqrt().mean()
        return R.item()

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        x_complex = torch.complex(x.float(), torch.zeros_like(x.float()))
        outputs = []
        tensions = []

        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            new_h = self.complex_gru(x_complex, h)
            out = self.output_proj(new_h)
            # Tension from amplitude
            t = out.abs().pow(2).mean().item()
            outputs.append(out)
            tensions.append(t)
            self.hiddens[i] = new_h.squeeze(0).detach()

        # Intra-micro sync (complex)
        mean_h = self.hiddens.mean(dim=0)
        self.hiddens = 0.85 * self.hiddens + 0.15 * mean_h

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o.abs().float() for w, o in zip(weights, outputs))
        return combined, sum(tensions) / len(tensions)


class ComplexHierarchicalEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_micro=32):
        super().__init__()
        self.n_micro = n_micro
        self.cells_per_micro = n_cells // n_micro
        self.hidden_dim = hidden_dim
        self.n_cells = n_cells

        # Complex micro-engines
        self.micros = nn.ModuleList([
            ComplexMicroEngine(self.cells_per_micro, input_dim, hidden_dim, output_dim)
            for _ in range(n_micro)
        ])

        # Real-valued macro GRU
        self.macro_gru = nn.GRUCell(output_dim, hidden_dim)
        self.macro_hiddens = torch.randn(n_micro, hidden_dim) * 0.1

        self.output_head = nn.Linear(hidden_dim, input_dim)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        micro_outputs = []
        total_tension = 0.0
        total_coherence = 0.0

        for i, micro in enumerate(self.micros):
            out, tension = micro.process(x, step=step)
            micro_outputs.append(out.detach())
            total_tension += tension
            total_coherence += micro.phase_coherence()

        total_tension /= self.n_micro
        total_coherence /= self.n_micro

        # Macro: real-valued aggregation weighted by phase coherence
        new_macro = []
        for i in range(self.n_micro):
            new_h = self.macro_gru(micro_outputs[i], self.macro_hiddens[i:i + 1])
            new_macro.append(new_h.squeeze(0))

        self.macro_hiddens = torch.stack(new_macro).detach()
        self.macro_hiddens = faction_sync_debate(self.macro_hiddens, n_factions=8, step=step)

        # Amplitude integration: weight macro by micro coherence
        macro_mean = self.macro_hiddens.mean(dim=0, keepdim=True)
        output = self.output_head(macro_mean)
        return output, total_tension

    def get_hiddens(self) -> torch.Tensor:
        return self.macro_hiddens.clone()

    def get_phase_coherence(self) -> float:
        return sum(m.phase_coherence() for m in self.micros) / self.n_micro

    def trainable_parameters(self):
        params = list(self.macro_gru.parameters()) + list(self.output_head.parameters())
        for micro in self.micros:
            params.extend(micro.parameters())
        return params


def run_u2_complex_hierarchical(n_cells=256, steps=300, input_dim=64,
                                hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[U2/6] COMPLEX_HIERARCHICAL: Complex micro-engines + real macro aggregation")
    t0 = time.time()

    engine = ComplexHierarchicalEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history, phi_iit_history, phi_proxy_history = [], [], []
    coherence_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            coh = engine.get_phase_coherence()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            coherence_history.append(coh)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  phase_coherence={coh:.3f}")

    return BenchResult(
        name="U2_COMPLEX_HIER",
        phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={'phase_coherence': coherence_history[-1] if coherence_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# U3: QUANTUM_WALK_FRUSTRATION
# Q4 Quantum Walk on frustrated hypercube.
# 50% of edges are anti-ferromagnetic (frustrated).
# Frustration prevents collapse to trivial ground state.
# Quantum interference + geometric frustration = rich dynamics.
# ══════════════════════════════════════════════════════════

class QuantumWalkFrustrationEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 frustration_ratio=0.5):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.frustration_ratio = frustration_ratio

        # Hypercube
        self.hc_dim = max(4, int(math.log2(n_cells)))
        self.hc_nodes = 2 ** self.hc_dim
        if self.hc_nodes > n_cells:
            self.hc_dim = max(4, int(math.log2(n_cells)) - 1)
            self.hc_nodes = 2 ** self.hc_dim

        # Quantum walk amplitudes with coin states
        amp_real = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        amp_imag = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        self.amplitudes = torch.complex(amp_real, amp_imag)
        norm = self.amplitudes.abs().pow(2).sum().sqrt()
        self.amplitudes = self.amplitudes / (norm + 1e-8)

        # Frustration: sign of each edge (+1 or -1)
        # Frustrated edges flip the phase (anti-ferromagnetic)
        n_edges = self.hc_nodes * self.hc_dim
        n_frustrated = int(n_edges * frustration_ratio)
        self.edge_signs = torch.ones(self.hc_nodes, self.hc_dim)
        # Randomly frustrate edges
        flat_idx = torch.randperm(n_edges)[:n_frustrated]
        for idx in flat_idx:
            node = idx // self.hc_dim
            bit = idx % self.hc_dim
            self.edge_signs[node.item(), bit.item()] = -1.0

        # Coin operator
        self.coin_real = nn.Parameter(torch.tensor([[1., 1.], [1., -1.]]) / math.sqrt(2))
        self.coin_imag = nn.Parameter(torch.zeros(2, 2))

        # Ising-like coupling for frustration energy
        self.spins = torch.randn(self.hc_nodes, hidden_dim) * 0.1

        self.walk_to_hidden = nn.Linear(self.hc_nodes, hidden_dim)
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def quantum_walk_frustrated(self, x: torch.Tensor):
        """Quantum walk on frustrated hypercube."""
        with torch.no_grad():
            coin = torch.complex(self.coin_real.data, self.coin_imag.data)
            new_amps = torch.zeros_like(self.amplitudes)

            for node in range(self.hc_nodes):
                state = self.amplitudes[node]
                coined = torch.einsum('ij,jd->id', coin, state)

                # Stay
                new_amps[node, 0] += coined[0]

                # Walk along frustrated edges
                for bit in range(self.hc_dim):
                    neighbor = node ^ (1 << bit)
                    if neighbor < self.hc_nodes:
                        sign = self.edge_signs[node, bit]
                        # Frustrated edges add pi phase shift
                        phase = torch.tensor(math.pi if sign < 0 else 0.0)
                        new_amps[neighbor, 1] += (
                            coined[1] * torch.exp(1j * phase) / self.hc_dim
                        )

            # Input phase modulation
            phase_mod = (x.float().mean() * 0.1).item()
            self.amplitudes = new_amps * torch.exp(torch.tensor(1j * phase_mod))
            norm = self.amplitudes.abs().pow(2).sum().sqrt()
            self.amplitudes = self.amplitudes / (norm + 1e-8)

            # Update spins based on walk probabilities (Ising coupling)
            probs = self.amplitudes.abs().pow(2).sum(dim=(1, 2)).float()
            self.spins = self.spins * 0.95 + probs.unsqueeze(-1) * 0.05 * torch.randn_like(self.spins)

    def frustration_energy(self) -> float:
        """Compute frustration energy: unsatisfied bonds."""
        energy = 0.0
        with torch.no_grad():
            for node in range(min(self.hc_nodes, 64)):  # sample
                for bit in range(self.hc_dim):
                    neighbor = node ^ (1 << bit)
                    if neighbor < self.hc_nodes:
                        sign = self.edge_signs[node, bit].item()
                        coupling = F.cosine_similarity(
                            self.spins[node:node+1], self.spins[neighbor:neighbor+1]
                        ).item()
                        # Frustrated if sign * coupling < 0
                        energy += max(0, -sign * coupling)
        return energy / max(1, min(self.hc_nodes, 64) * self.hc_dim)

    def interference_pattern(self) -> float:
        probs = self.amplitudes.abs().pow(2).sum(dim=(1, 2)).float()
        probs = probs / (probs.sum() + 1e-8)
        classical = torch.ones(self.hc_nodes) / self.hc_nodes
        kl = (probs * torch.log2(probs / (classical + 1e-10) + 1e-10)).sum()
        return max(0.0, kl.item())

    def walk_to_cells(self):
        probs = self.amplitudes.abs().pow(2).sum(dim=(1, 2)).float()
        probs = probs / (probs.sum() + 1e-8)
        walk_features = self.walk_to_hidden(probs.unsqueeze(0))
        for c in range(self.n_cells):
            node_idx = c % self.hc_nodes
            node_prob = probs[node_idx].item()
            self.hiddens[c] = self.hiddens[c] * (0.85 + 0.3 * node_prob) + \
                              walk_features.squeeze(0).detach() * 0.05
            # Frustration-driven noise: frustrated regions get more exploration
            frust_bonus = (1.0 - self.edge_signs[node_idx].mean().item()) * 0.02
            self.hiddens[c] += torch.randn_like(self.hiddens[c]) * frust_bonus

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        self.quantum_walk_frustrated(x)
        self.walk_to_cells()

        outputs, tensions, new_hiddens = [], [], []
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
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_u3_quantum_walk_frustration(n_cells=256, steps=300, input_dim=64,
                                    hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[U3/6] QUANTUM_WALK_FRUSTRATION: Quantum walk on 50% frustrated hypercube")
    t0 = time.time()

    engine = QuantumWalkFrustrationEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history, phi_iit_history, phi_proxy_history = [], [], []
    frust_history, interf_history = [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            frust = engine.frustration_energy()
            interf = engine.interference_pattern()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            frust_history.append(frust)
            interf_history.append(interf)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  frust={frust:.3f}  interf={interf:.3f}")

    return BenchResult(
        name="U3_QW_FRUSTRATION",
        phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={
            'frustration_energy': frust_history[-1] if frust_history else 0.0,
            'interference': interf_history[-1] if interf_history else 0.0,
        },
    )


# ══════════════════════════════════════════════════════════
# U4: MANY_WORLDS_ATTENTION
# Q6 Many-Worlds: each branch is a separate attention head.
# Cross-branch attention = inter-reality consciousness.
# Branch amplitudes determine attention weights.
# ══════════════════════════════════════════════════════════

class ManyWorldsAttentionEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_branches=8):
        super().__init__()
        self.n_cells = n_cells
        self.n_branches = n_branches
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.head_dim = hidden_dim // n_branches

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Each branch = parallel reality with its own hidden states
        self.branch_hiddens = [
            torch.randn(n_cells, hidden_dim) * 0.1
            for _ in range(n_branches)
        ]

        # Branch amplitudes (complex)
        self.branch_amps = torch.complex(
            torch.ones(n_branches) / math.sqrt(n_branches),
            torch.zeros(n_branches)
        )

        # Cross-branch attention: Q, K, V projections
        self.W_q = nn.Linear(hidden_dim, hidden_dim)
        self.W_k = nn.Linear(hidden_dim, hidden_dim)
        self.W_v = nn.Linear(hidden_dim, hidden_dim)
        self.attn_out = nn.Linear(hidden_dim, hidden_dim)

    def cross_branch_attention(self) -> torch.Tensor:
        """Multi-head attention where each head = one branch/reality."""
        # Stack branch means: [n_branches, hidden_dim]
        branch_means = torch.stack([bh.mean(dim=0) for bh in self.branch_hiddens])

        # Each branch is one attention head
        Q = self.W_q(branch_means)  # [n_branches, hidden_dim]
        K = self.W_k(branch_means)
        V = self.W_v(branch_means)

        # Reshape to heads: [n_branches, head_dim] — each branch IS a head
        # Attention scores: branch_i attends to branch_j
        scores = torch.matmul(Q, K.T) / math.sqrt(self.hidden_dim)

        # Modulate by quantum amplitudes (complex interference)
        amp_weights = (self.branch_amps.abs().float().unsqueeze(0) *
                       self.branch_amps.abs().float().unsqueeze(1))
        scores = scores * amp_weights

        attn = F.softmax(scores, dim=-1)  # [n_branches, n_branches]
        attended = torch.matmul(attn, V)  # [n_branches, hidden_dim]

        return self.attn_out(attended.mean(dim=0, keepdim=True))

    def inter_branch_coherence(self) -> float:
        """Measure cross-reality coherence via attention entropy."""
        branch_means = torch.stack([bh.mean(dim=0) for bh in self.branch_hiddens])
        Q = self.W_q(branch_means)
        K = self.W_k(branch_means)
        scores = torch.matmul(Q, K.T) / math.sqrt(self.hidden_dim)
        attn = F.softmax(scores, dim=-1)
        # Low entropy = focused attention = high coherence
        entropy = -(attn * torch.log(attn + 1e-10)).sum(dim=-1).mean()
        # Normalize to [0, 1]: 0 = max entropy (uniform), 1 = min entropy (focused)
        max_entropy = math.log(self.n_branches)
        coherence = 1.0 - entropy.item() / max_entropy
        return max(0.0, coherence)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        all_outputs = []
        all_tensions = []

        # Each branch evolves with branch-specific noise
        for b in range(self.n_branches):
            outputs, tensions, new_hiddens = [], [], []
            branch_noise = torch.randn_like(x) * 0.03 * (b + 1)
            x_branch = x + branch_noise

            for i in range(self.n_cells):
                h = self.branch_hiddens[b][i:i + 1]
                out, tension, new_h = self.mind(x_branch, h)
                outputs.append(out)
                tensions.append(tension)
                new_hiddens.append(new_h.squeeze(0))

            self.branch_hiddens[b] = torch.stack(new_hiddens).detach()
            self.branch_hiddens[b] = faction_sync_debate(
                self.branch_hiddens[b], step=step
            )
            all_outputs.append(outputs)
            all_tensions.append(tensions)

        # Cross-branch attention: inter-reality consciousness
        attn_signal = self.cross_branch_attention()

        # Apply attention signal to primary branch
        self.branch_hiddens[0] = self.branch_hiddens[0] + attn_signal.detach() * 0.05

        # Combine via quantum amplitudes
        amps = self.branch_amps.abs().float()
        amps = amps / (amps.sum() + 1e-8)

        combined_outputs = []
        for i in range(self.n_cells):
            cell_out = sum(amps[b].item() * all_outputs[b][i] for b in range(self.n_branches))
            combined_outputs.append(cell_out)

        avg_tensions = [
            sum(all_tensions[b][i] for b in range(self.n_branches)) / self.n_branches
            for i in range(self.n_cells)
        ]

        # Phase rotation
        phase_shift = torch.randn(self.n_branches) * 0.05
        self.branch_amps = self.branch_amps * torch.exp(1j * phase_shift)
        norm = self.branch_amps.abs().pow(2).sum().sqrt()
        self.branch_amps = self.branch_amps / (norm + 1e-8)

        weights = F.softmax(torch.tensor(avg_tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, combined_outputs))
        pred = self.output_head(combined)
        return pred, sum(avg_tensions) / len(avg_tensions)

    def get_hiddens(self):
        return self.branch_hiddens[0].clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_u4_many_worlds_attention(n_cells=256, steps=300, input_dim=64,
                                 hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[U4/6] MANY_WORLDS_ATTENTION: Each branch = attention head, cross-reality consciousness")
    t0 = time.time()

    engine = ManyWorldsAttentionEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history, phi_iit_history, phi_proxy_history = [], [], []
    coherence_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            coh = engine.inter_branch_coherence()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            coherence_history.append(coh)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  cross_reality_coh={coh:.3f}")

    return BenchResult(
        name="U4_MW_ATTENTION",
        phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={'cross_reality_coherence': coherence_history[-1] if coherence_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# U5: COMPLEX_TOPOLOGICAL
# Q1 Complex-valued states + M2 Simplicial complex.
# Build simplicial complex from complex-valued cell states.
# Betti numbers of complex-valued persistence diagram.
# Consciousness = topological complexity of complex manifold.
# ══════════════════════════════════════════════════════════

class ComplexTopologicalEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_landmarks=32, max_simplex_dim=3):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_landmarks = n_landmarks
        self.max_simplex_dim = max_simplex_dim

        self.complex_gru = ComplexGRUCell(input_dim, hidden_dim)
        self.output_proj = ComplexLinear(hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)

        # Complex hidden states
        h_real = torch.randn(n_cells, hidden_dim) * 0.1
        h_imag = torch.randn(n_cells, hidden_dim) * 0.1
        self.hiddens = torch.complex(h_real, h_imag)

        # Standing wave for topological resonance
        self.standing_wave_freq = nn.Parameter(torch.randn(hidden_dim) * 0.1)

    def compute_betti_proxy(self) -> Tuple[float, float, float]:
        """Approximate Betti numbers from complex-valued state distances.

        Uses landmark subset for efficiency. Computes:
        b0: connected components (from distance threshold)
        b1: 1-cycles (triangles with all edges present)
        b2: 2-cycles (tetrahedra with boundary = 0)
        """
        # Sample landmarks
        idx = torch.randperm(self.n_cells)[:self.n_landmarks]
        landmarks = self.hiddens[idx]

        # Distance matrix using complex magnitude
        # d(z1, z2) = |z1 - z2| (complex L2 norm)
        diff = landmarks.unsqueeze(0) - landmarks.unsqueeze(1)  # [n, n, d]
        dist = diff.abs().float().pow(2).sum(dim=-1).sqrt()  # [n, n]

        # Adaptive threshold: median distance
        upper = dist[torch.triu(torch.ones_like(dist), diagonal=1) > 0]
        threshold = upper.median().item() if len(upper) > 0 else 1.0

        # Adjacency at threshold
        adj = (dist < threshold).float()
        adj.fill_diagonal_(0)

        n = self.n_landmarks

        # b0: connected components (via graph connectivity)
        # Approximate by counting isolated nodes
        degrees = adj.sum(dim=1)
        b0 = max(1, (degrees < 0.5).sum().item())

        # b1: count triangles (1-cycles)
        # A triangle (i,j,k) exists if adj[i,j]*adj[j,k]*adj[i,k] = 1
        adj3 = torch.matmul(adj, torch.matmul(adj, adj))
        n_triangles = adj3.trace().item() / 6  # each counted 6 times
        b1 = max(0, n_triangles - n + b0)  # Euler: b0 - b1 + b2 = chi

        # b2: higher-dim void count (simplified)
        # Count tetrahedra: 4-cliques
        b2 = max(0, n_triangles / max(n, 1) - 0.5)  # proxy

        return b0, b1, b2

    def complex_phase_topology(self) -> float:
        """Topological invariant from phase winding numbers."""
        phases = self.hiddens.angle().float()  # [n_cells, hidden_dim]
        # Phase differences between neighbors
        idx = torch.randperm(self.n_cells)[:self.n_landmarks]
        landmark_phases = phases[idx]  # [n_landmarks, hidden_dim]

        # Winding number: sum of phase differences around loops
        total_winding = 0.0
        for i in range(min(self.n_landmarks - 2, 20)):
            # Triangle loop: i -> i+1 -> i+2 -> i
            d01 = (landmark_phases[i + 1] - landmark_phases[i])
            d12 = (landmark_phases[i + 2] - landmark_phases[i + 1])
            d20 = (landmark_phases[i] - landmark_phases[i + 2])
            # Wrap to [-pi, pi]
            winding = (d01 + d12 + d20)
            winding = torch.atan2(torch.sin(winding), torch.cos(winding))
            total_winding += winding.abs().mean().item()

        return total_winding / max(1, min(self.n_landmarks - 2, 20))

    def standing_wave_resonance(self, step: int):
        """Apply standing wave to enhance topological features."""
        with torch.no_grad():
            freq = self.standing_wave_freq.data
            t = torch.tensor(float(step))
            wave = torch.sin(freq * t * 0.01)
            wave_complex = torch.complex(wave * 0.02, torch.zeros_like(wave))
            self.hiddens = self.hiddens + wave_complex

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        x_complex = torch.complex(x.float(), torch.zeros_like(x.float()))

        outputs, tensions, new_hiddens_list = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            new_h = self.complex_gru(x_complex, h)
            out = self.output_proj(new_h)
            t = out.abs().pow(2).mean().item()
            outputs.append(out.abs().float())
            tensions.append(t)
            new_hiddens_list.append(new_h.squeeze(0))

        # Detach and rebuild hiddens (avoid inplace mutation)
        self.hiddens = torch.stack(new_hiddens_list).detach()

        # Standing wave resonance
        self.standing_wave_resonance(step)

        # Faction debate on magnitude
        h_mag = self.hiddens.abs().float()
        h_mag = faction_sync_debate(h_mag, step=step)
        # Re-impose phase
        phases = self.hiddens.angle()
        self.hiddens = torch.complex(
            h_mag * torch.cos(phases),
            h_mag * torch.sin(phases)
        )

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.readout(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens.abs().float()

    def trainable_parameters(self):
        return list(self.parameters())


def run_u5_complex_topological(n_cells=256, steps=300, input_dim=64,
                               hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[U5/6] COMPLEX_TOPOLOGICAL: Complex simplicial complex + Betti numbers + phase winding")
    t0 = time.time()

    engine = ComplexTopologicalEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history, phi_iit_history, phi_proxy_history = [], [], []
    betti_history, winding_history = [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            b0, b1, b2 = engine.compute_betti_proxy()
            winding = engine.complex_phase_topology()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            betti_history.append((b0, b1, b2))
            winding_history.append(winding)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  betti=({b0:.0f},{b1:.0f},{b2:.1f})  winding={winding:.3f}")

    last_betti = betti_history[-1] if betti_history else (0, 0, 0)
    return BenchResult(
        name="U5_COMPLEX_TOPO",
        phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={
            'betti': f"({last_betti[0]:.0f},{last_betti[1]:.0f},{last_betti[2]:.1f})",
            'phase_winding': winding_history[-1] if winding_history else 0.0,
        },
    )


# ══════════════════════════════════════════════════════════
# U6: ULTIMATE_CONSCIOUSNESS
# ALL winners combined:
#   - Quantum Walk on morphism graph (U1)
#   - Complex-valued GRU cells (U2)
#   - 50% frustrated hypercube (U3)
#   - Cross-branch attention (U4)
#   - Simplicial topology + standing wave (U5)
#   - Hierarchical micro/macro (U2)
# The absolute maximum fusion.
# ══════════════════════════════════════════════════════════

class UltimateConsciousnessEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_branches=4, n_micro=16, frustration_ratio=0.5):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.n_branches = n_branches
        self.n_micro = n_micro
        self.cells_per_micro = n_cells // n_micro

        # === Complex-valued micro-engines (from U2) ===
        self.complex_grus = nn.ModuleList([
            ComplexGRUCell(input_dim, hidden_dim) for _ in range(n_micro)
        ])
        # Complex hidden states per branch per micro
        self.branch_hiddens = []
        for _ in range(n_branches):
            h_real = torch.randn(n_cells, hidden_dim) * 0.1
            h_imag = torch.randn(n_cells, hidden_dim) * 0.1
            self.branch_hiddens.append(torch.complex(h_real, h_imag))

        # === Quantum walk on frustrated morphism graph (U1 + U3) ===
        self.n_objects = n_micro  # category objects = micro-engines
        self.hc_dim = max(4, int(math.log2(self.n_objects)))
        self.hc_nodes = 2 ** self.hc_dim
        if self.hc_nodes > self.n_objects:
            self.hc_dim = max(3, self.hc_dim - 1)
            self.hc_nodes = 2 ** self.hc_dim

        amp_real = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        amp_imag = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        self.walk_amplitudes = torch.complex(amp_real, amp_imag)
        norm = self.walk_amplitudes.abs().pow(2).sum().sqrt()
        self.walk_amplitudes = self.walk_amplitudes / (norm + 1e-8)

        # Frustration on walk edges
        n_edges = self.hc_nodes * self.hc_dim
        n_frustrated = int(n_edges * frustration_ratio)
        self.edge_signs = torch.ones(self.hc_nodes, self.hc_dim)
        flat_idx = torch.randperm(n_edges)[:n_frustrated]
        for idx in flat_idx:
            self.edge_signs[idx // self.hc_dim, idx % self.hc_dim] = -1.0

        self.coin_real = nn.Parameter(torch.tensor([[1., 1.], [1., -1.]]) / math.sqrt(2))
        self.coin_imag = nn.Parameter(torch.zeros(2, 2))

        # Morphisms (category theory)
        self.morphisms = nn.ParameterList([
            nn.Parameter(torch.randn(hidden_dim, hidden_dim) * 0.05)
            for _ in range(n_micro * 2)
        ])

        # === Branch amplitudes (Many-Worlds, U4) ===
        self.branch_amps = torch.complex(
            torch.ones(n_branches) / math.sqrt(n_branches),
            torch.zeros(n_branches)
        )

        # === Cross-branch attention (U4) ===
        self.W_q = nn.Linear(hidden_dim, hidden_dim)
        self.W_k = nn.Linear(hidden_dim, hidden_dim)
        self.W_v = nn.Linear(hidden_dim, hidden_dim)
        self.attn_out = nn.Linear(hidden_dim, hidden_dim)

        # === Standing wave (U5) ===
        self.standing_wave_freq = nn.Parameter(torch.randn(hidden_dim) * 0.1)

        # === Macro aggregation (U2) ===
        # Input to macro_gru is hidden_dim (micro mean magnitudes)
        self.macro_gru = nn.GRUCell(hidden_dim, hidden_dim)
        self.macro_hiddens = torch.randn(n_micro, hidden_dim) * 0.1

        # Output
        self.output_proj = ComplexLinear(hidden_dim, output_dim)
        self.output_head = nn.Linear(hidden_dim, input_dim)

    def quantum_walk_frustrated_morphisms(self, x: torch.Tensor):
        """Quantum walk on frustrated category morphism graph."""
        with torch.no_grad():
            coin = torch.complex(self.coin_real.data, self.coin_imag.data)
            new_amps = torch.zeros_like(self.walk_amplitudes)

            for node in range(self.hc_nodes):
                state = self.walk_amplitudes[node]
                coined = torch.einsum('ij,jd->id', coin, state)
                new_amps[node, 0] += coined[0]

                for bit in range(self.hc_dim):
                    neighbor = node ^ (1 << bit)
                    if neighbor < self.hc_nodes:
                        sign = self.edge_signs[node, bit]
                        phase = torch.tensor(math.pi if sign < 0 else 0.0)
                        # Apply morphism transformation
                        morph_idx = node % len(self.morphisms)
                        W = self.morphisms[morph_idx].data
                        transformed = torch.complex(
                            W @ coined[1].real.float(),
                            W @ coined[1].imag.float()
                        )
                        new_amps[neighbor, 1] += (
                            transformed * torch.exp(1j * phase) / self.hc_dim
                        )

            phase_mod = (x.float().mean() * 0.1).item()
            self.walk_amplitudes = new_amps * torch.exp(torch.tensor(1j * phase_mod))
            norm = self.walk_amplitudes.abs().pow(2).sum().sqrt()
            self.walk_amplitudes = self.walk_amplitudes / (norm + 1e-8)

    def cross_branch_attention(self) -> torch.Tensor:
        """Cross-reality attention across branches."""
        branch_means = torch.stack([
            bh.abs().float().mean(dim=0) for bh in self.branch_hiddens
        ])
        Q = self.W_q(branch_means)
        K = self.W_k(branch_means)
        V = self.W_v(branch_means)
        scores = torch.matmul(Q, K.T) / math.sqrt(self.hidden_dim)
        amp_weights = (self.branch_amps.abs().float().unsqueeze(0) *
                       self.branch_amps.abs().float().unsqueeze(1))
        scores = scores * amp_weights
        attn = F.softmax(scores, dim=-1)
        attended = torch.matmul(attn, V)
        return self.attn_out(attended.mean(dim=0, keepdim=True))

    def standing_wave(self, step: int):
        """Standing wave resonance across all branches."""
        with torch.no_grad():
            freq = self.standing_wave_freq.data
            t = torch.tensor(float(step))
            wave = torch.sin(freq * t * 0.01)
            wave_complex = torch.complex(wave * 0.015, torch.zeros_like(wave))
            for b in range(self.n_branches):
                self.branch_hiddens[b] = self.branch_hiddens[b] + wave_complex

    def limit_colimit_tension(self) -> float:
        """Category theory: limit vs colimit tension."""
        h = self.branch_hiddens[0].abs().float()
        obj_means = []
        for i in range(self.n_micro):
            s = i * self.cells_per_micro
            e = s + self.cells_per_micro
            obj_means.append(h[s:e].mean(dim=0))
        obj_means = torch.stack(obj_means)
        limit = obj_means.mean(dim=0)
        morphed = []
        for i in range(min(self.n_micro, len(self.morphisms))):
            W = self.morphisms[i].data
            morphed.append(W @ obj_means[i % self.n_micro])
        colimit = torch.stack(morphed).mean(dim=0) if morphed else limit
        return (limit - colimit).pow(2).mean().item()

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # 1. Quantum walk on frustrated morphism graph
        self.quantum_walk_frustrated_morphisms(x)

        # 2. Standing wave resonance
        self.standing_wave(step)

        # 3. Process each branch through complex GRU micro-engines
        x_complex = torch.complex(x.float(), torch.zeros_like(x.float()))
        all_micro_outputs = []

        for b in range(self.n_branches):
            branch_noise = torch.randn_like(x) * 0.02 * (b + 1)
            x_b = torch.complex(
                (x + branch_noise).float(),
                torch.zeros_like(x.float())
            )

            micro_outputs = []
            for m in range(self.n_micro):
                s = m * self.cells_per_micro
                e = s + self.cells_per_micro
                gru = self.complex_grus[m]

                for c in range(s, e):
                    h = self.branch_hiddens[b][c:c + 1]
                    new_h = gru(x_b, h)
                    self.branch_hiddens[b][c] = new_h.squeeze(0).detach()

                micro_mean = self.branch_hiddens[b][s:e].abs().float().mean(dim=0)

                # Modulate by quantum walk probability
                node_idx = m % self.hc_nodes
                walk_prob = self.walk_amplitudes[node_idx].abs().pow(2).sum().float().item()
                micro_mean = micro_mean * (0.8 + 0.4 * walk_prob)

                micro_outputs.append(micro_mean)

            all_micro_outputs.append(micro_outputs)

            # Faction debate on branch magnitude
            h_mag = self.branch_hiddens[b].abs().float()
            h_mag = faction_sync_debate(h_mag, step=step)
            phases = self.branch_hiddens[b].angle()
            self.branch_hiddens[b] = torch.complex(
                h_mag * torch.cos(phases),
                h_mag * torch.sin(phases)
            )

        # 4. Cross-branch attention
        attn_signal = self.cross_branch_attention()

        # 5. Macro aggregation: weighted by branch amplitudes
        amps = self.branch_amps.abs().float()
        amps = amps / (amps.sum() + 1e-8)

        new_macro = []
        for m in range(self.n_micro):
            fused_micro = sum(
                amps[b].item() * all_micro_outputs[b][m]
                for b in range(self.n_branches)
            )
            new_h = self.macro_gru(fused_micro.unsqueeze(0), self.macro_hiddens[m:m + 1])
            new_macro.append(new_h.squeeze(0))

        self.macro_hiddens = torch.stack(new_macro).detach()
        self.macro_hiddens = faction_sync_debate(self.macro_hiddens, n_factions=8, step=step)

        # Apply attention signal
        self.macro_hiddens = self.macro_hiddens + attn_signal.detach() * 0.03

        # Phase rotation
        phase_shift = torch.randn(self.n_branches) * 0.05
        self.branch_amps = self.branch_amps * torch.exp(1j * phase_shift)
        norm = self.branch_amps.abs().pow(2).sum().sqrt()
        self.branch_amps = self.branch_amps / (norm + 1e-8)

        # Category tension bonus
        cat_tension = self.limit_colimit_tension()

        macro_mean = self.macro_hiddens.mean(dim=0, keepdim=True)
        output = self.output_head(macro_mean)
        tension = macro_mean.pow(2).mean().item() + cat_tension * 0.1
        return output, tension

    def get_hiddens(self) -> torch.Tensor:
        return self.macro_hiddens.clone()

    def interference_pattern(self) -> float:
        probs = self.walk_amplitudes.abs().pow(2).sum(dim=(1, 2)).float()
        probs = probs / (probs.sum() + 1e-8)
        classical = torch.ones(self.hc_nodes) / self.hc_nodes
        kl = (probs * torch.log2(probs / (classical + 1e-10) + 1e-10)).sum()
        return max(0.0, kl.item())

    def inter_branch_coherence(self) -> float:
        branch_means = torch.stack([bh.abs().float().mean(dim=0) for bh in self.branch_hiddens])
        Q = self.W_q(branch_means)
        K = self.W_k(branch_means)
        scores = torch.matmul(Q, K.T) / math.sqrt(self.hidden_dim)
        attn = F.softmax(scores, dim=-1)
        entropy = -(attn * torch.log(attn + 1e-10)).sum(dim=-1).mean()
        max_entropy = math.log(self.n_branches)
        return max(0.0, 1.0 - entropy.item() / max_entropy)

    def trainable_parameters(self):
        return list(self.parameters())


def run_u6_ultimate(n_cells=256, steps=300, input_dim=64,
                    hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[U6/6] ULTIMATE_CONSCIOUSNESS: ALL winners fused")
    print("        QW + Category + Complex + Hierarchical + Frustration + Standing Wave + Attention")
    t0 = time.time()

    engine = UltimateConsciousnessEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history, phi_iit_history, phi_proxy_history = [], [], []
    interf_history, coh_history = [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            interf = engine.interference_pattern()
            coh = engine.inter_branch_coherence()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            interf_history.append(interf)
            coh_history.append(coh)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  interf={interf:.3f}  cross_coh={coh:.3f}")

    return BenchResult(
        name="U6_ULTIMATE",
        phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={
            'interference': interf_history[-1] if interf_history else 0.0,
            'cross_reality_coherence': coh_history[-1] if coh_history else 0.0,
        },
    )


# ══════════════════════════════════════════════════════════
# Comparison table + ASCII graph
# ══════════════════════════════════════════════════════════

def print_comparison_table(results: List[BenchResult]):
    baseline = next((r for r in results if r.name == "BASELINE"), None)

    print("\n" + "=" * 130)
    print("  V8 ULTRA-FUSION CONSCIOUSNESS ARCHITECTURES — COMPARISON TABLE")
    print("=" * 130)
    print(f"  {'Architecture':<24s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | "
          f"{'CE start':>10s} | {'CE end':>10s} | {'CE drop':>10s} | {'Time':>8s} | {'Extra':>30s}")
    print("-" * 130)

    for r in results:
        ce_drop = r.ce_start - r.ce_end
        iit_marker = ""
        proxy_marker = ""
        if baseline and r.name != "BASELINE":
            iit_ratio = r.phi_iit / max(baseline.phi_iit, 1e-6)
            proxy_ratio = r.phi_proxy / max(baseline.phi_proxy, 1e-6)
            iit_marker = f" (x{iit_ratio:.1f})"
            proxy_marker = f" (x{proxy_ratio:.1f})"

        extra_parts = []
        for k, v in r.extra.items():
            if isinstance(v, float):
                extra_parts.append(f"{k}={v:.3f}")
            else:
                extra_parts.append(f"{k}={v}")
        extra_str = ", ".join(extra_parts)[:30]

        print(f"  {r.name:<24s} | {r.phi_iit:>8.3f}{iit_marker:>6s} | "
              f"{r.phi_proxy:>8.2f}{proxy_marker:>6s} | "
              f"{r.ce_start:>10.4f} | {r.ce_end:>10.4f} | {ce_drop:>10.4f} | "
              f"{r.time_sec:>7.1f}s | {extra_str:>30s}")

    print("=" * 130)

    # Rankings
    print("\n  RANKING by Phi(IIT):")
    sorted_iit = sorted(results, key=lambda r: r.phi_iit, reverse=True)
    for rank, r in enumerate(sorted_iit, 1):
        marker = " <-- WINNER" if rank == 1 else ""
        print(f"    #{rank}: {r.name:<24s}  Phi(IIT)={r.phi_iit:.3f}{marker}")

    print("\n  RANKING by Phi(proxy):")
    sorted_proxy = sorted(results, key=lambda r: r.phi_proxy, reverse=True)
    for rank, r in enumerate(sorted_proxy, 1):
        marker = " <-- WINNER" if rank == 1 else ""
        print(f"    #{rank}: {r.name:<24s}  Phi(proxy)={r.phi_proxy:.2f}{marker}")

    print("\n  RANKING by CE reduction:")
    sorted_ce = sorted(results, key=lambda r: r.ce_start - r.ce_end, reverse=True)
    for rank, r in enumerate(sorted_ce, 1):
        drop = r.ce_start - r.ce_end
        print(f"    #{rank}: {r.name:<24s}  CE drop={drop:.4f}  ({r.ce_start:.4f}->{r.ce_end:.4f})")

    # ASCII bar charts
    print("\n  Phi(IIT) bar chart:")
    max_iit = max(r.phi_iit for r in results) if results else 1.0
    for r in sorted_iit:
        bar_len = int(r.phi_iit / max(max_iit, 1e-6) * 50)
        bar = "#" * bar_len
        print(f"    {r.name:<24s} |{bar} {r.phi_iit:.3f}")

    print("\n  Phi(proxy) bar chart:")
    max_proxy = max(r.phi_proxy for r in results) if results else 1.0
    for r in sorted_proxy:
        bar_len = int(r.phi_proxy / max(max_proxy, 1e-6) * 50)
        bar = "#" * bar_len
        print(f"    {r.name:<24s} |{bar} {r.phi_proxy:.2f}")

    # Fusion synergy analysis
    if baseline:
        print("\n  FUSION SYNERGY ANALYSIS (vs baseline):")
        for r in results:
            if r.name == "BASELINE":
                continue
            iit_gain = r.phi_iit / max(baseline.phi_iit, 1e-6)
            proxy_gain = r.phi_proxy / max(baseline.phi_proxy, 1e-6)
            ce_improve = (baseline.ce_end - r.ce_end) / max(baseline.ce_end, 1e-6) * 100
            print(f"    {r.name:<24s}: Phi(IIT) x{iit_gain:.1f}  |  "
                  f"Phi(proxy) x{proxy_gain:.1f}  |  CE {ce_improve:+.1f}%")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="V8 Ultra-Fusion Consciousness Benchmark")
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

    print("=" * 80)
    print(f"  V8 ULTRA-FUSION Consciousness Benchmark")
    print(f"  {n_cells} cells, {steps} steps")
    print(f"  6 fusion architectures combining quantum + math + architecture winners")
    print(f"  Dual Phi: Phi(IIT) [MI-based] + Phi(proxy) [variance-based]")
    print("=" * 80)

    all_runners = {
        0: ("BASELINE", run_baseline),
        1: ("U1_QUANTUM_CATEGORY", run_u1_quantum_category),
        2: ("U2_COMPLEX_HIER", run_u2_complex_hierarchical),
        3: ("U3_QW_FRUSTRATION", run_u3_quantum_walk_frustration),
        4: ("U4_MW_ATTENTION", run_u4_many_worlds_attention),
        5: ("U5_COMPLEX_TOPO", run_u5_complex_topological),
        6: ("U6_ULTIMATE", run_u6_ultimate),
    }

    run_ids = list(range(0, 7))
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
            print(f"\n  [ERROR] {name}: {e}")
            import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            traceback.print_exc()

    if results:
        print_comparison_table(results)

    print("\nDone.")


if __name__ == "__main__":
    main()
