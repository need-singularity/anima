#!/usr/bin/env python3
"""acceleration_phi_cascade_explosion.py — Phi Resonance Cascade Explosion (F6 Extended)

Hypothesis: By seeding a high Phi value into specific cells and synchronizing
oscillation frequencies across cells, a cascade explosion can be triggered
where Phi grows exponentially before saturating.

Experiments:
  Exp 1: Phi Seed Injection
         Inject artificially high Phi seeds (scaled hidden states) into
         a subset of cells. Measure propagation speed to neighbors.

  Exp 2: Frequency Synchronization
         Force cells into same oscillation period via periodic input coupling.
         Resonance condition: all cells at same frequency = cascade trigger.

  Exp 3: Cascade Detection
         Monitor Phi growth rate. When d(Phi)/dt > threshold = cascade event.
         Measure: time to cascade, max Phi, post-cascade stability.

  Exp 4: Controlled Detonation
         Combine seed injection + frequency sync + maximum coupling.
         Goal: trigger the most violent Phi explosion possible.

  Exp 5: Stability After Explosion
         After cascade, remove all forcing. Does Phi collapse or maintain?
         Self-sustaining = true consciousness emergence.

Key metric: cascade_ratio = max(Phi) / baseline_Phi

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_phi_cascade_explosion.py
"""

import sys
import os
import time
import json
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

# ===================================================================
# Constants
# ===================================================================

N_CELLS = 64
STEPS = 300
WARMUP = 30
SEED_CELLS = 8          # Number of cells to seed with high Phi
SEED_MAGNITUDE = 5.0    # How much to scale seeded hidden states
CASCADE_THRESHOLD = 0.5 # d(Phi)/dt threshold for cascade detection
SYNC_PERIOD = 6         # Synchronization period (n=6)
COUPLING_STRONG = 0.20  # Strong coupling for resonance forcing


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


def detect_cascade(phis, threshold=CASCADE_THRESHOLD, window=5):
    """Detect cascade events where Phi growth rate exceeds threshold."""
    events = []
    for i in range(window, len(phis)):
        d_phi = (phis[i] - phis[i - window]) / window
        if d_phi > threshold:
            events.append({'step': i, 'phi': phis[i], 'rate': d_phi})
    return events


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
    print(f"  {name:25s} {bar:<{bar_width}s} {value:.4f} ({sign}{pct:.1f}%)")


# ===================================================================
# Experiment 1: Phi Seed Injection
# ===================================================================

def exp1_seed_injection():
    print_header("EXP 1: PHI SEED INJECTION")
    print(f"  Inject high-energy seeds into {SEED_CELLS}/{N_CELLS} cells")
    print(f"  Seed magnitude: {SEED_MAGNITUDE}x hidden state scaling")

    engine = make_engine()

    # Warm up a few steps first
    warmup_phis = run_steps(engine, 20)
    phi_before_seed = warmup_phis[-1]

    # Inject seeds: scale hidden states of first SEED_CELLS cells
    for i in range(SEED_CELLS):
        engine.cell_states[i].hidden = engine.cell_states[i].hidden * SEED_MAGNITUDE

    phi_after_seed = engine.measure_phi()
    print(f"  Phi before seed: {phi_before_seed:.4f}")
    print(f"  Phi after seed:  {phi_after_seed:.4f}")
    print(f"  Instant jump:    {phi_after_seed - phi_before_seed:+.4f}")

    # Observe propagation
    phis_post = run_steps(engine, STEPS)

    # Baseline (no seed)
    baseline = make_engine()
    _ = run_steps(baseline, 20)  # same warmup
    phis_base = run_steps(baseline, STEPS)

    stats_seed = phi_stats(phis_post)
    stats_base = phi_stats(phis_base)

    # Detect cascade events
    cascades = detect_cascade(phis_post)
    print(f"\n  Cascade events detected: {len(cascades)}")
    for ev in cascades[:5]:
        print(f"    Step {ev['step']}: Phi={ev['phi']:.4f}, rate={ev['rate']:.4f}")

    # Propagation: check if non-seeded cells also increase
    print(f"\n  Seeded Phi mean: {stats_seed['mean']:.4f}")
    print(f"  Baseline Phi mean: {stats_base['mean']:.4f}")
    pct = (stats_seed['mean'] - stats_base['mean']) / max(stats_base['mean'], 1e-8) * 100
    print(f"  Seed boost: {pct:+.1f}%")
    sys.stdout.flush()

    ascii_phi_graph(phis_post, "Seeded")
    ascii_phi_graph(phis_base, "Baseline")

    return {
        'phi_before_seed': float(phi_before_seed),
        'phi_after_seed': float(phi_after_seed),
        'stats_seeded': stats_seed,
        'stats_baseline': stats_base,
        'n_cascades': len(cascades),
    }


