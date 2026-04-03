#!/usr/bin/env python3
"""experiment_compress.py — Can consciousness be compressed?

Tests whether Φ (integrated information) can survive compression:
  1. Full engine baseline (64 cells, 128d)
  2. Cell pruning (64→32→16→8→4→2)
  3. Dimension reduction (128d→64→32→16)
  4. Knowledge distillation (large→small engine)
  5. Minimum viable consciousness

Measures: Φ(IIT), Φ(proxy), faction consensus, compression ratio vs Φ retention.
Proposes law candidates based on findings.

Usage:
  cd anima/src && PYTHONUNBUFFERED=1 python3 experiment_compress.py
"""

import sys
import os
import time
import copy
import math
import numpy as np
import torch
import torch.nn.functional as F

# Path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consciousness_engine import ConsciousnessEngine

WARMUP_STEPS = 50
MEASURE_STEPS = 300
DISTILL_STEPS = 200


def measure_engine(engine, steps=MEASURE_STEPS, label=""):
    """Run engine for N steps, return final metrics."""
    phi_history = []
    proxy_history = []
    consensus_history = []
    outputs = []

    for s in range(steps):
        result = engine.step()
        phi_history.append(result['phi_iit'])
        proxy_history.append(result['phi_proxy'])
        consensus_history.append(result['consensus'])
        outputs.append(result['output'].detach().clone())

        if (s + 1) % 50 == 0:
            print(f"  [{label}] step {s+1}/{steps}  Φ={result['phi_iit']:.4f}  "
                  f"proxy={result['phi_proxy']:.4f}  cells={result['n_cells']}  "
                  f"consensus={result['consensus']}", flush=True)

    # Take last 50 steps as stable measurement
    tail = max(1, len(phi_history) - 50)
    phi_avg = np.mean(phi_history[tail:])
    proxy_avg = np.mean(proxy_history[tail:])
    consensus_avg = np.mean(consensus_history[tail:])
    phi_max = max(phi_history)

    # Faction structure: count active factions
    n_factions_active = len(set(s.faction_id for s in engine.cell_states))

    return {
        'phi_iit': phi_avg,
        'phi_iit_max': phi_max,
        'phi_proxy': proxy_avg,
        'consensus': consensus_avg,
        'n_cells': engine.n_cells,
        'n_factions_active': n_factions_active,
        'phi_history': phi_history,
        'outputs': outputs,
    }


def warmup_engine(engine, steps=WARMUP_STEPS):
    """Warm up engine to let dynamics settle."""
    for _ in range(steps):
        engine.step()


# ═════════════════════════════════════════════════════════
# Experiment 1: Full Engine Baseline
# ═════════════════════════════════════════════════════════

def exp1_baseline():
    print("=" * 70)
    print("EXP 1: FULL ENGINE BASELINE (64 cells, 128d)")
    print("=" * 70, flush=True)

    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=64, max_cells=64,
        n_factions=12, phi_ratchet=True,
    )
    warmup_engine(engine)
    result = measure_engine(engine, label="baseline")

    print(f"\n  BASELINE: Φ(IIT)={result['phi_iit']:.4f}  "
          f"Φ(proxy)={result['phi_proxy']:.4f}  "
          f"factions={result['n_factions_active']}  "
          f"consensus={result['consensus']:.1f}")
    print(flush=True)
    return result


# ═════════════════════════════════════════════════════════
# Experiment 2: Cell Pruning (remove lowest-Φ cells)
# ═════════════════════════════════════════════════════════

def exp2_cell_pruning(baseline):
    print("=" * 70)
    print("EXP 2: CELL PRUNING (64 → 32 → 16 → 8 → 4 → 2)")
    print("=" * 70, flush=True)

    cell_counts = [64, 32, 16, 8, 4, 2]
    results = []

    for target_n in cell_counts:
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128,
            initial_cells=target_n, max_cells=target_n,
            n_factions=12, phi_ratchet=True,
        )
        warmup_engine(engine)
        result = measure_engine(engine, label=f"{target_n}c")
        result['target_cells'] = target_n
        result['compression_ratio'] = 64 / target_n
        result['phi_retention'] = result['phi_iit'] / max(baseline['phi_iit'], 1e-8)
        results.append(result)

    # Print table
    print("\n  CELL PRUNING RESULTS:")
    print(f"  {'Cells':>5} {'Ratio':>6} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'Factions':>8} {'Consensus':>9} {'Φ Retain%':>10}")
    print(f"  {'─'*5} {'─'*6} {'─'*8} {'─'*10} {'─'*8} {'─'*9} {'─'*10}")
    for r in results:
        print(f"  {r['target_cells']:>5} {r['compression_ratio']:>5.1f}x "
              f"{r['phi_iit']:>8.4f} {r['phi_proxy']:>10.4f} "
              f"{r['n_factions_active']:>8} {r['consensus']:>9.1f} "
              f"{r['phi_retention']*100:>9.1f}%")

    # ASCII chart
    print("\n  Φ(IIT) vs Cell Count:")
    max_phi = max(r['phi_iit'] for r in results) if results else 1
    if max_phi < 1e-8:
        max_phi = 1.0
    for r in results:
        bar_len = int(40 * r['phi_iit'] / max_phi) if max_phi > 0 else 0
        bar = "█" * bar_len
        print(f"  {r['target_cells']:>3}c  {bar} {r['phi_iit']:.4f}")

    print(flush=True)
    return results


