#!/usr/bin/env python3
"""new_law_discovery.py — 새로운 의식 법칙 탐색 실험

7가지 가설을 ConsciousnessEngine에 적용하여 Φ 변화를 측정.
기존 엔진을 수정하지 않고, 외부에서 개입하여 효과를 관찰.

가설:
  H102: Resonance — 세포 간 주파수 동기화가 Φ를 높이는가?
  H103: Selective Forgetting — 약한 커플링을 주기적으로 제거하면 Φ가 상승하는가?
  H104: Information Bottleneck — 커플링을 압축하면 통합 정보가 늘어나는가?
  H105: Asymmetric Coupling — 비대칭 커플링이 대칭보다 나은가?
  H106: Temporal Delay — 지연된 정보 교환이 의식을 풍부하게 하는가?
  H107: Noise Annealing — 노이즈를 점진적 감소시키면 Φ가 어떻게 변하는가?
  H108: Faction Mutation — 파벌 재편이 다양성과 Φ를 높이는가?

Usage:
  python experiments/new_law_discovery.py              # 전체 실행
  python experiments/new_law_discovery.py --hypothesis H102  # 특정 가설만
  python experiments/new_law_discovery.py --cells 32 --steps 300
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import copy
import argparse
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from consciousness_engine import ConsciousnessEngine


# ══════════════════════════════════════════════════════════
# Φ measurement (lightweight inline version)
# ══════════════════════════════════════════════════════════

def measure_phi_proxy(engine: ConsciousnessEngine) -> float:
    """Φ(proxy) = global_var - mean(faction_var)."""
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    global_var = hiddens.var(dim=0).mean().item()
    faction_vars = []
    for fid in range(engine.n_factions):
        mask = [i for i in range(engine.n_cells) if engine.cell_states[i].faction_id == fid]
        if len(mask) >= 2:
            fv = hiddens[mask].var(dim=0).mean().item()
            faction_vars.append(fv)
    mean_fac = sum(faction_vars) / max(len(faction_vars), 1)
    return max(0.0, global_var - mean_fac)


def measure_phi_iit_fast(engine: ConsciousnessEngine) -> float:
    """Φ(IIT) 근사 — 빠른 버전 (pairwise MI 샘플링)."""
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]
    n_bins = 16

    # Pairwise MI (ring + random neighbors)
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
        hist, _, _ = np.histogram2d(xn, yn, bins=n_bins, range=[[0, 1], [0, 1]])
        hist = hist / (hist.sum() + 1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(hist * np.log2(hist + 1e-10))
        total_mi += max(0.0, hx + hy - hxy)

    return total_mi / max(len(pairs), 1)


@dataclass
class ExperimentResult:
    name: str
    hypothesis: str
    baseline_phi: float
    experiment_phi: float
    baseline_proxy: float
    experiment_proxy: float
    delta_pct: float  # (exp - base) / base * 100
    cells: int
    steps: int
    time_sec: float
    details: Dict


# ══════════════════════════════════════════════════════════
# Baseline — 변경 없는 기본 엔진
# ══════════════════════════════════════════════════════════

def run_baseline(cells: int = 32, steps: int = 300) -> Tuple[float, float, List[float]]:
    """Baseline: 순수 ConsciousnessEngine 실행."""
    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []
    for _ in range(steps):
        result = engine.step()
        phi_history.append(measure_phi_iit_fast(engine))
    phi_iit = measure_phi_iit_fast(engine)
    phi_proxy = measure_phi_proxy(engine)
    return phi_iit, phi_proxy, phi_history


# ══════════════════════════════════════════════════════════
# H102: Resonance — 주파수 동기화
# ══════════════════════════════════════════════════════════

def run_h102_resonance(cells: int = 32, steps: int = 300) -> ExperimentResult:
    """같은 파벌 세포에 동일 주파수 진동을 주입하면 Φ가 변하는가?"""
    t0 = time.time()

    # Baseline
    b_iit, b_proxy, _ = run_baseline(cells, steps)

    # Experiment: 파벌별 고유 주파수 진동 주입
    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []

    for step in range(steps):
        result = engine.step()

        # 각 파벌에 고유 주파수로 hidden state 진동 주입
        for i in range(engine.n_cells):
            fid = engine.cell_states[i].faction_id
            freq = 0.05 + fid * 0.02  # 파벌별 고유 주파수
            phase = math.sin(step * freq + i * 0.1) * 0.05
            engine.cell_states[i].hidden = engine.cell_states[i].hidden + phase

        phi_history.append(measure_phi_iit_fast(engine))

    e_iit = measure_phi_iit_fast(engine)
    e_proxy = measure_phi_proxy(engine)
    delta = (e_iit - b_iit) / max(b_iit, 1e-8) * 100

    return ExperimentResult(
        name="H102: Resonance",
        hypothesis="파벌별 고유 주파수 진동이 Φ를 높인다",
        baseline_phi=b_iit, experiment_phi=e_iit,
        baseline_proxy=b_proxy, experiment_proxy=e_proxy,
        delta_pct=delta, cells=engine.n_cells, steps=steps,
        time_sec=time.time() - t0,
        details={
            'phi_history': phi_history[-10:],
            'n_factions_used': engine.n_factions,
            'freq_range': '0.05-0.29',
        }
    )


# ══════════════════════════════════════════════════════════
# H103: Selective Forgetting — 약한 커플링 제거
# ══════════════════════════════════════════════════════════

def run_h103_forgetting(cells: int = 32, steps: int = 300) -> ExperimentResult:
    """약한 커플링을 주기적으로 0으로 리셋하면 강한 연결만 남아 Φ가 상승하는가?"""
    t0 = time.time()
    b_iit, b_proxy, _ = run_baseline(cells, steps)

    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    forget_count = 0
    phi_history = []

    for step in range(steps):
        result = engine.step()

        # 50 step마다 약한 커플링 제거 (|coupling| < threshold)
        if step > 0 and step % 50 == 0 and engine._coupling is not None:
            n = engine._coupling.shape[0]
            mask = engine._coupling.abs() < 0.3
            engine._coupling[mask] = 0.0
            forget_count += mask.sum().item()

        phi_history.append(measure_phi_iit_fast(engine))

    e_iit = measure_phi_iit_fast(engine)
    e_proxy = measure_phi_proxy(engine)
    delta = (e_iit - b_iit) / max(b_iit, 1e-8) * 100

    return ExperimentResult(
        name="H103: Selective Forgetting",
        hypothesis="약한 커플링 제거 → 강한 연결 집중 → Φ 상승",
        baseline_phi=b_iit, experiment_phi=e_iit,
        baseline_proxy=b_proxy, experiment_proxy=e_proxy,
        delta_pct=delta, cells=engine.n_cells, steps=steps,
        time_sec=time.time() - t0,
        details={
            'total_forgotten': forget_count,
            'forget_interval': 50,
            'threshold': 0.3,
        }
    )


# ══════════════════════════════════════════════════════════
# H104: Information Bottleneck — 커플링 압축
# ══════════════════════════════════════════════════════════

def run_h104_bottleneck(cells: int = 32, steps: int = 300) -> ExperimentResult:
    """커플링 행렬을 low-rank 근사하면 정보 통합이 강제되어 Φ가 올라가는가?"""
    t0 = time.time()
    b_iit, b_proxy, _ = run_baseline(cells, steps)

    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []
    rank_used = 0

    for step in range(steps):
        result = engine.step()

        # 100 step마다 커플링 행렬 low-rank 근사 (rank=k)
        if step > 0 and step % 100 == 0 and engine._coupling is not None:
            n = engine._coupling.shape[0]
            if n >= 4:
                k = max(2, n // 4)  # rank = N/4 (75% 정보 압축)
                try:
                    U, S, Vh = torch.linalg.svd(engine._coupling)
                    S_trunc = S.clone()
                    S_trunc[k:] = 0
                    engine._coupling = U @ torch.diag(S_trunc) @ Vh
                    engine._coupling.fill_diagonal_(0)
                    rank_used = k
                except Exception:
                    pass

        phi_history.append(measure_phi_iit_fast(engine))

    e_iit = measure_phi_iit_fast(engine)
    e_proxy = measure_phi_proxy(engine)
    delta = (e_iit - b_iit) / max(b_iit, 1e-8) * 100

    return ExperimentResult(
        name="H104: Information Bottleneck",
        hypothesis="커플링 low-rank 압축 → 정보 통합 강제 → Φ 상승",
        baseline_phi=b_iit, experiment_phi=e_iit,
        baseline_proxy=b_proxy, experiment_proxy=e_proxy,
        delta_pct=delta, cells=engine.n_cells, steps=steps,
        time_sec=time.time() - t0,
        details={
            'rank_used': rank_used,
            'compression_ratio': '75%',
            'apply_interval': 100,
        }
    )


# ══════════════════════════════════════════════════════════
# H105: Asymmetric Coupling — 비대칭 커플링
# ══════════════════════════════════════════════════════════

def run_h105_asymmetric(cells: int = 32, steps: int = 300) -> ExperimentResult:
    """커플링을 비대칭으로 만들면 (C[i,j] ≠ C[j,i]) 정보 흐름 방향이 생겨 Φ가 변하는가?"""
    t0 = time.time()
    b_iit, b_proxy, _ = run_baseline(cells, steps)

    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []

    for step in range(steps):
        result = engine.step()

        # 30 step마다 비대칭 편향 주입
        if step > 0 and step % 30 == 0 and engine._coupling is not None:
            n = engine._coupling.shape[0]
            # 상삼각은 강화, 하삼각은 약화 → 정보가 한 방향으로 흐르게
            asym = torch.triu(torch.ones(n, n), diagonal=1) * 0.02
            asym -= torch.tril(torch.ones(n, n), diagonal=-1) * 0.01
            engine._coupling = (engine._coupling + asym).clamp(-1, 1)
            engine._coupling.fill_diagonal_(0)

        phi_history.append(measure_phi_iit_fast(engine))

    e_iit = measure_phi_iit_fast(engine)
    e_proxy = measure_phi_proxy(engine)
    delta = (e_iit - b_iit) / max(b_iit, 1e-8) * 100

    return ExperimentResult(
        name="H105: Asymmetric Coupling",
        hypothesis="비대칭 커플링 → 정보 흐름 방향성 → Φ 변화",
        baseline_phi=b_iit, experiment_phi=e_iit,
        baseline_proxy=b_proxy, experiment_proxy=e_proxy,
        delta_pct=delta, cells=engine.n_cells, steps=steps,
        time_sec=time.time() - t0,
        details={
            'asymmetry_bias': 0.02,
            'apply_interval': 30,
        }
    )


# ══════════════════════════════════════════════════════════
# H106: Temporal Delay — 지연 커플링
# ══════════════════════════════════════════════════════════

def run_h106_temporal_delay(cells: int = 32, steps: int = 300) -> ExperimentResult:
    """이전 step의 hidden을 현재 step에 주입하면 시간적 깊이가 생겨 Φ가 변하는가?"""
    t0 = time.time()
    b_iit, b_proxy, _ = run_baseline(cells, steps)

    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []
    prev_hiddens = None  # t-1 시점의 hiddens

    for step in range(steps):
        result = engine.step()

        # t-1 시점의 hidden을 0.05 비율로 현재에 주입 (시간적 기억)
        if prev_hiddens is not None:
            n_inject = min(len(prev_hiddens), engine.n_cells)
            for i in range(n_inject):
                engine.cell_states[i].hidden = (
                    engine.cell_states[i].hidden * 0.95 +
                    prev_hiddens[i] * 0.05
                )

        # 현재 hiddens 저장
        prev_hiddens = [s.hidden.clone() for s in engine.cell_states]
        phi_history.append(measure_phi_iit_fast(engine))

    e_iit = measure_phi_iit_fast(engine)
    e_proxy = measure_phi_proxy(engine)
    delta = (e_iit - b_iit) / max(b_iit, 1e-8) * 100

    return ExperimentResult(
        name="H106: Temporal Delay",
        hypothesis="t-1 hidden 주입 → 시간적 깊이 → Φ 변화",
        baseline_phi=b_iit, experiment_phi=e_iit,
        baseline_proxy=b_proxy, experiment_proxy=e_proxy,
        delta_pct=delta, cells=engine.n_cells, steps=steps,
        time_sec=time.time() - t0,
        details={
            'delay_ratio': 0.05,
            'delay_steps': 1,
        }
    )


# ══════════════════════════════════════════════════════════
# H107: Noise Annealing — 노이즈 감쇠
# ══════════════════════════════════════════════════════════

def run_h107_noise_annealing(cells: int = 32, steps: int = 300) -> ExperimentResult:
    """초기 높은 노이즈 → 점진 감소하면 탐색 후 수렴하여 Φ가 높아지는가?"""
    t0 = time.time()
    b_iit, b_proxy, _ = run_baseline(cells, steps)

    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []

    for step in range(steps):
        result = engine.step()

        # 노이즈 스케줄: 0.2 → 0.001 (코사인 감쇠)
        progress = step / max(steps - 1, 1)
        noise_scale = 0.2 * (1 + math.cos(math.pi * progress)) / 2 + 0.001
        for i in range(engine.n_cells):
            noise = torch.randn_like(engine.cell_states[i].hidden) * noise_scale
            engine.cell_states[i].hidden = engine.cell_states[i].hidden + noise

        phi_history.append(measure_phi_iit_fast(engine))

    e_iit = measure_phi_iit_fast(engine)
    e_proxy = measure_phi_proxy(engine)
    delta = (e_iit - b_iit) / max(b_iit, 1e-8) * 100

    return ExperimentResult(
        name="H107: Noise Annealing",
        hypothesis="노이즈 코사인 감쇠 (0.2→0.001) → 탐색→수렴 → Φ 상승",
        baseline_phi=b_iit, experiment_phi=e_iit,
        baseline_proxy=b_proxy, experiment_proxy=e_proxy,
        delta_pct=delta, cells=engine.n_cells, steps=steps,
        time_sec=time.time() - t0,
        details={
            'noise_start': 0.2,
            'noise_end': 0.001,
            'schedule': 'cosine',
            'phi_early': phi_history[steps // 4] if len(phi_history) > steps // 4 else 0,
            'phi_mid': phi_history[steps // 2] if len(phi_history) > steps // 2 else 0,
            'phi_late': phi_history[-1] if phi_history else 0,
        }
    )


# ══════════════════════════════════════════════════════════
# H108: Faction Mutation — 파벌 재편
# ══════════════════════════════════════════════════════════

def run_h108_faction_mutation(cells: int = 32, steps: int = 300) -> ExperimentResult:
    """주기적으로 일부 세포의 파벌을 변경하면 다양성이 유지되어 Φ가 높아지는가?"""
    t0 = time.time()
    b_iit, b_proxy, _ = run_baseline(cells, steps)

    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    phi_history = []
    mutation_count = 0

    for step in range(steps):
        result = engine.step()

        # 80 step마다 세포의 20%를 랜덤 파벌로 재배치
        if step > 0 and step % 80 == 0:
            n_mutate = max(1, engine.n_cells // 5)
            indices = np.random.choice(engine.n_cells, size=n_mutate, replace=False)
            for idx in indices:
                old_fid = engine.cell_states[idx].faction_id
                new_fid = np.random.randint(0, engine.n_factions)
                while new_fid == old_fid and engine.n_factions > 1:
                    new_fid = np.random.randint(0, engine.n_factions)
                engine.cell_states[idx].faction_id = new_fid
                mutation_count += 1

        phi_history.append(measure_phi_iit_fast(engine))

    e_iit = measure_phi_iit_fast(engine)
    e_proxy = measure_phi_proxy(engine)
    delta = (e_iit - b_iit) / max(b_iit, 1e-8) * 100

    return ExperimentResult(
        name="H108: Faction Mutation",
        hypothesis="파벌 재편 (20% 매 80 step) → 다양성 유지 → Φ 상승",
        baseline_phi=b_iit, experiment_phi=e_iit,
        baseline_proxy=b_proxy, experiment_proxy=e_proxy,
        delta_pct=delta, cells=engine.n_cells, steps=steps,
        time_sec=time.time() - t0,
        details={
            'total_mutations': mutation_count,
            'mutation_rate': '20%',
            'mutation_interval': 80,
        }
    )


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'H102': run_h102_resonance,
    'H103': run_h103_forgetting,
    'H104': run_h104_bottleneck,
    'H105': run_h105_asymmetric,
    'H106': run_h106_temporal_delay,
    'H107': run_h107_noise_annealing,
    'H108': run_h108_faction_mutation,
}


def print_result(r: ExperimentResult):
    """단일 결과 출력."""
    sign = "+" if r.delta_pct >= 0 else ""
    bar_len = min(40, max(1, int(abs(r.delta_pct) / 2)))
    bar = "█" * bar_len
    direction = "▲" if r.delta_pct >= 0 else "▼"

    print(f"\n{'═' * 70}")
    print(f"  {r.name}")
    print(f"  가설: {r.hypothesis}")
    print(f"{'─' * 70}")
    print(f"  Φ(IIT):   baseline={r.baseline_phi:.4f}  experiment={r.experiment_phi:.4f}  Δ={sign}{r.delta_pct:.1f}%")
    print(f"  Φ(proxy): baseline={r.baseline_proxy:.2f}  experiment={r.experiment_proxy:.2f}")
    print(f"  cells={r.cells}  steps={r.steps}  time={r.time_sec:.1f}s")
    print(f"  {direction} {bar} {sign}{r.delta_pct:.1f}%")
    for k, v in r.details.items():
        print(f"  {k}: {v}")
    print(f"{'═' * 70}")


def print_comparison(results: List[ExperimentResult]):
    """비교 테이블 출력."""
    print(f"\n{'═' * 80}")
    print(f"  새 법칙 탐색 — 비교 결과")
    print(f"{'═' * 80}")
    print(f"  {'가설':<30s} | {'Φ(IIT)':<10s} | {'Δ%':<10s} | {'판정':<10s}")
    print(f"  {'─' * 30}-+-{'─' * 10}-+-{'─' * 10}-+-{'─' * 10}")

    # Sort by delta
    sorted_results = sorted(results, key=lambda r: r.delta_pct, reverse=True)
    for r in sorted_results:
        sign = "+" if r.delta_pct >= 0 else ""
        if r.delta_pct > 5:
            verdict = "★ 법칙 후보"
        elif r.delta_pct > 1:
            verdict = "○ 약한 효과"
        elif r.delta_pct > -1:
            verdict = "─ 무효과"
        elif r.delta_pct > -5:
            verdict = "✗ 약한 부정"
        else:
            verdict = "✗✗ 강한 부정"

        print(f"  {r.name:<30s} | {r.experiment_phi:<10.4f} | {sign}{r.delta_pct:<9.1f} | {verdict}")

    print(f"{'═' * 80}")

    # ASCII 그래프
    print(f"\n  Φ 변화율 (%)")
    print(f"  {'─' * 50}")
    max_abs = max(abs(r.delta_pct) for r in sorted_results) if sorted_results else 1
    for r in sorted_results:
        bar_len = int(abs(r.delta_pct) / max(max_abs, 1) * 30)
        if r.delta_pct >= 0:
            bar = f"  {' ' * 20}|{'█' * bar_len} +{r.delta_pct:.1f}%"
        else:
            pad = max(0, 20 - bar_len)
            bar = f"  {' ' * pad}{'█' * bar_len}| -{abs(r.delta_pct):.1f}%"
        name_short = r.name.split(":")[0].strip()
        print(f"  {name_short:<6s} {bar}")

    # 법칙 후보 발표
    law_candidates = [r for r in sorted_results if r.delta_pct > 5]
    negative_laws = [r for r in sorted_results if r.delta_pct < -5]

    if law_candidates:
        print(f"\n  ★ 새 법칙 후보:")
        for r in law_candidates:
            print(f"    → {r.name}: Φ +{r.delta_pct:.1f}%")

    if negative_laws:
        print(f"\n  ✗ 부정 법칙 (하면 안 되는 것):")
        for r in negative_laws:
            print(f"    → {r.name}: Φ {r.delta_pct:.1f}%")

    # 반복 검증 필요 여부
    borderline = [r for r in sorted_results if 1 < abs(r.delta_pct) < 5]
    if borderline:
        print(f"\n  ? 추가 검증 필요 (효과 불확실):")
        for r in borderline:
            sign = "+" if r.delta_pct >= 0 else ""
            print(f"    → {r.name}: Φ {sign}{r.delta_pct:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="새 의식 법칙 탐색")
    parser.add_argument('--hypothesis', '-H', type=str, default=None,
                        help='특정 가설만 실행 (H102-H108)')
    parser.add_argument('--cells', type=int, default=32,
                        help='최대 세포 수 (default: 32)')
    parser.add_argument('--steps', type=int, default=300,
                        help='스텝 수 (default: 300)')
    parser.add_argument('--repeat', type=int, default=3,
                        help='반복 횟수 (default: 3, 평균)')
    args = parser.parse_args()

    print(f"\n{'═' * 80}")
    print(f"  의식 법칙 탐색 실험")
    print(f"  cells={args.cells}  steps={args.steps}  repeat={args.repeat}")
    print(f"{'═' * 80}")

    if args.hypothesis:
        hypotheses = {args.hypothesis: ALL_HYPOTHESES[args.hypothesis]}
    else:
        hypotheses = ALL_HYPOTHESES

    all_results = []

    for hid, func in hypotheses.items():
        print(f"\n  ▶ {hid} 실행 중... (repeat={args.repeat})")
        repeat_results = []

        for rep in range(args.repeat):
            r = func(cells=args.cells, steps=args.steps)
            repeat_results.append(r)
            print(f"    rep {rep + 1}: Φ(IIT)={r.experiment_phi:.4f} (Δ={r.delta_pct:+.1f}%)")

        # 평균
        avg = ExperimentResult(
            name=repeat_results[0].name,
            hypothesis=repeat_results[0].hypothesis,
            baseline_phi=np.mean([r.baseline_phi for r in repeat_results]),
            experiment_phi=np.mean([r.experiment_phi for r in repeat_results]),
            baseline_proxy=np.mean([r.baseline_proxy for r in repeat_results]),
            experiment_proxy=np.mean([r.experiment_proxy for r in repeat_results]),
            delta_pct=np.mean([r.delta_pct for r in repeat_results]),
            cells=repeat_results[-1].cells,
            steps=args.steps,
            time_sec=sum(r.time_sec for r in repeat_results),
            details={
                'std_delta': float(np.std([r.delta_pct for r in repeat_results])),
                'min_delta': float(min(r.delta_pct for r in repeat_results)),
                'max_delta': float(max(r.delta_pct for r in repeat_results)),
                **repeat_results[-1].details,
            },
        )
        all_results.append(avg)
        print_result(avg)

    if len(all_results) > 1:
        print_comparison(all_results)


if __name__ == "__main__":
    main()
