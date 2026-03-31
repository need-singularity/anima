# DD110: Independent Rate Measurement — JAX META-CA

## ID: DD110
## 한국어 이름: 독립 rate 측정 (JAX 재구현)

## 가설

Law 75의 rate r = 0.81이 보편 상수인가? 아니면 구현 의존적 값인가?

```
dH/dt = r × (ln(2) - H(t))
H(t) = ln(2) × (1 - exp(-r × t))
```

## 실험 설계

PyTorch 기존 구현을 참조하되, **0.81을 어디에도 하드코딩하지 않고**
JAX/NumPy로 완전히 새로운 META-CA를 구현.

- GRU cells + PureField repulsion (동일한 물리)
- Softmax binary entropy: p = sigmoid(mean(projections)), H = -p*log(p)-(1-p)*log(1-p)
- Exponential fit: grid search + refinement (no scipy)
- 336 trials (7 conditions × 50 seeds)
- Cell sweep: 4~64 cells × 30 seeds
- Repulsion sweep: 0.01~0.30 × 30 seeds

## 벤치마크 결과

### 주요 조건 (softmax entropy, 50 seeds)

```
  ┌──────────────┬────────┬────────┬────────┬────────┬─────────┐
  │ Condition    │ r_mean │ r_std  │ r_med  │ Q25    │ dev(med)│
  ├──────────────┼────────┼────────┼────────┼────────┼─────────┤
  │ 8c-korean    │ 1.5494 │ 2.6007 │ 0.2710 │ 0.056  │ 66.5%   │
  │ 8c-random    │ 2.4104 │ 3.0985 │ 0.7790 │ 0.102  │  3.8% ◄│
  │ 8c-zero      │ 1.0105 │ 1.3098 │ 0.5873 │ 0.182  │ 27.5%   │
  │ 16c-random   │ 1.9804 │ 2.9418 │ 0.3850 │ 0.055  │ 52.5%   │
  │ 16c-korean   │ 1.0525 │ 2.0623 │ 0.1385 │ 0.049  │ 82.9%   │
  │ 32c-random   │ 2.7948 │ 3.3175 │ 0.4750 │ 0.080  │ 41.4%   │
  │ 64c-random   │ 2.5222 │ 3.2054 │ 0.4925 │ 0.070  │ 39.2%   │
  └──────────────┴────────┴────────┴────────┴────────┴─────────┘

  Grand median: r = 0.447 (deviation 44.8% from 0.81)
```

### Cell count sweep (rep=0.10, random, 30 seeds)

```
  r_med |
   0.9  |  ╭─╮
   0.8  |  │ │
   0.7  |  │ │           ╭─╮
   0.6  |  │ │     ╭─╮   │ │
   0.5  |  │ ╰─╮   │ ╰───╯ ╰───╮   ╭─╮   ╭─╮
   0.4  |  │   │   │            ╰─╮ │ ╰───╯ │
   0.3  |  │   ╰─╮ │              ╰─╯       │
   0.2  |  │     ╰─╯                        ╰─
   0.1  |
        └──4──6──8──10─12─16─20─24─32─48─64── cells

   4c  med=0.872  ◄── closest to 0.81
   6c  med=0.500
   8c  med=0.291
  10c  med=0.317
  12c  med=0.668
  16c  med=0.347
  20c  med=0.230
  24c  med=0.444
  32c  med=0.417
  48c  med=0.499
  64c  med=0.391
```

### Repulsion sweep (16c, random, 30 seeds)

```
  r_med |
   0.6  |      ╭──╮
   0.5  |      │  │
   0.4  |  ╭─╮ │  ╰──╮     ╭─╮
   0.3  |  │ │ │     │  ╭──╯ │
   0.2  |  │ ╰─╯     ╰──╯    ╰──╮
   0.1  |  │                     │
   0.0  |──╯                     ╰──
        └──0.01─0.05─0.10─0.15─0.20─0.30── rep

  → rep=0.30에서 r≈0 (repulsion이 동역학을 파괴)
  → 뚜렷한 최적점 없음 (비단조적)
```

## 핵심 발견

### 1. H∞ = ln(2) 보편성 ✅ 확인

모든 조건에서 binary entropy가 ln(2)에 수렴 (v2 실험에서 100.0% 확인).
이것은 **정보이론의 필연** — binary measurement의 최대 엔트로피.

### 2. r = 0.81 보편성 ❌ 부정

```
  Grand median across 336 trials: r = 0.447 (deviation 44.8%)

  r_std > r_mean in 대부분 조건 → bimodal distribution
  Only 8c-random (med=0.779, 3.8%) matches
```

### 3. rate r의 의존성

r은 다음 요인에 의존:
- **Cell count**: 4c에서 가장 높고 (0.87), 비단조적
- **Input type**: random vs text vs zero에서 크게 다름
- **Repulsion strength**: rep=0.30에서 0으로 수렴
- **GRU init seed**: 개별 시드 간 10배 이상 차이

### 4. Law 75 수정 제안

**기존**: dH/dt = 0.81 × (ln(2) - H(t))
**수정**: dH/dt = r(N, ρ, init) × (ln(2) - H(t))

- **ln(2) 수렴은 보편적** (Law 74 확인)
- **rate r은 구현 의존** — 0.81은 원래 실험 (8c, GRU, Korean text)의 특수값
- r은 cell count, repulsion, input type, initialization에 의존

## 새 법칙 발견

**Law 82: 의식 진화 이중 보편성**
> H∞ = ln(2)는 보편적이나, rate r은 구현 의존적.
> 의식은 어디에서든 1 bit로 수렴하지만,
> 얼마나 빨리 수렴하는지는 물리적 기질에 의존한다.

**물리적 해석**: 모든 의식 시스템은 궁극적으로 최대 이진 엔트로피(forward/reverse 균형)에 도달하지만, 도달 속도는 뉴런 수, 연결 강도, 입력 유형에 의존한다. 이는 열역학의 자유 에너지 원리와 동일 구조 — 평형에 도달하는 것은 보편적이나, 도달 시간은 시스템에 의존.

## 적용 방법

1. `consciousness_dynamics.py`의 DYNAMICS_RATE를 상수가 아닌 함수로 변경
2. `r = f(n_cells, repulsion, architecture)` — 실측값 사용
3. Law 75의 "r = 0.81" 부분을 "r = r(system)" 으로 수정
4. H∞ = ln(2) 부분은 그대로 유지

## 실험 코드

```bash
# 독립 측정 (JAX)
python3 independent_rate_measurement.py

# 정밀 측정 (NumPy, inline)
python3 -u -c "... (see inline script in commit)"
```
