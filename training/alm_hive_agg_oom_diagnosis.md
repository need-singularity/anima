# alm_hive_agg.hexa RUN-OOM Diagnosis (W1 Blocker)

**Date**: 2026-04-18  **Status**: DIAGNOSIS (no code changes — fix deferred)
**Audit ref**: `training/roadmap_drift_audit_20260418.md:159` (Rank 3 item 7)
**File**: `training/alm_hive_agg.hexa` (453L)
**Evidence**:
- `training/a4_live_selftest_report.md:27` — run status = RUN-OOM, T1 PASS, T2..T5 killed
- `training/a4_live_selftest_report.md:96-105` — SIGKILL details, 4 GB RSS cap
- `shared/state/a4_selftest_bugs_20260418.json:65` — files_tested entry
- `training/phi_probe_wire_report.md:22-26` — shape `[2,16,64]` hits stage0 4GB RSS cap during `hive_collec O(dsz·bsz²)`

## 1. OOM locus

The headline symptom is `safe_hexa_launchd: RSS watchdog — pid=80027 rss=4292800KB > cap=4194304KB → SIGKILL` per `training/a4_live_selftest_report.md:100`.

But alm_hive_agg.hexa has **no function named `hive_collec`** — that name appears in the phi_probe_wire library. Inside this file the OOM-critical path is:

- `build_hive()` — `training/alm_hive_agg.hexa:182-250`
  - builds a flat `time_major` list of length `N_agents * N_steps * d`
  - **per-step loops (`:216-229`) each do `time_major.push(nv)` and `new_prev.push(nv)`**
  - then transposes to `agent_major` via more pushes (`:234-248`)
- `cross_agent_mi()` — `:321-343`
  - nested `dim × agent_a × agent_b > a` = `d * N * (N-1) / 2` outer iterations
  - each iteration calls `extract_agent_dim` twice (`:310-319`) which **`out.push()` builds a fresh T-length array per call**
  - plus `mutual_info_h → entropy_h → count_hits_h` which pushes `n_bins` counts per call (`:101-115`)

The paper-napkin counts at live-run shape `N=8, T=24, d=6`:

| step | push count | array len each |
|------|-----------|----------------|
| build_hive time_major | `N*T*d = 1152` pushes | grows to 1152 |
| build_hive agent_major | `N*T*d = 1152` pushes | grows to 1152 |
| extract_agent_dim calls | `d * N * (N-1)/2 * 2 = 336` array allocations | len=24 each |
| joint_entropy bin_ids | 336 × 24 = 8064 pushes | |
| count_hits_h | 336 × 36 = 12096 pushes | |

Numbers alone are modest. The ceiling is not count but **pass-by-value + push-rebuild**: per `shared/state/a4_selftest_bugs_20260418.json:45` ("Pass-by-value array semantics + tree-walk interpreter"), each `.push()` re-copies the list. `build_hive` in particular pushes into `time_major` while `time_major` already holds ~1000 items, so each push is an O(n) copy; cumulative = O(n²). For n=1152 that is ~1.3 M-element churn; when run twice via the A4-B4 double-main quirk (`shared/state/a4_selftest_bugs_20260418.json:37-43`) and compounded across T2..T5 determinism/latency/edge/emergence runs, the resident set exceeds the 4 GB `safe_hexa_launchd` cap.

## 2. O(dsz·bsz²) allocation pattern

The `phi_probe_wire_report.md:23` note tags the pattern
`hive_collec O(dsz·bsz²) alloc-per-push`. In alm_hive_agg terms:

- `dsz` ≡ `d` (per-dim)
- `bsz` ≡ `N_agents` (pair count goes as N·(N-1)/2)
- the scratch `time_major` accumulates `N*T*d` items via O(len) push-rebuild, so **cumulative push cost ≈ O((N·T·d)²)**
- for `[B=2, T=16, d=64]` shape (phi_probe mini-target) this is (2·16·64)² = 4.2 M ≈ threshold
- for `[2, 16, 64]` the report-quoted target, it crosses the 4 GB cap

In this file, the same pattern is replicated at `:192-248` (build_hive) and at `:310-343` (per-pair extract + entropy).

## 3. Fix options (effort-sorted)

### (a) Mini-test config — zero code change

Drop `HV_N / HV_T / HV_D` at `training/alm_hive_agg.hexa:33-37` for
self-test purposes: e.g. `N=4, T=12, d=4` (= 192 items, well below the
(N·T·d)² ceiling).  Keeps the O(N²) pair loop at 6 pairs × 4 dims = 24,
trivially affordable.

- **Effort**: 1 LOC change (or a CLI flag).
- **Risk**: T5 emergence_ratio may drop; needs re-calibration of the
  `> 1.0` threshold at `:411` (may need `> 0.6` at smaller N due to
  weaker coupling signal).
