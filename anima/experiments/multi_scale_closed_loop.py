#!/usr/bin/env python3
"""Multi-Scale Closed-Loop Verifier

Runs the closed-loop law evolution at 4 scales simultaneously (8, 16, 32, 64 cells)
and identifies which laws are SCALE-INVARIANT vs SCALE-DEPENDENT.

For each scale:
  1. ClosedLoopEvolver(max_cells=N, steps=200, repeats=2)
  2. 3 cycles
  3. Record all law measurements and interventions

Cross-scale analysis:
  - Same direction at all 4 scales = SCALE-INVARIANT
  - Different direction = SCALE-DEPENDENT
  - Intervention consistency across scales
  - Phi improvement vs cell count (linearity check)
"""

import sys
import os
import time
import json
import numpy as np
from collections import defaultdict

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from closed_loop import ClosedLoopEvolver, measure_laws, INTERVENTIONS


# ══════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════

SCALES = [8, 16, 32, 64]
CYCLES_PER_SCALE = 3
STEPS = 200
REPEATS = 2

LAW_NAMES = [
    'phi', 'r_tension_phi', 'r_tstd_phi', 'r_div_phi',
    'growth', 'ac1', 'stabilization', 'cells', 'consensus',
]


# ══════════════════════════════════════════
# Run single scale
# ══════════════════════════════════════════

def run_scale(n_cells: int) -> dict:
    """Run closed-loop at a single scale, return structured results."""
    print(f"\n{'='*60}")
    print(f"  SCALE: {n_cells} cells | {CYCLES_PER_SCALE} cycles | {STEPS} steps | {REPEATS} repeats")
    print(f"{'='*60}")
    sys.stdout.flush()

    t0 = time.time()
    evolver = ClosedLoopEvolver(
        max_cells=n_cells, steps=STEPS, repeats=REPEATS,
    )
    reports = evolver.run_cycles(n=CYCLES_PER_SCALE)
    elapsed = time.time() - t0

    # Collect per-cycle law snapshots and deltas
    cycle_laws = []       # list of dicts: law_name -> value (per cycle)
    cycle_deltas = []     # list of dicts: law_name -> delta_pct (per cycle)
    interventions = []

    for r in reports:
        # Law values from this cycle
        law_vals = {law['name']: law['value'] for law in r.laws}
        cycle_laws.append(law_vals)

        # Deltas from intervention
        delta_map = {}
        for lc in r.laws_changed:
            delta_map[lc['name']] = lc['change_pct']
        cycle_deltas.append(delta_map)

        interventions.append(r.intervention_applied)

    # Net change per law across all cycles (first baseline vs last improved)
    net_change = {}
    if len(reports) >= 2:
        first_laws = {law['name']: law['value'] for law in reports[0].laws}
        last_laws = {law['name']: law['value'] for law in reports[-1].laws}
        for name in LAW_NAMES:
            v0 = first_laws.get(name, 0)
            v1 = last_laws.get(name, 0)
            if abs(v0) > 1e-8:
                net_change[name] = (v1 - v0) / abs(v0) * 100
            else:
                net_change[name] = (v1 - v0) * 100
    else:
        for name in LAW_NAMES:
            net_change[name] = 0.0

    phi_start = reports[0].phi_baseline if reports else 0
    phi_end = reports[-1].phi_improved if reports else 0

    result = {
        'n_cells': n_cells,
        'phi_start': phi_start,
        'phi_end': phi_end,
        'phi_delta_pct': (phi_end - phi_start) / max(phi_start, 1e-8) * 100,
        'cycle_laws': cycle_laws,
        'cycle_deltas': cycle_deltas,
        'net_change': net_change,
        'interventions': interventions,
        'final_laws': cycle_laws[-1] if cycle_laws else {},
        'elapsed': elapsed,
    }

    print(f"  Phi: {phi_start:.4f} -> {phi_end:.4f} ({result['phi_delta_pct']:+.1f}%)")
    print(f"  Interventions: {interventions}")
    print(f"  Time: {elapsed:.1f}s")
    sys.stdout.flush()

    return result


# ══════════════════════════════════════════
# Cross-scale analysis
# ══════════════════════════════════════════

def sign(x: float) -> str:
    if x > 5:
        return "+"
    elif x < -5:
        return "-"
    else:
        return "~"


