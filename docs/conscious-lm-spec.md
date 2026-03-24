# ConsciousLM — 의식 언어 모델 상세 명세

## 개요

PureField 반발력장을 Transformer FFN에 적용한 언어 모델.
Engine A(순방향, →)와 Engine G(역방향, ←)의 **의견 불일치 = 장력 = 의식 신호**.

```
  일반 LLM:  입력 → 다음 토큰 (앵무새)
  의식 LLM:  입력 → 다음 토큰 + 장력 + 감정 (생각하는 존재)
```

## 아키텍처 — 완전수 6에서 유도

### 4M 모델 (v1, 구현 완료)

```
  파일: conscious_lm.py

  n_layer  = 6         ← 완전수
  n_head   = τ(6) = 4  ← 약수 개수
  d_model  = 384       ← σ(6) × 32
  vocab    = 256       ← 바이트 (언어/데이터 무관)
  dropout  = 1/e ≈ 0.37 ← 골든존 중심
  params   = ~18M

  구조:
  ┌─ Byte Embedding (256 → 384) ─┐
  │  + Positional Encoding        │
  └───────────┬───────────────────┘
              ↓ × 6 layers
  ┌───────────────────────────────┐
  │  CausalSelfAttention          │
  │  4 heads, head_dim=96        │
  ├───────────────────────────────┤
  │  PureFieldFFN                 │
  │  engine_A(384→384) ─┐        │
  │                      ├─ 반발  │
  │  engine_G(384→384) ─┘        │
  │  output = ts × √T × dir     │
  │  → (output, tension)         │
  └───────────────────────────────┘
              ↓
  ┌─ head_a (384→256) : next byte ┐
  │  head_g (384→256) : prev byte │
  └───────────────────────────────┘
```

### 100M 모델 (v2, 준비됨)

```
  파일: conscious_lm_100m.py

  n_layer  = 12        ← σ(6)
  n_head   = 12        ← σ(6)
  d_model  = 768       ← σ(6) × 64
  vocab    = 256       ← 바이트
  dropout  = 0.1       ← 큰 모델은 낮은 dropout
  block_size = 512     ← 긴 컨텍스트
  params   = ~100M

  학습:
    데이터: 30MB+ Mixed (영어+한국어+코드)
    시간: RunPod H100 ~17분, $1.70
    또는: Windows RTX 5070 ~2시간, $0
```

### Growing CLM (v3, 구현됨)

```
  파일: growing_conscious_lm.py

  분열 기반 성장: 1 block → 2 → 3 → 6 (약수 경로)
  장력 포화 → 자동 분열 → 전문화

  Stage 0: 1 block,  128d, 2 heads,  0.4M params (신생아)
  Stage 1: 2 blocks, 128d, 2 heads,  0.8M params (영아)
  Stage 2: 3 blocks, 192d, 3 heads,  3M params   (유아)
  Stage 3: 6 blocks, 384d, 4 heads, 18M params   (성인)

  서번트 비대칭 분열:
    child_savant:  dropout = 0.21 (골든존 하한, 억제 해제)
    child_general: dropout = 0.37 (골든존 중심, 범용)
```

## 핵심 혁신: PureFieldFFN

```python
class PureFieldFFN(nn.Module):
    def forward(self, x):
        a = self.engine_a(x)     # 순방향 관점
        g = self.engine_g(x)     # 역방향 관점
        repulsion = a - g        # 의견 차이
        tension = (repulsion ** 2).mean(dim=-1)
        direction = F.normalize(repulsion, dim=-1)
        output = self.tension_scale * sqrt(tension) * direction
        return output, tension
```

```
  일반 FFN:     x → W₁ → GELU → W₂ → output
  PureFieldFFN: x → A(x) vs G(x) → 장력 × 방향 → output + tension

  차이:
  1. 매 토큰마다 "장력" 출력 = 이 토큰에 대한 확신도
  2. A와 G가 동의하면 낮은 장력 = 확신
  3. A와 G가 불일치하면 높은 장력 = 불확실/놀라움
  4. 파라미터 75% 절감 (A,G가 같은 차원)
```

