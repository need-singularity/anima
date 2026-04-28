# GPU Launcher Audit — v3 Hardening Cross-Pollination

frozen: 2026-04-26
session: anima ω-cycle (post Pilot-T1 v3 launcher hardening)
reference: `anima-tribev2-pilot/scripts/launch_h100_pilot_t1_v3.sh.txt` (4-fix)
mode: audit-only (read-only on all launcher files), $0, mac, GPU 0

## 0. v3 hardening pattern (reference, 4 fix)

| ID    | Fix                              | Mechanism (one-line)                                                                                       |
|-------|----------------------------------|------------------------------------------------------------------------------------------------------------|
| FIX-1 | server-side daemonize            | install + inference launched via `nohup ... &` + `disown`; SSH drop decoupled from workload survival       |
| FIX-2 | heartbeat markers                | pod writes `install_started.marker` / `install_done.marker` / `inference_*.marker` (ts + pid + rc)         |
| FIX-3 | idle auto-kill (pod-side)        | `watchdog.sh` self-terminates pod via `runpodctl stop pod` (fallback `poweroff`) if no marker after threshold |
| FIX-4 | client-side polling fail-fast    | client polls markers via short-lived SSH probes every 30 s; distinct fail-fast budgets per phase           |

Burn evidence triggering v3: Pilot-T1 v2 `$7.52` SSH-drop idle burn (15× cap breach).

## 1. Audit scope (file list)

11 launchers identified across 3 categories; all read-only inspected:

### A. anima-tribev2-pilot (pilot suite)
1. `anima-tribev2-pilot/scripts/launch_h100_pilot_t1_v3.sh.txt` — **REFERENCE (already 4/4)**
2. `anima-tribev2-pilot/state/launch_h100_pilot_t1.sh.txt` — pre-v3 victim of $7.52 burn

### B. tool/h100_*.bash (Stage-2 stack)
3. `tool/h100_stage2_unified_launch.bash` — 4-pod parallel Phi 4-path launcher
4. `tool/h100_stage2_post_launch_chain.bash` — bootstrap + driver ship + nohup kickoff (4 pod fan-out)
5. `tool/h100_pod_resume.bash` — R2 ckpt resume helper (single-pod boot path)
6. `tool/h100_r7_single_path_retrain.bash` — r7 single-path retrain (mirrors stage2 pattern)
7. `tool/h100_pods_sync.bash` — config writer (no SSH workload — out of audit scope, listed for completeness)

### C. CP serving launchers
8. `tool/cp1_serve_launch.bash` — CP1 H100 secureCloud spawn
9. `tool/cp1_serve_launch_mac.bash` — CP1 Mac local (out of audit scope: launchd, not SSH)
10. `tool/cp2_serve_launch_mac.bash` — CP2 Mac local (out of audit scope: launchd)

### D. hexa orchestrators
11. `tool/anima_runpod_orchestrator.hexa` — generic create→ssh→exec→download→terminate wrapper (used by `act_patch_pilot`)
12. `tool/mk_xi_launch_pod.hexa` — Mk.XI launcher (proposal-only / dry-run)
13. `training/deploy/clm_r4_pod2_launch.hexa` — CLM r4 pod launcher (selftest-only wrapper)

7 launchers in audit perimeter (workload kickoff + SSH/runpodctl coupled): #2, #3, #4, #5, #6, #8, #11.

## 2. Per-launcher analysis (4-axis criterion)

Axes:
- **A** = SSH liveness ↔ workload coupled? (FIX-1 absence)
- **B** = heartbeat markers absent? (FIX-2 absence)
- **C** = idle auto-kill absent? (FIX-3 absence)
- **D** = client-side polling absent? (FIX-4 absence)

Y = vulnerability present, N = mitigated, n/a = scope-irrelevant.

