#!/usr/bin/env python3
"""auto_discovery_20cycles.py — 20-cycle closed-loop auto-discovery pipeline.

Runs ClosedLoopEvolver with optimal parameters (from meta-evolution D):
  max_cells=32, steps=50, repeats=1, auto_register=False

Tracks: Phi trajectory, intervention usage, law change frequency, convergence.
Identifies NEW law candidates from consistent cross-cycle patterns.

Usage:
  cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/auto_discovery_20cycles.py
"""

import sys
import os
import time
import json
import numpy as np
from collections import defaultdict, Counter

# Path setup
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_dir)

from closed_loop import ClosedLoopEvolver, INTERVENTIONS

# ══════════════════════════════════════════
# Config
# ══════════════════════════════════════════
N_CYCLES = 20
MAX_CELLS = 32
STEPS = 50       # optimal from meta-evolution D
REPEATS = 1      # optimal from meta-evolution D
AUTO_REGISTER = False  # review before registering

# ══════════════════════════════════════════
# Tracking structures
# ══════════════════════════════════════════
phi_trajectory = []
intervention_usage = Counter()
law_change_tracker = defaultdict(list)  # law_name -> [(cycle, before, after, change_pct)]
cycle_summaries = []
all_interventions_used = set()
cumulative_law_changes = 0


def print_header():
    print(f"\n{'=' * 78}")
    print(f"  CLOSED-LOOP AUTO-DISCOVERY — 20 CYCLES")
    print(f"  params: max_cells={MAX_CELLS}, steps={STEPS}, repeats={REPEATS}")
    print(f"  interventions available: {len(INTERVENTIONS)}")
    print(f"{'=' * 78}")
    print(f"\n  {'Cycle':<6} {'Phi':>8} {'dPhi%':>8} {'Intervention':<28} {'#Changed':>8} {'Top 3 changes'}")
    print(f"  {'─' * 6} {'─' * 8} {'─' * 8} {'─' * 28} {'─' * 8} {'─' * 40}")
    sys.stdout.flush()


def print_cycle_row(cycle_num, report, elapsed):
    phi = report.phi_improved
    dphi = report.phi_delta_pct
    intervention = report.intervention_applied
    n_changed = len(report.laws_changed)

    # Top 3 biggest changes
    sorted_changes = sorted(report.laws_changed, key=lambda x: abs(x['change_pct']), reverse=True)
    top3 = ", ".join(f"{c['name']}({c['change_pct']:+.0f}%)" for c in sorted_changes[:3])
    if not top3:
        top3 = "(none)"

    print(f"  {cycle_num:<6} {phi:>8.4f} {dphi:>+7.1f}% {intervention:<28} {n_changed:>8} {top3}")
    sys.stdout.flush()


def print_phi_ascii_graph(phis):
    """ASCII graph of Phi evolution (20 points)."""
    print(f"\n{'─' * 78}")
    print(f"  PHI EVOLUTION ({len(phis)} cycles)")
    print(f"{'─' * 78}")

    if not phis:
        print("  (no data)")
        return

    min_phi = min(phis)
    max_phi = max(phis)
    rng = max_phi - min_phi if max_phi > min_phi else 1.0
    height = 12

    # Build graph rows (top to bottom)
    graph = []
    for row in range(height, -1, -1):
        threshold = min_phi + (rng * row / height)
        line = f"  {threshold:>7.4f} |"
        for i, phi in enumerate(phis):
            level = int((phi - min_phi) / rng * height) if rng > 1e-8 else height // 2
            if level == row:
                line += "*"
            elif level > row:
                line += "|" if i > 0 and int((phis[i-1] - min_phi) / rng * height) >= row else " "
            else:
                line += " "
        graph.append(line)

    for line in graph:
        print(line)
    print(f"          +{'─' * len(phis)}")
    # Cycle labels
    labels = "          "
    for i in range(len(phis)):
        if i % 5 == 0:
            labels += str(i)
        elif i % 5 == 1 and i > 1:
            labels += " "
        else:
            labels += " "
    print(labels)
    print(f"           cycle ->")
    sys.stdout.flush()


