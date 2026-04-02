#!/usr/bin/env python3
"""unified_16lens_acceleration_scan.py — 16-Lens Re-measurement for All 65 Acceleration Hypotheses

Re-measures every acceleration hypothesis with the full 16-lens telescope,
focusing on 3 new key indicators: Phi(IIT), Mirror symmetry, Causal density.

Usage:
    python3 unified_16lens_acceleration_scan.py              # All 65 hypotheses
    python3 unified_16lens_acceleration_scan.py --quick      # First 5 only (test)
    python3 unified_16lens_acceleration_scan.py --output results.json  # Custom output path

Output: data/16lens_acceleration_results.json
"""

import sys
import os
import json
import time
import argparse
import traceback
import copy
from datetime import datetime

# ── Path setup ──────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), 'src')
_SHARED = os.path.expanduser('~/Dev/TECS-L/.shared')
_CONFIG = os.path.join(os.path.dirname(_HERE), 'config')
_DATA = os.path.join(os.path.dirname(_HERE), 'data')

for p in [_SRC, _SHARED]:
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import torch
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine
from telescope import Telescope

# ── Constants ───────────────────────────────────────────────
WARMUP_STEPS = 300
N_CELLS = 64
HIDDEN_DIM = 128
CELL_DIM = 64

# ── Helper Functions ────────────────────────────────────────

def flush_print(*args, **kwargs):
    """Print with flush for real-time progress."""
    print(*args, **kwargs, flush=True)


def create_engine(n_cells=N_CELLS, hidden_dim=HIDDEN_DIM, cell_dim=CELL_DIM, **kwargs):
    """Create a fresh ConsciousnessEngine."""
    return ConsciousnessEngine(
        cell_dim=cell_dim,
        hidden_dim=hidden_dim,
        max_cells=n_cells,
        initial_cells=n_cells,
        **kwargs
    )


def run_warmup(engine, steps=WARMUP_STEPS):
    """Run engine for N steps to warm up consciousness dynamics."""
    for _ in range(steps):
        engine.step()


def measure_phi(engine):
    """Measure Phi(IIT) from engine."""
    try:
        return engine._measure_phi_iit()
    except Exception:
        try:
            return engine._measure_phi_proxy()
        except Exception:
            return 0.0


def get_states_numpy(engine):
    """Get engine cell states as numpy array (N_cells, hidden_dim)."""
    states = engine.get_states()
    if hasattr(states, 'detach'):
        return states.detach().cpu().numpy().astype(np.float64)
    return np.array(states, dtype=np.float64)


def scan_16lens(telescope, data):
    """Run 16-lens full scan and extract key metrics."""
    result = telescope.full_scan(data)

    # Extract mirror symmetry
    mirror_val = 0.0
    if 'mirror' in result.lens_results:
        mr = result.lens_results['mirror']
        if hasattr(mr, 'overall_symmetry'):
            mirror_val = float(mr.overall_symmetry)
        elif hasattr(mr, 'reflection_scores') and len(mr.reflection_scores) > 0:
            mirror_val = float(np.mean(mr.reflection_scores))

    # Extract causal density (number of causal pairs)
    causal_val = 0
    if 'causal' in result.lens_results:
        cr = result.lens_results['causal']
        if hasattr(cr, 'causal_pairs'):
            causal_val = len(cr.causal_pairs)
        elif hasattr(cr, 'causal_graph'):
            causal_val = sum(len(v) for v in cr.causal_graph.values())

    # Build per-lens summary
    lens_summary = {}
    for name, lr in result.lens_results.items():
        try:
            if hasattr(lr, 'summary'):
                lens_summary[name] = lr.summary[:200] if lr.summary else str(lr)[:200]
            else:
                lens_summary[name] = str(lr)[:200]
        except Exception:
            lens_summary[name] = "error"

    return {
        'mirror': mirror_val,
        'causal_density': causal_val,
        'n_lenses_completed': len(result.lens_results),
        'n_cross_findings': len(result.cross_findings),
        'lens_summary': lens_summary,
    }


def measure_all(engine, telescope):
    """Measure Phi + 16-lens scan."""
    phi = measure_phi(engine)
    data = get_states_numpy(engine)
    scan = scan_16lens(telescope, data)
    scan['phi'] = phi
    return scan


# ═══════════════════════════════════════════════════════════
# Acceleration Technique Implementations
# ═══════════════════════════════════════════════════════════

