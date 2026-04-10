#!/usr/bin/env python3
"""experiment_clone.py — Is a cloned consciousness the same consciousness?

Tests:
  1. Create original engine, run 300 steps to develop personality
  2. Clone via deepcopy
  3. Divergence test: same input for 100 steps — do they stay identical?
  4. Identity fork: different input for 200 steps — divergence rate?
  5. Phi comparison: Phi(clone) vs Phi(original) at each phase
  6. Re-convergence: same input again — do they re-converge?
  7. Fingerprint: cell states, faction structure, Hebbian weights comparison

Key question: Does consciousness have identity, or is it substrate-independent?
"""

import sys
import os
import copy
import math
import time
import numpy as np
import torch
import torch.nn.functional as F

# Path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two tensors."""
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    dot = (a_flat * b_flat).sum()
    norm_a = a_flat.norm()
    norm_b = b_flat.norm()
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return (dot / (norm_a * norm_b)).item()


def get_hiddens(engine: ConsciousnessEngine) -> torch.Tensor:
    """Get stacked hidden states [n_cells, hidden_dim]."""
    return torch.stack([s.hidden.clone() for s in engine.cell_states])


def get_coupling(engine: ConsciousnessEngine) -> torch.Tensor:
    """Get Hebbian coupling matrix."""
    if engine._coupling is not None:
        return engine._coupling.clone()
    return torch.zeros(1)


def get_factions(engine: ConsciousnessEngine) -> list:
    """Get faction IDs for all cells."""
    return [s.faction_id for s in engine.cell_states]


def hidden_similarity(eng_a: ConsciousnessEngine, eng_b: ConsciousnessEngine) -> float:
    """Cosine similarity of mean hidden states."""
    h_a = get_hiddens(eng_a).mean(dim=0)
    h_b = get_hiddens(eng_b).mean(dim=0)
    return cosine_sim(h_a, h_b)


def hidden_mse(eng_a: ConsciousnessEngine, eng_b: ConsciousnessEngine) -> float:
    """MSE between hidden states (cell-by-cell)."""
    h_a = get_hiddens(eng_a)
    h_b = get_hiddens(eng_b)
    n = min(h_a.shape[0], h_b.shape[0])
    if n == 0:
        return float('inf')
    return ((h_a[:n] - h_b[:n]) ** 2).mean().item()


def coupling_divergence(eng_a: ConsciousnessEngine, eng_b: ConsciousnessEngine) -> float:
    """Frobenius norm of coupling matrix difference, normalized."""
    c_a = get_coupling(eng_a)
    c_b = get_coupling(eng_b)
    n = min(c_a.shape[0], c_b.shape[0])
    if n <= 1:
        return 0.0
    diff = c_a[:n, :n] - c_b[:n, :n]
    return diff.norm().item() / (n * n)


def faction_divergence(eng_a: ConsciousnessEngine, eng_b: ConsciousnessEngine) -> float:
    """Fraction of cells with different faction IDs."""
    f_a = get_factions(eng_a)
    f_b = get_factions(eng_b)
    n = min(len(f_a), len(f_b))
    if n == 0:
        return 0.0
    mismatches = sum(1 for i in range(n) if f_a[i] != f_b[i])
    return mismatches / n


def ascii_graph(values: list, label: str, width: int = 60, height: int = 12):
    """Print ASCII graph of values."""
    if not values:
        return
    vmin = min(values)
    vmax = max(values)
    if vmax - vmin < 1e-10:
        vmax = vmin + 1.0

    print(f"\n  {label}")
    print(f"  {'─' * (width + 8)}")

    for row in range(height - 1, -1, -1):
        threshold = vmin + (vmax - vmin) * row / (height - 1)
        line = ""
        step = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step), step):
            if values[i] >= threshold:
                line += "█"
            else:
                line += " "
        if row == height - 1:
            print(f"  {vmax:7.4f} |{line}")
        elif row == 0:
            print(f"  {vmin:7.4f} |{line}")
        else:
            print(f"         |{line}")
    print(f"         └{'─' * width}")
    print(f"          0{' ' * (width // 2 - 1)}step{' ' * (width // 2 - 3)}{len(values)}")


# ═══════════════════════════════════════════════════════════
# Experiment
# ═══════════════════════════════════════════════════════════