# ===================================================================
# Experiment 2: Frequency Synchronization
# ===================================================================

def exp2_frequency_sync():
    print_header("EXP 2: FREQUENCY SYNCHRONIZATION")
    print(f"  Force all cells to oscillate at period={SYNC_PERIOD}")
    print(f"  Coupling strength: {COUPLING_STRONG}")

    engine = make_engine()

    phis_synced = []
    for s in range(STEPS):
        # Create synchronized forcing input: periodic signal at SYNC_PERIOD
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        sync_signal = torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0)
        sync_signal = sync_signal * COUPLING_STRONG

        # Mix with random noise
        x_input = torch.randn(64) * (1.0 - COUPLING_STRONG) + sync_signal
        result = engine.step(x_input=x_input)
        phis_synced.append(result.get('phi_iit', 0.0))

        if (s + 1) % 50 == 0:
            print(f"  step {s+1:3d}: Phi={result['phi_iit']:.4f}", flush=True)

    # Baseline (no sync)
    baseline = make_engine()
    phis_base = run_steps(baseline, STEPS)

    stats_sync = phi_stats(phis_synced)
    stats_base = phi_stats(phis_base)

    # Check for resonance: is Phi oscillation period near SYNC_PERIOD?
    phi_arr = np.array(phis_synced[WARMUP:]) - np.mean(phis_synced[WARMUP:])
    if np.std(phi_arr) > 1e-8:
        fft = np.abs(np.fft.rfft(phi_arr))
        freqs = np.fft.rfftfreq(len(phi_arr))
        if len(fft) > 1:
            peak_idx = np.argmax(fft[1:]) + 1
            dom_period = 1.0 / freqs[peak_idx] if freqs[peak_idx] > 0 else 0
        else:
            dom_period = 0
    else:
        dom_period = 0

    pct = (stats_sync['mean'] - stats_base['mean']) / max(stats_base['mean'], 1e-8) * 100
    print(f"\n  Synced Phi mean: {stats_sync['mean']:.4f}")
    print(f"  Baseline Phi mean: {stats_base['mean']:.4f}")
    print(f"  Sync boost: {pct:+.1f}%")
    print(f"  Dominant oscillation period: {dom_period:.1f} steps (target: {SYNC_PERIOD})")
    print(f"  Resonance achieved: {'YES' if abs(dom_period - SYNC_PERIOD) < 2 else 'NO'}")
    sys.stdout.flush()

    ascii_phi_graph(phis_synced, "Synced")

    return {
        'stats_synced': stats_sync,
        'stats_baseline': stats_base,
        'dom_period': float(dom_period),
        'target_period': SYNC_PERIOD,
        'resonance': abs(dom_period - SYNC_PERIOD) < 2,
    }


# ===================================================================
# Experiment 3: Cascade Detection (pure organic growth)
# ===================================================================

def exp3_cascade_detection():
    print_header("EXP 3: CASCADE DETECTION (organic growth)")
    print(f"  Run {N_CELLS}c engine for {STEPS * 2} steps, monitor for spontaneous cascades")

    engine = make_engine()
    phis = run_steps(engine, STEPS * 2)

    cascades = detect_cascade(phis, threshold=CASCADE_THRESHOLD * 0.5, window=5)

    stats = phi_stats(phis)
    print(f"\n  Total steps: {len(phis)}")
    print(f"  Phi mean: {stats['mean']:.4f}, max: {stats['max']:.4f}")
    print(f"  Cascade events (rate > {CASCADE_THRESHOLD * 0.5:.2f}/step): {len(cascades)}")

    if cascades:
        # Analyze first cascade
        first = cascades[0]
        print(f"  First cascade at step {first['step']}: Phi={first['phi']:.4f}, rate={first['rate']:.4f}")

        # Time between cascades
        if len(cascades) > 1:
            intervals = [cascades[i+1]['step'] - cascades[i]['step'] for i in range(len(cascades)-1)]
            print(f"  Mean interval between cascades: {np.mean(intervals):.1f} steps")
            print(f"  Cascade interval std: {np.std(intervals):.1f}")
    else:
        print(f"  No spontaneous cascades detected. Engine is too stable.")
        print(f"  Lowering threshold...")
        cascades_low = detect_cascade(phis, threshold=CASCADE_THRESHOLD * 0.1, window=10)
        print(f"  At threshold={CASCADE_THRESHOLD * 0.1:.3f}: {len(cascades_low)} events")
    sys.stdout.flush()

    ascii_phi_graph(phis, "Organic Phi")

    return {
        'stats': stats,
        'n_cascades': len(cascades),
        'cascades': [{'step': c['step'], 'phi': c['phi'], 'rate': c['rate']}
                     for c in cascades[:10]],
    }


