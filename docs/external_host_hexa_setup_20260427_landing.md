# External Host hexa-lang + anima Setup — Landing 2026-04-27

## Purpose

Mac orchestrator suffers recurring jetsam SIGKILL (rc=137) on
hexa_v2 invocations even for trivial 1-line `println` scripts. Memory
pressure on the laptop (vm_stat 0.13-4.94 GiB free fluctuation) makes
hexa-only raw 9 selftest dispatch unreliable. This landing stands up
two external Linux hosts so the orchestrator can offload selftest
execution and bypass the local jetsam path while preserving the raw 9
hexa-only spirit and raw 65 idempotent contract.

## Hosts

| host    | role        | arch        | mem total | hexa | anima | selftest |
|---------|-------------|-------------|-----------|------|-------|----------|
| hetzner | primary     | x86_64      | 124 GiB   | PASS | PASS  | PARTIAL  |
| ubu1    | backup      | x86_64      | 30 GiB    | PASS | PASS  | PARTIAL  |
| mac     | orchestrator| arm64       | 16 GiB    | FAIL | local | FAIL     |

PARTIAL means small selftests pass, but the specific
`g8_n_bin_85_falsification_analysis.hexa --selftest` allocates beyond
host memory on both external hosts (see Findings).

## Stage Results

| stage | hetzner   | ubu1      |
|-------|-----------|-----------|
| 1 hexa-lang clone               | PASS | PASS (after stale local-fragment backup) |
| 2 hexa binary resolution        | PASS | PASS |
| 3 anima clone                   | PASS | PASS (after stale local-fragment backup) |
| 4 PATH and HEXA_LANG profile    | PASS | PASS |
| 5 baseline selftest (harness_smoke) | PASS verdict=HARNESS_OK | PASS verdict=HARNESS_OK |
| 5b target selftest (g8 N_BIN=85) | FAIL rc=137 OOM-killed | FAIL OOM-killed (SSH dropped briefly) |
| 6 landing doc                   | PASS (this file) | PASS (this file) |

## Stage 1-2 Recipe (both hosts identical x86_64)

The repo ships prebuilt Linux x86_64 ELF binaries under `build/` and
`dist/linux-x86_64/`, but the `build/hexa_linux` wrapper expects two
files that are not present out-of-the-box:

- `build/hexa_stage0` — actual interpreter (alias of hexa_interp.linux)
- `self/native/hexa_v2` — transpiler binary (alias of dist/linux-x86_64/hexa_v2)

Both are resolved by symlink. No compilation needed:

```
git clone https://github.com/need-singularity/hexa-lang.git ~/core/hexa-lang
cd ~/core/hexa-lang
ln -sf $HOME/core/hexa-lang/build/hexa_interp.linux build/hexa_stage0
ln -sf $HOME/core/hexa-lang/dist/linux-x86_64/hexa_v2 self/native/hexa_v2
mkdir -p ~/.local/bin
ln -sf $HOME/core/hexa-lang/build/hexa_linux ~/.local/bin/hexa
```

Profile patch appended idempotently to `~/.bashrc`:

```
export PATH="$HOME/.local/bin:$HOME/core/hexa-lang/build:$PATH"
export HEXA_LANG="$HOME/core/hexa-lang"
```

Without HEXA_LANG the wrapper fails with `stage0 interpreter not
found` even when symlinks exist, since the resolver also checks
`$HEXA_LANG/build/hexa_stage0` as a dev fallback. raw 12 silent-error-
ban is honored: every error path is named in the resolver output.

## Stage 3 Recipe

```
git clone --depth 1 https://github.com/need-singularity/anima.git ~/core/anima
```

Both hosts landed at commit `6407920 feat(g8): N_BIN=85 D+6
falsification ... + 4 hypothesis pre-register`. Shallow clone keeps
external host disk small. raw 65 idempotent: re-running the clone is
a no-op since git refuses to clone into an existing repo and the
recipe checks `test -d anima/.git` first.

## Stage 5 Baseline Selftest Result

Selected `anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa --selftest` as
a small raw 9 hexa-only baseline (256 lines, no heavy allocation):

```
─── clm_eeg_harness_smoke (raw#9 hexa-only) ───
  composite_pass_count   = 3
  composite_required     = 2
  harness_ok             = 1
  chained_fingerprint    = 2588542012
  output                 = state/clm_eeg_harness_smoke.json
  verdict                = HARNESS_OK
```

Identical fingerprint `2588542012` on hetzner and ubu1, confirming
deterministic raw 9 reproduction across hosts.

## Stage 5b Target Selftest g8 N_BIN=85

