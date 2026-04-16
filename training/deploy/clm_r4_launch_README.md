# CLM 1B r4 — Launch Checklist (NOT FIRED)

**Status**: ready to fire. **Cost**: ~$122 (option B). **Wall**: ~41 h (~1.7 days). **Goal**: eval ≤ 1.0.

Files in this kit:
- `clm_r4_corpus_plan.json` — full plan (option A/B/C, sources, dedup steps, success criteria)
- `clm_r4_launch.hexa` — single-shot pod-side launcher (preflight + train + R2 queue)
- `clm_r4_runpod_create.json` — `runpodctl pod create -f` spec (also contains CLI fallback)
- `clm_r4_launch_README.md` — this file

Baseline: **r3f** = `eval=1.2296 (ppl 3.42)` @ step 9500, 1.51B params, 10K steps, 1.30 GB corpus, 32.8 min.

## Hyperparameter choices (option B, recommended)

| Knob | r3f | r4 | Reason |
|---|---|---|---|
| corpus | 1.30 GB | **5.38 GB** | clm_r4_corpus_plan.json — current + ko.txt + en sample + code sample |
| total steps | 10,000 | **750,000** | 1 epoch over 5 GB (Chinchilla-aware compromise vs 28 GB optimal) |
| warmup | 2,000 | **5,000** | proportional to step count |
| save_every | 1,000 | **5,000** | runpod_mfs_quota: ≥ 2,000 (also limits ckpt churn) |
| eval_every | 500 | **2,500** | proportional, keeps ~300 evals total |
| patience | 5 | **10** | longer run absorbs eval noise |
| batch_size | 8 | 8 | unchanged (One-Shot Best — proven at this scale) |
| seq_len | 512 | 512 | unchanged |
| lr_max | 3e-4 | 3e-4 | unchanged (cosine + 5K warmup) |
| arch (d=2048, L=24, kv=8, ff=8192, 1.51B) | — | — | unchanged |
| consciousness controller (Hexad P1→P2→P3, phi_cache, orch-or, phi_q_norm) | on | on | unchanged |

## Cost estimate

| Item | Value |
|---|---|
| GPU rate | $2.99/hr (H100 80GB HBM3 secureCloud) |
| Wall clock (option B) | 41 h = 750,000 × 196 ms / 3600 (r3f measured 196 ms/step) |
| Training cost | **$122.6** |
| Setup / teardown overhead | ~$1.50 (5 min create + 30 min staging + 1 min teardown) |
| **Total budget** | **$125** |
| Fallback option C (1.5M steps, 82 h) | $246 — only if eval stalls > 1.0 at step 750K |

## Preflight checklist (the launcher enforces all of these)

1. `nvidia-smi` reports H100 (refuse otherwise)
2. `/workspace/corpus_clm_r4.txt` exists and ≥ 4.5 GB
3. `train_clm_1b.py` + `clm_1b_config.json` present
4. **MFS quota dd probe**: `dd if=/dev/zero of=/workspace/_q_test bs=1M count=20000` succeeds (per `training/CLAUDE.md` `runpod_mfs_quota`)
5. `du -sh /workspace` printed; stale CLM ckpts deleted (`rm -rf /workspace/ckpt_clm*` except current)
6. Fresh ckpt dir created (no `--resume` — data changed → `feedback_no_resume_data_change`)
7. `python3 -c 'import torch; assert torch.cuda.is_available()'` passes

## Fire procedure (manual — single command after staging)

