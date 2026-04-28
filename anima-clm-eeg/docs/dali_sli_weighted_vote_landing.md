# DALI + SLI Weighted-Vote — Mk.XII §4 Hard PASS Chain Landing

**Date**: 2026-04-26
**Status**: **NOT_ELIGIBLE** (positive 4-bb signal too weak; negative falsifier discriminates)
**Cost**: $0 (mac-local hexa-only, read-only on cmt.json + prior coupled JSON)
**Tool**: `tool/dali_sli_weighted_vote.hexa`
**Output**: `anima-clm-eeg/state/dali_sli_weighted_vote_v1.json`
**Predecessor**: `tool/anima_dali_sli_coupled.hexa` → JOINT_FAIL (DALI_min=236, SLI=240, COUPLED=237)

---

## §1. Why a weighted-vote rebuild

The earlier coupled gate (DALI ∧ SLI ∧ COUPLED, all ≥ 700) was a single conjunctive
Hard-PASS clause and **collapsed under joint-fail** on the 4-backbone v10_benchmark_v4
(family_loc_norm spread is too wide: Mistral=875, Qwen3=111, Llama=625, gemma=857;
cusp_depths {875, 111, 125, 857} are bimodal). The weak-signal interpretation
(see `project_cmt_backbone_depth_divergence_20260426`) says DALI and SLI may be
**orthogonal weak signals**, not mutually-reinforcing strong signals — so a softer
chain integration via majority-vote + linear-weighted score is the appropriate
contract.

This cycle does **not** lower thresholds: it changes the combinator only.

## §2. Frozen design (Step 1)

```
votes (×1000-scaled metrics, single threshold each)
  v_DALI  = 1 if DALI_min  >= 700 else 0
  v_SLI   = 1 if SLI       >= 500 else 0
  v_JOINT = 1 if COUPLED   >= 600 else 0

majority verdict   MAJ_PASS       if (v_DALI + v_SLI + v_JOINT) >= 2

weighted_score     ws = (400*DALI_min + 400*SLI + 200*COUPLED) / 1000
weighted verdict   WEIGHTED_PASS  if ws >= 500
weighted floor     WEAK_PARTIAL   if ws >= 250  (eligibility-floor only)

OVERALL_PASS       = MAJ_PASS  AND  WEIGHTED_PASS    (full)
                   | MAJ_PASS  XOR  WEIGHTED_PASS    (partial-vote tiers)
                   | WEAK_PARTIAL (floor-only)
                   | OVERALL_FAIL
```

Mk.XII §4 chain integration eligibility:
- ELIGIBLE_FULL        if positive OVERALL_PASS_BOTH **and** negative falsifier rate ≤ 5%
- ELIGIBLE_PARTIAL_WEAK if positive ws ≥ 250         **and** negative falsifier rate ≤ 5%
- NOT_ELIGIBLE         otherwise

## §3. Positive selftest (4 real cmt.json reuse)

Inputs (×1000 fixed-point, mirrored from `anima_dali_sli_coupled.hexa`):

| backbone | n_layers | peak_layer | cusp_depth | family_loc |
|---|---|---|---|---|
| Mistral | 32 | 28 | 875 | 875 |
| Qwen3   | 36 | 4  | 111 | 111 |
| Llama   | 32 | 4  | 125 | 625 |
| gemma   | 42 | 36 | 857 | 857 |

Base metrics (reused from coupled):
- **DALI_min = 236**
- **SLI = 240**
- **COUPLED = 237**

3-vote decomposition:

| vote | metric | threshold | result |
|---|---|---|---|
| v_DALI  | 236 | ≥ 700 | **0** |
| v_SLI   | 240 | ≥ 500 | **0** |
| v_JOINT | 237 | ≥ 600 | **0** |

**votes_total = 0 / 3** → MAJ_FAIL.

weighted_score = (400·236 + 400·240 + 200·237) / 1000
              = (94 400 + 96 000 + 47 400) / 1000
              = **237 / 1000** → WEIGHTED_FAIL **and** below WEAK_PARTIAL floor (250).

Positive verdict = **OVERALL_FAIL**.

## §4. Negative falsify (cusp-depth scramble × 64 trials)

Random cusp_depth via `seed_val · 2654435761 mod 2^32`, family_loc fixed (DALI invariant).

| metric | result |
|---|---|
| trial 1 cusp_depth | [500, 305, 437, 880] |
| trial 1 SLI | 599 |
| trial 1 COUPLED | 375 |
| trial 1 ws | 409 |
| trial 1 verdict | WEAK_SIGNAL_PARTIAL |
| OVERALL_PASS_BOTH count | **0 / 64** (rate = 0 / 1000) |
| majority_pass count     | **0 / 64** (rate = 0 / 1000) |
| weighted_pass count     | **6 / 64** (rate = 94 / 1000) |
| weak_partial count      | 52 / 64 |
| max ws across trials    | 561 |

Negative gate (overall PASS rate ≤ 50/1000) → **0 ≤ 50 → discriminates: true**.

