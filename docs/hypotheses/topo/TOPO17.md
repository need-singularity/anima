# TOPO17 — 하이퍼큐브 + 소세계 1024셀 (Hypercube + Small-World Hybrid)

## 알고리즘

```
1024셀 = 2^10 (10차원 하이퍼큐브) + 소세계 바로가기
각 셀: 10개 비트플립 이웃 + 2개 랜덤 바로가기 = 12 이웃
i%3 반강자성 frustration

for each step:
  for each cell i:
    hc_neighbors = [i ^ (1<<b) for b in range(10)]  # 10 bit-flip
    sw_neighbors = random_shortcuts[i]                # 2 random
    neighbors = hc_neighbors + sw_neighbors           # 12 total
    interaction = mean(h_neighbors)
    if i % 3 == 0: interaction = -interaction
    h_i = 0.85 * h_i + 0.15 * interaction + noise
```

## 벤치마크 결과

```
Baseline Φ:   1.1369
TOPO17 Φ:   463.634 (×407.8)
Total MI:   306436
never_silent: 1.0

비교:
  TOPO8  (hyper 1024):  535.464 (×431.1)  → 하이퍼큐브보다 13.4% 하락!
  TOPO16 (SW 1024):     498.663 (×438.6)  → 소세계보다도 낮음
  TOPO12 (hyper+8fac):  535.329 (×470.9)  → 하이브리드 패턴 반복

이웃 수 비교 (1024c):
  TOPO8  (10 neighbors): Φ=535.5 ← 최적
  TOPO16 (4 neighbors):  Φ=498.7
  TOPO17 (12 neighbors): Φ=463.6 ← 이웃 과잉
```

## Φ 변화

```
Φ |                                  ╭──╮
  |                            ╭─────╯  ╰── 463.6
  |                      ╭─────╯
  |                ╭─────╯
  |          ╭─────╯
  |    ╭─────╯
  | ───╯
  └──────────────────────────────────────── step
  0        50       100      150       200
  (TOPO8의 535.5보다 낮음 — 바로가기가 해로움)
```

## 핵심 통찰

- **하이퍼큐브에 소세계 바로가기 추가 = Φ 감소 (535.5 → 463.6)**
- 법칙 48 재확인: 순수 메커니즘 > 하이브리드
- 바로가기 2개 추가로 이웃 수 10→12 = 역U자 법칙(법칙 46)의 이웃 과잉 영역 진입
- 하이퍼큐브의 비트플립 이웃은 이미 최적의 장거리 연결 — 추가 바로가기는 중복 + 간섭
- **하이퍼큐브는 그 자체로 완전한 토폴로지. 어떤 추가도 해롭다.**
