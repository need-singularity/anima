# ALM 14B r10d Launch Plan — D8 + D9 Drift Fix

**Date:** 2026-04-18 (post-r10c triage)
**Launcher:** `training/launch_alm_14b_r10d.hexa`
**Predecessor:** r10c KILLED at step ~75 (COLLAPSED_UNDETECTED)
**Launch status:** PREPARED — do NOT fire until Idle H100 pod sweep confirms a free pod.

---

## 1. Why r10d (drift origin)

r10c was the E7 triple-fix redesign (OSS-01/02/03/04). It inherited those guards
and added seed sweep, corpus-mix, and phi-hook. It still died. Watchdog flagged
`COLLAPSED_UNDETECTED` at step ~75 → two new drifts surfaced.

| Drift | Rule | Cause | Fix in r10d |
|-------|------|-------|-------------|
| **D8** | E7-OSS-05 | sentinel subprocess fallback only triggered when `subprocess.run` raised. When `hexa` binary was present but returned rc ∉ {0,2} (GLIBC mismatch returned rc=127/139), r10c labelled it `SENTINEL_ERROR(rc)` and kept training. r10c step~75 was actually collapsed; the rc-gate let it slide. | Always-inline byte-check: `inline_byte_check()` runs on every sentinel invocation, independent of subprocess outcome. `final_verdict = 'COLLAPSED'` iff (inline COLLAPSED) OR (subp explicitly COLLAPSED). |
| **D9** | E7-OSS-06 | LR=2e-6 constant × 2000 steps × 8×1024 batch × 95MB corpus (41.8M tokens) under-trains: ~0.4 epoch, LoRA adapter never locks in. r10c early-step loss stayed too high for real descent and when it did drop it was onto a repeat-token local minimum. | Linear warmup 200 steps to peak 1e-5, cosine decay to floor 1e-6 over remaining 1800 steps. 5× higher peak than r10c, matches reference LoRA recipe for ~100MB instruction corpus. |

---

## 2. Parameter diff vs r10c

| Knob | r10c | r10d | Rationale |
|------|------|------|-----------|
| LR schedule | constant 2e-6 | warmup 200 → 1e-5 cosine → 1e-6 | D9 fix (E7-OSS-06) |
| save_every | 2000 | 500 | r10c died @ step 75, zero recovery points. 500 = 4 ckpts, MFS quota-safe (~2.4GB total) |
| Sentinel decision rule | subprocess rc primary, inline only on exception | inline ALWAYS runs, final = inline COLLAPSED OR subp COLLAPSED | D8 fix (E7-OSS-05) |
| Abort status file | `r10c_abort.status` | `r10d_abort.status` | avoid conflict with r10c tombstone |
| Seed | 3407 | 3407 (sweep: 3407/42/1337 via `--seed-sweep`) | fresh LoRA, r9 adapter contamination avoided |
| Corpus | stripped_70b ⊕ kowiki 15% if present | same | no corpus drift (no_resume_data_change compliance) |
| Base | Qwen2.5-14B-Instruct | same | — |
| LoRA | r=32 α=64 dropout=0 q/k/v/o | same | — |
| batch × seq × grad_accum | 8 × 1024 × 1 | same | 70.9% MFU preserved |
| Consciousness B1 loss | OFF | OFF | oscillation avoidance |
| First-batch CE abort | > 8.0 | > 8.0 | unchanged |
| Step 1 loss abort | > 8.0 | > 8.0 | unchanged |
| Early-loss gate (E7-OSS-03) | step ≤ 500 ∧ loss < 1.0 → force sentinel | same | unchanged |

---

## 3. Abort triggers (hard)

1. **First-batch CE > 8.0** → `r10d_abort.status = FIRST_BATCH_CE_HIGH`, exit 2
2. **step=1 loss > 8.0** → `r10d_abort.status = STEP1_LOSS_HIGH`, exit 2
3. **Any sentinel invocation with final_verdict = COLLAPSED** → `r10d_abort.status = MODE_COLLAPSE_STEP=N_REASON=<reason>_INLINE=<v>_SUBP=<v>`, exit 2
   - Inline OR subp COLLAPSED → ABORT (D8 fix)
   - Subp rc ∈ {127, 139, 255, -1} no longer masks inline result

---

## 4. Acceptance gates (soft, for DONE validation)

