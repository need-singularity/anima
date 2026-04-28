# G10 Hexad Triangulation — Post-Arrival D+5 Workflow Spec

**version**: v1
**frozen_at**: 2026-04-26
**raw_rank**: 9 (hexa-only)
**status**: post-eeg-dependent (synthetic dry-run PASS, hardware activation pending)
**ssot**: this file is the SSOT for the post-arrival workflow; the scaffold tool
`anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa` is the SSOT for the
frozen criteria and the cell-matrix emission schema.

## 1. Frozen Hypothesis

**H_G10**: backbone-family signal × EEG band power × Hexad-category form a
3-axis triangulation in which a 4 × 4 family×band matrix yields ≥ 12 / 16
cell-level PASS *and* all three projected axes (family, band, Hexad-category)
each pass an ANOVA F-test against null at F_x1000 ≥ 4000 (≈ p < 0.01 with
df1 = 3 or 5, df2 ≈ 12).

**Falsification edge**: any single axis F < 4000, or cell PASS count < 12,
falsifies G10. The AND-gate (composite_rule in cert) is intentionally
strict — partial PASS is reported per-cell and per-axis but does not award
G10_PASS.

## 2. Frozen Criteria (mirror of scaffold tool)

| Code | Meaning                                  | Threshold (×1000) |
| ---- | ---------------------------------------- | ----------------- |
| C1   | per-cell coupling ≥ 0.5                  | 500               |
| C2   | per-cell F-statistic                     | 4000              |
| C3   | 16-cell PASS count (≥ 12 / 16)           | 12                |
| C4   | axis_A / B / C F-statistic               | 4000              |

**Verdict rule** (frozen):

```
G10.PASS  iff
    cell_pass_count ≥ 12
  AND axis_A_F ≥ 4000  (backbone family — 4 levels)
  AND axis_B_F ≥ 4000  (EEG band — 4 levels)
  AND axis_C_F ≥ 4000  (Hexad category — 6 levels)
```

Any post-hoc threshold change ⇒ v2 bump (no silent edit).

## 3. Day-by-Day Activation Plan (D+5 .. D+7)

### D+5 — Hardware bring-up + corpus run

**Goal**: capture 16ch × 250 Hz × ≥ 120s EEG per backbone-condition,
with the LLM concurrently emitting hidden-state traces.

| Step | Action                                                                                                         | Tool                                                              |
| ---- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 1    | OpenBCI Cyton+Daisy 16ch impedance check (< 50 kΩ all channels)                                                | `anima-eeg/calibrate.hexa`                                        |
| 2    | Resting baseline 60s eyes-closed (alpha-floor sanity)                                                          | `anima-eeg/eeg_recorder.hexa`                                     |
| 3    | Per-backbone session 120s (×4): Mistral / gemma2 / Llama-3 / Qwen3 each running v10 LoRA on Mk.XI v10 corpus   | `anima-eeg/eeg_recorder.hexa` + Mk.XI v10 inference harness       |
| 4    | Save raw `.npy` per backbone to `anima-eeg/recordings/g10_<backbone>_<timestamp>.npy`                          | `anima-eeg/eeg_recorder.hexa`                                     |
| 5    | Save concurrent hidden-state traces from LoRA forward path (per-backbone family-signal time-series)            | Mk.XI v10 inference harness `--save-family-trace`                 |

### D+6 — Coupling matrix construction

Replace the scaffold `synth_coupling_x1000` with **real measurement**:

```
coupling_x1000(fam, band) =
    1000 × |Pearson_r(
        family_signal_timeseries[fam],     // CLM hidden-state projection onto Mk.XI v10 family axis (fam)
        band_power_timeseries[band]        // EEG band-power per 1s window, averaged across 16 channels
    )|
```

Replace `synth_f_x1000` with **true 1-way ANOVA**:

```
f_x1000(fam, band) =
    1000 × F_stat(
        groups = 4 backbone-conditions × n_windows partitioned by family_signal sign,
        within = cell-level coupling residuals
    )
```

Per-axis ANOVAs (axis_A / B / C) likewise become true sampled F-tests:

```
axis_A_F_x1000 =
    1000 × F_stat(
        groups = 4 family-conditioned subsets,
        within = pooled (band, hexad) residuals
    )

axis_B_F_x1000 =
    1000 × F_stat(
        groups = 4 band-conditioned subsets,
        within = pooled (family, hexad) residuals
    )

axis_C_F_x1000 =
    1000 × F_stat(
        groups = 6 hexad-category-conditioned subsets,
        within = pooled (family, band) residuals
    )
```

The frozen verdict rule (§ 2) applies unchanged.

### D+7 — Verdict + ledger

- Re-run `g10_hexad_triangulation_scaffold.hexa` with env
  `G10_FIXTURE_PATH=<real_data_fixture>` after D+6 emits a real-data
  fixture in the same JSON schema as `synthetic_16ch_v1.json`.
- The scaffold's emission schema (`cell_matrix_4x4`, `family_means_x1000`,
  `band_means_x1000`, `hexad_means_x1000`, axis F triplet, AND-gate verdict)
  is reused byte-for-byte; only the upstream `synth_*` functions are replaced.
- Append result to `state/clm_eeg_g10_hexad_triangulation_post_arrival.json`.
- Register `roadmap N done` entry with G10_PASS / G10_FAIL verdict.

## 4. Hexad Category Mapping

Each (family_idx, band_idx) cell maps onto exactly one Hexad category:

