# Q4 Generalization Verdict — CPGD beyond AN11(b)

**Created**: 2026-04-26
**Path**: C (Q4)
**Author tool**: `anima-cpgd-research/tool/cpgd_generalization_smoke.hexa`
**Status**: ω-cycle complete, frozen-criteria pre-registered, single-pass

## Composite Verdict

```
CPGD_GENERALIZED
```

| Target | K | dim | Basis | G1 | G2 | G3 | G4 | Verdict |
|--------|---|-----|-------|----|----|----|----|---------|
| AN11(b) | 16 | 16 | orthonormal eigenvec | PASS | PASS (0/1600) | PASS | n/a | `VERIFIED` |
| AN9 | 4 | 4 | canonical basis e_1..e_4 | PASS (residual=0) | PASS (0/400) | PASS | n/a | `AN9_GENERALIZED` |
| AN-arbitrary | 4 | 8 | FNV-hashed pseudo-random + Gram-Schmidt | PASS (9.09e-13) | PASS (0/400) | PASS | PASS (cond=3.25) | `ANARB_GENERALIZED` |

All three targets satisfy G1 ∧ G2 ∧ G3 (∧ G4 for AN-arbitrary). The
deterministic 2-run sha256 over canonical payloads is byte-identical for
each target individually and at the composite chain level
(`1cb7339d14f4353eda1194f8ca9d72573516fb6a4cc81f674a144e945e880402`).

## Key Findings

### 1. Generalizability of the closed-form CPGD invariant

The AN11(b) 100% math guarantee — `∀k ≤ 100, ∀i: cos(W_k[i,:], v_i) ≥ COS_FLOOR` —
is **not specific to the AN11(b) eigenvec subspace**. It holds whenever:

- the target subspace S admits an orthonormal basis V (rows of V),
- `P_S = V^T · V` is constructed and verified idempotent,
- `W_0` is initialized as `P_S · W_random` (or equivalently `W_0 = V` for the
  template-aligned init), and
- gradient steps use `W_{k+1} = W_k − lr · (grad · P_S)` with lr in the
  small-step regime (≤ 0.001 here).

This is **linear-algebra-correct**: any subspace endowed with an orthonormal
basis admits the same projector + projected-gradient invariant. AN11(b)
was a **specific instantiation**, not the generality.

### 2. Non-orthonormal extension (AN-arbitrary) requires Gram-Schmidt

When V_raw is non-orthonormal (FNV-hashed pseudo-random in our case,
`cond_proxy(V_raw) = 3.247`), CPGD does **not** apply directly because
`V_raw^T · V_raw ≠ orthogonal projector`. The generalization step is to
**Gram-Schmidt orthonormalize V_raw → V_orth**, then run CPGD with V_orth
as the canonical eigenvec set. Under this extension:

- post-init residual: **9.09e-13** (well below `EPS_PROJ = 1e-4`)
- 100-step monotone descent: 0/400 violations
- byte-identical re-run: yes
- condition-number-conditioned (G4): cond_proxy = 3.247 < 100 ⇒ pass

### 3. Boundary conditions (where CPGD breaks)

**Negative falsify caught by both AN9 and AN-arbitrary tools:**

- **AN9 pathological** (`v_3 = zero-vector`): rank-deficient projector,
  `init_unit_cosine_ok = false` ⇒ verdict FAIL detected.
- **AN-arbitrary pathological** (`v_1 = v_0` collinear duplicate):
  Gram-Schmidt collapses (`‖u‖ < EPS_GS`), `rank_deficient = true` ⇒ verdict
  FAIL detected.

**Where the math floor breaks** (deductive, not measured):

- `cond(V_raw) → ∞`: numerical instability in P_S idempotence verification.
  Boundary measured: `cond_proxy = 3.247` is comfortably tractable; G4
  conservative cap is `cond_proxy < 100`.
- `nrank(V_raw) < TPL_COUNT`: rank-deficient projector, cos undefined for
  collapsed rows. Deterministically detected by Gram-Schmidt zero-norm
  catch.
- `lr · ‖grad‖ ≫ 1`: small-step regime broken. Not tested here (out of
  scope of frozen criteria); empirically max_drift ∝ lr·k confirms the
  Lagrangian bound from `docs/proof_cpgd.md` (canonical AN11(b) proof).

## Generalization Boundary Statement

CPGD generalizes **deterministically** to any AN-class downstream task that
satisfies:

1. **target rank ≥ K** — full-rank K-dimensional subspace exists in R^DIM
2. **lr in small-step regime** — `lr · max_norm(grad) < (1 − COS_FLOOR)`
3. **deterministic gradient seed** — RNG state shared between runs

Within this regime, the AN11(b) 100% math guarantee transfers exactly.

## Limits and Honest Caveats (raw#9 honest)

### What this experiment does NOT prove

- **Real-LM downstream task**: this is `lr=0.001, GRAD_SEED=20260426`,
  pseudo-random Gaussian gradient. No actual loss landscape, no actual LM.
  The **invariant** holds; whether the resulting `W_k` is **useful** for a
  real task is orthogonal.
- **Above the small-step regime**: `lr ≥ 0.01` was not measured. The
  Lagrangian bound from `docs/proof_cpgd.md` predicts breakdown at
  `lr · ‖grad‖ ≈ 1`; here `lr · ‖grad‖ ≈ 0.001` so we are 3 orders
  below the predicted boundary.
- **High condition number**: only `cond_proxy ≈ 3` tested; G4 cap `<100`
  is unverified above `~3.25`. A natural next step is a sweep
  `cond ∈ {1, 10, 100, 1000}` with FNV-mixing weights.

### What we DID prove

- ω-cycle 7-step pattern (design → implement → positive selftest → scope
  target → negative falsify → byte-identical → iterate) completed in single
  pass (0 iterations needed) for all 3 deliverables.
- 3 distinct target classes — orthonormal canonical basis (AN9), pre-existing
  AN11(b) eigenvecs, and FNV-hashed non-orthonormal (AN-arbitrary) — share
  the same deterministic CPGD invariant.
- Negative-falsify caught both pathological inputs, confirming the gates
  are not vacuous.
- All 3 selftest modes exit 0; composite chain verdict
  `CPGD_GENERALIZED` byte-identical across runs.

## Next Steps (recommended, not in scope)

1. **Real-LM prerequisite path**: integrate AN-arbitrary CPGD with one of
   `edu/lora/lora_cpgd_init.hexa` outputs to a small (Phi-3-mini) backbone
   forward pass; measure cosine alignment of trained LoRA weights with
   Gram-Schmidt'd eigenvecs after a real training step.
2. **Condition-number sweep**: parametrize `fnv_basis_raw()` to admit a
   condition-number target by scaling the smallest singular direction;
   measure G2 violation count vs cond.
3. **Larger LR regime**: vary `DEFAULT_LR ∈ {0.001, 0.01, 0.1}`; locate
   breakdown frontier predicted by Lagrangian bound.
4. **Multi-target chain**: extend the smoke chain to AN12 (gradient + value
   alignment), AN-large (K=64 dim=128), exploring whether template_count
   scaling preserves the invariant.
