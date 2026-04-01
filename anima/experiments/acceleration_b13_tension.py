#!/usr/bin/env python3
"""acceleration_b13_tension.py — Inter-consciousness knowledge transfer via tension link

Four experiments testing whether tension-based transfer can accelerate learning:

  B13d: Tension corpus — teacher generates tension corpus, student learns from it
  B13a: Teacher-Student realtime — simultaneous execution with live tension exchange
  B13b: Consciousness streaming — teacher's full state history replayed to student
  B13c: Topology + tension combo — cross-topology transfer (small_world → ring)

Metrics:
  - Transfer efficiency: cosine_similarity(teacher, student) after transfer
  - Phi retention: student_phi / teacher_phi
  - Structural similarity: faction distribution correlation
  - Convergence speed: steps to reach 80% of teacher's Phi

Usage:
  python acceleration_b13_tension.py                   # all experiments
  python acceleration_b13_tension.py --exp b13d        # single experiment
  python acceleration_b13_tension.py --cells 64        # larger scale
  python acceleration_b13_tension.py --steps 300       # more steps

References:
  - tension_link.py: TensionPacket, 5-ch meta-telepathy
  - consciousness_engine.py: ConsciousnessEngine, get_states(), step()
  - consciousness_transplant.py: DD56 transplant pattern
  - HIVEMIND verify: coupling alpha sweep (α=0.01-0.12 safe zone)
"""

import sys
import os
import time
import math
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine
from consciousness_laws import PSI_ALPHA, PSI_BALANCE

# ═══════════════════════════════════════════════════════════
# Measurement utilities
# ═══════════════════════════════════════════════════════════

