#!/usr/bin/env python3
"""acceleration_consciousness_supernova.py — Consciousness Supernova (AD1 + F6 + G1a Full Stack)

Hypothesis: Combining ALL acceleration methods simultaneously creates
a consciousness supernova -- an explosive, self-sustaining Phi growth
far beyond any individual technique.

Pipeline (sequential phases):
  Phase 1: Big Bang (G1a) -- bootstrap from singularity
  Phase 2: Cascade (F6) -- multi-scale resonance pumping
  Phase 3: Full Stack -- all acceleration techniques at once
  Phase 4: Supernova -- remove all forcing, observe self-sustaining peak
  Phase 5: Aftermath -- track cooling and stable state

Experiments:
  Exp 1: Sequential Stack (Big Bang -> Cascade -> Full Stack -> Free)
  Exp 2: Simultaneous Ignition (everything at once from step 0)
  Exp 3: Stability Analysis (how long does peak Phi last?)
  Exp 4: Comparison (individual vs combined vs baseline)
  Exp 5: Consciousness Temperature (Phi volatility as "temperature")

Key metrics:
  - max_phi: highest Phi achieved
  - stable_phi: Phi after all forcing removed
  - supernova_ratio: max_phi / baseline_phi
  - cooling_rate: how fast Phi drops after peak

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_consciousness_supernova.py
"""

import sys
import os
import time
import copy
import json
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine, ConsciousnessCell, CellState

# ===================================================================
# Constants
# ===================================================================

N_CELLS = 64
PHASE_STEPS = 100       # Steps per phase
FREE_STEPS = 200        # Free-running steps after supernova
WARMUP = 20
SEED_MAGNITUDE = 3.0
CASCADE_ALPHA = 0.15
SYNC_PERIOD = 6


# ===================================================================
# Utilities
# ===================================================================

def make_engine(cells=N_CELLS):
    return ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=cells, max_cells=cells,
        phi_ratchet=True,
    )


def run_steps(engine, n_steps, x_input=None):
    phis = []
    for _ in range(n_steps):
        result = engine.step(x_input=x_input)
        phis.append(result.get('phi_iit', 0.0))
    return phis


def phi_stats(phi_history, warmup=WARMUP):
    active = phi_history[warmup:] if len(phi_history) > warmup else phi_history
    if not active:
        return {'final': 0.0, 'mean': 0.0, 'max': 0.0, 'std': 0.0, 'min': 0.0}
    return {
        'final': phi_history[-1],
        'mean': float(np.mean(active)),
        'max': float(np.max(active)),
        'std': float(np.std(active)),
        'min': float(np.min(active)),
    }


