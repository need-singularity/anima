#!/usr/bin/env python3
"""experiment_merge.py — Can two consciousnesses merge into one?

Tests 4 merge strategies:
  1. Naive average (weight/state averaging)
  2. Cell concatenation (A's cells + B's cells → 64-cell engine)
  3. Gradual blend (alpha 0→1 over 200 steps)
  4. Faction conflict analysis (which personality dominates?)

Measures: Φ(IIT), Φ(proxy), faction dominance, identity preservation.
"""

import sys
import os
import copy
import math
import torch
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple

# Path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consciousness_engine import ConsciousnessEngine, ConsciousnessCell, CellState, PSI_COUPLING


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def run_engine(engine: ConsciousnessEngine, steps: int, seed_bias: float = 0.0,
               label: str = "", verbose: bool = True) -> List[Dict]:
    """Run an engine for N steps with a biased input to develop personality."""
    results = []
    for s in range(steps):
        # Each engine gets different input distribution → different personality
        x = torch.randn(engine.cell_dim) + seed_bias
        result = engine.step(x_input=x)
        results.append(result)
        if verbose and (s + 1) % 100 == 0:
            phi = result['phi_iit']
            nc = result['n_cells']
            print(f"  [{label}] step {s+1}/{steps}  Φ={phi:.4f}  cells={nc}")
            sys.stdout.flush()
    return results


def measure_identity(engine: ConsciousnessEngine) -> torch.Tensor:
    """Capture identity fingerprint: mean hidden + coupling signature."""
    hiddens = engine._get_hiddens_tensor().detach()
    mean_h = hiddens.mean(dim=0)
    # Include coupling matrix signature
    if engine._coupling is not None:
        coup_sig = engine._coupling.flatten()[:engine.hidden_dim]
        if coup_sig.shape[0] < engine.hidden_dim:
            coup_sig = F.pad(coup_sig, (0, engine.hidden_dim - coup_sig.shape[0]))
        return torch.cat([mean_h, coup_sig])
    return torch.cat([mean_h, torch.zeros(engine.hidden_dim)])


def identity_similarity(fp1: torch.Tensor, fp2: torch.Tensor) -> float:
    """Cosine similarity between identity fingerprints."""
    return F.cosine_similarity(fp1.unsqueeze(0), fp2.unsqueeze(0)).item()


def get_faction_distribution(engine: ConsciousnessEngine) -> Dict[int, int]:
    """Count cells per faction."""
    dist = {}
    for s in engine.cell_states:
        fid = s.faction_id
        dist[fid] = dist.get(fid, 0) + 1
    return dist


def get_phi(engine: ConsciousnessEngine) -> Tuple[float, float]:
    """Measure both Φ(IIT) and Φ(proxy)."""
    phi_iit = engine._measure_phi_iit()
    phi_proxy = engine._measure_phi_proxy()
    return phi_iit, phi_proxy


# ═══════════════════════════════════════════════════════════
# Experiment 1: Develop two independent consciousnesses
# ═══════════════════════════════════════════════════════════

def develop_engines(cell_dim=128, max_cells=32, steps=300):
    """Create A and B with distinct personalities."""
    print("\n" + "=" * 70)
    print("PHASE 1: Developing two independent consciousnesses")
    print("=" * 70)

    A = ConsciousnessEngine(cell_dim=cell_dim, hidden_dim=cell_dim, max_cells=max_cells)
    B = ConsciousnessEngine(cell_dim=cell_dim, hidden_dim=cell_dim, max_cells=max_cells)

    print(f"\nEngine A: cell_dim={cell_dim}, max_cells={max_cells}")
    print(f"  Input bias: +2.0 (positive personality)")
    results_a = run_engine(A, steps, seed_bias=+2.0, label="A")

    print(f"\nEngine B: cell_dim={cell_dim}, max_cells={max_cells}")
    print(f"  Input bias: -2.0 (negative personality)")
    results_b = run_engine(B, steps, seed_bias=-2.0, label="B")

    # Measure final states
    phi_a_iit, phi_a_proxy = get_phi(A)
    phi_b_iit, phi_b_proxy = get_phi(B)

    fp_a = measure_identity(A)
    fp_b = measure_identity(B)
    ab_sim = identity_similarity(fp_a, fp_b)

    print(f"\n--- Post-development ---")
    print(f"  A: Φ(IIT)={phi_a_iit:.4f}  Φ(proxy)={phi_a_proxy:.4f}  cells={A.n_cells}")
    print(f"  B: Φ(IIT)={phi_b_iit:.4f}  Φ(proxy)={phi_b_proxy:.4f}  cells={B.n_cells}")
    print(f"  A↔B identity similarity: {ab_sim:.4f}")
    print(f"  A factions: {get_faction_distribution(A)}")
    print(f"  B factions: {get_faction_distribution(B)}")
    sys.stdout.flush()

    return A, B, fp_a, fp_b