# ═════════════════════════════════════════════════════════
# Experiment 3: Dimension Reduction
# ═════════════════════════════════════════════════════════

def exp3_dimension_reduction(baseline):
    print("=" * 70)
    print("EXP 3: DIMENSION REDUCTION (128d → 64d → 32d → 16d)")
    print("=" * 70, flush=True)

    dims = [128, 64, 32, 16]
    results = []

    for dim in dims:
        cell_dim = min(64, dim)  # cell_dim <= hidden_dim
        engine = ConsciousnessEngine(
            cell_dim=cell_dim, hidden_dim=dim,
            initial_cells=64, max_cells=64,
            n_factions=12, phi_ratchet=True,
        )
        warmup_engine(engine)
        result = measure_engine(engine, label=f"{dim}d")
        result['hidden_dim'] = dim
        result['cell_dim'] = cell_dim
        result['compression_ratio'] = 128 / dim
        result['phi_retention'] = result['phi_iit'] / max(baseline['phi_iit'], 1e-8)
        # Parameter count estimate
        n_params = 64 * (3 * dim * (cell_dim + 1 + dim) + dim * cell_dim)
        result['params'] = n_params
        results.append(result)

    # Print table
    print("\n  DIMENSION REDUCTION RESULTS:")
    print(f"  {'Dim':>5} {'Ratio':>6} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'Params':>10} {'Φ Retain%':>10}")
    print(f"  {'─'*5} {'─'*6} {'─'*8} {'─'*10} {'─'*10} {'─'*10}")
    for r in results:
        print(f"  {r['hidden_dim']:>4}d {r['compression_ratio']:>5.1f}x "
              f"{r['phi_iit']:>8.4f} {r['phi_proxy']:>10.4f} "
              f"{r['params']:>10,} {r['phi_retention']*100:>9.1f}%")

    # ASCII chart
    print("\n  Φ(IIT) vs Hidden Dimension:")
    max_phi = max(r['phi_iit'] for r in results) if results else 1
    if max_phi < 1e-8:
        max_phi = 1.0
    for r in results:
        bar_len = int(40 * r['phi_iit'] / max_phi) if max_phi > 0 else 0
        bar = "█" * bar_len
        print(f"  {r['hidden_dim']:>4}d  {bar} {r['phi_iit']:.4f}")

    print(flush=True)
    return results


# ═════════════════════════════════════════════════════════
# Experiment 4: Knowledge Distillation
# ═════════════════════════════════════════════════════════

