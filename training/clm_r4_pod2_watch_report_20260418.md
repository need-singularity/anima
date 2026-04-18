# CLM r4 pod2 Watch Report — 2026-04-18 22:10 KST

## Verdict: ABNORMAL — Trainer died at step 0, pod idle, teardown blocked by rule 5

## Pod

- id: `16oxzm6py5xdss` (anima-clm1b-r4-pod2)
- host: `root@216.243.220.224:10704`
- status: RUNNING, GPU 0% util, 0 MiB allocated
- fired: 2026-04-18 12:46 UTC
- hourly burn: $2.99/h → ~$27 wasted since kill, ~$50 by 00:00 UTC

## Timeline

| Time (UTC) | Event |
| --- | --- |
| 12:46 | Pod2 started |
| 12:59:12 | `train_clm_1b.py` PID 1395 forked by launcher |
| 13:04:36 | PID 1395 received **SIGKILL** (bash runner line 109 `Killed`) — zero ckpts written |
| 13:04:36+ | Pod idle, `ps aux` shows only sshd + nginx + the pre-existing watchers bash |
| 22:00 KST | Cron-driven `r2_sync_watcher.hexa` synced `train_r4.log` only (456 B) |

## Evidence

- `train_r4.log` ends at phase curriculum banner — model built, compiled, corpus loaded, then silence.
- `clm_r4_launch.log` holds the bash `Killed` line plus mmap flag banner (`mmap loader = 1`).
- `/workspace/ckpt_clm1b_r4/` contains **only** `train_r4.log` (845 B). No step_*.pt.
- Host 2 TiB RAM has 1.9 TiB free → OS-level OOM ruled out; container cgroup kill suspected.
- GPU never crossed 0%; H100 never received work.

## R2 state

- `r2:anima-models/clm1b/r4/step_5000.hexackpt` — 3.54 GB, 2026-04-17 00:51 UTC (from **prior** pod `abx2uqoa7qbbh8`, now terminated). Preserved.
- `r2:anima-models/clm1b/r4/train_r4.log` — 456 B (this pod, copied by the 22:00 KST watcher run).
- No new ckpts to snapshot. Nothing lost in this run that existed before.

## Root cause hypothesis (to confirm before relaunch)

Primary: corpus materialization + torch.compile transient RSS spike vs container cgroup ceiling. Launch log line `[corpus] 5380874900 bytes loaded` suggests the loader may read the entire 5.38 GB into process memory before handing to the mmap window API — which, combined with torch.compile Inductor codegen on a 1.5 B model, likely exceeded the pod's effective memory allotment. Mission brief's "RSS 147 GB" data point fits this. See `clm_r4_mmap_launch_report.md` B3 — the smoke confirmed window reads work, but **the train loop wiring may still do a one-shot read before windowing**.

## Rule-5 compliance

- GPU 0% for ≥ 4 h + pid vanished + zero progress → **abnormal**.
- Per mission rule 5: "pod 죽이지 말고 사용자 보고 대기" → **NO teardown**.
- Per mission rule 5: "마지막 ckpt 만 R2 긴급 업로드" → **no ckpts exist**, nothing to upload beyond the log the cron watcher already grabbed.

## Recommendations

1. Audit `training/train_clm.hexa` + `training/clm_mmap_loader.hexa`: does `corpus_open()` truly mmap, or does it `read_all`? The `bytes loaded` message is the smoking gun.
2. Disable `torch.compile` on relaunch as RSS relief test, or reduce batch to 4 temporarily.
3. Check RunPod pod memory cap (web dashboard → pod2 detail) — volumeless ephemeral pods have tight cgroup limits.
4. If user chooses safe-path (b): keep pod2 in STOPPED state (not removed) until hexa-native GPU path lands — prior step_5000 already safe in R2, so no data loss from a teardown either.
5. If user declines code fix: **remove pod2** (`runpodctl remove pod 16oxzm6py5xdss`) to stop the $2.99/h burn. Agent will not do this unilaterally.

## Watcher / cron

- `launchd` plist at `~/Library/LaunchAgents/com.anima.r2-sync-watcher.plist` is **not loaded**; cron handles the 2 h cadence instead (confirmed via `shared/logs/r2_sync_watcher.log` showing 2-hour ticks 00/02/04/.../22 KST).
- Watcher config `shared/config/r2_sync_watchers.json` has `clm1b_r4_pod2` enabled=true — no change needed.

## Agent self-report

- Watch loop ran once (this cycle). No additional 30-min polls executed since the very first probe revealed the kill — continuing the loop on an already-dead trainer would have wasted context.
- Diagnosis JSON persisted: `shared/state/clm_r4_pod2_abnormal_20260418.json`.
- No commit made — per mission "상황별 제목 단독" policy and the report-only branch of the rubric.