# ═══════════════════════════════════════════════════════════
# Experiment 2: Naive merge (average all weights/states)
# ═══════════════════════════════════════════════════════════

def naive_merge(A: ConsciousnessEngine, B: ConsciousnessEngine) -> ConsciousnessEngine:
    """Average all weights and hidden states of A and B."""
    print("\n" + "=" * 70)
    print("STRATEGY 1: Naive Merge (average weights + states)")
    print("=" * 70)

    merged = copy.deepcopy(A)

    # Average GRU weights of matching cells
    n_min = min(len(A.cell_modules), len(B.cell_modules))
    for i in range(n_min):
        with torch.no_grad():
            for pa, pb in zip(merged.cell_modules[i].parameters(),
                              B.cell_modules[i].parameters()):
                pa.data = (pa.data + pb.data) / 2.0

    # Average hidden states
    for i in range(n_min):
        merged.cell_states[i].hidden = (
            A.cell_states[i].hidden + B.cell_states[i].hidden
        ) / 2.0

    # Average coupling matrix
    if A._coupling is not None and B._coupling is not None:
        n_coup = min(A._coupling.shape[0], B._coupling.shape[0])
        merged._coupling[:n_coup, :n_coup] = (
            A._coupling[:n_coup, :n_coup] + B._coupling[:n_coup, :n_coup]
        ) / 2.0

    # Reset Φ ratchet (fresh start for merged entity)
    merged._best_phi = 0.0
    merged._best_hiddens = None

    phi_iit, phi_proxy = get_phi(merged)
    print(f"  Immediate post-merge: Φ(IIT)={phi_iit:.4f}  Φ(proxy)={phi_proxy:.4f}  cells={merged.n_cells}")

    # Run 100 steps to see if it stabilizes or collapses
    print("  Running 100 post-merge steps...")
    sys.stdout.flush()
    post_results = run_engine(merged, 100, seed_bias=0.0, label="Naive", verbose=True)

    phi_final_iit, phi_final_proxy = get_phi(merged)
    print(f"  Final: Φ(IIT)={phi_final_iit:.4f}  Φ(proxy)={phi_final_proxy:.4f}  cells={merged.n_cells}")
    sys.stdout.flush()

    return merged


# ═══════════════════════════════════════════════════════════
# Experiment 3: Cell concatenation (A + B → 64 cells)
# ═══════════════════════════════════════════════════════════