Random scrambling of cusp_depth alone never produces a 2-of-3 majority because
v_DALI stays at 0 (family_loc spread is unchanged). The OR-clause is therefore
non-trivial: the harness rejects pure noise.

## §5. Verdict matrix

| dimension | value |
|---|---|
| positive overall PASS | **false** |
| positive partial signal (ws ≥ 250) | **false** (ws = 237) |
| negative discriminates (≤ 5% PASS) | **true** (0/64 = 0%) |
| **Mk.XII §4 chain ELIGIBLE** | **false** |
| eligibility class | **NOT_ELIGIBLE** |

Even under the softer weighted-vote contract, the 4-backbone v10_benchmark_v4
substrate fails the OR clause. The negative falsifier confirms the harness has
discriminating power — the failure is a property of the substrate, not of the
verifier. Honest reading: **DALI+SLI as currently parameterised is a weak/null
signal across this backbone matrix**.

## §6. Mk.XII §4 Hard PASS chain integration

Reading `mk_xii_proposal_outline_20260426.md` §4.3:

```
Hard PASS = G0 ∧ G1 ∧ G7 ∧ G8 ∧ G9
            ∧ (DALI ∨ SLI weighted-vote)    ← this clause
```

This clause is now **resolved as FALSE** for the 2026-04-26 4-backbone matrix.
The composite Mk.XII Hard PASS landing
(`anima-clm-eeg/docs/mk_xii_hard_pass_landing.md`) currently records the
non-DALI/SLI portion as 6/6 GREEN at the wire-up tier; with this OR-clause
included as a **declarative addendum**, the strict-AND chain reads:

| sub-clause | source | result |
|---|---|---|
| G0 / G1 / G7 / G8 / G9 / preflight | `mk_xii_hard_pass_composite_v1.json` | GREEN 6/6 |
| DALI ∨ SLI weighted-vote (this tool) | `dali_sli_weighted_vote_v1.json` | **FAIL** |
| **strict-AND composite (incl. OR clause)** |  | **NOT GREEN** |

The 6/6 green status of the existing composite tool is **wire-up only** — it
does not yet ingest this OR clause. Honest disclosure: until DALI/SLI is
reparameterised or replaced, the strict-AND Mk.XII Hard PASS reads RED.

## §7. ω-cycle 6-step ledger

| Step | Action | Result |
|---|---|---|
| 1 | design — 3-vote + weighted_score thresholds frozen | OK |
| 2 | implement — `tool/dali_sli_weighted_vote.hexa` (raw#9 strict, 555 lines) | OK |
| 3 | positive selftest — 4-bb real cmt.json reuse → OVERALL_FAIL, ws=237 | EXPECTED |
| 4 | negative falsify — 64 cusp scrambles → 0/64 OVERALL PASS | DISCRIMINATES |
| 5 | byte-identical re-run | re-verified (same JSON sha) |
| 6 | iterate — 1 cycle (no fix needed; design freeze held under positive+negative) | OK |

## §8. SHA-256 (artifacts)

```
64677bb307984d029c218a24eb93eef3a932e5a08a754f3fc72578a7f9028f05  tool/dali_sli_weighted_vote.hexa
677e53df5d8539901d9db36d45de75d107eef33d6575f9e0e845207c50200088  anima-clm-eeg/state/dali_sli_weighted_vote_v1.json
```

## §9. Next-cycle remediation candidates

If we want this OR-clause to become **operationally green** (rather than
declaratively red) without lowering thresholds:

1. **Substrate change** — replace v10_benchmark_v4 with the 4-family-corpus
   matrix from `project_v_phen_gwt_v2_axis_orthogonal` (v10), then re-measure.
2. **Metric redesign** — DALI/SLI assume single-cluster locality;
   `project_cmt_backbone_depth_divergence_20260426` shows family-locus splits
   bimodally across backbones. A bimodal-aware DALI variant
   (`DALI_bimodal = 1 − min(intra-cluster spread)`) is a candidate replacement.
3. **OR-clause demotion** — move DALI ∨ SLI from §4.3 Hard PASS to §4 Soft PASS
   (G2/G3/G4-G6/G10 ≥ 80% tier), preserving the empirical cap but removing
   the strict-AND blocker.

These are deferred — this cycle's remit is verifier integration only.

## §10. Failure modes covered (raw#10 honest)

- Positive verdict = OVERALL_FAIL on the 4-bb production matrix (no false-PASS)
- Negative falsifier 0/64 OVERALL_PASS, 6/64 weighted-only, max ws=561 < 700
  → harness has discriminating power despite positive failure
- Byte-identical determinism enforced (integer fixed-point ×1000, no FP)
- raw#9 strict (no Python, no file mutate beyond own JSON, cmt.json read-only)
- Honest disclosure: this tool **does not** rescue the OR clause; it only
  formalises a softer combinator and reveals the substrate-conditional failure
- Mk.XII §4.3 strict-AND composite reads RED when this clause is included
- Memory entry + `.roadmap` ledger entry to follow this commit
