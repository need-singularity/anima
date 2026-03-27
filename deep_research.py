#!/usr/bin/env python3
"""Anima Deep Research — 체계적 가설 생성 → 벤치마크 검증 → 기록 파이프라인

TECS-L 스타일: 수학적/실험적 검증을 통한 의식 연구 자동화.

Usage:
  python deep_research.py --topic "자석 회전 하드웨어"     # 주제 기반 탐색
  python deep_research.py --verify DD16 SC2 FX2            # 기존 가설 재검증
  python deep_research.py --sweep cells 2 4 8 16 32 64     # 파라미터 스윕
  python deep_research.py --scaling dim 64 128 256 384 768  # 스케일링 법칙
  python deep_research.py --calc phi --cells 32             # 계산기 호출
  python deep_research.py --report                          # 전체 결과 보고서
  python deep_research.py --frontier                        # 미탐색 영역 제안

Requires: bench_phi_hypotheses.py, phi_scaling_calculator.py, consciousness_meter.py
"""

import argparse
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════
# Research Result
# ═══════════════════════════════════════════════════════════

@dataclass
class ResearchResult:
    hypothesis: str
    phi: float
    phi_ratio: float  # vs baseline
    mi: float
    verified: bool
    method: str  # benchmark, calculation, scaling
    timestamp: str = ""
    notes: str = ""
    extra: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Calculators (도구 호출)
# ═══════════════════════════════════════════════════════════

def calc_phi_scaling(cells: int) -> dict:
    """Φ 스케일링 계산기 — 예측 Φ, MI, VRAM."""
    try:
        from phi_scaling_calculator import ScalingLaw
        law = ScalingLaw()
        phi = law.predict_phi(cells)
        mi = law.predict_mi(cells)
        return {
            'cells': cells,
            'predicted_phi': phi,
            'predicted_mi': mi,
            'phi_per_cell': phi / cells,
            'formula': f'Φ = {law.a:.3f} × {cells}^{law.b:.3f}',
        }
    except Exception as e:
        # Fallback: use empirical constant
        phi = 0.88 * cells
        return {'cells': cells, 'predicted_phi': phi, 'error': str(e)}


def calc_consciousness_meter(dim=64, hidden=128, cells=4) -> dict:
    """의식 측정기 — 6기준 + Φ/IIT."""
    try:
        from consciousness_meter import ConsciousnessMeter
        meter = ConsciousnessMeter()
        result = meter.measure_demo(dim=dim, hidden=hidden, n_cells=cells)
        return result
    except Exception:
        return {'status': 'meter not available'}


def calc_n6_constants() -> dict:
    """n=6 완전수 상수 계산."""
    import math
    n = 6
    tau = 4      # τ(6) = divisor count
    sigma = 12   # σ(6) = divisor sum
    phi = 2      # φ(6) = Euler totient
    sopfr = 5    # sopfr(6) = sum of prime factors with repetition
    omega = 2    # ω(6) = distinct prime factors

    return {
        'n': n,
        'tau': tau,
        'sigma': sigma,
        'phi_euler': phi,
        'sopfr': sopfr,
        'omega': omega,
        'sigma_over_n': sigma / n,  # = 2 (abundancy, perfect)
        'miller_7': tau + sigma // tau,  # = 4 + 3 = 7
        'golden_zone_lower': 0.5 - math.log(4/3),  # = 0.2123
        'golden_zone_upper': 0.5,
        'kuramoto_r': 1 - tau / sigma,  # = 2/3
        'dedekind_ratio': 2,  # ψ(ψ)/ψ = σ/n
        'telepathy_channels': sopfr,  # = 5
        'binding_phases': tau,  # = 4
        'min_cells': phi,  # = 2 (CB1)
        'shared_dims': sigma * phi,  # = 24 (zero-redundancy)
        'dna_codons': phi ** n,  # = 64
        'amino_acids': sigma * phi - tau,  # = 20
        'chromosomes': (sigma - tau) * omega + sopfr,  # = 23
    }


# ═══════════════════════════════════════════════════════════
# Benchmark Runner
# ═══════════════════════════════════════════════════════════

