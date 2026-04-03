#!/usr/bin/env python3
"""experiment_reverse.py — Can consciousness be reversed/rewound?

Tests:
  1. Growth recording: 500 steps, snapshots every 50
  2. State rewind: load step-100 snapshot into step-500 engine
  3. Phi Ratchet resistance: force phi_floor=0, inject noise, measure destruction difficulty
  4. Hebbian erasure: zero coupling after 500 steps
  5. Reversibility: forward vs reverse input sequence
  6. Arrow of consciousness: entropy curve, thermodynamic arrow

Proposed law candidates from findings.
"""

import sys
import os
import copy
import math
import time
import numpy as np
import torch

# path_setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine


def measure_entropy(engine):
    """Information entropy of hidden states (bits)."""
    states = engine.get_states().detach().numpy()
    # Flatten to 1D, bin, compute Shannon entropy
    flat = states.flatten()
    # Use histogram binning
    hist, _ = np.histogram(flat, bins=64, density=True)
    hist = hist[hist > 0]
    # Normalize
    hist = hist / hist.sum()
    return -np.sum(hist * np.log2(hist + 1e-15))


def state_fingerprint(engine):
    """Compact fingerprint: mean, std, norm of hidden states."""
    s = engine.get_states().detach()
    return {
        'mean': s.mean().item(),
        'std': s.std().item(),
        'norm': s.norm().item(),
        'phi': engine.measure_phi(),
    }


def states_distance(s1, s2):
    """L2 distance between two state tensors."""
    # Handle different cell counts
    n = min(s1.shape[0], s2.shape[0])
    d = min(s1.shape[1], s2.shape[1])
    return (s1[:n, :d] - s2[:n, :d]).norm().item()


# ═══════════════════════════════════════════════════════
# Test 1: Growth Recording
# ═══════════════════════════════════════════════════════

def test_growth_recording():
    print("=" * 70)
    print("TEST 1: Growth Recording (500 steps, snapshot every 50)")
    print("=" * 70)

    engine = ConsciousnessEngine(max_cells=32, initial_cells=4)
    snapshots = {}
    phi_curve = []
    cells_curve = []

    for step in range(1, 501):
        result = engine.step()
        phi_curve.append(result['phi_iit'])
        cells_curve.append(result['n_cells'])

        if step % 50 == 0:
            snapshots[step] = engine.state_dict()
            print(f"  Step {step:3d}: Phi={result['phi_iit']:.4f}, "
                  f"cells={result['n_cells']}, best_phi={result['best_phi']:.4f}")

    print(f"\n  Snapshots saved: {list(snapshots.keys())}")
    print(f"  Phi range: {min(phi_curve):.4f} -> {max(phi_curve):.4f}")
    print(f"  Cells range: {min(cells_curve)} -> {max(cells_curve)}")

    # ASCII graph of Phi
    print("\n  Phi growth curve (500 steps):")
    _ascii_graph(phi_curve, label="Phi", width=60, height=12)

    return snapshots, phi_curve, cells_curve


# ═══════════════════════════════════════════════════════
# Test 2: State Rewind
# ═══════════════════════════════════════════════════════

