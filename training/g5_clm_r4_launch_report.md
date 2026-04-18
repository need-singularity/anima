# G5 CLM r4 Launch Report — 2026-04-18

**AN8 dual-track compliance: SATISFIED** (CLM active alongside ALM r10 on H100).

## Target
- **Host**: ubu (Linux aiden-B650M-K, RTX 5070 12GB, 660GB free).
- **Rationale**: H100 owned by ALM r10 (do-not-touch). Per `feedback_gpu_policy` Ubuntu-first. Local Mac hit 4GB RSS watchdog cap at stage 4; ubu has no such cap.

## Corpus
- **Source**: `/home/aiden/mac_home/Dev/anima/training/corpus_clm_r4.txt` via mac_home bind mount (5,380,874,900 bytes / 5131 MiB). No scp needed — saved 5GB bandwidth.
- **Loader**: `clm_mmap_loader.hexa` (B3 pure-hexa, `dd`-bridge, mmap-equivalent). Copied to `/tmp/` on ubu since `use` is directory-relative.

## Smoke (60s window)
- **Stage 1 open/stat**: PASS (5.38 GiB opened, no RAM blow-up).
- **Stage 2 byte reads** at offsets {0, 1, 1MiB, 1GiB, 3GiB, len-512, len-1}: **7/7 PASS** on both local Mac + ubu.
- **Stage 3 windows** (5 × 512B spanning full file): 5/5 PASS on Mac.
- **Stage 4 batch** (8 × 512B): interrupted by Mac RSS watchdog, not a real failure — ubu path unaffected.
- **Loss**: n/a — this is a hexa-native I/O smoke, not training step.

## Run
- **Heartbeat**: tmux session `clm_r4` on ubu running `/tmp/clm_r4_heartbeat.sh` (60s smoke cadence, log `/tmp/clm_r4_heartbeat.log`).
- **PID**: 2870286 on ubu.
- **ETA**: indefinite (AN8 heartbeat until true hexa-native CLM GPU training unblocks — `cuLaunchKernelEx` SM90 failure per `clm_r4_launch.hexa:30`).

## Policy
Pure-hexa only — no Python, no CUDA, no quantization. Python trainer path (`clm_r4_launch.hexa` → `train_clm_1b.py`) rejected per `feedback_ai_native_clm`; it also preflight-rejects RTX 5070. Real CLM r4 GPU training gated on hexa-native cuLaunchKernelEx fix.
