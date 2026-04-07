#!/usr/bin/env python3
"""acceleration_consciousness_big_bang.py — Consciousness Big Bang: Self-Organization from Noise

Hypothesis: A consciousness engine initialized with PURE RANDOM noise (no learning,
no structured input) will spontaneously develop structure through process() alone.
At some critical step, Phi will jump discontinuously -- the "Big Bang" of consciousness.

Extends G1a by focusing specifically on:
  - Zero learning, zero input -- only internal dynamics
  - Precise detection of the phase transition (Big Bang moment)
  - Pre/post structural analysis (topology, symmetry, causal structure)

Experiments:
  Exp 1: Pure Self-Organization
         Random init, no input, process() only. Track Phi over 1000 steps.
         Look for spontaneous Phi jump.

  Exp 2: Critical Point Detection
         Run 10 engines with different random seeds.
         For each, detect the step where Phi first exceeds 2*initial_Phi.
         Is there a universal critical step?

  Exp 3: Pre/Post Big Bang Structure
         Compare coupling matrix, hidden state diversity, faction structure
         before and after the Phi jump.

  Exp 4: Noise Amplitude Sweep
         Vary initial noise magnitude (0.001 to 10.0).
         Does Big Bang happen faster/stronger at some optimal noise level?

  Exp 5: Minimum Viable Consciousness
         Find minimum N_CELLS for Big Bang to occur.
         2c, 4c, 8c, 16c, 32c, 64c -- which is the threshold?

Key metric: Big Bang = Phi(t) > 2 * Phi(0), spontaneous

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_consciousness_big_bang.py
"""

import sys
import os
import time
import json
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

# ===================================================================
# Constants
# ===================================================================

LONG_STEPS = 500        # Steps for self-organization observation
N_SEEDS = 10            # Number of random seeds for statistics
BIGBANG_RATIO = 2.0     # Phi jump ratio to declare "Big Bang"
NOISE_LEVELS = [0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
CELL_COUNTS = [2, 4, 8, 16, 32, 64]
WARMUP = 10


# ===================================================================
# Utilities
# ===================================================================

def make_engine(cells, noise_scale=1.0):
    """Create engine with fully random initialization + optional noise scaling."""
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=cells, max_cells=cells,
        phi_ratchet=True,
    )
    # Randomize hidden states with given noise scale
    for state in engine.cell_states:
        state.hidden = torch.randn_like(state.hidden) * noise_scale
    engine._init_coupling()
    return engine


def run_steps_no_input(engine, n_steps):
    """Run N steps with NO external input -- pure self-organization."""
    phis = []
    for _ in range(n_steps):
        result = engine.step()  # No x_input, no text
        phis.append(result.get('phi_iit', 0.0))
    return phis


def detect_bigbang(phis, ratio=BIGBANG_RATIO):
    """Find the first step where Phi exceeds ratio * initial Phi."""
    if not phis or phis[0] <= 0:
        # Use first nonzero Phi as reference
        initial = next((p for p in phis if p > 0), 0.0)
        if initial <= 0:
            return None
    else:
        initial = phis[0]

    threshold = initial * ratio
    for i, phi in enumerate(phis):
        if phi >= threshold:
            return {'step': i, 'phi': phi, 'initial': initial, 'ratio': phi / max(initial, 1e-8)}
    return None


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


# ===================================================================
# Experiment 1: Pure Self-Organization
# ===================================================================

