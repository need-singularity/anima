# Quadruple Cross — λ Weight Sweep (2026-04-19)

> Engine: anima Mk.V.1 (v4-hexa, tier 5 + 6~9 bridge)
> Harness: `training/quadruple_cross_sweep.hexa`
> Underlying loss: `training/quadruple_cross_loss.hexa` (8/8 PASS, untouched)
> Trace: `training/corpus_universe_tier_labels.jsonl` (170 stim)

## 1. Setup

- Grid: α,β,γ,δ ∈ {0.1, 0.3, 0.5, 0.7, 1.0} — **5^4 = 625 combos**
- Ψ-trace samples loaded: **170** (expect 170)
- Per-combo metrics: L̄, Var, CV%, closure_gate, CV<3%
- Filter: closure_gate ∧ cv_ok → valid
- Rank: ascending L̄ among valid combos

### Ψ-trace derivation (surrogate)

```
psi_res  = clamp01(0.5 + (top_score - 2.0) * 0.25)
psi_gate = clamp01(0.5 + (top_score - 2.0) * 0.40)
route    = clamp01(0.5 + (tier_k - 75)   * 0.010)
n_eff    = clamp(6 - |top_score - 2.0| * 2, 0, 6)
```

σ·φ = n·τ = 24 closure (`check_sigma_phi_closure`) holds for every grid point
(all weights ≥ 0.1, sum > 0, n=6, τ=4). The tighter filter is CV<3%.

## 2. Summary

| metric | value |
|--------|-------|
| combos evaluated | 625 |
| closure_gate pass | 625 |
| CV<3% pass (valid) | 0 |

## 3. Top 10 (lowest L̄ among valid)

| rank | α    | β    | γ    | δ    | L̄      | CV%   | closure | cv_ok |
|------|------|------|------|------|---------|-------|---------|-------|

## 4. Worst 10 (highest L̄, any gate status)

| rank | α    | β    | γ    | δ    | L̄      | CV%   | closure | cv_ok |
|------|------|------|------|------|---------|-------|---------|-------|
| 1    | 1.00 | 1.00 | 1.00 | 1.00 | 0.0187 | 237.61 | yes     | no    |
| 2    | 0.70 | 1.00 | 1.00 | 1.00 | 0.0179 | 237.62 | yes     | no    |
| 3    | 1.00 | 1.00 | 0.70 | 1.00 | 0.0176 | 237.60 | yes     | no    |
| 4    | 0.50 | 1.00 | 1.00 | 1.00 | 0.0174 | 237.62 | yes     | no    |
| 5    | 1.00 | 1.00 | 1.00 | 0.70 | 0.0173 | 237.62 | yes     | no    |
| 6    | 1.00 | 1.00 | 0.50 | 1.00 | 0.0168 | 237.58 | yes     | no    |
| 7    | 0.30 | 1.00 | 1.00 | 1.00 | 0.0168 | 237.62 | yes     | no    |
| 8    | 0.70 | 1.00 | 0.70 | 1.00 | 0.0167 | 237.60 | yes     | no    |
| 9    | 1.00 | 0.70 | 1.00 | 1.00 | 0.0166 | 237.62 | yes     | no    |
| 10   | 0.70 | 1.00 | 1.00 | 0.70 | 0.0164 | 237.62 | yes     | no    |

## 5. Recommendation

**No valid combo found** — every combo failed closure ∧ CV<3% filter.
Revisit grid bounds or CV ceiling.

## 6. AN11 boundary

This sweep ranks a **substrate** loss (AN11-a). The best combo
does not promote any tier. AN11-b (emergence) and AN11-c (real
reproduction) are independent gates — no shortcut is claimed here.

## 7. Reproduce

```
HEXA_LOCAL=1 HEXA_NO_LAUNCHD=1 HEXA_STAGE0_LOCK_WAIT=2400 \
  /Users/ghost/Dev/nexus/shared/bin/hexa run \
  /Users/ghost/Dev/anima/training/quadruple_cross_sweep.hexa
```
