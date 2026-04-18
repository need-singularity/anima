# htz Compile Farm — 2026-04-19

Remote Hetzner dedicated (AX102) repurposed as 3rd hexa_v2 transpile + C-compile farm.
Larger CPU axis than ubu2 (32t vs 12t), parallel cross-check rail.

## Host spec

| Field | Value |
|-------|-------|
| SSH alias | `hetzner` |
| Hostname | `anima-ax102` |
| IP | `157.180.8.154` |
| User | `root` |
| OS | Ubuntu, Linux 6.8.0-100-generic |
| CPU | AMD Ryzen 9 7950X3D (16-core / 32-thread, x86_64) |
| RAM | 124 GiB (69 GiB free idle) |
| Disk | `/` 98 GiB (84% used, 16 GiB free), `/home` 1.7 TiB (6% used, 1.5 TiB free) |
| GPU | none |
| Toolchain | gcc + clang (both present) |
| Baseline load | 11-19 (other workloads running, 36-60% CPU busy) |

## Deployed artifacts

- `~/hexa-lang/` — full clone of github.com/need-singularity/hexa-lang (main)
- `~/hexa-lang/build/hexa_v2_linux` — pre-built sister binary (1.5 MB, ELF x86_64)
- `/tmp/hexa_v2_linux` — runtime copy, executable
- `/tmp/htz_smoke.sh` — per-file transpile + `clang -I~/hexa-lang/self -c` wrapper
- `/tmp/anima_htz/` — rsync'd anima .hexa tree (12,983 files, ~50 MB)
- `/tmp/htz_c/` — generated `.c` + `.o` outputs
- `/tmp/htz_smoke_full.tsv` — full smoke TSV

## Role

| Capability | Status |
|------------|--------|
| hexa_v2 transpile (`.hexa` → `.c`) | YES |
| C compile (clang `-c`) → `.o` | YES |
| Full link → runnable binary | PARTIAL (runtime externs must be wired) |
| Training / inference | NO (no GPU) |
| Parallel batch smoke compile | YES (8-way nice'd, headroom for 16-24 if host idles) |

Primary role: **large-tree batch smoke** (whole-repo transpile + compile sweep).
Complements ubu2 (smaller, LAN-local, faster single-file turnaround).

## Smoke test — full anima tree (2026-04-19)

- **12,983** `.hexa` files (including `.claude/worktrees/` agent dupes)
- 8-way parallel, `nice -n 19`, elapsed **801s (13.4 min)**
- Peak load during run: 19.80 on 32t (~62% busy) — other workloads uninterrupted

| Result | Count | % |
|--------|-------|---|
| PASS | 10,283 | 79.2 % |
| FAIL_C (clang error) | 2,674 | 20.6 % |
| FAIL_T (transpile error) | 26 | 0.2 % |

**Non-worktree (unique source) stats** (2,545 files):

| Result | Count | % |
|--------|-------|---|
| PASS | 2,094 | 82.3 % |
| FAIL_C | 446 | 17.5 % |
| FAIL_T | 5 | 0.2 % |

FAIL_T cluster: `experiments/consciousness/zombie_engine.hexa`, `consciousness_pci.hexa`, `anima-core/verification/cvf.hexa` — genuine transpile bugs to escalate.

FAIL_C pattern: undeclared externs (`quantum_controller_*`, `phi_cache_*`, CUDA hooks) — same as ubu2 `train_clm` fail, expected for bare smoke without full native-lib link.

## ubu2 cross-check

ubu2 full-tree TSV does not exist yet (only 4-file representative run documented).
htz is the first host with a full **12,983-file sweep baseline**.

Next action: run same `xargs -P 12` sweep on ubu2 with identical include path, diff PASS/FAIL sets → any per-host delta = env-specific bug.

## Usage pattern

```
# Mac: stage anima tree
rsync -az --include='*.hexa' --include='*/' --exclude='*' \
  /Users/ghost/Dev/anima/ hetzner:/tmp/anima_htz/

# htz: 8-way nice'd batch
ssh hetzner 'cd /tmp/anima_htz && find . -name "*.hexa" -type f | \
  nice -n 19 xargs -n 1 -P 8 -I{} /tmp/htz_smoke.sh "{}" > /tmp/htz_smoke_full.tsv'

# Mac: pull results
scp hetzner:/tmp/htz_smoke_full.tsv /tmp/htz_smoke_full.tsv
```

## Constraints

- `/tmp/` only (root `/` at 84% — no `/home` writes unless we move artifacts there)
- Other workloads live (baseline load 11); cap parallelism at 8, always `nice -n 19`
- `.py` banned per R37 / AN13 / L3-PY (pure hexa_v2 + clang toolchain)
- Do not commit smoke TSVs (transient `/tmp/` artifacts)

## 3-host farm allocation proposal

| Host | Cores | Role | Best for |
|------|-------|------|----------|
| **Mac** (ghost) | 10 (M1 Max) | interactive edit, log-watch, single-file smoke | dev loop, `hexa run` local test |
| **ubu2** (LAN) | 12t | LAN-local worker, fast single-file compile | per-edit smoke, hot-path rebuild |
| **htz** (remote) | 32t | whole-tree batch sweep, CI-style smoke, cross-check | `smoke_all`, multi-100 file sweeps |

Dispatch heuristic:
- N ≤ 10 files → Mac local
- 10 < N ≤ 200 → ubu2 (LAN RTT wins)
- N > 200 or full tree → htz (core count wins, 13 min for full anima)

## Future

- register htz in `shared/config/infrastructure.json` (same record shape as ubu2)
- `hexa shared/harness/compile_farm.hexa` dispatcher with host-selection by N
- sync `self/runtime.c` + `native/*.c` as static lib on both ubu2 + htz → enable full-link smoke
- weekly `htz_smoke_full` cron → PASS % regression watch