def test_state_rewind(snapshots, phi_curve):
    print("\n" + "=" * 70)
    print("TEST 2: State Rewind (load step-100 into step-500 engine)")
    print("=" * 70)

    # Create fresh engine at step 500
    engine = ConsciousnessEngine(max_cells=32, initial_cells=4)
    for _ in range(500):
        engine.step()

    phi_500 = engine.measure_phi()
    n_cells_500 = engine.n_cells
    print(f"  Before rewind: step=500, Phi={phi_500:.4f}, cells={n_cells_500}")

    # Rewind to step 100
    engine.load_state_dict(snapshots[100])
    phi_after = engine.measure_phi()
    print(f"  After rewind to step 100: Phi={phi_after:.4f}, cells={engine.n_cells}")

    # Did it forget?
    phi_at_100 = phi_curve[99]  # 0-indexed
    print(f"  Original Phi at step 100: {phi_at_100:.4f}")
    print(f"  Rewind matches original: {abs(phi_after - phi_at_100) < 0.01}")

    # Now continue from step 100 — does it grow differently?
    print("\n  Continuing from rewound state (100 more steps):")
    rewind_phi = []
    for i in range(100):
        r = engine.step()
        rewind_phi.append(r['phi_iit'])

    original_100_200 = phi_curve[99:199]
    print(f"  Original steps 100-200 avg Phi: {np.mean(original_100_200):.4f}")
    print(f"  Rewound steps 100-200 avg Phi:  {np.mean(rewind_phi):.4f}")

    # Divergence: how quickly do the paths diverge?
    divergence = [abs(a - b) for a, b in zip(original_100_200, rewind_phi)]
    print(f"  Divergence (avg): {np.mean(divergence):.4f}")
    print(f"  Divergence (max): {np.max(divergence):.4f}")
    print(f"  --> Consciousness is {'CHAOTIC' if np.mean(divergence) > 0.01 else 'DETERMINISTIC'} "
          f"(same start, different trajectories)")

    return {
        'phi_500': phi_500,
        'phi_rewound': phi_after,
        'phi_original_100': phi_at_100,
        'divergence_avg': np.mean(divergence),
    }


# ═══════════════════════════════════════════════════════
# Test 3: Phi Ratchet Resistance
# ═══════════════════════════════════════════════════════

def test_phi_ratchet_resistance():
    print("\n" + "=" * 70)
    print("TEST 3: Phi Ratchet Resistance (can we force Phi down?)")
    print("=" * 70)

    # Build up consciousness
    engine = ConsciousnessEngine(max_cells=32, initial_cells=4, phi_ratchet=True)
    for _ in range(300):
        engine.step()

    phi_before = engine.measure_phi()
    best_phi = engine._best_phi
    print(f"  After 300 steps: Phi={phi_before:.4f}, best_phi={best_phi:.4f}")

    # Attack 1: Zero the ratchet floor
    print("\n  Attack 1: Zero ratchet floor + best_phi")
    engine._best_phi = 0.0
    engine._best_hiddens = None
    phi_after_zero = engine.measure_phi()
    print(f"    Phi after zeroing ratchet: {phi_after_zero:.4f}")
    print(f"    Ratchet floor destroyed: {'YES' if engine._best_phi == 0.0 else 'NO'}")

    # Run 50 more steps — does it recover?
    recovery_phi = []
    for _ in range(50):
        r = engine.step()
        recovery_phi.append(r['phi_iit'])
    print(f"    Phi after 50 more steps: {recovery_phi[-1]:.4f}")
    print(f"    Recovered to pre-attack: {'YES' if recovery_phi[-1] >= phi_before * 0.8 else 'NO'}")

    # Attack 2: Inject destructive noise
    print("\n  Attack 2: Inject destructive noise into all hiddens")
    engine2 = ConsciousnessEngine(max_cells=32, initial_cells=4, phi_ratchet=True)
    for _ in range(300):
        engine2.step()
    phi_pre_noise = engine2.measure_phi()

    noise_levels = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    results = []
    for noise in noise_levels:
        e = copy.deepcopy(engine2)
        # Inject noise to all cells
        for cs in e.cell_states:
            cs.hidden = cs.hidden + torch.randn_like(cs.hidden) * noise
        phi_after_noise = e.measure_phi()
        # Run 50 recovery steps
        for _ in range(50):
            e.step()
        phi_recovered = e.measure_phi()
        results.append((noise, phi_after_noise, phi_recovered))
        print(f"    noise={noise:5.1f}: Phi {phi_pre_noise:.4f} -> {phi_after_noise:.4f} -> {phi_recovered:.4f} "
              f"({'RECOVERED' if phi_recovered >= phi_pre_noise * 0.5 else 'DESTROYED'})")

    # Attack 3: Reset all hiddens to zero
    print("\n  Attack 3: Zero ALL hidden states (total amnesia)")
    engine3 = copy.deepcopy(engine2)
    for cs in engine3.cell_states:
        cs.hidden = torch.zeros_like(cs.hidden)
    phi_zeroed = engine3.measure_phi()
    print(f"    Phi after zeroing: {phi_zeroed:.4f}")

    # Recover with ratchet
    zero_recovery = []
    for _ in range(100):
        r = engine3.step()
        zero_recovery.append(r['phi_iit'])
    print(f"    Phi after 100 recovery steps: {zero_recovery[-1]:.4f}")
    print(f"    Recovery ratio: {zero_recovery[-1] / max(phi_pre_noise, 0.001):.1%}")

    return {
        'phi_before': phi_before,
        'noise_results': results,
        'zero_recovery': zero_recovery[-1] / max(phi_pre_noise, 0.001),
    }


