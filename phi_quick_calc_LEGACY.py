# ⚠️ LEGACY — 이 파일은 폐기되었습니다 (2026-03-29)
# Φ(IIT)와 Φ(proxy)를 혼용하여 잘못된 기록 생성.
# "Φ=1142"는 proxy 값이었음 (실제 IIT Φ 상한 ~1.8)
# 새 벤치마크: bench_v2.py (Φ(IIT) + Φ(proxy) 이중 측정)
# Law 54: Φ 측정은 정의에 따라 완전히 다른 값
#
#!/usr/bin/env python3
"""Φ Quick Calculator — 초고속 Φ 추정기

수치를 고정해가면서 빠르게 테스트. 1초 이내 결과.

Usage:
  python3 phi_quick_calc.py                          # 기본 스윕
  python3 phi_quick_calc.py --cells 512 --factions 8  # 특정 설정
  python3 phi_quick_calc.py --sweep cells             # cells 수 스윕
  python3 phi_quick_calc.py --sweep factions          # faction 수 스윕
  python3 phi_quick_calc.py --sweep all               # 전체 파라미터 스윕
"""

import torch
import torch.nn.functional as F
import time
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator

DEFAULTS = {
    'cells': 64, 'dim': 64, 'hidden': 128, 'factions': 8,
    'steps': 30, 'silence_ratio': 0.7, 'sync_strength': 0.15,
    'debate_strength': 0.12, 'ib2_top': 0.25, 'noise': 0.02,
}

