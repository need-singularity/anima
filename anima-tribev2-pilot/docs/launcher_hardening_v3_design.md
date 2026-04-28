# Pilot-T1 v3 Launcher Hardening — Design

frozen: 2026-04-26
session: anima ω-cycle (Pilot-T1 v3 launcher hardening, post-$7.52 burn)
target: `anima-tribev2-pilot/scripts/launch_h100_pilot_t1_v3.sh.txt`

## 1. Why (burn evidence)

Pilot-T1 v2 (`launch_h100_pilot_t1_v2.log`) terminated locally at line 56 with the
final visible event:

```
[2026-04-26T13:51:52Z] Stage complete. Running install...
Warning: Permanently added '[103.207.149.92]:19325' (ED25519) to the list of known hosts.
```

— i.e. SSH dropped during `$SSH "timeout 900 bash .../install_pod_deps.sh ..."`. Because
this command was **foreground over SSH**, the install process on the pod was tied to
the SSH session and terminated with it. Status check 2 h 31 min later confirmed:

| signal                         | observation        |
|--------------------------------|--------------------|
| pod state                      | RUNNING            |
| GPU utilization                | 0 %                |
| GPU memory                     | 0 MiB              |
| python processes               | 0                  |
| `state/` mtime change          | 0                  |
| **idle burn @ $2.99 / hr**     | **$7.52**          |
| cost cap this cycle            | $0.50 (15.04× breach) |

Marker: `state/markers/pilot_t1_v2_pod_status_check.marker`
Landing: `docs/pilot_t1_v2_pod_status_check_landing.md`

Root cause = **single point of failure**: SSH liveness ↔ pod-side workload liveness
were coupled, with **no heartbeat** to detect "started but disconnected" vs "never
started", and **no cost-cap safety net** on the pod side.

## 2. Hardening (4 fixes)

| ID    | Fix                          | Mechanism                                                                            |
|-------|------------------------------|--------------------------------------------------------------------------------------|
| FIX-1 | server-side daemonize        | Both install (`run_install.sh`) and inference (`run_infer.sh`) are launched on the pod via `nohup ... > LOG 2>&1 &` + `disown`. SSH session can drop with no impact on workload survival. |
| FIX-2 | heartbeat markers            | Pod-side wrappers write 4 markers under `${POD_WORK}/state/markers/`: `install_started.marker`, `install_done.marker`, `inference_started.marker`, `inference_done.marker`. Each marker carries timestamp + pid + rc. |
| FIX-3 | idle auto-kill (pod-side)    | `watchdog.sh` runs in parallel and, if `install_started.marker` is missing after `IDLE_KILL_SEC` (default 1800 s = 30 min), invokes `runpodctl stop pod` (or `poweroff` fallback) and writes `watchdog_kill.marker`. Caps worst-case idle burn at ~$1.50. |
| FIX-4 | client-side polling fail-fast| Local launcher polls markers via short-lived SSH probes every `POLL_INTERVAL_SEC` (30 s default). Distinct fail-fast budgets: install_started ≤ `CLIENT_FAIL_FAST_SEC` (3600 s), install_done ≤ 1200 s, inference_started ≤ 300 s, inference_done ≤ `INFER_CAP + 120 s`. Any breach → `runpodctl stop pod`. |

## 3. Marker contract

| marker                       | producer                    | content                                  |
|------------------------------|-----------------------------|------------------------------------------|
| `install_started.marker`     | `run_install.sh` (pod)      | `started_at=<ISO> pid=<int>`             |
| `install_done.marker`        | `run_install.sh` (pod)      | `done_at=<ISO> rc=<int>`                 |
| `inference_started.marker`   | `run_infer.sh`   (pod)      | `started_at=<ISO> pid=<int>`             |
| `inference_done.marker`      | `run_infer.sh`   (pod)      | `done_at=<ISO> rc=<int>`                 |
| `watchdog_kill.marker`       | `watchdog.sh`    (pod)      | reason + elapsed + threshold             |

Markers are pulled back to `state/markers_pod_v3/` for offline forensic re-construction
of the run timeline even if SSH dropped mid-run.

## 4. Env knobs

| var                    | default | meaning                                                  |
|------------------------|--------:|----------------------------------------------------------|
| `POD_ID`               |  (auto) | RunPod ID; auto-detected by name prefix `anima-pilot-t1` |
| `COST_CAP_USD`         |    0.65 | annotative; not enforced by launcher (advisory)          |
| `WALL_CLOCK_SEC`       |    3600 | total budget (install + inference)                       |
| `IDLE_KILL_SEC`        |    1800 | pod-side: kill self if `install_started` not seen        |
| `CLIENT_FAIL_FAST_SEC` |    3600 | client-side: kill pod if `install_started` not seen      |
| `POLL_INTERVAL_SEC`    |      30 | client-side polling cadence                              |
| `DRY_RUN`              |       0 | 1 = synthetic selftest path (no SSH, no pod ops)         |

## 5. Selftest (DRY_RUN=1)

Synthetic path verifies the polling timing logic without touching SSH or RunPod:

- **positive** : 4 markers are written by a background subshell at 1-second intervals.
  Polling loop must observe each marker within a 30 s budget.
- **negative** : empty synthetic dir; polling loop must trigger fail-fast at the 5 s
  threshold (compressed budget for selftest).

Both must pass for `DRY_RUN=1` exit 0.

## 6. Out of scope (raw#10 honest)

- v3 launcher does **not** create new pods. It still attaches to a RUNNING pod whose name starts with `anima-pilot-t1`.
- v3 launcher does **not** verify HF Llama-3.2-3B gate access — that's a separate
  prerequisite (see `docs/hf_gated_status.md`). Inference will still fail if gate is closed,
  but markers + auto-kill ensure the failure surfaces fast and cheap.
- `runpodctl stop pod` requires `runpodctl` to be installed and authenticated on the pod
  (FIX-3 fallback to `poweroff` when missing). On RunPod's standard images both paths
  result in pod-level shutdown that stops billing.
- Real H100 launch is **deferred** until user approval (per memory note: GPU/LLM/pod
  launch auto-approval, but this specific re-launch is gated on launcher v3 + HF gate
  re-verify).

## 7. Verdict (burn re-occurrence)

With v3:

- SSH drop after "Stage complete. Running install..." → install still runs (FIX-1).
- Install fails to launch entirely (e.g. nohup race) → pod self-kills at 30 min (FIX-3),
  capping worst-case idle at ~$1.50 (5× lower than v2's $7.52).
- Pod self-kill fails (e.g. `runpodctl` absent + `poweroff` denied) → client polling
  triggers `runpodctl stop pod` from local at 60 min (FIX-4).
- All four markers preserved for forensic timeline reconstruction (FIX-2).

The $7.52-class burn requires **all four** independent mechanisms to fail simultaneously.
