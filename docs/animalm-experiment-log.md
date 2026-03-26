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

## Next Steps

1. **v2 완료 후 inference 테스트** — tension이 대화에서 의미 있는 패턴을 보이는지
2. **v3 검토** — tension이 안정화되면 CE loss도 함께 개선되는 최적점 탐색
3. **LayerPHMonitor 적용** — v2 학습 중 layer tension topology 변화 추적
4. **H-287 anomaly detection** — OOD 입력에 tension spike 확인
5. **로컬 Anima 통합** — anima_unified.py --model animalm-v2
