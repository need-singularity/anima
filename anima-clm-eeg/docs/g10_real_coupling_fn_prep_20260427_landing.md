# G10 Real Coupling Fn Prep — D+5 Swap-Ready Landing

- **date**: 2026-04-27
- **raw_rank**: 9 (hexa-only) · raw#10 honesty · raw#12 silent-error-ban · raw#65 idempotent · raw#91 tier-honest · raw#101 minimal
- **scope**: D+5 prep — wire `real_coupling_fn` stub + selftest into existing G10 scaffold without breaking v1 byte-eq.
- **predecessor**: `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa` (v1, 2026-04-26)
- **next**: D+5 hardware port — replace stub body with cross-corr ↔ true ANOVA per `g10_triangulation_spec_post_arrival.md` §3 D+6.

## Deltas (v1 → v2)

| field | v1 | v2 |
|---|---|---|
| `detect_hardware_mode(fixture)` | — | NEW substring scan of `"hardware":` value |
| `real_coupling_fn_x1000(seed,fam,bnd,eeg_band,anima_axis)` | — | NEW STUB → returns `synth_coupling_x1000` (raw#65) |
| `real_f_x1000(...)` | — | NEW STUB → returns `synth_f_x1000` |
| `fixture_band_x1000(fixture, band)` | — | NEW aggregate-band extractor (4/4 bands) |
| `anima_axis_x1000_stub(seed, fam)` | — | NEW deterministic axis placeholder ∈ [200, 799] |
| `run_selftest(...)` | — | NEW 8-assert frozen baseline check |
| classification tier | `NOT_VERIFIED_SYNTHETIC` | branched: `NOT_VERIFIED_SYNTHETIC` / `REAL_HW_PENDING` |
| verdict label | `G10_DRY_RUN_PASS|FAIL` | branched: `G10_DRY_RUN_*` / `G10_REAL_HW_PENDING|FAIL` |

## Branch dispatch (raw#91 tier-honest)

| fixture `"hardware"` | path | classification | verdict label |
|---|---|---|---|
| `false` | `synth_coupling_x1000` (v1 byte-eq) | `NOT_VERIFIED_SYNTHETIC` | `G10_DRY_RUN_PASS` / `_FAIL` |
| `true` (stub) | `real_coupling_fn_x1000` → synth | `REAL_HW_PENDING` | `G10_REAL_HW_PENDING` |
| `true` (post-D+5 swap) | true cross-corr / ANOVA | `REAL_HW_PASS` / `_FAIL` | `G10_REAL_HW_PASS` / `_FAIL` |

raw#91: stub path NEVER advertises `REAL_HW_PASS`. Tier promotion gated on D+5 body swap.

## Selftest results (this land)

- mode synthetic: **8 / 8 PASS** (`fp_extracted=2960889009`, `fixture_bytes=2393`, `cell_pass=16`, `axis_A_F=7399`, `axis_B_F=4314`, `axis_C_F=6259`, `chained_fp=3014690086`, `g10_pass=1`)
- mode hardware (test fixture): **SKIP_HARDWARE_MODE** (sentinel; baseline re-freeze at D+5)
- 3-run reproducibility: synthetic sha256 = `0d969e6409a1f280879f6d2cbac8e06d56eb2bf478c1349e7b3f04d0afb7b9fc` (×3 byte-identical, raw#65 ✓)
- hardware-mode fingerprint: `2798848453` (differs from synth by 1 fixture byte `true`/`false`)

## D+5 critical path checklist (gated on EEG arrival)

- [ ] OpenBCI Cyton+Daisy 16ch impedance < 50 kΩ (`anima-eeg/calibrate.hexa`)
- [ ] Resting baseline 60s eyes-closed (`anima-eeg/eeg_recorder.hexa`)
- [ ] 4 backbone × 120s sessions captured → `anima-eeg/recordings/g10_<backbone>_<ts>.npy`
- [ ] Mk.XI v10 r14 LoRA hidden-state trace per backbone (`--save-family-trace`)
- [ ] Real-data fixture emitted in `synthetic_16ch_v1.json` schema with `"hardware": true`
- [ ] Replace `real_coupling_fn_x1000` stub body with cross-corr(family_ts, band_power_ts)
- [ ] Replace `real_f_x1000` stub body with true 1-way ANOVA F-stat
- [ ] Promote tier `REAL_HW_PENDING` → `REAL_HW_PASS` / `REAL_HW_FAIL`
- [ ] Re-freeze selftest baseline expected values (v3 bump) for hardware-mode
- [ ] Append cert to `state/clm_eeg_g10_hexad_triangulation_post_arrival.json`
- [ ] Roadmap N done entry with G10_REAL_HW verdict

## Cross-refs

- SSOT scaffold: `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa`
- post-arrival spec: `anima-clm-eeg/docs/g10_triangulation_spec_post_arrival.md`
- D-day readiness: `anima-clm-eeg/docs/eeg_d_day_readiness_check_landing.md`
- Mk.XI v10 family axes: memory `project_v_phen_gwt_v2_axis_orthogonal.md`
