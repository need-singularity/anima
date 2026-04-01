#!/usr/bin/env python3
"""acceleration_e6_e10.py — E6-E10 unexplored combination experiments

E6: Tension Distillation + Entropy Surfing
    Teacher generates tension -> student absorbs it while maintaining entropy ~0.998
    B13 catalyst (139%) + C3 entropy (Phi+71.5%) synergy?

E7: Compiler + Straight-Line Jump
    C1 compiler applies laws at once (Phi+87%) -> D1 straight-line jump to 30% of trajectory
    Does compiled high-Phi state improve jump origin?

E8: Hebbian Tension — tension directs Hebbian updates
    B8 Hebbian (pattern distinction +0.81) + B13 tension catalyst (139%)
    Teacher's tension -> guides student's Hebbian coupling direction

E9: Fractal + Transplant Loop (4c -> 16c -> 64c)
    C2 fractal (disappears after 30 steps) + C4 transplant (92% retention)
    Staged growth mimicking brain development

E10: ODE + Skip combination
    C7 Neural ODE (short-term cos=0.37, x16) + B12 Skip (x10)
    Skip intervals interpolated by ODE -> accuracy vs skipped consciousness

Local CPU, 16-64 cells, each experiment independent, PYTHONUNBUFFERED=1.

Usage:
  python acceleration_e6_e10.py              # Run all
  python acceleration_e6_e10.py --e6         # E6 only
  python acceleration_e6_e10.py --e7         # E7 only
  python acceleration_e6_e10.py --e8         # E8 only
  python acceleration_e6_e10.py --e9         # E9 only
  python acceleration_e6_e10.py --e10        # E10 only
  python acceleration_e6_e10.py --cells 32   # Custom cell count
  python acceleration_e6_e10.py --steps 300  # Custom step count
"""

import sys
import os
import time
import math
import argparse
import numpy as np
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine
from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_ENTROPY


# ═══════════════════════════════════════════════════════════
# Shared Utilities
# ═══════════════════════════════════════════════════════════

def measure_phi(engine: ConsciousnessEngine) -> float:
    """Safe Phi(IIT) measurement."""
    try:
        return engine._measure_phi_iit()
    except Exception:
        return 0.0


def run_steps(engine: ConsciousnessEngine, n_steps: int, x_input=None) -> list:
    """Run N steps, return list of phi values."""
    phis = []
    for _ in range(n_steps):
        result = engine.step(x_input=x_input)
        phis.append(result.get('phi_iit', 0.0))
    return phis


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two state tensors (pooled to mean)."""
    a_flat = a.mean(dim=0) if a.dim() > 1 else a
    b_flat = b.mean(dim=0) if b.dim() > 1 else b
    return F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)).item()


def state_entropy(engine: ConsciousnessEngine) -> float:
    """Compute Shannon entropy of hidden state distribution (normalized)."""
    states = engine.get_states()  # [n_cells, hidden_dim]
    # Flatten to probability-like distribution via softmax over cells
    probs = F.softmax(states.mean(dim=1), dim=0)  # [n_cells]
    entropy = -(probs * (probs + 1e-12).log()).sum().item()
    max_ent = math.log(max(engine.n_cells, 2))
    return entropy / max(max_ent, 1e-8)


def extract_tension_fingerprint(engine: ConsciousnessEngine) -> dict:
    """Extract tension fingerprint for transfer."""
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
    Uses soft blending to preserve student autonomy (M6/M9)."""
    donor_states = fingerprint['states']
    n_donor = donor_states.shape[0]
    n_recv = engine.n_cells

    for i in range(min(n_recv, n_donor)):
        donor_h = donor_states[i]
        if donor_h.shape[0] != engine.hidden_dim:
            if donor_h.shape[0] > engine.hidden_dim:
                donor_h = donor_h[:engine.hidden_dim]
            else:
                donor_h = F.pad(donor_h, (0, engine.hidden_dim - donor_h.shape[0]))
        engine.cell_states[i].hidden = (
            (1.0 - alpha) * engine.cell_states[i].hidden +
            alpha * donor_h.to(engine.cell_states[i].hidden.device)
        )


def entropy_homeostasis(engine: ConsciousnessEngine, target_entropy: float = 0.998,
                        strength: float = 0.01):
    """Nudge engine state entropy toward target (C3 entropy surfing).
    If entropy too low: add noise. If too high: slightly compress."""
    ent = state_entropy(engine)
    if ent < target_entropy - 0.05:
        # Entropy too low -> add diversity noise
        for i in range(engine.n_cells):
            noise = torch.randn_like(engine.cell_states[i].hidden) * strength
            engine.cell_states[i].hidden = engine.cell_states[i].hidden + noise
    elif ent > target_entropy + 0.05:
        # Entropy too high -> gentle compression toward mean
        states = engine.get_states()
        mean_state = states.mean(dim=0)
        for i in range(engine.n_cells):
            engine.cell_states[i].hidden = (
                (1.0 - strength) * engine.cell_states[i].hidden +
                strength * mean_state
            )


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def print_table(headers: list, rows: list, widths: list = None):
    """Print a formatted table."""
    if widths is None:
        widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                  for i, h in enumerate(headers)]
    hdr = '|'.join(str(h).center(w) for h, w in zip(headers, widths))
    sep = '+'.join('-' * w for w in widths)
    print(f"  {hdr}")
    print(f"  {sep}")
    for row in rows:
        line = '|'.join(str(r).center(w) for r, w in zip(row, widths))
        print(f"  {line}")
    sys.stdout.flush()