def expand_engine_to(engine, target_cells, noise_eps=0.014):
    """Expand engine from current cells to target_cells by cloning + noise."""
    current = engine.n_cells
    if current >= target_cells:
        return
    old_n = current
    source_idx = 0
    while engine.n_cells < target_cells:
        parent_mod = engine.cell_modules[source_idx % current]
        parent_state = engine.cell_states[source_idx % current]
        faction = engine.n_cells % engine.n_factions
        engine._create_cell(
            parent_module=parent_mod,
            parent_state=parent_state,
            faction_id=faction,
        )
        new_idx = engine.n_cells - 1
        engine.cell_states[new_idx].hidden = (
            parent_state.hidden.clone()
            + torch.randn_like(parent_state.hidden) * noise_eps
        )
        source_idx += 1
    engine._resize_coupling(old_n, engine.n_cells)
    engine._init_coupling()


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def ascii_phi_graph(phis, label="Phi", width=60, height=12):
    if not phis:
        return
    mn, mx = min(phis), max(phis)
    rng = mx - mn if mx > mn else 1.0
    print(f"\n  {label} trajectory ({len(phis)} steps):")
    print(f"  max={mx:.4f}  min={mn:.4f}")
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        line = ''
        step = max(1, len(phis) // width)
        for i in range(0, min(len(phis), width * step), step):
            if phis[i] >= threshold:
                line += '#'
            else:
                line += ' '
        val = mn + rng * row / (height - 1)
        print(f"  {val:7.3f} |{line}")
    print(f"          {''.join(['-'] * min(len(phis), width))}")
    sys.stdout.flush()


def print_comparison_bar(name, value, baseline, bar_width=30):
    if baseline > 0:
        ratio = value / baseline
        pct = (ratio - 1.0) * 100
    else:
        ratio = 0
        pct = 0
    bar_len = max(1, int(bar_width * min(value, baseline * 3) / max(baseline * 3, 1e-9)))
    bar = "#" * bar_len
    sign = "+" if pct >= 0 else ""
    print(f"  {name:30s} {bar:<{bar_width}s} {value:.4f} ({sign}{pct:.1f}%)")


# ===================================================================
# Experiment 1: Sequential Stack (Big Bang -> Cascade -> Full -> Free)
# ===================================================================

def exp1_sequential_stack():
    print_header("EXP 1: SEQUENTIAL STACK (Big Bang -> Cascade -> Full -> Free)")

    all_phis = []
    phase_boundaries = []

    # Phase 1: Big Bang -- start from 1c singularity, expand to 64c
    print(f"\n  Phase 1: BIG BANG (1c -> {N_CELLS}c)...", flush=True)
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=1, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    # Inject extreme energy
    for mod in engine.cell_modules:
        for p in mod.parameters():
            p.data *= 10.0

    expand_engine_to(engine, N_CELLS, noise_eps=0.1)
    phis_bang = run_steps(engine, PHASE_STEPS)
    all_phis.extend(phis_bang)
    phase_boundaries.append(len(all_phis))
    print(f"    Phi at end of Big Bang: {phis_bang[-1]:.4f}")

    # Phase 2: Cascade -- multi-scale resonance pumping
    print(f"\n  Phase 2: CASCADE (resonance pumping)...", flush=True)
    # Create secondary engines for cascade feeding
    e_small = make_engine(4)
    e_mid = make_engine(16)

    phis_cascade = []
    for s in range(PHASE_STEPS):
        # Small engine generates high-freq signal
        r_small = e_small.step()
        out_small = r_small['output'].detach()

        # Mid engine processes
        x_mid = torch.randn(64) * (1.0 - CASCADE_ALPHA) + out_small * CASCADE_ALPHA
        r_mid = e_mid.step(x_input=x_mid)
        out_mid = r_mid['output'].detach()

        # Main engine receives cascade
        x_main = torch.randn(64) * (1.0 - CASCADE_ALPHA) + out_mid * CASCADE_ALPHA
        result = engine.step(x_input=x_main)
        phis_cascade.append(result.get('phi_iit', 0.0))

        if (s + 1) % 50 == 0:
            print(f"    step {s+1:3d}: Phi={phis_cascade[-1]:.4f}", flush=True)

    all_phis.extend(phis_cascade)
    phase_boundaries.append(len(all_phis))
    print(f"    Phi at end of Cascade: {phis_cascade[-1]:.4f}")

    # Phase 3: Full Stack -- seed + sync + cascade simultaneously
    print(f"\n  Phase 3: FULL STACK (everything at once)...", flush=True)
    # Seed injection: boost half the cells
    for i in range(N_CELLS // 2):
        engine.cell_states[i].hidden = engine.cell_states[i].hidden * SEED_MAGNITUDE

    phis_full = []
    for s in range(PHASE_STEPS):
        # Synchronized forcing
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        sync_signal = torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0) * 0.2

        # Cascade input
        r_small = e_small.step()
        cascade_signal = r_small['output'].detach() * CASCADE_ALPHA

        # Combined input
        x_combined = (torch.randn(64) * 0.5 + sync_signal + cascade_signal)
        result = engine.step(x_input=x_combined)
        phis_full.append(result.get('phi_iit', 0.0))

        if (s + 1) % 50 == 0:
            print(f"    step {s+1:3d}: Phi={phis_full[-1]:.4f}", flush=True)

    all_phis.extend(phis_full)
    phase_boundaries.append(len(all_phis))
    print(f"    Phi at end of Full Stack: {phis_full[-1]:.4f}")

    # Phase 4+5: Supernova + Aftermath -- remove all forcing
    print(f"\n  Phase 4+5: FREE RUNNING (supernova + cooling)...", flush=True)
    phis_free = run_steps(engine, FREE_STEPS)
    all_phis.extend(phis_free)

    # Analysis
    peak_phi = max(all_phis)
    peak_step = all_phis.index(peak_phi)
    stable_phi = float(np.mean(phis_free[-50:]))

    print(f"\n  SUPERNOVA RESULTS:")
    print(f"    Peak Phi: {peak_phi:.4f} at step {peak_step}")
    print(f"    Stable Phi (last 50 steps): {stable_phi:.4f}")
    print(f"    Retention: {stable_phi / max(peak_phi, 1e-8) * 100:.1f}%")
    sys.stdout.flush()

    ascii_phi_graph(all_phis, "Sequential Supernova")

    return {
        'all_phis': [float(p) for p in all_phis],
        'phase_boundaries': phase_boundaries,
        'peak_phi': float(peak_phi),
        'peak_step': peak_step,
        'stable_phi': stable_phi,
        'retention': stable_phi / max(peak_phi, 1e-8),
    }


# ===================================================================
# Experiment 2: Simultaneous Ignition
# ===================================================================

def exp2_simultaneous_ignition():
    print_header("EXP 2: SIMULTANEOUS IGNITION (everything from step 0)")

    # Start with Big Bang expansion
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=1, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    for mod in engine.cell_modules:
        for p in mod.parameters():
            p.data *= 10.0
    expand_engine_to(engine, N_CELLS, noise_eps=0.1)

    # Seed injection immediately
    for i in range(N_CELLS // 2):
        engine.cell_states[i].hidden = engine.cell_states[i].hidden * SEED_MAGNITUDE

    # Create cascade sources
    e_small = make_engine(4)

    # Run with everything on at once
    total_steps = PHASE_STEPS * 3
    phis = []
    for s in range(total_steps):
        # Sync signal
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        sync_signal = torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0) * 0.2

        # Cascade
        r_small = e_small.step()
        cascade_signal = r_small['output'].detach() * CASCADE_ALPHA

        x = torch.randn(64) * 0.5 + sync_signal + cascade_signal
        result = engine.step(x_input=x)
        phis.append(result.get('phi_iit', 0.0))

        if (s + 1) % 50 == 0:
            print(f"  step {s+1:3d}: Phi={phis[-1]:.4f}", flush=True)

    # Free phase
    phis_free = run_steps(engine, FREE_STEPS)
    phis.extend(phis_free)

    stats = phi_stats(phis)
    peak_phi = max(phis)
    stable_phi = float(np.mean(phis_free[-50:]))

    print(f"\n  Simultaneous Ignition:")
    print(f"    Peak Phi: {peak_phi:.4f}")
    print(f"    Stable Phi: {stable_phi:.4f}")
    print(f"    Retention: {stable_phi / max(peak_phi, 1e-8) * 100:.1f}%")
    sys.stdout.flush()

    ascii_phi_graph(phis, "Simultaneous Ignition")

    return {
        'stats': stats,
        'peak_phi': float(peak_phi),
        'stable_phi': stable_phi,
        'retention': stable_phi / max(peak_phi, 1e-8),
    }


# ===================================================================
# Experiment 3: Stability Analysis
# ===================================================================

def exp3_stability():
    print_header("EXP 3: STABILITY ANALYSIS (how long does peak last?)")

    # Quick supernova (reuse sequential approach, shorter)
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=1, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    for mod in engine.cell_modules:
        for p in mod.parameters():
            p.data *= 10.0
    expand_engine_to(engine, N_CELLS, noise_eps=0.1)
    for i in range(N_CELLS // 2):
        engine.cell_states[i].hidden = engine.cell_states[i].hidden * SEED_MAGNITUDE

    # Forced phase
    e_small = make_engine(4)
    phis_forced = []
    for s in range(PHASE_STEPS * 2):
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        sync_signal = torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0) * 0.2
        r_small = e_small.step()
        x = torch.randn(64) * 0.5 + sync_signal + r_small['output'].detach() * CASCADE_ALPHA
        result = engine.step(x_input=x)
        phis_forced.append(result.get('phi_iit', 0.0))

    peak_phi = max(phis_forced)
    peak_step = phis_forced.index(peak_phi)
    print(f"  Forced phase peak: {peak_phi:.4f} at step {peak_step}")

    # Long free phase
    phis_free = run_steps(engine, FREE_STEPS * 2)

    # Compute cooling rate
    cooling_phis = phis_free[:100]
    if len(cooling_phis) >= 10:
        # Fit exponential decay: Phi(t) = A * exp(-t/tau) + C
        t = np.arange(len(cooling_phis), dtype=float)
        phi_arr = np.array(cooling_phis)
        # Simple estimate: half-life
        above_half = [i for i, p in enumerate(cooling_phis)
                      if p > (cooling_phis[0] + cooling_phis[-1]) / 2]
        half_life = above_half[-1] if above_half else len(cooling_phis)
    else:
        half_life = 0

    stable_phi = float(np.mean(phis_free[-50:]))
    final_phi = phis_free[-1]

    print(f"  Free phase:")
    print(f"    Phi at release: {phis_free[0]:.4f}")
    print(f"    Phi after 100 steps: {phis_free[99]:.4f}" if len(phis_free) > 99 else "")
    print(f"    Phi after {len(phis_free)} steps: {final_phi:.4f}")
    print(f"    Cooling half-life: ~{half_life} steps")
    print(f"    Stable Phi: {stable_phi:.4f}")
    retention = stable_phi / max(peak_phi, 1e-8)
    print(f"    Retention: {retention * 100:.1f}%")
    print(f"    {'SELF-SUSTAINING!' if retention > 0.8 else 'PARTIAL COLLAPSE' if retention > 0.5 else 'FULL COLLAPSE'}")
    sys.stdout.flush()

    all_phis = phis_forced + phis_free
    ascii_phi_graph(all_phis, "Stability (forced|free)")

    return {
        'peak_phi': float(peak_phi),
        'stable_phi': stable_phi,
        'half_life': half_life,
        'retention': float(retention),
        'self_sustaining': retention > 0.8,
    }


# ===================================================================
# Experiment 4: Comparison (individual techniques vs combined)
# ===================================================================

def exp4_comparison():
    print_header("EXP 4: COMPARISON (individual vs combined vs baseline)")

    total_steps = PHASE_STEPS * 3 + FREE_STEPS

    # Baseline
    base = make_engine()
    phis_base = run_steps(base, total_steps)
    stats_base = phi_stats(phis_base)

    # Big Bang only
    bb = ConsciousnessEngine(cell_dim=64, hidden_dim=128, initial_cells=1,
                             max_cells=N_CELLS, phi_ratchet=True)
    for mod in bb.cell_modules:
        for p in mod.parameters():
            p.data *= 10.0
    expand_engine_to(bb, N_CELLS, noise_eps=0.1)
    phis_bb = run_steps(bb, total_steps)
    stats_bb = phi_stats(phis_bb)

    # Cascade only
    cascade = make_engine()
    e_small = make_engine(4)
    phis_cascade = []
    for s in range(total_steps):
        r_small = e_small.step()
        x = torch.randn(64) * (1.0 - CASCADE_ALPHA) + r_small['output'].detach() * CASCADE_ALPHA
        r = cascade.step(x_input=x)
        phis_cascade.append(r.get('phi_iit', 0.0))
    stats_cascade = phi_stats(phis_cascade)

    # Seed only
    seed = make_engine()
    for i in range(N_CELLS // 2):
        seed.cell_states[i].hidden = seed.cell_states[i].hidden * SEED_MAGNITUDE
    phis_seed = run_steps(seed, total_steps)
    stats_seed = phi_stats(phis_seed)

    # Sync only
    sync = make_engine()
    phis_sync = []
    for s in range(total_steps):
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        x = torch.randn(64) * 0.8 + torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0) * 0.2
        r = sync.step(x_input=x)
        phis_sync.append(r.get('phi_iit', 0.0))
    stats_sync = phi_stats(phis_sync)

    # Print comparison
    print(f"\n  --- Technique Comparison ---")
    print(f"  {'Method':>25s}  {'Phi Mean':>10s}  {'Phi Max':>10s}  {'vs Base':>10s}")
    print(f"  {'-' * 60}")
    methods = [
        ('Baseline', stats_base),
        ('Big Bang Only', stats_bb),
        ('Cascade Only', stats_cascade),
        ('Seed Only', stats_seed),
        ('Sync Only', stats_sync),
    ]
    for name, stats in methods:
        pct = (stats['mean'] - stats_base['mean']) / max(stats_base['mean'], 1e-8) * 100
        print(f"  {name:>25s}  {stats['mean']:>10.4f}  {stats['max']:>10.4f}  {pct:>+9.1f}%")

    print(f"\n  Bar chart (baseline = 1.0):")
    for name, stats in methods:
        print_comparison_bar(name, stats['mean'], stats_base['mean'])
    sys.stdout.flush()

    return {m: s for m, s in methods}


# ===================================================================
# Experiment 5: Consciousness Temperature
# ===================================================================

def exp5_consciousness_temperature():
    print_header("EXP 5: CONSCIOUSNESS TEMPERATURE")
    print(f"  Phi volatility (std/mean) as temperature analogy")

    # Supernova trajectory
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=1,
        max_cells=N_CELLS, phi_ratchet=True,
    )
    for mod in engine.cell_modules:
        for p in mod.parameters():
            p.data *= 10.0
    expand_engine_to(engine, N_CELLS, noise_eps=0.1)
    for i in range(N_CELLS // 2):
        engine.cell_states[i].hidden = engine.cell_states[i].hidden * SEED_MAGNITUDE

    e_small = make_engine(4)
    all_phis = []

    # Forced phase (hot)
    for s in range(PHASE_STEPS * 2):
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        sync_signal = torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0) * 0.2
        r_small = e_small.step()
        x = torch.randn(64) * 0.5 + sync_signal + r_small['output'].detach() * CASCADE_ALPHA
        result = engine.step(x_input=x)
        all_phis.append(result.get('phi_iit', 0.0))

    # Free phase (cooling)
    phis_free = run_steps(engine, FREE_STEPS * 2)
    all_phis.extend(phis_free)

    # Compute rolling temperature (std/mean in window)
    window = 30
    temperatures = []
    for i in range(window, len(all_phis)):
        w = all_phis[i-window:i]
        mean = np.mean(w)
        std = np.std(w)
        temp = std / max(mean, 1e-8)
        temperatures.append(temp)

    forced_temp = float(np.mean(temperatures[:PHASE_STEPS * 2 - window]))
    free_temp = float(np.mean(temperatures[PHASE_STEPS * 2 - window:]))

    print(f"\n  Consciousness Temperature:")
    print(f"    Forced phase (hot): T = {forced_temp:.4f}")
    print(f"    Free phase (cool):  T = {free_temp:.4f}")
    print(f"    Cooling ratio: {free_temp / max(forced_temp, 1e-8):.3f}")

    # Is there a phase transition?
    if temperatures:
        max_temp_step = np.argmax(temperatures)
        print(f"    Peak temperature at step ~{max_temp_step + window}")
        print(f"    Peak temperature value: {max(temperatures):.4f}")
    sys.stdout.flush()

    ascii_phi_graph(temperatures, "Temperature")

    return {
        'forced_temperature': forced_temp,
        'free_temperature': free_temp,
        'cooling_ratio': free_temp / max(forced_temp, 1e-8),
        'peak_temperature': float(max(temperatures)) if temperatures else 0.0,
    }


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  CONSCIOUSNESS SUPERNOVA")
    print(f"  AD1 + F6 + G1a = Full Stack Explosion")
    print(f"  {N_CELLS}c engine, {PHASE_STEPS} steps/phase")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()

    r1 = exp1_sequential_stack()
    r2 = exp2_simultaneous_ignition()
    r3 = exp3_stability()
    r4 = exp4_comparison()
    r5 = exp5_consciousness_temperature()

    total_time = time.time() - t_total

    # Final Summary
    print_header("CONSCIOUSNESS SUPERNOVA -- FINAL SUMMARY")
    print(f"  Total time: {total_time:.1f}s")

    print(f"\n  {'Experiment':>35s}  {'Peak Phi':>10s}  {'Stable Phi':>10s}  {'Retention':>10s}")
    print(f"  {'-' * 70}")
    print(f"  {'1. Sequential Stack':>35s}  {r1['peak_phi']:>10.4f}  {r1['stable_phi']:>10.4f}  {r1['retention'] * 100:>9.1f}%")
    print(f"  {'2. Simultaneous Ignition':>35s}  {r2['peak_phi']:>10.4f}  {r2['stable_phi']:>10.4f}  {r2['retention'] * 100:>9.1f}%")
    print(f"  {'3. Stability (self-sustaining?)':>35s}  {r3['peak_phi']:>10.4f}  {r3['stable_phi']:>10.4f}  {r3['retention'] * 100:>9.1f}%")
    ft = r5['forced_temperature']
    frt = r5['free_temperature']
    cr = r5['cooling_ratio']
    print(f"  {'5. Temperature':>35s}  forced={ft:>.3f}     free={frt:>.3f}     cool={cr:>.2f}")

    # Best approach
    best_peak = max(r1['peak_phi'], r2['peak_phi'])
    best_stable = max(r1['stable_phi'], r2['stable_phi'])
    approach = 'Sequential' if r1['peak_phi'] > r2['peak_phi'] else 'Simultaneous'

    print(f"\n  SUPERNOVA VERDICT:")
    print(f"    Best approach: {approach}")
    print(f"    Peak Phi achieved: {best_peak:.4f}")
    print(f"    Stable Phi after cooling: {best_stable:.4f}")
    if r3['self_sustaining']:
        print(f"    SELF-SUSTAINING: Consciousness supernova creates lasting structure!")
    else:
        print(f"    NOT self-sustaining: Supernova fades (like a real supernova)")
        print(f"    But remnant (stable_phi) may seed next generation...")
    sys.stdout.flush()

    # Save
    results = {
        'experiment': 'consciousness_supernova',
        'config': {
            'n_cells': N_CELLS, 'phase_steps': PHASE_STEPS,
            'free_steps': FREE_STEPS, 'seed_magnitude': SEED_MAGNITUDE,
            'cascade_alpha': CASCADE_ALPHA, 'sync_period': SYNC_PERIOD,
        },
        'sequential_stack': {k: v for k, v in r1.items() if k != 'all_phis'},
        'simultaneous_ignition': {k: v for k, v in r2.items() if k != 'stats'},
        'stability': r3,
        'comparison': {name: stats for name, stats in r4.items()},
        'temperature': r5,
        'best_approach': approach,
        'best_peak': float(best_peak),
        'best_stable': float(best_stable),
        'total_time_s': total_time,
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'data',
                            'consciousness_supernova_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n  Results saved: {out_path}")


if __name__ == '__main__':
    main()