| Step | Criterion | Action on fail |
|------|-----------|----------------|
| 500  | CE < 4.0 AND sentinel CLEAN | abort, flag `LR_TOO_LOW_OR_HIGH` for r10e design |
| 1000 | kr_gen sentinel PASS (flagged < 3/5 samples) | abort, flag `MID_TRAIN_COLLAPSE` |
| 2000 | training loop exits wstatus=DONE, final ckpt complete | declare r10d done, R2 upload, register as next adapter candidate |

All three gates are **observational** — the trainer itself only aborts on hard
triggers (section 3). Gates 1–2 guide manual review before promoting r10d.

---

## 5. Post-training actions (manual; no in-training upload per MFS quota rule)

1. `rclone copy /workspace/ckpt_alm_14b_r10d_seed3407 r2:anima-models/alm14b/r10d/ -v --s3-no-check-bucket`
2. Run `kr_gen_sentinel.hexa` standalone on final adapter (native binary build,
   not pod binary — local Mac or separate verification pod)
3. Run `hire_sim_judge_lenient.hexa` eval against final adapter
4. If `hire_sim` lenient ≥ 0.85 AND all ckpt sentinels CLEAN → promote r10d as
   A-track canonical; update `shared/config/training_queue.json`

---

## 6. Rollback conditions

- r10d aborts before step 500 (hard trigger fires) → investigate whether D8/D9
  fixes are insufficient. Likely drifts: lr_peak=1e-5 too high (try 5e-6 in
  r10e), or corpus-level collapse independent of LR (revisit corpus mix pct).
- r10d completes but hire_sim ≥ r9 baseline (0.867) not achieved → adapter
  under-trained. r10e: extend to 3000 steps with same schedule or try r10d
  adapter warm-start + 500 more steps at constant 5e-7.
- r10d sentinel passes but hire_sim collapses on free-form domains (email,
  meeting, doc, research — same regression pattern as original r10 retraining
  diagnosis) → corpus identity problem, not LR. Move to r11 with mixed corpus
  (kowiki baseline + hire_sim tasks 20%) per `r10_regression_diagnosis.json`
  r11_design block.

---

## 7. Compliance audit

- `no_version_in_filename`: `r10d` = alphabetic variant suffix, not version number
- `no_resume_data_change`: fresh LoRA, fresh optimizer, step counter from 0. LR
  schedule changes are optimizer hyperparams, not a resume
- `one_shot_best`: hard-aborts enforce no mid-training parameter tweaks
- `HEXA-FIRST`: single `.hexa` launcher, zero new `.py`/`.rs`/`.sh` in repo.
  Python trainer materialised at `/tmp/_train_alm_14b_r10d.py` at runtime
  (same pattern as r10c)
- `hexa silent-exit`: launcher has 0 `use` imports (self-contained, ~500 LOC)
- `runpod_mfs_quota`: 20GB `dd` probe in wrapper, save_every=500 × ~600MB
  LoRA-only ≈ 2.4GB total, fresh ckpt dir per seed
- `no-quantization`: bfloat16 only, no 4/8-bit
- `troubleshoot-comments`: D8 + D9 fixes have inline comments citing root cause
- `One-Shot Best`: hyperparams locked at launch, no mid-run re-tune paths

---

## 8. Invocation

```bash
# Production (2000 steps, seed=3407 only)
hexa run /workspace/anima/training/launch_alm_14b_r10d.hexa

# Smoke (200 steps, single seed)
hexa run /workspace/anima/training/launch_alm_14b_r10d.hexa --smoke

# Seed sweep (3 × 200-step smokes, all must PASS before production)
hexa run /workspace/anima/training/launch_alm_14b_r10d.hexa --seed-sweep

# Selftest (local, no pod touch — verifies file generation)
hexa run /workspace/anima/training/launch_alm_14b_r10d.hexa --selftest

# Dry-run (print plan only, no file writes to /tmp are executed — writes happen
# but no bash invocation)
DRY_RUN=1 hexa run /workspace/anima/training/launch_alm_14b_r10d.hexa
```

---

## 9. Launch decision

Launch decision is deferred to the **Idle H100 pod sweep** background task. This
file prepares the launcher and plan only. A separate BG will consume this file
and fire when an idle pod is identified. Do not fire from this session.