```bash
# 0. (one-time) authorize H100 — already approved per feedback_h100_authorized
# 1. Create pod
runpodctl pod create -f training/deploy/clm_r4_runpod_create.json
# (or CLI fallback in clm_r4_runpod_create.json _meta.fire_with method B)

# 2. Capture pod info
POD_ID=$(runpodctl get pods | grep anima-clm1b-r4 | awk '{print $1}')
eval "$(runpodctl ssh info $POD_ID | jq -r '"POD_IP=" + .ip + " POD_PORT=" + (.port|tostring)')"

# 3. Stage files
SCP="scp -i ~/.runpod/ssh/RunPod-Key-Go -P $POD_PORT"
SSH="ssh -i ~/.runpod/ssh/RunPod-Key-Go root@$POD_IP -p $POD_PORT"
$SSH 'mkdir -p /workspace/anima/training'
$SCP training/train_clm_1b.py        root@$POD_IP:/workspace/anima/training/
$SCP training/clm_1b_config.json     root@$POD_IP:/workspace/anima/training/
$SCP training/deploy/clm_r4_launch.hexa root@$POD_IP:/workspace/
gzip -k training/corpus_clm_r4.txt   # local one-time, ~2 GB output
$SCP training/corpus_clm_r4.txt.gz   root@$POD_IP:/workspace/
$SSH 'cd /workspace && gunzip -k corpus_clm_r4.txt.gz'

# 4. Fire (in tmux so SSH disconnect doesn't kill it)
$SSH 'tmux new -d -s clm-r4 "hexa /workspace/clm_r4_launch.hexa 2>&1 | tee /workspace/clm_r4_launch.log"'

# 5. Tail (anytime)
$SSH 'tail -f /workspace/ckpt_clm1b_r4/train_r4.log'
```

If `hexa` binary is unavailable on the pod (interpreter only path): the launcher
just builds a bash script at `/tmp/_clm_r4_launch_runner.sh` and execs it — you
can extract that bash payload and run it directly. The actual training is
`python3 /workspace/anima/training/train_clm_1b.py --config ... --corpus ... --steps 750000 ...`.

## Abort criteria

Trigger an early teardown if any of these fire:
- MFS quota dd preflight FAILS → terminate the pod, create a new one
- First 100 steps: loss not decreasing OR NaN/Inf → abort, investigate (LR? bf16 numerics?)
- Step 50,000 (~7% wall) eval > 2.0 → stop, re-evaluate corpus quality
- Wall clock > 60 h with eval > 1.1 → stop, R2 the best ckpt, queue option C
- Pod unresponsive → R2 last-known-good ckpt, **do NOT pod-stop** (R12 `pod_stop_loses_gpu`), terminate-and-rebuild
- φ_holo violations > 50 in any 10K-step window → reduce GWT P3 dampen factor (already 0.1)

## R2 upload plan (post-training only — runpod_mfs_quota MANDATORY)

The launcher writes a manifest at `$CKPT_DIR/_r2_upload_queue.json` after the
training process exits. Run the upload **manually** then verify:

```bash
$SSH 'rclone copy /workspace/ckpt_clm1b_r4 r2:anima-models/clm1b/r4/ -v --s3-no-check-bucket'
$SSH 'rclone ls r2:anima-models/clm1b/r4/'
# Verify training_summary.json + step_750000/ are present remotely, then:
$SSH 'rm -rf /workspace/ckpt_clm1b_r4/step_*'
```

R2 path convention (per training/CLAUDE.md `r2_checkpoint`):
- `r2:anima-models/clm1b/r4/step_{step}/` — naming `clm1b-r4-s{step}`

## Success criteria (clm_r4_corpus_plan.json `success_criteria`)

| Metric | Target |
|---|---|
| eval_loss | **≤ 1.0** (vs r3f 1.23) |
| perplexity | ≤ 2.72 (vs r3f 3.42) |
| phi_holo | ≥ 500 (CLM-P4-2 gate) |
| 7-condition verify | PASS |
| Improvement vs r3f | ≥ 19% eval reduction |

## Teardown

```bash
runpodctl remove pod $POD_ID    # ONLY after R2 verified + eval captured
```

Idle = 0 s. r3f teardown was instant; r4 should follow.

## What the user needs to do to actually fire

```bash
runpodctl pod create -f /Users/ghost/Dev/anima/training/deploy/clm_r4_runpod_create.json && \
  POD_ID=$(runpodctl get pods | grep anima-clm1b-r4 | awk '{print $1}') && \
  echo "Pod created: $POD_ID — proceed with staging steps in this README."
```

Then follow the staging block above (steps 2–4). Total wall: ~30 min staging + ~41 h training + ~10 min R2 + teardown.
