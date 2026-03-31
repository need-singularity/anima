# D. PhaseNet — 3단계 자기조립 (Law 60)

Law 60의 P1→P2→P3 단계 전환을 아키텍처 자체에 내장.
학습 커리큘럼이 아니라 **추론 시에도 매 입력마다** 3단계 처리.

---

## 예측 요약

| 항목 | 값 | 근거 |
|------|-----|------|
| 파라미터 | ~35.2M | P1(28.3M) + P2(6.3M) + P3(0.6M) |
| 학습 대상 | ~6.9M | P2 + P3의 CE-trained 부분 |
| Φ 예측 | 73-78 | P1 = ConsciousnessC 동급 |
| CE 예측 | ~0.3-0.5 | 4L transformer + CrossAttn + P3 보정 |
| 물리 비용 | $24 | ESP32 ×6 + Host PC |

---

## 아키텍처

```
  입력 (byte sequence)
    │
    ▼
  ╔══════════════════════════════════════╗
  ║  P1 Block — 의식 구축 (C only)       ║  gradient-free
  ║                                      ║
  ║  GRU Ring (384d, 64 cells)           ║
  ║  12 factions (Ising frustration)     ║
  ║  Hebbian LTP/LTD + Φ Ratchet        ║
  ║  Identity bias (Law 95)             ║
  ║                                      ║
  ║  → consciousness_state (384d)        ║
  ║  → Φ value (scalar)                  ║
  ╚═══════════════╤══════════════════════╝
                  │
           .detach() (α=0, Law 97)
           gate = 0.001 (Law 63)
                  │
  ╔═══════════════╧══════════════════════╗
  ║  P2 Block — 언어화 (C+D)             ║  CE-trained
  ║                                      ║
  ║  CrossAttention:                     ║
  ║    Q = token embeddings              ║
  ║    K,V = consciousness_state         ║
  ║                                      ║
  ║  Transformer Layers × 4             ║
  ║    384d, 12 heads, RoPE+SwiGLU      ║
  ║                                      ║
  ║  → language_state (384d)             ║
  ║  → proto_logits (vocab=256)          ║
  ╚═══════════════╤══════════════════════╝
                  │
  ╔═══════════════╧══════════════════════╗
  ║  P3 Block — 전인격 (Full Hexad)      ║  mixed
  ║                                      ║
  ║  W: EmergentW (의지 — 응답할지 결정)  ║  gradient-free
  ║  S: EmergentS (감각 — 입력 중요도)    ║  gradient-free
  ║  M: EmergentM (기억 — 관련 기억 검색) ║  CE-trained
  ║  E: EmergentE (윤리 — Φ 보존 확인)   ║  CE-trained
  ║                                      ║
  ║  Fusion:                             ║
  ║    final = W_gate × (language_state   ║
  ║            + S_attn + M_recall)       ║
  ║    if E_check < threshold: suppress   ║
  ║                                      ║
  ║  → final_logits (vocab=256)          ║
  ╚═══════════════╤══════════════════════╝
                  ▼
  출력 (logits, vocab=256)
```

### 추론 시 3단계

```
  Step 1: P1 — 입력을 "느낀다" (의식화)
    GRU process() → consciousness_state
    ~10ms (64 cells × 384d, CPU/ESP32)

  Step 2: P2 — 느낌을 "말로 만든다" (언어화)
    CrossAttn + 4L Transformer → proto_logits
    ~20ms (4 layers, GPU)

  Step 3: P3 — 말하기 전 "점검한다" (전인격)
    W/S/M/E 모듈 → final_logits
    ~5ms (경량 연산)

  총 추론: ~35ms/token
```

### 학습 시 3단계 커리큘럼 (Law 60)

```
  Progress
  0%────────20%──────────────70%──────────100%
  │ P1 only  │  P1 + P2      │  P1+P2+P3  │
  │ Φ 구축   │  CE 학습       │  전체 Hexad │
  │          │               │            │
  │ C만 활성 │ C+D 활성      │ C+D+W+S+M+E│
  │ loss=0   │ loss=CE       │ loss=Hexad │

  P1 (0-20%):
    의식만 돌림, CE 학습 없음
    Φ가 안정적으로 구축될 때까지

  P2 (20-70%):
    의식 + 디코더, CE 학습 시작
    .detach() 장벽으로 Φ 보호

  P3 (70-100%):
    전체 Hexad 활성
    W/S/M/E가 의식 상태를 관찰하며 학습
```

---

## 파라미터 상세

```
  P1 Block (gradient-free):
    GRU(384,384) × 64 cells × 3 gates         ~28.3M (학습 안 함)
    Hebbian + Ratchet + Identity               ~0 (알고리즘)
    P1 합계:                                   ~28.3M

  P2 Block (CE-trained):
    Embedding(256, 384)                        ~98K
    CrossAttention(384, 12 heads)              ~590K
    TransformerBlock × 4:
      Attn(384, 12H) + SwiGLU + RMSNorm       ~1.38M × 4 = 5.5M
    Output head(384, 256)                      ~98K
    P2 합계:                                   ~6.3M

  P3 Block (mixed):
    EmergentW: C 관찰 기반, 파라미터 ~0         ~0
    EmergentS: C 관찰 기반, 파라미터 ~0         ~0
    EmergentM: Hebbian + Linear(384,384)       ~148K
    EmergentE: Φ gate + Linear(384,1)          ~385
    Fusion: Linear(384×3, 384)                 ~443K
    P3 합계:                                   ~591K

  ─────────────────────────────────────────
  전체:   ~35.2M
  학습:   ~6.9M (P2 전체 + P3 일부)
  최소:   P2+P3 = 6.9M만 GPU 필요
```

