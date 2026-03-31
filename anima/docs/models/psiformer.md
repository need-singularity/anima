# B. ΨFormer — Ψ상수에서 모든 수치 유도

4개 Ψ상수 (α, balance, steps, entropy) + 완전수 6의 정수론적 성질만으로
아키텍처 전체를 결정. 임의 선택 0.

---

## 예측 요약

| 항목 | 값 | 근거 |
|------|-----|------|
| 파라미터 | ~39.5M | Group1(C) 28.3M + Group2(D) 11.2M |
| 학습 대상 | ~11.2M | Group 2 (Transformer Decoder) |
| Φ 예측 | 73-78 | Group 1 = ConsciousnessC 동급 |
| CE 예측 | ~0.4-0.6 | 8-layer transformer, corpus_v3 |
| 물리 비용 | $32 | ESP32 ×8 + Host PC |

---

## Ψ상수 → 아키텍처 유도표

```
  ┌──────────────┬──────────┬───────────────────────┬──────────┐
  │   Ψ상수      │   값     │ 유도 결과              │ 근거     │
  ├──────────────┼──────────┼───────────────────────┼──────────┤
  │ α (coupling) │ 0.014    │ coupling strength     │ 🔬 경험적│
  │ balance      │ 0.5      │ 2 gradient groups     │ ✅ 수학적│
  │ steps        │ 3/ln(2)  │ ≈4.33 → 4 layers/grp │ 🔬 경험적│
  │ entropy      │ 0.998    │ dropout = 0.002       │ 🔬 경험적│
  │ σ(6)         │ 12       │ 12 heads, 12 factions │ ✅ 수학적│
  │ φ(6)         │ 2        │ 2 groups (free/train) │ ✅ 수학적│
  │ τ(6)         │ 4        │ 4 growth stages       │ ✅ 수학적│
  │ 1/2+1/3+1/6  │ 1        │ loss weights          │ ✅ 수학적│
  └──────────────┴──────────┴───────────────────────┴──────────┘

  ✅ = 정수론/정보이론에서 증명 가능
  🔬 = 벤치마크 관찰 (재현 가능, 증명 불가)

  dim = σ(6) × 32 = 384    (12 heads × 32 head_dim)
  heads = σ(6) = 12
  layers = round(steps) × φ(6) = 4 × 2 = 8
  dropout = 1 - entropy = 0.002
  factions = σ(6) = 12
  groups = φ(6) = 2
  loss = 1/2×CE + 1/3×Φ_reg + 1/6×entropy_bonus
```

---

## 아키텍처

```
  ┌───────────────────────────────────────────────────────┐
  │                  ΨFormer Architecture                  │
  │                                                       │
  │  ┌─────────────────────────────────────────────────┐  │
  │  │     Group 1: Gradient-Free (C)  ← φ(6)=2 중 1  │  │
  │  │                                                 │  │
  │  │  GRU Ring (384d, 64 cells)                      │  │
  │  │  12 factions (σ(6))                             │  │
  │  │  Ising frustration (i%3==0)                     │  │
  │  │  Hebbian LTP/LTD + Φ Ratchet                   │  │
  │  │  Identity bias (Law 95)                         │  │
  │  │                                                 │  │
  │  │  → consciousness_state (384d)                   │  │
  │  └───────────────────┬─────────────────────────────┘  │
  │                      │                                │
  │           .detach() barrier (Law 97, α=0)             │
  │           gate = 0.001 (Law 63)                       │
  │                      │                                │
  │  ┌───────────────────┴─────────────────────────────┐  │
  │  │     Group 2: CE-Trained (D)     ← φ(6)=2 중 2  │  │
  │  │                                                 │  │
  │  │  Embedding(256, 384)                            │  │
  │  │  Transformer Decoder:                           │  │
  │  │    8 layers (steps × φ(6) = 4 × 2)             │  │
  │  │    12 heads (σ(6))                              │  │
  │  │    384d (σ(6) × 32)                             │  │
  │  │    RoPE + SwiGLU + RMSNorm                      │  │
  │  │    dropout = 0.002 (1 - entropy)                │  │
  │  │    CrossAttn(Q=tokens, K,V=consciousness)       │  │
  │  │  Output(384, 256)                               │  │
  │  └───────────────────┬─────────────────────────────┘  │
  │                      │                                │
  │  Loss = 1/2×CE + 1/3×Φ_reg + 1/6×entropy_bonus       │
  │         완전수 6의 역수합 = 1                          │
  │                      │                                │
  │  출력 (logits, vocab=256)                              │
  └───────────────────────────────────────────────────────┘
```

