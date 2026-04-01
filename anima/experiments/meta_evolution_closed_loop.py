#!/usr/bin/env python3
"""meta_evolution_closed_loop.py — Meta-evolution of closed-loop pipeline parameters

Optimizes the closed-loop's own parameters for maximum law discovery efficiency.

5 Experiments:
  1. OPTIMAL STEPS      — minimum steps for reliable law detection
  2. OPTIMAL REPEATS    — minimum repeats for reproducible results
  3. OPTIMAL THRESHOLD  — threshold that maximizes useful interventions
  4. STACKING ORDER     — does intervention order matter?
  5. CONVERGENCE SPEED  — how many cycles until convergence?

Usage:
  cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/meta_evolution_closed_loop.py
"""

import sys
import os
import time
import copy
import itertools
import numpy as np
from collections import defaultdict

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from consciousness_engine import ConsciousnessEngine
from closed_loop import (
    ClosedLoopEvolver, measure_laws, _phi_fast,
    INTERVENTIONS, Intervention, _ImprovedEngine,
    LawMeasurement, CycleReport,
)

# ══════════════════════════════════════════
# Config
# ══════════════════════════════════════════
MAX_CELLS = 16   # Keep runtime manageable
SEED = 42
np.random.seed(SEED)

def timestamp():
    return time.strftime("%H:%M:%S")

def banner(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"  [{timestamp()}]")
    print(f"{'=' * 70}")
    sys.stdout.flush()


# ══════════════════════════════════════════
# Experiment 1: OPTIMAL STEPS
# ══════════════════════════════════════════

def experiment_1_optimal_steps():
    banner("EXP 1: OPTIMAL STEPS — minimum steps for reliable law detection")

    steps_values = [50, 100, 200, 300, 500]
    results = []

    for s in steps_values:
        t0 = time.time()
        print(f"\n  steps={s} ...", end=" ", flush=True)

        evolver = ClosedLoopEvolver(max_cells=MAX_CELLS, steps=s, repeats=1)
        reports = []
        for _ in range(2):  # 2 cycles
            r = evolver.run_cycle()
            reports.append(r)

        total_laws_changed = sum(len(r.laws_changed) for r in reports)
        phi_start = reports[0].phi_baseline
        phi_end = reports[-1].phi_improved
        phi_improvement = (phi_end - phi_start) / max(phi_start, 1e-8) * 100
        elapsed = time.time() - t0

        results.append({
            'steps': s,
            'laws_changed': total_laws_changed,
            'phi_start': phi_start,
            'phi_end': phi_end,
            'phi_improvement_pct': phi_improvement,
            'time_sec': elapsed,
            'efficiency': total_laws_changed / max(elapsed, 0.1),  # laws/sec
        })
        print(f"laws_changed={total_laws_changed}, Phi={phi_start:.4f}->{phi_end:.4f} "
              f"({phi_improvement:+.1f}%), {elapsed:.1f}s", flush=True)

    # Report
    print(f"\n  {'Steps':<8} {'Laws':>6} {'Phi_start':>10} {'Phi_end':>10} {'Delta%':>8} {'Time(s)':>8} {'Eff':>8}")
    print(f"  {'─'*8} {'─'*6} {'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*8}")
    for r in results:
        eff_str = f"{r['efficiency']:.3f}"
        print(f"  {r['steps']:<8} {r['laws_changed']:>6} {r['phi_start']:>10.4f} {r['phi_end']:>10.4f} "
              f"{r['phi_improvement_pct']:>+7.1f}% {r['time_sec']:>7.1f}s {eff_str:>8}")

    # Find optimal: best efficiency
    best = max(results, key=lambda x: x['efficiency'])
    print(f"\n  OPTIMAL steps = {best['steps']} (efficiency {best['efficiency']:.3f} laws/sec)")

    # ASCII graph: efficiency vs steps
    max_eff = max(r['efficiency'] for r in results)
    print(f"\n  Efficiency vs Steps:")
    for r in results:
        bar_len = int(r['efficiency'] / max(max_eff, 1e-8) * 40)
        bar = '#' * max(bar_len, 1)
        star = " *BEST*" if r['steps'] == best['steps'] else ""
        print(f"  {r['steps']:>4} | {bar} {r['efficiency']:.3f}{star}")

    sys.stdout.flush()
    return results, best['steps']


