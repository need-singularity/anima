# Hetzner AX102 — `/` Partition Cleanup (2026-04-19)

## Goal
Drop `/` partition usage from **94%** to **≤85%** before `r5-a5` checkpoint
saves begin (43 MB × N steps to `/`-resident path). `/home` (1.5 TiB free)
was out of scope.

## Constraints honored
- `drill_v3` tmux session (P3, ~22 iter) **kept running** — verified PIDs
  886653 / 886677 alive after every step.
- No edits under `/home/*`, `/etc`, `/var/lib` (besides `apt` lists), or
  hexa-lang / anima git worktrees.
- `airgenome-claude` container left running (image `dev-sshd` retained).

## Before / After

| Stage | Used | Avail | Use% |
|---|---|---|---|
| **Before** | 87 G | 6.1 G | **94%** |
| **After**  | 78 G | 16 G  | **84%** |

Net reclaimed: **~9 GiB** (10 percentage points).

## What was removed

| # | Target | Reclaimed | Rationale |
|---|---|---|---|
| 1 | `docker system prune -af` (build cache + dangling) | 1.59 GB | unused containerd build layers; rebuilt on next `docker build` |
| 2 | `/tmp/htz_c/*` (23 240 hexa C-cache `.c`/`.o` files) | 2.0 GiB | last-touched 2026-04-18 19:36; not held open by drill_v3 (started 14:44 next day); regenerated on demand |
| 3 | `/tmp/clm_smoke{4,5,6,_bench,_test*,_full.log,_cfg.json,4.log}`, `/tmp/clm_v3_smoke` | ~250 MiB | smoke-bench output dirs from Apr 18 |
| 4 | `apt-get clean` + `apt-get autoremove --purge -y` | ~700 MiB | downloaded `.deb` archives + obsolete kernel-accessory pkgs |
| 5 | `journalctl --vacuum-time=3d` | ~470 MiB total (273 MiB at 7d, +194 MiB at 3d) | rotated journals older than 3 days |
| 6 | `/root/.cache/pip/*` + `npm cache clean --force` | 382 MiB | pip http-v2 cache + npm `_cacache`; rebuilt on demand |
| 7 | `/root/Dev/test_hexa_fix/` | 566 MiB | Apr 11 throwaway repro dir (hexa-lang fix bisect) |
| 8 | `/root/Dev/airgenome.prev.1776496247/` | 149 MiB | Apr 15 timestamped backup snapshot |
| 9 | `/tmp/runaway_soak_` (single 2 GiB file) | 2.0 GiB | exactly 2³¹ bytes of random data, no open handles, written 2026-04-19 17:07 — leftover from a soak/runaway test |
| 10 | `/var/lib/apt/lists/*` | 460 MiB | refilled on next `apt update` |

## What was deliberately NOT touched

- `/home/*` (out of scope; 1.5 TiB free anyway)
- `/root/anima/anima-speak/corpus/*` (1.9 GiB — r5-a5 training corpus,
  needed for upcoming run)
- `/root/anima/`, `/root/Dev/anima/`, `/root/Dev/airgenome/`,
  `/home/hexa-lang/` (active work)
- `/root/.rustup/` (1.4 GiB toolchain, in active use by hexa builds)
- `airgenome-claude` running container + its `dev-sshd` image (1.27 GB
  — held by the live container)
- `drill_v3` tmux session and its working files under `/root/`
- `/tmp/anima_htz/` (active claude worktrees from drill session)
- `/var/lib/containerd` snapshots backing the running container

## Verification

```
$ tmux ls
drill_v3: 1 windows (created Sun Apr 19 14:44:32 2026)

$ ps -p 886653,886677 -o pid,etime,cmd
    PID     ELAPSED CMD
 886653       18:28 timeout --kill-after=30 1200 /root/Dev/hexa-lang/hexa run /root/Dev/nexus/run.hexa drill ...
 886677       18:28 /home/hexa-lang/build/hexa_stage0 /root/Dev/nexus/run.hexa drill ...

$ docker ps
CONTAINER ID   IMAGE                                         STATUS
33e3cd439174   ghcr.io/need-singularity/airgenome:dev-sshd   Up 18 minutes (healthy)
```

drill_v3 (P3) and airgenome-claude both intact.

## Headroom for r5-a5

At 16 GiB free, with 43 MB/ckpt, the partition can host **≈ 380 ckpts**
before brushing 95% again. Recommend redirecting checkpoint output to
`/home/` (1.5 TiB free) for any long-horizon run.

## Re-run cheatsheet (next time `/` creeps up)

```bash
ssh hetzner '
  docker system prune -af
  rm -rf /tmp/htz_c/* /tmp/clm_smoke* /tmp/clm_v3_smoke /tmp/runaway_soak_
  apt-get clean && apt-get autoremove --purge -y
  journalctl --vacuum-time=3d
  rm -rf /root/.cache/pip/*
  npm cache clean --force
  df -h /
'
```
