# CLM 1B r4 — Pod 2 (dedicated H100) launch plan

Status: **DRY-RUN / PLAN ONLY — NOT FIRED.** Awaiting user "fire" command.
Author: auto-generated 2026-04-18 per `feedback_h100_authorized` (max 2 H100 pods).

## Why a second pod

- Pod 1 (`dd88fldzkqhpgk`, `anima-alm14b-r9`) is running ALM r9 14B — cannot share.
- CLM r4 5.38 GB corpus × 750K steps × ~0.21 s/step = **~44 h wall time**.
- Policy gates (per memory):
  - `feedback_gpu_policy` — Ubuntu first, H100 last resort → but **ALM+CLM parallel is Ubuntu-impossible** (RTX 5070 < 14B model), H100 OK.
  - `feedback_h100_authorized` — max 2 pods, no confirmation needed.
  - `feedback_h100_free_use` — never stop loop for pod cost reasons.
  - `feedback_dual_track` — CLM hexa + ALM Python must run simultaneously.

## Pod spec (mirrors `clm_r4_runpod_create.json`)

| Field              | Value                                                    |
|--------------------|----------------------------------------------------------|
| name               | `anima-clm1b-r4-pod2`                                    |
| imageName          | `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` (CUDA only — no Python training from this session, hexa-native wrapper) |
| gpuTypeId          | `NVIDIA H100 80GB HBM3`                                  |
| gpuCount           | 1                                                        |
| vcpuCount          | 16                                                       |
| minMemoryInGb      | 64                                                       |
| containerDiskInGb  | 100 (peak ckpt rotation = 54 GB + 5.38 GB corpus)        |
| volumeInGb         | 0 (ephemeral — R2 watcher mandatory)                     |
| ports              | `22/tcp`                                                 |
| secureCloud        | true                                                     |

## Bootstrap sequence (7 steps)

1. **Pod create**
   `runpodctl pod create -f training/deploy/clm_r4_runpod_create.json`
2. **SSH info** — capture `POD_IP`, `POD_PORT` from `runpodctl ssh info <pod_id>`.
3. **Stage trainer + launcher**
   - `scp training/train_clm.hexa   root@$POD_IP:/workspace/anima/training/`
   - `scp training/clm_1b_config.json root@$POD_IP:/workspace/anima/training/`
   - `scp training/deploy/clm_r4_launch.hexa root@$POD_IP:/workspace/`
4. **R2-resume path (preferred — saves 5 GB upload + 14 kstep compute)**
   - `ssh root@$POD_IP -p $POD_PORT 'rclone copy r2:anima-models/clm1b/r4/step_5000.hexackpt /workspace/ckpt_clm1b_r4/ -v'`
   - Skips: corpus upload + first 5000 steps (~17 min saved).
   - **Caveat:** memory `feedback_no_resume_data_change` — OK here because corpus is unchanged (same 5.38 GB file).
5. **Corpus upload** (fallback if R2-resume impossible)
   - `scp -P $POD_PORT training/corpus_clm_r4.txt.gz root@$POD_IP:/workspace/`
   - `ssh ... 'cd /workspace && gunzip -k corpus_clm_r4.txt.gz'`
6. **hexa binary** — copy pre-built H100 binary (`$HEXA_LANG/target/release/hexa`) or fall back to bash-extracted payload (launcher is thin wrapper).
7. **Fire in tmux** (R11 nohup + R10 verify)
   - `ssh ... 'tmux new -d -s clm-r4 "hexa /workspace/clm_r4_launch.hexa 2>&1 | tee /workspace/clm_r4_launch.log"'`

## R2 sync automation (1h tick)

Reuses existing `scripts/r2_sync_watcher.hexa` — add new entry to
`shared/config/r2_sync_watchers.json`:

```json
{
  "id": "clm1b_r4_pod2",
  "enabled": true,
  "pod_id": "<FILL_AFTER_CREATE>",
  "host": "root@<FILL>",
  "port": 0,
  "ckpt_dir": "/workspace/ckpt_clm1b_r4",
  "r2_prefix": "r2:anima-models/clm1b/r4/",
  "rclone_flags": "-v --s3-no-check-bucket --transfers 4",
  "ssh_opts": "-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes",
  "note": "CLM r4 pod 2. Launchd fires every 2h (shared/launchd/com.anima.r2-sync-watcher.plist). Change StartInterval to 3600 for 1h if training enters critical step range."
}
```

Host-side watcher is **immune to pod restarts** (per
`RUNPOD_VOLUMELESS_EPHEMERAL_WIPE`, `clm_r4_launch.hexa:51`).

## Completion detection → auto-teardown

Trigger (all-of):
1. `training_summary.json` present in `/workspace/ckpt_clm1b_r4/`
2. `rclone ls r2:anima-models/clm1b/r4/step_750000/` non-empty
3. `eval_loss ≤ 1.0` recorded in summary

Teardown (manual approval, mirrors `feedback_pod2_delete_after`):
```
runpodctl remove pod <pod_id>
```

Abort criteria (per `clm_r4_runpod_create.json#_abort_criteria`):
- MFS quota dd probe fails → terminate, rebuild
- First 100 steps: loss NaN/Inf or not decreasing → abort
- Step 50000 eval > 2.0 → stop, re-evaluate corpus
- Wall clock > 60h with eval > 1.1 → stop, save best, option C next round

## Cost estimate

| Scenario          | Wall (h) | $/h   | Total    |
|-------------------|----------|-------|----------|
| R2-resume (5K→750K) | ~43.3    | 2.99  | **$129.5** |
| Fresh (0→750K)     | 44.0     | 2.99  | $131.6   |
| Option C fallback  | 82.1     | 2.99  | $245.5   |

## Self-test

```
hexa training/deploy/clm_r4_pod2_launch.hexa --selftest
```
Prints planned runpodctl invocation and bootstrap sequence without executing.

## Fire command (awaiting user approval)

```
hexa training/deploy/clm_r4_pod2_launch.hexa --selftest   # dry-run first
# Then user explicitly types "fire":
runpodctl pod create -f training/deploy/clm_r4_runpod_create.json
```
