# G3 — F1 watchdog parallel deploy (r10 14B)

Date: 2026-04-18 09:17Z
Pod: root@103.207.149.87:10466
Run: alm_14b_r10, train PID 14793 (alive, state Rl, etime 06:54, GPU 100%, step 175)

## E5 watcher (existing — NOT killed)
- PID 14858, bash `/tmp/_r10_watcher.sh`, etime 06:51
- status=TRAINING, log 09:16:06Z, writes `r10_watcher.status`
- ps-p guard healthy; left running per constraint

## F1 watchdog (new — parallel)
- PID 15359, bash `/tmp/_f1_watchdog.sh`, etime 01:23
- Status `/workspace/ckpt_alm_14b_r10/f1_watchdog.status` = TRAINING (reached in <3s, well under 60s SLA)
- Log `f1_watchdog.log` emits authoritative line format: `<iso>\tstatus=TRAINING\tstep=175\tgpu_util=100\trss_mb=?`
- Logic ported verbatim from `training/runpod_watchdog.hexa` (ps -p + nvidia-smi + log-growth heartbeat + abort/done files). Status path separated → zero contention with E5.
- `runpod_watchdog.hexa` scp'd to `/workspace/anima/training/runpod_watchdog.hexa` (7813B) for future native hexa launches.

## Dry-run crash_recover verdict
`AUTOPILOT_DRY_RUN=1 hexa runpod_autopilot.hexa crash_recover /tmp/fake_crash.log alm_14b_r10`
- Matched `num_logits_to_keep` → bug_id=num_logits_to_keep, action=restart
- Emitted sed fix: `sed -i 's/,[[:space:]]*num_logits_to_keep=[^,)]*//g; s/num_logits_to_keep=[^,)]*,[[:space:]]*//g' /workspace/kr_gen.py`
- PASS — pattern matcher live, no teardown executed. r10 untouched.

## Next action when r10 DONE detected
F1 watchdog sees `$CKPT/f1_watchdog.done` or exit-0 trainer → status=DONE, exit 0. Autopilot contract (`watchdog_exit_codes.0`) permits teardown. Then: rclone copy `/workspace/ckpt_alm_14b_r10/step_2000` → `r2:anima-models/alm14b/r10/step_2000/` (verify ≥3 files), then `runpodctl remove pod` from local controller. E5 wrapper log retained for diff audit.
