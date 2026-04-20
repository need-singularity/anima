# Cross-Verifier Agreement Matrix — 20260421

## Purpose

Cross-agreement matrix of the 7 verifiers landed in the recent trio +
drill + btr-evo set. Hypothesis: these verifiers can produce divergent
verdicts on the same input; the matrix quantifies that divergence.

## Inputs

| idx | sample         | source                                                                      |
| --- | -------------- | --------------------------------------------------------------------------- |
| s0  | btr_trajectory | experiments/holo_post/results/eeg_closed_loop_20260421_trajectory.jsonl     |
| s1  | an11_usable    | synthetic (delta=0.04, rank=8, max_cos=0.68, top3=1.55, JSD=0.42)           |
| s2  | an11_marginal  | synthetic (delta=0.0008, rank=4, max_cos=0.48, top3=1.15, JSD=0.16)         |
| s3  | an11_unusable  | synthetic (delta=0.0, rank=0, max_cos=0.2, top3=0.4, JSD=0.05, unhealthy)   |
| s4  | hexad_target   | anima-hexad/ (CDESM, 6/6 closed)                                            |

## Verifiers

| idx | tag    | AL | commit    | applicability                             |
| --- | ------ | -- | --------- | ----------------------------------------- |
| v0  | AN11a  | ν  | 8cf014ff  | AN11 ckpts only                           |
| v1  | AN11b  | ξ  | b1f487e7  | AN11 ckpts only                           |
| v2  | AN11c  | ο  | 15c0596e  | AN11 ckpts only (needs serve endpoint)    |
| v3  | Hexad  | σ  | 7680cd74  | anima-hexad/ target only                  |
| v4  | cargo7 | —  | 2b8d5948  | trajectory samples (has_trajectory \|\| has_hexad_tree) |
| v5  | η      | —  | ec8c92ea  | drill absorption (same applicability as v4) |
| v6  | θ      | —  | 1da65258  | cross-prover NDJSON (none present in matrix mode) |

## Matrix

```
sample           | AN11a  AN11b  AN11c  Hexad  cargo7  eta    theta
------------------------------------------------------------------------
btr_trajectory   | NA     NA     NA     NA     PASS    PASS   NA
an11_usable      | PASS   PASS   PASS   NA     NA      NA     NA
an11_marginal    | FAIL   FAIL   PASS   NA     NA      NA     NA   ← divergence
an11_unusable    | FAIL   FAIL   FAIL   NA     NA      NA     NA
hexad_target     | NA     NA     NA     PASS   PASS    PASS   NA
```

## Metrics

- **Fleiss' kappa (3-category, PASS/FAIL/NA) = −0.0324**
  - Schema artefact: 21/35 cells are NA (by design — verifiers are
    input-type specific), which dominates `P_e` and pushes kappa below
    chance. Not a real disagreement signal.
- **Pairwise agreement % (excluding NA pairs)**:
  - AN11a↔AN11b : 100.0% (3/3 overlap)
  - AN11a↔AN11c :  66.67% (2/3 overlap) ← divergence
  - AN11b↔AN11c :  66.67% (2/3 overlap) ← divergence
  - Hexad↔cargo7: 100.0% (1/1)
  - Hexad↔η     : 100.0% (1/1)
  - cargo7↔η    : 100.0% (2/2)
  - all others  : NA (no overlap)

## Largest divergence — s2 an11_marginal

| verifier | verdict | reason                                      |
| -------- | ------- | ------------------------------------------- |
| AN11a    | FAIL    | delta=0.0008 ≤ threshold 0.001              |
| AN11b    | FAIL    | max_cos=0.48 ≤ 0.5                          |
| AN11c    | PASS    | jsd=0.16 > 0.15 (barely)                    |

**Interpretation**: a "cognitively dead but behaviourally diverse"
trap. A ckpt with no measurable weight delta and no eigenvector
alignment to consciousness templates can still cross the JSD gate by
sampling noise alone.

**Mitigation options** (non-exclusive):
1. Raise AN11c JSD floor from 0.15 → ≥ 0.20 (shrinks marginal band).
2. Enforce AN11(a ∧ b) short-circuit before AN11c — which is what
   `rules/anima.json#AN11` AND-gate already does.

The matrix thus **confirms the AN11 AND-gate is load-bearing**, not
redundant: any single condition alone would mis-admit s2.

## Artefacts

- `tool/verifier_cross_matrix.hexa`            (anima — parses clean, sha256-stable)
- `shared/state/verifier_cross_matrix_20260421.json` (nexus SSOT — 35 cells + kappa + pairwise + largest_divergence)

## Landing

- anima tool landed under commit `7baf1869` (attribution swept by a
  parallel C3 meta-cert commit — tool content intact, message
  misattributed).
- nexus SSOT JSON landed under commit `9446a81b` (attribution swept by
  a parallel LSH probe commit — content intact, message misattributed).
- This manifest provides canonical attribution (feat(verifier): cross-
  agreement matrix — 7-verifier × sample input) for both artefacts.

V8 SAFE_COMMIT · additive · deterministic · LLM=none.
