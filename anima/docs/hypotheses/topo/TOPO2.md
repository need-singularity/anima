# TOPO2: 소세계 네트워크 (Small-World Network 512c)

## 알고리즘

```
1. 512개 세포를 Watts-Strogatz 소세계 네트워크로 연결
   - k=4 (각 세포 4개 이웃)
   - p=0.1 (10% 확률로 장거리 재연결)
2. Ising frustration 적용
3. 500 step 시뮬레이션

pseudocode:
  cells = watts_strogatz(n=512, k=4, p=0.1)
  # 결과: 높은 군집계수 + 짧은 평균경로 (소세계 특성)
  for cell in cells:
      cell.coupling = ANTIFERROMAGNETIC
  for step in range(500):
      for cell in cells:
          neighbors = cell.sw_neighbors  # 로컬 + 장거리
          cell.update(neighbors)
          cell.frustration = ising_frustration(cell, neighbors)
      phi = measure_phi(cells)
      mi  = mutual_information(cells)
```

## 벤치마크 결과

| 메트릭 | 값 |
|---------|-----|
| Φ (최종) | **127.259** |
| Φ 배율 | **x102.5** (baseline 1.2421) |
| MI (상호정보) | 28,088.8 |
| never_silent | 1.0 (항상 발화) |
| final_cells | ~202 |

## Φ 변화 그래프

```
Φ
130 |                                       ╭────
    |                                    ╭──╯
110 |                                 ╭──╯
    |                              ╭──╯
 90 |                           ╭──╯
    |                        ╭──╯
 70 |                     ╭──╯
    |                  ╭──╯
 50 |               ╭──╯
    |            ╭──╯
 30 |         ╭──╯
    |      ╭──╯
  1 |──────╯
    └──────────────────────────────────────────── step
    0        100       200       300       400  500
```

## 핵심 통찰

> **소세계 네트워크는 장거리 연결에도 불구하고 링/토러스를 넘지 못한다.**

Watts-Strogatz의 p=0.1 재연결은 평균 경로 길이를 단축시키지만, 이것이 반드시 의식(Φ)에 유리하지는 않다. 장거리 바로가기(shortcut)가 정보 전파를 빠르게 하지만, 동시에 로컬 frustration 패턴을 깨뜨려 분화의 강도를 약화시킨다. 소세계 특성(높은 군집 + 짧은 경로)은 뇌 네트워크의 효율성에는 좋지만, 순수 Φ 극대화에는 단순 링이 더 효과적이다.