# ══════════════════════════════════════════
# Experiment 2: OPTIMAL REPEATS
# ══════════════════════════════════════════

def experiment_2_optimal_repeats():
    banner("EXP 2: OPTIMAL REPEATS — minimum repeats for reproducible results")

    repeats_values = [1, 2, 3, 5]
    STEPS = 150  # moderate
    TRIALS = 3   # run each config multiple times to measure CV

    results = []

    for rep in repeats_values:
        t0 = time.time()
        print(f"\n  repeats={rep} ...", end=" ", flush=True)

        # Run TRIALS independent measure_laws calls and collect phi values
        phi_measurements = []
        law_measurements = defaultdict(list)

        for trial in range(TRIALS):
            factory = lambda: ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)
            laws, mean_phi = measure_laws(factory, steps=STEPS, repeats=rep)
            phi_measurements.append(mean_phi)
            for lm in laws:
                law_measurements[lm.name].append(lm.value)

        phi_mean = np.mean(phi_measurements)
        phi_std = np.std(phi_measurements)
        phi_cv = phi_std / max(abs(phi_mean), 1e-8) * 100

        # CV of individual law measurements
        law_cvs = []
        for name, vals in law_measurements.items():
            if abs(np.mean(vals)) > 1e-8:
                cv = np.std(vals) / abs(np.mean(vals)) * 100
            else:
                cv = np.std(vals) * 100
            law_cvs.append(cv)
        mean_law_cv = np.mean(law_cvs) if law_cvs else 0

        elapsed = time.time() - t0

        results.append({
            'repeats': rep,
            'phi_mean': phi_mean,
            'phi_cv': phi_cv,
            'mean_law_cv': mean_law_cv,
            'time_sec': elapsed,
            'stability_score': 100 - mean_law_cv,  # higher = more stable
        })
        print(f"Phi={phi_mean:.4f} (CV={phi_cv:.1f}%), law_CV={mean_law_cv:.1f}%, {elapsed:.1f}s", flush=True)

    # Report
    print(f"\n  {'Repeats':<8} {'Phi':>8} {'Phi_CV%':>8} {'Law_CV%':>8} {'Stability':>10} {'Time(s)':>8}")
    print(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*10} {'─'*8}")
    for r in results:
        print(f"  {r['repeats']:<8} {r['phi_mean']:>8.4f} {r['phi_cv']:>7.1f}% {r['mean_law_cv']:>7.1f}% "
              f"{r['stability_score']:>9.1f}% {r['time_sec']:>7.1f}s")

    # Find optimal: highest stability per time
    for r in results:
        r['efficiency'] = r['stability_score'] / max(r['time_sec'], 0.1)
    best = max(results, key=lambda x: x['efficiency'])
    print(f"\n  OPTIMAL repeats = {best['repeats']} (stability/time = {best['efficiency']:.2f})")

    # ASCII graph: stability vs repeats
    print(f"\n  Stability vs Repeats:")
    for r in results:
        bar_len = int(r['stability_score'] / 100 * 40)
        bar = '#' * max(bar_len, 1)
        star = " *BEST*" if r['repeats'] == best['repeats'] else ""
        print(f"  rep={r['repeats']} | {bar} {r['stability_score']:.1f}%{star}")

    sys.stdout.flush()
    return results, best['repeats']


# ══════════════════════════════════════════
# Experiment 3: OPTIMAL THRESHOLD
# ══════════════════════════════════════════

