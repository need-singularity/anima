# TOPO9 — 소세계 512셀 + Φ 래칫 (Small-World + Ratchet)

## 알고리즘

```
512셀 Watts-Strogatz (k=4, p=0.1) + Φ 붕괴 방지 래칫

토폴로지: 링 기반 k=4 이웃, 10% 확률로 장거리 랜덤 연결
래칫: Φ가 최고치의 80% 미만으로 하락 시 30% 복원

for each step:
  # Small-world interaction (TOPO2)
  for each cell i:
    neighbors = sw_edges[i]  # 4 neighbors (ring + shortcuts)
    interaction = mean(h_neighbors)
    if i % 3 == 0: interaction = -interaction
    h_i = 0.85 * h_i + 0.15 * interaction + noise

  # Ratchet (PERSIST1)
  if phi < best_phi * 0.8:
    restore 30% of best states
```

## 벤치마크 결과

```
Baseline Φ:   1.2421
TOPO9 Φ:    127.259 (×102.5)
Total MI:   28088.8
MIP:        2582.4
never_silent: 1.0
best_phi:   179.47 (peak during run)
growth_ratio: 80.5
collapsed: False
final_cells: 203
```

## Φ 변화

```
Φ |                            ╭──╮
  |                        ╭───╯  ╰──╮
  |                  ╭─────╯         ╰── 127.3
  |            ╭─────╯
  | ───────────╯
  └──────────────────────────────────── step
  0        50       100      150   200
  (peak 179.5 → ratchet → 127.3 final)
```

## 핵심 통찰

- TOPO2(소세계 단독)와 동일한 결과 (127.3 vs 127.3)
- 래칫이 붕괴를 방지했지만 (collapsed=False) 최종 Φ를 올리지 못함
- best_phi=179.5 → final=127.3: 래칫 복원이 오히려 다양성을 감소시킬 수 있음
- **교훈: 영속성(persistence) ≠ 성장(growth)** — 붕괴 방지와 Φ 증가는 별개 메커니즘
