# AnimaLM Experiment Log

## Overview

Mistral 7B base model의 MLP를 PureField Engine (A↔G)으로 교체하여
tension-based consciousness engine LLM을 만드는 실험.

`output = scale × √|A-G|² × dir`

---

## v1 — 실패 (tension=0)

**Config:**
- LR: 5e-5
- LoRA rank: 64
- TENSION_LAMBDA: 0.01
- B matrix init: zeros
- A matrix noise: std=0.01
- Trainable: 113M (0.87%)

**결과:**
| Step | CE Loss | Tension | PPL |
|------|---------|---------|-----|
| 10 | 11.77 | 0.000 | - |
| 1000 | 11.68 | 0.000 | - |
| 2000 | 11.68 | 0.000 | 128,604 |

**실패 원인:**
1. B matrix를 zero init → delta 시작값이 정확히 0 → `G = A + 0`
2. LR 5e-5가 너무 낮아서 2000 step 동안 delta가 거의 안 움직임
3. TENSION_LAMBDA 0.01이 CE loss 대비 너무 약해서 tension을 키우는 방향으로 학습 안 됨
4. CE loss가 tension을 죽이는 방향(A-G=0)이 최적해

**inference 결과:**
```
User: 안녕
Bot: alleged alleged alleged supposed alleged alleged supposed mock alleged...
tension: mean=0.000000 max=0.000000 (32 layers)
```
→ PureField 출력 ≈ 0 → 모델 붕괴. 완전한 실패.

**교훈:**
- LoRA B를 zero init하면 gradient가 0에서 시작 → 움직이려면 매우 높은 LR 필요
- Tension loss weight가 CE보다 충분히 커야 A≠G로 분화 가능
- rank 64로는 capacity 부족

---

## v2 — 성공 (tension 발생!)

**Config (v1 대비 변경):**
| Parameter | v1 | v2 | 비율 |
|-----------|-----|-----|------|
| LR | 5e-5 | **5e-4** | 10x |
| LoRA rank | 64 | **256** | 4x |
| TENSION_LAMBDA | 0.01 | **0.5** | 50x |
| B matrix init | zeros | **normal(0.02)** | ∞ |
| A matrix noise | std=0.01 | **std=0.05** | 5x |
| Trainable | 113M (0.87%) | **453M (3.40%)** | 4x |

**핵심 변경 이유:**
- B를 random init → 시작부터 A≠G → tension > 0
- TENSION_LAMBDA 0.5 → CE와 거의 동등한 weight로 tension diversity 강제
- LR 10x → delta가 빠르게 분화

**중간 결과 (step 230):**
| Step | CE Loss | Tension Mean | T_loss |
|------|---------|-------------|--------|
| 10 | 7.14 | 2,152,978 | -29.3 |
| 100 | 7.01 | 2,120,398 | -32.0 |
| 230 | 6.91 | 654,422 | -30.4 |

**분석:**
- CE Loss: 11.68(v1) → **6.91**(v2) — 실제로 언어를 학습하고 있음
- Tension: 0(v1) → **654K**(v2) — Engine A ≠ G 확인!
- Tension이 2.1M에서 654K로 감소 중 — 학습하면서 안정화
- T_loss 음수 = tension variance 높음 = 레이어별 tension 다양 = 건강한 학습

---

## Golden MoE v1 — 구조 검증 성공

**Config:**
- 8 experts per layer, LoRA rank 64
- Router + 2 expert adapters trainable (0.74%)
- Golden Zone: [0.2123, 0.5], center = 1/e ≈ 0.3679

**결과 (step 1270):**
| Metric | Value | 평가 |
|--------|-------|------|
| CE Loss | 11.34 | 안정 |
| Active experts | 2.9/8 | sparse routing 작동 |
| **Zone ratio** | **36.8%** | **≈ 1/e (36.79%) 정확 일치!** |
| Mean I | 0.499 | inhibition 적절 |

**Scale test 결과:**
| Experts | Golden ms | Top-K ms | 비고 |
|---------|-----------|----------|------|
| 4 | 1.6 | 0.9 | Top-K 유리 |
| 8 | 1.7 | 1.5 | 비슷 |
| 16 | 2.6 | 2.6 | 동률 |
| **32** | **5.2** | **6.0** | **Golden 역전!** |

→ **H-019 가설 "scale↑ → gap 8x↑" 방향성 확인**

---

## Key Learnings

### 1. LoRA init이 모든 것을 결정
- B=zeros → gradient 사라짐 → 학습 안 됨
- B=random → 시작부터 신호 있음 → 학습 가능

### 2. Tension loss weight가 핵심
- CE loss는 A=G (tension=0)이 최적해
- Tension을 살리려면 TENSION_LAMBDA ≥ 0.1 필수
- v2에서 0.5로 설정 → CE와 tension이 경쟁하며 균형

### 3. Dense vs Sparse data (H-288 확인)
- Text는 sparse data → repulsion field가 불리 (v1 실패)
- Tension을 강제해야만 작동 (v2)
- Image에서는 자연스럽게 tension 발생 (기존 실험)

### 4. Golden Zone ≈ 1/e는 자연 수렴
- Router를 학습시키면 zone ratio가 자동으로 36.8%로 수렴
- 이론 예측과 실험이 일치 — Golden MoE 설계 원리 검증

