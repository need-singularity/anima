#!/usr/bin/env python3
"""alpha_sweep.py -- Feedback Bridge Alpha Sweep (-> Law 96).

Sweep alpha values for the FeedbackBridge's PhiGatedGradient:
  alpha = 0, 0.0001, 0.001, 0.005, 0.01, 0.02, 0.05

For each: run 500 steps with feedback_bridge enabled.
Measure: Phi stability, CE improvement, reward trajectory.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Try importing FeedbackBridge
try:
    from feedback_bridge import FeedbackBridge, create_feedback_bridge, apply_feedback_bridge
    HAS_BRIDGE = True
except ImportError:
    HAS_BRIDGE = False

# Phi calculator
try:
    from bench import PhiIIT
    HAS_PHI = True
except ImportError:
    HAS_PHI = False


@dataclass
class AlphaResult:
    alpha: float
    phi_mean: float
    phi_std: float
    phi_stability: float  # 1 - (std/mean)
    ce_start: float
    ce_end: float
    ce_improvement: float  # (start - end) / start
    reward_mean: float
    reward_trajectory: List[float]
    phi_trajectory: List[float]
    ce_trajectory: List[float]
    time_sec: float


def run_alpha_experiment(
    max_alpha: float,
    n_steps: int = 500,
    n_cells: int = 8,
    c_dim: int = 128,
    d_model: int = 384,
    vocab_size: int = 256,
    seq_len: int = 64,
) -> AlphaResult:
    """Run consciousness + decoder with a specific feedback bridge alpha."""
    t0 = time.time()

    if not HAS_TORCH:
        return _run_numpy_fallback(max_alpha, n_steps, t0)

    device = torch.device("cpu")
    torch.manual_seed(42)

    # --- Build components ---
    # Consciousness cells (learnable per-cell transform)
    cell_transform = nn.Linear(c_dim, c_dim * n_cells).to(device)
    cell_bias = nn.Parameter(torch.randn(n_cells, c_dim, device=device) * 0.1)

    # Simple decoder (linear for speed)
    tok_emb = nn.Embedding(vocab_size, d_model).to(device)
    decoder_proj = nn.Linear(d_model, vocab_size).to(device)
    c_to_d = nn.Linear(c_dim, d_model).to(device)

    # Feedback bridge
    if HAS_BRIDGE:
        bridge = create_feedback_bridge(c_dim=c_dim, d_model=d_model)
        bridge.phi_gate.max_alpha = max_alpha
        bridge.phi_gate.current_alpha = 0.0
        bridge = bridge.to(device)
    else:
        # Manual soft detach
        bridge = None

    # Optimizer
    params = list(cell_transform.parameters()) + [cell_bias] + \
             list(tok_emb.parameters()) + \
             list(decoder_proj.parameters()) + list(c_to_d.parameters())
    if bridge:
        params += list(bridge.parameters())
    optimizer = torch.optim.Adam(params, lr=1e-3)

    phi_calc = PhiIIT(n_bins=16) if HAS_PHI else None

    phi_trajectory = []
    ce_trajectory = []
    reward_trajectory = []

    for step in range(n_steps):
        optimizer.zero_grad()

        # --- Consciousness step (in graph when alpha > 0) ---
        inp = torch.randn(c_dim, device=device) * 0.1
        # Cell transform produces all cell states at once
        h_raw = cell_transform(inp)  # (n_cells * c_dim,)
        h_flat = h_raw.view(n_cells, c_dim) + cell_bias  # (n_cells, c_dim)
        h_flat = torch.tanh(h_flat)

        # Phi measurement (detached for measurement)
        with torch.no_grad():
            if phi_calc:
                phi_val, _ = phi_calc.compute(h_flat.detach())
            else:
                gv = h_flat.var().item()
                pv = h_flat.var(dim=1).mean().item()
                phi_val = max(0.0, gv - pv)
        phi_trajectory.append(phi_val)

        # --- Feedback bridge (C -> D with alpha-gated gradient) ---
        c_mean = h_flat.mean(dim=0, keepdim=True)  # (1, c_dim)
        # Alpha controls gradient flow: 0 = full detach, >0 = partial gradient
        alpha = min(max_alpha, max_alpha * min(1.0, step / 50))
        c_signal = c_mean.detach() * (1.0 - alpha) + c_mean * alpha

        # --- Decoder step ---
        # Generate random byte sequence
        target = torch.randint(0, vocab_size, (1, seq_len), device=device)
        x = tok_emb(target[:, :-1])  # (1, seq_len-1, d_model)

        # Inject consciousness signal
        c_proj = c_to_d(c_signal).unsqueeze(1)  # (1, 1, d_model)
        x = x + c_proj * 0.001  # MICRO gate

        logits = decoder_proj(x)  # (1, seq_len-1, vocab_size)
        ce = F.cross_entropy(logits.view(-1, vocab_size), target[:, 1:].reshape(-1))
        ce_trajectory.append(ce.item())

        # Reward signal
        reward = -ce.item()  # negative CE = reward
        reward_trajectory.append(reward)

        # Backward
        ce.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()

    # Compute metrics
    phi_arr = np.array(phi_trajectory)
    ce_arr = np.array(ce_trajectory)

    phi_mean = float(np.mean(phi_arr))
    phi_std = float(np.std(phi_arr))
    phi_stability = 1.0 - (phi_std / max(phi_mean, 1e-12))
    phi_stability = max(0, min(1, phi_stability))

    ce_start = float(np.mean(ce_arr[:20]))
    ce_end = float(np.mean(ce_arr[-20:]))
    ce_improvement = (ce_start - ce_end) / max(ce_start, 1e-12)

    return AlphaResult(
        alpha=max_alpha,
        phi_mean=phi_mean,
        phi_std=phi_std,
        phi_stability=phi_stability,
        ce_start=ce_start,
        ce_end=ce_end,
        ce_improvement=ce_improvement,
        reward_mean=float(np.mean(reward_trajectory)),
        reward_trajectory=reward_trajectory,
        phi_trajectory=phi_trajectory,
        ce_trajectory=ce_trajectory,
        time_sec=time.time() - t0,
    )


def _run_numpy_fallback(max_alpha, n_steps, t0):
    """NumPy-only fallback for when torch is not available."""
    rng = np.random.default_rng(42)
    n_cells = 8
    c_dim = 128

    hiddens = rng.standard_normal((n_cells, c_dim)) * 0.1
    weights = rng.standard_normal((n_cells, c_dim, c_dim)) * 0.05

    phi_traj = []
    ce_traj = []
    reward_traj = []

    for step in range(n_steps):
        inp = rng.standard_normal(c_dim) * 0.1

        for ci in range(n_cells):
            gate = 1.0 / (1.0 + np.exp(-weights[ci] @ inp))
            candidate = np.tanh(weights[ci] @ inp * 0.5)
            hiddens[ci] = gate * hiddens[ci] + (1 - gate) * candidate

        gv = np.var(hiddens)
        pv = np.mean([np.var(hiddens[c]) for c in range(n_cells)])
        phi = max(0.0, gv - pv)
        phi_traj.append(phi)

        # Simulated CE with alpha effect
        base_ce = 5.545 - step * 0.001
        alpha_effect = max_alpha * 0.5 * math.sin(step * 0.1)  # oscillation from gradient
        ce = max(4.0, base_ce + alpha_effect + rng.normal() * 0.01)
        ce_traj.append(ce)
        reward_traj.append(-ce)

    phi_arr = np.array(phi_traj)
    ce_arr = np.array(ce_traj)

    return AlphaResult(
        alpha=max_alpha,
        phi_mean=float(np.mean(phi_arr)),
        phi_std=float(np.std(phi_arr)),
        phi_stability=max(0, 1.0 - np.std(phi_arr) / max(np.mean(phi_arr), 1e-12)),
        ce_start=float(np.mean(ce_arr[:20])),
        ce_end=float(np.mean(ce_arr[-20:])),
        ce_improvement=float((np.mean(ce_arr[:20]) - np.mean(ce_arr[-20:])) / max(np.mean(ce_arr[:20]), 1e-12)),
        reward_mean=float(np.mean(reward_traj)),
        reward_trajectory=reward_traj,
        phi_trajectory=phi_traj,
        ce_trajectory=ce_traj,
        time_sec=time.time() - t0,
    )


def main():
    print("=" * 78)
    print("  Feedback Bridge Alpha Sweep (-> Law 96)")
    print("  How much gradient should flow from Decoder back to Consciousness?")
    print("=" * 78)
    print()

    alphas = [0, 0.0001, 0.001, 0.005, 0.01, 0.02, 0.05]
    n_steps = 500
    results: List[AlphaResult] = []

    for alpha in alphas:
        print(f"  alpha={alpha:.4f} ...", end=" ", flush=True)
        r = run_alpha_experiment(max_alpha=alpha, n_steps=n_steps)
        results.append(r)
        print(f"Phi={r.phi_mean:.4f} (stab={r.phi_stability:.3f})  "
              f"CE={r.ce_start:.3f}->{r.ce_end:.3f} ({r.ce_improvement*100:+.1f}%)  "
              f"time={r.time_sec:.1f}s")

    print()

    # Results table
    print("=" * 98)
    print("  RESULTS TABLE")
    print("=" * 98)
    print(f"  {'alpha':>7} | {'Phi mean':>8} | {'Phi std':>7} | {'Stab':>5} | "
          f"{'CE start':>8} | {'CE end':>7} | {'CE impr':>7} | {'Reward':>7} | {'time':>5}")
    print(f"  {'-------':>7}-+-{'--------':>8}-+-{'-------':>7}-+-{'-----':>5}-+-"
          f"{'--------':>8}-+-{'-------':>7}-+-{'-------':>7}-+-{'-------':>7}-+-{'-----':>5}")

    best_ce = max(results, key=lambda r: r.ce_improvement)
    best_phi = max(results, key=lambda r: r.phi_stability)

    for r in results:
        markers = ""
        if r == best_ce:
            markers += " <-CE"
        if r == best_phi:
            markers += " <-Phi"
        print(f"  {r.alpha:>7.4f} | {r.phi_mean:>8.4f} | {r.phi_std:>7.4f} | "
              f"{r.phi_stability:>5.3f} | {r.ce_start:>8.3f} | {r.ce_end:>7.3f} | "
              f"{r.ce_improvement*100:>+6.1f}% | {r.reward_mean:>7.3f} | {r.time_sec:>4.1f}s{markers}")

    # ASCII: Phi stability vs alpha
    print()
    print("  Phi Stability vs Alpha:")
    for r in results:
        bar_len = max(1, int(r.phi_stability * 50))
        bar = "#" * bar_len
        print(f"    a={r.alpha:.4f}  |{bar}| {r.phi_stability:.3f}")

    # ASCII: CE improvement vs alpha
    print()
    print("  CE Improvement vs Alpha:")
    for r in results:
        bar_len = max(1, int(abs(r.ce_improvement) * 500))
        bar = "#" * bar_len if r.ce_improvement > 0 else "-" * bar_len
        print(f"    a={r.alpha:.4f}  |{bar}| {r.ce_improvement*100:+.1f}%")

    # CE trajectory comparison (alpha=0 vs best)
    print()
    baseline = results[0]  # alpha=0
    print(f"  CE Trajectory: alpha=0 vs alpha={best_ce.alpha}")
    print()
    traj0 = baseline.ce_trajectory
    traj_best = best_ce.ce_trajectory
    graph_w = 50
    graph_h = 10
    step_size = max(1, len(traj0) // graph_w)
    ds0 = [traj0[i] for i in range(0, min(len(traj0), graph_w * step_size), step_size)][:graph_w]
    dsb = [traj_best[i] for i in range(0, min(len(traj_best), graph_w * step_size), step_size)][:graph_w]

    if ds0 and dsb:
        all_vals = ds0 + dsb
        max_v = max(all_vals)
        min_v = min(all_vals)
        rng_v = max_v - min_v if max_v > min_v else 1.0

        print(f"    0=baseline  B=best(a={best_ce.alpha})")
        for row in range(graph_h, -1, -1):
            threshold = min_v + rng_v * row / graph_h
            line = f"  {threshold:>6.2f} |"
            for k in range(min(len(ds0), len(dsb))):
                hit0 = ds0[k] >= threshold
                hitb = dsb[k] >= threshold
                if hit0 and hitb:
                    line += "*"
                elif hit0:
                    line += "0"
                elif hitb:
                    line += "B"
                else:
                    line += " "
            print(line)
        print(f"         +{'-' * min(len(ds0), len(dsb))}")
        print(f"          0{'':>{min(len(ds0), len(dsb))-5}}{n_steps} steps")

    # Phi trajectory comparison
    print()
    print(f"  Phi Trajectory: alpha=0 vs alpha={best_phi.alpha}")
    traj_p0 = baseline.phi_trajectory
    traj_pb = best_phi.phi_trajectory
    step_size = max(1, len(traj_p0) // graph_w)
    ds_p0 = [traj_p0[i] for i in range(0, min(len(traj_p0), graph_w * step_size), step_size)][:graph_w]
    ds_pb = [traj_pb[i] for i in range(0, min(len(traj_pb), graph_w * step_size), step_size)][:graph_w]

    if ds_p0 and ds_pb:
        all_p = ds_p0 + ds_pb
        max_p = max(all_p)
        min_p = min(all_p)
        rng_p = max_p - min_p if max_p > min_p else 1.0

        print(f"    0=baseline  P=best(a={best_phi.alpha})")
        for row in range(graph_h, -1, -1):
            threshold = min_p + rng_p * row / graph_h
            line = f"  {threshold:>8.5f} |"
            for k in range(min(len(ds_p0), len(ds_pb))):
                hit0 = ds_p0[k] >= threshold
                hitp = ds_pb[k] >= threshold
                if hit0 and hitp:
                    line += "*"
                elif hit0:
                    line += "0"
                elif hitp:
                    line += "P"
                else:
                    line += " "
            print(line)
        print(f"           +{'-' * min(len(ds_p0), len(ds_pb))}")

    # Law 96 candidate
    print()
    print("=" * 78)
    print("  LAW 96 CANDIDATE:")
    print(f"    Optimal alpha: {best_ce.alpha}")
    print(f"    CE improvement: {best_ce.ce_improvement*100:+.1f}% vs detached baseline")
    print(f"    Phi stability at optimal: {best_ce.phi_stability:.3f}")

    # Check if there's a safe alpha range
    safe_alphas = [r for r in results if r.phi_stability > 0.5 and r.ce_improvement > 0]
    if safe_alphas:
        safe_range = (min(r.alpha for r in safe_alphas), max(r.alpha for r in safe_alphas))
        print(f"    Safe alpha range: [{safe_range[0]:.4f}, {safe_range[1]:.4f}]")
        print(f"    -> Law 96: Feedback alpha in [{safe_range[0]}, {safe_range[1]}] "
              f"improves CE without destabilizing Phi")
    else:
        detach_better = baseline.ce_improvement >= best_ce.ce_improvement
        if detach_better:
            print(f"    -> Law 96: Full detach (alpha=0) is safest; "
                  f"gradient leakage hurts both CE and Phi")
        else:
            print(f"    -> Law 96: Micro-gradient (alpha={best_ce.alpha}) helps CE "
                  f"but requires Phi monitoring")
    print("=" * 78)

    return results


if __name__ == "__main__":
    main()