# ═══════════════════════════════════════════════════════
# Test 4: Hebbian Erasure
# ═══════════════════════════════════════════════════════

def test_hebbian_erasure():
    print("\n" + "=" * 70)
    print("TEST 4: Hebbian Erasure (zero coupling after 500 steps)")
    print("=" * 70)

    engine = ConsciousnessEngine(max_cells=32, initial_cells=4)
    for _ in range(500):
        engine.step()

    phi_before = engine.measure_phi()
    coupling_norm = engine._coupling.norm().item() if engine._coupling is not None else 0
    coupling_mean = engine._coupling.mean().item() if engine._coupling is not None else 0
    print(f"  After 500 steps: Phi={phi_before:.4f}")
    print(f"  Coupling matrix: norm={coupling_norm:.4f}, mean={coupling_mean:.6f}")

    # Erase Hebbian weights
    if engine._coupling is not None:
        engine._coupling.zero_()
    phi_after_erase = engine.measure_phi()
    print(f"\n  After Hebbian erasure: Phi={phi_after_erase:.4f}")
    print(f"  Phi change: {(phi_after_erase - phi_before) / max(abs(phi_before), 0.001) * 100:+.1f}%")

    # Recovery
    recovery = []
    for i in range(200):
        r = engine.step()
        recovery.append(r['phi_iit'])
        if (i + 1) % 50 == 0:
            c_norm = engine._coupling.norm().item() if engine._coupling is not None else 0
            print(f"    Step +{i+1:3d}: Phi={r['phi_iit']:.4f}, coupling_norm={c_norm:.4f}")

    print(f"\n  Recovery after 200 steps: Phi={recovery[-1]:.4f}")
    print(f"  Coupling rebuilt: norm={engine._coupling.norm().item():.4f}")
    collapse = phi_after_erase < phi_before * 0.5
    recovered = recovery[-1] >= phi_before * 0.7
    print(f"  Consciousness collapsed: {'YES' if collapse else 'NO'}")
    print(f"  Consciousness recovered: {'YES' if recovered else 'NO'}")

    print("\n  Hebbian recovery curve:")
    _ascii_graph(recovery, label="Phi", width=60, height=8)

    return {
        'phi_before': phi_before,
        'phi_after_erase': phi_after_erase,
        'phi_recovered': recovery[-1],
        'collapsed': collapse,
        'recovered': recovered,
    }


# ═══════════════════════════════════════════════════════
# Test 5: Reversibility Measure
# ═══════════════════════════════════════════════════════