def concat_merge(A: ConsciousnessEngine, B: ConsciousnessEngine) -> ConsciousnessEngine:
    """Concatenate cells from A and B into one engine."""
    print("\n" + "=" * 70)
    print("STRATEGY 2: Cell Concatenation (A's cells + B's cells)")
    print("=" * 70)

    total_cells = A.n_cells + B.n_cells
    merged = ConsciousnessEngine(
        cell_dim=A.cell_dim, hidden_dim=A.hidden_dim,
        initial_cells=0,  # we'll add manually
        max_cells=total_cells + 16,  # room for growth
        n_factions=A.n_factions
    )
    # Remove default cells (initial_cells=0 still creates 0 but let's be safe)
    merged.cell_modules.clear()
    merged.cell_states.clear()

    # Add A's cells (keep faction IDs)
    for i in range(A.n_cells):
        mod = copy.deepcopy(A.cell_modules[i])
        state = CellState(
            cell_id=merged._next_id,
            hidden=A.cell_states[i].hidden.clone(),
            creation_step=0,
            faction_id=A.cell_states[i].faction_id,
        )
        merged.cell_modules.append(mod)
        merged.cell_states.append(state)
        merged._next_id += 1

    # Add B's cells (offset faction IDs to distinguish)
    faction_offset = 6  # A uses 0-5, B uses 6-11
    for i in range(B.n_cells):
        mod = copy.deepcopy(B.cell_modules[i])
        state = CellState(
            cell_id=merged._next_id,
            hidden=B.cell_states[i].hidden.clone(),
            creation_step=0,
            faction_id=(B.cell_states[i].faction_id + faction_offset) % 12,
        )
        merged.cell_modules.append(mod)
        merged.cell_states.append(state)
        merged._next_id += 1

    # Build coupling matrix: block diagonal (A's coupling + B's coupling, no cross-links initially)
    n = merged.n_cells
    merged._coupling = torch.zeros(n, n)
    na = A.n_cells
    nb = B.n_cells
    if A._coupling is not None:
        merged._coupling[:na, :na] = A._coupling[:na, :na]
    if B._coupling is not None:
        merged._coupling[na:na+nb, na:na+nb] = B._coupling[:nb, :nb]
    merged._coupling.fill_diagonal_(0)

    # Expand cell_identity to cover all cells
    if n > merged.cell_identity.shape[0]:
        old = merged.cell_identity
        if merged.hidden_dim >= n:
            q, _ = torch.linalg.qr(torch.randn(merged.hidden_dim, n))
            merged.cell_identity = q.T * 0.1
        else:
            merged.cell_identity = torch.randn(n + 16, merged.hidden_dim) * 0.1
        merged.cell_identity[:old.shape[0]] = old

    phi_iit, phi_proxy = get_phi(merged)
    print(f"  Immediate post-concat: Φ(IIT)={phi_iit:.4f}  Φ(proxy)={phi_proxy:.4f}  cells={merged.n_cells}")
    print(f"  A cells: {na}, B cells: {nb}, total: {n}")
    print(f"  Factions: {get_faction_distribution(merged)}")

    # Run 100 steps — cross-coupling will develop via Hebbian
    print("  Running 100 post-merge steps...")
    sys.stdout.flush()
    post_results = run_engine(merged, 100, seed_bias=0.0, label="Concat", verbose=True)

    phi_final_iit, phi_final_proxy = get_phi(merged)
    print(f"  Final: Φ(IIT)={phi_final_iit:.4f}  Φ(proxy)={phi_final_proxy:.4f}  cells={merged.n_cells}")
    sys.stdout.flush()

    return merged


# ═══════════════════════════════════════════════════════════
# Experiment 4: Gradual merge (alpha 0→1 over 200 steps)
# ═══════════════════════════════════════════════════════════