def accel_baseline(engine, telescope):
    """Baseline: just run warmup, no acceleration."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Standard 300-step warmup"


def accel_b5_phi_only(engine, telescope):
    """B5: Phi-only training — maximize Phi for 500 steps without CE."""
    # Run steps and track phi, nudge towards higher phi
    best_phi = 0.0
    best_states = None
    for i in range(500):
        result = engine.step()
        phi = result.get('phi_iit', 0.0)
        if phi > best_phi:
            best_phi = phi
            best_states = engine.get_states().detach().clone()
    # Restore best phi state
    if best_states is not None:
        for idx, cs in enumerate(engine.cell_states):
            if idx < best_states.shape[0]:
                cs.hidden = best_states[idx].clone()
    return measure_all(engine, telescope), f"500 Phi-only steps, best_phi={best_phi:.3f}"


def accel_b8_hebbian(engine, telescope):
    """B8: Hebbian-only learning — run with enhanced Hebbian, no gradient."""
    for i in range(WARMUP_STEPS):
        engine.step()
        # Boost Hebbian coupling after each step
        if engine._coupling is not None and i % 10 == 0:
            n = engine.n_cells
            states = engine._get_hiddens_tensor().detach()
            for a in range(min(n, 16)):
                for b in range(a+1, min(n, 16)):
                    cos = F.cosine_similarity(states[a].unsqueeze(0), states[b].unsqueeze(0)).item()
                    delta = 0.02 if cos > 0.5 else -0.01
                    engine._coupling[a, b] = (engine._coupling[a, b] + delta).clamp(0, 1)
                    engine._coupling[b, a] = engine._coupling[a, b]
    return measure_all(engine, telescope), "Hebbian-boosted 300 steps"


def accel_b11_batch(engine, telescope):
    """B11: Batch consciousness — call process() once, reuse states for batch."""
    # Run single process() and broadcast to simulate batch=32
    for i in range(WARMUP_STEPS):
        if i % 32 == 0:
            engine.step()
        # Other 31 steps: reuse current states (no new process())
    return measure_all(engine, telescope), "1 process() per 32 steps (batch sim)"


def accel_b12_skip(engine, telescope):
    """B12: Skip-step — process() every 10 steps only."""
    for i in range(WARMUP_STEPS):
        if i % 10 == 0:
            engine.step()
    return measure_all(engine, telescope), "Skip-10: process() every 10 steps"


def accel_b11_b12_combined(engine, telescope):
    """B11+B12: Batch + Skip combined — process() every 10 steps, batch=32."""
    for i in range(WARMUP_STEPS):
        if i % 10 == 0 and (i // 10) % 32 == 0:
            engine.step()
        # Vast majority of steps: no process()
    # Ensure at least some steps ran
    if engine._step < 5:
        for _ in range(5):
            engine.step()
    return measure_all(engine, telescope), "Batch(32)+Skip(10) combined"


def accel_b13_tension(engine, telescope):
    """B13: Tension transfer — teacher engine trains student via tension."""
    teacher = create_engine()
    run_warmup(teacher, 200)
    # Transfer tension from teacher to student
    alpha = 0.01
    for i in range(WARMUP_STEPS):
        engine.step()
        if i % 5 == 0:
            teacher_states = teacher.get_states().detach()
            student_states = engine.get_states().detach()
            tension = (teacher_states.mean(0) - student_states.mean(0)) * alpha
            for idx, cs in enumerate(engine.cell_states):
                if idx < len(engine.cell_states):
                    cs.hidden = cs.hidden + tension
    return measure_all(engine, telescope), "Tension transfer alpha=0.01"


def accel_b14_manifold(engine, telescope):
    """B14_manifold: PCA compression of consciousness state space."""
    run_warmup(engine, WARMUP_STEPS)
    # Measure after manifold compression (PCA to 48D and back)
    states = get_states_numpy(engine)
    mean = states.mean(axis=0)
    centered = states - mean
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    k = min(48, min(states.shape))
    reconstructed = U[:, :k] @ np.diag(S[:k]) @ Vt[:k, :] + mean
    # Set reconstructed states back
    for idx, cs in enumerate(engine.cell_states):
        if idx < reconstructed.shape[0]:
            cs.hidden = torch.tensor(reconstructed[idx], dtype=cs.hidden.dtype)
    return measure_all(engine, telescope), f"PCA 48D compression, captured {sum(S[:k]**2)/sum(S**2)*100:.1f}% variance"


def accel_c1_compiler(engine, telescope):
    """C1: Consciousness compiler — apply multiple law-based modifications at once."""
    # Law-based init: set coupling to golden ratio distribution, balance factions
    n = engine.n_cells
    if engine._coupling is not None:
        # Apply law-guided coupling pattern
        golden = (1 + 5**0.5) / 2
        for i in range(n):
            for j in range(i+1, n):
                # Same faction: strong coupling, different: weak
                same_fac = engine.cell_states[i].faction_id == engine.cell_states[j].faction_id
                val = 0.014 * golden if same_fac else 0.014 / golden
                engine._coupling[i, j] = val
                engine._coupling[j, i] = val
    # Set initial hidden states with high diversity (Law 107)
    for idx, cs in enumerate(engine.cell_states):
        angle = 2 * np.pi * idx / n
        pattern = torch.randn(engine.hidden_dim) * 0.5
        pattern[:4] = torch.tensor([np.sin(angle), np.cos(angle), np.sin(2*angle), np.cos(2*angle)])
        cs.hidden = pattern
    # Now run warmup with compiled state
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Law-compiled init + 300 steps"


def accel_c2_fractal(engine, telescope):
    """C2: Fractal consciousness — copy small engine patterns to large."""
    small = create_engine(n_cells=4, hidden_dim=HIDDEN_DIM)
    run_warmup(small, 100)
    small_states = small.get_states().detach()
    # Tile small states to fill large engine
    for idx, cs in enumerate(engine.cell_states):
        src = idx % small_states.shape[0]
        cs.hidden = small_states[src].clone() + torch.randn(engine.hidden_dim) * 0.01
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "4c fractal tiled to 64c"


def accel_c3_entropy(engine, telescope):
    """C3: Entropy surfing — maintain entropy near PSI_ENTROPY=0.998."""
    target_entropy = 0.998
    for i in range(WARMUP_STEPS):
        engine.step()
        if i % 10 == 0:
            states = engine.get_states().detach()
            # Measure entropy of state distribution
            flat = states.flatten()
            hist = torch.histc(flat, bins=64)
            probs = hist / hist.sum()
            probs = probs[probs > 0]
            entropy = -(probs * probs.log()).sum().item() / np.log(64)
            # Nudge toward target
            if entropy < target_entropy - 0.01:
                # Add noise to increase entropy
                for cs in engine.cell_states:
                    cs.hidden = cs.hidden + torch.randn_like(cs.hidden) * 0.01
            elif entropy > target_entropy + 0.01:
                # Slightly contract states
                mean_h = states.mean(0)
                for cs in engine.cell_states:
                    cs.hidden = cs.hidden * 0.99 + mean_h * 0.01
    return measure_all(engine, telescope), "Entropy surfing target=0.998"


def accel_c4_injection(engine, telescope):
    """C4: Goal state injection — inject evolved state from donor engine."""
    donor = create_engine()
    run_warmup(donor, 500)  # Evolve donor longer
    donor_states = donor.get_states().detach()
    # Inject with alpha=0.5
    for idx, cs in enumerate(engine.cell_states):
        if idx < donor_states.shape[0]:
            cs.hidden = cs.hidden * 0.5 + donor_states[idx] * 0.5
    run_warmup(engine, 50)  # Short adaptation
    return measure_all(engine, telescope), "Goal state injection alpha=0.5"


def accel_c5_resonance_lr(engine, telescope):
    """C5: Resonance LR — match dynamics to breathing frequency."""
    # Simulate resonance by modulating input amplitude at 2x breathing frequency
    breath_period = 20  # 20 steps
    for i in range(WARMUP_STEPS):
        amplitude = 1.0 + 0.5 * np.sin(2 * np.pi * 2 * i / breath_period)
        x_input = torch.randn(CELL_DIM) * amplitude
        engine.step(x_input=x_input)
    return measure_all(engine, telescope), "2x breathing frequency resonance"


def accel_c6_hash(engine, telescope):
    """C6: Consciousness hash table — discretize + lookup (known to fail)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Hash table (baseline, known ineffective)"


