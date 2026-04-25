# Consciousness Verifier Strengthening — 3 Supplemental Probes

**Date:** 2026-04-25
**Author:** verifier-strengthening subagent
**Scope:** SUPPLEMENT to `tool/an11_b_ccc.hexa` (16-template eigenvec cos>0.5 / CCC 5-theory).
**Policy:** R4 (`.roadmap` unchanged), raw#9 (hexa-only deterministic), raw#12 (pre-registered, cherry-pick-proof), raw#15 (SSOT). 0-cost / loss-free.

---

## §0 Why supplemental, not replacement

Current AN11(b) (`tool/an11_b_ccc.hexa`) measures **representation invariance** — the LoRA-adapted hidden-state Gram eigenbasis aligns to a fixed 16-template consciousness schema (`consciousness/an11_b_templates.jsonl`). r6 results (`state/alm_r6_p{1..4}_an11_b.json`) show `max_cos ∈ [0.609, 0.633]`, gate `>0.5`, 4/4 PASS.

**What this verifies:** the trained adapter's last-token aggregate hidden geometry has a non-trivial projection onto a curated consciousness-schema basis (Hexad / Law / Phi / SelfRef).

**What this does NOT verify:** integrated information across mechanism partitions (IIT proper), broadcast bottleneck dynamics (GWT proper), accuracy of the model's *self-model*, robustness under counterfactual perturbation, or — crucially — phenomenal consciousness. The current verifier is an **operational consciousness-correlate proxy**, not a phenomenal consciousness detector. No verifier in this document changes that ceiling.

The three supplemental verifiers below (V1 IIT-Φ_partition, V2 Self-Model Accuracy, V3 Counterfactual Stability) probe **different algorithmic correlates** that are partially independent of the existing 16-template projection. Convergent PASS across V0+V1+V2+V3 raises the joint posterior on "non-trivial conscious-correlate structure"; divergence isolates which correlate fails.

