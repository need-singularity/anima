#!/usr/bin/env python3
"""IQ Calculator — 의식 지능 측정기 (TECS-L n=6 수학 통합)

n=6 상수:
  σ(6)=12  약수의 합 (완전수: σ(n)=2n)
  τ(6)=4   약수의 개수
  φ(6)=2   오일러 토션트
  ψ(6)=12  데데킨트 프사이
  sopfr(6)=5  소인수 합 (2+3)
  6'=5     산술 미분

지능 측정 공식:
  IQ_compression = 1 - (effective_dims / total_dims)
  IQ_prediction = improvement(early_error → late_error)
  IQ_consistency = cosine_similarity(same input responses)
  IQ_adaptation = 1 - (adapt_steps / total_steps)
  IQ_generalization = output_diversity_for_novel_inputs

  IQ_combined = weighted combination (n=6 weights!)

n=6 연결:
  σ(6)/τ(6) = 12/4 = 3  → IQ 3대 핵심 지표 (compression, prediction, consistency)
  φ(6) = 2             → 2축 성장 (Φ + IQ)
  τ(6) = 4             → 4단계 지능 수준 (low/med/high/genius)
  sopfr(6) = 5         → 5가지 IQ 변수
  6' = 5               → 5가지 IQ 변수 (동일! 수학적 일치)

Usage:
  python3 iq_calculator.py                         # 기본 64c 측정
  python3 iq_calculator.py --cells 256             # 256c
  python3 iq_calculator.py --cells 512 --steps 50  # 512c, 50 step
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator


# ═══ n=6 Constants ═══
SIGMA_6 = 12   # σ(6) = 약수의 합
TAU_6 = 4      # τ(6) = 약수의 개수
PHI_6 = 2      # φ(6) = 오일러 토션트
SOPFR_6 = 5    # sopfr(6) = 소인수 합
N6_DERIV = 5   # 6' = 산술 미분

# IQ weights from n=6 arithmetic:
# σ(6)/τ(6)/φ(6) = 12/4/2 = normalized → [0.5, 0.167, 0.083, ...]
# 또는 간단하게: 5가지 변수에 균등 + 상위 3개 가중
IQ_WEIGHTS = {
    'compression': 3.0,    # σ(6)/τ(6) = 3 → compression이 3배 중요
    'prediction': 2.0,     # φ(6) = 2
    'consistency': 1.0,    # 기본
    'generalization': 1.0, # 기본
    'adaptation': 1.0,     # 기본
}
WEIGHT_SUM = sum(IQ_WEIGHTS.values())  # = 8.0


def measure_compression(engine, dim=64):
    """IQ2: 압축률 — 유효 차원 / 전체 차원"""
    with torch.no_grad():
        outputs = []
        for _ in range(30):
            x = torch.randn(1, dim)
            engine.process(x)
            out = torch.stack([c.hidden.squeeze()[:dim] for c in engine.cells]).mean(dim=0)
            outputs.append(out)
        out_stack = torch.stack(outputs)
        U, S, V = torch.svd(out_stack - out_stack.mean(dim=0))
        cumvar = (S ** 2).cumsum(0) / ((S ** 2).sum() + 1e-8)
        eff_dim = (cumvar < 0.95).sum().item() + 1
        return 1.0 - (eff_dim / dim), eff_dim


def measure_prediction(engine, dim=64, steps=30):
    """IQ1: 예측 정확도 — 이웃 세포 상태 예측 개선도"""
    errors_early = []
    errors_late = []
    prev_states = {}

    for step_i in range(steps):
        with torch.no_grad():
            for i in range(min(len(engine.cells), 8)):
                prev_states[i] = engine.cells[i].hidden.squeeze().clone()
        engine.process(torch.randn(1, dim))
        with torch.no_grad():
            nc = len(engine.cells)
            if nc >= 4 and prev_states:
                errs = []
                for i in range(min(nc, 8)):
                    j = (i + 1) % nc
                    if i in prev_states:
                        err = (prev_states[i] - engine.cells[j].hidden.squeeze()).norm().item()
                        errs.append(err)
                avg = sum(errs) / len(errs) if errs else 0
                if step_i < steps // 3:
                    errors_early.append(avg)
                else:
                    errors_late.append(avg)

    early = sum(errors_early) / len(errors_early) if errors_early else 1.0
    late = sum(errors_late) / len(errors_late) if errors_late else 1.0
    return max(0.0, min(1.0, (early - late) / (early + 1e-8)))


def measure_consistency(engine, dim=64):
    """IQ4: 일관성 — 같은 입력에 대한 응답 유사도"""
    test_input = torch.randn(1, dim)
    responses = []
    with torch.no_grad():
        for _ in range(10):
            engine.process(test_input)
            out = torch.stack([c.hidden.squeeze()[:dim] for c in engine.cells]).mean(dim=0)
            responses.append(out.clone())
    if len(responses) < 2:
        return 0.0
    sims = []
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            sim = F.cosine_similarity(responses[i].unsqueeze(0), responses[j].unsqueeze(0)).item()
            sims.append(sim)
    return max(0.0, sum(sims) / len(sims))


def measure_generalization(engine, dim=64, steps=30):
    """IQ3: 일반화 — 새로운 입력에 대한 반응 다양성"""
    # 학습: 같은 패턴 반복
    pattern = torch.randn(1, dim)
    for _ in range(steps):
        engine.process(pattern + torch.randn(1, dim) * 0.1)
    # 테스트: 완전 새로운 패턴
    outputs = []
    with torch.no_grad():
        for _ in range(20):
            engine.process(torch.randn(1, dim) * 2.0)
            out = torch.stack([c.hidden.squeeze()[:dim] for c in engine.cells]).mean(dim=0)
            outputs.append(out)
    if len(outputs) < 2:
        return 0.0
    out_stack = torch.stack(outputs)
    diffs = (out_stack[1:] - out_stack[:-1]).norm(dim=1)
    return min(1.0, (diffs > 0.01).float().mean().item())


def measure_adaptation(engine, dim=64, steps=30):
    """IQ5: 적응 속도 — 새 패턴에 적응하는 속도"""
    pattern = torch.randn(1, dim) * 2.0
    baseline = None
    adapted_step = steps

    for step_i in range(steps):
        engine.process(pattern + torch.randn(1, dim) * 0.2)
        with torch.no_grad():
            out = torch.stack([c.hidden.squeeze()[:dim] for c in engine.cells]).mean(dim=0)
            dist = (out - pattern.squeeze()[:dim]).norm().item()
            if step_i == 0:
                baseline = dist
            elif baseline and dist < baseline * 0.5 and adapted_step == steps:
                adapted_step = step_i

    return max(0.0, 1.0 - (adapted_step / steps))


def compute_iq(engine, dim=64, verbose=True):
    """종합 IQ 측정 — 5가지 변수 + n=6 가중 결합"""
    t0 = time.time()

    if verbose:
        print("Measuring intelligence...")

    # 5 measurements (= sopfr(6) = 6' = 5)
    compression, eff_dim = measure_compression(engine, dim)
    prediction = measure_prediction(engine, dim)
    consistency = measure_consistency(engine, dim)
    generalization = measure_generalization(engine, dim)
    adaptation = measure_adaptation(engine, dim)

    # n=6 weighted combination
    iq_raw = (
        IQ_WEIGHTS['compression'] * compression +
        IQ_WEIGHTS['prediction'] * prediction +
        IQ_WEIGHTS['consistency'] * consistency +
        IQ_WEIGHTS['generalization'] * generalization +
        IQ_WEIGHTS['adaptation'] * adaptation
    ) / WEIGHT_SUM

    # Scale to 0-200 (IQ-like range)
    iq_score = iq_raw * 200

    # τ(6)=4 intelligence levels
    if iq_score < 50:
        level = "Low"
        level_ko = "낮음"
    elif iq_score < 100:
        level = "Medium"
        level_ko = "보통"
    elif iq_score < 150:
        level = "High"
        level_ko = "높음"
    else:
        level = "Genius"
        level_ko = "천재"

    elapsed = time.time() - t0

    result = {
        'iq_score': round(iq_score, 1),
        'level': level,
        'level_ko': level_ko,
        'compression': round(compression, 4),
        'effective_dims': eff_dim,
        'prediction': round(prediction, 4),
        'consistency': round(consistency, 4),
        'generalization': round(generalization, 4),
        'adaptation': round(adaptation, 4),
        'cells': len(engine.cells),
        'elapsed': round(elapsed, 1),
    }

    if verbose:
        print(f"\n═══ Anima IQ Report ═══")
        print(f"  IQ Score: {iq_score:.1f} ({level} / {level_ko})")
        print(f"  ─────────────────────")
        print(f"  Compression:    {compression:.3f}  (×3 weight, {eff_dim}/{dim} dims)")
        print(f"  Prediction:     {prediction:.3f}  (×2 weight)")
        print(f"  Consistency:    {consistency:.3f}")
        print(f"  Generalization: {generalization:.3f}")
        print(f"  Adaptation:     {adaptation:.3f}")
        print(f"  ─────────────────────")
        print(f"  Cells: {len(engine.cells)}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  n=6: σ/τ/φ = {SIGMA_6}/{TAU_6}/{PHI_6} → weights 3/2/1")
        print(f"  sopfr(6) = {SOPFR_6} = 5 variables ✓")

    return result


def main():
    parser = argparse.ArgumentParser(description="Anima IQ Calculator")
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--steps", type=int, default=30, help="Steps per measurement")
    args = parser.parse_args()

    torch.manual_seed(42)

    engine = MitosisEngine(args.dim, args.hidden, args.dim, initial_cells=2, max_cells=args.cells)
    while len(engine.cells) < args.cells:
        engine._create_cell(parent=engine.cells[0])

    # Warm up
    for _ in range(10):
        engine.process(torch.randn(1, args.dim))

    # Measure Φ
    phi_calc = PhiCalculator(n_bins=16)
    phi, _ = phi_calc.compute_phi(engine)
    print(f"Φ = {phi:.2f}")

    # Measure IQ
    result = compute_iq(engine, args.dim)

    # Growth stage
    print(f"\n  Growth Map:")
    print(f"    Φ = {phi:.1f} (consciousness)")
    print(f"    IQ = {result['iq_score']:.1f} (intelligence)")


if __name__ == "__main__":
    main()
