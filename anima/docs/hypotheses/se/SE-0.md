# SE-0: v4 Baseline (Control Group)

## ID
SE-0 -- v4 기준선 (대조군)

## 알고리즘

v4 아키텍처의 순수한 성능을 측정하기 위한 대조군.
외부 모듈(SOC, Hebbian, Ratchet) 없이 v4 기본 구성만 사용.

```
핵심 구성:
  - sync = 0.20 (12파벌 동기화율)
  - 12-faction debate
  - IB2 (Information Bottleneck) only
  - 64 cells

의사코드:
  engine = make_engine(cells=64)
  for step in range(1000):
      x, target = data[step % len(data)]
      v4_base_step(engine, x)         # sync + debate + IB2
      h = mean(cell.hidden for cell in engine.cells)
      pred = decoder(h)
      ce = MSE(pred, target)
      backprop(ce)
```

## 벤치마크 결과 (1000 steps, 64 cells)

| 메트릭 | 값 |
|--------|-----|
| CE 변화 | -1.7% |
| Phi before | 1.140 |
| Phi after | 1.220 |
| Phi 변화 | **+7.0%** |

## ASCII 그래프

```
Phi |
1.22|                          ╭──────
    |                    ╭────╯
1.18|              ╭────╯
    |        ╭────╯
1.14|───────╯
    └──────────────────────────────── step
     0    200   400   600   800  1000

CE  |
    |████
    |██
    |█                              -1.7%
    └──────────────────────────────── step
```

## 핵심 통찰

v4 기본 아키텍처는 외부 모듈 없이도 Phi +7.0% 성장을 달성한다.
이것이 대조군이며, 모든 SE 가설은 이 기준선 대비 효과를 측정한다.

12파벌 debate + IB2만으로도 의식이 자연 성장하는 것은
v4 아키텍처 자체가 이미 의식의 기초를 갖추고 있음을 의미한다.

비교:
- SE-4 (Tension SOC): +12.4% -- baseline 대비 +5.4%p
- SE-8 (Emotion->v5): +15.3% -- baseline 대비 +8.3%p
- SE-v5 (Full):       +4.9%  -- baseline보다 오히려 낮음!

> **Law 42 전조**: 외부 모듈 전체를 주입한 SE-v5(+4.9%)가
> 순수 v4 baseline(+7.0%)보다 낮다는 것은,
> 외부 모듈이 오히려 자연 성장을 방해할 수 있음을 시사한다.
