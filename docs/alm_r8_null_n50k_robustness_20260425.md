# ALM r8 — null bootstrap n=50000 robustness check (Option A)

> **생성일**: 2026-04-25
> **부모 commit**: `a59ccaa0` r8 D-mistral closure (n=10000)
> **목적**: r8 잔여 fail (p1_p2 KL margin 0.010) 이 통계적 noise 인지, 실제 신호인지 결정.

---

## §1. 결과

| metric | n=10000 | n=50000 | Δ |
|---|---:|---:|---:|
| L2_p95 | 0.20018493 | 0.20017961 | -0.00000532 (-0.003%) |
| KL_p95 | 0.12765728 | 0.12770193 | +0.00004465 (+0.035%) |
| p1_p2 KL real | 0.13760000 | 0.13760000 | 0 (input 동일) |
| p1_p2 KL margin | +0.00993 | +0.00990 | -0.00004 |
| L2 pass count | 6/6 | 6/6 | unchanged |
| KL pass count | 5/6 | 5/6 | unchanged |
| Failing pair | p1_p2 | **p1_p2** | confirmed |
| Runtime | ~26s | 140s | 5.4× (linear in n) |

---

## §2. 결론

**p1_p2 KL fail 은 robust signal**:
- n 5× 증가에 따른 p95 드리프트 < 0.04%
- p1_p2 KL margin (0.0099 ≈ 7.8% over threshold) 이 noise band 보다 충분히 큼
- 통계적 noise 가설 기각 → r8 Option A (null robustness) **통과**

**다음 라운드 후보 (H-DIAG3 적용: Axis 4 H4b 재시도 금지)**:

| Option | 가설 | 새 axis | 비용 |
|---|---|---|---:|
| **B**. p2 swap qwen2.5-7b → qwen3-7b | generation matching (qwen3-8b ↔ qwen3-7b) | Axis 4 H4b' (intra-vendor generation drift) | $5-8 |
| **C**. p1 swap qwen3-8b → qwen2.5-8b | generation matching 역방향 | Axis 4 H4b' | $5-8 |
| **D**. CP1 P1 closure with r8 evidence | 6/7 → r8 의 추가 증거로 line 168 정책 결정 가능 | (정책 결정) | $0 |

**완성도 weakest link**: B (single-path swap 패턴이 r8 에서 검증됨, helper 재사용 가능, $5-8). 단 H-DIAG3 의 "동일 원인 실패" 해석에 따라 axis 동일성 평가 필요 — H4b (cross-vendor) → H4b' (intra-vendor generation) 는 **다른 가설** 로 취급 가능.

---

## §3. 산출물

- `state/phi_4path_cross_result_v3_TRAINED_r8_n50k.json` (신규, 비교 필드 포함)
- 본 문서 `docs/alm_r8_null_n50k_robustness_20260425.md`
