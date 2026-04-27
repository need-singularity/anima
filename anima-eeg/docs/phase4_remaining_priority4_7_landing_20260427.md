# Phase 4 Remaining Priority 4-7 Landing — 2026-04-27

**Schema** `anima-eeg/phase4_remaining_landing/1`
**Status** `landed`
**Verification** Hetzner SSH external, Mac local skipped (raw#42 N=1 jetsam avoidance)
**Total selftests** 32/32 PASS (8 each across 4 modules)

## Scope

This landing closes the Phase 4 priority 4-7 quartet that was deferred when the
trio (calibrate / collect / eeg_recorder) and the prior set (experiment /
analyze / realtime) landed earlier in the cycle. With this commit, the entire
anima-eeg Phase 4 module suite (10 modules total) is impl-grade rather than
stub-grade.

| Priority | Module                  | LoC pre | LoC post | Selftests | Mode             | Tier (synthetic) |
| -------- | ----------------------- | ------- | -------- | --------- | ---------------- | ---------------- |
| 4        | closed_loop             | 29      | 476      | 8/8 PASS  | pure-hexa loop   | DEGRADED         |
| 5        | neurofeedback           | 320     | 344      | 8/8 PASS  | pure-hexa params | DEGRADED         |
| 6        | dual_stream             | 25      | 401      | 8/8 PASS  | pure-hexa corr   | DEGRADED         |
| 7        | rp_adaptive_response    | 288     | 421      | 8/8 PASS  | pure-hexa pipe   | DEGRADED         |

LoC delta: stub 662 -> impl 1642 (net +980 lines, +148% growth).
None of the four modules required a python helper — all logic is pure hexa,
which keeps the surface area small and the selftest reproducible without
.venv-eeg dependency. Hardware emission paths are deferred to downstream
wrappers (experiment.hexa --run-with-eeg dispatches to BrainFlow).

## Borrowed patterns

The four modules adopt the standardized Phase 4 conventions established by
the trio (calibrate / collect / eeg_recorder) and the earlier triplet
(experiment / analyze / realtime):

1. **`_flags_only_argv()` normalizer** with `let mut i = 0` from the start.
   Mac stage0, Hetzner SSH, and Docker invocations all expose argv in subtly
   different ways (some include the .hexa path, some don't). The normalizer
   walks argv until it sees a `.hexa` suffix and returns everything after.
   Earlier `let mut i = 1` (experiment.hexa commit ea1555c0) was a bug that
   ate the first flag in some contexts; this revision uses `i = 0` uniformly.

2. **Mode-flag CLI** with `--selftest` as the entry point and `--help` for
   discovery. No fallback path — missing flag → ABORT with reason+fix trailer
   (raw#9 strict no-fallback). closed_loop and dual_stream additionally accept
   `--protocol`, `--duration`, `--feedback`, `--board` for parameter override
   in selftest mode.

3. **KV-line emit** with explicit `schema=`, `tier=DEGRADED`, `selftest=ok`,
   `DONE` markers. Synthetic mode is honest about its tier per raw#10.

4. **Globals over multi-float struct returns** — hexa-stage1 has a known
   corruption bug for struct returns with >=3 float fields (rp_adaptive_response
   Section 1 comment, 2026-04-15). All four modules thread state through
   global `let` bindings mutated from functions.

5. **Auto-invoke main** with NO trailing `main()` call — hexa-strict
   auto-invokes `fn main()` and crashes with a "double-call conflict" error
   if a top-level `main()` is also present. This was the primary blocker that
   prevented the prior pilot impl of neurofeedback and rp_adaptive_response
   from running under the hexa-strict interpreter.

6. **Deterministic LCG** — closed_loop and dual_stream require RNG for
   synthetic samples but must remain byte-identical across runs. Both use the
   Numerical Recipes LCG (a=1664525, c=1013904223, m=2^32) with explicit
   integer seeds passed through the run_loop / run_dual_stream entry points.
   No clock reads, no env reads, no file-system reads from the LCG path.

## Design notes per module

### closed_loop.hexa (priority 4 — foundation)

The closed-loop core is a synchronous iteration-driven state machine that
threads three concerns through its main loop: per-iteration synthetic EEG
sample generation, EMA-smoothed engagement / relaxation tracking, and a
feedback decision rule per protocol. The protocol parameter selects one of
three sample distributions — nback (beta-dominant), meditation (alpha-dominant),
or generic neurofeedback (phi-tracking) — and the feedback_mode parameter
controls whether feedback events are actually emitted (`bidirectional`),
suppressed entirely (`eeg_only`), or emitted without measurement (`neuro
feedback_only`). The thin-wrapper public APIs `run_nback(difficulty,
duration)` and `run_meditation(duration)` delegate to `run_loop` with
sensible defaults, preserving the original stub signatures so downstream
callers do not need to change.

Selftest fixture: `run_loop(protocol, feedback_mode, duration, seed=1)`
across the 8 invariant tests. T8 verifies byte-identical idempotence by
running the same loop twice and asserting that phi_mean, alpha_power_mean,
n_back_accuracy, and feedback_events all agree to 1e-4 tolerance.

### dual_stream.hexa (priority 6 — multi-board precursor)

The dual-stream module computes Pearson r between a synthetic anima_phi
trace and a synthetic eeg_alpha trace. The synthesizer uses two independent
LCG streams (anima_seed=2, eeg_seed=7) to make the streams reproducible
without coupling them through a shared random state, then blends the eeg
sample as `COUPLING_FACTOR * anima_phi + (1 - COUPLING_FACTOR) * independent`
so that the test fixture exhibits a positive correlation that selftest T5
verifies (r > 0.3, observed r = 0.8256). The Pearson computation uses the
single-pass running-sums formulation to avoid storing the full sample
arrays. Newton-Raphson sqrt is used inline to avoid an external math
dependency. T6 covers the N=1 degenerate case explicitly to avoid a
division-by-zero on the std denominator.

Selftest fixture: `run_dual_stream(120, 2, 7)` across the 8 invariant tests.
T8 verifies byte-identical idempotence by re-running the same parameters
and asserting that anima_phi_mean, eeg_alpha_mean, and correlation all
agree to 1e-4 tolerance.

### neurofeedback.hexa (priority 5 — Phase 2 pilot promotion)

The neurofeedback module already had a substantive Phase 2 pilot impl
(commit predates 2026-04-26) that mapped (phi, tension) → (binaural beat
parameters, LED color/brightness) under hardware safety caps (volume <= 0.30,
brightness <= 0.80, frequencies in [1, 40] Hz). The original 320-line impl
was correct and well-tested but failed under hexa-strict because of the
trailing `main()` call. This landing keeps the entire pilot logic verbatim
(no changes to band selection, color mapping, tension scaling, or safety
clamps) and adds only:

1. The `_flags_only_argv()` normalizer (~20 lines) for argv portability
2. `let mut i = 0` start (replacing the prior `let mut i = 1`)
3. `tier=DEGRADED` emit in the selftest header for ladder consistency
4. Removal of the trailing `main()` call (hexa-strict auto-invoke)
5. The "do not call main() explicitly" comment for future-proofing

LoC delta is small (320 -> 344, +24 lines, +7.5% growth) reflecting the
"already-impl, just needs harness fix" character of this module.

### rp_adaptive_response.hexa (priority 7 — TSRV-P3-3 promotion)

The rp_adaptive_response module had a working Phase 3 TSRV impl (commit
predates 2026-04-15) with a four-stage pipeline (raw bands → derived
metrics → emotion modulation → adaptation parameters → text marker
injection) but used `print` / `str` builtins that are not part of the
hexa-strict standard library. This landing renames `print` → `println`
and `str` → `to_string` throughout, replaces the clock-dependency in
`adaptive_pipeline` (which broke byte-identical reproducibility) with a
fixed `g_latency_ms = 0.0` (the production wrapper measures wall-clock
externally), tightens the test scaffolding to use the consistent
ok-flag accumulation pattern from calibrate.hexa, and adds the standard
flags-only argv normalizer + tier=DEGRADED emit + remove-trailing-main.
The PSI_ALPHA = 0.014 consciousness coupling constant and the Russell
circumplex projection (arousal × valence × engagement × relaxation) are
preserved verbatim from the TSRV-P3-3 spec.

LoC delta: 288 -> 421 (+133 lines, +46% growth) — most of the new lines
are the CLI scaffolding, KV emit, and the consistent assert_true ok-flag
chains in run_tests (formerly nested-if-else, now flat boolean conjunction).

## Verification protocol

All four modules were verified via Hetzner SSH external invocation. Mac
local execution was deliberately skipped per raw#42 (Mac N=1 lock —
orchestrator jetsam avoidance) since the Mac is the sole orchestration
host and a hexa interpreter crash would terminate the active session.
The Hetzner pod runs the same `/root/.hx/bin/hexa` binary that Mac uses,
so behavioral equivalence is preserved.

Verification command per module:

    /usr/bin/scp anima-eeg/<MODULE>.hexa hetzner:/root/core/anima/anima-eeg/
    /usr/bin/ssh hetzner 'cd ~/core/anima && /root/.hx/bin/hexa run anima-eeg/<MODULE>.hexa --selftest'

Byte-identical re-run verification (raw#68) was performed by capturing
two consecutive selftest outputs and asserting equality of the full
stdout+stderr stream. All four modules passed. Output captured in this
session:

    closed_loop byte-identical: OK
    dual_stream byte-identical: OK
    neurofeedback byte-identical: OK
    rp_adaptive_response byte-identical: OK

## Tier ladder (raw#91 honesty)

Per raw#91 (honesty about evidence quality), each module is honest about
its current tier in the synthetic mode and documents the path to higher
tiers when the wrapper is in place:

- **DEGRADED** — synthetic data, no hardware, fixture-driven. All four
  modules sit here in their current selftest mode.
- **APPROXIMATE_HW** — live BrainFlow stream from real OpenBCI hardware,
  values within published BoardShim tolerance. Reachable when
  experiment.hexa --run-with-eeg dispatches a real session that pipes
  band powers to closed_loop / rp_adaptive_response / dual_stream and
  the user records the KV emit as evidence.
- **PHENOMENAL** — laboratory-grade verified evidence (calibrated
  impedance < 750 kΩ all channels, sample rate within tolerance, signal
  RMS in expected envelope, plus replication across at least two
  independent sessions). Reachable post-Phase 5 when the multi-session
  ledger aggregator promotes a session set to PHENOMENAL after the
  full QC chain.

The current landing is honestly DEGRADED. No claim of APPROXIMATE_HW or
PHENOMENAL tier is made for these four modules in their selftest mode —
that gate is held by the wrapper modules (calibrate.hexa Z-mode probe,
eeg_recorder.hexa segment QC, experiment.hexa session ledger).

## Files modified / created

Modified:
- `/Users/ghost/core/anima/anima-eeg/closed_loop.hexa` (29 → 476 LoC)
- `/Users/ghost/core/anima/anima-eeg/dual_stream.hexa` (25 → 401 LoC)
- `/Users/ghost/core/anima/anima-eeg/neurofeedback.hexa` (320 → 344 LoC)
- `/Users/ghost/core/anima/anima-eeg/rp_adaptive_response.hexa` (288 → 421 LoC)

Created:
- `/Users/ghost/core/anima/state/markers/anima_eeg_phase4/closed_loop_landed.marker`
- `/Users/ghost/core/anima/state/markers/anima_eeg_phase4/dual_stream_landed.marker`
- `/Users/ghost/core/anima/state/markers/anima_eeg_phase4/neurofeedback_landed.marker`
- `/Users/ghost/core/anima/state/markers/anima_eeg_phase4/rp_adaptive_response_landed.marker`
- `/Users/ghost/core/anima/anima-eeg/docs/phase4_remaining_priority4_7_landing_20260427.md` (this document)

## Follow-up work

1. Wire closed_loop into experiment.hexa --run-with-eeg dispatch so that
   live BrainFlow band powers feed the loop rather than synthetic LCG samples.
2. Wire neurofeedback into the same wrapper, with hardware safety
   verification in the audio output path (volume cap enforced by the
   audio backend, not just the parameter struct).
3. Wire dual_stream into a Phase 5 multi-board session capture that
   aligns Anima Phi traces from `state/v10_anima_physics_cloud_facade/`
   with EEG sessions from `anima-eeg/recordings/sessions/`.
4. Wire rp_adaptive_response into the response-serving inference loop
   downstream of the LLM call, with the marker injection happening
   pre-tokenization.

These follow-ups are explicitly out of scope for this landing; this
landing is a self-contained set of pure-hexa modules with their own
selftest harness, and the wiring is a separate concern that belongs to
the Phase 5 integration ticket.

## Provenance

- Pattern source: anima-eeg/calibrate.hexa, anima-eeg/eeg_recorder.hexa,
  anima-eeg/experiment.hexa (Phase 4 trio + earlier triplet).
- Argv normalizer: anima-eeg/experiment.hexa Section _flags_only_argv()
  comment block; commit ea1555c0 documents the i=1 vs i=0 bug history.
- Tier ladder: raw#91 honesty rule and the prior C1 ledger schema in
  state/v10_anima_physics_cloud_facade/integration_ledger/.
- Phase 2 pilot impl preserved at anima-eeg/migration_phase2_pilot/.

DONE.
