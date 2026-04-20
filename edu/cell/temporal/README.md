# edu/cell/temporal — 시간축 (temporal) MVP

Eighth axis of edu/cell: **temporal emergence**.
Pre-registered before measurement — drill outcome frozen 2026-04-21.

## Design (drill 결과, 2026-04-21)

Main claim: a Φ(t) trajectory exhibits **emergent temporal structure** iff it
simultaneously carries memory, a causality arrow, and 1/f pink-noise long-range
correlation. All three observables must PASS together.

| axis | name | definition | threshold |
|---|---|---|---|
| **O1** | τ_mem(Δ)   | normalized autocorrelation at lag Δ=4 (Pearson, sliding window) | > 0.65 |
| **O2** | I_irr       | forward irreversibility = max(0, E[ΔΦ]) / E\[\|ΔΦ\|] | forward > 0.35 AND reverse < 0.15 |
| **O3** | H (Hurst)   | exponent from R/S analysis on first-difference series | 0.5 < H < 0.75 (pink noise) |

**Verdict**: ALL 3 PASS → `TEMPORAL_EMERGED` / 2 PASS → `TEMPORAL_PARTIAL` / ≤1 PASS → `TEMPORAL_FAILED`.

## Files

| file | role | lines |
|---|---|---|
| `temporal_emergence.hexa` | MVP — Φ(t) trajectory + 3 observables + verdict cert | ~340 |
| `fixtures/gen4_trajectory.json` | manifest for Φ(t) anchors (seed, anchors, length) | ~15 |
| `verifier/temporal_falsification.hexa` | adversarial (identity / reverse / shuffle) with pass/fail assertions | ~320 |

## Trajectory

Length **64**, seed **20260421**. Anchors come from the 4-gen crystallize ladder
(`anima/shared/state/edu_cell_4gen_crystallize.json`, commit `58aa75eb` lineage):

| tick | anchor Φ | source |
|---|---|---|
| 0   | 0.040 | gen 1 score_per_mille/1000 (tl=0‰) |
| 16  | 0.125 | gen 2 (tl=300‰) |
| 32  | 0.687 | gen 3 (tl=550‰) |
| 48  | 1.000 | gen 4 (tl=800‰) |

Between anchors: AR(1) noise process (φ=0.75, innovation amplitude 0.04 via
two avalanche-hashed uniforms). Noise is pinned to 0 at anchor ticks so the
trajectory threads exactly through the crystallize data. After tick 48 the
series saturates at Φ=1.0 with the same AR(1) jitter.

## CLI

```
cd ~/core/anima
hexa edu/cell/temporal/temporal_emergence.hexa
hexa edu/cell/temporal/verifier/temporal_falsification.hexa
```

Both re-run byte-identical. Cert written to `shared/state/edu_cell_temporal_O123.json`.

## Measurement (2026-04-21)

| observable | value | threshold | pass |
|---|---|---|---|
| O1  τ_mem(Δ=4)       | **0.935213** | > 0.65 | ✅ |
| O2  I_irr (forward)  | **0.594175** | > 0.35 | ✅ |
| O2  I_irr (reverse)  | **0.000000** | < 0.15 | ✅ |
| O3  Hurst            | **0.731220** | 0.5 < H < 0.75 | ✅ |

**Verdict**: `TEMPORAL_EMERGED` (3/3 PASS).

### Adversarial

| case | corruption | expected | observed |
|---|---|---|---|
| T1 identity       | — | O1+O2+O3 PASS, verdict EMERGED | all 3 PASS, EMERGED ✅ |
| T2 time-reverse   | φ reversed | O2 must FAIL (arrow flips) | I_irr_fwd = 0.000, O2 FAIL ✅ |
| T3 shuffle        | deterministic Fisher-Yates | O1 must FAIL (memory erased) | τ_mem = −0.062, O1 FAIL ✅ |

All 3 adversarial assertions pass.

## RAW contract

raw#9 · hexa-only · snake_case (raw#11) · deterministic · LLM=none · V8 SAFE_COMMIT (additive).
Fixture seed **20260421**. Runtime ≤ 2 min CPU (mac arm64, stage0.real).