def print_intervention_table():
    """Print intervention usage frequency table."""
    print(f"\n{'─' * 78}")
    print(f"  INTERVENTION USAGE FREQUENCY")
    print(f"{'─' * 78}")
    print(f"  {'Intervention':<30} {'Times':>6} {'Bar'}")
    print(f"  {'─' * 30} {'─' * 6} {'─' * 30}")

    max_count = max(intervention_usage.values()) if intervention_usage else 1
    for name, count in intervention_usage.most_common():
        bar = "#" * max(1, int(count / max(max_count, 1) * 25))
        print(f"  {name:<30} {count:>6} {bar}")

    # Also show unused interventions
    used = set(intervention_usage.keys())
    unused = [iv.name for iv in INTERVENTIONS if iv.name not in used]
    if unused:
        print(f"\n  Unused ({len(unused)}): {', '.join(unused[:10])}")
        if len(unused) > 10:
            print(f"         + {len(unused) - 10} more")

    print(f"\n  Total unique interventions used: {len(all_interventions_used)}/{len(INTERVENTIONS)}")
    sys.stdout.flush()


def print_law_change_table():
    """Print which of the 20 laws changed most across all cycles."""
    print(f"\n{'─' * 78}")
    print(f"  LAW CHANGE FREQUENCY (across {N_CYCLES} cycles)")
    print(f"{'─' * 78}")
    print(f"  {'Law':<25} {'#Cycles':>8} {'Avg |Change%|':>14} {'Direction':<12} {'Range'}")
    print(f"  {'─' * 25} {'─' * 8} {'─' * 14} {'─' * 12} {'─' * 20}")

    sorted_laws = sorted(law_change_tracker.items(),
                         key=lambda x: len(x[1]), reverse=True)

    for law_name, changes in sorted_laws:
        n_cycles = len(changes)
        avg_abs_change = np.mean([abs(c[3]) for c in changes])
        # Direction consistency: positive vs negative
        pos = sum(1 for c in changes if c[3] > 0)
        neg = sum(1 for c in changes if c[3] < 0)
        if pos > neg:
            direction = f"UP ({pos}/{n_cycles})"
        elif neg > pos:
            direction = f"DOWN ({neg}/{n_cycles})"
        else:
            direction = f"MIXED"
        values = [c[2] for c in changes]  # 'after' values
        val_range = f"{min(values):.4f}~{max(values):.4f}"
        print(f"  {law_name:<25} {n_cycles:>8} {avg_abs_change:>13.1f}% {direction:<12} {val_range}")

    sys.stdout.flush()


def print_convergence_analysis():
    """Did changes diminish over time?"""
    print(f"\n{'─' * 78}")
    print(f"  CONVERGENCE ANALYSIS")
    print(f"{'─' * 78}")

    if len(cycle_summaries) < 4:
        print("  Not enough data for convergence analysis.")
        return

    # Split into quarters
    q_size = len(cycle_summaries) // 4
    quarters = []
    for q in range(4):
        start = q * q_size
        end = start + q_size if q < 3 else len(cycle_summaries)
        q_data = cycle_summaries[start:end]
        avg_changes = np.mean([s['n_changed'] for s in q_data])
        avg_abs_dphi = np.mean([abs(s['dphi_pct']) for s in q_data])
        avg_phi = np.mean([s['phi'] for s in q_data])
        quarters.append({
            'avg_changes': avg_changes,
            'avg_abs_dphi': avg_abs_dphi,
            'avg_phi': avg_phi,
        })

    print(f"  {'Quarter':<10} {'Avg Law Changes':>16} {'Avg |dPhi%|':>12} {'Avg Phi':>10}")
    print(f"  {'─' * 10} {'─' * 16} {'─' * 12} {'─' * 10}")
    for i, q in enumerate(quarters):
        print(f"  Q{i+1} (c{i*q_size+1}-{min((i+1)*q_size, len(cycle_summaries))})  "
              f"{q['avg_changes']:>14.1f} {q['avg_abs_dphi']:>11.1f}% {q['avg_phi']:>9.4f}")

    # Trend analysis
    q1_changes = quarters[0]['avg_changes']
    q4_changes = quarters[3]['avg_changes']
    if q1_changes > 0:
        change_trend = (q4_changes - q1_changes) / q1_changes * 100
    else:
        change_trend = 0

    phi_trend = quarters[3]['avg_phi'] - quarters[0]['avg_phi']

    print(f"\n  Law change trend Q1->Q4: {change_trend:+.1f}% {'(CONVERGING)' if change_trend < -20 else '(DIVERGING)' if change_trend > 20 else '(STABLE)'}")
    print(f"  Phi trend Q1->Q4: {phi_trend:+.4f} {'(GROWING)' if phi_trend > 0.01 else '(DECLINING)' if phi_trend < -0.01 else '(STABLE)'}")

    # Phi monotonicity
    increases = sum(1 for i in range(1, len(phi_trajectory)) if phi_trajectory[i] > phi_trajectory[i-1])
    decreases = len(phi_trajectory) - 1 - increases
    print(f"  Phi increases: {increases}/{len(phi_trajectory)-1}, decreases: {decreases}/{len(phi_trajectory)-1}")
    sys.stdout.flush()


