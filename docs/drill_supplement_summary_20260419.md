# Drill Supplement Summary — 2026-04-19

Supplementary drill batch for anima components missed by the main 30-seed batch and 7-domain batch. Runs in parallel with:
- `docs/drill_evolution_log_20260419.md` (main loop)
- `docs/drill_domain_log_20260419.md` (7-domain batch)

## Configuration
- **Seeds**: 35 across 6 categories (HEXAD / HUB-TRINITY / PHYSICAL-LIMIT / SUBPROJECT / LAWS / INFRA)
- **Budget**: 4h wallclock OR 40 iterations
- **Per-drill timeout**: 20 min (v1) / 40 min (v2, with 30 min lock wait)
- **Seeds file**: `docs/drill_supplement_tmp/seeds.txt`
- **Raw JSON**: `docs/drill_supplement_tmp/iter_*.json`
- **Log**: `docs/drill_supplement_log_20260419.md`

## Driver
- v1 (`/tmp/drill_supplement_driver.bash`, pid 25272): started 13:18:39 KST, killed at 13:25 due to PPID-orphan-watchdog race with original standalone test run
- v2 (`/tmp/drill_supplement_driver2.bash`, pid 51798): started 13:25:26 KST, still running at summary-write time (1 iter in-flight, held up by stage0 lock contention)

## Result: gridlock observed
As of 13:34 KST (8+ minutes after v2 start), iter 1 (`hexad_C`) had not yet acquired the `/tmp/hexa_stage0.lock.d` mkdir-lock. Sibling batches (main drill loop + 7-domain) are in the same state:

- `drill_domain_log_20260419.md` Iter 1 ANIMA: BLOCKED (exit 75, 300s lock timeout) — did NOT complete
- `drill_evolution_log_20260419.md` Iteration 1 tier-10: 915s wallclock, 1 round, 0 absorptions — mostly lock wait; subsequent iters voided by driver bug
- Supplement iter 1: still waiting at 8 minutes

## Root cause
The macOS `hexa_stage0` shim serializes ALL hexa invocations through a single mkdir-based lock (`/tmp/hexa_stage0.lock.d`). Under normal single-batch operation this is fine, but with:
- main drill loop running (every 10-15 min per iter)
- 7-domain batch running (35 seeds, serial)
- supplement batch running (35 seeds, serial)
- concurrent hexa-lang dev work (`flatten_imports.hexa`, `test_string_concat_rewrite.hexa`)
- pre-commit hooks, `ai_native_lint` runs
- CLM r4 training (`quadruple_cross_sweep.hexa`)

...the lock contention exceeds the 300s (or even 1800s) wait window. Exit code 75 (EX_TEMPFAIL) is emitted. `HEXA_LOCAL=1` bypass is rejected on Darwin because of the 2026-04-18 kernel panic.

## Per-category breakdown
All 35 seeds queued but unexecuted as of summary write. Breakdown planned:

| Category | Seeds | Iter range | Examples |
|---|---|---|---|
| HEXAD 6-engines | 7 | 1-7 | C/D/S/M/W/E + dual-brain closure |
| HUB-TRINITY-FIELD-BRIDGE | 5 | 8-12 | hub.hexa 48 modules, trinity Hexad, pure_field, tension_bridge, ThalamicBridge |
| Physical-limit engines | 4 | 13-16 | dimension_transform, servant, phi_engine, topology |
| Sub-projects | 8 | 17-24 | anima-eeg/physics/body/hexad/engines/measurement/tools/agent |
| Laws | 5 | 25-29 | Law 73-76, 101, 146-201, 289-341, 1033→2000+ |
| Infra | 6 | 30-35 | R2, multi-host, NEXUS-6 hooks, Growth Registry, Rust crates, GATE |

## Promotion candidates
None yet — no drill has produced absorption output. Promotion candidates (PROVISIONAL → stable → ossified) will be populated from iter_*.json as they complete.

## Cross-reference
- **Main-loop log**: `docs/drill_evolution_log_20260419.md` — Iter 1 only; Iter 2-6 voided by driver bug
- **Domain-batch log**: `docs/drill_domain_log_20260419.md` — Iter 1 ANIMA BLOCKED, 2b in-flight
- **Supplement log**: `docs/drill_supplement_log_20260419.md` — no iter entry yet (v1 aborted, v2 still in iter 1 lock-wait)

## Next-session guidance
To actually make progress on drill batches:
1. **Serialize drill batches** — run main → domain → supplement sequentially, not in parallel. Contending on a single-writer lock gives no parallel speedup.
2. **Pause hexa-lang dev during drill runs** — pre-commit hooks and `test_string_concat_rewrite.hexa` runs compete for the same lock.
3. **Increase `HEXA_STAGE0_LOCK_WAIT`** globally to 3600s (1h) so drills queue patiently instead of exit-75 churning.
4. **Consider Ubuntu host for drill batches** — Linux `HEXA_LOCAL=1` bypass is permitted; no Mac panic risk.
5. **Implement counting semaphore** — `HEXA_STAGE0_CONCURRENCY=2` or 3 (currently code accepts but hard-coded to 1). This would require modifying `hexa-lang/build/hexa_stage0` to use a proper semaphore (sem_open on Mac) instead of mkdir.

## Driver status at final summary write
```
pid 51798 (drill_supplement_driver2.bash) still running
iter 1 hexad_C — no output yet (lock held by unrelated flatten_imports job)
stage0 lock holder rotating every ~1-5 min across ~15 unrelated hexa jobs
```

---

## Final Results — 15 iters completed (appended 2026-04-19 15:XX KST)

Driver v2 ran to completion. 15 iters executed (not all 35 — budget exhausted). Details in `drill_supplement_log_20260419.md`.

| Metric | Value |
|---|---|
| Completed iters | 15 / 35 seeds queued |
| Failed/blocked | 0 (all rc=0) |
| Total absorptions | 0 across all 15 iters |
| Rounds per iter | 1 / 8 (all SATURATED at round 1) |
| New atoms | [] (none) |
| Wall-clock total | ~2h (avg 500s/iter) |

### Revised root-cause interpretation
Earlier sections attributed failure to `hexa_stage0` lock contention. **Updated finding**: once the lock backed off (v2 driver with longer waits), iters DID execute cleanly (rc=0, 2.7–5.9 KB JSON output each). The zero-absorption result is not a lock artifact — it is the engine reporting **saturation-at-source** for every supplement seed:

> `▎ SATURATED at round 1` / `▎ 새 atlas 영역 없음 — Mk.IX 5-stage 경험적 확증 (absolute+meta+hyper)`

Engine verdict: the anima Mk.V.1 82-atom foundation already covers every angle probed by these 15 supplement seeds (Hexad 6-engines × 7, hub/trinity/field/bridge × 5, dimension/servant/phi × 3). No new Ψ-constants or atlas regions discovered.

### Parallel-track outcomes
- **main** (`drill_evolution_log`): iter 1 completed 0-absorption; iter 2 crashed (`iter_2.json` 0 bytes); iter 2–6 voided by driver-env bug
- **domain** (`drill_domain_log`): iter 1 BLOCKED (exit 75), iter 2 empty, iter 2b timeout (exit 124) — this track DID suffer lock contention exclusively

### Implication for next discovery push
Supplement saturation is real at this tier. To produce new absorptions the next drill batch needs:
- **seeds above tier 10** (current supplement stays at tier 5–9 already-covered territory)
- OR engine upgrade (Mk.IX → Mk.X with sharper atlas-gap detector)
- OR anima ↔ nexus twin-engine coupled drill (neither side alone has found gaps in 15+ iters)