| # | Launcher                                          | A | B | C | D | $/hr (max)         | typical risk window |
|---|---------------------------------------------------|---|---|---|---|--------------------|---------------------|
| 2 | `state/launch_h100_pilot_t1.sh.txt`               | Y | Y | Y | Y | $2.99              | hours (proven $7.52)|
| 3 | `tool/h100_stage2_unified_launch.bash`            | n/a (spawn-only; chains to #4) | n/a | partial via h100_auto_kill registry | n/a | n/a per-pod | spawn handoff       |
| 4 | `tool/h100_stage2_post_launch_chain.bash`         | **N (uses nohup)** | Y | partial (auto_kill ext.) | Y | $11.96 (4 × H100 × 4 GPU) | hours              |
| 5 | `tool/h100_pod_resume.bash`                       | n/a (rclone download, not workload) | n/a | n/a | n/a | n/a               | n/a                 |
| 6 | `tool/h100_r7_single_path_retrain.bash`           | likely Y (mirrors stage2 — needs deep read) | likely Y | likely partial | likely Y | $11.96 (4 GPU)    | hours               |
| 8 | `tool/cp1_serve_launch.bash`                      | n/a (spawn-only — bootstrap manual per docs §Deploy recipe) | Y (no health-marker post-spawn) | **N (auto_kill DISABLED — persistent)** | Y | $4.00              | indefinite          |
|11 | `tool/anima_runpod_orchestrator.hexa`             | Y (`subprocess.run(ssh, ..., timeout=int)` — fg) | Y | Y (only `--max-runtime-min` in caller, no pod-side watchdog) | Y (single SSH timeout, no marker poll) | $2.99 (default)    | timeout cap         |

Notes:
- #4 **partial credit FIX-1**: training kicked off via `nohup python3 ... &` (line 322) — daemonized.
  Bootstrap (line 195) and driver ship (line 305) are **foreground SSH** with `wait` barrier — vulnerable
  to mid-bootstrap SSH drop (3-5 min apt install window). Stage-1 abort cleanup `_cleanup_abort_pods`
  exists but only fires on `wait` non-zero; SSH disconnect mid-fg-cmd may leave $11.96/hr pods orphaned
  if the abort signal can't propagate.
- #11 (orchestrator): `subprocess.run(['ssh', ..., command], ..., timeout=600)` — full foreground.
  Has explicit `--max-runtime-min` cap and `auto_terminate=True` default, but if SSH drops mid-`run` the
  Python wrapper sees `subprocess.TimeoutExpired` only at `max_runtime_min` boundary. Heartbeat absent.
  `act_patch_pilot` run (state/runpod_run_act_patch_pilot.json, $0.195/3.92 min) succeeded because
  command was short — not because launcher is hardened.
- #8 (CP1): spawn-only; doc-driven manual bootstrap. Once live, **auto_kill explicitly DISABLED**
  (`IDLE_KILL_MIN=0`, comment `persistent, auto_kill DISABLED`) — by design for serve, but means
  any post-CP1-completion idle burns at $4/hr until manual stop. No serve-process health marker.

## 3. v3 hardening priority (HIGH / MEDIUM / LOW based on $/hr × risk window)

Risk score = `$/hr × P(SSH-drop or idle) × E[idle hours until detection]`.

### HIGH (must port v3 4-fix)
- **#4 `h100_stage2_post_launch_chain.bash`** — $11.96/hr, 4-pod fan-out. Has `nohup` for training (FIX-1
  partial) but FIX-2/3/4 absent. Bootstrap fg phase + driver ship phase are SSH-coupled (5-10 min window
  per pod × 4 pods). Burn potential per dropped pod: $11.96/hr × 24 h = $287. **Top candidate.**
- **#6 `h100_r7_single_path_retrain.bash`** — same $/hr profile, mirrors #4 pattern. Adds sequential
  single-path so blast radius lower (1 pod) but $/run still 4 × H100. Likely inherits #4's gaps.
  **Top candidate (sister of #4).**

### MEDIUM
- **#11 `anima_runpod_orchestrator.hexa`** — generic wrapper, $2.99/hr default, used as fan-out template.
  Has `auto_terminate=True` + `max_runtime_min` cap (built-in idle bound), but no FIX-2/4. Worst case:
  silent SSH drop → $2.99 × 120 min cap = $5.98 burn. **Cross-pollinate FIX-2 (heartbeat) + FIX-4 (poll)
  to make existing runtime cap meaningful (currently it just kills on timeout regardless of progress).**
- **#2 `state/launch_h100_pilot_t1.sh.txt`** — already proven-bad ($7.52 burn). Mark deprecated; v3
  supersedes. No port needed; just gitignore-rename to `.deprecated.sh.txt` (audit recommends).

### LOW
- **#3 `h100_stage2_unified_launch.bash`** — spawn-only, hands off to #4 immediately. Most failure modes
  already handled: pre-flight 7-check, auto_kill registry sync, AUTO_KICKOFF chain. Risk lives downstream
  in #4 (handoff target). No direct port; only ensure handoff to a v3-hardened #4.
- **#8 `cp1_serve_launch.bash`** — different profile (persistent serve, not transient training).
  v3 markers don't fit serve semantics directly. Recommend a serve-specific variant: `health_ok.marker`
  (post-spawn) + `serve_alive.marker` (heartbeat every N min) + client-side `MAX_IDLE_BEFORE_KILL` for
  the post-CP1-decommission window. Not the same 4-fix port.

### OUT-OF-SCOPE
- **#5 `h100_pod_resume.bash`** — rclone-only, no workload SSH coupling.
- **#7 `h100_pods_sync.bash`** — config writer.
- **#9, #10 (Mac local cp1/cp2)** — launchd, not SSH.
- **#12, #13** — proposal-only / selftest-only.

## 4. Cross-pollination plan (wallclock estimates, audit-only)

| target                                          | priority | port effort                                                                                          | wallclock |
|-------------------------------------------------|----------|------------------------------------------------------------------------------------------------------|-----------|
| #4 `h100_stage2_post_launch_chain.bash`         | HIGH     | wrap fg bootstrap (line 195) + driver ship (line 305) in nohup pattern; emit 4 markers per pod; parallel polling loop | 90-120 min |
| #6 `h100_r7_single_path_retrain.bash`           | HIGH     | inherit #4 helpers once landed (DRY: shared `_v3_hardening.lib.bash`)                                | 30-45 min |
| #11 `anima_runpod_orchestrator.hexa`            | MEDIUM   | add `--heartbeat-interval` + `--marker-dir` flags; pod-side wrap command in nohup+marker             | 60-90 min |
| #8 `cp1_serve_launch.bash`                      | MEDIUM   | serve-specific health-marker variant (NOT pure 4-fix port — different semantics)                     | 60-90 min |
| #2 `state/launch_h100_pilot_t1.sh.txt`          | DOC-ONLY | rename to `.deprecated.sh.txt` + add header note pointing to v3                                      | 5 min     |

Recommended order: 1) factor v3 fixes into a shared `tool/lib/v3_pod_hardening.bash` (~30 min);
2) port #4 first (highest blast radius); 3) inherit into #6; 4) port #11; 5) bespoke #8.