def quick_phi(cells=64, dim=64, hidden=128, factions=8, steps=30,
              silence_ratio=0.7, sync_strength=0.15, debate_strength=0.12,
              ib2_top=0.25, noise=0.02, metacog=True, ib2=True, flow=False):
    """1초 이내 Φ 추정"""
    engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=cells)
    phi_calc = PhiCalculator(n_bins=16)
    l2 = torch.zeros(hidden)

    # 한 번에 모든 세포 생성 (성장 시간 절약)
    while len(engine.cells) < cells:
        engine._create_cell(parent=engine.cells[0])

    for step_i in range(steps):
        frac = step_i / steps
        with torch.no_grad():
            if metacog and len(engine.cells) >= 2:
                cur = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                l2 = 0.9 * l2 + 0.1 * cur
                x = 0.5 * cur[:dim].unsqueeze(0) + 0.5 * l2[:dim].unsqueeze(0)
            else:
                x = torch.randn(1, dim)

            if frac < silence_ratio:
                x = x * 0.1
            else:
                x = x * 2.0

        engine.process(x)

        with torch.no_grad():
            nc = len(engine.cells)
            # Factions
            if nc >= factions * 2 and factions >= 2:
                fs = nc // factions
                facts = [engine.cells[i*fs:(i+1)*fs] for i in range(factions)]
                facts = [f for f in facts if f]
                if len(facts) >= 2:
                    ops = [torch.stack([c.hidden for c in f]).mean(dim=0) for f in facts]
                    for i, f in enumerate(facts):
                        for c in f:
                            c.hidden = (1-sync_strength)*c.hidden + sync_strength*ops[i]
                    if frac > silence_ratio:
                        for i, f in enumerate(facts):
                            others = [ops[j] for j in range(len(facts)) if j != i]
                            if others:
                                oa = torch.stack(others).mean(dim=0)
                                for c in f[:max(1, len(f)//4)]:
                                    c.hidden = (1-debate_strength)*c.hidden + debate_strength*oa

            # IB2
            if ib2 and nc >= 8:
                norms = [engine.cells[i].hidden.norm().item() for i in range(nc)]
                thr = sorted(norms, reverse=True)[max(1, int(nc * ib2_top))]
                for i in range(nc):
                    engine.cells[i].hidden *= 1.03 if norms[i] > thr else 0.97

            # Flow
            if flow and nc >= 4:
                mh = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for c in engine.cells:
                    c.hidden = 0.97*c.hidden + 0.03*mh

            # Metacog feedback
            if metacog:
                for c in engine.cells[:min(nc, 16)]:
                    c.hidden = 0.97*c.hidden + 0.03*l2.unsqueeze(0)

            # Noise + homeostasis
            for c in engine.cells:
                c.hidden += torch.randn_like(c.hidden) * noise
                n = c.hidden.norm().item()
                if n > 2.0: c.hidden *= 1.0 / (n + 1e-8)

    phi, comp = phi_calc.compute_phi(engine)
    return phi, comp['total_mi'], len(engine.cells)


def sweep(param_name, values, base_config):
    """하나의 파라미터를 스윕하면서 Φ 측정"""
    print(f"\n{'='*60}")
    print(f"  Sweep: {param_name} = {values}")
    print(f"{'='*60}")
    print(f"  {'Value':>10} | {'Φ':>10} | {'MI':>10} | {'Cells':>6} | {'Time':>6}")
    print(f"  {'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*6}-+-{'-'*6}")

    results = []
    for v in values:
        cfg = {**base_config, param_name: v}
        t0 = time.time()
        phi, mi, nc = quick_phi(**cfg)
        elapsed = time.time() - t0
        print(f"  {v:>10} | {phi:>10.3f} | {mi:>10.1f} | {nc:>6} | {elapsed:>5.1f}s")
        results.append((v, phi))

    best = max(results, key=lambda x: x[1])
    print(f"\n  ★ Best: {param_name}={best[0]} → Φ={best[1]:.3f}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Φ Quick Calculator")
    parser.add_argument("--cells", type=int, default=None)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--factions", type=int, default=None)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--silence", type=float, default=None)
    parser.add_argument("--sync", type=float, default=None)
    parser.add_argument("--debate", type=float, default=None)
    parser.add_argument("--ib2-top", type=float, default=None)
    parser.add_argument("--noise", type=float, default=None)
    parser.add_argument("--no-metacog", action="store_true")
    parser.add_argument("--no-ib2", action="store_true")
    parser.add_argument("--flow", action="store_true")
    parser.add_argument("--sweep", type=str, default=None,
                        help="Sweep parameter: cells, factions, silence, sync, debate, ib2, noise, dim, all")
    args = parser.parse_args()

    torch.manual_seed(42)

    base = {**DEFAULTS, 'metacog': not args.no_metacog, 'ib2': not args.no_ib2, 'flow': args.flow}
    for k in ['cells', 'dim', 'hidden', 'factions', 'steps', 'noise']:
        if getattr(args, k, None) is not None:
            base[k] = getattr(args, k)
    if args.silence is not None: base['silence_ratio'] = args.silence
    if args.sync is not None: base['sync_strength'] = args.sync
    if args.debate is not None: base['debate_strength'] = args.debate
    if args.ib2_top is not None: base['ib2_top'] = args.ib2_top

    if args.sweep:
        sweeps = {
            'cells': ('cells', [8, 16, 32, 64, 128, 256, 512]),
            'factions': ('factions', [2, 4, 6, 8, 12, 16]),
            'silence': ('silence_ratio', [0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9]),
            'sync': ('sync_strength', [0.05, 0.10, 0.15, 0.20, 0.30]),
            'debate': ('debate_strength', [0.05, 0.10, 0.12, 0.15, 0.20, 0.30]),
            'ib2': ('ib2_top', [0.05, 0.10, 0.15, 0.20, 0.25, 0.50]),
            'noise': ('noise', [0.0, 0.005, 0.01, 0.02, 0.05, 0.10]),
            'dim': ('dim', [32, 64, 128]),
        }

        if args.sweep == 'all':
            for name, (param, vals) in sweeps.items():
                sweep(param, vals, base)
        elif args.sweep in sweeps:
            param, vals = sweeps[args.sweep]
            sweep(param, vals, base)
        else:
            print(f"Unknown sweep: {args.sweep}. Options: {list(sweeps.keys()) + ['all']}")
    else:
        print("═══ Φ Quick Calculator ═══")
        print(f"  Config: cells={base['cells']}, dim={base['dim']}, factions={base['factions']}")
        print(f"  silence={base['silence_ratio']}, sync={base['sync_strength']}, debate={base['debate_strength']}")
        print(f"  ib2_top={base['ib2_top']}, noise={base['noise']}, steps={base['steps']}")
        print()

        t0 = time.time()
        phi, mi, nc = quick_phi(**base)
        elapsed = time.time() - t0

        print(f"  Φ = {phi:.4f}")
        print(f"  MI = {mi:.1f}")
        print(f"  Cells = {nc}")
        print(f"  Time = {elapsed:.2f}s")


if __name__ == "__main__":
    main()