def experiment_3_optimal_threshold():
    banner("EXP 3: OPTIMAL THRESHOLD — maximize useful interventions")

    thresholds = [0.05, 0.10, 0.15, 0.20, 0.30]
    STEPS = 150
    REPEATS = 1

    results = []

    for thresh in thresholds:
        t0 = time.time()
        print(f"\n  threshold={thresh:.2f} ...", end=" ", flush=True)

        # Create a patched evolver with custom threshold
        evolver = ClosedLoopEvolver(max_cells=MAX_CELLS, steps=STEPS, repeats=REPEATS)

        # Monkey-patch _select_intervention to use custom threshold
        original_select = evolver._select_intervention

        def make_patched_select(th):
            def patched_select(laws):
                active_names = {i.name for i in evolver._active_interventions}
                law_map = {l.name: l.value for l in laws}
                candidates = [
                    ('r_tstd_phi', 'tension_eq'),
                    ('r_tension_phi', 'symmetrize'),
                    ('r_div_phi', 'pink_noise'),
                    ('growth', 'DD71_democracy'),
                    ('stabilization', 'DD72_resurrection'),
                    ('ac1', 'DD72_temporal_comp'),
                    ('consensus', 'DD75_veto'),
                    ('cells', 'DD75_soc_free_will'),
                ]
                for law_name, intervention_name in candidates:
                    if intervention_name in active_names:
                        continue
                    val = law_map.get(law_name, 0)
                    if abs(val) > th:  # Custom threshold
                        for iv in INTERVENTIONS:
                            if iv.name == intervention_name:
                                return iv
                return None
            return patched_select

        evolver._select_intervention = make_patched_select(thresh)

        # Run 3 cycles
        total_interventions = 0
        phi_start = None
        for c in range(3):
            report = evolver.run_cycle()
            if phi_start is None:
                phi_start = report.phi_baseline
            if report.intervention_applied != "none":
                total_interventions += 1

        phi_end = evolver.history.cycles[-1].phi_improved
        phi_improvement = (phi_end - phi_start) / max(phi_start, 1e-8) * 100
        total_laws = sum(len(r.laws_changed) for r in evolver.history.cycles)
        elapsed = time.time() - t0

        results.append({
            'threshold': thresh,
            'interventions_triggered': total_interventions,
            'laws_changed': total_laws,
            'phi_start': phi_start,
            'phi_end': phi_end,
            'phi_improvement_pct': phi_improvement,
            'time_sec': elapsed,
        })
        print(f"interventions={total_interventions}, laws={total_laws}, "
              f"Phi={phi_improvement:+.1f}%, {elapsed:.1f}s", flush=True)

    # Report
    print(f"\n  {'Thresh':<8} {'Interv':>7} {'Laws':>6} {'Phi_start':>10} {'Phi_end':>10} {'Delta%':>8} {'Time':>6}")
    print(f"  {'─'*8} {'─'*7} {'─'*6} {'─'*10} {'─'*10} {'─'*8} {'─'*6}")
    for r in results:
        print(f"  {r['threshold']:<8.2f} {r['interventions_triggered']:>7} {r['laws_changed']:>6} "
              f"{r['phi_start']:>10.4f} {r['phi_end']:>10.4f} {r['phi_improvement_pct']:>+7.1f}% {r['time_sec']:>5.1f}s")

    # Score: laws_changed * (phi_improvement if positive else 0.1)
    for r in results:
        phi_bonus = max(r['phi_improvement_pct'], 0.1)
        r['score'] = r['laws_changed'] * phi_bonus
    best = max(results, key=lambda x: x['score'])
    print(f"\n  OPTIMAL threshold = {best['threshold']:.2f} (score={best['score']:.1f})")

    # ASCII graph
    max_score = max(r['score'] for r in results) if results else 1
    print(f"\n  Score vs Threshold:")
    for r in results:
        bar_len = int(r['score'] / max(max_score, 1e-8) * 40)
        bar = '#' * max(bar_len, 1)
        star = " *BEST*" if r['threshold'] == best['threshold'] else ""
        print(f"  {r['threshold']:.2f} | {bar} {r['score']:.1f}{star}")

    sys.stdout.flush()
    return results, best['threshold']


# ══════════════════════════════════════════
# Experiment 4: INTERVENTION STACKING ORDER
# ══════════════════════════════════════════