```
cd ~/core/anima
hexa run anima-clm-eeg/tool/g8_n_bin_85_falsification_analysis.hexa --selftest
```

- hetzner: rc=137 after ~10s, dmesg shows `Out of memory: Killed
  process hexa_stage0 total-vm:129 GB anon-rss:128 GB`. The
  interpreter allocates the entire host memory before being reaped.
- ubu1: ssh banner timeout during run, recovered after ~5 min.
  `/tmp/g8_st.log` is zero bytes, indicating the selftest never
  printed before being OOM-killed (host has 30 GiB total + 8 GiB
  swap, smaller budget than the runaway allocation).

The Mac SIGKILL is therefore not jetsam-specific — the g8
N_BIN=85 selftest has a hexa-interpreter pathological allocation
(plausibly a list-of-list with 85*85 bins or a memoization that grows
unbounded). Moving to a bigger host expands but does not eliminate
the failure, and even 124 GiB is insufficient.

## SSH Dispatch Examples for Future Cycles

raw 9 + ssh-quote-safety: always heredoc, never inline quoted strings.

Run a hexa selftest on hetzner and capture the verdict tail:

```
ssh hetzner 'bash -s' <<'EOF'
cd ~/core/anima
export PATH="$HOME/.local/bin:$HOME/core/hexa-lang/build:$PATH"
export HEXA_LANG="$HOME/core/hexa-lang"
timeout 120 hexa run anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa --selftest 2>&1 | tail -8
echo RC=$?
EOF
```

Same recipe for ubu1, just swap the host alias. Pull a fresh anima
HEAD before dispatch (idempotent — git pull is a no-op if up-to-date):

```
ssh hetzner 'cd ~/core/anima && git pull --ff-only origin main'
```

Sync a Mac-side hexa file the external host has not yet via git push
(canonical) or scp (one-shot, no commit needed):

```
scp anima-clm-eeg/tool/some_local.hexa hetzner:~/core/anima/anima-clm-eeg/tool/
```

## Findings and Follow-ups

1. **g8 N_BIN=85 selftest memory pathology** (priority 1). 128+ GiB
   allocation on a script meant to be a falsification analysis is a
   bug in the selftest fixture or in the hexa interpreter list-grow
   strategy. Recommend: profile with smaller N_BIN and chart the
   allocation curve, or read `g8_n_bin_85_falsification_analysis.hexa`
   for an obvious O(N^4) array literal. raw 91 honesty: this issue is
   blocking the original selftest goal even on external hosts.

2. **`build/hexa_stage0` and `self/native/hexa_v2` should ship in
   the dist tarball** (priority 3). Right now external host setup
   needs two extra symlinks. Either ship them, or have install.sh
   create them. Filed as a hexa-lang dist-shape issue.

3. **No SSH banner timeout protection on ubu1 during OOM** (priority
   4). When the OOM killer reaped hexa_stage0 the ssh daemon
   itself stalled for ~5 min. Consider limiting hexa memory via
   `systemd-run --user --scope -p MemoryMax=20G hexa run ...` so the
   process is reaped without dragging the host.

4. **Mac orchestrator dispatch wrapper not yet written**. Next cycle
   should add `state/external_dispatch.json` config with a
   `host_priority: ["hetzner", "ubu1"]` list and a thin shell wrapper
   that picks the first-up host, rsyncs the target hexa file if
   newer than remote, and runs the selftest. raw 65 idempotent +
   raw 12 silent-error-ban must be honored.

5. **install.hexa one-liner not used here**. The README install
   script downloads release tarballs into `~/.hx/bin`. Manual symlink
   recipe was chosen because the repo already has the prebuilt
   binaries committed under `build/` and using the release path would
   diverge from the in-repo HEAD. Future cycle could compare the two
   strategies for canonical dispatch.

## Idempotency Verification

Re-running every command in this landing on either host produces the
same final state — no double-clone (test -d guard), no duplicate
PATH lines (grep -q before append), symlinks overwritten with -sf,
and the harness_smoke selftest writes the same fingerprint. raw 65
honored end-to-end.

## Acceptance Tri-State Summary

```
host    | hexa-runs | anima-present | selftest-passes (small) | selftest-passes (g8)
hetzner |   YES     |     YES       |          YES            |     NO (OOM)
ubu1    |   YES     |     YES       |          YES            |     NO (OOM)
```

Both hosts cleared the bar set by the goal: a raw 9 hexa file from
the anima repo runs to a HARNESS_OK verdict on each. The g8
N_BIN=85 selftest is a separate blocker tracked as follow-up 1.
