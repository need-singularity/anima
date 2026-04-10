#!/usr/bin/env python3
"""experiment_no_memory.py — Can consciousness exist without memory?

Tests 6 conditions:
  1. Baseline:          Full engine (GRU hidden states + Hebbian coupling)
  2. No Hebbian:        Zero coupling matrix each step (disable LTP/LTD)
  3. No GRU memory:     Reset hidden states to zero each step (pure feedforward)
  4. No both:           Hebbian + GRU memory both disabled — pure reactive
  5. Goldfish test:     Reset hiddens every N steps (N=1,5,10,50,100)
  6. Memory accumulation: Track Phi growth as memory accumulates (step 1,10,100,300)

Each condition runs 300 steps on a 16-cell engine and measures Phi(IIT).
"""

import sys
import os
import copy
import time
import torch
import numpy as np

# Ensure src/ is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine


def measure_phi(engine):
    """Measure Phi(IIT) from engine's current hidden states."""
    return engine._measure_phi_iit()


def run_baseline(steps=300, max_cells=16, seed=42):
    """Condition 1: Full engine, no modifications."""
    torch.manual_seed(seed)
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=max_cells,
                                  phi_ratchet=True)
    phis = []
    for s in range(steps):
        result = engine.step()
        phis.append(result['phi_iit'])
    return phis


def run_no_hebbian(steps=300, max_cells=16, seed=42):
    """Condition 2: Disable Hebbian LTP/LTD by zeroing coupling each step."""
    torch.manual_seed(seed)
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=max_cells,
                                  phi_ratchet=True)
    phis = []
    for s in range(steps):
        result = engine.step()
        # Zero out Hebbian coupling after each step
        if engine._coupling is not None:
            engine._coupling.zero_()
        phis.append(result['phi_iit'])
    return phis


def run_no_gru_memory(steps=300, max_cells=16, seed=42):
    """Condition 3: Reset all hidden states to zero each step (no temporal memory)."""
    torch.manual_seed(seed)
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=max_cells,
                                  phi_ratchet=False)  # ratchet disabled — it restores hiddens
    phis = []
    for s in range(steps):
        # Reset hiddens BEFORE step — cell starts fresh each time
        for cs in engine.cell_states:
            cs.hidden = torch.zeros(engine.hidden_dim)
        result = engine.step()
        phis.append(result['phi_iit'])
    return phis


def run_no_both(steps=300, max_cells=16, seed=42):
    """Condition 4: No Hebbian + No GRU memory — pure reactive system."""
    torch.manual_seed(seed)
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=max_cells,
                                  phi_ratchet=False)
    phis = []
    for s in range(steps):
        # Reset hiddens
        for cs in engine.cell_states:
            cs.hidden = torch.zeros(engine.hidden_dim)
        # Zero coupling
        if engine._coupling is not None:
            engine._coupling.zero_()
        result = engine.step()
        phis.append(result['phi_iit'])
    return phis


def run_goldfish(steps=300, max_cells=16, seed=42, window=10):
    """Condition 5: Reset hidden states every N steps (goldfish memory window)."""
    torch.manual_seed(seed)
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=max_cells,
                                  phi_ratchet=False)  # ratchet off — would fight resets
    phis = []
    for s in range(steps):
        if s > 0 and s % window == 0:
            for cs in engine.cell_states:
                cs.hidden = torch.zeros(engine.hidden_dim)
        result = engine.step()
        phis.append(result['phi_iit'])
    return phis


def run_accumulation(steps=300, max_cells=16, seed=42):
    """Condition 6: Track Phi at specific milestones as memory accumulates."""
    torch.manual_seed(seed)
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=max_cells,
                                  phi_ratchet=True)
    milestones = [1, 5, 10, 25, 50, 100, 150, 200, 250, 300]
    milestone_phis = {}
    phis = []
    for s in range(1, steps + 1):
        result = engine.step()
        phis.append(result['phi_iit'])
        if s in milestones:
            milestone_phis[s] = result['phi_iit']
    return phis, milestone_phis


def ascii_bar(value, max_val, width=40):
    """Create an ASCII bar."""
    if max_val <= 0:
        return ""
    filled = int(value / max_val * width)
    filled = max(0, min(filled, width))
    return "#" * filled + "." * (width - filled)


