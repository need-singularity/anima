# A4 Live-Selftest W2/W3/W4 Spec (Gap → Live-PASS)

**Date**: 2026-04-18  **Status**: SPEC (diagnosis, no code changes)
**Audit ref**: `training/roadmap_drift_audit_20260418.md:134` (D6), `:159` (Rank 3 item 7)
**Primary evidence**: `training/a4_live_selftest_report.md:117-136` (promotion gate), `shared/state/a4_selftest_bugs_20260418.json`
**Companion**: `training/alm_hive_agg_oom_diagnosis.md` (W1 blocker)
**Precursor**: W1 = `hook_real_verify_n5 PASS Σw=15.6225` per `shared/convergence/phi_hook_wire.convergence:12` and `training/w1_hook_real_verify_n5_report.md:15`

## W-bucket reconciliation

Two W-series co-exist and must be disambiguated:

1. **phi_hook_wire W1-series** (one subtrack only, W1 = hook real verify n=5)
   — source `shared/convergence/phi_hook_wire.convergence:6-13`. Already PASS.
2. **a4_live_selftest W1-W4 buckets** (this doc) — source
   `training/a4_live_selftest_report.md:133-136`. Bundles the 11 live-run files
   into 4 buckets tied to P5-P20 integration evidence.

This spec covers (2). W1 in (2) is `hive bundle`, which is blocked by the
alm_hive_agg RUN-OOM (see companion doc). W2/W3/W4 in (2) are the focus below.

---

## W2 — alm_affect + alm_finitude + alm_nested (P12/P15/P8 heads)

### Scope
Head/loss modules wired via `training/wire_p5_p20_report.md:14,16,13` — affect
(P12), finitude (P15), nested_loss (P8). Live-run produces 5/5 test PASS each
per `training/a4_live_selftest_report.md:24-26`.

### Artifacts present
- `training/alm_affect_head.hexa` (534L) — `training/a4_live_selftest_report.md:24` 5/5 PASS, centroid 7/7, noisy acc 0.949
- `training/alm_finitude_head.hexa` (419L) — `:25` 5/5 PASS, R²=0.954
- `training/alm_nested_loss.hexa` (435L) — `:26` 5/5 PASS, K=3 stable / K=5 unstable

### Done-criteria analogue to W1 (phi_hook_wire)
W1's done-criteria was `Σw=15.6225 with n=5 real ckpts` (`training/w1_hook_real_verify_n5_report.md:15`).
For W2 the analogue is:

> **W2 done** = 3/3 head files, each showing live-run 5/5 PASS with a
> correctness-headline metric (noisy_acc for affect, R² for finitude, K=3
> stable for nested) logged to `shared/state/`.

Per `training/a4_live_selftest_report.md:134` this bucket is marked
**PROMOTE** already — the only reason `@w2_artifact TBD` in the convergence
file is the convergence file was not updated after the selftest report
landed.

### Blocker to live-PASS
**None** — files are untracked (`git status` shows `??` on all three per
`training/roadmap_drift_audit_20260418.md:135`) but run clean. The gap is
**bookkeeping only**: stage the files and record promotion in
`shared/convergence/a4_live_selftest.convergence`.

### Rank
**EASIEST (1)** — no code work, just: git add + convergence field update.

---

## W3 — engine_ablation + run_ablation (P? sweep tooling)

### Scope
Ablation driver + sweep runner. Provides the KEEP/REVIEW/DROP decision layer
that gates individual Φ kernels from entering the 16-dim probe bundle. See
`training/a4_live_selftest_report.md:19-20`.

### Artifacts present
- `training/engine_ablation.hexa` — `:19` 7/7 PASS
- `training/run_ablation.hexa` — `:20` 5/5 PASS after fix A4-B1 (`shared/state/a4_selftest_bugs_20260418.json:9-19`); sweep result `KEEP=33 REVIEW=19 DROP=19` per `:120`

### Done-criteria analogue to W1
> **W3 done** = 2/2 ablation tools, run_ablation produces a deterministic
> KEEP/REVIEW/DROP tally (currently 33/19/19) with no `.set()`-on-void
> errors, and A4-B1 fix is staged in the file.

