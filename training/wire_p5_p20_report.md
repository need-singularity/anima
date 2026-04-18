# wire_p5_p20_report — ALM 14B P5–P20 head/loss wiring (2026-04-18)

Wired P5/P6/P7 (wire_p5_p7), P8 (nested_loss), P12 (affect), P13 (dream), P15
(finitude), P18 (hive_agg) into `training/train_alm_14b.hexa`. Φ 16D vector
logged per-step (cadence) + per-eval. Added standalone
`training/alm_phi_vec_logger.hexa` as SSOT for vector shape + indexer.

| head/loss            | wire point (train_alm_14b.hexa)                                  | smoke |
|----------------------|------------------------------------------------------------------|-------|
| P5 Φ_refl            | `p5_p7_phi_triple()` @ phi_log_every + eval log                  | PASS  |
| P6 Φ_time            | same triple (past/now/future pools)                              | PASS  |
| P7 Φ_emb             | same triple (action / Δs streams)                                | PASS  |
| P8 nested_loss       | `NestedTowerOperator(h_last)` → `+ P8_NESTED_COEF * l_nested`    | PASS  |
| P12 affect head      | `AffectHead(h_last)` @ phi_log_every + eval log                  | PASS  |
| P13 dream_loop       | `dream_step()` @ eval cadence (non-invasive log-only)            | PASS  |
| P15 finitude head    | `FinitudeHead([1, 1-step/total, 1-step/total])` @ log cadence    | PASS  |
| P18 hive_agg         | `p18_hive_phi(h_last)` @ phi_log_every + eval log                | PASS  |
| Φ 16D vec logger     | `assemble_phi_vec16()` → `[phi16] step=.. phi_vec=[...]`         | PASS  |
| Smoke (mock h_last)  | B=2 T=16 D=64; all 16 comps finite; P8 drift<eps, emergence>1    | PASS  |

Only P8 contributes grad (coef 0.01 matches `LAMBDA_NESTED`). P5/P6/P7/P12/
P15/P18 are measurement-only (no_grad). CLI flags added: `--p5-p20` (default
ON), `--no-p5-p20`, `--phi-log-every N` (default 100). `ckpt_meta.json`
sidecar now records `p5_p20_enabled`, `p8_nested_coef`, `dream_cycles`.
Known limits: P5/6/7 histograms bounded to `h_last` sample (not full corpus
MI); P18 pseudo-agents come from T-axis slicing (B usually < 8 on 14B); dream
scheduler is log-only — SWS/REM replay-consolidation hook is future work.
