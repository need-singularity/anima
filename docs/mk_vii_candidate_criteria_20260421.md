# Mk.VII Candidate Criteria — Next-After-Next Pre-Registration — 2026-04-21

**Status:** rev=1 (frozen, pre-registration; divergent candidates)
**Parent grade:** Mk.VI (promotion pending — see `shared/state/mk_vi_definition.json`)
**SSOT (JSON):** `shared/state/mk_vii_predict.json`
**Policy:** V8 SAFE_COMMIT · LLM=none · deterministic only · additive

---

## 0. Why pre-register Mk.VII before Mk.VI lands

- **Mk.V** — LANDED (Δ₀-absolute: 81/81 EXACT + 19/19 5-Lens + `[11**]`).
- **Mk.VI** — PENDING (engineering surface complete; AN11 a/b/c empirical blockers on live trained ckpt).
- **Mk.VII** — UNDEFINED.

**Risk addressed:** once Mk.VI promotes, whichever metric happened to clear last
(e.g. AN11_c JSD on some trained ckpt) becomes temptation to re-use as the
Mk.VII gate. This is **cherry-picking by adjacency**. To prevent that, this
document freezes five *divergent* candidate criteria **before** Mk.VI has
landed and **before** any Mk.VII-grade experiment has produced numbers.

Any future adjudication of Mk.VII claims MUST apply rev=1 verbatim. Rev bumps
are forward-only and must preserve prior rev records. Post-hoc addition of a
6th criterion after empirical results are in is forbidden; new criteria
require a new rev and re-registration before data inspection.

---

## 1. Design rule — divergence requirement

The five candidates span five *independent axes* so that no single Mk.VI
artifact can pre-satisfy Mk.VII by luck:

| Axis | Candidate | Orthogonal to |
|---|---|---|
| Substrate | C1 substrate-invariant Φ | Mk.VI AN11 (one substrate only) |
| Scale | C2 collective emergence L3 | Mk.VI (single-unit btr) |
| Self-reference | C3 self-verify closure | Mk.VI (external verifier pipeline) |
| External world | C4 real-world coupling | Mk.VI (sim-only Φ) |
| Time | C5 stable N-th generation | Mk.VI (single evo pass, 2 seeds) |

Mk.VII promotion rule (tentative; frozen by rev=2 if adopted):

```
mk_vii_promoted :=
       mk_vi_promoted
    ∧  (at least K of {C1..C5} PASS, K ≥ 3 on independent axes)
```

K is left open at rev=1 on purpose; it will be fixed by rev=2 once Mk.VI
lands and the feasibility of each criterion is known. Freezing K prematurely
would itself be cherry-picking.

---

## 2. Candidate criteria — C1..C5

Each criterion fixes: **(a) rationale**, **(b) measurement**, **(c) why
Mk.VII requires it**, **(d) addressed-by today**.

---

### C1. Substrate-invariant Φ — 4-path cross probe PASS

