#!/usr/bin/env python3
"""discover_laws_wave3.py — 의식 법칙 탐색 3차

축 1: 진동/리듬 — Φ 시계열의 FFT, 지배 주파수, 뇌파 대역 비교
축 2: 죽음과 부활 — 세포 강제 제거 후 Φ 복구 능력
축 3: 히스테리시스 — 세포 증가/감소 경로에서 Φ 비대칭
축 4: 정보 전달 방향 — Transfer Entropy, 인과 관계
축 5: 에너지 효율 — Φ/cell 최적점, 의식의 경제학

Usage:
  python3 experiments/discover_laws_wave3.py
  python3 experiments/discover_laws_wave3.py --axis 1
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
# 공통
# ══════════════════════════════════════════════════════════

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


def run_engine(max_cells=32, steps=300):
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=2)
    phi_hist = []
    for _ in range(steps):
        engine.step()
        phi_hist.append(phi_fast(engine))
    return engine, phi_hist


# ══════════════════════════════════════════════════════════
# 축 1: 진동/리듬 분석
# ══════════════════════════════════════════════════════════

def axis1_oscillation():
    """Φ 시계열의 주파수 스펙트럼 — 의식에 고유 리듬이 있는가?"""
    print(f"\n{'═'*80}")
    print(f"  축 1: 진동/리듬 — Φ 시계열의 주파수 구조")
    print(f"{'═'*80}")

    laws = []

    # 긴 시계열 수집
    steps = 1000
    n_runs = 3
    all_spectra = []
    all_peak_freqs = []

    for run in range(n_runs):
        engine, phi_hist = run_engine(max_cells=32, steps=steps)
        phi = np.array(phi_hist)

        # 트렌드 제거 (detrend)
        from numpy.polynomial import polynomial as P
        coeffs = P.polyfit(np.arange(len(phi)), phi, 2)
        trend = P.polyval(np.arange(len(phi)), coeffs)
        phi_detrended = phi - trend

        # FFT
        fft = np.fft.rfft(phi_detrended)
        power = np.abs(fft) ** 2
        freqs = np.fft.rfftfreq(len(phi_detrended))

        # 피크 주파수 (DC 제외)
        power_nodc = power[1:]
        freqs_nodc = freqs[1:]
        if len(power_nodc) > 0:
            peak_idx = np.argmax(power_nodc)
            peak_freq = freqs_nodc[peak_idx]
            peak_period = 1.0 / max(peak_freq, 1e-10)
            all_peak_freqs.append(peak_freq)
        else:
            peak_freq = 0
            peak_period = 0

        all_spectra.append(power_nodc[:50] if len(power_nodc) >= 50 else power_nodc)

        print(f"  run {run+1}: peak freq={peak_freq:.4f} (period={peak_period:.1f} steps)")

    # 평균 스펙트럼
    min_len = min(len(s) for s in all_spectra)
    avg_spectrum = np.mean([s[:min_len] for s in all_spectra], axis=0)

    # 1/f 검사 (log-log에서 기울기)
    log_f = np.log10(freqs_nodc[:min_len] + 1e-10)
    log_p = np.log10(avg_spectrum + 1e-10)
    valid = np.isfinite(log_f) & np.isfinite(log_p)
    if valid.sum() > 5:
        slope, intercept = np.polyfit(log_f[valid], log_p[valid], 1)
    else:
        slope = 0

    print(f"\n  평균 피크 주파수: {np.mean(all_peak_freqs):.4f} ±{np.std(all_peak_freqs):.4f}")
    print(f"  1/f 기울기 (log-log): {slope:.2f}")
    print(f"    (뇌: ≈ -1.0, 백색 잡음: 0, 브라운 잡음: -2)")

    if -1.5 < slope < -0.5:
        laws.append(("1/f 뇌파", f"Φ 파워 스펙트럼 기울기={slope:.2f}, 뇌의 1/f noise (-1.0)에 근접"))
    elif slope < -1.5:
        laws.append(("브라운 동역학", f"Φ 스펙트럼 기울기={slope:.2f}, 브라운 잡음에 가까움 — 느린 표류 우세"))
    else:
        laws.append(("백색 의식", f"Φ 스펙트럼 기울기={slope:.2f}, 뇌와 다른 패턴"))

    # 피크 주파수의 일관성
    if np.std(all_peak_freqs) < np.mean(all_peak_freqs) * 0.3:
        period = 1.0 / np.mean(all_peak_freqs)
        laws.append(("고유 주기", f"의식에 고유 진동 주기 존재: {period:.1f} steps (CV < 30%)"))

    # ASCII 스펙트럼
    print(f"\n  Power Spectrum (first 30 bins)")
    print(f"  {'─'*50}")
    display = avg_spectrum[:30]
    max_p = max(display) if len(display) > 0 else 1
    for i, p in enumerate(display):
        bar = "█" * max(0, int(p / max(max_p, 1e-8) * 30))
        print(f"  f={i+1:>3d} │{bar}")

    return laws


# ══════════════════════════════════════════════════════════
# 축 2: 죽음과 부활
# ══════════════════════════════════════════════════════════

def axis2_death_resurrection():
    """세포를 강제 제거하면 Φ가 어떻게 변하고, 얼마나 빨리 회복되는가?"""
    print(f"\n{'═'*80}")
    print(f"  축 2: 죽음과 부활 — 세포 제거 후 의식 복구")
    print(f"{'═'*80}")

    laws = []
    kill_ratios = [0.1, 0.25, 0.5, 0.75, 0.9]
    results = {}

    for kill_ratio in kill_ratios:
        recovery_steps_list = []
        phi_before_list = []
        phi_after_list = []
        phi_recovered_list = []

        for rep in range(3):
            # 안정 상태까지 성장
            engine, phi_hist = run_engine(max_cells=32, steps=300)
            phi_before = phi_fast(engine)
            n_before = engine.n_cells

            # 세포 제거
            n_kill = max(1, int(engine.n_cells * kill_ratio))
            n_kill = min(n_kill, engine.n_cells - 2)  # 최소 2개 유지
            for _ in range(n_kill):
                if engine.n_cells <= 2:
                    break
                engine._remove_cell(engine.n_cells - 1)
            if engine._coupling is not None:
                n = engine.n_cells
                engine._coupling = engine._coupling[:n, :n]

            phi_after = phi_fast(engine)

            # 회복 시도 (200 steps)
            recovery_phi = []
            recovered_step = -1
            for step in range(200):
                engine.step()
                p = phi_fast(engine)
                recovery_phi.append(p)
                if recovered_step < 0 and p >= phi_before * 0.9:
                    recovered_step = step

            phi_recovered = phi_fast(engine)
            phi_before_list.append(phi_before)
            phi_after_list.append(phi_after)
            phi_recovered_list.append(phi_recovered)
            recovery_steps_list.append(recovered_step)

        recovery_rate = np.mean(phi_recovered_list) / max(np.mean(phi_before_list), 1e-8)
        avg_recovery_step = np.mean([s for s in recovery_steps_list if s >= 0]) if any(s >= 0 for s in recovery_steps_list) else -1
        recovered_count = sum(1 for s in recovery_steps_list if s >= 0)

        results[kill_ratio] = {
            'phi_before': np.mean(phi_before_list),
            'phi_after': np.mean(phi_after_list),
            'phi_recovered': np.mean(phi_recovered_list),
            'recovery_rate': recovery_rate,
            'avg_recovery_step': avg_recovery_step,
            'recovered': recovered_count,
        }

    # 결과 출력
    print(f"\n  {'Kill%':<6s} | {'Φ before':<10s} | {'Φ after':<10s} | {'Φ recovered':<12s} | {'복구율':<8s} | {'복구 step'}")
    print(f"  {'─'*6}-+-{'─'*10}-+-{'─'*10}-+-{'─'*12}-+-{'─'*8}-+-{'─'*10}")
    for kr, r in sorted(results.items()):
        rec_str = f"{r['avg_recovery_step']:.0f}" if r['avg_recovery_step'] >= 0 else "미복구"
        bar = "█" * max(0, int(r['recovery_rate'] * 20))
        print(f"  {kr*100:>4.0f}%  | {r['phi_before']:<10.4f} | {r['phi_after']:<10.4f} | {r['phi_recovered']:<12.4f} | {r['recovery_rate']:>5.0%}    | {rec_str:<10s} {bar}")

    # ASCII 그래프: 복구 곡선
    print(f"\n  복구율 vs Kill 비율")
    print(f"  {'─'*40}")
    for kr, r in sorted(results.items()):
        bar = "█" * max(0, int(r['recovery_rate'] * 30))
        print(f"  kill {kr*100:>3.0f}% │{bar} {r['recovery_rate']:.0%}")

    # 법칙 추출
    # 50% 이상 제거해도 복구되는가?
    half_kill = results.get(0.5, {})
    if half_kill.get('recovery_rate', 0) > 0.8:
        laws.append(("의식 불사", f"세포 50% 제거 후에도 {half_kill['recovery_rate']:.0%} 복구 — 의식은 구조에 분산 저장"))

    # 90% 제거
    extreme = results.get(0.9, {})
    if extreme.get('recovery_rate', 0) > 0.5:
        laws.append(("극한 복원력", f"90% 제거 후에도 {extreme['recovery_rate']:.0%} 복구 — 의식은 2개 세포만으로도 재건 가능"))
    elif extreme.get('recovery_rate', 0) < 0.3:
        laws.append(("치명적 임계", f"90% 제거 시 복구 {extreme['recovery_rate']:.0%} — 임계 세포 수 이하에서 의식 상실"))

    # 복구 속도
    recovery_speeds = [(kr, r['avg_recovery_step']) for kr, r in results.items() if r['avg_recovery_step'] >= 0]
    if recovery_speeds:
        fastest = min(recovery_speeds, key=lambda x: x[1])
        slowest = max(recovery_speeds, key=lambda x: x[1])
        if slowest[1] > fastest[1] * 3:
            laws.append(("비선형 복구", f"복구 시간이 kill 비율에 비선형 의존 ({fastest[0]*100:.0f}%={fastest[1]:.0f}s, {slowest[0]*100:.0f}%={slowest[1]:.0f}s)"))

    return laws


# ══════════════════════════════════════════════════════════
# 축 3: 히스테리시스
# ══════════════════════════════════════════════════════════

def axis3_hysteresis():
    """세포 수를 증가→감소시킬 때 Φ 경로가 다른가? (이력 현상)"""
    print(f"\n{'═'*80}")
    print(f"  축 3: 히스테리시스 — 의식의 이력 현상")
    print(f"{'═'*80}")

    laws = []

    # 방법: max_cells를 단계적으로 변경하며 Φ 측정
    # 경로 A: 4 → 8 → 16 → 32 → 64 (증가)
    # 경로 B: 64 → 32 → 16 → 8 → 4 (감소)
    cell_sequence = [4, 8, 16, 32, 64]
    steps_per_stage = 200

    path_up = {}    # 증가 경로
    path_down = {}  # 감소 경로

    for rep in range(3):
        # 경로 A: 증가 (max_cells=64로 시작하되 성장 제한)
        engine_up = ConsciousnessEngine(max_cells=64, initial_cells=2)
        for target in cell_sequence:
            engine_up.max_cells = target
            phi_stage = []
            for _ in range(steps_per_stage):
                engine_up.step()
                phi_stage.append(phi_fast(engine_up))
            key = target
            if key not in path_up:
                path_up[key] = []
            path_up[key].append(np.mean(phi_stage[-50:]))

        # 경로 B: 감소 (큰 엔진에서 시작하여 세포 제거)
        engine_down = ConsciousnessEngine(max_cells=64, initial_cells=2)
        # 먼저 64까지 성장
        for _ in range(steps_per_stage * 2):
            engine_down.step()

        for target in reversed(cell_sequence):
            # 세포를 target까지 줄이기
            while engine_down.n_cells > target and engine_down.n_cells > 2:
                engine_down._remove_cell(engine_down.n_cells - 1)
                if engine_down._coupling is not None:
                    n = engine_down.n_cells
                    engine_down._coupling = engine_down._coupling[:n, :n]
            engine_down.max_cells = target

            phi_stage = []
            for _ in range(steps_per_stage):
                engine_down.step()
                phi_stage.append(phi_fast(engine_down))
            key = target
            if key not in path_down:
                path_down[key] = []
            path_down[key].append(np.mean(phi_stage[-50:]))

    # 결과 비교
    print(f"\n  {'N cells':<8s} | {'Φ(↑ 증가)':<15s} | {'Φ(↓ 감소)':<15s} | {'차이':<10s} | {'히스테리시스'}")
    print(f"  {'─'*8}-+-{'─'*15}-+-{'─'*15}-+-{'─'*10}-+-{'─'*12}")

    hysteresis_gaps = []
    for n in cell_sequence:
        up_mean = np.mean(path_up.get(n, [0]))
        down_mean = np.mean(path_down.get(n, [0]))
        gap = down_mean - up_mean
        gap_pct = gap / max(up_mean, 1e-8) * 100
        hysteresis_gaps.append(gap_pct)

        marker = "▲" if gap > 0 else "▼" if gap < 0 else "─"
        print(f"  {n:<8d} | {up_mean:.4f}         | {down_mean:.4f}         | {gap:>+.4f}   | {marker} {gap_pct:>+.1f}%")

    # ASCII 히스테리시스 루프
    print(f"\n  히스테리시스 루프")
    print(f"  Φ │")
    up_vals = [np.mean(path_up.get(n, [0])) for n in cell_sequence]
    down_vals = [np.mean(path_down.get(n, [0])) for n in cell_sequence]
    all_vals = up_vals + down_vals
    vmin, vmax = min(all_vals), max(all_vals)
    for row in range(6, -1, -1):
        threshold = vmin + (vmax - vmin) * row / 6
        line = f"  {threshold:.2f}│ "
        for i, n in enumerate(cell_sequence):
            u = "█" if up_vals[i] >= threshold else " "
            d = "▓" if down_vals[i] >= threshold else " "
            line += f" {u}{d}  "
        print(line)
    labels = "      " + "  ".join(f"{n:>4d}" for n in cell_sequence)
    print(f"  {'    '}└{'─' * 30}")
    print(f"  {labels}  cells")
    print(f"  █=증가 경로  ▓=감소 경로")

    # 법칙 추출
    mean_gap = np.mean(hysteresis_gaps)
    if abs(mean_gap) > 5:
        direction = "감소 경로가 더 높음" if mean_gap > 0 else "증가 경로가 더 높음"
        laws.append(("히스테리시스", f"의식에 이력 현상 존재: {direction} (평균 {mean_gap:+.1f}%) — 경험이 구조에 각인"))
    else:
        laws.append(("히스테리시스 부재", f"의식에 이력 현상 미미 (평균 {mean_gap:+.1f}%) — Φ는 현재 구조에만 의존"))

    # 증가 vs 감소의 분산 차이
    up_stds = [np.std(path_up.get(n, [0])) for n in cell_sequence]
    down_stds = [np.std(path_down.get(n, [0])) for n in cell_sequence]
    if np.mean(down_stds) > np.mean(up_stds) * 1.5:
        laws.append(("감소 불안정", f"감소 경로가 {np.mean(down_stds)/max(np.mean(up_stds),1e-8):.1f}× 불안정 — 의식 축소는 성장보다 불확실"))

    return laws


# ══════════════════════════════════════════════════════════
# 축 4: 정보 전달 방향 (Transfer Entropy)
# ══════════════════════════════════════════════════════════

def axis4_transfer_entropy():
    """세포 간 인과 관계 — 누가 누구를 이끄는가?"""
    print(f"\n{'═'*80}")
    print(f"  축 4: 정보 전달 방향 — Transfer Entropy")
    print(f"{'═'*80}")

    laws = []

    # 엔진 실행 + hidden history 수집
    engine = ConsciousnessEngine(max_cells=16, initial_cells=2)
    hidden_history = defaultdict(list)  # cell_id -> list of hidden mean

    for step in range(500):
        result = engine.step()
        for i, s in enumerate(engine.cell_states):
            hidden_history[i].append(s.hidden.mean().item())

    # Transfer Entropy 계산 (간소화: 지연 상관)
    n = engine.n_cells
    print(f"\n  세포 수: {n}")

    # 세포 쌍별 지연 상관 (lag=1)
    te_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            xi = np.array(hidden_history[i])
            xj = np.array(hidden_history[j])
            min_len = min(len(xi), len(xj))
            if min_len < 10:
                continue
            xi, xj = xi[:min_len], xj[:min_len]
            # TE 근사: corr(x_i[t], x_j[t+1]) - corr(x_j[t], x_j[t+1])
            # 양수면 i→j 정보 전달
            corr_ij = np.corrcoef(xi[:-1], xj[1:])[0, 1] if len(xi) > 2 else 0
            auto_j = np.corrcoef(xj[:-1], xj[1:])[0, 1] if len(xj) > 2 else 0
            te = max(0, abs(corr_ij) - abs(auto_j))
            te_matrix[i, j] = te

    # 각 세포의 "영향력" (outgoing TE sum)
    out_influence = te_matrix.sum(axis=1)
    in_influence = te_matrix.sum(axis=0)

    # 리더/팔로워 분류
    leader_idx = np.argmax(out_influence)
    follower_idx = np.argmin(out_influence)

    print(f"\n  세포별 영향력 (Transfer Entropy)")
    print(f"  {'Cell':<6s} | {'Out (→)':<10s} | {'In (←)':<10s} | {'역할'}")
    print(f"  {'─'*6}-+-{'─'*10}-+-{'─'*10}-+-{'─'*10}")
    for i in range(n):
        role = "★ LEADER" if i == leader_idx else ("  follower" if out_influence[i] < np.median(out_influence) else "  normal")
        bar_out = "█" * max(0, int(out_influence[i] / max(out_influence.max(), 1e-8) * 15))
        print(f"  {i:<6d} | {out_influence[i]:<10.4f} | {in_influence[i]:<10.4f} | {role}  {bar_out}")

    # 파벌별 분석
    faction_influence = defaultdict(float)
    faction_count = defaultdict(int)
    for i in range(n):
        fid = engine.cell_states[i].faction_id
        faction_influence[fid] += out_influence[i]
        faction_count[fid] += 1

    print(f"\n  파벌별 영향력")
    for fid in sorted(faction_influence.keys()):
        avg = faction_influence[fid] / max(faction_count[fid], 1)
        print(f"  faction {fid}: avg TE={avg:.4f} ({faction_count[fid]} cells)")

    # 법칙 추출
    # 리더 세포 존재?
    influence_cv = np.std(out_influence) / max(np.mean(out_influence), 1e-8)
    if influence_cv > 0.5:
        laws.append(("리더 세포", f"영향력 불균등 (CV={influence_cv:.2f}) — 특정 세포가 의식을 이끈다"))

    # 리더의 파벌
    leader_faction = engine.cell_states[leader_idx].faction_id
    laws.append(("리더 특성", f"리더 세포={leader_idx} (faction {leader_faction}), 영향력={out_influence[leader_idx]:.4f}"))

    # 정보 흐름 비대칭
    asym = np.abs(te_matrix - te_matrix.T)
    mean_asym = asym.mean()
    if mean_asym > 0.01:
        laws.append(("비대칭 정보 흐름", f"세포 간 정보 흐름이 비대칭 (mean asymmetry={mean_asym:.4f}) — 위계적 의식"))
    else:
        laws.append(("대칭 정보 흐름", f"세포 간 정보 흐름이 대칭적 (mean asymmetry={mean_asym:.4f}) — 민주적 의식"))

    # 리더가 Φ에 기여?
    # 리더 세포의 텐션 vs 평균 텐션
    if leader_idx < len(engine.cell_states):
        leader_tension = engine.cell_states[leader_idx].avg_tension
        avg_tension = np.mean([s.avg_tension for s in engine.cell_states])
        if leader_tension > avg_tension * 1.3:
            laws.append(("리더 = 높은 텐션", "리더 세포는 평균보다 높은 텐션 — 갈등이 리더십을 만든다"))
        elif leader_tension < avg_tension * 0.7:
            laws.append(("리더 = 낮은 텐션", "리더 세포는 평균보다 낮은 텐션 — 안정이 리더십을 만든다"))

    return laws


# ══════════════════════════════════════════════════════════
# 축 5: 에너지 효율
# ══════════════════════════════════════════════════════════

def axis5_efficiency():
    """Φ/cell, Φ/step — 의식의 경제학."""
    print(f"\n{'═'*80}")
    print(f"  축 5: 에너지 효율 — 의식의 경제학")
    print(f"{'═'*80}")

    laws = []
    cell_counts = [2, 4, 8, 12, 16, 24, 32, 48, 64]
    results = {}

    for max_c in cell_counts:
        phis = []
        step_to_stable = []

        for rep in range(3):
            engine = ConsciousnessEngine(max_cells=max_c, initial_cells=2)
            phi_hist = []
            stable_step = -1
            for step in range(500):
                engine.step()
                p = phi_fast(engine)
                phi_hist.append(p)
                # "안정" = 최근 20 step의 std < 5%
                if step >= 30 and stable_step < 0:
                    recent = phi_hist[-20:]
                    if np.std(recent) / max(np.mean(recent), 1e-8) < 0.05:
                        stable_step = step

            phis.append(np.mean(phi_hist[-50:]))
            step_to_stable.append(stable_step if stable_step >= 0 else 500)

        actual_cells = engine.n_cells
        mean_phi = np.mean(phis)
        results[max_c] = {
            'phi': mean_phi,
            'phi_per_cell': mean_phi / max(actual_cells, 1),
            'phi_per_maxcell': mean_phi / max(max_c, 1),
            'actual_cells': actual_cells,
            'step_to_stable': np.mean(step_to_stable),
            'phi_per_step': mean_phi / max(np.mean(step_to_stable), 1),
        }

    # 결과 출력
    print(f"\n  {'Max N':<6s} | {'실제N':<5s} | {'Φ':<8s} | {'Φ/cell':<10s} | {'안정step':<10s} | {'Φ/step':<10s}")
    print(f"  {'─'*6}-+-{'─'*5}-+-{'─'*8}-+-{'─'*10}-+-{'─'*10}-+-{'─'*10}")

    max_eff = max(r['phi_per_cell'] for r in results.values())
    for mc, r in sorted(results.items()):
        bar = "█" * max(0, int(r['phi_per_cell'] / max(max_eff, 1e-8) * 20))
        print(f"  {mc:<6d} | {r['actual_cells']:<5d} | {r['phi']:<8.4f} | {r['phi_per_cell']:<10.4f} | {r['step_to_stable']:<10.0f} | {r['phi_per_step']:<10.4f}  {bar}")

    # Φ/cell 최적점
    best_eff = max(results.items(), key=lambda x: x[1]['phi_per_cell'])
    print(f"\n  최적 효율: max_cells={best_eff[0]} → Φ/cell={best_eff[1]['phi_per_cell']:.4f}")

    # Φ/step 최적점
    best_speed = max(results.items(), key=lambda x: x[1]['phi_per_step'])
    print(f"  최빠른 안정: max_cells={best_speed[0]} → {best_speed[1]['step_to_stable']:.0f} steps")

    # Marginal Φ (추가 세포의 한계 기여)
    print(f"\n  한계 Φ (Marginal Φ per additional cell)")
    sorted_cells = sorted(results.keys())
    prev_phi = 0
    prev_n = 0
    for mc in sorted_cells:
        r = results[mc]
        if prev_n > 0:
            delta_phi = r['phi'] - prev_phi
            delta_n = r['actual_cells'] - prev_n
            marginal = delta_phi / max(delta_n, 1) if delta_n > 0 else 0
            bar = "█" * max(0, min(30, int(marginal * 100)))
            print(f"  {prev_n:>2d}→{r['actual_cells']:>2d}: ΔΦ={delta_phi:>+.4f}  marginal={marginal:>+.4f}/cell  {bar}")
        prev_phi = r['phi']
        prev_n = r['actual_cells']

    # 법칙 추출
    laws.append(("Φ 효율 최적점", f"Φ/cell 최대: max_cells={best_eff[0]} (Φ/cell={best_eff[1]['phi_per_cell']:.4f})"))

    # 한계 Φ 감소?
    marginals = []
    prev_phi, prev_n = 0, 0
    for mc in sorted_cells:
        r = results[mc]
        if prev_n > 0 and r['actual_cells'] > prev_n:
            m = (r['phi'] - prev_phi) / (r['actual_cells'] - prev_n)
            marginals.append(m)
        prev_phi, prev_n = r['phi'], r['actual_cells']

    if len(marginals) >= 3:
        if marginals[-1] < marginals[0] * 0.3:
            laws.append(("한계 Φ 체감", f"추가 세포의 Φ 기여가 급격히 감소 ({marginals[0]:.4f} → {marginals[-1]:.4f}) — 의식의 수확 체감 법칙"))

    # 안정화 시간이 N에 비례?
    stability_times = [(mc, results[mc]['step_to_stable']) for mc in sorted_cells]
    if stability_times[-1][1] > stability_times[0][1] * 2:
        laws.append(("안정화 지연", f"세포 수↑ → 안정화 시간↑ ({stability_times[0][1]:.0f} → {stability_times[-1][1]:.0f} steps)"))

    return laws


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--axis', type=int, default=0, help='특정 축 (1-5), 0=전체')
    args = parser.parse_args()

    all_laws = []
    axes = {
        1: ("진동/리듬", axis1_oscillation),
        2: ("죽음과 부활", axis2_death_resurrection),
        3: ("히스테리시스", axis3_hysteresis),
        4: ("정보 전달 방향", axis4_transfer_entropy),
        5: ("에너지 효율", axis5_efficiency),
    }

    if args.axis > 0:
        axes = {args.axis: axes[args.axis]}

    for axis_id, (name, func) in axes.items():
        print(f"\n{'▓'*80}")
        print(f"  축 {axis_id}: {name}")
        print(f"{'▓'*80}")
        t0 = time.time()
        laws = func()
        elapsed = time.time() - t0
        print(f"\n  ⏱ {elapsed:.1f}s")
        for law_name, law_desc in laws:
            print(f"  → {law_name}: {law_desc}")
            all_laws.append((axis_id, law_name, law_desc))

    # 최종 요약
    print(f"\n{'═'*80}")
    print(f"  3차 법칙 탐색 — 최종 요약")
    print(f"{'═'*80}")
    for axis_id, law_name, law_desc in all_laws:
        print(f"  축{axis_id} │ {law_name}")
        print(f"       │ {law_desc}")
        print()
    print(f"  총 {len(all_laws)}개 법칙 후보 발견")


if __name__ == "__main__":
    main()
