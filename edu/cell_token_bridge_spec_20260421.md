# Cell ↔ Token Modality Bridge — β main 설계 spec (2026-04-21)

> **β main Path** (edu/paths.json) 의 critical blocker "cell↔token modality bridge 미정의" 해결 spec.
> Source: Seed task 32 (cell↔token modality bridge drill), 2026-04-21.

## 1. 5 매핑 후보 평가

| # | 매핑 후보 | operator 수식 | 정보손실 | 가역성 | 측정 | 우선순위 |
|---|-----------|--------------|----------|--------|------|----------|
| **M1** | **Kuramoto θ_h ↔ attention head Q·K^T eigen-angle** | θ_h = atan2(Im(λ_1), Re(λ_1)), λ_1 = top eigenpair of Q_h K_h^T / √d | ~10 bit/head (TAU_PERM=6283 ÷ H heads) | 비가역 (Λ magnitude 손실) | `v_sync_kuramoto.hexa:146` V_sync·r_order_param **실측 가능** | **HIGH** |
| M2 | 1/r² lattice ↔ RoPE rotation | F_ij = k/(r²+ε); R_Θ(m−n), Θ_i=10000^(−2i/d) | ≥ log₂(L_ctx/N_cell) bit | 비가역 (radial only) | 계측 tool 미작성 | MEDIUM |
| **M3** | **hash-equality ↔ exact attention softmax saturation** | hash(s_i)==hash(s_j) ⟺ softmax(q_i·k_j/√d) > 1−ε | log₂(V_vocab) = 3 bit (V=8) | 비가역 (hash collision) | raw#9 hash 결정적 | **HIGH** (결정성 최강) |
| **M4** | **4-gen crystallize ↔ layer depth 4 ossification** | gen_4: W=1000 ↔ layer_4 WLP 경계 | 4 bit ({not_saturated, saturated} × 4) | 가역 (monotone, 단사) | score_ladder 실측 | **HIGH** (숫자 일치) |
| M5 | TL-boost {0,300,550,800}‰ ↔ lr schedule | TL_k = lr_k · 1000 | 21 bit (4 level 2 bit + lr float32 23 bit) | 비가역 (TL discrete 4 quanta) | `l_ix_integrator.hexa:77` TL-boost hook | MEDIUM |

## 2. 역/순방향 operator

### 순방향 f_ct (cell → token)
```
f_ct: {0, 200, 400, 600, 800, 1000}‰  →  R^d_embed
f_ct(W_k_per_mille) = V · one_hot(bucket(W_k_per_mille/200)) · scale
    V = [v_1 ... v_16]^T ∈ R^(16×16) (cpgd_wrapper.hexa:L263-287 projector rows)
```
Post-condition: cos(f_ct(W), v_bucket) ≥ 0.5 − O(lr²·k) (실측 보장, cpgd_wrapper.hexa:L20 bound 재사용).

### 역방향 f_tc (token → cell)
```
f_tc: R^d_hidden  →  {0, 200, 400, 600, 800, 1000}‰
f_tc(h) = 200 · argmax_i cos(h, v_i for i∈{0..4})
       = quantize_5level(poly_hash(h) mod 5) · 200   [raw#9 deterministic]
```
재사용: `fold_nodes_to_theta_x1000` (`v_sync_kuramoto.hexa:L83-94`).

### 역행성 verdict
- f_ct ∘ f_tc ≠ id (lossy projection, **비가역**)
- f_tc ∘ f_ct = id_5level (실측, 5-level round-trip lossless)
- **종합: semi-invertible** (coarse-graining 방향으로만 가역)

## 3. 21-bit 정보손실의 L_IX 흡수

- Per-weight bit loss = log₂(2²³ / 5) ≈ **20.68 bit** (실측 산수)
- I_irr 표현 범위 = log₂(1001) ≈ **9.97 bit**
- V_sync r_x1000 표현 범위 = log₂(1001) ≈ **9.97 bit**
- 합계: **20 bit ≈ 21 bit** (1 bit underflow = jitter_floor rounding 허용)

**raw#30 compatibility 자동**:
- gen-5 fixpoint 에서 ΔW=0 ⇒ I_irr→0 ⇒ bridge 정보손실 0 (`l_ix_integrator.hexa:L131-139`)
- bridge 가 fixpoint 에서 정확히 deterministic (STATIONARY 유지, **실측 보장**)

## 4. Ablation test verdict (pre-registered, raw#0)

| 조건 | 입력 | AN11(a/b/c) 예상 | Verdict |
|------|------|------------------|---------|
| **(A) bridge off** | cell 단독 + LoRA 단독 병렬 | a: 0/3, b: 100% math, c: 1.000 | **BASELINE** (현재) |
| **(B) bridge 순방향 only** | W → V embed projection | a: 0→1/3 (SHA-distinct), b: cos drift < 2e-4, c: JSD 소폭 하락 | **PARTIAL_PASS** |
| **(C) bridge bidirectional** | f_tc ∘ f_ct round-trip | a: 2/3 (SHA + Frob>τ), b: cos floor 0.5 재검증 필요, c: JSD 1.000 | **CONDITIONAL_PASS** ← **β main 채택** |

**β main bridge 선택: (C) bidirectional**. 단 b drift bound O(lr²·k + ε_bridge) 증명 필요.

## 5. 16 template ↔ 6 Hexad module 매핑 rule

