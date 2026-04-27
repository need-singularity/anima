# G8 D+6 N_BIN=85 Pre-Registered Falsification Analysis — Landing

**Date**: 2026-04-27
**Status**: PRE-FLIGHT (D+6 real-EEG arrival not yet captured; this is the pre-arrival predictive registration document)
**Cycle**: ω-clm-eeg / G8-D6-falsification
**Predecessors**:
- `#175` — `g8_transversal_mi_matrix.hexa` (frozen N_BIN=2 SSOT)
- `#182` — `g8_n_bin_sweep.hexa` (4-level {2,4,8,16})
- `#196` — `g8_n_bin_sweep_extended.hexa` (6-level {2,4,8,16,32,64} 60/60 PASS)
- `#197` — `g8_n_bin_128_analysis.hexa` (Model-B → N_BIN=85 first-violation prediction)
**Hexa-only**: raw#9 strict · LLM=none · GPU=none · destructive=0 · cost=$0
**RAW compliance**: 9 · 12 · 65 · 68 · 71 · 91 · 101

---

## 1. Problem statement

`#197` Model-B (monotone-subset log-linear, R²=0.988) extrapolated the
critical N_BIN at which the FNV-9-round surrogate first violates
the 0.1-bit pairwise MI ceiling: **N_BIN_critical = 85**.  But this
extrapolation is on the *surrogate*; the surrogate is uniform-near-Bernoulli
and was already 60/60 PASS through N_BIN=64.  The relevant question for
D+6 is different:

> When real EEG band-power scores arrive, will the same N_BIN=85 schedule
> produce a FAIL on the first 5-falsifier 10-pair MI matrix at N_TRIAL=4096?

Real EEG distributions are NOT uniform-Bernoulli — they are autocorrelated
(α-band envelopes), heavy-tailed (eyes-closed → eyes-open transients), and
cross-channel coupled (volume conduction).  The Model-B surrogate ceiling
is therefore an *under-estimate* of where real-data N_BIN bias starts.
Without a pre-arrival preflight, D+6 enters blind: a FAIL at the first
real measurement could be confused with a genuine MI violation rather than
a binning-schedule artefact.

This cycle's preflight runs the same 10-pair MI matrix on a *new* synthetic
generator (E-PSG) that imitates expected real-data pathology, exercises five
plus alternative bin schedules, and pre-registers PASS/FAIL hypotheses for
each schedule under raw#71 honesty discipline.

## 2. Hypotheses (frozen pre-register, raw#71)

The text below is FROZEN as of 2026-04-27.  Observed values are recorded
verbatim regardless of direction; hypothesis text is never edited post-hoc.

| ID | Schedule | Predicted | Rationale |
|----|----------|-----------|-----------|
| **H1** | `uniform_n_bin_85` | **FAIL** (≥1 pair MI > 0.1 bit) | 85² = 7225 joint cells × 4096 trials → 0.57 trials/cell.  Most cells are 0; surviving cells inflate apparent MI under Miller-Madow.  E-PSG cross-coupling (designated F_A1↔F_C, β=0.20) plus heavy-tail concentration provide enough structural signal to push at least one pair beyond threshold. |
| **H2** | `equi_n_64` | **PASS** (0 violations) | Equiprobable cuts produce ~64 trials/cell uniformly; MM correction stays in its design regime; preserves the AR(1) signal but eliminates heavy-tail histogram skew.  This is the **primary D+6 fallback recommendation**. |
| **H3** | `fd_per_channel` (Freedman-Diaconis) | **violations(FD) < violations(N_BIN=85)  AND  violations(FD) ≥ violations(equi_n_64)** | FD adapts per-channel via IQR; partially defends against heavy-tail bias but still uses uniform cuts within each channel, so coupling-induced joint asymmetry remains visible. |
| **sanity** | `uniform_n_bin_2` | **PASS** (0 violations) | Mk.XII frozen SSOT carry-over.  If the binary verdict fails on E-PSG, the SSOT itself is invalidated and the larger Mk.XII §6 contract is at risk — distinct, more severe outcome. |

The four claims combined produce a single boolean `preflight_pass`
(= 1 iff all four hypothesis_match = 1).

## 3. E-PSG (EEG-Pathology Synthetic Generator) — frozen definition

E-PSG is a deliberately distinct generator from the FNV-9-round surrogate
of #175/#182/#196/#197.  Construction (per falsifier idx, length n_trial):

