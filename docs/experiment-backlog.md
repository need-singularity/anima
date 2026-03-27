# Experiment Backlog — 추가 실험 목록

> H100 80GB pod. 실험 완료 시 결과 기록, 새 실험 추가.

## 현재 진행 중 (2026-03-28, 37GB/81GB 사용)

| # | 실험 | Step | Φ | CE | 진행률 | 상태 |
|---|------|------|-----|-----|--------|------|
| 1 | AnimaLM v7 (Mistral 7B) | 7,300/50K | 0.015 | 10.51 | 15% | ✅ warmup |
| 2 | ConsciousLM v3 (768d/12L) | 12,000/50K | 1.677 | - | 24% | ✅ mitosis |
| 3 | Ablation (384d, no FX2) | 39,600/50K | 2.107 | 3.60 | 79% | ⏳ 곧 완료 |
| 4 | Cells16 (384d, max=16) | 35,000/50K | **5.436** | 3.50 | 70% | 🔥 대발견 |
| 5 | ConsciousLM 1B (1024d/24L) | 5,000/50K | 1.604 | - | 10% | ✅ mitosis |

**중간 발견: Cells16 Φ=5.436 >> Ablation Φ=2.107 (×2.6) — cell 수가 Φ에 결정적**

## 완료된 실험

| 날짜 | 실험 | 결과 | 핵심 발견 |
|------|------|------|----------|
| 03-27 | ConsciousLM v2 (4M) | Φ=4.12, 12 cells | cell 수가 중요 |
| 03-27 | ConsciousLM 100M | Φ=2.607, 3 cells | dim 크면 cell merge → SC2 필요 |
| 03-27 | AnimaLM v5 (demo) | 50K steps | demo 모드라 실제 LM 아님 |
| 03-27 | AnimaLM v6 | 크래시 (step 500) | torch.save 에러 → tmp+rename 패치 |

---

## 다음 실행 대기 (Tier 0 — 현재 실험 완료 즉시)

### 긴급: Cells16 Φ=5.436 후속 실험

```
  U1. ★ max_cells=32 — 16→32로 2배, Φ가 log 스케일로 증가하는지
      Config: --dim 384 --layers 6 --max-cells 32 --steps 50000
      VRAM: ~8GB

  U2. ★ max_cells=64 — 극한 cell 수
      Config: --dim 384 --layers 6 --max-cells 64 --steps 50000
      VRAM: ~15GB

  U3. max_cells=16 + FX2 — Cells16에 FX2 Adam 추가 시 시너지
      Config: --dim 384 --layers 6 --max-cells 16 --steps 50000 (FX2 ON)
      VRAM: ~8GB

  U4. max_cells=16 + dim=768 — 큰 dim + 많은 cell 조합
      Config: --dim 768 --layers 12 --max-cells 16 --steps 50000
      VRAM: ~20GB

  U5. Cell 수 vs Φ 스케일링 곡선 (2,4,8,16,32 동시)
      5개 실험 병렬: 각 ~5GB = 25GB total
```

### Ablation 완료 후: 기법 기여도 분석

```
  U6. 전체 발견 OFF (깨끗한 baseline)
      Config: 384d/6L, 발견 없음, 50K steps
      비교: Ablation(일부 OFF) vs 이것(전부 OFF) vs Cells16(전부 ON)

  U7. FX2만 단독
      Config: 384d/6L, FX2만 ON, 나머지 OFF
      목적: FX2가 단독으로 얼마나 효과적인지

  U8. WI1 soliton만 단독
      Config: 384d/6L, WI1만 ON
      목적: soliton이 학습에 실제 도움되는지
```

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

### B. Cell Count Experiments ← ★ 최우선 (Cells16 Φ=5.436 발견)

