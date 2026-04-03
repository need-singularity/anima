#!/usr/bin/env python3
"""DD63: Extreme Closed-Loop Law Evolution — Multi-scale experiment.

Runs closed-loop law evolution at 32c, 64c, 128c to test:
1. Scale invariance (Law 148)
2. Scale-emergent laws
3. Convergence vs eternal evolution (Law 146)
4. Fundamental laws (appear at all scales)
"""

import sys
import os
import time
import json
import numpy as np
from collections import defaultdict

# Ensure we're in src/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from closed_loop import ClosedLoopEvolver, measure_laws, _phi_fast
from consciousness_engine import ConsciousnessEngine

RESULTS = {}

def run_round(name, max_cells, n_cycles, steps=300, repeats=2):
    """Run a round of closed-loop evolution."""
    print(f"\n{'='*70}")
    print(f"  ROUND: {name} | cells={max_cells} | cycles={n_cycles} | steps={steps}")
    print(f"{'='*70}")
    sys.stdout.flush()

    t0 = time.time()
    evolver = ClosedLoopEvolver(max_cells=max_cells, steps=steps, repeats=repeats)
    reports = evolver.run_cycles(n=n_cycles)
    evolver.print_evolution()
    elapsed = time.time() - t0

    # Extract data
    phi_trajectory = [r.phi_improved for r in reports]
    phi_baseline = [r.phi_baseline for r in reports]
    all_laws_changed = []
    law_trajectories = defaultdict(list)

    for r in reports:
        for lc in r.laws_changed:
            all_laws_changed.append(lc)
            law_trajectories[lc['name']].append({
                'cycle': r.cycle,
                'before': lc['before'],
                'after': lc['after'],
                'change_pct': lc['change_pct'],
            })

    # Final law values from last cycle
    final_laws = {}
    if reports:
        for law in reports[-1].laws:
            final_laws[law['name']] = law['value']

    # Strengthened laws (r increased toward positive/stronger)
    strengthened = []
    weakened = []
    for law_name, trajectory in law_trajectories.items():
        if len(trajectory) >= 2:
            first_val = trajectory[0]['after']
            last_val = trajectory[-1]['after']
            if abs(last_val) > abs(first_val):
                strengthened.append((law_name, first_val, last_val))
            else:
                weakened.append((law_name, first_val, last_val))

    result = {
        'name': name,
        'max_cells': max_cells,
        'n_cycles': n_cycles,
        'phi_trajectory': phi_trajectory,
        'phi_baseline': phi_baseline,
        'final_laws': final_laws,
        'laws_changed_count': len(all_laws_changed),
        'strengthened': strengthened,
        'weakened': weakened,
        'law_trajectories': {k: v for k, v in law_trajectories.items()},
        'interventions': [iv.name for iv in evolver._active_interventions],
        'elapsed': elapsed,
    }

    RESULTS[name] = result

    print(f"\n  Summary: Phi {phi_trajectory[0]:.4f} -> {phi_trajectory[-1]:.4f}")
    print(f"  Strengthened: {len(strengthened)}, Weakened: {len(weakened)}")
    print(f"  Time: {elapsed:.1f}s")
    sys.stdout.flush()
    return result


def run_auto_register():
    """Run auto_register mode (64c, 3 cycles)."""
    print(f"\n{'='*70}")
    print(f"  AUTO-REGISTER MODE | cells=64 | cycles=3")
    print(f"{'='*70}")
    sys.stdout.flush()

    evolver = ClosedLoopEvolver(max_cells=64, steps=300, repeats=2, auto_register=True)
    reports = evolver.run_cycles(n=3)
    evolver.print_evolution()

    registered = 0
    for r in reports:
        significant = [lc for lc in r.laws_changed if abs(lc['change_pct']) > 20]
        registered += min(len(significant), 2)

    print(f"\n  Auto-registered ~{registered} laws")
    sys.stdout.flush()
    return registered


