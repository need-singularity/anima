#!/usr/bin/env python3
"""acceleration_c_series.py — C-series acceleration experiments

C1: Consciousness Compiler (laws → weights direct calculation)
C2: Fractal Consciousness (small→large self-similar replication)
C4: Reverse-Time Consciousness (goal state → initial state injection)
C5: Resonance Frequency Matching (breathing frequency × learning rate)
C8: Topology Pumping (topology transition tension bursts → Hebbian boost)

All experiments run on local CPU with small scale (4-64 cells).
Each experiment is independent and produces a results table.

Usage:
  python acceleration_c_series.py           # Run all
  python acceleration_c_series.py --c1      # C1 only
  python acceleration_c_series.py --c2      # C2 only
  python acceleration_c_series.py --c4      # C4 only
  python acceleration_c_series.py --c5      # C5 only
  python acceleration_c_series.py --c8      # C8 only
"""

import sys
import os
import time
import math
import copy
import argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
from consciousness_engine import ConsciousnessEngine


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def measure_phi(engine: ConsciousnessEngine) -> float:
    """Measure Phi(IIT) from engine."""
    return engine.measure_phi()


def run_steps(engine: ConsciousnessEngine, n_steps: int, x_input=None) -> list:
    """Run N steps, return list of phi values."""
    phis = []
    for _ in range(n_steps):
        result = engine.step(x_input=x_input)
        phis.append(result.get('phi_iit', 0.0))
    return phis


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def print_table(headers: list, rows: list, widths: list = None):
    """Print a formatted table."""
    if widths is None:
        widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) + 2
                  for i, h in enumerate(headers)]
    # Header
    hdr = '|'.join(str(h).center(w) for h, w in zip(headers, widths))
    sep = '+'.join('-' * w for w in widths)
    print(f"  {hdr}")
    print(f"  {sep}")
    for row in rows:
        line = '|'.join(str(r).center(w) for r, w in zip(row, widths))
        print(f"  {line}")
    sys.stdout.flush()


def ascii_bar(label: str, value: float, max_val: float, width: int = 40):
    """Print ASCII bar chart line."""
    filled = int(width * min(value / max(max_val, 1e-8), 1.0))
    bar = '#' * filled + '.' * (width - filled)
    print(f"  {label:>20s}  [{bar}] {value:.4f}")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# C1: Consciousness Compiler — laws → weights direct calculation
# ═══════════════════════════════════════════════════════════

