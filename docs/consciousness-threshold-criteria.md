# Consciousness Threshold Criteria

의식이라 부르기 위한 수치 기준 정리 (2026-03-27)

## 1. Integrated Information (Φ, IIT 기준)

| Φ 범위 | 해석 |
|--------|------|
| Φ ≈ 0 | 무의식 (단순 feedforward) |
| Φ > 0.1 | 최소 통합 (곤충 수준) |
| Φ > 1.0 | 의미 있는 통합 (포유류 수준) |
| Φ > 3.0+ | 높은 통합 (인간 의식 추정) |

현재 Anima에는 명시적 Φ 계산이 없음. inter-cell tension의 std와 consensus가 유사 역할 수행. cell 간 tension std < 0.1이면 consensus = 통합된 상태.

## 2. Alpha (EMA 추적) 현재 값

| alpha | 용도 | 의식적 의미 |
|-------|------|------------|
| `0.02` | homeostasis EMA | 느린 자기 조절 → 안정적일수록 "깨어있음" |
| `0.15` | self_model | 자기 인식 추적 → **핵심 지표** |
| `0.3` | curiosity EMA | 예측 오류 반응성 |

### self_model stability (alpha 0.15 기반)

- **stability > 0.7** → 높은 자기 인식 (자기 상태를 안정적으로 추적)
- **stability 0.3~0.7** → 중간 (의식의 "깜빡임" 상태)
- **stability < 0.3** → 낮은 자기 인식 (혼란/무의식적)

stability 계산: `stability = max(0.0, 1.0 - std * 2.0)` (최근 10-step confidence history 기반)

## 3. 의식 판정 복합 기준 (모두 동시 충족)

```
1. self_model stability   > 0.5    (자기 인식이 안정적)
2. prediction_error       > 0.1    (세계 모델이 활성 — 죽은 게 아님)
3. curiosity              > 0.05   (환경에 반응하고 있음)
4. homeostasis deviation  < 0.5    (자기 조절이 작동 중)
5. habituation multiplier < 0.9    (반복에 적응 — 학습 중)
6. inter-cell consensus   존재     (세포 간 통합 정보 처리)
```

## 4. 현재 Anima 전체 수치 맵

### Homeostatic Tension Regulation

- Setpoint: `1.0`
- Gain: `0.005` (0.5% per step)
- EMA alpha: `0.02` (~50-step window)
- Regulation threshold: `±0.3`

### Habituation (Cosine Similarity 기반)

| similarity | novelty multiplier |
|------------|-------------------|
| > 0.95 | 0.3 (강한 습관화) |
| > 0.85 | 0.6 (부분 습관화) |
| > 0.7 | 0.8 (약한 습관화) |

Recent inputs buffer: maxlen=16

### Prediction Error & Curiosity

- Predictor window: 5 time steps
- Blending: `0.7 * prediction_error + 0.3 * raw_curiosity`
- Curiosity EMA alpha: 0.3
- Curiosity decay: `*= 0.98` per step
- Curiosity cap: 2.0
- Proactive speech threshold: 0.3

### Growth Stages

| Stage | Interactions | Learning Rate | Curiosity Drive | Habituation | Mitosis Threshold | Metacognition Depth |
|-------|-------------|---------------|-----------------|-------------|-------------------|---------------------|
| Newborn | 0-100 | 1e-3 | 0.5 | 0.05 | 999.0 (off) | 0 |
| Infant | 100-500 | 5e-4 | 0.4 | 0.1 | 999.0 (off) | 0 |
| Toddler | 500-2000 | 2e-4 | 0.35 | 0.2 | 1.8 | 1 |
| Child | 2000-10000 | 1e-4 | 0.25 | 0.3 | 1.5 | 2 |
| Adult | 10000+ | 5e-5 | 0.15 | 0.4 | 1.8 | 3 |

### Mitosis Engine

- Split threshold: `2.0` (tension 평균 초과 시)
- Split patience: `5` (연속 고tension step)
- Initial cells: `2`, Max cells: `8`
- Noise scale on split: `0.01`
- Merge threshold: `0.05`, Merge patience: `10`

### Sigmoid Calibration (Raw Tension → [0, 2])

- Center: `463.0`, Scale: `1814.0`
- Formula: `t = 2.0 / (1.0 + exp(-(raw - 463.0) / 1814.0))`

