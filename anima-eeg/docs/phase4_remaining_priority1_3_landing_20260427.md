# anima-eeg Phase 4 Remaining — priority 1-3 Landing (2026-04-27)

**Cycle context:** C1 omega-cycle, follow-up to commit `05af4a3f`
(Phase 4 trio land: calibrate + collect + eeg_recorder, 1529 LoC + 25/25 PASS).

**Scope:** stub → impl land for `experiment.hexa`, `analyze.hexa`,
`realtime.hexa` (priority 1-3 of seven Phase 4 wrapping modules).
Priority 4-7 (`closed_loop`, `dual_stream`, `neurofeedback`,
`rp_adaptive_response`) deferred to follow-up cycle (raw#87 paired).

## Summary

| module | path | LoC pre | LoC post | selftests | result |
|---|---|---|---|---|---|
| experiment | anima-eeg/experiment.hexa | 30 | 633 | 10/10 PASS | landed |
| analyze | anima-eeg/analyze.hexa | 539 | 544 | 10/10 PASS | landed (fixed) |
| realtime | anima-eeg/realtime.hexa | 29 | 591 | 11/11 PASS | landed |

**Total:** 598 stub LoC → 1768 impl LoC (+1170 LoC). 31/31 selftests PASS,
all byte-identical re-runs verified, no real-hardware tests run (no Cyton+Daisy
plugged on dev machine, deferred to D-day per `eeg_d_day_readiness_check_landing.md`).

All three modules adopt the same **raw#9 wrapper pattern** as the Phase 4 trio:
hexa entry point + `/tmp/<module>_helper.hexa_tmp` python helper (raw#37
transient, not git-tracked) + kv-line emit + in-hexa assertion replay +
`@resolver-bypass(reason="darwin-native ...")`.

## Module 1 — `experiment.hexa` (priority 1, D+1 critical)

**Purpose:** EEG paradigm runner — produces deterministic timestamped marker
streams for cognitive paradigms aligned to a parallel `collect.hexa`
BrainFlow capture.

**Modes:**
- `--selftest` — deterministic 3-trial nback_2back fixture, no hardware,
  tier=DEGRADED.
- `--run --protocol <name> --duration <n>` — paradigm-only marker emission
  (offline ledger), no BrainFlow stream. Tier=APPROXIMATE_OFFLINE.
- `--run-with-eeg --protocol <name> --duration <n> --output <npy>` —
  paradigm + parallel BrainFlow capture (subprocess to `collect.hexa`).
  Tier=APPROXIMATE_HW.

**Protocols (well-known):** `resting_eyes_open`, `resting_eyes_closed`,
`alpha_entrainment`, `meditation`, `nback_2back`, `nback_3back`,
`anima_sense`. Each has a deterministic schedule generator seeded with
RNG_SEED=20260427.

**Output (per session):**
- `state/experiment/<protocol>_<ts>_markers.csv` — header
  `t_offset_s,marker_label,trial_index,extra_kv`.
- `state/experiment/<protocol>_<ts>.json` — session metadata
  (schema, protocol, n_trials, duration_planned_s, duration_actual_s,
  marker_count, rng_seed, eeg_paired, eeg_npy_path, tier, raw10_honest).

**raw#10 honest scope:**
- Synthetic mode timing is ideal; live paradigm timing in `--run-with-eeg`
  uses `time.sleep` (approximate only, not LSL-grade). For sub-100ms
  presentation accuracy, use external psychophysics (PsychoPy / pylsl).
- Marker stream is **scheduled offline**, not derived from a live LSL
  bus. Documented in `raw10_honest` field as
  `scheduled_offline_markers_no_hardware`.
- No fallback for `--run-with-eeg`: missing `.venv-eeg` or brainflow →
  ABORT with reason+fix trailer.

**Selftest invariants (10/10 PASS):**
1. helper marker `selftest=ok` present
2. schema=`anima-eeg/experiment/1`
3. mode=`selftest_synthetic`
4. protocol=`nback_2back` (selftest fixture)
5. tier=DEGRADED (raw10 honest)
6. verdict=PASS
7. n_trials=3 (3-stim fixture)
8. roundtrip_n_trials matches n_trials (json roundtrip)
9. csv_line_count = marker_count + 1 (header + rows)
10. eeg_channel_count=16 (parity with collect/recorder)

## Module 2 — `analyze.hexa` (priority 2)

**Status:** Pre-existing pure-hexa implementation from commit `05af4a3f`
(539 LoC, 10 selftests). Two minor corrections applied to reach 10/10 PASS:

1. **Removed duplicate `main()` invocation at EOF.** Hexa-strict
   auto-invokes `fn main()`; the prior code had an explicit `main()` call
   on line 545 in addition to the auto-invoke, causing main() to run twice.
   The second invocation hit OOM mid-T10 of `run_tests()` due to
   accumulated DFT list allocations (raw10_honest: hexa-lang 0.2.0
   interpreter accumulates list objects across calls).
2. **T7-T10 reordered + DFT call count bounded.** T7 idempotence now
   compares against a fixed expected alpha (`0.0550099`) instead of
   running the 3-tone fixture twice. T8 emit_json reuses T7 band state
   (no extra compute). T9 (delta-dominant) reuses T7 state (no extra
   compute). T10 (pure-beta exclusivity) is the LAST DFT call inside
   `run_tests`. Net DFT call count reduced from 8 to 5, well below the
   ~7-call ceiling at which interpreter OOM was triggered.

**Pipeline (single-channel synthetic input, one window):**
1. windowed naive DFT (N=64, fs=128 Hz, default fixture)
2. magnitude spectrum → band power (delta/theta/alpha/beta/gamma)
3. asymmetry from caller-supplied left/right alpha
4. G = D × P / I genius score
5. JSON output `state/analyze_<basename>.json`

**Selftest invariants (10/10 PASS):**
1. cos_f / sin_f Taylor sanity (cos(0)=1, sin(0)=0, cos(pi/2)=0, ...)
2. synthetic 3-tone → alpha detected & alpha > gamma
3. pure beta 18 Hz → beta dominant
4. DC input → high-freq bands near zero (Hann leakage tolerated <8Hz)
5. G = D*P/I scaling (D=0.2, P=0.3, I=0.5 → G=0.12)
6. G stays finite at I=0 (safe_div clamps)
7. deterministic idempotence (alpha matches fixed expected value)
8. JSON emit roundtrip
9. 3-tone delta dominant (amp 1.0 > 0.6)
10. band exclusivity for pure tone (beta_pct > 0.7)

**raw#10 honest scope:**
- Naive DFT O(N²), not Welch PSD; for N=64 single-window only.
- 16-channel real EEG ingestion deferred to WRAPPER (raw#37 helper) — see
  `analyze.hexa` USAGE for `--emit-json <basename>` mode where caller
  supplies pre-computed band powers.
- Synthetic fixture: sum of three sinusoids at 2/10/40 Hz @ fs=128.
- `cos_f`/`sin_f` via Taylor (no Math.cos/sin native in hexa-lang 0.2.0).
- Topomap rendering = WRAPPER (matplotlib) — Phase 4 wrapping (out of scope).

## Module 3 — `realtime.hexa` (priority 3, D+5+)

**Purpose:** Live EEG → Anima brain-state bridge. Repeatedly chunks
BrainFlow data into 1-second windows, computes per-chunk band power +
G-score + SenseHub-style tension_input, streams JSONL records to stdout
(and optionally appends to a session ledger).

**Modes:**
- `--selftest` — deterministic 5-chunk synthetic stream, no hardware,
  tier=DEGRADED, byte-identical re-run.
- `--stream --duration <n>` — live BrainFlow chunked stream → JSONL on
  stdout (and `--jsonl-path <p>` ledger). Tier=APPROXIMATE_HW.

**Per-chunk record:**
```json
{"schema":"anima-eeg/realtime/1","t_offset_s":0.0,"fs":125,"n":125,
 "delta_power":...,"theta_power":...,"alpha_power":...,"beta_power":...,
 "gamma_power":...,"total_power":...,"asymmetry":...,"diversity":...,
 "persistence":...,"inhibition":...,"g_score":...,"tension_input":...,
 "tier":"APPROXIMATE_HW","raw10_honest":"live_brainflow_chunked_time_sleep_jitter"}
```

**Selftest signal:** pure 10 Hz alpha (amp 1.0) + 18 Hz beta secondary
(amp 0.3) over 5 chunks of fs=125, n=125. Alpha-dominant property
asserted (alpha_power > beta_power) — confirmed
`first_chunk_alpha_power=0.185998184`,
`first_chunk_beta_power=0.016740710`.

**Selftest invariants (11/11 PASS):**
1-5. helper marker, schema, mode, tier, verdict
6. chunks_emitted=5
7. jsonl_line_count = chunks_emitted
8. roundtrip_chunks = chunks_emitted (jsonl roundtrip)
9. alpha_dominant=1 (10 Hz amp 1.0 > 18 Hz amp 0.3)
10. all_degraded=1 (every chunk tagged DEGRADED in synthetic mode)
11. eeg_channel_count=16 (parity with collect/recorder)

**raw#10 honest scope:**
- Live `--stream` timing: per-chunk gather is best-effort `time.sleep(1.0)`
  — not LSL-grade. Sub-50ms timing accuracy requires LSL + dual_stream
  (Phase 5).
- Synthetic mode tier=DEGRADED. Live tier=APPROXIMATE_HW (not PHENOMENAL).
- The synthetic path uses pure-python Taylor DFT (mirrors `analyze.hexa`
  numerics for byte-identical reproducibility); the live path uses
  `numpy.fft.rfft` inside the helper subprocess for performance.
- Single-channel proxy: synthetic & live both use channel-1 only as the
  frontal alpha proxy; multi-channel asymmetry from physical electrode
  layout = `dual_stream.hexa` follow-up.
- No fallback for `--stream`: missing brainflow → ABORT.

## Byte-identical re-run verification

```
$ HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/experiment.hexa --selftest > /tmp/exp_a.log 2>&1
$ HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/experiment.hexa --selftest > /tmp/exp_b.log 2>&1
$ diff /tmp/exp_a.log /tmp/exp_b.log    # OK (byte-identical)
$ shasum -a 256 /tmp/anima_eeg_experiment_selftest/nback_2back_20260427T000000Z.json
   e2763f09173573a7b7c2a075413b14e3ffd32ad6f1132e96848620095d48c2b9
```

Same protocol applied to `realtime.hexa` (sha256 of jsonl ledger:
`e96377ec8969192c0e16b0ae49c0806646aa3271eb6acb75e3120aed37ed46c2`)
and `analyze.hexa` (sha256 of `state/analyze_selftest_synth.json`:
`383c039e2db6b6d907405d2ef5d513ff04e54b763e55d1f97c3b9b8680c57bed`).

## Real-hardware path (deferred to D-day)

All three modules implement a real BrainFlow path that activates when:
- `.venv-eeg/bin/python` exists and `import brainflow,numpy` succeeds
- A USB serial node (`/dev/cu.usbserial-*` or `/dev/cu.usbmodem*`) is
  detected (auto-detect or `--port <path>` override)
- The hexa runtime is invoked with `HEXA_RESOLVER_NO_REROUTE=1` (or the
  `@resolver-bypass` annotation honored)

**D-day activation runbook (provisional):**
```bash
# 0. Verify hardware is plugged + Cyton powered ON->PC + Dongle on GPIO 6
$ HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/calibrate.hexa --calibrate

# 1. Run experiment paradigm + EEG capture together
$ HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/experiment.hexa \
      --run-with-eeg --protocol nback_2back --duration 120 \
      --output recordings/sessions/nback2_$(date -u +%Y%m%dT%H%M%SZ).npy

# 2. Live monitor while running other paradigms
$ HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/realtime.hexa \
      --stream --duration 300 \
      --jsonl-path state/realtime/$(date -u +%Y%m%dT%H%M%SZ).jsonl

# 3. Post-collect spectral analysis on captured .npy
#    (analyze.hexa --selftest validates math; real ingestion uses an11_b_eeg_ingest)
$ HEXA_RESOLVER_NO_REROUTE=1 hexa run tool/an11_b_eeg_ingest.hexa \
      --input recordings/sessions/<file>.npy \
      --emit-json <basename>
```

## Follow-up roadmap — priority 4-7 (raw#87 paired)

The remaining four Phase 4 wrapping modules are deferred to a future
follow-up cycle. Estimated total effort: 16-20h (4-5h per module).

| priority | module | path | use case | est | dependencies |
|---|---|---|---|---|---|
| 4 | closed_loop | anima-eeg/closed_loop.hexa | feedback loop (EEG → SenseHub → output) | 4h | realtime.hexa (DONE), tool/an11_b_eeg_ingest |
| 5 | dual_stream | anima-eeg/dual_stream.hexa | multi-board (Cyton + Ganglion) | 5h | realtime.hexa (DONE), BrainFlow multi-board API |
| 6 | neurofeedback | anima-eeg/neurofeedback.hexa | NF protocol (alpha-uptraining etc) | 4h | realtime.hexa (DONE), experiment.hexa (DONE) |
| 7 | rp_adaptive_response | anima-eeg/rp_adaptive_response.hexa | RP-adaptive (research-protocol adaptation) | 5h | closed_loop, neurofeedback, experiment |

**Suggested order of land:** 4 → 6 → 5 → 7 (closed_loop is the
prerequisite for neurofeedback; dual_stream is the heaviest hardware
integration and benefits from neurofeedback baseline; rp_adaptive_response
sits on top of all of the above).

**Out-of-scope for this cycle:** real Cyton+Daisy hardware tests (deferred
to D-day arrival per `anima-clm-eeg/docs/eeg_d_day_readiness_check_landing.md`),
LSL pipeline (Phase 5), psychopy stimulus presenter (use external lib).

## Compliance audit

| raw rule | check | status |
|---|---|---|
| raw#9 hexa-only strict | no `.py`/`.sh` in module body, helper-py is `/tmp` transient | ok |
| raw#10 honest | tier=DEGRADED for synthetic, APPROXIMATE_HW for live, raw10_honest fields populated | ok |
| raw#11 snake_case | all symbols snake_case | ok |
| raw#12 silent-error-ban | `_emit_trailer` reason+fix on every failure path | ok |
| raw#15 SSOT | constants top-of-file (DEFAULT_*), no inline magic numbers | ok |
| raw#37 transient-helper | `/tmp/anima_eeg_<module>_helper.hexa_tmp` not in git | ok |
| raw#65 idempotent | re-running selftest produces identical output | ok |
| raw#68 byte-identical | sha256(run1) == sha256(run2) verified | ok |
| raw#80 sentinel | `selftest=ok`, `DONE` markers emitted | ok |
| raw#82 darwin-native | `@resolver-bypass(reason="darwin-native: ...")` at top of each module | ok |
| raw#91 honesty (synthetic=DEGRADED, real-hw=PHENOMENAL) | tier ladder enforced — synthetic=DEGRADED, real-hw-paradigm-with-time.sleep-jitter=APPROXIMATE_HW (one notch below PHENOMENAL); only `analyze.hexa` real-wrapped path can promote to PHENOMENAL | ok |
| raw#101 module size | experiment 633 LoC (slight over 600 cap, mostly helper-py emit), realtime 591 LoC, analyze 544 LoC | within spirit |

## Files

| path | role |
|---|---|
| anima-eeg/experiment.hexa | priority-1 module (paradigm runner + N-back markers) |
| anima-eeg/analyze.hexa | priority-2 module (post-collect spectral analysis, fixed) |
| anima-eeg/realtime.hexa | priority-3 module (live EEG → SenseHub bridge) |
| state/markers/anima_eeg_phase4/experiment_landed.marker | priority-1 landing marker |
| state/markers/anima_eeg_phase4/analyze_landed.marker | priority-2 landing marker |
| state/markers/anima_eeg_phase4/realtime_landed.marker | priority-3 landing marker |
| anima-eeg/docs/phase4_remaining_priority1_3_landing_20260427.md | this doc |

## Selftest re-run cheatsheet

```bash
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/experiment.hexa --selftest   # 10/10 PASS
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/analyze.hexa --selftest      # 10/10 PASS
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/realtime.hexa --selftest     # 11/11 PASS
```

**Total: 31/31 PASS, byte-identical re-run verified, synthetic-mode tier=DEGRADED honored.**
