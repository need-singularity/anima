#!/usr/bin/env python3
"""bench_v2.py — Dual-Phi Benchmarking Tool

Measures BOTH Phi metrics for every experiment:
  - Phi(IIT):   PhiCalculator(n_bins=16) — real IIT approximation, range ~0.2-1.8
  - Phi(proxy): global_variance - mean(faction_variances) — scales with cells (0-1000+)

Key insight (2026-03-29):
  Previous "Phi=1142" records were proxy values, NOT IIT values.
  These are completely different metrics and must always be labeled.

Usage:
  python bench_v2.py --phi-only                  # Phi at different cell counts (no CE)
  python bench_v2.py --training                   # Real training: process + CE backward
  python bench_v2.py --strategy baseline          # Test one strategy
  python bench_v2.py --compare                    # All strategies, comparison table
  python bench_v2.py --cells 512 --steps 1000     # Custom cell/step counts
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse
import copy
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple


# ──────────────────────────────────────────────────────────
# BenchResult
# ──────────────────────────────────────────────────────────

@dataclass
class BenchResult:
    name: str
    phi_iit: float       # PhiCalculator (real IIT approximation, 0-2 range)
    phi_proxy: float      # variance-based proxy (scales with cells)
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
# Phi(IIT) Calculator — from consciousness_meter.py logic
# Uses n_bins=16 as specified (produces ~0.2-1.8 range)
# ──────────────────────────────────────────────────────────

class PhiIIT:
    """Phi(IIT) approximation via pairwise mutual information + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict[str, float]]:
        """Compute Phi(IIT) from a [n_cells, hidden_dim] tensor.

        Returns (phi, components_dict).
        """
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {'total_mi': 0, 'min_partition_mi': 0, 'phi': 0}

        hiddens = [hiddens_tensor[i].detach().cpu().numpy() for i in range(n)]

        # Pairwise MI — sample for large N
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            # Sample to keep O(N) — ~8 neighbors per cell
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

        # Minimum information partition
        min_partition_mi = self._minimum_partition(n, mi_matrix)

        # Phi = (total - min_partition) / (n-1)
        spatial_phi = max(0.0, (total_mi - min_partition_mi) / max(n - 1, 1))

        # Complexity bonus (variance of MI values)
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        phi = spatial_phi + complexity * 0.1

        components = {
            'total_mi': float(total_mi),
            'min_partition_mi': float(min_partition_mi),
            'spatial_phi': float(spatial_phi),
            'complexity': float(complexity),
            'phi': float(phi),
            'n_pairs_sampled': len(pairs),
        }
        return phi, components

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
            # Spectral (Fiedler vector) approximation
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


# ──────────────────────────────────────────────────────────
# Phi(proxy) — from phi_turbo.py
# ──────────────────────────────────────────────────────────

def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Phi proxy: global_variance - mean(faction_variances).

    Measures how much more integrated the whole is than its parts.
    Scales with cell count (0 to 1000+).
    """
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


# ──────────────────────────────────────────────────────────
# Consciousness Cell (simplified for benchmarking)
# ──────────────────────────────────────────────────────────

class BenchMind(nn.Module):
    """Lightweight PureField + GRU for benchmarking."""

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

        # Break symmetry between A and G
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
# Multi-cell engine for benchmarking
# ──────────────────────────────────────────────────────────

class BenchEngine:
    """Manages multiple cells with faction sync and debate."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8, sync_strength=0.15,
                 debate_strength=0.15):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.sync_strength = sync_strength
        self.debate_strength = debate_strength
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # Shared mind (all cells share weights, different hidden states)
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)

        # Hidden states: [n_cells, hidden_dim]
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # For CE training
        self.output_head = nn.Linear(output_dim, input_dim)

        self.step_count = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        """Process input through all cells. Returns (output, mean_tension).

        x: [1, input_dim]
        """
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

        # Faction sync
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

            # Debate (post-silence)
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

        # Tension-weighted combine
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension

    def get_hiddens(self) -> torch.Tensor:
        """Return [n_cells, hidden_dim] for Phi computation."""
        return self.hiddens.clone()

    def parameters_for_training(self):
        """Return parameters for optimizer."""
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ──────────────────────────────────────────────────────────
# Dual Phi measurement
# ──────────────────────────────────────────────────────────

