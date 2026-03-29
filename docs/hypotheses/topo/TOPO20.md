# TOPO20 — 계층적 하이퍼큐브 1024셀 (Hierarchical Hypercube 8×128 Clusters)

## 알고리즘

```
1024셀 = 8 클러스터 × 128셀
각 클러스터: 7D 하이퍼큐브 (2^7 = 128셀, 7 이웃)
클러스터 간: 소수의 인터클러스터 바로가기로 연결
i%3 반강자성 frustration

for each step:
  for each cell i:
    cluster_id = i // 128
    local_i = i % 128
    # Intra-cluster: 7D hypercube neighbors
    intra = [cluster_id*128 + (local_i ^ (1<<b)) for b in range(7)]
    # Inter-cluster: sparse shortcuts
    inter = inter_cluster_edges[i]
    neighbors = intra + inter
    interaction = mean(h_neighbors)
    if i % 3 == 0: interaction = -interaction
    h_i = 0.85 * h_i + 0.15 * interaction + noise
```

## 벤치마크 결과

```
Baseline Φ:   1.1369
TOPO20 Φ:   212.637 (×187.0)
Total MI:   65615
never_silent: 1.0

1024c 토폴로지 비교:
  TOPO19a (hyper+50%frust): 639.622 (×562.6) ← 1위
  TOPO8   (hyper 10D):      535.464 (×431.1) ← 2위
  TOPO16  (SW 1024):        498.663 (×438.6) ← 3위
  TOPO17  (hyper+SW):       463.634 (×407.8)
  TOPO15  (torus 1024):     274.708 (×241.6)
  TOPO1   (ring 1024):      285.198 (×229.6)
  TOPO20  (hier hyper):     212.637 (×187.0) ← 최하위!

MI도 최하위:
  TOPO8:  MI=372424
  TOPO20: MI=65615  → 17.6%에 불과
```

## Φ 변화

```
Φ |                          ╭──╮
  |                    ╭─────╯  ╰── 212.6
  |              ╭─────╯
  |        ╭─────╯
  |  ──────╯
  └──────────────────────────────────── step
  0        50       100      150   200
  (1024c 토폴로지 중 최하위!)
```

## 1024c 토폴로지 순위 비교

```
Φ |
  | ███ 639.6  TOPO19a (hyper+50%frust) ★
  | ███ 535.5  TOPO8   (hyper 10D)
  | ██▌ 498.7  TOPO16  (SW 1024)
  | ██▌ 465.1  TOPO21  (dynamic)
  | ██▌ 463.6  TOPO17  (hyper+SW)
  | █▌  285.2  TOPO1   (ring)
  | █▌  274.7  TOPO15  (torus)
  | █   212.6  TOPO20  (hier hyper) ← 최하위
  └──────────────────────────────────
```

## 핵심 통찰

- **1024c 토폴로지 최하위: Φ = 212.6 (×187.0)**
- 계층적 모듈성이 정보 통합을 차단!
- 각 클러스터 내부(7D hyper)는 잘 작동하지만 클러스터 간 연결이 너무 희소
- MI=65615는 TOPO8(372424)의 17.6% — 정보가 클러스터 경계를 넘지 못함
- **모듈성(modularity) = 의식의 적** — IIT의 핵심 예측
- 뇌의 모듈은 "밀접하게" 연결된 모듈이지 "고립된" 모듈이 아님
- 10D 하이퍼큐브는 이미 최적의 글로벌 연결 — 인위적 분할은 파괴적
