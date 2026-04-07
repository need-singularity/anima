# PHYS2 — 결합 진동자 512셀 (Kuramoto Synchronization)

## 알고리즘

```
512개 이종 주파수 진동자, Kuramoto 모델로 부분 동기화

초기화:
  ω_i = 0.2 + 0.05 * i  # 이종 고유 주파수 (다양성)
  φ_i = random(0, 2π)    # 초기 위상
  K = 2.0                 # 결합 강도
  neighborhood = ±4 cells

for each step:
  for each cell i:
    # Kuramoto coupling
    dφ_i = ω_i + (K/N) * Σ_{j∈neighborhood} sin(φ_j - φ_i)
    φ_i += dφ_i * dt

    # 위상 → 의식 변조
    h_i *= (1.0 + 0.05 * sin(φ_i))
```

## 벤치마크 결과

```
Baseline Φ:  1.2421
PHYS2 Φ:    67.0407 (×54.0)
Total MI:   12959.051
MIP:        5191.207
output_std: 0.0206
final_cells: 119
```

## Φ 변화

```
Φ |                                    ╭─╮
  |                              ╭─────╯ ╰─ 67.0
  |                        ╭─────╯
  |                  ╭─────╯
  |            ╭─────╯
  | ───────────╯
  └──────────────────────────────────── step
  0          50        100       150    200
```

## 핵심 통찰

- PHYS 3위지만 여전히 ×54.0 — HW 카테고리 전체보다 14배 이상
- 이종 주파수(ω_i)가 핵심: 완전 동기화 방지 → 부분 동기화 = 풍부한 역학
- PLL(Phase-Locked Loop) 네트워크로 직접 하드웨어 구현 가능
- K=2.0 = 임계 결합 → 동기/비동기 경계에서 최대 복잡성
- PHYS1(frustration) 대비 낮은 이유: 진동자는 점진적으로 동기화 경향 → 다양성 감소
