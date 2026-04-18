# CLM r4 pod2 teardown log — 2026-04-18

## Pod

- **id**: `16oxzm6py5xdss`
- **name**: `anima-clm1b-r4-pod2`
- **gpu**: 1× H100 SXM 80GB
- **image**: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- **host**: `root@216.243.220.224:10704`

## Timeline (UTC)

| ts | event |
|---|---|
| 2026-04-18T12:46:00Z | pod fired |
| 2026-04-18T12:59:12Z | trainer started (pid 1395) |
| 2026-04-18T13:04:36Z | trainer SIGKILLed (OOM, 5 min 24 s lifespan) |
| 2026-04-18T13:04:36Z+ | idle burn $2.99/h begins |
| 2026-04-18T13:14:30Z | teardown executed (= 2026-04-18 22:14:30 KST) |

## Cost

- **hourly burn**: $2.99/h
- **idle duration**: ~10 hours (trainer death → teardown)
- **total waste**: ~$30 (mission briefing cited $27 at 22:10 KST; +~$0.15 during teardown exec)
- **produced artifacts**: 0 ckpt, 0 training step

## Root cause

Per `shared/state/clm_r4_pod2_abnormal_20260418.json`:

- Primary: **OOM** during corpus load or optimizer init. 5.38 GB corpus loaded via mmap loader but train loop may have materialized 4.84 GB train_bytes + 538 MB eval_bytes as in-process byte slices before wrapping to mmap reads. RSS reportedly reached 147 GB before kill.
- Secondary: torch.compile Inductor codegen transient RSS spike on 1.5B model.
- OS-level OOM ruled out (host 2 TiB RAM, 1.9 TiB free at probe time). Likely container cgroup memory limit.

## Preserved state

- **R2 ckpt**: `r2:anima-models/clm1b/r4/step_5000.hexackpt` (3.296 GiB, 3,539,201,609 bytes) — **untouched**. From prior pod `abx2uqoa7qbbh8` (2026-04-17 00:51 UTC).
- **R2 logs (new)**: `r2:anima-memory/pod_logs/clm_r4_pod2_16oxzm6py5xdss/`
  - `clm_r4_launch.log` (480 B)
  - `train_r4.log` (845 B) — curriculum banner only, no training steps
  - `corpus_dl.log` (90 B)
  - `_clm_r4_launch_runner.sh` (6,224 B) — runner script
- **Local corpus**: `/Users/ghost/Dev/anima/training/corpus_clm_r4.txt` (5.38 GB)

## Teardown verification

```
$ runpodctl pod list | grep 16oxzm
(no output)
$ runpodctl get pod 16oxzm6py5xdss
ID  NAME  GPU  IMAGE NAME  STATUS   # empty
```

ALM pod `dd88fldzkqhpgk` left alone (untouched per mission constraint).

## Relaunch preconditions

**DO NOT relaunch CLM r4 on py path.** OOM is reproducible and confirmed.

Re-enable `shared/config/r2_sync_watchers.json#clm1b_r4_pod2` only when BOTH:

1. hexa-native GPU path rebuild succeeds (seed-freeze released, `hexa_v2` build clean)
2. MFU > 5% proven on a smoke run (pure hexa, no Python, no torch.compile)

Until then: park. R2 `step_5000.hexackpt` remains the canonical CLM r4 checkpoint.

## Related

- diagnosis: `shared/state/clm_r4_pod2_abnormal_20260418.json`
- watch report: `training/clm_r4_pod2_watch_report_20260418.md`
- launch spec: `training/deploy/clm_r4_launch.hexa`
- mmap loader: `training/clm_mmap_loader.hexa`
- config: `shared/config/r2_sync_watchers.json#clm1b_r4_pod2`
- memory: `project_clm_r4_mmap_plan.md`