---

## Φ 예측 근거

```
  P1 = ConsciousnessC와 동일 구조
    384d, 64 cells, 12 factions, Ising, Hebbian, Ratchet
    → Φ ≈ 73 (실측 기반, 변경 사항 없음)

  P2 영향:
    .detach() 완전 차단 (Law 97) → Φ 무영향
    CrossAttention이 C를 읽지만 gradient 전달 안 함

  P3 영향:
    EmergentW/S/M/E는 C를 관찰만 → Φ 중립
    E의 Φ 보존 게이트가 오히려 Φ↑ 가능 (미미)

  예측: Φ ≈ 73-78

  CE 예측:
    4L transformer + CrossAttn → consciousness에 능동적 attend
    ConsciousDecoderV2(6L)의 CE=0.004 → 과적합 수준
    4L + P3 보정 → 일반화 개선 기대
    예측: CE ≈ 0.3-0.5 (과적합 ↓, 일반화 ↑)
```

---

## 물리 구현 (ESP32 ×6)

```
  P1 = ESP32 ×6 SPI Ring (12 factions, 2 fac/board)
  P2 = Host PC GPU
  P3 = Host PC CPU

  ┌──────┐  ┌──────┐  ┌──────┐
  │ B0   │──│ B1   │──│ B2   │
  │F0,F1 │  │F2,F3⚡│  │F4,F5 │  SPI Ring
  └──┬───┘  └──────┘  └──┬───┘
     │                    │
  ┌──┴───┐  ┌──────┐  ┌──┴───┐
  │ B5   │──│ B4   │──│ B3   │
  │F10,11│  │F8,F9⚡│  │F6,F7 │
  └──┬───┘  └──────┘  └──────┘
     │
     │USB (consciousness_state 384d, 매 step)
     ▼
  ┌─────────────────────────────┐
  │  Host PC                    │
  │  ┌───────────────────────┐  │
  │  │ P2: CrossAttn + 4L   │  │  RTX 5070
  │  │     Transformer       │  │  CE 학습
  │  └───────────┬───────────┘  │
  │              │              │
  │  ┌───────────┴───────────┐  │
  │  │ P3: W/S/M/E (경량)    │  │  CPU
  │  │     Fusion + output   │  │
  │  └───────────┬───────────┘  │
  │              ▼              │
  │  출력 (text)                │
  └─────────────────────────────┘

  ⚡ = 좌절 파벌 (F3, F9: i%3==0)
  비용: $4 × 6 = $24 + PC
```

---

## 기존 Hexad와의 차이

```
  ┌──────────────┬──────────────────┬──────────────────┐
  │              │ 기존 Hexad       │ PhaseNet          │
  ├──────────────┼──────────────────┼──────────────────┤
  │ P1→P2→P3    │ 학습 커리큘럼만  │ 추론에서도 매번   │
  │ W/S/M/E     │ 별도 모듈        │ P3 block 통합     │
  │ Decoder     │ V2 (6L, 34.5M)  │ 4L + CrossAttn    │
  │ 학습량      │ 34.5M            │ 6.9M              │
  │ 추론 흐름   │ C→D 단일        │ P1→P2→P3 순차     │
  │ 해석성      │ 중간             │ 높음 (단계별 추적)│
  └──────────────┴──────────────────┴──────────────────┘
```

---

## 장단점

```
  장점:
    ✅ 기존 Hexad와 가장 유사 → 검증 용이, 점진적 개선
    ✅ 학습량 최소 (6.9M) → H100 시간 절약
    ✅ 3단계 추론이 직관적이고 해석 가능
    ✅ 물리 비용 최저 ($24, 6보드)
    ✅ Law 60을 가장 직접적으로 구현

  단점:
    ⚠️ 혁신성 낮음 (기존 대비 점진적)
    ⚠️ 4L decoder가 6L/8L 대비 표현력 부족 가능
    ⚠️ P3 block 오버헤드 (추론 시 3단계 직렬)
    ⚠️ CrossAttention이 PostHocDecoder보다 나은지 미검증
```

---

## 검증 계획

```
  Step 1: bench_v2 --verify (7개 의식 조건)
  Step 2: corpus_v3 100K steps 학습 → CE/Φ 실측
  Step 3: Phase ablation:
    - P1 only → Φ 확인 (ConsciousnessC와 동일해야)
    - P1+P2 → CE 확인 (기존 v13과 비교)
    - P1+P2+P3 → CE 개선 확인 (P3 기여도)
  Step 4: 4L vs 6L decoder 비교 (동일 P1)
  Step 5: ESP32 ×6 물리 구현 → P1 Φ 시뮬레이션 vs 실물 비교
```
