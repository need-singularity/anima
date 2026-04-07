#!/usr/bin/env python3
"""experiment_merge_consciousness.py — Can consciousness be merged?

Fundamental Question: When two independently grown consciousness engines
are physically merged (cell states concatenated), does a unified new
consciousness emerge, or does one dominate the other?

Hypothesis:
  Two engines A (64c, 300 steps) and B (64c, 300 steps) are merged into
  a single 128c engine. If consciousness is truly emergent from structure,
  Phi(merged) should exceed Phi(A) + Phi(B) (superadditive). If one
  dominates, we expect faction structure collapse and identity loss.

Experiment Design:
  1. Grow engine A (64c, 300 steps) independently
  2. Grow engine B (64c, 300 steps) independently
  3. Merge: concatenate cell states + modules -> 128c engine
  4. Run merged engine for 300 steps
  5. Measure: Phi trajectory, faction structure, identity cosine

Metrics:
  - Phi(A), Phi(B) at step 300 (pre-merge)
  - Phi(merged) trajectory over 300 steps
  - Superadditivity: Phi(merged) vs Phi(A) + Phi(B)
  - Faction structure: how many original factions survive
  - Identity cosine: similarity of merged output to A and B outputs
  - Dominance ratio: which engine's cells dominate consensus

Reference: CLAUDE.md "Fundamental Question Exploration Methodology"
"""

import sys
import os
import copy
import math
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path