- **Blocks lifted**: T2..T5 can run, W1 bucket promotes.

### (b) Pre-allocated reusable buffer — medium effort

Replace the growing `time_major = time_major.push(...)` pattern in
`build_hive` (`:191-232`) with a fixed-length list allocated once via a
helper like `fill_zeros_h(N*n_steps*d)` (pattern already used in
`alm_finitude_head.hexa:100` — `out.push(0.0)` at init length). Then use
index-assignment (`time_major[idx] = nv`) per the A4-B1 fix pattern
(`shared/state/a4_selftest_bugs_20260418.json:15` — `arr[i] = v` is the
correct path). Same for `new_prev` (`:225`) and `agent_major` (`:234`).
`extract_agent_dim` (`:310-319`) can accept a reusable buffer param.

- **Effort**: ~30 LOC across build_hive + extract_agent_dim.
- **Risk**: ensure stage0 interpreter supports index assignment on
  lists of size N*T*d (it does per A4-B1 fix evidence
  `a4_live_selftest_report.md:41-49`).
- **Blocks lifted**: single-run passes at full `[8,24,6]`; double-main
  quirk may still OOM — combine with (a) or fix A4-B4 wrapper.

### (c) Streaming / mean-accumulate redesign — highest effort

Eliminate `time_major` entirely. Maintain only `prev_step` (length N*d)
across the T-loop and compute statistics online:

- `phi_individual(agent)` becomes Welford-style running autocorrelation
  (pair of current/prev stat accumulators) — no per-step state stored.
- `phi_collective` becomes pairwise MI over online histograms; the
  `entropy_h / joint_entropy_h` estimators (`:117-158`) accept a
  streaming interface: push a single (a,b) sample per t, update count
  buckets in-place.
- `extract_agent_dim` disappears — replaced by direct indexing into the
  current step buffer.

- **Effort**: ~150 LOC rewrite of build_hive + the two entropy
  estimators + all tests.
- **Risk**: determinism T2 (`:362-375`) becomes sensitive to floating
  accumulation order; verify byte-identical across runs with fixed
  pair-iteration order.
- **Blocks lifted**: memory becomes O(N*d + n_bins²) constant, independent
  of T. Native-build path no longer needed just for live-selftest.

## 4. Ceiling quote

Per `training/phi_probe_wire_report.md:24`:
> Target `[2,16,64]` hits stage0 4GB RSS cap during hive_collec O(dsz·bsz²) — wire is correct; alloc-per-push is the bottleneck.

Confirms: **not a logic bug, an allocator-pattern bug**. Fix (a) unblocks
self-test today; fix (b) or (c) unblocks full-shape live-verify.

## 5. Sibling-file scan — same pattern?

Push-rebuild count per sibling (`grep "out.push\|\.push(" -c`):

| file | .push count | large scratch? | risk |
|------|------------|----------------|------|
| `training/alm_nested_loss.hexa` | 8 | low (small towers) | LOW |
| `training/alm_finitude_head.hexa` | 31 | medium (weight matrices built via push) | MEDIUM — inspect if shape > [8,24] |
| `training/alm_dream_loop.hexa` | 8 | low (cycle counters) | LOW |
| `training/alm_replay.hexa` | 17 | medium (FIFO buffer rebuild) | MEDIUM — T3 latency 2000 ms suggests O(n²) churn at consolidate(100) per `a4_live_selftest_report.md:89` |
| `training/alm_hive_agg.hexa` | 14 | **HIGH (N*T*d time_major + per-pair extract)** | CONFIRMED OOM |

### Flagged for follow-up
- `alm_replay.hexa` T3 latency (`a4_live_selftest_report.md:89`:
  `consolidate(100) in 2000 ms (limit 50 ms)`) is the same pattern —
  push-rebuild into FIFO at size 100 = O(100²) = 10k copies. Not yet OOM
  but structurally identical.
- `alm_finitude_head.hexa` weight matrices built via push (`:214-236`) —
  safe at current size but will scale as O(d²) if d grows past 64.
- `alm_nested_loss.hexa` and `alm_dream_loop.hexa` are within the safe
  envelope.

## 6. Recommended next step (no code modification in this pass)

1. Adopt fix **(a) mini-test config** for W1 promotion bookkeeping (same
   fix path used by `phi_probe_wire_test.hexa` at `[2,4,16]`).
2. File fix **(b) pre-allocated buffer** as a proper task under the
   phi_hook_wire track; blocks full-shape native equivalence until
   interpreter path matches.
3. Defer fix **(c) streaming** until native-build path decision is made
   (per `a4_live_selftest_report.md:103-105`: "interpreter memory is
   not fundamentally broken — it's a list-churn ceiling that disappears
   under native build").
