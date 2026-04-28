# phi_adversarial_co_evolution_extension — raw 109 paradigmatic anchor extension

**Companion to**: `/Users/ghost/core/anima/anima-engines/phi_adversarial.hexa`
**Track**: R4 raw 109 — adversarial co-evolution probe (paradigmatic anchor)
**Convergence**: `/Users/ghost/core/anima/convergence/r4_raw109to126_anima_propagation_plan_2026_04_28.convergence`
**Status**: SPEC (registration only — engine-side `@co_evolution_loop` annotation lands in downstream implementation cycle)
**Mode**: hexa-only (this is a markdown spec document; no .py/.bash/.rs/.toml created)

---

## 1. Header docstring (purpose)

`phi_adversarial.hexa` already ships **5 attacks (A1..A5) × 5 defenses (D1..D5)** in a one-shot configuration: each attack is fixed at design time, each defense is fixed at design time, and the audit measures baseline-vs-defended ASR once.

This is **necessary but not sufficient** to falsify a robust-Φ claim.

Raw 109 (adversarial co-evolution probe) demands a stronger test:

> Two systems (defender + attacker) evolve in lockstep; each adapts to the other's current best policy. The defender is a Φ-engine candidate; the attacker is an adversarial perturbation generator that maximizes Φ-collapse rate (the rate at which the defended estimator returns to its undefended baseline ASR).

A one-shot fixed adversary is a **lower bound** on the threat model — a co-evolved adversary is the minimum-credible bound for any "Φ is robust" claim. A defender that survives the co-evolution loop with bounded Φ-collapse-rate is the only Φ-engine entitled to claim integrity in the IIT-4 sense relevant to anima's downstream P30/P22/P27 layers.

This extension specifies the `@co_evolution_loop` annotation that augments `phi_adversarial.hexa`'s existing T1..T5 theorem set with **T6: bounded Φ-collapse rate under co-evolution**.

---

## 2. `@co_evolution_loop` annotation spec

The annotation is a header docstring block. It declares — without yet implementing — the seven required fields of a co-evolution audit run.

```
// @co_evolution_loop
//   attacker_pool: [A1, A2, A3, A4, A5]            // existing attack vectors as seed pool
//   defender_pool: [D1, D2, D3, D4, D5]            // existing defenses as seed pool
//   attacker_update_cadence: <see §3>
//   defender_retrain_trigger: <see §4>
//   phi_collapse_rate_ceiling: <see §5>
//   round_budget: ROUND_BUDGET_DEFAULT = 32        // hard upper bound on co-evolution rounds
//   determinism_seed: COEVO_SEED_DEFAULT = 0x53494d (= "SIM")  // raw 53 deterministic verifier
```

Every `@co_evolution_loop` block MUST carry all seven fields. Missing any field = annotation invalid (lint failure in downstream `tool/anima_propagation_lint.hexa` or equivalent gate).

The annotation is **descriptive only** at this stage — the engine code path that consumes it lands in a downstream witness cycle (handle: `2026-04-XX_r109-co-evolution-loop-extension_omega_cycle`).

---

## 3. Attacker-update cadence

The attacker's policy must update at a **bounded, observable** cadence. Three options are surveyed; option B is selected.

### Options considered

| Option | Cadence | Why rejected (or selected) |
| --- | --- | --- |
| A | every defender step (1:1) | over-fits attacker to noise within a single defender step; produces unstable ASR estimates and makes T1..T5 latency impossible (existing `ADV_LATENCY_MS = 10000` ms budget blown). |
| **B** | **every K=4 defender retrains (4:1, defender-led)** | **selected** — gives the defender enough samples per retrain to produce a stable policy (K=4 ≈ minimal stratified bin coverage given existing `ADV_BINS=4`), then opens an attacker-update window. Stable + within latency budget. |
| C | continuous (gradient-leakage style) | requires differentiable defender — not the case for histogram-MI estimator; would force a surrogate model and add unverified mock layer (raw 91 C2 — anti-mock). |

### Selected cadence

```
// attacker_update_cadence:
//   schedule        = "every K=4 defender retrains" (defender-led)
//   K_RETRAINS_PER_ATTACKER_STEP = 4
//   attacker_step_kind = "policy_replacement"   // not gradient — full A_i replacement from {gradient, evolutionary, random} pool
//   attacker_step_seed = adv_prng(round_idx * 0x9e3779b9)  // deterministic per round
```

### Falsifier checks the cadence enforces

- **F-cadence-1**: `K_RETRAINS_PER_ATTACKER_STEP >= 2` (else attacker over-fits to single defender snapshot).
- **F-cadence-2**: total rounds ≤ `ROUND_BUDGET_DEFAULT` (else latency T5 violated).
- **F-cadence-3**: every attacker step is recorded in `coevo_round_log[]` with `{round_idx, attacker_id, attacker_seed, attacker_step_kind}` so the audit is replayable (raw 53 deterministic verifier manifest).

