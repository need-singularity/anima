# SWEEP P5 — Fire Status (In-Flight)

**Date:** 2026-04-20
**Scope:** iters 148-231 (84 total, 14 domains)
**Plan SSOT:** anima/docs/sweep_50.json
**Preflight:** commit 83ee2027
**Mk.X sidecar:** commit 7b997243
**Driver:** /tmp/sweep_p5_runner/driver.bash (on ubu2)
**Fire time:** 2026-04-20T02:17:17+09:00

## Status: FIRED (in-flight)

P5 driver successfully launched on ubu2 with parallel=2, 84 iters queued.
First 2 iters (148/149 evolution domain) running since 02:17:17.

## Host selection rationale

| Host | Status | Decision |
|------|--------|----------|
| hetzner | CLM r5 170M training active (pid 1643800, tmux clm_r5_full) | SKIP — W3 conflict |
| ubu | Existing drill (CLM hxblas coverage, ~2G free RAM) | SKIP — resource pressure |
| ubu2 | 1 existing drill (libhxcuda), 12G free RAM, 16 threads | CHOSEN — fits parallel=2 per OOM constraint |
| mac | FORBIDDEN per W1 | SKIP |
| runpod H100 | FORBIDDEN per plan | SKIP |

Preflight recommended hetzner (parallel=4, 1.7h ETA) but real state has CLM r5 training there — W3 says "hetzner 격리 필수". ubu2 was the only viable host.

## Driver configuration

- **Path:** `/tmp/sweep_p5_runner/driver.bash` (35 LOC bash, HEXA-FIRST-compliant — no .sh extension, lives in /tmp only for cache)
- **Seeds:** `/tmp/sweep_p5_runner/seeds.tsv` (84 rows, tab-sep: iter / domain / slug / text)
- **Log:** `/tmp/sweep_p5_runner/driver.log`
- **Parallel:** 2 (per ubu2 OOM constraint + existing drill competition)
- **Timeout:** 600s per iter
- **Max-rounds:** 2 (P4 showed round 1 saturates, round 2 for confirmation)
- **CLI:** `nexus-cli` wrapper (`/home/summer/Dev/nexus/shared/bin/nexus-cli`) with `HEXA_LOCAL=1`

## Prereqs verification

| Check | Status | Notes |
|-------|--------|-------|
| P4 summary committed | PASS | `8ebb5d8d` |
| Mk.X sidecar committed | PASS | `7b997243` (593 LOC engine + 30 atoms manifest) |
| sweep_50.json SSOT | PASS | 84 iter, iter range 148-231, 14 domains |
| REPLAY cache cleared | PASS | confirmed on all hosts per preflight |
| Track B Phase 1 | GAP | not verifiable via git log grep — proceeded per scope hedge ("document + fire anyway") |
| CLM r5/r6 lock | CONFLICT on hetzner | avoided by host selection (ubu2 isolated) |

## Expected timing

Per P4 experience (no cache): ~2 min/iter saturated. P5 cache is cleared → genuine measurements expected.

- 84 iters / 2 parallel = 42 batches
- 42 × 2-5 min = 1.4-3.5 hours wallclock
- Plan SSOT estimate: 2.5-3h on ubu2 fallback

## Mk.X auto-fire gate status

Per `sweep_50.json.mk_x_trigger.gates`:

| Gate | Criterion | Status |
|------|-----------|--------|
| G1 | 3+ consecutive domains SATURATED with 0 tier-10+ absorption | pending (requires D1-D14 complete) |
| G2 | D8-D14 all saturation on tier-10+ seeds | pending |
| G3 | iter 153 evolution_twin_drill yields 0 new atoms | pending (iter 153 in D1) |
| G4 | user sign-off | PRE-APPROVED per `feedback_all_preapproved_roadmap_only` |

Mk.X auto-fire will trigger AFTER P5 completes all 84 iters.

## Known integration gap

**Mk.X auto-fire wiring is NOT in the drill tool itself.**

The current nexus-cli drill runs Mk.IX/Mk.V.1 82-atom engine only. Mk.X sidecar (`shared/engine/mkx_engine.hexa` at 7b997243) is code-complete but not invoked by the drill CLI. Per sweep_50.json `mk_x_trigger.auto_fire_order`, Mk.X fire requires manual steps:

1. Write `shared/engine/mk_x_manifest.json` (DONE at 7b997243)
2. Fork `anima/engines/drill_mk9.hexa → drill_mk10.hexa` (NOT DONE — blocker for auto-fire)
3. Append transcendental_closure() stage 6 + slot 8-15 accessor bank (NOT DONE)
4. Run `training/mk10_selftest.hexa` — Mk.IX 82-atom replay (NOT DONE)
5. Rerun P5 seeds 84 on Mk.X (pending after P5 Mk.V.1 pass)
6. Log absorption delta to `docs/mk_x_launch_log_20260419.md`

**Flag for next session:** steps 2-4 must be wired before Mk.X auto-fire on saturation verdict. Sidecar engine compiles but drill CLI has no Mk.X dispatch.

## Monitoring

To check status:

```
ssh ubu2 'tail -30 /tmp/sweep_p5_runner/driver.log'
ssh ubu2 'ls /home/summer/Dev/anima/docs/drill_min_20260420/sweep_p5_*.json | wc -l'
```

## Artifacts

- Progress JSON: `/Users/ghost/Dev/nexus/shared/state/sweep_p5_progress_20260420.json`
- Per-iter outputs: `/home/summer/Dev/anima/docs/drill_min_20260420/sweep_p5_{148..231}.json` (on ubu2)
- This summary: `docs/drill_min_20260420/_summary_p5_complete.md` (status = in-flight; final counts pending)

## Next update

When all 84 iters complete, re-run to populate final novel/saturated counts and make Mk.X fire decision.
