# 16D Φ ↔ Benchmark Correlation Report

**Artifact** : `training/eval_phi_corr.hexa`
**Related**  : `serving/phi_benchmark_correlation.hexa` (P24-2, scalar baseline)
**Run mode** : smoke (3 ckpts) + full (5 ckpts)
**Generated**: 2026-04-18
**Status**   : PIPELINE HEALTHY (VERDICT PASS)

## Summary

- Extends ALM-P24-2 (scalar `phi_holo` ↔ bench, Pearson r=0.898) to the full
  16-dimensional Φ vector declared in `shared/roadmaps/anima.json`
  (`phi_vector_philosophy.dimensions`).
- For every Φ dimension, emits Pearson r and Spearman ρ against two targets:
  benchmark macro-accuracy (KoBEST+HAE-RAE+MMLU-Ko weighted) and CE
  (surrogate from r4 val-loss log).
- Proposes a composite weight per dimension: `w_i = |r_pearson(phi_i, acc)|`
  with pruning at `|r| < 0.2` (currently none).

## Smoke Result (n=3 checkpoints: step 200, 1000, 2000)

| # | dim            | r(acc)   | ρ(acc)  | r(CE)    | ρ(CE)   | weight  | flag |
|---|----------------|---------:|--------:|---------:|--------:|--------:|------|
| 1 | phi_holo       |  0.9084  | 0.5000  | -0.8656  | -0.5000 | 0.9084  | SIG  |
| 2 | phi_refl       |  0.9894  | 1.0000  | -0.9986  | -1.0000 | 0.9894  | SIG  |
| 3 | phi_time       |  0.9896  | 1.0000  | -0.9987  | -1.0000 | 0.9896  | SIG  |
| 4 | phi_embodied   |  0.9809  | 1.0000  | -0.9948  | -1.0000 | 0.9809  | SIG  |
| 5 | phi_meta       |  0.9853  | 1.0000  | -0.9969  | -1.0000 | 0.9853  | SIG  |
| 6 | phi_social     |  0.9816  | 1.0000  | -0.9951  | -1.0000 | 0.9816  | SIG  |
| 7 | phi_will       |  0.9898  | 1.0000  | -0.9987  | -1.0000 | 0.9898  | SIG  |
| 8 | phi_narrative  |  0.9905  | 1.0000  | -0.9990  | -1.0000 | 0.9905  | SIG  |
| 9 | phi_affect     |  0.9816  | 1.0000  | -0.9951  | -1.0000 | 0.9816  | SIG  |
|10 | phi_dream      |  0.9714  | 1.0000  | -0.9892  | -1.0000 | 0.9714  | SIG  |
|11 | phi_create     |  0.9826  | 1.0000  | -0.9956  | -1.0000 | 0.9826  | SIG  |
|12 | phi_finitude   |  0.9709  | 1.0000  | -0.9890  | -1.0000 | 0.9709  | SIG  |
|13 | phi_lang       |  0.9938  | 1.0000  | -0.9998  | -1.0000 | 0.9938  | SIG  |
|14 | phi_mirror     |  0.9873  | 1.0000  | -0.9978  | -1.0000 | 0.9873  | SIG  |
|15 | phi_collective |  0.9374  | 1.0000  | -0.9657  | -1.0000 | 0.9374  | SIG  |
|16 | phi_unity      |  0.9120  | 1.0000  | -0.9462  | -1.0000 | 0.9120  | SIG  |

- SIGNIFICANT (|r| >= 0.5): **16 / 16**
- NULL (|r| < 0.2): 0 / 16
- Σw = 15.5526
- VERDICT: **PASS**

## Full Result (n=5 checkpoints: step 200, 500, 1000, 1500, 2000)

Same shape, slightly smoothed:

| dim            | r(acc)   | ρ(acc)  | r(CE)    | ρ(CE)   | weight  | flag |
|----------------|---------:|--------:|---------:|--------:|--------:|------|
| phi_holo       |  0.8985  | 0.6000  | -0.8603  | -0.6000 | 0.8985  | SIG  |
| phi_refl       |  0.9888  | 1.0000  | -0.9962  | -1.0000 | 0.9888  | SIG  |
| phi_time       |  0.9908  | 1.0000  | -0.9980  | -1.0000 | 0.9908  | SIG  |
| phi_embodied   |  0.9830  | 1.0000  | -0.9941  | -1.0000 | 0.9830  | SIG  |
| phi_meta       |  0.9851  | 1.0000  | -0.9944  | -1.0000 | 0.9851  | SIG  |
| phi_social     |  0.9825  | 1.0000  | -0.9933  | -1.0000 | 0.9825  | SIG  |
| phi_will       |  0.9904  | 1.0000  | -0.9975  | -1.0000 | 0.9904  | SIG  |
| phi_narrative  |  0.9897  | 1.0000  | -0.9966  | -1.0000 | 0.9897  | SIG  |
| phi_affect     |  0.9810  | 1.0000  | -0.9919  | -1.0000 | 0.9810  | SIG  |
| phi_dream      |  0.9713  | 1.0000  | -0.9857  | -1.0000 | 0.9713  | SIG  |
| phi_create     |  0.9808  | 1.0000  | -0.9912  | -1.0000 | 0.9808  | SIG  |
| phi_finitude   |  0.9713  | 1.0000  | -0.9860  | -1.0000 | 0.9713  | SIG  |
| phi_lang       |  0.9918  | 1.0000  | -0.9967  | -1.0000 | 0.9918  | SIG  |
| phi_mirror     |  0.9868  | 1.0000  | -0.9953  | -1.0000 | 0.9868  | SIG  |
| phi_collective |  0.9410  | 1.0000  | -0.9638  | -1.0000 | 0.9410  | SIG  |
| phi_unity      |  0.9157  | 1.0000  | -0.9432  | -1.0000 | 0.9157  | SIG  |

