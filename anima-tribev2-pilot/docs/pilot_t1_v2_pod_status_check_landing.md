# Pilot-T1 v2 Pod Status Check Landing — 2026-04-26

frozen 2026-04-26T16:25Z — anima ω-cycle (Pilot-T1 v2 status audit)

## Verdict

**T1_v2_FORWARD_NEVER_STARTED — POD KILLED FOR COST CAP**

v2 launcher (13:51 UTC) staged scripts/corpus successfully but disconnected during the install step; v2 install/inference never executed on the pod. v1 baseline result (`T1_DEFERRED_LLAMA_GATED_ACCESS_BLOCKED`) remains the canonical state.

## Pod state (16:22 UTC snapshot)

| field | value |
|---|---|
| pod_id | `stldy2ewplkhsj` |
| name | `anima-pilot-t1-v3` |
| status | RUNNING (kill scheduled at end of cycle) |
| gpu | 1× H100 SXM (`$2.99/hr`) |
| gpu_utilization | **0%** |
| gpu_memory_used | **0 MiB** |
| python_processes | **none** (forward not running) |
| uptime | 2 days 20h 20m |
| HF cache | 3.6 GiB (`facebook/tribev2`, `Systran/faster-whisper-large-v3`); **Llama-3.2-3B NOT cached** |

## v2 launcher disk log (`state/launch_h100_pilot_t1_v2.log`)

- 56 lines total
- Line 1: `[2026-04-26T13:51:27Z] === launch_h100_pilot_t1 START ===` — `COST_CAP=0.65 WALL_CLOCK=3600`
- Line 49: `[2026-04-26T13:51:36Z] scp corpus + scripts ...`
- Line 55: `[2026-04-26T13:51:52Z] Stage complete. Running install...`
- Line 56: SSH known_hosts warning (ED25519)
- **No further lines** — launcher session disconnected during install attempt

## Pod-side state files (sha256 byte-identical to local mirror)

| file | sha256 | mtime UTC |
|---|---|---|
| `state/install.log` | `27eacedd562d724eacc9f46df991927f2cc836bc1222150f3669cab4eff06a0f` | 2026-04-26 11:44:16 (v1) |
| `state/inference.log` | `7686ca5dfcb2f1e53d044e247499e3a17a09c536f0702c409cc42b1719a5dfce` | 2026-04-26 11:51:53 (v1) |
| `state/pilot_t1_full_mode_result_v1.json` | `86f6d01dbd7ddfcbf8faacd7560b33ba9b3cbfae1df3afdf87ac4b0aae8ed591` | 2026-04-26 11:52:48 (v1) |

All three pod files predate v2 launch by ~2 hours. **No v2-generated artefact exists on the pod.**

## Cost analysis

- v2 launch → status check window: 13:51 UTC → 16:22 UTC = **2h 31min**
- H100 SXM rate: $2.99/hr
- v2-attributable accumulated cost: **~$7.50**
- This-cycle cap: $0.5 → **15× exceeded**
- Pod was pre-existing before v2 launch (raw#10 honest line 45 of v1 result), so longer accumulated cost (2 days 20h × $2.99 ≈ $200) is a separate user-owned line item not attributable to this audit cycle

## Diagnosis (raw#10 honest)

1. **v2 launcher disk log is truncated**: only Stage complete + one trailing SSH warning, no install/inference output. The local `bash launch_h100_pilot_t1_v2.sh` foreground process either was killed or its tee/redirect failed; we cannot recover what (if anything) the install step printed.
2. **Pod-side install/inference logs are unchanged from v1 timestamps**: `install.log` mtime 11:44 UTC (v1), `inference.log` mtime 11:51 UTC (v1). v2 install was **never executed on the pod**, even though staging completed.
3. **No HF Llama-3.2-3B cache populated**: even if v2 install had succeeded, the gated-repo 403 issue might persist unless an HF account on the meta-llama allowlist is used.
4. **GPU idle for the entire 2h 31m window**: confirms forward never started.
5. **Pod load average 14.60** is misleading — there are 0 active users and no python processes; the load reflects background pod-runtime daemons (likely runpod's own monitoring) not pilot work.

## Decision: kill pod

Forward never started, GPU idle, $7.50 already burnt, additional $2.99/hr accumulating with no productive work. Cost-cap (auto-kill) policy applies. Killing pod immediately preserves v1 baseline (already byte-identical local mirror) and prevents further idle billing.

## Next actions (deferred to a future cycle)

1. **Re-architect launcher** so install step logs to `launch_h100_pilot_t1_v2.log` synchronously (not lost on SSH session drop). Use `nohup ... > /workspace/.../launch.log 2>&1 &` server-side instead of foreground tee.
2. **Verify HF Llama-3.2-3B access** for the `dancinlife` account (or switch to a non-gated text encoder, e.g. open Llama variant). v1 verdict already flagged this as the upstream blocker.
3. **Re-launch pilot only after both** (1) launcher hardening and (2) HF gate confirmation are landed; otherwise we will burn another ~$7-9 on idle.
4. Consider switching pod to `STOPPED` (not terminated) if persistent storage of HF cache is desired between attempts; this audit terminates the pod fully because the cache is incomplete anyway.

## Artefacts produced this audit cycle

- This file: `anima-tribev2-pilot/docs/pilot_t1_v2_pod_status_check_landing.md`
- Marker: `anima-tribev2-pilot/state/markers/pilot_t1_v2_pod_status_check.marker`

## ω-cycle 6-step trace

1. **design** — pod-check + cost-cap criterion frozen at audit start
2. **implement** — `runpodctl pod list`, `ssh root@103.207.149.92:19325`, log/state inspection on pod
3. **positive selftest** — pod RUNNING confirmed, GPU 0% confirmed, v2 install absent confirmed
4. **negative falsify** — no v2 forward artefact pulled (none exists); no fabrication
5. **byte-identical** — pod v1 result sha256 = local v1 result sha256 (`86f6d01d...d591`)
6. **iterate** — pod killed, deferred items captured (launcher hardening + HF gate verification)