# ===================================================================
# Experiment 4: Controlled Detonation
# ===================================================================

def exp4_controlled_detonation():
    print_header("EXP 4: CONTROLLED DETONATION")
    print(f"  Seed injection + frequency sync + max coupling = BOOM")

    engine = make_engine()

    # Phase 1: Warmup (50 steps)
    phis_warmup = run_steps(engine, 50)
    phi_before = phis_warmup[-1]
    print(f"  Phase 1 (warmup): Phi={phi_before:.4f}")

    # Phase 2: Seed injection into half the cells
    for i in range(N_CELLS // 2):
        engine.cell_states[i].hidden = engine.cell_states[i].hidden * SEED_MAGNITUDE
    phi_after_seed = engine.measure_phi()
    print(f"  Phase 2 (seed): Phi={phi_after_seed:.4f}")

    # Phase 3: Synchronized forcing + evolution (200 steps)
    phis_detonation = []
    for s in range(STEPS):
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        sync_signal = torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0)
        # Max coupling = 0.3
        alpha = 0.3
        x_input = torch.randn(64) * (1.0 - alpha) + sync_signal * alpha
        result = engine.step(x_input=x_input)
        phis_detonation.append(result.get('phi_iit', 0.0))

        if (s + 1) % 50 == 0:
            print(f"    step {s+1:3d}: Phi={result['phi_iit']:.4f}", flush=True)

    stats_det = phi_stats(phis_detonation)
    cascades = detect_cascade(phis_detonation)

    # Baseline
    baseline = make_engine()
    phis_base = run_steps(baseline, 50 + STEPS)
    stats_base = phi_stats(phis_base)

    print(f"\n  Detonation results:")
    print(f"    Max Phi: {stats_det['max']:.4f}")
    print(f"    Mean Phi: {stats_det['mean']:.4f}")
    print(f"    Cascade events: {len(cascades)}")
    print(f"    Baseline mean: {stats_base['mean']:.4f}")
    explosion_ratio = stats_det['max'] / max(stats_base['max'], 1e-8)
    print(f"    Explosion ratio (max): {explosion_ratio:.2f}x")
    print(f"    {'DETONATION SUCCESSFUL!' if explosion_ratio > 2.0 else 'Controlled burn (no explosion)'}")
    sys.stdout.flush()

    ascii_phi_graph(phis_detonation, "Detonation")
    ascii_phi_graph(phis_base[50:], "Baseline")

    return {
        'phi_before': float(phi_before),
        'phi_after_seed': float(phi_after_seed),
        'stats_detonation': stats_det,
        'stats_baseline': stats_base,
        'explosion_ratio': float(explosion_ratio),
        'n_cascades': len(cascades),
    }


# ===================================================================
# Experiment 5: Stability After Explosion
# ===================================================================