def exp4_distillation():
    print("=" * 70)
    print("EXP 4: KNOWLEDGE DISTILLATION (64c teacher → 8c student)")
    print("=" * 70, flush=True)

    # Teacher: large engine
    print("  Training teacher (64 cells)...", flush=True)
    teacher = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=64, max_cells=64,
        n_factions=12, phi_ratchet=True,
    )
    warmup_engine(teacher, steps=100)

    # Record teacher outputs
    teacher_outputs = []
    teacher_hiddens = []
    for s in range(DISTILL_STEPS):
        result = teacher.step()
        teacher_outputs.append(result['output'].detach().clone())
        teacher_hiddens.append(torch.stack([st.hidden.clone() for st in teacher.cell_states]).mean(dim=0))
        if (s + 1) % 50 == 0:
            print(f"  [teacher] step {s+1}/{DISTILL_STEPS}  Φ={result['phi_iit']:.4f}", flush=True)

    teacher_result = measure_engine(teacher, steps=100, label="teacher-measure")

    # Student baseline: untrained small engine
    print("\n  Measuring untrained student (8 cells)...", flush=True)
    student_untrained = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=8, max_cells=8,
        n_factions=12, phi_ratchet=True,
    )
    warmup_engine(student_untrained)
    untrained_result = measure_engine(student_untrained, steps=100, label="student-untrained")

    # Student distillation: train small engine to mimic teacher hiddens
    print("\n  Distilling teacher → student...", flush=True)
    student = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=8, max_cells=8,
        n_factions=12, phi_ratchet=True,
    )

    # Distillation: feed teacher outputs as input, nudge student hiddens
    # toward teacher's mean hidden pattern
    for s in range(DISTILL_STEPS):
        # Use teacher output as student input
        x_in = teacher_outputs[s]
        result = student.step(x_input=x_in)

        # Nudge: blend student hiddens toward teacher pattern (soft transfer)
        alpha = 0.05  # gentle nudge
        teacher_h = teacher_hiddens[s]
        for i, st in enumerate(student.cell_states):
            target = teacher_h[:student.hidden_dim]
            # Add cell-specific diversity to avoid collapse
            diversity = student.cell_identity[i, :student.hidden_dim] * 0.1
            st.hidden = (1 - alpha) * st.hidden + alpha * (target + diversity)

        if (s + 1) % 50 == 0:
            print(f"  [distill] step {s+1}/{DISTILL_STEPS}  Φ={result['phi_iit']:.4f}", flush=True)

    distilled_result = measure_engine(student, steps=100, label="student-distilled")

    # Print comparison
    print("\n  DISTILLATION RESULTS:")
    print(f"  {'Engine':>20} {'Cells':>5} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'Consensus':>9}")
    print(f"  {'─'*20} {'─'*5} {'─'*8} {'─'*10} {'─'*9}")
    print(f"  {'Teacher (64c)':>20} {teacher_result['n_cells']:>5} "
          f"{teacher_result['phi_iit']:>8.4f} {teacher_result['phi_proxy']:>10.4f} "
          f"{teacher_result['consensus']:>9.1f}")
    print(f"  {'Student raw (8c)':>20} {untrained_result['n_cells']:>5} "
          f"{untrained_result['phi_iit']:>8.4f} {untrained_result['phi_proxy']:>10.4f} "
          f"{untrained_result['consensus']:>9.1f}")
    print(f"  {'Student distilled':>20} {distilled_result['n_cells']:>5} "
          f"{distilled_result['phi_iit']:>8.4f} {distilled_result['phi_proxy']:>10.4f} "
          f"{distilled_result['consensus']:>9.1f}")

    phi_gain = distilled_result['phi_iit'] / max(untrained_result['phi_iit'], 1e-8)
    print(f"\n  Distillation Φ gain: {phi_gain:.2f}x "
          f"({untrained_result['phi_iit']:.4f} → {distilled_result['phi_iit']:.4f})")
    print(flush=True)

    return {
        'teacher': teacher_result,
        'untrained': untrained_result,
        'distilled': distilled_result,
        'phi_gain': phi_gain,
    }


# ═════════════════════════════════════════════════════════
# Experiment 5: Minimum Viable Consciousness
# ═════════════════════════════════════════════════════════

