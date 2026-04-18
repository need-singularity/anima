# CLM r4 Pod 3 — PROVISION PLAN (DRAFT, NOT FIRED)

**Status:** PLAN ONLY — `runpodctl pod create` NOT executed.
**Timestamp:** 2026-04-18
**Context:** pod2 (`16oxzm6py5xdss`) OOM teardown (commit e80ec871). ALM pod
also deleted (r10 퇴출). Active pods: **0** (verified via `runpodctl pod list`).
Blocker #5 (hexa-native trainer) resolved → relaunch-ready.

## 1. Current pod state

| Pod | Status |
|-----|--------|
| (none) | `runpodctl pod list` → `[]` (0 active / 0 stopped / 0 idle) |

Zero-idle policy satisfied.

## 2. Target spec (pod3)

| Field | Value | Source |
|-------|-------|--------|
| name | `anima-clm1b-r4-pod3` | fresh pod = pod3 (pod2 was OOM) |
| gpuId | `NVIDIA H100 80GB HBM3` | confirmed in `runpodctl gpu list` |
| gpuCount | 1 | single-GPU 1B CLM |
| cloud-type | `SECURE` | pod2 used SECURE ($2.99/hr) |
| image | `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` | **same as pod2** (glibc 2.35 OK, CUDA 12.4 OK for SM90) |
| container-disk | 100 GB | matches pod2 |
| volume | 100 GB @ `/workspace` | **CHANGED from pod2's 0 GB ephemeral** — gives R2 recovery headroom if watcher lags |
| ports | `22/tcp` | SSH only |
| ssh | enabled, `/Users/ghost/.runpod/ssh/RunPod-Key-Go` | same key as pod2 |
| env | `PYTHONUNBUFFERED=1`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, `ANIMA_ROOT=/workspace/anima`, `HF_HOME=/workspace/hf_cache` | mirror pod2 |

### Cost

| Line | Value |
|------|-------|
| Hourly (H100 SXM SECURE) | **$2.99/hr** |
| 24h cap | **$71.76/day** |
| 43h R2-resume ETA | **$128.57** |
| Hard abort if > 60h | $179.40 |

## 3. Ready-to-execute command (DO NOT RUN)

```
runpodctl pod create --name anima-clm1b-r4-pod3 --image runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04 --gpu-id "NVIDIA H100 80GB HBM3" --gpu-count 1 --cloud-type SECURE --container-disk-in-gb 100 --volume-in-gb 100 --volume-mount-path /workspace --ports "22/tcp" --ssh --env '{"PYTHONUNBUFFERED":"1","PYTORCH_CUDA_ALLOC_CONF":"expandable_segments:True","ANIMA_ROOT":"/workspace/anima","HF_HOME":"/workspace/hf_cache"}'
```

Note: `runpodctl 2.x` new syntax — `pod create` (not deprecated `create pod`), flags are kebab-case (`--gpu-id` not `--gpuType`), env as JSON object.

## 4. Pre-flight checklist (post-create, in order)

1. `ssh root@<ip> -p <port> -i /Users/ghost/.runpod/ssh/RunPod-Key-Go 'hostname && nvidia-smi -L'` — SSH + GPU alive
2. `ssh ... 'dd if=/dev/zero of=/workspace/_q bs=1M count=20000 status=none && rm /workspace/_q'` — MFS quota preflight (MANDATORY)
3. `ssh ... 'apt-get install -y rclone tmux'` — tools
4. `scp ~/.config/rclone/rclone.conf root@<ip>:/root/.config/rclone/` — R2 creds
5. `ssh ... 'rclone lsf r2:anima-models/clm1b/r4/ | head'` — R2 reachable
6. `scp /opt/hexa/bin/hexa_v2 root@<ip>:/usr/local/bin/hexa && ssh ... 'chmod +x /usr/local/bin/hexa && hexa --version'` — native binary (glibc 2.35 compatible)
7. `scp training/train_clm.hexa training/clm_1b_config.json training/launch_*.hexa` — trainer sources
8. `ssh ... 'rclone copy r2:anima-models/clm1b/r4/step_5000/ /workspace/ckpt_clm1b_r4/ -v'` — R2-resume (≈3.5 GB)
9. Register pod_id in `shared/config/r2_sync_watchers.json#clm1b_r4_pod3`
10. `ssh ... 'tmux new -d -s clm-r4 "cd /workspace && hexa /workspace/launch_clm_r4.hexa | tee clm_r4.log"'` — FIRE

## 5. Confirmation required from user

- [ ] GPU type: **H100 SXM SECURE** @ $2.99/hr (alt: H100 NVL, H100 PCIe COMMUNITY ~$2.3/hr)
- [ ] Volume: **100 GB persistent** (pod2 used 0 GB ephemeral — crashed lost everything post-teardown; 100 GB adds $0.10/hr ≈ $2.4/day)
- [ ] Image: **pytorch 2.4.0 / cuda 12.4 / ubuntu 22.04** (same as pod2)
- [ ] 24h cost cap: **$71.76/day**, abort if >60h wall-clock
- [ ] Go-signal command: user types `fire pod3` or equivalent

## 6. References

- pod2 fire log: `training/deploy/clm_r4_pod2_fire_log_20260418_214746.md`
- pod2 bootstrap: `training/deploy/clm_r4_pod2_bootstrap_complete_20260418_220205.md`
- pod2 teardown: `training/deploy/clm_r4_pod2_teardown_log_20260418.md`
- r4 design: `training/alm_r11_design.md` (relaunch-adjacent)
- MFS trap: MEMORY `feedback_runpod_mfs_quota`
- Zero-idle: MEMORY `feedback_h100_idle_zero`
