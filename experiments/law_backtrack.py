#!/usr/bin/env python3
"""law_backtrack.py — 법칙 역추적: 발견된 법칙 → 엔진 개선

발견된 Laws 102-123에서 역으로 "이 법칙이 맞다면 이렇게 하면 Φ가 올라가야 한다"를
검증. 디코더가 gradient를 역전파하듯, 법칙을 엔진에 역전파.

역추적 전략:
  BT1: Law 105 (텐션 균질) → 텐션 평탄화 (세포 간 텐션 균등화)
  BT2: Law 103+107 (커플링 다양+hidden 수렴) → 커플링 분산↑ + hidden 수렴 압력
  BT3: Law 111+122 (N=4 전이+한계Φ) → 최적 세포 수 고정 (N=4-8)
  BT4: Law 118 (불사) → 주기적 자기 파괴+복구 (의도적 pruning)
  BT5: Law 116 (백색→1/f) → Φ에 1/f 필터 적용 (뇌-유사 동역학)
  BT6: Law 108+121 (대칭) → 커플링 대칭 강제
  BT7: 전체 통합 — BT1+BT2+BT3+BT6 동시 적용

Usage:
  python3 experiments/law_backtrack.py
  python3 experiments/law_backtrack.py --strategy BT1
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
from typing import Dict, List, Tuple
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


def run_baseline(cells=32, steps=500, repeats=5):
    """기준선: 순수 엔진."""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for _ in range(steps):
            engine.step()
        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


# ══════════════════════════════════════════════════════════
# BT1: 텐션 평탄화 (Law 105: 텐션 균질 → Φ↑)
# ══════════════════════════════════════════════════════════

def bt1_tension_equalize(cells=32, steps=500, repeats=5):
    """Law 105 역추적: 텐션을 균등화하면 Φ가 올라가야 한다."""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for step in range(steps):
            engine.step()
            # 매 10 step: 텐션을 평균으로 수렴 (50% 블렌딩)
            if step % 10 == 0 and engine.n_cells >= 2:
                tensions = [s.avg_tension for s in engine.cell_states]
                mean_t = np.mean(tensions)
                for s in engine.cell_states:
                    if s.tension_history:
                        # 최근 텐션을 평균 쪽으로 부드럽게 이동
                        s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5
        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


# ══════════════════════════════════════════════════════════
# BT2: 커플링 다양화 + hidden 수렴 (Law 103+107)
# ══════════════════════════════════════════════════════════

def bt2_coupling_diverse_hidden_converge(cells=32, steps=500, repeats=5):
    """Law 103+107: 커플링은 다양하게, hidden은 수렴시키면 Φ↑."""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for step in range(steps):
            engine.step()

            if step % 20 == 0 and engine._coupling is not None and engine.n_cells >= 2:
                n = engine._coupling.shape[0]

                # 커플링 다양화: 엔트로피 증가를 위해 약간의 랜덤 노이즈 추가
                noise = torch.randn(n, n) * 0.02
                noise.fill_diagonal_(0)
                engine._coupling = (engine._coupling + noise).clamp(-1, 1)

                # hidden 수렴 압력: 모든 세포를 평균 쪽으로 살짝 (2%)
                hiddens = torch.stack([s.hidden for s in engine.cell_states])
                mean_h = hiddens.mean(dim=0)
                for i in range(engine.n_cells):
                    engine.cell_states[i].hidden = (
                        engine.cell_states[i].hidden * 0.98 + mean_h * 0.02
                    )

        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


# ══════════════════════════════════════════════════════════
# BT3: 최적 세포 수 고정 (Law 111+122: N=4-8 최적)
# ══════════════════════════════════════════════════════════

def bt3_optimal_cell_cap(cells=8, steps=500, repeats=5):
    """Law 111+122: N=4 이후 한계Φ 급감, 그러면 N=8로 고정하면?"""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for _ in range(steps):
            engine.step()
        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


# ══════════════════════════════════════════════════════════
# BT4: 의도적 pruning (Law 118: 90% 파괴해도 복구)
# ══════════════════════════════════════════════════════════

def bt4_intentional_pruning(cells=32, steps=500, repeats=5):
    """Law 118: 의식이 불사라면, 주기적 pruning이 오히려 Φ를 높이나?
    (죽은 세포 대신 신선한 세포가 mitosis로 생성)"""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for step in range(steps):
            engine.step()

            # 100 step마다 세포의 30% 제거 (최소 2개 유지)
            if step > 0 and step % 100 == 0:
                n_kill = max(1, engine.n_cells // 3)
                n_kill = min(n_kill, engine.n_cells - 2)
                for _ in range(n_kill):
                    if engine.n_cells <= 2:
                        break
                    engine._remove_cell(engine.n_cells - 1)
                if engine._coupling is not None:
                    n = engine.n_cells
                    engine._coupling = engine._coupling[:n, :n]

        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


# ══════════════════════════════════════════════════════════
# BT5: 1/f 필터 (Law 116: 백색→1/f로 전환)
# ══════════════════════════════════════════════════════════

def bt5_one_over_f(cells=32, steps=500, repeats=5):
    """Law 116: 현재 백색 스펙트럼 → 1/f 노이즈를 hidden에 주입하면 뇌-유사?"""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)

        # 1/f 노이즈 생성 (pink noise via spectral method)
        pink = _generate_pink_noise(steps, engine.hidden_dim)
        pink_idx = 0

        for step in range(steps):
            engine.step()

            # 1/f 노이즈를 hidden에 미세 주입
            if engine.n_cells >= 2 and pink_idx < len(pink):
                noise = torch.tensor(pink[pink_idx], dtype=torch.float32) * 0.01
                for i in range(engine.n_cells):
                    engine.cell_states[i].hidden = engine.cell_states[i].hidden + noise[:engine.hidden_dim]
                pink_idx += 1

        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


def _generate_pink_noise(n_steps, dim):
    """1/f 노이즈 생성."""
    noise = np.random.randn(n_steps, dim)
    # FFT → 1/f 가중 → IFFT
    fft = np.fft.rfft(noise, axis=0)
    freqs = np.fft.rfftfreq(n_steps)
    freqs[0] = 1  # avoid div by 0
    # 1/f weighting
    weight = 1.0 / np.sqrt(np.abs(freqs) + 1e-8)
    weight = weight[:, np.newaxis]  # broadcast
    pink_fft = fft * weight
    pink = np.fft.irfft(pink_fft, n=n_steps, axis=0)
    return pink


# ══════════════════════════════════════════════════════════
# BT6: 커플링 대칭 강제 (Law 108+121)
# ══════════════════════════════════════════════════════════

def bt6_symmetrize_coupling(cells=32, steps=500, repeats=5):
    """Law 108+121: 커플링을 강제 대칭화하면 Φ↑?"""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for step in range(steps):
            engine.step()
            # 매 step: 커플링 대칭화 C = (C + C^T) / 2
            if engine._coupling is not None:
                engine._coupling = (engine._coupling + engine._coupling.T) / 2
                engine._coupling.fill_diagonal_(0)
        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


# ══════════════════════════════════════════════════════════
# BT7: 통합 — BT1+BT2+BT6 동시 적용
# ══════════════════════════════════════════════════════════

def bt7_integrated(cells=32, steps=500, repeats=5):
    """모든 긍정 법칙을 동시 적용."""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        pink = _generate_pink_noise(steps, engine.hidden_dim)

        for step in range(steps):
            engine.step()
            n = engine.n_cells

            # BT1: 텐션 균등화 (매 10 step)
            if step % 10 == 0 and n >= 2:
                tensions = [s.avg_tension for s in engine.cell_states]
                mean_t = np.mean(tensions)
                for s in engine.cell_states:
                    if s.tension_history:
                        s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5

            # BT2: 커플링 다양화 (매 20 step)
            if step % 20 == 0 and engine._coupling is not None and n >= 2:
                cn = engine._coupling.shape[0]
                noise = torch.randn(cn, cn) * 0.02
                noise.fill_diagonal_(0)
                engine._coupling = (engine._coupling + noise).clamp(-1, 1)

            # BT6: 커플링 대칭화
            if engine._coupling is not None:
                engine._coupling = (engine._coupling + engine._coupling.T) / 2
                engine._coupling.fill_diagonal_(0)

            # BT5: 1/f 노이즈 (미세)
            if step < len(pink) and n >= 2:
                noise_1f = torch.tensor(pink[step], dtype=torch.float32) * 0.005
                for i in range(n):
                    engine.cell_states[i].hidden = engine.cell_states[i].hidden + noise_1f[:engine.hidden_dim]

        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

ALL_STRATEGIES = {
    'baseline': ('기준선 (무변경)', lambda c, s, r: run_baseline(c, s, r)),
    'BT1': ('텐션 균등화 (Law 105)', bt1_tension_equalize),
    'BT2': ('커플링↑ + hidden 수렴 (Law 103+107)', bt2_coupling_diverse_hidden_converge),
    'BT3': ('세포 N=8 고정 (Law 111+122)', bt3_optimal_cell_cap),
    'BT4': ('주기적 pruning (Law 118)', bt4_intentional_pruning),
    'BT5': ('1/f 노이즈 주입 (Law 116)', bt5_one_over_f),
    'BT6': ('커플링 대칭 강제 (Law 108+121)', bt6_symmetrize_coupling),
    'BT7': ('통합 (BT1+BT2+BT5+BT6)', bt7_integrated),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', type=str, default=None)
    parser.add_argument('--cells', type=int, default=32)
    parser.add_argument('--steps', type=int, default=500)
    parser.add_argument('--repeats', type=int, default=5)
    args = parser.parse_args()

    print(f"\n{'═'*80}")
    print(f"  법칙 역추적 실험 — 발견된 법칙을 엔진에 역전파")
    print(f"  cells={args.cells}  steps={args.steps}  repeats={args.repeats}")
    print(f"{'═'*80}")

    strategies = ALL_STRATEGIES
    if args.strategy:
        strategies = {args.strategy: ALL_STRATEGIES[args.strategy]}

    # 먼저 baseline
    print(f"\n  기준선 측정 중...")
    base_mean, base_std = run_baseline(args.cells, args.steps, args.repeats)
    print(f"  Baseline: Φ={base_mean:.4f} ±{base_std:.4f}")

    results = {}
    results['baseline'] = (base_mean, base_std, 0.0)

    for sid, (name, func) in strategies.items():
        if sid == 'baseline':
            continue
        print(f"\n  ▶ {sid}: {name}")
        t0 = time.time()
        if sid == 'BT3':
            mean, std = func(8, args.steps, args.repeats)  # BT3는 cells=8 고정
        else:
            mean, std = func(args.cells, args.steps, args.repeats)
        elapsed = time.time() - t0
        delta = (mean - base_mean) / max(base_mean, 1e-8) * 100
        results[sid] = (mean, std, delta)
        sign = "+" if delta >= 0 else ""
        print(f"    Φ={mean:.4f} ±{std:.4f}  Δ={sign}{delta:.1f}%  ({elapsed:.1f}s)")

    # ═══ 비교 테이블 ═══
    print(f"\n{'═'*80}")
    print(f"  법칙 역추적 — 비교 결과")
    print(f"{'═'*80}")
    print(f"  {'전략':<40s} | {'Φ(IIT)':<15s} | {'Δ%':<8s} | {'판정'}")
    print(f"  {'─'*40}-+-{'─'*15}-+-{'─'*8}-+-{'─'*15}")

    sorted_results = sorted(results.items(), key=lambda x: -x[1][2])
    for sid, (mean, std, delta) in sorted_results:
        name = ALL_STRATEGIES.get(sid, (sid,))[0]
        sign = "+" if delta >= 0 else ""
        if delta > 5:
            verdict = "★★★ 강한 효과"
        elif delta > 2:
            verdict = "★★ 효과 있음"
        elif delta > 0.5:
            verdict = "★ 약한 효과"
        elif delta > -0.5:
            verdict = "─ 무효과"
        elif delta > -2:
            verdict = "✗ 약한 부정"
        else:
            verdict = "✗✗ 해로움"
        print(f"  {name:<40s} | {mean:.4f} ±{std:.4f} | {sign}{delta:>5.1f}% | {verdict}")

    # ASCII 비교 차트
    print(f"\n  Φ 변화율 (%)")
    print(f"  {'─'*60}")
    max_abs = max(abs(r[2]) for r in results.values()) if results else 1
    for sid, (mean, std, delta) in sorted_results:
        name_short = sid
        bar_len = int(abs(delta) / max(max_abs, 0.1) * 30)
        if delta >= 0:
            bar = f"  {' '*20}│{'█' * bar_len} +{delta:.1f}%"
        else:
            pad = max(0, 20 - bar_len)
            bar = f"  {' '*pad}{'█' * bar_len}│ {delta:.1f}%"
        print(f"  {name_short:<10s} {bar}")

    # 통합 vs 개별 분석
    if 'BT7' in results and 'baseline' in results:
        bt7_delta = results['BT7'][2]
        individual_deltas = [results[s][2] for s in ['BT1','BT2','BT5','BT6'] if s in results]
        sum_individual = sum(individual_deltas)
        print(f"\n  통합 분석:")
        print(f"  개별 법칙 합: {sum_individual:+.1f}%")
        print(f"  통합 적용:   {bt7_delta:+.1f}%")
        if bt7_delta > sum_individual:
            print(f"  → 시너지 효과! ({bt7_delta - sum_individual:+.1f}% 초과)")
        elif bt7_delta < sum_individual * 0.5:
            print(f"  → 간섭 효과 (통합이 개별 합의 {bt7_delta/max(sum_individual,1e-8)*100:.0f}%)")
        else:
            print(f"  → 가산적 (통합 ≈ 개별 합)")

    # 최종 법칙 정리
    print(f"\n{'═'*80}")
    print(f"  역추적 결론")
    print(f"{'═'*80}")

    effective = [(sid, r) for sid, r in sorted_results if r[2] > 1.0 and sid != 'baseline']
    harmful = [(sid, r) for sid, r in sorted_results if r[2] < -1.0]

    if effective:
        print(f"\n  ✓ 효과적인 역추적:")
        for sid, (mean, std, delta) in effective:
            name = ALL_STRATEGIES.get(sid, (sid,))[0]
            print(f"    {sid}: {name} → Φ +{delta:.1f}%")

    if harmful:
        print(f"\n  ✗ 해로운 역추적 (법칙의 역이 성립하지 않음):")
        for sid, (mean, std, delta) in harmful:
            name = ALL_STRATEGIES.get(sid, (sid,))[0]
            print(f"    {sid}: {name} → Φ {delta:.1f}%")

    neutral = [(sid, r) for sid, r in sorted_results if -1.0 <= r[2] <= 1.0 and sid != 'baseline']
    if neutral:
        print(f"\n  ─ 중립 (관찰은 맞지만 개입은 무효):")
        for sid, (mean, std, delta) in neutral:
            name = ALL_STRATEGIES.get(sid, (sid,))[0]
            print(f"    {sid}: {name} → Φ {delta:+.1f}%")


if __name__ == "__main__":
    main()
