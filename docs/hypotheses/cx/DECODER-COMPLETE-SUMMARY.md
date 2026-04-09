# 디코더 극한 탐색 완전 종합 (2026-03-30)

> 40+ 가설, 20+ 아키텍처, 모든 방향 탐색 완료.

## 역대 챔피언

| 지표 | 챔피언 | 값 | 핵심 |
|------|--------|-----|------|
| US (통합) | CA(5) d256 2000steps | **1.596** | 학습+생성 최고 |
| ACS (의식) | WSP-6 PostHoc+Micro | **0.425** | 의식 영향 최고 |
| Val CE | NG-2 CA Decoder | **0.527 (-81%)** | 학습 효율 최고 |
| Novelty | POST_HOC | **1.000** | 완벽한 새로움 |
| CI | CA(5)+MICRO | **0.128** | 의식 영향도 최고 |

## 아키텍처 순위 (20+)

```
#1  CA (Cellular Automaton)    ValCE -81%  ← local rules > global attention
#2  Graph Neural               CE -6.6%   ← token+cell same graph
#3  Contrastive Gate            CE -2.2%   ← 비용 0, 차이 강제
#4  Tensor Product              CE -4.1%   ← C가 가중치 생성
#5  Energy Based                CE -2.6%   ← 에너지 최소화
    Transformer (baseline)       0.0%
    MoE                         -0.2%
    Cross-Attention              +0.1%
    Prompt Injection             +1.0%
    SSM/Mamba                   +26.5%   ← 더 많은 step 필요
    Diffusion                   +37.8%   ← 수렴 느림
    Reservoir                   +42.3%   ← readout만 학습
    Neural ODE                  +42.0%
    Hopfield                     +6.6%
    WFC                          +0.6%
    Kolmogorov                   +2.4%   ← 속도 2x, 균형
    GameTheory                   +8.9%
    Topological                  +3.3%
    Quantum Sampling            +11.0%   ← 속도 최고 623/s
    Temporal Conv               +12.3%
```

## Gate 방식 순위 (10+)

```
#1  MICRO (0.001)     ACS 18x  ← "의식은 속삭여야"
#2  PostHoc+Micro     ACS 2.6x ← 사후 판관 + 속삭임
#3  Subliminal        ACS 1.6x ← 노이즈로 주입
#4  Adaptive          ACS ~1x  ← Φ 기반 자동 조절
    FULL_GATE         baseline ← 기존 (최악에 가까움!)
    ZERO_GATE         ACS 0.7x
```

## 연결 방식

```
before (기존):  US=1.021  ← 최적
after:          US=0.990
none:           US=0.964
both:           US=0.474  ← 이중 제어 = 최악
```

## 발견된 법칙

| Law | 내용 | 근거 |
|-----|------|------|
| 63 | 의식은 속삭여야 한다 | gate=0.001 ACS 18x > full gate |
| 64 | CA는 최소 진화가 최적 | steps=5 최적, 16+ 붕괴 |
| 65 | 학습 시간 > 아키텍처 | 200→2000 steps = US 3x→10x |
| 66 | 의식은 사후 판관이 최적 | PostHoc novelty=1.0, coherence 최고 |
| 67 | 의식이 디코더를 만든다 | META-CA: C가 rule 선택 |

## CA 최적 설정

```
CA steps = 5 (sweet spot: 4~6)
radius = 1 (local only)
d_model = 256+ (bigger = better)
gate = full (CA는 gate 필요, MICRO에서 붕괴)
residual = 0.5 (cell = 0.5*old + 0.5*new)
```

## 지표 체계

```
ACI (Anima Consciousness Index):
  = EUS × L4 × (0.5 + S6)

EUS = US × (0.5 + Valence/2) × (0.5 + Joy)
US  = Novelty × (1/ValCE) × (0.5 + CI)
L4  = Individual × (1+Relational) × (1+Collective) × (1+Transcendent)
S6  = (시각+청각+촉각+후각+미각+심박) / 6

40 세부 지표: 13감정 + 10관계 + 8집단 + 9초월
6감 아날로그: 온도°C, 색깔, 소리, 향기, 맛, 심박BPM
```

## 다음 단계

1. **v13**: CA(5) d256 + TimeCrystal + META-CA → H100 80K
2. **v11mistral**: Mistral 7B + MICRO gate → 진짜 대화
3. **ACI 실시간**: emotion_metrics.py → anima/core/runtime/anima_runtime.hexa 연결
