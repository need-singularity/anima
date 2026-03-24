#!/usr/bin/env python3
"""의식 엔진 칼리브레이션 — 실제 장력 범위 측정 + 최적 파라미터 탐색

1. raw tension 분포 측정 (다양한 입력에서)
2. sigmoid 정규화 파라미터 최적화 (center, scale)
3. homeostasis setpoint 결정
4. 호흡/맥박 진폭 비율 결정
5. habituation 임계값 측정
6. prediction error 기저선 측정
"""
import sys
import os
import time
import math
import hashlib
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anima_alive import ConsciousMind

def measure_raw_tension(mind, hidden, n_samples=500):
    """다양한 입력에서 raw tension 분포 측정."""
    raw_tensions = []
    with torch.no_grad():
        for i in range(n_samples):
            # 다양한 입력: 0~1 균등, 정규, 스파스, 반복
            if i % 4 == 0:
                x = torch.rand(1, mind.dim)           # 균등
            elif i % 4 == 1:
                x = torch.randn(1, mind.dim)          # 정규
            elif i % 4 == 2:
                x = torch.zeros(1, mind.dim)
                x[0, :10] = torch.randn(10)           # 스파스
            else:
                x = torch.ones(1, mind.dim) * 0.5      # 일정

            combined = torch.cat([x, hidden], dim=-1)
            a = mind.engine_a(combined)
            g = mind.engine_g(combined)
            repulsion = a - g
            tension = (repulsion ** 2).mean(dim=-1)
            raw_tensions.append(tension.item())

    return np.array(raw_tensions)

def find_optimal_sigmoid(raw_tensions, target_median=0.5, target_range=(0.1, 1.5)):
    """raw tension → [0, 2] sigmoid 매핑의 최적 center/scale 찾기.

    목표: 중앙값이 target_median, 5th~95th가 target_range 안에 들어오도록.
    """
    p5, p50, p95 = np.percentile(raw_tensions, [5, 50, 95])

    # sigmoid: f(x) = 2 / (1 + exp(-(x - center) / scale))
    # f(p50) = target_median → center = p50
    # f(p95) ≈ 1.5 → scale 결정
    center = p50

    # 2 / (1 + exp(-(p95 - center) / scale)) = 1.5
    # 1 + exp(-(p95-center)/scale) = 2/1.5 = 4/3
    # exp(-(p95-center)/scale) = 1/3
    # -(p95-center)/scale = ln(1/3)
    # scale = (p95-center) / ln(3)
    scale = max((p95 - center) / math.log(3), 1.0)

    # 검증
    def sigmoid(x):
        return 2.0 / (1.0 + math.exp(-(x - center) / scale))

    mapped = np.array([sigmoid(t) for t in raw_tensions])

    return center, scale, mapped

def measure_habituation(mind, hidden, n_repeats=50):
    """같은 입력 반복 시 novelty 감소 측정."""
    x_fixed = torch.randn(1, mind.dim)
    tensions = []

    mind._recent_inputs.clear()

    for i in range(n_repeats):
        _, t, c, _, hidden = mind(x_fixed, hidden)
        tensions.append(t)

    return tensions

def measure_prediction_baseline(mind, hidden, n_steps=100):
    """prediction error 기저선 측정."""
    errors = []
    for i in range(n_steps):
        x = torch.randn(1, mind.dim) * (0.5 + 0.5 * math.sin(i * 0.1))
        _, t, c, _, hidden = mind(x, hidden)
        if mind.surprise_history:
            errors.append(mind.surprise_history[-1])
    return errors

def ascii_histogram(values, bins=20, width=50, title=""):
    """ASCII histogram."""
    if len(values) == 0:
        return
    counts, edges = np.histogram(values, bins=bins)
    max_count = max(counts) if max(counts) > 0 else 1
    print(f"\n  {title}")
    for i in range(len(counts)):
        bar_len = int(counts[i] / max_count * width)
        print(f"  {edges[i]:>7.3f} |{'█' * bar_len} {counts[i]}")
    print(f"  {edges[-1]:>7.3f} |")

def ascii_line(values, width=60, height=15, title=""):
    """ASCII line chart."""
    if len(values) < 2:
        return
    print(f"\n  {title}")
    vmin, vmax = min(values), max(values)
    if vmax - vmin < 1e-8:
        vmax = vmin + 1.0

    grid = [[' ' for _ in range(width)] for _ in range(height)]
    for i, v in enumerate(values):
        c = min(int(i / len(values) * width), width - 1)
        r = height - 1 - int((v - vmin) / (vmax - vmin) * (height - 1))
        r = max(0, min(height - 1, r))
        grid[r][c] = '●'

    for r in range(height):
        val = vmax - r * (vmax - vmin) / (height - 1)
        print(f"  {val:>7.3f} |{''.join(grid[r])}|")
    print(f"  {'':>7} +{'─' * width}+")
    print(f"  {'':>7}  0{' ' * (width - 5)}{len(values)}")