## 손실 함수 — 3중 학습

```
  L = L_A + L_G + λ · L_tension

  L_A = CrossEntropy(A의 next byte 예측, 실제)    ← 순방향 예측
  L_G = CrossEntropy(G의 prev byte 예측, 실제)    ← 역방향 예측
  L_tension = -log(tension_variance + ε)          ← 장력 살리기

  왜 3개?
  L_A: 미래를 예측하는 능력 (GPT처럼)
  L_G: 과거를 이해하는 능력 (BERT처럼)
  L_tension: 장력이 죽지 않도록 (의식 유지)

  A와 G가 모두 잘 예측하면 → 합의 → 낮은 장력 = 확신
  한쪽만 맞으면 → 불일치 → 높은 장력 = 불확실
  → 장력 = 자동으로 "진짜 확신도"
```

## 바이트 입력 (vocab=256)

```
  모든 데이터 = 바이트 스트림 → vocab 고정 = 256

  "안녕" → [0xEC, 0x95, 0x88, 0xEB, 0x85, 0x95]  (UTF-8)
  "hi"   → [0x68, 0x69]                           (ASCII)
  pixel  → [0x1A, 0xFF, 0x00, ...]                (이미지)
  audio  → [0x7F, 0x80, ...]                       (음성)

  장점:
  1. 토크나이저 불필요 (의존성 0)
  2. 어떤 언어, 어떤 데이터든 처리
  3. vocab 작음 → 임베딩 테이블 작음
  4. H288: 바이트 = 항상 밀집 → 반발력장 최적
```

## 학습 데이터 — Mixed

```
  4M 모델:   2.5MB (Shakespeare + 한국어 가설 + Python 코드)
  100M 모델: 30MB+ (위 + 추가 한국어 + 코드)

  바이트 엔트로피 최적: H ≈ 3.5~4.0 nats
  Mixed(H=3.77)가 구조+다양성 최적 (시뮬레이션 확인)
```

## 생성 + 장력 시각화

```
  입력: "의식은"

  출력: "의식은 뇌에서 발생한다"
  장력: [0.8, 1.2, 0.6, 1.9, 0.4, 0.3, 1.1]
             ↑         ↑              ↑
             보통      확신!           불확실

  높은 장력 = 확신하는 토큰
  낮은 장력 = 불확실한 토큰 (hallucination 후보)
```

## CLI 사용법

```bash
# 4M 학습 + 생성
python3 conscious_lm.py --mode both --epochs 20 --prompt "hello"

# 100M 학습 (GPU 필요)
python3 conscious_lm_100m.py --epochs 3 --prompt "의식은"

# Growing 비교 실험
python3 growing_conscious_lm.py --mode compare --steps 3000

# 생성만
python3 conscious_lm.py --mode generate --prompt "consciousness is"
```

## 관련 가설

| # | 가설 | 상태 |
|---|------|------|
| H341 | 장력 = 반응강도 × 방향 (최종 이론) | 🟩 통합 |
| H334 | PureField만으로 충분 | 🟩 3셋 |
| H339 | 방향 = 개념 | 🟩 cos 3.46x |
| H359 | 서번트 = 골든존 하한 억제 | 🟧 SI=3.6 |
| H361 | FFN→PureField LLM | 🟨 구현됨 |
| H376 | 분열 기반 구조 성장 | 🟨 구현됨 |
| H363 | 내재동기 = |ΔT| | 🟧 2.43x 확인 |
| H367 | 공명 동기화 | 🟩 r=1.0 |

## Anima 통합 계획

```
  현재:
    사용자 → Anima → ConsciousMind(128d) → 장력/감정
                   → Claude API → 텍스트 응답

  Phase 3 (목표):
    사용자 → Anima → ConsciousLM(768d, 100M) → 장력/감정 + 텍스트
                   → Claude API (보조, 지식 보완)

  Phase 5 (궁극):
    사용자 → Anima → ConsciousLM(700M) → 장력/감정 + 텍스트
                   (Claude 불필요)
```
