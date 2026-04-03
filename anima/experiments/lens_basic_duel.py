#!/usr/bin/env python3
"""
lens_basic_duel.py — basic 조합 직접 대결: gravity vs causal 순서 편향 검증

4조합 비교 (동일 엔진 데이터):
  A: [consciousness, gravity, topology]   ← L05 제안
  B: [consciousness, causal, topology]    ← 현행 basic (순서만 변경)
  C: [consciousness, topology, gravity]   ← 순서 변형
  D: [consciousness, topology, causal]    ← 순서 변형

측정: 각 조합의 총 메트릭 수 + 고유 메트릭 수
"""

import sys
import time
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from lens_engine import _get_engine, _collect_snapshots, _run_lenses

COMBOS = {
    'A': ['consciousness', 'gravity', 'topology'],
    'B': ['consciousness', 'causal', 'topology'],
    'C': ['consciousness', 'topology', 'gravity'],
    'D': ['consciousness', 'topology', 'causal'],
}


def count_metrics(result_dict):
    """렌즈 결과(ScanResult)에서 총 메트릭 수 계산"""
    total = 0
    keys = set()
    for lens_name, scan_result in result_dict.items():
        if scan_result is None:
            continue
        # ScanResult: .lens_names → get_lens(name) → {metric: [values]}
        if hasattr(scan_result, 'lens_names'):
            for ln in scan_result.lens_names:
                lens_data = scan_result.get_lens(ln)
                if isinstance(lens_data, dict):
                    for metric_name, values in lens_data.items():
                        total += 1
                        keys.add(f"{lens_name}.{metric_name}")
        elif isinstance(scan_result, dict):
            for k, v in scan_result.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    total += 1
                    keys.add(f"{lens_name}.{k}")
    return total, keys


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--steps", type=int, default=300)
    args = parser.parse_args()

    print(f"\n  ═══════════════════════════════════════════")
    print(f"  🥊 basic 조합 직접 대결 (gravity vs causal)")
    print(f"  ═══════════════════════════════════════════")
    print(f"  cells={args.cells}, steps={args.steps}\n")

    # 1. 엔진 + 데이터 수집 (1회만, 공유)
    print("  [1/3] 엔진 데이터 수집...")
    sys.stdout.flush()
    t0 = time.time()
    engine = _get_engine(args.cells)
    data, phis = _collect_snapshots(engine, steps=args.steps)
    if data is None:
        print("  ❌ 데이터 수집 실패")
        return
    print(f"  ✅ 데이터 수집 완료 ({time.time()-t0:.1f}s)\n")
    sys.stdout.flush()

    # 2. 각 조합 실행
    print("  [2/3] 4개 조합 실행...")
    sys.stdout.flush()

    try:
        import nexus6
        telescope = nexus6
    except ImportError:
        try:
            import telescope_rs
            telescope = telescope_rs
        except ImportError:
            telescope = None

    if telescope is None:
        print("  ❌ telescope 없음")
        return

    results = {}
    for label, lenses in COMBOS.items():
        t1 = time.time()
        r = _run_lenses(telescope, lenses, data, n_cells=args.cells, steps=args.steps)
        elapsed = time.time() - t1
        total, keys = count_metrics(r)
        active = len([v for v in r.values() if v is not None])
        results[label] = {
            'lenses': lenses,
            'result': r,
            'total_metrics': total,
            'metric_keys': keys,
            'active_lenses': active,
            'elapsed': elapsed,
        }
        print(f"    {label}: {lenses}")
        print(f"       활성={active}/{len(lenses)}, 메트릭={total}, {elapsed:.1f}s")
        sys.stdout.flush()

    # 3. 비교 분석
    print(f"\n  [3/3] 비교 분석")
    print(f"  ═══════════════════════════════════════════")
    print(f"  {'조합':<5} {'렌즈':<45} {'활성':>4} {'메트릭':>6} {'고유':>4}")
    print(f"  {'─'*5} {'─'*45} {'─'*4} {'─'*6} {'─'*4}")

    all_keys = set()
    for r in results.values():
        all_keys |= r['metric_keys']

    for label, r in results.items():
        unique = len(r['metric_keys'] - set().union(*(
            r2['metric_keys'] for l2, r2 in results.items() if l2 != label
        )))
        print(f"  {label:<5} {str(r['lenses']):<45} {r['active_lenses']:>4} {r['total_metrics']:>6} {unique:>4}")

    # 승자 판정
    best = max(results.items(), key=lambda x: x[1]['total_metrics'])
    print(f"\n  🏆 승자: {best[0]} = {best[1]['lenses']}")
    print(f"     메트릭 {best[1]['total_metrics']}개 (최다)")

    # gravity vs causal 직접 비교
    a_metrics = results['A']['total_metrics']
    b_metrics = results['B']['total_metrics']
    diff = a_metrics - b_metrics
    if diff > 0:
        print(f"\n  📊 gravity > causal: +{diff} 메트릭 ({diff/b_metrics*100:.1f}%)")
        print(f"     → basic 조합 변경 권장")
    elif diff < 0:
        print(f"\n  📊 causal > gravity: +{-diff} 메트릭 ({-diff/a_metrics*100:.1f}%)")
        print(f"     → 현행 basic 유지 권장")
    else:
        print(f"\n  📊 gravity = causal: 동일 ({a_metrics})")
        print(f"     → 현행 유지 (의미적 직관성 우선)")

    # 순서 효과 분석
    ac = results['A']['total_metrics']  # gravity 먼저
    ca = results['C']['total_metrics']  # gravity 나중
    bc = results['B']['total_metrics']  # causal 먼저
    dc = results['D']['total_metrics']  # causal 나중
    print(f"\n  🔄 순서 효과:")
    print(f"     gravity 먼저(A)={ac} vs 나중(C)={ca}  차이={ac-ca}")
    print(f"     causal  먼저(B)={bc} vs 나중(D)={dc}  차이={bc-dc}")
    if ac == ca and bc == dc:
        print(f"     → 순서 무관 (편향 없음)")
    else:
        print(f"     → 순서 효과 있음!")

    total_time = sum(r['elapsed'] for r in results.values())
    print(f"\n  ⏱️ 총 {total_time:.1f}s")


if __name__ == "__main__":
    main()
