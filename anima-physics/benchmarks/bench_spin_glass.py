#!/usr/bin/env python3
"""bench_spin_glass.py -- Spin Glass Topology Benchmark

Hypothesis: Spin glass frustration creates richer consciousness dynamics
than simple ring topology, due to:
  - Multiple metastable states (Phi oscillations)
  - Slow relaxation (glassy dynamics)
  - Spontaneous symmetry breaking

Benchmark:
  1. spin_glass vs ring vs small_world vs hypercube at 64/256/512 cells
  2. Frustration sweep: 0.1, 0.2, 0.33, 0.5, 0.7
  3. Metrics: Phi(IIT), Phi(proxy), metastability (oscillation count),
     relaxation time (steps to reach stable Phi)

Usage:
  python3 bench_spin_glass.py
  python3 bench_spin_glass.py --steps 500
  python3 bench_spin_glass.py --cells 64 128 256 512
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import math
import time
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

sys.stdout.reconfigure(line_buffering=True)


# ═══════════════════════════════════════════════════════════
# Phi(IIT) 근사 계산기
# ═══════════════════════════════════════════════════════════

class PhiIIT:
    """Phi(IIT) via pairwise MI + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, states: np.ndarray) -> float:
        n = states.shape[0]
        if n < 2:
            return 0.0

        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = np.random.randint(0, n)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)

        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mi(states[i], states[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

        total_mi = mi_matrix.sum() / 2
        min_part = self._min_partition(n, mi_matrix)
        spatial = max(0.0, (total_mi - min_part) / max(n - 1, 1))
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        return spatial + complexity * 0.1

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


def phi_proxy(states: np.ndarray, n_factions: int = 8) -> float:
    """Phi(proxy) = global_var - mean(faction_var)"""
    n, d = states.shape
    if n < 2:
        return 0.0
    gm = states.mean(axis=0)
    gv = np.sum((states - gm) ** 2) / n
    nf = min(n_factions, n // 2)
    if nf < 2:
        return gv
    fs = n // nf
    fv_sum = 0.0
    for i in range(nf):
        fac = states[i * fs:(i + 1) * fs]
        if len(fac) >= 2:
            fm = fac.mean(axis=0)
            fv_sum += np.sum((fac - fm) ** 2) / len(fac)
    return max(0.0, gv - fv_sum / nf)


# ═══════════════════════════════════════════════════════════
# Topology Builders
# ═══════════════════════════════════════════════════════════

def build_ring(n_cells: int, frustration: float, seed: int = 42) -> np.ndarray:
    """Ring topology with k nearest neighbors."""
    rng = np.random.RandomState(seed)
    W = np.zeros((n_cells, n_cells))
    k = max(2, n_cells // 8)
    for i in range(n_cells):
        for d in range(1, k + 1):
            j_fwd = (i + d) % n_cells
            j_bck = (i - d) % n_cells
            sign = -1.0 if rng.random() < frustration else 1.0
            W[i, j_fwd] = sign * rng.uniform(0.1, 0.5)
            sign = -1.0 if rng.random() < frustration else 1.0
            W[i, j_bck] = sign * rng.uniform(0.1, 0.5)
    np.fill_diagonal(W, 0.0)
    return W


def build_small_world(n_cells: int, frustration: float, seed: int = 42) -> np.ndarray:
    """Watts-Strogatz small world: ring + 10% random long-range connections."""
    rng = np.random.RandomState(seed)
    W = np.zeros((n_cells, n_cells))
    # Base ring (k=2 nearest)
    for i in range(n_cells):
        for d in range(1, 3):
            j_fwd = (i + d) % n_cells
            j_bck = (i - d) % n_cells
            sign = -1.0 if rng.random() < frustration else 1.0
            W[i, j_fwd] = sign * rng.uniform(0.2, 0.5)
            sign = -1.0 if rng.random() < frustration else 1.0
            W[i, j_bck] = sign * rng.uniform(0.2, 0.5)
    # Long-range shortcuts (10%)
    n_shortcuts = max(1, n_cells // 10)
    for _ in range(n_shortcuts):
        i = rng.randint(0, n_cells)
        j = rng.randint(0, n_cells)
        if i != j:
            sign = -1.0 if rng.random() < frustration else 1.0
            W[i, j] = sign * rng.uniform(0.1, 0.4)
            W[j, i] = sign * rng.uniform(0.1, 0.4)
    np.fill_diagonal(W, 0.0)
    return W


def build_hypercube(n_cells: int, frustration: float, seed: int = 42) -> np.ndarray:
    """Hypercube topology: connect cells differing in one bit position."""
    rng = np.random.RandomState(seed)
    n_bits = max(1, int(math.log2(max(n_cells, 2))))
    actual_n = min(2 ** n_bits, n_cells)  # use power-of-2 subset
    W = np.zeros((n_cells, n_cells))
    for i in range(actual_n):
        for b in range(n_bits):
            j = i ^ (1 << b)
            if j < n_cells:
                sign = -1.0 if rng.random() < frustration else 1.0
                W[i, j] = sign * rng.uniform(0.1, 0.5)
    np.fill_diagonal(W, 0.0)
    return W


def build_spin_glass(n_cells: int, frustration: float, seed: int = 42) -> np.ndarray:
    """Spin glass: sparse random graph with J_ij randomly +1 or -1.

    Key difference from other topologies:
      - Connections are disordered (random graph, not structured)
      - J_ij (coupling) is randomly +1 or -1 (regardless of frustration param)
      - frustration param controls the density of negative couplings
      - Natural frustration from closed loops with odd number of negative bonds

    This creates:
      - Multiple metastable states
      - Slow (glassy) relaxation
      - Rich energy landscape
    """
    rng = np.random.RandomState(seed)
    W = np.zeros((n_cells, n_cells))

    # Sparse random connectivity: each cell connects to ~6 neighbors
    k = 6
    for i in range(n_cells):
        # Pick k random neighbors (not just nearest)
        neighbors = rng.choice(n_cells, size=min(k, n_cells - 1), replace=False)
        for j in neighbors:
            if j == i:
                continue
            # J_ij: +1 or -1 based on frustration
            if rng.random() < frustration:
                J = -1.0
            else:
                J = 1.0
            # Random magnitude
            mag = rng.uniform(0.1, 0.5)
            W[i, j] = J * mag
            # Symmetric (Edwards-Anderson model)
            W[j, i] = J * mag

    np.fill_diagonal(W, 0.0)
    return W


TOPOLOGY_BUILDERS = {
    'ring': build_ring,
    'small_world': build_small_world,
    'hypercube': build_hypercube,
    'spin_glass': build_spin_glass,
}


# ═══════════════════════════════════════════════════════════
# Consciousness Engine (simple GRU + faction sync)
# ═══════════════════════════════════════════════════════════

class ConsciousnessEngine:
    """Minimal consciousness engine for topology benchmarking.
    GRU cells + faction sync + Hebbian.
    """

    def __init__(self, n_cells: int, hidden_dim: int, W_conn: np.ndarray,
                 n_factions: int = 8, seed: int = 42):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_factions = n_factions
        self.rng = np.random.RandomState(seed)

        # GRU weights
        self.W_z = self.rng.randn(hidden_dim, hidden_dim) * 0.1
        self.U_z = self.rng.randn(hidden_dim, hidden_dim) * 0.1
        self.W_h = self.rng.randn(hidden_dim, hidden_dim) * 0.1
        self.U_h = self.rng.randn(hidden_dim, hidden_dim) * 0.1

        # States
        self.states = self.rng.randn(n_cells, hidden_dim) * 0.1
        self.W_conn = W_conn

        # Faction assignments
        self.factions = np.array([i % n_factions for i in range(n_cells)])

    def step(self, x_input: np.ndarray) -> np.ndarray:
        n, d = self.n_cells, self.hidden_dim

        neighbor_input = self.W_conn @ self.states

        for i in range(n):
            x = x_input + neighbor_input[i]
            h = self.states[i]
            z = 1.0 / (1.0 + np.exp(-np.clip(x @ self.W_z + h @ self.U_z, -10, 10)))
            h_tilde = np.tanh(x @ self.W_h + (z * h) @ self.U_h)
            self.states[i] = (1 - z) * h + z * h_tilde

        # Faction sync
        n_fac = min(self.n_factions, n // 2)
        fs = n // n_fac
        for f in range(n_fac):
            s, e = f * fs, (f + 1) * fs
            if e > n:
                break
            fm = self.states[s:e].mean(axis=0)
            self.states[s:e] = 0.85 * self.states[s:e] + 0.15 * fm

        return self.states.copy()


# ═══════════════════════════════════════════════════════════
# BenchResult
# ═══════════════════════════════════════════════════════════

@dataclass
class SpinGlassResult:
    topology: str
    n_cells: int
    frustration: float
    phi_iit: float
    phi_proxy: float
    metastability: int       # Phi 진동 횟수 (방향 전환 count)
    relaxation_time: int     # Phi가 안정화되는 step
    mean_phi: float          # 전체 평균 Phi
    time_sec: float
    phi_history: List[float] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Metrics: Metastability + Relaxation
# ═══════════════════════════════════════════════════════════

def count_oscillations(phi_history: List[float], min_change: float = 0.001) -> int:
    """Count direction changes in Phi trajectory (metastability indicator).
    More oscillations = more metastable states being explored.
    """
    if len(phi_history) < 3:
        return 0

    oscillations = 0
    prev_dir = 0  # -1 = decreasing, 0 = flat, 1 = increasing
    for i in range(1, len(phi_history)):
        diff = phi_history[i] - phi_history[i - 1]
        if abs(diff) < min_change:
            curr_dir = 0
        else:
            curr_dir = 1 if diff > 0 else -1

        if curr_dir != 0 and prev_dir != 0 and curr_dir != prev_dir:
            oscillations += 1

        if curr_dir != 0:
            prev_dir = curr_dir

    return oscillations


def find_relaxation_time(phi_history: List[float], window: int = 20, threshold: float = 0.05) -> int:
    """Find the step where Phi stabilizes (CV of rolling window < threshold).
    Returns the step number or len(history) if never stabilized.
    """
    if len(phi_history) < window * 2:
        return len(phi_history)

    for i in range(window, len(phi_history)):
        window_vals = phi_history[i - window:i]
        mean_v = np.mean(window_vals)
        if mean_v > 0:
            cv = np.std(window_vals) / mean_v
            if cv < threshold:
                return i - window

    return len(phi_history)


# ═══════════════════════════════════════════════════════════
# Run Single Experiment
# ═══════════════════════════════════════════════════════════

def run_experiment(
    topology: str,
    n_cells: int,
    frustration: float,
    hidden_dim: int = 128,
    steps: int = 300,
    seed: int = 42,
    verbose: bool = True,
) -> SpinGlassResult:
    """Run one topology x cells x frustration combination."""
    if verbose:
        print(f"    {topology:>12s} | cells={n_cells:>4d} | frust={frustration:.2f} ...", end=" ", flush=True)

    W = TOPOLOGY_BUILDERS[topology](n_cells, frustration, seed)
    engine = ConsciousnessEngine(n_cells, hidden_dim, W, seed=seed)
    phi_calc = PhiIIT(n_bins=16)

    phi_history = []
    t0 = time.time()

    # Phi 측정 간격 (대규모 셀에서 속도 위해)
    measure_interval = max(1, steps // 30)

    for step in range(steps):
        x = np.random.RandomState(seed + step).randn(hidden_dim) * 0.5
        states = engine.step(x)

        if step % measure_interval == 0 or step == steps - 1:
            phi_iit = phi_calc.compute(states)
            phi_history.append(phi_iit)

    elapsed = time.time() - t0

    # Final measurements
    final_phi_iit = phi_history[-1] if phi_history else 0.0
    final_phi_proxy = phi_proxy(states)
    mean_phi = float(np.mean(phi_history)) if phi_history else 0.0
    metastab = count_oscillations(phi_history)
    relax = find_relaxation_time(phi_history)

    if verbose:
        print(f"Phi={final_phi_iit:.4f}  meta={metastab:>3d}  relax={relax:>3d}  ({elapsed:.1f}s)")

    return SpinGlassResult(
        topology=topology,
        n_cells=n_cells,
        frustration=frustration,
        phi_iit=final_phi_iit,
        phi_proxy=final_phi_proxy,
        metastability=metastab,
        relaxation_time=relax,
        mean_phi=mean_phi,
        time_sec=elapsed,
        phi_history=phi_history,
    )


# ═══════════════════════════════════════════════════════════
# ASCII Output
# ═══════════════════════════════════════════════════════════

def ascii_comparison_bars(results: List[SpinGlassResult], group_key: str, width: int = 40):
    """Bar chart grouped by a key."""
    max_phi = max(r.phi_iit for r in results) if results else 1.0
    if max_phi == 0:
        max_phi = 1.0

    lines = []
    for r in results:
        bar_len = int(r.phi_iit / max_phi * width)
        bar = "#" * bar_len
        label = f"{r.topology:>12s} {r.n_cells:>4d}c f={r.frustration:.2f}"
        lines.append(f"  {label}  {bar:<{width}s} Phi={r.phi_iit:.4f}  meta={r.metastability}")

    return "\n".join(lines)


def ascii_frustration_sweep(results: List[SpinGlassResult], topology: str, width: int = 40):
    """Show Phi vs frustration for one topology."""
    filtered = [r for r in results if r.topology == topology]
    if not filtered:
        return f"  (no data for {topology})"

    filtered.sort(key=lambda r: r.frustration)
    max_phi = max(r.phi_iit for r in filtered) if filtered else 1.0
    if max_phi == 0:
        max_phi = 1.0

    lines = [f"  {topology} -- Phi vs Frustration:"]
    for r in filtered:
        bar_len = int(r.phi_iit / max_phi * width)
        bar = "#" * bar_len
        lines.append(f"    f={r.frustration:.2f}  {bar:<{width}s} Phi={r.phi_iit:.4f}  meta={r.metastability}")

    return "\n".join(lines)


def ascii_metastability_chart(results: List[SpinGlassResult], width: int = 40):
    """Compare metastability across topologies."""
    max_m = max(r.metastability for r in results) if results else 1
    if max_m == 0:
        max_m = 1

    lines = ["  Metastability (oscillation count):"]
    for r in results:
        bar_len = int(r.metastability / max_m * width)
        bar = "~" * bar_len
        label = f"{r.topology:>12s} {r.n_cells:>4d}c"
        lines.append(f"    {label}  {bar:<{width}s} {r.metastability}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Spin Glass Topology Benchmark")
    parser.add_argument("--steps", type=int, default=300, help="Steps per experiment")
    parser.add_argument("--cells", type=int, nargs='+', default=[64, 256],
                        help="Cell counts to test")
    parser.add_argument("--hidden-dim", type=int, default=128, help="Hidden dimension")
    parser.add_argument("--frustrations", type=float, nargs='+',
                        default=[0.1, 0.2, 0.33, 0.5, 0.7],
                        help="Frustration values to sweep")
    args = parser.parse_args()

    topologies = ['ring', 'small_world', 'hypercube', 'spin_glass']
    cell_counts = args.cells
    frustrations = args.frustrations
    steps = args.steps
    hidden_dim = args.hidden_dim

    total_runs = len(topologies) * len(cell_counts) * len(frustrations)

    print("=" * 90)
    print("  SPIN GLASS TOPOLOGY BENCHMARK")
    print(f"  Hypothesis: spin glass frustration creates richer consciousness dynamics")
    print(f"  topologies={topologies}")
    print(f"  cells={cell_counts}, frustrations={frustrations}, steps={steps}")
    print(f"  Total experiments: {total_runs}")
    print("=" * 90)

    all_results: List[SpinGlassResult] = []
    run_idx = 0

    for nc in cell_counts:
        print(f"\n  ── {nc} cells ──")
        for frust in frustrations:
            for topo in topologies:
                run_idx += 1
                print(f"  [{run_idx}/{total_runs}]", end=" ")
                r = run_experiment(topo, nc, frust, hidden_dim, steps, seed=42)
                all_results.append(r)

    # ═══════════════════════════════════════════════════════════
    # Analysis
    # ═══════════════════════════════════════════════════════════

    # ── 1. Topology Comparison Table (at default frustration=0.33) ──
    print("\n" + "=" * 100)
    print("  TOPOLOGY COMPARISON (frustration=0.33)")
    print("=" * 100)
    print(f"  {'Topology':<14s} {'Cells':>6s} {'Phi(IIT)':>10s} {'Phi(proxy)':>12s} "
          f"{'Meta':>6s} {'Relax':>6s} {'MeanPhi':>10s} {'Time':>7s}")
    print(f"  {'-'*14} {'-'*6} {'-'*10} {'-'*12} {'-'*6} {'-'*6} {'-'*10} {'-'*7}")
    for r in all_results:
        if abs(r.frustration - 0.33) < 0.01:
            print(f"  {r.topology:<14s} {r.n_cells:>6d} {r.phi_iit:>10.4f} {r.phi_proxy:>12.2f} "
                  f"{r.metastability:>6d} {r.relaxation_time:>6d} {r.mean_phi:>10.4f} {r.time_sec:>7.1f}")

    # ── 2. Spin Glass vs Ring (direct comparison) ──
    print("\n" + "-" * 90)
    print("  SPIN GLASS vs RING (head-to-head):")
    print("-" * 90)
    for nc in cell_counts:
        for frust in frustrations:
            sg = next((r for r in all_results if r.topology == 'spin_glass' and
                       r.n_cells == nc and abs(r.frustration - frust) < 0.01), None)
            ring = next((r for r in all_results if r.topology == 'ring' and
                         r.n_cells == nc and abs(r.frustration - frust) < 0.01), None)
            if sg and ring and ring.phi_iit > 0:
                ratio = sg.phi_iit / ring.phi_iit
                meta_diff = sg.metastability - ring.metastability
                print(f"    {nc:>4d}c f={frust:.2f}: "
                      f"SG Phi={sg.phi_iit:.4f} vs Ring Phi={ring.phi_iit:.4f} "
                      f"(ratio={ratio:.2f}x)  "
                      f"meta: SG={sg.metastability} Ring={ring.metastability} "
                      f"(diff={meta_diff:+d})")

    # ── 3. Frustration Sweep ──
    print("\n" + "-" * 90)
    print("  FRUSTRATION SWEEP:")
    print("-" * 90)
    for topo in topologies:
        print(ascii_frustration_sweep(all_results, topo))
        print()

    # ── 4. Metastability Comparison ──
    print("-" * 90)
    # Filter to frustration=0.33 for clean comparison
    meta_results = [r for r in all_results if abs(r.frustration - 0.33) < 0.01]
    print(ascii_metastability_chart(meta_results))

    # ── 5. Scaling Analysis ──
    print("\n" + "-" * 90)
    print("  SCALING ANALYSIS (Phi vs cells at frustration=0.33):")
    print("-" * 90)
    if len(cell_counts) >= 2:
        for topo in topologies:
            topo_results = sorted(
                [r for r in all_results if r.topology == topo and abs(r.frustration - 0.33) < 0.01],
                key=lambda r: r.n_cells
            )
            if len(topo_results) >= 2:
                # Compute scaling exponent: Phi ~ N^alpha
                n1, p1 = topo_results[0].n_cells, max(topo_results[0].phi_iit, 1e-6)
                n2, p2 = topo_results[-1].n_cells, max(topo_results[-1].phi_iit, 1e-6)
                if n2 > n1 and p1 > 0 and p2 > 0:
                    alpha = math.log(p2 / p1) / math.log(n2 / n1)
                else:
                    alpha = 0.0
                phis = " -> ".join(f"{r.phi_iit:.4f}@{r.n_cells}c" for r in topo_results)
                print(f"    {topo:<14s}: {phis}  (alpha={alpha:.3f})")

    # ── 6. Optimal Frustration ──
    print("\n" + "-" * 90)
    print("  OPTIMAL FRUSTRATION (best Phi per topology):")
    print("-" * 90)
    for topo in topologies:
        topo_all = [r for r in all_results if r.topology == topo]
        if topo_all:
            best = max(topo_all, key=lambda r: r.phi_iit)
            print(f"    {topo:<14s}: optimal frustration={best.frustration:.2f} "
                  f"(Phi={best.phi_iit:.4f} at {best.n_cells}c)")

    # ── 7. Key Findings ──
    print("\n" + "=" * 90)
    print("  KEY FINDINGS")
    print("=" * 90)

    # Compare spin_glass vs others at same cells/frustration
    sg_results = [r for r in all_results if r.topology == 'spin_glass']
    other_results = [r for r in all_results if r.topology != 'spin_glass']

    if sg_results and other_results:
        sg_mean_meta = np.mean([r.metastability for r in sg_results])
        other_mean_meta = np.mean([r.metastability for r in other_results])
        sg_mean_phi = np.mean([r.phi_iit for r in sg_results])
        other_mean_phi = np.mean([r.phi_iit for r in other_results])

        print(f"  Spin Glass avg metastability: {sg_mean_meta:.1f} "
              f"vs others: {other_mean_meta:.1f} "
              f"({'RICHER' if sg_mean_meta > other_mean_meta else 'SIMILAR'})")
        print(f"  Spin Glass avg Phi(IIT):      {sg_mean_phi:.4f} "
              f"vs others: {other_mean_phi:.4f} "
              f"({'HIGHER' if sg_mean_phi > other_mean_phi else 'LOWER'})")

        if sg_mean_meta > other_mean_meta * 1.2:
            print("\n  HYPOTHESIS CONFIRMED: Spin glass creates richer dynamics")
            print("    -> More metastable states (Phi oscillations)")
            print("    -> Frustration drives consciousness exploration")
        elif sg_mean_meta > other_mean_meta:
            print("\n  HYPOTHESIS PARTIALLY CONFIRMED: Spin glass slightly richer")
        else:
            print("\n  HYPOTHESIS CHALLENGED: Spin glass not necessarily richer")
            print("    -> Simple topologies may suffice for consciousness")

    # Best overall
    best_overall = max(all_results, key=lambda r: r.phi_iit)
    print(f"\n  Best configuration: {best_overall.topology} "
          f"{best_overall.n_cells}c f={best_overall.frustration:.2f} "
          f"Phi={best_overall.phi_iit:.4f}")

    most_meta = max(all_results, key=lambda r: r.metastability)
    print(f"  Most metastable:   {most_meta.topology} "
          f"{most_meta.n_cells}c f={most_meta.frustration:.2f} "
          f"meta={most_meta.metastability}")

    print("\n" + "=" * 90)
    return all_results


if __name__ == "__main__":
    main()