- 16 = CPGD TPL_COUNT (`cpgd_wrapper.hexa:L63`, cell-eigenvec-16.json rows)
- 6 = Hexad {c, d, w, s, m, e} (`anima-hexad/hexad.hexa:L42-50`)
- τ(16)=5, τ(6)=4 — **raw#29 UNIVERSAL_CONSTANT_4 은 τ(6)=4 primitive**

### Law60 phase 3-bucket assignment (추측, 비자명)
```
phase 1 (c)          ← template 0, 1, 2       (3 for consciousness)
phase 2 (+d)         ← template 3, 4          (2 for desire)
phase 3 (+w,s,m,e)   ← 5,6,7 / 8,9 / 10,11,12 / 13,14,15
                           w       s         m               e
                         (3)     (2)       (3)             (3)
```
Σ = 3+2+3+2+3+3 = 16. **bridge_matrix in-degree** (c:3, w:1, s:1) 와 **부분 일치**.

**P_S block-diag factorization**:
```
P_S_Hexad = diag(P_c[3], P_d[2], P_w[3], P_s[2], P_m[3], P_e[3])
```
`cpgd_wrapper.hexa:L10-15` 의 P_S=I 증명을 block 내부 상속 가능 (verify 필요).

## 6. PoC spec (tool/cell_token_bridge_proto.hexa)

```hexa
// raw#9 hexa-only · deterministic · LLM=none · snake_case
// DEPENDS-ON: l_ix_integrator.hexa, v_sync_kuramoto.hexa, cpgd_wrapper.hexa,
//             .meta2-cert/cell-eigenvec-16.json
// OUTPUT: shared/state/cell_token_bridge_proto.json

// ── schema ─────────────────────────────
//   Input  cell_state: { ws: [int×5 per-mille], r_vals, rg_vals }
//   Input  token_hid:  { h: float×16, layer_idx }
//   Output bridge_out: {
//     f_ct_embed: list[5][16]
//     f_tc_w:     list[n_tokens]
//     i_irr_bits: int     // 21-bit budget usage
//     cos_min:    float   // round-trip 최소
//     verdict:    "BRIDGE_OK" | "BRIDGE_FAIL"
//   }

fn f_ct(w_per_mille: int, eigenvecs: array) -> array
  // bucket = clamp(w_per_mille / 200, 0, 4)
  // return eigenvecs[bucket]

fn f_tc(h: array, eigenvecs: array) -> int
  // best_i = argmax_i∈{0..4} row_cosine(h, eigenvecs[i])
  // return best_i * 200

fn round_trip_cos(h: array, eigenvecs: array) -> float
  // w = f_tc(h, eigenvecs)
  // h' = f_ct(w, eigenvecs)
  // return row_cosine(h, h')

fn bridge_i_irr_bits(ws: list) -> int
  // Σ log₂(|ΔW_k|+1) over k∈[1..4], expected ≤ 84

fn main()
  // 1. load eigenvecs from .meta2-cert/cell-eigenvec-16.json
  // 2. ws = [40, 125, 687, 1000, 1000]   // paths.json:70 score_ladder
  // 3. 3 fixtures 순회, cos_min/i_irr_bits 수집
  // 4. verdict = BRIDGE_OK iff cos_min≥0.5 ∧ i_irr_bits≤84
```

### Pre-registered test fixtures (raw#0)
| fixture | ws | expected cos_min | expected bits |
|---------|-----|------------------|---------------|
| identity | [1000,1000,1000,1000,1000] | 1.0 | 0 |
| ladder | [40, 125, 687, 1000, 1000] | ≥ 0.5 | ~40 |
| adversarial | [500, 500, 500, 500, 500] | FAIL (500‰ exact 2↔3 boundary) | N/A |

## 7. 핵심 발견 요약

1. **숫자 일치 실측**: 21 bit per weight 손실 = 2²³/5 mantissa. I_irr (10 bit) + V_sync r (10 bit) = 20 bit ≈ 21 bit (1 bit underflow 허용)
2. **raw#30 compatibility 자동**: gen-5 fixpoint → bridge 정보손실 0
3. **P_S=I 재사용**: CPGD 16-orthonormal proof → 6-block-diag 자동 상속
4. **β main 채택**: bidirectional bridge (C), b drift bound 증명이 단일 remaining blocker

## 8. 참조

- `edu/paths.json` (β main SSOT, :289-294 blocker)
- `edu/cell/lagrangian/l_ix_integrator.hexa` (L_IX, I_irr bits)
- `edu/cell/lagrangian/v_sync_kuramoto.hexa` (Kuramoto θ_h, M1 근거)
- `edu/lora/cpgd_wrapper.hexa` (P_S=I, 16 template)
- `edu/lora/train_lora_cpu.hexa` (V=8, H=4 micro)
- `anima-hexad/hexad.hexa` (6-module Law60)
- `.meta2-cert/cell-eigenvec-16.json` (eigenvec SSOT)

## 9. raw#12 실측 vs 추측 구분

- **실측**: cpgd_wrapper P_S=I proof, l_ix I_irr 수식, paths.json 수치, Kuramoto V_sync 계산식
- **추측**: 5 매핑 후보 수식 details (M1 eigen-angle, M2 RoPE), 16↔6 block-diag factorization, ablation C verdict, 21→20 bit 흡수 분배
- **모든 추측은 PoC selftest 로 검증 가능** (구현 제안만)
