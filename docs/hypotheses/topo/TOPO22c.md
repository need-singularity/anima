# TOPO22c — 하이퍼큐브 1024 + 100% 좌절 (Hypercube 1024 + 100% Anti-Ferromagnetic)

## 알고리즘

```
1024셀 = 2^10 (10차원 하이퍼큐브)
각 셀: 10개 이웃 (비트 flip)
100% 반강자성 frustration — 모든 상호작용이 반발
완전 anti-ferromagnetic Ising 모델

for each step:
  for each cell i:
    neighbors = [i ^ (1<<b) for b in range(10)]  # 10 bit-flip neighbors
    interaction = mean(h_neighbors)
    interaction = -interaction                     # 100% frustration (ALL)
    h_i = 0.85 * h_i + 0.15 * interaction + noise
```

## 벤치마크 결과

```
Baseline Φ:   1.1369
TOPO22c Φ:  443.747 (×390.3)
Total MI:   629997  ← HIGHEST MI IN ENTIRE SWEEP!
never_silent: 1.0
final_cells: 994   ← HIGHEST CELLS IN ENTIRE SWEEP!

MI 비교 (Frustration Sweep):
  TOPO19a (50%):  MI=618580, cells=949
  TOPO22c (100%): MI=629997, cells=994  ← MI 1위!
  TOPO22a (60%):  MI=330854, cells=682
  TOPO22d (90%):  MI=298262, cells=671
  TOPO22b (75%):  MI=241517

100% anti-ferro의 역설:
  MI는 최고 (629K) — 모든 상호작용이 반발 = 최대 정보량
  Φ는 중간 (444) — 완벽한 대칭이 협력 구조를 파괴
  → MI(정보량) ≠ Φ(정보 통합)
```

## Φ 변화

```
Φ |                                ╭──╮
  |                          ╭─────╯  ╰── 443.7
  |                    ╭─────╯
  |              ╭─────╯
  |        ╭─────╯
  |  ╭─────╯
  |──╯
  └──────────────────────────────────────── step
  0        50       100      150       200
```

## MI vs Φ 분리

```
       MI (×1000)          Φ
700 |  ▓ 630 (100%)    640 | ★ (50%)
    |  ▒ 619 (50%)        |
600 |                  560 |
    |                      |
500 |                  480 | ○ (60%)
    |  ░ 403 (20%)        |  ▓ (100%)
400 |                  440 |  ▒ (90%)
    |  ░ 372 (33%)        |
300 |  ░ 331 (60%)    400 |
    |  ░ 298 (90%)        |  ░ (75%)
200 |  ░ 242 (75%)    360 |
    |                      |
    └─── frustration      └─── frustration

MI는 100%에서 최대 ← 반발이 정보량 극대화
Φ는 50%에서 최대  ← 통합에 협력 구조 필요
```

## 핵심 통찰

- **100% anti-ferromagnetic: MI 최고(630K) but Φ 중간(444)**
- 완전 반발 = 최대 정보량 (모든 셀이 이웃과 반대 → 정보 다양성 극대)
- 그러나 Φ는 50%보다 30.6% 낮음 — 협력 구조 없이는 정보 "통합" 불가
- 셀 성장은 994/1024(97.1%)로 최고 — 반발이 분화를 극대화
- **MI(정보의 양) ≠ Φ(정보의 통합): 50%가 최적인 이유는 반발+협력의 균형**
- 75%(384)보다 높은 이유: 완벽한 대칭이 부분적 비대칭(i%4)보다 양호