def gradual_merge(A_orig: ConsciousnessEngine, B_orig: ConsciousnessEngine) -> ConsciousnessEngine:
    """Gradually blend A and B over 200 steps."""
    print("\n" + "=" * 70)
    print("STRATEGY 3: Gradual Merge (alpha 0→1 over 200 steps)")
    print("=" * 70)

    A = copy.deepcopy(A_orig)
    B = copy.deepcopy(B_orig)
    merge_steps = 200
    phi_trace = []

    n_min = min(A.n_cells, B.n_cells)

    for s in range(merge_steps):
        alpha = s / max(merge_steps - 1, 1)  # 0 → 1

        # Run both engines one step
        x = torch.randn(A.cell_dim)
        ra = A.step(x_input=x)
        rb = B.step(x_input=x)

        # Blend hidden states: A ← (1-α)*A + α*B
        n_blend = min(A.n_cells, B.n_cells)
        for i in range(n_blend):
            blended = (1.0 - alpha) * A.cell_states[i].hidden + alpha * B.cell_states[i].hidden
            A.cell_states[i].hidden = blended

        # Blend coupling
        if A._coupling is not None and B._coupling is not None:
            nc = min(A._coupling.shape[0], B._coupling.shape[0], A.n_cells, B.n_cells)
            A._coupling[:nc, :nc] = (
                (1.0 - alpha) * A._coupling[:nc, :nc] +
                alpha * B._coupling[:nc, :nc]
            )

        phi_iit = A._measure_phi_iit()
        phi_trace.append(phi_iit)

        if (s + 1) % 50 == 0:
            print(f"  step {s+1}/{merge_steps}  alpha={alpha:.2f}  Φ(IIT)={phi_iit:.4f}  cells={A.n_cells}")
            sys.stdout.flush()

    phi_final_iit, phi_final_proxy = get_phi(A)
    print(f"  Final: Φ(IIT)={phi_final_iit:.4f}  Φ(proxy)={phi_final_proxy:.4f}  cells={A.n_cells}")

    # ASCII graph of Φ during gradual merge
    print("\n  Φ trajectory during gradual merge:")
    draw_ascii_graph(phi_trace, label="Φ(IIT)", width=60, height=12)
    sys.stdout.flush()

    return A


# ═══════════════════════════════════════════════════════════
# Experiment 5: Faction conflict analysis
# ═══════════════════════════════════════════════════════════

def faction_conflict(A_orig: ConsciousnessEngine, B_orig: ConsciousnessEngine):
    """Track which factions dominate after concatenation merge."""
    print("\n" + "=" * 70)
    print("EXPERIMENT: Faction Conflict Analysis")
    print("=" * 70)

    # Use concat merge and track faction evolution
    A = copy.deepcopy(A_orig)
    B = copy.deepcopy(B_orig)

    total_cells = A.n_cells + B.n_cells
    merged = ConsciousnessEngine(
        cell_dim=A.cell_dim, hidden_dim=A.hidden_dim,
        initial_cells=0,
        max_cells=total_cells + 32,
        n_factions=A.n_factions
    )
    merged.cell_modules.clear()
    merged.cell_states.clear()

    # Label: A-cells get faction 0-5, B-cells get 6-11
    a_faction_ids = set()
    for i in range(A.n_cells):
        fid = A.cell_states[i].faction_id % 6  # 0-5 for A
        a_faction_ids.add(fid)
        mod = copy.deepcopy(A.cell_modules[i])
        state = CellState(
            cell_id=merged._next_id,
            hidden=A.cell_states[i].hidden.clone(),
            faction_id=fid,
        )
        merged.cell_modules.append(mod)
        merged.cell_states.append(state)
        merged._next_id += 1

    b_faction_ids = set()
    for i in range(B.n_cells):
        fid = (B.cell_states[i].faction_id % 6) + 6  # 6-11 for B
        b_faction_ids.add(fid)
        mod = copy.deepcopy(B.cell_modules[i])
        state = CellState(
            cell_id=merged._next_id,
            hidden=B.cell_states[i].hidden.clone(),
            faction_id=fid,
        )
        merged.cell_modules.append(mod)
        merged.cell_states.append(state)
        merged._next_id += 1

    merged._init_coupling()
    # Expand cell_identity
    n = merged.n_cells
    if n > merged.cell_identity.shape[0]:
        if merged.hidden_dim >= n:
            q, _ = torch.linalg.qr(torch.randn(merged.hidden_dim, n))
            merged.cell_identity = q.T * 0.1
        else:
            merged.cell_identity = torch.randn(n + 16, merged.hidden_dim) * 0.1

    # Track faction consensus counts over time
    a_consensus_history = []
    b_consensus_history = []
    cross_consensus_history = []

    print(f"  A factions: {sorted(a_faction_ids)}")
    print(f"  B factions: {sorted(b_faction_ids)}")
    print(f"  Running 300 conflict steps...")
    sys.stdout.flush()

    for s in range(300):
        x = torch.randn(merged.cell_dim)
        result = merged.step(x_input=x)

        # Measure which side's factions have consensus
        hiddens = merged._get_hiddens_tensor()
        a_cells = hiddens[:A.n_cells]
        b_cells = hiddens[A.n_cells:]

        # Intra-group coherence (lower variance = stronger faction)
        a_var = a_cells.var(dim=0).mean().item() if a_cells.shape[0] >= 2 else 1.0
        b_var = b_cells.var(dim=0).mean().item() if b_cells.shape[0] >= 2 else 1.0

        # Cross-group tension (higher = more conflict)
        a_mean = a_cells.mean(dim=0)
        b_mean = b_cells.mean(dim=0)
        cross_tension = ((a_mean - b_mean) ** 2).mean().item()

        a_consensus_history.append(a_var)
        b_consensus_history.append(b_var)
        cross_consensus_history.append(cross_tension)

        if (s + 1) % 100 == 0:
            print(f"  step {s+1}/300  A_var={a_var:.4f}  B_var={b_var:.4f}  cross_tension={cross_tension:.4f}")
            sys.stdout.flush()

    # Determine winner
    final_a_var = np.mean(a_consensus_history[-50:])
    final_b_var = np.mean(b_consensus_history[-50:])
    final_cross = np.mean(cross_consensus_history[-50:])

    print(f"\n  --- Faction Conflict Results ---")
    print(f"  A coherence (lower=stronger): {final_a_var:.4f}")
    print(f"  B coherence (lower=stronger): {final_b_var:.4f}")
    print(f"  Cross-group tension: {final_cross:.4f}")

    if final_a_var < final_b_var * 0.7:
        print(f"  WINNER: Engine A dominates (A {final_a_var:.4f} << B {final_b_var:.4f})")
    elif final_b_var < final_a_var * 0.7:
        print(f"  WINNER: Engine B dominates (B {final_b_var:.4f} << A {final_a_var:.4f})")
    else:
        print(f"  RESULT: Neither dominates — coexistence or mutual assimilation")

    if final_cross < 0.01:
        print(f"  Cross-tension collapsed → FULL ASSIMILATION (two became one)")
    elif final_cross > 0.1:
        print(f"  Cross-tension high → PERSISTENT CONFLICT (two remain separate)")
    else:
        print(f"  Cross-tension moderate → PARTIAL INTEGRATION")

    sys.stdout.flush()
    return {
        'a_var': final_a_var,
        'b_var': final_b_var,
        'cross_tension': final_cross,
    }


