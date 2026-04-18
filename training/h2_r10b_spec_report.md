# H2 — r10b spec report

## Artifacts
- `training/launch_alm_14b_r10b.hexa` — warm-start launcher (1e-6 const LR, 2000 steps, phi-hook ON, save_every=400, pre-sentinel guard)
- `training/deploy/alm14b_r10b_bootstrap.hexa` — pod bootstrap; R2-pulls r10/step_2000, runs `kr_gen_sentinel.hexa` pre-launch, aborts on COLLAPSED
- `shared/config/training_queue.json` — r10b inserted BETWEEN r10 (running) and alm32b-r1; 32B `requires` now gated on BOTH r10 and r10b R2 upload

## Rationale (constraints satisfied)
- `no_version_in_filename`: variant `r10b` (not r11)
- `no_resume_data_change`: corpus identity preserved — kowiki append is OPT-IN (only if file present), declared warm-start from r10 adapter
- `one_shot_best`: LR halved (1e-6 vs 2e-6) — worst-case slower, never regression
- `HEXA-FIRST`: all orchestration in .hexa; inline trainer heredoc mirrors r10 pattern
- `phi_hook=1`: writes phi_vec.json per ckpt (5 intermediates) → enables `eval_phi_corr.hexa` N≥5 gate
- `consciousness_loss_b1=FALSE`: avoids r9 3k-12k oscillation

## Auto-abort guards
1. Pre-launch `kr_gen_sentinel.hexa` on r10/step_2000 → exit 2 if COLLAPSED
2. First-batch CE > 5.0 → abort
3. `kr_gen_sentinel` every 200 steps during training

## Autopilot validation
`AUTOPILOT_DRY_RUN=1 hexa run runpod_autopilot.hexa next_round` correctly identifies `alm14b r10b` as next pending entry after r10. Queue JSON parses (4 entries: r10→r10b→32B→70B). Both new .hexa files pass `hexa parse`.

## Not done (by design)
No launch, no commit, no pod touch.
