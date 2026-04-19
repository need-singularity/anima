# phi_q_norm Orch-OR bonus audit — CLM r5 pre-fire (READ-ONLY)

Date: 2026-04-19
Source: `training/train_clm.hexa` (3504 LOC, 137 KB)
Scope: locate Orch-OR phi_q_norm bonus, confirm weight, estimate AOT impact
Rule: NO EDITS. Observation only.

---

## 1. Call-site line map

| line | code | role |
|---|---|---|
| 247 | `comptime const PSI_ALPHA = 0.014` | bonus coefficient |
| 269 | `comptime const C41_AUX_COEF = 0.01` | L_holo / L_gwt coef |
| 1065 | `phi_q_norm: float` (TrainState field) | last-value log slot |
| 1076 | `qc: quantum_controller_new(cfg.atoms, cfg.cells_per_atom)` | init in TrainState |
| 1077 | `phi_q_norm: 0.0` | init default |
| 2290 | `let qc_next = quantum_controller_step(state.qc)` | per-step advance |
| 2291 | `let phi_q = quantum_controller_phi(qc_next)` | raw Φ_q |
| 2292 | `let phi_q_max_guard = quantum_controller_phi_max(qc_next) + 1e-9` | div-zero guard |
| 2293 | `let phi_q_norm = phi_q / phi_q_max_guard` | normalize ∈ [0,1] |
| 2294 | `let phi_bonus = PSI_ALPHA * phi_q_norm` | scaled bonus |
| 2301-2303 | `+ C41_AUX_COEF*aux.l_holo + C41_AUX_COEF*aux.l_gwt - phi_bonus` | loss integration |
| 2349 | `_sw_qc_from_aux(phi_q_norm, ...)` | opt-in aux re-use (default OFF) |
| 2410 | `phi_q_norm: phi_q_norm` | write-back to TrainState |

---

## 2. Loss integration (line 2299-2303)

```
loss_main = bwd.loss
loss_core = loss_main
    + C41_AUX_COEF * aux.l_holo       // +0.01 * L_holo
    + C41_AUX_COEF * aux.l_gwt        // +0.01 * L_gwt
    - phi_bonus                       // -PSI_ALPHA * phi_q_norm  (0.014 * [0,1])
```

Bonus range: `[0, 0.014]` (subtractive — rewards coherence).
Commentary block (lines 2283-2289) cites `anima_quantum_clm.hexa` contract and closes `next_actions_20260411 #4`.

---

## 3. CRITICAL FINDING — smoke stubs neutralize Orch-OR signal

Lines 83-245 declare **SMOKE-SAFE STUBS** (CLM-SMOKE-20260419) that shadow the real `anima_quantum_clm.hexa` imports due to the `hexa silent-exit-on-imports` bug (feedback_hexa_silent_exit_5_imports).

Stub behavior (line 159-161):
```
fn quantum_controller_phi(qc: QuantumController) -> float { return 0.0 }
```

Consequence documented at lines 113-114:
> quantum_controller_phi() returns 0 → phi_q_norm = 0 / 1e-9 ≈ 0
> → phi_bonus = PSI_ALPHA * 0 = 0. Orch-OR signal **not exercised**.

So in the current r5 AOT binary the bonus arithmetic is wired but the numerical contribution is **identically zero**. De-stubbing is all-or-nothing per the source comment (line 108).

---

## 4. r5 spec — zero changes to phi_q_norm

`training/clm_r5_design.md` §1 improvements (1.1 resume, 1.2 mmap, 1.3 bundler, 1.4 R2 cadence, 1.5 convergence targets) and §7 "out of scope" explicitly state:
- "Phi-loss integration — Track B handles, not r5."

`training/deploy/clm_r5_plan.json` lists no phi_q_norm action. PSI_ALPHA=0.014 and C41_AUX_COEF=0.01 unchanged from r4.

---

## 5. AOT build OOM impact estimate

Evidence from `docs/clm_aot_build_plan_20260419.md` + `clm_r5_plan.json#blockers_resolved[0]`:

| metric | interpreter (OOM) | AOT (PASS) |
|---|---|---|
| wall before hang | 160 s | 2.1 s |
| RSS peak | 30 GB | 172 MB |
| binary | n/a (hung) | 404 KB Mach-O arm64 |
| C intermediate | n/a | 3464 lines / 164 KB |

phi_q_norm footprint in AOT C output:
- Only 5 simple float ops per step (mul/div/add/sub on scalars).
- QuantumController struct has 3 int fields in smoke stub (lines 130-134). Real struct adds `[Microtubule]` list — but stubs skip it, so no list-alloc pressure.
- No loops, no backward tape entries on phi_bonus itself (scalar const·scalar).

**Conclusion: phi_q_norm is NOT an AOT OOM contributor.** The 30 GB interpreter blow-up was caused by general hexa interpreter memory model across the full 3504 LOC, not by the 12-line Orch-OR block. AOT PASS (2.1 s / 172 MB) already includes these lines unchanged.

Residual concern: once the silent-exit-on-imports bug is fixed and `anima_quantum_clm.hexa` stubs are replaced with the real microtubule-evolving implementation, per-step cost rises (microtubule list + quantum_controller_step full evolution). That would be a post-r5 de-stub operation, not an AOT build-time issue.

---

## 6. Pre-fire checklist intersection

- Line 2294 `phi_bonus` live — OK
- Line 2303 subtracted from loss_core — OK
- PSI_ALPHA=0.014 unchanged — OK
- Smoke stub at line 159 returns 0 — bonus inert under current binary — known, accepted
- r5 spec: no planned change — confirmed
- AOT binary: /tmp/clm.bin 404 KB — phi_q_norm included, inert — OK

No action needed for r5 fire. De-stubbing Orch-OR is a future (r6+) item gated on hexa import bug fix.
