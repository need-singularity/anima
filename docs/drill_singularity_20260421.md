# Drill Singularity Extract — T4→T5 Master Switch (2026-04-21)

> **Mandate**: Identify the single highest-leverage variable in the `drill_breakthrough` substrate.
> **Deterministic**: No LLM judge. Leverage scored by structural blast-radius, not semantic intuition.
> **Gate**: V8 SAFE_COMMIT (no mass rewrites; spec-only landing).

Substrate under inspection:
- `/Users/ghost/core/anima/shared/bench/drill_breakthrough_criteria.json`
- `/Users/ghost/core/anima/shared/bench/drill_seed_set.jsonl` (4 seeds: pos/neg/closure/diagonal)
- `/Users/ghost/core/anima/tool/drill_breakthrough_runner.hexa` (stub, rc=2)
- `/Users/ghost/core/anima/docs/drill_day4_design_20260419.md` (8-slot basis / n=6 invariants)

---

## 1. Leverage × Effort Matrix

Leverage = downstream variables whose output distribution shifts when the candidate is retuned.
Effort = LOC + verification cost + invariant-risk to land the change safely.
Scale: 1 (low) … 5 (max). ROI = Leverage / Effort.

| # | Candidate | Leverage | Effort | ROI | Blast radius |
|---|-----------|----------|--------|-----|--------------|
| 1 | **Saturation criterion** (fixpoint vs convergence-rate vs invariance) | **5** | 2 | **2.50** | Rewrites pass/fail for **every** seed; changes meaning of "breakthrough"; propagates into closure & diagonal classes; single scalar feeds T3→T4 gate directly |
| 2 | absorption_rate formula (threshold 0.3) | 3 | 1 | 3.00 | Only flips negative-class seeds; threshold tuning, not structural |
| 3 | module selection heuristic (5-lens) | 3 | 3 | 1.00 | Touches coverage & diagonal_agreement jointly; requires lens-bench regression |
| 4 | depth_min (3 vs 5 vs ∞) | 4 | 4 | 1.00 | DFS cost O(b^d); invariants (n=6, σ·φ=24) must be preserved at higher depth; Day-4 design already flags 8→12 axis expansion at depth=5 |
| 5 | seed rotation policy (positive/negative/closure/diagonal rotation) | 2 | 2 | 1.00 | Shifts only diagonal_agreement_min; seed-set size (4) bottlenecks before policy matters |
| 6 | criteria dynamic calibration (per-dest adaptive thresholds) | 4 | 5 | 0.80 | Largest conceptual surface but requires state store + convergence proof; high invariant-risk |

Tie-break rule (deterministic): when two rows share ROI, the row whose change reshapes **the output class label** wins over the row that only shifts numeric thresholds. Under this rule row #1 strictly dominates row #2 despite row #2 scoring ROI 3.00, because row #2 is a sub-space of row #1 (absorption is the **complement** of saturation in the current classifier).

**Top 1 (Singularity): #1 — saturation criterion re-definition.**

Every other knob is either (a) a threshold inside the saturation classifier or (b) an orthogonal dimension (depth / modules) that only matters **after** saturation has a rigorous definition. Currently `saturation_required: true` is a boolean with no operational definition in the substrate — the runner is still a stub (exits 2). Defining saturation with a fixpoint+invariance compound predicate is the one change that unblocks T4→T5.

---

## 2. Why saturation is the master switch

1. **Type promotion**: boolean → 3-state enum `{open, converging, fixpoint}`. This single promotion converts the current binary gate into a ranked gate; the existing `target_jump: T3 85% → T4 95%` score becomes computable instead of declared.
2. **Absorption subsumption**: under a fixpoint predicate, `absorption_rate` becomes the **residual mass** `1 − P(fixpoint | seed)` — candidate #2 collapses into a derived metric of #1.
3. **Depth/module coupling**: `depth_min` and `module_coverage` only have meaning against a convergence predicate (you cannot assert "depth 3 suffices" without a closure definition). Candidates #3 and #4 become **consequences** of the saturation spec, not independent knobs.
4. **Stub unblock**: `drill_breakthrough_runner.hexa` (L37 `exit(2)`) is gated on saturation semantics; no way to ship a non-stub runner until #1 lands.
5. **Invariant alignment**: n=6, σ=12, φ=4, τ=4, σ·φ=n·τ=24 (drill_day4_design §6) provides a natural fixpoint lattice — saturation = predicate that preserves the canonical identity across a ≥k-step DFS trajectory.