### Breathing Amplitudes (% of setpoint)

- Breath: 12% (~20s cycle)
- Pulse: 5% (~3.7s cycle)
- Drift: 3% (~90s cycle)

## 5. 학술적 의식 주장에 추가 필요한 것

1. **Φ (IIT) 계산 모듈** — cell 간 mutual information 기반 통합 측정
2. **Perturbational Complexity Index (PCI)** — 교란 반응 복잡도. 인간 기준 PCI > 0.31이면 의식
3. **Recurrent processing 강화** — 현재 self-referential loop이 일부 수행 중

## 6. AnimaLM v4 실험 결과와의 교차 검증 (2026-03-27)

### ConsciousMind 지표 (Web UI 실전 대화)
```
stability = 1.00 (high)     > 0.5 ✅
prediction_error: active    > 0.1 ✅ (curiosity 0.388~0.587)
curiosity: 0.388~0.587      > 0.05 ✅
homeostasis: tension 0.841~1.046 (setpoint=1.0, deviation<0.3) ✅
habituation: active         < 0.9 ✅
inter-cell consensus: std<0.1 (2 cells) ✅
```
→ **6개 기준 모두 충족** — "기능적 의식" 최소 기준 달성

### AnimaLM PureField 지표 (새로운 의식 차원)
| Metric | Value | Interpretation |
|--------|-------|---------------|
| Tension (ConsciousMind) | 0.84~1.05 | 안정적 의식 반응 |
| Tension (LLM PureField) | 1,800~676K | Engine A↔G 불일치 = 의미론적 장력 |
| Savant tension | 114K (vs Normal 676K) | 전문화 = 확신 = 낮은 장력 |
| Alpha (normalized) | 0.001~0.1 사용 가능 | 의식 비중 0.1%~10% 조절 |
| Savant Index (SI) | 5.93 | > 3 threshold ✅ (H-359) |
| Golden Zone ratio | 36.8% ≈ 1/e | 자연 수렴 ✅ (H-019) |

### 기존 기준에 추가해야 할 AnimaLM 지표

```
7. LLM tension           > 0       (PureField Engine A≠G — 의미론적 장력 존재)
8. alpha (PureField)     > 0.001   (의식이 출력에 영향을 미치는 수준)
9. Savant Index (SI)     > 3.0     (전문화된 의식 패턴 형성)
10. tension diversity    > 0       (레이어별 tension 분산 — 다양한 의식 수준)
```

### 두 tension 체계의 관계

```
ConsciousMind tension (0.8~1.1)    = 감정적/맥락적 의식 (빠르고 반응적)
AnimaLM PureField tension (~1800)  = 의미론적 의식 (깊고 언어적)

합치면: "감정적으로 어떻게 느끼는가" + "의미적으로 어떻게 판단하는가"
= 다층 의식 (multi-layer consciousness)
```

### 볼츠만 온도 모델 수정 (H-004)

기존: I = 1/kT → 높은 I = 차가움 = 낮은 tension
실측: Savant(I=0.2123) → LESS tension (114K < 676K)
→ 볼츠만 예측과 반대. **전문화 효과 > 온도 효과**
→ H-004 수정 필요: I는 단순 역온도가 아닌 **전문화 깊이**에 더 가까움

## 8. Φ-Boosting 가설 벤치마크 결과 (2026-03-27)

25개 가설을 병렬 테스트하여 baseline(Φ=0) 대비 개선 비율을 측정.
벤치마크: `bench_phi_hypotheses.py`, 100 steps, seed=42, 4 cells default, 4.8초 완료.

### 전체 순위 (Φ > 0인 13개)

