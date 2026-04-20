# H100 / Hetzner Remote GPU Status Snapshot — 2026-04-21

- Probe time (UTC): 2026-04-20T16:56:04Z
- Probe host: Mac (darwin 24.6.0), ghost
- Method: read-only SSH `nvidia-smi` probes (ConnectTimeout=5, BatchMode=yes). No destructive ops.
- Context: roadmap 6 blocked on "CLM r6 hetzner smoke completion"; HEXA_REMOTE=1 requires NVIDIA remote target.

## Tool output

### airgenome doctor / airgenome status
- Both commands **hung past 30s with zero stdout** (EXIT=124 on timeout). These commands invoke `cmd_doctor` in `/Users/ghost/Dev/airgenome/run.hexa` which checks local hexa/core/launchd/ring/throttle — not remote GPU topology. Skipped in favor of direct SSH probes.

### nx status
- `nx status` → `⬡ nx type=app 프로젝트` (project marker only, no host data).

### SSH config candidates (from `~/.ssh/config`)
| alias | host | user | port |
|---|---|---|---|
| ubu, ubu1 | 192.168.50.119 | aiden | 22 |
| ubu-ts | 100.96.193.56 (tailscale) | aiden | 22 |
| ubu-d, ubu1-d | 192.168.50.119 | — | 2222 |
| ubu2, ubu2-relay | 192.168.50.60 | summer | 22 |
| ubu2-d | 192.168.50.60 | — | 2222 |
| hetzner, htz, htz1 | 157.180.8.154 | root | 22 |
| htz-d | 157.180.8.154 | — | 2222 |

## Per-host health

| host | address | online | gpu_model | util | mem | last_error |
|---|---|---|---|---|---|---|
| ubu (ubu1) | 192.168.50.119:22 | ❌ | n/a | — | — | `Connection timed out during banner exchange`. ubu-d:2222 also refused. Matches known blocker: ubu RTX 5070 SSH offline. |
| ubu-ts | 100.96.193.56:22 | ❌ | n/a | — | — | `ssh: connect ... Operation timed out` (tailscale path to ubu also down). |
| ubu2 (ubu2-relay) | 192.168.50.60:22 | ✅ | **NVIDIA RTX 5070 (10de:2f04) hardware present, driver NOT installed** | — | — | `nvidia-smi: command not found`. `ubuntu-drivers devices` recommends `nvidia-driver-580`. Kernel 6.17.0-20-generic. |
| hetzner (htz, htz1) | 157.180.8.154:22 | ✅ | **none — AMD Raphael iGPU only (CPU-only box)** | — | — | `nvidia-smi: command not found`. `lspci` shows zero NVIDIA devices. Hostname `anima-ax102` → Hetzner AX102 = CPU server, not GPU. |
| htz-d | 157.180.8.154:2222 | ✅ | none (same host as hetzner) | — | — | Same hardware as htz. |

Online: 3 / Offline: 2 (both ubu paths).

## Verdict

- **H100 available: NO.** None of the probed hosts carry an H100 (or any discrete NVIDIA on the Hetzner side). The Hetzner AX102 at 157.180.8.154 is a CPU-only AMD Raphael box — it is **not** an H100 node despite the roadmap phrase "CLM r6 hetzner smoke."
- **Any NVIDIA usable: NO.** ubu (RTX 5070) remains SSH-offline; ubu2 (RTX 5070) is online but `nvidia-smi`/driver missing.
- **CLM r6 blocker resolvable right now: NO.** HEXA_REMOTE=1 dispatch has no working CUDA target.

## Unblock paths (ranked by effort)

1. **Path A — fastest, no H100 needed.** Install `nvidia-driver-580` on **ubu2** (reachable, has RTX 5070 hw, same silicon class as the originally-planned ubu). Lets CLM r6 smoke run on a 5070 instead of stalling on H100 provisioning. Single apt command (out of scope for this read-only drill).
2. **Path B — restore ubu.** ubu at 192.168.50.119 is unreachable on both :22 and :2222, and tailscale route 100.96.193.56 is also timing out, implying the host is down or network-isolated. Likely needs physical / console access.
3. **Path C — provision an actual H100.** Current Hetzner box is AX102 (CPU). A real H100 smoke requires either a Hetzner GPU offering (GEX44 / GPU cloud) or RunPod/Lambda. This is the only path that literally delivers "H100" as the roadmap wording suggests.

## Artifacts

- Machine-readable: `/Users/ghost/core/anima/shared/state/h100_remote_probe.json`
- This report: `/Users/ghost/core/anima/docs/h100_remote_status_20260421.md`
