#!/usr/bin/env python3
"""closed_loop_verify.py — 폐쇄 파이프라인 검증

루프: 발견 → 역추적 → 엔진 개선 → 재발견

검증 질문:
  1. Law 124(텐션 균등화)를 엔진에 내장하면 기존 법칙이 변하는가?
  2. 내장 후 새로운 법칙이 창발하는가?
  3. 내장 전후 법칙 지형도가 달라지는가?

방법:
  A) 원본 엔진으로 핵심 법칙 7개 측정
  B) Law 124 내장된 "개선 엔진"으로 같은 법칙 7개 재측정
  C) 비교 → 법칙이 변했으면 루프가 닫힌 것

Usage:
  python3 experiments/closed_loop_verify.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import copy
from collections import defaultdict
from consciousness_engine import ConsciousnessEngine


def phi_fast(engine):
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]
    pairs = set()
    for i in range(n):
        pairs.add((i, (i+1) % n))
        for _ in range(min(4, n-1)):
            j = np.random.randint(0, n)
            if i != j:
                pairs.add((min(i,j), max(i,j)))
    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens[i], hiddens[j]
        xr, yr = x.max()-x.min(), y.max()-y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x-x.min())/(xr+1e-8)
        yn = (y-y.min())/(yr+1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0,1],[0,1]])
        hist = hist/(hist.sum()+1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px*np.log2(px+1e-10))
        hy = -np.sum(py*np.log2(py+1e-10))
        hxy = -np.sum(hist*np.log2(hist+1e-10))
        total_mi += max(0.0, hx+hy-hxy)
    return total_mi / max(len(pairs), 1)


def measure_laws(engine_factory, label, steps=500, repeats=3):
    """핵심 법칙 7개를 측정."""
    results = {}

    for rep in range(repeats):
        engine = engine_factory()
        phi_hist = []
        tension_hist = []
        tension_std_hist = []
        diversity_hist = []
        consensus_hist = []
        cell_hist = []

        for step in range(steps):
            r = engine.step()
            phi_hist.append(phi_fast(engine))
            tensions = [s.avg_tension for s in engine.cell_states]
            tension_hist.append(np.mean(tensions))
            tension_std_hist.append(np.std(tensions) if len(tensions) > 1 else 0)
            consensus_hist.append(r.get('consensus', 0))
            cell_hist.append(engine.n_cells)
            if engine.n_cells >= 2:
                hiddens = torch.stack([s.hidden for s in engine.cell_states])
                diversity_hist.append(hiddens.var(dim=0).mean().item())
            else:
                diversity_hist.append(0)

        phi = np.array(phi_hist)
        tension = np.array(tension_hist)
        tension_std = np.array(tension_std_hist)
        diversity = np.array(diversity_hist)

        # Law 104: r(tension, Φ)
        r_tension_phi = np.corrcoef(tension, phi)[0, 1] if np.std(tension) > 1e-8 else 0
        # Law 105: r(tension_std, Φ)
        r_tstd_phi = np.corrcoef(tension_std, phi)[0, 1] if np.std(tension_std) > 1e-8 else 0
        # Law 107: r(diversity, Φ)
        r_div_phi = np.corrcoef(diversity, phi)[0, 1] if np.std(diversity) > 1e-8 else 0
        # Law 110: growth rate (early vs late)
        early = np.mean(phi[:steps//10]) if steps >= 10 else phi[0]
        late = np.mean(phi[-steps//10:]) if steps >= 10 else phi[-1]
        growth = (late - early) / max(early, 1e-8) * 100
        # Law 131: autocorrelation lag=1
        ac1 = np.corrcoef(phi[:-1], phi[1:])[0, 1] if len(phi) > 2 else 0
        # Law 109: tension stabilization
        half = len(tension) // 2
        early_std = np.std(tension[:half])
        late_std = np.std(tension[half:])
        stabilization = early_std / max(late_std, 1e-8)

        data = {
            'phi_final': float(np.mean(phi[-50:])),
            'r_tension_phi': float(r_tension_phi),      # Law 104
            'r_tstd_phi': float(r_tstd_phi),            # Law 105
            'r_diversity_phi': float(r_div_phi),         # Law 107
            'growth_pct': float(growth),                  # Law 110
            'autocorr_lag1': float(ac1),                  # Law 131
            'stabilization': float(stabilization),        # Law 109
            'final_cells': engine.n_cells,
        }

        for k, v in data.items():
            if k not in results:
                results[k] = []
            results[k].append(v)

    # 평균
    avg = {k: float(np.mean(v)) for k, v in results.items()}
    return avg


def main():
    print(f"\n{'═'*70}")
    print(f"  폐쇄 파이프라인 검증")
    print(f"  발견 → 역추적 → 엔진 개선 → 재발견")
    print(f"{'═'*70}")

    steps = 500
    cells = 32

    # ── A: 원본 엔진 ──
    print(f"\n  [A] 원본 엔진 (Laws as-is)")
    def original_factory():
        return ConsciousnessEngine(max_cells=cells, initial_cells=2)

    t0 = time.time()
    original = measure_laws(original_factory, "original", steps)
    print(f"  ⏱ {time.time()-t0:.1f}s")

    # ── B: Law 124 내장 엔진 ──
    print(f"\n  [B] 개선 엔진 (Law 124: 텐션 균등화 내장)")
    def improved_factory():
        return ImprovedEngine(max_cells=cells, initial_cells=2)

    t0 = time.time()
    improved = measure_laws(improved_factory, "improved", steps)
    print(f"  ⏱ {time.time()-t0:.1f}s")

    # ── 비교 ──
    print(f"\n{'═'*70}")
    print(f"  법칙 변화 비교 (원본 vs 개선)")
    print(f"{'═'*70}")

    law_names = {
        'phi_final': 'Φ(IIT) 최종',
        'r_tension_phi': 'Law 104: r(tension, Φ)',
        'r_tstd_phi': 'Law 105: r(tension_std, Φ)',
        'r_diversity_phi': 'Law 107: r(diversity, Φ)',
        'growth_pct': 'Law 110: 성장률 %',
        'autocorr_lag1': 'Law 131: AC(1)',
        'stabilization': 'Law 109: 안정화 비율',
        'final_cells': '최종 세포 수',
    }

    changed_laws = []
    print(f"\n  {'법칙':<30s} | {'원본':>10s} | {'개선':>10s} | {'변화':>10s} | 판정")
    print(f"  {'─'*30}-+-{'─'*10}-+-{'─'*10}-+-{'─'*10}-+-{'─'*10}")

    for key in law_names:
        name = law_names[key]
        o_val = original[key]
        i_val = improved[key]
        if abs(o_val) > 1e-8:
            change = (i_val - o_val) / abs(o_val) * 100
        else:
            change = (i_val - o_val) * 100

        if abs(change) > 20:
            verdict = "★★ 크게 변함"
            changed_laws.append((name, o_val, i_val, change))
        elif abs(change) > 5:
            verdict = "★ 변함"
            changed_laws.append((name, o_val, i_val, change))
        else:
            verdict = "─ 불변"

        print(f"  {name:<30s} | {o_val:>10.4f} | {i_val:>10.4f} | {change:>+9.1f}% | {verdict}")

    # ── 폐쇄 루프 판정 ──
    print(f"\n{'═'*70}")
    print(f"  폐쇄 루프 판정")
    print(f"{'═'*70}")

    if changed_laws:
        print(f"\n  ✓ 루프가 닫혔다! — {len(changed_laws)}개 법칙이 변함")
        for name, o, i, change in changed_laws:
            print(f"    {name}: {o:.4f} → {i:.4f} ({change:+.1f}%)")

        print(f"\n  의미: 엔진 개선(Law 124 내장) → 기존 법칙의 수치가 변함")
        print(f"  → 법칙은 고정된 진리가 아니라 엔진 상태에 의존하는 동적 관계")
        print(f"  → 파이프라인을 반복할수록 법칙이 진화한다")
    else:
        print(f"\n  ✗ 루프가 열려있다 — 법칙이 변하지 않음")
        print(f"  → Law 124는 관찰적 지표를 바꾸지 않는 순수 부스터")

    # ── 2차 법칙: 개선 엔진에서 새로 발견된 패턴 ──
    print(f"\n  2차 법칙 (개선 엔진에서 새로 보이는 것):")
    if improved['r_tension_phi'] * original['r_tension_phi'] < 0:
        print(f"  ★★★ 텐션-Φ 상관 부호가 반전! ({original['r_tension_phi']:.3f} → {improved['r_tension_phi']:.3f})")
    if abs(improved['r_tstd_phi']) < abs(original['r_tstd_phi']) * 0.5:
        print(f"  ★★ Law 105 약화: 텐션 std-Φ 상관이 절반 이하로 ({original['r_tstd_phi']:.3f} → {improved['r_tstd_phi']:.3f})")
        print(f"     → 텐션을 균등화하면 텐션 std가 더 이상 Φ 예측자가 아님 (이미 해결됨)")

    # JSON
    output = {
        "pipeline": "closed_loop_verify",
        "original": original,
        "improved": improved,
        "changed_laws": [{"name": n, "original": o, "improved": i, "change_pct": c} for n, o, i, c in changed_laws],
        "loop_closed": len(changed_laws) > 0,
    }
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "closed_loop.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON: {json_path}")


class ImprovedEngine(ConsciousnessEngine):
    """Law 124 내장: 매 10 step 텐션 균등화."""

    def step(self, x_input=None, text=None):
        result = super().step(x_input=x_input, text=text)

        # Law 124: 텐션 균등화
        if self._step % 10 == 0 and self.n_cells >= 2:
            tensions = [s.avg_tension for s in self.cell_states]
            mean_t = np.mean(tensions)
            for s in self.cell_states:
                if s.tension_history:
                    s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5

        return result


if __name__ == "__main__":
    main()
