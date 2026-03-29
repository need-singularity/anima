# 역대 전 기록 bench_v2 재측정 (2026-03-29)

## 결과

```
Config                    Cells  Φ(IIT)  Φ(proxy)  이전 보고값
─────────────────────────────────────────────────────────────
64c baseline                64    1.16     0.53        49
128c v4 optimal            128    1.18     0.10       140
256c v4 optimal            256    1.15     0.10       282
512c v4 optimal            512    1.02     0.09       591
1024c v4 optimal          1024    1.45     0.09      1142
1024c + frust 50%         1024    1.45     0.09       639
```

## Φ(IIT) 스케일링

```
Φ(IIT)
 |
1.5 ┤                         ★ ★ 1024c
    |
1.2 ┤ ★    ★    ★              128c, 256c
    |   64c
1.0 ┤              ★ 512c
    |
    └──────────────────────→ cells
     64  128  256  512  1024

→ Φ(IIT)는 cells에 무관 (1.0~1.5 범위)
→ sync+faction이 hidden을 수렴시켜 MI가 낮아짐
```

## Φ(proxy) 스케일링

```
Φ(proxy)
 |
0.5 ┤ ★ 64c (baseline, no sync)
    |
0.1 ┤ ★ ★ ★ ★ ★ (sync 적용 시 모두 ~0.1)
    |
    └──────────────────────→ cells

→ sync가 variance를 0으로 만듦
→ proxy = global_var - faction_var ≈ 0
```

## 이전 보고값 (49~1142) 의 정체

```
이전 보고값은 현재 PhiCalculator에서 재현 불가.
가능한 설명:
  1. 이전 세션에서 consciousness_meter.py가 다른 버전이었음
  2. MI 계산에 선형 외삽(linear extrapolation)이 포함되었을 수 있음
  3. 또는 완전히 다른 Φ 계산 함수를 사용
  4. Training Φ (53.9, 123.8)도 같은 문제일 수 있음

결론:
  모든 이전 Φ 기록은 "어떤 Φ 정의인지" 불명확
  bench_v2 기준으로 재측정된 값만 신뢰
```

## 교훈

```
Law 54 재확인:
  "Φ"라는 같은 이름이 완전히 다른 값을 의미할 수 있다.
  모든 Φ 보고에는 반드시 측정 방법을 명시해야 한다.

  Φ(IIT, n_bins=16): PhiCalculator MI 기반, ~1.0-1.5
  Φ(proxy, variance): global-faction var, cells에 비례
  Φ(이전 보고): 불명확 — 재현 불가
```