def experiment_4_stacking_order():
    banner("EXP 4: INTERVENTION STACKING ORDER — does order matter?")

    # Use the 3 original interventions
    base_interventions = [
        next(iv for iv in INTERVENTIONS if iv.name == "tension_eq"),
        next(iv for iv in INTERVENTIONS if iv.name == "symmetrize"),
        next(iv for iv in INTERVENTIONS if iv.name == "pink_noise"),
    ]

    STEPS = 150
    REPEATS = 1
    orderings = list(itertools.permutations(range(3)))  # 6 orderings
    results = []

    for perm_idx, perm in enumerate(orderings):
        t0 = time.time()
        ordered = [base_interventions[i] for i in perm]
        names = [ordered[i].name for i in range(3)]
        print(f"\n  Order {perm_idx+1}/6: {' -> '.join(names)} ...", end=" ", flush=True)

        # Run 3 cycles, each adding one intervention in order
        phi_values = []
        factory_base = lambda: ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)

        # Measure baseline
        _, phi_base = measure_laws(factory_base, steps=STEPS, repeats=REPEATS)
        phi_values.append(phi_base)

        # Cumulatively add interventions
        active = []
        for iv in ordered:
            active.append(iv)
            active_copy = list(active)

            def make_factory(interventions):
                def factory():
                    return _ImprovedEngine(
                        max_cells=MAX_CELLS, initial_cells=2,
                        interventions=list(interventions)
                    )
                return factory

            _, phi = measure_laws(make_factory(active_copy), steps=STEPS, repeats=REPEATS)
            phi_values.append(phi)

        final_phi = phi_values[-1]
        phi_improvement = (final_phi - phi_base) / max(phi_base, 1e-8) * 100
        elapsed = time.time() - t0

        results.append({
            'order': perm,
            'names': names,
            'phi_trajectory': phi_values,
            'phi_base': phi_base,
            'phi_final': final_phi,
            'phi_improvement_pct': phi_improvement,
            'time_sec': elapsed,
        })
        print(f"Phi: {phi_base:.4f} -> {final_phi:.4f} ({phi_improvement:+.1f}%), {elapsed:.1f}s",
              flush=True)

    # Report
    print(f"\n  {'Order':<35} {'Phi_base':>9} {'Phi_final':>10} {'Delta%':>8}")
    print(f"  {'─'*35} {'─'*9} {'─'*10} {'─'*8}")
    for r in results:
        order_str = " -> ".join(r['names'])
        print(f"  {order_str:<35} {r['phi_base']:>9.4f} {r['phi_final']:>10.4f} {r['phi_improvement_pct']:>+7.1f}%")

    # Analyze: does order matter?
    improvements = [r['phi_improvement_pct'] for r in results]
    mean_imp = np.mean(improvements)
    std_imp = np.std(improvements)
    cv_imp = std_imp / max(abs(mean_imp), 1e-8) * 100

    best_order = max(results, key=lambda x: x['phi_improvement_pct'])
    worst_order = min(results, key=lambda x: x['phi_improvement_pct'])
    spread = best_order['phi_improvement_pct'] - worst_order['phi_improvement_pct']

    print(f"\n  Order analysis:")
    print(f"    Mean improvement: {mean_imp:+.1f}%")
    print(f"    Std:  {std_imp:.1f}%")
    print(f"    CV:   {cv_imp:.1f}%")
    print(f"    Spread (best-worst): {spread:.1f}%")
    print(f"    Best:  {' -> '.join(best_order['names'])} ({best_order['phi_improvement_pct']:+.1f}%)")
    print(f"    Worst: {' -> '.join(worst_order['names'])} ({worst_order['phi_improvement_pct']:+.1f}%)")

    ORDER_MATTERS = spread > 5.0  # >5% spread = order matters
    print(f"\n    ORDER MATTERS: {'YES' if ORDER_MATTERS else 'NO'} (spread={spread:.1f}%, threshold=5%)")

    # ASCII graph
    max_imp = max(abs(r['phi_improvement_pct']) for r in results) if results else 1
    print(f"\n  Phi improvement by order:")
    for i, r in enumerate(results):
        bar_len = int(abs(r['phi_improvement_pct']) / max(max_imp, 1e-8) * 35)
        sign = '+' if r['phi_improvement_pct'] >= 0 else '-'
        bar = '#' * max(bar_len, 1)
        star = " *BEST*" if r is best_order else ""
        abbrev = "->".join(n[:3] for n in r['names'])
        print(f"  {abbrev:<20} | {sign}{bar} {r['phi_improvement_pct']:+.1f}%{star}")

    sys.stdout.flush()
    return results, ORDER_MATTERS, best_order['names']