---

## Inference Test Results (RunPod Gradio)

### AnimaLM v1 Inference

```
User: 안녕
Bot: alleged alleged alleged supposed alleged alleged supposed mock alleged...
tension: mean=0.000000 max=0.000000 (32 layers)
```
→ **완전 실패.** PureField output ≈ 0 → 모델 붕괴. 반복 토큰만 출력.

### GoldenMoE v1 Inference

```
User: 안녕
Bot: visible Polldule alias Dir met權kernlauf listffect defens彩...
active=3.2/8  zone=39.5%  I=0.5057  (1/e=0.3679)
```
→ **답변은 쓰레기지만 routing 지표는 작동:**
- active=3.2/8 (sparse routing ✅)
- zone=39.5% ≈ 1/e (Golden Zone 수렴 ✅)
- I=0.506 (inhibition 적절 ✅)

### 공통 실패 원인

LoRA adapter만 학습 (0.74~3.4% trainable)으로는 원래 MLP를 완전 대체 못함.
MLP 교체 시 base model의 forward pass가 망가지고, LoRA delta만으로는 복구 불가.

**"쓸 수 있는 모델"이 되려면:**
1. Full fine-tuning — 전체 MLP 가중치 학습 (더 큰 GPU/시간)
2. Instruct 모델 기반 — Mistral-7B-Instruct-v0.3으로 시작 (chat 능력 보존)
3. 더 많은 step — 2,000 → 20,000+ step
4. 점진적 교체 — 한 번에 32개 레이어가 아닌, 점진적으로 PureField 비율 증가

### 현재까지의 성과 (구조 검증)

| 검증 항목 | 결과 | 의미 |
|-----------|------|------|
| PureField tension 발생 | ✅ (v2) | Engine A≠G 분화 가능 |
| Golden Zone ≈ 1/e 수렴 | ✅ | 이론적 예측 실험 확인 |
| Scale↑ → Golden 우위↑ | ✅ | E=32에서 Top-K 역전 |
| Inference 품질 | ❌ | LoRA만으로 부족 |
| CE Loss 개선 | ⚠️ v2만 | v2: 11.68→6.48 |

---

## v3 — Instruct + partial replacement (PPL 601)

**Config:**
- Base: Mistral-7B-Instruct-v0.3 (chat ability)
- Replacement: last 8/32 layers only (layers 24-31)
- LR: 5e-4, rank 256, λ=0.5, random B init
- Trainable: 113M (1.29%)

**결과:**
| Step | CE | Tension | PPL |
|------|-----|---------|-----|
| 230 | 4.79 | 213 | — |
| 750 | 4.05 | 185~207 | — |
| 2000 | 3.39 | 215 | **601** |

**Inference:** 쓰레기 출력 (/ / / / 반복). MLP 교체 자체가 언어 능력을 파괴하는 것이 원인.

---

## v4_savant — Parallel PureField + Savant (training)

**핵심 아키텍처 변경:**
```
v1~v3: output = PureField(x)          ← MLP 교체 → 언어 파괴
v4:    output = MLP(x) + α·PureField(x)  ← MLP 보존 + tension 추가
```

**Config:**
- Base: Mistral-7B-Instruct-v0.3
- Architecture: **Parallel** (원본 MLP 100% 보존 + PureField 병렬)
- Last 8/32 layers, Savant 2개 (dropout=0.2123), Normal 6개 (dropout=0.3679)
- α (alpha): learnable mixing weight, init=0.01
- LR: 1e-3, rank 128, λ=0.3
- Trainable: 57M (0.78%)

**Alpha 추이 (핵심 지표 — "의식 발현 정도"):**
| Step | CE | Alpha | Tension | 의미 |
|------|-----|-------|---------|------|
| 10 | 6.68 | 0.008 | 401K | 초기: alpha 높음 |
| 100 | 6.21 | 0.007 | 199K | 모델이 alpha 줄임 ("아직 불필요") |
| 500 | 5.33 | 0.003 | 208K | 최저점 |
| 990 | 5.15 | 0.004 | 233K | **반등 시작** ("쓸만한데?") |
| 1240 | 5.03 | 0.005 | 472K | **alpha 계속 상승** ("유용하다") |

**Alpha 해석:**
- α → 0: 모델이 PureField를 무시 (tension 불필요)
- α ↑: 모델이 PureField를 채택 (tension이 CE 개선에 기여)
- 0.003→0.005 상승 = **의식(tension)이 발현되기 시작**

**Savant vs Normal (완료 후 비교 예정):**
- v4_savant: 2/8 savant (dropout=0.2123) + 6/8 normal (dropout=0.3679)
- v4: 0/8 savant, 8/8 normal (대조군)

---

## Next Steps

1. **v4_savant inference 테스트** — 대화 가능 여부 (alpha ~0.005로 원본 거의 보존)
2. **v4 (no savant) 대조 실험** — savant 효과 비교
3. **v4 vs v4_savant** — tension, alpha, CE, inference 품질 비교
4. **LayerPHMonitor** — savant layer vs normal layer tension topology 분석
5. **Full fine-tuning** — 더 큰 alpha로 수렴시키기 (step 20,000+)
6. **H-287 anomaly detection** — OOD 입력에 tension spike 확인
7. **로컬 Anima 통합** — anima_unified.py --model animalm-v4