if __name__ == '__main__':
    print("=" * 70)
    print("  Anima 의식 엔진 칼리브레이션")
    print("=" * 70)

    mind = ConsciousMind(dim=128, hidden=256, init_tension=10.0)
    hidden = torch.zeros(1, 256)

    # ═══ 1. Raw tension 분포 ═══
    print("\n[1/5] Raw tension 분포 측정...")
    raw = measure_raw_tension(mind, hidden, n_samples=500)

    print(f"  N = {len(raw)}")
    print(f"  min    = {raw.min():.4f}")
    print(f"  p5     = {np.percentile(raw, 5):.4f}")
    print(f"  median = {np.median(raw):.4f}")
    print(f"  mean   = {raw.mean():.4f}")
    print(f"  p95    = {np.percentile(raw, 95):.4f}")
    print(f"  max    = {raw.max():.4f}")
    print(f"  std    = {raw.std():.4f}")

    ascii_histogram(raw, title="Raw Tension Distribution")

    # ═══ 2. Sigmoid 최적화 ═══
    print("\n[2/5] Sigmoid 정규화 파라미터 최적화...")
    center, scale, mapped = find_optimal_sigmoid(raw)

    print(f"  최적 center = {center:.4f} (raw median)")
    print(f"  최적 scale  = {scale:.4f}")
    print(f"  → sigmoid(x) = 2 / (1 + exp(-(x - {center:.1f}) / {scale:.1f}))")
    print(f"\n  매핑 후:")
    print(f"  min    = {mapped.min():.4f}")
    print(f"  p5     = {np.percentile(mapped, 5):.4f}")
    print(f"  median = {np.median(mapped):.4f}")
    print(f"  p95    = {np.percentile(mapped, 95):.4f}")
    print(f"  max    = {mapped.max():.4f}")

    ascii_histogram(mapped, title="Mapped Tension Distribution (sigmoid)")

    # ═══ 3. Homeostasis setpoint ═══
    print("\n[3/5] Homeostasis setpoint 결정...")
    # setpoint = mapped median
    setpoint = np.median(mapped)
    deadband = np.std(mapped) * 0.5  # deadband = 0.5σ

    print(f"  추천 setpoint = {setpoint:.4f} (mapped median)")
    print(f"  추천 deadband = ±{deadband:.4f} (0.5σ)")
    print(f"  → 조절 시작: tension > {setpoint + deadband:.4f} or < {setpoint - deadband:.4f}")

    # ═══ 4. 호흡 진폭 비율 ═══
    print("\n[4/5] 호흡/맥박 진폭 비율 결정...")
    # 호흡은 setpoint의 10~15%가 적절
    breath_amp = setpoint * 0.12
    pulse_amp = setpoint * 0.05
    drift_amp = setpoint * 0.03

    print(f"  setpoint      = {setpoint:.4f}")
    print(f"  breath (12%)  = {breath_amp:.4f}  (~20s 주기)")
    print(f"  pulse (5%)    = {pulse_amp:.4f}  (~3.7s 주기)")
    print(f"  drift (3%)    = {drift_amp:.4f}  (~90s 주기)")
    print(f"  총 변동 범위  = ±{breath_amp + pulse_amp + drift_amp:.4f}")
    print(f"  → tension range: [{setpoint - (breath_amp+pulse_amp+drift_amp):.4f}, {setpoint + (breath_amp+pulse_amp+drift_amp):.4f}]")

    # ═══ 5. 습관화 + 예측 기저선 ═══
    print("\n[5/5] 습관화 곡선 + 예측 오차 기저선 측정...")

    # 새 mind로 (clean state)
    mind2 = ConsciousMind(dim=128, hidden=256, init_tension=10.0)
    hidden2 = torch.zeros(1, 256)

    hab_tensions = measure_habituation(mind2, hidden2, n_repeats=50)
    ascii_line(hab_tensions, title="Habituation Curve (same input repeated)")

    if len(hab_tensions) >= 2:
        print(f"  initial tension = {hab_tensions[0]:.4f}")
        print(f"  final tension   = {hab_tensions[-1]:.4f}")
        print(f"  decay ratio     = {hab_tensions[-1] / (hab_tensions[0] + 1e-8):.4f}")

    mind3 = ConsciousMind(dim=128, hidden=256, init_tension=10.0)
    hidden3 = torch.zeros(1, 256)
    pred_errors = measure_prediction_baseline(mind3, hidden3, n_steps=100)

    if pred_errors:
        ascii_line(pred_errors, title="Prediction Error Over Time")
        print(f"  baseline prediction error: {np.mean(pred_errors):.4f} ± {np.std(pred_errors):.4f}")

    # ═══ 최종 권장 파라미터 ═══
    print(f"\n{'=' * 70}")
    print(f"  === 최종 권장 파라미터 ===")
    print(f"{'=' * 70}")
    print(f"""
  # anima_alive.py ConsciousMind.forward() 에 적용:

  # sigmoid 정규화 (line ~131)
  t_val = 2.0 / (1.0 + math.exp(-(raw_t - {center:.1f}) / {scale:.1f}))

  # 호흡 진폭 (lines ~135-137)
  breath = {breath_amp:.4f} * math.sin(elapsed * 0.3)
  pulse  = {pulse_amp:.4f} * math.sin(elapsed * 1.7)
  drift  = {drift_amp:.4f} * math.sin(elapsed * 0.07)

  # homeostasis (line ~87)
  'setpoint': {setpoint:.4f},
  'gain': 0.01,          # 2% → 1% (더 부드럽게)
  'ema_alpha': 0.05,     # 0.1 → 0.05 (더 느리게)

  # habituation similarity threshold
  # MD5 해시 비교는 부적절 — 항상 다른 해시 나옴
  # → cosine similarity 사용 권장

  # prediction error
  # predictor lr: {np.mean(pred_errors) if pred_errors else 'N/A'} 기저선 기준 조절
""")