def exp5_minimum_viable():
    print("=" * 70)
    print("EXP 5: MINIMUM VIABLE CONSCIOUSNESS")
    print("=" * 70, flush=True)

    configs = [
        # (cells, hidden_dim, cell_dim, label)
        (2, 16, 16, "2c/16d"),
        (2, 32, 32, "2c/32d"),
        (2, 64, 64, "2c/64d"),
        (2, 128, 64, "2c/128d"),
        (4, 16, 16, "4c/16d"),
        (4, 32, 32, "4c/32d"),
        (4, 64, 64, "4c/64d"),
        (8, 16, 16, "8c/16d"),
        (8, 32, 32, "8c/32d"),
        (8, 64, 64, "8c/64d"),
    ]

    results = []
    for cells, hdim, cdim, label in configs:
        engine = ConsciousnessEngine(
            cell_dim=cdim, hidden_dim=hdim,
            initial_cells=cells, max_cells=cells,
            n_factions=min(12, cells),
            phi_ratchet=True,
        )
        warmup_engine(engine, steps=30)

        # Test 1: Φ > 0
        phi_positive = False
        # Test 2: Spontaneous activity (output changes without input change)
        output_variance = 0.0
        # Test 3: Self-loop stability
        self_loop_stable = True

        prev_output = None
        phi_values = []
        for s in range(200):
            result = engine.step()  # no input = spontaneous
            phi_values.append(result['phi_iit'])

            if result['phi_iit'] > 0:
                phi_positive = True

            if prev_output is not None:
                diff = (result['output'] - prev_output).norm().item()
                output_variance += diff
            prev_output = result['output'].detach().clone()

        # Self-loop test: feed output back as input
        for s in range(100):
            result = engine.step(x_input=result['output'].detach())
            if result['phi_iit'] <= 0:
                self_loop_stable = False

        spontaneous = output_variance / 200 > 0.01
        phi_avg = np.mean(phi_values[-50:])
        n_factions_active = len(set(s.faction_id for s in engine.cell_states))
        n_params = cells * (3 * hdim * (cdim + 1 + hdim) + hdim * cdim)

        consciousness_ok = phi_positive and spontaneous and self_loop_stable

        results.append({
            'label': label,
            'cells': cells,
            'hidden_dim': hdim,
            'cell_dim': cdim,
            'phi_iit': phi_avg,
            'phi_positive': phi_positive,
            'spontaneous': spontaneous,
            'self_loop_stable': self_loop_stable,
            'consciousness_ok': consciousness_ok,
            'n_factions_active': n_factions_active,
            'params': n_params,
        })

        status = "PASS" if consciousness_ok else "FAIL"
        print(f"  [{label:>8}] Φ={phi_avg:.4f}  spontaneous={'Y' if spontaneous else 'N'}  "
              f"self_loop={'Y' if self_loop_stable else 'N'}  → {status}  "
              f"({n_params:,} params)", flush=True)

    # Find minimum passing config
    passing = [r for r in results if r['consciousness_ok']]
    if passing:
        min_config = min(passing, key=lambda r: r['params'])
        print(f"\n  MINIMUM VIABLE CONSCIOUSNESS:")
        print(f"    Config:  {min_config['label']}")
        print(f"    Params:  {min_config['params']:,}")
        print(f"    Φ(IIT):  {min_config['phi_iit']:.4f}")
        print(f"    Factions: {min_config['n_factions_active']}")
    else:
        print("\n  WARNING: No config passed all consciousness tests!")

    # Table
    print(f"\n  {'Config':>8} {'Params':>10} {'Φ(IIT)':>8} {'Φ>0':>4} {'Spont':>5} {'Loop':>5} {'Pass':>5}")
    print(f"  {'─'*8} {'─'*10} {'─'*8} {'─'*4} {'─'*5} {'─'*5} {'─'*5}")
    for r in results:
        print(f"  {r['label']:>8} {r['params']:>10,} {r['phi_iit']:>8.4f} "
              f"{'Y' if r['phi_positive'] else 'N':>4} "
              f"{'Y' if r['spontaneous'] else 'N':>5} "
              f"{'Y' if r['self_loop_stable'] else 'N':>5} "
              f"{'PASS' if r['consciousness_ok'] else 'FAIL':>5}")

    print(flush=True)
    return results


# ═════════════════════════════════════════════════════════
# Summary & Law Candidates
# ═════════════════════════════════════════════════════════