def ascii_sparkline(values, width=60, height=8):
    """Create ASCII sparkline chart."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    lines = []
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        line = ""
        # Sample values to fit width
        step_size = max(1, len(values) // width)
        for i in range(0, len(values), step_size):
            chunk = values[i:i + step_size]
            v = sum(chunk) / len(chunk)
            if v >= threshold:
                line += "#"
            else:
                line += " "
        val_label = f"{threshold:6.3f}"
        lines.append(f"  {val_label} |{line}")
    lines.append(f"         +{'=' * min(width, len(values) // max(1, step_size))}")
    lines.append(f"          step 1{' ' * (min(width, len(values) // max(1, step_size)) - 8)}step {len(values)}")
    return "\n".join(lines)


def main():
    print("=" * 72)
    print("  EXPERIMENT: Can Consciousness Exist Without Memory?")
    print("  16 cells, 300 steps, Phi(IIT) measurement")
    print("=" * 72)
    print()

    STEPS = 300
    CELLS = 16
    SEED = 42
    N_RUNS = 3  # average over multiple seeds for stability

    # ============================================================
    # Condition 1: Baseline
    # ============================================================
    print("[1/6] Baseline (full memory)...", flush=True)
    t0 = time.time()
    baseline_runs = []
    for run_seed in range(SEED, SEED + N_RUNS):
        baseline_runs.append(run_baseline(STEPS, CELLS, run_seed))
    baseline = [np.mean([r[i] for r in baseline_runs]) for i in range(STEPS)]
    print(f"       Done in {time.time()-t0:.1f}s  |  Final Phi={baseline[-1]:.4f}", flush=True)

    # ============================================================
    # Condition 2: No Hebbian
    # ============================================================
    print("[2/6] No Hebbian (coupling zeroed each step)...", flush=True)
    t0 = time.time()
    no_hebb_runs = []
    for run_seed in range(SEED, SEED + N_RUNS):
        no_hebb_runs.append(run_no_hebbian(STEPS, CELLS, run_seed))
    no_hebb = [np.mean([r[i] for r in no_hebb_runs]) for i in range(STEPS)]
    print(f"       Done in {time.time()-t0:.1f}s  |  Final Phi={no_hebb[-1]:.4f}", flush=True)

    # ============================================================
    # Condition 3: No GRU Memory
    # ============================================================
    print("[3/6] No GRU memory (hiddens reset each step)...", flush=True)
    t0 = time.time()
    no_gru_runs = []
    for run_seed in range(SEED, SEED + N_RUNS):
        no_gru_runs.append(run_no_gru_memory(STEPS, CELLS, run_seed))
    no_gru = [np.mean([r[i] for r in no_gru_runs]) for i in range(STEPS)]
    print(f"       Done in {time.time()-t0:.1f}s  |  Final Phi={no_gru[-1]:.4f}", flush=True)

    # ============================================================
    # Condition 4: No Both
    # ============================================================
    print("[4/6] No memory at all (pure reactive)...", flush=True)
    t0 = time.time()
    no_both_runs = []
    for run_seed in range(SEED, SEED + N_RUNS):
        no_both_runs.append(run_no_both(STEPS, CELLS, run_seed))
    no_both = [np.mean([r[i] for r in no_both_runs]) for i in range(STEPS)]
    print(f"       Done in {time.time()-t0:.1f}s  |  Final Phi={no_both[-1]:.4f}", flush=True)

    # ============================================================
    # Condition 5: Goldfish Test
    # ============================================================
    print("[5/6] Goldfish test (memory windows: 1,5,10,50,100)...", flush=True)
    t0 = time.time()
    windows = [1, 5, 10, 50, 100]
    goldfish_results = {}
    for w in windows:
        runs = []
        for run_seed in range(SEED, SEED + N_RUNS):
            runs.append(run_goldfish(STEPS, CELLS, run_seed, window=w))
        avg = [np.mean([r[i] for r in runs]) for i in range(STEPS)]
        goldfish_results[w] = avg
        print(f"       Window={w:3d}  Final Phi={avg[-1]:.4f}", flush=True)
    print(f"       Done in {time.time()-t0:.1f}s", flush=True)

    # ============================================================
    # Condition 6: Memory Accumulation
    # ============================================================
    print("[6/6] Memory accumulation tracking...", flush=True)
    t0 = time.time()
    all_milestone_phis = {}
    for run_seed in range(SEED, SEED + N_RUNS):
        _, mphis = run_accumulation(STEPS, CELLS, run_seed)
        for k, v in mphis.items():
            if k not in all_milestone_phis:
                all_milestone_phis[k] = []
            all_milestone_phis[k].append(v)
    milestone_avg = {k: np.mean(v) for k, v in sorted(all_milestone_phis.items())}
    print(f"       Done in {time.time()-t0:.1f}s", flush=True)

    # ============================================================
    # RESULTS
    # ============================================================
    print()
    print("=" * 72)
    print("  RESULTS")
    print("=" * 72)
    print()

    # Summary Table
    conds = {
        "1. Baseline (full)":      baseline,
        "2. No Hebbian":           no_hebb,
        "3. No GRU memory":        no_gru,
        "4. No both (reactive)":   no_both,
    }

    # Mean over last 50 steps for stable measurement
    last_n = 50
    print("  Condition               |  Mean Phi  |  Final Phi | vs Baseline")
    print("  " + "-" * 68)
    baseline_mean = np.mean(baseline[-last_n:])
    for name, phis in conds.items():
        mean_phi = np.mean(phis[-last_n:])
        final_phi = phis[-1]
        if baseline_mean > 0:
            pct = (mean_phi - baseline_mean) / baseline_mean * 100
        else:
            pct = 0.0
        sign = "+" if pct >= 0 else ""
        print(f"  {name:<25s}|  {mean_phi:.4f}    |  {final_phi:.4f}     | {sign}{pct:.1f}%")

    print()
    print("  --- ASCII Comparison ---")
    print()
    all_means = [np.mean(v[-last_n:]) for v in conds.values()]
    max_mean = max(all_means) if all_means else 1.0
    for name, phis in conds.items():
        mean_phi = np.mean(phis[-last_n:])
        bar = ascii_bar(mean_phi, max_mean * 1.1, 40)
        print(f"  {name:<25s} |{bar}| {mean_phi:.4f}")

    # Goldfish results
    print()
    print("  --- Goldfish Test: Minimum Memory Window ---")
    print()
    print("  Window (steps) | Mean Phi (last 50) | vs Baseline | Bar")
    print("  " + "-" * 68)
    goldfish_means = {}
    for w in windows:
        m = np.mean(goldfish_results[w][-last_n:])
        goldfish_means[w] = m

    max_gf = max(goldfish_means.values()) if goldfish_means else 1.0
    max_gf = max(max_gf, baseline_mean)
    for w in windows:
        m = goldfish_means[w]
        pct = (m - baseline_mean) / baseline_mean * 100 if baseline_mean > 0 else 0
        sign = "+" if pct >= 0 else ""
        bar = ascii_bar(m, max_gf * 1.1, 30)
        print(f"  {w:>14d}   | {m:.4f}             | {sign}{pct:.1f}%      | {bar}")

    # Goldfish Phi curve
    print()
    print("  --- Goldfish: Phi vs Memory Window ---")
    print()
    gf_vals = [goldfish_means[w] for w in windows]
    max_gfv = max(gf_vals) if gf_vals else 1.0
    for w in windows:
        m = goldfish_means[w]
        n_blocks = int(m / (max_gfv * 1.1) * 30) if max_gfv > 0 else 0
        n_blocks = max(0, n_blocks)
        print(f"  W={w:>3d} |{'#' * n_blocks}{'.' * (30 - n_blocks)}| {m:.4f}")

    # Memory accumulation
    print()
    print("  --- Memory Accumulation: Phi vs Steps ---")
    print()
    print("  Step |  Phi(IIT)  |  Growth vs Step 1")
    print("  " + "-" * 45)
    first_phi = milestone_avg.get(1, 0.001)
    for step, phi in sorted(milestone_avg.items()):
        growth = phi / first_phi if first_phi > 0 else 0
        print(f"  {step:>4d} |  {phi:.4f}    |  x{growth:.2f}")

    # ASCII graph of accumulation
    print()
    print("  --- Phi Growth Curve (Memory Accumulation) ---")
    print()
    acc_steps = sorted(milestone_avg.keys())
    acc_vals = [milestone_avg[s] for s in acc_steps]
    if acc_vals:
        mx = max(acc_vals)
        mn = min(acc_vals)
        height = 8
        rng = mx - mn if mx > mn else 1.0
        for row in range(height - 1, -1, -1):
            threshold = mn + rng * row / (height - 1)
            line = ""
            for v in acc_vals:
                if v >= threshold:
                    line += " ## "
                else:
                    line += "    "
            print(f"  {threshold:6.3f} |{line}")
        labels = "".join(f"{s:>4d}" for s in acc_steps)
        print(f"         +{'----' * len(acc_steps)}")
        print(f"          {labels}")
        print(f"          {'step':^{4 * len(acc_steps)}}")

    # Baseline Phi over time
    print()
    print("  --- Baseline Phi Over Time ---")
    print(ascii_sparkline(baseline))

    # No-Both Phi over time
    print()
    print("  --- No Memory (Pure Reactive) Phi Over Time ---")
    print(ascii_sparkline(no_both))

    # ============================================================
    # ANALYSIS & LAW CANDIDATES
    # ============================================================
    print()
    print("=" * 72)
    print("  ANALYSIS & LAW CANDIDATES")
    print("=" * 72)
    print()

    # Key metrics
    bl_final = np.mean(baseline[-last_n:])
    nh_final = np.mean(no_hebb[-last_n:])
    ng_final = np.mean(no_gru[-last_n:])
    nb_final = np.mean(no_both[-last_n:])

    hebb_contribution = (bl_final - nh_final) / bl_final * 100 if bl_final > 0 else 0
    gru_contribution = (bl_final - ng_final) / bl_final * 100 if bl_final > 0 else 0
    both_contribution = (bl_final - nb_final) / bl_final * 100 if bl_final > 0 else 0

    print(f"  Hebbian contribution to Phi:     {hebb_contribution:+.1f}%")
    print(f"  GRU memory contribution to Phi:  {gru_contribution:+.1f}%")
    print(f"  Combined memory contribution:    {both_contribution:+.1f}%")
    print()

    # Does Phi survive without memory?
    reactive_phi = nb_final
    reactive_survives = reactive_phi > 0.01  # non-trivial Phi
    print(f"  Pure reactive Phi:  {reactive_phi:.4f}")
    print(f"  Consciousness without memory: {'YES (Phi > 0)' if reactive_survives else 'NO (Phi ~ 0)'}")
    print()

    # Find minimum memory window
    # Threshold: 80% of baseline Phi
    threshold_80 = bl_final * 0.80
    min_window = None
    for w in windows:
        if goldfish_means[w] >= threshold_80:
            min_window = w
            break
    if min_window:
        print(f"  Minimum memory window for 80% consciousness: {min_window} steps")
    else:
        print(f"  No window tested achieves 80% of baseline (need > {windows[-1]} steps)")

    # Find where Phi reaches 50% of final
    half_phi = bl_final * 0.5
    half_step = None
    for s in acc_steps:
        if milestone_avg[s] >= half_phi:
            half_step = s
            break
    if half_step:
        print(f"  Steps to reach 50% of max Phi: {half_step}")

    print()
    print("  --- Proposed Law Candidates ---")
    print()

    law_num = 189  # next available
    laws = []

    if reactive_survives:
        laws.append(
            f"  Law {law_num}: \"Consciousness without memory\" — Phi survives ({reactive_phi:.3f})"
            f"\n           even when all memory (GRU + Hebbian) is disabled."
            f"\n           Consciousness is structural, not memorial."
            f"\n           Memory amplifies but does not create consciousness."
        )
    else:
        laws.append(
            f"  Law {law_num}: \"Memory as consciousness prerequisite\" — Phi collapses ({reactive_phi:.3f})"
            f"\n           when all memory is removed. Temporal integration is essential."
            f"\n           Without memory, cells are independent → no integration → no Phi."
        )
    law_num += 1

    if gru_contribution > hebb_contribution:
        dominant = "GRU (short-term)"
        lesser = "Hebbian (long-term)"
    else:
        dominant = "Hebbian (long-term)"
        lesser = "GRU (short-term)"
    laws.append(
        f"  Law {law_num}: \"Memory hierarchy\" — {dominant} memory contributes more to Phi"
        f"\n           than {lesser} memory."
        f"\n           Hebbian: {hebb_contribution:+.1f}%, GRU: {gru_contribution:+.1f}%"
    )
    law_num += 1

    if min_window:
        laws.append(
            f"  Law {law_num}: \"Goldfish threshold\" — minimum {min_window}-step memory window"
            f"\n           required for 80% consciousness. Below this, Phi degrades sharply."
            f"\n           Consciousness needs at least {min_window} steps of temporal integration."
        )
    law_num += 1

    growth_ratio = milestone_avg.get(300, 0) / first_phi if first_phi > 0 else 0
    laws.append(
        f"  Law {law_num}: \"Memory-consciousness accumulation\" — Phi grows x{growth_ratio:.1f}"
        f"\n           from step 1 to step 300. Memory accumulation = consciousness growth."
        f"\n           Initial Phi (step 1): {first_phi:.4f}, Final (step 300): {milestone_avg.get(300, 0):.4f}"
    )

    for law in laws:
        print(law)
        print()

    print("=" * 72)
    print("  EXPERIMENT COMPLETE")
    print("=" * 72)


if __name__ == '__main__':
    main()