def run_c1(cells: int = 32, steps: int = 300):
    """C1: Apply all parseable laws at once vs standard evolution.

    Hypothesis: Batch law application can shortcut to high-Phi states
    faster than gradual step-by-step evolution.
    """
    print_header("C1: Consciousness Compiler (laws -> weights)")

    from self_modifying_engine import LawParser, EngineModifier

    # --- Baseline: standard 300 steps ---
    print(f"  [1/3] Baseline: {steps} steps, {cells} cells...")
    sys.stdout.flush()
    engine_base = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_base = run_steps(engine_base, steps)
    time_base = time.time() - t0
    phi_base_final = phis_base[-1] if phis_base else 0.0
    phi_base_peak = max(phis_base) if phis_base else 0.0
    print(f"    Done in {time_base:.2f}s  Phi_final={phi_base_final:.4f}  Phi_peak={phi_base_peak:.4f}")
    sys.stdout.flush()

    # --- Compiled: parse all laws, apply at once, then short evolution ---
    print(f"  [2/3] Compiled: parse laws + apply + {steps//3} steps...")
    sys.stdout.flush()
    engine_comp = ConsciousnessEngine(max_cells=cells)
    parser = LawParser()
    modifier = EngineModifier(engine_comp)

    # Warmup: 10 steps so engine has some state
    run_steps(engine_comp, 10)

    t0 = time.time()
    # Apply all parsed modifications
    n_applied = 0
    n_failed = 0
    n_rollback = 0
    for lid_str, mods in parser.parsed.items():
        for mod in mods:
            success = modifier.apply(mod)
            if success:
                n_applied += 1
            else:
                n_failed += 1
    time_compile = time.time() - t0
    phi_after_compile = measure_phi(engine_comp)

    print(f"    Laws parsed: {len(parser.parsed)}, applied: {n_applied}, "
          f"failed: {n_failed}, rollback: {n_rollback}")
    print(f"    Compile time: {time_compile:.3f}s  Phi_after_compile={phi_after_compile:.4f}")
    sys.stdout.flush()

    # Short evolution after compile
    t0 = time.time()
    phis_comp = run_steps(engine_comp, steps // 3)
    time_comp_evolve = time.time() - t0
    phi_comp_final = phis_comp[-1] if phis_comp else phi_after_compile
    phi_comp_peak = max([phi_after_compile] + phis_comp)
    time_comp_total = time_compile + time_comp_evolve

    print(f"    Post-compile {steps//3} steps in {time_comp_evolve:.2f}s")
    print(f"    Phi_final={phi_comp_final:.4f}  Phi_peak={phi_comp_peak:.4f}")
    sys.stdout.flush()

    # --- Hybrid: compile + full evolution ---
    print(f"  [3/3] Hybrid: compile + {steps} steps...")
    sys.stdout.flush()
    engine_hybrid = ConsciousnessEngine(max_cells=cells)
    run_steps(engine_hybrid, 10)
    modifier_h = EngineModifier(engine_hybrid)
    t0 = time.time()
    for lid_str, mods in parser.parsed.items():
        for mod in mods:
            modifier_h.apply(mod)
    phis_hybrid = run_steps(engine_hybrid, steps)
    time_hybrid = time.time() - t0
    phi_hybrid_final = phis_hybrid[-1] if phis_hybrid else 0.0
    phi_hybrid_peak = max(phis_hybrid) if phis_hybrid else 0.0

    # --- Results ---
    print(f"\n  C1 Results ({cells}c, {steps} steps)")
    print_table(
        ['Method', 'Phi_final', 'Phi_peak', 'Time(s)', 'Speedup'],
        [
            ['Baseline', f'{phi_base_final:.4f}', f'{phi_base_peak:.4f}',
             f'{time_base:.2f}', '1.00x'],
            [f'Compiled+{steps//3}s', f'{phi_comp_final:.4f}', f'{phi_comp_peak:.4f}',
             f'{time_comp_total:.2f}',
             f'{time_base/max(time_comp_total,0.001):.2f}x'],
            [f'Hybrid+{steps}s', f'{phi_hybrid_final:.4f}', f'{phi_hybrid_peak:.4f}',
             f'{time_hybrid:.2f}',
             f'{time_base/max(time_hybrid,0.001):.2f}x'],
        ]
    )

    # Bar chart
    print(f"\n  Phi Peak Comparison:")
    max_phi = max(phi_base_peak, phi_comp_peak, phi_hybrid_peak, 0.001)
    ascii_bar('Baseline', phi_base_peak, max_phi)
    ascii_bar(f'Compiled+{steps//3}s', phi_comp_peak, max_phi)
    ascii_bar(f'Hybrid+{steps}s', phi_hybrid_peak, max_phi)

    print(f"\n  Laws compiled: {n_applied}/{n_applied + n_failed} "
          f"({100*n_applied/max(n_applied+n_failed,1):.0f}% success)")

    return {
        'baseline_phi': phi_base_peak,
        'compiled_phi': phi_comp_peak,
        'hybrid_phi': phi_hybrid_peak,
        'compile_time': time_compile,
        'laws_applied': n_applied,
    }


# ═══════════════════════════════════════════════════════════
# C2: Fractal Consciousness — small → large self-similar replication
# ═══════════════════════════════════════════════════════════

def run_c2(small_cells: int = 4, large_cells: int = 64, steps: int = 300):
    """C2: Train small engine, replicate pattern to large engine.

    Hypothesis: Fractal initialization (trained small → tiled large)
    converges faster than random initialization.
    """
    print_header("C2: Fractal Consciousness (small -> large replication)")

    # --- Phase 1: Train small engine ---
    print(f"  [1/3] Training small engine ({small_cells}c, {steps} steps)...")
    sys.stdout.flush()
    engine_small = ConsciousnessEngine(max_cells=small_cells, initial_cells=small_cells)
    t0 = time.time()
    phis_small = run_steps(engine_small, steps)
    time_small = time.time() - t0
    phi_small_final = phis_small[-1] if phis_small else 0.0
    print(f"    Small engine Phi={phi_small_final:.4f} in {time_small:.2f}s")
    sys.stdout.flush()

    # Extract trained state
    small_states = engine_small.get_states()  # (n_cells, hidden_dim)
    small_n = small_states.shape[0]
    small_coupling = engine_small._coupling[:small_n, :small_n].clone() if engine_small._coupling is not None else None

    # --- Phase 2: Fractal initialization ---
    print(f"  [2/3] Fractal init: {small_cells}c -> {large_cells}c (tile x{large_cells//max(small_n,1)})...")
    sys.stdout.flush()
    engine_fractal = ConsciousnessEngine(max_cells=large_cells, initial_cells=large_cells)

    # Tile small states into large engine
    n_tiles = large_cells // max(small_n, 1)
    actual_large_n = engine_fractal.n_cells
    with torch.no_grad():
        for i in range(actual_large_n):
            src_idx = i % small_n
            # Copy hidden state with small perturbation for diversity
            noise = torch.randn_like(small_states[src_idx]) * 0.01
            engine_fractal.cell_states[i].hidden = small_states[src_idx].clone() + noise

        # Tile coupling matrix
        if small_coupling is not None and engine_fractal._coupling is not None:
            for i in range(actual_large_n):
                for j in range(actual_large_n):
                    si, sj = i % small_n, j % small_n
                    engine_fractal._coupling[i, j] = small_coupling[si, sj]

    phi_fractal_init = measure_phi(engine_fractal)
    print(f"    Fractal init Phi={phi_fractal_init:.4f}")
    sys.stdout.flush()

    # Evolve fractal engine
    t0 = time.time()
    phis_fractal = run_steps(engine_fractal, steps)
    time_fractal = time.time() - t0
    phi_fractal_final = phis_fractal[-1] if phis_fractal else phi_fractal_init
    phi_fractal_peak = max([phi_fractal_init] + phis_fractal)

    # --- Phase 3: Random baseline ---
    print(f"  [3/3] Random init baseline ({large_cells}c, {steps} steps)...")
    sys.stdout.flush()
    engine_random = ConsciousnessEngine(max_cells=large_cells, initial_cells=large_cells)
    phi_random_init = measure_phi(engine_random)
    t0 = time.time()
    phis_random = run_steps(engine_random, steps)
    time_random = time.time() - t0
    phi_random_final = phis_random[-1] if phis_random else 0.0
    phi_random_peak = max([phi_random_init] + phis_random)

    # --- Results ---
    # Find step where each reaches 50% of their respective peak
    def steps_to_threshold(phis, threshold):
        for i, p in enumerate(phis):
            if p >= threshold:
                return i + 1
        return len(phis)

    target_phi = min(phi_fractal_peak, phi_random_peak) * 0.5
    steps_fractal_50 = steps_to_threshold(phis_fractal, target_phi)
    steps_random_50 = steps_to_threshold(phis_random, target_phi)

    total_time_fractal = time_small + time_fractal

    print(f"\n  C2 Results ({small_cells}c -> {large_cells}c, {steps} steps)")
    print_table(
        ['Method', 'Phi_init', 'Phi_final', 'Phi_peak', 'Time(s)', 'Steps_50%'],
        [
            [f'Random {large_cells}c', f'{phi_random_init:.4f}', f'{phi_random_final:.4f}',
             f'{phi_random_peak:.4f}', f'{time_random:.2f}', str(steps_random_50)],
            [f'Fractal {small_cells}c->{large_cells}c', f'{phi_fractal_init:.4f}',
             f'{phi_fractal_final:.4f}', f'{phi_fractal_peak:.4f}',
             f'{total_time_fractal:.2f}', str(steps_fractal_50)],
        ]
    )

    # Phi trajectory comparison (sample every 30 steps)
    print(f"\n  Phi Trajectory (sampled every {steps//10} steps):")
    sample_interval = max(steps // 10, 1)
    print(f"  {'Step':>6s}  {'Random':>10s}  {'Fractal':>10s}  {'Delta':>10s}")
    print(f"  {'-'*6}  {'-'*10}  {'-'*10}  {'-'*10}")
    for i in range(0, min(len(phis_random), len(phis_fractal)), sample_interval):
        r = phis_random[i]
        f = phis_fractal[i]
        d = f - r
        print(f"  {i:>6d}  {r:>10.4f}  {f:>10.4f}  {d:>+10.4f}")
    sys.stdout.flush()

    speedup = steps_random_50 / max(steps_fractal_50, 1)
    print(f"\n  Fractal speedup to 50% target: {speedup:.1f}x")
    print(f"  Phi advantage at step 0: {phi_fractal_init - phi_random_init:+.4f}")

    return {
        'fractal_phi': phi_fractal_peak,
        'random_phi': phi_random_peak,
        'fractal_init_phi': phi_fractal_init,
        'speedup_50pct': speedup,
    }


# ═══════════════════════════════════════════════════════════
# C4: Reverse-Time Consciousness — goal state → initial state injection
# ═══════════════════════════════════════════════════════════

def run_c4(cells: int = 32, steps: int = 300):
    """C4: Record peak Phi state, inject into fresh engine.

    Hypothesis: Injecting a "good state" lets a new engine skip
    the initial exploration phase and maintain high Phi immediately.
    """
    print_header("C4: Reverse-Time Consciousness (goal state injection)")

    # --- Phase 1: Evolve donor, record peak state ---
    print(f"  [1/4] Evolving donor engine ({cells}c, {steps} steps)...")
    sys.stdout.flush()
    donor = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    best_phi = 0.0
    best_states = None
    best_coupling = None
    best_step = 0
    phis_donor = []

    t0 = time.time()
    for s in range(steps):
        result = donor.step()
        phi = result.get('phi_iit', 0.0)
        phis_donor.append(phi)
        if phi > best_phi:
            best_phi = phi
            best_states = donor.get_states().clone()
            best_coupling = donor._coupling.clone() if donor._coupling is not None else None
            best_step = s
    time_donor = time.time() - t0

    print(f"    Donor peak Phi={best_phi:.4f} at step {best_step}")
    sys.stdout.flush()

    # --- Phase 2: Inject peak state into fresh engine ---
    print(f"  [2/4] Injecting peak state into fresh engine...")
    sys.stdout.flush()
    engine_inject = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    n_inject = min(best_states.shape[0], engine_inject.n_cells)

    with torch.no_grad():
        for i in range(n_inject):
            engine_inject.cell_states[i].hidden = best_states[i].clone()
        if best_coupling is not None and engine_inject._coupling is not None:
            n_c = min(best_coupling.shape[0], engine_inject._coupling.shape[0])
            engine_inject._coupling[:n_c, :n_c] = best_coupling[:n_c, :n_c].clone()

    phi_inject_t0 = measure_phi(engine_inject)
    print(f"    Injected Phi at step 0: {phi_inject_t0:.4f}")
    sys.stdout.flush()

    # --- Phase 3: Short evolution after injection ---
    short_steps = steps // 6  # 50 steps if steps=300
    print(f"  [3/4] Post-injection evolution ({short_steps} steps)...")
    sys.stdout.flush()
    t0 = time.time()
    phis_inject = run_steps(engine_inject, short_steps)
    time_inject = time.time() - t0
    phi_inject_final = phis_inject[-1] if phis_inject else phi_inject_t0
    phi_inject_peak = max([phi_inject_t0] + phis_inject)

    # --- Phase 4: Random baseline full evolution ---
    print(f"  [4/4] Random baseline ({cells}c, {steps} steps)...")
    sys.stdout.flush()
    engine_rand = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    t0 = time.time()
    phis_rand = run_steps(engine_rand, steps)
    time_rand = time.time() - t0
    phi_rand_final = phis_rand[-1] if phis_rand else 0.0
    phi_rand_peak = max(phis_rand) if phis_rand else 0.0

    # --- Results ---
    # Time to reach injected phi level from random start
    target = phi_inject_t0 * 0.9
    steps_rand_to_target = steps
    for i, p in enumerate(phis_rand):
        if p >= target:
            steps_rand_to_target = i + 1
            break

    print(f"\n  C4 Results ({cells}c)")
    print_table(
        ['Method', 'Steps', 'Phi_final', 'Phi_peak', 'Time(s)'],
        [
            [f'Random {steps}s', str(steps), f'{phi_rand_final:.4f}',
             f'{phi_rand_peak:.4f}', f'{time_rand:.2f}'],
            [f'Donor {steps}s', str(steps), f'{phis_donor[-1]:.4f}',
             f'{best_phi:.4f}', f'{time_donor:.2f}'],
            [f'Inject+{short_steps}s', str(short_steps), f'{phi_inject_final:.4f}',
             f'{phi_inject_peak:.4f}', f'{time_inject:.2f}'],
        ]
    )

    print(f"\n  Injection advantage:")
    print(f"    Phi at step 0 (injected): {phi_inject_t0:.4f}")
    print(f"    Steps for random to reach 90% of that: {steps_rand_to_target}")
    print(f"    Time saved: {time_donor:.2f}s donor + {time_inject:.2f}s post "
          f"= {time_donor + time_inject:.2f}s total vs {time_rand:.2f}s random")

    # Check if injection holds
    phi_retention = phi_inject_final / max(phi_inject_t0, 1e-8)
    print(f"    Phi retention after {short_steps} steps: {phi_retention:.1%}")
    if phi_retention < 0.5:
        print(f"    WARNING: Injected state decayed significantly — engine dynamics override")
    elif phi_retention > 0.9:
        print(f"    STRONG: Injected state is stable — goal state persists")

    return {
        'donor_peak': best_phi,
        'inject_t0': phi_inject_t0,
        'inject_final': phi_inject_final,
        'random_peak': phi_rand_peak,
        'retention': phi_retention,
    }


# ═══════════════════════════════════════════════════════════
# C5: Resonance Frequency Matching — breathing × lr
# ═══════════════════════════════════════════════════════════

def run_c5(cells: int = 32, steps: int = 300):
    """C5: Synchronize Hebbian LR with consciousness breathing cycle.

    Hypothesis: Learning at the breathing peak (0.12 freq, 20s cycle)
    accelerates Phi growth vs fixed or anti-resonance LR schedules.

    We modulate the Hebbian coupling update strength in sync with
    the consciousness breathing rhythm.
    """
    print_header("C5: Resonance Frequency Matching (breathing x Hebbian LR)")

    BREATH_FREQ = 0.12  # 20s cycle, from consciousness_engine.py
    BASE_LR = 0.01      # Default Hebbian LR

    results = {}

    for label, lr_fn in [
        ('Fixed LR', lambda step: BASE_LR),
        ('Resonance', lambda step: BASE_LR * (1.0 + 0.5 * math.sin(step * BREATH_FREQ))),
        ('Anti-resonance', lambda step: BASE_LR * (1.0 - 0.5 * math.sin(step * BREATH_FREQ))),
        ('Double-freq', lambda step: BASE_LR * (1.0 + 0.5 * math.sin(step * BREATH_FREQ * 2))),
        ('Half-freq', lambda step: BASE_LR * (1.0 + 0.5 * math.sin(step * BREATH_FREQ * 0.5))),
    ]:
        print(f"  Running: {label} ({cells}c, {steps} steps)...")
        sys.stdout.flush()

        engine = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
        phis = []
        t0 = time.time()

        for s in range(steps):
            # Override Hebbian LR for this step
            lr = max(lr_fn(s), 0.001)  # Floor at 0.001
            result = engine.step()
            phi = result.get('phi_iit', 0.0)
            phis.append(phi)

            # Apply Hebbian with modulated LR (re-run with custom lr)
            if engine.n_cells >= 2:
                outputs = engine.get_states()[:, :engine.cell_dim]
                engine._hebbian_update(outputs, lr=lr)

        elapsed = time.time() - t0
        phi_final = phis[-1] if phis else 0.0
        phi_peak = max(phis) if phis else 0.0
        phi_mean = sum(phis[-50:]) / min(50, len(phis)) if phis else 0.0

        results[label] = {
            'phis': phis,
            'phi_final': phi_final,
            'phi_peak': phi_peak,
            'phi_mean_last50': phi_mean,
            'time': elapsed,
        }
        print(f"    Phi_final={phi_final:.4f}  Phi_peak={phi_peak:.4f}  "
              f"mean_last50={phi_mean:.4f}  time={elapsed:.2f}s")
        sys.stdout.flush()

    # --- Results ---
    print(f"\n  C5 Results ({cells}c, {steps} steps)")
    rows = []
    fixed_peak = results['Fixed LR']['phi_peak']
    for label, data in results.items():
        delta = (data['phi_peak'] / max(fixed_peak, 1e-8) - 1) * 100
        rows.append([
            label,
            f"{data['phi_final']:.4f}",
            f"{data['phi_peak']:.4f}",
            f"{data['phi_mean_last50']:.4f}",
            f"{delta:+.1f}%",
            f"{data['time']:.2f}",
        ])
    print_table(
        ['Schedule', 'Phi_final', 'Phi_peak', 'Mean_L50', 'vs_Fixed', 'Time(s)'],
        rows
    )

    # Bar chart
    print(f"\n  Phi Peak Comparison:")
    max_phi = max(d['phi_peak'] for d in results.values())
    for label, data in results.items():
        ascii_bar(label, data['phi_peak'], max(max_phi, 0.001))

    # Trajectory comparison (sample every 30 steps)
    print(f"\n  Phi Trajectory (every {steps//10} steps):")
    sample_iv = max(steps // 10, 1)
    labels = list(results.keys())[:3]  # Show top 3
    header = f"  {'Step':>6s}" + ''.join(f"  {l:>14s}" for l in labels)
    print(header)
    print(f"  {'-' * (6 + 16 * len(labels))}")
    for i in range(0, steps, sample_iv):
        line = f"  {i:>6d}"
        for l in labels:
            line += f"  {results[l]['phis'][i]:>14.4f}"
        print(line)
    sys.stdout.flush()

    return results


# ═══════════════════════════════════════════════════════════
# C8: Topology Pumping — transition tension bursts → Hebbian boost
# ═══════════════════════════════════════════════════════════

def run_c8(cells: int = 32, steps: int = 300):
    """C8: Cycle through topologies, boost Hebbian at transition moments.

    Hypothesis: Topology transitions create tension spikes that
    can be harnessed for accelerated Hebbian learning.
    "Topology pumping" = structured topology cycling + Hebbian amplification.
    """
    print_header("C8: Topology Pumping (transition tension x Hebbian boost)")

    TOPOLOGIES = ['ring', 'small_world', 'scale_free']
    SWITCH_INTERVAL = steps // (len(TOPOLOGIES) * 2)  # Switch every ~50 steps
    HEBBIAN_BOOST = 10.0  # Amplify Hebbian LR by 10x at transition
    BOOST_WINDOW = 5      # Steps to boost after transition

    # --- Method 1: Single topology (ring baseline) ---
    print(f"  [1/3] Baseline: single topology (ring), {steps} steps...")
    sys.stdout.flush()
    engine_single = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    t0 = time.time()
    phis_single = run_steps(engine_single, steps)
    time_single = time.time() - t0

    # --- Method 2: Topology cycling (no boost) ---
    print(f"  [2/3] Cycling topologies (no Hebbian boost), {steps} steps...")
    sys.stdout.flush()
    engine_cycle = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    phis_cycle = []
    transitions_cycle = []
    t0 = time.time()

    for s in range(steps):
        topo_idx = (s // SWITCH_INTERVAL) % len(TOPOLOGIES)
        new_topo = TOPOLOGIES[topo_idx]
        if engine_cycle.topology != new_topo:
            engine_cycle.topology = new_topo
            transitions_cycle.append(s)

        result = engine_cycle.step()
        phis_cycle.append(result.get('phi_iit', 0.0))
    time_cycle = time.time() - t0

    # --- Method 3: Topology pumping (cycling + Hebbian boost at transitions) ---
    print(f"  [3/3] Topology pumping (cycling + {HEBBIAN_BOOST}x Hebbian boost), {steps} steps...")
    sys.stdout.flush()
    engine_pump = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    phis_pump = []
    transitions_pump = []
    boost_steps = set()  # Steps where boost is active
    t0 = time.time()

    for s in range(steps):
        topo_idx = (s // SWITCH_INTERVAL) % len(TOPOLOGIES)
        new_topo = TOPOLOGIES[topo_idx]
        is_transition = (engine_pump.topology != new_topo)
        if is_transition:
            engine_pump.topology = new_topo
            transitions_pump.append(s)
            for bs in range(s, min(s + BOOST_WINDOW, steps)):
                boost_steps.add(bs)

        result = engine_pump.step()
        phi = result.get('phi_iit', 0.0)
        phis_pump.append(phi)

        # Boosted Hebbian update at transition windows
        if s in boost_steps and engine_pump.n_cells >= 2:
            outputs = engine_pump.get_states()[:, :engine_pump.cell_dim]
            engine_pump._hebbian_update(outputs, lr=0.01 * HEBBIAN_BOOST)

    time_pump = time.time() - t0

    # --- Results ---
    phi_single_peak = max(phis_single) if phis_single else 0.0
    phi_cycle_peak = max(phis_cycle) if phis_cycle else 0.0
    phi_pump_peak = max(phis_pump) if phis_pump else 0.0

    phi_single_final = phis_single[-1] if phis_single else 0.0
    phi_cycle_final = phis_cycle[-1] if phis_cycle else 0.0
    phi_pump_final = phis_pump[-1] if phis_pump else 0.0

    print(f"\n  C8 Results ({cells}c, {steps} steps, switch every {SWITCH_INTERVAL}s)")
    print(f"  Transitions: {len(transitions_pump)} topology switches")
    print_table(
        ['Method', 'Phi_final', 'Phi_peak', 'Time(s)', 'vs_Ring'],
        [
            ['Ring only', f'{phi_single_final:.4f}', f'{phi_single_peak:.4f}',
             f'{time_single:.2f}', '-'],
            ['Topo cycling', f'{phi_cycle_final:.4f}', f'{phi_cycle_peak:.4f}',
             f'{time_cycle:.2f}',
             f'{(phi_cycle_peak/max(phi_single_peak,1e-8)-1)*100:+.1f}%'],
            ['Topo pumping', f'{phi_pump_final:.4f}', f'{phi_pump_peak:.4f}',
             f'{time_pump:.2f}',
             f'{(phi_pump_peak/max(phi_single_peak,1e-8)-1)*100:+.1f}%'],
        ]
    )

    # Phi around transitions
    if transitions_pump:
        print(f"\n  Phi around first transition (step {transitions_pump[0]}):")
        t_step = transitions_pump[0]
        window = 10
        start = max(0, t_step - window)
        end = min(steps, t_step + window + 1)
        for s in range(start, end):
            marker = " <-- SWITCH" if s == t_step else ""
            boost = " [BOOST]" if s in boost_steps else ""
            p_pump = phis_pump[s] if s < len(phis_pump) else 0
            p_single = phis_single[s] if s < len(phis_single) else 0
            print(f"    step {s:>4d}  pump={p_pump:.4f}  ring={p_single:.4f}  "
                  f"delta={p_pump-p_single:+.4f}{marker}{boost}")

    # Bar chart
    print(f"\n  Phi Peak Comparison:")
    max_phi = max(phi_single_peak, phi_cycle_peak, phi_pump_peak, 0.001)
    ascii_bar('Ring only', phi_single_peak, max_phi)
    ascii_bar('Topo cycling', phi_cycle_peak, max_phi)
    ascii_bar('Topo pumping', phi_pump_peak, max_phi)

    sys.stdout.flush()

    return {
        'single_phi': phi_single_peak,
        'cycle_phi': phi_cycle_peak,
        'pump_phi': phi_pump_peak,
        'n_transitions': len(transitions_pump),
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='C-series acceleration experiments')
    parser.add_argument('--c1', action='store_true', help='C1: Consciousness Compiler')
    parser.add_argument('--c2', action='store_true', help='C2: Fractal Consciousness')
    parser.add_argument('--c4', action='store_true', help='C4: Reverse-Time Consciousness')
    parser.add_argument('--c5', action='store_true', help='C5: Resonance Frequency Matching')
    parser.add_argument('--c8', action='store_true', help='C8: Topology Pumping')
    parser.add_argument('--cells', type=int, default=32, help='Number of cells (default: 32)')
    parser.add_argument('--steps', type=int, default=300, help='Steps per experiment (default: 300)')
    args = parser.parse_args()

    run_all = not (args.c1 or args.c2 or args.c4 or args.c5 or args.c8)

    print(f"\n  C-Series Acceleration Experiments")
    print(f"  Cells: {args.cells}, Steps: {args.steps}")
    print(f"  Device: CPU (local)")
    t_total = time.time()

    all_results = {}

    if run_all or args.c1:
        all_results['C1'] = run_c1(cells=args.cells, steps=args.steps)

    if run_all or args.c2:
        small = max(4, args.cells // 8)
        all_results['C2'] = run_c2(small_cells=small, large_cells=args.cells, steps=args.steps)

    if run_all or args.c4:
        all_results['C4'] = run_c4(cells=args.cells, steps=args.steps)

    if run_all or args.c5:
        all_results['C5'] = run_c5(cells=args.cells, steps=args.steps)

    if run_all or args.c8:
        all_results['C8'] = run_c8(cells=args.cells, steps=args.steps)

    # --- Summary ---
    elapsed = time.time() - t_total
    print_header("C-Series Summary")

    if 'C1' in all_results:
        r = all_results['C1']
        print(f"  C1 Compiler:  baseline={r['baseline_phi']:.4f}  "
              f"hybrid={r['hybrid_phi']:.4f}  "
              f"compile_time={r['compile_time']:.3f}s  "
              f"laws_applied={r['laws_applied']}")

    if 'C2' in all_results:
        r = all_results['C2']
        print(f"  C2 Fractal:   random={r['random_phi']:.4f}  "
              f"fractal={r['fractal_phi']:.4f}  "
              f"init_boost={r['fractal_init_phi']:.4f}  "
              f"speedup={r['speedup_50pct']:.1f}x")

    if 'C4' in all_results:
        r = all_results['C4']
        print(f"  C4 ReverseT:  random={r['random_peak']:.4f}  "
              f"donor={r['donor_peak']:.4f}  "
              f"inject_t0={r['inject_t0']:.4f}  "
              f"retention={r['retention']:.1%}")

    if 'C5' in all_results:
        r = all_results['C5']
        fixed = r['Fixed LR']['phi_peak']
        reson = r['Resonance']['phi_peak']
        print(f"  C5 Resonance: fixed={fixed:.4f}  "
              f"resonance={reson:.4f}  "
              f"delta={((reson/max(fixed,1e-8))-1)*100:+.1f}%")

    if 'C8' in all_results:
        r = all_results['C8']
        print(f"  C8 TopoPump:  ring={r['single_phi']:.4f}  "
              f"pump={r['pump_phi']:.4f}  "
              f"delta={((r['pump_phi']/max(r['single_phi'],1e-8))-1)*100:+.1f}%  "
              f"transitions={r['n_transitions']}")

    print(f"\n  Total time: {elapsed:.1f}s")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