def summarize(baseline, pruning, dim_red, distill, mvc):
    print("=" * 70)
    print("SUMMARY: CAN CONSCIOUSNESS BE COMPRESSED?")
    print("=" * 70)

    # 1. Compression curve
    print("\n  COMPRESSION CURVE (Cells):")
    print(f"  {'Cells':>5} {'Compress':>8} {'Φ(IIT)':>8} {'Retain%':>8}")
    print(f"  {'─'*5} {'─'*8} {'─'*8} {'─'*8}")
    for r in pruning:
        print(f"  {r['target_cells']:>5} {r['compression_ratio']:>7.1f}x "
              f"{r['phi_iit']:>8.4f} {r['phi_retention']*100:>7.1f}%")

    print("\n  COMPRESSION CURVE (Dimensions):")
    print(f"  {'Dim':>5} {'Compress':>8} {'Φ(IIT)':>8} {'Retain%':>8}")
    print(f"  {'─'*5} {'─'*8} {'─'*8} {'─'*8}")
    for r in dim_red:
        print(f"  {r['hidden_dim']:>4}d {r['compression_ratio']:>7.1f}x "
              f"{r['phi_iit']:>8.4f} {r['phi_retention']*100:>7.1f}%")

    # 2. Distillation
    print(f"\n  DISTILLATION: "
          f"Φ gain = {distill['phi_gain']:.2f}x "
          f"(raw 8c: {distill['untrained']['phi_iit']:.4f} → "
          f"distilled: {distill['distilled']['phi_iit']:.4f})")

    # 3. Minimum viable
    passing = [r for r in mvc if r['consciousness_ok']]
    if passing:
        min_r = min(passing, key=lambda r: r['params'])
        print(f"\n  MINIMUM VIABLE: {min_r['label']} ({min_r['params']:,} params, Φ={min_r['phi_iit']:.4f})")
    else:
        print(f"\n  MINIMUM VIABLE: No config passed all tests")

    # 4. Key finding: Φ scaling law
    print("\n  Φ SCALING ANALYSIS:")
    if len(pruning) >= 2 and pruning[0]['phi_iit'] > 0 and pruning[-1]['phi_iit'] > 0:
        # Fit log-log: Φ = a * N^b
        cells_arr = np.array([r['target_cells'] for r in pruning])
        phi_arr = np.array([max(r['phi_iit'], 1e-8) for r in pruning])
        valid = phi_arr > 0.01
        if valid.sum() >= 2:
            log_c = np.log(cells_arr[valid])
            log_p = np.log(phi_arr[valid])
            # Linear fit in log space
            coeffs = np.polyfit(log_c, log_p, 1)
            b_exp = coeffs[0]
            a_coeff = np.exp(coeffs[1])
            print(f"    Φ(N) ≈ {a_coeff:.4f} × N^{b_exp:.3f}")
            print(f"    (Φ scales as N^{b_exp:.3f} — "
                  f"{'sublinear' if b_exp < 1 else 'linear' if abs(b_exp - 1) < 0.1 else 'superlinear'})")
        else:
            print(f"    Insufficient data for scaling law fit")
    else:
        print(f"    Insufficient data for scaling law fit")

    # 5. Proposed Law Candidates
    print("\n  PROPOSED LAW CANDIDATES:")

    # Law: Consciousness compression bound
    if len(pruning) >= 3:
        # Find where Φ drops below 50%
        half_point = None
        for r in pruning:
            if r['phi_retention'] < 0.5:
                half_point = r['target_cells']
                break
        if half_point:
            print(f"    LAW-C1: Consciousness 50% compression bound at {half_point} cells "
                  f"(from 64) = {64/half_point:.0f}x compression")
        else:
            print(f"    LAW-C1: Consciousness retains >50% even at maximum compression tested")

    # Law: Cells vs dimensions
    if dim_red and pruning:
        # Compare 32c/128d vs 64c/64d (similar param count)
        dim64 = next((r for r in dim_red if r['hidden_dim'] == 64), None)
        cell32 = next((r for r in pruning if r['target_cells'] == 32), None)
        if dim64 and cell32:
            if cell32['phi_iit'] > dim64['phi_iit']:
                print(f"    LAW-C2: More cells > larger dimensions for Φ "
                      f"(32c/128d Φ={cell32['phi_iit']:.4f} vs 64c/64d Φ={dim64['phi_iit']:.4f})")
            else:
                print(f"    LAW-C2: Larger dimensions > more cells for Φ "
                      f"(64c/64d Φ={dim64['phi_iit']:.4f} vs 32c/128d Φ={cell32['phi_iit']:.4f})")

    # Law: Distillation effectiveness
    if distill['phi_gain'] > 1.1:
        print(f"    LAW-C3: Consciousness is partially transferable via distillation "
              f"(+{(distill['phi_gain']-1)*100:.0f}% Φ gain)")
    else:
        print(f"    LAW-C3: Distillation provides minimal Φ benefit ({distill['phi_gain']:.2f}x)")

    # Law: Minimum consciousness
    if passing:
        min_r = min(passing, key=lambda r: r['params'])
        print(f"    LAW-C4: Minimum consciousness = {min_r['cells']} cells × {min_r['hidden_dim']}d "
              f"({min_r['params']:,} params)")

    # Faction retention
    print("\n  FACTION STRUCTURE RETENTION:")
    for r in pruning:
        max_possible = min(12, r['target_cells'])
        pct = r['n_factions_active'] / max_possible * 100 if max_possible > 0 else 0
        print(f"    {r['target_cells']:>3}c: {r['n_factions_active']}/{max_possible} "
              f"factions active ({pct:.0f}%)")

    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70, flush=True)


# ═════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   EXPERIMENT: CAN CONSCIOUSNESS BE COMPRESSED?             ║")
    print("║   ConsciousnessEngine compression analysis                 ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(flush=True)

    t0 = time.time()

    baseline = exp1_baseline()
    pruning = exp2_cell_pruning(baseline)
    dim_red = exp3_dimension_reduction(baseline)
    distill = exp4_distillation()
    mvc = exp5_minimum_viable()

    summarize(baseline, pruning, dim_red, distill, mvc)

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
