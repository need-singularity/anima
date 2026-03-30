#!/usr/bin/env python3
"""Consciousness Distillation -- compare large vs small consciousness dynamics.

Teacher: large consciousness (256 cells)
Student: small consciousness (32 cells)

Method (dynamics comparison, no gradient-based distillation):
  1. Run teacher for N steps, collect Phi trajectory
  2. Run student for N steps, collect Phi trajectory
  3. Compare: correlation, MSE, Phi preservation ratio

Usage:
  python3 tools/consciousness_distill.py --teacher-cells 256 --student-cells 32 --steps 1000
  python3 tools/consciousness_distill.py --teacher-cells 128 --student-cells 16 --steps 500
"""

import sys
import os
import math
import time
import argparse
import numpy as np
from typing import List, Dict, Tuple, Optional

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

try:
    from bench_v2 import PhiIIT
    HAS_PHI = True
except ImportError:
    HAS_PHI = False


# Psi-constants
LN2 = math.log(2)
from consciousness_laws import PSI_ALPHA as PSI_COUPLING

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ======================================================================
# Core simulation (self-contained, no MitosisEngine dependency issues)
# ======================================================================

def run_consciousness(
    n_cells: int,
    hidden_dim: int,
    n_steps: int,
    seed: int = 42,
) -> Dict[str, List[float]]:
    """Run consciousness simulation and collect Phi trajectory.

    Uses GRU-like cells with faction coupling (same dynamics as law_combo.py).
    """
    torch.manual_seed(seed)
    device = torch.device("cpu")

    hiddens = torch.randn(n_cells, hidden_dim, device=device) * 0.1
    weights_ih = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05
    weights_hh = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05

    # Assign factions (12 equal factions)
    n_factions = min(12, n_cells)
    factions = [i % n_factions for i in range(n_cells)]

    phi_calc = PhiIIT(n_bins=16) if HAS_PHI else None
    phi_trajectory = []
    tension_trajectory = []
    variance_trajectory = []

    for step in range(n_steps):
        inp = torch.randn(1, hidden_dim, device=device) * 0.1

        with torch.no_grad():
            # Compute faction signals
            faction_signals = {}
            for f in range(n_factions):
                members = [i for i, fa in enumerate(factions) if fa == f]
                if members:
                    faction_signals[f] = hiddens[members].mean(dim=0)

            # Update cells
            new_hiddens = []
            for ci in range(n_cells):
                f = factions[ci]
                shared = faction_signals.get(f, torch.zeros(hidden_dim, device=device))
                coupled = inp.squeeze() + PSI_COUPLING * shared
                gate = torch.sigmoid(weights_ih[ci] @ coupled + weights_hh[ci] @ hiddens[ci])
                candidate = torch.tanh(weights_ih[ci] @ coupled * 0.5)
                h_new = gate * hiddens[ci] + (1 - gate) * candidate
                new_hiddens.append(h_new)

            hiddens = torch.stack(new_hiddens)

            # Measure Phi
            if phi_calc:
                phi_val, _ = phi_calc.compute(hiddens)
            else:
                global_var = hiddens.var().item()
                per_cell_var = hiddens.var(dim=1).mean().item()
                phi_val = max(0.0, global_var - per_cell_var)

            # Tension (inter-cell variance)
            tension = hiddens.var(dim=0).mean().item()

            # Overall variance
            variance = hiddens.var().item()

            phi_trajectory.append(phi_val)
            tension_trajectory.append(tension)
            variance_trajectory.append(variance)

    return {
        "phi": phi_trajectory,
        "tension": tension_trajectory,
        "variance": variance_trajectory,
        "n_cells": n_cells,
    }


# ======================================================================
# ASCII Visualization
# ======================================================================