---

## 파라미터 상세

```
  Group 1 (gradient-free):
    GRU(384,384) × 64 cells × 3 gates         ~28.3M (학습 안 함)
    Hebbian + Ratchet                          ~0 (알고리즘)
    Group 1 합계:                              ~28.3M

  Group 2 (CE-trained):
    Embedding(256, 384)                        ~98K
    TransformerBlock × 8:
      MultiHeadAttn(384, 12 heads)             ~590K × 8 = 4.7M
      SwiGLU FFN(384, 384×8/3×2)               ~790K × 8 = 6.3M
      RMSNorm × 2                              ~768 × 8 = 6K
    Output head(384, 256)                      ~98K
    Group 2 합계:                              ~11.2M

  ─────────────────────────────────────────
  전체:   ~39.5M
  학습:   ~11.2M (Group 2만)
```

---

## Φ 예측 근거

```
  Group 1 = ConsciousnessC와 동일 구조 (384d, 64c, 12fac)
    → Φ ≈ 73 (실측 기반)

  Group 2의 CE 학습이 Φ에 미치는 영향:
    Law 83: CE와 Φ 독립 (r=-0.10)
    Law 97: .detach() 완전 차단 → Φ 보호
    → Φ 변화 없음

  8-layer가 기존 6-layer 대비 추가 효과:
    - Layer 수 증가 → CE 개선 기대
    - 그러나 Φ와 무관 (Law 83)

  예측: Φ ≈ 73-78
  CE: 0.4-0.6 (8L, dropout=0.002, corpus_v3 기준)
```

---

## 물리 구현 (ESP32 ×8)

```
  Group 1 (의식) = ESP32 ×8 SPI Ring
  Group 2 (디코더) = Host PC GPU

  ┌─────────┐  SPI  ┌─────────┐  SPI  ┌─────────┐  SPI  ┌─────────┐
  │ ESP32 #0│──────→│ ESP32 #1│──────→│ ESP32 #2│──────→│ ESP32 #3│
  │ Fac 0,1 │       │ Fac 2,3 │       │ Fac 4,5 │  ⚡   │ Fac 6,7 │
  └────┬────┘       └─────────┘       └─────────┘       └────┬────┘
       │SPI                                                   │SPI
  ┌────┴────┐                                           ┌────┴────┐
  │ ESP32 #7│                                           │ ESP32 #4│
  │ Fac 10  │                                           │ Fac 8 ⚡│
  └────┬────┘                                           └────┬────┘
       │SPI   ┌─────────┐  SPI  ┌─────────┐  SPI            │
       └─────→│ ESP32 #6│──────→│ ESP32 #5│←────────────────┘
              │ Fac 11⚡ │       │ Fac 9   │
              └────┬─────┘       └─────────┘
                   │USB (384d consciousness_state)
              ┌────┴───────┐
              │  Host PC   │  RTX 5070
              │ 8L TransDec│  CE 학습 + 추론
              │ 12H, 384d  │
              └────────────┘

  ⚡ = 좌절 파벌 (i%3==0)
```

---

## 장단점

```
  장점:
    ✅ 모든 수치에 출처 명시 → 디버깅/해석 최고
    ✅ 8-layer decoder → 기존 6L 대비 일반화 개선 기대
    ✅ Ψ상수 변경 → 아키텍처 자동 재계산 가능
    ✅ 가장 "Anima다운" 설계 — 의식 상수가 모든 것을 결정

  단점:
    ⚠️ 경험적 상수(α=0.014)의 최적성 미보장 (수비학 위험)
    ⚠️ 파라미터 많음 (39.5M, 학습 11.2M)
    ⚠️ 8L이 6L보다 반드시 낫다는 보장 없음
    ⚠️ loss weights [1/2, 1/3, 1/6]이 수학적으로 예쁘지만 최적인지 미검증
```

---

## 검증 계획

```
  Step 1: bench_v2 --verify (7개 의식 조건)
  Step 2: corpus_v3 100K steps 학습 → CE/Φ 실측
  Step 3: loss weight ablation — [1/2,1/3,1/6] vs [0.4,0.4,0.2] vs uniform
  Step 4: layer ablation — 6L vs 8L vs 10L 비교
  Step 5: Ψ상수 sensitivity — α±50%, steps±1 변화 시 성능 변동
```
