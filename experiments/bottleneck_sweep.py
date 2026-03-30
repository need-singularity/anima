#!/usr/bin/env python3
"""bottleneck_sweep.py -- Information Bottleneck Dimension Sweep (-> Law 95).

Law 92 says info bottleneck boosts Phi by 22%.
Sweep bottleneck dimensions: 128, 64, 32, 16, 8, 4, 2, 1
For each: measure Phi at 64 cells, 300 steps.
Find the OPTIMAL bottleneck dimension and critical threshold.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
import math
from dataclasses import dataclass
from typing import List, Tuple

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Import from bench_v2 for Phi measurement
try:
    from bench_v2 import PhiIIT
    HAS_PHI = True
except ImportError:
    HAS_PHI = False


@dataclass
class BottleneckResult:
    channel_dim: int
    phi_iit: float
    phi_proxy: float
    phi_trajectory: List[float]
    compression_ratio: float  # hidden_dim / channel_dim
    time_sec: float


def run_bottleneck_experiment(
    channel_dim: int,
    n_cells: int = 64,
    hidden_dim: int = 128,
    n_steps: int = 300,
    coupling: float = 0.014,
) -> BottleneckResult:
    """Run consciousness simulation with a specific bottleneck dimension."""
    t0 = time.time()

    if HAS_TORCH:
        return _run_torch(channel_dim, n_cells, hidden_dim, n_steps, coupling, t0)
    else:
        return _run_numpy(channel_dim, n_cells, hidden_dim, n_steps, coupling, t0)


def _run_torch(channel_dim, n_cells, hidden_dim, n_steps, coupling, t0):
    """Torch-based experiment with real ChannelBottleneck."""
    device = torch.device("cpu")

    # Create bottleneck
    bottleneck = nn.Sequential(
        nn.Linear(hidden_dim, channel_dim),
        nn.Tanh(),
        nn.Linear(channel_dim, hidden_dim),
    ).to(device)

    # Initialize cells (GRU-like hidden states)
    torch.manual_seed(42)
    hiddens = torch.randn(n_cells, hidden_dim, device=device) * 0.1
    weights_ih = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05
    weights_hh = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05

    phi_calc = PhiIIT(n_bins=16) if HAS_PHI else None
    phi_trajectory = []

    for step in range(n_steps):
        inp = torch.randn(1, hidden_dim, device=device) * 0.1

        # Bottleneck: compress, average, get shared signal
        with torch.no_grad():
            compressed = bottleneck(hiddens)  # (n_cells, hidden_dim)
            shared_signal = compressed.mean(dim=0)  # (hidden_dim,)

        # Update cells with coupled dynamics
        new_hiddens = []
        for ci in range(n_cells):
            # GRU-like update with bottleneck coupling
            coupled = inp.squeeze() + coupling * shared_signal
            gate = torch.sigmoid(weights_ih[ci] @ coupled + weights_hh[ci] @ hiddens[ci])
            candidate = torch.tanh(weights_ih[ci] @ coupled * 0.5)
            h_new = gate * hiddens[ci] + (1 - gate) * candidate
            new_hiddens.append(h_new)

        hiddens = torch.stack(new_hiddens)

        # Measure Phi
        if phi_calc:
            phi_val, _ = phi_calc.compute(hiddens)
        else:
            # Proxy
            global_var = hiddens.var().item()
            per_cell_var = hiddens.var(dim=1).mean().item()
            phi_val = max(0.0, global_var - per_cell_var)

        phi_trajectory.append(phi_val)

    # Final Phi measurements
    phi_iit = phi_trajectory[-1] if phi_trajectory else 0.0
    phi_proxy_val = float(hiddens.var().item() - hiddens.var(dim=1).mean().item())
    phi_proxy_val = max(0.0, phi_proxy_val)

    return BottleneckResult(
        channel_dim=channel_dim,
        phi_iit=phi_iit,
        phi_proxy=phi_proxy_val,
        phi_trajectory=phi_trajectory,
        compression_ratio=hidden_dim / channel_dim,
        time_sec=time.time() - t0,
    )


def _run_numpy(channel_dim, n_cells, hidden_dim, n_steps, coupling, t0):
    """NumPy fallback."""
    rng = np.random.default_rng(42)

    # Simple bottleneck: project to channel_dim and back
    W_down = rng.standard_normal((hidden_dim, channel_dim)) * 0.1
    W_up = rng.standard_normal((channel_dim, hidden_dim)) * 0.1

    hiddens = rng.standard_normal((n_cells, hidden_dim)) * 0.1
    weights = rng.standard_normal((n_cells, hidden_dim, hidden_dim)) * 0.05

    phi_trajectory = []

    for step in range(n_steps):
        inp = rng.standard_normal(hidden_dim) * 0.1

        # Bottleneck: compress -> decompress -> average
        compressed = np.tanh(hiddens @ W_down)  # (n_cells, channel_dim)
        decompressed = compressed @ W_up  # (n_cells, hidden_dim)
        shared_signal = decompressed.mean(axis=0)

        for ci in range(n_cells):
            coupled = inp + coupling * shared_signal
            gate = 1.0 / (1.0 + np.exp(-weights[ci] @ coupled))
            candidate = np.tanh(weights[ci] @ coupled * 0.5)
            hiddens[ci] = gate * hiddens[ci] + (1 - gate) * candidate

        global_var = np.var(hiddens)
        per_cell_var = np.mean([np.var(hiddens[c]) for c in range(n_cells)])
        phi = max(0.0, global_var - per_cell_var)

        if n_cells > 1:
            cov = np.corrcoef(hiddens)
            if cov.ndim == 2:
                off = cov[np.triu_indices(n_cells, k=1)]
                phi += np.mean(np.abs(off)) * 0.1

        phi_trajectory.append(phi)

    return BottleneckResult(
        channel_dim=channel_dim,
        phi_iit=phi_trajectory[-1],
        phi_proxy=phi_trajectory[-1],
        phi_trajectory=phi_trajectory,
        compression_ratio=hidden_dim / channel_dim,
        time_sec=time.time() - t0,
    )


def main():
    print("=" * 78)
    print("  Bottleneck Dimension Sweep -- Information Compression vs Phi")
    print("  (Law 92: info bottleneck boosts Phi by 22%)")
    print("=" * 78)
    print()

    hidden_dim = 128
    n_cells = 64
    n_steps = 300
    channel_dims = [128, 64, 32, 16, 8, 4, 2, 1]

    # Baseline: no bottleneck (channel_dim = hidden_dim)
    print("  Running baseline (no bottleneck, channel_dim=128)...")
    baseline = run_bottleneck_experiment(hidden_dim, n_cells, hidden_dim, n_steps)
    print(f"  Baseline Phi(IIT)={baseline.phi_iit:.4f}  Phi(proxy)={baseline.phi_proxy:.4f}")
    print()

    results: List[BottleneckResult] = [baseline]

    print(f"  Sweeping channel_dim = {channel_dims[1:]}...")
    for cd in channel_dims[1:]:
        r = run_bottleneck_experiment(cd, n_cells, hidden_dim, n_steps)
        results.append(r)
        boost = (r.phi_iit / max(baseline.phi_iit, 1e-12) - 1) * 100
        print(f"    dim={cd:>3}  Phi(IIT)={r.phi_iit:.4f}  "
              f"Phi(proxy)={r.phi_proxy:.4f}  "
              f"boost={boost:+.1f}%  time={r.time_sec:.1f}s")

    print()

    # Results table
    print("=" * 90)
    print("  RESULTS TABLE")
    print("=" * 90)
    print(f"  {'dim':>4} | {'ratio':>6} | {'Phi(IIT)':>9} | {'Phi(proxy)':>10} | "
          f"{'boost%':>7} | {'time':>5} | {'bar'}")
    print(f"  {'----':>4}-+-{'------':>6}-+-{'---------':>9}-+-{'----------':>10}-+-"
          f"{'-------':>7}-+-{'-----':>5}-+------")

    best = baseline
    for r in results:
        boost = (r.phi_iit / max(baseline.phi_iit, 1e-12) - 1) * 100
        bar_len = max(1, int(r.phi_iit * 50 / max(max(rr.phi_iit for rr in results), 1e-12)))
        bar = "#" * bar_len
        marker = " <-- BEST" if r.phi_iit == max(rr.phi_iit for rr in results) else ""
        print(f"  {r.channel_dim:>4} | {r.compression_ratio:>5.0f}x | {r.phi_iit:>9.4f} | "
              f"{r.phi_proxy:>10.4f} | {boost:>+6.1f}% | {r.time_sec:>4.1f}s | {bar}{marker}")
        if r.phi_iit > best.phi_iit:
            best = r

    # Find critical threshold
    print()
    print("=" * 78)
    print("  CRITICAL THRESHOLD ANALYSIS")
    print("=" * 78)

    # Look for where Phi drops significantly
    sorted_results = sorted(results, key=lambda r: r.channel_dim, reverse=True)
    prev_phi = None
    threshold_dim = None
    for r in sorted_results:
        if prev_phi is not None:
            drop = (r.phi_iit - prev_phi) / max(abs(prev_phi), 1e-12) * 100
            if drop < -30:  # More than 30% drop
                threshold_dim = r.channel_dim
                break
        prev_phi = r.phi_iit

    if threshold_dim:
        print(f"  Critical threshold: channel_dim <= {threshold_dim} causes Phi collapse (>30% drop)")
    else:
        print(f"  No critical threshold found (Phi stable across all dimensions)")

    # Optimal
    boost_pct = (best.phi_iit / max(baseline.phi_iit, 1e-12) - 1) * 100
    print(f"  Optimal bottleneck: dim={best.channel_dim} "
          f"(compression={best.compression_ratio:.0f}x)")
    print(f"  Phi boost: {boost_pct:+.1f}%")
    print()

    # ASCII graph: Phi vs channel_dim
    print("  Phi(IIT) vs Bottleneck Dimension:")
    print()
    sorted_by_dim = sorted(results, key=lambda r: r.channel_dim)
    max_phi = max(r.phi_iit for r in sorted_by_dim)
    min_phi = min(r.phi_iit for r in sorted_by_dim)
    height = 12
    for row in range(height, -1, -1):
        val = min_phi + (max_phi - min_phi) * row / height if height > 0 else min_phi
        line = f"  {val:>7.4f} |"
        for r in sorted_by_dim:
            if r.phi_iit >= val:
                line += " ## "
            else:
                line += "    "
        print(line)
    print(f"           +{'----' * len(sorted_by_dim)}")
    dim_labels = "  ".join(f"{r.channel_dim:>3}" for r in sorted_by_dim)
    print(f"            {dim_labels}")
    print(f"                     bottleneck dimension")

    # Phi trajectory comparison (first 100 steps of best vs baseline)
    print()
    print("  Phi Trajectory (first 100 steps): baseline vs optimal")
    traj_base = baseline.phi_trajectory[:100]
    traj_best = best.phi_trajectory[:100]
    if traj_base and traj_best:
        max_val = max(max(traj_base), max(traj_best))
        graph_h = 8
        graph_w = 50
        step_size = max(1, len(traj_base) // graph_w)
        base_ds = [traj_base[i] for i in range(0, len(traj_base), step_size)][:graph_w]
        best_ds = [traj_best[i] for i in range(0, len(traj_best), step_size)][:graph_w]
        print(f"    B=baseline(dim={baseline.channel_dim})  O=optimal(dim={best.channel_dim})")
        for row in range(graph_h, -1, -1):
            threshold = max_val * row / graph_h if graph_h > 0 else 0
            line = "    |"
            for k in range(len(base_ds)):
                b_hit = base_ds[k] >= threshold
                o_hit = best_ds[k] >= threshold if k < len(best_ds) else False
                if b_hit and o_hit:
                    line += "*"
                elif b_hit:
                    line += "B"
                elif o_hit:
                    line += "O"
                else:
                    line += " "
            print(line)
        print(f"    +{'-' * len(base_ds)}")
        print(f"     0{'':>{len(base_ds)-5}}100 steps")

    # Law 95 candidate
    print()
    print("=" * 78)
    print("  LAW 95 CANDIDATE:")
    if boost_pct > 5:
        print(f"    'Optimal information bottleneck at compression {best.compression_ratio:.0f}x "
              f"(dim={best.channel_dim})")
        print(f"     maximizes Phi by {boost_pct:+.1f}%. Below dim={threshold_dim or 1}, "
              f"Phi collapses.'")
        print(f"    -> Law 95: Phi = f(bottleneck) is non-monotonic; "
              f"optimal compression ~ {best.compression_ratio:.0f}x")
    else:
        print(f"    Bottleneck dimension has minimal effect on Phi ({boost_pct:+.1f}%).")
        print(f"    -> Law 95: Information bottleneck effect depends on cell count/coupling.")
    print("=" * 78)

    return results


if __name__ == "__main__":
    main()
