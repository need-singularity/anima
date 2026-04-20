# edu/cell/causal — 인과축 (causal) MVP

Seventh axis of edu/cell: causal emergence.
Pre-registered before measurement — drill outcome frozen.

## Design (drill 결과, 2026-04-21)

Main metric: **Causal Emergence Index** CEI = Φ_macro / Φ_micro (Hoel 2013).

| axis | name | definition | threshold |
|---|---|---|---|
| **O1** | IR (Intervention Robustness)  | E[ \|ΔBehavior\| / ΔIntervention ] | ≥ 0.70 |
| **O2** | CD (Causal Density)           | non-spurious edges / all possible (Granger lagged correlation) | ≥ 0.40 |
| **O3** | MB (Markov Blanket Score)     | Jaccard(discovered_MB, true_MB) | ≥ 0.75 |

Verdict: **CAUSAL_EMERGED** iff IR ≥ 0.70 **and** CD ≥ 0.40 **and** MB ≥ 0.75.
Anything less = **CAUSAL_PARTIAL** (single-axis fail) or **CAUSAL_FAILED** (≥2 axes fail).

## Files

| file | role | lines |
|---|---|---|
| `causal_core.hexa` | CausalGraph + intervention + MB discovery | ~280 |
| `emergence_metric.hexa` | CEI + CD (Granger lagged correlation) | ~200 |
| `mvp_demo.hexa` | 20-var toy network × 50 interventions, jsonl stdout | ~180 |

## MVP harness

- **20 binary variables**, deterministic seed = 42
- **50 interventions**: knock-out (hold to 0), pulse (one-tick spike), sustained (hold to 1)
- **coarse-grain** 20 micro vars → 4 macro blocks (5 vars/block, majority vote) for Φ_macro
- **Φ_micro** reduced TPM on 4-block projection (full 2^20 TPM infeasible; Φ_macro uses 4-node TPM, Φ_micro uses *per-block* 5-node TPM averaged — Hoel-style macro-upward comparison)
- jsonl stdout: `{evt:"perturb", step, var, kind, CEI, IR, CD, MB}` + final verdict record
- re-run byte-identical

## CLI

```
cd ~/core/anima
hexa run edu/cell/causal/mvp_demo.hexa > shared/state/edu_causal_mvp.jsonl
```

## Dependency

`/Users/ghost/core/hexa-lang/self/ml/phi_metric.hexa` — stage0 module loader is fragile,
so we **INLINE** a minimal EI() compatible with phi_metric.effective_information()
(byte-equivalent algorithm, not a source import).

## Measured values (seed=42, N=20, STEPS=20, NI=50, 2026-04-21)

| metric | value | threshold | axis verdict |
|---|---|---|---|
| **CEI** (baseline) | **0.896** | (positive ⇒ macro is more informative than mean micro) | — |
| **IR_mean**        | **0.698** | ≥ 0.70 | FAIL (0.002 short) |
| **CD_mean**        | **0.408** | ≥ 0.40 | **PASS** |
| **MB_mean**        | **0.363** | ≥ 0.75 | FAIL |

**Verdict**: `CAUSAL_FAILED` (2 axes fail).

Interpretation: CEI > 0.89 indicates *macro-level* informational structure
(4-way majority-vote coarse-graining retains ~90% of the micro EI, Hoel-positive
regime).  CD narrowly passes (~41% of ordered pairs show above-threshold lag-1
Pearson).  IR comes within 0.002 of its threshold; the 20-node threshold net
with 7 outbound edges per node is near, but not at, full-Hamming butterfly
sensitivity.  MB jaccard 0.36 reflects the dense-MB problem: true_MB(v) for
this topology averages 15/20 nodes (parents ∪ children ∪ parents-of-children
saturates), and the lag-1 co-activation discovery threshold (40% of max) is
tight.

MVP certifies the 7th axis is **implemented + measurable**; full
`CAUSAL_EMERGED` would require either (a) sparser topology with larger N, or
(b) stochastic dynamics to break the fixed-point attractor, or (c) lowering
the pre-registered thresholds.  The result is filed as-measured; the goal was
MVP completeness, not cherry-picked pass.

## Artifact SHA-256

```
jsonl (50 perturb + config + baseline + summary, 53 lines) = byte-identical on re-run
output sha256 = 2556f7f34f565f1f9d68dee5a6186674d50b0a65e778f6d5cc7543ca03cd0787
```

Re-run:
```
HEXA_MAC_BUILD_OK=1 hexa-build edu/cell/causal/mvp_demo.hexa \
  -o build/edu_causal_mvp
build/edu_causal_mvp > shared/state/edu_causal_mvp.jsonl
```

## RAW contract

raw#9 · hexa-only · deterministic · LLM=none · V8 SAFE_COMMIT (additive).