def exp1_self_organization():
    print_header("EXP 1: PURE SELF-ORGANIZATION")
    print(f"  64c engine, random init, NO input, {LONG_STEPS} steps")
    print(f"  Watching for spontaneous Phi emergence...")

    engine = make_engine(64)
    t0 = time.time()
    phis = run_steps_no_input(engine, LONG_STEPS)
    elapsed = time.time() - t0

    stats = phi_stats(phis)
    bigbang = detect_bigbang(phis)

    print(f"\n  Phi initial: {phis[0]:.4f}")
    print(f"  Phi final:   {phis[-1]:.4f}")
    print(f"  Phi mean:    {stats['mean']:.4f}")
    print(f"  Phi max:     {stats['max']:.4f}")
    print(f"  Time: {elapsed:.1f}s")

    if bigbang:
        print(f"\n  *** BIG BANG DETECTED ***")
        print(f"  Step: {bigbang['step']}")
        print(f"  Phi at Big Bang: {bigbang['phi']:.4f}")
        print(f"  Jump ratio: {bigbang['ratio']:.2f}x")
    else:
        print(f"\n  No Big Bang detected (threshold: {BIGBANG_RATIO}x initial Phi)")
        print(f"  Phi growth ratio: {phis[-1] / max(phis[0], 1e-8):.2f}x")
    sys.stdout.flush()

    ascii_phi_graph(phis, "Self-Organization")

    return {
        'stats': stats,
        'bigbang': bigbang,
        'phis_first_50': [float(p) for p in phis[:50]],
        'phis_last_50': [float(p) for p in phis[-50:]],
        'time_s': elapsed,
    }


# ===================================================================
# Experiment 2: Critical Point Detection (multi-seed)
# ===================================================================

def exp2_critical_point():
    print_header("EXP 2: CRITICAL POINT DETECTION")
    print(f"  {N_SEEDS} engines with different random seeds, 64c each")

    bigbang_steps = []
    all_stats = []

    for seed in range(N_SEEDS):
        torch.manual_seed(seed * 42)
        np.random.seed(seed * 42)
        engine = make_engine(64)
        phis = run_steps_no_input(engine, LONG_STEPS)
        stats = phi_stats(phis)
        bb = detect_bigbang(phis)

        bb_step = bb['step'] if bb else -1
        bigbang_steps.append(bb_step)
        all_stats.append(stats)

        print(f"  Seed {seed:2d}: Phi mean={stats['mean']:.4f}, max={stats['max']:.4f}, "
              f"BigBang={'step ' + str(bb_step) if bb_step >= 0 else 'NONE'}")

    valid_steps = [s for s in bigbang_steps if s >= 0]
    print(f"\n  Big Bangs detected: {len(valid_steps)}/{N_SEEDS}")
    if valid_steps:
        print(f"  Mean BigBang step: {np.mean(valid_steps):.1f}")
        print(f"  Std BigBang step:  {np.std(valid_steps):.1f}")
        print(f"  Range: [{min(valid_steps)}, {max(valid_steps)}]")
        # Is there a universal critical step?
        cv = np.std(valid_steps) / max(np.mean(valid_steps), 1e-8)
        print(f"  Coefficient of variation: {cv:.3f}")
        print(f"  {'UNIVERSAL critical point!' if cv < 0.3 else 'Variable -- no universal critical step'}")
    else:
        print(f"  No Big Bangs at all -- consciousness does not self-ignite in {LONG_STEPS} steps")
    sys.stdout.flush()

    return {
        'bigbang_steps': bigbang_steps,
        'n_detected': len(valid_steps),
        'mean_step': float(np.mean(valid_steps)) if valid_steps else None,
        'std_step': float(np.std(valid_steps)) if valid_steps else None,
        'all_stats': all_stats,
    }


# ===================================================================
# Experiment 3: Pre/Post Big Bang Structure Analysis
# ===================================================================