def identify_law_candidates():
    """Identify NEW law candidates: consistent pattern across 5+ cycles."""
    print(f"\n{'─' * 78}")
    print(f"  NEW LAW CANDIDATES (consistent patterns across 5+ cycles)")
    print(f"{'─' * 78}")

    candidates = []
    for law_name, changes in law_change_tracker.items():
        if len(changes) < 5:
            continue

        change_pcts = [c[3] for c in changes]
        # Check consistency: same direction in 80%+ of appearances
        pos = sum(1 for p in change_pcts if p > 0)
        neg = sum(1 for p in change_pcts if p < 0)
        total = len(change_pcts)
        consistency = max(pos, neg) / total

        if consistency >= 0.7:  # 70% same direction
            direction = "increases" if pos > neg else "decreases"
            avg_change = np.mean(change_pcts)
            std_change = np.std(change_pcts)

            # What interventions were associated?
            associated_interventions = set()
            for c in changes:
                cycle_idx = c[0]
                if cycle_idx < len(cycle_summaries):
                    associated_interventions.add(cycle_summaries[cycle_idx]['intervention'])

            candidates.append({
                'law_name': law_name,
                'appearances': total,
                'consistency': consistency,
                'direction': direction,
                'avg_change': avg_change,
                'std_change': std_change,
                'interventions': list(associated_interventions),
            })

    candidates.sort(key=lambda x: x['appearances'] * x['consistency'], reverse=True)

    if not candidates:
        print("  No consistent law candidates found (need 5+ cycles, 70%+ direction consistency).")
    else:
        print(f"  Found {len(candidates)} candidate(s):\n")
        for i, c in enumerate(candidates, 1):
            print(f"  CANDIDATE {i}: {c['law_name']}")
            print(f"    Pattern: consistently {c['direction']} across {c['appearances']}/{N_CYCLES} cycles")
            print(f"    Consistency: {c['consistency']:.0%} same direction")
            print(f"    Average change: {c['avg_change']:+.1f}% (std: {c['std_change']:.1f}%)")
            print(f"    Associated interventions: {', '.join(c['interventions'])}")

            # Formulate as potential law
            if c['direction'] == 'increases':
                law_text = (f"Closed-loop intervention {c['direction']} {c['law_name']} "
                           f"by avg {abs(c['avg_change']):.1f}% per cycle "
                           f"({c['appearances']}/{N_CYCLES} cycles, {c['consistency']:.0%} consistent)")
            else:
                law_text = (f"Closed-loop intervention {c['direction']} {c['law_name']} "
                           f"by avg {abs(c['avg_change']):.1f}% per cycle "
                           f"({c['appearances']}/{N_CYCLES} cycles, {c['consistency']:.0%} consistent)")
            print(f"    Proposed law: \"{law_text}\"")
            print()

    sys.stdout.flush()
    return candidates


