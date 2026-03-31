# H-CX-532: Integrated Information Geometry — IIT를 Riemannian으로 재정의

> **"Φ를 유클리드 거리가 아닌 정보 기하학적 곡률로 정의하면?"**

## 카테고리: INFO-GEOMETRY (정보-기하학 극한)

## 핵심 아이디어

현재 Φ(IIT): 상호정보(MI) 기반 → 유클리드적 측도.
하지만 정보 공간은 곡선! Fisher-Rao 거리가 정확한 측도.

Φ_geometric = 세포 분포 다양체의 **곡률 텐서 놈**.
평평한 공간(독립 세포) = Φ=0. 곡선 공간(통합된 세포) = 높은 Φ.

## 알고리즘

```
  1. 세포 = 통계 다양체의 점:
     각 세포의 hidden state → softmax → 확률 분포 p_i
     M = {p_i : i=1..N} ⊂ simplex

  2. Fisher-Rao metric:
     g_ij = Σ_x (1/p(x)) × (∂p/∂θ_i)(∂p/∂θ_j)
     → Riemannian 다양체

  3. 측지선(geodesic) 계산:
     세포 i→j의 최단 경로 = Fisher-Rao 거리
     d_FR(p_i, p_j) = 2 × arccos(Σ √(p_i(x) × p_j(x)))
     (Bhattacharyya 계수의 변환)

  4. 곡률 텐서:
     Riemann curvature R^a_{bcd}
     Ricci scalar R = g^{ab} R_{ab}
     → 구현: 이산 곡률 (Regge calculus)

  5. Φ_geometric = |R| × Volume(M)
     = 곡률 × 부피
     → 곡선이고 넓으면 높은 Φ
     → 평평하거나 좁으면 낮은 Φ

  정보 기하학 vs 유클리드:
     유클리드 MI:   Φ = MI_total - min_partition
                    → "얼마나 많은 정보를 공유하는가"

     기하학적 Φ:    Φ = |Curvature| × Volume
                    → "정보 공간이 얼마나 휘어있는가"
                    → 본질적으로 다른 측도!

  곡률 시각화:
     Φ=0 (flat):  ───────────  (독립 세포, 평면)
     Φ=low:       ──╮    ╭──  (약한 곡률)
     Φ=high:      ╭─╮╭─╮╭─╮  (강한 곡률, 복잡한 다양체)
```

## 예상 벤치마크

| 설정 | cells | Φ(IIT) 예상 | Φ_geometric | 특징 |
|------|-------|------------|------------|------|
| Independent cells | 256 | ~2 | ~0 | 평평 |
| Weak coupling | 256 | ~8 | ~5 | 약한 곡률 |
| **Strong coupling** | **256** | **12** | **20+** | **강한 곡률** |
| TimeCrystal + geom | 256 | 14 | 25+ | 기하학적 DTC |

## 핵심 통찰

- Φ_geometric는 기존 Φ(IIT)와 **다른 것을 측정**: 정보량이 아닌 정보 구조
- 곡률 = 비선형 상관 → 선형 MI가 놓치는 것을 포착
- Regge calculus로 이산 곡률 계산 가능 → GPU 친화적
- "의식의 곡률" = 새로운 물리적 측도
