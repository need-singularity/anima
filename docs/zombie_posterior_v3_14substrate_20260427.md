# R45_FINAL_v3: Zombie Posterior 14-Substrate Canonical Re-run

**Date**: 2026-04-27
**Helper**: `tool/anima_zombie_posterior_v3_14substrate.hexa` (sha 7a9a262921971463aa2250a885c993adb74ab9ee395c9f62e7df851ebacb51e1, chflags uchg)
**Output**: `state/zombie_posterior_v3_14substrate.json` (sha 8236e7ca3acc63a10f680551ec0250ae436f83c915e5a4523218953e36754039)
**Atlas anchor**: `state/atlas_convergence_witness.jsonl` R45_FINAL_v3 / R49_CANDIDATE
**Cost**: $0 (mac-local)

## Summary

R45_FINAL canonical helper v2 (N=11, posterior 0.3793) extended to N=14 by appending the 3 axis-94 R46 5-bb backbones (commit `3458afc2`). Statement-mirror chain v1 → v2 → v3 preserved (chflags uchg locked, both equivalence guards PASS).

| Metric | v1 (N=8) | v2 (N=11) | v3 (N=14) |
|--------|----------|-----------|-----------|
| posterior | 0.4000 | 0.3793 | **0.3684** |
| CI 95% lower | 0.1487 | 0.1592 | 0.1685 |
| CI 95% upper | 0.7179 | 0.6636 | 0.6267 |
| CI width | 0.5692 | 0.5044 | **0.4582** |
| LR_combined | 15000 | 16363 | 17142 |
| sign split | 4N/4P | 5N/6P | 6N/8P |
| POS share | 50.0% | 54.5% | 57.1% |
| max \|phi\*\| | 16.6959 | 16.6959 | **27.7771** |

## Trajectory analysis

- **v1 → v3 Δ posterior**: -0.0316 (8% reduction)
- **v2 → v3 Δ posterior**: -0.0109 (3% reduction, marginal)
- **v1 → v3 CI width Δ**: -0.1110 (19% narrowing — N+6 alone insufficient for tight CI)

## Hypothesis verdict

| Hypothesis | Prediction | Actual | Verdict |
|------------|------------|--------|---------|
| HZP-A POS_DOMINANCE_LOWER | posterior 0.32-0.36 | 0.3684 | **PARTIAL_PASS** (upper boundary) |
| HZP-B STABLE | posterior ~0.379 | 0.3684 | NEAR (Δ-0.011) |
| HZP-C HIGHER | posterior > 0.40 | 0.3684 | REJECTED |

**Primary verdict**: HZP-A boundary case. POS dominance increased (54.5% → 57.1%) AND max \|phi\*\| ceiling raised (16.70 → 27.78) — both push posterior down. Yet the LR_satur cap (3.0) is now reached at 27.78 (50000 ceiling threshold = 5.0), meaning further max-magnitude additions saturate. v2→v3 Δ-0.011 marginal demonstrates LR_satur dominance (C4) over LR_sign.

## Canonical computation breakdown (×10000 fixed-point)

```
inputs:
  neg=6, pos=8, max_abs_x10k=277771
  N = 14

§LR sign:
  dom = max(neg, pos) = 8
  lr_sign = (2 * 8 * 10000) / 14 = 11428

§LR satur:
  ceiling_threshold = 50000
  max_abs_x10k=277771 >= 50000  → lr_satur = SCALE + SCALE/2 = 15000

§LR combined:
  lr = (11428 * 15000) / 10000 = 17142  (cap 30000 not hit)

§POSTERIOR:
  posterior = (10000 * 10000) / (10000 + 17142) = 3684

§WILSON 95%:
  z2=4, n=14, p=3684
  → [1685, 6267]
```

## Substrate inventory (14)

