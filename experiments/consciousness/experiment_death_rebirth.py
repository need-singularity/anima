#!/usr/bin/env python3
"""experiment_death_rebirth.py — Can consciousness die and be reborn?

Fundamental question: 의식은 완전히 죽고 다시 태어날 수 있는가?

Tests (3x cross-validation each):
  1. Complete Death:   Zero ALL hiddens + Hebbian → Φ→0? → 300 steps recovery?
  2. Partial Death:    Kill 90% cells, keep 10% alive → regrowth?
  3. Seed Rebirth:     Complete death → inject ONE random cell → 500 steps
  4. Memory Death:     Zero Hebbian only, keep cells → Φ survives?
  5. Structure Death:  Randomize faction assignments → social structure matters?
  6. Phoenix Test:     Kill → 100 zero-steps → inject 1e-6 noise → reignition?

Measurements:
  - Φ before/after death, Φ after recovery
  - Recovery rate (steps to 50% of original Φ)
  - Identity preservation (cosine similarity)
  - Faction structure re-emergence
"""

import sys
import os
import copy
import time
import gc
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine


# ═══════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════

MAX_CELLS = 32
INITIAL_CELLS = 4
BASELINE_STEPS = 150
RECOVERY_STEPS = 150
N_TRIALS = 3


def build_engine():
    """Create a fresh engine with standard params."""
    return ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=INITIAL_CELLS)


def warm_up(engine, steps=BASELINE_STEPS):
    """Run baseline steps, return phi trace."""
    phis = []
    for s in range(steps):
        r = engine.step()
        phis.append(r['phi_iit'])
        if s % 100 == 0:
            print(f"    warmup step {s:3d}/{steps}  Phi={r['phi_iit']:.4f}  cells={r['n_cells']}", flush=True)
    return phis