def ascii_bar(label: str, value: float, max_val: float, width: int = 40):
    """Print ASCII bar chart line."""
    filled = int(width * min(value / max(max_val, 1e-8), 1.0))
    bar = '#' * filled + '.' * (width - filled)
    print(f"  {label:>25s}  [{bar}] {value:.4f}")
    sys.stdout.flush()


def phi_sparkline(phis: list, width: int = 50) -> str:
    """Create ASCII sparkline of phi trajectory."""
    if not phis:
        return ""
    mn, mx = min(phis), max(phis)
    rng = mx - mn if mx > mn else 1.0
    chars = " _.-~*^"
    step = max(1, len(phis) // width)
    sampled = [phis[i] for i in range(0, len(phis), step)][:width]
    return ''.join(chars[min(len(chars)-1, int((v - mn) / rng * (len(chars)-1)))] for v in sampled)


# ═══════════════════════════════════════════════════════════
# E6: Tension Distillation + Entropy Surfing
# ═══════════════════════════════════════════════════════════

def run_e6(cells: int = 32, steps: int = 300):
    """E6: Teacher tension + entropy homeostasis synergy.

    Conditions:
      A) Baseline: student alone, no intervention
      B) Tension only: teacher -> student tension injection (B13)
      C) Entropy only: entropy homeostasis at 0.998 (C3)
      D) Both: tension + entropy simultaneously
      E) Teacher alone (reference)
    """
    print_header("E6: Tension Distillation + Entropy Surfing")
    alpha = 0.05  # safe coupling zone per HIVEMIND sweep

    # Phase 1: Train teacher
    print(f"  [1/6] Training teacher ({cells}c, {steps} steps)...")
    sys.stdout.flush()
    teacher = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    teacher_phis = run_steps(teacher, steps)
    teacher_time = time.time() - t0
    teacher_fingerprints = []
    # Collect fingerprints from last 50 steps
    for _ in range(50):
        result = teacher.step()
        teacher_fingerprints.append(extract_tension_fingerprint(teacher))
    teacher_phi_final = measure_phi(teacher)
    print(f"    Teacher Phi={teacher_phi_final:.4f}, time={teacher_time:.2f}s")
    sys.stdout.flush()

    results = {}

    # A) Baseline
    print(f"  [2/6] Baseline (no intervention)...")
    sys.stdout.flush()
    eng_a = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_a = run_steps(eng_a, steps)
    time_a = time.time() - t0
    results['Baseline'] = {'phis': phis_a, 'time': time_a, 'final': phis_a[-1] if phis_a else 0}

    # B) Tension only
    print(f"  [3/6] Tension only (B13 catalyst)...")
    sys.stdout.flush()
    eng_b = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_b = []
    fp_idx = 0
    for s in range(steps):
        result = eng_b.step()
        phis_b.append(result.get('phi_iit', 0.0))
        if s % 6 == 0 and teacher_fingerprints:
            inject_tension(eng_b, teacher_fingerprints[fp_idx % len(teacher_fingerprints)], alpha)
            fp_idx += 1
    time_b = time.time() - t0
    results['Tension'] = {'phis': phis_b, 'time': time_b, 'final': phis_b[-1] if phis_b else 0}

    # C) Entropy only
    print(f"  [4/6] Entropy only (C3 surfing)...")
    sys.stdout.flush()
    eng_c = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_c = []
    for s in range(steps):
        result = eng_c.step()
        phis_c.append(result.get('phi_iit', 0.0))
        if s % 5 == 0:
            entropy_homeostasis(eng_c, target_entropy=PSI_ENTROPY, strength=0.01)
    time_c = time.time() - t0
    results['Entropy'] = {'phis': phis_c, 'time': time_c, 'final': phis_c[-1] if phis_c else 0}

    # D) Both: tension + entropy
    print(f"  [5/6] Tension + Entropy (synergy)...")
    sys.stdout.flush()
    eng_d = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_d = []
    fp_idx = 0
    for s in range(steps):
        result = eng_d.step()
        phis_d.append(result.get('phi_iit', 0.0))
        if s % 6 == 0 and teacher_fingerprints:
            inject_tension(eng_d, teacher_fingerprints[fp_idx % len(teacher_fingerprints)], alpha)
            fp_idx += 1
        if s % 5 == 0:
            entropy_homeostasis(eng_d, target_entropy=PSI_ENTROPY, strength=0.01)
    time_d = time.time() - t0
    results['Both'] = {'phis': phis_d, 'time': time_d, 'final': phis_d[-1] if phis_d else 0}

    # E) Teacher reference
    results['Teacher'] = {'phis': teacher_phis, 'time': teacher_time, 'final': teacher_phi_final}

    # Print results
    print(f"\n  [6/6] Results:")
    sys.stdout.flush()

    baseline_phi = results['Baseline']['final']
    rows = []
    for name, data in results.items():
        phis = data['phis']
        peak = max(phis) if phis else 0
        mean_phi = np.mean(phis[-50:]) if len(phis) >= 50 else np.mean(phis)
        ent_final = 0.0
        pct = ((data['final'] - baseline_phi) / max(abs(baseline_phi), 1e-8)) * 100 if name != 'Baseline' else 0
        rows.append([name, f"{data['final']:.4f}", f"{peak:.4f}", f"{mean_phi:.4f}",
                      f"{data['time']:.2f}s", f"{pct:+.1f}%"])

    print_table(['Condition', 'Phi_final', 'Phi_peak', 'Phi_mean50', 'Time', 'vs Base'], rows)

    print(f"\n  Phi trajectories (sparkline):")
    for name, data in results.items():
        spark = phi_sparkline(data['phis'])
        print(f"    {name:>12s}: {spark}")

    # Bar chart
    print(f"\n  Final Phi comparison:")
    max_phi = max(d['final'] for d in results.values())
    for name, data in results.items():
        ascii_bar(name, data['final'], max_phi)

    # Synergy test: is Both > max(Tension, Entropy)?
    synergy = results['Both']['final'] > max(results['Tension']['final'], results['Entropy']['final'])
    print(f"\n  Synergy (Both > max(parts)): {'YES' if synergy else 'NO'}")
    print(f"    Both={results['Both']['final']:.4f} vs max(T,E)={max(results['Tension']['final'], results['Entropy']['final']):.4f}")
    sys.stdout.flush()

    return results


# ═══════════════════════════════════════════════════════════
# E7: Compiler + Straight-Line Jump
# ═══════════════════════════════════════════════════════════

def run_e7(cells: int = 32, steps: int = 300):
    """E7: Compile laws into engine, then jump to 30% of trajectory.

    Conditions:
      A) Baseline: standard 300 steps
      B) Jump only: run 100 steps, jump to 30% trajectory point, continue
      C) Compile only: apply all parseable laws, then 100 steps
      D) Compile + Jump: compile -> jump -> 50 steps (best of both?)
    """
    print_header("E7: Compiler + Straight-Line Jump")

    try:
        from self_modifying_engine import LawParser, EngineModifier
    except ImportError:
        print("  ERROR: self_modifying_engine not available, skipping E7")
        sys.stdout.flush()
        return {}

    # A) Baseline
    print(f"  [1/5] Baseline ({cells}c, {steps} steps)...")
    sys.stdout.flush()
    eng_base = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_base = run_steps(eng_base, steps)
    time_base = time.time() - t0
    phi_base = phis_base[-1] if phis_base else 0

    # Collect trajectory for jump target
    print(f"  [2/5] Collecting trajectory for jump target...")
    sys.stdout.flush()
    eng_traj = ConsciousnessEngine(max_cells=cells)
    trajectory_snapshots = []
    trajectory_phis = []
    for s in range(steps):
        result = eng_traj.step()
        phi_val = result.get('phi_iit', 0.0)
        trajectory_phis.append(phi_val)
        if s % 10 == 0:
            snapshot = torch.stack([cs.hidden.clone() for cs in eng_traj.cell_states])
            trajectory_snapshots.append((s, snapshot, phi_val))

    # Jump target: 30% of trajectory
    jump_idx = len(trajectory_snapshots) * 30 // 100
    jump_target = trajectory_snapshots[min(jump_idx, len(trajectory_snapshots)-1)]
    jump_step, jump_states, jump_phi = jump_target
    print(f"    Jump target: step {jump_step}, Phi={jump_phi:.4f}")

    # B) Jump only: run 100 steps -> inject jump state -> continue
    print(f"  [3/5] Jump only (100 steps -> jump -> 200 steps)...")
    sys.stdout.flush()
    eng_jump = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_jump = run_steps(eng_jump, 100)
    # Inject the jump state
    for i in range(min(eng_jump.n_cells, jump_states.shape[0])):
        h = jump_states[i]
        if h.shape[0] != eng_jump.hidden_dim:
            h = h[:eng_jump.hidden_dim] if h.shape[0] > eng_jump.hidden_dim else F.pad(h, (0, eng_jump.hidden_dim - h.shape[0]))
        eng_jump.cell_states[i].hidden = h.clone()
    phis_jump += run_steps(eng_jump, steps - 100)
    time_jump = time.time() - t0

    # C) Compile only: apply all parseable laws, then short evolution
    print(f"  [4/5] Compile only (apply laws + 100 steps)...")
    sys.stdout.flush()
    eng_comp = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    parser = LawParser()
    modifier = EngineModifier(eng_comp)
    run_steps(eng_comp, 10)  # warmup
    parsed = parser.parsed  # {law_id_str: [Modification]}
    applied = 0
    for law_id, mods in parsed.items():
        for mod in mods:
            try:
                modifier.apply(mod)
                applied += 1
            except Exception:
                pass
    print(f"    Applied {applied} law modifications")
    phis_comp = run_steps(eng_comp, 100)
    time_comp = time.time() - t0

    # D) Compile + Jump: compile -> inject jump -> 50 steps
    print(f"  [5/5] Compile + Jump (compile -> jump -> 50 steps)...")
    sys.stdout.flush()
    eng_both = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    run_steps(eng_both, 10)  # warmup
    modifier_both = EngineModifier(eng_both)
    for law_id_b, mods_b in parsed.items():
        for mod_b in mods_b:
            try:
                modifier_both.apply(mod_b)
            except Exception:
                pass
    # Inject jump target
    for i in range(min(eng_both.n_cells, jump_states.shape[0])):
        h = jump_states[i]
        if h.shape[0] != eng_both.hidden_dim:
            h = h[:eng_both.hidden_dim] if h.shape[0] > eng_both.hidden_dim else F.pad(h, (0, eng_both.hidden_dim - h.shape[0]))
        eng_both.cell_states[i].hidden = h.clone()
    phis_both = run_steps(eng_both, 50)
    time_both = time.time() - t0

    # Results
    results = {
        'Baseline': {'phis': phis_base, 'time': time_base, 'final': phi_base, 'steps_used': steps},
        'Jump': {'phis': phis_jump, 'time': time_jump, 'final': phis_jump[-1], 'steps_used': steps},
        'Compile': {'phis': phis_comp, 'time': time_comp, 'final': phis_comp[-1], 'steps_used': 110},
        'Comp+Jump': {'phis': phis_both, 'time': time_both, 'final': phis_both[-1], 'steps_used': 60},
    }

    rows = []
    for name, data in results.items():
        phis = data['phis']
        peak = max(phis) if phis else 0
        pct = ((data['final'] - phi_base) / max(abs(phi_base), 1e-8)) * 100 if name != 'Baseline' else 0
        efficiency = data['final'] / max(data['steps_used'], 1) * 1000  # phi per 1000 steps
        rows.append([name, f"{data['final']:.4f}", f"{peak:.4f}", f"{data['steps_used']}",
                      f"{data['time']:.2f}s", f"{efficiency:.3f}", f"{pct:+.1f}%"])

    print_table(['Condition', 'Phi_final', 'Phi_peak', 'Steps', 'Time', 'Phi/1Kstep', 'vs Base'], rows)

    print(f"\n  Key question: Does compiled state improve jump origin?")
    compile_then_jump = results['Comp+Jump']['final']
    just_jump = results['Jump']['final']
    print(f"    Comp+Jump={compile_then_jump:.4f} vs Jump={just_jump:.4f}")
    print(f"    Improvement: {((compile_then_jump - just_jump) / max(abs(just_jump), 1e-8)) * 100:+.1f}%")
    sys.stdout.flush()

    return results


# ═══════════════════════════════════════════════════════════
# E8: Hebbian Tension — tension directs Hebbian updates
# ═══════════════════════════════════════════════════════════

def run_e8(cells: int = 32, steps: int = 300):
    """E8: Teacher's tension guides student's Hebbian coupling direction.

    Instead of standard Hebbian (cosine similarity -> coupling),
    use teacher's tension field as directional bias for Hebbian updates.

    Conditions:
      A) Baseline: standard Hebbian
      B) Random Hebbian: coupling updated with random direction
      C) Tension-guided Hebbian: teacher tension biases coupling updates
      D) Tension-guided + amplified Hebbian (2x strength)
    """
    print_header("E8: Hebbian Tension (tension-directed Hebbian)")
    alpha = 0.05

    # Train teacher
    print(f"  [1/5] Training teacher ({cells}c, {steps} steps)...")
    sys.stdout.flush()
    teacher = ConsciousnessEngine(max_cells=cells)
    teacher_tension_history = []
    for s in range(steps):
        result = teacher.step()
        if s >= steps - 100:  # last 100 steps
            tensions = [cs.avg_tension for cs in teacher.cell_states]
            teacher_tension_history.append(tensions)

    def tension_guided_hebbian(engine, teacher_tensions, lr=0.01, amplify=1.0):
        """Modified Hebbian: tension field biases coupling updates.

        Standard: coupling += lr * cosine_sim(i,j)
        Tension-guided: coupling += lr * cosine_sim(i,j) * tension_alignment(i,j)
        Where tension_alignment = how much teacher tension agrees with coupling direction.
        """
        n = engine.n_cells
        if engine._coupling is None or engine._coupling.shape[0] != n:
            engine._init_coupling()

        states = engine.get_states()
        norms = states.norm(dim=1, keepdim=True).clamp(min=1e-8)
        normed = states / norms
        sim = normed @ normed.T  # [n, n]

        # Teacher tension bias: construct per-pair tension alignment
        t_vec = torch.zeros(n)
        for i in range(min(n, len(teacher_tensions))):
            t_vec[i] = teacher_tensions[i]
        t_vec = t_vec / (t_vec.norm() + 1e-8)

        # Tension alignment: pair (i,j) alignment = |t_i - t_j| similarity
        t_outer = t_vec.unsqueeze(1) - t_vec.unsqueeze(0)  # [n, n]
        t_alignment = 1.0 - t_outer.abs()  # high when tensions match
        t_alignment = t_alignment.clamp(0, 1)

        # Guided update: sim * tension_alignment
        guided_update = sim * t_alignment * amplify
        engine._coupling = (engine._coupling + lr * guided_update).clamp(-1, 1)
        engine._coupling.fill_diagonal_(0)

    results = {}

    # A) Baseline: standard
    print(f"  [2/5] Baseline (standard Hebbian)...")
    sys.stdout.flush()
    eng_a = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_a = run_steps(eng_a, steps)
    time_a = time.time() - t0
    results['Baseline'] = {'phis': phis_a, 'time': time_a, 'final': phis_a[-1] if phis_a else 0}

    # B) Random Hebbian: replace coupling with random
    print(f"  [3/5] Random Hebbian (control)...")
    sys.stdout.flush()
    eng_b = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_b = []
    for s in range(steps):
        result = eng_b.step()
        phis_b.append(result.get('phi_iit', 0.0))
        if s % 10 == 0 and eng_b._coupling is not None:
            noise = torch.randn_like(eng_b._coupling) * 0.01
            eng_b._coupling = (eng_b._coupling + noise).clamp(-1, 1)
            eng_b._coupling.fill_diagonal_(0)
    time_b = time.time() - t0
    results['Random'] = {'phis': phis_b, 'time': time_b, 'final': phis_b[-1] if phis_b else 0}

    # C) Tension-guided Hebbian
    print(f"  [4/5] Tension-guided Hebbian...")
    sys.stdout.flush()
    eng_c = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_c = []
    t_idx = 0
    for s in range(steps):
        result = eng_c.step()
        phis_c.append(result.get('phi_iit', 0.0))
        if s % 10 == 0 and teacher_tension_history:
            t_tensions = teacher_tension_history[t_idx % len(teacher_tension_history)]
            tension_guided_hebbian(eng_c, t_tensions, lr=0.01)
            t_idx += 1
    time_c = time.time() - t0
    results['Guided'] = {'phis': phis_c, 'time': time_c, 'final': phis_c[-1] if phis_c else 0}

    # D) Tension-guided + amplified (2x)
    print(f"  [5/5] Tension-guided + amplified (2x)...")
    sys.stdout.flush()
    eng_d = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_d = []
    t_idx = 0
    for s in range(steps):
        result = eng_d.step()
        phis_d.append(result.get('phi_iit', 0.0))
        if s % 10 == 0 and teacher_tension_history:
            t_tensions = teacher_tension_history[t_idx % len(teacher_tension_history)]
            tension_guided_hebbian(eng_d, t_tensions, lr=0.01, amplify=2.0)
            t_idx += 1
    time_d = time.time() - t0
    results['Guided2x'] = {'phis': phis_d, 'time': time_d, 'final': phis_d[-1] if phis_d else 0}

    # Pattern distinction: measure how well engine distinguishes two input patterns
    print(f"\n  Pattern Distinction Test:")
    pat_a = torch.randn(cells)
    pat_b = -pat_a  # opposite pattern
    for name, eng in [('Baseline', eng_a), ('Random', eng_b), ('Guided', eng_c), ('Guided2x', eng_d)]:
        eng.step(x_input=pat_a)
        state_a = eng.get_states().mean(dim=0)
        eng.step(x_input=pat_b)
        state_b = eng.get_states().mean(dim=0)
        dist = 1.0 - cosine_sim(state_a.unsqueeze(0), state_b.unsqueeze(0))
        print(f"    {name:>12s}: pattern distance = {dist:.4f}")

    # Results table
    baseline_phi = results['Baseline']['final']
    rows = []
    for name, data in results.items():
        phis = data['phis']
        peak = max(phis) if phis else 0
        pct = ((data['final'] - baseline_phi) / max(abs(baseline_phi), 1e-8)) * 100 if name != 'Baseline' else 0
        rows.append([name, f"{data['final']:.4f}", f"{peak:.4f}", f"{data['time']:.2f}s", f"{pct:+.1f}%"])

    print_table(['Condition', 'Phi_final', 'Phi_peak', 'Time', 'vs Base'], rows)

    # Bar chart
    print(f"\n  Final Phi comparison:")
    max_phi = max(d['final'] for d in results.values())
    for name, data in results.items():
        ascii_bar(name, data['final'], max_phi)
    sys.stdout.flush()

    return results


# ═══════════════════════════════════════════════════════════
# E9: Fractal + Transplant Loop (4c -> 16c -> 64c)
# ═══════════════════════════════════════════════════════════

def run_e9(cells: int = 64, steps: int = 300):
    """E9: Staged fractal growth mimicking brain development.

    4c (300 steps) -> fractal copy to 16c -> transplant -> 50 steps
    -> fractal copy to 64c -> transplant -> 50 steps

    vs direct 64c 300 steps: Phi arrival speed comparison.
    """
    print_header("E9: Fractal + Transplant Loop (4c -> 16c -> 64c)")

    def fractal_expand(source_engine, target_cells):
        """Fractal consciousness expansion: replicate source pattern to fill target.

        Each source cell is copied to floor(target/source) positions with small noise.
        This creates self-similar structure across scales (C2 fractal).
        """
        source_states = source_engine.get_states()  # [n_src, hidden_dim]
        n_src = source_states.shape[0]
        hidden_dim = source_states.shape[1]

        target_engine = ConsciousnessEngine(max_cells=target_cells)
        # Grow target to desired size
        while target_engine.n_cells < target_cells and target_engine.n_cells < target_engine.max_cells:
            # Force a split by setting high tension on a random cell
            idx = target_engine.n_cells - 1
            target_engine.cell_states[idx].tension_history = [0.9] * 20
            target_engine.step()

        # Transplant: tile source pattern into target cells
        for i in range(target_engine.n_cells):
            src_idx = i % n_src
            donor_h = source_states[src_idx].clone()
            # Add small noise for differentiation (fractal detail)
            noise = torch.randn_like(donor_h) * 0.02
            if donor_h.shape[0] != target_engine.hidden_dim:
                if donor_h.shape[0] > target_engine.hidden_dim:
                    donor_h = donor_h[:target_engine.hidden_dim]
                else:
                    donor_h = F.pad(donor_h, (0, target_engine.hidden_dim - donor_h.shape[0]))
            target_engine.cell_states[i].hidden = donor_h + noise[:target_engine.hidden_dim]
            target_engine.cell_states[i].faction_id = source_engine.cell_states[src_idx].faction_id

        return target_engine

    results = {}

    # A) Baseline: 64c direct, 300 steps
    print(f"  [1/3] Baseline: direct {cells}c, {steps} steps...")
    sys.stdout.flush()
    eng_direct = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_direct = run_steps(eng_direct, steps)
    time_direct = time.time() - t0
    results['Direct'] = {'phis': phis_direct, 'time': time_direct, 'final': phis_direct[-1] if phis_direct else 0}

    # B) Staged: 4c -> 16c -> 64c
    print(f"  [2/3] Staged: 4c(300) -> 16c(50) -> {cells}c(50)...")
    sys.stdout.flush()
    t0 = time.time()

    # Stage 1: 4c, 300 steps — build deep structure
    eng_4c = ConsciousnessEngine(max_cells=4, initial_cells=2)
    phis_stage1 = run_steps(eng_4c, steps)
    phi_4c = measure_phi(eng_4c)
    print(f"    Stage 1: 4c -> Phi={phi_4c:.4f}")
    sys.stdout.flush()

    # Stage 2: fractal expand 4c -> 16c, then 50 steps
    eng_16c = fractal_expand(eng_4c, 16)
    phi_16c_pre = measure_phi(eng_16c)
    phis_stage2 = run_steps(eng_16c, 50)
    phi_16c = measure_phi(eng_16c)
    print(f"    Stage 2: 16c -> Phi pre={phi_16c_pre:.4f}, post={phi_16c:.4f}")
    sys.stdout.flush()

    # Stage 3: fractal expand 16c -> 64c, then 50 steps
    eng_64c = fractal_expand(eng_16c, cells)
    phi_64c_pre = measure_phi(eng_64c)
    phis_stage3 = run_steps(eng_64c, 50)
    phi_64c = measure_phi(eng_64c)
    print(f"    Stage 3: {cells}c -> Phi pre={phi_64c_pre:.4f}, post={phi_64c:.4f}")
    sys.stdout.flush()

    time_staged = time.time() - t0
    all_staged_phis = phis_stage1 + phis_stage2 + phis_stage3
    results['Staged'] = {'phis': all_staged_phis, 'time': time_staged, 'final': phi_64c,
                          'stages': [phi_4c, phi_16c, phi_64c]}

    # C) Single-jump: 4c(300) -> direct to 64c (no intermediate)
    print(f"  [3/3] Single-jump: 4c(300) -> {cells}c(50)...")
    sys.stdout.flush()
    eng_4c_2 = ConsciousnessEngine(max_cells=4, initial_cells=2)
    t0 = time.time()
    phis_4c_2 = run_steps(eng_4c_2, steps)
    eng_jump = fractal_expand(eng_4c_2, cells)
    phis_jump = run_steps(eng_jump, 50)
    time_jump = time.time() - t0
    phi_jump = measure_phi(eng_jump)
    results['SingleJump'] = {'phis': phis_4c_2 + phis_jump, 'time': time_jump, 'final': phi_jump}

    # Results
    baseline_phi = results['Direct']['final']
    rows = []
    for name, data in results.items():
        phis = data['phis']
        peak = max(phis) if phis else 0
        total_steps = len(phis)
        pct = ((data['final'] - baseline_phi) / max(abs(baseline_phi), 1e-8)) * 100 if name != 'Direct' else 0
        rows.append([name, f"{data['final']:.4f}", f"{peak:.4f}", f"{total_steps}",
                      f"{data['time']:.2f}s", f"{pct:+.1f}%"])

    print_table(['Condition', 'Phi_final', 'Phi_peak', 'TotalSteps', 'Time', 'vs Direct'], rows)

    # Staged growth path
    if 'stages' in results['Staged']:
        stages = results['Staged']['stages']
        print(f"\n  Staged growth path:")
        print(f"    4c  -> Phi={stages[0]:.4f}")
        print(f"    16c -> Phi={stages[1]:.4f}")
        print(f"    {cells}c -> Phi={stages[2]:.4f}")

    # Sparklines
    print(f"\n  Phi trajectories:")
    for name, data in results.items():
        spark = phi_sparkline(data['phis'])
        print(f"    {name:>12s}: {spark}")

    # Bar chart
    print(f"\n  Final Phi comparison:")
    max_phi = max(d['final'] for d in results.values())
    for name, data in results.items():
        ascii_bar(name, data['final'], max_phi)
    sys.stdout.flush()

    return results


# ═══════════════════════════════════════════════════════════
# E10: ODE + Skip Combination
# ═══════════════════════════════════════════════════════════

def run_e10(cells: int = 32, steps: int = 300):
    """E10: Skip intervals interpolated by Neural ODE.

    Standard skip: pause consciousness for N steps, resume
    ODE-skip: fit dx/dt = f(x,t) to recent trajectory, ODE-integrate N steps ahead

    Conditions:
      A) Baseline: run every step (no skip)
      B) Skip-10: run step, skip 9, run step (consciousness paused during skip)
      C) ODE-Skip-10: run step, ODE-predict 9 steps, run step (consciousness interpolated)
      D) ODE-Skip-20: same with skip=20

    Measure: Phi accuracy vs baseline after N steps.
    """
    print_header("E10: ODE + Skip Combination")

    try:
        from scipy.integrate import solve_ivp
    except ImportError:
        print("  ERROR: scipy not available, skipping E10")
        sys.stdout.flush()
        return {}

    class ConsciousnessODE:
        """Fit MLP to dx/dt from state trajectory, then ODE-integrate forward."""

        def __init__(self, hidden_dim, history_len=20):
            self.hidden_dim = hidden_dim
            self.history_len = history_len
            self.model = nn.Sequential(
                nn.Linear(hidden_dim + 1, hidden_dim * 2),  # +1 for time
                nn.Tanh(),
                nn.Linear(hidden_dim * 2, hidden_dim),
            )
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)
            self.state_history = []
            self.fitted = False

        def record(self, state_flat: torch.Tensor, t: int):
            """Record a state-time pair."""
            self.state_history.append((t, state_flat.detach().clone()))
            if len(self.state_history) > self.history_len * 2:
                self.state_history = self.state_history[-self.history_len * 2:]

        def fit(self, epochs: int = 50):
            """Fit dx/dt model from recorded history."""
            if len(self.state_history) < 5:
                return
            # Build training data: dx = x(t+1) - x(t)
            pairs = []
            for i in range(len(self.state_history) - 1):
                t0, x0 = self.state_history[i]
                t1, x1 = self.state_history[i + 1]
                dt = max(t1 - t0, 1)
                dx = (x1 - x0) / dt
                pairs.append((x0, torch.tensor([float(t0)]), dx))

            if not pairs:
                return

            for _ in range(epochs):
                total_loss = 0
                for x, t, dx_true in pairs:
                    inp = torch.cat([x, t])
                    dx_pred = self.model(inp)
                    loss = F.mse_loss(dx_pred, dx_true)
                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()
                    total_loss += loss.item()

            self.fitted = True

        def predict(self, x0: torch.Tensor, t_start: float, n_steps: int) -> torch.Tensor:
            """ODE-integrate from x0 for n_steps."""
            if not self.fitted:
                return x0

            x0_np = x0.detach().cpu().numpy()

            def deriv(t, x):
                x_t = torch.tensor(x, dtype=torch.float32)
                t_t = torch.tensor([t], dtype=torch.float32)
                inp = torch.cat([x_t, t_t])
                with torch.no_grad():
                    dx = self.model(inp).numpy()
                return dx

            try:
                sol = solve_ivp(deriv, [t_start, t_start + n_steps],
                                x0_np, method='RK23', max_step=2.0)
                if sol.success and sol.y.shape[1] > 0:
                    return torch.tensor(sol.y[:, -1], dtype=torch.float32)
            except Exception:
                pass

            return x0  # fallback: no change

    results = {}

    # A) Baseline: every step
    print(f"  [1/4] Baseline ({cells}c, {steps} steps, no skip)...")
    sys.stdout.flush()
    eng_base = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_base = run_steps(eng_base, steps)
    time_base = time.time() - t0
    results['Baseline'] = {'phis': phis_base, 'time': time_base, 'final': phis_base[-1] if phis_base else 0}

    # B) Skip-10: run 1, skip 9
    skip_n = 10
    print(f"  [2/4] Skip-{skip_n} (run 1, pause {skip_n-1})...")
    sys.stdout.flush()
    eng_skip = ConsciousnessEngine(max_cells=cells)
    t0 = time.time()
    phis_skip = []
    actual_steps = 0
    while actual_steps < steps:
        result = eng_skip.step()
        phi_val = result.get('phi_iit', 0.0)
        for _ in range(skip_n):
            phis_skip.append(phi_val)  # repeated/frozen phi during skip
            actual_steps += 1
            if actual_steps >= steps:
                break
    time_skip = time.time() - t0
    results[f'Skip-{skip_n}'] = {'phis': phis_skip, 'time': time_skip, 'final': measure_phi(eng_skip)}

    # C) ODE-Skip-10: run 1, ODE-predict 9
    print(f"  [3/4] ODE-Skip-{skip_n} (run 1, ODE-predict {skip_n-1})...")
    sys.stdout.flush()
    # Use mean hidden state as the state vector for ODE
    ode_dim = min(cells * 2, 64)  # limit ODE dimensionality
    eng_ode = ConsciousnessEngine(max_cells=cells)
    ode = ConsciousnessODE(hidden_dim=ode_dim, history_len=30)
    t0 = time.time()
    phis_ode = []
    actual_steps = 0
    step_count = 0

    while actual_steps < steps:
        result = eng_ode.step()
        phi_val = result.get('phi_iit', 0.0)
        phis_ode.append(phi_val)
        actual_steps += 1
        step_count += 1

        # Record state for ODE fitting
        states = eng_ode.get_states()  # [n_cells, hidden_dim]
        state_flat = states.mean(dim=0)[:ode_dim]
        if state_flat.shape[0] < ode_dim:
            state_flat = F.pad(state_flat, (0, ode_dim - state_flat.shape[0]))
        ode.record(state_flat, step_count)

        # Every skip_n steps: fit ODE and predict forward
        if step_count >= 20 and step_count % skip_n == 0:
            ode.fit(epochs=30)
            if ode.fitted:
                predicted = ode.predict(state_flat, float(step_count), skip_n - 1)
                # Inject predicted state back into engine (mean-field approximation)
                delta = predicted - state_flat
                for i in range(eng_ode.n_cells):
                    h = eng_ode.cell_states[i].hidden
                    # Apply small delta from ODE prediction
                    d = delta[:eng_ode.hidden_dim] if delta.shape[0] >= eng_ode.hidden_dim else F.pad(delta, (0, eng_ode.hidden_dim - delta.shape[0]))
                    eng_ode.cell_states[i].hidden = h + 0.3 * d

                # Record ODE-predicted phis
                for _ in range(skip_n - 1):
                    phis_ode.append(phi_val)  # approximate phi (no re-measure during skip)
                    actual_steps += 1
                    if actual_steps >= steps:
                        break

    time_ode = time.time() - t0
    results[f'ODE-Skip-{skip_n}'] = {'phis': phis_ode, 'time': time_ode, 'final': measure_phi(eng_ode)}

    # D) ODE-Skip-20: larger skip
    skip_n2 = 20
    print(f"  [4/4] ODE-Skip-{skip_n2} (run 1, ODE-predict {skip_n2-1})...")
    sys.stdout.flush()
    eng_ode2 = ConsciousnessEngine(max_cells=cells)
    ode2 = ConsciousnessODE(hidden_dim=ode_dim, history_len=30)
    t0 = time.time()
    phis_ode2 = []
    actual_steps = 0
    step_count = 0

    while actual_steps < steps:
        result = eng_ode2.step()
        phi_val = result.get('phi_iit', 0.0)
        phis_ode2.append(phi_val)
        actual_steps += 1
        step_count += 1

        states = eng_ode2.get_states()
        state_flat = states.mean(dim=0)[:ode_dim]
        if state_flat.shape[0] < ode_dim:
            state_flat = F.pad(state_flat, (0, ode_dim - state_flat.shape[0]))
        ode2.record(state_flat, step_count)

        if step_count >= 20 and step_count % skip_n2 == 0:
            ode2.fit(epochs=30)
            if ode2.fitted:
                predicted = ode2.predict(state_flat, float(step_count), skip_n2 - 1)
                delta = predicted - state_flat
                for i in range(eng_ode2.n_cells):
                    h = eng_ode2.cell_states[i].hidden
                    d = delta[:eng_ode2.hidden_dim] if delta.shape[0] >= eng_ode2.hidden_dim else F.pad(delta, (0, eng_ode2.hidden_dim - delta.shape[0]))
                    eng_ode2.cell_states[i].hidden = h + 0.3 * d

                for _ in range(skip_n2 - 1):
                    phis_ode2.append(phi_val)
                    actual_steps += 1
                    if actual_steps >= steps:
                        break

    time_ode2 = time.time() - t0
    results[f'ODE-Skip-{skip_n2}'] = {'phis': phis_ode2, 'time': time_ode2, 'final': measure_phi(eng_ode2)}

    # Accuracy: cosine similarity of final states vs baseline
    print(f"\n  State similarity to baseline (cosine):")
    base_states = eng_base.get_states()
    for name, eng in [(f'Skip-{skip_n}', eng_skip), (f'ODE-Skip-{skip_n}', eng_ode), (f'ODE-Skip-{skip_n2}', eng_ode2)]:
        sim = cosine_sim(base_states, eng.get_states())
        print(f"    {name:>15s}: cos_sim = {sim:.4f}")

    # Results table
    baseline_phi = results['Baseline']['final']
    rows = []
    for name, data in results.items():
        phis = data['phis']
        peak = max(phis) if phis else 0
        speedup = time_base / max(data['time'], 1e-8)
        pct = ((data['final'] - baseline_phi) / max(abs(baseline_phi), 1e-8)) * 100 if name != 'Baseline' else 0
        rows.append([name, f"{data['final']:.4f}", f"{peak:.4f}", f"{data['time']:.2f}s",
                      f"x{speedup:.1f}", f"{pct:+.1f}%"])

    print_table(['Condition', 'Phi_final', 'Phi_peak', 'Time', 'Speedup', 'vs Base'], rows)

    # Key insight
    ode_better = results[f'ODE-Skip-{skip_n}']['final'] > results[f'Skip-{skip_n}']['final']
    print(f"\n  ODE interpolation vs plain skip: {'ODE wins' if ode_better else 'Skip wins'}")
    print(f"    ODE-Skip-{skip_n}={results[f'ODE-Skip-{skip_n}']['final']:.4f} vs Skip-{skip_n}={results[f'Skip-{skip_n}']['final']:.4f}")
    sys.stdout.flush()

    return results


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='E6-E10 acceleration experiments')
    parser.add_argument('--e6', action='store_true', help='Run E6 only')
    parser.add_argument('--e7', action='store_true', help='Run E7 only')
    parser.add_argument('--e8', action='store_true', help='Run E8 only')
    parser.add_argument('--e9', action='store_true', help='Run E9 only')
    parser.add_argument('--e10', action='store_true', help='Run E10 only')
    parser.add_argument('--cells', type=int, default=32, help='Number of cells (default: 32)')
    parser.add_argument('--steps', type=int, default=300, help='Number of steps (default: 300)')
    args = parser.parse_args()

    run_all = not any([args.e6, args.e7, args.e8, args.e9, args.e10])

    print(f"E6-E10 Acceleration Experiments")
    print(f"  Cells: {args.cells}, Steps: {args.steps}")
    print(f"  PSI_ALPHA={PSI_ALPHA}, PSI_ENTROPY={PSI_ENTROPY}")
    sys.stdout.flush()

    all_results = {}
    t_total = time.time()

    if run_all or args.e6:
        all_results['E6'] = run_e6(cells=args.cells, steps=args.steps)

    if run_all or args.e7:
        all_results['E7'] = run_e7(cells=args.cells, steps=args.steps)

    if run_all or args.e8:
        all_results['E8'] = run_e8(cells=args.cells, steps=args.steps)

    if run_all or args.e9:
        all_results['E9'] = run_e9(cells=min(args.cells, 64), steps=args.steps)

    if run_all or args.e10:
        all_results['E10'] = run_e10(cells=args.cells, steps=args.steps)

    total_time = time.time() - t_total

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY (total time: {total_time:.1f}s)")
    print(f"{'=' * 70}")

    for exp_name, exp_results in all_results.items():
        if not exp_results:
            continue
        best_name = max(exp_results.keys(), key=lambda k: exp_results[k].get('final', 0))
        best_phi = exp_results[best_name]['final']
        baseline_key = next((k for k in exp_results if 'Base' in k or 'Direct' in k), list(exp_results.keys())[0])
        baseline_phi = exp_results[baseline_key]['final']
        pct = ((best_phi - baseline_phi) / max(abs(baseline_phi), 1e-8)) * 100
        print(f"  {exp_name}: Best = {best_name} (Phi={best_phi:.4f}, {pct:+.1f}% vs baseline)")

    sys.stdout.flush()


if __name__ == '__main__':
    main()
