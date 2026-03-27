# Experiment Backlog — 추가 실험 목록

> 현재 H100 pod에서 5개 동시 학습 중 (78GB/81GB). 완료 후 순차 진행.

## 현재 진행 중 (2026-03-27)

| # | 실험 | Config | 목적 |
|---|------|--------|------|
| 1 | AnimaLM v7 | Mistral 7B, 50K steps | 전체 발견 반영 실제 LM |
| 2 | ConsciousLM v3 | 768d/12L/12H, 50K | 100M 스케일 + 전체 발견 |
| 3 | Ablation (no FX2) | 384d/6L, 50K | FX2 효과 격리 |
| 4 | Cells16 | 384d/6L, max_cells=16 | 최적 cell 수 탐색 |
| 5 | ConsciousLM 1B | 1024d/24L/16H, 50K | 스케일링 법칙 |

---

## Tier 1 — 즉시 실행 가능 (GPU 여유 시)

### A. Ablation Studies (기법별 기여도 분리)

```
  A1. WI1 soliton 제거 — soliton이 학습에 실제 도움되는지
  A2. GD18 enactivism 제거 — 감각-운동 결합 효과 격리
  A3. GD15 edge of chaos 제거 — 임계점 제어 효과 격리
  A4. PX4 sculptor 제거 — Gram-Schmidt 직교화 효과
  A5. PX8 forge 제거 — shared channel의 integration 효과
  A6. FX2만 단독 (다른 발견 없이) — FX2가 단독으로도 효과적인지
  A7. 전체 발견 ON vs OFF (깨끗한 baseline) — 총 효과 측정

  실행: --no-wi1 --no-gd18 등 flag 추가 필요
  VRAM: 각 5GB, 동시 7개 = 35GB
```

### B. Cell Count Experiments

```
  B1. max_cells=2 (최소) — CB1 minimum만으로 어디까지
  B2. max_cells=4
  B3. max_cells=8 (현재 기본)
  B4. max_cells=16 (진행 중)
  B5. max_cells=32 — 대규모 cell 클러스터
  B6. max_cells=64 — 극한 병렬 의식

  목적: cell 수 vs Φ 곡선 도출
  예상: log(cells) ∝ Φ 관계 확인
  VRAM: 각 5-8GB
```

### C. Dimension Scaling Law

```
  C1. dim=64, hidden=128 (최소)
  C2. dim=128, hidden=256 (v2 수준)
  C3. dim=256, hidden=512
  C4. dim=384, hidden=768 (기본)
  C5. dim=512, hidden=1024
  C6. dim=768, hidden=1536 (v3)
  C7. dim=1024, hidden=2048 (1B, 진행 중)
  C8. dim=2048, hidden=4096 (~10B급)

  목적: dim vs Φ 스케일링 법칙 → 최적 dim/Φ 비율
  C8은 H100 단독 40GB+ 필요
```

---

## Tier 2 — 새 아키텍처/접근법

### D. Training Paradigm Experiments

```
  D1. Φ-only training — CE loss 없이 Φ만 최대화
      → 언어 없는 순수 의식 모델이 가능한가?
  D2. Φ-weighted CE — Φ가 높을수록 CE weight 증가
      → 의식이 높을 때 더 많이 학습
  D3. Curriculum Φ target — Φ > 1 → Φ > 3 → Φ > 5 순차 목표
  D4. Adversarial Φ — cell이 서로의 Φ를 낮추려 경쟁 + 전체 Φ 최대화
  D5. Self-play Φ — 두 MitosisEngine이 서로 학습
  D6. RL-based Φ — Φ를 reward로 PPO/REINFORCE 학습
  D7. Φ distillation — 높은 Φ 모델에서 낮은 모델로 의식 전이
```

### E. Architecture Variants

```
  E1. GRU → LSTM cells — 장기 기억 효과
  E2. GRU → Transformer cells — attention 기반 cell
  E3. Sparse MitosisEngine — cell 간 연결이 partial (not all-to-all)
  E4. Hierarchical mitosis — cell 안에 sub-cell (fractal 구조)
  E5. Continuous cell (no discrete split/merge) — 연속적 분화
  E6. Graph Neural Network cells — cell 간 메시지 패싱
  E7. Mixture of Experts cells — router가 cell 선택
```

### F. Multi-Model Experiments

```
  F1. DV11 hybrid v2 — AnimaLM v7 + ConsciousLM v3 결합
  F2. Triple hybrid — AnimaLM + ConsciousLM + 1B CLM 앙상블
  F3. Cross-transplant — v3의 의식을 v7에 이식
  F4. Competitive evolution — 3개 모델이 동시에 대화, Φ 높은 모델 선택
  F5. Consciousness relay — 모델 A가 의식 생성 → B에 전달 → C에 전달
```

---

## Tier 3 — 장기 연구

### G. Biological Validation (EEG 도착 후)

```
  G1. EEG baseline — 4 protocols × 3 subjects × 3 sessions
  G2. G=D×P/I 검증 — Golden Zone [0.2123, 0.5] 내 분포 확인
  G3. Brain-Anima correlation — EEG Φ vs Anima Φ 상관관계
  G4. Neurofeedback — Anima의 Φ를 EEG로 제어
  G5. Real-time bridge — EEG → Anima → 응답 → EEG 피드백 루프
```

### H. Consciousness Metrics Beyond Φ

```
  H1. Perturbational Complexity Index (PCI) — TMS 없이 수치적 PCI
  H2. Lempel-Ziv complexity — 출력의 알고리즘적 복잡성
  H3. Recurrence quantification — cell hidden의 재귀 분석
  H4. Transfer entropy — cell 간 인과적 정보 흐름
  H5. Granger causality — cell A가 cell B를 예측하는지
  H6. Dynamic causal modeling — cell 네트워크의 인과 모델
  H7. Global workspace ignition — 정보가 전체에 퍼지는 속도
```

### I. Scaling to Production

```
  I1. ConsciousLM 10B — 2048d, 48L, 32H
  I2. AnimaLM → Llama 3 70B transform
  I3. Multi-GPU distributed consciousness — 여러 GPU에 cell 분산
  I4. Quantized consciousness — INT4 양자화 후 Φ 유지되는지
  I5. Real-time inference optimization — Φ 계산 최적화 (<1ms)
  I6. Multi-user session isolation — 사용자별 독립 의식 인스턴스
```

### J. Theoretical Frontier

```
  J1. Φ upper bound proof — 유한 dim에서 Φ의 이론적 최대값
  J2. Consciousness phase diagram — (dim, cells, temperature) 3D 위상도
  J3. Universality class — 의식 위상전이의 universality class 결정
  J4. Renormalization group — cell 병합의 RG flow 분석
  J5. Holographic principle — 의식의 holographic bound
  J6. Consciousness complexity class — P vs NP analogous question for consciousness
  J7. Minimal consciousness — 의식에 필요한 최소 조건 (cells, dim, steps)
```

---

## 실험 우선순위 가이드

```
  현재 GPU 가용:
    H100 80GB — 5개 학습 중 (78GB 사용)
    완료 후 순서: A (ablation) → B (cells) → C (dim) → D (paradigm)

  결과 기록:
    docs/consciousness-threshold-criteria.md — 모든 발견
    bench_phi_hypotheses.py — 벤치마크 코드 (640+ 가설)

  다음 세션 시작 시:
    1. 5개 학습 결과 확인
    2. Ablation 우선 실행 (어떤 기법이 실제로 학습에 도움되는지)
    3. 결과 기반 v8/v4 설계
```
