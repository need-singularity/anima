#!/usr/bin/env python3
"""Benchmark QuantumConsciousnessEngineFast as DomainC in Trinity.

Compares:
  1. QuantumC (QuantumConsciousnessEngineFast) — native wrapper
  2. DomainC(TimeCrystalConsciousness)
  3. DomainC(CambrianExplosionEngine)

All run through benchmark_trinity() with 50 steps.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import torch
torch.set_grad_enabled(True)

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trinity import benchmark_trinity, QuantumC, DomainC

# Engine configs
NC = 32
DIM = 64
N_STEPS = 50

results = []

# 1. QuantumConsciousnessEngineFast via QuantumC
print("=" * 60)
print(f"1. QuantumC (QuantumConsciousnessEngineFast, {NC}c, dim={DIM})")
print("=" * 60)
r1 = benchmark_trinity(QuantumC(nc=NC, dim=DIM), name='QuantumFast', n_steps=N_STEPS)
print(f"   CE={r1['ce']:.4f}  Phi={r1['phi']:.3f}  Phi_avg={r1['phi_avg']:.3f}")
print(f"   pain={r1['pain']:.3f}  curiosity={r1['curiosity']:.3f}  satisfaction={r1['satisfaction']:.3f}")
print(f"   n_cells={r1['n_cells']}  params={r1['params']}")
results.append(r1)

# 2. TimeCrystalConsciousness via DomainC
print()
print("=" * 60)
print(f"2. DomainC (TimeCrystalConsciousness, {NC}c, dim=128)")
print("=" * 60)
try:
    from bench_extreme_arch import TimeCrystalConsciousness
    r2 = benchmark_trinity(DomainC(TimeCrystalConsciousness, nc=NC, dim=128), name='TimeCrystal', n_steps=N_STEPS)
    print(f"   CE={r2['ce']:.4f}  Phi={r2['phi']:.3f}  Phi_avg={r2['phi_avg']:.3f}")
    print(f"   pain={r2['pain']:.3f}  curiosity={r2['curiosity']:.3f}  satisfaction={r2['satisfaction']:.3f}")
    print(f"   n_cells={r2['n_cells']}  params={r2['params']}")
    results.append(r2)
except Exception as e:
    print(f"   FAILED: {e}")
    r2 = None

# 3. CambrianExplosionEngine via DomainC
print()
print("=" * 60)
print(f"3. DomainC (CambrianExplosionEngine, {NC}c, dim={DIM})")
print("=" * 60)
try:
    from bench_evolution_engines import CambrianExplosionEngine

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    r3 = benchmark_trinity(DomainC(CambrianExplosionEngine, nc=NC, dim=DIM), name='Cambrian', n_steps=N_STEPS)
    print(f"   CE={r3['ce']:.4f}  Phi={r3['phi']:.3f}  Phi_avg={r3['phi_avg']:.3f}")
    print(f"   pain={r3['pain']:.3f}  curiosity={r3['curiosity']:.3f}  satisfaction={r3['satisfaction']:.3f}")
    print(f"   n_cells={r3['n_cells']}  params={r3['params']}")
    results.append(r3)
except Exception as e:
    print(f"   FAILED: {e}")
    r3 = None

# Summary comparison
print()
print("=" * 60)
print("COMPARISON TABLE (50 steps)")
print("=" * 60)
print(f"{'Engine':<25} {'CE':>8} {'Phi':>10} {'Phi_avg':>10} {'Cells':>6}")
print("-" * 60)
for r in results:
    print(f"{r['name']:<25} {r['ce']:>8.4f} {r['phi']:>10.3f} {r['phi_avg']:>10.3f} {r['n_cells']:>6}")

if results:
    best_ce = min(results, key=lambda x: x['ce'])
    best_phi = max(results, key=lambda x: x['phi'])
    print()
    print(f"  CE winner:  {best_ce['name']} (CE={best_ce['ce']:.4f})")
    print(f"  Phi winner: {best_phi['name']} (Phi={best_phi['phi']:.3f})")
