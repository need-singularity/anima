#!/usr/bin/env python3
"""Singularity Finder — 파라미터 공간에서 Φ가 급변하는 특이점 탐색

Param sweep에서 값이 선형적으로 변하다가 갑자기 뛰어오르는 "특이점"을 찾는다.
이진 탐색(bisection)으로 전이점(phase transition)을 정밀하게 찾음.

invest의 benchmark_turbo.py 속도 + 벤치마크 패턴 적용.

Usage:
  python singularity_finder.py --demo              # 모든 파라미터 특이점 탐색
  python singularity_finder.py --param SL2_blend    # 특정 파라미터
  python singularity_finder.py --cells              # 세포 수 특이점
  python singularity_finder.py --resolution 20      # 초기 해상도
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
from typing import List, Tuple, Dict

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator
from bench_phi_hypotheses import make_diverse_inputs, BenchResult


def quick_phi(n_cells: int, dim: int = 64, hidden: int = 128, steps: int = 30) -> float:
    """초고속 Φ 측정 (30 step)."""
    torch.manual_seed(42)
    engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=max(n_cells, 2))
    while len(engine.cells) < n_cells:
        engine._create_cell(parent=engine.cells[len(engine.cells) % len(engine.cells)])
    phi_calc = PhiCalculator(n_bins=16)
    for i in range(steps):
        x = torch.randn(1, dim) * (1.0 + math.sin(i * 0.3))
        engine.process(x)
    phi, _ = phi_calc.compute_phi(engine)
    return phi


def quick_phi_with_param(param_name: str, param_value: float,
                         n_cells: int = 16, dim: int = 64, hidden: int = 128,
                         steps: int = 30) -> float:
    """특정 파라미터 값에서 Φ 측정."""
    torch.manual_seed(42)
    engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=max(n_cells, 2))
    while len(engine.cells) < n_cells:
        engine._create_cell(parent=engine.cells[len(engine.cells) % len(engine.cells)])
    phi_calc = PhiCalculator(n_bins=16)
    inputs = make_diverse_inputs(steps, dim)

    for step_i, x in enumerate(inputs):
        engine.process(x)
        with torch.no_grad():
            if param_name == 'noise_scale':
                for cell in engine.cells:
                    cell.hidden += torch.randn_like(cell.hidden) * param_value
            elif param_name == 'blend_ratio':
                if len(engine.cells) >= 2:
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for cell in engine.cells:
                        cell.hidden = (1 - param_value) * cell.hidden + param_value * mean_h
            elif param_name == 'repulsion_strength':
                for i in range(len(engine.cells)):
                    for j in range(i+1, min(i+3, len(engine.cells))):
                        diff = engine.cells[i].hidden - engine.cells[j].hidden
                        push = param_value * diff / (diff.norm() + 1e-8)
                        engine.cells[i].hidden += push
                        engine.cells[j].hidden -= push
            elif param_name == 'entropy_target':
                hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
                entropy = hiddens.var(dim=0).mean().item()
                if entropy > param_value * 1.5:
                    for cell in engine.cells:
                        cell.hidden *= 0.98
                elif entropy < param_value * 0.5:
                    for cell in engine.cells:
                        cell.hidden += torch.randn_like(cell.hidden) * 0.02

    phi, _ = phi_calc.compute_phi(engine)
    return phi


def find_singularities_1d(param_name: str, values: List[float],
                          measure_fn, resolution: int = 20) -> List[Dict]:
    """1D 파라미터 공간에서 특이점 탐색.

    1단계: coarse sweep (resolution 개 점)
    2단계: 급변 구간 감지 (Φ 변화율 상위)
    3단계: 이진 탐색으로 정밀 위치 결정
    """
    # 1단계: Coarse sweep
    coarse_results = []
    for v in values:
        phi = measure_fn(v)
        coarse_results.append((v, phi))

    # 2단계: 급변 구간 감지
    gradients = []
    for i in range(1, len(coarse_results)):
        v_prev, phi_prev = coarse_results[i-1]
        v_curr, phi_curr = coarse_results[i]
        dv = v_curr - v_prev
        if dv > 0:
            gradient = abs(phi_curr - phi_prev) / dv
            gradients.append((i, gradient, v_prev, v_curr, phi_prev, phi_curr))

    if not gradients:
        return []

    # 상위 gradient 구간
    gradients.sort(key=lambda x: -x[1])
    singularities = []

    for idx, grad, v_lo, v_hi, phi_lo, phi_hi in gradients[:3]:
        # 3단계: 이진 탐색으로 정밀 위치
        for _ in range(10):  # 10회 bisection = 1024배 정밀도
            v_mid = (v_lo + v_hi) / 2
            phi_mid = measure_fn(v_mid)
            if abs(phi_mid - phi_lo) > abs(phi_mid - phi_hi):
                v_hi = v_mid
                phi_hi = phi_mid
            else:
                v_lo = v_mid
                phi_lo = phi_mid

        singularities.append({
            'param': param_name,
            'location': (v_lo + v_hi) / 2,
            'phi_before': phi_lo,
            'phi_after': phi_hi,
            'gradient': grad,
            'jump': abs(phi_hi - phi_lo),
        })

    return singularities


def find_cell_singularity(max_cells: int = 512, resolution: int = 20) -> List[Dict]:
    """세포 수 특이점 탐색 — 어디서 Φ가 급변하는가?"""
    # Log scale: 2, 4, 8, 16, 32, 64, 128, 256, 512
    cell_counts = sorted(set([int(2 ** (i * math.log2(max_cells) / resolution))
                              for i in range(resolution + 1)] + [2, 4, 8, 16, 32, 64, 128, 256, 512]))
    cell_counts = [c for c in cell_counts if 2 <= c <= max_cells]

    print(f"  Scanning {len(cell_counts)} cell counts: {cell_counts[:10]}...")
    values = [(c, quick_phi(c, steps=20)) for c in cell_counts]

    singularities = []
    for i in range(1, len(values)):
        c_prev, phi_prev = values[i-1]
        c_curr, phi_curr = values[i]
        ratio = phi_curr / max(phi_prev, 1e-8)
        if ratio > 1.5:  # 50%+ jump
            singularities.append({
                'param': 'cell_count',
                'location': f'{c_prev}→{c_curr}',
                'phi_before': phi_prev,
                'phi_after': phi_curr,
                'ratio': ratio,
                'jump': phi_curr - phi_prev,
            })

    return singularities, values


def main():
    parser = argparse.ArgumentParser(description="Singularity Finder — Φ phase transition detector")
    parser.add_argument("--demo", action="store_true", help="Full demo")
    parser.add_argument("--param", type=str, help="Specific parameter to scan")
    parser.add_argument("--cells", action="store_true", help="Cell count singularity scan")
    parser.add_argument("--resolution", type=int, default=20, help="Scan resolution")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════╗")
    print("║  Singularity Finder — Φ Phase Transition Detector ║")
    print("╚══════════════════════════════════════════════════╝\n")

    if args.cells or args.demo:
        print("[Cell Count Singularity Scan]")
        t0 = time.time()
        sings, values = find_cell_singularity(512, args.resolution)
        elapsed = time.time() - t0
        print(f"\n  {'Cells':>6} {'Φ':>10} {'Ratio':>8}")
        print(f"  {'-'*30}")
        for c, phi in values:
            print(f"  {c:>6} {phi:>10.2f}")
        print(f"\n  Phase Transitions (>50% jump):")
        for s in sings:
            print(f"  ★ {s['location']:>10}: Φ {s['phi_before']:.2f} → {s['phi_after']:.2f} "
                  f"(×{s['ratio']:.1f}, jump={s['jump']:.1f})")
        print(f"\n  Scan time: {elapsed:.1f}s")

    if args.demo:
        print("\n[Parameter Singularity Scan]")
        param_configs = {
            'noise_scale': np.linspace(0.001, 0.3, args.resolution).tolist(),
            'blend_ratio': np.linspace(0.01, 0.5, args.resolution).tolist(),
            'repulsion_strength': np.linspace(0.001, 0.1, args.resolution).tolist(),
            'entropy_target': np.linspace(0.01, 3.0, args.resolution).tolist(),
        }

        for param_name, values in param_configs.items():
            print(f"\n  Scanning {param_name}...")
            t0 = time.time()
            sings = find_singularities_1d(
                param_name, values,
                lambda v, pn=param_name: quick_phi_with_param(pn, v),
                args.resolution,
            )
            elapsed = time.time() - t0

            if sings:
                for s in sings[:2]:
                    print(f"  ★ {param_name} = {s['location']:.4f}: "
                          f"Φ jump = {s['jump']:.2f}, gradient = {s['gradient']:.1f}")
            else:
                print(f"    No singularity found")
            print(f"    ({elapsed:.1f}s)")

    if args.param:
        print(f"\n[Scanning {args.param}]")
        values = np.linspace(0.001, 0.5, args.resolution * 2).tolist()
        sings = find_singularities_1d(
            args.param, values,
            lambda v: quick_phi_with_param(args.param, v),
            args.resolution * 2,
        )
        for s in sings:
            print(f"  ★ {s['location']:.6f}: jump={s['jump']:.2f}, gradient={s['gradient']:.1f}")


if __name__ == '__main__':
    main()
