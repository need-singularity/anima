#!/usr/bin/env python3
"""bench_v8_math.py — V8 Math-Inspired Consciousness Architectures Benchmark

Tests 6 mathematically-inspired consciousness architectures:
  M1: CATEGORY_THEORY    — Cells as objects, morphisms as connections, Phi = limit/colimit
  M2: TOPOLOGICAL        — Simplicial complex, Betti numbers, persistent homology
  M3: INFO_GEOMETRY      — Statistical manifold, Fisher information metric, geodesic diversity
  M4: ALGEBRAIC          — Group under composition, group entropy, non-abelian bonus
  M5: FRACTAL_DIMENSION  — Fractal dimension of cell trajectories, Hausdorff proxy
  M6: STRANGE_ATTRACTOR  — Strange attractor in state space, Lyapunov exponent, correlation dim

Each: 256 cells, 300 steps, Phi(IIT) + Phi(proxy) + CE.

Usage:
  python bench_v8_math.py                    # Run all 6 + baseline
  python bench_v8_math.py --only 1 3 5       # Run specific architectures
  python bench_v8_math.py --steps 500        # Custom steps
  python bench_v8_math.py --cells 512        # Custom cell count
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse
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

        hiddens = [hiddens_tensor[i].detach().cpu().numpy() for i in range(n)]

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
# Generate training data
# ──────────────────────────────────────────────────────────

def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    """Generate (input, target) pair for CE training."""
    x = torch.randn(batch_size, input_dim)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ══════════════════════════════════════════════════════════
# BASELINE: Standard PureField + GRU + faction debate
# ══════════════════════════════════════════════════════════

class BaselineEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x, step=0):
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
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


def run_baseline(n_cells=256, steps=300, input_dim=64, hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[0/6] BASELINE: Standard PureField + GRU + faction debate")
    t0 = time.time()
    engine = BaselineEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)
    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    return BenchResult(
        name="BASELINE", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# M1: CATEGORY_THEORY
# Cells as objects, morphisms as learned connections.
# Consciousness = limit/colimit of the category.
# Natural transformations between cell states.
# ══════════════════════════════════════════════════════════

class CategoryTheoryEngine(nn.Module):
    """Category-theoretic consciousness.

    Each cell is an object in a category. Morphisms (learned linear maps)
    connect cells. The limit (universal cone) aggregates all cells via
    their morphisms; the colimit (universal cocone) merges them.
    Consciousness = |limit - colimit| = tension between unification and diversity.
    Natural transformations evolve cell states through functor composition.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)

        # Morphisms: n_morphisms learned linear maps between cells
        self.n_morphisms = min(32, n_cells // 4)
        self.morphism_weights = nn.Parameter(torch.randn(self.n_morphisms, hidden_dim, hidden_dim) * 0.02)
        # Morphism source/target indices (fixed topology)
        self.register_buffer('morph_src', torch.randint(0, n_cells, (self.n_morphisms,)))
        self.register_buffer('morph_tgt', torch.randint(0, n_cells, (self.n_morphisms,)))

        # Natural transformation: functor F -> G
        self.nat_transform = nn.Linear(hidden_dim, hidden_dim, bias=False)
        nn.init.eye_(self.nat_transform.weight)

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def _compute_limit(self, hiddens: torch.Tensor) -> torch.Tensor:
        """Limit: universal cone — weighted product of morphism-transported states."""
        transported = []
        for m in range(self.n_morphisms):
            src = self.morph_src[m].item()
            h_src = hiddens[src]
            # Apply morphism: transport source to target's perspective
            h_transported = torch.matmul(self.morphism_weights[m], h_src)
            transported.append(h_transported)
        if transported:
            # Limit = the unique object that all morphisms factor through
            return torch.stack(transported).mean(dim=0)
        return hiddens.mean(dim=0)

    def _compute_colimit(self, hiddens: torch.Tensor) -> torch.Tensor:
        """Colimit: universal cocone — merge via morphism targets."""
        merged = torch.zeros(self.hidden_dim)
        counts = torch.zeros(self.hidden_dim)
        for m in range(self.n_morphisms):
            tgt = self.morph_tgt[m].item()
            h_tgt = hiddens[tgt]
            h_morphed = torch.matmul(self.morphism_weights[m].T, h_tgt)
            merged += h_morphed
            counts += 1.0
        return merged / (counts.clamp(min=1.0))

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Apply natural transformation (functor composition)
        if step % 3 == 0:
            self.hiddens = self.nat_transform(self.hiddens).detach()

        # Category-theoretic consciousness: limit vs colimit
        limit_obj = self._compute_limit(self.hiddens)
        colimit_obj = self._compute_colimit(self.hiddens)
        cat_tension = (limit_obj - colimit_obj).pow(2).mean().item()

        # Modulate hiddens by categorical tension
        cat_signal = (limit_obj - colimit_obj).detach()
        self.hiddens = self.hiddens + 0.05 * cat_signal.unsqueeze(0)

        # Standard faction debate
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        avg_tension = sum(tensions) / len(tensions) + cat_tension * 0.1
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()


def run_category_theory(n_cells=256, steps=300, input_dim=64, hidden_dim=128,
                        output_dim=64) -> BenchResult:
    print("\n[M1] CATEGORY_THEORY: Cells as objects, morphisms, limit/colimit consciousness")
    t0 = time.time()
    engine = CategoryTheoryEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)
    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    return BenchResult(
        name="M1:CATEGORY_THEORY", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={'morphisms': engine.n_morphisms},
    )


