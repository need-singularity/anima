# TOPO21 — 동적 토폴로지 1024셀 (Dynamic Topology 1024c)

## 알고리즘

```
1024셀 = 2^10 (10차원 하이퍼큐브) 기본
Φ가 5% 이상 하락하면 적응적 재배선 (adaptive rewire)
새 엣지를 MI가 낮은 셀 쌍 사이에 추가

for each step:
  for each cell i:
    neighbors = hypercube_edges[i] + dynamic_edges[i]
    interaction = mean(h_neighbors)
    if i % 3 == 0: interaction = -interaction
    h_i = 0.85 * h_i + 0.15 * interaction + noise

  # Adaptive rewiring
  if Φ_current < 0.95 * Φ_prev:
    low_mi_pair = find_lowest_MI_pair()
    add_edge(low_mi_pair)
    n_dynamic_edges += 1
```

## 벤치마크 결과

```
Baseline Φ:   1.1369
TOPO21 Φ:   465.051 (×409.1)
Total MI:   278582
never_silent: 1.0
final_cells: 597
n_dynamic_edges: 8 (200 step에서 단 8개만 추가됨)

비교:
  TOPO8  (hyper 1024):  535.464 (×431.1)  → 동적이 더 낮음 (-13.2%)
  TOPO17 (hyper+SW):    463.634 (×407.8)  → TOPO17과 거의 동급
  TOPO16 (SW 1024):     498.663 (×438.6)  → SW보다도 낮음

동적 엣지 분석:
  총 200 step 중 Φ 5% 하락 = 8회 발생
  8개 엣지 추가 → 효과 미미 (하이퍼큐브 10240 엣지 대비 0.08%)
  하이퍼큐브는 이미 안정적 → 적응적 재배선 거의 트리거 안 됨
```

## Φ 변화

```
Φ |                                  ╭──╮
  |                            ╭─────╯  ╰── 465.1
  |                      ╭─────╯
  |                ╭──↑──╯    (↑ = dynamic edge 추가 시점)
  |          ╭─────╯
  |    ╭──↑──╯
  | ───╯
  └──────────────────────────────────────── step
  0        50       100      150       200
  (Φ 하락 시에만 재배선 → 8회 트리거)
```

## 핵심 통찰

- **동적 재배선은 한계적 개선 (marginal improvement) 개념**
- 하이퍼큐브가 이미 충분히 안정적 → Φ 5% 하락이 드물게 발생 (200 step에서 8회)
- 8개 추가 엣지는 10240개 기존 엣지 대비 0.08% — 효과 무의미
- TOPO17(하이퍼큐브+SW 하이브리드)과 거의 동급: 465.1 vs 463.6
- **적응적 토폴로지 변경은 기본 토폴로지가 약할 때만 의미 있음**
- 하이퍼큐브처럼 이미 최적에 가까운 토폴로지에서는 동적 변경 불필요
- 법칙 48 재확인: 순수한 하이퍼큐브(535.5) > 어떤 변형(463~465)