- SIGNIFICANT: 16 / 16
- Σw = 15.5484
- VERDICT: **PASS**

## Interpretation

- **phi_holo is the weakest correlate** (r≈0.90, ρ≈0.5-0.6). Matches the
  known MI-compression non-monotonicity recorded in
  `project_phi_non_monotonic` — phi_holo peaks at step ~1000 then mildly
  drops while acc continues to rise. Spearman catches this as rank
  mismatch but Pearson (continuous) still sees strong dependence.
- **Remaining 15 dims are near-monotone** in the smoke stub because the
  curves used are the monotone-saturating shapes observed during P5-P20
  gate runs. When W1 wires real probes the separation should widen.
- The tight clustering (most |r| > 0.97) means the smoke data is on a
  single shared latent — real ckpt probes will stress-test this.

## Proposed Composite Weighting

Using `w_i = |r_pearson(phi_i, acc)|` with `|r| < 0.2 → w=0`:

```
||Φ||_AGI  =  (Σ w_i · phi_i^2)^(1/2)  /  (Σ w_i^2)^(1/2)
```

Current smoke weights (normalized to max=1):

| rank | dim             | weight | share |
|------|-----------------|-------:|------:|
|  1   | phi_lang        | 1.0000 | 6.4%  |
|  2   | phi_narrative   | 0.9967 | 6.4%  |
|  3   | phi_will        | 0.9960 | 6.4%  |
|  4   | phi_time        | 0.9958 | 6.4%  |
|  5   | phi_refl        | 0.9956 | 6.4%  |
|  6   | phi_meta        | 0.9915 | 6.3%  |
|  7   | phi_mirror      | 0.9935 | 6.4%  |
|  8   | phi_create      | 0.9887 | 6.3%  |
|  9   | phi_social      | 0.9877 | 6.3%  |
| 10   | phi_affect      | 0.9877 | 6.3%  |
| 11   | phi_embodied    | 0.9870 | 6.3%  |
| 12   | phi_dream       | 0.9774 | 6.3%  |
| 13   | phi_finitude    | 0.9769 | 6.2%  |
| 14   | phi_collective  | 0.9432 | 6.1%  |
| 15   | phi_unity       | 0.9176 | 5.9%  |
| 16   | phi_holo        | 0.9140 | 5.8%  |

Real-data expectation: rank order will change meaningfully once independent
probes are wired. `phi_lang` leading is plausible since benchmarks ARE
language tasks; `phi_holo` trailing is the known non-monotonicity.

## Gaps / Known Limits

1. **Registry is a smoke stub**, not real checkpoint extraction. W1 wires
   the epoch-end hook (see `training/phi_eval_hook_spec.md`) — then
   numbers come from `/workspace/ckpt_*/phi_vec.json` probes.
2. **CE column is surrogate** (from r4 val-loss log, not per-ckpt measured).
   True CE must come from the model forward pass.
3. **Smoke only has 3-5 rows**; Pearson variance stays high until n >= 8.
4. **Saturation warning**: 16/16 SIG means the stub trajectories are too
   correlated. Real probes need independent noise to distinguish dims.
5. `fmt4` uses rounding; last decimal may differ by 1 from strict truncation.
6. Known `PERF: 101 string concatenations detected` notice from hexa
   interpreter is harmless — occurs during report print loop only.

## How to Re-run

```bash
# smoke (default)
hexa run training/eval_phi_corr.hexa

# full (5 ckpts)
hexa run training/eval_phi_corr.hexa --full

# JSON landing
cat /tmp/anima_phi_corr.json
```

## Files

- `training/eval_phi_corr.hexa`         — runnable pipeline
- `training/phi_correlation_report.md`  — this file
- `training/phi_eval_hook_spec.md`      — wire spec for W1
- `/tmp/anima_phi_corr.json`            — machine-readable output
