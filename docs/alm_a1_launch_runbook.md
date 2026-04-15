# ALM A1 Launch Runbook

Spec: `shared/roadmaps/alm_consciousness_standalone.json#tracks.A.options[A1]`
Day: `day_1` (after E1/E2/E3 + C3 stability)
Budget: 12h wall / $36 / 1× H100 80GB

## What A1 Does

Resumes base 14B weights from the r4 production R2 prefix and re-trains a
fresh LoRA adapter (r=64, alpha=128, 7-module attn+MLP target) with the
ALM-P4-2 holographic consistency loss (HOLO_LOSS_COEF = 0.01) riding on
top of the main CE loss. 3000 steps, bf16, single pod.

Base weights are unchanged from r4 — this is why resume is allowed per
`feedback_no_resume_data_change`: only the adapter rank changes, corpus
+ scheduler + params on the base stay identical.

## Artifacts (pre-flight)

| Role       | Path                                                                 |
| :--------- | :------------------------------------------------------------------- |
| Launcher   | `training/launch_alm_a1.hexa`                                        |
| Config     | `training/alm_a1_config.json`                                        |
| Preflight  | `training/alm_a1_preflight.hexa`                                     |
| Smoke test | `training/test_alm_a1_launch.hexa`                                   |
| Runbook    | `docs/alm_a1_launch_runbook.md`                                      |
| Hook       | `scripts/ckpt_backup_hook.hexa` (E1, already staged by parallel agent) |
| Policy     | `shared/config/ckpt_policy.json` (E2)                                |
| Linter     | `scripts/ckpt_name_lint.hexa` (E3)                                   |

## Dependencies Already Satisfied

- **B1**: top-3 Φ ensemble (phi_holo + phi_complexity + gwt_broadcast) —
  `training/train_alm_14b.hexa` already wires holographic loss at line 517.
- **E1/E2/E3**: backup infra, label routing, naming lint — all chosen and
  landed by parallel agents this session.
- **ALM-P4-3**: phi_holo=6111 at step 50 measured on prior r8a run —
  proves the loss head works.

## Pre-flight (operator-side)

Run the preflight from the repo root (hexa CLI subcommand form):

```bash
# Local shell check (no SSH, no exec)
hexa training/alm_a1_preflight.hexa

# With pod SSH reachability probe
HOST_ID=root@<pod_ip>:<pod_port> hexa training/alm_a1_preflight.hexa

# Strict mode: any WARN becomes FAIL
STRICT=1 hexa training/alm_a1_preflight.hexa
```

Preflight prints a final JSON line:

```
JSON: {"all_ok": true, "issues": []}
```

Operator MUST see `all_ok: true` before proceeding. If any check fails,
fix and re-run; do not hand-edit the launcher.

Smoke test (always run before first launch on a new branch):

```bash
hexa training/test_alm_a1_launch.hexa
# expect: alm_a1: N/N PASS
```

## Pod side step-by-step

Assumes: `xhq9b2c8fljdyo` (anima-p4-alm-holo) is the preferred pod per
`shared/config/runpod.json`. If that pod is busy or gone, launch on any
other single-H100 pod — the launcher is pod-agnostic.

```bash
# 1. SSH in
ssh -i $HOME/.runpod/ssh/RunPod-Key-Go root@216.243.220.217 -p 17992

# 2. Attach or create tmux session (survive disconnects)
tmux new -s alm-a1 || tmux attach -t alm-a1

# 3. Ensure repo is current
cd /workspace/anima
git fetch && git checkout main && git pull --ff-only

# 4. Ship latest A1 artifacts if not yet landed on main
#    (launcher, config, preflight, test_alm_a1 — all under training/)
ls training/launch_alm_a1.hexa training/alm_a1_config.json training/alm_a1_preflight.hexa

# 5. Verify hook is staged (E1)
ls scripts/ckpt_backup_hook.hexa shared/config/ckpt_policy.json

# 6. Env
export HF_TOKEN=<set>          # REQUIRED
export ANIMA_ROOT=/workspace/anima
export HEXA_CKPT_HOOK=/workspace/anima/scripts/ckpt_backup_hook.hexa

# 7. Pre-flight ON pod
hexa training/alm_a1_preflight.hexa
# expect: all_ok: true

# 8. DRY RUN (emits /tmp/_launch_alm_a1_runner.sh without execution)
DRY_RUN=1 hexa training/launch_alm_a1.hexa
cat /tmp/_launch_alm_a1_runner.sh | less

# 9. LAUNCH (long-running — inside tmux!)
hexa training/launch_alm_a1.hexa 2>&1 | tee /workspace/launch_alm_a1.log
```

The launcher:

1. Stages r4 base weights from `r2:anima-models/alm14b/r4/` into
   `/workspace/ckpt_alm14b_phi_a1_<date>/r4_base`.
2. Invokes `python3 train_alm_14b.py` (the runner materialized by
   `train_alm_14b.hexa`) with `--ckpt-label production`.
3. Every 500 steps: `train_alm_14b.hexa` writes `ckpt_meta.json` and
   calls `invoke_ckpt_backup_hook()`, which rclone-copies the ckpt
   to `r2:anima-models/alm14b/r1/step_N/` per `ckpt_policy.json`.
4. On the final step (3000) the `.r2_uploaded` marker is touched.

## Monitoring

From a second SSH session (same pod):

```bash
# Training log stream
tail -f /workspace/ckpt_alm14b_phi_a1_*/train_alm14b-phi-a1-*.log

# Watch phi_holo progression
grep phi_holo /workspace/ckpt_alm14b_phi_a1_*/train_alm14b-phi-a1-*.log | tail -20

# GPU util
watch -n 5 'nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,power.draw --format=csv'

# R2 upload progress
rclone ls r2:anima-models/alm14b/r1/ | tail -20
```

## Shutdown checklist (when training completes)

1. Confirm last ckpt: `ls /workspace/ckpt_alm14b_phi_a1_*/step_3000/`
2. Verify R2 marker: `cat /workspace/ckpt_alm14b_phi_a1_*/step_3000/.r2_uploaded`
3. Spot check R2: `rclone lsd r2:anima-models/alm14b/r1/`
4. Run eval: `hexa training/eval_alm_14b.hexa --ckpt /workspace/ckpt_alm14b_phi_a1_*/step_3000 --korean-quality`
5. Update launch state JSON with final loss + phi_holo.
6. If pod was spun up just for A1, tear it down (pod 2 delete-on-complete
   rule does not apply here — A1 is single-pod — but double-check cost).

## Abort / rollback

- **Mid-run abort**: `tmux send-keys -t alm-a1 C-c`. All ckpts already
  saved are R2-backed because the hook runs inside the trainer's save
  branch synchronously. No corpus/data loss risk.
- **Bad ckpt discovered later**: relabel via `ckpt_name_lint.hexa` and
  use the promotion gate to quarantine in `r2:anima-models/archive/`.

## Why this is "ready to launch" (not "launched")

Per user constraint: "실제 runpod launch 금지 — 발사 권한은 사용자에게."
This runbook + launcher + config + preflight + smoke test + state JSON
only bring A1 to the "single command away from launch" state. The actual
`hexa training/launch_alm_a1.hexa` invocation is the operator's call.