### Blocker to live-PASS
**None** — A4-B1 fix already applied in-file
(`shared/state/a4_selftest_bugs_20260418.json:12-13` lists
`run_ablation.hexa:426` as fixed). Per `a4_live_selftest_report.md:135`,
**PROMOTE 2/2**. Same bookkeeping gap as W2: update convergence file.

### Rank
**EASY (2)** — same as W2: stage + convergence update. Slight edge case:
ensure A4-B1 fix is committed (fix ref: `a4_live_selftest_report.md:44-48`).

---

## W4 — wire_p5_p7_into_alm + eval_phi_corr (P5/P6/P7 triple wire + correlation verdict)

### Scope
The three-dim Φ triple (phi_refl P5, phi_time P6, phi_emb P7) wired into
`train_alm_14b` and the correlation verdict that reads `phi_vec.json` and
emits SIG/WEAK/DECAY classification per dim.

### Artifacts present
- `training/wire_p5_p7_into_alm.hexa` — `:23` 5/6 (T5 latency EXPECTED-FAIL under interpreter, per `shared/state/a4_selftest_bugs_20260418.json:44-52` A4-B5). Φ numerics PASS: Φ_holo=6111 Φ_refl=1.458 Φ_time=74.50 Φ_emb=17.88 ‖Φ‖=6111.48 deterministic (`a4_live_selftest_report.md:87-88`).
- `training/eval_phi_corr.hexa` — `:21` VERDICT PASS, 16/16 SIG, Σw=15.5526 per `a4_live_selftest_report.md:121`

### Done-criteria analogue to W1
> **W4 done** = 2/2 files, eval_phi_corr emits `VERDICT PASS Σw>=15.0` on
> the n=5 realistic ckpts, wire_p5_p7 produces deterministic Φ numerics
> across runs, and T5 latency is tagged EXPECTED-FAIL-UNDER-INTERPRETER
> rather than FAIL.

### Blocker to live-PASS
**One caveat** — `wire_p5_p7_into_alm.hexa` T5 latency gate
(8000 ms actual vs 50 ms budget per `a4_live_selftest_report.md:86`) fails
under the tree-walk interpreter. Not a correctness bug; marked as
A4-B5 EXPECTED-FAIL in `shared/state/a4_selftest_bugs_20260418.json:44-53`.
Per `a4_live_selftest_report.md:136`: **PROMOTE with interpreter-speed caveat**.

### Rank
**MEDIUM (3)** — mostly bookkeeping, but needs an explicit convergence
carve-out: `@w4_caveat interpreter_speed_t5_expected_fail`. Otherwise the
5/6 score on wire_p5_p7 looks like an unresolved bug instead of a known
env limit awaiting native-build path.

---

## Ranking summary (easiest → hardest to close live-PASS)

| rank | bucket | files | remaining work | blocker |
|------|--------|-------|----------------|---------|
| 1 | **W2** | alm_affect/finitude/nested | git add + convergence update | none |
| 2 | **W3** | engine_ablation/run_ablation | convergence update (A4-B1 already fixed in-file) | none |
| 3 | **W4** | wire_p5_p7 + eval_phi_corr | convergence update w/ `@w4_caveat interpreter_speed` | T5 latency (EXPECTED-FAIL, not a bug) |
| -- | **W1** | hive bundle | see `training/alm_hive_agg_oom_diagnosis.md` | RUN-OOM — real code work needed |

## Systemic ossification candidate

The friction pattern across all four buckets: **parse-only verification was
accepted as done, then live-run exposed real issues** (A4-B1 `.set()`-on-void,
A4-B2 tuple-return parse, alm_hive_agg OOM, A4-B5 interpreter-speed). This
warrants a new rule.

> **A4-OSS-02 MINI_SHAPE_SMOKE_BEFORE_FULL_SHAPE** — every live-run self-test
> must demonstrate a mini-shape smoke (e.g., `[2,4,16]` as in
> `phi_probe_wire_report.md:23`) before attempting full-shape. Mini-smoke
> surfaces alloc-per-push blowup, interpreter-speed gates, and parse regressions
> cheaply. Full-shape without mini-smoke is the historical root of RUN-OOM
> (hive_agg) and interpreter-gate FAILs (A4-B5).

This pairs with existing A4-OSS-01 (`a4_live_selftest.convergence:15`)
which ossified "parse-only is insufficient, live-run required". A4-OSS-02
tightens that: **live-run at full shape is also insufficient — require
mini-shape first**.
