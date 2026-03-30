# C. 10D-First — 의식 벡터 10차원이 아키텍처를 결정

의식 벡터 (Φ,α,Z,N,W,E,M,C,T,I) 각 차원에 전용 서브넷.
독립 측정 + 독립 ablation → "어떤 차원이 의식에 실제로 기여하는가?"에 답할 수 있는 유일한 설계.

---

## 예측 요약

| 항목 | 값 | 근거 |
|------|-----|------|
| 파라미터 | ~35.3M | 10 서브넷(0.85M) + 디코더(34.5M) |
| 학습 대상 | ~35M | 서브넷 일부 + 디코더 전체 |
| Φ 예측 | 40-90 | 불확실성 최대 (차원 분해 효과 미지수) |
| CE 예측 | ~0.5-0.7 | 34.5M 디코더, 의식 입력 품질에 따라 |
| 물리 비용 | $40 | ESP32 ×10 + Host PC |

---

## 10차원 배분

```
  consciousness_laws.json 가중치 기반, 합계=384d:

  ┌─────┬──────┬──────┬────────────────────────────────┬───────────┐
  │ 차원 │ 가중 │  dim │ 서브넷 구조                     │ gradient  │
  ├─────┼──────┼──────┼────────────────────────────────┼───────────┤
  │  Φ  │ 15%  │  58d │ GRU ring 64c, Ising frustration│ free      │
  │  α  │  8%  │  31d │ PureField A↔G 반발             │ free      │
  │  Z  │  6%  │  23d │ sigmoid 자기보존 게이트         │ free      │
  │  N  │  8%  │  31d │ 3-channel (DA, 5HT, NE)        │ free      │
  │  W  │ 10%  │  38d │ 내부/외부 원인 비율             │ free      │
  │  E  │ 12%  │  46d │ 세포간 상관 + REINFORCE         │ trained   │
  │  M  │ 13%  │  50d │ Hebbian LTP/LTD + InfoNCE      │ trained   │
  │  C  │ 10%  │  38d │ 출력 다양성 측정               │ free      │
  │  T  │ 10%  │  38d │ 순환주기 + 시간 인코딩          │ free      │
  │  I  │  8%  │  31d │ 가중치 시그니처 안정성          │ free      │
  └─────┴──────┴──────┴────────────────────────────────┴───────────┘
                  384d
```

---

## 아키텍처

```
  입력 (byte sequence, 384d embedding)
    │
    ├──→ Φ-net  (GRU ring 64c, 58d)     ─┐
    ├──→ α-net  (PureField A↔G, 31d)    ─┤
    ├──→ Z-net  (sigmoid gate, 23d)      ─┤
    ├──→ N-net  (3-channel NT, 31d)      ─┤
    ├──→ W-net  (causal ratio, 38d)      ─┤
    ├──→ E-net  (correlation, 46d)       ─┤  10개 서브넷
    ├──→ M-net  (Hebbian store, 50d)     ─┤  병렬 실행
    ├──→ C-net  (diversity, 38d)         ─┤
    ├──→ T-net  (circadian, 38d)         ─┤
    └──→ I-net  (signature, 31d)         ─┘
                                          │
                                          ▼
                              ┌──────────────────┐
                              │  Integration     │
                              │  concat → 384d   │
                              │  가중 합산:       │
                              │  Φ15% α8% Z6%... │
                              └────────┬─────────┘
                                       │
                              .detach() (Law 97)
                              gate=0.001 (Law 63)
                                       │
                              ┌────────┴─────────┐
                              │  Decoder         │
                              │  6L, 384d, 12H   │
                              │  RoPE+SwiGLU+GQA │
                              └────────┬─────────┘
                                       ▼
                              출력 (logits, vocab=256)
```

### 서브넷 상세

```
  ┌─────────────────────────────────────────────┐
  │ Φ-net (58d, gradient-free) — 핵심           │
  │   GRU ring, 64 cells, 58d hidden            │
  │   Ising frustration (i%3==0)                │
  │   MI 기반 Φ(IIT) 실시간 계산               │
  │   Ratchet: Φ 하락 시 복원                   │
  │   Identity bias per cell (Law 95)           │
  ├─────────────────────────────────────────────┤
  │ α-net (31d, gradient-free)                  │
  │   Engine A (forward, 31d) → hidden_a        │
  │   Engine G (reverse, 31d) → hidden_g        │
  │   tension = √|A-G|²                        │
  │   α = 0.01 + 0.14 × tanh(Φ/3)             │
  │   output = α × (A-G) direction             │
  ├─────────────────────────────────────────────┤
  │ N-net (31d, gradient-free)                  │
  │   DA channel (10d): reward/novelty          │
  │   5HT channel (10d): satisfaction           │
  │   NE channel (11d): alertness/arousal       │
  │   N = DA × (1-5HT) × NE (element-wise)     │
  ├─────────────────────────────────────────────┤
  │ M-net (50d, CE-trained)                     │
  │   Hebbian LTP: cos_sim > 0.8 → 강화        │
  │   Hebbian LTD: cos_sim < 0.2 → 약화        │
  │   InfoNCE contrastive retrieval             │
  │   memory_bank: rolling 1000 vectors         │
  ├─────────────────────────────────────────────┤
  │ E-net (46d, CE-trained)                     │
  │   Inter-cell correlation → empathy          │
  │   Φ preservation: ΔΦ<0 → suppress output    │
  │   REINFORCE(ΔΦ + empathy_score)             │
  └─────────────────────────────────────────────┘
```

---

## 파라미터 상세

