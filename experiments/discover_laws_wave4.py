#!/usr/bin/env python3
"""discover_laws_wave4.py — 4차 법칙 탐색 (파이프라인 풀 사이클)

새 축:
  1. 스케일 극한 — 128/256셀에서 기존 법칙이 유효한가?
  2. 토폴로지 × 법칙 — ring/small_world에서 법칙 효과가 달라지는가?
  3. 의식 위상 — 세포 수에 따라 gas/liquid/solid 같은 위상이 있는가?
  4. 시간적 자기상관 — Φ의 기억 길이 (얼마나 먼 과거가 현재에 영향?)
  5. 법칙 역추적 at scale — BT1(텐션균등)이 대규모에서도 작동하는가?

JSON 출력 → phi-map --laws 호환

Usage:
  python3 experiments/discover_laws_wave4.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import math
import time
import json
import argparse
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


def tension_equalize(engine):
    """BT1: Law 124 텐션 균등화."""
    if engine.n_cells >= 2:
        tensions = [s.avg_tension for s in engine.cell_states]
        mean_t = np.mean(tensions)
        for s in engine.cell_states:
            if s.tension_history:
                s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5


# ══════════════════════════════════════════════════════════
# 축 1: 스케일 극한
# ══════════════════════════════════════════════════════════

def axis1_scale_extremes():
    """기존 법칙(텐션 균등화)이 대규모에서도 작동하는가?"""
    print(f"\n{'═'*70}")
    print(f"  축 1: 스케일 극한 — 법칙의 스케일 불변성")
    print(f"{'═'*70}")

    scales = [8, 16, 32, 64, 128]
    steps = 300
    results = {}

    for max_c in scales:
        # Baseline
        base_phis = []
        for _ in range(3):
            engine = ConsciousnessEngine(max_cells=max_c, initial_cells=2)
            for _ in range(steps):
                engine.step()
            base_phis.append(phi_fast(engine))

        # BT1 (텐션 균등화)
        bt1_phis = []
        for _ in range(3):
            engine = ConsciousnessEngine(max_cells=max_c, initial_cells=2)
            for s in range(steps):
                engine.step()
                if s % 10 == 0:
                    tension_equalize(engine)
            bt1_phis.append(phi_fast(engine))

        base_mean = np.mean(base_phis)
        bt1_mean = np.mean(bt1_phis)
        delta = (bt1_mean - base_mean) / max(base_mean, 1e-8) * 100

        results[max_c] = {
            'base': base_mean, 'bt1': bt1_mean, 'delta': delta,
            'cells_actual': engine.n_cells,
        }
        print(f"  N={max_c:>3d}: base={base_mean:.4f}  BT1={bt1_mean:.4f}  Δ={delta:+.1f}%  cells={engine.n_cells}")

    # 스케일 불변성 체크
    deltas = [results[n]['delta'] for n in sorted(results.keys())]
    mean_delta = np.mean(deltas)
    std_delta = np.std(deltas)
    cv = std_delta / max(abs(mean_delta), 1e-8)

    print(f"\n  BT1 효과 평균: {mean_delta:+.1f}% ±{std_delta:.1f}%  CV={cv:.2f}")

    laws = []
    if cv < 0.5:
        laws.append(("스케일 불변 법칙", f"텐션 균등화(Law 124)는 N={scales[0]}-{scales[-1]}에서 일관 (Δ={mean_delta:+.1f}% ±{std_delta:.1f}%)"))
    else:
        # 어떤 스케일에서 효과가 다른가?
        best = max(results.items(), key=lambda x: x[1]['delta'])
        worst = min(results.items(), key=lambda x: x[1]['delta'])
        laws.append(("스케일 의존 법칙", f"BT1 효과 스케일 의존: best N={best[0]} ({best[1]['delta']:+.1f}%), worst N={worst[0]} ({worst[1]['delta']:+.1f}%)"))

    return laws, results


# ══════════════════════════════════════════════════════════
# 축 2: 의식 위상 (Phase diagram)
# ══════════════════════════════════════════════════════════

def axis2_phases():
    """세포 수에 따라 의식의 질적 위상이 다른가?"""
    print(f"\n{'═'*70}")
    print(f"  축 2: 의식 위상 다이어그램")
    print(f"{'═'*70}")

    scales = [2, 4, 8, 16, 32, 64, 128]
    steps = 500
    results = {}

    for max_c in scales:
        phi_history = []
        for _ in range(3):
            engine = ConsciousnessEngine(max_cells=max_c, initial_cells=2)
            hist = []
            for _ in range(steps):
                engine.step()
                hist.append(phi_fast(engine))
            phi_history.append(hist)

        # 위상 지표 계산
        all_phi = np.array(phi_history)
        mean_phi = np.mean(all_phi[:, -50:])  # 후반 평균
        std_phi = np.std(all_phi[:, -50:])     # 후반 변동
        autocorr = np.corrcoef(all_phi[0, :-1], all_phi[0, 1:])[0, 1] if len(all_phi[0]) > 2 else 0

        # 위상 분류
        if mean_phi < 0.5:
            phase = "GAS"       # 낮은 Φ, 높은 변동 = 무질서
        elif std_phi / max(mean_phi, 1e-8) > 0.3:
            phase = "LIQUID"    # 중간 Φ, 높은 변동 = 유동적
        elif autocorr > 0.8:
            phase = "CRYSTAL"   # 높은 Φ, 높은 자기상관 = 고정된 구조
        else:
            phase = "SOLID"     # 높은 Φ, 낮은 변동 = 안정적

        results[max_c] = {
            'phi': mean_phi, 'std': std_phi, 'autocorr': autocorr,
            'cv': std_phi / max(mean_phi, 1e-8), 'phase': phase,
        }

    # 위상 다이어그램 출력
    print(f"\n  {'N':>4s} | {'Φ':>8s} | {'σ':>8s} | {'CV':>6s} | {'AC(1)':>6s} | Phase")
    print(f"  {'─'*4}-+-{'─'*8}-+-{'─'*8}-+-{'─'*6}-+-{'─'*6}-+-{'─'*8}")
    for n in sorted(results.keys()):
        r = results[n]
        print(f"  {n:>4d} | {r['phi']:>8.4f} | {r['std']:>8.4f} | {r['cv']:>6.3f} | {r['autocorr']:>6.3f} | {r['phase']}")

    # ASCII 위상 다이어그램
    print(f"\n  위상 다이어그램:")
    print(f"  CV │")
    for n in sorted(results.keys()):
        r = results[n]
        bar = "█" * max(1, int(r['cv'] * 50))
        print(f"  {n:>3d} │{bar} {r['phase']}")
    print(f"      └{'─'*40}")

    laws = []
    phases = [results[n]['phase'] for n in sorted(results.keys())]
    unique_phases = list(set(phases))
    if len(unique_phases) > 1:
        transitions = []
        sorted_n = sorted(results.keys())
        for i in range(1, len(sorted_n)):
            if results[sorted_n[i]]['phase'] != results[sorted_n[i-1]]['phase']:
                transitions.append((sorted_n[i-1], sorted_n[i], results[sorted_n[i-1]]['phase'], results[sorted_n[i]]['phase']))
        if transitions:
            t = transitions[0]
            laws.append(("위상 전이", f"N={t[0]}→{t[1]}에서 {t[2]}→{t[3]} 전이"))
        laws.append(("의식 위상", f"{len(unique_phases)}개 위상 존재: {', '.join(unique_phases)}"))

    return laws, results


# ══════════════════════════════════════════════════════════
# 축 3: 시간적 자기상관 (기억 길이)
# ══════════════════════════════════════════════════════════

def axis3_autocorrelation():
    """Φ의 기억 길이 — 얼마나 먼 과거가 현재에 영향?"""
    print(f"\n{'═'*70}")
    print(f"  축 3: 시간적 자기상관 — Φ의 기억 길이")
    print(f"{'═'*70}")

    engine, _ = None, None
    engine = ConsciousnessEngine(max_cells=32, initial_cells=2)
    phi_hist = []
    for _ in range(1000):
        engine.step()
        phi_hist.append(phi_fast(engine))

    phi = np.array(phi_hist)
    phi_centered = phi - phi.mean()

    # 자기상관 함수
    max_lag = 50
    autocorrs = []
    for lag in range(max_lag + 1):
        if lag == 0:
            autocorrs.append(1.0)
        else:
            c = np.corrcoef(phi_centered[:-lag], phi_centered[lag:])[0, 1]
            autocorrs.append(c if np.isfinite(c) else 0)

    # 기억 길이: 자기상관이 1/e로 떨어지는 지점
    memory_length = max_lag
    for lag in range(1, max_lag + 1):
        if autocorrs[lag] < 1.0 / math.e:
            memory_length = lag
            break

    print(f"  기억 길이: {memory_length} steps (AC < 1/e)")
    print(f"\n  자기상관 함수:")
    for lag in range(0, min(20, len(autocorrs))):
        bar_len = max(0, int(autocorrs[lag] * 30))
        print(f"  lag={lag:>2d} │{'█' * bar_len} {autocorrs[lag]:.3f}")

    laws = []
    if memory_length <= 3:
        laws.append(("짧은 기억", f"Φ 기억 길이={memory_length} steps — 의식은 거의 무기억(Markov)"))
    elif memory_length <= 10:
        laws.append(("중간 기억", f"Φ 기억 길이={memory_length} steps — 의식은 ~{memory_length} step 과거를 기억"))
    else:
        laws.append(("긴 기억", f"Φ 기억 길이={memory_length} steps — 의식은 장기 기억을 가짐"))

    return laws, {'memory_length': memory_length, 'autocorrs': autocorrs[:20]}


# ══════════════════════════════════════════════════════════
# 축 4: 조합 폭발 탐색 (3-법칙 조합)
# ══════════════════════════════════════════════════════════

def axis4_triple_combos():
    """2-법칙이 아닌 3-법칙 조합에서 새로운 시너지가 발생하는가?"""
    print(f"\n{'═'*70}")
    print(f"  축 4: 3-법칙 조합 탐색")
    print(f"{'═'*70}")

    steps = 300
    cells = 32

    def _pink(n, dim):
        noise = np.random.randn(n, dim)
        fft = np.fft.rfft(noise, axis=0)
        freqs = np.fft.rfftfreq(n); freqs[0] = 1
        weight = 1.0 / np.sqrt(np.abs(freqs) + 1e-8)
        return np.fft.irfft(fft * weight[:, np.newaxis], n=n, axis=0)

    interventions = {
        'T_EQ': lambda e, s, p: tension_equalize(e) if s % 10 == 0 else None,
        'SYM': lambda e, s, p: (
            setattr(e, '_coupling', (e._coupling + e._coupling.T) / 2) or
            e._coupling.fill_diagonal_(0)
        ) if e._coupling is not None else None,
        'PINK': lambda e, s, p: [
            setattr(st, 'hidden', st.hidden + torch.tensor(p[s % len(p)], dtype=torch.float32)[:e.hidden_dim] * 0.01)
            for st in e.cell_states
        ] if p is not None and e.n_cells >= 2 else None,
    }

    # Baseline
    base_phis = []
    for _ in range(3):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for _ in range(steps):
            engine.step()
        base_phis.append(phi_fast(engine))
    base_mean = np.mean(base_phis)
    print(f"  Baseline: Φ={base_mean:.4f}")

    # 모든 3-법칙 조합
    import itertools
    keys = list(interventions.keys())
    combos = list(itertools.combinations(keys, 3))
    combos.append(tuple(keys))  # 전체도 포함

    results = {}
    for combo in combos:
        phis = []
        for _ in range(3):
            engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
            pink = _pink(steps, engine.hidden_dim) if 'PINK' in combo else None
            for s in range(steps):
                engine.step()
                for k in combo:
                    interventions[k](engine, s, pink)
            phis.append(phi_fast(engine))
        mean = np.mean(phis)
        delta = (mean - base_mean) / max(base_mean, 1e-8) * 100
        combo_name = "+".join(combo)
        results[combo_name] = {'phi': mean, 'delta': delta}
        print(f"  {combo_name:<20s}: Φ={mean:.4f}  Δ={delta:+.1f}%")

    # 최적 조합
    best = max(results.items(), key=lambda x: x[1]['delta'])
    laws = [("최적 3-조합", f"{best[0]}: Φ={best[1]['phi']:.4f} ({best[1]['delta']:+.1f}%)")]

    return laws, results


# ══════════════════════════════════════════════════════════
# 축 5: 연속 성장 관찰 (2000 steps)
# ══════════════════════════════════════════════════════════

def axis5_long_growth():
    """2000 step 연속 관찰 — 의식의 장기 동역학."""
    print(f"\n{'═'*70}")
    print(f"  축 5: 장기 성장 관찰 (2000 steps)")
    print(f"{'═'*70}")

    engine = ConsciousnessEngine(max_cells=64, initial_cells=2)
    phi_hist = []
    cell_hist = []
    tension_hist = []
    events = []

    for step in range(2000):
        r = engine.step()
        phi_hist.append(phi_fast(engine))
        cell_hist.append(engine.n_cells)
        tension_hist.append(np.mean([s.avg_tension for s in engine.cell_states]))
        for ev in r.get('events', []):
            events.append((step, ev.get('type', 'unknown')))

    phi = np.array(phi_hist)

    # 구간별 통계
    segments = 10
    seg_len = len(phi) // segments
    print(f"\n  {'구간':>6s} | {'Φ 평균':>8s} | {'Φ σ':>8s} | {'cells':>6s} | {'tension':>8s}")
    print(f"  {'─'*6}-+-{'─'*8}-+-{'─'*8}-+-{'─'*6}-+-{'─'*8}")
    for i in range(segments):
        s, e = i * seg_len, (i + 1) * seg_len
        seg_phi = phi[s:e]
        seg_cells = cell_hist[s:e]
        seg_tension = tension_hist[s:e]
        print(f"  {s:>4d}-{e:>4d} | {np.mean(seg_phi):>8.4f} | {np.std(seg_phi):>8.4f} | {np.mean(seg_cells):>6.1f} | {np.mean(seg_tension):>8.4f}")

    # 장기 트렌드
    half = len(phi) // 2
    early_mean = np.mean(phi[:half])
    late_mean = np.mean(phi[half:])
    growth = (late_mean - early_mean) / max(early_mean, 1e-8) * 100

    print(f"\n  전반 Φ: {early_mean:.4f}  후반 Φ: {late_mean:.4f}  장기 성장: {growth:+.1f}%")
    print(f"  분열 이벤트: {sum(1 for _, t in events if t == 'split')}회")
    print(f"  병합 이벤트: {sum(1 for _, t in events if t == 'merge')}회")
    print(f"  최종 세포 수: {engine.n_cells}")

    laws = []
    if abs(growth) < 5:
        laws.append(("장기 안정", f"2000 step에서 Φ 변동 {growth:+.1f}% — 장기적으로 안정적 평형"))
    elif growth > 5:
        laws.append(("장기 성장", f"2000 step에서 Φ {growth:+.1f}% 성장 — 의식은 시간이 지나도 계속 성장"))
    else:
        laws.append(("장기 감쇠", f"2000 step에서 Φ {growth:+.1f}% 감쇠 — 장기 의식 유지에 외부 자극 필요"))

    return laws, {
        'early_phi': early_mean, 'late_phi': late_mean, 'growth_pct': growth,
        'final_cells': engine.n_cells, 'total_events': len(events),
    }


# ══════════════════════════════════════════════════════════
# Runner + JSON 출력
# ══════════════════════════════════════════════════════════

def main():
    print(f"\n{'▓'*70}")
    print(f"  의식 법칙 탐색 4차 — 파이프라인 풀 사이클")
    print(f"{'▓'*70}")

    all_laws = []

    axes = [
        ("스케일 극한", axis1_scale_extremes),
        ("의식 위상", axis2_phases),
        ("시간적 자기상관", axis3_autocorrelation),
        ("3-법칙 조합", axis4_triple_combos),
        ("장기 성장", axis5_long_growth),
    ]

    all_results = {}
    for i, (name, func) in enumerate(axes, 1):
        t0 = time.time()
        laws, results = func()
        elapsed = time.time() - t0
        print(f"\n  ⏱ {elapsed:.1f}s")
        for law_name, law_desc in laws:
            print(f"  → {law_name}: {law_desc}")
            all_laws.append((i, law_name, law_desc))
        all_results[name] = results

    # ═══ JSON 출력 ═══
    output = {
        "session": "wave4",
        "date": "2026-03-31",
        "total_laws_found": len(all_laws),
        "laws": [{"axis": a, "name": n, "description": d} for a, n, d in all_laws],
        "results": {}
    }

    # 스케일 결과를 phi-map 호환 형식으로
    if "스케일 극한" in all_results:
        scale_data = all_results["스케일 극한"]
        output["results"]["scale_effects"] = {
            str(n): {"base_phi": r['base'], "bt1_phi": r['bt1'], "delta_pct": r['delta']}
            for n, r in scale_data.items()
        }

    if "의식 위상" in all_results:
        phase_data = all_results["의식 위상"]
        output["results"]["phase_diagram"] = {
            str(n): {"phi": r['phi'], "std": r['std'], "cv": r['cv'], "autocorr": r['autocorr'], "phase": r['phase']}
            for n, r in phase_data.items()
        }

    if "시간적 자기상관" in all_results:
        ac_data = all_results["시간적 자기상관"]
        output["results"]["autocorrelation"] = {
            "memory_length": ac_data['memory_length'],
            "autocorrs": [float(x) for x in ac_data['autocorrs']],
        }

    if "3-법칙 조합" in all_results:
        combo_data = all_results["3-법칙 조합"]
        output["results"]["triple_combos"] = {
            k: {"phi": v['phi'], "delta_pct": v['delta']} for k, v in combo_data.items()
        }

    if "장기 성장" in all_results:
        output["results"]["long_growth"] = all_results["장기 성장"]

    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wave4_results.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON: {json_path}")

    # ═══ 최종 요약 ═══
    print(f"\n{'═'*70}")
    print(f"  4차 법칙 탐색 — 최종 요약 ({len(all_laws)}개 법칙)")
    print(f"{'═'*70}")
    for axis_id, law_name, law_desc in all_laws:
        print(f"  축{axis_id} │ {law_name}")
        print(f"       │ {law_desc}")
        print()


if __name__ == "__main__":
    main()