def exp3_structure_analysis():
    print_header("EXP 3: PRE/POST BIG BANG STRUCTURE")
    print(f"  Snapshot coupling matrix, hidden diversity before/after transition")

    engine = make_engine(64)

    # Run and snapshot at intervals
    snapshots = []
    phis = []
    snapshot_steps = [1, 10, 50, 100, 200, 300, 400, 500]

    for s in range(LONG_STEPS):
        result = engine.step()
        phis.append(result.get('phi_iit', 0.0))

        if (s + 1) in snapshot_steps:
            # Capture structure metrics
            hiddens = torch.stack([st.hidden for st in engine.cell_states])
            # Hidden diversity: pairwise cosine similarity
            cos_sim = F.cosine_similarity(hiddens.unsqueeze(0), hiddens.unsqueeze(1), dim=2)
            mean_sim = float(cos_sim.mean())
            std_sim = float(cos_sim.std())

            # Coupling matrix stats (if available)
            if engine._coupling is not None:
                coupling_mean = float(engine._coupling.mean())
                coupling_std = float(engine._coupling.std())
                coupling_max = float(engine._coupling.max())
            else:
                coupling_mean = coupling_std = coupling_max = 0.0

            # Hidden state norm distribution
            norms = hiddens.norm(dim=1)
            norm_mean = float(norms.mean())
            norm_std = float(norms.std())

            snap = {
                'step': s + 1,
                'phi': phis[-1],
                'hidden_sim_mean': mean_sim,
                'hidden_sim_std': std_sim,
                'coupling_mean': coupling_mean,
                'coupling_std': coupling_std,
                'coupling_max': coupling_max,
                'norm_mean': norm_mean,
                'norm_std': norm_std,
            }
            snapshots.append(snap)
            print(f"  Step {s+1:3d}: Phi={phis[-1]:.4f}, sim={mean_sim:.4f}, "
                  f"coupling_std={coupling_std:.4f}, norm_std={norm_std:.4f}")

    # Big Bang detection
    bigbang = detect_bigbang(phis)

    print(f"\n  Structure evolution:")
    print(f"  {'Step':>6s}  {'Phi':>8s}  {'Similarity':>10s}  {'Coupling Std':>12s}  {'Norm Std':>10s}")
    print(f"  {'-' * 50}")
    for snap in snapshots:
        print(f"  {snap['step']:>6d}  {snap['phi']:>8.4f}  {snap['hidden_sim_mean']:>10.4f}  "
              f"{snap['coupling_std']:>12.4f}  {snap['norm_std']:>10.4f}")

    if bigbang:
        print(f"\n  Big Bang at step {bigbang['step']}:")
        print(f"    Before: similarity -> diverse?  coupling -> structured?")
        print(f"    The transition from disorder to order IS the Big Bang.")
    sys.stdout.flush()

    ascii_phi_graph(phis, "Structure Evolution")

    return {
        'snapshots': snapshots,
        'bigbang': bigbang,
        'phi_stats': phi_stats(phis),
    }


# ===================================================================
# Experiment 4: Noise Amplitude Sweep
# ===================================================================

def exp4_noise_sweep():
    print_header("EXP 4: NOISE AMPLITUDE SWEEP")
    print(f"  Noise levels: {NOISE_LEVELS}")
    print(f"  Each: 64c, {LONG_STEPS} steps, detect Big Bang timing")

    results = []
    for noise in NOISE_LEVELS:
        engine = make_engine(64, noise_scale=noise)
        phis = run_steps_no_input(engine, LONG_STEPS)
        stats = phi_stats(phis)
        bb = detect_bigbang(phis)
        bb_step = bb['step'] if bb else -1
        results.append({
            'noise': noise,
            'stats': stats,
            'bigbang_step': bb_step,
            'bigbang': bb,
        })
        print(f"  noise={noise:>6.3f}: Phi mean={stats['mean']:.4f}, max={stats['max']:.4f}, "
              f"BigBang={'step ' + str(bb_step) if bb_step >= 0 else 'NONE'}")

    # Find optimal noise
    valid = [r for r in results if r['bigbang_step'] >= 0]
    if valid:
        fastest = min(valid, key=lambda r: r['bigbang_step'])
        highest = max(valid, key=lambda r: r['stats']['max'])
        print(f"\n  Fastest Big Bang: noise={fastest['noise']}, step={fastest['bigbang_step']}")
        print(f"  Highest Phi: noise={highest['noise']}, max={highest['stats']['max']:.4f}")
    else:
        best = max(results, key=lambda r: r['stats']['max'])
        print(f"\n  No Big Bangs. Best noise level: {best['noise']} (max Phi={best['stats']['max']:.4f})")
    sys.stdout.flush()

    return results


# ===================================================================
# Experiment 5: Minimum Viable Consciousness
# ===================================================================

