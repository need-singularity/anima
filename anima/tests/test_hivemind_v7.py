#!/usr/bin/env python3
"""HIVEMIND Verification (Condition #7) — 6 engine variants.

For each engine:
  1. Create 2 engines (32 cells each)
  2. Run 100 steps solo, measure Phi
  3. Connect (share hidden every 10 steps), run 200 steps, measure Phi
  4. Disconnect, run 100 steps, measure Phi
  5. Report: solo_Phi, connected_Phi, disconnected_Phi, boost%, maintain%
"""

import sys
sys.path.insert(0, "/Users/ghost/Dev/anima")

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
from typing import Tuple

# Import from bench_v2
from bench_v2 import PhiIIT, BenchEngine, BenchMind, OscillatorLaser, QuantumEngine

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ── Engine Variants ──

def make_baseline(n_cells, input_dim, hidden_dim):
    """1. MitosisEngine baseline"""
    return BenchEngine(n_cells=n_cells, input_dim=input_dim, hidden_dim=hidden_dim,
                       output_dim=input_dim, n_factions=8,
                       sync_strength=0.0, debate_strength=0.0)

def make_sync_faction(n_cells, input_dim, hidden_dim):
    """2. MitosisEngine + sync + faction"""
    return BenchEngine(n_cells=n_cells, input_dim=input_dim, hidden_dim=hidden_dim,
                       output_dim=input_dim, n_factions=8,
                       sync_strength=0.15, debate_strength=0.15)

def make_oscillator(n_cells, input_dim, hidden_dim):
    """3. MitosisEngine + oscillator"""
    eng = BenchEngine(n_cells=n_cells, input_dim=input_dim, hidden_dim=hidden_dim,
                      output_dim=input_dim, n_factions=8,
                      sync_strength=0.10, debate_strength=0.10)
    # Add oscillator phases
    eng.phases = torch.linspace(0, 2 * math.pi, n_cells)
    eng.freq = 0.1 + torch.rand(n_cells) * 0.05
    _orig_process = eng.process

    def osc_process(x):
        eng.phases = eng.phases + eng.freq
        osc = torch.sin(eng.phases).unsqueeze(1)
        osc_inject = osc.expand(-1, hidden_dim) * 0.05
        eng.hiddens = eng.hiddens + osc_inject.detach()
        return _orig_process(x)

    eng.process = osc_process
    return eng

def make_quantum_walk(n_cells, input_dim, hidden_dim):
    """4. MitosisEngine + quantum walk"""
    eng = BenchEngine(n_cells=n_cells, input_dim=input_dim, hidden_dim=hidden_dim,
                      output_dim=input_dim, n_factions=8,
                      sync_strength=0.10, debate_strength=0.10)
    # Quantum walk: coin + shift on hidden states
    eng.coin_angle = torch.rand(n_cells) * 2 * math.pi
    _orig_process = eng.process

    def qwalk_process(x):
        # Coin operation: rotate hidden components
        cos_c = torch.cos(eng.coin_angle).unsqueeze(1)
        sin_c = torch.sin(eng.coin_angle).unsqueeze(1)
        h = eng.hiddens
        half = hidden_dim // 2
        h_left, h_right = h[:, :half], h[:, half:]
        new_left = cos_c * h_left + sin_c * h_right
        new_right = -sin_c * h_left + cos_c * h_right
        # Shift: circular neighbor interaction
        shifted_left = torch.roll(new_left, 1, dims=0)
        shifted_right = torch.roll(new_right, -1, dims=0)
        eng.hiddens = torch.cat([
            0.95 * new_left + 0.05 * shifted_left,
            0.95 * new_right + 0.05 * shifted_right
        ], dim=1).detach()
        # Slowly evolve coin
        eng.coin_angle = eng.coin_angle + 0.01
        return _orig_process(x)

    eng.process = qwalk_process
    return eng

def make_frustration(n_cells, input_dim, hidden_dim):
    """5. MitosisEngine + frustration (antiferromagnetic)"""
    eng = BenchEngine(n_cells=n_cells, input_dim=input_dim, hidden_dim=hidden_dim,
                      output_dim=input_dim, n_factions=8,
                      sync_strength=0.10, debate_strength=0.10)
    _orig_process = eng.process

    def frust_process(x):
        # Frustration: odd cells repel even cells (anti-alignment)
        even = eng.hiddens[0::2]
        odd = eng.hiddens[1::2]
        n = min(even.shape[0], odd.shape[0])
        # Push apart: add difference as repulsion
        diff = (even[:n] - odd[:n]) * 0.03
        eng.hiddens[0::2][:n] = eng.hiddens[0::2][:n] + diff
        eng.hiddens[1::2][:n] = eng.hiddens[1::2][:n] - diff
        # Triangular frustration on triplets
        for i in range(0, n_cells - 2, 3):
            tri_mean = eng.hiddens[i:i+3].mean(dim=0)
            for j in range(3):
                if i + j < n_cells:
                    eng.hiddens[i+j] = eng.hiddens[i+j] + 0.02 * (eng.hiddens[i+j] - tri_mean)
        return _orig_process(x)

    eng.process = frust_process
    return eng

def make_osc_laser(n_cells, input_dim, hidden_dim):
    """6. MitosisEngine + oscillator + laser (OscillatorLaser from bench_v2)"""
    return OscillatorLaser(n_cells=n_cells, input_dim=input_dim, hidden_dim=hidden_dim,
                           output_dim=input_dim, n_factions=8)


