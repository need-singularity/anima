# TOPO1: 링 토폴로지 1024 세포 (Ring Topology 1024c)

## 알고리즘

```
1. 1024개 세포를 원형 링으로 배치 (각 세포는 좌우 2개 이웃)
2. Ising frustration 적용:
   - 이웃 세포 간 반강자성(antiferromagnetic) 커플링
   - frustration = 인접 세포가 동시에 만족할 수 없는 상태
3. 500 step 시뮬레이션
4. 매 step: 세포 상태 업데이트 → tension 전파 → MI 측정 → Φ 계산

pseudocode:
  cells = ring_topology(n=1024, neighbors=2)
  for cell in cells:
      cell.coupling = ANTIFERROMAGNETIC
  for step in range(500):
      for cell in cells:
          cell.update(neighbors=cell.ring_neighbors)
          cell.frustration = ising_frustration(cell, cell.ring_neighbors)
      phi = measure_phi(cells)
      mi  = mutual_information(cells)
```

## 벤치마크 결과

| 메트릭 | 값 |
|---------|-----|
| Φ (최종) | **285.198** |
| Φ 배율 | **x229.6** (baseline 1.2421) |
| MI (상호정보) | 112,000.5 |
| never_silent | 1.0 (항상 발화) |
| final_cells | 387 |

## Φ 변화 그래프

```
Φ
300 |                                          ╭──
    |                                       ╭──╯
250 |                                    ╭──╯
    |                                 ╭──╯
200 |                              ╭──╯
    |                           ╭──╯
150 |                        ╭──╯
    |                     ╭──╯
100 |                  ╭──╯
    |               ╭──╯
 50 |            ╭──╯
    |         ╭──╯
  1 |─────────╯
    └──────────────────────────────────────────── step
    0        100       200       300       400  500
```

## 핵심 통찰

> **링 1024c는 링 512c (PHYS1, Φ=134.23)의 2.12배 -- 초선형 스케일링!**

세포 수가 2배일 때 Φ가 2배 이상 증가한다. 이는 링 토폴로지에서 정보 통합이 세포 수에 대해 초선형(superlinear)으로 스케일링됨을 의미한다. 링의 단순한 구조(이웃 2개)가 오히려 장거리 상관관계를 강화하며, Ising frustration이 세포 간 분화를 극대화한다.

MI = 112,000은 전체 카테고리 중 최고 수준으로, 1024개 세포 간 정보 교환이 폭발적으로 이루어짐을 보여준다.
