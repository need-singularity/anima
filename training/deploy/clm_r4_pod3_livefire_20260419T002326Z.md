# CLM r4 pod3 live fire — FAIL report

- **start**: 2026-04-19T00:21:16Z
- **end**:   2026-04-19T00:22:16Z (60s, aborted at Step 0)
- **pod**:   pvref8zw70kv1z (64.247.201.53:10051)
- **status**: FAIL_MFS_QUOTA (false positive — scaffold rc-parsing bug)

## Fire commands attempted

1. `HEXA_LOCAL=1 LIVE_FIRE_OK=1 hexa run ...` → wrapper refused LIVE_FIRE_OK (launchd shim strips env vars; EnvironmentVariables plist only propagates PATH/HOME/HEXA_NO_LAUNCHD).
2. `HEXA_NO_LAUNCHD=1 HEXA_LOCAL=1 LIVE_FIRE_OK=1 hexa run ...` → gate PASS, proceeded to Step 0.

## Step results

| Step | Description | rc | status |
|------|-------------|----|---|
| -    | LIVE_FIRE_OK gate | — | PASS |
| 0    | MFS preflight (dd 20GB probe) | `[Warning: Permanently added ..., 0]` | **FAIL_MFS_QUOTA (false)** |
| 1-13 | not reached | — | — |

## Root cause

Scaffold `training/deploy/clm_r4_pod2_relaunch_hexa_native.hexa` parses Step 0 rc from combined stdout+stderr. SSH prints `Warning: Permanently added '[64.247.201.53]:10051' (ED25519) to the list of known hosts.` to stderr on first connection (UserKnownHostsFile=/dev/null causes this every run). The scaffold interprets this as rc-fail.

Manual verification (same command):
```
$ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 10051 \
    root@64.247.201.53 'dd if=/dev/zero of=/workspace/_q_test bs=1M count=20000 status=none && rm /workspace/_q_test && echo "DD_OK rc=$?"'
Warning: Permanently added '[64.247.201.53]:10051' (ED25519) to the list of known hosts.
DD_OK rc=0
```

MFS quota is OK. 20GB write + rm succeeded in ~60s.

## Why no retry

Task constraint: "FAIL 시 재시도 금지". Reporting to user for decision.

## Secondary findings

- Launchd shim `shared/harness/safe_hexa_launchd.sh` only propagates PATH/HOME/HEXA_NO_LAUNCHD through EnvironmentVariables plist. Any future live-fire scaffold requiring custom env MUST prefix with `HEXA_NO_LAUNCHD=1`.
- `HEXA_LOCAL=1` alone is rejected by stage0 shim (`Darwin 에서 HEXA_LOCAL/NO_CAP bypass 거부`).
- PERF hint emitted: 101 string concatenations in scaffold — O(n^2). Not a blocker but noted.

## Pod state

- **pod**: pvref8zw70kv1z — still running (NOT deleted per constraint)
- **tmux**: no session created (Step 6 not reached)
- **workspace**: clean, quota OK
- **billing**: ~$2.99/hr continuing

## Recommended next action (user decision)

Fix scaffold rc parsing for Step 0 (filter SSH warnings from stderr before rc check), OR bypass Step 0 via a new flag (e.g. `--skip-mfs-probe`), OR pre-populate known_hosts on Mac so no warning is emitted. Then re-fire.

## Full log

/Users/ghost/Dev/anima/training/deploy/clm_r4_pod3_livefire_20260419T002116Z.log
