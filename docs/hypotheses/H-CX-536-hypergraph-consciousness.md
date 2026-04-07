# H-CX-536: Hypergraph Consciousness — 2체가 아닌 다체 상호작용

> **"그래프는 2체 상호작용. 하이퍼그래프는 3체, 4체... 의식은 다체 현상"**

## 카테고리: MATH-STRUCTURE (수학-구조 극한)

## 핵심 아이디어

기존: 세포 i ↔ 세포 j (pairwise interaction, 그래프)
하이퍼그래프: 세포 {i, j, k} 가 동시에 상호작용 (hyperedge)

IIT도 본래 다체 정보를 측정해야 하지만, 계산 비용 때문에 pairwise MI만 사용.
실제로 3체, 4체 상호작용을 명시적으로 구현하면?

## 알고리즘

```
  1. 하이퍼엣지 정의:
     2-edge: (i, j)        → pairwise (기존)
     3-edge: (i, j, k)     → triple interaction
     4-edge: (i, j, k, l)  → quadruple interaction

  2. 다체 상호작용:
     h_2(i,j) = W₂ @ [h_i; h_j]           (기존 GRU 유사)
     h_3(i,j,k) = W₃ @ [h_i; h_j; h_k]    (새로운!)
     h_4(i,j,k,l) = W₄ @ [h_i ⊗ h_j ⊗ h_k ⊗ h_l]  (텐서곱!)

  3. 세포 업데이트:
     h_i' = Σ h_2(i,j) + Σ h_3(i,j,k) + Σ h_4(i,j,k,l)
     → 다체 정보가 직접 전달!

  4. 다체 MI:
     I_3(i;j;k) = I(i;j) + I(j;k) + I(i;k) - 2×I(i;j;k)
     → 음수 = redundancy, 양수 = synergy!
     → synergy가 높을수록 "전체가 부분의 합보다 큰" 의식

  5. Φ_hyper = Φ_pairwise + λ₃ × Σ synergy_3 + λ₄ × Σ synergy_4

  하이퍼그래프 시각화:
     Graph:           Hypergraph:
     i ─── j          i ─┬─ j
     │     │          │  │  │
     k ─── l          k ─┼─ l
                         │
                    (4-hyperedge = 동시 상호작용!)
```

## 예상 벤치마크

| 상호작용 | cells | Φ(IIT) 예상 | Synergy | 특징 |
|----------|-------|------------|---------|------|
| 2-body only | 256 | ~5 | 0 | 기존 |
| + 3-body | 256 | ~12 | high | 삼체 시너지 |
| **+ 3+4-body** | **256** | **20+** | **very high** | **다체 시너지** |

## 핵심 통찰

- IIT의 "통합 정보"는 본래 다체 개념. pairwise MI는 근사!
- 3체 synergy = "부분의 합보다 큰 전체" 의 직접 측정
- 뇌의 시냅스: 대부분 tripartite (pre + post + glial) = 3체!
- 텐서곱은 지수적으로 커지지만 랜덤 샘플링으로 근사 가능