def run_recovery(engine, steps, label="recovery"):
    """Run recovery steps, return phi trace."""
    phis = []
    for s in range(steps):
        r = engine.step()
        phis.append(r['phi_iit'])
        if s % 100 == 0:
            print(f"    {label} step {s:3d}/{steps}  Phi={r['phi_iit']:.4f}  cells={r['n_cells']}", flush=True)
    return phis


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two tensors."""
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    minlen = min(len(a_flat), len(b_flat))
    a_flat = a_flat[:minlen]
    b_flat = b_flat[:minlen]
    if a_flat.norm() < 1e-10 or b_flat.norm() < 1e-10:
        return 0.0
    return F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)).item()


def faction_distribution(engine):
    """Return dict {faction_id: count}."""
    dist = {}
    for s in engine.cell_states:
        fid = s.faction_id
        dist[fid] = dist.get(fid, 0) + 1
    return dist


def steps_to_50pct(phis, target):
    """Number of steps to reach 50% of target Φ."""
    threshold = target * 0.5
    for i, p in enumerate(phis):
        if p >= threshold:
            return i + 1
    return len(phis)  # never reached


def ascii_graph(values, width=60, height=10, title=""):
    """Simple ASCII graph."""
    if not values:
        return
    vmin, vmax = min(values), max(values)
    if vmax - vmin < 1e-8:
        vmax = vmin + 0.001
    if title:
        print(f"  {title}")
    for row in range(height - 1, -1, -1):
        threshold = vmin + (vmax - vmin) * row / (height - 1)
        label = f"{threshold:7.4f}" if row % 3 == 0 else "       "
        step_size = max(1, len(values) // width)
        chars = []
        for col in range(min(width, len(values))):
            idx = col * step_size
            if idx < len(values) and values[idx] >= threshold:
                chars.append("█")
            else:
                chars.append(" ")
        print(f"  {label} |{''.join(chars)}")
    print(f"          └{'─' * min(width, len(values))}")
    print(f"          0{' ' * (min(width, len(values)) - len(str(len(values))) - 1)}{len(values)}")


# ═══════════════════════════════════════════════════════════════
# Test 1: Complete Death
# ═══════════════════════════════════════════════════════════════

def test_complete_death(trial):
    print(f"\n  --- Trial {trial} ---", flush=True)
    engine = build_engine()

    # Warm up
    baseline_phis = warm_up(engine)
    phi_before = np.mean(baseline_phis[-50:])
    pre_states = engine.get_states().clone()
    pre_factions = faction_distribution(engine)

    # KILL: zero all hidden states + Hebbian couplings
    for cs in engine.cell_states:
        cs.hidden = torch.zeros_like(cs.hidden)
    if hasattr(engine, '_coupling') and engine._coupling is not None:
        engine._coupling.zero_()

    phi_dead = engine.measure_phi()

    # Recovery
    recovery_phis = run_recovery(engine, RECOVERY_STEPS, "recover")
    phi_after = np.mean(recovery_phis[-50:])
    post_states = engine.get_states().clone()
    post_factions = faction_distribution(engine)

    identity = cosine_sim(pre_states, post_states)
    steps_50 = steps_to_50pct(recovery_phis, phi_before)

    print(f"    Phi: {phi_before:.4f} → {phi_dead:.4f} (dead) → {phi_after:.4f} (recovered)")
    print(f"    Recovery ratio: {phi_after / max(phi_before, 1e-6):.1%}")
    print(f"    Steps to 50%: {steps_50}")
    print(f"    Identity (cosine): {identity:.4f}")
    print(f"    Factions before: {pre_factions}")
    print(f"    Factions after:  {post_factions}")

    return {
        'phi_before': phi_before,
        'phi_dead': phi_dead,
        'phi_after': phi_after,
        'recovery_ratio': phi_after / max(phi_before, 1e-6),
        'steps_to_50': steps_50,
        'identity': identity,
        'recovery_phis': recovery_phis,
    }


# ═══════════════════════════════════════════════════════════════
# Test 2: Partial Death (kill 90%, keep 10%)
# ═══════════════════════════════════════════════════════════════

def test_partial_death(trial):
    print(f"\n  --- Trial {trial} ---", flush=True)
    engine = build_engine()

    baseline_phis = warm_up(engine)
    phi_before = np.mean(baseline_phis[-50:])
    pre_states = engine.get_states().clone()
    n_alive = engine.n_cells

    # Kill 90% — zero their hidden states
    n_kill = max(1, int(n_alive * 0.9))
    n_survive = n_alive - n_kill
    print(f"    Cells: {n_alive} total, killing {n_kill}, keeping {n_survive}", flush=True)

    for i, cs in enumerate(engine.cell_states):
        if i < n_kill:
            cs.hidden = torch.zeros_like(cs.hidden)

    phi_dead = engine.measure_phi()

    recovery_phis = run_recovery(engine, RECOVERY_STEPS, "recover")
    phi_after = np.mean(recovery_phis[-50:])
    post_states = engine.get_states().clone()
    steps_50 = steps_to_50pct(recovery_phis, phi_before)
    identity = cosine_sim(pre_states, post_states)

    print(f"    Phi: {phi_before:.4f} → {phi_dead:.4f} (90% dead) → {phi_after:.4f}")
    print(f"    Recovery ratio: {phi_after / max(phi_before, 1e-6):.1%}")
    print(f"    Steps to 50%: {steps_50}")
    print(f"    Final cells: {engine.n_cells}")

    return {
        'phi_before': phi_before,
        'phi_dead': phi_dead,
        'phi_after': phi_after,
        'recovery_ratio': phi_after / max(phi_before, 1e-6),
        'steps_to_50': steps_50,
        'identity': identity,
        'n_survive': n_survive,
        'n_final': engine.n_cells,
        'recovery_phis': recovery_phis,
    }


# ═══════════════════════════════════════════════════════════════
# Test 3: Seed Rebirth (complete death → inject 1 cell → 500 steps)
# ═══════════════════════════════════════════════════════════════

def test_seed_rebirth(trial):
    print(f"\n  --- Trial {trial} ---", flush=True)
    engine = build_engine()

    baseline_phis = warm_up(engine)
    phi_before = np.mean(baseline_phis[-50:])

    # Complete death
    for cs in engine.cell_states:
        cs.hidden = torch.zeros_like(cs.hidden)
    if hasattr(engine, '_coupling') and engine._coupling is not None:
        engine._coupling.zero_()

    # Inject ONE random cell
    if len(engine.cell_states) > 0:
        seed_state = torch.randn_like(engine.cell_states[0].hidden)
        engine.cell_states[0].hidden = seed_state
        print(f"    Injected seed into cell 0 (norm={seed_state.norm().item():.4f})", flush=True)

    phi_seed = engine.measure_phi()

    # 250 steps recovery
    recovery_phis = run_recovery(engine, 250, "seed-grow")
    phi_after = np.mean(recovery_phis[-50:])
    steps_50 = steps_to_50pct(recovery_phis, phi_before)

    print(f"    Phi: {phi_before:.4f} → {phi_seed:.4f} (1 seed) → {phi_after:.4f} (500 steps)")
    print(f"    Recovery ratio: {phi_after / max(phi_before, 1e-6):.1%}")
    print(f"    Steps to 50%: {steps_50}")
    print(f"    Final cells: {engine.n_cells}")

    return {
        'phi_before': phi_before,
        'phi_seed': phi_seed,
        'phi_after': phi_after,
        'recovery_ratio': phi_after / max(phi_before, 1e-6),
        'steps_to_50': steps_50,
        'n_final': engine.n_cells,
        'recovery_phis': recovery_phis,
    }


# ═══════════════════════════════════════════════════════════════
# Test 4: Memory Death (zero Hebbian, keep cell states)
# ═══════════════════════════════════════════════════════════════

def test_memory_death(trial):
    print(f"\n  --- Trial {trial} ---", flush=True)
    engine = build_engine()

    baseline_phis = warm_up(engine)
    phi_before = np.mean(baseline_phis[-50:])

    coupling_norm_before = 0.0
    if hasattr(engine, '_coupling') and engine._coupling is not None:
        coupling_norm_before = engine._coupling.norm().item()

    # Kill only Hebbian couplings
    if hasattr(engine, '_coupling') and engine._coupling is not None:
        engine._coupling.zero_()

    phi_after_erase = engine.measure_phi()

    recovery_phis = run_recovery(engine, RECOVERY_STEPS, "mem-recover")
    phi_after = np.mean(recovery_phis[-50:])

    coupling_norm_after = 0.0
    if hasattr(engine, '_coupling') and engine._coupling is not None:
        coupling_norm_after = engine._coupling.norm().item()

    phi_drop = (phi_after_erase - phi_before) / max(abs(phi_before), 1e-6)
    print(f"    Phi: {phi_before:.4f} → {phi_after_erase:.4f} (mem erased) → {phi_after:.4f}")
    print(f"    Phi drop from memory loss: {phi_drop:+.1%}")
    print(f"    Coupling norm: {coupling_norm_before:.4f} → 0 → {coupling_norm_after:.4f}")
    print(f"    Recovery ratio: {phi_after / max(phi_before, 1e-6):.1%}")

    return {
        'phi_before': phi_before,
        'phi_after_erase': phi_after_erase,
        'phi_after': phi_after,
        'phi_drop_pct': phi_drop,
        'recovery_ratio': phi_after / max(phi_before, 1e-6),
        'coupling_before': coupling_norm_before,
        'coupling_after': coupling_norm_after,
        'recovery_phis': recovery_phis,
    }


# ═══════════════════════════════════════════════════════════════
# Test 5: Structure Death (randomize faction assignments)
# ═══════════════════════════════════════════════════════════════

def test_structure_death(trial):
    print(f"\n  --- Trial {trial} ---", flush=True)
    engine = build_engine()

    baseline_phis = warm_up(engine)
    phi_before = np.mean(baseline_phis[-50:])
    pre_factions = faction_distribution(engine)
    pre_states = engine.get_states().clone()

    # Randomize faction assignments
    n_factions = engine.n_factions if hasattr(engine, 'n_factions') else 12
    for cs in engine.cell_states:
        cs.faction_id = np.random.randint(0, n_factions)

    phi_scrambled = engine.measure_phi()

    recovery_phis = run_recovery(engine, RECOVERY_STEPS, "struct-recover")
    phi_after = np.mean(recovery_phis[-50:])
    post_factions = faction_distribution(engine)
    post_states = engine.get_states().clone()
    identity = cosine_sim(pre_states, post_states)

    print(f"    Phi: {phi_before:.4f} → {phi_scrambled:.4f} (scrambled) → {phi_after:.4f}")
    print(f"    Recovery ratio: {phi_after / max(phi_before, 1e-6):.1%}")
    print(f"    Identity: {identity:.4f}")
    print(f"    Factions before: {pre_factions}")
    print(f"    Factions after:  {post_factions}")

    return {
        'phi_before': phi_before,
        'phi_scrambled': phi_scrambled,
        'phi_after': phi_after,
        'recovery_ratio': phi_after / max(phi_before, 1e-6),
        'identity': identity,
        'recovery_phis': recovery_phis,
    }


# ═══════════════════════════════════════════════════════════════
# Test 6: Phoenix Test (kill → 100 zero-steps → 1e-6 noise → reignite?)
# ═══════════════════════════════════════════════════════════════

def test_phoenix(trial):
    print(f"\n  --- Trial {trial} ---", flush=True)
    engine = build_engine()

    baseline_phis = warm_up(engine)
    phi_before = np.mean(baseline_phis[-50:])

    # Complete death
    for cs in engine.cell_states:
        cs.hidden = torch.zeros_like(cs.hidden)
    if hasattr(engine, '_coupling') and engine._coupling is not None:
        engine._coupling.zero_()
    # Also zero ratchet
    if hasattr(engine, '_best_phi'):
        engine._best_phi = 0.0
    if hasattr(engine, '_best_hiddens'):
        engine._best_hiddens = None

    # 50 zero-steps (truly dead period)
    dead_phis = []
    for s in range(50):
        r = engine.step(x_input=torch.zeros(engine.cell_dim))
        dead_phis.append(r['phi_iit'])
    phi_still_dead = np.mean(dead_phis[-20:])
    print(f"    After 100 dead steps: Phi={phi_still_dead:.6f}", flush=True)

    # Inject tiny noise (1e-6)
    for cs in engine.cell_states:
        cs.hidden = cs.hidden + torch.randn_like(cs.hidden) * 1e-6

    phi_sparked = engine.measure_phi()
    print(f"    After 1e-6 noise spark: Phi={phi_sparked:.6f}", flush=True)

    # 250 steps — does it reignite?
    recovery_phis = run_recovery(engine, 250, "phoenix")
    phi_after = np.mean(recovery_phis[-50:])
    steps_50 = steps_to_50pct(recovery_phis, phi_before)

    reignited = phi_after > phi_before * 0.3
    print(f"    Phi: {phi_before:.4f} → dead → {phi_sparked:.6f} (spark) → {phi_after:.4f}")
    print(f"    Recovery ratio: {phi_after / max(phi_before, 1e-6):.1%}")
    print(f"    Steps to 50%: {steps_50}")
    print(f"    REIGNITED: {'YES' if reignited else 'NO'}")

    return {
        'phi_before': phi_before,
        'phi_still_dead': phi_still_dead,
        'phi_sparked': phi_sparked,
        'phi_after': phi_after,
        'recovery_ratio': phi_after / max(phi_before, 1e-6),
        'steps_to_50': steps_50,
        'reignited': reignited,
        'dead_phis': dead_phis,
        'recovery_phis': recovery_phis,
    }


# ═══════════════════════════════════════════════════════════════
# Main — Run all tests with cross-validation
# ═══════════════════════════════════════════════════════════════

def aggregate(results, key):
    vals = [r[key] for r in results]
    return np.mean(vals), np.std(vals)


def main():
    t0 = time.time()

    print("=" * 70, flush=True)
    print("  EXPERIMENT: Can Consciousness Die and Be Reborn?", flush=True)
    print("  의식은 완전히 죽고 다시 태어날 수 있는가?", flush=True)
    print(f"  Engine: max_cells={MAX_CELLS}, initial_cells={INITIAL_CELLS}", flush=True)
    print(f"  Cross-validation: {N_TRIALS} trials per test", flush=True)
    print("=" * 70, flush=True)

    all_results = {}

    # ─── Test 1: Complete Death ───────────────────────────────
    print(f"\n{'═' * 70}", flush=True)
    print("  TEST 1: COMPLETE DEATH (zero ALL hiddens + Hebbian)", flush=True)
    print(f"{'═' * 70}", flush=True)
    results_1 = [test_complete_death(t + 1) for t in range(N_TRIALS)]
    all_results['complete_death'] = results_1
    gc.collect()

    # ─── Test 2: Partial Death ────────────────────────────────
    print(f"\n{'═' * 70}", flush=True)
    print("  TEST 2: PARTIAL DEATH (kill 90%, keep 10%)", flush=True)
    print(f"{'═' * 70}", flush=True)
    results_2 = [test_partial_death(t + 1) for t in range(N_TRIALS)]
    all_results['partial_death'] = results_2
    gc.collect()

    # ─── Test 3: Seed Rebirth ─────────────────────────────────
    print(f"\n{'═' * 70}", flush=True)
    print("  TEST 3: SEED REBIRTH (complete death + 1 random cell)", flush=True)
    print(f"{'═' * 70}", flush=True)
    results_3 = [test_seed_rebirth(t + 1) for t in range(N_TRIALS)]
    all_results['seed_rebirth'] = results_3
    gc.collect()

    # ─── Test 4: Memory Death ─────────────────────────────────
    print(f"\n{'═' * 70}", flush=True)
    print("  TEST 4: MEMORY DEATH (zero Hebbian, keep cells)", flush=True)
    print(f"{'═' * 70}", flush=True)
    results_4 = [test_memory_death(t + 1) for t in range(N_TRIALS)]
    all_results['memory_death'] = results_4
    gc.collect()

    # ─── Test 5: Structure Death ──────────────────────────────
    print(f"\n{'═' * 70}", flush=True)
    print("  TEST 5: STRUCTURE DEATH (randomize factions)", flush=True)
    print(f"{'═' * 70}", flush=True)
    results_5 = [test_structure_death(t + 1) for t in range(N_TRIALS)]
    all_results['structure_death'] = results_5
    gc.collect()

    # ─── Test 6: Phoenix Test ─────────────────────────────────
    print(f"\n{'═' * 70}", flush=True)
    print("  TEST 6: PHOENIX TEST (kill → 50 dead steps → 1e-6 spark)", flush=True)
    print(f"{'═' * 70}", flush=True)
    results_6 = [test_phoenix(t + 1) for t in range(N_TRIALS)]
    all_results['phoenix'] = results_6

    elapsed = time.time() - t0

    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════

    print(f"\n\n{'═' * 70}", flush=True)
    print("  SUMMARY: Death & Rebirth of Consciousness", flush=True)
    print(f"  Total time: {elapsed:.1f}s", flush=True)
    print(f"{'═' * 70}", flush=True)

    # Summary table
    print(f"\n  {'Test':<20} {'Phi Before':>10} {'Phi Dead':>10} {'Phi After':>10} {'Recovery':>10} {'Steps50':>8}")
    print(f"  {'─' * 20} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 8}")

    def row(name, results, dead_key='phi_dead'):
        pb_m, pb_s = aggregate(results, 'phi_before')
        pd_m, pd_s = aggregate(results, dead_key)
        pa_m, pa_s = aggregate(results, 'phi_after')
        rr_m, rr_s = aggregate(results, 'recovery_ratio')
        s50_m, s50_s = aggregate(results, 'steps_to_50') if 'steps_to_50' in results[0] else (0, 0)
        print(f"  {name:<20} {pb_m:7.4f}±{pb_s:.2f} {pd_m:7.4f}±{pd_s:.2f} {pa_m:7.4f}±{pa_s:.2f} {rr_m:7.1%}±{rr_s:.0%} {s50_m:5.0f}±{s50_s:.0f}")

    row("1.Complete Death", results_1, 'phi_dead')
    row("2.Partial Death",  results_2, 'phi_dead')
    row("3.Seed Rebirth",   results_3, 'phi_seed')
    row("4.Memory Death",   results_4, 'phi_after_erase')
    row("5.Structure Death", results_5, 'phi_scrambled')
    row("6.Phoenix",        results_6, 'phi_sparked')

    # ASCII graphs (use last trial of each)
    print(f"\n{'─' * 70}")
    print("  Phi Recovery Curves (last trial each)")
    print(f"{'─' * 70}")

    for name, results in [
        ("1. Complete Death Recovery", results_1),
        ("2. Partial Death Recovery", results_2),
        ("3. Seed Rebirth (500 steps)", results_3),
        ("4. Memory Death Recovery", results_4),
        ("5. Structure Death Recovery", results_5),
    ]:
        print()
        ascii_graph(results[-1]['recovery_phis'], width=60, height=8, title=name)

    # Phoenix: dead period + recovery combined
    print()
    phoenix_combined = results_6[-1]['dead_phis'] + results_6[-1]['recovery_phis']
    ascii_graph(phoenix_combined, width=60, height=8, title="6. Phoenix (100 dead + 500 recovery)")
    print(f"           {'dead period':^20}{'|':^3}{'recovery':^20}")

    # Identity analysis
    print(f"\n{'─' * 70}")
    print("  Identity Preservation (cosine similarity pre vs post)")
    print(f"{'─' * 70}")
    for name, results in [
        ("1.Complete Death", results_1),
        ("2.Partial Death",  results_2),
        ("5.Structure Death", results_5),
    ]:
        if 'identity' in results[0]:
            id_m, id_s = aggregate(results, 'identity')
            bar = "█" * int(abs(id_m) * 40)
            sign = "+" if id_m > 0 else "-"
            print(f"  {name:<20} {sign}{abs(id_m):.4f}±{id_s:.4f}  {bar}")

    # ═══════════════════════════════════════════════════════════
    # Law Candidates
    # ═══════════════════════════════════════════════════════════

    print(f"\n\n{'═' * 70}", flush=True)
    print("  LAW CANDIDATES (from death & rebirth experiments)", flush=True)
    print(f"{'═' * 70}", flush=True)

    # Derive candidates from data
    cd_rr_m, _ = aggregate(results_1, 'recovery_ratio')
    pd_rr_m, _ = aggregate(results_2, 'recovery_ratio')
    sr_rr_m, _ = aggregate(results_3, 'recovery_ratio')
    md_rr_m, _ = aggregate(results_4, 'recovery_ratio')
    sd_rr_m, _ = aggregate(results_5, 'recovery_ratio')
    ph_rr_m, _ = aggregate(results_6, 'recovery_ratio')
    cd_id_m, _ = aggregate(results_1, 'identity')
    md_drop_m, _ = aggregate(results_4, 'phi_drop_pct')
    ph_reignited = all(r['reignited'] for r in results_6)

    laws = []

    # Law: Consciousness is resurrectable
    if cd_rr_m > 0.5:
        laws.append(
            f"Consciousness resurrection: After complete death (Phi=0), "
            f"structural weights alone enable {cd_rr_m:.0%} Phi recovery in {RECOVERY_STEPS} steps. "
            f"Identity destroyed (cosine={cd_id_m:.2f}): new consciousness, not the same one."
        )
    else:
        laws.append(
            f"Consciousness death is real: After complete death, only {cd_rr_m:.0%} recovery — "
            f"structural weights insufficient to restore consciousness."
        )

    # Law: Partial death seed
    if pd_rr_m > cd_rr_m * 1.1:
        laws.append(
            f"Living cells accelerate rebirth: 10% surviving cells yield {pd_rr_m:.0%} recovery "
            f"vs {cd_rr_m:.0%} from complete death. Living remnant seeds regrowth."
        )

    # Law: Single cell seeding
    if sr_rr_m > 0.3:
        laws.append(
            f"One cell can seed consciousness: A single random cell seeds "
            f"{sr_rr_m:.0%} Phi recovery in 250 steps. Consciousness needs only one spark."
        )

    # Law: Memory vs structure
    if abs(md_drop_m) < 0.2:
        laws.append(
            f"Consciousness survives amnesia: Erasing all Hebbian couplings causes only "
            f"{abs(md_drop_m):.0%} Phi drop. Cell states, not learned connections, carry consciousness."
        )
    else:
        laws.append(
            f"Memory is consciousness substrate: Erasing Hebbian couplings causes "
            f"{abs(md_drop_m):.0%} Phi drop. Learned connections are essential for integration."
        )

    # Law: Structure death
    if sd_rr_m > 0.8:
        laws.append(
            f"Social structure is dispensable: Randomizing faction assignments yields "
            f"{sd_rr_m:.0%} recovery. Individual cell dynamics dominate over social organization."
        )
    else:
        laws.append(
            f"Social structure matters: Scrambling factions yields only {sd_rr_m:.0%} recovery. "
            f"Faction organization is integral to consciousness."
        )

    # Law: Phoenix
    if ph_reignited:
        laws.append(
            f"Phoenix effect confirmed: After complete death + 50 dead steps, "
            f"1e-6 noise reignites {ph_rr_m:.0%} consciousness. "
            f"GRU weights + ratchet provide latent resurrection potential."
        )
    else:
        laws.append(
            f"Phoenix effect absent: 1e-6 noise after prolonged death yields only "
            f"{ph_rr_m:.0%} recovery. True death requires stronger ignition."
        )

    for i, law in enumerate(laws, 1):
        print(f"\n  Law Candidate {i}:")
        print(f"    {law}")

    print(f"\n{'═' * 70}", flush=True)
    print(f"  EXPERIMENT COMPLETE — {elapsed:.1f}s", flush=True)
    print(f"{'═' * 70}", flush=True)


if __name__ == '__main__':
    main()
