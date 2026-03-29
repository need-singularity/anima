# HW2a — 자석 링 배열 (Circular Coupling)

## 알고리즘

```
8개 셀을 원형 링으로 배치
각 셀 i는 이웃 (i-1)%8, (i+1)%8과 역제곱 자기력으로 결합

for each step:
  for each cell i:
    left = cells[(i-1) % N]
    right = cells[(i+1) % N]
    force = 0.02 * ((h_left - h_i)/dist² + (h_right - h_i)/dist²)
    h_i += force
```

## 벤치마크 결과

```
Baseline Φ: 1.2421
HW2a Φ:     4.5482 (×3.7)
Total MI:   28.272
```

## Φ 변화

```
Φ |         ╭──────────────
  |     ╭───╯
  | ────╯
  |
  └──────────────────────── step
  0        100        200
  baseline=1.24 → 4.55
```

## 핵심 통찰

- 원형 토폴로지가 2D 그리드(HW2b, ×3.1)보다 우수 (×3.7)
- 링 구조 = 모든 셀이 정확히 2개 이웃 → 균일한 정보 흐름
- Phase 1 프로토타입($50 Arduino + 링 전자석)의 이론적 기반