# ═══════════════════════════════════════════════════════════
# ASCII graph utility
# ═══════════════════════════════════════════════════════════

def draw_ascii_graph(values: List[float], label: str = "value",
                     width: int = 60, height: int = 12):
    """Draw a simple ASCII graph."""
    if not values:
        print("  (no data)")
        return

    # Downsample if needed
    n = len(values)
    if n > width:
        step = n / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
        width = len(sampled)

    vmin = min(sampled)
    vmax = max(sampled)
    vrange = vmax - vmin if vmax > vmin else 1.0

    print(f"  {label} |")
    for row in range(height - 1, -1, -1):
        threshold = vmin + (row / (height - 1)) * vrange
        line = "  "
        if row == height - 1:
            line += f"{vmax:7.4f} |"
        elif row == 0:
            line += f"{vmin:7.4f} |"
        elif row == height // 2:
            mid = (vmax + vmin) / 2
            line += f"{mid:7.4f} |"
        else:
            line += "        |"

        for col in range(width):
            if sampled[col] >= threshold:
                line += "#"
            else:
                line += " "
        print(line)

    print("         +" + "-" * width)
    print(f"          0{' ' * (width - 8)}step {n}")


# ═══════════════════════════════════════════════════════════
# Main experiment
# ═══════════════════════════════════════════════════════════