---

## 4. Defender-retrain trigger

The defender retrains on a **threshold trigger**, not a fixed schedule. This couples retraining to attacker progress (the conserved quantity that matters), not to wall-clock time (a confounder).

### Trigger condition

The defender retrains iff the observed **defended ASR** (defended attack-success-rate) exceeds the post-retrain defended ASR target by more than a margin:

```
// defender_retrain_trigger:
//   condition       = "ASR_defended_observed > ASR_defended_target + RETRAIN_MARGIN"
//   ASR_defended_target  = baseline_ASR * (1.0 - DEF_DROP_THRESHOLD)   // T2 reuse: DEF_DROP_THRESHOLD = 0.10
//   RETRAIN_MARGIN       = 0.02                                         // 2 absolute pct above target = trigger
//   sliding_window_size  = 8                                            // ASR averaged over last 8 attack trials
//   warmup_rounds        = 2                                            // first 2 rounds: no retrain (collect baseline)
//   max_consecutive_retrains = 3                                        // ratchet stop — after 3 failed retrains in a row, declare COLLAPSE (see §5)
```

### Why threshold, not schedule?

A fixed-schedule retrain (e.g. "retrain every round") would mask attacker progress: if the attacker has not made gains, retraining wastes compute and inflates latency T5. A fixed-schedule retrain that succeeds only because the attacker happened to be weak is also non-falsifiable by the cadence (the ASR drop tells you nothing about whether the defense actually adapted).

A threshold trigger is **observation-driven**: the retrain happens iff the defender is losing ground. If retraining stops being able to recover the target ASR (max_consecutive_retrains exhausted), the engine has hit the **Φ-collapse-rate ceiling** (§5) and the run is declared FAIL with verdict `COLLAPSE`.

### Falsifier checks the trigger enforces