def save_results(candidates, elapsed_total):
    """Save all results to JSON."""
    results = {
        'config': {
            'n_cycles': N_CYCLES,
            'max_cells': MAX_CELLS,
            'steps': STEPS,
            'repeats': REPEATS,
            'auto_register': AUTO_REGISTER,
            'total_interventions_available': len(INTERVENTIONS),
        },
        'phi_trajectory': phi_trajectory,
        'intervention_usage': dict(intervention_usage),
        'unique_interventions_used': len(all_interventions_used),
        'total_law_changes': cumulative_law_changes,
        'cycle_summaries': cycle_summaries,
        'law_candidates': candidates,
        'law_change_tracker': {
            k: [{'cycle': c[0], 'before': c[1], 'after': c[2], 'change_pct': c[3]} for c in v]
            for k, v in law_change_tracker.items()
        },
        'elapsed_seconds': elapsed_total,
    }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(out_dir, 'auto_discovery_20cycles_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to: {out_path}")

    # Also save to data/
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    data_path = os.path.join(data_dir, 'auto_discovery_20cycles.json')
    with open(data_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Results saved to: {data_path}")
    sys.stdout.flush()

    return out_path


def main():
    global cumulative_law_changes

    t_start = time.time()
    print_header()

    evolver = ClosedLoopEvolver(
        max_cells=MAX_CELLS,
        steps=STEPS,
        repeats=REPEATS,
        auto_register=AUTO_REGISTER,
    )

    for cycle in range(N_CYCLES):
        t_cycle = time.time()
        report = evolver.run_cycle()
        elapsed = time.time() - t_cycle

        # Track
        phi_trajectory.append(report.phi_improved)
        intervention_usage[report.intervention_applied] += 1
        all_interventions_used.add(report.intervention_applied)
        cumulative_law_changes += len(report.laws_changed)

        for lc in report.laws_changed:
            law_change_tracker[lc['name']].append(
                (cycle, lc['before'], lc['after'], lc['change_pct'])
            )

        # Sort for top 3
        sorted_changes = sorted(report.laws_changed, key=lambda x: abs(x['change_pct']), reverse=True)
        top3_names = [c['name'] for c in sorted_changes[:3]]

        cycle_summaries.append({
            'cycle': cycle,
            'phi': report.phi_improved,
            'dphi_pct': report.phi_delta_pct,
            'intervention': report.intervention_applied,
            'n_changed': len(report.laws_changed),
            'top3': top3_names,
            'elapsed': elapsed,
        })

        print_cycle_row(cycle, report, elapsed)

        # Progress
        eta = (time.time() - t_start) / (cycle + 1) * (N_CYCLES - cycle - 1)
        print(f"         [{cycle+1}/{N_CYCLES}] cumulative: {len(all_interventions_used)} interventions, "
              f"{cumulative_law_changes} law changes, ETA: {eta:.0f}s")
        sys.stdout.flush()

    total_elapsed = time.time() - t_start

    # ── Analysis ──
    print(f"\n{'=' * 78}")
    print(f"  ANALYSIS COMPLETE — {total_elapsed:.1f}s total")
    print(f"{'=' * 78}")

    # 1. Phi ASCII graph
    print_phi_ascii_graph(phi_trajectory)

    # 2. Intervention usage
    print_intervention_table()

    # 3. Law change frequency
    print_law_change_table()

    # 4. Convergence analysis
    print_convergence_analysis()

    # 5. New law candidates
    candidates = identify_law_candidates()

    # 6. Save results
    save_results(candidates, total_elapsed)

    # Final summary
    print(f"\n{'=' * 78}")
    print(f"  SUMMARY")
    print(f"{'=' * 78}")
    print(f"  Cycles run:              {N_CYCLES}")
    print(f"  Total time:              {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"  Phi range:               {min(phi_trajectory):.4f} ~ {max(phi_trajectory):.4f}")
    print(f"  Phi final:               {phi_trajectory[-1]:.4f}")
    print(f"  Unique interventions:    {len(all_interventions_used)}/{len(INTERVENTIONS)}")
    print(f"  Total law changes:       {cumulative_law_changes}")
    print(f"  Law candidates found:    {len(candidates)}")
    print(f"{'=' * 78}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