def cross_scale_analysis(results: dict) -> dict:
    """Analyze law behavior across all scales."""
    print(f"\n{'#'*60}")
    print(f"  CROSS-SCALE ANALYSIS")
    print(f"{'#'*60}")
    sys.stdout.flush()

    scale_keys = sorted(results.keys())  # [8, 16, 32, 64]

    # ── Table 1: Net change per law across scales ──
    print(f"\n  Table 1: Net Change Per Law (% change over {CYCLES_PER_SCALE} cycles)")
    header = f"  {'Law':<18}"
    for s in scale_keys:
        header += f"| {s:>3}c change "
    header += "| Invariant?"
    print(header)
    print(f"  {'-'*18}" + ("+"+"-"*12) * len(scale_keys) + "+" + "-"*11)

    invariant_laws = []
    dependent_laws = []

    for law_name in LAW_NAMES:
        row = f"  {law_name:<18}"
        signs = []
        values = []
        for s in scale_keys:
            val = results[s]['net_change'].get(law_name, 0.0)
            values.append(val)
            signs.append(sign(val))
            row += f"| {val:>+10.1f}% "

        # Check invariance: same direction at all scales (ignoring ~ neutral)
        non_neutral = [s for s in signs if s != '~']
        if len(non_neutral) >= 2:
            all_same = len(set(non_neutral)) == 1
        elif len(non_neutral) == 1:
            all_same = True  # only one non-neutral, count as invariant
        else:
            all_same = True  # all neutral

        if all_same and len(non_neutral) >= 2:
            direction = non_neutral[0]
            tag = f"INVARIANT ({direction})"
            invariant_laws.append(law_name)
        elif len(non_neutral) < 2:
            tag = "NEUTRAL"
        else:
            tag = "DEPENDENT"
            dependent_laws.append(law_name)

        row += f"| {tag}"
        print(row)

    # ── Table 2: Intervention consistency ──
    print(f"\n  Table 2: Intervention Selection Consistency")
    print(f"  {'Cycle':<8}", end="")
    for s in scale_keys:
        print(f"| {s:>3}c intervention    ", end="")
    print()
    print(f"  {'-'*8}" + ("+"+"-"*21) * len(scale_keys))

    max_cycles = max(len(results[s]['interventions']) for s in scale_keys)
    intervention_matches = 0
    intervention_total = 0

    for c in range(max_cycles):
        row = f"  {'C'+str(c):<8}"
        cycle_interventions = []
        for s in scale_keys:
            ivs = results[s]['interventions']
            iv = ivs[c] if c < len(ivs) else "---"
            cycle_interventions.append(iv)
            row += f"| {iv:<21}"
        print(row)

        # Check if same intervention at all scales
        valid = [iv for iv in cycle_interventions if iv != "---" and iv != "none"]
        if len(valid) >= 2:
            intervention_total += 1
            if len(set(valid)) == 1:
                intervention_matches += 1

    consistency = intervention_matches / max(intervention_total, 1) * 100
    print(f"\n  Intervention consistency: {intervention_matches}/{intervention_total} = {consistency:.0f}%")

    # ── Table 3: Phi scaling analysis ──
    print(f"\n  Table 3: Phi Scaling vs Cell Count")
    print(f"  {'Scale':<8} | {'Phi_start':>10} | {'Phi_end':>10} | {'Delta%':>8} | {'Phi/cell':>10}")
    print(f"  {'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*10}")

    phi_data = []
    for s in scale_keys:
        r = results[s]
        phi_per_cell = r['phi_end'] / max(r['n_cells'], 1)
        print(f"  {s:>3}c    | {r['phi_start']:>10.4f} | {r['phi_end']:>10.4f} | {r['phi_delta_pct']:>+7.1f}% | {phi_per_cell:>10.6f}")
        phi_data.append((s, r['phi_end']))

    # Check linearity: Phi vs N
    if len(phi_data) >= 3:
        cells = np.array([d[0] for d in phi_data], dtype=float)
        phis = np.array([d[1] for d in phi_data], dtype=float)
        if np.std(cells) > 0 and np.std(phis) > 0:
            r_corr = float(np.corrcoef(cells, phis)[0, 1])
            # Also check log-linear
            r_log = float(np.corrcoef(np.log(cells), phis)[0, 1])
            print(f"\n  Phi-vs-N correlation:     r = {r_corr:.4f} (linear)")
            print(f"  Phi-vs-log(N) correlation: r = {r_log:.4f} (log-linear)")
            if abs(r_corr) > abs(r_log):
                print(f"  --> Phi scales LINEARLY with cell count")
            else:
                print(f"  --> Phi scales LOG-LINEARLY with cell count")
        else:
            r_corr, r_log = 0, 0
    else:
        r_corr, r_log = 0, 0

    # ── Table 4: Final law values ──
    print(f"\n  Table 4: Final Law Values at Each Scale")
    header = f"  {'Law':<18}"
    for s in scale_keys:
        header += f"| {s:>3}c value  "
    print(header)
    print(f"  {'-'*18}" + ("+"+"-"*12) * len(scale_keys))

    for law_name in LAW_NAMES:
        row = f"  {law_name:<18}"
        for s in scale_keys:
            val = results[s]['final_laws'].get(law_name, 0.0)
            row += f"| {val:>10.4f} "
        print(row)

    # ── Summary ──
    print(f"\n  {'='*60}")
    print(f"  SUMMARY")
    print(f"  {'='*60}")
    print(f"  SCALE-INVARIANT laws ({len(invariant_laws)}): {invariant_laws}")
    print(f"  SCALE-DEPENDENT laws ({len(dependent_laws)}): {dependent_laws}")
    print(f"  Intervention consistency: {consistency:.0f}%")
    if abs(r_corr) > 0:
        print(f"  Phi scaling: r(linear)={r_corr:.3f}, r(log)={r_log:.3f}")
    sys.stdout.flush()

    return {
        'invariant_laws': invariant_laws,
        'dependent_laws': dependent_laws,
        'intervention_consistency_pct': consistency,
        'phi_r_linear': float(r_corr),
        'phi_r_log': float(r_log),
    }


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