```
cat = (family_idx * 2 + band_idx) mod 6
```

Category index ↔ name:

| cat_idx | name         | Mk.XI v10 lineage                                 |
| ------- | ------------ | ------------------------------------------------- |
| 0       | Law          | Mistral family-leading (rule-bound, deterministic) |
| 1       | Phi          | gemma2 family-leading (φ-symbolic)                |
| 2       | SelfRef      | Llama-3 family-leading (self-reference)           |
| 3       | Hexad        | Qwen3 family-leading (6-fold integration)         |
| 4       | Reflexive    | cross-band coherence (γ↔β phase-lock)             |
| 5       | Transcendent | whole-spectrum integration (1/f scaling)          |

**Cell-count distribution** (asymmetric on purpose — see scaffold comment):

| cat | count |
| --- | ----- |
| 0   | 3     |
| 1   | 3     |
| 2   | 3     |
| 3   | 3     |
| 4   | 2     |
| 5   | 2     |

Total = 16. Asymmetry preserves axis_C dispersion (a balanced 6-cat mapping
would average each cat to grand mean and null the axis_C F).

## 5. Synthetic Dry-Run Verdict (D+0 baseline)

Tool: `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa`
Output: `state/clm_eeg_g10_hexad_triangulation.json`
Determinism: byte-identical (sha256 stable across re-runs)

| Metric            | Value          | Threshold | Pass |
| ----------------- | -------------- | --------- | ---- |
| cell_pass_count   | 16 / 16        | ≥ 12      | ✓    |
| axis_A F ×1000    | 7399           | ≥ 4000    | ✓    |
| axis_B F ×1000    | 4314           | ≥ 4000    | ✓    |
| axis_C F ×1000    | 6259           | ≥ 4000    | ✓    |
| **g10_dry_run**   | G10_DRY_RUN_PASS                | ✓    |

Negative falsifier (`G10_NEG_UNIFORM=1`): all 16 cells uniform 400/1000 →
cell_pass=0, axis_A/B/C F=0 → G10_DRY_RUN_FAIL ✓ (falsifier
edge confirmed).

## 6. Post-Arrival Activation Verdict

`G10_READY_FOR_HARDWARE = TRUE` once:

- [x] Synthetic positive selftest emits G10_DRY_RUN_PASS
- [x] Synthetic negative falsifier emits G10_DRY_RUN_FAIL
- [x] Two consecutive runs produce byte-identical sha256
- [ ] Hardware: OpenBCI Cyton+Daisy 16ch arrives + impedance check passes
- [ ] Hardware: 4 backbone × 120s sessions captured
- [ ] D+6 coupling matrix function ported (replaces `synth_coupling_x1000`)
- [ ] D+6 ANOVA function ported (replaces `synth_f_x1000` + `axis_f_x1000`)

The first three boxes are **complete this cycle** (synthetic prep DONE).
The last four are gated on the EEG hardware arrival event.

## 7. raw#10 Honest Caveats

1. The synthetic dry-run uses a **structured family×band×hexad model with
   small FNV jitter** so that all four AND-gate predicates pass on the
   canonical fixture. This is a SCAFFOLD: it demonstrates the harness wires
   up end-to-end with frozen criteria, but it does NOT assert any real
   backbone↔EEG correlation. Real coupling effect-sizes at D+6 may yield
   far weaker F-stats; the AND-gate may then falsify G10.

2. The 1-way ANOVA proxy `axis_f_x1000` uses a fixed `ANOVA_RESIDUAL_X1000_SQ
   = 1000` rather than a true within-group residual. This is intentional —
   the scaffold ranks group-mean dispersion, not sampled variance. At D+6
   this function is replaced by a true `scipy.stats.f_oneway`-equivalent in
   hexa (ported in `anima-eeg/analyze.hexa` style).

3. Hexad-category mapping `(fam*2+band)%6` is asymmetric to preserve
   axis_C dispersion. A balanced Latin-square mapping would null the F-test
   regardless of underlying data — the asymmetric choice is documented as
   a design constraint, not an empirical finding.

4. The 4-backbone family-signal lineage (Mistral=Law / gemma=Phi /
   Llama=SelfRef / Qwen3=Hexad) is the **Mk.XI v10 LoRA-trained**
   assumption. Memory entry `project_v_phen_gwt_v2_axis_orthogonal.md`
   notes that gemma BASE is Hexad-leading (0.584) but r14 LoRA-trained is
   Law-leading (0.673) — the Mk.XI v10 family axes are corpus-conditional.
   At D+5 the LoRA must be the same r14 build used in #144 evidence.

5. No GPU, no LLM call, no network — this entire prep cycle ran mac-local
   at $0. Hardware-arrival activation cost is bounded by EEG session time
   (≈ 8 min of recording per backbone × 4 backbones = 32 min raw + ≈ 1 hr
   processing) and 0 GPU dollars (the LoRA is pre-trained).

## 8. Cross-References

- `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa` — SSOT scaffold
- `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` — fixture (fingerprint 2960889009)
- `anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa` — pattern parent (P1/P2/P3 aggregator)
- `anima-eeg/analyze.hexa` — band-power FFT pipeline (delta/theta/alpha/beta/gamma)
- Memory: `project_v_phen_gwt_v2_axis_orthogonal.md` (Mk.XI v10 family axis evidence)
- Memory: `project_paradigm_v11_stack_complete.md` (paradigm v11 stack)
- Memory (next): `project_g10_hexad_triangulation_prep_20260426.md` (this cycle)
