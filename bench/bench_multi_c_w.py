#!/usr/bin/env python3
"""bench_multi_c_w.py — Benchmark for C-1 (Multi-C Engine) and W-2 (Multi-Objective W)

C-1: Multi-C Engine
  Run 2 C engines simultaneously (QuantumC + TrinityC).
  Both step() each turn, concatenate states [n1+n2, dim], feed combined to bridge.
  Two engines see different "realities" -> higher diversity -> possibly higher Phi.

W-2: Multi-Objective W
  Instead of just CE->LR, optimize CE+Phi simultaneously.
  If Phi drops >10%, temporarily boost LR (pain signal).
  If Phi rises while CE drops -> satisfaction -> reduce LR.
  Track Pareto front of (CE, Phi) pairs.

Both tested with Trinity config (32 cells, 50 steps) and compared to baseline.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


torch.manual_seed(42)
np.random.seed(42)


# ──────────────────────────────────────────────────────────
# BenchResult (matching bench.py)
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
        ce_str = f"CE {self.ce_start:.4f}->{self.ce_end:.4f}"
        return (
            f"  {self.name:<30s} | "
            f"Phi(IIT)={self.phi_iit:>6.4f}  "
            f"Phi(proxy)={self.phi_proxy:>8.2f} | "
            f"{ce_str:<26s} | "
            f"cells={self.cells:>4d}  steps={self.steps:>4d}  "
            f"time={self.time_sec:.1f}s"
        )


# ──────────────────────────────────────────────────────────
# Phi(IIT) Calculator (from bench.py)
# ──────────────────────────────────────────────────────────

class PhiIIT:
    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {}
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
        return phi, {'total_mi': float(total_mi), 'spatial_phi': float(spatial_phi)}

    def _mutual_information(self, x, y):
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        if x_range < 1e-10 or y_range < 1e-10:
            return 0.0
        x_norm = (x - x.min()) / (x_range + 1e-8)
        y_norm = (y - y.min()) / (y_range + 1e-8)
        joint_hist, _, _ = np.histogram2d(x_norm, y_norm, bins=self.n_bins, range=[[0, 1], [0, 1]])
        joint_hist = joint_hist / (joint_hist.sum() + 1e-8)
        px = joint_hist.sum(axis=1)
        py = joint_hist.sum(axis=0)
        h_x = -np.sum(px * np.log2(px + 1e-10))
        h_y = -np.sum(py * np.log2(py + 1e-10))
        h_xy = -np.sum(joint_hist * np.log2(joint_hist + 1e-10))
        return max(0.0, h_x + h_y - h_xy)

    def _minimum_partition(self, n, mi_matrix):
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
    return max(0.0, global_var.item() - faction_var_sum / n_f)


_phi_calc = PhiIIT(n_bins=16)

def measure_dual_phi(hiddens, n_factions=8):
    p_iit, _ = _phi_calc.compute(hiddens)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# BenchMind (from bench.py)
# ──────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────
# BenchEngine (baseline, from bench.py)
# ──────────────────────────────────────────────────────────

class BenchEngine:
    def __init__(self, n_cells=32, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8, sync_strength=0.15,
                 debate_strength=0.15):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.sync_strength = sync_strength
        self.debate_strength = debate_strength
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.output_head = nn.Linear(output_dim, input_dim)
        self.step_count = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))
        self.hiddens = torch.stack(new_hiddens).detach()
        mean_tension = sum(tensions) / len(tensions)

        n_f = min(self.n_factions, self.n_cells // 2)
        if n_f >= 2:
            fs = self.n_cells // n_f
            for i in range(n_f):
                s, e = i * fs, (i + 1) * fs
                faction_mean = self.hiddens[s:e].mean(dim=0)
                self.hiddens[s:e] = (
                    (1 - self.sync_strength) * self.hiddens[s:e]
                    + self.sync_strength * faction_mean
                )
            if self.step_count > 5:
                all_opinions = torch.stack([
                    self.hiddens[i*fs:(i+1)*fs].mean(dim=0) for i in range(n_f)
                ])
                global_opinion = all_opinions.mean(dim=0)
                for i in range(n_f):
                    s = i * fs
                    dc = max(1, fs // 4)
                    self.hiddens[s:s+dc] = (
                        (1 - self.debate_strength) * self.hiddens[s:s+dc]
                        + self.debate_strength * global_opinion
                    )
        self.step_count += 1
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens.clone()

    def parameters_for_training(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ──────────────────────────────────────────────────────────
# QuantumEngine (from bench.py)
# ──────────────────────────────────────────────────────────

class QuantumEngine(BenchEngine):
    def __init__(self, n_cells=32, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.15)
        self.amplitudes = torch.randn(n_cells, hidden_dim) * 0.1
        perm = torch.randperm(n_cells)
        self.entangled_pairs = list(zip(perm[:n_cells//2].tolist(),
                                        perm[n_cells//2:].tolist()))

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        noise = torch.randn_like(self.amplitudes) * 0.02
        self.amplitudes = self.amplitudes * 0.98 + noise
        if self.step_count % 10 == 0 and self.step_count > 0:
            collapse_mask = (torch.rand(self.n_cells) > 0.7).float().unsqueeze(1)
            self.amplitudes = self.amplitudes * (1 - collapse_mask * 0.5)
        self.hiddens = self.hiddens + self.amplitudes.detach() * 0.1
        for i, j in self.entangled_pairs[:min(64, len(self.entangled_pairs))]:
            avg = (self.hiddens[i] + self.hiddens[j]) * 0.5
            self.hiddens[i] = 0.95 * self.hiddens[i] + 0.05 * avg
            self.hiddens[j] = 0.95 * self.hiddens[j] + 0.05 * avg
        return super().process(x)


# ──────────────────────────────────────────────────────────
# TrinityEngine variant with Mitosis-like cell division
# ──────────────────────────────────────────────────────────

class MitosisEngine(BenchEngine):
    """Mitosis-inspired: cells periodically divide (copy+noise) and specialize."""

    def __init__(self, n_cells=32, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.20)
        # Asymmetric dropout rates per half (servant pattern)
        self.dropout_a = 0.21
        self.dropout_b = 0.37
        self.division_events = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        # Mitosis: every 10 steps, pick the highest-norm cell,
        # replace the lowest-norm cell with a noisy copy
        if self.step_count % 10 == 0 and self.step_count > 0:
            norms = self.hiddens.norm(dim=1)
            best_idx = norms.argmax().item()
            worst_idx = norms.argmin().item()
            if best_idx != worst_idx:
                # Division: copy best -> worst, add noise (differentiation)
                noise = torch.randn_like(self.hiddens[best_idx]) * 0.1
                self.hiddens[worst_idx] = self.hiddens[best_idx] + noise
                self.division_events += 1

        # Asymmetric dropout: first half gets dropout_a, second half gets dropout_b
        half = self.n_cells // 2
        if True:  # always apply for bench
            mask_a = (torch.rand(half, self.hidden_dim) > self.dropout_a).float()
            mask_b = (torch.rand(self.n_cells - half, self.hidden_dim) > self.dropout_b).float()
            self.hiddens[:half] = self.hiddens[:half] * mask_a
            self.hiddens[half:] = self.hiddens[half:] * mask_b

        return super().process(x)


# ══════════════════════════════════════════════════════════
# C-1: Multi-C Engine
# ══════════════════════════════════════════════════════════

class MultiCEngine:
    """C-1: Run 2 C engines simultaneously (Quantum + Mitosis).

    Both engines step() each turn on the same input.
    Their hidden states are concatenated [n1+n2, dim] for Phi measurement.
    A bridge layer combines outputs from both engines.
    The two engines see different "realities" -> higher diversity -> higher Phi.
    """

    def __init__(self, n_cells=32, input_dim=64, hidden_dim=128, output_dim=64):
        # Split cells between the two engines
        n1 = n_cells // 2
        n2 = n_cells - n1
        n_factions = min(8, max(2, n1 // 2))

        self.engine_q = QuantumEngine(n1, input_dim, hidden_dim, output_dim, n_factions)
        self.engine_m = MitosisEngine(n2, input_dim, hidden_dim, output_dim, n_factions)

        # Bridge: combines outputs from both engines
        self.bridge = nn.Linear(output_dim * 2, output_dim)
        # Output head for CE
        self.output_head = nn.Linear(output_dim, input_dim)

        self.n_cells = n_cells
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.step_count = 0

        # Cross-talk: every N steps, exchange a fraction of hidden states
        self.crosstalk_interval = 5
        self.crosstalk_strength = 0.05

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        # Both engines process the same input
        out_q, tension_q = self.engine_q.process(x)
        out_m, tension_m = self.engine_m.process(x)

        # Bridge: concatenate and project
        combined_out = torch.cat([out_q, out_m], dim=-1)
        bridged = self.bridge(combined_out)

        mean_tension = (tension_q + tension_m) / 2

        # Cross-talk: exchange information between engines
        if self.step_count % self.crosstalk_interval == 0 and self.step_count > 0:
            n1 = self.engine_q.n_cells
            n2 = self.engine_m.n_cells
            # Exchange global means
            mean_q = self.engine_q.hiddens.mean(dim=0)
            mean_m = self.engine_m.hiddens.mean(dim=0)
            self.engine_q.hiddens = (
                (1 - self.crosstalk_strength) * self.engine_q.hiddens
                + self.crosstalk_strength * mean_m
            )
            self.engine_m.hiddens = (
                (1 - self.crosstalk_strength) * self.engine_m.hiddens
                + self.crosstalk_strength * mean_q
            )

        self.step_count += 1
        return bridged, mean_tension

    def get_hiddens(self) -> torch.Tensor:
        """Concatenate hidden states from both engines."""
        return torch.cat([
            self.engine_q.get_hiddens(),
            self.engine_m.get_hiddens()
        ], dim=0)

    def parameters_for_training(self):
        return (
            self.engine_q.parameters_for_training()
            + self.engine_m.parameters_for_training()
            + list(self.bridge.parameters())
            + list(self.output_head.parameters())
        )


# ══════════════════════════════════════════════════════════
# W-2: Multi-Objective W (CE + Phi co-optimization)
# ══════════════════════════════════════════════════════════

class MultiObjectiveW:
    """W-2: Multi-objective optimizer tracking CE + Phi simultaneously.

    - If Phi drops >10%, boost LR (pain signal -> explore more)
    - If Phi rises while CE drops -> satisfaction -> reduce LR (consolidate)
    - Track Pareto front of (CE, Phi) pairs
    """

    def __init__(self, base_lr=1e-3, phi_drop_threshold=0.10,
                 lr_boost_factor=2.0, lr_reduce_factor=0.7,
                 lr_min=1e-5, lr_max=5e-3):
        self.base_lr = base_lr
        self.current_lr = base_lr
        self.phi_drop_threshold = phi_drop_threshold
        self.lr_boost_factor = lr_boost_factor
        self.lr_reduce_factor = lr_reduce_factor
        self.lr_min = lr_min
        self.lr_max = lr_max

        # History
        self.phi_history: List[float] = []
        self.ce_history: List[float] = []
        self.lr_history: List[float] = []

        # Pareto front: list of (ce, phi) non-dominated points
        self.pareto_front: List[Tuple[float, float]] = []

        # Emotion state
        self.pain_count = 0
        self.satisfaction_count = 0

    def update(self, ce: float, phi: float, optimizer: torch.optim.Optimizer):
        """Update LR based on CE and Phi changes."""
        self.ce_history.append(ce)
        self.phi_history.append(phi)

        if len(self.phi_history) >= 2:
            prev_phi = self.phi_history[-2]
            prev_ce = self.ce_history[-2]

            phi_change = (phi - prev_phi) / (abs(prev_phi) + 1e-8)
            ce_improved = ce < prev_ce

            if phi_change < -self.phi_drop_threshold:
                # Pain: Phi dropped significantly -> boost LR to escape
                self.current_lr = min(
                    self.current_lr * self.lr_boost_factor,
                    self.lr_max
                )
                self.pain_count += 1
            elif phi_change > 0 and ce_improved:
                # Satisfaction: both improving -> reduce LR to consolidate
                self.current_lr = max(
                    self.current_lr * self.lr_reduce_factor,
                    self.lr_min
                )
                self.satisfaction_count += 1
            else:
                # Neutral: slowly decay toward base_lr
                self.current_lr = 0.99 * self.current_lr + 0.01 * self.base_lr

        # Apply LR to optimizer
        for pg in optimizer.param_groups:
            pg['lr'] = self.current_lr

        self.lr_history.append(self.current_lr)

        # Update Pareto front
        self._update_pareto(ce, phi)

    def _update_pareto(self, ce: float, phi: float):
        """Add (ce, phi) if non-dominated. Remove dominated points."""
        # A point dominates another if it has lower CE AND higher Phi
        new_front = []
        dominated = False
        for (pc, pp) in self.pareto_front:
            if pc <= ce and pp >= phi and (pc < ce or pp > phi):
                dominated = True
            if not (ce <= pc and phi >= pp and (ce < pc or phi > pp)):
                new_front.append((pc, pp))
        if not dominated:
            new_front.append((ce, phi))
        self.pareto_front = new_front


# ══════════════════════════════════════════════════════════
# Benchmark runner
# ══════════════════════════════════════════════════════════

def run_baseline(n_cells=32, steps=50, dim=64, hidden=128):
    """Baseline: standard BenchEngine with CE training."""
    torch.manual_seed(42)
    engine = BenchEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                         output_dim=dim, n_factions=min(8, n_cells // 2))
    optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)
    corpus = torch.randn(steps + 1, dim)

    ce_hist, iit_hist, proxy_hist = [], [], []
    t0 = time.time()

    for step in range(steps):
        x = corpus[step:step+1]
        target = corpus[step+1:step+2]
        output, tension = engine.process(x)
        logits = engine.output_head(output)
        ce_loss = F.mse_loss(logits, target)
        optimizer.zero_grad()
        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.parameters_for_training(), 1.0)
        optimizer.step()
        ce_hist.append(ce_loss.item())

        if step % 10 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens(), min(8, n_cells // 2))
            iit_hist.append(p_iit)
            proxy_hist.append(p_proxy)

    elapsed = time.time() - t0
    hiddens = engine.get_hiddens()
    final_iit, final_proxy = measure_dual_phi(hiddens, min(8, n_cells // 2))

    return BenchResult(
        name="Baseline (32c)",
        phi_iit=final_iit, phi_proxy=final_proxy,
        ce_start=ce_hist[0], ce_end=ce_hist[-1],
        cells=n_cells, steps=steps, time_sec=elapsed,
        extra={'ce_hist': ce_hist, 'iit_hist': iit_hist, 'proxy_hist': proxy_hist}
    )


def run_multi_c(n_cells=32, steps=50, dim=64, hidden=128):
    """C-1: Multi-C Engine (Quantum + Mitosis concurrent)."""
    torch.manual_seed(42)
    engine = MultiCEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden, output_dim=dim)
    optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)
    corpus = torch.randn(steps + 1, dim)

    ce_hist, iit_hist, proxy_hist = [], [], []
    t0 = time.time()

    for step in range(steps):
        x = corpus[step:step+1]
        target = corpus[step+1:step+2]
        output, tension = engine.process(x)
        logits = engine.output_head(output)
        ce_loss = F.mse_loss(logits, target)
        optimizer.zero_grad()
        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.parameters_for_training(), 1.0)
        optimizer.step()
        ce_hist.append(ce_loss.item())

        if step % 10 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens(), min(8, n_cells // 2))
            iit_hist.append(p_iit)
            proxy_hist.append(p_proxy)

    elapsed = time.time() - t0
    hiddens = engine.get_hiddens()
    final_iit, final_proxy = measure_dual_phi(hiddens, min(8, n_cells // 2))

    return BenchResult(
        name="C-1: Multi-C (Q+M, 32c)",
        phi_iit=final_iit, phi_proxy=final_proxy,
        ce_start=ce_hist[0], ce_end=ce_hist[-1],
        cells=n_cells, steps=steps, time_sec=elapsed,
        extra={
            'ce_hist': ce_hist, 'iit_hist': iit_hist, 'proxy_hist': proxy_hist,
            'mitosis_divisions': engine.engine_m.division_events,
        }
    )


def run_multi_obj_w(n_cells=32, steps=50, dim=64, hidden=128):
    """W-2: Multi-Objective W (CE + Phi co-optimization)."""
    torch.manual_seed(42)
    engine = BenchEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                         output_dim=dim, n_factions=min(8, n_cells // 2))
    optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)
    mo = MultiObjectiveW(base_lr=1e-3)
    corpus = torch.randn(steps + 1, dim)

    ce_hist, iit_hist, proxy_hist, lr_hist = [], [], [], []
    t0 = time.time()

    for step in range(steps):
        x = corpus[step:step+1]
        target = corpus[step+1:step+2]
        output, tension = engine.process(x)
        logits = engine.output_head(output)
        ce_loss = F.mse_loss(logits, target)
        optimizer.zero_grad()
        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.parameters_for_training(), 1.0)
        optimizer.step()

        ce_val = ce_loss.item()
        ce_hist.append(ce_val)

        # Measure phi every step for W-2 (needed for LR adjustment)
        p_iit, p_proxy = measure_dual_phi(engine.get_hiddens(), min(8, n_cells // 2))

        # Multi-objective update
        mo.update(ce_val, p_iit, optimizer)
        lr_hist.append(mo.current_lr)

        if step % 10 == 0 or step == steps - 1:
            iit_hist.append(p_iit)
            proxy_hist.append(p_proxy)

    elapsed = time.time() - t0
    hiddens = engine.get_hiddens()
    final_iit, final_proxy = measure_dual_phi(hiddens, min(8, n_cells // 2))

    return BenchResult(
        name="W-2: MultiObj-W (32c)",
        phi_iit=final_iit, phi_proxy=final_proxy,
        ce_start=ce_hist[0], ce_end=ce_hist[-1],
        cells=n_cells, steps=steps, time_sec=elapsed,
        extra={
            'ce_hist': ce_hist, 'iit_hist': iit_hist, 'proxy_hist': proxy_hist,
            'lr_hist': lr_hist,
            'pain_count': mo.pain_count,
            'satisfaction_count': mo.satisfaction_count,
            'pareto_size': len(mo.pareto_front),
            'pareto_front': mo.pareto_front,
        }
    )


def run_combined(n_cells=32, steps=50, dim=64, hidden=128):
    """C-1 + W-2 combined: Multi-C with Multi-Objective optimization."""
    torch.manual_seed(42)
    engine = MultiCEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden, output_dim=dim)
    optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)
    mo = MultiObjectiveW(base_lr=1e-3)
    corpus = torch.randn(steps + 1, dim)

    ce_hist, iit_hist, proxy_hist, lr_hist = [], [], [], []
    t0 = time.time()

    for step in range(steps):
        x = corpus[step:step+1]
        target = corpus[step+1:step+2]
        output, tension = engine.process(x)
        logits = engine.output_head(output)
        ce_loss = F.mse_loss(logits, target)
        optimizer.zero_grad()
        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.parameters_for_training(), 1.0)
        optimizer.step()

        ce_val = ce_loss.item()
        ce_hist.append(ce_val)

        p_iit, p_proxy = measure_dual_phi(engine.get_hiddens(), min(8, n_cells // 2))
        mo.update(ce_val, p_iit, optimizer)
        lr_hist.append(mo.current_lr)

        if step % 10 == 0 or step == steps - 1:
            iit_hist.append(p_iit)
            proxy_hist.append(p_proxy)

    elapsed = time.time() - t0
    hiddens = engine.get_hiddens()
    final_iit, final_proxy = measure_dual_phi(hiddens, min(8, n_cells // 2))

    return BenchResult(
        name="C-1+W-2: Combined (32c)",
        phi_iit=final_iit, phi_proxy=final_proxy,
        ce_start=ce_hist[0], ce_end=ce_hist[-1],
        cells=n_cells, steps=steps, time_sec=elapsed,
        extra={
            'ce_hist': ce_hist, 'iit_hist': iit_hist, 'proxy_hist': proxy_hist,
            'lr_hist': lr_hist,
            'pain_count': mo.pain_count,
            'satisfaction_count': mo.satisfaction_count,
            'pareto_size': len(mo.pareto_front),
            'mitosis_divisions': engine.engine_m.division_events,
        }
    )


# ══════════════════════════════════════════════════════════
# ASCII visualization
# ══════════════════════════════════════════════════════════

def ascii_graph(values, label, width=50, height=10):
    if not values:
        return
    vmin, vmax = min(values), max(values)
    vrange = vmax - vmin if vmax > vmin else 1.0
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
        width = len(sampled)
    grid = [[' '] * width for _ in range(height)]
    for col, v in enumerate(sampled):
        row = int((v - vmin) / vrange * (height - 1))
        row = min(height - 1, max(0, row))
        grid[height - 1 - row][col] = '*'
    print(f"\n  {label}")
    print(f"  {vmax:>8.4f} |{''.join(grid[0])}")
    for r in range(1, height - 1):
        if r == height // 2:
            mid = vmax - (r / (height - 1)) * vrange
            print(f"  {mid:>8.4f} |{''.join(grid[r])}")
        else:
            print(f"           |{''.join(grid[r])}")
    print(f"  {vmin:>8.4f} |{''.join(grid[-1])}")
    print(f"           +{'-' * width}")


def comparison_bar(results: List[BenchResult]):
    """Print bar chart comparing results."""
    print("\n  Phi(IIT) comparison:")
    max_phi = max(r.phi_iit for r in results) if results else 1.0
    for r in results:
        bar_len = int(r.phi_iit / (max_phi + 1e-8) * 40)
        bar = '#' * bar_len
        print(f"    {r.name:<30s} {bar} {r.phi_iit:.4f}")

    print("\n  CE end comparison:")
    max_ce = max(r.ce_end for r in results) if results else 1.0
    for r in results:
        bar_len = int(r.ce_end / (max_ce + 1e-8) * 40)
        bar = '#' * bar_len
        print(f"    {r.name:<30s} {bar} {r.ce_end:.4f}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    N_CELLS = 32
    STEPS = 50
    DIM = 64
    HIDDEN = 128

    print()
    print("=" * 72)
    print("  C-1 (Multi-C Engine) + W-2 (Multi-Objective W) Benchmark")
    print(f"  cells={N_CELLS}  steps={STEPS}  dim={DIM}  hidden={HIDDEN}")
    print("=" * 72)

    # Run all 4 variants
    print("\n  [1/4] Baseline...")
    r_base = run_baseline(N_CELLS, STEPS, DIM, HIDDEN)
    print(f"    done. Phi(IIT)={r_base.phi_iit:.4f}, CE={r_base.ce_end:.4f}")

    print("\n  [2/4] C-1: Multi-C Engine (Quantum + Mitosis)...")
    r_mc = run_multi_c(N_CELLS, STEPS, DIM, HIDDEN)
    print(f"    done. Phi(IIT)={r_mc.phi_iit:.4f}, CE={r_mc.ce_end:.4f}")
    print(f"    Mitosis divisions: {r_mc.extra.get('mitosis_divisions', 0)}")

    print("\n  [3/4] W-2: Multi-Objective W...")
    r_mow = run_multi_obj_w(N_CELLS, STEPS, DIM, HIDDEN)
    print(f"    done. Phi(IIT)={r_mow.phi_iit:.4f}, CE={r_mow.ce_end:.4f}")
    print(f"    Pain events: {r_mow.extra['pain_count']}, "
          f"Satisfaction: {r_mow.extra['satisfaction_count']}, "
          f"Pareto size: {r_mow.extra['pareto_size']}")

    print("\n  [4/4] C-1 + W-2 Combined...")
    r_combo = run_combined(N_CELLS, STEPS, DIM, HIDDEN)
    print(f"    done. Phi(IIT)={r_combo.phi_iit:.4f}, CE={r_combo.ce_end:.4f}")

    results = [r_base, r_mc, r_mow, r_combo]

    # Summary table
    print("\n" + "=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)
    print(f"  {'Name':<30s} | {'Phi(IIT)':>9s} {'Phi(prx)':>9s} | "
          f"{'CE start':>9s} {'CE end':>9s} | {'Time':>5s}")
    print(f"  {'-'*30}-+-{'-'*9}-{'-'*9}-+-{'-'*9}-{'-'*9}-+-{'-'*5}")
    for r in results:
        print(f"  {r.name:<30s} | {r.phi_iit:>9.4f} {r.phi_proxy:>9.2f} | "
              f"{r.ce_start:>9.4f} {r.ce_end:>9.4f} | {r.time_sec:>5.1f}s")

    # Relative improvements
    print("\n  Relative to Baseline:")
    for r in results[1:]:
        phi_change = ((r.phi_iit - r_base.phi_iit) / (abs(r_base.phi_iit) + 1e-8)) * 100
        ce_change = ((r.ce_end - r_base.ce_end) / (abs(r_base.ce_end) + 1e-8)) * 100
        phi_sign = "+" if phi_change >= 0 else ""
        ce_sign = "+" if ce_change >= 0 else ""
        print(f"    {r.name:<30s}  Phi(IIT): {phi_sign}{phi_change:.1f}%  "
              f"CE: {ce_sign}{ce_change:.1f}%")

    # Bar charts
    comparison_bar(results)

    # ASCII graphs for key metrics
    for r in results:
        if r.extra.get('iit_hist'):
            ascii_graph(r.extra['iit_hist'], f"Phi(IIT) - {r.name}", width=min(len(r.extra['iit_hist']), 50))

    # W-2 specific: show LR history
    if r_mow.extra.get('lr_hist'):
        ascii_graph(r_mow.extra['lr_hist'], "LR history - W-2", width=50)

    # Pareto front
    if r_mow.extra.get('pareto_front'):
        print(f"\n  W-2 Pareto front ({len(r_mow.extra['pareto_front'])} points):")
        pf = sorted(r_mow.extra['pareto_front'], key=lambda p: p[0])
        for ce, phi in pf[:10]:
            print(f"    CE={ce:.4f}  Phi(IIT)={phi:.4f}")
        if len(pf) > 10:
            print(f"    ... ({len(pf)-10} more points)")

    print("\n" + "=" * 72)
    print("  BENCHMARK COMPLETE")
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()