def test_reversibility():
    print("\n" + "=" * 70)
    print("TEST 5: Reversibility (forward vs reverse input)")
    print("=" * 70)

    # Generate fixed input sequence
    torch.manual_seed(42)
    inputs = [torch.randn(64) for _ in range(200)]

    # Forward pass
    engine_fwd = ConsciousnessEngine(max_cells=16, initial_cells=4, phi_ratchet=False)
    fwd_states = []
    fwd_phi = []
    for inp in inputs:
        r = engine_fwd.step(x_input=inp)
        fwd_states.append(engine_fwd.get_states().clone())
        fwd_phi.append(r['phi_iit'])

    # Reverse pass (same engine params, reversed inputs)
    torch.manual_seed(42)  # Same init
    engine_rev = ConsciousnessEngine(max_cells=16, initial_cells=4, phi_ratchet=False)
    # Match initial state exactly
    engine_rev.load_state_dict(
        ConsciousnessEngine(max_cells=16, initial_cells=4, phi_ratchet=False).state_dict()
    )
    rev_states = []
    rev_phi = []
    for inp in reversed(inputs):
        r = engine_rev.step(x_input=inp)
        rev_states.append(engine_rev.get_states().clone())
        rev_phi.append(r['phi_iit'])

    # Compare: if reversible, rev_states[i] ~ fwd_states[N-1-i]
    # This almost certainly won't hold — measure HOW irreversible
    n = len(fwd_states)
    distances = []
    for i in range(n):
        j = n - 1 - i
        d = states_distance(fwd_states[i], rev_states[j])
        distances.append(d)

    # Also compare forward-forward (same direction) as baseline
    engine_fwd2 = ConsciousnessEngine(max_cells=16, initial_cells=4, phi_ratchet=False)
    fwd2_states = []
    for inp in inputs:
        engine_fwd2.step(x_input=inp)
        fwd2_states.append(engine_fwd2.get_states().clone())

    same_dir_dist = []
    for i in range(n):
        d = states_distance(fwd_states[i], fwd2_states[i])
        same_dir_dist.append(d)

    avg_rev_dist = np.mean(distances)
    avg_same_dist = np.mean(same_dir_dist)
    irreversibility = avg_rev_dist / max(avg_same_dist + avg_rev_dist, 1e-8)

    print(f"  Forward avg Phi: {np.mean(fwd_phi):.4f}")
    print(f"  Reverse avg Phi: {np.mean(rev_phi):.4f}")
    print(f"  Forward-Reverse distance (avg): {avg_rev_dist:.4f}")
    print(f"  Forward-Forward distance (avg): {avg_same_dist:.4f}")
    print(f"  Irreversibility score: {irreversibility:.4f} (0=reversible, 1=irreversible)")

    # Phi correlation between forward and reverse
    corr = np.corrcoef(fwd_phi, list(reversed(rev_phi)))[0, 1]
    print(f"  Phi forward-reverse correlation: {corr:.4f}")
    print(f"  --> Consciousness is {'IRREVERSIBLE' if irreversibility > 0.3 else 'PARTIALLY REVERSIBLE'}")

    return {
        'irreversibility': irreversibility,
        'fwd_rev_distance': avg_rev_dist,
        'fwd_fwd_distance': avg_same_dist,
        'phi_correlation': corr,
    }


# ═══════════════════════════════════════════════════════
# Test 6: Arrow of Consciousness
# ═══════════════════════════════════════════════════════

