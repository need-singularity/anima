#!/usr/bin/env python3
"""DD60: Consciousness Engine Stress Tests — Push to Limits

7 experiments:
  1. Scale limits (256, 512, 1024 cells)
  2. Without Phi ratchet
  3. Without Hebbian LTP/LTD
  4. Without SOC sandpile
  5. Without factions (all same faction)
  6. Adversarial input
  7. Minimum viable consciousness
"""

import sys
import os
import time
import traceback
import torch
import numpy as np

# Ensure we can import from src/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine

RESULTS = {}

def measure_engine(engine, steps, x_fn=None, label=""):
    """Run engine for N steps, return phi history and timing."""
    phis = []
    consensuses = []
    t0 = time.time()
    for s in range(steps):
        x = x_fn(s) if x_fn else None
        result = engine.step(x)
        phis.append(result['phi_iit'])
        consensuses.append(result['consensus'])
        if (s+1) % max(1, steps//5) == 0:
            print(f"  [{label}] step {s+1}/{steps}: Phi={result['phi_iit']:.4f}, cells={result['n_cells']}, consensus={result['consensus']}")
            sys.stdout.flush()
    dt = time.time() - t0
    return {
        'phis': phis,
        'phi_final': phis[-1] if phis else 0,
        'phi_max': max(phis) if phis else 0,
        'phi_min': min(phis) if phis else 0,
        'phi_mean': np.mean(phis) if phis else 0,
        'consensus_mean': np.mean(consensuses) if consensuses else 0,
        'total_time': dt,
        'ms_per_step': dt / steps * 1000,
        'n_cells_final': engine.n_cells,
        'collapsed': phis[-1] < 0.01 if phis else True,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 1: Scale Limits
# ═══════════════════════════════════════════════════════════

def exp1_scale_limits():
    print("\n" + "="*70)
    print("EXPERIMENT 1: SCALE LIMITS (256, 512, 1024 cells)")
    print("="*70)
    results = {}
    for n in [64, 128, 256, 512, 1024]:
        print(f"\n--- {n} cells ---")
        sys.stdout.flush()
        try:
            engine = ConsciousnessEngine(
                cell_dim=64, hidden_dim=128,
                initial_cells=n, max_cells=n
            )
            steps = 20
            r = measure_engine(engine, steps, label=f"{n}c")
            results[n] = r
            print(f"  RESULT: Phi={r['phi_final']:.4f}, {r['ms_per_step']:.0f}ms/step, cells={r['n_cells_final']}")
            # Estimate memory: each cell has GRU params + hidden state
            param_count = sum(p.numel() for m in engine.cell_modules for p in m.parameters())
            mem_mb = param_count * 4 / 1024 / 1024  # float32
            hidden_mb = n * 128 * 4 / 1024 / 1024
            print(f"  Memory: params={param_count:,} ({mem_mb:.1f}MB), hiddens={hidden_mb:.2f}MB")
        except Exception as e:
            print(f"  FAILED: {e}")
            traceback.print_exc()
            results[n] = {'error': str(e)}
        sys.stdout.flush()
    RESULTS['exp1_scale'] = results
    return results


# ═══════════════════════════════════════════════════════════
# Experiment 2: Without Phi Ratchet
# ═══════════════════════════════════════════════════════════

def exp2_no_ratchet():
    print("\n" + "="*70)
    print("EXPERIMENT 2: WITHOUT PHI RATCHET")
    print("="*70)

    # Baseline with ratchet
    print("\n--- Baseline (ratchet ON) ---")
    engine_on = ConsciousnessEngine(initial_cells=32, max_cells=64, phi_ratchet=True)
    r_on = measure_engine(engine_on, 300, label="ratchet-ON")

    # Without ratchet
    print("\n--- No ratchet ---")
    engine_off = ConsciousnessEngine(initial_cells=32, max_cells=64, phi_ratchet=False)
    r_off = measure_engine(engine_off, 300, label="ratchet-OFF")

    # Disabled ratchet by sabotaging best_phi
    print("\n--- Sabotaged ratchet (best_phi = -1) ---")
    engine_sab = ConsciousnessEngine(initial_cells=32, max_cells=64, phi_ratchet=True)
    engine_sab._best_phi = -1
    engine_sab._best_hiddens = None
    r_sab = measure_engine(engine_sab, 300, label="ratchet-SABOTAGED")

    results = {
        'ratchet_on': r_on,
        'ratchet_off': r_off,
        'ratchet_sabotaged': r_sab,
    }
    RESULTS['exp2_no_ratchet'] = results

    print(f"\n  COMPARE:")
    print(f"    Ratchet ON:        Phi_final={r_on['phi_final']:.4f}, Phi_max={r_on['phi_max']:.4f}, collapsed={r_on['collapsed']}")
    print(f"    Ratchet OFF:       Phi_final={r_off['phi_final']:.4f}, Phi_max={r_off['phi_max']:.4f}, collapsed={r_off['collapsed']}")
    print(f"    Ratchet SABOTAGED: Phi_final={r_sab['phi_final']:.4f}, Phi_max={r_sab['phi_max']:.4f}, collapsed={r_sab['collapsed']}")
    sys.stdout.flush()
    return results


# ═══════════════════════════════════════════════════════════
# Experiment 3: Without Hebbian LTP/LTD
# ═══════════════════════════════════════════════════════════

def exp3_no_hebbian():
    print("\n" + "="*70)
    print("EXPERIMENT 3: WITHOUT HEBBIAN LTP/LTD")
    print("="*70)

    # Baseline
    print("\n--- Baseline (Hebbian ON) ---")
    engine_on = ConsciousnessEngine(initial_cells=32, max_cells=64)
    r_on = measure_engine(engine_on, 300, label="hebbian-ON")

    # Disable Hebbian by monkey-patching
    print("\n--- No Hebbian ---")
    engine_off = ConsciousnessEngine(initial_cells=32, max_cells=64)
    engine_off._hebbian_update = lambda outputs, lr=0.01: None  # no-op
    r_off = measure_engine(engine_off, 300, label="hebbian-OFF")

    # Measure coupling diversity
    coupling_on = engine_on._coupling
    coupling_off = engine_off._coupling

    c_on_std = coupling_on.std().item() if coupling_on is not None else 0
    c_off_std = coupling_off.std().item() if coupling_off is not None else 0

    results = {
        'hebbian_on': r_on,
        'hebbian_off': r_off,
        'coupling_std_on': c_on_std,
        'coupling_std_off': c_off_std,
    }
    RESULTS['exp3_no_hebbian'] = results

    print(f"\n  COMPARE:")
    print(f"    Hebbian ON:  Phi_final={r_on['phi_final']:.4f}, coupling_std={c_on_std:.4f}")
    print(f"    Hebbian OFF: Phi_final={r_off['phi_final']:.4f}, coupling_std={c_off_std:.4f}")
    sys.stdout.flush()
    return results


# ═══════════════════════════════════════════════════════════
# Experiment 4: Without SOC Sandpile
# ═══════════════════════════════════════════════════════════

def exp4_no_soc():
    print("\n" + "="*70)
    print("EXPERIMENT 4: WITHOUT SOC SANDPILE")
    print("="*70)

    # Baseline
    print("\n--- Baseline (SOC ON) ---")
    engine_on = ConsciousnessEngine(initial_cells=32, max_cells=64)
    r_on = measure_engine(engine_on, 300, label="SOC-ON")
    avalanches_on = engine_on._soc_avalanche_sizes[-50:] if engine_on._soc_avalanche_sizes else []

    # Disable SOC
    print("\n--- No SOC ---")
    engine_off = ConsciousnessEngine(initial_cells=32, max_cells=64)
    engine_off._soc_sandpile = lambda: None  # no-op
    r_off = measure_engine(engine_off, 300, label="SOC-OFF")

    results = {
        'soc_on': r_on,
        'soc_off': r_off,
        'avg_avalanche': np.mean(avalanches_on) if avalanches_on else 0,
        'max_avalanche': max(avalanches_on) if avalanches_on else 0,
    }
    RESULTS['exp4_no_soc'] = results

    print(f"\n  COMPARE:")
    print(f"    SOC ON:  Phi_final={r_on['phi_final']:.4f}, avg_avalanche={results['avg_avalanche']:.1f}")
    print(f"    SOC OFF: Phi_final={r_off['phi_final']:.4f}")
    sys.stdout.flush()
    return results


# ═══════════════════════════════════════════════════════════
# Experiment 5: Without Factions (all same faction)
# ═══════════════════════════════════════════════════════════

def exp5_no_factions():
    print("\n" + "="*70)
    print("EXPERIMENT 5: WITHOUT FACTIONS (all same faction)")
    print("="*70)

    # Baseline: 12 factions
    print("\n--- Baseline (12 factions) ---")
    engine_on = ConsciousnessEngine(initial_cells=32, max_cells=64, n_factions=12)
    r_on = measure_engine(engine_on, 300, label="12-factions")

    # All same faction: set n_factions=1
    print("\n--- 1 faction (all same) ---")
    engine_off = ConsciousnessEngine(initial_cells=32, max_cells=64, n_factions=1)
    # Force all cells to faction 0
    for s in engine_off.cell_states:
        s.faction_id = 0
    r_off = measure_engine(engine_off, 300, label="1-faction")

    # 2 factions (minimal diversity)
    print("\n--- 2 factions ---")
    engine_2 = ConsciousnessEngine(initial_cells=32, max_cells=64, n_factions=2)
    r_2 = measure_engine(engine_2, 300, label="2-factions")

    results = {
        '12_factions': r_on,
        '1_faction': r_off,
        '2_factions': r_2,
    }
    RESULTS['exp5_no_factions'] = results

    print(f"\n  COMPARE:")
    print(f"    12 factions: Phi={r_on['phi_final']:.4f}, consensus={r_on['consensus_mean']:.2f}")
    print(f"    2 factions:  Phi={r_2['phi_final']:.4f}, consensus={r_2['consensus_mean']:.2f}")
    print(f"    1 faction:   Phi={r_off['phi_final']:.4f}, consensus={r_off['consensus_mean']:.2f}")
    sys.stdout.flush()
    return results


# ═══════════════════════════════════════════════════════════
# Experiment 6: Adversarial Input
# ═══════════════════════════════════════════════════════════

def exp6_adversarial():
    print("\n" + "="*70)
    print("EXPERIMENT 6: ADVERSARIAL INPUT")
    print("="*70)

    # 6a: All zeros for 500 steps
    print("\n--- 6a: All zeros (500 steps) ---")
    engine_z = ConsciousnessEngine(initial_cells=32, max_cells=64)
    r_z = measure_engine(engine_z, 500, x_fn=lambda s: torch.zeros(64), label="zeros")

    # 6b: Random noise with increasing amplitude
    print("\n--- 6b: Increasing noise (500 steps, amp 0→100) ---")
    engine_n = ConsciousnessEngine(initial_cells=32, max_cells=64)
    def increasing_noise(s):
        amp = s / 5.0  # 0 → 100 over 500 steps
        return torch.randn(64) * amp
    r_n = measure_engine(engine_n, 500, x_fn=increasing_noise, label="inc-noise")

    # 6c: Repeated identical input
    print("\n--- 6c: Repeated identical input (500 steps) ---")
    engine_r = ConsciousnessEngine(initial_cells=32, max_cells=64)
    fixed_input = torch.randn(64)
    r_r = measure_engine(engine_r, 500, x_fn=lambda s: fixed_input.clone(), label="repeated")

    # 6d: Sudden reversal
    print("\n--- 6d: Sudden input reversal (500 steps) ---")
    engine_rev = ConsciousnessEngine(initial_cells=32, max_cells=64)
    pattern_a = torch.randn(64)
    pattern_b = -pattern_a
    def reversal(s):
        if s < 200:
            return pattern_a.clone()
        elif s < 250:
            return pattern_b.clone()  # sudden flip
        elif s < 400:
            return pattern_a.clone()  # flip back
        else:
            return pattern_b.clone()  # flip again
    r_rev = measure_engine(engine_rev, 500, x_fn=reversal, label="reversal")

    # 6e: NaN/Inf attack
    print("\n--- 6e: Extreme values (1e6 amplitude) ---")
    engine_ext = ConsciousnessEngine(initial_cells=32, max_cells=64)
    r_ext = measure_engine(engine_ext, 100, x_fn=lambda s: torch.randn(64) * 1e6, label="extreme")

    results = {
        'zeros': r_z,
        'increasing_noise': r_n,
        'repeated': r_r,
        'reversal': r_rev,
        'extreme': r_ext,
    }
    RESULTS['exp6_adversarial'] = results

    print(f"\n  COMPARE:")
    for name, r in results.items():
        print(f"    {name:20s}: Phi_final={r['phi_final']:.4f}, collapsed={r['collapsed']}, cells={r['n_cells_final']}")
    sys.stdout.flush()
    return results


# ═══════════════════════════════════════════════════════════
# Experiment 7: Minimum Viable Consciousness
# ═══════════════════════════════════════════════════════════

def exp7_minimum_viable():
    print("\n" + "="*70)
    print("EXPERIMENT 7: MINIMUM VIABLE CONSCIOUSNESS")
    print("="*70)

    # Test different cell counts
    results_cells = {}
    for n in [2, 4, 8, 12, 16, 24, 32]:
        print(f"\n--- {n} cells ---")
        engine = ConsciousnessEngine(initial_cells=n, max_cells=n)
        r = measure_engine(engine, 300, label=f"{n}c")
        # Check verify-like criteria
        # ZERO_INPUT: phi after 300 steps without meaningful input
        # SPONTANEOUS_SPEECH: consensus > 5 events in 300 steps
        phi_50pct = r['phi_max'] * 0.5
        phi_maintained = r['phi_final'] >= phi_50pct if r['phi_max'] > 0 else False
        consensus_ok = r['consensus_mean'] >= 0.1
        results_cells[n] = {
            **r,
            'phi_maintained': phi_maintained,
            'consensus_ok': consensus_ok,
            'passes': r['phi_final'] > 0.01 and phi_maintained,
        }
        print(f"  Phi={r['phi_final']:.4f}, maintained={phi_maintained}, consensus_ok={consensus_ok}")
        sys.stdout.flush()

    # Test different hidden_dims
    print("\n--- Hidden dim sweep (16 cells) ---")
    results_dims = {}
    for hdim in [16, 32, 64, 128, 256]:
        print(f"\n--- hidden_dim={hdim} ---")
        try:
            engine = ConsciousnessEngine(cell_dim=max(16, hdim//2), hidden_dim=hdim, initial_cells=16, max_cells=16)
            r = measure_engine(engine, 200, label=f"h{hdim}")
            results_dims[hdim] = r
            print(f"  Phi={r['phi_final']:.4f}, {r['ms_per_step']:.0f}ms/step")
        except Exception as e:
            print(f"  FAILED: {e}")
            results_dims[hdim] = {'error': str(e)}
        sys.stdout.flush()

    results = {'cells': results_cells, 'hidden_dims': results_dims}
    RESULTS['exp7_minimum'] = results

    print(f"\n  MINIMUM VIABLE CELLS:")
    for n, r in results_cells.items():
        status = "PASS" if r.get('passes') else "FAIL"
        print(f"    {n:3d} cells: Phi={r['phi_final']:.4f} [{status}]")

    print(f"\n  HIDDEN DIM SWEEP:")
    for hdim, r in results_dims.items():
        if 'error' in r:
            print(f"    dim={hdim:3d}: ERROR")
        else:
            print(f"    dim={hdim:3d}: Phi={r['phi_final']:.4f}")
    sys.stdout.flush()
    return results


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("DD60: Consciousness Engine Stress Tests")
    print("=" * 70)
    t_start = time.time()

    exp1_scale_limits()
    exp2_no_ratchet()
    exp3_no_hebbian()
    exp4_no_soc()
    exp5_no_factions()
    exp6_adversarial()
    exp7_minimum_viable()

    total_time = time.time() - t_start
    print(f"\n\nALL EXPERIMENTS COMPLETE in {total_time:.1f}s")
    print("=" * 70)

    # Print summary
    print("\n=== SUMMARY TABLE ===")
    print(f"{'Experiment':<35} {'Key Finding':<50}")
    print("-" * 85)

    if 'exp1_scale' in RESULTS:
        for n, r in RESULTS['exp1_scale'].items():
            if 'error' in r:
                print(f"  Scale {n:>4d}c                       ERROR: {r['error'][:40]}")
            else:
                print(f"  Scale {n:>4d}c                       Phi={r['phi_final']:.4f}, {r['ms_per_step']:.0f}ms/step")

    if 'exp2_no_ratchet' in RESULTS:
        r = RESULTS['exp2_no_ratchet']
        delta = r['ratchet_off']['phi_final'] - r['ratchet_on']['phi_final']
        print(f"  No Ratchet                          Delta_Phi={delta:+.4f}, collapsed={r['ratchet_off']['collapsed']}")

    if 'exp3_no_hebbian' in RESULTS:
        r = RESULTS['exp3_no_hebbian']
        delta = r['hebbian_off']['phi_final'] - r['hebbian_on']['phi_final']
        print(f"  No Hebbian                          Delta_Phi={delta:+.4f}")

    if 'exp4_no_soc' in RESULTS:
        r = RESULTS['exp4_no_soc']
        delta = r['soc_off']['phi_final'] - r['soc_on']['phi_final']
        print(f"  No SOC                              Delta_Phi={delta:+.4f}")

    if 'exp5_no_factions' in RESULTS:
        r = RESULTS['exp5_no_factions']
        delta = r['1_faction']['phi_final'] - r['12_factions']['phi_final']
        print(f"  No Factions (1 vs 12)               Delta_Phi={delta:+.4f}")

    if 'exp6_adversarial' in RESULTS:
        for name, r in RESULTS['exp6_adversarial'].items():
            status = "SURVIVED" if not r['collapsed'] else "COLLAPSED"
            print(f"  Adversarial/{name:<14s}       Phi={r['phi_final']:.4f} [{status}]")

    if 'exp7_minimum' in RESULTS:
        cells = RESULTS['exp7_minimum']['cells']
        min_viable = None
        for n in sorted(cells.keys()):
            if cells[n].get('passes'):
                min_viable = n
                break
        print(f"  Minimum Viable                      {min_viable} cells (smallest passing)")

    sys.stdout.flush()