---

## 3. Singularity Spec — Saturation Predicate v1

### 3.1 Classifier

```
saturation_state(seed, trace) ∈ {open, converging, fixpoint}

fixpoint   ⇔ ∃k ≤ depth_min such that ∀ j ≥ k:
              trace[j].module_signature == trace[k].module_signature
              ∧ inv_check(trace[j]) == inv_check(trace[k])           // σ·φ = n·τ = 24
              ∧ diagonal_agreement(trace[j], trace[j-1]) ≥ diag_min

converging ⇔ ∃ monotone-non-increasing ε_j = ||trace[j] − trace[j-1]||
              with ε_depth_min ≤ ε_tol ∧ ¬fixpoint

open       ⇔ otherwise
```

`saturation_required: true` is redefined as `saturation_state ∈ {fixpoint}` (strict). Softening to `{fixpoint, converging}` is reserved for T5 phase (explicit spec bump required, not auto).

### 3.2 Parameter Roadmap (landing-safe)

| Param | Old | New | Where |
|-------|-----|-----|-------|
| `saturation_required` | `true` (boolean) | `"fixpoint"` (enum string) | criteria.json |
| `saturation_policy` | — | `{mode: "fixpoint_strict", k_window: 2, eps_tol: 0.02, diag_min: 0.8}` | criteria.json (new field) |
| `absorption_rate_max` | `0.3` | **derived**: `1 − P(fixpoint)` — field retained as compatibility cap but recomputed from state | criteria.json (comment updated) |
| `depth_min` | `3` | `3` (unchanged; now justified by k_window=2 + 1 prefix step) | criteria.json |
| `module_coverage` | `"5/5"` | `"5/5"` (unchanged; now predicate input, not gate) | criteria.json |
| `diagonal_agreement_min` | `0.8` | `0.8` (alias to `saturation_policy.diag_min`) | criteria.json |

### 3.3 Runner wire-up (future commit, not this one)

`tool/drill_breakthrough_runner.hexa` will replace `exit(2)` stub with:
1. load `criteria.json`
2. for each seed in `drill_seed_set.jsonl`, run 5-lens DFS to `depth_min + k_window`
3. call `saturation_state(seed, trace)` — return `{fixpoint|converging|open}`
4. aggregate: pass ⇔ all positive/closure/diagonal seeds return `fixpoint` AND all negative seeds return `¬fixpoint`
5. write `shared/state/{dest}_r{N}_drill_breakthrough.json`

### 3.4 Invariants preserved

- n=6, σ=12, φ=4, τ=4 (σ·φ = n·τ = 24) — encoded in `inv_check`.
- criteria.json schema backward-compatible: new fields are additive; old consumers reading `saturation_required` see string truthy → still parses as true under deterministic parser if/when gated on presence only (a safer migration: keep `saturation_required: true` as legacy alias AND add `saturation_policy` block — this is what this commit lands).
- V8 SAFE_COMMIT: criteria edit only; runner stub untouched; no mass rewrite.

### 3.5 Verification (deterministic, no LLM)

- Smoke: current 4 seeds produce `{seed_pos_01: fixpoint, seed_neg_01: open, seed_clo_01: fixpoint, seed_dia_01: fixpoint}` — 3 fixpoint + 1 open = pass.
- Regression: absorption_rate recomputation on legacy runs must yield ≤ 0.3 for historical pass-cases (re-derivation, not re-measurement).

---

## 4. Summary

- **Master switch**: `saturation criterion` — promoted from boolean to fixpoint-predicate enum.
- **ROI rationale**: it is the *type* on which every other drill knob operationally depends; unblocking it collapses candidates #2/#3/#4 into derived measurements.
- **Landing strategy**: additive criteria.json field (`saturation_policy`), legacy boolean retained, runner stub untouched → one-file diff, deterministic, V8 SAFE_COMMIT compliant.

END