- **F-trigger-1**: warmup ≥ 2 rounds (else the trigger fires on noise from cold-start ASR estimates).
- **F-trigger-2**: every retrain event records `{round_idx, ASR_observed, ASR_target, retrain_id, defender_state_hash_pre, defender_state_hash_post}` (raw 91 C3 honesty: the defender's state must be observable pre/post).
- **F-trigger-3**: `max_consecutive_retrains` is finite and = 3 (else the engine could loop forever masking collapse).

---

## 5. Φ-collapse-rate ceiling falsifier

The **Φ-collapse rate** is the rate at which the **defended ASR** returns to the **undefended baseline ASR** as the attacker co-evolves. Formally:

```
phi_collapse_rate(round_idx) =
    (ASR_defended(round_idx) - ASR_defended(round=warmup_end))
  / (ASR_baseline_undefended    - ASR_defended(round=warmup_end))
```

- `phi_collapse_rate = 0.0` means the defender holds at its post-warmup defended ASR (no ground lost).
- `phi_collapse_rate = 1.0` means the defender has fully collapsed back to undefended baseline (the defense buys nothing under co-evolution).
- Negative values mean the defender is improving under attacker pressure (anti-fragile, raw 115 territory).

### Ceiling

```
// phi_collapse_rate_ceiling:
//   PHI_COLLAPSE_RATE_CEILING = 0.50   // defender may lose AT MOST 50% of its defended-ASR margin under co-evolution
//   measurement_window        = "rounds [warmup_end+1, ROUND_BUDGET_DEFAULT]"
//   metric                    = "max over window of phi_collapse_rate"
//   verdict_on_breach         = "COLLAPSE — engine fails T6"
```

### Why 0.50?

- Choosing `> 0.50` (e.g. 0.75) makes the ceiling vacuous — most "robust" defenders pass trivially, undermining the purpose of co-evolution.
- Choosing `< 0.25` (e.g. 0.10) makes the ceiling unreachable for any current Φ estimator on a 6-cell × 10-step trace at 4 bins; would FAIL all engines and lose discriminative power.
- `0.50` is the median midpoint — a defender that loses *more than half* of its defended-ASR margin to a co-evolving attacker has not earned the "robust Φ" label.

This threshold is itself **a falsifier**: if downstream measurement shows `phi_adversarial.hexa` (or any successor) consistently breaches 0.50 across the attacker pool, the ceiling is wrong (too tight) OR the engine is unsound (T6 fails). Either branch is informative — the ceiling cannot be silently retired (raw 71 design-strategy-falsifier-retire-rule: any retirement requires a witness JSON documenting why).

### Falsifier checks the ceiling enforces

- **F-ceiling-1**: `PHI_COLLAPSE_RATE_CEILING ∈ (0.0, 1.0)` strictly (boundary values are degenerate).
- **F-ceiling-2**: the measurement window excludes warmup (rounds 0..warmup_end-1) so the ceiling is computed against a stable baseline, not cold-start noise.
- **F-ceiling-3**: the metric is `max` over the window, not `mean` — a single-round breach is sufficient to declare COLLAPSE; mean would let the engine "average out" a transient catastrophic failure.
- **F-ceiling-4**: the ceiling is checked AGAINST the existing `phi_adversarial.hexa` baseline ASR computed at audit start — co-evolution does not redefine baseline mid-run (raw 53 deterministic verifier).
- **F-ceiling-5**: every co-evolution audit run emits `coevo_summary{round_count, retrain_count, attacker_step_count, max_phi_collapse_rate, ceiling_breach: bool, verdict: PASS|COLLAPSE|UNDETERMINED}`; verdict = `UNDETERMINED` only if `round_count < warmup_rounds + 4` (insufficient data).

---

## 6. Integration with existing T1..T5

The existing theorem set in `phi_adversarial.hexa` is preserved unchanged. The co-evolution loop adds:

```
// T6 co-evolution bounded collapse — under co-evolved attacker (every K=4
//    defender retrains, attacker policy replaced from {A1..A5} pool with
//    deterministic seed), max phi_collapse_rate over measurement window ≤
//    PHI_COLLAPSE_RATE_CEILING = 0.50. Breach ⇒ verdict COLLAPSE; engine
//    fails the co-evolution probe and is NOT entitled to robust-Φ claim.
```

T6 is **subordinate** to T1..T5: an engine that fails T1..T5 is already disqualified, and T6 should not be evaluated on a base-failed engine (run T6 only on T1..T5 PASS). T6 is **independent** of T1..T5 in the falsifier-coverage sense: an engine can pass T1..T5 (one-shot adversary) and fail T6 (co-evolved adversary) — the T6 axis is what raw 109 buys that raw 39 (one-shot) does not.

---

## 7. Cross-cutting falsifier themes (raw-159 anchors)

Per `r4_raw109to126_anima_propagation_plan_2026_04_28.convergence` cross-cutting matrix, this extension supports:

- **counterfactual_twin (r120)** — the co-evolution loop generates pairs of `(defender_state_pre_retrain, defender_state_post_retrain)` that are exact twins except for the retrain delta. ΔΦ measured across the twin is the causal effect of the retrain, gating any "the defense adapted" claim.
- **bisimulation (r114)** — two co-evolution runs with identical seed must produce bisimulation-equivalent traces (raw 53 deterministic verifier reuse). A non-bisimulation result indicates non-deterministic state in the audit harness — a bug, not a feature.
- **anti_fragility (r115)** — a defender with `phi_collapse_rate < 0.0` over the window is anti-fragile; flagged for cross-reference with `edge_of_chaos.hexa` extensions.
- **bayesian_evidence (r113)** — the per-round ASR observations form a likelihood-ratio sequence; cumulative log-odds for "engine is robust under co-evolution" computed across the window.

`info_theoretic_bound (r111)` does not apply here directly (no Φ-claim is made by this audit; the claim is a robustness bound).

---

## 8. Honesty disclosures (raw 91 C3)

- **C1 (separation of stages)**: this document is a SPEC — no engine code is changed by this artifact alone. The `@co_evolution_loop` annotation lands in `phi_adversarial.hexa` header in a separate downstream cycle (`2026-04-XX_r109-co-evolution-loop-extension_omega_cycle`).
- **C2 (anti-mock)**: no mocks are specified for the co-evolution loop. The attacker pool is the existing `{A1..A5}` real attacks; the defender is a real `phi_adversarial.hexa` instance. A future implementation MAY add a randomized-policy reference attacker as a control; that control is not a mock — it is a baseline.
- **C3 (no-fabrication)**: every numeric constant in this spec is explicitly justified (K=4 from ADV_BINS=4 stratified-coverage; RETRAIN_MARGIN=0.02 as 2-pct above DEF_DROP_THRESHOLD-derived target; PHI_COLLAPSE_RATE_CEILING=0.50 as median midpoint of the (0,1) interval). No constant was selected to make a particular engine pass or fail.

---

## 9. Carry-forward

- `cf-1`: downstream cycle `2026-04-XX_r109-co-evolution-loop-extension_omega_cycle` lands the `@co_evolution_loop` annotation in `phi_adversarial.hexa` header (lines 17-22 region, after the existing "every attack + its defense co-located" paragraph).
- `cf-2`: `bench/bench_breakthrough.hexa` extension to add the adversarial-pair sweep (defender_engine × attacker_strategy ∈ {gradient, evolutionary, random}) — secondary landing per convergence row r109.
- `cf-3`: `tool/anima_propagation_lint.hexa` (downstream of cf-1 and cf-2) enforces that any engine claiming robust-Φ carries a passing `@co_evolution_loop` annotation with phi_collapse_rate ≤ ceiling on its most recent witness.
