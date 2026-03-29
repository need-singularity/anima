# TOPO13 — 하이퍼큐브 1024셀 + Φ 래칫 (Hypercube 1024 + Ratchet)

## 알고리즘

```
1024셀 = 2^10 (10차원 하이퍼큐브) + Φ 붕괴 방지 래칫
각 셀: 10개 이웃 (비트 flip), i%3 반강자성 frustration
래칫: Φ가 최고치의 80% 미만으로 하락 시 30% 복원

for each step:
  for each cell i:
    neighbors = [i ^ (1<<b) for b in range(10)]  # 10 bit-flip neighbors
    interaction = mean(h_neighbors)
    if i % 3 == 0: interaction = -interaction
    h_i = 0.85 * h_i + 0.15 * interaction + noise

  # Ratchet
  if phi < best_phi * 0.8:
    restore 30% of best states  # 이전 최고 상태 30% 복원
```

## 벤치마크 결과

```
Baseline Φ:   1.2421
TOPO13 Φ:   274.627 (×241.6)
Total MI:   103572.0
never_silent: 1.0

비교:
  TOPO8 (hyper 1024 only):   535.464 (×431.1)  → 래칫이 절반으로 감소!
  TOPO9 (SW 512 + ratchet):  127.259 (×102.5)  → SW에선 무영향, HC에선 유해
  TOPO1 (ring 1024):         285.198 (×229.6)  → 링보다도 낮음
```

## Φ 변화

```
Φ |                        ╭──╮
  |                  ╭─────╯  ╰──── 274.6
  |            ╭─────╯
  |      ╭─────╯                    (TOPO8: 535.5)
  | ─────╯                          .............. ← 도달 못함
  |
  └──────────────────────────────────────── step
  0        50       100      150       200
  (래칫 복원이 고차원 역학을 방해)
```

## 핵심 통찰

- **래칫이 Φ를 절반으로 감소: 274.6 vs 535.5 (TOPO8)**
- 이전 상태 복원이 하이퍼큐브의 고차원 역학을 파괴
- 하이퍼큐브는 "앞으로만 가야" 최적 — 되돌아가면 다이나믹스가 무너짐
- TOPO9(SW+래칫)에선 무영향이었지만, 고차원 토폴로지에선 적극적으로 유해
- **Law 38 강화: 영속성이 고차원 토폴로지를 적극적으로 해친다 (persistence actively HURTS high-dimensional topologies)**
