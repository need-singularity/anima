# W1 Hook Integration Report

**Spec:** `training/phi_eval_hook_spec.md` — **Date:** 2026-04-18 — **Status:** PARSE-OK RUN-OK

## Files changed (all uncommitted)

| File | Delta | Purpose |
|------|-------|---------|
| `alm_phi_vec_logger.hexa` | +165 @L140 | `write_phi_vec_json` / `write_ce_json` / `append_run_manifest` / `parse_steps_array` + helpers |
| `train_alm_14b.hexa` | +60 Py @L1262, +7 argparse @L1340 | `--phi-hook {0,1}`; when 1 emits `phi_vec.json`+`ce.json`+`phi_runs.json` per save |
| `eval_phi_corr.hexa` | +180 @L346, `main()` patch | `--manifest` loader + scalar/steps JSON parsers |
| `w1_hook_smoke.hexa` | NEW 275 LOC | 3 mock ckpts + round-trip assert + consumer cmd hint |

## Parse / run

- `hexa parse`: OK on all 4 files.
- `hexa run w1_hook_smoke.hexa`: PASS (3/3 ckpts, manifest round-trip PASS).
- `hexa run eval_phi_corr.hexa --manifest /tmp/w1_hook_smoke/phi_runs.json`: VERDICT PASS (16/16 SIG dims, pass=1).

## Gotchas

1. `use "alm_phi_vec_logger"` did not resolve siblings; smoke inlines byte-identical copies. Logger stays SSOT.
2. `exec()` blocks shell metachars (`>`, `||`).
3. `index_of_from` / `string_trim` / `string_split` not in stdlib — rewrote via `.substring` + `.index_of` + `.split`.
4. `--phi-hook` default OFF: r9/r10 ckpts untouched.
5. Trainer reuses `phi_vec` / `phi_vec_e` from existing `[phi16]` cadence; p5_p20 off → 16 zeros (honest NULL).