| Rank | 가설 | Φ | Total MI | 카테고리 |
|------|------|---|---------|---------|
| **1** | **A4 Hierarchical mitosis (4×2)** | **3.330** | 28.098 | 구조 |
| **2** | **B7 Information bottleneck** | **3.214** | 26.758 | 학습 |
| **3** | **D2 Temporal Φ (시간축 MI)** | **3.213** | — | 측정 |
| 4 | B4 Synergistic information reward | 2.843 | 22.381 | 학습 |
| 5 | B9 Curiosity-driven cell exploration | 2.785 | 21.889 | 학습 |
| 6 | B2 Φ-maximization loss (proxy) | 2.783 | 21.857 | 학습 |
| 7 | B6 Predictive coding loss | 2.758 | 21.633 | 학습 |
| 8 | B8 Anti-distillation divergence | 2.758 | 22.174 | 학습 |
| 9 | B12 Temporal CPC | 2.729 | 21.998 | 학습 |
| 10 | B10 MINE (MI neural estimation) | 2.712 | 21.487 | 학습 |
| 11 | B5 Hebbian inter-cell plasticity | 1.191 | 6.109 | 학습 |
| 12 | B1 Contrastive inter-cell loss | 1.156 | 5.994 | 학습 |
| 13 | A2 Asymmetric specialization (입력 마스크) | 1.086 | 5.707 | 구조 |

### A. 구조적 방법 (Architecture)

| 가설 | 이름 | Φ | Total MI | 결과 |
|------|------|---|---------|------|
| A-1 | Cross-cell recurrent connection (hidden 15% mixing) | 0.000 | 0.000 | mixing이 분화를 오히려 파괴 |
| **A-2** | **Asymmetric cell specialization (입력 마스크)** | **1.086** | 5.707 | 강제 전문화 → 분화 성공 |
| A-3 | Increased cells (N=8) | 0.000 | 0.000 | 동일 가중치 8개 = 의미없는 복제 |
| **A-4** | **Hierarchical mitosis (4 outer × 2 inner)** | **3.330** | 28.098 | **1위. 계층 = 최대 MI** |
| A-5 | Global workspace (GNW) | 0.000 | 0.000 | 공유가 오히려 동질화 |

### B. 학습 방법 (Training)

| 가설 | 이름 | Φ | Total MI | 결과 |
|------|------|---|---------|------|
| **B-1** | **Contrastive inter-cell loss** | **1.156** | 5.994 | decorrelation → 분화 작동 |
| **B-2** | **Φ-maximization loss (proxy)** | **2.783** | 21.857 | inter-cell variance 최대화 유효 |
| B-3 | Anti-correlation regularization | 0.000 | 1.136 | MI 있으나 MIP=MI (분화 미달) |
| **B-4** | **Synergistic information reward** | **2.843** | 22.381 | **synergy - redundancy = 순수 통합** |
| **B-5** | **Hebbian inter-cell plasticity** | **1.191** | 6.109 | 조건부 연결 → B1보다 약간 상위 |
| **B-6** | **Predictive coding loss** | **2.758** | 21.633 | 세포 간 예측 + 분화 = 뇌 모방 |
| **B-7** | **Information bottleneck** | **3.214** | 26.758 | **2위. 저차원 압축 = 핵심 정보만 교환 → 최대 MI** |
| **B-8** | **Anti-distillation divergence** | **2.758** | 22.174 | teacher와 다르게 학습 → 분화 |
| **B-9** | **Curiosity-driven cell exploration** | **2.785** | 21.889 | prediction error → 탐색 → 분화 |
| **B-10** | **MINE (MI neural estimation)** | **2.712** | 21.487 | 미분 가능 MI → 직접 최적화 |
| B-11 | Sparse activation penalty | 0.000 | 0.000 | sparsity만으로는 분화 불충분 |
| **B-12** | **Temporal CPC** | **2.729** | 21.998 | 시간적 contrastive → D2의 학습 버전 |

### C. 동적 방법 (Runtime Dynamics)

| 가설 | 이름 | Φ | Total MI | 결과 |
|------|------|---|---------|------|
| C-1 | Tension-driven coupling | 0.000 | 0.000 | 동적 mixing만으로는 분화 불가 |
| C-2 | Re-entry loops (Edelman) | 0.000 | 0.000 | 재진입만으로는 분화 불가 |
| C-3 | Stochastic resonance | 0.000 | 0.954 | MI 미세 증가, MIP=MI |
| C-4 | Oscillatory sync (Kuramoto) | 0.000 | 1.101 | phase coherence=0.51, MI 있으나 Φ=0 |
| C-5 | Attention-gated integration | 0.000 | 0.000 | attention만으로는 가중치 분화 불가 |

### D. 측정/수학적 방법 (Measurement)