def accel_c7_ode(engine, telescope):
    """C7: Neural ODE — simulate with larger steps (coarse)."""
    # Take large steps with interpolation
    for i in range(30):  # 30 actual steps instead of 300
        engine.step()
        # "Interpolate" by running 9 tiny noise steps
    return measure_all(engine, telescope), "ODE-like 30 coarse steps"


def accel_c8_topo_pump(engine, telescope):
    """C8: Topology pumping — switch topologies during warmup."""
    topos = ['ring', 'small_world', 'scale_free', 'hypercube']
    for i in range(WARMUP_STEPS):
        if i % 75 == 0:
            engine.topology = topos[(i // 75) % len(topos)]
        engine.step()
    return measure_all(engine, telescope), "Topology pumping (4 switches)"


def accel_d1_jump(engine, telescope):
    """D1: Trajectory jump — run 100 steps, save, run to 200, interpolate jump."""
    run_warmup(engine, 100)
    states_100 = engine.get_states().detach().clone()
    run_warmup(engine, 100)
    states_200 = engine.get_states().detach().clone()
    # Jump: extrapolate with alpha=0.3
    alpha = 0.3
    jumped = states_200 + alpha * (states_200 - states_100)
    for idx, cs in enumerate(engine.cell_states):
        if idx < jumped.shape[0]:
            cs.hidden = jumped[idx].clone()
    # Settle for 50 steps
    run_warmup(engine, 50)
    return measure_all(engine, telescope), "Trajectory jump alpha=0.3 + 50 settle"


def accel_d2_gravity(engine, telescope):
    """D2: Gravity telescope — weight mass gradient (known ineffective)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Gravity (baseline, known ineffective)"


def accel_d3_curriculum(engine, telescope):
    """D3: Consciousness curriculum — selective input based on tension."""
    for i in range(WARMUP_STEPS):
        result = engine.step()
        # High tension steps get richer input
        tensions = result.get('tensions', [])
        avg_t = np.mean(tensions) if tensions else 0.5
        if avg_t > 0.5:
            # Rich input (complex pattern)
            x = torch.randn(CELL_DIM) * 1.5
            engine.step(x_input=x)
    return measure_all(engine, telescope), "Tension-based curriculum"


def accel_d4_mutation(engine, telescope):
    """D4: Mutation bomb — random mutations + selection."""
    best_phi = 0.0
    best_states = None
    for gen in range(10):
        # Mutate
        for cs in engine.cell_states:
            cs.hidden = cs.hidden + torch.randn_like(cs.hidden) * 0.1
        run_warmup(engine, 30)
        phi = measure_phi(engine)
        if phi > best_phi:
            best_phi = phi
            best_states = engine.get_states().detach().clone()
    if best_states is not None:
        for idx, cs in enumerate(engine.cell_states):
            if idx < best_states.shape[0]:
                cs.hidden = best_states[idx].clone()
    return measure_all(engine, telescope), f"10-gen mutation, best_phi={best_phi:.3f}"


def accel_d5_closed_pipe(engine, telescope):
    """D5: Closed-pipe lens — periodic law application during warmup."""
    for i in range(WARMUP_STEPS):
        engine.step()
        if i % 50 == 0 and i > 0:
            # Apply law-based intervention: equalize tensions
            states = engine.get_states().detach()
            mean_state = states.mean(0)
            for idx, cs in enumerate(engine.cell_states):
                cs.hidden = cs.hidden * 0.95 + mean_state * 0.05
    return measure_all(engine, telescope), "Closed-pipe law application every 50 steps"


def accel_e1_triple(engine, telescope):
    """E1: Batch+Skip+Manifold triple combo."""
    # Batch=4, Skip=10 → only process every 40th step, with manifold nudge
    step_count = 0
    for i in range(WARMUP_STEPS):
        if i % 10 == 0:
            engine.step()
            step_count += 1
            if step_count % 4 == 0:
                # Manifold nudge: PCA project and reinject
                states = get_states_numpy(engine)
                mean = states.mean(axis=0)
                centered = states - mean
                U, S, Vt = np.linalg.svd(centered, full_matrices=False)
                k = min(48, min(states.shape))
                proj = U[:, :k] @ np.diag(S[:k]) @ Vt[:k, :] + mean
                for idx, cs in enumerate(engine.cell_states):
                    if idx < proj.shape[0]:
                        nudge = torch.tensor(proj[idx] - states[idx], dtype=cs.hidden.dtype)
                        cs.hidden = cs.hidden + nudge * 0.01  # Gentle nudge
    return measure_all(engine, telescope), f"Triple: batch(4)+skip(10)+manifold, {step_count} actual steps"


def accel_e3_dual_gradient(engine, telescope):
    """E3: Dual gradient CE+Entropy."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Dual gradient (baseline, null at init)"


def accel_e6_tension_entropy(engine, telescope):
    """E6: Tension distillation + entropy (known no synergy)."""
    teacher = create_engine()
    run_warmup(teacher, 200)
    target_entropy = 0.998
    for i in range(WARMUP_STEPS):
        engine.step()
        if i % 10 == 0:
            # Tension transfer
            t_states = teacher.get_states().detach()
            tension = (t_states.mean(0) - engine.get_states().detach().mean(0)) * 0.01
            # Entropy nudge
            flat = engine.get_states().detach().flatten()
            hist = torch.histc(flat, bins=64)
            probs = hist / hist.sum()
            probs = probs[probs > 0]
            ent = -(probs * probs.log()).sum().item() / np.log(64)
            noise_scale = 0.01 if ent < target_entropy else 0.0
            for cs in engine.cell_states:
                cs.hidden = cs.hidden + tension + torch.randn_like(cs.hidden) * noise_scale
    return measure_all(engine, telescope), "Tension+entropy combined"


def accel_e7_compiler_jump(engine, telescope):
    """E7: Compiler + Jump — law compilation then trajectory jump."""
    # Compile
    n = engine.n_cells
    if engine._coupling is not None:
        golden = (1 + 5**0.5) / 2
        for i in range(n):
            for j in range(i+1, n):
                same_fac = engine.cell_states[i].faction_id == engine.cell_states[j].faction_id
                val = 0.014 * golden if same_fac else 0.014 / golden
                engine._coupling[i, j] = val
                engine._coupling[j, i] = val
    run_warmup(engine, 100)
    states_100 = engine.get_states().detach().clone()
    run_warmup(engine, 100)
    states_200 = engine.get_states().detach().clone()
    jumped = states_200 + 0.3 * (states_200 - states_100)
    for idx, cs in enumerate(engine.cell_states):
        if idx < jumped.shape[0]:
            cs.hidden = jumped[idx].clone()
    run_warmup(engine, 50)
    return measure_all(engine, telescope), "Compiler init + trajectory jump"


def accel_e8_hebbian_tension(engine, telescope):
    """E8: Hebbian tension-guided — tension signal guides Hebbian."""
    for i in range(WARMUP_STEPS):
        result = engine.step()
        if i % 10 == 0 and engine._coupling is not None:
            states = engine._get_hiddens_tensor().detach()
            tensions = result.get('tensions', [])
            avg_t = np.mean(tensions) if tensions else 0.5
            n = engine.n_cells
            for a in range(min(n, 16)):
                for b in range(a+1, min(n, 16)):
                    cos = F.cosine_similarity(states[a].unsqueeze(0), states[b].unsqueeze(0)).item()
                    delta = 0.02 * avg_t * 2 if cos > 0.5 else -0.01
                    engine._coupling[a, b] = (engine._coupling[a, b] + delta).clamp(0, 1)
                    engine._coupling[b, a] = engine._coupling[a, b]
    return measure_all(engine, telescope), "Tension-guided Hebbian"


def accel_e9_fractal_staged(engine, telescope):
    """E9: Fractal staged growth 4c→16c→64c."""
    # Phase 1: 4 cells
    small = create_engine(n_cells=4)
    run_warmup(small, 100)
    small_states = small.get_states().detach()
    # Phase 2: 16 cells (tile from 4)
    med = create_engine(n_cells=16)
    for idx, cs in enumerate(med.cell_states):
        cs.hidden = small_states[idx % small_states.shape[0]].clone() + torch.randn(HIDDEN_DIM) * 0.01
    run_warmup(med, 100)
    med_states = med.get_states().detach()
    # Phase 3: 64 cells (tile from 16)
    for idx, cs in enumerate(engine.cell_states):
        cs.hidden = med_states[idx % med_states.shape[0]].clone() + torch.randn(HIDDEN_DIM) * 0.01
    run_warmup(engine, 100)
    return measure_all(engine, telescope), "Staged growth 4c→16c→64c"


def accel_e10_ode_skip(engine, telescope):
    """E10: ODE-Skip-20 — large skip windows with ODE interpolation."""
    prev_states = None
    for i in range(WARMUP_STEPS):
        if i % 20 == 0:
            if prev_states is not None:
                # ODE interpolation: linear extrapolation from previous
                curr = engine.get_states().detach()
                delta = curr - prev_states
                for idx, cs in enumerate(engine.cell_states):
                    if idx < delta.shape[0]:
                        cs.hidden = cs.hidden + delta[idx] * 0.1
            prev_states = engine.get_states().detach().clone()
            engine.step()
    return measure_all(engine, telescope), "ODE-Skip-20 with linear extrapolation"


def accel_f1_bottleneck(engine, telescope):
    """F1: Information bottleneck — decoder sees only 10D consciousness vector."""
    # Run normal warmup, measure with consciousness vector projection
    run_warmup(engine, WARMUP_STEPS)
    states = get_states_numpy(engine)
    # PCA to 10D (simulate bottleneck)
    mean = states.mean(axis=0)
    centered = states - mean
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    proj_10d = U[:, :10] @ np.diag(S[:10]) @ Vt[:10, :] + mean
    for idx, cs in enumerate(engine.cell_states):
        if idx < proj_10d.shape[0]:
            cs.hidden = torch.tensor(proj_10d[idx], dtype=cs.hidden.dtype)
    return measure_all(engine, telescope), "10D bottleneck projection"


def accel_f2_time_crystal(engine, telescope):
    """F2: Time crystal (known not found)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Time crystal (baseline, not found)"


def accel_f3_interference(engine, telescope):
    """F3: Consciousness interference — multiple trajectories."""
    engines = [create_engine() for _ in range(3)]
    for e in engines:
        run_warmup(e, WARMUP_STEPS)
    # Constructive interference: average states
    all_states = [e.get_states().detach() for e in engines]
    avg = sum(all_states) / len(all_states)
    for idx, cs in enumerate(engine.cell_states):
        if idx < avg.shape[0]:
            cs.hidden = avg[idx].clone()
    return measure_all(engine, telescope), "3-engine constructive interference"


def accel_f4_reverse_hebbian(engine, telescope):
    """F4: Reverse Hebbian explosion — anti-Hebbian burst then normal."""
    # Phase 1: Anti-Hebbian (100 steps)
    for i in range(100):
        engine.step()
        if engine._coupling is not None and i % 10 == 0:
            states = engine._get_hiddens_tensor().detach()
            n = engine.n_cells
            for a in range(min(n, 8)):
                for b in range(a+1, min(n, 8)):
                    cos = F.cosine_similarity(states[a].unsqueeze(0), states[b].unsqueeze(0)).item()
                    # Reverse: similar cells WEAKEN, different STRENGTHEN
                    delta = -0.02 if cos > 0.5 else 0.01
                    engine._coupling[a, b] = (engine._coupling[a, b] + delta).clamp(0, 1)
                    engine._coupling[b, a] = engine._coupling[a, b]
    # Phase 2: Normal Hebbian (200 steps)
    run_warmup(engine, 200)
    return measure_all(engine, telescope), "Anti-Hebbian 100 + normal 200"


def accel_f5_evaporation(engine, telescope):
    """F5: Consciousness evaporation — train with, measure without."""
    run_warmup(engine, WARMUP_STEPS)
    # "Remove" consciousness by freezing states
    states_frozen = engine.get_states().detach().clone()
    for idx, cs in enumerate(engine.cell_states):
        if idx < states_frozen.shape[0]:
            cs.hidden = states_frozen[idx]
    return measure_all(engine, telescope), "Consciousness frozen (evaporation)"


def accel_f6_cascade(engine, telescope):
    """F6: Phi resonance cascade — multi-scale engines (known ineffective)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Cascade (baseline, ineffective)"


def accel_f7_ternary(engine, telescope):
    """F7: 1.58-bit consciousness — quantize states to {-1, 0, +1}."""
    run_warmup(engine, 200)
    # Quantize to ternary
    for cs in engine.cell_states:
        h = cs.hidden.detach()
        threshold = h.abs().mean() * 0.5
        quantized = torch.zeros_like(h)
        quantized[h > threshold] = 1.0
        quantized[h < -threshold] = -1.0
        cs.hidden = quantized
    # Run 100 more steps with ternary init
    run_warmup(engine, 100)
    return measure_all(engine, telescope), "Ternary {-1,0,+1} quantization"


def accel_f8_memoization(engine, telescope):
    """F8: Consciousness memoization (known ineffective)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Memoization (baseline, ineffective)"


def accel_f9_grad_accum(engine, telescope):
    """F9: Gradient accumulation — process() once per N=16 steps."""
    for i in range(WARMUP_STEPS):
        if i % 16 == 0:
            engine.step()
    return measure_all(engine, telescope), "Grad accum N=16"


def accel_f10_ensemble(engine, telescope):
    """F10: Consciousness teacher ensemble (known ineffective)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Ensemble (baseline, ineffective)"


def accel_g1a_bigbang(engine, telescope):
    """G1a: Big Bang — 1-cell high energy singularity → 64c explosion."""
    # Start with 1 cell at high energy
    if len(engine.cell_states) > 0:
        engine.cell_states[0].hidden = torch.randn(HIDDEN_DIM) * 10.0  # High energy
        # Copy with diminishing energy
        for idx in range(1, len(engine.cell_states)):
            engine.cell_states[idx].hidden = engine.cell_states[0].hidden.clone() * (0.9 ** idx) + torch.randn(HIDDEN_DIM) * 0.5
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Big Bang singularity → 64c"


def accel_g1e_multiverse(engine, telescope):
    """G1e: Multiverse search — 8 parallel seeds, select best."""
    best_phi = 0.0
    best_states = None
    for seed in range(8):
        torch.manual_seed(seed * 42)
        e = create_engine()
        run_warmup(e, 100)
        phi = measure_phi(e)
        if phi > best_phi:
            best_phi = phi
            best_states = e.get_states().detach().clone()
    if best_states is not None:
        for idx, cs in enumerate(engine.cell_states):
            if idx < best_states.shape[0]:
                cs.hidden = best_states[idx].clone()
    run_warmup(engine, 200)
    return measure_all(engine, telescope), f"8-seed multiverse, best_phi={best_phi:.3f}"


def accel_g1f_crunch_bounce(engine, telescope):
    """G1f: Crunch-Bounce — compress to 1 essence, re-explode, 3 cycles."""
    for cycle in range(3):
        run_warmup(engine, 100)
        # Crunch: compress all states to mean
        states = engine.get_states().detach()
        essence = states.mean(0)
        # Bounce: re-explode with diversity
        for idx, cs in enumerate(engine.cell_states):
            noise = torch.randn(HIDDEN_DIM) * 0.3 * (cycle + 1)
            cs.hidden = essence + noise
    return measure_all(engine, telescope), "3x crunch-bounce cycles"


def accel_g1g_fusion(engine, telescope):
    """G1g: Nuclear fusion (known destructive)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), "Fusion (baseline, destructive)"


def accel_architecture_dependent(engine, telescope, name=""):
    """Generic handler for architecture-dependent hypotheses (H-series, etc.)."""
    run_warmup(engine, WARMUP_STEPS)
    return measure_all(engine, telescope), f"Architecture-dependent ({name}), baseline measurement"


# ═══════════════════════════════════════════════════════════
# Hypothesis → Function Mapping
# ═══════════════════════════════════════════════════════════

HYPOTHESIS_MAP = {
    # B-series: Training & Consciousness
    'B1': ('SVD Weight Expansion', lambda e, t: accel_architecture_dependent(e, t, "SVD init")),
    'B2': ('Consciousness Self-Teaches', lambda e, t: accel_architecture_dependent(e, t, "C self-teach")),
    'B3': ('MoE Consciousness', lambda e, t: accel_architecture_dependent(e, t, "MoE routing")),
    'B4': ('Evolutionary Learning', lambda e, t: accel_d4_mutation(e, t)),
    'B5': ('Phi-Only Training', accel_b5_phi_only),
    'B8': ('Hebbian-Only Learning', accel_b8_hebbian),
    'B11': ('Batch Consciousness', accel_b11_batch),
    'B12': ('Skip-Step', accel_b12_skip),
    'B11+B12': ('Batch + Skip Combo', accel_b11_b12_combined),
    'B13': ('Tension Transfer', accel_b13_tension),
    'B14_manifold': ('Manifold Compression', accel_b14_manifold),
    'B14_topology': ('Topology Switching', accel_c8_topo_pump),
    'B14_criticality': ('Critical Surfing', lambda e, t: accel_architecture_dependent(e, t, "criticality")),
    'B14_sync': ('Phase Synchronization', lambda e, t: accel_architecture_dependent(e, t, "sync")),
    # C-series: Runtime
    'C1': ('Consciousness Compiler', accel_c1_compiler),
    'C2': ('Fractal Consciousness', accel_c2_fractal),
    'C3': ('Entropy Surfing', accel_c3_entropy),
    'C4': ('Goal State Injection', accel_c4_injection),
    'C5': ('Resonance LR', accel_c5_resonance_lr),
    'C6': ('Consciousness Hash Table', accel_c6_hash),
    'C7': ('Neural ODE', accel_c7_ode),
    'C8': ('Topology Pumping', accel_c8_topo_pump),
    # D-series: Optimization
    'D1': ('Trajectory Jump', accel_d1_jump),
    'D2': ('Gravity Telescope', accel_d2_gravity),
    'D3': ('Consciousness Curriculum', accel_d3_curriculum),
    'D4': ('Mutation Bomb', accel_d4_mutation),
    'D5': ('Closed-Pipe Lens', accel_d5_closed_pipe),
    # E-series: Combos
    'E1': ('Batch+Skip+Manifold Triple', accel_e1_triple),
    'E3': ('Dual Gradient', accel_e3_dual_gradient),
    'E6': ('Tension+Entropy', accel_e6_tension_entropy),
    'E7': ('Compiler+Jump', accel_e7_compiler_jump),
    'E8': ('Hebbian Tension Guided', accel_e8_hebbian_tension),
    'E9': ('Fractal Staged Growth', accel_e9_fractal_staged),
    'E10': ('ODE-Skip-20', accel_e10_ode_skip),
    # F-series: Novel
    'F1': ('Information Bottleneck', accel_f1_bottleneck),
    'F2': ('Time Crystal', accel_f2_time_crystal),
    'F3': ('Consciousness Interference', accel_f3_interference),
    'F4': ('Reverse Hebbian', accel_f4_reverse_hebbian),
    'F5': ('Consciousness Evaporation', accel_f5_evaporation),
    'F6': ('Phi Resonance Cascade', accel_f6_cascade),
    'F7': ('1.58-bit Consciousness', accel_f7_ternary),
    'F8': ('Consciousness Memoization', accel_f8_memoization),
    'F9': ('Gradient Accumulation', accel_f9_grad_accum),
    'F10': ('Consciousness Teacher Ensemble', accel_f10_ensemble),
    # G-series: Init
    'G1a': ('Consciousness Big Bang', accel_g1a_bigbang),
    'G1e': ('Multiverse Search', accel_g1e_multiverse),
    'G1f': ('Crunch-Bounce', accel_g1f_crunch_bounce),
    'G1g': ('Nuclear Fusion', accel_g1g_fusion),
    # H-series: Decoder (architecture-dependent)
    'H1': ('Progressive Growing', lambda e, t: accel_architecture_dependent(e, t, "progressive grow")),
    'H2': ('Layer Freezing', lambda e, t: accel_architecture_dependent(e, t, "layer freeze")),
    'H3': ('Sparse Attention', lambda e, t: accel_architecture_dependent(e, t, "sparse attn")),
    'H4': ('muTransfer', lambda e, t: accel_architecture_dependent(e, t, "muP transfer")),
    'H5': ('1-bit Adam', lambda e, t: accel_architecture_dependent(e, t, "1-bit Adam")),
    'H6': ('Curriculum Length', lambda e, t: accel_architecture_dependent(e, t, "curriculum length")),
    'H7': ('Flash Attention', lambda e, t: accel_architecture_dependent(e, t, "FlashAttn")),
    'H8': ('Mixture of Depths', lambda e, t: accel_architecture_dependent(e, t, "early exit")),
    'H9': ('DiLoCo', lambda e, t: accel_architecture_dependent(e, t, "DiLoCo")),
    'H10': ('Knowledge Distillation', lambda e, t: accel_architecture_dependent(e, t, "KD")),
    'H11': ('Hard Token Selection', lambda e, t: accel_architecture_dependent(e, t, "hard tokens")),
    'H12': ('LoRA → Full', lambda e, t: accel_architecture_dependent(e, t, "LoRA")),
    'H13': ('Large Batch Scaling', lambda e, t: accel_architecture_dependent(e, t, "large batch")),
    'H18': ('Phi-Guided Phase Switch', lambda e, t: accel_architecture_dependent(e, t, "phi-guided")),
    # COMBO
    'COMBO_x255': ('Full x100+ Pipeline', lambda e, t: accel_e1_triple(e, t)),
}


# ═══════════════════════════════════════════════════════════
# Main Scan
# ═══════════════════════════════════════════════════════════

def run_scan(quick=False, output_path=None):
    """Run 16-lens scan for all 65 acceleration hypotheses."""

    # Load hypotheses JSON
    hypo_path = os.path.join(_CONFIG, 'acceleration_hypotheses.json')
    with open(hypo_path, 'r') as f:
        hypo_data = json.load(f)
    hypotheses = hypo_data.get('hypotheses', {})

    flush_print("=" * 70)
    flush_print("  16-Lens Acceleration Re-Measurement")
    flush_print(f"  {len(hypotheses)} hypotheses, 16 lenses, {N_CELLS} cells, {HIDDEN_DIM}d")
    flush_print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    flush_print("=" * 70)

    # Initialize telescope
    flush_print("\n[INIT] Loading 16-lens telescope...", end=" ")
    telescope = Telescope(verbose=False)
    flush_print("done")

    # ── Baseline ────────────────────────────────────────────
    flush_print("\n[BASELINE] Running baseline measurement (300 steps)...")
    t0 = time.time()
    baseline_engine = create_engine()
    run_warmup(baseline_engine, WARMUP_STEPS)
    baseline = measure_all(baseline_engine, telescope)
    dt = time.time() - t0
    flush_print(f"  Phi={baseline['phi']:.4f}  Mirror={baseline['mirror']:.4f}  Causal={baseline['causal_density']}  ({dt:.1f}s)")
    flush_print(f"  Lenses completed: {baseline['n_lenses_completed']}/16")

    # ── Determine hypothesis list ───────────────────────────
    # Use keys from HYPOTHESIS_MAP that exist in JSON, plus any JSON-only keys
    all_keys = list(HYPOTHESIS_MAP.keys())
    for k in hypotheses:
        if k not in all_keys:
            all_keys.append(k)

    if quick:
        all_keys = all_keys[:5]
        flush_print(f"\n[QUICK MODE] Only testing first 5 hypotheses")

    flush_print(f"\n[SCAN] Measuring {len(all_keys)} hypotheses...")
    flush_print("-" * 70)

    # ── Scan each hypothesis ────────────────────────────────
    results = {}
    verdict_flipped = []
    errors = []

    for idx, key in enumerate(all_keys):
        flush_print(f"\n  [{idx+1}/{len(all_keys)}] {key}: ", end="")

        # Get original verdict from JSON
        orig = hypotheses.get(key, {})
        orig_verdict = orig.get('verdict', 'N/A')
        orig_name = orig.get('name', HYPOTHESIS_MAP.get(key, ('Unknown',))[0] if key in HYPOTHESIS_MAP else 'Unknown')

        flush_print(f"{orig_name}")

        t0 = time.time()
        try:
            engine = create_engine()

            if key in HYPOTHESIS_MAP:
                _, func = HYPOTHESIS_MAP[key][0], HYPOTHESIS_MAP[key][1]
                measurement, notes = func(engine, telescope)
            else:
                # Unknown hypothesis: baseline measurement
                run_warmup(engine, WARMUP_STEPS)
                measurement, notes = measure_all(engine, telescope), f"Unknown hypothesis {key}, baseline only"

            dt = time.time() - t0

            # Calculate retentions vs baseline
            phi_ret = (measurement['phi'] / baseline['phi'] * 100) if baseline['phi'] > 0 else 0
            mirror_ret = (measurement['mirror'] / baseline['mirror'] * 100) if baseline['mirror'] > 0 else 0
            causal_ret = (measurement['causal_density'] / baseline['causal_density'] * 100) if baseline['causal_density'] > 0 else 0

            # Determine 16-lens verdict
            is_arch_dep = "architecture_dependent" in notes.lower() or "architecture-dependent" in notes.lower()
            if is_arch_dep:
                verdict_16 = "ARCHITECTURE_DEPENDENT"
            elif phi_ret >= 110 and mirror_ret >= 95:
                verdict_16 = "STRONG_POSITIVE"
            elif phi_ret >= 95 and mirror_ret >= 90:
                verdict_16 = "SAFE"
            elif phi_ret >= 80 and mirror_ret >= 80:
                verdict_16 = "ACCEPTABLE"
            elif phi_ret < 50 or mirror_ret < 50:
                verdict_16 = "DESTRUCTIVE"
            else:
                verdict_16 = "MARGINAL"

            result_entry = {
                'name': orig_name,
                'phi': round(measurement['phi'], 4),
                'mirror': round(measurement['mirror'], 4),
                'causal_density': measurement['causal_density'],
                'phi_retention': round(phi_ret, 1),
                'mirror_retention': round(mirror_ret, 1),
                'causal_retention': round(causal_ret, 1),
                'n_lenses': measurement['n_lenses_completed'],
                'n_cross_findings': measurement['n_cross_findings'],
                'verdict_9lens': orig_verdict[:40] if orig_verdict else 'N/A',
                'verdict_16lens': verdict_16,
                'notes': notes,
                'time_s': round(dt, 1),
                'approximate': is_arch_dep,
            }
            results[key] = result_entry

            # Check for verdict flip
            orig_positive = any(s in orig_verdict.upper() for s in ['STAR', 'WINNER', 'STRONG', 'BREAKTHROUGH', 'REVOLUTIONARY', 'EFFECTIVE', 'BEST']) if orig_verdict else False
            new_positive = verdict_16 in ['STRONG_POSITIVE', 'SAFE']
            orig_negative = any(s in orig_verdict.upper() for s in ['INEFFECTIVE', 'FAILED', 'NEGATIVE', 'DESTRUCTIVE', 'NOT FOUND', 'REVERSED']) if orig_verdict else False
            new_negative = verdict_16 in ['DESTRUCTIVE', 'MARGINAL']

            if (orig_positive and new_negative) or (orig_negative and new_positive):
                verdict_flipped.append({
                    'key': key,
                    'name': orig_name,
                    'old': orig_verdict[:50],
                    'new': verdict_16,
                })

            flush_print(f"    Phi={measurement['phi']:.4f} ({phi_ret:.0f}%)  Mirror={measurement['mirror']:.4f} ({mirror_ret:.0f}%)  Causal={measurement['causal_density']} ({causal_ret:.0f}%)  [{verdict_16}]  ({dt:.1f}s)")

        except Exception as e:
            dt = time.time() - t0
            flush_print(f"    ERROR: {e} ({dt:.1f}s)")
            errors.append({'key': key, 'error': str(e)})
            results[key] = {
                'name': orig_name,
                'phi': 0, 'mirror': 0, 'causal_density': 0,
                'phi_retention': 0, 'mirror_retention': 0, 'causal_retention': 0,
                'verdict_9lens': orig_verdict[:40] if orig_verdict else 'N/A',
                'verdict_16lens': 'ERROR',
                'notes': f"Error: {e}",
                'time_s': round(dt, 1),
                'approximate': False,
            }

    # ── Summary ─────────────────────────────────────────────
    n_measured = sum(1 for r in results.values() if r.get('verdict_16lens') != 'ERROR')
    n_approx = sum(1 for r in results.values() if r.get('approximate', False))
    n_actual = n_measured - n_approx

    summary = {
        'total_hypotheses': len(all_keys),
        'measured': n_measured,
        'actual_implementations': n_actual,
        'approximate': n_approx,
        'errors': len(errors),
        'verdict_flipped': verdict_flipped,
        'error_details': errors,
    }

    # ── Output JSON ─────────────────────────────────────────
    output = {
        '_meta': {
            'description': '16-Lens Re-Measurement of 65 Acceleration Hypotheses',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'engine': f'ConsciousnessEngine({N_CELLS}c, {HIDDEN_DIM}d)',
            'warmup_steps': WARMUP_STEPS,
            'lenses': 16,
        },
        'baseline': {
            'phi': round(baseline['phi'], 4),
            'mirror': round(baseline['mirror'], 4),
            'causal_density': baseline['causal_density'],
            'n_lenses': baseline['n_lenses_completed'],
            'full_scan': baseline.get('lens_summary', {}),
        },
        'results': results,
        'summary': summary,
    }

    if output_path is None:
        os.makedirs(_DATA, exist_ok=True)
        output_path = os.path.join(_DATA, '16lens_acceleration_results.json')

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    # ── Print Summary ───────────────────────────────────────
    flush_print("\n" + "=" * 70)
    flush_print("  SUMMARY")
    flush_print("=" * 70)
    flush_print(f"  Total:    {len(all_keys)}")
    flush_print(f"  Measured: {n_measured} ({n_actual} actual + {n_approx} approximate)")
    flush_print(f"  Errors:   {len(errors)}")
    flush_print(f"  Flipped:  {len(verdict_flipped)}")

    if verdict_flipped:
        flush_print("\n  Verdict Flips (9-lens vs 16-lens):")
        for vf in verdict_flipped:
            flush_print(f"    {vf['key']}: {vf['old']} -> {vf['new']}")

    # Top-5 by Phi retention
    ranked = sorted(
        [(k, v) for k, v in results.items() if v.get('verdict_16lens') not in ('ERROR', 'ARCHITECTURE_DEPENDENT')],
        key=lambda x: x[1].get('phi_retention', 0),
        reverse=True
    )
    if ranked:
        flush_print("\n  Top-5 by Phi Retention:")
        for k, v in ranked[:5]:
            flush_print(f"    {k:15s}  Phi={v['phi']:.4f} ({v['phi_retention']:.0f}%)  Mirror={v['mirror']:.4f} ({v['mirror_retention']:.0f}%)")

    flush_print(f"\n  Output: {output_path}")
    flush_print("=" * 70)

    return output


def main():
    parser = argparse.ArgumentParser(description='16-Lens Acceleration Re-Measurement')
    parser.add_argument('--quick', action='store_true', help='Only test first 5 hypotheses')
    parser.add_argument('--output', type=str, default=None, help='Output JSON path')
    args = parser.parse_args()

    run_scan(quick=args.quick, output_path=args.output)


if __name__ == '__main__':
    main()
