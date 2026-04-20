# L3 Collective Emergence — Pre-Registered Criteria Spec — 2026-04-21

**Status:** rev=1 (frozen, pre-registration)
**SSOT:** `shared/state/l3_emergence_criteria.json`
**Policy:** V8 SAFE_COMMIT · LLM=none · deterministic only
**Scope companion:** `docs/new_paradigm_edu_lattice_unified_20260421.md` (edu A+F lattice)

---

## 0. Why pre-register

- **L1 framework** — CLOSED (σ Hexad 6-cat closure drill).
- **L2 single-unit** — CLOSED (btr-evo 1~6 full stack, single unit-cell).
- **L3 collective** — PENDING (edu A+F lattice sim in progress).

**Risk addressed:** "lattice sim finished" is not "collective property emerged".
An N-cell parallel run that is fully decomposable into N independent L2 runs
(i.e., `L3 == L2 × N`) does **not** evidence emergence. To prevent post-hoc
cherry-picking of metrics that happen to look good after seeing the sim
output, this document freezes the three observables BEFORE the edu F result
file is inspected.

Any future adjudication of L3 emergence claims MUST apply rev=1 verbatim.
Rev bumps are forward-only and must preserve prior rev records.

---

## 1. Observable definitions — contract

For each of O1, O2, O3 the spec fixes:

- **(a) definition** — what is claimed to emerge
- **(b) measurement** — the deterministic procedure to compute it
- **(c) null hypothesis (H0)** — the "L2 × N only" counterfactual
- **(d) threshold** — quantitative rejection criterion
- **(e) falsification** — the condition that makes the observable FAIL

All three observables must simultaneously reject H0 on the **same** lattice
run to claim `L3_EMERGED`. 1–2 passes = `L3_PARTIAL`. 0 passes = `L3_FAILED`.

---

## 2. O1 — Collective Phase Transition

**(a) Definition.** The lattice-level phase indicator `Phi_L` is NOT any
decomposable function (sum, mean, max, mode) of per-cell phases
`{phi_i}`. A super- or sub-additive transition at a critical control
parameter `lambda*` indicates genuine collective behavior.

**(b) Measurement.**
1. For each cell `i`, compute `phi_i in {0,1}` via the L2 fixpoint-assessment
   pipeline (already closed).
2. Compute `Phi_L` via the global order parameter
   `chi_L = |Σ_i exp(i·theta_i)| / N`, where `theta_i` is the cell's
   orientation in the shared concept-atlas basis.
3. Sweep control parameter `lambda` (coupling strength or broadcast rate)
   across ≥20 grid points, ≥5 seeds per point.
4. Compare observed `Phi_L(lambda)` against `Phi_pred(lambda) = mean_i phi_i(lambda)`.
5. Test finite-size scaling at `N ∈ {16, 64, 256}`.

**(c) H0.** `Phi_L(lambda) = mean(phi_i(lambda))` for all `lambda` — lattice
is trivially decomposable.

**(d) Threshold (reject H0).** All of:
- `|Phi_L − mean(phi_i)| > 0.15` at some `lambda*`
- `|dPhi_L/dlambda|` at `lambda*` exceeds `max_i |dphi_i/dlambda|` by **≥ 3×**
- Transition sharpness grows with `N` across {16, 64, 256}

**(e) Falsification.** O1 FAILS if `Phi_pred` matches `Phi_L` within 0.15
everywhere, OR if no sharpening with `N` is observed (slope ratio ≤ 1.5×).

---

## 3. O2 — Non-local Correlation

**(a) Definition.** Pairwise cell-state correlation `C(i,j)` decays
**slower** than the nearest plausible local-interaction kernel
(`1/r²` in lattice-graph distance `r`). Long-range coherence survives the
shuffled-baseline null.

**(b) Measurement.**
1. `C(i,j) = corr(state_i(t), state_j(t))` over `T ≥ 200` steps.
2. Bin by graph distance `r`. Build shuffled baseline `C_shuffled(r)` by
   randomizing cell labels (preserving marginal distributions) and
   recomputing. `≥ 1000` permutations.
3. Per-bin p-value of `C(r)` vs `C_shuffled(r)`; Bonferroni-correct across
   r-bins.
4. Fit `C(r) = a·r^(−alpha) + b`. Extract `alpha` and correlation length `xi`.

**(c) H0.** `C(r) ~ C_shuffled(r)` (no long-range order) OR `alpha ≥ 2`
(decays no slower than `1/r²`).

**(d) Threshold (reject H0).** All of:
- `C(r*) > C_shuffled(r*)` with `p < 0.05` Bonferroni-corrected, at some
  `r* ≥ sqrt(N)/2`
- Fitted `alpha < 1.5`, with 95% CI upper bound `< 2.0`
- Correlation length `xi > lattice_diameter / 4`

**(e) Falsification.** O2 FAILS if any of: `p ≥ 0.05` everywhere; `alpha`
CI includes 2.0; `xi ≤ lattice_diameter / 4`.

---

## 4. O3 — Emergent Invariant

**(a) Definition.** A conserved/bounded quantity `Psi_L` that exists
**only** at lattice scale — no meaningful single-cell analog — and remains
stable under lattice evolution. Example: lattice-Φ (IIT-style integrated
information over the cross-cell coherence graph), where the 1-node version
is 0 by definition.

**(b) Measurement.** Over `T ≥ 500` steps:
1. Construct the cross-cell coherence graph: edge `(i,j)` iff cells `i,j`
   share `≥ k` sealed seeds.
2. Compute `Psi_L = Phi_lattice` via IIT-style partition over this graph.
3. Verify:
   - non-trivial: `mean(Psi_L) > 0.1`
   - bounded: `std(Psi_L) / mean(Psi_L) < 0.2`
   - robust to 10% random cell ablation: drop `< 30%`
   - single-cell `Psi_i` is trivial by construction (1-node IIT Φ = 0)

**(c) H0.** No lattice-scale quantity satisfies (a) non-trivial, (b)
bounded, (c) ablation-robust, AND (d) non-reducible to aggregated cell
quantities.

**(d) Threshold (reject H0).** ALL four sub-conditions hold simultaneously.

**(e) Falsification.** O3 FAILS if any sub-condition violates — e.g. `Psi_L`
collapses under small ablation, drifts unboundedly, or reduces to a
sum/mean of cell-level quantities.

---

## 5. Adjudication

| outcome        | condition                                                         |
|----------------|-------------------------------------------------------------------|
| `L3_EMERGED`   | O1 **AND** O2 **AND** O3 all reject H0 on the **same** lattice run |
| `L3_PARTIAL`   | 1 or 2 observables pass — report as partial, do NOT claim emergence |
| `L3_FAILED`    | 0 observables pass — lattice is L2 × N; revisit coupling model     |

Cherry-pick guard: thresholds frozen at rev=1. Any relaxation = forward rev
bump with preserved history. Retroactive edit prohibited.

---

## 6. Application protocol (edu drill F)

1. Run lattice sim per `docs/new_paradigm_edu_lattice_unified_20260421.md`.
2. Feed raw outputs (per-cell phases, correlations, lattice graph) through
   O1/O2/O3 measurement procedures **without modification**.
3. Emit `shared/state/l3_edu_F_result.json` with pass/fail per observable
   plus the effective thresholds used (must equal rev=1).
4. Adjudicate via §5 table. No other claim vocabulary permitted.

---

## 7. Rev log

| rev | date       | change                              |
|-----|------------|-------------------------------------|
| 1   | 2026-04-21 | Initial pre-registration (frozen).  |