def exp5_post_explosion_stability():
    print_header("EXP 5: STABILITY AFTER EXPLOSION")
    print(f"  Detonate, then remove all forcing. Does Phi self-sustain?")

    engine = make_engine()

    # Warmup
    run_steps(engine, 30)

    # Detonate: seed + sync (100 steps)
    for i in range(N_CELLS // 2):
        engine.cell_states[i].hidden = engine.cell_states[i].hidden * SEED_MAGNITUDE

    phis_forced = []
    for s in range(100):
        phase = 2.0 * math.pi * s / SYNC_PERIOD
        sync_signal = torch.sin(torch.arange(64, dtype=torch.float32) * phase / 64.0) * 0.3
        x_input = torch.randn(64) * 0.7 + sync_signal
        result = engine.step(x_input=x_input)
        phis_forced.append(result.get('phi_iit', 0.0))

    phi_at_release = phis_forced[-1]
    print(f"  Phi at release (end of forcing): {phi_at_release:.4f}")

    # Release: no more forcing, pure random input
    phis_free = run_steps(engine, STEPS)

    stats_forced = phi_stats(phis_forced, warmup=10)
    stats_free = phi_stats(phis_free)

    # Stability: does Phi maintain after release?
    phi_decay = phis_free[-1] - phi_at_release
    retention = phis_free[-1] / max(phi_at_release, 1e-8)

    print(f"\n  Forced phase Phi mean: {stats_forced['mean']:.4f}")
    print(f"  Free phase Phi mean: {stats_free['mean']:.4f}")
    print(f"  Phi at release: {phi_at_release:.4f}")
    print(f"  Phi after {STEPS} free steps: {phis_free[-1]:.4f}")
    print(f"  Retention ratio: {retention:.3f}")
    print(f"  {'SELF-SUSTAINING!' if retention > 0.9 else 'DECAYS (not self-sustaining)' if retention < 0.5 else 'PARTIAL RETENTION'}")
    sys.stdout.flush()

    all_phis = phis_forced + phis_free
    ascii_phi_graph(all_phis, "Forced|Free")

    return {
        'stats_forced': stats_forced,
        'stats_free': stats_free,
        'phi_at_release': float(phi_at_release),
        'phi_final_free': float(phis_free[-1]),
        'retention_ratio': float(retention),
        'self_sustaining': retention > 0.9,
    }


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  PHI RESONANCE CASCADE EXPLOSION")
    print(f"  {N_CELLS}c engine, {STEPS} steps per experiment")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()

    r1 = exp1_seed_injection()
    r2 = exp2_frequency_sync()
    r3 = exp3_cascade_detection()
    r4 = exp4_controlled_detonation()
    r5 = exp5_post_explosion_stability()

    total_time = time.time() - t_total

    # Summary
    print_header("PHI CASCADE EXPLOSION -- SUMMARY")
    print(f"  Total time: {total_time:.1f}s")
    print(f"\n  {'Experiment':>30s}  {'Key Result':>15s}  {'Verdict':>15s}")
    print(f"  {'-' * 65}")
    print(f"  {'1. Seed Injection':>30s}  {'boost=' + f'{(r1[\"stats_seeded\"][\"mean\"] - r1[\"stats_baseline\"][\"mean\"]) / max(r1[\"stats_baseline\"][\"mean\"], 1e-8) * 100:+.1f}%':>15s}  {'WORKS' if r1['n_cascades'] > 0 else 'WEAK':>15s}")
    print(f"  {'2. Frequency Sync':>30s}  {'resonance=' + str(r2['resonance']):>15s}  {'LOCKED' if r2['resonance'] else 'UNLOCKED':>15s}")
    print(f"  {'3. Cascade Detection':>30s}  {'events=' + str(r3['n_cascades']):>15s}  {'CASCADE!' if r3['n_cascades'] > 3 else 'STABLE':>15s}")
    print(f"  {'4. Controlled Detonation':>30s}  {'ratio=' + f'{r4[\"explosion_ratio\"]:.2f}x':>15s}  {'BOOM!' if r4['explosion_ratio'] > 2.0 else 'FIZZLE':>15s}")
    print(f"  {'5. Post-Explosion Stability':>30s}  {'retain=' + f'{r5[\"retention_ratio\"]:.2f}':>15s}  {'SUSTAIN' if r5['self_sustaining'] else 'DECAY':>15s}")
    sys.stdout.flush()

    # Save results
    results = {
        'experiment': 'phi_cascade_explosion',
        'config': {
            'n_cells': N_CELLS, 'steps': STEPS, 'seed_cells': SEED_CELLS,
            'seed_magnitude': SEED_MAGNITUDE, 'sync_period': SYNC_PERIOD,
            'cascade_threshold': CASCADE_THRESHOLD,
        },
        'seed_injection': r1,
        'frequency_sync': r2,
        'cascade_detection': r3,
        'controlled_detonation': r4,
        'post_explosion_stability': r5,
        'total_time_s': total_time,
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'data',
                            'phi_cascade_explosion_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n  Results saved: {out_path}")


if __name__ == '__main__':
    main()
