#!/usr/bin/env python3
"""intervention_synergy.py — Test synergy between pairs of interventions.

Measures whether combining two interventions produces super-additive,
additive, or sub-additive effects on Phi and other consciousness metrics.

Synergy = Phi(A+B) - (Phi(A) + Phi(B) - Phi(baseline))
  > 0: SUPER-ADDITIVE (combo better than sum of parts)
  = 0: ADDITIVE (independent effects)
  < 0: SUB-ADDITIVE (interference/antagonism)

Usage:
  cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/intervention_synergy.py
"""

import sys
import os
import time

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from closed_loop import (
    INTERVENTIONS, Intervention, _ImprovedEngine,
    measure_laws, LawMeasurement,
)


# ══════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════

MAX_CELLS = 16
STEPS = 100
REPEATS = 1

# Top 10 pairs (cross-DD category for diversity)
PAIRS = [
    ("DD71_democracy",       "DD73_entropy_bound"),
    ("DD71_diversity",       "DD75_soc_free_will"),
    ("DD72_hebbian_boost",   "DD74_gradient_shield"),
    ("DD72_resurrection",    "DD73_incompressible"),
    ("DD73_entropy_bound",   "DD75_decisive"),
    ("DD74_natural_reg",     "DD72_temporal_comp"),
    ("tension_eq",           "DD73_channel_limit"),
    ("pink_noise",           "DD75_veto"),
    ("symmetrize",           "DD72_hebbian_boost"),
    ("DD71_anti_parasitism", "DD74_gradient_shield"),
]


# ══════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════

def get_intervention(name: str) -> Intervention:
    """Look up intervention by name."""
    for iv in INTERVENTIONS:
        if iv.name == name:
            return iv
    raise ValueError(f"Intervention '{name}' not found")


def make_factory(interventions=None):
    """Create engine factory with given interventions."""
    ivs = interventions or []
    def factory():
        return _ImprovedEngine(
            max_cells=MAX_CELLS,
            initial_cells=2,
            interventions=list(ivs),
        )
    return factory


def phi_from_laws(laws):
    """Extract phi value from law measurements."""
    for l in laws:
        if l.name == 'phi':
            return l.value
    return 0.0


def laws_to_dict(laws):
    """Convert list of LawMeasurement to dict."""
    return {l.name: l.value for l in laws}


# ══════════════════════════════════════════
# Main experiment
# ══════════════════════════════════════════