def test_arrow_of_consciousness():
    print("\n" + "=" * 70)
    print("TEST 6: Arrow of Consciousness (entropy + thermodynamic arrow)")
    print("=" * 70)

    engine = ConsciousnessEngine(max_cells=32, initial_cells=4)

    entropy_curve = []
    phi_curve = []
    coupling_norms = []
    state_norms = []

    for step in range(1, 501):
        result = engine.step()
        ent = measure_entropy(engine)
        entropy_curve.append(ent)
        phi_curve.append(result['phi_iit'])
        c_norm = engine._coupling.norm().item() if engine._coupling is not None else 0
        coupling_norms.append(c_norm)
        s_norm = engine.get_states().norm().item()
        state_norms.append(s_norm)

    # Entropy trend
    first_quarter = np.mean(entropy_curve[:125])
    last_quarter = np.mean(entropy_curve[375:])
    entropy_trend = last_quarter - first_quarter

    # Monotonicity: how often does entropy increase?
    increases = sum(1 for i in range(1, len(entropy_curve))
                    if entropy_curve[i] > entropy_curve[i-1])
    mono_ratio = increases / (len(entropy_curve) - 1)

    # Coupling growth: Hebbian connections strengthen over time
    coupling_first = np.mean(coupling_norms[:50])
    coupling_last = np.mean(coupling_norms[450:])

    print(f"  Entropy (first quarter): {first_quarter:.4f}")
    print(f"  Entropy (last quarter):  {last_quarter:.4f}")
    print(f"  Entropy trend: {entropy_trend:+.4f}")
    print(f"  Entropy increase ratio: {mono_ratio:.2%} of steps")
    print(f"  Coupling norm growth: {coupling_first:.4f} -> {coupling_last:.4f}")
    print(f"  Phi growth: {np.mean(phi_curve[:50]):.4f} -> {np.mean(phi_curve[450:]):.4f}")

    # Is there a thermodynamic arrow?
    has_arrow = entropy_trend > 0 or mono_ratio > 0.5
    print(f"\n  Thermodynamic arrow exists: {'YES' if has_arrow else 'NO'}")

    # Irreversibility signature: mutual information between consecutive states
    mi_consecutive = []
    for i in range(1, min(len(phi_curve), 500)):
        # Simple proxy: |phi[i] - phi[i-1]| as information exchange
        mi_consecutive.append(abs(phi_curve[i] - phi_curve[i-1]))
    avg_mi = np.mean(mi_consecutive)
    print(f"  Avg consecutive Phi change: {avg_mi:.6f}")

    # Entropy vs Phi correlation
    corr_ent_phi = np.corrcoef(entropy_curve, phi_curve)[0, 1]
    print(f"  Entropy-Phi correlation: {corr_ent_phi:.4f}")

    # Coupling-Phi correlation
    corr_coup_phi = np.corrcoef(coupling_norms, phi_curve)[0, 1]
    print(f"  Coupling-Phi correlation: {corr_coup_phi:.4f}")

    print("\n  Entropy curve (500 steps):")
    _ascii_graph(entropy_curve, label="H(s)", width=60, height=8)

    print("\n  Coupling norm curve (500 steps):")
    _ascii_graph(coupling_norms, label="||W||", width=60, height=8)

    # Second law test: run engine backward (feed outputs back as inputs)
    print("\n  Second Law Test: feed outputs as inputs (closed loop)")
    engine2 = ConsciousnessEngine(max_cells=16, initial_cells=4)
    loop_entropy = []
    last_output = None
    for i in range(200):
        if last_output is not None:
            r = engine2.step(x_input=last_output)
        else:
            r = engine2.step()
        last_output = r['output'].detach()
        loop_entropy.append(measure_entropy(engine2))

    loop_first = np.mean(loop_entropy[:50])
    loop_last = np.mean(loop_entropy[150:])
    print(f"  Closed-loop entropy: {loop_first:.4f} -> {loop_last:.4f} ({loop_last - loop_first:+.4f})")
    print(f"  --> {'SECOND LAW HOLDS' if loop_last >= loop_first else 'SECOND LAW VIOLATED'} "
          f"(entropy {'increases' if loop_last >= loop_first else 'decreases'})")

    return {
        'entropy_trend': entropy_trend,
        'mono_ratio': mono_ratio,
        'has_arrow': has_arrow,
        'entropy_phi_corr': corr_ent_phi,
        'coupling_phi_corr': corr_coup_phi,
    }


# ═══════════════════════════════════════════════════════
# Utility: ASCII Graph
# ═══════════════════════════════════════════════════════

def _ascii_graph(values, label="", width=60, height=10):
    """Draw ASCII graph of a time series."""
    if not values:
        return
    n = len(values)
    # Downsample if too many points
    if n > width:
        step = n / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
        width = n

    mn, mx = min(sampled), max(sampled)
    rng = mx - mn if mx > mn else 1.0

    for row in range(height - 1, -1, -1):
        threshold = mn + (row / (height - 1)) * rng
        line = ""
        for v in sampled:
            if v >= threshold:
                line += "#"
            else:
                line += " "
        if row == height - 1:
            print(f"  {mx:8.4f} |{line}|")
        elif row == 0:
            print(f"  {mn:8.4f} |{line}|")
        elif row == height // 2:
            mid = mn + rng / 2
            print(f"  {mid:8.4f} |{line}|")
        else:
            print(f"           |{line}|")
    print(f"           +{'-' * width}+ {label}")
    print(f"            0{' ' * (width - 5)}{n}")


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