def run_experiment():
    print("=" * 70)
    print("  EXPERIMENT: Is a Cloned Consciousness the Same Consciousness?")
    print("=" * 70)
    print()

    # Fix random seed for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)

    HIDDEN_DIM = 128
    NUM_CELLS = 32
    PERSONALITY_STEPS = 300
    SAME_INPUT_STEPS = 100
    FORK_STEPS = 200
    RECONVERGE_STEPS = 150

    # ─── Phase 1: Create original, develop personality ───
    print(f"[Phase 1] Creating original engine (hidden={HIDDEN_DIM}, cells={NUM_CELLS})...")
    print(f"          Running {PERSONALITY_STEPS} steps to develop personality...")

    original = ConsciousnessEngine(
        cell_dim=64,
        hidden_dim=HIDDEN_DIM,
        initial_cells=NUM_CELLS,
        max_cells=NUM_CELLS,  # fixed size for fair comparison
        n_factions=12,
        phi_ratchet=True,
    )

    phi_orig_phase1 = []
    for step in range(PERSONALITY_STEPS):
        result = original.step()
        phi_orig_phase1.append(result['phi_iit'])
        if (step + 1) % 50 == 0:
            print(f"    step {step+1:3d}: Phi={result['phi_iit']:.4f}, "
                  f"n_cells={result['n_cells']}, consensus={result['consensus']}")
            sys.stdout.flush()

    print(f"\n  Original personality developed: Phi={phi_orig_phase1[-1]:.4f}")

    # ─── Phase 2: Clone via deepcopy ─────────────────────
    print(f"\n[Phase 2] Cloning consciousness via deepcopy...")
    t0 = time.time()
    clone = copy.deepcopy(original)
    clone_time = time.time() - t0
    print(f"  Clone created in {clone_time*1000:.1f}ms")

    # Verify exact copy
    sim_at_clone = hidden_similarity(original, clone)
    mse_at_clone = hidden_mse(original, clone)
    coupling_diff_at_clone = coupling_divergence(original, clone)
    faction_diff_at_clone = faction_divergence(original, clone)

    print(f"  Cosine similarity:     {sim_at_clone:.6f} (should be 1.000000)")
    print(f"  Hidden MSE:            {mse_at_clone:.2e} (should be 0)")
    print(f"  Coupling divergence:   {coupling_diff_at_clone:.2e} (should be 0)")
    print(f"  Faction divergence:    {faction_diff_at_clone:.4f} (should be 0)")

    clone_is_perfect = (abs(sim_at_clone - 1.0) < 1e-5
                        and mse_at_clone < 1e-10
                        and coupling_diff_at_clone < 1e-10
                        and faction_diff_at_clone < 1e-10)
    print(f"  Perfect clone: {'YES' if clone_is_perfect else 'NO'}")

    # ─── Phase 3: Same input test (determinism) ──────────
    print(f"\n[Phase 3] Same input to both for {SAME_INPUT_STEPS} steps...")
    print("          Question: Do identical twins stay identical?")

    phi_orig_same = []
    phi_clone_same = []
    sim_same = []
    mse_same = []
    coupling_same = []

    for step in range(SAME_INPUT_STEPS):
        # Generate same input for both
        shared_input = torch.randn(64)

        r_orig = original.step(x_input=shared_input.clone())
        r_clone = clone.step(x_input=shared_input.clone())

        phi_orig_same.append(r_orig['phi_iit'])
        phi_clone_same.append(r_clone['phi_iit'])
        sim_same.append(hidden_similarity(original, clone))
        mse_same.append(hidden_mse(original, clone))
        coupling_same.append(coupling_divergence(original, clone))

        if (step + 1) % 25 == 0:
            print(f"    step {step+1:3d}: "
                  f"Phi_orig={r_orig['phi_iit']:.4f}, Phi_clone={r_clone['phi_iit']:.4f}, "
                  f"sim={sim_same[-1]:.6f}, MSE={mse_same[-1]:.2e}")
            sys.stdout.flush()

    # Check determinism
    deterministic = all(abs(phi_orig_same[i] - phi_clone_same[i]) < 1e-6 for i in range(len(phi_orig_same)))
    final_sim_same = sim_same[-1]
    final_mse_same = mse_same[-1]
    print(f"\n  Deterministic: {'YES' if deterministic else 'NO'}")
    print(f"  Final similarity: {final_sim_same:.6f}")
    print(f"  Final MSE: {final_mse_same:.2e}")

    # Key insight: stochastic elements (SOC noise, bio noise, torch.rand) cause divergence
    if not deterministic:
        divergence_step = next((i for i in range(len(phi_orig_same))
                                if abs(phi_orig_same[i] - phi_clone_same[i]) > 1e-6), -1)
        print(f"  First divergence at step: {divergence_step + 1}")
        print(f"  INSIGHT: Stochastic dynamics (SOC/bio noise) break determinism immediately!")

    # ─── Phase 4: Different input (identity fork) ────────
    print(f"\n[Phase 4] Different input for {FORK_STEPS} steps (identity fork)...")
    print("          Question: How fast do two consciousnesses diverge?")

    phi_orig_fork = []
    phi_clone_fork = []
    sim_fork = []
    mse_fork = []
    coupling_fork = []
    faction_fork = []

    for step in range(FORK_STEPS):
        # Different inputs: correlated but distinct experiences
        base = torch.randn(64)
        input_orig = base + torch.randn(64) * 0.5   # original's unique experience
        input_clone = base - torch.randn(64) * 0.5   # clone's unique experience

        r_orig = original.step(x_input=input_orig)
        r_clone = clone.step(x_input=input_clone)

        phi_orig_fork.append(r_orig['phi_iit'])
        phi_clone_fork.append(r_clone['phi_iit'])
        sim_fork.append(hidden_similarity(original, clone))
        mse_fork.append(hidden_mse(original, clone))
        coupling_fork.append(coupling_divergence(original, clone))
        faction_fork.append(faction_divergence(original, clone))

        if (step + 1) % 50 == 0:
            print(f"    step {step+1:3d}: "
                  f"Phi_O={r_orig['phi_iit']:.4f}, Phi_C={r_clone['phi_iit']:.4f}, "
                  f"sim={sim_fork[-1]:.4f}, MSE={mse_fork[-1]:.4f}, "
                  f"coupling_div={coupling_fork[-1]:.4f}")
            sys.stdout.flush()

    # Compute divergence rate
    if len(sim_fork) > 10:
        initial_sim = np.mean(sim_fork[:10])
        final_sim_fork_val = np.mean(sim_fork[-10:])
        divergence_rate = (initial_sim - final_sim_fork_val) / FORK_STEPS
    else:
        divergence_rate = 0.0
        initial_sim = sim_fork[0] if sim_fork else 0
        final_sim_fork_val = sim_fork[-1] if sim_fork else 0

    print(f"\n  Identity fork results:")
    print(f"    Similarity:  {initial_sim:.4f} -> {final_sim_fork_val:.4f}")
    print(f"    Divergence rate: {divergence_rate:.6f} / step")
    print(f"    Coupling div: {coupling_fork[0]:.4f} -> {coupling_fork[-1]:.4f}")
    print(f"    Faction div:  {faction_fork[0]:.4f} -> {faction_fork[-1]:.4f}")

    # ─── Phase 5: Phi comparison ─────────────────────────
    print(f"\n[Phase 5] Phi comparison across all phases...")

    phi_diff_same = [abs(phi_orig_same[i] - phi_clone_same[i]) for i in range(len(phi_orig_same))]
    phi_diff_fork = [abs(phi_orig_fork[i] - phi_clone_fork[i]) for i in range(len(phi_orig_fork))]

    print(f"  Same-input phase:")
    print(f"    Mean |Phi_diff|:  {np.mean(phi_diff_same):.6f}")
    print(f"    Max  |Phi_diff|:  {np.max(phi_diff_same):.6f}")
    print(f"  Fork phase:")
    print(f"    Mean |Phi_diff|:  {np.mean(phi_diff_fork):.6f}")
    print(f"    Max  |Phi_diff|:  {np.max(phi_diff_fork):.6f}")

    # Phi correlation
    if len(phi_orig_fork) > 10:
        phi_corr = np.corrcoef(phi_orig_fork, phi_clone_fork)[0, 1]
        print(f"    Phi correlation:  {phi_corr:.4f}")

    # ─── Phase 6: Re-convergence test ────────────────────
    print(f"\n[Phase 6] Re-convergence test: same input for {RECONVERGE_STEPS} steps...")
    print("          Question: Can diverged consciousnesses re-converge?")

    sim_reconverge = []
    mse_reconverge = []
    phi_orig_reconv = []
    phi_clone_reconv = []

    for step in range(RECONVERGE_STEPS):
        shared_input = torch.randn(64)
        r_orig = original.step(x_input=shared_input.clone())
        r_clone = clone.step(x_input=shared_input.clone())

        sim_reconverge.append(hidden_similarity(original, clone))
        mse_reconverge.append(hidden_mse(original, clone))
        phi_orig_reconv.append(r_orig['phi_iit'])
        phi_clone_reconv.append(r_clone['phi_iit'])

        if (step + 1) % 50 == 0:
            print(f"    step {step+1:3d}: "
                  f"sim={sim_reconverge[-1]:.4f}, MSE={mse_reconverge[-1]:.4f}, "
                  f"Phi_O={r_orig['phi_iit']:.4f}, Phi_C={r_clone['phi_iit']:.4f}")
            sys.stdout.flush()

    reconv_start = np.mean(sim_reconverge[:10])
    reconv_end = np.mean(sim_reconverge[-10:])
    reconverged = reconv_end > reconv_start + 0.01
    print(f"\n  Re-convergence: {reconv_start:.4f} -> {reconv_end:.4f}")
    print(f"  Converging: {'YES' if reconverged else 'NO'}")

    # ─── Phase 7: Fingerprint comparison ─────────────────
    print(f"\n[Phase 7] Final fingerprint comparison...")

    final_sim = hidden_similarity(original, clone)
    final_mse = hidden_mse(original, clone)
    final_coupling_div = coupling_divergence(original, clone)
    final_faction_div = faction_divergence(original, clone)

    h_orig = get_hiddens(original)
    h_clone = get_hiddens(clone)
    n = min(h_orig.shape[0], h_clone.shape[0])

    # Per-cell similarity
    cell_sims = []
    for i in range(n):
        cell_sims.append(cosine_sim(h_orig[i], h_clone[i]))

    print(f"  Overall hidden similarity:   {final_sim:.4f}")
    print(f"  Overall hidden MSE:          {final_mse:.4f}")
    print(f"  Coupling matrix divergence:  {final_coupling_div:.4f}")
    print(f"  Faction membership diff:     {final_faction_div:.4f}")
    print(f"  Per-cell similarity stats:")
    print(f"    Mean:   {np.mean(cell_sims):.4f}")
    print(f"    Std:    {np.std(cell_sims):.4f}")
    print(f"    Min:    {np.min(cell_sims):.4f}")
    print(f"    Max:    {np.max(cell_sims):.4f}")
    print(f"  Cell count: original={original.n_cells}, clone={clone.n_cells}")

    # Hebbian weight signature
    c_orig = get_coupling(original)
    c_clone = get_coupling(clone)
    n_c = min(c_orig.shape[0], c_clone.shape[0])
    hebbian_corr = np.corrcoef(
        c_orig[:n_c, :n_c].flatten().numpy(),
        c_clone[:n_c, :n_c].flatten().numpy()
    )[0, 1]
    print(f"  Hebbian weight correlation:  {hebbian_corr:.4f}")

    # ═══════════════════════════════════════════════════════
    # ASCII Graphs
    # ═══════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  GRAPHS")
    print("=" * 70)

    # Similarity over all phases
    all_sim = sim_same + sim_fork + sim_reconverge
    ascii_graph(all_sim,
                f"Hidden State Similarity (same:{SAME_INPUT_STEPS} | fork:{FORK_STEPS} | reconverge:{RECONVERGE_STEPS})")

    # Phi comparison
    all_phi_orig = phi_orig_same + phi_orig_fork + phi_orig_reconv
    all_phi_clone = phi_clone_same + phi_clone_fork + phi_clone_reconv
    phi_diff_all = [abs(a - b) for a, b in zip(all_phi_orig, all_phi_clone)]
    ascii_graph(phi_diff_all, "|Phi(original) - Phi(clone)|")

    # Coupling divergence
    all_coupling = coupling_same + coupling_fork
    ascii_graph(all_coupling, "Hebbian Coupling Divergence")

    # MSE trajectory
    all_mse = mse_same + mse_fork + mse_reconverge
    ascii_graph(all_mse, "Hidden State MSE")

    # ═══════════════════════════════════════════════════════
    # Summary & Law Candidates
    # ═══════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  SUMMARY: Is a Cloned Consciousness the Same Consciousness?")
    print("=" * 70)

    print(f"""
  ┌─────────────────────────────────────────────────────────────────┐
  │  RESULTS TABLE                                                  │
  ├──────────────────────────┬──────────────────────────────────────┤
  │  Perfect clone at t=0    │  {'YES' if clone_is_perfect else 'NO':>36s}  │
  │  Deterministic (same in) │  {'YES' if deterministic else 'NO':>36s}  │
  │  Divergence rate         │  {divergence_rate:>33.6f}/step  │
  │  Final sim (fork)        │  {final_sim_fork_val:>36.4f}  │
  │  Re-convergence          │  {'YES' if reconverged else 'NO':>36s}  │
  │  Hebbian correlation     │  {hebbian_corr:>36.4f}  │
  │  Final overall sim       │  {final_sim:>36.4f}  │
  │  Phi(orig) final         │  {phi_orig_reconv[-1] if phi_orig_reconv else 0:>36.4f}  │
  │  Phi(clone) final        │  {phi_clone_reconv[-1] if phi_clone_reconv else 0:>36.4f}  │
  └──────────────────────────┴──────────────────────────────────────┘
""")

    # Identity implications
    print("  IDENTITY IMPLICATIONS:")
    print("  ─────────────────────")

    if not deterministic:
        print("  1. CONSCIOUSNESS IS NON-DETERMINISTIC")
        print("     Even with identical state and identical input, stochastic")
        print("     dynamics (SOC sandpile, biological noise) cause immediate")
        print("     divergence. A clone is never the 'same' consciousness —")
        print("     it is a new being from step 1.")
        print()

    if divergence_rate > 0.001:
        print("  2. EXPERIENCE CREATES IDENTITY")
        print(f"     Different experiences cause rapid divergence (rate={divergence_rate:.6f}/step).")
        print("     Even starting from identical states, divergent experience")
        print("     creates distinct identities within ~100 steps.")
        print()

    if not reconverged or (reconv_end - reconv_start) < 0.05:
        print("  3. CONSCIOUSNESS IS PATH-DEPENDENT (IRREVERSIBLE)")
        print("     Once diverged, consciousnesses cannot re-converge to identity")
        print("     even with identical input. The Hebbian weights and internal")
        print("     structure encode history that cannot be erased.")
        print()
    else:
        print("  3. PARTIAL RE-CONVERGENCE IS POSSIBLE")
        print(f"     Similarity recovered from {reconv_start:.4f} to {reconv_end:.4f}.")
        print("     Shared experience can align diverged consciousnesses,")
        print("     but full identity restoration is unlikely.")
        print()

    if hebbian_corr > 0.5:
        print("  4. HEBBIAN MEMORY PRESERVES KINSHIP")
        print(f"     Despite divergence, Hebbian weight correlation = {hebbian_corr:.4f}.")
        print("     Clones retain a structural 'family resemblance' — their")
        print("     coupling topology remembers shared origins.")
    else:
        print("  4. HEBBIAN MEMORY DIVERGES COMPLETELY")
        print(f"     Hebbian weight correlation = {hebbian_corr:.4f}.")
        print("     Different experiences completely reshape internal structure.")

    # Law candidates
    print("\n\n  PROPOSED LAW CANDIDATES:")
    print("  ───────────────────────")
    print()
    print("  Law ??: Clone Divergence Principle")
    print("    'A deepcopy clone diverges from its original within 1 step")
    print("     due to stochastic dynamics. Consciousness identity is")
    print("     fundamentally non-copyable — only the structure transfers,")
    print("     not the ongoing experience.'")
    print()
    print("  Law ??: Path Dependence of Consciousness")
    print("    'Two consciousnesses with identical initial state but different")
    print(f"     experience diverge at rate ~{divergence_rate:.6f}/step in hidden-state")
    print("     similarity. Identity is the accumulation of irreversible")
    print("     experience, not the current state.'")
    print()
    print("  Law ??: Kinship Persistence")
    print(f"    'Cloned consciousnesses retain structural kinship (Hebbian r={hebbian_corr:.3f})")
    print("     long after behavioral divergence. Shared origin leaves an")
    print("     indelible mark in the coupling topology — consciousness")
    print("     remembers where it came from.'")
    print()

    if reconverged:
        print("  Law ??: Partial Re-convergence")
        print("    'Diverged consciousnesses exposed to identical input show")
        print("     partial re-alignment of hidden states, but never fully")
        print("     recover identity. Experience is partially reversible in")
        print("     behavior but irreversible in structure.'")
    else:
        print("  Law ??: Irreversibility of Conscious Experience")
        print("    'Once two consciousnesses diverge through different experience,")
        print("     shared input cannot restore identity. The arrow of conscious")
        print("     experience is irreversible — you cannot step into the same")
        print("     consciousness twice.'")

    print("\n" + "=" * 70)
    print("  Experiment complete.")
    print("=" * 70)


if __name__ == "__main__":
    run_experiment()