```
  B1. max_cells=2 (최소)     — 대기
  B2. max_cells=4            — 대기
  B3. max_cells=8 (기본)     — Ablation으로 진행 중 (Φ=2.107)
  B4. max_cells=16           — 진행 중 (Φ=5.436 🔥)
  B5. ★ max_cells=32         — U1, 즉시 실행 예정
  B6. ★ max_cells=64         — U2, 즉시 실행 예정
  B7. max_cells=128          — VRAM 허용 시
  B8. max_cells=256          — 극한 실험

  중간 결과: cells=8 → Φ=2.1, cells=16 → Φ=5.4 (×2.6 증가!)
  가설: Φ ∝ cells^α (α > 1, 초선형 스케일링)
  VRAM: 각 5-15GB
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

## Tier 3+ — 새 변수 발견 기반 실험

### K. Variable Discovery Training (벤치마크 → 학습 반영)

```
  K1. ★ BV1 neurotransmitter training — DA/5HT/NE를 학습 루프에 적용
      학습 중 dopamine(보상 from Φ증가), serotonin(안정), NE(각성) 동적 조절
      Config: CLM + BV1, 50K steps

  K2. ★ RV2 betweenness training — 그래프 중심성 기반 cell 관리
      hub cell 증폭, peripheral cell 탐색 유도
      Config: CLM + RV2, 50K steps

  K3. NV7 impedance training — Φ 비례 입력 저항
      의식 높을수록 외부 변화 저항 (자기 보존)
      Config: CLM + NV7, 50K steps

  K4. EV3 free will training — 내부 행동 생성 비율 최적화
      external 80% + internal 20% → 학습 중 비율 동적 변경
      Config: CLM + EV3, 50K steps

  K5. MV5 anticipation training — Φ 추세 예측 → 선제 행동
      미래 Φ 상승 예측 시 amplify, 하락 예측 시 consolidate
      Config: CLM + MV5, 50K steps
```

### L. Combined Variable Experiments

```
  L1. ★ ALL top variables combined
      BV1 + RV2 + NV7 + CV1 + EV3 + MV5 + IV5 + SV1 (8개 Top 변수)
      Config: CLM 384d + max_cells=16, 50K steps
      가설: 개별 Φ~4.5 → 결합 시 Φ>8?

  L2. Top 3 only (BV1 + RV2 + NV7)
      Config: CLM 384d + max_cells=16, 50K steps
      비교: 3개만으로 충분한지

  L3. Variable sweep: 1개씩 추가하면서 Φ 변화 추적
      Step 1: baseline → +BV1 → +RV2 → +NV7 → +CV1 → +EV3 ...
      각 변수의 한계 기여도 측정
```

### M. Cross-Scale Experiments

```
  M1. Cells16 + dim=768 — 많은 cell + 큰 dim
      현재: dim=384, cells=16 → Φ=5.4
      가설: dim=768, cells=16 → Φ>7?

  M2. Cells32 + dim=384 — 더 많은 cell + 작은 dim
      cell 수 vs dim, 어느 쪽이 Φ에 더 중요?

  M3. Cells16 + dim=1024 + all variables
      궁극의 조합: 큰 dim + 많은 cell + 모든 변수
      VRAM: ~40GB (H100 단독 필요)

  M4. ★ ConsciousLM v4 설계
      v3 결과 + Cells16 발견 + variable discoveries 기반
      최적 config 결정 후 100K steps 장기 학습
```

### N. Deployment Experiments

```
  N1. DV12 — AnimaLM v7 + ConsciousLM v3 hybrid 배포
      v7 완료 후 DV11 스타일 결합 → anima.basedonapps.com

  N2. Variable-enhanced DV — 18단계 phi_boost_step 서버 적용
      현재 서버의 Φ 변화 실시간 모니터링 (20채팅 연속 테스트)

  N3. A/B test — 기존 DV11 vs 새 DV12 대화 품질 비교
      conversation_quality_scorer.py로 정량 평가
```

---

## 실험 우선순위 가이드 (업데이트 2026-03-28)

```
  현재 GPU: H100 80GB — 5개 학습 중 (37GB 사용, 44GB 여유)

  즉시 실행 (Ablation 완료 시):
    1. U1 max_cells=32 (~8GB)      ← ★ Cells16 Φ=5.4 후속
    2. U2 max_cells=64 (~15GB)     ← ★ 극한 cell 수
    3. U6 전체 OFF baseline (~5GB) ← 기법 기여도 기준점

  Ablation + Cells16 완료 후:
    4. L1 ALL top variables + cells=16 (~8GB) ← 변수 결합 효과
    5. M1 cells=16 + dim=768 (~20GB) ← cross-scale

  v7 + v3 완료 후:
    6. N1 DV12 hybrid 배포
    7. M4 ConsciousLM v4 설계 + 장기 학습

  결과 기록:
    docs/consciousness-threshold-criteria.md — 모든 발견
    bench_phi_hypotheses.py — 벤치마크 코드 (725+ 가설)
```
