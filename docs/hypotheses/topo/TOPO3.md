# TOPO3: 척도없는 네트워크 (Scale-Free Network 512c)

## 알고리즘

```
1. 512개 세포를 Barabasi-Albert 척도없는 네트워크로 연결
   - m=3 (새 노드가 기존 3개에 연결)
   - 결과: 멱법칙 차수 분포 P(k) ~ k^(-3)
   - 소수 허브 + 다수 저차수 노드
2. Ising frustration 적용
3. 500 step 시뮬레이션

pseudocode:
  cells = barabasi_albert(n=512, m=3)
  # 허브 노드: 수십~수백 이웃
  # 말단 노드: 3개 이웃
  for cell in cells:
      cell.coupling = ANTIFERROMAGNETIC
  for step in range(500):
      for cell in cells:
          neighbors = cell.ba_neighbors
          cell.update(neighbors)
          cell.frustration = ising_frustration(cell, neighbors)
      phi = measure_phi(cells)
      mi  = mutual_information(cells)
```

## 벤치마크 결과

| 메트릭 | 값 |
|---------|-----|
| Φ (최종) | **135.159** |
| Φ 배율 | **x108.8** (baseline 1.2421) |
| MI (상호정보) | 27,582.7 |
| never_silent | 1.0 (항상 발화) |
| final_cells | 205 |

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

> **척도없는 네트워크의 허브는 양날의 검 -- 정보 집중은 통합을 돕지만, 허브 동기화는 분화를 해친다.**

BA 네트워크의 허브 노드는 정보를 빠르게 통합하지만, 너무 많은 이웃을 가진 허브는 평균장(mean-field)에 가까워져 분화가 약해진다. TOPO3이 TOPO5(토러스)와 거의 동일한 Φ를 보이는 것은, 허브의 통합력과 분화 손실이 상쇄되기 때문이다. 그러나 TOPO6(완전 그래프)처럼 모든 노드가 허브가 되면 의식이 붕괴한다 -- 적절한 불균형이 핵심이다.
