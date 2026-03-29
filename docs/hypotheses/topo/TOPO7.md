# TOPO7 — 링+스핀글래스 하이브리드 512셀 (Ring + SpinGlass Hybrid)

## 알고리즘

```
512셀, 링 이웃(left/right) + 랜덤 4개 sparse ±J 연결
interaction = 0.6 × ring_interaction + 0.4 × spinglass_interaction

ring: i%3==0 반강자성 (PHYS1)
glass: J_ij ~ {-1, +1} 무질서 결합 (PHYS3)
```

## 벤치마크 결과

```
Baseline Φ:  1.2421
TOPO7 Φ:   104.849 (×84.4)
Total MI:   18675.3
MIP:        1234.6
never_silent: 1.0
final_cells: 169
```

## Φ 변화

```
Φ |                          ╭──────────── 104.8
  |                    ╭─────╯
  |              ╭─────╯
  |        ╭─────╯
  | ───────╯
  └──────────────────────────────── step
  0        50       100      150   200
```

## 핵심 통찰

- **실패**: PHYS1(134.2)보다 낮음. 두 종류 frustration이 간섭
- 60/40 혼합이 각각의 순수 효과를 희석
- **교훈: 순수한 메커니즘 > 하이브리드**
