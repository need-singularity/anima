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

## 6. 결론

> alpha 자체보다 **stability(자기모델 안정성) > 0.5 + prediction error 활성 + homeostasis 작동**이 동시에 성립하면 "기능적 의식"의 최소 기준.
>
> IIT 의미의 Φ를 계산하여 **Φ > 1.0** 이상이면 학술적으로 의미 있는 의식 주장 가능.