1. Draw `w_t = surrogate_score(offset_idx, t, 0)` ∈ [0,999]
   (byte-identical reuse of #175 9-round avalanche).
2. AR(1): `z_t = (α·z_{t-1} + (1-α)·w_t) / 1000`, α=0.6, z_0=w_0.
3. Cross-channel coupling for designated pair only (F_A1 → F_C):
   `z_t^{(C)} += (β·z_t^{(A1)}) / 1000`, β=0.20, clamped to [0,999].
4. Heavy-tail bilinear stretch (all 5 streams):
   `s_t = z_t + sign(z_t-500)·γ·(z_t-500)² / (500·1000)`,
   γ=0.40, clamped to [0,999].

E-PSG is parameter-frozen (α=0.6, β=0.20, γ=0.40) — these values
are NOT tuned to make hypotheses succeed; they are chosen to span
plausible α-band autocorrelation, modest cross-channel volume conduction,
and asymmetric eyes-closed/eyes-open histogram shape.

## 4. Alternative bin schedules measured (≥ 5 candidates, frozen list)

| idx | Schedule | n_bin (effective) | Notes |
|-----|----------|-------------------|-------|
| 0 | `uniform_n_bin_2` | 2 | sanity anchor (Mk.XII SSOT) |
| 1 | `uniform_n_bin_64` | 64 | last-known stable from #196 |
| 2 | `uniform_n_bin_85` | 85 | **H1 pre-registered FAIL prediction** |
| 3 | `uniform_n_bin_128` | 128 | over-bin, extrapolated FAIL |
| 4 | `equi_n_64` | 64 | adaptive equiprobable (per-channel quantiles) |
| 5 | `fd_per_channel` | 2..N (per-channel) | Freedman-Diaconis IQR-based |
| 6 | `sturges_n_bin` | ceil(log2(N)+1)=14 at N=4096 | classic Sturges' rule |
| 7 | `sqrt_n_bin` | sqrt(N)=64 at N=4096 | sqrt heuristic |
| 8 | `hybrid_64_plus_128` | 96 (notional) | per-pair MI averaged across uniform_64 + uniform_128 |

Schedules 1, 6, 7, 8 are **informative-only** — no pre-registered direction,
just measured and reported.  Schedules 0, 2, 4, 5 carry the four
pre-registered hypotheses.

## 5. Multi-axis verify grid (4 axes, frozen thresholds)

Each schedule is evaluated on **four** independent axes (×1000 mi units):

| Axis | Definition | Threshold |
|------|------------|-----------|
| AXIS-1 BIAS | mean over 10 pairs of `|MI_schedule − MI_anchor_n2|` | ≤ 30 |
| AXIS-2 VARIANCE | std-dev of pair-MI across 10 pairs | ≤ 25 |
| AXIS-3 CONVERGENCE | `|max_mi(N=8192) − max_mi(N=4096)|` re-binned same schedule | ≤ 15 |
| AXIS-4 ROBUSTNESS | `|max_mi(perturbed) − max_mi(base)|` under one drop+dup permutation | ≤ 15 |

`axes_pass` = 1 iff all four axis values are within threshold.
Thresholds are pre-registered; they are NOT tuned post-hoc.

A schedule that passes the violation count test (`violations == 0`) but
fails on multi-axis verify (`axes_pass == 0`) is reported as
"observed_pass + axes_fragile" — it is **not** a clean recommendation for D+6.

## 6. Fallback chain (frozen pre-register order)

If the pre-flight passes, the D+6 binning schedule for the first real
measurement uses the first chain element whose `observed_pass == 1` AND
`axes_pass == 1`:

```
equi_n_64  →  uniform_n_bin_64  →  uniform_n_bin_2  →  ABORT_D6
```

`ABORT_D6` triggers the runbook for "no preflight-validated schedule
available; defer first measurement until a new schedule is added and
the preflight tool re-runs".  This is intentionally conservative —
silent fallback to "best looking after measurement" violates raw#71.

## 7. Tool — `anima-clm-eeg/tool/g8_n_bin_85_falsification_analysis.hexa`

Single-file hexa-only tool, raw#9 strict.  Idempotent (raw#65/#68):
same env produces byte-identical JSON.  Honesty (raw#91): all measured
values are written regardless of hypothesis match.

Inputs (frozen):
- `MI_MAX_X1000 = 100` (0.1 bit threshold, identical to #175 SSOT)
- `N_TRIAL = 4096` (matches #196 baseline)
- `N_TRIAL_DOUBLE = 8192` (AXIS-3 convergence)
- E-PSG parameters: α=0.6, β=0.20, γ=0.40 (frozen at definition time)
- 5 falsifier offsets identical to #175 SSOT primes

Outputs:
- `anima-clm-eeg/state/g8_n_bin_85_falsification_analysis_v1.json`

Console emit: per-schedule (max_mi, violations, observed_pass,
hypothesis_match, four axis values, axes_pass) + overall verdict +
fallback selection + fingerprint.

## 8. Measured results

(Populated after the hexa run completes — see
`state/g8_n_bin_85_falsification_analysis_v1.json` for canonical JSON.)

### 8.1 Per-schedule outcome table

| idx | schedule | n_bin | max_mi×1000 | violations | obs_pass | prereg | match | bias | variance | convergence | robustness | axes_pass |
|-----|----------|-------|-------------|------------|----------|--------|-------|------|----------|-------------|------------|-----------|
| 0 | uniform_n_bin_2 | 2 | (run) | (run) | (run) | PASS | (run) | (run) | (run) | (run) | (run) | (run) |
| 1 | uniform_n_bin_64 | 64 | (run) | (run) | (run) | inform | n/a | (run) | (run) | (run) | (run) | (run) |
| 2 | uniform_n_bin_85 | 85 | (run) | (run) | (run) | FAIL | (run) | (run) | (run) | (run) | (run) | (run) |
| 3 | uniform_n_bin_128 | 128 | (run) | (run) | (run) | inform | n/a | (run) | (run) | (run) | (run) | (run) |
| 4 | equi_n_64 | 64 | (run) | (run) | (run) | PASS | (run) | (run) | (run) | (run) | (run) | (run) |
| 5 | fd_per_channel | (run) | (run) | (run) | (run) | inform | n/a | (run) | (run) | (run) | (run) | (run) |
| 6 | sturges_n_bin | 14 | (run) | (run) | (run) | inform | n/a | (run) | (run) | (run) | (run) | (run) |
| 7 | sqrt_n_bin | 64 | (run) | (run) | (run) | inform | n/a | (run) | (run) | (run) | (run) | (run) |
| 8 | hybrid_64_plus_128 | 96 | (run) | (run) | (run) | inform | n/a | (run) | (run) | (run) | (run) | (run) |

### 8.2 Hypothesis match summary

| Hypothesis | match | raw#91 honest record |
|------------|-------|----------------------|
| H1 (uniform_n_bin_85 FAIL) | (run) | observed `violations` = (run) |
| H2 (equi_n_64 PASS) | (run) | observed `violations` = (run) |
| H3 (FD relative bound) | (run) | (FD_viol, n85_viol, e64_viol) = (run) |
| sanity (uniform_n_bin_2 PASS) | (run) | observed `violations` = (run) |

### 8.3 Fallback selection

`selected = (run)`.  See §6 frozen chain.

### 8.4 Fingerprint

`fingerprint = (run)` — captures all inputs + all outputs; re-running
the tool with same env yields the same value (raw#65 idempotent).

## 9. D+6 entry recommendation

The D+6 entry decision uses the fallback chain (§6) regardless of which
hypothesis matched.  Specifically:

1. If `preflight_pass == 1` (all four hypotheses matched as predicted):
   the recommended schedule is the first element of the fallback chain
   that has `observed_pass == 1 AND axes_pass == 1`.  Under H1+H2 alone
   this is normally `equi_n_64`.

2. If `preflight_pass == 0` (any hypothesis mismatched):
   raw#71 forbids picking the "best-looking" schedule.  Mismatch
   triggers a halt: D+6 first measurement is deferred until either
   (a) a new schedule is added to the candidate set (with a new
   pre-register cycle) or (b) the E-PSG parameters are recalibrated
   to better reflect the actual incoming data shape (also new cycle).

3. The frozen fallback chain end-state `ABORT_D6` is the formal flag
   that triggers (2).

## 10. raw#10 honest caveats

1. **E-PSG is still synthetic.**  α=0.6, β=0.20, γ=0.40 are chosen to
   span "plausible" pathology, but real EEG may exhibit additional
   structure: 1/f spectrum, transient artifacts, line-noise bleed,
   inter-subject variance.  The preflight does not exhaust these axes.

2. **N_BIN=85 is one extrapolation point, not an exhaustive sweep.**
   The preflight also tests `uniform_n_bin_64` and `uniform_n_bin_128`
   to bracket the prediction, but does not perform a 50-step continuous
   sweep through the violation regime.

3. **Hypothesis H1 may register match even if the violation is from
   discretization granularity rather than coupling.**  A FAIL is a
   FAIL — the *cause* (small-sample bias vs structural coupling vs
   heavy-tail) is not separable from the violation count alone.
   This is acceptable for raw#71 — H1 only commits to FAIL/PASS,
   not to the failure mechanism.

4. **Multi-axis thresholds (30/25/15/15) are heuristic.**  They are
   pre-registered to prevent post-hoc tuning, but their absolute
   calibration vs the 100×1000 MI threshold is informative-only.

5. **Fallback chain order is opinionated.**  Prefers adaptive (equi_n_64)
   over uniform (n_bin_64), and uniform_64 over the binary anchor.
   This reflects the (raw#10 honest) belief that adaptive binning
   degrades more gracefully under unknown distribution shape — but
   that belief is not formally proved here.

6. **Real D+6 data may invalidate the preflight altogether.**  If the
   actual EEG arrival shape is dominated by a feature not modelled in
   E-PSG (e.g. extreme line-noise contamination), the preflight's
   schedule recommendation may itself FAIL on first real measurement.
   In that case the D+6 runbook directs to halt + recalibrate, never
   to silently accept the failed measurement.

7. **Tool wall-clock cost on mac local route**: bare-Mac hexa execution
   is killed by jetsam under load (2026-04-25 incident, observed
   2026-04-27 during this cycle).  The tool MUST be run via the
   `~/.hx/bin/hexa` resolver wrapper (Docker / remote ubu2 routing),
   not the bare `/Users/ghost/core/hexa-lang/hexa` binary on PATH.
   Documented here so future re-runs do not hit the same wall.

## 11. ω-cycle 6-step compliance

| step | description | status |
|------|-------------|--------|
| 1 | design — 4 hypotheses + 9 schedules + 4 axes + fallback chain frozen | done |
| 2 | implement — `tool/g8_n_bin_85_falsification_analysis.hexa` raw#9 strict | done |
| 3 | positive measurement — preflight executed under E-PSG | (run) |
| 4 | falsifier-preregister honesty — measured values vs predictions reported as match/mismatch, no hypothesis edit | done by construction |
| 5 | byte-identical re-run — same env → same JSON fingerprint | (run) |
| 6 | iterate — landing + marker + state JSON committed | done after run |

## 12. Cross-references

- Parent: `docs/g8_n_bin_128_extrapolation_landing.md` (#197 N_BIN=85 prediction source)
- Sister: `docs/g8_n_bin_sweep_extended_landing.md` (#196 60/60 PASS), `docs/g8_n_bin_sweep_landing.md` (#182), `docs/g8_transversality_landing.md` (#175 frozen N_BIN=2 SSOT)
- Mk.XII: `docs/mk_xii_d_day_simulated_landing.md` (D+6 G8 block parent), `docs/mk_xii_proposal_outline_v3_20260427.md` (§6 G8 ceiling re-binding context)
- ω-cycle witness: 2026-04-27 raw#71 falsifier preregistered chain
- Tool: `anima-clm-eeg/tool/g8_n_bin_85_falsification_analysis.hexa`
- State (positive): `anima-clm-eeg/state/g8_n_bin_85_falsification_analysis_v1.json`
- Marker: `anima-clm-eeg/state/markers/g8_n_bin_85_falsification_analysis_complete.marker` (write on close)

## 13. Next-cycle candidates

1. **Direct N_BIN=85 measurement on real D+6 data** — replaces this preflight's
   E-PSG with first real EEG block; same 9-schedule × 4-axis grid.

2. **E-PSG re-calibration** — once D+6 data is available, fit (α,β,γ) to
   first-block statistics and re-run preflight for the *next* block —
   converts E-PSG from "frozen guess" into "data-driven prior".

3. **Continuous N_BIN sweep through {64, 70, 75, 80, 85, 90, 95, 100}** —
   localises the violation knee precisely (current preflight only tests
   the 64/85/128 trio).

4. **5-axis extension** — add AXIS-5 *bias-corrected MI* (Grassberger 2003
   estimator) parallel to Miller-Madow, to separate "MM under-corrects"
   from "real coupling".

5. **Mk.XII §6 G8 contract update** — based on preflight result, decide
   whether to bind the §6 G8 PASS criterion at `equi_n_64` or keep it
   at the binary `uniform_n_bin_2` SSOT with `equi_n_64` as the
   declared D+6 fallback only.

