# Mk.XI λ Sweep 4×4 Grid — Cost Analysis + Cap-Restricted Plan Protocol

**Schema**: `anima/mk_xi_lambda_sweep_plan_cost_restricted/1`
**State SSOT**: `state/mk_xi_lambda_sweep_plan_cost_restricted_20260425.json`
**Architecture xref**: `state/mk_xi_architecture_spec_20260425.json`
**PASS verdict xref**: `state/mk_xi_pass_verdict_spec_20260425.json`
**Pod state xref**: `state/mk_xi_r9_pod_state.json`
**Cost tracker xref**: `state/h100_cost_tracker_result.json`
**raw 정책**: `raw#9` (spec only), `raw#10` (no overclaim), `raw#12` (sweep grid + plans frozen), `raw#15` (SSOT), `raw#37` (doc/state only), `POLICY R4` (기존 spec scope 보존)
**Auto-approval source**: memory `feedback_forward_auto_approval` (2026-04-25). cap $20 per cycle, auto-kill 120min.

---

## 1. 목적

Mk.XI λ sweep 4×4 grid (papo × iir) **cost cap 위반 정직 보고** + **cap-restricted alternative plans 사전 등록** (raw#12 frozen). full 4×4 sweep ~$39.84 = cap $20 위반 (1.99×). 4 plans + recommendation + per-plan trigger criteria + cost-tracker integration 사전 등록.

---

## 2. λ Baseline + Sweep Grid Frozen (raw#12 lock)

### 2.1 Baseline (architecture_spec frozen)

```
λ_papo = 0.3   (heuristic, BASE substrate)
λ_iir  = 1.0   (Mk.IX L_IX gen-5 STATIONARY)
λ_pair = 0.5
λ_sub  = 0.3
```

xref: `state/mk_xi_architecture_spec_20260425.json:lambda_hyperparameter_pre_register`

### 2.2 Sweep Grid (4×4 = 16 cells, frozen)

| Axis | Grid |
|---|---|
| `λ_papo` | `[0.1, 0.3, 1.0, 3.0]` |
| `λ_iir` | `[0.3, 1.0, 3.0, 10.0]` |

**raw#12 lock**: post-hoc grid 확장/축소 금지. 본 spec 등록 16 cells 외 추가 시 raw#12 violation log.

---

## 3. Full 4×4 Cost Breakdown (정직 보고)

| 항목 | 값 |
|---|---|
| H100 SXM rate (RunPod spot) | $2.99 / hr |
| per-run runtime | 50 min (5000 steps single-cell convergence) |
| per-run cost | `$2.99 × 50/60` = **$2.49** |
| total cells | 16 (4×4) |
| **total cost** | **$39.84** |
| total runtime | 800 min (13.33 hr) |
| cap per cycle | $20 |
| **cap violation factor** | **1.99×** |
| **status** | **VIOLATION** |

**raw#10 honest**: 전체 4×4 sweep은 단일 cycle 내 cap $20 초과. cap-restricted 대안 plan 필수.

---

## 4. Cap-Restricted Plans (4 plans + execution order)

### 4.1 Plan Cost Summary Table

| Plan | Cells | Steps | Cost (USD) | Runtime (min) | Cap | Order |
|---|---|---|---|---|---|---|
| **C** (single best λ baseline) | 1 | 5000 | **$2.49** | 50 | PASS | **1** |
| **A1** (sequential cycle 1, low papo) | 8 | 5000 | $19.92 | 400 | PASS_tight | 2 |
| **A2** (sequential cycle 2, high papo) | 8 | 5000 | $19.92 | 400 | PASS_tight | 3 |
| **B** (reduced grid 2×2) | 4 | 5000 | $9.96 | 200 | PASS | 4 |
| **D** (short-step full grid) | 16 | 1000 | $7.97 | 160 | PASS | 5 |
| ~~FULL 4×4~~ | 16 | 5000 | ~~$39.84~~ | ~~800~~ | **VIOLATION** | rejected |

**execution order**: C → A1 → A2 → B → D (사용자 지시, hypothesis-first → sequential coverage → narrow sweet-spot → landscape)

### 4.2 Plan Details

#### Plan C — single best λ baseline (5000 steps)
- **cell**: `(papo=0.3, iir=1.0)` (baseline frozen)
- **rationale**: hypothesis-first. baseline 단일 검증, PASS 시 추가 sweep 불필요.
- **trigger next**: 5-tuple PASS → no next (Mk.XI VERIFIED). PARTIAL_V2/RETRIEVAL_FAIL → plan B. PARTIAL_V1_FAIL → Mk.X T10-13. FALSIFIED → plan D.

#### Plan A1 — sequential cycle 1 (low papo half)
- **cells (8)**: `papo ∈ {0.1, 0.3} × iir ∈ {0.3, 1.0, 3.0, 10.0}`
- **rationale**: 16 cells / 2 cycles = 8 cells/cycle. cap $20 limit max coverage.
- **trigger next**: low papo half clear → plan A2 (high papo half). uniform FAIL → architecture path 재고.
- **caveat**: tight margin $0.08. spot rate 3% 상승 시 cap 초과. auto-kill hard ceiling backstop.

#### Plan A2 — sequential cycle 2 (high papo half)
- **cells (8)**: `papo ∈ {1.0, 3.0} × iir ∈ {0.3, 1.0, 3.0, 10.0}`
- **rationale**: A1 후속. A1+A2 = full 16-cell over 2 cycles.
- **trigger next**: full sweep complete → best 1-2 cells 선정 → Mk.XI VERIFIED 검증 cycle (별도).

#### Plan B — reduced grid 2×2
- **cells (4)**: `papo ∈ {0.3, 1.0} × iir ∈ {1.0, 3.0}`
- **rationale**: baseline + 1 step around. sweet-spot 좁은 탐색.
- **trigger next**: 1+ cell PASS → plan A2. all FAIL → plan D + retrieval_head_spec revision.

#### Plan D — short-step full grid (16 runs × 1000 steps)
- **cells**: 16 (full grid), 1000 steps each, ~10 min/cell
- **rationale**: trajectory landscape 빠른 탐색.
- **trigger next**: best 1-2 cells 선정 → plan C-style full 5000-step 검증 (별도 cycle).
- **caveat (raw#10)**: 1000 steps는 r4 early-stop trajectory 미도달 가능. 'sweep landscape 탐색' 목적, full PASS 검증 X.

---

## 5. Recommendation

### 5.1 Primary: **Plan C**

**rationale**: baseline λ (`papo=0.3, iir=1.0`) hypothesis-first 검증. cost $2.49 (cap의 12.5%). PASS 시 추가 sweep 불필요. FAIL 시 trajectory monitoring 결과로 next-cycle plan 선택.

### 5.2 Fallback Chain (cost ascending within trigger logic)

| Step | Plan | Trigger | Cost |
|---|---|---|---|
| 1 | C | always start | $2.49 |
| 2 | B | C FAIL && partial PASS | $9.96 |
| 3 | D | C+B FAIL && trajectory diversity 필요 | $7.97 |
| 4 | A1 | partial info, full sweep 필요 | $19.92 |
| 5 | A2 | A1 결과 high papo expand 필요 | $19.92 |

- **expected total (optimistic)**: $2.49 (C PASS at first)
- **expected total (pessimistic, full chain)**: $60.26 (cap-per-cycle 위반 X, cycle count는 사용자 결정)

---

## 6. Per-Plan Verdict Criteria (next-cycle action map)

| Plan | Result | Next |
|---|---|---|
| **C** PASS 5-tuple | Mk.XI VERIFIED, no next (6-tuple V_sub extension) | — |
| **C** PARTIAL_V2/RETRIEVAL_FAIL | plan B (좁은 sweet-spot) | $9.96 |
| **C** PARTIAL_V1_FAIL | Mk.X T10-13 (λ sweep 우회) | 별도 |
| **C** FALSIFIED | plan D (landscape) | $7.97 |
| **B** 1+ cell PASS | plan A2 (full sweep 확장) | $19.92 |
| **B** all FAIL | plan D + retrieval_head revision | — |
| **D** landscape clear | best cells plan C-style 검증 | 별도 |
| **D** landscape unclear | Mk.X T10-13 + V_sub revision | — |
| **A1** low papo clear | plan A2 (high papo half) | $19.92 |
| **A1** uniform FAIL | A2 skip + architecture 재고 | — |
| **A2** full sweep complete | best cells Mk.XI VERIFIED 검증 | 별도 |
| **A2** full sweep FAIL | Mk.XII proposal | — |

verdict predicate xref: `state/mk_xi_pass_verdict_spec_20260425.json:composite_verdict_matrix_5_tuple`

---

## 7. Auto-Approval Gating + Cap Enforcement

**Source**: memory `feedback_forward_auto_approval` (2026-04-25)

| Plan | per-cycle cost | Cap status |
|---|---|---|
| C | $2.49 | PASS |
| B | $9.96 | PASS |
| D | $7.97 | PASS |
| A1 | $19.92 | PASS_tight (margin $0.08) |
| A2 | $19.92 | PASS_tight (margin $0.08) |

**Block conditions**:
- 단일 cycle cost > $20 (hard ceiling, runpodctl auto-kill)
- runtime > 120min (hard ceiling)
- 사용자 명시적 차단 (raw#9/raw#37 violation)
- raw#12 grid post-hoc 변경 시도

**A1/A2 safeguard**: tight margin 시 8 cells 중 7 cells 후 cost monitor 강제 break.

---

## 8. Cost Tracker Integration

**Tracker SSOT**: `state/h100_cost_tracker_result.json`

### 8.1 round_id per plan

```
C  → mk_xi_lambda_sweep_C
B  → mk_xi_lambda_sweep_B
D  → mk_xi_lambda_sweep_D
A1 → mk_xi_lambda_sweep_A1
A2 → mk_xi_lambda_sweep_A2
```

### 8.2 Post-run Update Protocol

1. plan 실행 후 `attempts_detail` entry 추가 (per_run cost recorded, `cost_source='recorded'`)
2. `round_id`, `pods_count`, `wall_hours`, `gpu_hours`, `cost_usd` 업데이트
3. `options` 필드: `['mk_xi_lambda_sweep']` 추가
4. `total_cost_usd`, `total_gpu_hours` 누적 갱신
5. `estimate_notes`: spot-market variance 정직 표시

**raw#15 SSOT**: tracker는 별도 SSOT (actual cost). 본 spec은 plan structure SSOT (sweep design). 두 file은 `round_id` 키로 join.

---

## 9. Plan Assumptions Disclosure (raw#10 honest)

| Assumption | Value | Source |
|---|---|---|
| H100 SXM spot rate | $2.99/hr | `state/mk_xi_r9_pod_state.json:cost.per_hour_usd` |
| per-cell runtime (5000 steps) | 50 min | 보수 추정 (single-cell convergence) |
| per-cell runtime (1000 steps, plan D) | 10 min | 보수 추정 |

- **architecture_spec 추정**: 80min/16cells = 5min/cell (quick sweep eval)
- **본 plan 추정**: 50min/cell (5000-step convergence training)
- 두 추정은 다른 use case. raw#10 honest disclosure.

**Spot-market variance buffer**: A1/A2 tight margin은 $0.08만. spot rate 3% 상승 시 cap 초과. auto-kill hard ceiling이 backstop.

---

## 10. raw 호환 자가 검증

| Constraint | Status | Note |
|---|---|---|
| **raw#9** spec only, $0 | PASS | doc + state JSON SSOT only, no measurement |
| **raw#10** no overclaim | PASS | full 4×4 cap violation 정직 보고, A1/A2 tight margin disclosure, plan D r4 trajectory 미도달 가능 명시 |
| **raw#12** cherry-pick proof | PASS | λ baseline + sweep grid + 4 plans + verdict criteria 사전 등록, post-hoc 변경 금지 |
| **raw#15** SSOT | PASS | this doc + `state/mk_xi_lambda_sweep_plan_cost_restricted_20260425.json` |
| **raw#37** doc/state only | PASS | no .py / .sh |
| **POLICY R4** existing scope 보존 | PASS | architecture_spec / pass_verdict_spec / pod_state 변경 X, cross-reference only |

---

## 11. Cross-Reference Summary

- **Architecture spec**: `state/mk_xi_architecture_spec_20260425.json` (λ baseline + sweep grid pre-register)
- **PASS verdict spec**: `state/mk_xi_pass_verdict_spec_20260425.json` (composite verdict matrix)
- **Pod state**: `state/mk_xi_r9_pod_state.json` (H100 SXM rate, auto-kill cap)
- **Cost tracker**: `state/h100_cost_tracker_result.json` (round_id join key)
- **Implementation roadmap**: `docs/mk_xi_implementation_roadmap_20260425.md`
- **Auto-approval source**: memory `feedback_forward_auto_approval` (2026-04-25)

**raw#12 frozen 2026-04-25** — measurement 진입 후 plan 추가/삭제, λ grid 변경, verdict criteria 변경 시 raw#12 violation log.