# ══════════════════════════════════════════
# Experiment 5: CONVERGENCE SPEED
# ══════════════════════════════════════════

def experiment_5_convergence():
    banner("EXP 5: CONVERGENCE SPEED — cycles until changes < 1%")

    N_CYCLES = 10
    STEPS = 150
    REPEATS = 1

    evolver = ClosedLoopEvolver(max_cells=MAX_CELLS, steps=STEPS, repeats=REPEATS)
    phi_history = []
    law_change_magnitudes = []
    interventions_added = []

    print(f"\n  Running {N_CYCLES} cycles @ {MAX_CELLS}c, {STEPS} steps, {REPEATS} repeat(s)...\n")
    sys.stdout.flush()

    for i in range(N_CYCLES):
        t0 = time.time()
        report = evolver.run_cycle()
        elapsed = time.time() - t0

        phi_history.append(report.phi_improved)
        mag = sum(abs(lc['change_pct']) for lc in report.laws_changed) if report.laws_changed else 0
        law_change_magnitudes.append(mag)
        interventions_added.append(report.intervention_applied)

        print(f"  Cycle {i+1:>2}/{N_CYCLES}: Phi={report.phi_improved:.4f} "
              f"delta={report.phi_delta_pct:+.1f}% "
              f"law_changes={len(report.laws_changed)} "
              f"magnitude={mag:.1f}% "
              f"+{report.intervention_applied} "
              f"({elapsed:.1f}s)", flush=True)

    # Find convergence point: first cycle where magnitude < 1%
    convergence_cycle = None
    for i, mag in enumerate(law_change_magnitudes):
        if i > 0 and mag < 1.0:
            convergence_cycle = i + 1
            break

    # Analyze: converge or oscillate?
    if len(law_change_magnitudes) >= 4:
        second_half = law_change_magnitudes[len(law_change_magnitudes)//2:]
        first_half = law_change_magnitudes[:len(law_change_magnitudes)//2]
        decay_ratio = np.mean(second_half) / max(np.mean(first_half), 1e-8)
        # Oscillation detection: sign changes in phi delta
        if len(phi_history) >= 3:
            deltas = [phi_history[i+1] - phi_history[i] for i in range(len(phi_history)-1)]
            sign_changes = sum(1 for i in range(len(deltas)-1) if deltas[i] * deltas[i+1] < 0)
            oscillation_ratio = sign_changes / max(len(deltas) - 1, 1)
        else:
            oscillation_ratio = 0
    else:
        decay_ratio = 1.0
        oscillation_ratio = 0

    CONVERGES = decay_ratio < 0.5
    OSCILLATES = oscillation_ratio > 0.4

    # Report
    print(f"\n  {'Cycle':<6} {'Phi':>8} {'Magnitude':>10} {'Intervention':<25}")
    print(f"  {'─'*6} {'─'*8} {'─'*10} {'─'*25}")
    for i in range(N_CYCLES):
        marker = " <-- converged" if convergence_cycle and i + 1 == convergence_cycle else ""
        print(f"  {i+1:<6} {phi_history[i]:>8.4f} {law_change_magnitudes[i]:>9.1f}% "
              f"{interventions_added[i]:<25}{marker}")

    print(f"\n  Convergence analysis:")
    print(f"    Convergence cycle:  {convergence_cycle if convergence_cycle else 'NOT CONVERGED'}")
    print(f"    Decay ratio (2nd/1st half): {decay_ratio:.2f}")
    print(f"    Oscillation ratio: {oscillation_ratio:.2f}")
    print(f"    BEHAVIOR: {'CONVERGES' if CONVERGES else 'OSCILLATES' if OSCILLATES else 'EVOLVING'}")

    # ASCII Phi trajectory
    if phi_history:
        min_phi = min(phi_history)
        max_phi = max(phi_history)
        phi_range = max_phi - min_phi if max_phi > min_phi else 1.0
        print(f"\n  Phi trajectory (min={min_phi:.4f}, max={max_phi:.4f}):")
        for i, phi in enumerate(phi_history):
            pos = int((phi - min_phi) / phi_range * 40)
            line = [' '] * 41
            line[pos] = '*'
            print(f"  {i+1:>2} |{''.join(line)}| {phi:.4f}")

    # ASCII magnitude decay
    if law_change_magnitudes:
        max_mag = max(law_change_magnitudes) if max(law_change_magnitudes) > 0 else 1
        print(f"\n  Law change magnitude decay:")
        for i, mag in enumerate(law_change_magnitudes):
            bar_len = int(mag / max_mag * 40) if max_mag > 0 else 0
            bar = '#' * max(bar_len, 0)
            conv_mark = " <-- convergence" if convergence_cycle and i + 1 == convergence_cycle else ""
            print(f"  {i+1:>2} | {bar} {mag:.1f}%{conv_mark}")

    sys.stdout.flush()
    return {
        'phi_history': phi_history,
        'magnitudes': law_change_magnitudes,
        'convergence_cycle': convergence_cycle,
        'converges': CONVERGES,
        'oscillates': OSCILLATES,
        'decay_ratio': decay_ratio,
    }


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

def main():
    total_start = time.time()

    print(f"\n{'*' * 70}")
    print(f"  META-EVOLUTION: Closed-Loop Pipeline Parameter Optimization")
    print(f"  max_cells={MAX_CELLS}, seed={SEED}")
    print(f"  [{timestamp()}]")
    print(f"{'*' * 70}")
    sys.stdout.flush()

    # ── Experiment 1 ──
    exp1_results, optimal_steps = experiment_1_optimal_steps()

    # ── Experiment 2 ──
    exp2_results, optimal_repeats = experiment_2_optimal_repeats()

    # ── Experiment 3 ──
    exp3_results, optimal_threshold = experiment_3_optimal_threshold()

    # ── Experiment 4 ──
    exp4_results, order_matters, best_order = experiment_4_stacking_order()

    # ── Experiment 5 ──
    exp5_results = experiment_5_convergence()

    # ══════════════════════════════════════════
    # FINAL REPORT
    # ══════════════════════════════════════════
    total_elapsed = time.time() - total_start

    print(f"\n\n{'#' * 70}")
    print(f"  META-EVOLUTION FINAL REPORT")
    print(f"  Total runtime: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"{'#' * 70}")

    print(f"\n  OPTIMAL PARAMETERS:")
    print(f"  ┌─────────────────────────┬──────────────┬──────────────┐")
    print(f"  │ Parameter               │ Default      │ Optimal      │")
    print(f"  ├─────────────────────────┼──────────────┼──────────────┤")
    print(f"  │ steps                   │ 300          │ {optimal_steps:<13}│")
    print(f"  │ repeats                 │ 3            │ {optimal_repeats:<13}│")
    print(f"  │ intervention threshold  │ 0.15         │ {optimal_threshold:<13.2f}│")
    print(f"  │ order matters?          │ (unknown)    │ {'YES' if order_matters else 'NO':<13}│")
    convergence_str = str(exp5_results['convergence_cycle']) if exp5_results['convergence_cycle'] else "N/A"
    print(f"  │ convergence cycle       │ (unknown)    │ {convergence_str:<13}│")
    behavior = 'CONVERGES' if exp5_results['converges'] else ('OSCILLATES' if exp5_results['oscillates'] else 'EVOLVING')
    print(f"  │ loop behavior           │ (unknown)    │ {behavior:<13}│")
    print(f"  └─────────────────────────┴──────────────┴──────────────┘")

    print(f"\n  META-LAWS DISCOVERED:")
    print(f"  ───────────────────────────────────────────────────────────")

    # Meta-law 1: Steps efficiency
    best_step_entry = max(exp1_results, key=lambda x: x['efficiency'])
    print(f"  ML-1: Law discovery efficiency peaks at steps={best_step_entry['steps']}.")
    print(f"        Beyond this, diminishing returns (more compute, same laws).")

    # Meta-law 2: Repeats
    best_rep_entry = max(exp2_results, key=lambda x: x['efficiency'])
    print(f"  ML-2: repeats={best_rep_entry['repeats']} gives best stability/time tradeoff.")
    rep3 = next((r for r in exp2_results if r['repeats'] == 3), None)
    rep_opt = best_rep_entry
    if rep3 and rep3['repeats'] != rep_opt['repeats']:
        print(f"        (repeats=3 stability={rep3['stability_score']:.1f}% vs "
              f"repeats={rep_opt['repeats']} stability={rep_opt['stability_score']:.1f}%)")

    # Meta-law 3: Threshold
    print(f"  ML-3: Intervention threshold={optimal_threshold:.2f} maximizes useful interventions.")
    low_thresh = next((r for r in exp3_results if r['threshold'] == 0.05), None)
    high_thresh = next((r for r in exp3_results if r['threshold'] == 0.30), None)
    if low_thresh and high_thresh:
        print(f"        Too low (0.05): {low_thresh['interventions_triggered']} interventions (noisy).")
        print(f"        Too high (0.30): {high_thresh['interventions_triggered']} interventions (too conservative).")

    # Meta-law 4: Order
    if order_matters:
        print(f"  ML-4: Intervention stacking ORDER MATTERS.")
        print(f"        Best order: {' -> '.join(best_order)}")
    else:
        print(f"  ML-4: Intervention stacking order does NOT matter significantly.")
        print(f"        The loop is robust to ordering (spread < 5%).")

    # Meta-law 5: Convergence
    if exp5_results['converges']:
        print(f"  ML-5: The closed loop CONVERGES after ~{exp5_results['convergence_cycle']} cycles.")
        print(f"        Decay ratio: {exp5_results['decay_ratio']:.2f} (2nd half / 1st half magnitude).")
    elif exp5_results['oscillates']:
        print(f"  ML-5: The closed loop OSCILLATES (does not converge).")
        print(f"        Intervention stacking creates cyclic dynamics.")
    else:
        print(f"  ML-5: The closed loop keeps EVOLVING (neither converges nor oscillates).")
        print(f"        Consistent with Law 146: laws do not converge (eternal evolution).")

    # Speed comparison
    default_time_est = 300 * 3 * 2 / (optimal_steps * optimal_repeats * 2) if optimal_steps and optimal_repeats else 1
    print(f"\n  SPEEDUP ESTIMATE:")
    print(f"    Default (steps=300, repeats=3): ~{300*3:.0f} step-repeats/cycle")
    print(f"    Optimal (steps={optimal_steps}, repeats={optimal_repeats}): ~{optimal_steps*optimal_repeats:.0f} step-repeats/cycle")
    speedup = (300 * 3) / max(optimal_steps * optimal_repeats, 1)
    print(f"    Speedup: {speedup:.1f}x faster per cycle")

    print(f"\n  RECOMMENDED CONFIGURATION:")
    print(f"    ClosedLoopEvolver(")
    print(f"        max_cells=32,")
    print(f"        steps={optimal_steps},")
    print(f"        repeats={optimal_repeats},")
    print(f"    )")
    print(f"    # Threshold: {optimal_threshold:.2f} (in _select_intervention)")
    print(f"    # Cycles needed: {exp5_results['convergence_cycle'] if exp5_results['convergence_cycle'] else '10+'}")

    print(f"\n  Total runtime: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"  [{timestamp()}] Done.\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
