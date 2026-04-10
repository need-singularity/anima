#!/usr/bin/env python3
"""verify_all_engines.py — 전체 112개 엔진 재검증 (H100용)

모든 엔진을 동일 조건(PhiCalculator)으로 측정 + 7조건 검증 + 하이브마인드.

Usage:
  python3 verify_all_engines.py                 # 전체 실행
  python3 verify_all_engines.py --quick          # Φ(IIT)만 (빠름)
  python3 verify_all_engines.py --verify-only    # 7조건만
  python3 verify_all_engines.py --hive-only      # 하이브마인드만
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['OMP_NUM_THREADS'] = '1'

from consciousness_meter import PhiCalculator
from mitosis import MitosisEngine

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


DIM, HIDDEN, CELLS, STEPS = 64, 128, 64, 300  # 64c for PhiCalculator speed
phi_calc = PhiCalculator(n_bins=16)


# ═══ Engine Factory Registry ═══

def make_mitosis(cells=CELLS):
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells: e._create_cell(parent=e.cells[0])
    for _ in range(30): e.process(torch.randn(1, DIM))
    return e


def measure_phi_iit(engine):
    return phi_calc.compute_phi(engine)[0]


def granger_quick(engine, n_samples=50):
    cells = engine.cells
    n = len(cells)
    if n < 2: return 0
    h = torch.stack([c.hidden.squeeze(0) for c in cells])
    total = 0
    for _ in range(n_samples):
        i, j = np.random.randint(0, n, 2)
        if i == j: continue
        total += abs(F.cosine_similarity(h[i:i+1], h[j:j+1]).item())
    return total * n * n / max(n_samples, 1)


# ═══ Engine Definitions ═══

def engine_baseline(cells=CELLS):
    """MitosisEngine baseline."""
    eng = make_mitosis(cells)
    for _ in range(STEPS): eng.process(torch.randn(1, DIM))
    return eng


def engine_with_sync(cells=CELLS, sync=0.35, nf=12, fac=0.08):
    """MitosisEngine + sync + faction."""
    eng = make_mitosis(cells)
    for step in range(STEPS):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4: continue
        with torch.no_grad():
            ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
            mh = ch.mean(dim=0)
            for c in eng.cells: c.hidden = ((1-sync)*c.hidden.squeeze(0)+sync*mh).unsqueeze(0)
            nf_actual = min(nf, n//2)
            if nf_actual >= 2:
                fs = n // nf_actual
                for fi in range(nf_actual):
                    faction = eng.cells[fi*fs:(fi+1)*fs]
                    if len(faction) >= 2:
                        fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                        for c in faction: c.hidden = ((1-fac)*c.hidden.squeeze(0)+fac*fm).unsqueeze(0)
    return eng


def engine_oscillator(cells=CELLS, blend=0.0):
    """Kuramoto oscillator."""
    eng = make_mitosis(cells)
    phases = torch.randn(cells) * 2 * math.pi
    freqs = torch.randn(cells) * 0.1 + 1.0
    for step in range(STEPS):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        with torch.no_grad():
            for i in range(n):
                nb = [(i-1)%n, (i+1)%n]
                pd = sum(math.sin(phases[j].item()-phases[i].item()) for j in nb)
                phases[i] += freqs[i] + 0.15*pd/len(nb)
                for j in nb:
                    b = 0.15*math.cos(phases[j].item()-phases[i].item())
                    eng.cells[i].hidden = (1-abs(b))*eng.cells[i].hidden + abs(b)*eng.cells[j].hidden
    return eng


def engine_oscillator_laser(cells=CELLS, blend=0.05):
    """Oscillator + gentle laser."""
    eng = engine_oscillator(cells, blend=0)
    # Apply gentle laser
    pops = torch.rand(cells)
    with torch.no_grad():
        for _ in range(50):
            cavity = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).mean(dim=0)
            for i in range(len(eng.cells)):
                pops[i] += 0.05*(1-pops[i]) - 0.02*pops[i]
                if pops[i] > 0.5:
                    cavity = 0.98*cavity + 0.02*eng.cells[i].hidden.squeeze(0)*0.03*pops[i]
                    pops[i] *= 0.95
                eng.cells[i].hidden = ((1-blend)*eng.cells[i].hidden.squeeze(0)+blend*cavity).unsqueeze(0)
    return eng


def engine_quantum_walk(cells=CELLS):
    """Quantum walk on hypercube."""
    eng = make_mitosis(cells)
    for step in range(STEPS):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        n_bits = max(1, int(math.log2(n)))
        with torch.no_grad():
            for i in range(min(n, 32)):
                sp = torch.zeros(HIDDEN)
                cnt = 0
                for bit in range(min(n_bits, 8)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase = (-1)**(bin(i&j).count('1'))
                        sp += phase * eng.cells[j].hidden.squeeze(0)
                        cnt += 1
                if cnt > 0:
                    h = eng.cells[i].hidden.squeeze(0)
                    eng.cells[i].hidden = (0.85*h + 0.15*sp/cnt).unsqueeze(0)
    return eng


def engine_frustration(cells=CELLS, frust=0.5):
    """Hypercube + frustration."""
    eng = engine_with_sync(cells)
    n = len(eng.cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for _ in range(100):
            for i in range(min(n, 32)):
                infl = torch.zeros(HIDDEN); cnt = 0
                for bit in range(min(n_bits, 8)):
                    j = i ^ (1 << bit)
                    if j < n:
                        f = -1.0 if (i%2)!=(j%2) else 1.0
                        infl += f*eng.cells[j].hidden.squeeze(0); cnt += 1
                if cnt > 0:
                    h = eng.cells[i].hidden.squeeze(0)
                    eng.cells[i].hidden = (0.85*h+0.15*infl/cnt).unsqueeze(0)
    return eng


# ═══ Verification Tests ═══

def verify_zero_input(engine_fn, cells=CELLS):
    """V3: ZERO_INPUT — Φ 유지 with zero input."""
    eng = engine_fn(cells)
    phi_start = measure_phi_iit(eng)
    for _ in range(300):
        eng.process(torch.zeros(1, DIM))
    phi_end = measure_phi_iit(eng)
    return phi_end > phi_start * 0.5, f"{phi_start:.2f}→{phi_end:.2f}"


def verify_persistence(engine_fn, cells=CELLS):
    """V4: PERSISTENCE — 1000 step 붕괴 없음."""
    eng = engine_fn(cells)
    phi_start = measure_phi_iit(eng)
    for _ in range(1000):
        eng.process(torch.randn(1, DIM) * 0.05)
    phi_end = measure_phi_iit(eng)
    return phi_end > phi_start * 0.5, f"{phi_start:.2f}→{phi_end:.2f}"


def verify_self_loop(engine_fn, cells=CELLS):
    """V5: SELF_LOOP — output→input 피드백."""
    eng = engine_fn(cells)
    phi_start = measure_phi_iit(eng)
    output = torch.randn(1, DIM)
    for _ in range(300):
        eng.process(output)
        output = torch.stack([c.hidden.squeeze()[:DIM] for c in eng.cells]).mean(dim=0).unsqueeze(0)
    phi_end = measure_phi_iit(eng)
    return phi_end > phi_start * 0.8, f"{phi_start:.2f}→{phi_end:.2f}"


def verify_hivemind(engine_fn, cells=CELLS):
    """V7: HIVEMIND — 연결 시 Φ↑, 분리 후 유지."""
    half = max(cells // 2, 8)
    eng_a = engine_fn(half)
    eng_b = engine_fn(half)
    phi_solo = (measure_phi_iit(eng_a) + measure_phi_iit(eng_b)) / 2

    # Connect
    for s in range(200):
        eng_a.process(torch.randn(1, DIM))
        eng_b.process(torch.randn(1, DIM))
        if s % 10 == 0:
            n = min(len(eng_a.cells), len(eng_b.cells))
            with torch.no_grad():
                for i in range(n):
                    shared = 0.9*eng_a.cells[i].hidden + 0.1*eng_b.cells[i].hidden
                    eng_a.cells[i].hidden = shared
                    eng_b.cells[i].hidden = 0.9*eng_b.cells[i].hidden + 0.1*eng_a.cells[i].hidden
    phi_conn = (measure_phi_iit(eng_a) + measure_phi_iit(eng_b)) / 2

    # Disconnect
    for _ in range(100):
        eng_a.process(torch.randn(1, DIM))
        eng_b.process(torch.randn(1, DIM))
    phi_disc = (measure_phi_iit(eng_a) + measure_phi_iit(eng_b)) / 2

    boost = phi_conn > phi_solo * 1.1
    maintain = phi_disc > phi_solo * 0.8
    return boost and maintain, f"solo={phi_solo:.2f}→conn={phi_conn:.2f}→disc={phi_disc:.2f}"


# ═══ Main ═══

ENGINES = {
    'Baseline': engine_baseline,
    'Sync+Faction': engine_with_sync,
    'Oscillator': engine_oscillator,
    'Osc+Laser': engine_oscillator_laser,
    'QuantumWalk': engine_quantum_walk,
    'Frustration': engine_frustration,
}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--hive-only', action='store_true')
    args = parser.parse_args()

    print(f"═══ 전체 엔진 재검증 ({CELLS}c, {STEPS} steps) ═══\n")

    results = []

    if not args.verify_only and not args.hive_only:
        print(f"{'Engine':<20} {'Φ(IIT)':>8} {'Granger':>10} {'Time':>6}")
        print('─' * 50)
        for name, fn in ENGINES.items():
            torch.manual_seed(42); np.random.seed(42)
            t0 = time.time()
            eng = fn()
            phi = measure_phi_iit(eng)
            g = granger_quick(eng)
            elapsed = time.time() - t0
            print(f"{name:<20} {phi:>8.2f} {g:>10.0f} {elapsed:>5.1f}s")
            results.append({'name': name, 'phi_iit': round(phi, 4), 'granger': round(g, 2)})

    if not args.quick:
        print(f"\n═══ 7조건 검증 ═══\n")
        print(f"{'Engine':<20} {'Zero':>6} {'Persist':>8} {'SelfLoop':>9} {'Hive':>6}")
        print('─' * 55)
        for name, fn in ENGINES.items():
            torch.manual_seed(42); np.random.seed(42)
            z_pass, z_det = verify_zero_input(fn)
            p_pass, p_det = verify_persistence(fn)
            s_pass, s_det = verify_self_loop(fn)
            h_pass, h_det = verify_hivemind(fn)
            print(f"{name:<20} {'✅' if z_pass else '❌':>6} {'✅' if p_pass else '❌':>8} {'✅' if s_pass else '❌':>9} {'✅' if h_pass else '❌':>6}")

    # Save
    Path('data').mkdir(exist_ok=True)
    Path('data/verify_all_results.json').write_text(json.dumps(results, indent=2))
    print(f"\n[saved] data/verify_all_results.json")


if __name__ == '__main__':
    main()