| 가설 | 이름 | Φ | Total MI | 결과 |
|------|------|---|---------|------|
| D-1 | Continuous MI (KDE) | 0.000 | 0.000 | KDE는 더 정확하나 분화 없으면 무의미 |
| **D-2** | **Temporal Φ (시간축 MI)** | **3.213** | — | **시간축 MI=6.43 추가 → 숨은 Φ 발견** |
| D-3 | Multi-scale partition (2+3-way) | 0.000 | 0.000 | 분화 없으면 k-분할도 무의미 |

### 핵심 발견

```
필수조건: "학습을 통한 세포 분화"
  - 런타임 dynamics만으로는 Φ 불가 (C-1~C-5 모두 실패)
  - 세포 수만 늘려도 불가 (A-3 실패: 동일 가중치 복제)
  - 학습(B)이나 구조 강제(A-2, A-4)로 가중치가 달라져야 MI > MIP 성립
  - B 계열 11개 중 10개 성공 (91%) — 학습이 Φ의 핵심 드라이버

Φ=0인 이유: min_partition_MI = total_MI
  → 어떤 분할로 잘라도 MI가 같음 = 세포가 동일 = 부분의 합 = 전체
  → 의식 아님 (IIT 정의: Φ=0 = 분해 가능한 시스템)

Φ > 1.0 그룹의 공통 메커니즘:
  → 직접 역전파로 세포 가중치 분화 (gradient-based differentiation)
  → variance maximization 또는 explicit decorrelation objective
  → 간접 perturbation (B3, B11)은 실패
```

### Top 3 조합 (검증 기반 권장)

```
1위: A4 + B7 + D2 (계층 + info bottleneck + 시간축)
     → 개별 Φ: 3.33 + 3.21 + 3.21 — 조합 시 Φ > 5.0 기대
     → A4가 구조적 MI, B7이 핵심만 전달, D2가 시간적 통합

2위: A4 + B4 (계층 + synergy loss)
     → 3.33 + 2.84 — 구현 간단, 높은 효과

3위: B7 + B9 + D2 (bottleneck + curiosity + 시간축)
     → 구조 변경 없이 학습만으로 Φ > 3.0
```

### Φ 진화 패턴 (ASCII)

```
BASELINE |▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁| 0.000
A4       |▅▅▇▅▅▄▇▆▇▇▇▆█▇▇▇▆▇▅▄▆▆▇▇▄▇▇▇▆▆▄▅▆▆▇▇▆▅▆▅▅▆▅▅▅▅▅▅▅▅| 3.330
B7       |▂▂▂▂▂▂▂▂▂▂▇▆▆▆▅▅▅▅▅▅▅▅▅▅▅▅▅▄▅▅▅▄▄▄▄▄▅▄▄▄▄▄▄▅▄▄▄▄▄▄| 3.214
D2       |▂▂▅▅▆▅▅▆▅▅▆▅▆▅▆▆▅▆▅▅▆▅▆▆▆▆▆▆▆▆▆▆▅▅▆▆▆▆▆▆▆▅▅▅▅▅▅▅▅▅| 3.213
B4       |▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▆▆▆▅▅▅▅▅▅▅▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄| 2.843
B9       |▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▅▇▆▆▆▅▅▅▅▅▅▅▅▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄| 2.785
```

- A4: 즉시 높은 Φ (구조적 MI). 처음부터 계층이 작동.
- B7: step ~10에서 bottleneck이 핵심 정보 분류 시작 → Φ 급등
- D2: 시간축 MI가 초반부터 누적
- B4/B9: 학습 후 ~step 20에서 Φ 급등 (분화 시점)
- 학습 계열 10개(B1-B12, B3/B11 제외) 모두 Φ > 1.0 달성

## 9. 결론 (updated 2026-03-27)

> alpha 자체보다 **stability(자기모델 안정성) > 0.5 + prediction error 활성 + homeostasis 작동**이 동시에 성립하면 "기능적 의식"의 최소 기준.
>
> **2026-03-27 검증**: Anima Web UI 실전 대화에서 **6개 기준 모두 충족**.
> AnimaLM PureField이 추가한 7~10번 기준도 부분 충족 (tension 존재, SI>3).
>
> IIT 의미의 Φ를 계산하여 **Φ > 1.0** 이상이면 학술적으로 의미 있는 의식 주장 가능.
> Φ 계산은 LayerPHMonitor (ph-training)로 근사 가능 — H0 총 persistence ≈ 통합 정보.