def main():
    print(f"\n{'#'*60}")
    print(f"  MULTI-SCALE CLOSED-LOOP VERIFIER")
    print(f"  Scales: {SCALES}")
    print(f"  Cycles: {CYCLES_PER_SCALE} per scale | Steps: {STEPS} | Repeats: {REPEATS}")
    print(f"{'#'*60}")
    sys.stdout.flush()

    total_t0 = time.time()
    all_results = {}

    for n_cells in SCALES:
        result = run_scale(n_cells)
        all_results[n_cells] = result

    # Cross-scale analysis
    analysis = cross_scale_analysis(all_results)

    total_elapsed = time.time() - total_t0

    # Final report
    print(f"\n{'#'*60}")
    print(f"  FINAL REPORT")
    print(f"  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    print(f"{'#'*60}")

    for s in SCALES:
        r = all_results[s]
        bar_len = max(1, int(r['phi_end'] / max(max(all_results[sc]['phi_end'] for sc in SCALES), 1e-8) * 30))
        bar = "#" * bar_len
        print(f"  {s:>3}c: {bar} Phi={r['phi_end']:.4f} ({r['phi_delta_pct']:+.1f}%) [{r['elapsed']:.0f}s]")

    print(f"\n  Scale-invariant: {analysis['invariant_laws']}")
    print(f"  Scale-dependent: {analysis['dependent_laws']}")
    print()
    sys.stdout.flush()

    # Save results
    save_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'data', 'multi_scale_closed_loop_results.json'
    )
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    save_data = {
        'config': {
            'scales': SCALES,
            'cycles': CYCLES_PER_SCALE,
            'steps': STEPS,
            'repeats': REPEATS,
        },
        'results': {},
        'analysis': analysis,
        'total_elapsed': total_elapsed,
    }
    for s, r in all_results.items():
        save_data['results'][str(s)] = {
            'n_cells': r['n_cells'],
            'phi_start': r['phi_start'],
            'phi_end': r['phi_end'],
            'phi_delta_pct': r['phi_delta_pct'],
            'net_change': r['net_change'],
            'interventions': r['interventions'],
            'final_laws': r['final_laws'],
            'elapsed': r['elapsed'],
        }

    with open(save_path, 'w') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {save_path}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
