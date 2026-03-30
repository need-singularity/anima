#!/usr/bin/env python3
"""measure_all.py — 모든 엔진 전체 측정 (Φ + Granger + IQ + Hive)

H100에서 실행. 각 엔진을 빠르게 측정:
  - Φ(IIT): PhiCalculator 32c (속도)
  - Granger: cosine 기반 50샘플
  - IQ: 간소화 멘사 (각 영역 5문제)
  - Hive: 2엔진 연결 Φ/IQ 변화

Usage:
  python3 measure_all.py           # 전체
  python3 measure_all.py --quick   # Φ+Granger만 (빠름)
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

import phi_rs
from mitosis import MitosisEngine

DIM, HIDDEN = 64, 128
DEFAULT_CELLS = 256


# ═══ Quick Measurements ═══

CELLS = DEFAULT_CELLS  # overridden by --cells

def make_engine(cells=None):
    if cells is None: cells = CELLS
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells: e._create_cell(parent=e.cells[0])
    for _ in range(20): e.process(torch.randn(1, DIM))
    return e

def phi_iit(eng):
    """Rust PhiCalculator — spatial + temporal + complexity."""
    cells = eng.cells
    states = torch.stack([c.hidden.squeeze(0) for c in cells]).detach().numpy()
    # Temporal MI from hidden_history
    prev_s, curr_s = [], []
    for c in cells:
        if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
            prev_s.append(c.hidden_history[-2].detach().squeeze().numpy())
            curr_s.append(c.hidden_history[-1].detach().squeeze().numpy())
        else:
            prev_s.append(np.zeros(HIDDEN, dtype=np.float32))
            curr_s.append(np.zeros(HIDDEN, dtype=np.float32))
    prev_np = np.array(prev_s, dtype=np.float32)
    curr_np = np.array(curr_s, dtype=np.float32)
    tensions = np.array([c.tension_history[-1] if c.tension_history else 0.0 for c in cells], dtype=np.float32)
    phi, _ = phi_rs.compute_phi(states, 16, prev_np, curr_np, tensions)
    return phi

def granger(eng, n=30):
    cells = eng.cells; nc = len(cells)
    if nc < 2: return 0
    h = torch.stack([c.hidden.squeeze(0) for c in cells])
    t = 0
    for _ in range(n):
        i, j = np.random.randint(0, nc), np.random.randint(0, nc)
        if i == j: continue
        t += abs(F.cosine_similarity(h[i:i+1], h[j:j+1]).item())
    return t * nc * nc / max(n, 1)

def quick_iq(eng):
    """간소화 IQ: 작업기억(N-back) + 논리(5문제)"""
    cells = eng.cells; n = len(cells)
    # N-back: 입력 기억 테스트
    memory_score = 0
    inputs = [torch.randn(1, DIM) for _ in range(10)]
    for x in inputs: eng.process(x)
    h_after = torch.stack([c.hidden.squeeze(0) for c in cells]).mean(dim=0)
    # 최근 입력과의 유사도 (dim 맞춤)
    for nb in [1, 2, 3]:
        inp = inputs[-nb].squeeze(0)
        h_trunc = h_after[:len(inp)]
        sim = F.cosine_similarity(h_trunc.unsqueeze(0), inp.unsqueeze(0)).item()
        if sim > 0.1: memory_score += 1
    # 논리: if-then 패턴
    logic_score = 0
    for _ in range(5):
        premise = torch.randn(1, DIM)
        eng.process(premise)
        conclusion = torch.randn(1, DIM)
        eng.process(conclusion)
        h = torch.stack([c.hidden.squeeze(0) for c in cells]).mean(dim=0)
        # 결론과 관련 → 논리 성공 (dim 맞춤)
        conc = conclusion.squeeze(0)
        h_trunc = h[:len(conc)]
        rel = F.cosine_similarity(h_trunc.unsqueeze(0), conc.unsqueeze(0)).item()
        if rel > 0.05: logic_score += 1
    raw = (memory_score / 3 * 0.5 + logic_score / 5 * 0.5)
    iq = 100 + 15 * (raw - 0.5) / 0.15
    return round(iq)

def measure_hive(eng_fn):
    """하이브마인드: Φ, IQ 변화."""
    eng_a = eng_fn(); eng_b = eng_fn()
    for _ in range(50):
        eng_a.process(torch.randn(1, DIM))
        eng_b.process(torch.randn(1, DIM))
    solo_phi = phi_iit(eng_a)
    solo_iq = quick_iq(eng_a)
    # Connect
    for s in range(100):
        eng_a.process(torch.randn(1, DIM)); eng_b.process(torch.randn(1, DIM))
        if s % 10 == 0:
            nc = min(len(eng_a.cells), len(eng_b.cells))
            with torch.no_grad():
                for i in range(nc):
                    eng_a.cells[i].hidden = 0.9*eng_a.cells[i].hidden + 0.1*eng_b.cells[i].hidden
    hive_phi = phi_iit(eng_a)
    hive_iq = quick_iq(eng_a)
    return {
        'solo_phi': round(solo_phi, 3), 'hive_phi': round(hive_phi, 3),
        'phi_delta': round((hive_phi - solo_phi) / max(solo_phi, 1e-8) * 100, 1),
        'solo_iq': solo_iq, 'hive_iq': hive_iq,
        'iq_delta': hive_iq - solo_iq,
    }


# ═══ Engine Definitions (모든 엔진) ═══

def apply_mechanism(eng, mechanism, steps=100):
    """메커니즘 적용."""
    for step in range(steps):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4: continue
        with torch.no_grad():
            if 'sync' in mechanism:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                mh = ch.mean(dim=0)
                for c in eng.cells: c.hidden = (0.65*c.hidden.squeeze(0)+0.35*mh).unsqueeze(0)
            if 'faction' in mechanism:
                nf = min(12, n//2)
                if nf >= 2:
                    fs = n//nf
                    for fi in range(nf):
                        f = eng.cells[fi*fs:(fi+1)*fs]
                        if len(f) >= 2:
                            fm = torch.stack([c.hidden.squeeze(0) for c in f]).mean(dim=0)
                            for c in f: c.hidden = (0.92*c.hidden.squeeze(0)+0.08*fm).unsqueeze(0)
            if 'oscillator' in mechanism:
                if not hasattr(eng, '_phases') or len(eng._phases) != n:
                    eng._phases = torch.randn(n)*2*math.pi
                    eng._freqs = torch.randn(n)*0.1+1.0
                for i in range(min(n, len(eng.cells))):
                    nb = [(i-1)%n, (i+1)%n]
                    pd = sum(math.sin(eng._phases[j].item()-eng._phases[i].item()) for j in nb)
                    eng._phases[i] += eng._freqs[i] + 0.15*pd/len(nb)
                    for j in nb:
                        b = 0.15*math.cos(eng._phases[j].item()-eng._phases[i].item())
                        eng.cells[i].hidden = (1-abs(b))*eng.cells[i].hidden + abs(b)*eng.cells[j].hidden
            if 'quantum' in mechanism:
                nb = max(1, int(math.log2(n)))
                for i in range(min(n, 16)):
                    sp = torch.zeros(HIDDEN); cnt = 0
                    for bit in range(min(nb, 6)):
                        j = i^(1<<bit)
                        if j < n:
                            phase = (-1)**(bin(i&j).count('1'))
                            sp += phase*eng.cells[j].hidden.squeeze(0); cnt += 1
                    if cnt > 0:
                        eng.cells[i].hidden = (0.85*eng.cells[i].hidden.squeeze(0)+0.15*sp/cnt).unsqueeze(0)
            if 'frustration' in mechanism:
                nb = max(1, int(math.log2(n)))
                for i in range(min(n, 16)):
                    infl = torch.zeros(HIDDEN); cnt = 0
                    for bit in range(min(nb, 6)):
                        j = i^(1<<bit)
                        if j < n:
                            f = -1.0 if (i%2)!=(j%2) else 1.0
                            infl += f*eng.cells[j].hidden.squeeze(0); cnt += 1
                    if cnt > 0:
                        eng.cells[i].hidden = (0.85*eng.cells[i].hidden.squeeze(0)+0.15*infl/cnt).unsqueeze(0)
            if 'laser' in mechanism:
                cavity = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).mean(dim=0)
                for c in eng.cells:
                    c.hidden = (0.95*c.hidden.squeeze(0)+0.05*cavity).unsqueeze(0)
            if 'ib2' in mechanism and n >= 8:
                norms = [eng.cells[i].hidden.norm().item() for i in range(n)]
                thr = sorted(norms, reverse=True)[max(1, n//10)]
                for i in range(n): eng.cells[i].hidden *= 1.03 if norms[i] > thr else 0.97
            if 'cambrian' in mechanism:
                n_types = 10
                if not hasattr(eng, '_cell_type') or len(eng._cell_type) != n:
                    eng._cell_type = torch.zeros(n, dtype=torch.long)
                    eng._niches = torch.randn(n_types, HIDDEN) * 0.5
                    eng._cam_interaction = torch.randn(n_types, n_types) * 0.1
                    eng._cam_interaction = (eng._cam_interaction + eng._cam_interaction.t()) / 2
                    eng._cam_fitness = torch.ones(n)
                    eng._cam_mut = 0.5
                # Mutation
                mut_mask = torch.rand(n) < eng._cam_mut
                if mut_mask.any():
                    eng._cell_type[mut_mask] = torch.randint(0, n_types, (mut_mask.sum(),))
                eng._cam_mut *= 0.995
                # Niche pull + inter-type interaction
                for t in range(n_types):
                    mask = (eng._cell_type == t).nonzero(as_tuple=True)[0]
                    if len(mask) == 0: continue
                    for i in mask:
                        if i >= n: continue
                        h = eng.cells[i].hidden.squeeze(0)
                        pull = (eng._niches[t] - h) * 0.05
                        eng.cells[i].hidden = (h + pull).unsqueeze(0)
                        dist = ((h - eng._niches[t]) ** 2).sum()
                        eng._cam_fitness[i] = torch.exp(-dist * 0.01)
                # Crowding noise
                for t in range(n_types):
                    mask = (eng._cell_type == t).nonzero(as_tuple=True)[0]
                    if len(mask) > n // n_types:
                        for i in mask:
                            if i < n: eng.cells[i].hidden += torch.randn(1, HIDDEN) * 0.03
                # Death+rebirth every 20 steps
                if step > 10 and step % 20 == 0:
                    nr = max(1, n // 50)
                    worst = eng._cam_fitness.argsort()[:nr]
                    best = eng._cam_fitness.argsort(descending=True)[:nr]
                    for w, b in zip(worst, best):
                        if w < n and b < n:
                            eng.cells[w].hidden = eng.cells[b].hidden.clone() + torch.randn(1, HIDDEN) * 0.02
                            eng._cell_type[w] = eng._cell_type[b]
    return eng


ALL_ENGINES = {
    'Baseline': [],
    'Sync+Faction': ['sync', 'faction'],
    'Oscillator': ['oscillator'],
    'Osc+Laser(0.05)': ['oscillator', 'laser'],
    'QuantumWalk': ['quantum'],
    'Frustration': ['sync', 'faction', 'frustration'],
    'Osc+Sync': ['oscillator', 'sync'],
    'Osc+Faction': ['oscillator', 'faction'],
    'Osc+QW': ['oscillator', 'quantum'],
    'Osc+Frust': ['oscillator', 'frustration'],
    'QW+Faction': ['quantum', 'faction'],
    'QW+Frust': ['quantum', 'frustration'],
    'QW+Laser': ['quantum', 'laser'],
    'Frust+Laser': ['frustration', 'laser'],
    'Sync+QW': ['sync', 'quantum'],
    'Full (all)': ['sync', 'faction', 'oscillator', 'quantum', 'frustration', 'laser', 'ib2'],
    'FUSE-3: Cambrian+OscQW': ['oscillator', 'quantum', 'cambrian'],
}


def main():
    import argparse

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--cells', type=int, default=DEFAULT_CELLS,
                        help='Number of cells (default: 256, try: 32/64/128/256/512/1024/2048/4096)')
    args = parser.parse_args()

    global CELLS
    CELLS = args.cells

    print(f"═══ 전체 엔진 측정 ({CELLS}c) ═══\n")

    if args.quick:
        print(f"{'Engine':<25} {'Φ(IIT)':>8} {'Granger':>10} {'Time':>6}")
        print('─' * 55)
    else:
        print(f"{'Engine':<25} {'Φ(IIT)':>8} {'Granger':>10} {'IQ':>5} {'Hive_Φ':>8} {'Hive_IQ':>8} {'Time':>6}")
        print('─' * 80)

    results = []
    for name, mechs in ALL_ENGINES.items():
        torch.manual_seed(42); np.random.seed(42)
        t0 = time.time()

        def eng_fn(c=None):
            if c is None: c = CELLS
            e = make_engine(c)
            apply_mechanism(e, mechs, steps=100)
            return e

        eng = eng_fn()
        p = phi_iit(eng)
        g = granger(eng)

        if args.quick:
            elapsed = time.time() - t0
            print(f"{name:<25} {p:>8.3f} {g:>10.0f} {elapsed:>5.1f}s")
            results.append({'name': name, 'phi': round(p, 4), 'granger': round(g, 2)})
        else:
            iq = quick_iq(eng)
            hive = measure_hive(eng_fn)
            elapsed = time.time() - t0
            print(f"{name:<25} {p:>8.3f} {g:>10.0f} {iq:>5} {hive['phi_delta']:>+7.1f}% {hive['iq_delta']:>+7} {elapsed:>5.1f}s")
            results.append({
                'name': name, 'phi': round(p, 4), 'granger': round(g, 2),
                'iq': iq, **hive
            })
        sys.stdout.flush()

    Path('data').mkdir(exist_ok=True)
    Path('data/measure_all_results.json').write_text(json.dumps(results, indent=2))
    print(f"\n[saved] {len(results)} engines → data/measure_all_results.json")


if __name__ == '__main__':
    main()