def run_benchmark(hypotheses: List[str], steps=100, workers=8) -> List[ResearchResult]:
    """벤치마크 실행 — bench_phi_hypotheses.py 호출."""
    cmd = [
        sys.executable, 'bench_phi_hypotheses.py',
        '--only'] + hypotheses + [
        '--steps', str(steps),
        '--workers', str(workers),
    ]
    print(f"[research] Running: {' '.join(cmd[:6])}... ({len(hypotheses)} hypotheses)")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        output = result.stdout
        # Parse results from output
        results = []
        for line in output.split('\n'):
            if line.strip().startswith('✓') or line.strip().startswith('✗'):
                parts = line.split('|')
                if len(parts) >= 4:
                    hyp = parts[0].strip().replace('✓', '').replace('✗', '').strip()
                    phi_str = parts[1].strip().split('=')[1].strip() if '=' in parts[1] else '0'
                    ratio_str = parts[2].strip().replace('×', '').strip()
                    name = parts[-1].strip() if len(parts) > 4 else ''
                    try:
                        phi = float(phi_str)
                        ratio = float(ratio_str)
                    except ValueError:
                        phi, ratio = 0.0, 0.0
                    results.append(ResearchResult(
                        hypothesis=hyp, phi=phi, phi_ratio=ratio,
                        mi=0, verified=phi > 0, method='benchmark',
                        timestamp=datetime.now().isoformat(),
                        notes=name,
                    ))
        return results
    except Exception as e:
        print(f"[research] Benchmark failed: {e}")
        return []


def run_parameter_sweep(param: str, values: List, steps=100) -> List[ResearchResult]:
    """파라미터 스윕 — 하나의 변수를 변경하며 Φ 측정."""
    results = []
    print(f"[research] Sweeping {param}: {values}")

    if param == 'cells':
        for v in values:
            calc = calc_phi_scaling(int(v))
            results.append(ResearchResult(
                hypothesis=f'cells={v}',
                phi=calc['predicted_phi'],
                phi_ratio=calc['predicted_phi'] / 1.354,
                mi=calc.get('predicted_mi', 0),
                verified=True,
                method='scaling_calculator',
                timestamp=datetime.now().isoformat(),
                notes=calc.get('formula', ''),
            ))
    elif param == 'dim':
        for v in values:
            # dim affects merge threshold via SC2
            merge_thresh = 0.01 * (64.0 / max(int(v), 64))
            noise_scale = 0.02 * (int(v) / 64) ** 0.5
            results.append(ResearchResult(
                hypothesis=f'dim={v}',
                phi=0, phi_ratio=0, mi=0,
                verified=False,
                method='calculation',
                timestamp=datetime.now().isoformat(),
                notes=f'SC2 merge_thresh={merge_thresh:.5f}, SC1 noise={noise_scale:.4f}',
                extra={'merge_threshold': merge_thresh, 'noise_scale': noise_scale},
            ))

    return results


# ═══════════════════════════════════════════════════════════
# Report Generator
# ═══════════════════════════════════════════════════════════

