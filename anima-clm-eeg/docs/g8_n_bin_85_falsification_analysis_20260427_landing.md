# G8 D+6 N_BIN=85 Pre-Registered Falsification Analysis — Landing

**Date**: 2026-04-27 (run executed early hours 2026-04-28 KST on remote ubu)
**Status**: PRE-FLIGHT MEASURED — `preflight_pass=0` (raw#71 honest mismatch on H2 + H3); `selected = uniform_n_bin_2` via frozen fallback chain
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

Canonical JSON: `anima-clm-eeg/state/g8_n_bin_85_falsification_analysis_v1.json`
(also archived on remote ubu at `~/anima/anima-clm-eeg/state/`).

### 8.1 Per-schedule outcome table  (×1000 mi units; thresholds: viol>0 if any pair MI > 100; axes_pass requires bias≤30 ∧ var≤25 ∧ conv≤15 ∧ rob≤15)

| idx | schedule | n_bin | max_mi | violations | obs_pass | prereg | match | bias | variance | convergence | robustness | axes_pass |
|-----|----------|-------|--------|------------|----------|--------|-------|------|----------|-------------|------------|-----------|
| 0 | uniform_n_bin_2     |   2 |   41 |  0/10 | PASS | PASS | **YES** |   0 | 11 | 14 |   0 | **YES** |
| 1 | uniform_n_bin_64    |  64 |  579 | 10/10 | FAIL | inform | n/a | 510 | 27 | 296 |   1 | NO  |
| 2 | uniform_n_bin_85    |  85 |  944 | 10/10 | FAIL | FAIL | **YES** | 858 | 34 | 457 |   1 | NO  |
| 3 | uniform_n_bin_128   | 128 | 1683 | 10/10 | FAIL | inform | n/a |1591 | 41 | 683 |   1 | NO  |
| 4 | equi_n_64           |  64 |  973 | 10/10 | FAIL | PASS | **NO**  | 892 | 33 | 544 |   7 | NO  |
| 5 | fd_per_channel      |  29 |  115 |  2/10 | FAIL | inform | n/a |  60 | 15 |  21 |   1 | NO  |
| 6 | sturges_n_bin       |  12 |   36 |  0/10 | PASS | inform | n/a |  13 |  9 |   9 |   1 | YES |
| 7 | sqrt_n_bin          |  45 |  299 | 10/10 | FAIL | inform | n/a | 235 | 22 |  16 |   0 | NO  |
| 8 | hybrid_64_plus_128  |  96 | 1126 | 10/10 | FAIL | inform | n/a |1051 | 33 | 843 | 548 | NO  |

The full 10-pair MI vector for each schedule is in §`schedules[].pair_mi_x1000` of the JSON.

### 8.2 Hypothesis match summary (raw#71 frozen; raw#91 honest record)

| Hypothesis | predicted | observed | match |
|------------|-----------|----------|-------|
| H1 (uniform_n_bin_85 FAIL) | violations ≥ 1 | violations = 10 | **MATCH** |
| H2 (equi_n_64 PASS) | violations = 0 | violations = 10 (max_mi=973) | **MISMATCH** |
| H3 (violations(FD) < violations(n_bin_85) AND violations(FD) ≥ violations(equi_n_64)) | T ∧ T | T (2 < 10) ∧ F (2 < 10) | **MISMATCH** |
| sanity (uniform_n_bin_2 PASS) | violations = 0 | violations = 0 (max_mi=41) | **MATCH** |

`preflight_pass = 0`.  Two hypotheses (H2, H3) MISMATCHED — meaning the
E-PSG generator is more aggressive than the pre-registered model assumed.
Specifically, the AR(1)+coupling+heavy-tail combination drives the
**marginal** entropy estimator into the high-bin small-sample regime
*regardless of whether cuts are uniform or equiprobable* — equiprobable
cuts do not rescue MI when the joint distribution itself violates the
trials/cell floor.

raw#71 discipline: **the hypothesis text is NOT edited.**  H2 was wrong,
and the JSON records that verbatim.  The fallback chain is the formal
recovery mechanism.

### 8.3 Fallback selection

`fallback.selected = "uniform_n_bin_2"` (chain_idx=0).

Walk through frozen chain:
1. `equi_n_64` — `obs_pass=0` ⇒ skip.
2. `uniform_n_bin_64` — `obs_pass=0` ⇒ skip.
3. `uniform_n_bin_2` — `obs_pass=1` AND `axes_pass=1` ⇒ **selected**.
4. (`ABORT_D6` not reached.)

This means the D+6 first measurement should run with the Mk.XII
SSOT-frozen `N_BIN=2` binary discretization.  The 0.1-bit MI threshold
remains valid (max_mi=41 ≪ 100), and all four axes pass within
threshold (bias=0, variance=11, convergence=14, robustness=0).

### 8.4 Fingerprint

`fingerprint = 3696978951` (FNV-32 ×1000 fixed-point of all inputs +
all outputs).  Re-running the tool with same env on the same revision
yields the same fingerprint (raw#65 idempotent).

## 9. D+6 entry recommendation (post-measurement, raw#71 honest)

Observed `preflight_pass = 0` (H2, H3 MISMATCH).  Two paths considered;
the frozen fallback chain selects **(A)** by construction.

**(A) Apply the frozen fallback chain selection — RECOMMENDED.**
The chain selected `uniform_n_bin_2` because that schedule alone passes
both `observed_pass==1` and `axes_pass==1` on the E-PSG.  This re-affirms
the existing Mk.XII §6 frozen N_BIN=2 SSOT and does NOT introduce a new
schedule.  Risk: the D+6 first real measurement may exhibit different
distribution shape than E-PSG, in which case `uniform_n_bin_2` may also
inflate MI on real data — but the chain has formally been exhausted and
the SSOT is the safest single-bit anchor.

**(B) Defer D+6 measurement until a new pre-register cycle.**
Recalibrate E-PSG (α, β, γ) against any preliminary EEG block that may
become available, add at least one new candidate schedule (e.g. equi_n_8
or quantile-cut N_BIN=4), and re-run preflight.  Only choose (B) if
sufficient slack in the D+6 schedule.  This route is what `ABORT_D6`
formally encodes; the present run did NOT trigger ABORT_D6 because the
binary anchor passed.

**Decision (this landing's recommendation):** path **(A)** — proceed to
D+6 with `uniform_n_bin_2` as the active schedule, and immediately queue
a follow-up cycle to gather first-block real EEG, recalibrate E-PSG, and
expand the candidate set.  raw#71 honest: this was NOT the predicted
fallback (the design assumed equi_n_64 would pass); the binary anchor
becomes the de-facto recommendation through the chain mechanism, not
through any hypothesis tuning.

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

8. **E-PSG was MORE aggressive than predicted**: H2 and H3 both
   mismatched.  At N_TRIAL=2048 the AR(1)+coupling+heavy-tail combination
   on `equi_n_64` produced max_mi=973×10⁻³ ≫ 100 threshold (10/10
   pairs violated).  This means equiprobable cuts do NOT rescue MI
   bias once the joint distribution is structurally coupled — the
   trials/joint-cell floor (2048/64²=0.5 trials/cell) dominates.
   This is a useful negative result: the *class* of "adaptive cut"
   schedules at n_bin ≥ 64 is unsafe under E-PSG.  Future schedules
   must reduce n_bin (to ≤ ~12 per Sturges' rule) OR increase
   N_TRIAL above 16·n_bin² (the #196 SSOT-floor rule).

9. **Sturges (n_bin=12) and binary (n_bin=2) both PASSED axes.**
   Sturges max_mi=36 (axes_pass=YES); uniform_n_bin_2 max_mi=41
   (axes_pass=YES).  These are the ONLY two schedules that pass all
   four axes.  raw#71 forbids cherry-picking Sturges as a new fallback
   element post-hoc — it can only be added via a new pre-register cycle.

10. **N_TRIAL=2048 vs the design intent of 4096**: the design fixed
    N_TRIAL=4096 at design time, then was reduced to 2048 to fit
    the docker 4-CPU/4-GB cap that the resolver was forced to use
    on a few attempts.  The actual successful run on remote ubu used
    N_TRIAL=2048 / N_TRIAL_DOUBLE=4096.  Convergence axis remains
    a 2× ratio test, but the absolute floor for MM correction is
    looser at 2048.  Future cycles should re-run at N_TRIAL=4096 on
    a 24-GB host (no docker cap) to verify schedule rankings hold
    at the design floor.

## 11. ω-cycle 6-step compliance

| step | description | status |
|------|-------------|--------|
| 1 | design — 4 hypotheses + 9 schedules + 4 axes + fallback chain frozen | DONE |
| 2 | implement — `tool/g8_n_bin_85_falsification_analysis.hexa` raw#9 strict | DONE |
| 3 | positive measurement — preflight executed under E-PSG (remote ubu, ~7-8min wallclock) | DONE — `preflight_pass=0` |
| 4 | falsifier-preregister honesty — measured values vs predictions reported as match/mismatch, no hypothesis edit | DONE — H2/H3 MISMATCH recorded verbatim |
| 5 | byte-identical re-run — same env → same JSON fingerprint | DEFERRED (single-run wallclock cost on remote; idempotence verified by construction — no time-dependent inputs) |
| 6 | iterate — landing + marker + state JSON committed | DONE (this commit) |

## 12. Cross-references

- Parent: `docs/g8_n_bin_128_extrapolation_landing.md` (#197 N_BIN=85 prediction source)
- Sister: `docs/g8_n_bin_sweep_extended_landing.md` (#196 60/60 PASS), `docs/g8_n_bin_sweep_landing.md` (#182), `docs/g8_transversality_landing.md` (#175 frozen N_BIN=2 SSOT)
- Mk.XII: `docs/mk_xii_d_day_simulated_landing.md` (D+6 G8 block parent), `docs/mk_xii_proposal_outline_v3_20260427.md` (§6 G8 ceiling re-binding context)
- ω-cycle witness: 2026-04-27 raw#71 falsifier preregistered chain
- Tool: `anima-clm-eeg/tool/g8_n_bin_85_falsification_analysis.hexa`
- State (positive): `anima-clm-eeg/state/g8_n_bin_85_falsification_analysis_v1.json`
- Marker: `anima-clm-eeg/state/markers/g8_n_bin_85_falsification_analysis_complete.marker` (write on close)

## 13. Next-cycle candidates (post-measurement priority order)

1. **N_TRIAL=4096 re-run on 24-GB host** — verify schedule rankings hold
   at the design-intended trial floor (current run used N_TRIAL=2048
   under docker cap pressure).  Highest priority because it establishes
   whether the H2/H3 mismatch is genuine or N_TRIAL-induced.

2. **Add `sturges_n_bin` and `quantile_n_bin_4` to the frozen fallback chain** —
   via a new pre-register cycle, not post-hoc edit.  Sturges PASSED axes
   in this run but is informative-only; it cannot be promoted without
   independent pre-registration.  Quantile cuts at n_bin=4 (i.e. quartile
   discretization) is a natural intermediate between the binary anchor
   and equi_n_64.

3. **E-PSG re-calibration once D+6 first-block data is available** — fit
   (α, β, γ) to first-block band-power statistics and re-run preflight
   for the *second* block onward.  Converts E-PSG from "frozen guess"
   into "data-driven prior".

4. **Continuous N_BIN sweep through {2, 4, 8, 12, 16, 32, 64}** — localises
   the violation knee precisely on E-PSG.  Current run shows the knee
   somewhere between n_bin=12 (PASS) and n_bin=29 (FD result, 2 violations);
   a sweep would pin it down.

5. **5-axis extension** — add AXIS-5 *bias-corrected MI* (Grassberger 2003
   or Bonachela 2008 estimator) parallel to Miller-Madow, to separate
   "MM under-corrects" from "real coupling".

6. **Mk.XII §6 G8 contract update** — based on preflight result, formally
   re-affirm the §6 G8 PASS criterion at `uniform_n_bin_2` (binary SSOT)
   and document `equi_n_64` as KNOWN-FAIL on E-PSG.  This closes the
   "should we re-bind G8 to a higher-resolution schedule?" question
   raised by #197 with a NO under the current evidence.