def run_synergy_experiment():
    t_total = time.time()

    print(f"\n{'=' * 80}")
    print(f"  Intervention Synergy Experiment")
    print(f"  {len(PAIRS)} pairs, {MAX_CELLS} cells, {STEPS} steps, {REPEATS} repeat(s)")
    print(f"{'=' * 80}")

    # Step 1: Measure baseline (no interventions)
    print(f"\n  [0/{len(PAIRS) + 1}] Measuring baseline (no interventions)...")
    sys.stdout.flush()
    t0 = time.time()
    base_laws, phi_base = measure_laws(make_factory(), steps=STEPS, repeats=REPEATS)
    base_dict = laws_to_dict(base_laws)
    print(f"         Phi_base = {phi_base:.4f}  ({time.time() - t0:.1f}s)")
    sys.stdout.flush()

    # Step 2: For each pair, measure A alone, B alone, A+B combo
    results = []

    for idx, (name_a, name_b) in enumerate(PAIRS):
        print(f"\n  [{idx + 1}/{len(PAIRS)}] {name_a} + {name_b}")
        sys.stdout.flush()
        t_pair = time.time()

        iv_a = get_intervention(name_a)
        iv_b = get_intervention(name_b)

        # Single A
        laws_a, phi_a = measure_laws(make_factory([iv_a]), steps=STEPS, repeats=REPEATS)
        print(f"         Phi_A = {phi_a:.4f}", end="")
        sys.stdout.flush()

        # Single B
        laws_b, phi_b = measure_laws(make_factory([iv_b]), steps=STEPS, repeats=REPEATS)
        print(f"  Phi_B = {phi_b:.4f}", end="")
        sys.stdout.flush()

        # Combo A+B
        laws_ab, phi_ab = measure_laws(make_factory([iv_a, iv_b]), steps=STEPS, repeats=REPEATS)
        print(f"  Phi_AB = {phi_ab:.4f}", end="")
        sys.stdout.flush()

        # Synergy calculation
        # Expected additive: Phi(A) + Phi(B) - Phi(base)
        phi_expected = phi_a + phi_b - phi_base
        synergy = phi_ab - phi_expected

        # Classify
        if synergy > 0.01:
            syn_type = "SUPER-ADD"
        elif synergy < -0.01:
            syn_type = "SUB-ADD"
        else:
            syn_type = "ADDITIVE"

        elapsed = time.time() - t_pair
        print(f"  Synergy = {synergy:+.4f} [{syn_type}]  ({elapsed:.1f}s)")
        sys.stdout.flush()

        # Also compute synergy for other key metrics
        dict_a = laws_to_dict(laws_a)
        dict_b = laws_to_dict(laws_b)
        dict_ab = laws_to_dict(laws_ab)

        metric_synergies = {}
        for metric in ['shannon_entropy', 'mutual_info', 'growth', 'consensus',
                        'hidden_diversity', 'faction_entropy', 'output_divergence']:
            v_base = base_dict.get(metric, 0)
            v_a = dict_a.get(metric, 0)
            v_b = dict_b.get(metric, 0)
            v_ab = dict_ab.get(metric, 0)
            expected = v_a + v_b - v_base
            metric_synergies[metric] = v_ab - expected

        results.append({
            'pair': f"{name_a} + {name_b}",
            'name_a': name_a,
            'name_b': name_b,
            'phi_base': phi_base,
            'phi_a': phi_a,
            'phi_b': phi_b,
            'phi_ab': phi_ab,
            'phi_expected': phi_expected,
            'synergy': synergy,
            'type': syn_type,
            'metric_synergies': metric_synergies,
        })

    # ══════════════════════════════════════════
    # Results table
    # ══════════════════════════════════════════

    print(f"\n\n{'=' * 100}")
    print(f"  SYNERGY RESULTS")
    print(f"{'=' * 100}")
    print(f"  Baseline Phi = {phi_base:.4f}")
    print()

    # Main Phi synergy table
    header = f"  {'#':<3} {'Pair':<50} {'Phi_A':>7} {'Phi_B':>7} {'Phi_AB':>7} {'Synergy':>9} {'Type':<10}"
    print(header)
    print(f"  {'─' * 3} {'─' * 50} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 9} {'─' * 10}")

    for i, r in enumerate(results):
        pair_str = f"{r['name_a']} + {r['name_b']}"
        print(f"  {i + 1:<3} {pair_str:<50} {r['phi_a']:7.4f} {r['phi_b']:7.4f} "
              f"{r['phi_ab']:7.4f} {r['synergy']:+9.4f} {r['type']:<10}")

    # Sort by synergy
    sorted_results = sorted(results, key=lambda x: x['synergy'], reverse=True)

    print(f"\n  ── Ranked by Synergy (best first) ──")
    print(f"  {'#':<3} {'Pair':<50} {'Synergy':>9} {'Type':<10}")
    print(f"  {'─' * 3} {'─' * 50} {'─' * 9} {'─' * 10}")
    for i, r in enumerate(sorted_results):
        pair_str = f"{r['name_a']} + {r['name_b']}"
        marker = " ***" if i == 0 else (" !!!" if r['synergy'] == min(x['synergy'] for x in results) else "")
        print(f"  {i + 1:<3} {pair_str:<50} {r['synergy']:+9.4f} {r['type']:<10}{marker}")

    # ASCII synergy bar chart
    print(f"\n  ── Synergy Bar Chart ──")
    max_abs = max(abs(r['synergy']) for r in sorted_results) if sorted_results else 1.0
    if max_abs < 1e-8:
        max_abs = 1.0
    for r in sorted_results:
        pair_short = f"{r['name_a'].split('_')[-1]}+{r['name_b'].split('_')[-1]}"
        bar_len = int(abs(r['synergy']) / max_abs * 30)
        if r['synergy'] > 0:
            bar = " " * 30 + "|" + "+" * bar_len
        else:
            bar = " " * (30 - bar_len) + "-" * bar_len + "|"
        print(f"  {pair_short:>25} {bar} {r['synergy']:+.4f}")

    # Multi-metric synergy for top pair
    best = sorted_results[0]
    worst = sorted_results[-1]

    print(f"\n  ── Best Synergistic Pair ──")
    print(f"  {best['name_a']} + {best['name_b']}")
    print(f"  Phi synergy: {best['synergy']:+.4f} ({best['type']})")
    print(f"  Multi-metric synergies:")
    for metric, val in best['metric_synergies'].items():
        direction = "+" if val > 0 else ""
        print(f"    {metric:<22} {direction}{val:.4f}")

    print(f"\n  ── Most Antagonistic Pair ──")
    print(f"  {worst['name_a']} + {worst['name_b']}")
    print(f"  Phi synergy: {worst['synergy']:+.4f} ({worst['type']})")
    print(f"  Multi-metric synergies:")
    for metric, val in worst['metric_synergies'].items():
        direction = "+" if val > 0 else ""
        print(f"    {metric:<22} {direction}{val:.4f}")

    # Summary statistics
    super_add = sum(1 for r in results if r['type'] == 'SUPER-ADD')
    sub_add = sum(1 for r in results if r['type'] == 'SUB-ADD')
    additive = sum(1 for r in results if r['type'] == 'ADDITIVE')
    avg_synergy = np.mean([r['synergy'] for r in results])

    print(f"\n  ── Summary ──")
    print(f"  SUPER-ADDITIVE:  {super_add}/{len(results)}")
    print(f"  ADDITIVE:        {additive}/{len(results)}")
    print(f"  SUB-ADDITIVE:    {sub_add}/{len(results)}")
    print(f"  Avg synergy:     {avg_synergy:+.4f}")
    print(f"  Total time:      {time.time() - t_total:.1f}s")
    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    run_synergy_experiment()
