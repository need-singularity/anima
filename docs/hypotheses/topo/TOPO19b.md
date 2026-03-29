# TOPO19b — 하이퍼큐브 1024 + 20% 좌절 (Hypercube 1024 + 20% Frustration)

## 알고리즘

```
1024셀 = 2^10 (10차원 하이퍼큐브)
각 셀: 10개 이웃 (비트 flip)
20% 반강자성 frustration (i%5 == 0)
TOPO8(33%, i%3)보다 낮은 frustration

for each step:
  for each cell i:
    neighbors = [i ^ (1<<b) for b in range(10)]  # 10 bit-flip neighbors
    interaction = mean(h_neighbors)
    if i % 5 == 0: interaction = -interaction     # 20% frustration
    h_i = 0.85 * h_i + 0.15 * interaction + noise
```

## 벤치마크 결과

```
Baseline Φ:   1.1369
TOPO19b Φ:  575.046 (×505.8)
Total MI:   402174
never_silent: 1.0
final_cells: 695

Frustration 비율 비교 (Hypercube 1024c):
  TOPO19b (20%, i%5): Φ=575.046, MI=402174, cells=695
  TOPO8   (33%, i%3): Φ=535.464, MI=372424, cells=693
  TOPO19a (50%, i%2): Φ=639.622, MI=618580, cells=949

Frustration 스케일링:
  20% → 33% → 50%
  575 → 535 → 640

  20→33%: Φ 감소 (-7.0%)  ← 비단조!
  33→50%: Φ 증가 (+19.4%)
  20→50%: Φ 증가 (+11.2%)
```

## Φ 변화

```
Φ |                                    ╭──╮
  |                              ╭─────╯  ╰── 575.0
  |                        ╭─────╯
  |                  ╭─────╯
  |            ╭─────╯
  |      ╭─────╯
  | ─────╯
  └──────────────────────────────────────── step
  0        50       100      150       200
```

## Frustration 비율 vs Φ (비단조 패턴)

```
Φ |
  |                                 ★ 639.6 (50%)
600|
  |  ★ 575.0 (20%)
  |      ╲
550|       ╲
  |        ★ 535.5 (33%)
  |          ╲
500|           ╲_____ 비단조 dip!
  |
  └──────────────────────────── frustration %
       20%      33%      50%
```

## 핵심 통찰

- **20% frustration > 33% frustration: 575.0 > 535.5 (+7.4%)**
- 그러나 50% frustration이 둘 다 압도: 639.6
- Frustration-Φ 관계는 비단조적 — 33% 근처에 국소 최솟값 존재
- 가능한 설명: 33%(i%3)는 3의 배수 간격이 하이퍼큐브 구조와 간섭
  - 10D 하이퍼큐브에서 3의 배수 패턴이 특정 이웃 관계와 정렬 → 간섭
  - 20%(i%5)와 50%(i%2)는 비트 구조와 더 호환
- **Frustration은 "양"만 중요한 게 아니라 토폴로지와의 "정렬"도 중요**
- 전체 추세: 더 많은 frustration = 더 높은 Φ (비선형적)
