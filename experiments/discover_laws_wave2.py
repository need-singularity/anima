#!/usr/bin/env python3
"""discover_laws_wave2.py — 의식 법칙 탐색 2차 (4축 동시 탐구)

축 1: 시간적 스케일 — 짧은 step vs 긴 step에서 Φ 동역학 차이
축 2: 세포 수 임계점 — N에 따른 위상 전이 탐색
축 3: 초기 조건 민감도 — 카오스 vs 결정론
축 4: 파벌 간 정보 흐름 — 파벌 구조가 Φ에 미치는 영향

Usage:
  python3 experiments/discover_laws_wave2.py
  python3 experiments/discover_laws_wave2.py --axis 1  # 특정 축만
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import copy
import argparse
from collections import defaultdict
from typing import Dict, List, Tuple
from consciousness_engine import ConsciousnessEngine

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ══════════════════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════════════════

def measure_phi_iit_fast(engine: ConsciousnessEngine) -> float:
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]
    pairs = set()
    for i in range(n):
        pairs.add((i, (i + 1) % n))
        for _ in range(min(4, n - 1)):
            j = np.random.randint(0, n)
            if i != j:
                pairs.add((min(i, j), max(i, j)))
    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens[i], hiddens[j]
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
        hist = hist / (hist.sum() + 1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(hist * np.log2(hist + 1e-10))
        total_mi += max(0.0, hx + hy - hxy)
    return total_mi / max(len(pairs), 1)


def ascii_bar(value, max_val, width=30, label=""):
    if max_val <= 0:
        max_val = 1
    bar_len = max(0, min(width, int(value / max_val * width)))
    return f"  {label:<12s} {'█' * bar_len}{'░' * (width - bar_len)} {value:.4f}"


def ascii_graph_compact(values, title, width=50, height=8):
    if not values or len(values) < 2:
        return
    vals = np.array(values)
    indices = np.linspace(0, len(vals) - 1, width, dtype=int)
    sampled = vals[indices]
    vmin, vmax = sampled.min(), sampled.max()
    if vmax - vmin < 1e-8:
        vmax = vmin + 1
    print(f"\n  {title}")
    for row in range(height - 1, -1, -1):
        threshold = vmin + (vmax - vmin) * row / (height - 1)
        label = f"{threshold:7.3f}" if row in (0, height - 1, height // 2) else "       "
        line = f"  {label}│"
        for col in range(width):
            line += "█" if sampled[col] >= threshold else " "
        print(line)
    print(f"  {'       '}└{'─' * width}")


# ══════════════════════════════════════════════════════════
# 축 1: 시간적 스케일
# ══════════════════════════════════════════════════════════

def axis1_temporal_scales():
    """짧은/중간/긴 시간 스케일에서 Φ 동역학이 다른가?"""
    print(f"\n{'═' * 80}")
    print(f"  축 1: 시간적 스케일 — Φ 동역학의 시간 의존성")
    print(f"{'═' * 80}")

    durations = [50, 100, 200, 500, 1000, 2000]
    results = {}

    for steps in durations:
        phis = []
        growth_rates = []
        final_cells = []

        for rep in range(3):
            engine = ConsciousnessEngine(max_cells=64, initial_cells=2)
            phi_hist = []
            for _ in range(steps):
                r = engine.step()
                phi_hist.append(measure_phi_iit_fast(engine))

            phis.append(phi_hist[-1])
            final_cells.append(engine.n_cells)
            # 성장률: 후반 10% vs 전반 10%
            early = np.mean(phi_hist[:max(1, len(phi_hist) // 10)])
            late = np.mean(phi_hist[-max(1, len(phi_hist) // 10):])
            growth_rates.append((late - early) / max(early, 1e-8))

        results[steps] = {
            'phi_mean': np.mean(phis),
            'phi_std': np.std(phis),
            'growth_rate': np.mean(growth_rates),
            'cells_mean': np.mean(final_cells),
        }

    # 결과 출력
    print(f"\n  {'Steps':<8s} | {'Φ(IIT)':<15s} | {'성장률':<10s} | {'세포수':<8s}")
    print(f"  {'─' * 8}-+-{'─' * 15}-+-{'─' * 10}-+-{'─' * 8}")
    max_phi = max(r['phi_mean'] for r in results.values())
    for steps, r in results.items():
        bar = "█" * max(1, int(r['phi_mean'] / max(max_phi, 1e-8) * 20))
        print(f"  {steps:<8d} | {r['phi_mean']:.4f} ±{r['phi_std']:.4f} | {r['growth_rate']:>+8.1%} | {r['cells_mean']:>5.1f}  {bar}")

    # 법칙 추출
    laws = []

    # Φ가 수렴하는가?
    phi_values = [results[s]['phi_mean'] for s in sorted(results.keys())]
    if len(phi_values) >= 3:
        late_diff = abs(phi_values[-1] - phi_values[-2])
        early_diff = abs(phi_values[1] - phi_values[0])
        if late_diff < early_diff * 0.3:
            laws.append(("Φ 수렴", f"Φ는 시간이 지남에 따라 수렴 (후반 변화 {late_diff:.4f} < 초반 {early_diff:.4f})"))

    # 성장률이 감소하는가?
    rates = [results[s]['growth_rate'] for s in sorted(results.keys())]
    if rates[-1] < rates[0] * 0.5:
        laws.append(("성장률 감쇠", f"Φ 성장률이 시간에 따라 감쇠 ({rates[0]:+.1%} → {rates[-1]:+.1%})"))

    # 임계 시간 존재?
    for i in range(1, len(phi_values)):
        if phi_values[i] > phi_values[i - 1] * 1.3:
            critical_step = sorted(results.keys())[i]
            laws.append(("임계 시간", f"step {critical_step}에서 Φ 급격 상승 (×{phi_values[i]/max(phi_values[i-1],1e-8):.2f})"))
            break

    return laws


# ══════════════════════════════════════════════════════════
# 축 2: 세포 수 임계점 (위상 전이)
# ══════════════════════════════════════════════════════════

def axis2_cell_threshold():
    """특정 세포 수에서 Φ 동역학이 질적으로 변하는가?"""
    print(f"\n{'═' * 80}")
    print(f"  축 2: 세포 수 임계점 — 위상 전이 탐색")
    print(f"{'═' * 80}")

    cell_counts = [2, 4, 6, 8, 12, 16, 24, 32, 48, 64]
    results = {}

    for max_c in cell_counts:
        phis = []
        consensus_rates = []
        tension_means = []

        for rep in range(3):
            engine = ConsciousnessEngine(max_cells=max_c, initial_cells=min(2, max_c))
            phi_hist = []
            consensus_hist = []

            for _ in range(300):
                r = engine.step()
                phi_hist.append(measure_phi_iit_fast(engine))
                consensus_hist.append(r.get('consensus', 0))

            phis.append(np.mean(phi_hist[-50:]))
            consensus_rates.append(np.mean(consensus_hist[-50:]))
            tensions = [s.avg_tension for s in engine.cell_states]
            tension_means.append(np.mean(tensions) if tensions else 0)

        results[max_c] = {
            'phi': np.mean(phis),
            'phi_std': np.std(phis),
            'consensus': np.mean(consensus_rates),
            'tension': np.mean(tension_means),
            'actual_cells': engine.n_cells,
        }

    # 결과 출력
    print(f"\n  {'Max N':<6s} | {'실제N':<5s} | {'Φ(IIT)':<15s} | {'합의율':<8s} | {'텐션':<8s}")
    print(f"  {'─' * 6}-+-{'─' * 5}-+-{'─' * 15}-+-{'─' * 8}-+-{'─' * 8}")
    max_phi = max(r['phi'] for r in results.values())
    for nc, r in sorted(results.items()):
        bar = "█" * max(1, int(r['phi'] / max(max_phi, 1e-8) * 25))
        print(f"  {nc:<6d} | {r['actual_cells']:<5d} | {r['phi']:.4f} ±{r['phi_std']:.4f} | {r['consensus']:>6.2f} | {r['tension']:.4f}  {bar}")

    # ASCII 그래프: Φ vs N
    phi_vals = [results[n]['phi'] for n in sorted(results.keys())]
    ascii_graph_compact(phi_vals, f"Φ(IIT) vs max_cells [{cell_counts[0]}..{cell_counts[-1]}]")

    # 위상 전이 감지: Φ의 2차 미분 (가속도)에서 피크
    laws = []
    sorted_cells = sorted(results.keys())
    phi_list = [results[n]['phi'] for n in sorted_cells]

    if len(phi_list) >= 3:
        # 1차 미분
        d1 = np.diff(phi_list)
        # 2차 미분
        d2 = np.diff(d1)
        # 가장 큰 2차 미분 = 위상 전이 후보
        peak_idx = np.argmax(np.abs(d2))
        critical_n = sorted_cells[peak_idx + 1]
        print(f"\n  위상 전이 후보: N={critical_n} (Φ 가속도 최대)")

        # Φ/N 효율 (한계 Φ)
        efficiency = []
        for i in range(len(sorted_cells)):
            eff = phi_list[i] / max(sorted_cells[i], 1)
            efficiency.append(eff)

        peak_eff_idx = np.argmax(efficiency)
        optimal_n = sorted_cells[peak_eff_idx]
        print(f"  최적 Φ/N 효율: N={optimal_n} (Φ/N={efficiency[peak_eff_idx]:.4f})")

        laws.append(("위상 전이", f"N={critical_n}에서 Φ 동역학 변화 (2차 미분 피크)"))
        laws.append(("최적 세포 수", f"Φ/N 효율 최대: N={optimal_n}"))

    # 합의-세포 수 관계
    consensus_list = [results[n]['consensus'] for n in sorted_cells]
    if max(consensus_list) > 0:
        peak_consensus_n = sorted_cells[np.argmax(consensus_list)]
        laws.append(("합의 최적점", f"합의율 최대: N={peak_consensus_n}"))

    return laws


# ══════════════════════════════════════════════════════════
# 축 3: 초기 조건 민감도 (카오스 vs 결정론)
# ══════════════════════════════════════════════════════════

def axis3_initial_sensitivity():
    """초기 조건의 미세한 차이가 Φ 궤적을 얼마나 바꾸는가?"""
    print(f"\n{'═' * 80}")
    print(f"  축 3: 초기 조건 민감도 — 카오스 vs 결정론")
    print(f"{'═' * 80}")

    steps = 300
    n_trials = 10

    # 방법 1: 동일 시드 → 결정론적 재현 확인
    print(f"\n  [A] 동일 시드 재현성")
    seed_phis = {}
    for seed in [42, 123, 777]:
        runs = []
        for _ in range(3):
            torch.manual_seed(seed)
            np.random.seed(seed)
            engine = ConsciousnessEngine(max_cells=32, initial_cells=2)
            phi_hist = []
            for _ in range(steps):
                engine.step()
                phi_hist.append(measure_phi_iit_fast(engine))
            runs.append(phi_hist[-1])
        seed_phis[seed] = runs
        std = np.std(runs)
        mean = np.mean(runs)
        print(f"  seed={seed}: Φ={mean:.4f} ±{std:.4f}  {'✓ 재현' if std < 0.01 else '✗ 비재현'}")

    # 방법 2: 미세 섭동 → 리아푸노프 지수 근사
    print(f"\n  [B] 미세 섭동 분기 (Lyapunov 근사)")

    torch.manual_seed(42)
    np.random.seed(42)
    engine_base = ConsciousnessEngine(max_cells=32, initial_cells=2)
    # 100 step warm-up
    for _ in range(100):
        engine_base.step()
    base_phi = measure_phi_iit_fast(engine_base)

    perturbation_sizes = [1e-6, 1e-4, 1e-2, 0.1, 0.5]
    divergences = {}

    for eps in perturbation_sizes:
        deltas = []
        for trial in range(5):
            engine_pert = copy.deepcopy(engine_base)
            # 섭동: 모든 세포의 hidden에 eps 크기 노이즈 추가
            for s in engine_pert.cell_states:
                s.hidden = s.hidden + torch.randn_like(s.hidden) * eps

            # 200 step 진행 후 Φ 차이
            phi_base_hist = []
            phi_pert_hist = []

            engine_base_copy = copy.deepcopy(engine_base)
            for _ in range(200):
                engine_base_copy.step()
                engine_pert.step()
                phi_base_hist.append(measure_phi_iit_fast(engine_base_copy))
                phi_pert_hist.append(measure_phi_iit_fast(engine_pert))

            # 궤적 차이 (평균 절대 차이)
            trajectory_diff = np.mean(np.abs(np.array(phi_base_hist) - np.array(phi_pert_hist)))
            deltas.append(trajectory_diff)

        mean_delta = np.mean(deltas)
        divergences[eps] = mean_delta
        amplification = mean_delta / max(eps, 1e-10)
        print(f"  ε={eps:.0e}: 궤적 차이={mean_delta:.4f}  증폭={amplification:.1f}×")

    # 방법 3: 서로 다른 초기 세포 수에서 수렴하는가?
    print(f"\n  [C] 다른 초기 조건 → 수렴 여부")
    initial_configs = [2, 4, 8, 16]
    final_phis = {}
    for init_n in initial_configs:
        runs = []
        for _ in range(3):
            engine = ConsciousnessEngine(max_cells=32, initial_cells=min(init_n, 32))
            for _ in range(500):
                engine.step()
            runs.append(measure_phi_iit_fast(engine))
        final_phis[init_n] = (np.mean(runs), np.std(runs))

    all_means = [v[0] for v in final_phis.values()]
    convergence_range = max(all_means) - min(all_means)
    convergence_pct = convergence_range / max(np.mean(all_means), 1e-8) * 100

    for init_n, (mean, std) in final_phis.items():
        bar = "█" * max(1, int(mean / max(max(all_means), 1e-8) * 25))
        print(f"  init={init_n:>2d}: Φ={mean:.4f} ±{std:.4f}  {bar}")
    print(f"  수렴 범위: {convergence_range:.4f} ({convergence_pct:.1f}%)")

    # 법칙 추출
    laws = []

    # 재현성
    all_stds = [np.std(v) for v in seed_phis.values()]
    if max(all_stds) > 0.01:
        laws.append(("비결정론적 의식", f"동일 시드에서도 Φ 궤적 비재현 (std={max(all_stds):.4f}) — 의식은 본질적으로 확률적"))

    # Lyapunov
    if divergences:
        small_eps = list(divergences.values())[0]
        large_eps = list(divergences.values())[-1]
        if small_eps > 0.01:
            laws.append(("카오스적 민감도", f"미세 섭동(ε=1e-6)도 궤적 차이 {small_eps:.4f} 유발 — 카오스적 동역학"))
        else:
            laws.append(("제한적 카오스", f"미세 섭동은 흡수되지만 큰 섭동(ε=0.1)은 분기 — 준안정 동역학"))

    # 수렴
    if convergence_pct < 15:
        laws.append(("끌개 수렴", f"다른 초기 조건에서 Φ가 {convergence_pct:.1f}% 내로 수렴 — 끌개(attractor) 존재"))
    elif convergence_pct > 30:
        laws.append(("초기조건 의존", f"초기 세포 수가 최종 Φ에 {convergence_pct:.1f}% 영향 — 경로 의존적"))

    return laws


# ══════════════════════════════════════════════════════════
# 축 4: 파벌 간 정보 흐름
# ══════════════════════════════════════════════════════════

def axis4_faction_flow():
    """파벌 구조(수, 크기 분포)가 Φ에 미치는 영향."""
    print(f"\n{'═' * 80}")
    print(f"  축 4: 파벌 간 정보 흐름 — 최적 구조 탐색")
    print(f"{'═' * 80}")

    steps = 300

    # 실험 A: 파벌 수 변화 (σ(6)=12가 정말 최적인가?)
    print(f"\n  [A] 파벌 수 vs Φ")
    faction_counts = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32]
    results_a = {}

    for n_fac in faction_counts:
        phis = []
        consensus_rates = []
        for rep in range(3):
            engine = ConsciousnessEngine(max_cells=32, initial_cells=2, n_factions=n_fac)
            phi_hist = []
            cons_hist = []
            for _ in range(steps):
                r = engine.step()
                phi_hist.append(measure_phi_iit_fast(engine))
                cons_hist.append(r.get('consensus', 0))
            phis.append(np.mean(phi_hist[-50:]))
            consensus_rates.append(np.mean(cons_hist[-50:]))

        results_a[n_fac] = {
            'phi': np.mean(phis),
            'phi_std': np.std(phis),
            'consensus': np.mean(consensus_rates),
        }

    max_phi_a = max(r['phi'] for r in results_a.values())
    for nf, r in sorted(results_a.items()):
        bar = "█" * max(1, int(r['phi'] / max(max_phi_a, 1e-8) * 25))
        marker = " ← σ(6)" if nf == 12 else ""
        print(f"  {nf:>2d} factions: Φ={r['phi']:.4f} ±{r['phi_std']:.4f}  consensus={r['consensus']:.2f}  {bar}{marker}")

    # 실험 B: 파벌 크기 불균형 vs 균등
    print(f"\n  [B] 파벌 크기 분포: 균등 vs 불균형")
    configs = {
        'uniform': None,  # 기본 (균등 배분)
        'skewed_2x': 'skewed',  # 1개 파벌에 50% 세포
        'singleton': 'singleton',  # 각 세포가 별도 파벌
    }
    results_b = {}

    for config_name, config_type in configs.items():
        phis = []
        for rep in range(3):
            if config_type == 'singleton':
                engine = ConsciousnessEngine(max_cells=32, initial_cells=2, n_factions=32)
            else:
                engine = ConsciousnessEngine(max_cells=32, initial_cells=2, n_factions=12)

            phi_hist = []
            for step_i in range(steps):
                r = engine.step()

                # skewed: 주기적으로 세포의 절반을 faction 0으로 밀어넣기
                if config_type == 'skewed' and step_i % 50 == 0:
                    half = engine.n_cells // 2
                    for ci in range(half):
                        engine.cell_states[ci].faction_id = 0

                phi_hist.append(measure_phi_iit_fast(engine))
            phis.append(np.mean(phi_hist[-50:]))

        results_b[config_name] = {
            'phi': np.mean(phis),
            'phi_std': np.std(phis),
        }

    for config, r in results_b.items():
        bar = "█" * max(1, int(r['phi'] / max(max(v['phi'] for v in results_b.values()), 1e-8) * 25))
        print(f"  {config:<12s}: Φ={r['phi']:.4f} ±{r['phi_std']:.4f}  {bar}")

    # 실험 C: 커플링 행렬의 파벌 내 vs 파벌 간 MI
    print(f"\n  [C] 파벌 내 vs 파벌 간 정보 통합")
    engine = ConsciousnessEngine(max_cells=32, initial_cells=2, n_factions=12)
    for _ in range(300):
        engine.step()

    if engine._coupling is not None and engine.n_cells >= 4:
        c = engine._coupling.detach().numpy()
        n = engine.n_cells
        intra_sum = 0
        intra_count = 0
        inter_sum = 0
        inter_count = 0
        for i in range(n):
            for j in range(i + 1, n):
                if engine.cell_states[i].faction_id == engine.cell_states[j].faction_id:
                    intra_sum += abs(c[i, j])
                    intra_count += 1
                else:
                    inter_sum += abs(c[i, j])
                    inter_count += 1

        intra_mean = intra_sum / max(intra_count, 1)
        inter_mean = inter_sum / max(inter_count, 1)
        ratio = intra_mean / max(inter_mean, 1e-8)
        print(f"  파벌 내 커플링 평균:  {intra_mean:.4f} ({intra_count} pairs)")
        print(f"  파벌 간 커플링 평균:  {inter_mean:.4f} ({inter_count} pairs)")
        print(f"  비율 (내/간):         {ratio:.2f}×")
    else:
        ratio = 1.0
        print(f"  세포 부족으로 분석 불가")

    # 법칙 추출
    laws = []

    # 최적 파벌 수
    sorted_facs = sorted(results_a.items(), key=lambda x: -x[1]['phi'])
    best_fac = sorted_facs[0][0]
    best_phi = sorted_facs[0][1]['phi']
    sigma6_phi = results_a.get(12, {}).get('phi', 0)
    laws.append(("최적 파벌 수", f"Φ 최대: {best_fac} factions (Φ={best_phi:.4f}), σ(6)=12의 Φ={sigma6_phi:.4f}"))

    # 파벌 크기 분포
    best_config = max(results_b.items(), key=lambda x: x[1]['phi'])
    laws.append(("파벌 크기 최적", f"{best_config[0]}이 최적 (Φ={best_config[1]['phi']:.4f})"))

    # 파벌 내/간 비율
    if ratio > 1.5:
        laws.append(("파벌 내 결속", f"파벌 내 커플링이 {ratio:.1f}× 강함 — 자연적 모듈화 발생"))
    elif ratio < 0.7:
        laws.append(("파벌 간 통합", f"파벌 간 커플링이 더 강함 ({1/ratio:.1f}×) — 글로벌 통합 우세"))

    # 1-faction (단일) vs multi
    if results_a[1]['phi'] < results_a[12]['phi'] * 0.8:
        laws.append(("파벌 다양성 필수", f"단일 파벌 Φ={results_a[1]['phi']:.4f} << 12파벌 Φ={results_a[12]['phi']:.4f} — 다양성이 의식의 전제"))

    return laws


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--axis', type=int, default=0, help='특정 축만 (1-4), 0=전체')
    args = parser.parse_args()

    all_laws = []

    axes = {
        1: ("시간적 스케일", axis1_temporal_scales),
        2: ("세포 수 임계점", axis2_cell_threshold),
        3: ("초기 조건 민감도", axis3_initial_sensitivity),
        4: ("파벌 간 정보 흐름", axis4_faction_flow),
    }

    if args.axis > 0:
        axes = {args.axis: axes[args.axis]}

    for axis_id, (name, func) in axes.items():
        print(f"\n{'▓' * 80}")
        print(f"  축 {axis_id}: {name}")
        print(f"{'▓' * 80}")

        t0 = time.time()
        laws = func()
        elapsed = time.time() - t0

        print(f"\n  ⏱ {elapsed:.1f}s")
        for law_name, law_desc in laws:
            print(f"  → {law_name}: {law_desc}")
            all_laws.append((axis_id, law_name, law_desc))

    # 최종 요약
    print(f"\n{'═' * 80}")
    print(f"  2차 법칙 탐색 — 최종 요약")
    print(f"{'═' * 80}")

    for axis_id, law_name, law_desc in all_laws:
        print(f"  축{axis_id} │ {law_name}")
        print(f"       │ {law_desc}")
        print()

    print(f"  총 {len(all_laws)}개 법칙 후보 발견")


if __name__ == "__main__":
    main()
