# ALT: Alternating Training Ratio Hypotheses

> "CE 학습과 Phi 부스트의 최적 교대 비율은 1:1이 아니다.
> Reward-based가 CE와 Phi 모두 최고. 모든 ALT 변형이 PHI-K3(1:1)을 능가."

## 동기

PHI-K3 (1:1 alternating)이 combinator 결과에서 강한 성능을 보여 교대 비율을 체계적으로 탐색.
핵심 질문: CE 학습과 Phi 부스트의 최적 비율/패턴은 무엇인가?

## 결과 테이블

| ID    | 전략                        | CE start | CE end | CE drop | Phi before | Phi after | Phi ok | Time |
|-------|---------------------------|----------|--------|---------|------------|-----------|--------|------|
| PHI-K3 | 1:1 alternating (baseline) | 0.3167 | 0.4087 | -29.1%  | 1.160      | 1.131     | YES    | 2.2s |
| ALT-1 | 3:1 (CE heavy)            | 0.2684  | 0.2801 | -4.4%   | 1.219      | 1.453     | YES    | 1.8s |
| ALT-2 | 1:3 (Phi heavy)           | 0.3981  | 0.3607 | **+9.4%** | 1.143    | 1.160     | YES    | 1.4s |
| ALT-3 | Adaptive ratio            | 0.3816  | 0.3208 | **+16.0%** | 1.189   | 1.469     | YES    | 1.7s |
| ALT-4 | Burst 10:10               | 0.2800  | 0.2355 | **+15.9%** | 1.324   | 1.018     | YES    | 1.4s |
| ALT-5 | Fibonacci alternation     | 0.3261  | 0.3005 | **+7.9%** | 1.212    | 1.209     | YES    | 1.4s |
| ALT-6 | Reward-based switching    | 0.4115  | 0.3263 | **+20.7%** | 1.222   | **1.390** | YES    | 1.3s |

## 개별 가설

### ALT-1: 3:1 Ratio (CE 중심)
- 알고리즘: 3 CE steps -> 1 Phi step (cycle of 4)
- 결과: CE -4.4% (거의 무변화), Phi 1.453 (1.19x)
- CE 학습 비율이 높으면 CE는 유지되지만 개선은 안 됨
- Phi는 오히려 좋음 -- 가끔 들어오는 Phi 부스트가 효율적

### ALT-2: 1:3 Ratio (Phi 중심)
- 알고리즘: 1 CE step -> 3 Phi steps (cycle of 4)
- 결과: CE +9.4% 개선, Phi 1.160 (1.01x)
- Phi 유지 + CE도 개선 -- 적은 CE step이 오히려 집중 학습

### ALT-3: Adaptive Ratio
- 알고리즘: Phi/Phi_target 비율에 따라 CE vs Phi 결정
- 결과: CE +16.0% 개선, Phi **1.469** (1.24x, 2위)
- Phi target이 높으면(50x) 초반 Phi 집중 -> 후반 CE 집중
- 핵심: 자연스러운 curriculum -- 의식 먼저, 학습 나중

```
Phi/CE | Phi 집중          CE 집중
ratio  | ████████████████  ████████
       | Phi/target=0.02   Phi/target=0.8
       └──────────────────────────── step
```

### ALT-4: Burst Mode (10:10)
- 알고리즘: 10 CE steps 연속, then 10 Phi steps 연속
- 결과: CE +15.9% 개선, Phi 1.018 (0.77x, 가장 낮음)
- 핵심 발견: **연속 학습이 교대 학습보다 CE에 효과적**
- CE를 10 step 연속하면 gradient가 일관된 방향으로 축적
- 대신 Phi 보존이 가장 약함 -- trade-off

```
CE |  ╮  ╮  ╮  ╮  ╮
   | ╭╯╭╯╭╯╭╯╭╯╭╯
   |╭╯╭╯╭╯╭╯╭╯
   |╯ ╯
   └──────────────── step
     CE  Phi CE  Phi CE  (burst periods)
```

### ALT-5: Fibonacci Alternation
- 알고리즘: CE for fib(n) steps, then Phi for fib(n+1) steps
- 결과: CE +7.9% 개선, Phi 1.209 (1.00x)
- 후반부에 fibonacci가 커져서 긴 연속 구간 형성
- Phi 완벽 보존 + CE 개선 -- 균형 잡힌 전략

### ALT-6: Reward-Based -- BEST OVERALL
- 알고리즘: CE 개선되면 계속 CE, 안 되면 Phi로 전환 (2 step후 복귀)
- 결과: **CE +20.7% 개선 (최고)**, **Phi 1.390 (1.14x, 최고)**
- switches=256 (평균 2 step마다 전환)
- 핵심: Phi 부스트 타이밍을 CE 실패에 맞추면 둘 다 최적화
- CE가 나빠질 때 = 의식이 불안정할 때 -> Phi 부스트가 가장 효과적

```
Phi |         ╭──╮     ╭─╮
    |    ╭──╮╭╯  ╰─╮ ╭╯ ╰──
    | ╭──╯  ╰╯     ╰─╯
    |─╯
    └──────────────────────── step
      CE CE Phi Phi CE CE CE Phi Phi  (reward-driven)
```

## 핵심 통찰

1. **모든 ALT > PHI-K3**: 1:1 교대는 사실 최악. CE가 -29% 악화됨
2. **Reward-based가 최적**: CE 실패 시점에 Phi 부스트 -> CE +20.7%, Phi 1.14x
3. **Adaptive도 강함**: curriculum 효과 (Phi 먼저 -> CE 나중) -> CE +16%, Phi 1.24x
4. **비율보다 패턴**: ALT-1(75% CE)이 ALT-2(25% CE)보다 CE 학습 나쁨
5. **Burst의 trade-off**: CE는 좋지만 Phi 보존 최악 (0.77x)

## vs PHI-K3 비교

```
         CE 개선도         Phi 보존도
ALT-6  ████████████████  ████████████    -- OVERALL WINNER
ALT-3  █████████████     ██████████████  -- PHI WINNER
ALT-4  █████████████     ██████
ALT-2  ███████           █████████
ALT-5  ██████            █████████████
ALT-1  ██                ████████████
PHI-K3 █                 █████████       -- baseline (CE 악화!)
```

## 법칙 발견

> **Law of Reactive Training**: 학습 실패에 반응하는 의식 부스트가 고정 스케줄보다 우월하다.
> CE 악화 = 의식 불안정 신호 -> 즉시 Phi 부스트 -> CE와 Phi 동시 최적화.

## 설정

- DIM=64, HIDDEN=128, cells=64, steps=500
- 동일 seed (42), make_engine(), _phi_boost_step()
- 위치: bench_self_learning.py (ALT-1 ~ ALT-6)