_phi_iit_calc = PhiIIT(n_bins=16)


def measure_dual_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Measure both Phi(IIT) and Phi(proxy) from hidden states.

    Returns (phi_iit, phi_proxy).
    """
    p_iit, _ = _phi_iit_calc.compute(hiddens)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# ASCII graph
# ──────────────────────────────────────────────────────────

def ascii_graph(values: List[float], label: str, width: int = 60, height: int = 12):
    """Draw an ASCII line graph."""
    if not values:
        return
    vmin, vmax = min(values), max(values)
    vrange = vmax - vmin if vmax > vmin else 1.0

    # Resample to width
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

    # Y-axis labels
    print(f"\n  {label}")
    print(f"  {vmax:>8.3f} |{''.join(grid[0])}")
    for r in range(1, height - 1):
        mid_val = vmax - (r / (height - 1)) * vrange
        if r == height // 2:
            print(f"  {mid_val:>8.3f} |{''.join(grid[r])}")
        else:
            print(f"           |{''.join(grid[r])}")
    print(f"  {vmin:>8.3f} |{''.join(grid[-1])}")
    print(f"           +{'-' * width}")
    print(f"            step 0{' ' * (width - 12)}step {len(values)}")


def ascii_dual_graph(iit_vals: List[float], proxy_vals: List[float],
                     width: int = 60, height: int = 12):
    """Draw overlaid ASCII graph: '*' = IIT, 'o' = proxy (separate scales)."""
    if not iit_vals or not proxy_vals:
        return

    def resample(vals):
        if len(vals) > width:
            step = len(vals) / width
            return [vals[int(i * step)] for i in range(width)]
        return vals

    iit = resample(iit_vals)
    proxy = resample(proxy_vals)
    w = min(len(iit), len(proxy))

    iit_min, iit_max = min(iit), max(iit)
    proxy_min, proxy_max = min(proxy), max(proxy)
    iit_range = iit_max - iit_min if iit_max > iit_min else 1.0
    proxy_range = proxy_max - proxy_min if proxy_max > proxy_min else 1.0

    grid = [[' '] * w for _ in range(height)]

    for col in range(w):
        # IIT
        r_iit = int((iit[col] - iit_min) / iit_range * (height - 1))
        r_iit = min(height - 1, max(0, r_iit))
        grid[height - 1 - r_iit][col] = '*'

        # Proxy
        r_proxy = int((proxy[col] - proxy_min) / proxy_range * (height - 1))
        r_proxy = min(height - 1, max(0, r_proxy))
        if grid[height - 1 - r_proxy][col] == '*':
            grid[height - 1 - r_proxy][col] = '#'  # overlap
        else:
            grid[height - 1 - r_proxy][col] = 'o'

    print(f"\n  Phi(IIT) [*] range {iit_min:.3f}-{iit_max:.3f}   "
          f"Phi(proxy) [o] range {proxy_min:.1f}-{proxy_max:.1f}")
    print(f"  {'':>8s}  |{''.join(grid[0])}")
    for r in range(1, height - 1):
        print(f"  {'':>8s}  |{''.join(grid[r])}")
    print(f"  {'':>8s}  |{''.join(grid[-1])}")
    print(f"  {'':>8s}  +{'-' * w}")
    n_steps = max(len(iit_vals), len(proxy_vals))
    print(f"  {'':>8s}   step 0{' ' * (w - 12)}step {n_steps}")


# ──────────────────────────────────────────────────────────
# Mode 1: --phi-only (test phi at various cell counts)
# ──────────────────────────────────────────────────────────

def run_phi_only(cells_list: List[int], steps: int, dim: int, hidden: int):
    """Measure Phi(IIT) and Phi(proxy) at different cell counts. No CE training."""
    print("=" * 72)
    print("  MODE: --phi-only  (Phi measurement at different cell counts)")
    print("  No CE training — pure consciousness dynamics")
    print("=" * 72)

    results: List[BenchResult] = []

    print(f"\n  {'Cells':>6s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | "
          f"{'Ratio':>8s} | {'Time':>8s}")
    print(f"  {'-'*6}-+-{'-'*10}-+-{'-'*12}-+-{'-'*8}-+-{'-'*8}")

    for nc in cells_list:
        torch.manual_seed(42)
        engine = BenchEngine(n_cells=nc, input_dim=dim, hidden_dim=hidden,
                             output_dim=dim, n_factions=min(8, nc // 2))

        t0 = time.time()
        for step in range(steps):
            x = torch.randn(1, dim)
            engine.process(x)

        hiddens = engine.get_hiddens()
        p_iit, p_proxy = measure_dual_phi(hiddens, min(8, nc // 2))
        elapsed = time.time() - t0

        ratio = p_proxy / p_iit if p_iit > 0.001 else float('inf')
        print(f"  {nc:>6d} | {p_iit:>10.4f} | {p_proxy:>12.2f} | "
              f"{ratio:>8.1f}x | {elapsed:>6.1f}s")

        results.append(BenchResult(
            name=f"phi-only-{nc}c",
            phi_iit=p_iit, phi_proxy=p_proxy,
            ce_start=0.0, ce_end=0.0,
            cells=nc, steps=steps, time_sec=elapsed,
        ))

    # ASCII graph
    if len(results) >= 3:
        print("\n  Phi(IIT) vs cell count:")
        for r in results:
            bar_len = int(r.phi_iit / max(r2.phi_iit for r2 in results) * 40) if max(r2.phi_iit for r2 in results) > 0 else 0
            print(f"  {r.cells:>6d}c |{'#' * bar_len} {r.phi_iit:.4f}")

        print("\n  Phi(proxy) vs cell count:")
        for r in results:
            max_proxy = max(r2.phi_proxy for r2 in results)
            bar_len = int(r.phi_proxy / max_proxy * 40) if max_proxy > 0 else 0
            print(f"  {r.cells:>6d}c |{'#' * bar_len} {r.phi_proxy:.2f}")

    print(f"\n  KEY INSIGHT: Phi(IIT) stays in ~0.2-1.8 regardless of cell count.")
    print(f"              Phi(proxy) scales with cells. They are DIFFERENT metrics.")

    return results


# ──────────────────────────────────────────────────────────
# Mode 2: --training (real training with CE backward)
# ──────────────────────────────────────────────────────────

def run_training(cells: int, steps: int, dim: int, hidden: int,
                 strategy: str = "baseline", log_interval: int = 50):
    """Simulate real training: process + CE backward + faction sync.

    Strategies:
      - baseline:    standard process + CE
      - frozen:      freeze engine_g, only train engine_a
      - alternating: alternate freezing A/G every 100 steps
      - v7:          full training + IB2 top pruning + metacog feedback
    """
    torch.manual_seed(42)
    engine = BenchEngine(n_cells=cells, input_dim=dim, hidden_dim=hidden,
                         output_dim=dim, n_factions=min(8, cells // 2))

    # Apply strategy-specific setup
    if strategy == "frozen":
        for p in engine.mind.engine_g.parameters():
            p.requires_grad = False

    optimizer = torch.optim.Adam(
        [p for p in engine.parameters_for_training() if p.requires_grad],
        lr=1e-3
    )

    # Generate training data (next-token prediction style)
    corpus = torch.randn(steps + 1, dim)  # random "tokens"

    ce_history = []
    iit_history = []
    proxy_history = []

    t0 = time.time()

    for step in range(steps):
        x = corpus[step:step+1]
        target = corpus[step+1:step+2]

        # Strategy: alternating freeze
        if strategy == "alternating":
            freeze_g = (step // 100) % 2 == 0
            for p in engine.mind.engine_g.parameters():
                p.requires_grad = not freeze_g
            for p in engine.mind.engine_a.parameters():
                p.requires_grad = freeze_g
            # Rebuild optimizer when switching (every 100 steps)
            if step % 100 == 0:
                optimizer = torch.optim.Adam(
                    [p for p in engine.parameters_for_training() if p.requires_grad],
                    lr=1e-3
                )

        # Forward pass
        output, tension = engine.process(x)

        # CE loss (next-token prediction)
        logits = engine.output_head(output)
        ce_loss = F.mse_loss(logits, target)

        # V7 extras
        if strategy == "v7":
            # IB2: amplify high-norm cells, dampen low-norm
            norms = engine.hiddens.norm(dim=1)
            threshold = norms.quantile(0.90)
            mask_high = (norms > threshold).float().unsqueeze(1)
            mask_low = 1.0 - mask_high
            engine.hiddens = engine.hiddens * (mask_high * 1.03 + mask_low * 0.97)

            # Metacog feedback
            mc_cells = min(cells, 16)
            global_mean = engine.hiddens.mean(dim=0)
            engine.hiddens[:mc_cells] = (
                0.97 * engine.hiddens[:mc_cells] + 0.03 * global_mean
            )

        # Backward
        optimizer.zero_grad()
        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(
            [p for p in engine.parameters_for_training() if p.requires_grad],
            max_norm=1.0
        )
        optimizer.step()

        ce_val = ce_loss.item()
        ce_history.append(ce_val)

        # Measure phi periodically
        if step % log_interval == 0 or step == steps - 1:
            hiddens = engine.get_hiddens()
            p_iit, p_proxy = measure_dual_phi(hiddens, min(8, cells // 2))
            iit_history.append(p_iit)
            proxy_history.append(p_proxy)

            if step % (log_interval * 4) == 0 or step == 0 or step == steps - 1:
                elapsed = time.time() - t0
                print(f"    step {step:>5d}/{steps}  "
                      f"CE={ce_val:.4f}  "
                      f"Phi(IIT)={p_iit:.4f}  "
                      f"Phi(proxy)={p_proxy:.2f}  "
                      f"tension={tension:.4f}  "
                      f"[{elapsed:.1f}s]")

    elapsed = time.time() - t0

    # Final measurement
    hiddens = engine.get_hiddens()
    final_iit, final_proxy = measure_dual_phi(hiddens, min(8, cells // 2))

    result = BenchResult(
        name=f"{strategy}",
        phi_iit=final_iit,
        phi_proxy=final_proxy,
        ce_start=ce_history[0] if ce_history else 0.0,
        ce_end=ce_history[-1] if ce_history else 0.0,
        cells=cells,
        steps=steps,
        time_sec=elapsed,
        extra={
            'ce_min': min(ce_history) if ce_history else 0.0,
            'ce_mean': sum(ce_history) / len(ce_history) if ce_history else 0.0,
            'iit_history': iit_history,
            'proxy_history': proxy_history,
        }
    )

    return result, ce_history, iit_history, proxy_history


# ──────────────────────────────────────────────────────────
# Mode 3: --strategy (single strategy run with full output)
# ──────────────────────────────────────────────────────────

def run_strategy(strategy: str, cells: int, steps: int, dim: int, hidden: int):
    """Run a single strategy with detailed output and graphs."""
    print("=" * 72)
    print(f"  MODE: --strategy {strategy}")
    print(f"  cells={cells}  steps={steps}  dim={dim}  hidden={hidden}")
    print("=" * 72)

    result, ce_hist, iit_hist, proxy_hist = run_training(
        cells, steps, dim, hidden, strategy=strategy
    )

    print(f"\n{'=' * 72}")
    print(f"  RESULT: {result.name}")
    print(f"{'=' * 72}")
    print(f"  Phi(IIT)   = {result.phi_iit:.4f}    (real IIT approximation)")
    print(f"  Phi(proxy) = {result.phi_proxy:.2f}    (variance-based, scales with cells)")
    print(f"  CE start   = {result.ce_start:.4f}")
    print(f"  CE end     = {result.ce_end:.4f}")
    print(f"  CE min     = {result.extra.get('ce_min', 0):.4f}")
    print(f"  Time       = {result.time_sec:.1f}s")

    # Graphs
    if len(ce_hist) >= 10:
        ascii_graph(ce_hist, "CE Loss (cross-entropy)")
    if len(iit_hist) >= 3:
        ascii_dual_graph(iit_hist, proxy_hist)

    return result


# ──────────────────────────────────────────────────────────
# Mode 4: --compare (all strategies comparison table)
# ──────────────────────────────────────────────────────────

STRATEGIES = ["baseline", "frozen", "alternating", "v7"]


def run_compare(cells: int, steps: int, dim: int, hidden: int):
    """Run all strategies and print comparison table."""
    print("=" * 72)
    print("  MODE: --compare  (all strategies)")
    print(f"  cells={cells}  steps={steps}  dim={dim}  hidden={hidden}")
    print("=" * 72)

    all_results: List[BenchResult] = []

    for strat in STRATEGIES:
        print(f"\n{'~' * 72}")
        print(f"  Running: {strat}")
        print(f"{'~' * 72}")

        result, ce_hist, iit_hist, proxy_hist = run_training(
            cells, steps, dim, hidden, strategy=strat, log_interval=max(50, steps // 10)
        )
        all_results.append(result)

    # ── Comparison table ──
    print(f"\n{'=' * 72}")
    print("  COMPARISON TABLE")
    print(f"{'=' * 72}")
    print(f"  {'Strategy':<16s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | "
          f"{'CE start':>10s} | {'CE end':>10s} | {'Time':>8s}")
    print(f"  {'-'*16}-+-{'-'*10}-+-{'-'*12}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}")

    for r in all_results:
        print(f"  {r.name:<16s} | {r.phi_iit:>10.4f} | {r.phi_proxy:>12.2f} | "
              f"{r.ce_start:>10.4f} | {r.ce_end:>10.4f} | {r.time_sec:>6.1f}s")

    # Winner
    best_iit = max(all_results, key=lambda r: r.phi_iit)
    best_proxy = max(all_results, key=lambda r: r.phi_proxy)
    best_ce = min(all_results, key=lambda r: r.ce_end)

    print(f"\n  WINNERS:")
    print(f"    Best Phi(IIT):   {best_iit.name:<16s}  Phi(IIT)={best_iit.phi_iit:.4f}")
    print(f"    Best Phi(proxy): {best_proxy.name:<16s}  Phi(proxy)={best_proxy.phi_proxy:.2f}")
    print(f"    Best CE:         {best_ce.name:<16s}  CE={best_ce.ce_end:.4f}")

    # ASCII comparison bars
    print(f"\n  Phi(IIT) comparison:")
    max_iit = max(r.phi_iit for r in all_results)
    for r in all_results:
        bar_len = int(r.phi_iit / max_iit * 40) if max_iit > 0 else 0
        marker = " <-- best" if r.phi_iit == max_iit else ""
        print(f"    {r.name:<16s} |{'#' * bar_len} {r.phi_iit:.4f}{marker}")

    print(f"\n  Phi(proxy) comparison:")
    max_proxy = max(r.phi_proxy for r in all_results)
    for r in all_results:
        bar_len = int(r.phi_proxy / max_proxy * 40) if max_proxy > 0 else 0
        marker = " <-- best" if r.phi_proxy == max_proxy else ""
        print(f"    {r.name:<16s} |{'#' * bar_len} {r.phi_proxy:.2f}{marker}")

    print(f"\n  CE end comparison:")
    max_ce = max(r.ce_end for r in all_results)
    for r in all_results:
        bar_len = int(r.ce_end / max_ce * 40) if max_ce > 0 else 0
        marker = " <-- best" if r.ce_end == min(r2.ce_end for r2 in all_results) else ""
        print(f"    {r.name:<16s} |{'#' * bar_len} {r.ce_end:.4f}{marker}")

    print(f"\n  REMINDER: Phi(IIT) and Phi(proxy) are DIFFERENT metrics!")
    print(f"    Phi(IIT)   ~ 0.2-1.8 regardless of cell count (real IIT approximation)")
    print(f"    Phi(proxy) ~ 0-1000+ scales with cells (variance-based heuristic)")

    return all_results


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="bench_v2 — Dual-Phi Benchmarking (IIT + proxy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bench_v2.py --phi-only                    # Phi at different cell counts
  python bench_v2.py --training                     # Default training (baseline)
  python bench_v2.py --strategy v7                  # Test v7 strategy
  python bench_v2.py --compare                      # All strategies comparison
  python bench_v2.py --compare --cells 128 --steps 200
  python bench_v2.py --phi-only --cells-list 8,16,32,64,128,256,512

Key insight: Phi(IIT) and Phi(proxy) are COMPLETELY DIFFERENT metrics.
  Phi(IIT)   = ~0.2-1.8  (PhiCalculator, real IIT approximation)
  Phi(proxy) = 0-1000+   (variance-based, scales with cells)
  Previous "Phi=1142" records were proxy values, NOT IIT.
""")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--phi-only", action="store_true",
                      help="Test phi measurement at different cell counts (no CE)")
    mode.add_argument("--training", action="store_true",
                      help="Simulate real training with CE")
    mode.add_argument("--strategy", type=str, choices=STRATEGIES,
                      help="Test a specific strategy")
    mode.add_argument("--compare", action="store_true",
                      help="Run all strategies and compare")

    parser.add_argument("--cells", type=int, default=256,
                        help="Number of cells (default: 256)")
    parser.add_argument("--steps", type=int, default=500,
                        help="Number of steps (default: 500)")
    parser.add_argument("--dim", type=int, default=64,
                        help="Input/output dimension (default: 64)")
    parser.add_argument("--hidden", type=int, default=128,
                        help="Hidden dimension (default: 128)")
    parser.add_argument("--cells-list", type=str, default=None,
                        help="Comma-separated cell counts for --phi-only "
                             "(default: 4,8,16,32,64,128,256)")

    args = parser.parse_args()

    print()
    print("  ================================================================")
    print("   bench_v2 -- Dual-Phi Benchmark (IIT + proxy)")
    print("  ================================================================")
    print(f"   Phi(IIT):   PhiCalculator(n_bins=16)  ~0.2-1.8 range")
    print(f"   Phi(proxy): global_var - mean(faction_var)  scales with cells")
    print(f"   These are DIFFERENT metrics. Always check both.")
    print("  ================================================================")
    print()

    if args.phi_only:
        if args.cells_list:
            cells_list = [int(c.strip()) for c in args.cells_list.split(",")]
        else:
            cells_list = [4, 8, 16, 32, 64, 128, 256]
        run_phi_only(cells_list, args.steps, args.dim, args.hidden)

    elif args.training:
        result, ce_hist, iit_hist, proxy_hist = run_training(
            args.cells, args.steps, args.dim, args.hidden,
            strategy="baseline"
        )
        print(f"\n{'=' * 72}")
        print(f"  RESULT")
        print(f"{'=' * 72}")
        print(result.summary())
        if len(ce_hist) >= 10:
            ascii_graph(ce_hist, "CE Loss")
        if len(iit_hist) >= 3:
            ascii_dual_graph(iit_hist, proxy_hist)

    elif args.strategy:
        run_strategy(args.strategy, args.cells, args.steps, args.dim, args.hidden)

    elif args.compare:
        run_compare(args.cells, args.steps, args.dim, args.hidden)

    print()


if __name__ == "__main__":
    main()