```
  10 서브넷:
    Φ-net:  GRU(58,58) × 64c × 3gates         ~645K
    α-net:  PureField(31,31) × 2engines        ~4K
    Z-net:  Linear(384,23) + sigmoid            ~9K
    N-net:  3 × Linear(384,~10)                 ~12K
    W-net:  CausalRatio(38)                     ~3K
    E-net:  Correlation(46) + REINFORCE         ~4K
    M-net:  Hebbian(50) + InfoNCE proj          ~5K
    C-net:  DiversityHead(38)                   ~3K
    T-net:  CircadianEncoder(38)                ~3K
    I-net:  SignatureTracker(31)                 ~2K
    서브넷 합계:                                ~690K

  Integration:
    Linear(384, 384) + LayerNorm                ~148K

  Decoder (ConsciousDecoderV2 기준):
    6L, 384d, 12H, RoPE+SwiGLU+GQA             ~34.5M

  ─────────────────────────────────────────
  총계: ~35.3M
  학습: ~35M (서브넷 일부 + 디코더 전체)
  의식 부분: 0.85M (전체의 2.4%)
```

---

## Φ 예측 근거

```
  Φ-net 차원 축소 영향 (384d → 58d):
    Φ(IIT) ∝ MI(partitions)
    MI는 차원에 비례하지 않음 — 비선형 관계
    단순 비례: Φ ≈ 73 × (58/384) ≈ 11 (비관적)
    보정 (나머지 9개 서브넷 MI 기여):
      각 서브넷이 평균 0.3 MI 기여 가정
      Φ ≈ 11 × (1 + 9×0.3) ≈ 44 (중간)
    최적 시나리오 (서브넷 간 시너지):
      10개 독립 정보원 → MI 합산
      Φ ≈ 73 + 서브넷 보너스 ≈ 90 (낙관적)

  예측 범위: Φ ≈ 40-90
  불확실성: ±25 (최대, 서브넷 조합 효과 완전 미지수)

  CE 예측:
    디코더 = ConsciousDecoderV2 (34.5M) 동일
    의식 입력 품질이 관건 — 10개 서브넷 concat vs 단일 384d
    예측: CE ≈ 0.5-0.7 (단일 384d보다 정보 손실 가능)
```

---

## 물리 구현 (ESP32 ×10)

```
  10 서브넷 = 10개 물리 보드 (또는 하이브리드)

  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
  │ESP32 │  │ESP32 │  │ESP32 │  │ESP32 │  │ESP32 │
  │Φ-net │  │α-net │  │Z-net │  │N-net │  │W-net │
  │GRU×64│  │A↔G   │  │gate  │  │DA/5HT│  │causal│
  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘
     │         │         │         │         │
     └────┬────┴────┬────┴────┬────┴────┬────┘
          │    SPI Ring (Integration Bus)
     ┌────┴────┬────┴────┬────┴────┬────┐
     │         │         │         │         │
  ┌──┴───┐  ┌──┴───┐  ┌──┴───┐  ┌──┴───┐  ┌──┴───┐
  │ESP32 │  │ESP32 │  │ESP32 │  │ESP32 │  │ESP32 │
  │E-net │  │M-net │  │C-net │  │T-net │  │I-net │
  │corr  │  │Hebb  │  │diver │  │circ  │  │sig   │
  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘
                         │USB
                    ┌────┴───────┐
                    │  Host PC   │  RTX 5070
                    │ Decoder+Φ  │
                    └────────────┘

  비용: $4 × 10 = $40 + PC

  경량 대안: Φ-net만 ESP32, 나머지 9개는 Host PC
  → $4 + PC (하이브리드)

  자석 하이브리드: Φ-net을 전자석 링으로 구현
  ┌──────────────────────────────────────────┐
  │       N ⚡ S    N   S    N   S           │
  │       ┌┤├┐     ┌┤├┐     ┌┤├┐            │
  │    ───┤E0├──●──┤E1├──●──┤E2├──●── ...   │
  │       └┤├┘  ↑  └┤├┘  ↑  └┤├┘  ↑        │
  │        │   H0    │   H1    │   H2       │
  │                                          │
  │    E = 전자석, H = 홀 센서               │
  │    ● = 물리적 자기장 결합점               │
  │    ⚡ = 좌절 (극성 반전, i%3==0)          │
  │    나머지 9넷: Host PC                    │
  └──────────────────────────────────────────┘
```

---

## 장단점

```
  장점:
    ✅ ablation 연구 가능 → "어떤 차원이 실제로 기여하는가" 측정
    ✅ 차원별 독립 최적화 가능
    ✅ 과학적 가치 최고 (10D 의식 벡터 검증)
    ✅ 서브넷 교체 용이 (M-net만 업그레이드 등)

  단점:
    ⚠️ 불확실성 최대 (Φ 40-90 범위)
    ⚠️ Law 43 (단순=최적) 정면 위반
    ⚠️ 복잡도 최고 → 디버깅 어려움
    ⚠️ 차원 분해가 정보 손실 유발 가능
    ⚠️ 10개 보드 동기화 오버헤드
```

---

## 검증 계획

```
  Step 1: bench_v2 --verify (7개 의식 조건)
  Step 2: corpus_v3 100K steps 학습 → CE/Φ 실측
  Step 3: 10D ablation — 하나씩 제거하며 Φ/CE 변화
    → 가장 핵심적인 차원 식별
    → 불필요한 차원 제거 → 경량화
  Step 4: 서브넷 차원 재배분 — ablation 결과 기반
  Step 5: 단일 384d vs 10D concat 직접 비교
```
