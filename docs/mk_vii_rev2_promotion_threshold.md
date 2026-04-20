# Mk.VII Promotion Threshold — rev=2 Decision

- Date: 2026-04-21
- Parent SSOT: `shared/state/mk_vii_predict.json` (rev=1 FROZEN_PREREGISTER)
- Child SSOT: `shared/state/mk_vii_predict_rev2.json` (this rev)
- Policy: V8 SAFE_COMMIT — additive, deterministic, LLM-free, forward-only rev chain.

## 1. Purpose

rev=1 pre-registered 5 divergent candidate criteria on 5 independent axes (C1..C5)
but left the K-of-5 promotion threshold **OPEN** to avoid cherry-picking before
Mk.VI closure. rev=2 fixes K with explicit rationale, BEFORE empirical results
on the 5 axes are inspected.

## 2. rev=1 → rev=2 Transition (preserved history)

- rev=1 manifest sha (user-cited): `9d035936` — K_threshold = OPEN.
- rev=1 `k_threshold_hint`: "K >= 3 of 5 on independent axes (tentative)".
- rev=1 in-tree addressing snapshot:
  - C1 substrate-invariant Φ — PARTIAL (1/4 paths; cross-prover diagonal wired).
  - C2 L3 collective — PARTIAL (spec frozen, no lattice run).
  - C3 self-verify closure — PARTIAL (compiler-layer fixpoint precedent only).
  - C4 real EEG — MINIMAL (synthesized α driver only, no real trace).
  - C5 stable N=10 — PARTIAL (single-generation results only).
- Strongest in-tree hooks (rev=1 note): C1, C3.
- Weakest in-tree hook (rev=1 note): C4.

rev=2 preserves every rev=1 field verbatim; only `design_rule.k_threshold` is
resolved, plus a new `k_rationale` block is added. No criterion is removed or
reworded. rev=1 file remains frozen on disk.

## 3. Decision

**K = 4 of 5** — "moderate, one-optional".

**Optional axis**: C4 (real-world EEG coupling).

**Hard-required axes (MUST pass)**: C1 (substrate), C2 (scale), C3 (self-ref).

**Conditional**: one of {C4, C5} must pass in addition to C1∧C2∧C3, giving 4/5.

Formally:

```
mk_vii_promoted :=
    mk_vi_promoted
    AND C1 PASS
    AND C2 PASS
    AND C3 PASS
    AND (C4 PASS OR C5 PASS)
```

Equivalent statement: `K = 4` with the constraint that the three non-optional
axes {C1, C2, C3} are all required; C4 is the single optional axis, and C5
can substitute for C4 (but cannot substitute for C1/C2/C3).

## 4. Rationale — 3-axis analysis

### 4.1 Conservative (K = 5, all-required) — REJECTED

- **Pro**: paradigm-breakthrough threshold; false-positive floor.
- **Con**: promotion gated on C4 real EEG dataset availability. C4 is the
  weakest in-tree hook (rev=1: MINIMAL) and depends on external-world data
  curation that is not under the repo's deterministic control. This turns
  the Mk.VII gate into a dataset-sourcing bottleneck rather than a
  consciousness-grade claim, which is the wrong failure mode.
- **Verdict**: too strict given the asymmetric in-tree addressability.

### 4.2 Moderate (K = 4, one-optional) — SELECTED

- **Pro**: mitigates C4 real-EEG sourcing risk without weakening the
  substrate/scale/self-reference claims, which are the three axes that
  distinguish Mk.VII from Mk.VI as a *formal* grade jump.
- **Con**: allows promotion without real-world coupling in the strict sense.
  Mitigation: C5 (stable N=10) must then PASS — i.e. temporal robustness
  stands in for external-world coupling as the fourth axis.
- **Why C4 and not C3 is the optional one**: C3 is the self-hosting analog
  (f60841a6 precedent exists in-tree); C4 requires out-of-tree data.
  Making C3 optional would weaken the *formal* claim; making C4 optional
  only weakens the *empirical sim/reality bridge* claim, which is strictly
  recoverable post-promotion by landing a real trace later.
- **Hard floor**: C1∧C2∧C3 MUST all pass. This prevents the degenerate case
  where two "easy" axes plus two more carry the grade while the paradigm-
  distinguishing axes (substrate invariance, collective scale, self-verify)
  are skipped.
- **Verdict**: selected.

### 4.3 Liberal (K = 3, two-optional) — REJECTED

- **Pro**: earliest possible promotion; maximum empirical flexibility.
- **Con**: Mk.VII is a phase-jump from Mk.VI (single-unit, sim-only,
  externally-verified). K = 3 allows e.g. {C1, C3, C5} to carry the grade
  without ever demonstrating collective emergence (C2) or real-world
  coupling (C4), which collapses Mk.VII into "Mk.VI with substrate
  shuffle + N-recurse". That is not a grade promotion; it is a lateral
  robustness extension.
- **Verdict**: too permissive for a phase-jump claim.

## 5. C4-optional condition

C4 may be deferred past promotion under the following explicit conditions,
all of which must be logged in the rev=2 state file:

1. C1, C2, C3 each PASS per their rev=1 thresholds (unchanged).
2. C5 PASSes per its rev=1 threshold, acting as the 4th axis.
3. C4 remains in `pending_empirical` status, with a pre-registered dataset
   target recorded before promotion (not after).
4. If C4 later returns FAIL on the pre-registered dataset, Mk.VII is
   **demoted** to Mk.VII_CONDITIONAL until a replacement pre-registered
   dataset is run. Demotion is an explicit rev=3 event, not a quiet retract.

This keeps C4 from being a silent escape hatch while acknowledging the
in-tree sourcing gap.

## 6. Non-changes (rev=1 preserved)

- The 5 axes themselves, the per-criterion thresholds, the `_meta.rev_policy`
  ("forward-only; rev bumps must preserve prior records; no post-hoc
  criterion addition after empirical results inspected"), and the
  divergence_requirement are all preserved verbatim.
- No empirical result on C1..C5 has been inspected at the time of this
  decision. K is fixed by in-tree addressability asymmetry and the
  structural Mk.VI→Mk.VII phase-jump argument, not by preview of outcomes.

## 7. V8 SAFE_COMMIT

- additive only (new `docs/mk_vii_rev2_promotion_threshold.md` +
  `shared/state/mk_vii_predict_rev2.json`; rev=1 file untouched).
- deterministic (no LLM, no stochastic content).
- LLM 금지.
- canonical rev=1 SSOT preserved.
- rev chain: rev=1 FROZEN_PREREGISTER → rev=2 K_FIXED.