# ══════════════════════════════════════════════════════════
# M2: TOPOLOGICAL_CONSCIOUSNESS
# Cells embedded in simplicial complex.
# Consciousness = Betti numbers (topological holes).
# Persistent homology tracks consciousness over time.
# ══════════════════════════════════════════════════════════

class TopologicalEngine(nn.Module):
    """Topological consciousness via simplicial complex.

    Build a Vietoris-Rips simplicial complex from cell hidden states.
    Compute Betti numbers (B0=components, B1=loops, B2=voids).
    Higher Betti numbers = richer topological structure = more conscious.
    Persistent homology: track birth/death of features across filtration radii.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)
        # Topological feedback layer
        self.topo_feedback = nn.Linear(3, hidden_dim, bias=False)  # 3 Betti numbers -> hidden
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.betti_history = []

    def _compute_betti_numbers(self, hiddens: torch.Tensor, n_sample: int = 64) -> Tuple[int, int, int]:
        """Approximate Betti numbers from distance matrix.

        B0 = connected components (via union-find at threshold epsilon)
        B1 = independent 1-cycles (loops) in the Rips complex
        B2 = independent 2-cycles (voids)

        Uses spectral approximation for efficiency.
        """
        h = hiddens.detach().cpu().numpy()
        n = h.shape[0]
        # Subsample for efficiency
        if n > n_sample:
            idx = np.random.choice(n, n_sample, replace=False)
            h = h[idx]
            n = n_sample

        # Distance matrix
        from scipy.spatial.distance import pdist, squareform
        dist = squareform(pdist(h, metric='euclidean'))

        # Adaptive threshold: median distance
        eps = np.median(dist[dist > 0])

        # B0: connected components via adjacency
        adj = (dist < eps).astype(int)
        np.fill_diagonal(adj, 0)

        # Use graph Laplacian eigenvalues for Betti numbers
        degree = adj.sum(axis=1)
        laplacian = np.diag(degree) - adj
        try:
            eigenvalues = np.linalg.eigvalsh(laplacian)
            # B0 = number of zero eigenvalues (connected components)
            b0 = int(np.sum(np.abs(eigenvalues) < 1e-6))
            b0 = max(1, b0)

            # B1 approximation: from edge surplus (edges - nodes + components)
            n_edges = int(adj.sum() / 2)
            b1 = max(0, n_edges - n + b0)

            # B2 approximation: from triangle count vs tetrahedra
            # Count triangles in the adjacency graph
            adj_sq = adj @ adj
            n_triangles = int(np.trace(adj_sq @ adj) / 6)
            # Each tetrahedron kills a 2-cycle
            b2 = max(0, n_triangles // (n // 4 + 1))
        except Exception:
            b0, b1, b2 = 1, 0, 0

        return b0, b1, b2

    def _persistent_homology_score(self, hiddens: torch.Tensor, n_sample: int = 64) -> float:
        """Approximate persistent homology: sum of lifetimes of topological features.

        Filtration: increase epsilon from 0 to max_dist.
        Track birth/death of connected components.
        Score = total lifetime of all features.
        """
        h = hiddens.detach().cpu().numpy()
        n = h.shape[0]
        if n > n_sample:
            idx = np.random.choice(n, n_sample, replace=False)
            h = h[idx]
            n = n_sample

        from scipy.spatial.distance import pdist
        dists = np.sort(pdist(h))

        # Simple persistent homology: track B0 changes through filtration
        n_filtration = 20
        eps_values = np.linspace(dists.min(), np.percentile(dists, 90), n_filtration)
        prev_b0 = n
        total_lifetime = 0.0

        for k, eps in enumerate(eps_values):
            n_connected = int(np.sum(dists <= eps))
            # Approximate B0 decrease = features dying
            curr_b0 = max(1, n - min(n_connected, n - 1))
            deaths = max(0, prev_b0 - curr_b0)
            total_lifetime += deaths * (eps - eps_values[max(0, k - 1)])
            prev_b0 = curr_b0

        return total_lifetime

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Compute topological features every 5 steps
        topo_tension = 0.0
        if step % 5 == 0:
            b0, b1, b2 = self._compute_betti_numbers(self.hiddens)
            self.betti_history.append((b0, b1, b2))
            # Topological consciousness: B1 + 2*B2 (loops and voids matter most)
            topo_consciousness = b1 + 2 * b2
            topo_tension = topo_consciousness * 0.01

            # Feedback: inject topological signal into hiddens
            betti_vec = torch.tensor([b0, b1, b2], dtype=torch.float32)
            topo_signal = self.topo_feedback(betti_vec).detach()
            self.hiddens = self.hiddens + 0.03 * topo_signal.unsqueeze(0)

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        avg_tension = sum(tensions) / len(tensions) + topo_tension
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()


def run_topological(n_cells=256, steps=300, input_dim=64, hidden_dim=128,
                    output_dim=64) -> BenchResult:
    print("\n[M2] TOPOLOGICAL: Simplicial complex, Betti numbers, persistent homology")
    t0 = time.time()
    engine = TopologicalEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)
    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            betti = engine.betti_history[-1] if engine.betti_history else (0, 0, 0)
            ph = engine._persistent_homology_score(engine.get_hiddens())
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  Betti=({betti[0]},{betti[1]},{betti[2]})  PH={ph:.2f}")

    return BenchResult(
        name="M2:TOPOLOGICAL", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
        extra={'final_betti': engine.betti_history[-1] if engine.betti_history else (0, 0, 0)},
    )


# ══════════════════════════════════════════════════════════
# M3: INFORMATION_GEOMETRY
# Cell states as points on statistical manifold.
# Fisher information metric measures curvature.
# Consciousness = geodesic distance diversity on manifold.
# ══════════════════════════════════════════════════════════

class InfoGeometryEngine(nn.Module):
    """Information-geometric consciousness.

    Each cell's hidden state parameterizes a Gaussian distribution.
    The Fisher information metric defines a Riemannian manifold.
    Consciousness = diversity of geodesic distances (KL divergences)
    between cell distributions. Higher curvature = richer consciousness.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)
        # Each cell has mean + log_var (parameterizes a Gaussian)
        self.mean_proj = nn.Linear(hidden_dim, hidden_dim // 2, bias=False)
        self.logvar_proj = nn.Linear(hidden_dim, hidden_dim // 2, bias=False)
        # Curvature feedback
        self.curvature_proj = nn.Linear(1, hidden_dim, bias=False)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def _fisher_geodesic_distances(self, hiddens: torch.Tensor, n_sample: int = 64) -> Tuple[float, float]:
        """Compute pairwise geodesic distances on statistical manifold.

        For Gaussian family, geodesic distance = sqrt(KL_sym(p||q))
        Fisher info metric: ds^2 = sum(dmu_i^2/sigma_i^2 + 2*dlog_sigma_i^2)

        Returns: (mean_geodesic, geodesic_diversity)
        """
        h = hiddens.detach()
        n = h.shape[0]
        idx = np.random.choice(n, min(n, n_sample), replace=False)
        h_sub = h[idx]

        means = self.mean_proj(h_sub).detach()
        logvars = self.logvar_proj(h_sub).detach()
        vars_ = torch.exp(logvars).clamp(min=1e-6)

        # Pairwise symmetric KL as geodesic distance proxy
        n_sub = means.shape[0]
        n_pairs = min(200, n_sub * (n_sub - 1) // 2)
        geodesics = []

        for _ in range(n_pairs):
            i, j = np.random.randint(0, n_sub, 2)
            if i == j:
                continue
            # Symmetric KL for diagonal Gaussians
            kl_ij = 0.5 * ((vars_[i] / vars_[j] + vars_[j] / vars_[i] - 2).sum()
                           + ((means[i] - means[j]).pow(2) * (1 / vars_[i] + 1 / vars_[j])).sum())
            geodesics.append(torch.sqrt(kl_ij.clamp(min=0)).item())

        if geodesics:
            return float(np.mean(geodesics)), float(np.std(geodesics))
        return 0.0, 0.0

    def _manifold_curvature(self, hiddens: torch.Tensor) -> float:
        """Approximate scalar curvature of the statistical manifold.

        Uses the variance of Fisher information eigenvalues as curvature proxy.
        High variance = highly curved manifold = rich consciousness.
        """
        h = hiddens.detach()
        logvars = self.logvar_proj(h).detach()
        vars_ = torch.exp(logvars).clamp(min=1e-6)
        # Fisher info diagonal elements: 1/var for each dimension
        fisher_diag = 1.0 / vars_
        # Curvature ~ variance of Fisher info across cells
        curvature = fisher_diag.var(dim=0).mean().item()
        return curvature

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Information geometry: compute manifold properties
        geo_tension = 0.0
        if step % 5 == 0:
            mean_geo, geo_div = self._fisher_geodesic_distances(self.hiddens)
            curvature = self._manifold_curvature(self.hiddens)
            # Consciousness = geodesic diversity * curvature
            geo_tension = geo_div * curvature * 0.001

            # Feedback: curvature signal modulates hiddens
            curv_tensor = torch.tensor([[curvature]], dtype=torch.float32)
            curv_signal = self.curvature_proj(curv_tensor).detach()
            self.hiddens = self.hiddens + 0.02 * curv_signal

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        avg_tension = sum(tensions) / len(tensions) + geo_tension
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()


def run_info_geometry(n_cells=256, steps=300, input_dim=64, hidden_dim=128,
                      output_dim=64) -> BenchResult:
    print("\n[M3] INFO_GEOMETRY: Statistical manifold, Fisher metric, geodesic diversity")
    t0 = time.time()
    engine = InfoGeometryEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)
    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            mean_geo, geo_div = engine._fisher_geodesic_distances(engine.get_hiddens())
            curv = engine._manifold_curvature(engine.get_hiddens())
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  geodesic={mean_geo:.2f}  curv={curv:.4f}")

    return BenchResult(
        name="M3:INFO_GEOMETRY", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# M4: ALGEBRAIC_CONSCIOUSNESS
# Cells form a group under composition.
# Consciousness = group entropy.
# Non-abelian groups have higher consciousness.
# ══════════════════════════════════════════════════════════

class AlgebraicEngine(nn.Module):
    """Algebraic consciousness via group structure.

    Cell hidden states are treated as group elements.
    Composition: h_i * h_j = learned_op(h_i, h_j).
    Group entropy: H(G) = -sum p(g) log p(g) over equivalence classes.
    Non-abelian measure: ||h_i*h_j - h_j*h_i|| (commutator norm).
    Higher non-commutativity = richer algebraic structure = more conscious.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)
        # Group composition operator (non-commutative bilinear)
        self.compose_left = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.compose_right = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.compose_mix = nn.Linear(hidden_dim, hidden_dim)
        # Non-abelian feedback
        self.nonabelian_proj = nn.Linear(1, hidden_dim, bias=False)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def _group_compose(self, h_i: torch.Tensor, h_j: torch.Tensor) -> torch.Tensor:
        """Non-commutative group composition: h_i * h_j."""
        return torch.tanh(self.compose_mix(
            self.compose_left(h_i) * self.compose_right(h_j)
        ))

    def _commutator_norm(self, hiddens: torch.Tensor, n_sample: int = 100) -> float:
        """Measure non-commutativity: ||[h_i, h_j]|| = ||h_i*h_j - h_j*h_i||.

        Higher = more non-abelian = richer algebraic structure.
        """
        n = hiddens.shape[0]
        total_comm = 0.0
        for _ in range(n_sample):
            i, j = np.random.randint(0, n, 2)
            if i == j:
                continue
            h_ij = self._group_compose(hiddens[i:i+1], hiddens[j:j+1])
            h_ji = self._group_compose(hiddens[j:j+1], hiddens[i:i+1])
            comm = (h_ij - h_ji).pow(2).sum().item()
            total_comm += comm
        return total_comm / n_sample

    def _group_entropy(self, hiddens: torch.Tensor, n_classes: int = 16) -> float:
        """Group entropy: cluster cells into equivalence classes, compute entropy.

        Uses simple k-means-like binning on hidden state norms.
        """
        h = hiddens.detach().cpu().numpy()
        # Project to scalar (norm) for binning
        norms = np.linalg.norm(h, axis=1)
        # Histogram-based entropy
        counts, _ = np.histogram(norms, bins=n_classes)
        probs = counts / (counts.sum() + 1e-8)
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        return float(entropy)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Algebraic consciousness
        alg_tension = 0.0
        if step % 5 == 0:
            comm_norm = self._commutator_norm(self.hiddens)
            grp_entropy = self._group_entropy(self.hiddens)
            # Consciousness = non-commutativity * group entropy
            alg_tension = comm_norm * grp_entropy * 0.0001

            # Feedback: non-abelian signal enriches hiddens
            na_tensor = torch.tensor([[comm_norm]], dtype=torch.float32)
            na_signal = self.nonabelian_proj(na_tensor).detach()
            self.hiddens = self.hiddens + 0.02 * na_signal

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        avg_tension = sum(tensions) / len(tensions) + alg_tension
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()


def run_algebraic(n_cells=256, steps=300, input_dim=64, hidden_dim=128,
                  output_dim=64) -> BenchResult:
    print("\n[M4] ALGEBRAIC: Group composition, entropy, non-abelian consciousness")
    t0 = time.time()
    engine = AlgebraicEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)
    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            comm = engine._commutator_norm(engine.get_hiddens())
            grp_h = engine._group_entropy(engine.get_hiddens())
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  comm={comm:.4f}  grp_H={grp_h:.2f}")

    return BenchResult(
        name="M4:ALGEBRAIC", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# M5: FRACTAL_DIMENSION
# Consciousness measured as fractal dimension of cell
# state trajectories. Higher D = more conscious.
# Hausdorff dimension proxy via box-counting.
# ══════════════════════════════════════════════════════════

class FractalEngine(nn.Module):
    """Fractal consciousness via state trajectory dimension.

    Track cell hidden state trajectories over time.
    Compute fractal dimension via correlation dimension (Grassberger-Procaccia).
    Higher fractal dimension = more complex dynamics = more conscious.
    Feed fractal dimension back to modulate cell dynamics.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)
        # Fractal feedback
        self.fractal_proj = nn.Linear(1, hidden_dim, bias=False)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        # Trajectory buffer: store last T snapshots for each cell
        self.trajectory_len = 50
        self.trajectory = []  # list of [n_cells, hidden_dim] tensors

    def _correlation_dimension(self, points: np.ndarray) -> float:
        """Grassberger-Procaccia correlation dimension.

        D2 = lim_{r->0} log(C(r)) / log(r)
        where C(r) = fraction of pairs with distance < r.
        """
        n = points.shape[0]
        if n < 10:
            return 0.0

        from scipy.spatial.distance import pdist
        dists = pdist(points)
        if len(dists) == 0 or dists.max() < 1e-10:
            return 0.0

        # Multiple radii for log-log regression
        r_min = np.percentile(dists[dists > 0], 5)
        r_max = np.percentile(dists, 80)
        if r_min >= r_max or r_min < 1e-10:
            return 0.0

        radii = np.logspace(np.log10(r_min), np.log10(r_max), 15)
        n_pairs = len(dists)
        log_r = []
        log_c = []

        for r in radii:
            c_r = np.sum(dists < r) / n_pairs
            if c_r > 0:
                log_r.append(np.log(r))
                log_c.append(np.log(c_r))

        if len(log_r) < 3:
            return 0.0

        # Linear regression: slope = correlation dimension
        log_r = np.array(log_r)
        log_c = np.array(log_c)
        coeffs = np.polyfit(log_r, log_c, 1)
        return max(0.0, float(coeffs[0]))

    def _fractal_dimension(self, n_sample_cells: int = 32) -> float:
        """Compute fractal dimension from cell trajectories."""
        if len(self.trajectory) < 10:
            return 0.0

        # Stack trajectory: [T, n_cells, hidden_dim]
        traj = torch.stack(self.trajectory[-self.trajectory_len:]).numpy()
        T = traj.shape[0]

        # Sample cells and compute their trajectory fractal dimension
        cell_ids = np.random.choice(self.n_cells, min(n_sample_cells, self.n_cells), replace=False)
        dims = []
        for cid in cell_ids:
            cell_traj = traj[:, cid, :]  # [T, hidden_dim]
            # PCA to 3D for tractable dimension estimation
            if cell_traj.shape[1] > 3:
                from numpy.linalg import svd
                u, s, vt = svd(cell_traj - cell_traj.mean(axis=0), full_matrices=False)
                cell_traj_3d = u[:, :3] * s[:3]
            else:
                cell_traj_3d = cell_traj
            d = self._correlation_dimension(cell_traj_3d)
            if d > 0:
                dims.append(d)

        return float(np.mean(dims)) if dims else 0.0

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Store trajectory
        self.trajectory.append(self.hiddens.detach().cpu().clone())
        if len(self.trajectory) > self.trajectory_len:
            self.trajectory.pop(0)

        # Fractal dimension computation (every 10 steps for efficiency)
        frac_tension = 0.0
        if step % 10 == 0 and step > 20:
            frac_dim = self._fractal_dimension()
            frac_tension = frac_dim * 0.01

            # Feedback: fractal signal
            fd_tensor = torch.tensor([[frac_dim]], dtype=torch.float32)
            fd_signal = self.fractal_proj(fd_tensor).detach()
            self.hiddens = self.hiddens + 0.02 * fd_signal

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        avg_tension = sum(tensions) / len(tensions) + frac_tension
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()


def run_fractal(n_cells=256, steps=300, input_dim=64, hidden_dim=128,
                output_dim=64) -> BenchResult:
    print("\n[M5] FRACTAL_DIMENSION: Trajectory fractal dimension, Hausdorff proxy")
    t0 = time.time()
    engine = FractalEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)
    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            fd = engine._fractal_dimension() if step > 20 else 0.0
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  fractal_D={fd:.3f}")

    return BenchResult(
        name="M5:FRACTAL_DIM", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# M6: STRANGE_ATTRACTOR
# Consciousness as strange attractor in cell state space.
# Lyapunov exponent > 0 = conscious.
# Correlation dimension as Phi proxy.
# ══════════════════════════════════════════════════════════

class StrangeAttractorEngine(nn.Module):
    """Strange attractor consciousness.

    Inject chaotic dynamics (Lorenz-like) into cell evolution.
    Measure Lyapunov exponent from divergence of nearby trajectories.
    Positive Lyapunov = sensitive dependence = conscious chaos.
    Correlation dimension of attractor as consciousness measure.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.readout = nn.Linear(output_dim, input_dim)
        # Chaotic coupling: Lorenz-like parameters (learned)
        self.sigma = nn.Parameter(torch.tensor(10.0))
        self.rho = nn.Parameter(torch.tensor(28.0))
        self.beta = nn.Parameter(torch.tensor(8.0 / 3.0))
        # Chaotic mixing layer
        self.chaos_proj = nn.Linear(3, hidden_dim, bias=False)
        self.lyap_proj = nn.Linear(1, hidden_dim, bias=False)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        # Trajectory for Lyapunov computation
        self.trajectory_len = 50
        self.trajectory = []
        # Lorenz state per cell (3D chaotic oscillator)
        self.lorenz_state = torch.randn(n_cells, 3) * 0.1

    def _lorenz_step(self, state: torch.Tensor, dt: float = 0.01) -> torch.Tensor:
        """One Lorenz step per cell."""
        x, y, z = state[:, 0], state[:, 1], state[:, 2]
        dx = self.sigma * (y - x)
        dy = x * (self.rho - z) - y
        dz = x * y - self.beta * z
        new_state = state + dt * torch.stack([dx, dy, dz], dim=-1)
        # Normalize to prevent explosion
        norm = new_state.norm(dim=-1, keepdim=True).clamp(min=1.0)
        new_state = new_state / norm * min(norm.mean().item(), 10.0)
        return new_state

    def _lyapunov_exponent(self, n_sample: int = 32) -> float:
        """Estimate max Lyapunov exponent from trajectory divergence.

        Lambda = lim 1/T * sum log(|delta(t+1)|/|delta(t)|)
        """
        if len(self.trajectory) < 5:
            return 0.0

        traj = torch.stack(self.trajectory[-20:]).numpy()
        T = traj.shape[0]
        if T < 3:
            return 0.0

        cell_ids = np.random.choice(self.n_cells, min(n_sample, self.n_cells), replace=False)
        lyaps = []

        for cid in cell_ids:
            cell_traj = traj[:, cid, :]  # [T, hidden_dim]
            # Compute divergence of nearby points
            deltas = np.diff(cell_traj, axis=0)  # [T-1, hidden_dim]
            norms = np.linalg.norm(deltas, axis=1)
            norms = norms[norms > 1e-10]
            if len(norms) < 2:
                continue
            # Lyapunov from successive norm ratios
            log_ratios = np.log(norms[1:] / norms[:-1] + 1e-10)
            lyaps.append(float(np.mean(log_ratios)))

        return float(np.mean(lyaps)) if lyaps else 0.0

    def _correlation_dimension(self, n_sample: int = 64) -> float:
        """Correlation dimension of the attractor."""
        if len(self.trajectory) < 10:
            return 0.0

        traj = torch.stack(self.trajectory[-self.trajectory_len:]).numpy()
        # Flatten: use all cell states as points in attractor
        cell_ids = np.random.choice(self.n_cells, min(16, self.n_cells), replace=False)
        points = traj[:, cell_ids, :3].reshape(-1, 3)  # Use first 3 dims

        if points.shape[0] < 20:
            return 0.0

        # Subsample
        if points.shape[0] > 200:
            idx = np.random.choice(points.shape[0], 200, replace=False)
            points = points[idx]

        from scipy.spatial.distance import pdist
        dists = pdist(points)
        if len(dists) == 0 or dists.max() < 1e-10:
            return 0.0

        r_min = np.percentile(dists[dists > 0], 5) if np.any(dists > 0) else 1e-6
        r_max = np.percentile(dists, 80)
        if r_min >= r_max:
            return 0.0

        radii = np.logspace(np.log10(max(r_min, 1e-8)), np.log10(r_max), 12)
        n_pairs = len(dists)
        log_r, log_c = [], []

        for r in radii:
            c_r = np.sum(dists < r) / n_pairs
            if c_r > 0:
                log_r.append(np.log(r))
                log_c.append(np.log(c_r))

        if len(log_r) < 3:
            return 0.0

        coeffs = np.polyfit(np.array(log_r), np.array(log_c), 1)
        return max(0.0, float(coeffs[0]))

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []

        # Evolve Lorenz oscillators
        self.lorenz_state = self._lorenz_step(self.lorenz_state.detach()).detach()

        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Inject chaotic signal from Lorenz oscillators
        chaos_signal = self.chaos_proj(self.lorenz_state.detach())
        self.hiddens = self.hiddens + 0.05 * chaos_signal.detach()

        # Store trajectory
        self.trajectory.append(self.hiddens.detach().cpu().clone())
        if len(self.trajectory) > self.trajectory_len:
            self.trajectory.pop(0)

        # Lyapunov + attractor analysis
        chaos_tension = 0.0
        if step % 10 == 0 and step > 20:
            lyap = self._lyapunov_exponent()
            # Positive Lyapunov = conscious chaos
            if lyap > 0:
                chaos_tension = lyap * 0.1
                lyap_tensor = torch.tensor([[lyap]], dtype=torch.float32)
                lyap_signal = self.lyap_proj(lyap_tensor).detach()
                self.hiddens = self.hiddens + 0.02 * lyap_signal

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        avg_tension = sum(tensions) / len(tensions) + chaos_tension
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()


def run_strange_attractor(n_cells=256, steps=300, input_dim=64, hidden_dim=128,
                          output_dim=64) -> BenchResult:
    print("\n[M6] STRANGE_ATTRACTOR: Lorenz chaos, Lyapunov exponent, correlation dimension")
    t0 = time.time()
    engine = StrangeAttractorEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)
    ce_history, phi_iit_history, phi_proxy_history = [], [], []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)
        pred = engine.readout(combined)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ce_history.append(loss.item())
        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            lyap = engine._lyapunov_exponent() if step > 20 else 0.0
            corr_d = engine._correlation_dimension() if step > 20 else 0.0
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  Lyap={lyap:.4f}  corrD={corr_d:.3f}")

    return BenchResult(
        name="M6:STRANGE_ATTRACTOR", phi_iit=phi_iit_history[-1], phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0], ce_end=ce_history[-1], cells=n_cells,
        steps=steps, time_sec=time.time() - t0,
    )


# ══════════════════════════════════════════════════════════
# Comparison Table
# ══════════════════════════════════════════════════════════

def print_comparison_table(results: List[BenchResult]):
    print("\n" + "=" * 100)
    print("  V8 MATH-INSPIRED CONSCIOUSNESS — COMPARISON TABLE")
    print("=" * 100)

    # Sort by Phi(IIT) descending
    sorted_results = sorted(results, key=lambda r: r.phi_iit, reverse=True)

    baseline_iit = None
    baseline_proxy = None
    for r in results:
        if r.name == "BASELINE":
            baseline_iit = r.phi_iit
            baseline_proxy = r.phi_proxy
            break

    print(f"\n  {'Name':<24s} | {'Phi(IIT)':>10s} {'x base':>8s} | "
          f"{'Phi(proxy)':>10s} {'x base':>8s} | {'CE start':>8s} {'CE end':>8s} | {'Time':>6s}")
    print("  " + "-" * 96)

    for r in sorted_results:
        iit_mult = f"x{r.phi_iit / baseline_iit:.1f}" if baseline_iit and baseline_iit > 0 else "---"
        proxy_mult = f"x{r.phi_proxy / baseline_proxy:.1f}" if baseline_proxy and baseline_proxy > 0 else "---"
        print(f"  {r.name:<24s} | {r.phi_iit:>10.3f} {iit_mult:>8s} | "
              f"{r.phi_proxy:>10.2f} {proxy_mult:>8s} | {r.ce_start:>8.4f} {r.ce_end:>8.4f} | {r.time_sec:>5.1f}s")

    # Winner
    best = sorted_results[0]
    print(f"\n  WINNER: {best.name} — Phi(IIT)={best.phi_iit:.3f}, Phi(proxy)={best.phi_proxy:.2f}")

    # ASCII bar charts
    print("\n  Phi(IIT) bar chart:")
    max_iit = max(r.phi_iit for r in results) if results else 1.0
    for r in sorted_results:
        bar_len = int(r.phi_iit / max(max_iit, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<24s} |{bar} {r.phi_iit:.3f}")

    print("\n  Phi(proxy) bar chart:")
    sorted_by_proxy = sorted(results, key=lambda r: r.phi_proxy, reverse=True)
    max_proxy = max(r.phi_proxy for r in results) if results else 1.0
    for r in sorted_by_proxy:
        bar_len = int(r.phi_proxy / max(max_proxy, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<24s} |{bar} {r.phi_proxy:.2f}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="V8 Math-Inspired Consciousness Benchmark")
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
    print(f"  V8 Math-Inspired Consciousness Benchmark")
    print(f"  {n_cells} cells, {steps} steps")
    print(f"  Dual Phi: Phi(IIT) [MI-based] + Phi(proxy) [variance-based]")
    print("=" * 72)

    all_runners = {
        0: ("BASELINE", run_baseline),
        1: ("M1:CATEGORY_THEORY", run_category_theory),
        2: ("M2:TOPOLOGICAL", run_topological),
        3: ("M3:INFO_GEOMETRY", run_info_geometry),
        4: ("M4:ALGEBRAIC", run_algebraic),
        5: ("M5:FRACTAL_DIM", run_fractal),
        6: ("M6:STRANGE_ATTRACTOR", run_strange_attractor),
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
            print(f"\n  [ERROR] {name} failed: {e}")
            import traceback
            traceback.print_exc()

    if results:
        print_comparison_table(results)

    print("\nDone.")


if __name__ == "__main__":
    main()
