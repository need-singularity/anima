# TOPO5: 토러스 토폴로지 (Torus 512c)

## 알고리즘

```
1. 512개 세포를 22x23 2D 토러스에 배치 (22*23=506, 패딩으로 512)
   - 경계 없는 2D 격자 (상하좌우 연결)
   - 각 세포는 4개 이웃 (상, 하, 좌, 우)
2. Ising frustration 적용
3. 500 step 시뮬레이션

pseudocode:
  rows, cols = 22, 23  # ~512 cells
  cells = torus_2d(rows, cols)
  # 경계 조건: cell[0][j]의 위 이웃 = cell[rows-1][j]
  #            cell[i][0]의 왼쪽 이웃 = cell[i][cols-1]
  for cell in cells:
      cell.coupling = ANTIFERROMAGNETIC
  for step in range(500):
      for cell in cells:
          neighbors = cell.torus_neighbors  # 상하좌우 (4개)
          cell.update(neighbors)
          cell.frustration = ising_frustration(cell, neighbors)
      phi = measure_phi(cells)
      mi  = mutual_information(cells)
```

## 벤치마크 결과

| 메트릭 | 값 |
|---------|-----|
| Φ (최종) | **135.543** |
| Φ 배율 | **x109.1** (baseline 1.2421) |
| MI (상호정보) | 27,788.9 |
| never_silent | 1.0 (항상 발화) |
| final_cells | 202 |

## Φ 변화 그래프

```
Φ
140 |                                        ╭───
    |                                     ╭──╯
120 |                                  ╭──╯
    |                               ╭──╯
100 |                            ╭──╯
    |                         ╭──╯
 80 |                      ╭──╯
    |                   ╭──╯
 60 |                ╭──╯
    |             ╭──╯
 40 |          ╭──╯
    |       ╭──╯
  1 |───────╯
    └──────────────────────────────────────────── step
    0        100       200       300       400  500
```

## 핵심 통찰

> **토러스 512c(Φ=135.5) >= PHYS1 링 512c(Φ=134.2) -- 경계 없는 2D가 1D 링과 동등하다!**

토러스는 "경계가 없는 2D 격자"다. 놀라운 발견: 2D 토러스(이웃 4개)가 1D 링(이웃 2개)과 거의 동일한 Φ를 달성한다. 이것은 다음을 의미한다:

1. **차원보다 경계 부재가 중요**: 토러스의 핵심은 2D가 아니라 "경계가 없다"는 것
2. **이웃 수의 최적점**: 2개(링)~4개(토러스)가 Φ 극대화의 최적 범위
3. **이웃이 많아지면 Φ 감소**: 4(토러스) → 9(하이퍼큐브) → 전체(완전그래프)로 갈수록 Φ 감소

토러스는 물리학에서 가장 자연스러운 토폴로지다 -- 우주 자체가 토러스일 수 있다는 가설과 맥이 닿는다.