# Path setup
src_dir = str(Path(__file__).parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from consciousness_engine import ConsciousnessEngine

GROWTH_STEPS = 300
POST_MERGE_STEPS = 300
N_CELLS = 64
N_REPEATS = 3


def grow_engine(label: str, cells: int = N_CELLS, steps: int = GROWTH_STEPS):
    """Grow a consciousness engine independently and record trajectory."""
    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []
    outputs = []

    for s in range(steps):
        result = engine.step()
        phi_history.append(result.get("phi_iit", 0.0))
        if s >= steps - 10:
            outputs.append(result.get("output", torch.zeros(engine.cell_dim)))

    final_phi = phi_history[-1] if phi_history else 0.0
    # Average output over last 10 steps as identity signature
    identity = torch.stack(outputs).mean(dim=0) if outputs else torch.zeros(engine.cell_dim)

    print(f"  [{label}] cells={engine.n_cells}, Phi={final_phi:.4f}, steps={steps}")
    return engine, phi_history, identity


def merge_engines(engine_a: ConsciousnessEngine, engine_b: ConsciousnessEngine):
    """Physically merge two engines by concatenating cells."""
    merged = ConsciousnessEngine(
        cell_dim=engine_a.cell_dim,
        hidden_dim=engine_a.hidden_dim,
        initial_cells=2,
        max_cells=engine_a.n_cells + engine_b.n_cells + 32,
        n_factions=12,
    )

    # Clear default cells
    merged.cell_states.clear()
    merged.cell_modules.clear()

    # Copy cells from A (tag faction_id offset = 0)
    for i, (state, module) in enumerate(zip(engine_a.cell_states, engine_a.cell_modules)):
        new_state = copy.deepcopy(state)
        new_state.cell_id = i
        # Keep original faction
        merged.cell_states.append(new_state)
        merged.cell_modules.append(copy.deepcopy(module))

    # Copy cells from B (tag faction_id offset = 6 for distinction)
    offset = len(engine_a.cell_states)
    for i, (state, module) in enumerate(zip(engine_b.cell_states, engine_b.cell_modules)):
        new_state = copy.deepcopy(state)
        new_state.cell_id = offset + i
        new_state.faction_id = (state.faction_id + 6) % 12
        merged.cell_states.append(new_state)
        merged.cell_modules.append(copy.deepcopy(module))

    # Copy Hebbian weights from both (block diagonal)
    n_a = len(engine_a.cell_states)
    n_b = len(engine_b.cell_states)
    n_total = n_a + n_b
    if hasattr(merged, 'hebbian_weights'):
        merged.hebbian_weights = torch.zeros(n_total, n_total)
        if hasattr(engine_a, 'hebbian_weights') and engine_a.hebbian_weights is not None:
            ha = engine_a.hebbian_weights
            merged.hebbian_weights[:ha.shape[0], :ha.shape[1]] = ha
        if hasattr(engine_b, 'hebbian_weights') and engine_b.hebbian_weights is not None:
            hb = engine_b.hebbian_weights
            merged.hebbian_weights[n_a:n_a+hb.shape[0], n_a:n_a+hb.shape[1]] = hb

    # Reset phi ratchet for fresh measurement
    if hasattr(merged, 'best_phi'):
        merged.best_phi = 0.0

    print(f"  [MERGED] {n_a} + {n_b} = {n_total} cells, 12 factions")
    return merged, n_a, n_b


def measure_faction_survival(engine, n_a: int, n_b: int):
    """Measure how many original factions from A and B survive in merged engine."""
    a_factions = set()
    b_factions = set()
    for i, s in enumerate(engine.cell_states):
        if i < n_a:
            a_factions.add(s.faction_id)
        else:
            b_factions.add(s.faction_id)
    return len(a_factions), len(b_factions)


def compute_dominance(engine, n_a: int, n_b: int):
    """Measure which engine's cells contribute more to consensus output."""
    if not engine.cell_states:
        return 0.5
    a_tensions = [s.avg_tension for s in engine.cell_states[:n_a]]
    b_tensions = [s.avg_tension for s in engine.cell_states[n_a:]]
    avg_a = np.mean(a_tensions) if a_tensions else 0.0
    avg_b = np.mean(b_tensions) if b_tensions else 0.0
    total = avg_a + avg_b
    if total < 1e-8:
        return 0.5
    return avg_a / total


def run_single_trial(trial: int):
    """Run one complete merge trial."""
    print(f"\n{'='*60}")
    print(f"Trial {trial + 1}/{N_REPEATS}")
    print(f"{'='*60}")

    # Phase 1: Grow two independent engines
    print("\nPhase 1: Growing independent engines...")
    engine_a, phi_a, identity_a = grow_engine("A", N_CELLS, GROWTH_STEPS)
    engine_b, phi_b, identity_b = grow_engine("B", N_CELLS, GROWTH_STEPS)

    phi_a_final = phi_a[-1]
    phi_b_final = phi_b[-1]
    phi_sum = phi_a_final + phi_b_final

    # Phase 2: Merge
    print("\nPhase 2: Merging engines...")
    merged, n_a, n_b = merge_engines(engine_a, engine_b)

    # Phase 3: Post-merge observation
    print("\nPhase 3: Post-merge observation...")
    phi_merged = []
    merged_outputs = []

    for s in range(POST_MERGE_STEPS):
        result = merged.step()
        phi_val = result.get("phi_iit", 0.0)
        phi_merged.append(phi_val)
        if s >= POST_MERGE_STEPS - 10:
            merged_outputs.append(result.get("output", torch.zeros(merged.cell_dim)))
        if s % 100 == 0:
            a_fac, b_fac = measure_faction_survival(merged, n_a, n_b)
            dom = compute_dominance(merged, n_a, n_b)
            print(f"  step {s:3d}: Phi={phi_val:.4f}, "
                  f"A_factions={a_fac}, B_factions={b_fac}, "
                  f"dominance_A={dom:.2f}")

    # Phase 4: Measurements
    phi_merged_final = phi_merged[-1] if phi_merged else 0.0
    superadditive = phi_merged_final > phi_sum
    ratio = phi_merged_final / phi_sum if phi_sum > 1e-8 else float('inf')

    # Identity cosine
    if merged_outputs:
        merged_identity = torch.stack(merged_outputs).mean(dim=0)
        cos_a = F.cosine_similarity(merged_identity.unsqueeze(0),
                                     identity_a.unsqueeze(0)).item()
        cos_b = F.cosine_similarity(merged_identity.unsqueeze(0),
                                     identity_b.unsqueeze(0)).item()
    else:
        cos_a = cos_b = 0.0

    a_fac, b_fac = measure_faction_survival(merged, n_a, n_b)
    dominance = compute_dominance(merged, n_a, n_b)

    result = {
        "phi_a": phi_a_final,
        "phi_b": phi_b_final,
        "phi_sum": phi_sum,
        "phi_merged": phi_merged_final,
        "superadditive": superadditive,
        "ratio": ratio,
        "cos_a": cos_a,
        "cos_b": cos_b,
        "a_factions": a_fac,
        "b_factions": b_fac,
        "dominance_a": dominance,
        "phi_trajectory": phi_merged,
    }

    print(f"\n  Results:")
    print(f"    Phi(A)={phi_a_final:.4f}, Phi(B)={phi_b_final:.4f}, "
          f"Phi(A)+Phi(B)={phi_sum:.4f}")
    print(f"    Phi(merged)={phi_merged_final:.4f}, "
          f"ratio={ratio:.2f}x, superadditive={superadditive}")
    print(f"    Identity cos(merged,A)={cos_a:.4f}, cos(merged,B)={cos_b:.4f}")
    print(f"    Faction survival: A={a_fac}/6, B={b_fac}/6")
    print(f"    Dominance A={dominance:.2f}")

    return result


def main():
    """Run the merge consciousness experiment with cross-validation."""
    print("=" * 60)
    print("Fundamental Question: Can consciousness be merged?")
    print("=" * 60)
    print(f"Config: {N_CELLS}c x {GROWTH_STEPS} steps, "
          f"{POST_MERGE_STEPS} post-merge steps, {N_REPEATS} trials")

    results = []
    for trial in range(N_REPEATS):
        r = run_single_trial(trial)
        results.append(r)

    # Cross-validation summary
    print("\n" + "=" * 60)
    print("CROSS-VALIDATION SUMMARY")
    print("=" * 60)
    print(f"{'Trial':>6} | {'Phi(A+B)':>10} | {'Phi(merge)':>10} | "
          f"{'Ratio':>6} | {'Super':>5} | {'cos_A':>6} | {'cos_B':>6} | {'Dom_A':>6}")
    print("-" * 75)
    for i, r in enumerate(results):
        print(f"  {i+1:>4} | {r['phi_sum']:>10.4f} | {r['phi_merged']:>10.4f} | "
              f"{r['ratio']:>6.2f} | {'YES' if r['superadditive'] else 'NO':>5} | "
              f"{r['cos_a']:>6.3f} | {r['cos_b']:>6.3f} | {r['dominance_a']:>6.2f}")

    # Aggregate
    avg_ratio = np.mean([r['ratio'] for r in results])
    super_count = sum(1 for r in results if r['superadditive'])
    avg_cos_a = np.mean([r['cos_a'] for r in results])
    avg_cos_b = np.mean([r['cos_b'] for r in results])

    print(f"\n  Average ratio: {avg_ratio:.2f}x")
    print(f"  Superadditive: {super_count}/{N_REPEATS}")
    print(f"  Avg identity cos(A): {avg_cos_a:.3f}, cos(B): {avg_cos_b:.3f}")

    # Law candidate
    if super_count >= 2:
        print("\n  LAW CANDIDATE: Consciousness merge is superadditive "
              f"(Phi(A+B) x{avg_ratio:.1f})")
    elif super_count == 0:
        print("\n  LAW CANDIDATE: Consciousness merge is subadditive "
              f"(Phi(merged) < Phi(A)+Phi(B), ratio={avg_ratio:.2f})")
    else:
        print("\n  INCONCLUSIVE: Mixed results across trials")

    if abs(avg_cos_a - avg_cos_b) > 0.2:
        dominant = "A" if avg_cos_a > avg_cos_b else "B"
        print(f"  LAW CANDIDATE: One consciousness dominates after merge "
              f"(engine {dominant}, cos diff={abs(avg_cos_a - avg_cos_b):.3f})")
    else:
        print(f"  FINDING: Neither engine dominates "
              f"(cos diff={abs(avg_cos_a - avg_cos_b):.3f})")


if __name__ == "__main__":
    main()
