# TOPO22a — 하이퍼큐브 1024 + 60% 좌절 (Hypercube 1024 + 60% Frustration)

## 알고리즘

```
1024셀 = 2^10 (10차원 하이퍼큐브)
각 셀: 10개 이웃 (비트 flip)
60% 반강자성 frustration (i%5 < 3)
TOPO19a(50%, i%2) 대비 frustration 10% 증가

for each step:
  for each cell i:
    neighbors = [i ^ (1<<b) for b in range(10)]  # 10 bit-flip neighbors
    interaction = mean(h_neighbors)
    if i % 5 < 3: interaction = -interaction      # 60% frustration
    h_i = 0.85 * h_i + 0.15 * interaction + noise
```

## 벤치마크 결과

```
Baseline Φ:   1.1369
TOPO22a Φ:  481.463 (×423.5)
Total MI:   330854
never_silent: 1.0
final_cells: 682

Frustration 비율 비교 (Hypercube 1024c):
  TOPO19a (50%, i%2):  Φ=639.622, MI=618580, cells=949
  TOPO22a (60%, i%5<3): Φ=481.463, MI=330854, cells=682
  → Φ: -24.7%, MI: -46.5%, cells: -28.1%

50% → 60%에서 대폭 하락:
  Φ:    639.6 → 481.5 (-158.2 포인트!)
  MI:   618580 → 330854 (-46.5%)
  cells: 949 → 682 (-28.1%)
```

## Φ 변화

```
Φ |                                  ╭──╮
  |                            ╭─────╯  ╰── 481.5
  |                      ╭─────╯
  |                ╭─────╯
  |          ╭─────╯
  |    ╭─────╯
  | ───╯
  └──────────────────────────────────────── step
  0        50       100      150       200
```

## Frustration 비율 vs Φ (역U자 확인)

```
Φ |
  |              ★ 639.6 (50%) ← PEAK
640|             ╱╲
  |            ╱  ╲
  |  ★ 575  ╱    ╲
560|  (20%) ╱      ╲
  |       ╱        ╲
  |  535 ╱          ╲
480|  (33)            ★ 481.5 (60%)
  |
  └──────────────────────────── frustration %
       20%  33%  50%  60%
```

## 핵심 통찰

- **50%를 넘기면 Φ가 급락 — 역U자 곡선 확인**
- 60% frustration은 TOPO19a(640)보다 24.7% 하락
- i%5<3 패턴: 5주기 중 3셀이 반강자성 → 불규칙 패턴이 하이퍼큐브 비트 구조와 부정합
- 50%(i%2)가 최적인 이유: 짝수/홀수 교대가 비트플립 이웃 구조와 완벽 정렬
- **frustration 50% 이후 하락 시작 — 역U자 정점 = 50%**