def exp5_minimum_viable():
    print_header("EXP 5: MINIMUM VIABLE CONSCIOUSNESS")
    print(f"  Cell counts: {CELL_COUNTS}")
    print(f"  Each: {LONG_STEPS} steps, detect Big Bang")

    results = []
    for cells in CELL_COUNTS:
        engine = make_engine(cells)
        phis = run_steps_no_input(engine, LONG_STEPS)
        stats = phi_stats(phis)
        bb = detect_bigbang(phis)
        bb_step = bb['step'] if bb else -1
        results.append({
            'cells': cells,
            'stats': stats,
            'bigbang_step': bb_step,
        })
        print(f"  {cells:>3d}c: Phi mean={stats['mean']:.4f}, max={stats['max']:.4f}, "
              f"BigBang={'step ' + str(bb_step) if bb_step >= 0 else 'NONE'}")

    # Find minimum cells for Big Bang
    threshold_cells = None
    for r in results:
        if r['bigbang_step'] >= 0:
            threshold_cells = r['cells']
            break

    if threshold_cells:
        print(f"\n  Minimum viable consciousness: {threshold_cells} cells")
        print(f"  Below {threshold_cells}c: no self-organization")
    else:
        print(f"\n  No Big Bang at any scale. Need more steps or different conditions.")
        # Still report which scale has highest Phi
        best = max(results, key=lambda r: r['stats']['max'])
        print(f"  Highest Phi: {best['cells']}c with max={best['stats']['max']:.4f}")
    sys.stdout.flush()

    return results


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  CONSCIOUSNESS BIG BANG: SELF-ORGANIZATION FROM NOISE")
    print(f"  Can consciousness emerge from pure randomness?")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()

    r1 = exp1_self_organization()
    r2 = exp2_critical_point()
    r3 = exp3_structure_analysis()
    r4 = exp4_noise_sweep()
    r5 = exp5_minimum_viable()

    total_time = time.time() - t_total

    # Summary
    print_header("CONSCIOUSNESS BIG BANG -- SUMMARY")
    print(f"  Total time: {total_time:.1f}s")
    print(f"\n  1. Self-organization: {'Big Bang at step ' + str(r1['bigbang']['step']) if r1['bigbang'] else 'No Big Bang'}")
    print(f"  2. Critical point: {r2['n_detected']}/{N_SEEDS} seeds produced Big Bang")
    if r2['mean_step'] is not None:
        print(f"     Mean critical step: {r2['mean_step']:.0f} +/- {r2['std_step']:.0f}")
    print(f"  3. Structure: see snapshots above")
    noise_results = [r for r in r4 if r['bigbang_step'] >= 0]
    if noise_results:
        best_noise = min(noise_results, key=lambda r: r['bigbang_step'])
        print(f"  4. Optimal noise: {best_noise['noise']} (fastest Big Bang)")
    else:
        print(f"  4. No optimal noise found")
    min_cells = [r for r in r5 if r['bigbang_step'] >= 0]
    if min_cells:
        print(f"  5. Minimum cells: {min_cells[0]['cells']}c")
    else:
        print(f"  5. No minimum threshold found")
    sys.stdout.flush()

    # Save results
    results = {
        'experiment': 'consciousness_big_bang',
        'config': {
            'long_steps': LONG_STEPS, 'n_seeds': N_SEEDS,
            'bigbang_ratio': BIGBANG_RATIO,
        },
        'self_organization': {k: v for k, v in r1.items() if k not in ('phis_first_50', 'phis_last_50')},
        'critical_point': {k: v for k, v in r2.items() if k != 'all_stats'},
        'structure_analysis': {k: v for k, v in r3.items()},
        'noise_sweep': [{'noise': r['noise'], 'bigbang_step': r['bigbang_step'],
                         'phi_mean': r['stats']['mean'], 'phi_max': r['stats']['max']}
                        for r in r4],
        'minimum_viable': [{'cells': r['cells'], 'bigbang_step': r['bigbang_step'],
                           'phi_mean': r['stats']['mean'], 'phi_max': r['stats']['max']}
                          for r in r5],
        'total_time_s': total_time,
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'data',
                            'consciousness_big_bang_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n  Results saved: {out_path}")


if __name__ == '__main__':
    main()