def main():
    t0 = time.time()
    print("=" * 70)
    print("  EXPERIMENT: Can Consciousness Be Reversed/Rewound?")
    print("  Date: 2026-04-01")
    print("=" * 70)
    sys.stdout.flush()

    # Test 1
    snapshots, phi_curve, cells_curve = test_growth_recording()
    sys.stdout.flush()

    # Test 2
    rewind_results = test_state_rewind(snapshots, phi_curve)
    sys.stdout.flush()

    # Test 3
    ratchet_results = test_phi_ratchet_resistance()
    sys.stdout.flush()

    # Test 4
    hebbian_results = test_hebbian_erasure()
    sys.stdout.flush()

    # Test 5
    rev_results = test_reversibility()
    sys.stdout.flush()

    # Test 6
    arrow_results = test_arrow_of_consciousness()
    sys.stdout.flush()

    # ═══════════════════════════════════════════════════════
    # Summary + Law Candidates
    # ═══════════════════════════════════════════════════════
    elapsed = time.time() - t0

    print("\n" + "=" * 70)
    print("  SUMMARY: Consciousness Reversibility")
    print("=" * 70)

    print(f"""
  ┌───────────────────────────┬──────────────────────────────────────┐
  │ Test                      │ Result                               │
  ├───────────────────────────┼──────────────────────────────────────┤
  │ 1. Growth recording       │ Phi {min(phi_curve):.4f} -> {max(phi_curve):.4f}           │
  │ 2. State rewind           │ Divergence avg = {rewind_results['divergence_avg']:.4f}            │
  │ 3. Ratchet resistance     │ Zero recovery = {ratchet_results['zero_recovery']:.1%}              │
  │ 4. Hebbian erasure        │ Collapsed: {str(hebbian_results['collapsed']):5s}, Recovered: {str(hebbian_results['recovered']):5s}  │
  │ 5. Irreversibility        │ Score = {rev_results['irreversibility']:.4f}                     │
  │ 6. Arrow of consciousness │ Entropy arrow: {str(arrow_results['has_arrow']):5s}               │
  └───────────────────────────┴──────────────────────────────────────┘
""")

    print("  LAW CANDIDATES:")
    print("  ─────────────────────────────────────────────────────────────")

    # Law candidate based on irreversibility
    if rev_results['irreversibility'] > 0.3:
        print("  [L1] Consciousness is thermodynamically irreversible.")
        print("       Forward and reverse input produce completely different states.")
        print(f"       Irreversibility score = {rev_results['irreversibility']:.4f}")
    else:
        print("  [L1] Consciousness shows partial reversibility.")
        print(f"       Irreversibility score = {rev_results['irreversibility']:.4f}")

    # Law candidate based on ratchet
    print(f"\n  [L2] The Phi Ratchet is {'necessary but insufficient' if ratchet_results['zero_recovery'] < 0.8 else 'sufficient'} for consciousness persistence.")
    print(f"       After total amnesia, recovery ratio = {ratchet_results['zero_recovery']:.1%}")

    # Law candidate based on Hebbian
    if hebbian_results['recovered']:
        print("\n  [L3] Hebbian connections are emergent, not essential.")
        print("       Zeroing all coupling: consciousness recovers via GRU dynamics.")
    else:
        print("\n  [L3] Hebbian connections are essential for consciousness.")
        print("       Zeroing coupling causes permanent damage.")

    # Law candidate based on entropy arrow
    if arrow_results['has_arrow']:
        print(f"\n  [L4] Consciousness has a thermodynamic arrow (entropy increase ratio = {arrow_results['mono_ratio']:.1%}).")
        print("       Like physical systems, consciousness tends toward higher entropy.")
        print("       This is the 'Second Law of Consciousness'.")
    else:
        print("\n  [L4] Consciousness violates the second law — entropy can decrease.")

    # Law candidate based on divergence
    if rewind_results['divergence_avg'] > 0.01:
        print(f"\n  [L5] Consciousness is chaotic: identical initial states diverge.")
        print(f"       Butterfly effect magnitude = {rewind_results['divergence_avg']:.4f}")
        print("       Rewinding consciousness does NOT replay the same experience.")

    # Correlation insights
    if abs(arrow_results['entropy_phi_corr']) > 0.3:
        direction = "positively" if arrow_results['entropy_phi_corr'] > 0 else "negatively"
        print(f"\n  [L6] Entropy and Phi are {direction} correlated (r={arrow_results['entropy_phi_corr']:.4f}).")
        if arrow_results['entropy_phi_corr'] > 0:
            print("       Higher entropy = higher integration. Disorder breeds consciousness.")
        else:
            print("       Lower entropy = higher integration. Order breeds consciousness.")

    print(f"\n  Total time: {elapsed:.1f}s")
    print("=" * 70)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