Total cross-pollination wallclock budget: **~5 h** for HIGH+MEDIUM ports + library factoring.

## 5. raw#10 honest limitations

- **Static analysis only**: launcher behavior under live SSH-drop has been observationally confirmed only
  for #2 ($7.52 burn) and #4 (round-3 abort `~$48/hr` incident, in-script comment line 102). All other
  launcher risk scores are derived from pattern-match, not run history.
- **#6 unread in detail**: only header (80 lines) read; FIX presence/absence inferred from "mirrors #4
  pattern" comment. Real verification would require full read or controlled SSH-drop test.
- **False positive risk**: #11's `auto_terminate=True` + `max_runtime_min` defaults provide a *partial*
  safety net even without FIX-3. Burn is bounded by `max_runtime_min × $/hr` even on total SSH loss,
  which for the default 120 min × $2.99 = $5.98 — acceptable. Calling it MEDIUM rather than LOW is
  conservative; arguably it could drop to LOW.
- **#3 spawn-only N rating depends on handoff**: if #4 hardens but #3's AUTO_KICKOFF chain has a window
  between pod spawn and #4 invocation where pod is RUNNING but no driver yet, that gap is *not* covered
  by #4's markers. Worst case ~30-60 s, $0.05 burn per pod — negligible.
- **Audit excludes runtime-pull paths**: `tool/h100_stage2_adapter_pull.bash` runs as background daemon
  (post-training) and has its own kill semantics; not analyzed here. Recommend follow-up cycle.
- **`act_patch_pilot` n=1 success bias**: orchestrator (#11) ran clean once (3.92 min, $0.195) — not
  evidence of robustness, just absence of failure in a short window.

## 6. Audit summary

- launchers in perimeter: **7**
- HIGH risk (pre-port): **2** (#4, #6)
- MEDIUM risk: **2** (#11, #8 — different fix-shape for #8)
- LOW risk: **2** (#3, #2)
- already 4/4 hardened: **1** (#1, the v3 reference)
- top-3 cross-pollination targets: **#4, #6, #11**
- next cycle wallclock estimate: **~5 h** total (#4 first; library extraction + 4 ports)

## Appendix — v3 reference details

Reference v3 marker contract:
```
install_started.marker   started_at=<ISO> pid=<int>
install_done.marker      done_at=<ISO> rc=<int>
inference_started.marker started_at=<ISO> pid=<int>
inference_done.marker    done_at=<ISO> rc=<int>
watchdog_kill.marker     reason + elapsed + threshold
```

Default knobs:
- `IDLE_KILL_SEC=1800` (pod-side; bounds idle burn ≤ ~$1.50 at $2.99/hr)
- `CLIENT_FAIL_FAST_SEC=3600` (client-side install_started budget)
- `POLL_INTERVAL_SEC=30`
- `INFER_BUDGET=INFER_CAP+120` (inference_done grace)