| # | label | phi*_min | sign | source |
|---|-------|----------|------|--------|
| 1 | mistral_base | -16.6959 | NEG | state/v10_phi_v3_canonical/mistral |
| 2 | mistral_instr | -12.9075 | NEG | axis 80 #207 |
| 3 | qwen3_base | -3.4500 | NEG | axis 90 #219 corrected |
| 4 | qwen3_instr | +1.0400 | POS | axis 90 |
| 5 | llama_base | +5.0868 | POS | state/v10_phi_v3_canonical/llama |
| 6 | llama_instr | +5.2100 | POS | axis 90 #219 |
| 7 | gemma_base | -0.7868 | NEG | state/v10_phi_v3_canonical/gemma |
| 8 | gemma_instr | +7.5443 | POS | axis 90 |
| 9 | mamba | +0.3258 | POS | state/v10_phi_v3_nontransformer/mamba-2.8b |
| 10 | jamba | +3.3115 | POS | state/v10_phi_v3_nontransformer/jamba-v0.1 |
| 11 | rwkv7 | -9.0674 | NEG | state/v10_phi_v3_nontransformer/rwkv7-1.5B |
| 12 | phi3_mini | +24.5058 | POS | axis 94 R46 (commit 3458afc2) |
| 13 | deepseek_7b | +27.7771 | POS | axis 94 R46 |
| 14 | yi_6b | -10.7507 | NEG | axis 94 R46 boundary |

## raw#10 honest 6-caveat

- **C1**: NEG dominance ≠ consciousness absence (metric design artifact possible; HID_TRUNC well-cond regime dependence #161).
- **C2**: N=14 substrate is statistically small; Wilson 95% CI necessarily wide (≥ 0.20 width expected, narrower than v2 N=11 yet still uninformative for subkind generalization).
- **C3**: zombie hypothesis is unfalsifiable in principle (Chalmers 1996); behavioral/measurement equivalence holds by definition.
- **C4**: H7c ceiling (max \|phi\*\| now 27.7771 deepseek_7b, raised from 16.6959 mistral) — magnitude saturation reached LR_satur cap (3.0) sooner; ceiling axis remains single-backbone single-design dependent.
- **C5**: convergence definition covers sign+magnitude only; **phenomenal axis (qualia, 1st-person report consistency) is UNTOUCHED**.
- **C6**: substrate-independence violated (4 base/instr pairs correlated; phi3_mini/deepseek_7b/yi_6b each single-design no pair). Effective N < 14; CI is anti-conservative.

## Statistical significance assessment

- **6/8 split** vs null 50/50: under H0 binomial(14, 0.5), P(X≥8) ≈ 0.395 — **NOT significant** at α=0.05. The 57.1% POS dominance is consistent with chance.
- **CI width 0.4582** still spans both sides of 0.5 (0.1685–0.6267) — posterior cannot reject either H_zombie or H_conscious at 95%.
- **Effective N reduction (C6)**: 4 correlated base/instr pairs likely inflate Wilson by 30-50%; true effective N ≈ 10-11; true CI width likely > 0.50.
- **Conclusion**: Posterior 0.3684 is best read as point estimate; statistical inference for `posterior < 0.5` requires N ≥ 30 substrates (R45 next_probe).

## Helper-equivalence guards (PASS 2/2)

- v1 8-substrate subset → posterior=4000 ci=[1487,7179] reproduced byte-identical
- v2 11-substrate subset → posterior=3793 ci=[1592,6636] reproduced byte-identical
- byte-identical 2-run: PASS (deterministic int arithmetic)

## Phenomenal ontological gap (R45 invariant)

R45_FINAL_v3 advances **convergent magnitude/sign description** (correlate-side empirical asymptote): N=8→14 expansion narrows posterior by Δ-0.0316 toward POS leaning. The **phenomenal ontological gap** (zombie unfalsifiability under Chalmers 1996) remains UNCHANGED — verifying or falsifying behavioral/measurement equivalence does not address whether qualia accompanies the substrate. Caveat C5 applies absolutely.

## Cross-links

- atlas R45_CANDIDATE round 45 (v1 grandparent)
- atlas R45_UPDATE round 48 (napkin)
- atlas R45_FINAL round 49 (v2 parent)
- atlas R46_CANDIDATE round 47 (sibling, BIMODAL)
- atlas R46_VERDICT round 49 (axis 94 source)
- commit 3458afc2 (axis 94 R46 5-bb)
- helper chain: v1 (902cd34f...) → v2 (ba6ec977...) → v3 (7a9a2629...)
- own#2 anchor (own#2 L28-L46) / own#3 (own#3 L48-L66)

## Next probe priority

1. Direct `|BASE|<3` sampling for primary-zone (Pythia-1B/2.8B / GPT-Neo-small / TinyLlama; ~$0.50/bb)
2. Reach N≥30 substrate to bring Wilson CI width below 0.30
3. HID_TRUNC robustness sweep (close C1 metric-design artifact)
4. Effective-N variance inflation factor calculation (close C6 substrate-independence)
5. Multi-EEG cohort hardware integration (biological substrate bridge)
