# E6 — r10 kr_gen OOM Root Fix + F1 Autopilot Ossification

**Session:** 2026-04-18 E6 urgent
**Pod:** dd88fldzkqhpgk (103.207.149.87:10466)
**Run:** alm_14b_r10

## What crashed
Step 200 kr_gen invoked `model.generate` inside the training loop; unsloth 2026.4.6 `fast_generate → run_attention` tried to allocate 80 MiB but GPU had only 12.12 MiB free (78.31 GiB allocated, 43.74 MiB reserved-unallocated). Halving batch was useless — batch was already 1×1024; the leak was *train-step activations* not freed before generate.

## What was fixed (Part A)
1. Patched on-pod `/tmp/_r10_train.py` `kr_gen(step)`: added `gc.collect() + torch.cuda.empty_cache()` before eval, wrapped generate in `torch.no_grad()`, reduced `max_new_tokens` 64→32, `del iid, g` + cache-clear in finally.
2. Mirror-patched laptop heredoc in `training/launch_alm_14b_r10.hexa`.
3. Exported `PYTORCH_ALLOC_CONF=expandable_segments:True`.
4. Clean ckpt (MFS preflight OK) + `setsid nohup` relaunch. PID 15766.

**Trajectory verification:** first-batch CE=5.2372 (match), step 25 loss=2.9254 (match). Next milestone step 200 kr_gen.

## Autopilot ossification delta (Part B)
- Split coarse `cuda_oom` into TWO patterns in `shared/config/runpod_autopilot.json`:
  - `cuda_oom_kr_gen` — matches `run_attention|generate|fast_generate` → action `inject_cuda_empty_cache_before_generate_and_restart` (new patch_fn_registry entry `patch_kr_gen_oom_fix`).
  - `cuda_oom_batch` — matches `reserved by PyTorch but unallocated` → preserves legacy `drop_batch_size_half_and_restart`.
- `runpod_autopilot.hexa` `diagnose_crash/crash_action/crash_fix_command` extended; new fix emits an idempotent python3 -c sed-patch for `/tmp/_r10_train.py`.

## Closed-loop verification (Part D)
`training/runpod_autopilot_test.hexa` extended to 9 cases (added T9 kr_gen OOM). **SUMMARY: 9/9 PASS** — ossification criteria met.

## Logs (Part C)
- Incident appended: `shared/state/runpod_incidents.jsonl` (step200_oom_at_kr_gen).
- Pitfall appended: `shared/hexa_pitfalls_log.jsonl` `P-UNSLOTH-GENERATE-OOM-AT-KR-GEN`.

## Next expected event
Step 200 kr_gen at ~T+13 min (currently step 25, 5318 tok/s). If collapse_hits<3 the run continues to step 2000 save.
