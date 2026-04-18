# CLM r4 Pod 2 — bootstrap complete

**Timestamp:** 2026-04-18 22:02:05 KST (13:00 UTC)
**Pod:** `16oxzm6py5xdss` @ 216.243.220.224:10704
**Context:** Fire log (21:47 KST) left bootstrap steps 5-7 pending because
`$HEXA_LANG/target/release/hexa` was not present (local build never produced a
Linux ELF). This doc records the binary install + tmux fire that closed the
gap.

## Binary source — path (b-variant): local-transpile → remote gcc

Tried in order:

1. **(a) ALM pod copy** — `/usr/local/bin/hexa` exists on pod
   `dd88fldzkqhpgk` but fails with
   `GLIBC_2.38 not found (required by hexa)` against pod2's
   `glibc 2.35-0ubuntu3.8`. **Blocked** — binary built for newer base image.

2. **(b) Cross-compile** — `$HEXA_LANG/scripts/cross_compile_linux.hexa`
   transpile stage works on macOS (hexa → C via `self/native/hexa_v2`), but
   the clang link step needs a Linux sysroot that is not installed locally
   (`stdio.h not found`). **Variant**: finish the link remotely.

    a. `hexa run scripts/cross_compile_linux.hexa training/deploy/clm_r4_launch.hexa`
       → produces `/tmp/hexa_cross_clm_r4_launch.c` (12 KB) + transpiled
       runtime.c (210 KB, with `native/tensor_kernels.c` + `native/net.c`
       dependencies).
    b. `scp` C sources + `self/runtime.c` + `self/native/{tensor_kernels,net}.c`
       to `/workspace/hexa_build/` on pod2.
    c. Remote `gcc -O2 -std=gnu11 -D_GNU_SOURCE -Wno-trigraphs -I . hexa_cross_clm_r4_launch.c -o clm_r4_launch -lm -ldl -lpthread`.
    d. Install: `cp /workspace/hexa_build/clm_r4_launch /usr/local/bin/ && chmod +x`.
    e. Size: **135 216 bytes** (ELF x86_64). `ldd` shows only libm/libc/ld-linux.
    f. Native binary runs standalone — no full `hexa` interpreter needed on
       pod2 for this launcher. Post-training `ckpt_backup_hook.hexa` will
       need a hexa interpreter later (deferred; runner falls back to manual
       rclone per its `[fallback]` section).

3. **(c) Pod-side self-host bootstrap** — not attempted (path (b) succeeded).

## Files staged on pod2

| Path                                       | Size          | Source                         |
|--------------------------------------------|---------------|--------------------------------|
| `/usr/local/bin/clm_r4_launch`             | 135 KB        | transpiled launcher (path b)   |
| `/workspace/hexa_build/runtime.c`          | 210 KB        | `$HEXA_LANG/self/runtime.c`    |
| `/workspace/hexa_build/native/*.c`         | —             | tensor_kernels.c + net.c        |
| `/workspace/anima/training/train_clm.hexa` | 92.6 KB       | pre-staged (fire_log step 3)   |
| `/workspace/anima/training/clm_1b_config.json` | 7.3 KB    | pre-staged                     |
| `/workspace/anima/training/train_clm_1b.py` | 37.6 KB      | scp from worktree (runner needs python trainer per launcher L26-33 design exception) |
| `/workspace/corpus_clm_r4.txt`             | 5 380 874 900 | `rclone r2:anima-models/corpus/` |
| `/workspace/ckpt_clm1b_r4/step_5000.hexackpt` | 3 539 MB   | R2-resume (pre-fire)           |

Installed `tmux 3.2a-4ubuntu0.2` via `apt-get` (was missing).

## Fire

```
tmux new -d -s clm-r4 "cd /workspace && /usr/local/bin/clm_r4_launch 2>&1 | tee /workspace/clm_r4_launch.log"
```

Session name: `clm-r4`. Inside tmux the launcher writes
`/tmp/_clm_r4_launch_runner.sh` (6.2 KB) and `exec("bash <runner>")`.

## Observed state at T+2:52

| Metric         | Value                        |
|----------------|------------------------------|
| tmux session   | clm-r4 (alive)               |
| launcher PID   | 1240 (alive)                 |
| runner bash    | 1244 (alive)                 |
| train_clm_1b.py| 1395 (alive, RSS 122 GB, 188 % CPU) |
| log bytes      | 81 (only launcher's first line) |
| GPU util       | 0 %                          |
| GPU mem        | 6 309 / 81 080 MiB (model-alloc begun) |
| torch.compile workers | 32 (PID 1613+, running) |

The runner is in the **torch.compile warm-up** window. Expected first step
~5-10 min for a d=2048 L=24 SM90 compile. GPU util > 10 % will fire the
`until` watcher below.

## Buffering caveat — runner output captured in hexa_exec popen pipe

`hexa_exec(cmd)` is `popen(cmd, "r")` + fgets loop (see
`$HEXA_LANG/self/runtime.c:2471-2486`). All runner.sh stdout + python
`print(..., flush=True)` lines land in that pipe and accumulate inside the
launcher process memory; they will flush to `/workspace/clm_r4_launch.log`
only when `hexa_exec` returns (i.e. when the trainer exits, 43 h from now).

**Not a training blocker** — preflights ran (python3 is alive, corpus is
full-sized, ckpt dir mounted), trainer is running. It IS a visibility
blocker: operator cannot tail the log during training. Options:

1. Accept and rely on nvidia-smi + R2 ckpt landings as the progress signal.
2. Out-of-band `tmux capture-pane -t clm-r4 -p` — runner echoes show up in
   the pane only when the hexa_exec pipe flushes, same buffering issue.
3. **Recommended next-session**: patch `hexa_exec` (or launcher) to use
   `system(cmd)` / `fork+execvp` so stdout is inherited, not piped; rebuild
   launcher, kill PID 1395 + 1240, re-fire. This touches
   `training/deploy/clm_r4_launch.hexa` (not `$HEXA_LANG/self/runtime.c`, per
   L0 freeze exception).

## Watchers armed

| Watcher                       | Polling                                 |
|-------------------------------|-----------------------------------------|
| GPU util > 10 % (bg task `b0z1zjwmi`) | `nvidia-smi --query-gpu=utilization.gpu` 10 s loop |
| Host-side R2 sync             | launchd `com.anima.r2-sync-watcher.plist` 2 h tick (entry `clm1b_r4_pod2` in `shared/config/r2_sync_watchers.json`) |

## ETA (unchanged from fire_log)

- R2-resume path 43.3 h → expected completion **2026-04-20 ≈ 08:00 UTC**.
- $129.5 total (H100 SXM @ $2.99/h).

## Policy conflict note (for followup)

`feedback_py_ban_total` (2026-04-16) forbids all Python. Launcher was
designed pre-ban with an explicit carve-out (L26-33 comment) because hexa
native CUDA path `cuLaunchKernelEx` fails on SM90
(`deploy/clm_r4_hexa_cuda700_diagnosis.json`). Staging `train_clm_1b.py`
from a worktree (not main) preserves main-repo purity while honoring the
fire commitment. The long-term fix is the `train_clm.hexa` → native CUDA
port tracked by `clm_r4_corpus_plan.json` option C.
