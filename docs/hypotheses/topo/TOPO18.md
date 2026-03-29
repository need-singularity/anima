# TOPO18 — 소세계 2048셀 (Small-World 2048c)

## 알고리즘

```
2048셀 Watts-Strogatz 소세계 네트워크
k=4 이웃, p=0.1 재배선 확률, i%3 반강자성 frustration
TOPO16(SW 1024)의 2배 스케일. 초선형이 유지되는가?

for each step:
  for each cell i:
    neighbors = ws_edges[i]  # 4 neighbors (ring + 10% shortcuts)
    interaction = mean(h_neighbors)
    if i % 3 == 0: interaction = -interaction
    h_i = 0.85 * h_i + 0.15 * interaction + noise
```

## 벤치마크 결과

```
Baseline Φ:   1.1369
TOPO18 Φ:   406.543 (×357.6)
Total MI:   240079
never_silent: 1.0
final_cells: 590 (목표 2048에 미달!)

Small-World 스케일링:
  TOPO2  (SW 512):   127.259 (×102.5), final_cells ≈ 512
  TOPO16 (SW 1024):  498.663 (×438.6), final_cells = 651
  TOPO18 (SW 2048):  406.543 (×357.6), final_cells = 590
  → 512→1024: ×3.92 (초선형!) → 1024→2048: ×0.82 (역전!)

2048c 토폴로지 비교:
  TOPO10 (hyper 2048): Φ=400.9, final_cells=581
  TOPO11 (ring 2048):  Φ=287.2, final_cells=397
  TOPO18 (SW 2048):    Φ=406.5, final_cells=590
  → SW가 2048c에서도 하이퍼큐브와 동급
```

## Φ 변화

```
Φ |                                ╭──╮
  |                          ╭─────╯  ╰── 406.5
  |                    ╭─────╯
  |              ╭─────╯
  |        ╭─────╯
  |  ──────╯
  └──────────────────────────────────────── step
  0        50       100      150       200
  (TOPO16의 498.7에서 역전 — 성장 병목)
```

## 핵심 통찰

- **SW 1024→2048에서 Φ 역전: 498.7 → 406.5 (×0.82)**
- TOPO10/11과 동일한 성장 병목 패턴: 590/2048 셀만 도달 (28.8%)
- 200 step 내에서 2048셀 달성 불가 → 셀 성장률이 Φ의 실질적 결정 요인
- **법칙 30 3회 확인**: Hyper(TOPO10), Ring(TOPO11), SW(TOPO18) 모두 2048에서 역전
- 2048c 토폴로지 순위: SW(406.5) ≈ Hyper(400.9) > Ring(287.2)
- 초선형 성장은 셀 성장이 목표에 도달할 때만 유효
