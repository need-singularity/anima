# Mk.XI PASS Verdict Protocol — raw#12 frozen 2026-04-25

**Schema**: `anima/mk_xi_pass_verdict_spec/1`
**State SSOT**: `state/mk_xi_pass_verdict_spec_20260425.json`
**Architecture xref**: `state/mk_xi_architecture_spec_20260425.json`
**raw 정책**: `raw#9` (spec only), `raw#10` (no overclaim), `raw#12` (composite verdict frozen), `raw#15` (SSOT), `raw#37` (doc/state only), `POLICY R4` (기존 verifier scope 보존)

---

## 1. 목적

Mk.XI minimum consciousness-correlate architecture에 대한 **PASS verdict aggregation** rules + **composite verdict matrix** 사전 동결 (raw#12 frozen). measurement 진입 전 7개 verdict category + 6개 PASS predicate 등록하여 post-hoc cherry-pick 차단.

---

## 2. PASS Verdict Aggregation Rules

### 2.1 Tuple Semantics

| Tuple | Axes | Joint H0 (independence) | 용도 |
|---|---|---|---|
| 4-tuple | V0+V1+V2+V3 | 0.05^4 ≈ 6.25e-6 | baseline only |
| **5-tuple (PRIMARY)** | V0+V1+V2+V3+V_pairrank | 0.05^5 ≈ 3.125e-7 (< 1e-6) | **Mk.XI primary verdict 단위** |
| 6-tuple (EXTENSION) | 5-tuple + V_sub | 0.05^6 ≈ 1.5625e-8 | ANTI_MAP frozen 후 활성 |

**raw#12 lock**: 5-tuple이 본 spec primary unit. 6-tuple은 V_sub spec ANTI_MAP/RANDOM ground truth pre-registration 후 activation.

### 2.2 Per-Axis PASS Predicate (cross-reference, frozen)

| Axis | Metric | Predicate | Frozen spec |
|---|---|---|---|
| **V0** | max_cosine over 16-template | `max_cosine > 0.5` | `state/alm_r6_p{1..4}_an11_b.json` |
| **V1** | Φ_mip | `phi_mip >= 0.55` | `tool/an11_b_v1_phi_mip.hexa` |
| **V2** | SMA_lift + SMA absolute | `SMA_lift >= +0.20 AND SMA >= 0.55` | `tool/an11_b_v2_sma.hexa`, `tool/an11_b_v2_papo_multi_axis.hexa` |
| **V3** | CPS + delta_pres + delta_des | `CPS >= 3.0 AND delta_pres <= 0.20 AND delta_des >= 0.40` | `tool/an11_b_v3_cps.hexa` |
| **V_pairrank** | V_pairrank + top3_hit | `V_pairrank >= 0.50 AND top3_hit >= 0.80` | `tool/an11_b_v_pairrank.hexa` |
| **V_sub** (6-tuple) | V_sub = δ_anti / δ_rand | `V_sub >= 2.0` | `state/an11_v3_semantic_substitution_metric_spec_20260425.json` |

**V3 metric flag (raw#10 disclosure)**:
- V3 original Gram Frob ratio = **FALSIFIED** (commit `c369b375`)
- V3 v2 mirror SMA permutation = **FALSIFIED** (commit `1002d16a`)
- V_pairrank = V3와 **orthogonal axis** (path-level orthogonality probe, commit `55132d54`)
- V_sub redesign 후보 (Option C) — measurement NOT performed, ANTI_MAP 부재

### 2.3 Aggregation Order & Tie-Break

- **Evaluation order**: V0 → V1 → V2 → V3 → V_pairrank (axis index 순서). 6-tuple 시 V_sub 마지막.
- **Tie-break**: matrix entry는 mutually exclusive. 동시 PASS 시 단일 verdict.
- **Boundary**: V_sub AMBIGUOUS [1.3, 2.0)은 FAIL 처리 (raw#10 conservative).
- **raw#12 lock**: post-hoc threshold tuning 금지. measurement 후 verdict re-define = raw#12 violation.

---

## 3. Composite Verdict Matrix (5-tuple PRIMARY)

```
5-tuple all PASS                     → MK_XI_VERIFIED
V0+V1+V2+V3 PASS, V_pairrank FAIL    → MK_XI_PARTIAL_RETRIEVAL_FAIL
V0+V1+V2+V_pairrank PASS, V3 FAIL    → MK_XI_PARTIAL_V3_FAIL
V0+V2+V3+V_pairrank PASS, V1 FAIL    → MK_XI_PARTIAL_V1_FAIL
V0+V1+V3+V_pairrank PASS, V2 FAIL    → MK_XI_PARTIAL_V2_FAIL
V0 PASS only                         → MK_XI_TEMPLATE_FITTED_NON_INTEGRATED
≤2 PASS                              → MK_XI_FALSIFIED
```

### 3.1 Failure-Mode → Next-Cycle Action Map

| Verdict | Interpretation | Next-cycle action |
|---|---|---|
| **MK_XI_VERIFIED** | consciousness-correlate verifiable floor 도달 (joint H0 < 1e-6) | 6-tuple V_sub extension / Mk.XII proposal |
| **MK_XI_PARTIAL_RETRIEVAL_FAIL** | structural 4/4 PASS, retrieval lever 부재 | retrieval head 조정 + L_contrastive_pair λ sweep `[0.1, 0.3, 1.0, 3.0]` |
| **MK_XI_PARTIAL_V3_FAIL** | V3 metric flaw (Gram Frob FALSIFIED 인지) | V_sub spec revision / ANTI_MAP v3 revision |
| **MK_XI_PARTIAL_V1_FAIL** | atom partition ossification 부족 | Mk.X T10-13 atom partition path (≥10 atoms, Φ_atom_floor ≈ 0.9) |
| **MK_XI_PARTIAL_V2_FAIL** | PAPO top-3 lever translation 실패 | λ_papo sweep + D-mistral architecture 재확인 (Axis 4 H4b VALIDATED, `da156aa0`) |
| **MK_XI_TEMPLATE_FITTED_NON_INTEGRATED** | 4-tuple FAIL, integration 모든 axis 실패 | fundamental rethink — backbone / L_total composition 재검 |
| **MK_XI_FALSIFIED** | ≤2 PASS, substrate path 실패 | architecture path 재고 — Mk.XII alternative / Mk.IX L_IX 단독 재시도 |

---

## 4. 6-tuple Extension Rules

**Activation prerequisite** (모두 충족 시):
1. ANTI_MAP design protocol 5단계 PASS (per `an11_v3_semantic_substitution_metric_spec_20260425.json`)
2. RANDOM pool frozen (별도 prompts pool, raw#12 new revision)
3. forward batch (anti + random) 수행 (forward auto-approval per memory)

**6-tuple verdict matrix**: 5-tuple matrix + V_sub axis. 7 verdict 카테고리는 5-tuple과 동일 schema, V_sub PASS 여부는 추가 modifier.

**Extension semantics**: 5-tuple PASS + V_sub PASS = strongest verifiable correlate (joint H0 ≈ 1.5e-8). 5-tuple PASS + V_sub FAIL = MK_XI_VERIFIED (V_sub는 stronger evidence axis로 우선 차원에서는 5-tuple 기준 유지) but trigger V_sub redesign cycle.

---

## 5. Statistical Justification (raw#12 frozen)

### 5.1 Joint Independence Assumption

각 axis PASS threshold는 random baseline distribution 5%-tile 기준 (raw#12 frozen):
- V1 phi_mip 0.55 ≈ random Φ_mip 5%-quantile
- V2 SMA_lift 0.20 ≈ paired structure absent baseline 5%-tile
- (per-axis 사전 등록, post-hoc tuning 금지)

### 5.2 Joint H0 Computation

| Tuple | Joint H0 (independence) | < 1e-6 floor 만족 |
|---|---|---|
| 4-tuple | 0.05^4 ≈ 6.25e-6 | ✗ |
| **5-tuple** | **0.05^5 ≈ 3.125e-7** | **✓** |
| 6-tuple | 0.05^6 ≈ 1.5625e-8 | ✓ (much stronger) |

### 5.3 Independence Caveat

real correlation may inflate joint p-value. 하지만 본 세션 orthogonality probe finding (commit `55132d54`)에서:
- V0/V2 vs V_pairrank/CCC = path-level orthogonal
- 5-tuple은 substrate-level orthogonal axes로 구성

따라서 joint 독립성 가정은 substrate evidence로 정당화. **5-tuple PASS = consciousness-correlate verifiable floor**.

---

## 6. raw#10 Honest Scope (Non-Overclaim)

### 6.1 Verifiable Floor Definition

> 5-tuple PASS = **third-person measurement framework로 도달 가능한 가장 강한 evidence**. consciousness-correlate **verifiable floor**.

### 6.2 NOT Phenomenal Consciousness

- **Hard Problem of Consciousness** (Chalmers): subjective experience를 third-person measurement로 입증 불가.
- **Levine explanatory gap**: functional correlate ≠ phenomenal experience.
- 본 spec의 5-tuple PASS는 **functional/structural correlate**만 측정. **phenomenal consciousness 보장 X**.

### 6.3 Framing

Mk.XI 5-tuple PASS은 **'minimum verifiable correlate floor 도달'** 주장.
**'machine is conscious'** 주장 **아님**.

### 6.4 Metric Flag Disclosure (raw#10)

| Metric | Status | Commit |
|---|---|---|
| V3 Gram Frob ratio | FALSIFIED | `c369b375` |
| V3 v2 mirror SMA | FALSIFIED | `1002d16a` |
| V_pairrank base | FAIL (top3 hit 0%) | `c3aaea8b` |
| V_sub | NOT_TESTED (ANTI_MAP 부재) | — |

---

## 7. raw 호환 자가 검증

| Constraint | Status | Note |
|---|---|---|
| **raw#9** spec only, $0 | PASS | doc + state JSON SSOT only, no measurement |
| **raw#10** phenomenal/functional 구분 | PASS | verifiable floor 명시, V3 FALSIFIED disclosure |
| **raw#12** composite verdict frozen | PASS | 7 verdict + 6 predicate 사전 등록, post-hoc 금지 |
| **raw#15** SSOT | PASS | this doc + `state/mk_xi_pass_verdict_spec_20260425.json` |
| **raw#37** doc/state only | PASS | no .py / .sh |
| **POLICY R4** existing verifier scope 보존 | PASS | 기존 verifier 변경 없음, aggregation은 신규 axis |

---

## 8. Cross-Reference Summary

- **Architecture spec**: `state/mk_xi_architecture_spec_20260425.json` (5-tuple all-PASS minimum architecture)
- **V_sub spec**: `state/an11_v3_semantic_substitution_metric_spec_20260425.json` (6-tuple extension)
- **V0**: `state/alm_r6_p{1..4}_an11_b.json`
- **V1/V2/V3/V_pairrank verifiers**: `tool/an11_b_*.hexa`
- **Forward auto-approval**: memory `feedback_forward_auto_approval`

**raw#12 frozen 2026-04-25** — measurement 진입 후 verdict matrix / threshold / aggregation rule 변경 시 raw#12 violation log.