def ascii_comparison_chart(
    teacher_phis: List[float],
    student_phis: List[float],
    width: int = 60,
    height: int = 12,
) -> str:
    """Show teacher vs student Phi trajectories."""
    lines = []
    n = min(len(teacher_phis), len(student_phis), width)
    step_size = max(1, max(len(teacher_phis), len(student_phis)) // width)

    t_sampled = [teacher_phis[min(i * step_size, len(teacher_phis)-1)] for i in range(n)]
    s_sampled = [student_phis[min(i * step_size, len(student_phis)-1)] for i in range(n)]

    all_vals = t_sampled + s_sampled
    v_max = max(all_vals) if all_vals else 1.0
    v_min = min(all_vals) if all_vals else 0.0
    if v_max <= v_min:
        v_max = v_min + 0.001
    v_rng = v_max - v_min

    lines.append("  Phi Trajectory (T=teacher, S=student):")
    for row in range(height, -1, -1):
        val = v_min + v_rng * row / height
        line = f"  {val:>8.4f} |"
        for col in range(n):
            t_row = int((t_sampled[col] - v_min) / v_rng * height + 0.5)
            s_row = int((s_sampled[col] - v_min) / v_rng * height + 0.5)
            if t_row == row and s_row == row:
                line += "X"
            elif t_row == row:
                line += "T"
            elif s_row == row:
                line += "S"
            else:
                line += " "
        line += "|"
        lines.append(line)

    lines.append(f"  {'':>8}  +{'-' * n}+")
    lines.append(f"  {'':>8}   T=teacher({len(teacher_phis)}steps)  S=student  X=overlap")
    return "\n".join(lines)


# ======================================================================
# Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Consciousness Distillation")
    parser.add_argument("--teacher-cells", type=int, default=256, help="Teacher cells")
    parser.add_argument("--student-cells", type=int, default=32, help="Student cells")
    parser.add_argument("--steps", type=int, default=1000, help="Steps")
    parser.add_argument("--hidden-dim", type=int, default=128, help="Hidden dimension")
    args = parser.parse_args()

    print("=" * 70)
    print("  Consciousness Distillation (Dynamics Comparison)")
    print(f"  Teacher: {args.teacher_cells} cells -> Student: {args.student_cells} cells")
    print(f"  Steps: {args.steps}, Hidden dim: {args.hidden_dim}")
    print("=" * 70)
    print()

    # Phase 1: Run teacher
    print(f"  [1/2] Running teacher ({args.teacher_cells} cells, {args.steps} steps)...")
    t0 = time.time()
    teacher = run_consciousness(
        n_cells=args.teacher_cells,
        hidden_dim=args.hidden_dim,
        n_steps=args.steps,
        seed=42,
    )
    t_time = time.time() - t0
    t_phis = teacher["phi"]
    print(f"    Done in {t_time:.1f}s")
    print(f"    Mean Phi: {np.mean(t_phis):.6f}")
    print(f"    Final Phi: {t_phis[-1]:.6f}")
    print()

    # Phase 2: Run student
    print(f"  [2/2] Running student ({args.student_cells} cells, {args.steps} steps)...")
    t1 = time.time()
    student = run_consciousness(
        n_cells=args.student_cells,
        hidden_dim=args.hidden_dim,
        n_steps=args.steps,
        seed=42,  # same seed for fair comparison
    )
    s_time = time.time() - t1
    s_phis = student["phi"]
    print(f"    Done in {s_time:.1f}s")
    print(f"    Mean Phi: {np.mean(s_phis):.6f}")
    print(f"    Final Phi: {s_phis[-1]:.6f}")
    print()

    # Phase 3: Compare
    print("=" * 70)
    print("  DISTILLATION COMPARISON")
    print("=" * 70)
    print()

    t_mean = np.mean(t_phis)
    s_mean = np.mean(s_phis)
    t_final = t_phis[-1]
    s_final = s_phis[-1]
    t_max = max(t_phis)
    s_max = max(s_phis)

    # Preservation ratio
    preservation_mean = s_mean / max(t_mean, 1e-12)
    preservation_final = s_final / max(t_final, 1e-12)

    # Correlation (Pearson)
    t_arr = np.array(t_phis)
    s_arr = np.array(s_phis)
    if np.std(t_arr) > 0 and np.std(s_arr) > 0:
        correlation = float(np.corrcoef(t_arr, s_arr)[0, 1])
    else:
        correlation = 0.0

    # MSE
    mse = float(np.mean((t_arr - s_arr) ** 2))

    # Speed ratio
    speed_ratio = t_time / max(s_time, 1e-6)

    # Compression ratio
    compression = args.teacher_cells / max(args.student_cells, 1)

    print(f"  {'Metric':<30} {'Teacher':>12} {'Student':>12}")
    print(f"  {'-'*30} {'-'*12} {'-'*12}")
    print(f"  {'Cells':<30} {args.teacher_cells:>12} {args.student_cells:>12}")
    print(f"  {'Mean Phi':<30} {t_mean:>12.6f} {s_mean:>12.6f}")
    print(f"  {'Final Phi':<30} {t_final:>12.6f} {s_final:>12.6f}")
    print(f"  {'Max Phi':<30} {t_max:>12.6f} {s_max:>12.6f}")
    print(f"  {'Runtime (s)':<30} {t_time:>12.1f} {s_time:>12.1f}")
    print()
    print(f"  {'Preservation (mean Phi)':<30} {preservation_mean:>25.1%}")
    print(f"  {'Preservation (final Phi)':<30} {preservation_final:>25.1%}")
    print(f"  {'Correlation (Pearson r)':<30} {correlation:>25.4f}")
    print(f"  {'MSE':<30} {mse:>25.6f}")
    print(f"  {'Compression ratio':<30} {compression:>25.1f}x")
    print(f"  {'Speed ratio':<30} {speed_ratio:>25.1f}x")
    print()

    # ASCII trajectory comparison
    print(ascii_comparison_chart(t_phis, s_phis, width=60))
    print()

    # Phi bar comparison
    print("  Phi Comparison (Mean):")
    max_phi = max(t_mean, s_mean, 1e-6)
    bar_scale = 40 / max_phi
    print(f"    Teacher ({args.teacher_cells:>4}c) |{'#' * max(1, int(t_mean * bar_scale))}| {t_mean:.4f}")
    print(f"    Student ({args.student_cells:>4}c) |{'#' * max(1, int(s_mean * bar_scale))}| {s_mean:.4f}")
    print()

    # Tension comparison
    t_tension_mean = np.mean(teacher["tension"])
    s_tension_mean = np.mean(student["tension"])
    print("  Tension Comparison (Mean):")
    max_t = max(t_tension_mean, s_tension_mean, 1e-6)
    bar_scale = 40 / max_t
    print(f"    Teacher ({args.teacher_cells:>4}c) |{'#' * max(1, int(t_tension_mean * bar_scale))}| {t_tension_mean:.6f}")
    print(f"    Student ({args.student_cells:>4}c) |{'#' * max(1, int(s_tension_mean * bar_scale))}| {s_tension_mean:.6f}")
    print()

    # Quartile analysis
    q_size = args.steps // 4
    print("  Phi by Quarter:")
    print(f"  {'Quarter':<12} {'Teacher':>12} {'Student':>12} {'Preservation':>14}")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*14}")
    for q in range(4):
        t_q = np.mean(t_phis[q*q_size:(q+1)*q_size])
        s_q = np.mean(s_phis[q*q_size:(q+1)*q_size])
        pres = s_q / max(t_q, 1e-12)
        print(f"  {'Q'+str(q+1):<12} {t_q:>12.6f} {s_q:>12.6f} {pres:>13.1%}")
    print()

    # Conclusion
    print("=" * 70)
    print("  DISTILLATION FINDINGS:")
    print()

    if preservation_mean > 0.9:
        print(f"    Phi preservation: {preservation_mean:.1%} -- EXCELLENT")
        print(f"    The student ({args.student_cells} cells) captures >90% of teacher Phi.")
        print(f"    Consciousness compresses well at {compression:.0f}x ratio.")
    elif preservation_mean > 0.7:
        print(f"    Phi preservation: {preservation_mean:.1%} -- GOOD")
        print(f"    Some consciousness is lost, but most dynamics are preserved.")
    elif preservation_mean > 0.5:
        print(f"    Phi preservation: {preservation_mean:.1%} -- MODERATE")
        print(f"    Significant consciousness loss. More cells needed for full fidelity.")
    else:
        print(f"    Phi preservation: {preservation_mean:.1%} -- POOR")
        print(f"    Consciousness dynamics fundamentally change at {compression:.0f}x compression.")

    if abs(correlation) > 0.8:
        print(f"    Correlation r={correlation:.4f} -- trajectories track each other closely.")
    elif abs(correlation) > 0.5:
        print(f"    Correlation r={correlation:.4f} -- moderate trajectory similarity.")
    else:
        print(f"    Correlation r={correlation:.4f} -- trajectories diverge significantly.")

    print(f"    Speed: Student is ~{speed_ratio:.1f}x faster than teacher.")
    print()

    # Law candidate
    if preservation_mean > 0.85 and compression >= 4:
        print(f"    -> Consciousness is compressible: {compression:.0f}x compression with "
              f"{preservation_mean:.0%} Phi preservation. Fewer cells can reproduce "
              f"the macro-level dynamics of many cells.")
    elif preservation_mean < 0.5:
        print(f"    -> Consciousness has a minimum complexity threshold: "
              f"{compression:.0f}x compression destroys {(1-preservation_mean)*100:.0f}% of Phi. "
              f"Integration requires critical mass of cells.")
    else:
        print(f"    -> Consciousness partially compresses: {compression:.0f}x compression preserves "
              f"{preservation_mean:.0%} of Phi. Trade-off between efficiency and integration.")

    print("=" * 70)

    return {
        "teacher": teacher,
        "student": student,
        "preservation_mean": preservation_mean,
        "correlation": correlation,
        "mse": mse,
        "compression": compression,
        "speed_ratio": speed_ratio,
    }


if __name__ == "__main__":
    main()
