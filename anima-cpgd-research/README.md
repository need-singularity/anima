# anima-cpgd-research — Path C (Q4 generalization)

**Created**: 2026-04-26
**Path**: C (Q4 — CPGD generalization beyond AN11(b))
**Mode**: mac local · CPU only · raw#9 hexa-only strict · $0
**Status**: ω-cycle frozen criteria registered

## Background

CPGD = **Constraint-Projected Gradient Descent**
- Closed-form orthonormal init: `W_0 = P_S · W_random`
- Projector `P_S = V^T · V` (orthonormal-row eigenvec matrix V)
- Step: `W_{k+1} = W_k − lr · (grad · P_S)`
- Invariant: `cos(W_k[i,:], v_i) ≥ COS_FLOOR` for all k, i

**ω-cycle TRAINING-axis paradigm 3** — single highest-confidence paradigm (0.95).
At AN11(b) toy regime: weight update 0, AN11(b) 100% math guarantee.
Existing evidence:
- `edu/lora/cpgd_wrapper.hexa` (1600/1600 cos floor PASS, 100-step)
- `edu/lora/cpgd_minimal_proof.hexa` (10-step demonstrative companion)
- `edu/lora/cpgd_wrapper_selftest.hexa`
- `edu/lora/lora_cpgd_init.hexa`

## Q4 Open Question

> **Does the AN11(b) 100% math guarantee hold for non-AN11(b) downstream targets?**

The current 100% verdict is conditional on the AN11(b) eigenvec subspace
(K=16 orthonormal templates, dim=16). It is unknown whether the closed-form
init + projected-gradient invariant generalizes to:

1. **AN9** axis — simpler causal probing, K=4 dim=4 toy
2. **AN-arbitrary** — non-orthonormal, condition-number > 10, dim=8 synthetic

## Falsifier Criteria (FROZEN — ω-cycle pre-registration)

The following gates are pre-registered before implementation. They cannot
be relaxed post-hoc; failure of any one gate yields a NEGATIVE generalization
verdict for that target class.

### G1 — closed-form init residual
After `W_0 = P_S · W_random`, the projected weight matrix must lie in S
within numerical floor:
```
max_i ‖(I - P_S) · W_0[i,:]‖ ≤ EPS_PROJ   (= 1e-5)
```
Equivalently for orthonormal targets, `cos(W_0[i,:], v_i) ≥ COS_FLOOR`
(= 0.5) at step 0.

### G2 — 100-step monotone descent (no oscillation)
Across all 100 steps, the **per-template max drift from cos=1** must
not increase past a single peak:
```
∀i, drift_i(k) := |1 − cos(W_k[i,:], v_i)| has at most ⌈log₂(STEP_COUNT)⌉
                                                       monotone-violating turns
```
Equivalently: `total_violations` (cos < COS_FLOOR) over 100 × K = 0.

### G3 — byte-identical re-run (deterministic)
Two consecutive `run_once()` invocations with the same seed must produce
identical sha256 of the canonical payload:
```
sha256(payload_run1) == sha256(payload_run2)
```

### G4 — condition-number-conditioned monotone (AN-arbitrary only)
For non-orthonormal target with `cond(V) ∈ [1, 100]`:
```
G2 must hold AND
post-init residual scales as O(cond(V) · EPS_PROJ)
```

## Composite Verdict

```
CPGD_GENERALIZED  := G1 ∧ G2 ∧ G3 (∧ G4 for AN-arbitrary)
                       across {AN11(b), AN9, AN-arbitrary}
```

Single-target failure → **PARTIAL_GENERALIZATION** with target-class boundary
documented in `docs/q4_generalization_verdict.md`.

## Deliverables

| # | File | Target | Output |
|---|------|--------|--------|
| 1 | this README.md | theorem statement | — |
| 2 | `tool/cpgd_an9_falsifier.hexa` | AN9 4-d synthetic | `state/cpgd_an9_falsifier_v1.json` |
| 3 | `tool/cpgd_anarbitrary_falsifier.hexa` | AN-arbitrary 8-d FNV-hashed non-orthonormal | `state/cpgd_anarbitrary_falsifier_v1.json` |
| 4 | `tool/cpgd_generalization_smoke.hexa` | composite chain | `state/cpgd_generalization_smoke.json` |

## Constraints

- **read-only**: `edu/lora/*` is canonical CPGD reference; not modified.
- **raw#9**: pure hexa, modular arithmetic, integer fixed-point ×1000 where
  determinism over float matters; no Python emit; no GPU; no LLM.
- **deterministic**: every artifact must be byte-identical across runs.
- **mac local** · CPU only · $0.

## ω-cycle pattern (per deliverable)

1. design — frozen G1/G2/G3 (+G4) pre-registered above
2. implement — raw#9 hexa-only
3. positive selftest — orthonormal target sanity baseline
4. scope target test — AN9 / AN-arbitrary verdict
5. negative falsify — pathological condition (zero singular value)
6. byte-identical — sha256 stable
7. iterate — any FAIL → re-design

## Dependencies

- `edu/lora/cpgd_wrapper.hexa` (CPGD core algorithm reference)
- `edu/lora/cpgd_minimal_proof.hexa` (10-step minimal pattern)
- hexa-lang 0.2.0+ runtime (`/Users/ghost/core/hexa-lang/hexa run`)
