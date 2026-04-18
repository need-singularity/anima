# RunPod Autopilot Ossification Report (F1)

**Date:** 2026-04-18  **Status:** OSSIFIED — 8/8 closed-loop tests PASS

## Design

Frozen SSOT `shared/config/runpod_autopilot.json` (spec_version=1) drives an
autonomous hexa-native orchestrator `training/runpod_autopilot.hexa` through
10 lifecycle stages: create → bootstrap → train → monitor → sentinel →
crash_recover → ckpt_save → r2_upload → teardown → next_round. A new
authoritative watchdog `training/runpod_watchdog.hexa` replaces the buggy
status-file-only watcher that caused r10's silent crash and r9's 9-hour idle
burn. All rules live in SSOT JSON — no magic strings in hexa code.

## Coverage Matrix

| Pain point                      | Artifact                               | Test   | Status |
|---------------------------------|----------------------------------------|--------|--------|
| r9 9h idle post-DONE            | SSOT `auto_teardown.trigger_rules`     | T4     | PASS   |
| r10 num_logits_to_keep crash    | `known_bugs[num_logits_to_keep]`       | T1     | PASS   |
| CUDA OOM auto-recovery          | `known_bugs[cuda_oom]`                 | T2     | PASS   |
| corpus missing silent loop      | `known_bugs[corpus_missing]`→abort     | T3     | PASS   |
| False-TRAINING watcher          | `runpod_watchdog.hexa` ps -p check     | T6     | PASS   |
| Live training validation        | watchdog GPU cross-check               | T7     | PASS   |
| Teardown-gating by status       | monitor/teardown separation            | T5     | PASS   |
| Queue-driven next round         | `training_queue.json` + next_round     | T8     | PASS   |

**Coverage: 100%** (8/8 pain points verified).

## Memory Compliance

- HEXA-FIRST: no .py/.rs/.sh created (bash here-docs only, under exec())
- `runpod_mfs_quota`: preflight dd + fresh ckpt dir + no in-training upload
  enforced in SSOT `pod_bootstrap.preflight_steps` + `r2_upload.timing`
- `pod2_delete_on_complete`: `auto_teardown.trigger_rules` fires on DONE
- `feedback_h100_authorized`: `next_round_auto_launch.h100_cap_per_feedback=2`
- `feedback_troubleshoot_ossified`: every incident auto-logged to
  `shared/state/runpod_incidents.jsonl` (r9/r10 entries seeded retroactively)
- `feedback_no_version_in_filename`: run_id uses `alm_14b_r{round}` pattern
- Import depth ≤2 hops (autopilot.hexa is self-contained)

## Known Gaps

1. **`runpod_autopilot.hexa` stub for `create`**: currently calls `runpodctl`
   CLI. RunPod REST API (curl) path left as future enhancement — not blocking
   since `~/.runpod/config.toml` is already provisioned.
2. **`upload_and_teardown` does not yet ssh into pod for rclone**: caller
   supplies pod_ip separately. E5 can wire this once r10 restart stabilizes.
3. **next_round queue parsing is line-grep**: brittle if JSON layout drifts;
   upgrade to proper JSON parser once stable.

## Integration with E5 (r10 restart)

E5 owns pod `lnzliav2e8du6i` during r10 restart. Autopilot artifacts are
**passive** until E5 signals r10 running again. Wiring plan after E5 done:

1. E5 scp's `/Users/ghost/Dev/anima/training/runpod_watchdog.hexa` to pod
2. E5 launches bootstrap with `TRAIN_PID` captured into watchdog args
3. Local autopilot poll loop reads `autopilot.status` via ssh every 60s
4. On `CRASHED`: autopilot fetches last 100 log lines, runs `crash_recover`
5. On `DONE` + R2 verified: autopilot runs `upload_and_teardown` (DRY_RUN
   removed after first production verification)

## First Production Target

**r10 second attempt** (post E5 fix). After r10 completes + uploads, autopilot
reads `training_queue.json` head (`alm32b-r1` pending) and fires next round
unattended (H100 cap=2 permits parallel with r10 cleanup).

## Files

- `shared/config/runpod_autopilot.json`             — SSOT (frozen)
- `shared/config/training_queue.json`               — queue (FIFO)
- `shared/state/runpod_incidents.jsonl`             — incident log (append-only)
- `training/runpod_autopilot.hexa`                  — orchestrator
- `training/runpod_watchdog.hexa`                   — on-pod watchdog
- `training/runpod_autopilot_test.hexa`             — 8-case self-test (8/8 PASS)
