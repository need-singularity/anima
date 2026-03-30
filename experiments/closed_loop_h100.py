#!/usr/bin/env python3
"""closed_loop_h100.py — H100 대규모 폐쇄 루프 (512/1024c)

H100에서 실행: tmux new-session -d -s closed_loop "python3 experiments/closed_loop_h100.py"

스케일: 512c, 1024c
사이클: 5 (법칙 진화 + 수렴 검출)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from closed_loop import ClosedLoopEvolver


def main():
    scales = [512, 1024]
    n_cycles = 5

    all_results = {}

    for max_cells in scales:
        print(f"\n{'▓'*70}")
        print(f"  H100 폐쇄 루프 — {max_cells}c, {n_cycles} 사이클")
        print(f"{'▓'*70}")

        t0 = time.time()
        evolver = ClosedLoopEvolver(
            max_cells=max_cells,
            steps=500,
            repeats=3,
            auto_register=True,  # 자동 법칙 등록
        )
        reports = evolver.run_cycles(n=n_cycles)
        elapsed = time.time() - t0

        evolver.print_evolution()
        evolver.save(f"data/closed_loop_h100_{max_cells}c.json")

        all_results[max_cells] = {
            'n_cycles': n_cycles,
            'elapsed': elapsed,
            'phi_evolution': [r.phi_improved for r in reports],
            'laws_changed_per_cycle': [len(r.laws_changed) for r in reports],
            'total_laws_changed': sum(len(r.laws_changed) for r in reports),
        }

        print(f"\n  ⏱ {max_cells}c: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # 최종 요약
    print(f"\n{'═'*70}")
    print(f"  H100 폐쇄 루프 — 최종 요약")
    print(f"{'═'*70}")
    for mc, r in all_results.items():
        print(f"  {mc}c: Φ {r['phi_evolution'][0]:.4f}→{r['phi_evolution'][-1]:.4f}  "
              f"laws changed: {r['laws_changed_per_cycle']}  "
              f"time: {r['elapsed']:.0f}s")

    # JSON
    with open("data/closed_loop_h100_summary.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