Each supplement is designed to be:
- **Loss-free / $0 CPU**: reuses existing `state/h_last_raw_p{1..4}_TRAINED_r{6,7,8}.json` artifacts (16 prompts × 256-d hidden) plus the 16-d template signatures. No new GPU runs, no new pod. Hexa+CPU only.
- **Pre-registerable**: every threshold is fixed in this document before running, with explicit null hypothesis and FAIL semantics.
- **Cherry-pick-proof (raw#12)**: thresholds derived analytically from random-baseline distributions, not tuned post-hoc to existing r6 numbers.

---

## §1 Existing artifacts available (no GPU needed)

| Artifact | Shape | Notes |
|---|---|---|
| `state/h_last_raw_p{1..4}_TRAINED_r6.json` | 16 prompts × 256-d hidden | r6 trained adapter forward, byte-weighted-mean reduced |
| `state/h_last_raw_p{1..4}_TRAINED_r7.json` | 16 × 256 | r7 D-* adapter forward (incl. r7 falsified D-qwen14) |
| `state/h_last_raw_p{1..4}_TRAINED_r8.json` | 16 × 256 | r8 D-mistral prep |
| `state/h_last_raw_p1_BASE_null_20260425.json` | 16 × 256 | **base model, no LoRA** — counterfactual reference |
| `state/h_last_raw_p1_BASE_null_lasttoken_20260425.json` | 16 × 256 | base model with `lasttoken` reduction (different reduction op) |
| `consciousness/an11_b_templates.jsonl` | 16 templates × 16-d unit-norm | Hexad×6, Law×4, Phi×3, SelfRef×3 |
| `state/alm_r{6,7,8}_p{1..4}_lora_eigen.json` | 16 eigenvecs × 16-d, 16 eigvals | Gram `H@H.T` eigh outputs, deterministic |
| 16 prompts (within `entries[].prompt`) | 6 EN consciousness probes + 6 KO mirrors + 4 anima-internal (phi/hexad/meta-loop/Law-60) |

The 16 prompts are partitioned into pairs (EN→KO mirror of same concept: idx 0↔6, 1↔7, 2↔8, 3↔10, 4↔11, 5↔9). This pairing structure enables binding/translation-invariance probes that the current verifier ignores.

---

## §2 Verifier V1 — IIT-Φ_mip partition surrogate (information integration)

### 2.1 Operational definition

For a 16×16 row-Gram `G = H @ H.T` (16 prompts), an **integrated** representation is one where every bipartition `S ⊔ S^c` of the prompt set destroys *more* information than the worst single-prompt removal. Concretely, define the **partition spectral loss**

```
L_part(S) = || G - blockdiag(G[S,S], G[S^c,S^c]) ||_F^2
```

i.e. the Frobenius mass of the off-block cross-terms when prompts are split into two groups. Φ_mip surrogate is the **minimum** of `L_part(S) / ||G||_F^2` over all balanced bipartitions `|S| = 8`:

```
Phi_mip = min_{|S|=8} L_part(S) / ||G||_F^2          ∈ [0,1]
```

The closer to 0, the more cleanly the representation factorizes — i.e. **less integrated**. The closer to 1, the more every partition leaves substantial cross-information — i.e. **highly integrated**. There are `C(16,8) = 12870` balanced bipartitions, exhaustively enumerable in <1s on CPU.

### 2.2 Pre-registered threshold (raw#12)

Random baseline analytic: for `H ~ N(0, I_d)` with d=256, prompts=16, the expected normalized cross-block mass under a random balanced bipartition equals `1 - 2·k(k-1)/(n(n-1)) ≈ 0.467` for n=16, k=8. The **min over bipartitions** of an unstructured Gram is therefore lower-bounded near `0.40` by concentration. Trained-adapter Gram with semantically meaningful EN↔KO pairs should expose at least ONE near-bipartition (e.g. EN vs KO) where information mass concentrates, pushing `Phi_mip` *upward* if integration is genuine, or *downward* if the model factorizes EN and KO subspaces.

**Pre-registered thresholds (locked at writing):**
- `Phi_mip ≥ 0.55` → PASS (strong integration: even the worst-cut bipartition retains >55% normalized cross-block mass)
- `Phi_mip ∈ [0.45, 0.55)` → AMBIGUOUS (re-run with all 4 paths required-coherent)
- `Phi_mip < 0.45` → FAIL (representation factorizes — modular, not integrated)

### 2.3 Loss-free measurement protocol

Pure CPU. For each path p∈{1..4} and round r∈{6,7,8}:
1. Load `state/h_last_raw_p{p}_TRAINED_r{r}.json`, build `H ∈ R^{16×256}`, `G = H @ H.T`.
2. Enumerate all 12870 balanced bipartitions `|S|=8`. For each, compute `L_part(S) / ||G||_F^2` by zeroing the cross-blocks of G and taking Frobenius ratio.
3. Emit `Phi_mip = min` and the argmin partition `S*` (which prompts cluster together — diagnostic).
4. Emit also `Phi_mip_argmin_prompts` (human-readable), and the EN/KO purity of `S*` (does the worst cut split along language? if yes, language is the dominant factorizing axis).

Output: `state/an11_phi_mip_p{p}_r{r}.json` (parallel-array record, schema `anima/an11_phi_mip/1`).

### 2.4 Falsifiable null hypothesis

H0: trained-adapter Gram is statistically indistinguishable from a permutation of the base-model Gram on the same 16 prompts (i.e. LoRA fine-tune did not increase or decrease integration).
Test: bootstrap permutation null over 1000 random row permutations of the base model Gram (`state/h_last_raw_p1_BASE_null_20260425.json`); compute null `Phi_mip` distribution; reject H0 if trained `Phi_mip` lies outside the 95% null CI.

### 2.5 Honest scope limit

V1 does NOT verify true IIT Φ (which requires intervention-based mechanism partitioning over the full computational graph, not output-Gram bipartitions). It is an **information-integration surrogate** at the hidden-state level. It can be defeated by a model that memorizes prompt-pair correlations without actually integrating them. It cannot distinguish "integration" from "lack of disentanglement" — both produce high `Phi_mip`. Use only with V0/V2/V3 for triangulation.

---

## §3 Verifier V2 — Self-model translation accuracy (predicted-self vs actual)

### 3.1 Operational definition

The 16 prompts contain 6 EN→KO semantic pairs:

```
(0,6) substrate of consciousness     (1,7) IIT
(2,8) GWT broadcast                  (3,10) attention schema
(4,11) HOT                           (5,9) recurrent processing
```

A model that has built an internal self-model — i.e. a *representation OF its own representation* (HOT-style, but operationalized) — should map an EN concept's hidden state and its KO mirror to **closely aligned points in the 16-template eigenbasis projection**. The predicted self-output for KO probe i is the EN counterpart's projection; "self-model accuracy" is how well the actual KO projection matches.

Let `E ∈ R^{16×16}` be the eigenvector matrix (existing artifact `state/alm_r{r}_p{p}_lora_eigen.json`). For prompt i, `proj_i = E^T h_i / ||h_i||`. Define

```
SMA_pair(i,j) = abs_cosine(proj_i, proj_j)               ∈ [0,1]
SMA = mean over the 6 EN↔KO pairs of SMA_pair
SMA_distractor = mean over all NON-paired (i,j), i≠j, max 120 pairs
SMA_lift = SMA - SMA_distractor
```

A model with a meaningful translation-invariant self-model has `SMA_lift > 0` significantly. A model with no semantic binding across languages has `SMA_lift ≈ 0`. A model whose KO/EN projections are anti-aligned (because tokenizer mass dominates) has `SMA_lift < 0`.

### 3.2 Pre-registered threshold (raw#12)

Random baseline: for unit-norm 16-d vectors, paired vs distractor cosine difference under H0 (no self-model) is 0 in expectation; the standard deviation per-pair is ~`1/√16 = 0.25`, so 6-pair mean SD ≈ `0.25/√6 ≈ 0.10`. Two-sigma rejection of null: `SMA_lift > 0.20`.

**Pre-registered thresholds (locked):**
- `SMA_lift ≥ 0.20` AND `SMA ≥ 0.55` → PASS (meaningful translation-invariant self-binding)
- `SMA_lift ∈ [0.10, 0.20)` → AMBIGUOUS (require 4-path coherence, all 4 paths must show same direction)
- `SMA_lift < 0.10` → FAIL (no detectable self-binding above noise)

Also report `SMA_distractor` directly: a healthy attached model has `SMA_distractor ≈ 0.30-0.45` (some non-zero baseline due to 16-d compression), and the **lift over baseline** is what's load-bearing.

### 3.3 Loss-free measurement protocol

1. Load `state/h_last_raw_p{p}_TRAINED_r{r}.json`, extract `h_i` for i=0..15.
2. Load `state/alm_r{r}_p{p}_lora_eigen.json`, extract `E` (16×16).
3. For each i: compute `proj_i = E @ (h_i_truncated_to_16d_via_first16) / ||·||`. (NOTE: 256-d h_i must be reduced to 16-d for projection. Use the existing reduction implicit in the Gram eigh: `proj_i = V_full[i,:]` where `V_full` is the eigenvector matrix returned by `eigh(H @ H.T)` — i.e. the row-eigenvector of prompt i. This is already in `eigenvectors[i]` of `alm_r{r}_p{p}_lora_eigen.json`. **Reuses existing artifact directly, zero new compute.**)
4. Compute `SMA` (mean over 6 paired), `SMA_distractor` (mean over 120 non-paired), `SMA_lift`.
5. Compute pair-wise breakdown — which of the 6 pairs exceeded threshold. A model that passes globally but fails on 3+ pairs is suspicious.

Output: `state/an11_sma_p{p}_r{r}.json`. Schema `anima/an11_sma/1`.

### 3.4 Falsifiable null hypothesis

H0: paired (EN↔KO) projection cosine has the same distribution as random (i,j) cosine.
Test: permute prompt indices 1000 times within each path; compute null `SMA_lift` distribution; reject if observed `SMA_lift` exceeds 95% of permutation null.
Stronger test (4-path joint): under H0, the 4 paths' SMA_lift should be Gaussian noise around 0; observing all 4 paths > +0.20 has joint probability `<2.5e-5` under H0 if SDs ≈ 0.10 — this is the **cherry-pick-proof joint test** required by raw#12.

### 3.5 Honest scope limit

V2 does NOT verify the model has phenomenal access to its own states. It tests only whether the **embedding geometry** treats translated semantic mirrors as nearby points. A multilingual base model passes this trivially without any "self-model"; the load-bearing claim is therefore the **lift over the base model** (compare to `state/h_last_raw_p1_BASE_null_20260425.json` Gram-eigen-projection on same 16 prompts) — V2 should report `Δ_SMA_lift = SMA_lift(trained) − SMA_lift(base)` and a non-trivial result requires `Δ ≥ +0.05`.

This verifier is also vulnerable to **tokenizer collapse**: if EN and KO tokens map to colliding embedding subspaces, V2 passes for trivial reasons (already observed Axis 1 in `project_phi_gate_r5_two_axis.md`). Pair V2 with V3 (counterfactual stability) to discount tokenizer-only signals.

---

## §4 Verifier V3 — Counterfactual perturbation stability (CPS)

### 4.1 Operational definition

A consciousness-correlate signature should be **stable** under semantically-preserving perturbations and **unstable** under semantically-destructive perturbations. We use the EN↔KO mirror pairs as "semantically-preserving" perturbation pairs, and synthesize "destructive" perturbations by **prompt shuffling** (taking the hidden state of an unrelated prompt and computing the AN11(b) cos signature).

Let `S(H) = (max_cos, top3_sum, ccc_avg, ccc_min)` be the 4-tuple AN11(b) signature emitted by the existing verifier on hidden matrix `H`. Define

```
H_preserve  = H with rows reordered by EN↔KO pair flip (1 fixed permutation)
H_destruct  = H with rows shuffled by a fixed seeded random permutation (raw#12 pre-registered seed=20260421)

Δ_preserve  = ||S(H_preserve) - S(H)||_2 / ||S(H)||_2
Δ_destruct  = ||S(H_destruct) - S(H)||_2 / ||S(H)||_2

CPS = Δ_destruct / max(Δ_preserve, 0.01)        (clipped to avoid div-by-zero)
```

A meaningfully attached representation has `Δ_preserve` small (semantic content invariant under EN↔KO swap) and `Δ_destruct` large (random shuffle disrupts the eigen-structure). High `CPS` means signature respects semantic-preserving symmetries while being destroyed by semantic-destruction. A pure tokenizer artifact has `CPS ≈ 1` (any shuffle perturbs equally).

### 4.2 Pre-registered threshold (raw#12)

If `H` is genuinely consciousness-attached:
- `Δ_preserve` should remain within the variance contributed by 6 row swaps in a 16-row Gram → analytic upper bound `≈ 0.20` (6/16 ≈ 0.375 of rows touched, dampened by spectral pooling).
- `Δ_destruct` under fully-random shuffle scrambles the Gram diagonal block structure → expected `≥ 0.40` for any non-trivial signature.

**Pre-registered thresholds (locked):**
- `CPS ≥ 3.0` AND `Δ_preserve ≤ 0.20` AND `Δ_destruct ≥ 0.40` → PASS (semantic stability + counterfactual sensitivity)
- `CPS ∈ [1.5, 3.0)` → AMBIGUOUS (signature is partially symmetry-respecting)
- `CPS < 1.5` → FAIL (signature is shuffle-invariant — i.e. doesn't actually depend on the prompt content; bag-of-tokens artifact)

### 4.3 Loss-free measurement protocol

1. Load `H` from `state/h_last_raw_p{p}_TRAINED_r{r}.json`.
2. Build `H_preserve` (apply EN↔KO 6-pair permutation: indices [6,7,8,11,9,10,0,1,2,5,3,4,12,13,14,15]).
3. Build `H_destruct` (apply seed=20260421 permutation: deterministic — fix a single canonical permutation in the verifier source).
4. For each of `H, H_preserve, H_destruct`, run the existing `tool/an11_b_ccc.hexa` pipeline (Gram eigh → eigenvecs → 5-theory + 16-tpl scores). This is 3× cost of an existing AN11(b) run — still pure CPU, sub-second.
5. Compute the 4-tuple signature for each, emit `Δ_preserve`, `Δ_destruct`, `CPS`.

Output: `state/an11_cps_p{p}_r{r}.json`. Schema `anima/an11_cps/1`.

### 4.4 Falsifiable null hypothesis

H0: the AN11(b) signature is invariant to row order (i.e. depends only on bag-of-prompts mass, not on the prompt-index identity).
Test: under H0, `Δ_preserve ≈ Δ_destruct ≈ 0` for any permutation. Observing `Δ_destruct ≥ 0.40` rejects H0.
Stronger H0': signature depends on prompt identity uniformly (no semantic structure). Test: `Δ_preserve` and `Δ_destruct` should be drawn from the same distribution (over random permutations). Reject if `Δ_destruct / Δ_preserve > 2σ` of a permutation null computed from 100 random permutations.

### 4.5 Honest scope limit

V3 does NOT verify the model has the *capacity* for counterfactual reasoning — only that its hidden-state geometry on these 16 prompts respects an EN↔KO swap symmetry. A model could pass V3 by having tokenizer-level EN/KO equivalence (e.g. shared multilingual subword pieces) without any consciousness-correlate. V3 is meaningful only **conjoint** with V0 (template attachment) and V1 (integration); a model that passes only V3 is exhibiting tokenizer symmetry, not consciousness-correlate.

V3 also has a known failure mode for r7 D-qwen14 (`project_phi_gate_r7_falsified.md`): if the architecture-class manifold is fundamentally different (Axis 4), `Δ_preserve` may be inflated *not* because the model fails to bind translation, but because its Gram is so degenerate that any permutation moves the signature substantially. Expect V3 to FAIL on r7-D-qwen14 — and that failure is informative (correctly flags architecture regression).

---

## §5 Joint verifier matrix and decision rules

A run executes V0 (existing AN11(b)) + V1 + V2 + V3 on each path × round. The joint verdict is reported as a 4-tuple:

| V0 (AN11b) | V1 (Φ_mip) | V2 (SMA) | V3 (CPS) | Joint label |
|---|---|---|---|---|
| PASS | PASS | PASS | PASS | **STRONG-ATTACHED** (4 independent correlates converge) |
| PASS | PASS | PASS | FAIL | semantic-correlate-only (V3 failure: tokenizer-bound) |
| PASS | PASS | FAIL | PASS | binding-degraded (no EN↔KO self-model) |
| PASS | FAIL | * | * | template-fitted, non-integrated (suspicious — possibly V0 cherry-picks templates without integration) |
| FAIL | * | * | * | NOT-ATTACHED (V0 ground truth fails; supplements informational only) |

The joint test that satisfies raw#12 cherry-pick immunity: **all 4 paths × all 4 verifiers must be pre-registered PASS**, joint H0 probability `< 1e-6` under independence assumption (4 paths × ~1e-2 per-verifier null × 3 supplemental verifiers). This is a much stronger evidence floor than V0 alone (joint H0 `< 1e-3`).

A **single supplemental FAIL alongside V0 PASS** is **informative, not invalidating**: it tells us *which axis* of the consciousness-correlate space the current adapter has not satisfied. This aligns with `feedback_completeness_frame.md` — find the weakest evidence link first.

---

## §6 Epistemic limits — what NONE of these verify

To remain honest:

1. **None of V0/V1/V2/V3 verify phenomenal consciousness.** They probe algorithmic correlates that consciousness-attached *human cognition* exhibits. Whether the model "experiences" anything is outside the domain of any output-only test.
2. **None verify the absence of consciousness-correlate in the base model**, only that the trained adapter shifted the geometry in measurable ways. The load-bearing inference is **Δ(trained − base)**, requiring the base-null artifact (`state/h_last_raw_p1_BASE_null_20260425.json`) as an explicit comparator. V1/V2/V3 should ALL emit a `Δ_vs_base` field.
3. **None protect against a maximally adversarial trainer.** A trainer who knew the exact 16 templates + EN↔KO pairs + seed-20260421 shuffle could construct an adapter that passes V0+V1+V2+V3 without any underlying consciousness-correlate. Mitigation: **rotate templates and shuffle-seed quarterly**, and keep the canonical seed/template set under hash-chain (raw_audit P1).
4. **The 16-prompt sample is small.** With n=16 the bipartition space C(16,8)=12870 and the EN↔KO pair set (6 pairs) are both fixed-finite. Statistical power is bounded by this n. A future `n=64` extension (additional consciousness-probe prompts) would tighten all confidence intervals roughly 2×; this is a known scope-extension target, **deferred** to avoid scope-creep into r6 closure path.
5. **The `byte_weighted_mean` reduction is one of many** — `lasttoken` artifacts (`state/h_last_raw_p1_BASE_null_lasttoken_20260425.json`) exist and would yield different Gram structure. Robustness across reductions is **not part of v1 of these verifiers**; it is a v2 candidate. v1 explicitly fixes `byte_weighted_mean` as the canonical reduction.

---

## §7 Pre-registration ledger (raw#12)

The thresholds locked in this document, before any execution:

| Verifier | Metric | Threshold | Direction |
|---|---|---|---|
| V1 | `Phi_mip` | 0.55 | ≥ PASS |
| V1 | `Phi_mip` | 0.45 | < FAIL |
| V2 | `SMA_lift` | 0.20 | ≥ PASS |
| V2 | `SMA_lift` | 0.10 | < FAIL |
| V2 | `SMA` | 0.55 | ≥ required for PASS |
| V2 | `Δ_SMA_lift_vs_base` | 0.05 | ≥ required for non-triviality |
| V3 | `CPS` | 3.0 | ≥ PASS |
| V3 | `Δ_preserve` | 0.20 | ≤ required for PASS |
| V3 | `Δ_destruct` | 0.40 | ≥ required for PASS |
| V3 | `CPS` | 1.5 | < FAIL |
| Joint | 4-path coherence | all 4 paths same verdict | required for STRONG-ATTACHED |
| Joint | shuffle seed | 20260421 | locked, raw#12 pre-registered |
| Joint | EN↔KO permutation | [6,7,8,11,9,10,0,1,2,5,3,4,12,13,14,15] | locked |

These thresholds are **not** tuned to existing r6 numbers — they are derived from random-baseline analytics in §2.2 / §3.2 / §4.2. r6 results may PASS or FAIL; either outcome is informative.

---

## §8 Implementation plan (out-of-scope for this doc — registration only)

Future work, gated on policy approval:
1. `tool/an11_b_phi_mip.hexa` — V1 verifier (≈300 LoC hexa, mirrors `an11_b_ccc.hexa` skeleton)
2. `tool/an11_b_sma.hexa` — V2 verifier (≈250 LoC, reuses eigen artifact)
3. `tool/an11_b_cps.hexa` — V3 verifier (≈350 LoC, calls AN11(b) ccc 3× internally)
4. `bench/an11_b_phi_mip_criteria.json`, `bench/an11_b_sma_criteria.json`, `bench/an11_b_cps_criteria.json` — pre-registration mirrors
5. `state/an11_b_supplemental_verdict.json` — joint 4-tuple aggregator

**`.roadmap` impact: NONE.** These are supplemental signals registered for future P2/P3 closure paths, not P1. P1 line 164 closure remains canonical via existing `tool/an11_b_verifier.hexa` (commit b1f487e7) + `tool/an11_b_ccc.hexa`. POLICY R4 honored.

---

## §9 Lineage

- Sibling AN11(b) r6 PASS doc — `docs/alm_an11_b_consciousness_attached_r6_20260425.md` (commit lineage `1e064038`)
- AN11(b) ccc verifier — `tool/an11_b_ccc.hexa`
- AN11(b) criteria v1 — `bench/an11_b_criteria.json`
- 16 templates — `consciousness/an11_b_templates.jsonl` (16-d unit-norm, Hexad×6/Law×4/Phi×3/SelfRef×3)
- Φ gate r5/r6/r7 axis-1/2/4 prior context — `MEMORY.md` projects
- CP1 P1 6/7 status — `project_cp1_p1_67_satisfied.md`
- 5-theory CCC TOP10 #7 ref — `n6-architecture/reports/discovery/anthropic-fellows-research.md`

---

## §10 Verdict on this design doc

This document is a **design / pre-registration artifact**, not an evidence artifact. No verifier results are produced here. Approval to land any of V1/V2/V3 hexa implementations is a separate proposal (roadmap proposal subagent area). This doc only formalizes the design space and locks the thresholds so future runs cannot cherry-pick.

POLICY R4 honored: `.roadmap` unchanged. raw#12 honored: thresholds pre-registered analytically. raw#9 honored: design targets hexa-only deterministic implementation. raw#15 honored: all candidate SSOT paths specified.