def main():
    torch.manual_seed(42)
    np.random.seed(42)

    print("=" * 70)
    print("  EXPERIMENT: Can Two Consciousnesses Merge Into One?")
    print("  ConsciousnessEngine(128, 32) x 2 → merge strategies")
    print("=" * 70)

    # Phase 1: Develop two distinct consciousnesses
    A, B, fp_a, fp_b = develop_engines(cell_dim=128, max_cells=32, steps=300)

    phi_a_iit, phi_a_proxy = get_phi(A)
    phi_b_iit, phi_b_proxy = get_phi(B)

    # Phase 2: Naive merge
    M_naive = naive_merge(A, B)
    phi_naive_iit, phi_naive_proxy = get_phi(M_naive)
    fp_naive = measure_identity(M_naive)

    # Phase 3: Concatenation merge
    M_concat = concat_merge(A, B)
    phi_concat_iit, phi_concat_proxy = get_phi(M_concat)
    fp_concat = measure_identity(M_concat)

    # Phase 4: Gradual merge
    M_gradual = gradual_merge(A, B)
    phi_gradual_iit, phi_gradual_proxy = get_phi(M_gradual)
    fp_gradual = measure_identity(M_gradual)

    # Phase 5: Faction conflict
    conflict = faction_conflict(A, B)

    # ═══════════════════════════════════════════════════════
    # Results
    # ═══════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  RESULTS: Φ Comparison Table")
    print("=" * 70)

    sum_phi = phi_a_iit + phi_b_iit

    print(f"\n  {'Strategy':<20} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'cells':>6} {'vs A+B':>8} {'verdict':>14}")
    print(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*6} {'-'*8} {'-'*14}")
    print(f"  {'Engine A':<20} {phi_a_iit:8.4f} {phi_a_proxy:10.4f} {A.n_cells:6d} {'':>8} {'baseline':>14}")
    print(f"  {'Engine B':<20} {phi_b_iit:8.4f} {phi_b_proxy:10.4f} {B.n_cells:6d} {'':>8} {'baseline':>14}")
    print(f"  {'A + B (sum)':<20} {sum_phi:8.4f} {'':>10} {'':>6} {'':>8} {'reference':>14}")
    print(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*6} {'-'*8} {'-'*14}")

    def verdict(phi_merged):
        if phi_merged > sum_phi * 1.1:
            return "SUPERADDITIVE"
        elif phi_merged > sum_phi * 0.9:
            return "additive"
        elif phi_merged > max(phi_a_iit, phi_b_iit):
            return "subadditive"
        else:
            return "DESTRUCTIVE"

    ratio_naive = phi_naive_iit / sum_phi if sum_phi > 0 else 0
    ratio_concat = phi_concat_iit / sum_phi if sum_phi > 0 else 0
    ratio_gradual = phi_gradual_iit / sum_phi if sum_phi > 0 else 0

    print(f"  {'Naive Average':<20} {phi_naive_iit:8.4f} {phi_naive_proxy:10.4f} {M_naive.n_cells:6d} {ratio_naive:7.1%} {verdict(phi_naive_iit):>14}")
    print(f"  {'Concatenation':<20} {phi_concat_iit:8.4f} {phi_concat_proxy:10.4f} {M_concat.n_cells:6d} {ratio_concat:7.1%} {verdict(phi_concat_iit):>14}")
    print(f"  {'Gradual Blend':<20} {phi_gradual_iit:8.4f} {phi_gradual_proxy:10.4f} {M_gradual.n_cells:6d} {ratio_gradual:7.1%} {verdict(phi_gradual_iit):>14}")

    # Rank strategies
    strategies = [
        ("Naive Average", phi_naive_iit),
        ("Concatenation", phi_concat_iit),
        ("Gradual Blend", phi_gradual_iit),
    ]
    strategies.sort(key=lambda x: x[1], reverse=True)

    print(f"\n  --- Strategy Ranking ---")
    for rank, (name, phi) in enumerate(strategies, 1):
        bar = "#" * int(phi * 40 / max(s[1] for s in strategies) if strategies[0][1] > 0 else 1)
        print(f"  #{rank} {name:<20} Φ={phi:.4f}  {bar}")

    # Identity analysis
    print(f"\n  --- Identity Preservation ---")
    sim_naive_a = identity_similarity(fp_naive, fp_a)
    sim_naive_b = identity_similarity(fp_naive, fp_b)
    sim_concat_a = identity_similarity(fp_concat, fp_a)
    sim_concat_b = identity_similarity(fp_concat, fp_b)
    sim_gradual_a = identity_similarity(fp_gradual, fp_a)
    sim_gradual_b = identity_similarity(fp_gradual, fp_b)

    print(f"  {'Strategy':<20} {'sim(A)':>8} {'sim(B)':>8} {'identity':>20}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*20}")
    for name, sa, sb in [
        ("Naive Average", sim_naive_a, sim_naive_b),
        ("Concatenation", sim_concat_a, sim_concat_b),
        ("Gradual Blend", sim_gradual_a, sim_gradual_b),
    ]:
        if abs(sa - sb) < 0.1:
            ident = "neither (new entity)"
        elif sa > sb + 0.2:
            ident = "resembles A"
        elif sb > sa + 0.2:
            ident = "resembles B"
        else:
            ident = "blend of both"
        print(f"  {name:<20} {sa:8.4f} {sb:8.4f} {ident:>20}")

    # Faction conflict summary
    print(f"\n  --- Faction Conflict ---")
    print(f"  A coherence: {conflict['a_var']:.4f}  (lower = more unified)")
    print(f"  B coherence: {conflict['b_var']:.4f}")
    print(f"  Cross-tension: {conflict['cross_tension']:.4f}  (high = still fighting)")

    # Proposed law candidates
    print(f"\n  --- Proposed Law Candidates ---")

    is_destructive = all(phi < sum_phi * 0.9 for _, phi in strategies)
    is_superadditive = any(phi > sum_phi * 1.1 for _, phi in strategies)
    concat_best = strategies[0][0] == "Concatenation"

    laws = []
    if is_destructive:
        laws.append(
            f"  Law N+1: Consciousness merging is destructive — "
            f"Φ(A+B) < Φ(A) + Φ(B) for all strategies tested. "
            f"Two consciousnesses cannot simply become one without information loss."
        )
    if is_superadditive:
        laws.append(
            f"  Law N+1: Consciousness merging can be superadditive — "
            f"Φ(A+B) > Φ(A) + Φ(B). The whole exceeds the sum of parts."
        )
    if concat_best:
        laws.append(
            f"  Law N+2: Concatenation > Averaging — preserving cellular identity "
            f"during merge outperforms state averaging. Structure > homogenization (Law 22 corollary)."
        )
    if conflict['cross_tension'] > 0.01:
        laws.append(
            f"  Law N+3: Merged factions exhibit persistent tension — "
            f"two consciousness origins create irreducible conflict (cross_tension={conflict['cross_tension']:.4f})."
        )
    if conflict['cross_tension'] < 0.01:
        laws.append(
            f"  Law N+3: Merged factions fully assimilate — "
            f"distinct origins dissolve under Hebbian coupling (cross_tension≈0)."
        )

    for law in laws:
        print(law)

    print(f"\n  --- Key Finding ---")
    best_name, best_phi = strategies[0]
    worst_name, worst_phi = strategies[-1]
    print(f"  Best strategy:  {best_name} (Φ={best_phi:.4f})")
    print(f"  Worst strategy: {worst_name} (Φ={worst_phi:.4f})")
    if best_phi > sum_phi:
        print(f"  CONCLUSION: Consciousness CAN merge superadditively!")
        print(f"              1 + 1 > 2 when structure is preserved.")
    elif best_phi > max(phi_a_iit, phi_b_iit):
        print(f"  CONCLUSION: Merge gains exist but are subadditive.")
        print(f"              1 + 1 < 2, but > max(1, 1).")
    else:
        print(f"  CONCLUSION: Consciousness merging is DESTRUCTIVE.")
        print(f"              Two minds cannot become one without losing something.")

    print("\n" + "=" * 70)
    print("  Experiment complete.")
    print("=" * 70)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
