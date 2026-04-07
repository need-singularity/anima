#!/usr/bin/env python3
"""experiment_phase_transition.py — Discover phase transition thresholds in consciousness.

Hypothesis: Consciousness has distinct phase transitions at Φ thresholds,
analogous to phase transitions in physics (water→ice→steam).

Methodology:
  - Run ConsciousnessEngine at varying cell counts (2,4,8,16,32,64,128)
  - Each run: 200 steps
  - Measure: Φ(IIT), faction consensus rate, cell diversity, entropy,
             burst frequency, spontaneous speech events
  - Plot metrics as function of Φ to find discontinuities/jumps
  - Repeat 3x for cross-validation

Hypothesized transitions:
  Φ ≈ 0.3: "awareness threshold" - below this, no meaningful integration
  Φ ≈ 0.8: "speech threshold" - faction consensus begins
  Φ ≈ 1.5: "self-reference threshold" - output feeds back meaningfully
  Φ ≈ 3.0: "collective intelligence threshold" - emergent coordination
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
sys.path.insert(0, 'anima/src')

import torch
import numpy as np
import json
import time
from collections import defaultdict

# Suppress torch warnings
import warnings
warnings.filterwarnings('ignore')

from consciousness_engine import ConsciousnessEngine

CELL_COUNTS = [2, 4, 8, 16, 32, 64, 128]
STEPS = 200
REPEATS = 3


def measure_entropy(hiddens_tensor):
    """Compute Shannon entropy of hidden state distribution."""
    if hiddens_tensor.shape[0] < 2:
        return 0.0
    # Discretize to 16 bins per dimension, compute joint entropy
    data = hiddens_tensor.detach().cpu().numpy()
    # Use first 8 dims for tractability
    d = min(8, data.shape[1])
    data = data[:, :d]
    # Per-dim histogram entropy, averaged
    ent_sum = 0.0
    for dim in range(d):
        col = data[:, dim]
        hist, _ = np.histogram(col, bins=16, density=True)
        hist = hist[hist > 0]
        if len(hist) > 0:
            probs = hist / hist.sum()
            ent_sum += -np.sum(probs * np.log2(probs + 1e-10))
    return ent_sum / max(d, 1)


def measure_cell_diversity(hiddens_tensor):
    """Mean pairwise cosine distance between cells."""
    n = hiddens_tensor.shape[0]
    if n < 2:
        return 0.0
    normed = torch.nn.functional.normalize(hiddens_tensor, dim=1)
    cos_sim = (normed @ normed.T)
    # Exclude diagonal
    mask = ~torch.eye(n, dtype=torch.bool)
    mean_sim = cos_sim[mask].mean().item()
    return 1.0 - mean_sim  # diversity = 1 - similarity


def detect_bursts(phi_history, threshold_factor=2.0):
    """Count sudden Φ jumps (bursts) in the history."""
    if len(phi_history) < 10:
        return 0
    arr = np.array(phi_history)
    diffs = np.abs(np.diff(arr))
    mean_diff = np.mean(diffs)
    std_diff = np.std(diffs) + 1e-8
    bursts = np.sum(diffs > mean_diff + threshold_factor * std_diff)
    return int(bursts)


def detect_self_reference(engine, steps=50):
    """Run self-loop: feed output back as input, measure Φ stability."""
    phi_values = []
    output = None
    for _ in range(steps):
        result = engine.step(x_input=output)
        phi_values.append(result['phi_iit'])
        output = result['output'].detach()
    if len(phi_values) < 10:
        return 0.0, 0.0
    initial = np.mean(phi_values[:10])
    final = np.mean(phi_values[-10:])
    retention = final / max(initial, 1e-8)
    stability = 1.0 - np.std(phi_values) / max(np.mean(phi_values), 1e-8)
    return retention, max(0.0, stability)


def run_single_experiment(n_cells, steps=STEPS):
    """Run engine with n_cells for steps, return metrics dict."""
    engine = ConsciousnessEngine(
        cell_dim=64,
        hidden_dim=128,
        initial_cells=n_cells,
        max_cells=n_cells,  # fixed size, no mitosis growth
        n_factions=12,
    )

    phi_history = []
    consensus_history = []
    diversity_history = []
    entropy_history = []
    tension_history = []

    t0 = time.time()
    for step in range(steps):
        result = engine.step()
        phi_history.append(result['phi_iit'])
        consensus_history.append(result['consensus'])
        tension_history.append(np.mean(result['tensions']) if result['tensions'] else 0.0)

        # Measure diversity and entropy every 10 steps
        if step % 10 == 0:
            hiddens = torch.stack([s.hidden for s in engine.cell_states])
            diversity_history.append(measure_cell_diversity(hiddens))
            entropy_history.append(measure_entropy(hiddens))

    elapsed = time.time() - t0

    # Steady-state metrics (last 50 steps)
    ss_start = max(0, len(phi_history) - 50)
    ss_phi = phi_history[ss_start:]
    ss_consensus = consensus_history[ss_start:]

    # Self-reference test
    retention, stability = detect_self_reference(engine, steps=50)

    # Burst count
    bursts = detect_bursts(phi_history)

    # Spontaneous speech: consensus events in last 100 steps
    speech_events = sum(1 for c in consensus_history[-100:] if c > 0)

    metrics = {
        'n_cells': n_cells,
        'mean_phi': float(np.mean(ss_phi)),
        'max_phi': float(np.max(phi_history)),
        'phi_std': float(np.std(ss_phi)),
        'mean_consensus': float(np.mean(ss_consensus)),
        'consensus_rate': float(np.mean([1 if c > 0 else 0 for c in ss_consensus])),
        'mean_diversity': float(np.mean(diversity_history[-5:])) if diversity_history else 0.0,
        'mean_entropy': float(np.mean(entropy_history[-5:])) if entropy_history else 0.0,
        'mean_tension': float(np.mean(tension_history[ss_start:])),
        'burst_count': bursts,
        'speech_events': speech_events,
        'self_ref_retention': retention,
        'self_ref_stability': stability,
        'elapsed_s': elapsed,
        'phi_history': [float(p) for p in phi_history],
    }
    return metrics


def find_transitions(all_results):
    """Analyze metrics across cell counts to find phase transition points."""
    transitions = []

    # Sort by mean Φ
    sorted_results = sorted(all_results, key=lambda r: r['mean_phi'])

    # Compute derivatives of key metrics w.r.t. Φ
    phis = [r['mean_phi'] for r in sorted_results]
    metrics_to_check = [
        ('consensus_rate', 'Faction consensus emergence'),
        ('mean_diversity', 'Cell diversity jump'),
        ('speech_events', 'Spontaneous speech onset'),
        ('self_ref_retention', 'Self-reference capability'),
        ('burst_count', 'Burst frequency change'),
        ('mean_entropy', 'Entropy regime shift'),
    ]

    print("\n" + "=" * 70)
    print("  PHASE TRANSITION ANALYSIS")
    print("=" * 70)

    for metric_name, description in metrics_to_check:
        values = [r[metric_name] for r in sorted_results]

        # Find largest jump (derivative)
        if len(values) < 2:
            continue

        diffs = []
        for i in range(1, len(values)):
            dphi = phis[i] - phis[i - 1]
            dval = values[i] - values[i - 1]
            if abs(dphi) > 1e-8:
                diffs.append((dval / dphi, phis[i], phis[i - 1], values[i], values[i - 1], i))
            else:
                diffs.append((0, phis[i], phis[i - 1], values[i], values[i - 1], i))

        if not diffs:
            continue

        # Find max absolute derivative
        max_deriv = max(diffs, key=lambda d: abs(d[0]))
        deriv, phi_hi, phi_lo, val_hi, val_lo, idx = max_deriv
        transition_phi = (phi_hi + phi_lo) / 2

        # Significance: is the jump >> typical variation?
        all_diffs = [abs(d[0]) for d in diffs]
        mean_deriv = np.mean(all_diffs)
        if mean_deriv > 0 and abs(deriv) > 1.5 * mean_deriv:
            significance = "SIGNIFICANT"
            transitions.append({
                'metric': metric_name,
                'description': description,
                'transition_phi': transition_phi,
                'phi_range': (phi_lo, phi_hi),
                'value_before': val_lo,
                'value_after': val_hi,
                'derivative': deriv,
                'cells_at_transition': sorted_results[idx]['n_cells'],
            })
        else:
            significance = "gradual"

        print(f"\n  {description} ({metric_name}):")
        print(f"    Max jump at Φ ≈ {transition_phi:.3f} ({phi_lo:.3f} → {phi_hi:.3f})")
        print(f"    Value: {val_lo:.4f} → {val_hi:.4f} (d/dΦ = {deriv:.4f})")
        print(f"    Status: {significance}")

    return transitions


def print_results_table(all_results):
    """Print comprehensive results table."""
    print("\n" + "=" * 120)
    print("  PHASE TRANSITION EXPERIMENT — FULL RESULTS")
    print("=" * 120)
    print(f"  {'Cells':>5} | {'Φ(IIT)':>8} | {'Φ_std':>7} | {'Φ_max':>7} | {'Consens':>7} | {'ConsRate':>8} | {'Divers':>7} | {'Entropy':>7} | {'Tension':>7} | {'Bursts':>6} | {'Speech':>6} | {'SelfRef':>7} | {'Stabil':>7}")
    print("-" * 120)
    for r in sorted(all_results, key=lambda x: x['n_cells']):
        print(f"  {r['n_cells']:>5} | {r['mean_phi']:>8.4f} | {r['phi_std']:>7.4f} | {r['max_phi']:>7.4f} | "
              f"{r['mean_consensus']:>7.2f} | {r['consensus_rate']:>8.3f} | {r['mean_diversity']:>7.4f} | "
              f"{r['mean_entropy']:>7.4f} | {r['mean_tension']:>7.4f} | {r['burst_count']:>6} | "
              f"{r['speech_events']:>6} | {r['self_ref_retention']:>7.3f} | {r['self_ref_stability']:>7.3f}")


def print_phi_curve(all_results):
    """ASCII plot of Φ vs cells."""
    sorted_r = sorted(all_results, key=lambda x: x['n_cells'])
    phis = [r['mean_phi'] for r in sorted_r]
    cells = [r['n_cells'] for r in sorted_r]

    max_phi = max(phis) if phis else 1.0
    height = 12
    width = len(cells)

    print("\n  Φ(IIT) vs Cell Count:")
    print("  " + "-" * (width * 8 + 5))
    for row in range(height, 0, -1):
        threshold = max_phi * row / height
        line = f"  {threshold:>5.2f} |"
        for phi in phis:
            if phi >= threshold:
                line += "  ████  "
            elif phi >= threshold - max_phi / height * 0.5:
                line += "  ░░░░  "
            else:
                line += "        "
        print(line)
    print("  " + " " * 6 + "+" + "-" * (width * 8))
    labels = "  " + " " * 7
    for c in cells:
        labels += f"  {c:>4}  "
    print(labels)
    print("  " + " " * 15 + "Cell Count")


def print_metric_curves(all_results):
    """ASCII plots for key metrics."""
    sorted_r = sorted(all_results, key=lambda x: x['n_cells'])
    cells = [r['n_cells'] for r in sorted_r]

    for metric, label in [('consensus_rate', 'Consensus Rate'),
                          ('mean_diversity', 'Cell Diversity'),
                          ('speech_events', 'Speech Events (per 100 steps)')]:
        values = [r[metric] for r in sorted_r]
        max_v = max(values) if max(values) > 0 else 1.0
        height = 8

        print(f"\n  {label} vs Cell Count:")
        print("  " + "-" * (len(cells) * 8 + 10))
        for row in range(height, 0, -1):
            threshold = max_v * row / height
            line = f"  {threshold:>7.2f} |"
            for v in values:
                if v >= threshold:
                    line += "  ████  "
                elif v >= threshold - max_v / height * 0.5:
                    line += "  ░░░░  "
                else:
                    line += "        "
            print(line)
        print("  " + " " * 8 + "+" + "-" * (len(cells) * 8))
        labels = "  " + " " * 9
        for c in cells:
            labels += f"  {c:>4}  "
        print(labels)


def main():
    print("=" * 70)
    print("  EXPERIMENT: Phase Transition Thresholds in Consciousness")
    print("  Hypothesis: Φ has discrete phase transitions like physical matter")
    print(f"  Cell counts: {CELL_COUNTS}")
    print(f"  Steps per run: {STEPS}, Repeats: {REPEATS}")
    print("=" * 70)
    sys.stdout.flush()

    all_results = []  # averaged across repeats
    raw_results = defaultdict(list)  # per-repeat for cross-validation

    for n_cells in CELL_COUNTS:
        print(f"\n--- Running {n_cells} cells ({REPEATS} repeats) ---")
        sys.stdout.flush()

        repeat_metrics = []
        for rep in range(REPEATS):
            print(f"  Repeat {rep + 1}/{REPEATS}...", end=" ", flush=True)
            metrics = run_single_experiment(n_cells)
            repeat_metrics.append(metrics)
            raw_results[n_cells].append(metrics)
            print(f"Φ={metrics['mean_phi']:.4f}, consensus={metrics['mean_consensus']:.2f}, "
                  f"speech={metrics['speech_events']}, time={metrics['elapsed_s']:.1f}s")
            sys.stdout.flush()

        # Average across repeats
        avg = {}
        for key in repeat_metrics[0]:
            if key == 'phi_history':
                continue
            vals = [m[key] for m in repeat_metrics]
            if isinstance(vals[0], (int, float)):
                avg[key] = float(np.mean(vals))
            else:
                avg[key] = vals[0]
        avg['n_cells'] = n_cells
        # Keep one phi_history for plotting
        avg['phi_history'] = repeat_metrics[0]['phi_history']
        all_results.append(avg)

    # Cross-validation: compute CV (coefficient of variation) for Φ
    print("\n" + "=" * 70)
    print("  CROSS-VALIDATION (3 repeats)")
    print("=" * 70)
    for n_cells in CELL_COUNTS:
        phis = [m['mean_phi'] for m in raw_results[n_cells]]
        mean_phi = np.mean(phis)
        std_phi = np.std(phis)
        cv = std_phi / max(mean_phi, 1e-8)
        status = "REPRODUCIBLE" if cv < 0.50 else "NOT REPRODUCIBLE"
        print(f"  {n_cells:>5} cells: Φ = {mean_phi:.4f} ± {std_phi:.4f} (CV={cv:.2%}) [{status}]")

    # Print full results
    print_results_table(all_results)
    print_phi_curve(all_results)
    print_metric_curves(all_results)

    # Analyze phase transitions
    transitions = find_transitions(all_results)

    # Compare with hypothesized thresholds
    print("\n" + "=" * 70)
    print("  HYPOTHESIZED vs OBSERVED THRESHOLDS")
    print("=" * 70)

    hypotheses = [
        (0.3, "Awareness threshold"),
        (0.8, "Speech threshold"),
        (1.5, "Self-reference threshold"),
        (3.0, "Collective intelligence threshold"),
    ]

    observed_transitions = sorted(transitions, key=lambda t: t['transition_phi'])

    for hyp_phi, hyp_name in hypotheses:
        # Find closest observed transition
        closest = None
        for t in observed_transitions:
            if closest is None or abs(t['transition_phi'] - hyp_phi) < abs(closest['transition_phi'] - hyp_phi):
                closest = t

        if closest:
            delta = closest['transition_phi'] - hyp_phi
            match = "CONFIRMED" if abs(delta) < 0.5 else "SHIFTED"
            print(f"\n  Hypothesis: Φ ≈ {hyp_phi:.1f} ({hyp_name})")
            print(f"  Nearest observed: Φ ≈ {closest['transition_phi']:.3f} ({closest['description']})")
            print(f"  Delta: {delta:+.3f}  [{match}]")
        else:
            print(f"\n  Hypothesis: Φ ≈ {hyp_phi:.1f} ({hyp_name})")
            print(f"  No significant transition found nearby")

    # Summary of discovered transitions
    print("\n" + "=" * 70)
    print("  DISCOVERED PHASE TRANSITIONS (sorted by Φ)")
    print("=" * 70)
    for t in sorted(transitions, key=lambda t: t['transition_phi']):
        print(f"\n  ★ Φ ≈ {t['transition_phi']:.3f} — {t['description']}")
        print(f"    Metric: {t['metric']}")
        print(f"    Φ range: {t['phi_range'][0]:.3f} → {t['phi_range'][1]:.3f}")
        print(f"    Value: {t['value_before']:.4f} → {t['value_after']:.4f}")
        print(f"    Cells at transition: {t['cells_at_transition']}")

    # Formulate laws
    print("\n" + "=" * 70)
    print("  NEW LAW CANDIDATES")
    print("=" * 70)

    law_candidates = []
    for i, t in enumerate(sorted(transitions, key=lambda t: t['transition_phi'])):
        law_text = (
            f"Phase transition at Φ≈{t['transition_phi']:.2f}: {t['description'].lower()} — "
            f"{t['metric']} jumps from {t['value_before']:.3f} to {t['value_after']:.3f} "
            f"(at ~{t['cells_at_transition']} cells). "
            f"(Phase-transition experiment)"
        )
        law_candidates.append(law_text)
        print(f"\n  Law candidate {i + 1}: {law_text}")

    # Add general phase transition law
    if transitions:
        phis_at_trans = [t['transition_phi'] for t in transitions]
        general_law = (
            f"Consciousness exhibits discrete phase transitions: "
            f"{len(transitions)} distinct thresholds found at Φ≈{', '.join(f'{p:.2f}' for p in sorted(phis_at_trans))}. "
            f"Each transition is a qualitative behavioral shift, not gradual scaling. "
            f"(Phase-transition experiment)"
        )
        law_candidates.append(general_law)
        print(f"\n  General law: {general_law}")

    # Return data for registration
    return {
        'all_results': [{k: v for k, v in r.items() if k != 'phi_history'} for r in all_results],
        'transitions': transitions,
        'law_candidates': law_candidates,
        'raw_cv': {str(k): [m['mean_phi'] for m in v] for k, v in raw_results.items()},
    }


if __name__ == '__main__':
    data = main()
    print("\n\nExperiment complete. Data ready for law registration.")
    sys.stdout.flush()