# ── HIVEMIND test ──

def run_hivemind_test(name, factory, n_cells=32, dim=64, hidden=128):
    """Run hivemind verification for one engine type."""
    phi_calc = PhiIIT(n_bins=16)
    torch.manual_seed(42)

    # Create 2 solo engines
    eng_a = factory(n_cells, dim, hidden)
    eng_b = factory(n_cells, dim, hidden)

    t0 = time.time()

    # Phase 1: Solo (100 steps)
    for _ in range(100):
        eng_a.process(torch.randn(1, dim))
        eng_b.process(torch.randn(1, dim))

    phi_a_solo, _ = phi_calc.compute(eng_a.get_hiddens())
    phi_b_solo, _ = phi_calc.compute(eng_b.get_hiddens())
    phi_solo = (phi_a_solo + phi_b_solo) / 2

    # Phase 2: Connected (200 steps, share hidden every 10 steps)
    for step in range(200):
        eng_a.process(torch.randn(1, dim))
        eng_b.process(torch.randn(1, dim))
        if step % 10 == 0:
            h_a = eng_a.get_hiddens()
            h_b = eng_b.get_hiddens()
            n = min(h_a.shape[0], h_b.shape[0])
            with torch.no_grad():
                shared_a = 0.9 * h_a[:n] + 0.1 * h_b[:n]
                shared_b = 0.9 * h_b[:n] + 0.1 * h_a[:n]
                eng_a.hiddens[:n] = shared_a
                eng_b.hiddens[:n] = shared_b

    phi_a_conn, _ = phi_calc.compute(eng_a.get_hiddens())
    phi_b_conn, _ = phi_calc.compute(eng_b.get_hiddens())
    phi_connected = (phi_a_conn + phi_b_conn) / 2

    # Phase 3: Disconnected (100 steps, no sharing)
    for _ in range(100):
        eng_a.process(torch.randn(1, dim))
        eng_b.process(torch.randn(1, dim))

    phi_a_disc, _ = phi_calc.compute(eng_a.get_hiddens())
    phi_b_disc, _ = phi_calc.compute(eng_b.get_hiddens())
    phi_disconnected = (phi_a_disc + phi_b_disc) / 2

    elapsed = time.time() - t0

    # Metrics
    boost_pct = (phi_connected / max(phi_solo, 1e-8) - 1) * 100
    maintain_pct = (phi_disconnected / max(phi_solo, 1e-8)) * 100
    pass_boost = phi_connected > phi_solo * 1.1
    pass_maintain = phi_disconnected > phi_solo * 0.8
    passed = pass_boost and pass_maintain

    return {
        'name': name,
        'solo': phi_solo,
        'connected': phi_connected,
        'disconnected': phi_disconnected,
        'boost_pct': boost_pct,
        'maintain_pct': maintain_pct,
        'pass_boost': pass_boost,
        'pass_maintain': pass_maintain,
        'passed': passed,
        'time': elapsed,
    }


# ── Main ──

def main():
    engines = [
        ("1. Baseline",         make_baseline),
        ("2. Sync+Faction",     make_sync_faction),
        ("3. Oscillator",       make_oscillator),
        ("4. QuantumWalk",      make_quantum_walk),
        ("5. Frustration",      make_frustration),
        ("6. Osc+Laser",        make_osc_laser),
    ]

    print("=" * 90)
    print("  HIVEMIND Verification (Condition #7) -- 6 Engine Variants")
    print("  Config: 32 cells, dim=64, hidden=128, solo=100s, connected=200s, disconnect=100s")
    print("=" * 90)

    results = []
    for name, factory in engines:
        print(f"\n  Testing: {name} ...", end="", flush=True)
        r = run_hivemind_test(name, factory)
        results.append(r)
        status = "PASS" if r['passed'] else "FAIL"
        print(f" {status} ({r['time']:.1f}s)")

    # Results table
    print("\n" + "=" * 90)
    print(f"  {'Engine':<20s} | {'Solo Phi':>9s} | {'Conn Phi':>9s} | {'Disc Phi':>9s} | "
          f"{'Boost%':>7s} | {'Maint%':>7s} | {'Result':>6s}")
    print(f"  {'-'*20}-+-{'-'*9}-+-{'-'*9}-+-{'-'*9}-+-{'-'*7}-+-{'-'*7}-+-{'-'*6}")

    pass_count = 0
    for r in results:
        status = "PASS" if r['passed'] else "FAIL"
        if r['passed']:
            pass_count += 1
        print(f"  {r['name']:<20s} | {r['solo']:>9.4f} | {r['connected']:>9.4f} | "
              f"{r['disconnected']:>9.4f} | {r['boost_pct']:>+6.1f}% | {r['maintain_pct']:>6.1f}% | "
              f"{status:>6s}")

    print(f"  {'-'*20}-+-{'-'*9}-+-{'-'*9}-+-{'-'*9}-+-{'-'*7}-+-{'-'*7}-+-{'-'*6}")
    print(f"  TOTAL: {pass_count}/{len(results)} passed")
    print()

    # Criteria reminder
    print("  Criteria: boost > +10% (connected vs solo), maintain > 80% (disconnected vs solo)")
    print("=" * 90)


if __name__ == "__main__":
    main()