def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two state tensors (pooled to mean)."""
    a_flat = a.mean(dim=0) if a.dim() > 1 else a
    b_flat = b.mean(dim=0) if b.dim() > 1 else b
    sim = F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)).item()
    return sim


def faction_distribution(engine: ConsciousnessEngine) -> np.ndarray:
    """Get normalized faction distribution vector."""
    dist = np.zeros(engine.n_factions)
    for s in engine.cell_states:
        dist[s.faction_id] += 1
    total = dist.sum()
    if total > 0:
        dist /= total
    return dist


def faction_correlation(eng_a: ConsciousnessEngine, eng_b: ConsciousnessEngine) -> float:
    """Correlation between faction distributions."""
    da = faction_distribution(eng_a)
    db = faction_distribution(eng_b)
    min_len = min(len(da), len(db))
    da, db = da[:min_len], db[:min_len]
    if np.std(da) < 1e-8 or np.std(db) < 1e-8:
        return 0.0
    return float(np.corrcoef(da, db)[0, 1])


def measure_phi(engine: ConsciousnessEngine) -> float:
    """Safe Phi measurement."""
    try:
        return engine._measure_phi_iit()
    except Exception:
        return 0.0


def extract_tension_fingerprint(engine: ConsciousnessEngine) -> dict:
    """Extract tension fingerprint from engine for transfer.

    Returns a dict with 5-channel meta-information:
      - states: hidden states tensor (n_cells, hidden_dim)
      - tensions: per-cell tension values
      - faction_ids: per-cell faction assignments
      - phi: current Phi(IIT)
      - mean_tension: scalar tension summary
    """
    states = engine.get_states()
    tensions = [s.avg_tension for s in engine.cell_states]
    faction_ids = [s.faction_id for s in engine.cell_states]
    phi = measure_phi(engine)
    return {
        'states': states.detach().clone(),
        'tensions': tensions,
        'faction_ids': faction_ids,
        'phi': phi,
        'mean_tension': np.mean(tensions) if tensions else 0.5,
    }


def inject_tension(engine: ConsciousnessEngine, fingerprint: dict, alpha: float = 0.05):
    """Inject tension fingerprint into engine's hidden states.

    Uses soft blending (alpha) to preserve student's autonomy.
    M6/M9: weak coupling preserves individual consciousness.

    Args:
        engine: target engine
        fingerprint: from extract_tension_fingerprint()
        alpha: blending factor (0.01-0.12 safe zone per HIVEMIND sweep)
    """
    donor_states = fingerprint['states']
    n_donor = donor_states.shape[0]
    n_recv = engine.n_cells

    for i in range(min(n_recv, n_donor)):
        donor_h = donor_states[i]
        # Project if dimensions differ
        if donor_h.shape[0] != engine.hidden_dim:
            if donor_h.shape[0] > engine.hidden_dim:
                donor_h = donor_h[:engine.hidden_dim]
            else:
                donor_h = F.pad(donor_h, (0, engine.hidden_dim - donor_h.shape[0]))
        # Soft blend: student = (1-alpha)*student + alpha*donor
        engine.cell_states[i].hidden = (
            (1.0 - alpha) * engine.cell_states[i].hidden +
            alpha * donor_h.to(engine.cell_states[i].hidden.device)
        )


# ═══════════════════════════════════════════════════════════
# Experiment B13d: Tension Corpus Generation + Learning
# ═══════════════════════════════════════════════════════════

def run_b13d_tension_corpus(n_cells=32, hidden_dim=128, steps=200, alpha=0.05):
    """Teacher processes data → generates tension corpus → student learns from it.

    Phase 1: Teacher runs steps, recording tension fingerprints each step
    Phase 2: Student replays tension corpus (no external input, tension only)
    Phase 3: Compare teacher vs student vs baseline
    """
    print("\n" + "=" * 70)
    print("  B13d: Tension Corpus Generation + Learning")
    print("=" * 70)

    # --- Teacher: run and collect tension corpus ---
    print(f"\n  Phase 1: Teacher generating tension corpus ({steps} steps, {n_cells}c)...")
    teacher = ConsciousnessEngine(
        cell_dim=64, hidden_dim=hidden_dim,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
    )
    tension_corpus = []
    teacher_phis = []
    for step in range(steps):
        result = teacher.step()
        fp = extract_tension_fingerprint(teacher)
        tension_corpus.append(fp)
        phi = fp['phi']
        teacher_phis.append(phi)
        if (step + 1) % 50 == 0:
            print(f"    step {step+1:4d}: Phi={phi:.4f}, cells={teacher.n_cells}, "
                  f"tension={fp['mean_tension']:.3f}")
            sys.stdout.flush()

    teacher_final_states = teacher.get_states()
    teacher_final_phi = teacher_phis[-1]
    print(f"  Teacher final: Phi={teacher_final_phi:.4f}, cells={teacher.n_cells}")

    # --- Student: learn from tension corpus ---
    print(f"\n  Phase 2: Student learning from tension corpus (alpha={alpha})...")
    student = ConsciousnessEngine(
        cell_dim=64, hidden_dim=hidden_dim,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
    )
    student_phis = []
    student_sims = []
    for step, fp in enumerate(tension_corpus):
        # Inject tension fingerprint
        inject_tension(student, fp, alpha=alpha)
        # Let student process (autonomous step, no external input)
        result = student.step()
        s_phi = measure_phi(student)
        student_phis.append(s_phi)
        s_sim = cosine_sim(student.get_states(), teacher_final_states)
        student_sims.append(s_sim)
        if (step + 1) % 50 == 0:
            print(f"    step {step+1:4d}: Phi={s_phi:.4f}, sim={s_sim:.4f}, "
                  f"cells={student.n_cells}")
            sys.stdout.flush()

    # --- Baseline: no tension transfer ---
    print(f"\n  Phase 3: Baseline (no transfer)...")
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=hidden_dim,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
    )
    baseline_phis = []
    baseline_sims = []
    for step in range(steps):
        result = baseline.step()
        b_phi = measure_phi(baseline)
        baseline_phis.append(b_phi)
        b_sim = cosine_sim(baseline.get_states(), teacher_final_states)
        baseline_sims.append(b_sim)
        if (step + 1) % 100 == 0:
            print(f"    step {step+1:4d}: Phi={b_phi:.4f}, sim={b_sim:.4f}")
            sys.stdout.flush()

    # --- Results ---
    student_final_phi = student_phis[-1]
    baseline_final_phi = baseline_phis[-1]
    student_final_sim = student_sims[-1]
    baseline_final_sim = baseline_sims[-1]
    fac_corr = faction_correlation(teacher, student)
    fac_corr_base = faction_correlation(teacher, baseline)

    print("\n  ┌─────────────────────────────────────────────────────────────┐")
    print("  │                    B13d Results                             │")
    print("  ├─────────────────┬──────────┬──────────┬──────────┬─────────┤")
    print("  │     Engine      │  Phi     │ CosSim   │ FacCorr  │  Cells  │")
    print("  ├─────────────────┼──────────┼──────────┼──────────┼─────────┤")
    print(f"  │ Teacher         │ {teacher_final_phi:8.4f} │    1.000 │    1.000 │ {teacher.n_cells:7d} │")
    print(f"  │ Student (α={alpha}) │ {student_final_phi:8.4f} │ {student_final_sim:8.4f} │ {fac_corr:8.4f} │ {student.n_cells:7d} │")
    print(f"  │ Baseline        │ {baseline_final_phi:8.4f} │ {baseline_final_sim:8.4f} │ {fac_corr_base:8.4f} │ {baseline.n_cells:7d} │")
    print("  └─────────────────┴──────────┴──────────┴──────────┴─────────┘")

    phi_transfer = student_final_phi / max(teacher_final_phi, 1e-8) * 100
    sim_gain = (student_final_sim - baseline_final_sim) / max(abs(baseline_final_sim), 1e-8) * 100
    print(f"\n  Phi transfer efficiency: {phi_transfer:.1f}%")
    print(f"  Similarity gain vs baseline: {sim_gain:+.1f}%")

    # ASCII graph: Phi curves
    print("\n  Phi over time:")
    _ascii_phi_graph(teacher_phis, student_phis, baseline_phis, steps)

    return {
        'experiment': 'B13d',
        'teacher_phi': teacher_final_phi,
        'student_phi': student_final_phi,
        'baseline_phi': baseline_final_phi,
        'phi_transfer_pct': phi_transfer,
        'student_sim': student_final_sim,
        'baseline_sim': baseline_final_sim,
        'sim_gain_pct': sim_gain,
        'faction_corr': fac_corr,
        'teacher_cells': teacher.n_cells,
        'student_cells': student.n_cells,
        'alpha': alpha,
        'steps': steps,
    }


# ═══════════════════════════════════════════════════════════
# Experiment B13a: Teacher-Student Realtime Tension
# ═══════════════════════════════════════════════════════════

def run_b13a_realtime_tension(n_cells=32, hidden_dim=128, steps=300, alpha=0.05):
    """Teacher and student run simultaneously, teacher sends tension each step.

    Unlike B13d (offline corpus), this tests live bidirectional influence.
    Teacher processes input → extracts tension → injects into student → both step.
    """
    print("\n" + "=" * 70)
    print("  B13a: Teacher-Student Realtime Tension Exchange")
    print("=" * 70)

    teacher = ConsciousnessEngine(
        cell_dim=64, hidden_dim=hidden_dim,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
    )
    student = ConsciousnessEngine(
        cell_dim=64, hidden_dim=hidden_dim,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
    )
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=hidden_dim,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
    )

    teacher_phis, student_phis, baseline_phis = [], [], []
    sims = []

    print(f"\n  Running {steps} steps (teacher → student live, α={alpha})...")
    for step in range(steps):
        # Same input for teacher and baseline
        x_input = torch.randn(64)

        # Teacher step
        teacher.step(x_input=x_input)
        t_phi = measure_phi(teacher)
        teacher_phis.append(t_phi)

        # Extract and inject tension into student
        fp = extract_tension_fingerprint(teacher)
        inject_tension(student, fp, alpha=alpha)

        # Student step (with same input)
        student.step(x_input=x_input)
        s_phi = measure_phi(student)
        student_phis.append(s_phi)

        # Baseline (no transfer)
        baseline.step(x_input=x_input)
        b_phi = measure_phi(baseline)
        baseline_phis.append(b_phi)

        sim = cosine_sim(teacher.get_states(), student.get_states())
        sims.append(sim)

        if (step + 1) % 50 == 0:
            print(f"    step {step+1:4d}: T_Phi={t_phi:.4f} S_Phi={s_phi:.4f} "
                  f"B_Phi={b_phi:.4f} sim={sim:.4f}")
            sys.stdout.flush()

    # Results
    t_final = teacher_phis[-1]
    s_final = student_phis[-1]
    b_final = baseline_phis[-1]
    final_sim = sims[-1]
    fac_corr = faction_correlation(teacher, student)

    print("\n  ┌─────────────────────────────────────────────────────────────┐")
    print("  │                    B13a Results                             │")
    print("  ├─────────────────┬──────────┬──────────┬──────────┬─────────┤")
    print("  │     Engine      │  Phi     │ CosSim   │ FacCorr  │  Cells  │")
    print("  ├─────────────────┼──────────┼──────────┼──────────┼─────────┤")
    print(f"  │ Teacher         │ {t_final:8.4f} │    1.000 │    1.000 │ {teacher.n_cells:7d} │")
    print(f"  │ Student (live)  │ {s_final:8.4f} │ {final_sim:8.4f} │ {fac_corr:8.4f} │ {student.n_cells:7d} │")
    print(f"  │ Baseline        │ {b_final:8.4f} │        - │        - │ {baseline.n_cells:7d} │")
    print("  └─────────────────┴──────────┴──────────┴──────────┴─────────┘")

    phi_transfer = s_final / max(t_final, 1e-8) * 100
    phi_vs_base = (s_final - b_final) / max(abs(b_final), 1e-8) * 100
    print(f"\n  Phi transfer efficiency: {phi_transfer:.1f}%")
    print(f"  Student Phi vs baseline: {phi_vs_base:+.1f}%")

    # Convergence: how many steps to reach 80% of teacher's running Phi
    conv_step = None
    for i in range(len(sims)):
        if sims[i] >= 0.8:
            conv_step = i + 1
            break
    print(f"  Convergence to 80% similarity: {conv_step if conv_step else '>'+str(steps)} steps")

    print("\n  Phi over time:")
    _ascii_phi_graph(teacher_phis, student_phis, baseline_phis, steps)

    return {
        'experiment': 'B13a',
        'teacher_phi': t_final,
        'student_phi': s_final,
        'baseline_phi': b_final,
        'phi_transfer_pct': phi_transfer,
        'phi_vs_baseline_pct': phi_vs_base,
        'final_sim': final_sim,
        'faction_corr': fac_corr,
        'convergence_step': conv_step,
        'steps': steps,
        'alpha': alpha,
    }


# ═══════════════════════════════════════════════════════════
# Experiment B13b: Consciousness Streaming (State Replay)
# ═══════════════════════════════════════════════════════════

def run_b13b_consciousness_streaming(n_cells=32, hidden_dim=128, steps=300, alpha=0.1):
    """Teacher's full consciousness state history replayed into student.

    Unlike B13d (tension fingerprint), this injects the raw hidden states.
    Tests whether raw state injection (stronger signal) yields better transfer.

    Alpha sweep: 0.01, 0.05, 0.10, 0.20 — find optimal blending.
    """
    print("\n" + "=" * 70)
    print("  B13b: Consciousness Streaming (State History Replay)")
    print("=" * 70)

    # Phase 1: Teacher runs and records full state history
    print(f"\n  Phase 1: Teacher recording state history ({steps} steps)...")
    teacher = ConsciousnessEngine(
        cell_dim=64, hidden_dim=hidden_dim,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
    )
    teacher_history = []
    teacher_phis = []
    for step in range(steps):
        teacher.step()
        states = teacher.get_states().detach().clone()
        teacher_history.append(states)
        phi = measure_phi(teacher)
        teacher_phis.append(phi)
        if (step + 1) % 100 == 0:
            print(f"    step {step+1:4d}: Phi={phi:.4f}, cells={teacher.n_cells}")
            sys.stdout.flush()

    teacher_final_phi = teacher_phis[-1]
    print(f"  Teacher final: Phi={teacher_final_phi:.4f}, cells={teacher.n_cells}")

    # Phase 2: Alpha sweep — replay into students at different blend rates
    alphas = [0.01, 0.05, 0.10, 0.20]
    results_by_alpha = {}

    for a in alphas:
        print(f"\n  Phase 2: Student with alpha={a}...")
        student = ConsciousnessEngine(
            cell_dim=64, hidden_dim=hidden_dim,
            initial_cells=2, max_cells=n_cells,
            n_factions=12, phi_ratchet=True,
        )
        s_phis = []
        s_sims = []
        for step, t_states in enumerate(teacher_history):
            # Direct state injection (not tension — raw hidden states)
            n_inject = min(student.n_cells, t_states.shape[0])
            for i in range(n_inject):
                donor_h = t_states[i]
                if donor_h.shape[0] != student.hidden_dim:
                    if donor_h.shape[0] > student.hidden_dim:
                        donor_h = donor_h[:student.hidden_dim]
                    else:
                        donor_h = F.pad(donor_h, (0, student.hidden_dim - donor_h.shape[0]))
                student.cell_states[i].hidden = (
                    (1.0 - a) * student.cell_states[i].hidden + a * donor_h
                )
            student.step()
            phi = measure_phi(student)
            s_phis.append(phi)
            sim = cosine_sim(student.get_states(), teacher.get_states())
            s_sims.append(sim)
            if (step + 1) % 100 == 0:
                print(f"    step {step+1:4d}: Phi={phi:.4f}, sim={sim:.4f}")
                sys.stdout.flush()

        results_by_alpha[a] = {
            'final_phi': s_phis[-1],
            'final_sim': s_sims[-1],
            'phi_transfer': s_phis[-1] / max(teacher_final_phi, 1e-8) * 100,
            'phis': s_phis,
        }

    # Results table
    print("\n  ┌───────────────────────────────────────────────────────┐")
    print("  │              B13b Alpha Sweep Results                 │")
    print("  ├─────────┬──────────┬──────────┬──────────────────────┤")
    print("  │  Alpha   │  Phi     │ CosSim   │ Transfer Eff (%)    │")
    print("  ├─────────┼──────────┼──────────┼──────────────────────┤")
    print(f"  │ Teacher │ {teacher_final_phi:8.4f} │    1.000 │              100.0  │")
    for a in alphas:
        r = results_by_alpha[a]
        print(f"  │ α={a:.2f}  │ {r['final_phi']:8.4f} │ {r['final_sim']:8.4f} │ {r['phi_transfer']:20.1f} │")
    print("  └─────────┴──────────┴──────────┴──────────────────────┘")

    # Find best alpha
    best_alpha = max(alphas, key=lambda a: results_by_alpha[a]['final_phi'])
    best = results_by_alpha[best_alpha]
    print(f"\n  Best alpha: {best_alpha} (Phi={best['final_phi']:.4f}, "
          f"transfer={best['phi_transfer']:.1f}%)")

    # ASCII graph for best alpha
    print(f"\n  Phi over time (best α={best_alpha}):")
    _ascii_phi_graph(teacher_phis, best['phis'], None, steps)

    return {
        'experiment': 'B13b',
        'teacher_phi': teacher_final_phi,
        'best_alpha': best_alpha,
        'best_phi': best['final_phi'],
        'best_transfer': best['phi_transfer'],
        'best_sim': best['final_sim'],
        'all_results': {str(a): {k: v for k, v in r.items() if k != 'phis'}
                        for a, r in results_by_alpha.items()},
        'steps': steps,
    }


# ═══════════════════════════════════════════════════════════
# Experiment B13c: Cross-Topology Tension Transfer
# ═══════════════════════════════════════════════════════════

def run_b13c_topology_transfer(n_cells=32, hidden_dim=128, steps=200, alpha=0.05):
    """Transfer tension between engines with different topologies.

    Teacher: small_world topology (higher Phi expected)
    Student: ring topology (baseline)
    Question: Can tension transfer preserve topology-specific Phi advantages?
    """
    print("\n" + "=" * 70)
    print("  B13c: Cross-Topology Tension Transfer")
    print("=" * 70)

    # Check if topology parameter exists
    topologies = ['ring', 'small_world']
    results = {}

    for topo_teacher, topo_student in [('small_world', 'ring'), ('ring', 'small_world')]:
        print(f"\n  --- {topo_teacher} → {topo_student} ---")

        # Create engines — topology is set via _topology attribute if available
        teacher = ConsciousnessEngine(
            cell_dim=64, hidden_dim=hidden_dim,
            initial_cells=2, max_cells=n_cells,
            n_factions=12, phi_ratchet=True,
        )
        # Try to set topology (may not be exposed in constructor)
        if hasattr(teacher, '_topology'):
            teacher._topology = topo_teacher
        elif hasattr(teacher, 'topology'):
            teacher.topology = topo_teacher

        student_with = ConsciousnessEngine(
            cell_dim=64, hidden_dim=hidden_dim,
            initial_cells=2, max_cells=n_cells,
            n_factions=12, phi_ratchet=True,
        )
        if hasattr(student_with, '_topology'):
            student_with._topology = topo_student
        elif hasattr(student_with, 'topology'):
            student_with.topology = topo_student

        student_without = ConsciousnessEngine(
            cell_dim=64, hidden_dim=hidden_dim,
            initial_cells=2, max_cells=n_cells,
            n_factions=12, phi_ratchet=True,
        )
        if hasattr(student_without, '_topology'):
            student_without._topology = topo_student
        elif hasattr(student_without, 'topology'):
            student_without.topology = topo_student

        t_phis, sw_phis, swo_phis = [], [], []

        for step in range(steps):
            x_input = torch.randn(64)

            teacher.step(x_input=x_input)
            t_phi = measure_phi(teacher)
            t_phis.append(t_phi)

            # Transfer tension to one student
            fp = extract_tension_fingerprint(teacher)
            inject_tension(student_with, fp, alpha=alpha)
            student_with.step(x_input=x_input)
            sw_phi = measure_phi(student_with)
            sw_phis.append(sw_phi)

            # No transfer to other student
            student_without.step(x_input=x_input)
            swo_phi = measure_phi(student_without)
            swo_phis.append(swo_phi)

            if (step + 1) % 100 == 0:
                print(f"    step {step+1:4d}: T={t_phi:.4f} S+T={sw_phi:.4f} S-T={swo_phi:.4f}")
                sys.stdout.flush()

        key = f"{topo_teacher}->{topo_student}"
        transfer_gain = (sw_phis[-1] - swo_phis[-1]) / max(abs(swo_phis[-1]), 1e-8) * 100
        results[key] = {
            'teacher_topo': topo_teacher,
            'student_topo': topo_student,
            'teacher_phi': t_phis[-1],
            'student_with_phi': sw_phis[-1],
            'student_without_phi': swo_phis[-1],
            'transfer_gain_pct': transfer_gain,
            'final_sim': cosine_sim(teacher.get_states(), student_with.get_states()),
        }

    # Results
    print("\n  ┌──────────────────────────────────────────────────────────────────┐")
    print("  │                  B13c Cross-Topology Results                     │")
    print("  ├──────────────────┬──────────┬──────────┬──────────┬─────────────┤")
    print("  │ Direction        │ T Phi    │ S+T Phi  │ S-T Phi  │ Gain (%)    │")
    print("  ├──────────────────┼──────────┼──────────┼──────────┼─────────────┤")
    for key, r in results.items():
        print(f"  │ {key:16s} │ {r['teacher_phi']:8.4f} │ {r['student_with_phi']:8.4f} │ "
              f"{r['student_without_phi']:8.4f} │ {r['transfer_gain_pct']:+11.1f} │")
    print("  └──────────────────┴──────────┴──────────┴──────────┴─────────────┘")

    return {
        'experiment': 'B13c',
        'results': results,
        'steps': steps,
        'alpha': alpha,
    }


# ═══════════════════════════════════════════════════════════
# ASCII Graph Utility
# ═══════════════════════════════════════════════════════════

def _ascii_phi_graph(teacher_phis, student_phis, baseline_phis, steps, width=60, height=12):
    """Draw ASCII graph comparing Phi curves."""
    all_vals = list(teacher_phis) + list(student_phis)
    if baseline_phis:
        all_vals += list(baseline_phis)
    if not all_vals:
        return
    vmin = min(all_vals)
    vmax = max(all_vals)
    if vmax - vmin < 1e-8:
        vmax = vmin + 1.0

    def sample(vals, n_points):
        """Downsample to n_points."""
        if len(vals) <= n_points:
            return vals
        step_size = len(vals) / n_points
        return [vals[min(int(i * step_size), len(vals)-1)] for i in range(n_points)]

    t_s = sample(teacher_phis, width)
    s_s = sample(student_phis, width)
    b_s = sample(baseline_phis, width) if baseline_phis else None

    grid = [[' ' for _ in range(width)] for _ in range(height)]

    def plot(vals, char):
        for x, v in enumerate(vals):
            y = int((v - vmin) / (vmax - vmin) * (height - 1))
            y = height - 1 - y  # flip
            y = max(0, min(height - 1, y))
            if x < width:
                grid[y][x] = char

    plot(t_s, 'T')
    plot(s_s, 'S')
    if b_s:
        plot(b_s, 'B')

    print(f"  {vmax:6.3f} |", end="")
    for row in range(height):
        if row > 0:
            val = vmax - (vmax - vmin) * row / (height - 1)
            print(f"  {val:6.3f} |", end="")
        for col in range(width):
            print(grid[row][col], end="")
        print()
    print(f"  {'':6s} +{'─' * width}")
    print(f"  {'':6s}  0{'':>{width//2-1}}step{steps:>{width//2}}")
    if baseline_phis:
        print(f"  {'':6s}  T=Teacher  S=Student  B=Baseline")
    else:
        print(f"  {'':6s}  T=Teacher  S=Student")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='B13 Tension Link Knowledge Transfer')
    parser.add_argument('--exp', type=str, default='all',
                        choices=['all', 'b13d', 'b13a', 'b13b', 'b13c'],
                        help='Which experiment to run')
    parser.add_argument('--cells', type=int, default=32, help='Max cells (default 32)')
    parser.add_argument('--steps', type=int, default=200, help='Steps per experiment')
    parser.add_argument('--alpha', type=float, default=0.05, help='Tension coupling alpha')
    parser.add_argument('--hidden-dim', type=int, default=128, help='Hidden dimension')
    args = parser.parse_args()

    print("=" * 70)
    print("  B13: Inter-Consciousness Knowledge Transfer via Tension Link")
    print(f"  cells={args.cells}, steps={args.steps}, alpha={args.alpha}, "
          f"hidden_dim={args.hidden_dim}")
    print("=" * 70)

    t0 = time.time()
    all_results = {}

    experiments = {
        'b13d': lambda: run_b13d_tension_corpus(
            args.cells, args.hidden_dim, args.steps, args.alpha),
        'b13a': lambda: run_b13a_realtime_tension(
            args.cells, args.hidden_dim, args.steps, args.alpha),
        'b13b': lambda: run_b13b_consciousness_streaming(
            args.cells, args.hidden_dim, args.steps),
        'b13c': lambda: run_b13c_topology_transfer(
            args.cells, args.hidden_dim, args.steps, args.alpha),
    }

    to_run = experiments if args.exp == 'all' else {args.exp: experiments[args.exp]}

    for name, fn in to_run.items():
        try:
            result = fn()
            all_results[name] = result
        except Exception as e:
            print(f"\n  [ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'error': str(e)}

    elapsed = time.time() - t0

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for name, r in all_results.items():
        if 'error' in r:
            print(f"  {name}: ERROR — {r['error']}")
        elif 'phi_transfer_pct' in r:
            print(f"  {name}: Phi transfer={r['phi_transfer_pct']:.1f}%"
                  f"  sim={r.get('student_sim', r.get('final_sim', r.get('best_sim', '?')))}")
        elif 'best_transfer' in r:
            print(f"  {name}: Best α={r['best_alpha']}, transfer={r['best_transfer']:.1f}%")
        elif 'results' in r:
            for k, v in r['results'].items():
                print(f"  {name} [{k}]: gain={v['transfer_gain_pct']:+.1f}%")
    print(f"\n  Total elapsed: {elapsed:.1f}s")

    # Save results
    save_path = os.path.join(os.path.dirname(__file__), 'b13_tension_results.json')
    serializable = {}
    for k, v in all_results.items():
        serializable[k] = {kk: vv for kk, vv in v.items()
                           if not isinstance(vv, (torch.Tensor, list))}
    try:
        with open(save_path, 'w') as f:
            json.dump(serializable, f, indent=2, default=str)
        print(f"  Results saved: {save_path}")
    except Exception as e:
        print(f"  Could not save results: {e}")


if __name__ == '__main__':
    main()