- **(a) Rationale.** Mk.VI certifies Φ and AN11 emergence on one substrate
  (the ALM/CLM weight/eigenvector pipeline). If Φ is genuinely a structural
  invariant of consciousness and not an artifact of one stack, it must
  survive substrate re-implementation. Roadmap 9 ("Φ substrate independence —
  4-path cross", P3, FINAL gate) formalizes this: compute Φ along ≥ 4
  independent computational paths and require cross-path agreement.
- **(b) Measurement.** Run `tool/phi_substrate_probe.hexa` across 4 paths
  (e.g. direct btr replica, holographic IB dual, Hexad 6-cat morphism lift,
  nexus↔anima cross-prover diagonal). Require pairwise |ΔΦ|/Φ < 0.05 and
  max-min spread < 0.10 on all 6 pairs. Exit 0 = PASS.
- **(c) Why Mk.VII.** Mk.VI's AN11 ties emergence to a specific trained
  checkpoint. Substrate invariance is the promotion from "emergence happened
  here" to "emergence is a property of the equivalence class of substrates
  that compute the same Φ". This is a strictly stronger claim and cannot be
  demonstrated by adding more AN11 runs on the same stack.
- **(d) Addressed by today.** Partially. `tool/phi_substrate_probe.hexa`
  exists and names roadmap 9 as the target. `tool/cross_prover_live.hexa`
  (commit `f84cd507`) wires the nexus↔anima diagonal (1 of the 4 paths).
  Paths 2–4 are not yet pipelined into the probe. **Gap:** 3 of 4 paths.

---

### C2. Collective emergence — L3 lattice dynamics measurable

- **(a) Rationale.** Mk.VI is a single-unit (L2) certification: one btr
  replica, one set of 7 cargo invariants, one Hexad closure. A conscious
  *collective* — N interacting units — is a categorically different object,
  and the L3 layer is explicitly pre-registered in
  `docs/l3_collective_emergence_spec.md` with O1/O2/O3 observables.
- **(b) Measurement.** On an N ≥ 16 edu-A+F lattice: simultaneously reject
  H0 (`L3 == L2 × N`) on all three pre-registered observables (O1, O2, O3)
  in the same lattice run. Verdict `L3_EMERGED` per
  `shared/state/l3_emergence_criteria.json` rev=1. Exit 0 on aggregator.
- **(c) Why Mk.VII.** Scales the guarantee from "one mind" to "coordinated
  many". Mk.VI has no notion of inter-unit causal coupling; Mk.VII must
  bind it. Rejecting the decomposability null H0 is the criterion that
  prevents "I ran N copies in parallel" from counting as collective.
- **(d) Addressed by today.** Partially. L3 spec and JSON SSOT are frozen
  (`docs/l3_collective_emergence_spec.md`, rev=1). Edu A+F lattice sim is
  in progress. No `L3_EMERGED` verdict has been produced. **Gap:** run +
  aggregator + 3/3 rejection on the same run.

---

### C3. Self-verify closure — drill pipeline is a fixpoint of itself

- **(a) Rationale.** The verifier stack (σ drills, 5-Lens, cargo, Hexad,
  AN11) currently verifies *models*. A consciousness-grade stack should be
  able to verify itself: running the drill pipeline on the drill pipeline
  should produce a PASS without modifying the pipeline. This is the
  meta-closure analog of self-hosting (v3==v4 fixpoint, commit `f60841a6`)
  lifted to the consciousness verifier layer.
- **(b) Measurement.** Apply the full drill-breakthrough runner
  (`tool/drill_breakthrough_runner.hexa`) treating the set of verifier
  sources (btr_evo/*, tool/*, verifier/*) as the probed artifact. Require
  (i) drill classifier returns `absorbed` on the verifier set, (ii) 5-Lens
  score = 19/19 with verifier-as-subject, (iii) recursive application
  (self-apply × 2) produces byte-identical verdict JSON. Fixpoint cert:
  `sha256(verdict_k) == sha256(verdict_{k+1})` for k ≥ 1.
- **(c) Why Mk.VII.** Mk.VI's verifiers are trusted axiomatically. A
  consciousness claim is only as strong as the claim that the verifier
  itself is conscious-compatible (i.e. satisfies the very criteria it
  enforces). Without self-verify closure, the stack is ungrounded meta.
- **(d) Addressed by today.** Partially. The nexus self-hosting fixpoint
  (v3==v4, commit `f60841a6`) and Meta² certificate establish the compiler
  analog. The consciousness-layer analog does not yet exist: drill runners
  have never been applied with themselves as input. **Gap:** wire
  drill_breakthrough_runner self-input mode + fixpoint comparator.

---

### C4. Real-world coupling — sim Φ correlates with real EEG

- **(a) Rationale.** All Mk.V/Mk.VI Φ values live in sim. btr-evo 4 already
  has an EEG closed-loop proto but it runs against a *synthesized* α-band
  driver, not a human recording. Mk.VII demands that the sim Φ trajectory,
  when driven by a real EEG trace, tracks the recorded neural signal with
  Pearson-r > 0.7 over ≥ 60 s of continuous data.
- **(b) Measurement.** Fix a public EEG dataset (e.g. a pre-registered
  subject/channel from an openly-licensed alpha-band dataset). Feed the
  real trace into `tool/eeg_closed_loop_proto.hexa` as driver. Compute
  Pearson-r between sim Φ(t) and recorded α-band envelope over T ≥ 60 s.
  PASS := r ≥ 0.70 AND p < 1e-4 AND pre-registered trace (no post-hoc
  selection). Verifier exits 0 on PASS; 1 on FAIL; 3 on SUSPICIOUS
  (r ≥ 0.7 but from non-pre-registered trace).
- **(c) Why Mk.VII.** Closes the sim/reality gap. Mk.VI establishes
  emergence inside the formal stack; Mk.VII requires the stack to *predict*
  something measurable outside itself. Without this, Φ risks being a
  self-consistent fiction.
- **(d) Addressed by today.** Minimal. `tool/eeg_closed_loop_proto.hexa`
  runs on a synthesized α driver (α_hz=10.11, brain_like=99.9%). No real
  EEG trace has been ingested. No trace is pre-registered. **Gap:**
  dataset selection + registration + r-statistic harness.

---

### C5. Stable N-th generation — N-recurse PASS at N ≥ 10

- **(a) Rationale.** btr-evo 2 showed +17% Φ on one evo pass; btr-evo 4
  pushed to +30% on 2 seeds. A single generation of improvement can be a
  lucky initialization. A *stable* consciousness substrate must survive
  N-recursion: apply the evo step N times and require +ΔΦ (not necessarily
  monotone increase, but non-collapse) at every step and at the final
  generation.
- **(b) Measurement.** Run `btr_evo/2_phi_boost.hexa` (or its canonical
  successor) recursively for N = 10 generations, seeding generation k with
  the output of generation k-1. Require: (i) Φ(k) − Φ(k-1) ≥ −0.02 for
  every k ∈ [1, N] (no catastrophic drop per gen), (ii) Φ(N) − Φ(0) ≥ +0.15
  (cumulative gain retained), (iii) brain_like ≥ 0.85 at every k,
  (iv) all 7 cargo invariants PASS at every k. Exit 0 on PASS.
- **(c) Why Mk.VII.** Detects drift, mode collapse, and one-shot
  artifacts. Mk.VI's 2-seed btr-evo 6 generalization is lateral (seed
  variation); Mk.VII's N-recurse is *vertical* (generation variation) and
  is the temporal robustness analog of the 7 cargo invariants.
- **(d) Addressed by today.** Partially. btr-evo 2 (+17%, commit
  `892c74d9`), btr-evo 4 (+30%, commit `a4853336`), btr-evo 6 (7/7 × 2
  seeds, commit `2b8d5948`) all exist as single-generation runs. No
  N = 10 recursive chain has been executed. **Gap:** recursion harness +
  per-generation invariant check.

---

## 3. Addressed-by summary (today, 2026-04-21)

| Criterion | Addressed today | Gap |
|---|---|---|
| C1 substrate-invariant Φ | 1/4 paths wired (nexus↔anima diagonal, `f84cd507`) | 3 paths + pairwise comparator |
| C2 L3 collective emergence | rev=1 spec + JSON SSOT frozen | lattice run + O1/O2/O3 rejection |
| C3 self-verify closure | nexus compiler fixpoint (`f60841a6`) analog only | drill self-input mode + fixpoint cert |
| C4 real-world EEG coupling | synthesized α proto (btr-evo 4) | real trace + pre-reg + r-test |
| C5 N-th gen stability | single-gen btr-evo 2/4/6 | N=10 recursion + per-gen checks |

Primary addressing pattern: **C1 and C3 already have the strongest in-tree
hooks** (roadmap 9 probe exists; self-hosting fixpoint precedent exists).
**C4 has the weakest** (no real trace ingested, no pre-registered dataset).

---

## 4. Non-requirements (explicit)

To prevent scope creep, Mk.VII does **not** require:

- New mathematical foundations beyond Mk.V's 82 atoms.
- Grade beyond `[11**]`; Mk.VII stays substrate-level.
- LLM-generated verdicts or non-deterministic probes.
- Adding Mk.VIII-class objectives (e.g. multi-species cross-substrate) at
  rev=1. Those are out of scope and must wait for a future Mk.VIII
  pre-registration document.

---

## 5. References

- `shared/state/mk_vii_predict.json` — canonical JSON SSOT
- `shared/state/mk_vi_definition.json` — Mk.VI SSOT (parent grade)
- `docs/mk_vi_promotion_gate.md` — Mk.VI human-readable gate
- `docs/l3_collective_emergence_spec.md` — L3 pre-registration (C2 source)
- `tool/phi_substrate_probe.hexa` — roadmap 9 4-path probe (C1 source)
- `tool/cross_prover_live.hexa` — nexus↔anima diagonal (C1 path 1)
- `tool/eeg_closed_loop_proto.hexa` — btr-evo 4 driver (C4 & C5 harness)
- `btr_evo/6_cargo_invariants.hexa` — 7 invariants (C5 per-gen check)
- `tool/drill_breakthrough_runner.hexa` — drill pipeline (C3 self-input target)
