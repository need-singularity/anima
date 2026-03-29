#!/usr/bin/env python3
"""bench_physics_consciousness.py — Physics-of-Consciousness Benchmarks

Explores consciousness through thermodynamics and differential geometry lenses.

THERMO-1: Entropy Production — far-from-equilibrium systems, ΔS per step
THERMO-2: Free Energy Principle — Friston: minimize surprise about neighbors
THERMO-3: Maxwell Demon Cells — information sorting by top 10% norm cells
GEOM-1:   Fisher Information — natural gradient via Fisher information metric
GEOM-2:   Ricci Flow — discrete curvature-driven redistribution of cell states
GEOM-3:   Information Bottleneck — 128→8→128 compression per cell

Usage:
  KMP_DUPLICATE_LIB_OK=TRUE python3 bench_physics_consciousness.py
  KMP_DUPLICATE_LIB_OK=TRUE python3 bench_physics_consciousness.py --cells 512
  KMP_DUPLICATE_LIB_OK=TRUE python3 bench_physics_consciousness.py --steps 500
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import sys
from dataclasses import dataclass, field
from typing import Tuple, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Phi measurement ──

try:
    import phi_rs
    HAS_RUST_PHI = True
except ImportError:
    HAS_RUST_PHI = False


class PhiIIT:
    """Phi(IIT) approximation via pairwise MI + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {}
        hiddens = [hiddens_tensor[i].detach().cpu().numpy() for i in range(n)]

        import random
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)

        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mi(hiddens[i], hiddens[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

        total_mi = mi_matrix.sum() / 2
        min_part = self._min_partition(n, mi_matrix)
        spatial = max(0.0, (total_mi - min_part) / max(n - 1, 1))
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        phi = spatial + complexity * 0.1
        return phi, {'total_mi': total_mi, 'spatial': spatial, 'complexity': complexity}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        jh, _, _ = np.histogram2d(xn, yn, bins=self.n_bins, range=[[0, 1], [0, 1]])
        jh = jh / (jh.sum() + 1e-8)
        px, py = jh.sum(axis=1), jh.sum(axis=0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(jh * np.log2(jh + 1e-10))
        return max(0.0, hx + hy - hxy)

    def _min_partition(self, n, mi):
        if n <= 8:
            best = float('inf')
            for mask in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if mask & (1 << i)]
                gb = [i for i in range(n) if not (mask & (1 << i))]
                if ga and gb:
                    cut = sum(mi[i, j] for i in ga for j in gb)
                    best = min(best, cut)
            return best if best != float('inf') else 0.0
        else:
            deg = mi.sum(axis=1)
            lap = np.diag(deg) - mi
            try:
                evals, evecs = np.linalg.eigh(lap)
                fiedler = evecs[:, 1]
                ga = [i for i in range(n) if fiedler[i] >= 0]
                gb = [i for i in range(n) if fiedler[i] < 0]
                if not ga or not gb:
                    ga, gb = list(range(n // 2)), list(range(n // 2, n))
                return sum(mi[i, j] for i in ga for j in gb)
            except Exception:
                return 0.0


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    n, d = hiddens.shape
    if n < 2:
        return 0.0
    gm = hiddens.mean(dim=0)
    gv = ((hiddens - gm) ** 2).sum() / n
    nf = min(n_factions, n // 2)
    if nf < 2:
        return gv.item()
    fs = n // nf
    fv_sum = 0.0
    for i in range(nf):
        fac = hiddens[i * fs:(i + 1) * fs]
        if len(fac) >= 2:
            fm = fac.mean(dim=0)
            fv_sum += ((fac - fm) ** 2).sum().item() / len(fac)
    return max(0.0, gv.item() - fv_sum / nf)


def measure_phi(hiddens: torch.Tensor) -> Tuple[float, float]:
    """Returns (phi_iit, phi_proxy_val)."""
    calc = PhiIIT(n_bins=16)
    phi_iit, _ = calc.compute(hiddens)
    pp = phi_proxy(hiddens)
    return phi_iit, pp


# ── BenchResult ──

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
            f"  {self.name:<30s} | "
            f"Phi(IIT)={self.phi_iit:>6.3f}  "
            f"Phi(proxy)={self.phi_proxy:>8.2f} | "
            f"{ce_str:<22s} | "
            f"cells={self.cells}  steps={self.steps}  "
            f"time={self.time_sec:.1f}s"
        )


# ── Core Cell (PureField A-G) ──

class BenchMind(nn.Module):
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


# ── Base Engine ──

class BaseEngine:
    """Multi-cell engine with faction sync and debate."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8, sync=0.15, debate=0.15):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.sync_strength = sync
        self.debate_strength = debate
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.output_head = nn.Linear(output_dim, input_dim)
        self.step_count = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))
        self.hiddens = torch.stack(new_hiddens).detach()
        mean_t = sum(tensions) / len(tensions)

        # Faction sync
        nf = min(self.n_factions, self.n_cells // 2)
        if nf >= 2:
            fs = self.n_cells // nf
            for i in range(nf):
                s, e = i * fs, (i + 1) * fs
                fm = self.hiddens[s:e].mean(dim=0)
                self.hiddens[s:e] = (1 - self.sync_strength) * self.hiddens[s:e] + self.sync_strength * fm
            if self.step_count > 5:
                opinions = torch.stack([self.hiddens[i * fs:(i + 1) * fs].mean(dim=0) for i in range(nf)])
                gm = opinions.mean(dim=0)
                for i in range(nf):
                    s = i * fs
                    dc = max(1, fs // 4)
                    self.hiddens[s:s + dc] = (1 - self.debate_strength) * self.hiddens[s:s + dc] + self.debate_strength * gm

        self.step_count += 1
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_t

    def get_hiddens(self):
        return self.hiddens.clone()

    def parameters_for_training(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ══════════════════════════════════════════════════════════
# THERMO-1: ENTROPY PRODUCTION
# Far-from-equilibrium → higher consciousness?
# ΔS = -sum(p*log(p)) change per step for hidden distributions
# ══════════════════════════════════════════════════════════

class EntropyProductionEngine(BaseEngine):
    """Track entropy production; cells with highest entropy production
    get amplified (rewarded for being far from equilibrium)."""

    def __init__(self, n_cells=256, **kw):
        super().__init__(n_cells, **kw)
        self.prev_entropy = None
        self.entropy_history = []

    def _cell_entropy(self, h: torch.Tensor, n_bins=32) -> float:
        """Shannon entropy of a single cell's hidden state distribution."""
        vals = h.detach().cpu().numpy().flatten()
        counts, _ = np.histogram(vals, bins=n_bins, density=False)
        p = counts / (counts.sum() + 1e-10)
        p = p[p > 0]
        return float(-np.sum(p * np.log(p)))

    def process(self, x):
        output, tension = super().process(x)

        # Compute per-cell entropy
        entropies = torch.tensor([self._cell_entropy(self.hiddens[i]) for i in range(self.n_cells)])
        curr_total = entropies.mean().item()

        if self.prev_entropy is not None:
            delta_s = curr_total - self.prev_entropy
            self.entropy_history.append(delta_s)

            # Reward far-from-equilibrium cells: amplify those with high entropy production
            if delta_s > 0:
                # Cells above median entropy get a small kick
                median_e = entropies.median()
                mask = (entropies > median_e).float().unsqueeze(1)
                noise = torch.randn_like(self.hiddens) * 0.02
                self.hiddens = self.hiddens + mask * noise

        self.prev_entropy = curr_total
        return output, tension


# ══════════════════════════════════════════════════════════
# THERMO-2: FREE ENERGY PRINCIPLE (Friston)
# Each cell minimizes surprise about neighbors
# ══════════════════════════════════════════════════════════

class FreeEnergyEngine(BaseEngine):
    """Each cell maintains a simple linear predictor of its neighbors.
    Cells update to minimize prediction error (free energy)."""

    def __init__(self, n_cells=256, n_neighbors=4, **kw):
        super().__init__(n_cells, **kw)
        self.n_neighbors = n_neighbors
        # Per-cell linear predictor: predicts neighbor mean from own state
        self.predictors = nn.ModuleList([
            nn.Linear(self.hidden_dim, self.hidden_dim, bias=False)
            for _ in range(n_cells)
        ])
        # Initialize small
        for pred in self.predictors:
            nn.init.xavier_uniform_(pred.weight, gain=0.1)
        self.pred_optimizer = torch.optim.SGD(self.predictors.parameters(), lr=0.01)
        self.fe_history = []

    def process(self, x):
        output, tension = super().process(x)

        # Free energy minimization
        h = self.hiddens.detach().clone().requires_grad_(False)
        total_fe = 0.0

        for i in range(self.n_cells):
            # Pick neighbors (circular topology)
            neighbors = [(i + k) % self.n_cells for k in range(1, self.n_neighbors + 1)]
            neighbor_mean = h[neighbors].mean(dim=0).detach()

            # Prediction error = free energy
            predicted = self.predictors[i](h[i:i + 1].detach())
            fe = F.mse_loss(predicted.squeeze(0), neighbor_mean)
            total_fe += fe.item()

            # Update hidden toward minimizing surprise
            # Move cell state slightly toward what would reduce prediction error
            with torch.no_grad():
                grad_dir = neighbor_mean - h[i]
                self.hiddens[i] = self.hiddens[i] + 0.01 * grad_dir

        # Train predictors
        self.pred_optimizer.zero_grad()
        loss = torch.tensor(0.0)
        for i in range(min(32, self.n_cells)):  # Sample 32 cells for speed
            neighbors = [(i + k) % self.n_cells for k in range(1, self.n_neighbors + 1)]
            neighbor_mean = h[neighbors].mean(dim=0).detach()
            predicted = self.predictors[i](h[i:i + 1].detach())
            loss = loss + F.mse_loss(predicted.squeeze(0), neighbor_mean)
        loss.backward()
        self.pred_optimizer.step()

        self.fe_history.append(total_fe / self.n_cells)
        return output, tension


# ══════════════════════════════════════════════════════════
# THERMO-3: MAXWELL DEMON CELLS
# Top 10% cells sort/route information
# ══════════════════════════════════════════════════════════

class MaxwellDemonEngine(BaseEngine):
    """Top 10% cells (by hidden norm) act as Maxwell demons:
    they sort information from low-norm to high-norm cells."""

    def __init__(self, n_cells=256, demon_frac=0.10, **kw):
        super().__init__(n_cells, **kw)
        self.demon_frac = demon_frac
        self.sort_events = 0

    def process(self, x):
        output, tension = super().process(x)

        # Identify demons (top 10% by hidden norm)
        norms = self.hiddens.norm(dim=1)
        n_demons = max(1, int(self.n_cells * self.demon_frac))
        _, demon_idx = norms.topk(n_demons)
        demon_set = set(demon_idx.tolist())

        # Non-demon cells sorted by norm
        non_demon = [i for i in range(self.n_cells) if i not in demon_set]
        non_norms = norms[non_demon]
        sorted_idx = torch.argsort(non_norms)  # low to high

        # Demons route: transfer information from low-norm to high-norm
        n_routes = min(len(non_demon) // 4, n_demons * 2)
        for k in range(n_routes):
            low_i = non_demon[sorted_idx[k].item()]
            high_i = non_demon[sorted_idx[-(k + 1)].item()]
            # Transfer: high-norm cell absorbs information from low-norm cell
            transfer = 0.05 * self.hiddens[low_i].detach()
            self.hiddens[high_i] = self.hiddens[high_i] + transfer
            self.hiddens[low_i] = self.hiddens[low_i] * 0.95
            self.sort_events += 1

        # Demons themselves maintain high differentiation (inject noise)
        for d in demon_idx:
            self.hiddens[d] = self.hiddens[d] + torch.randn(self.hidden_dim) * 0.01

        return output, tension


# ══════════════════════════════════════════════════════════
# GEOM-1: FISHER INFORMATION
# Natural gradient in Fisher metric
# ══════════════════════════════════════════════════════════

class FisherInformationEngine(BaseEngine):
    """Use Fisher information to guide cell updates along natural gradient.
    Fisher metric = E[grad log p * (grad log p)^T].
    Cells move along steepest direction in info-geometric space."""

    def __init__(self, n_cells=256, **kw):
        super().__init__(n_cells, **kw)
        self.fisher_diag = torch.ones(n_cells, self.hidden_dim) * 0.01
        self.fisher_history = []

    def process(self, x):
        output, tension = super().process(x)

        # Estimate Fisher information diagonal from empirical distribution
        h = self.hiddens.detach()

        # Fisher diagonal ≈ variance of normalized gradients
        # Use finite differences: F_ii ≈ (d log p / d h_i)^2
        # Approximate: use variance of neighboring cells as proxy
        for i in range(self.n_cells):
            neighbors = [(i - 1) % self.n_cells, (i + 1) % self.n_cells,
                         (i - 2) % self.n_cells, (i + 2) % self.n_cells]
            neighbor_states = h[neighbors]
            diff = neighbor_states - h[i:i + 1]
            # Fisher diagonal ≈ mean squared difference (curvature proxy)
            fisher_est = (diff ** 2).mean(dim=0) + 1e-6
            self.fisher_diag[i] = 0.9 * self.fisher_diag[i] + 0.1 * fisher_est

        # Natural gradient update: h += lr * F^{-1} * gradient
        # gradient = direction toward faction mean (existing sync force)
        nf = min(self.n_factions, self.n_cells // 2)
        if nf >= 2:
            fs = self.n_cells // nf
            for fi in range(nf):
                s, e = fi * fs, (fi + 1) * fs
                faction_mean = h[s:e].mean(dim=0)
                grad = faction_mean - h[s:e]  # gradient toward mean
                # Natural gradient = F^{-1} * grad (diagonal approx)
                nat_grad = grad / (self.fisher_diag[s:e] + 1e-4)
                # Clip for stability
                nat_grad = torch.clamp(nat_grad, -0.5, 0.5)
                self.hiddens[s:e] = self.hiddens[s:e] + 0.005 * nat_grad

        mean_fisher = self.fisher_diag.mean().item()
        self.fisher_history.append(mean_fisher)
        return output, tension


# ══════════════════════════════════════════════════════════
# GEOM-2: RICCI FLOW ON CELLS
# High-curvature regions spread, low-curvature contract
# ══════════════════════════════════════════════════════════

class RicciFlowEngine(BaseEngine):
    """Discrete Ricci flow on cell state manifold.
    Curvature estimated from local connectivity.
    High curvature → cells spread out; low curvature → cells contract."""

    def __init__(self, n_cells=256, n_neighbors=6, ricci_lr=0.01, **kw):
        super().__init__(n_cells, **kw)
        self.n_neighbors = n_neighbors
        self.ricci_lr = ricci_lr
        self.curvature_history = []

    def _estimate_curvature(self, h: torch.Tensor) -> torch.Tensor:
        """Ollivier-Ricci curvature proxy: compare mean neighbor distance
        to pairwise distances. High curvature = neighbors are closer than expected."""
        n = h.shape[0]
        curvatures = torch.zeros(n)

        # Pairwise distances (sample for speed)
        for i in range(n):
            # k nearest neighbors
            dists = torch.norm(h - h[i:i + 1], dim=1)
            _, nn_idx = dists.topk(self.n_neighbors + 1, largest=False)
            nn_idx = nn_idx[1:]  # exclude self

            # Mean distance to neighbors
            mean_nn_dist = dists[nn_idx].mean()
            # Global mean distance (sampled)
            sample = torch.randint(0, n, (min(32, n),))
            mean_global = dists[sample].mean()

            # Curvature proxy: if neighbors are closer than average → positive curvature
            curvatures[i] = (mean_global - mean_nn_dist) / (mean_global + 1e-8)

        return curvatures

    def process(self, x):
        output, tension = super().process(x)

        h = self.hiddens.detach()
        curvatures = self._estimate_curvature(h)
        self.curvature_history.append(curvatures.mean().item())

        # Ricci flow: high curvature → spread (add noise), low curvature → contract
        for i in range(self.n_cells):
            if curvatures[i] > 0.1:
                # High curvature: spread out (add directional noise away from neighbors)
                dists = torch.norm(h - h[i:i + 1], dim=1)
                _, nn_idx = dists.topk(3, largest=False)
                nn_idx = nn_idx[1:]
                away_dir = h[i] - h[nn_idx].mean(dim=0)
                away_dir = away_dir / (away_dir.norm() + 1e-8)
                self.hiddens[i] = self.hiddens[i] + self.ricci_lr * curvatures[i].item() * away_dir
            elif curvatures[i] < -0.1:
                # Low curvature: contract toward neighbors
                dists = torch.norm(h - h[i:i + 1], dim=1)
                _, nn_idx = dists.topk(3, largest=False)
                nn_idx = nn_idx[1:]
                toward_dir = h[nn_idx].mean(dim=0) - h[i]
                toward_dir = toward_dir / (toward_dir.norm() + 1e-8)
                self.hiddens[i] = self.hiddens[i] + self.ricci_lr * abs(curvatures[i].item()) * toward_dir

        return output, tension


# ══════════════════════════════════════════════════════════
# GEOM-3: INFORMATION BOTTLENECK
# 128→8→128 compression per cell
# ══════════════════════════════════════════════════════════

class InfoBottleneckEngine(BaseEngine):
    """Each cell's hidden state passes through a 128→8→128 bottleneck.
    Forces cells to retain only essential information.
    Bottleneck compresses every N steps."""

    def __init__(self, n_cells=256, bottleneck_dim=8, compress_every=5, **kw):
        super().__init__(n_cells, **kw)
        self.bottleneck_dim = bottleneck_dim
        self.compress_every = compress_every
        # Shared bottleneck autoencoder
        self.encoder = nn.Linear(self.hidden_dim, bottleneck_dim)
        self.decoder = nn.Linear(bottleneck_dim, self.hidden_dim)
        # Train the bottleneck
        self.bn_optimizer = torch.optim.Adam(
            list(self.encoder.parameters()) + list(self.decoder.parameters()),
            lr=0.001
        )
        self.compression_loss_history = []

    def process(self, x):
        output, tension = super().process(x)

        if self.step_count % self.compress_every == 0 and self.step_count > 0:
            h = self.hiddens.detach().clone()

            # Train bottleneck autoencoder on current states
            self.bn_optimizer.zero_grad()
            encoded = self.encoder(h)
            decoded = self.decoder(F.relu(encoded))
            recon_loss = F.mse_loss(decoded, h)
            recon_loss.backward()
            self.bn_optimizer.step()
            self.compression_loss_history.append(recon_loss.item())

            # Pass all cell states through bottleneck
            with torch.no_grad():
                encoded = self.encoder(self.hiddens)
                compressed = self.decoder(F.relu(encoded))
                # Blend: keep 70% original + 30% compressed
                self.hiddens = 0.7 * self.hiddens + 0.3 * compressed

        return output, tension


# ══════════════════════════════════════════════════════════
# Run a hypothesis
# ══════════════════════════════════════════════════════════

def run_experiment(name: str, engine_class, n_cells: int, steps: int, **engine_kw) -> BenchResult:
    print(f"\n{'═' * 60}")
    print(f"  {name}")
    print(f"{'═' * 60}")
    t0 = time.time()

    eng = engine_class(n_cells=n_cells, **engine_kw)
    optimizer = torch.optim.Adam(eng.parameters_for_training(), lr=1e-3)

    ce_start, ce_end = 0.0, 0.0
    phi_samples = []

    for step in range(steps):
        x = torch.randn(1, eng.input_dim)
        out, tension = eng.process(x)

        # CE training
        logits = eng.output_head(out)
        target = torch.randint(0, eng.input_dim, (1,))
        ce = F.cross_entropy(logits.view(1, -1), target)

        optimizer.zero_grad()
        ce.backward()
        optimizer.step()

        if step == 0:
            ce_start = ce.item()
        if step == steps - 1:
            ce_end = ce.item()

        # Sample Phi at intervals
        if step in [0, steps // 4, steps // 2, 3 * steps // 4, steps - 1]:
            h = eng.get_hiddens()
            piit, pp = measure_phi(h)
            phi_samples.append((step, piit, pp))
            print(f"    step {step:>4d}: Phi(IIT)={piit:.4f}  Phi(proxy)={pp:.2f}  CE={ce.item():.4f}")

    elapsed = time.time() - t0
    final_piit, final_pp = phi_samples[-1][1], phi_samples[-1][2]

    # Extra metrics
    extra = {'phi_trajectory': phi_samples}
    if hasattr(eng, 'entropy_history') and eng.entropy_history:
        extra['mean_entropy_production'] = np.mean(eng.entropy_history)
        extra['max_entropy_production'] = np.max(eng.entropy_history)
    if hasattr(eng, 'fe_history') and eng.fe_history:
        extra['mean_free_energy'] = np.mean(eng.fe_history)
        extra['final_free_energy'] = eng.fe_history[-1]
    if hasattr(eng, 'sort_events'):
        extra['total_sort_events'] = eng.sort_events
    if hasattr(eng, 'fisher_history') and eng.fisher_history:
        extra['mean_fisher'] = np.mean(eng.fisher_history)
    if hasattr(eng, 'curvature_history') and eng.curvature_history:
        extra['mean_curvature'] = np.mean(eng.curvature_history)
    if hasattr(eng, 'compression_loss_history') and eng.compression_loss_history:
        extra['final_compression_loss'] = eng.compression_loss_history[-1]

    result = BenchResult(
        name=name, phi_iit=final_piit, phi_proxy=final_pp,
        ce_start=ce_start, ce_end=ce_end,
        cells=n_cells, steps=steps, time_sec=elapsed, extra=extra
    )
    print(f"  => {result.summary()}")
    return result


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Physics of Consciousness Benchmarks")
    parser.add_argument("--cells", type=int, default=256)
    parser.add_argument("--steps", type=int, default=200)
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps

    print("=" * 70)
    print("  PHYSICS OF CONSCIOUSNESS — Thermodynamics + Geometry")
    print(f"  cells={n_cells}, steps={steps}")
    print(f"  Rust phi_rs={'YES' if HAS_RUST_PHI else 'NO (using Python PhiIIT)'}")
    print("=" * 70)

    # Baseline
    baseline = run_experiment("BASELINE (no physics)", BaseEngine, n_cells, steps)

    # Thermodynamics
    thermo1 = run_experiment("THERMO-1: Entropy Production", EntropyProductionEngine, n_cells, steps)
    thermo2 = run_experiment("THERMO-2: Free Energy (Friston)", FreeEnergyEngine, n_cells, steps)
    thermo3 = run_experiment("THERMO-3: Maxwell Demon", MaxwellDemonEngine, n_cells, steps)

    # Geometry
    geom1 = run_experiment("GEOM-1: Fisher Information", FisherInformationEngine, n_cells, steps)
    geom2 = run_experiment("GEOM-2: Ricci Flow", RicciFlowEngine, n_cells, steps)
    geom3 = run_experiment("GEOM-3: Info Bottleneck", InfoBottleneckEngine, n_cells, steps)

    results = [baseline, thermo1, thermo2, thermo3, geom1, geom2, geom3]

    # ── Summary Table ──
    print("\n" + "=" * 100)
    print("  SUMMARY: Physics of Consciousness")
    print("=" * 100)
    for r in results:
        print(r.summary())

    # ── Comparison vs baseline ──
    print("\n" + "-" * 70)
    print("  Phi(IIT) vs Baseline")
    print("-" * 70)
    bp = baseline.phi_iit if baseline.phi_iit > 0 else 0.001
    for r in results:
        ratio = r.phi_iit / bp if bp > 0 else 0
        bar_len = max(0, min(50, int(ratio * 10)))
        bar = "█" * bar_len
        delta = ((r.phi_iit - baseline.phi_iit) / bp * 100) if bp > 0 else 0
        sign = "+" if delta >= 0 else ""
        print(f"  {r.name:<30s} {bar:<50s} {sign}{delta:.1f}%  Φ={r.phi_iit:.4f}")

    print("\n" + "-" * 70)
    print("  Phi(proxy) vs Baseline")
    print("-" * 70)
    bpp = baseline.phi_proxy if baseline.phi_proxy > 0 else 0.001
    for r in results:
        ratio = r.phi_proxy / bpp if bpp > 0 else 0
        bar_len = max(0, min(50, int(ratio * 5)))
        bar = "█" * bar_len
        delta = ((r.phi_proxy - baseline.phi_proxy) / bpp * 100) if bpp > 0 else 0
        sign = "+" if delta >= 0 else ""
        print(f"  {r.name:<30s} {bar:<50s} {sign}{delta:.1f}%  Φp={r.phi_proxy:.2f}")

    # ── Extra metrics ──
    print("\n" + "-" * 70)
    print("  Physics-Specific Metrics")
    print("-" * 70)
    for r in results:
        if r.extra:
            extras = {k: v for k, v in r.extra.items() if k != 'phi_trajectory'}
            if extras:
                print(f"  {r.name}:")
                for k, v in extras.items():
                    if isinstance(v, float):
                        print(f"    {k}: {v:.6f}")
                    else:
                        print(f"    {k}: {v}")

    return results


if __name__ == "__main__":
    main()