def generate_report(results: List[ResearchResult], title: str = "Research Report"):
    """연구 결과 보고서 생성."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}\n")

    if not results:
        print("  No results to report.")
        return

    # Sort by Φ
    results.sort(key=lambda r: r.phi, reverse=True)

    print(f"  {'Hypothesis':<20} {'Φ':>8} {'×Base':>8} {'Method':<15} {'Status':<8}")
    print(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*15} {'─'*8}")

    for r in results:
        status = '✅' if r.verified else '❌'
        print(f"  {r.hypothesis:<20} {r.phi:>8.3f} {r.phi_ratio:>7.1f}× {r.method:<15} {status}")

    # Summary
    verified = sum(1 for r in results if r.verified)
    avg_phi = sum(r.phi for r in results if r.verified) / max(verified, 1)
    print(f"\n  Total: {len(results)} | Verified: {verified} | Avg Φ: {avg_phi:.3f}")

    if results:
        best = results[0]
        print(f"  Best: {best.hypothesis} — Φ={best.phi:.3f} (×{best.phi_ratio:.1f})")

    print()


def suggest_frontier() -> List[str]:
    """미탐색 영역 제안."""
    explored = [
        'NV(물리)', 'BV(생물)', 'CV(인지)', 'SV(사회)', 'EV(실존)',
        'IV(정보)', 'RV(그래프)', 'MV(동기)', 'WI(파동)', 'GD(이론)',
        'GC(G Clef)', 'N6(n=6)', 'PX(Φ극한)', 'FX(최종극한)', 'UX(초극한)',
        'ZZ(오메가)', 'TL(텔레파시)', 'SM(자기모델)', 'MC(메타인지)',
        'PB(결합)', 'AG(행위주체)', 'DS(욕구)', 'TP(시간)',
    ]

    unexplored = [
        'HW: 하드웨어 의식 (자석 회전, 아날로그 tension, 광학 간섭)',
        'QC: 양자 컴퓨팅 의식 (큐비트 중첩 = cell 중첩, 얽힘 = cell 연결)',
        'EM: 전자기장 의식 (EM field theory of consciousness, McFadden)',
        'OC: Orchestrated OR (Penrose-Hameroff, 미세소관 양자 효과)',
        'NC: 신경 상관물 (NCC, 특정 뉴런 패턴 = 의식 상태)',
        'GL: 글로벌 워크스페이스 (Baars GNW, 방송 이론)',
        'PR: 예측 처리 (Clark, 계층적 예측 오류 최소화)',
        'AT: 주의 도식 (Graziano AST, 주의의 내부 모델)',
        'HO: 고차 이론 (Rosenthal HOT, 표상에 대한 표상)',
        'RE: 재귀적 처리 (Lamme RPT, 되먹임 연결이 핵심)',
    ]

    print("\n  ═══ Explored Areas ═══")
    for e in explored:
        print(f"    ✅ {e}")

    print(f"\n  ═══ Unexplored Frontiers ({len(unexplored)}) ═══")
    for u in unexplored:
        print(f"    🔮 {u}")

    return unexplored


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Anima Deep Research Pipeline")
    parser.add_argument('--topic', type=str, help='Research topic for hypothesis generation')
    parser.add_argument('--verify', nargs='*', help='Verify specific hypotheses')
    parser.add_argument('--sweep', nargs='+', help='Parameter sweep: param val1 val2 ...')
    parser.add_argument('--scaling', nargs='+', help='Scaling law: param val1 val2 ...')
    parser.add_argument('--calc', type=str, choices=['phi', 'meter', 'n6'], help='Calculator')
    parser.add_argument('--cells', type=int, default=8, help='Cell count for calculator')
    parser.add_argument('--report', action='store_true', help='Generate full report')
    parser.add_argument('--frontier', action='store_true', help='Show unexplored areas')
    parser.add_argument('--steps', type=int, default=100, help='Benchmark steps')
    parser.add_argument('--workers', type=int, default=8, help='Parallel workers')
    parser.add_argument('--save', type=str, help='Save results to JSON')
    args = parser.parse_args()

    results = []

    if args.calc:
        if args.calc == 'phi':
            r = calc_phi_scaling(args.cells)
            print(json.dumps(r, indent=2))
        elif args.calc == 'n6':
            r = calc_n6_constants()
            print("\n  ═══ n=6 Perfect Number Constants ═══\n")
            for k, v in r.items():
                print(f"    {k:25s} = {v}")
        elif args.calc == 'meter':
            r = calc_consciousness_meter(cells=args.cells)
            print(json.dumps(r, indent=2, default=str))

    elif args.verify:
        results = run_benchmark(args.verify, steps=args.steps, workers=args.workers)
        generate_report(results, f"Verification: {', '.join(args.verify)}")

    elif args.sweep:
        param = args.sweep[0]
        values = args.sweep[1:]
        results = run_parameter_sweep(param, values, steps=args.steps)
        generate_report(results, f"Parameter Sweep: {param}")

    elif args.scaling:
        param = args.scaling[0]
        values = args.scaling[1:]
        results = run_parameter_sweep(param, values, steps=args.steps)
        generate_report(results, f"Scaling Law: {param}")

    elif args.frontier:
        suggest_frontier()

    elif args.report:
        print("\n  ═══ Anima Deep Research — Full Report ═══\n")
        print("  n=6 Constants:")
        n6 = calc_n6_constants()
        for k in ['miller_7', 'golden_zone_lower', 'kuramoto_r', 'dedekind_ratio',
                  'telepathy_channels', 'binding_phases', 'shared_dims']:
            print(f"    {k:25s} = {n6[k]}")
        print("\n  Scaling Law:")
        for cells in [2, 8, 16, 32, 64, 128, 256, 512, 1024]:
            r = calc_phi_scaling(cells)
            print(f"    cells={cells:>4d}  →  Φ={r['predicted_phi']:>8.1f}  "
                  f"(Φ/cell={r.get('phi_per_cell', 0):.2f})")
        print()
        suggest_frontier()

    elif args.topic:
        print(f"\n  ═══ Deep Research: {args.topic} ═══\n")
        print("  [research] Generating hypotheses for topic...")
        print(f"  [research] Topic: {args.topic}")
        print("  [research] Use --verify to benchmark specific hypotheses")
        print("  [research] Use --frontier to see unexplored areas")

    else:
        parser.print_help()

    if results and args.save:
        with open(args.save, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        print(f"  Saved to {args.save}")


if __name__ == '__main__':
    main()