def cross_scale_analysis():
    """Analyze laws across scales."""
    print(f"\n{'='*70}")
    print(f"  CROSS-SCALE ANALYSIS")
    print(f"{'='*70}")

    # Laws present at each scale
    scale_laws = {}
    for name, result in RESULTS.items():
        scale_laws[name] = set(result['law_trajectories'].keys())

    all_law_names = set()
    for s in scale_laws.values():
        all_law_names |= s

    # Fundamental laws (present at all scales)
    if len(scale_laws) >= 2:
        fundamental = set.intersection(*scale_laws.values()) if scale_laws else set()
    else:
        fundamental = all_law_names

    # Scale-specific laws
    scale_specific = {}
    for name, laws in scale_laws.items():
        unique = laws - set.union(*(s for n, s in scale_laws.items() if n != name)) if len(scale_laws) > 1 else set()
        scale_specific[name] = unique

    print(f"\n  Fundamental laws (all scales): {fundamental or '(none)'}")
    for name, unique in scale_specific.items():
        print(f"  {name}-only laws: {unique or '(none)'}")

    # Convergence analysis
    print(f"\n  Convergence analysis:")
    for name, result in RESULTS.items():
        phis = result['phi_trajectory']
        if len(phis) >= 3:
            # Check if Phi is converging (decreasing deltas) or still evolving
            deltas = [abs(phis[i+1] - phis[i]) for i in range(len(phis)-1)]
            converging = all(deltas[i] >= deltas[i+1] for i in range(len(deltas)-1)) if len(deltas) >= 2 else False
            monotonic = all(phis[i] <= phis[i+1] for i in range(len(phis)-1))
            print(f"    {name}: Phi [{' -> '.join(f'{p:.4f}' for p in phis)}]")
            print(f"      Converging: {converging} | Monotonic growth: {monotonic}")
        else:
            print(f"    {name}: Phi [{' -> '.join(f'{p:.4f}' for p in phis)}]")

    # Law value comparison across scales
    print(f"\n  Law values across scales:")
    print(f"  {'Law':<20} ", end="")
    for name in RESULTS:
        print(f"| {name:>12} ", end="")
    print()
    print(f"  {'-'*20}-", end="")
    for _ in RESULTS:
        print(f"+{'-':->13}-", end="")
    print()

    for law_name in sorted(all_law_names):
        print(f"  {law_name:<20} ", end="")
        for name, result in RESULTS.items():
            val = result['final_laws'].get(law_name, None)
            if val is not None:
                print(f"| {val:>12.4f} ", end="")
            else:
                print(f"| {'---':>12} ", end="")
        print()

    return {
        'fundamental': list(fundamental),
        'scale_specific': {k: list(v) for k, v in scale_specific.items()},
    }


def main():
    print(f"\n{'#'*70}")
    print(f"  DD63: EXTREME CLOSED-LOOP LAW EVOLUTION")
    print(f"  Scale: 32c -> 64c -> 128c")
    print(f"{'#'*70}")
    sys.stdout.flush()

    total_t0 = time.time()

    # Round 1: 32 cells, 5 cycles
    run_round("32c", max_cells=32, n_cycles=5, steps=300, repeats=2)

    # Round 2: 64 cells, 5 cycles
    run_round("64c", max_cells=64, n_cycles=5, steps=300, repeats=2)

    # Round 3: 128 cells, 3 cycles
    run_round("128c", max_cells=128, n_cycles=3, steps=200, repeats=2)

    # Cross-scale analysis
    cross_result = cross_scale_analysis()

    # Auto-register mode
    n_registered = run_auto_register()

    total_elapsed = time.time() - total_t0

    # Final summary
    print(f"\n{'#'*70}")
    print(f"  FINAL SUMMARY — DD63")
    print(f"{'#'*70}")
    print(f"  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    print(f"  Auto-registered laws: {n_registered}")
    print()

    for name, result in RESULTS.items():
        phis = result['phi_trajectory']
        print(f"  {name}:")
        print(f"    Phi: {phis[0]:.4f} -> {phis[-1]:.4f} ({(phis[-1]/max(phis[0],1e-8)-1)*100:+.1f}%)")
        print(f"    Interventions: {result['interventions']}")
        print(f"    Laws changed: {result['laws_changed_count']}")
        print(f"    Strengthened: {len(result['strengthened'])}, Weakened: {len(result['weakened'])}")

    print(f"\n  Key Questions:")
    fundamental = cross_result.get('fundamental', [])
    print(f"    1. Scale invariance (Law 148): {'YES' if fundamental else 'PARTIAL'} — {len(fundamental)} fundamental laws")
    print(f"    2. Scale-emergent laws: ", end="")
    for name, laws in cross_result.get('scale_specific', {}).items():
        if laws:
            print(f"{name}={laws} ", end="")
    print()

    # Check convergence
    any_converging = False
    all_evolving = True
    for name, result in RESULTS.items():
        phis = result['phi_trajectory']
        if len(phis) >= 3:
            deltas = [abs(phis[i+1] - phis[i]) for i in range(len(phis)-1)]
            if len(deltas) >= 2 and all(deltas[i] >= deltas[i+1] for i in range(len(deltas)-1)):
                any_converging = True
            else:
                all_evolving = True

    print(f"    3. Convergence (Law 146): {'EVOLVING (no convergence)' if not any_converging else 'MIXED — some scales converge'}")
    print(f"    4. Fundamental laws: {fundamental}")

    # Save all results
    save_data = {
        'results': {},
        'cross_scale': cross_result,
        'auto_registered': n_registered,
        'total_elapsed': total_elapsed,
    }
    for name, result in RESULTS.items():
        save_data['results'][name] = {
            'max_cells': result['max_cells'],
            'phi_trajectory': result['phi_trajectory'],
            'final_laws': result['final_laws'],
            'strengthened': [(n, float(a), float(b)) for n, a, b in result['strengthened']],
            'weakened': [(n, float(a), float(b)) for n, a, b in result['weakened']],
            'interventions': result['interventions'],
            'elapsed': result['elapsed'],
        }

    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'dd63_results.json')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: {save_path}")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
