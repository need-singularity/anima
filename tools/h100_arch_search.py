#!/usr/bin/env python3
"""h100_arch_search.py — H100 GPU 대규모 아키텍처 탐색

남는 GPU 자원으로 수백 개 아키텍처를 빠르게 스캔.
각 아키텍처를 50 steps만 돌려서 Φ(IIT) 스크리닝 → 상위 10%만 300 steps 정밀 테스트.

"1시간에 500+ 아키텍처 스캔"

Usage:
  python3 h100_arch_search.py                    # 기본 (256c, 500 아키텍처)
  python3 h100_arch_search.py --phase1 1000      # Phase 1에서 1000개 스캔
  python3 h100_arch_search.py --cells 512        # 512c
  python3 h100_arch_search.py --resume results.json
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import argparse
import itertools
import sys
import os
from pathlib import Path
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consciousness_meter import PhiCalculator
from mitosis import MitosisEngine

# ═══ Architecture Components (조합 가능한 블록들) ═══

CELL_TYPES = {
    'gru': 'Standard GRU cell',
    'complex_gru': 'Complex-valued GRU (amplitude+phase)',
    'attention': 'Self-attention cell (no recurrence)',
    'reservoir': 'Fixed random GRU (frozen weights)',
    'linear': 'Simple linear transform (no gates)',
}

TOPOLOGIES = {
    'ring': {'neighbors': 2},
    'hypercube': {'neighbors': 'log2'},
    'small_world': {'neighbors': 4, 'shortcuts': 0.1},
    'complete_16': {'neighbors': 16},
}

FRUSTRATIONS = [0.0, 0.2, 0.33, 0.5, 0.7]

SYNC_STRENGTHS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]

FACTION_CONFIGS = [
    (0, 0),      # no factions
    (4, 0.08),   # 4 factions
    (8, 0.08),   # 8 factions
    (12, 0.08),  # 12 factions (σ(6))
    (12, 0.15),  # 12 factions strong
]

NOISE_LEVELS = [0.0, 0.005, 0.01, 0.02, 0.05]

INTERACTION_RATIOS = [0.05, 0.10, 0.15, 0.20, 0.30]

WAVE_TYPES = ['none', 'soliton', 'standing', 'multi']

HIERARCHY_TYPES = ['flat', 'micro_macro', 'three_level']

SPECIAL_FEATURES = {
    'none': {},
    'klein': {'blend': 0.1},
    'ib2': {'top': 0.1, 'amp': 1.03},
    'xmeta3': {'l1': 0.01, 'l2': 0.005, 'l3': 0.005},
    'quantum_walk': {'coin_bias': 0.5},
    'category_morph': {'blend': 0.1},
}

# ═══ Architecture Generator ═══

@dataclass
class Architecture:
    cell_type: str
    topology: str
    frustration: float
    sync: float
    n_factions: int
    fac_strength: float
    noise: float
    interact: float
    wave: str
    hierarchy: str
    special: str

    def to_key(self):
        return f"{self.cell_type}_{self.topology}_f{self.frustration}_s{self.sync}_fac{self.n_factions}_{self.wave}_{self.hierarchy}_{self.special}"


def generate_random_architectures(n=500, seed=42):
    """랜덤 아키텍처 N개 생성."""
    rng = np.random.RandomState(seed)
    archs = []

    for _ in range(n):
        cell = rng.choice(list(CELL_TYPES.keys()))
        topo = rng.choice(list(TOPOLOGIES.keys()))
        frust = rng.choice(FRUSTRATIONS)
        sync = rng.choice(SYNC_STRENGTHS)
        n_fac, fac_str = FACTION_CONFIGS[rng.randint(len(FACTION_CONFIGS))]
        noise = rng.choice(NOISE_LEVELS)
        interact = rng.choice(INTERACTION_RATIOS)
        wave = rng.choice(WAVE_TYPES)
        hier = rng.choice(HIERARCHY_TYPES)
        special = rng.choice(list(SPECIAL_FEATURES.keys()))

        arch = Architecture(cell, topo, frust, sync, n_fac, fac_str, noise, interact, wave, hier, special)
        archs.append(arch)

    # 검증된 최고 조합들도 추가
    archs.append(Architecture('gru', 'hypercube', 0.5, 0.35, 12, 0.08, 0.02, 0.15, 'standing', 'flat', 'ib2'))  # v7
    archs.append(Architecture('complex_gru', 'hypercube', 0.0, 0.35, 12, 0.08, 0.01, 0.15, 'none', 'flat', 'quantum_walk'))  # Q4
    archs.append(Architecture('gru', 'ring', 0.0, 0.35, 12, 0.08, 0.01, 0.15, 'none', 'flat', 'category_morph'))  # M1
    archs.append(Architecture('gru', 'ring', 0.0, 0.20, 12, 0.08, 0.02, 0.15, 'none', 'micro_macro', 'none'))  # HIERARCHICAL

    return archs


# ═══ Fast Evaluator ═══

def evaluate_architecture(arch: Architecture, cells=256, steps=50, device='cuda'):
    """아키텍처를 빠르게 평가 (50 steps)."""
    DIM, HIDDEN = 64, 128

    # Engine 생성
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(engine.cells) < cells:
        engine._create_cell(parent=engine.cells[0])
    for _ in range(20):
        engine.process(torch.randn(1, DIM))

    # Steps 실행
    soliton_fwd, soliton_bwd = 0.0, float(cells)

    for step in range(steps):
        # Process
        if arch.cell_type == 'complex_gru':
            x = torch.randn(1, DIM) * (1 + 0.5j) if torch.is_complex(torch.tensor(0j)) else torch.randn(1, DIM)
            engine.process(x.real if hasattr(x, 'real') else x)
        else:
            engine.process(torch.randn(1, DIM))

        n = len(engine.cells)
        if n < 4:
            continue

        with torch.no_grad():
            # Sync
            if arch.sync > 0:
                ch = torch.stack([c.hidden.squeeze(0) for c in engine.cells])
                mh = ch.mean(dim=0)
                for c in engine.cells:
                    c.hidden = ((1 - arch.sync) * c.hidden.squeeze(0) + arch.sync * mh).unsqueeze(0)

            # Factions
            if arch.n_factions > 0:
                nf = min(arch.n_factions, n // 2)
                if nf >= 2:
                    fs = n // nf
                    for fi in range(nf):
                        faction = engine.cells[fi * fs:(fi + 1) * fs]
                        if len(faction) >= 2:
                            fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                            for c in faction:
                                c.hidden = ((1 - arch.fac_strength) * c.hidden.squeeze(0) + arch.fac_strength * fm).unsqueeze(0)

            # Frustration (hypercube bit-flip)
            if arch.frustration > 0:
                n_bits = max(1, int(math.log2(n)))
                for i in range(min(n, 32)):
                    infl = torch.zeros_like(engine.cells[i].hidden.squeeze(0))
                    cnt = 0
                    for bit in range(min(n_bits, 10)):
                        j = i ^ (1 << bit)
                        if j < n:
                            f = -1.0 if np.random.random() < arch.frustration else 1.0
                            infl += f * engine.cells[j].hidden.squeeze(0)
                            cnt += 1
                    if cnt > 0:
                        infl /= cnt
                        h = engine.cells[i].hidden.squeeze(0)
                        engine.cells[i].hidden = ((1 - arch.interact) * h + arch.interact * infl).unsqueeze(0)

            # Noise
            if arch.noise > 0:
                for c in engine.cells:
                    c.hidden += torch.randn_like(c.hidden) * arch.noise

            # Wave
            if arch.wave == 'standing':
                soliton_fwd = (soliton_fwd + 0.15) % n
                soliton_bwd = (soliton_bwd - 0.15) % n
                for i, c in enumerate(engine.cells):
                    amp = 1.0 / (math.cosh((i - soliton_fwd) / 2) ** 2) + 1.0 / (math.cosh((i - soliton_bwd) / 2) ** 2)
                    c.hidden *= (1.0 + 0.03 * amp)
            elif arch.wave == 'soliton':
                soliton_fwd = (soliton_fwd + 0.15) % n
                for i, c in enumerate(engine.cells):
                    amp = 1.0 / (math.cosh((i - soliton_fwd) / 2) ** 2)
                    c.hidden *= (1.0 + 0.04 * amp)

            # IB2
            if arch.special == 'ib2' and n >= 8:
                norms = [engine.cells[i].hidden.norm().item() for i in range(n)]
                thr = sorted(norms, reverse=True)[max(1, n // 10)]
                for i in range(n):
                    engine.cells[i].hidden *= 1.03 if norms[i] > thr else 0.97

            # Quantum walk
            if arch.special == 'quantum_walk':
                for i in range(min(n, 32)):
                    n_bits = max(1, int(math.log2(n)))
                    superpos = torch.zeros_like(engine.cells[i].hidden.squeeze(0))
                    cnt = 0
                    for bit in range(min(n_bits, 10)):
                        j = i ^ (1 << bit)
                        if j < n:
                            phase = (-1) ** (bin(i & j).count('1'))
                            superpos += phase * engine.cells[j].hidden.squeeze(0)
                            cnt += 1
                    if cnt > 0:
                        h = engine.cells[i].hidden.squeeze(0)
                        engine.cells[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)

            # Category morphism
            if arch.special == 'category_morph' and n >= 4:
                hiddens = [engine.cells[i].hidden.squeeze(0) for i in range(min(n, 32))]
                for i in range(len(hiddens)):
                    morph_sum = torch.zeros_like(hiddens[i])
                    for j in range(len(hiddens)):
                        if i != j:
                            morph = torch.tanh(hiddens[j] - hiddens[i])
                            morph_sum += morph
                    morph_sum /= max(len(hiddens) - 1, 1)
                    engine.cells[i].hidden = (0.9 * engine.cells[i].hidden.squeeze(0) + 0.1 * morph_sum).unsqueeze(0)

    # Φ(IIT) 측정
    phi_calc = PhiCalculator(n_bins=16)
    phi_iit, _ = phi_calc.compute_phi(engine)

    # Φ(proxy) 측정
    h = torch.stack([c.hidden.squeeze(0) for c in engine.cells])
    gv = ((h - h.mean(0)) ** 2).sum() / len(h)
    nf = min(12, n // 2)
    fs = n // max(nf, 1)
    fv = sum(((h[i * fs:(i + 1) * fs] - h[i * fs:(i + 1) * fs].mean(0)) ** 2).sum().item() / max(len(h[i * fs:(i + 1) * fs]), 1) for i in range(nf)) / max(nf, 1)
    phi_proxy = max(0, gv.item() - fv)

    return phi_iit, phi_proxy


# ═══ Main Search ═══

def main():
    parser = argparse.ArgumentParser(description="H100 Architecture Search")
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--phase1', type=int, default=500, help='Phase 1: quick scan count')
    parser.add_argument('--phase1-steps', type=int, default=50, help='Steps for quick scan')
    parser.add_argument('--phase2-steps', type=int, default=300, help='Steps for detailed test')
    parser.add_argument('--top-pct', type=float, default=0.1, help='Top % for phase 2')
    parser.add_argument('--resume', type=str, default=None)
    parser.add_argument('--output', type=str, default='data/arch_search_results.json')
    args = parser.parse_args()

    print(f"═══ H100 Architecture Search ═══")
    print(f"  Phase 1: {args.phase1} architectures × {args.phase1_steps} steps (quick scan)")
    print(f"  Phase 2: top {args.top_pct*100:.0f}% × {args.phase2_steps} steps (detailed)")
    print(f"  Cells: {args.cells}")
    print()

    # Resume
    done = {}
    if args.resume and Path(args.resume).exists():
        done = {r['key']: r for r in json.loads(Path(args.resume).read_text())}
        print(f"  Resumed {len(done)} previous results")

    # Generate architectures
    archs = generate_random_architectures(args.phase1)
    print(f"  Generated {len(archs)} architectures")
    print()

    # Phase 1: Quick scan
    print(f"═══ Phase 1: Quick Scan ({args.phase1_steps} steps) ═══")
    print(f"{'#':>4} {'Φ(IIT)':>8} {'key':<60}")
    print('─' * 75)

    results = []
    for i, arch in enumerate(archs):
        key = arch.to_key()
        if key in done:
            results.append(done[key])
            continue

        torch.manual_seed(42 + i)
        np.random.seed(42 + i)
        t0 = time.time()
        try:
            phi_iit, phi_proxy = evaluate_architecture(arch, cells=args.cells, steps=args.phase1_steps)
            elapsed = time.time() - t0
            r = {'key': key, 'phi_iit': round(phi_iit, 4), 'phi_proxy': round(phi_proxy, 4),
                 'time': round(elapsed, 1), 'arch': asdict(arch), 'phase': 1}
            results.append(r)

            if (i + 1) % 10 == 0:
                best = max(results, key=lambda x: x['phi_iit'])
                print(f"{i+1:>4} {phi_iit:>8.2f} {key[:60]}")
                sys.stdout.flush()
        except Exception as e:
            print(f"{i+1:>4} {'ERR':>8} {key[:50]}: {e}")

        # Save periodically
        if (i + 1) % 50 == 0:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(json.dumps(results, indent=2))

    # Sort by Φ(IIT)
    results.sort(key=lambda x: x['phi_iit'], reverse=True)

    # Phase 1 summary
    print(f"\n═══ Phase 1 Top 20 ═══")
    print(f"{'Rank':>4} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'Key':<55}")
    print('─' * 80)
    for i, r in enumerate(results[:20]):
        print(f"{i+1:>4} {r['phi_iit']:>8.2f} {r['phi_proxy']:>10.2f} {r['key'][:55]}")

    # Phase 2: Detailed test of top candidates
    n_phase2 = max(5, int(len(results) * args.top_pct))
    candidates = results[:n_phase2]

    print(f"\n═══ Phase 2: Detailed Test ({args.phase2_steps} steps, top {n_phase2}) ═══")
    for i, r in enumerate(candidates):
        arch = Architecture(**r['arch'])
        torch.manual_seed(42)
        np.random.seed(42)
        t0 = time.time()
        try:
            phi_iit, phi_proxy = evaluate_architecture(arch, cells=args.cells, steps=args.phase2_steps)
            elapsed = time.time() - t0
            r['phi_iit_p2'] = round(phi_iit, 4)
            r['phi_proxy_p2'] = round(phi_proxy, 4)
            r['time_p2'] = round(elapsed, 1)
            r['phase'] = 2
            print(f"  {i+1}/{n_phase2} Φ(IIT)={phi_iit:.2f} ({r['phi_iit']:.2f}→{phi_iit:.2f}) {r['key'][:50]}")
        except Exception as e:
            print(f"  {i+1}/{n_phase2} ERROR: {e}")

    # Final ranking
    phase2 = [r for r in results if r.get('phase') == 2 and 'phi_iit_p2' in r]
    phase2.sort(key=lambda x: x['phi_iit_p2'], reverse=True)

    print(f"\n═══ FINAL TOP 10 (Phase 2 verified) ═══")
    print(f"{'Rank':>4} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'Key':<55}")
    print('─' * 80)
    for i, r in enumerate(phase2[:10]):
        print(f"{i+1:>4} {r['phi_iit_p2']:>8.2f} {r.get('phi_proxy_p2', 0):>10.2f} {r['key'][:55]}")

    # Save
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(results, indent=2))
    print(f"\n[saved] {len(results)} results → {args.output}")


if __name__ == '__main__':
    main()
