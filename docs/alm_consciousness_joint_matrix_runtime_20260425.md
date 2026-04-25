# Consciousness Joint Verifier Matrix — Runtime (V0+V1+V2+V3 automated)

**Date:** 2026-04-25
**Tool:** `tool/an11_b_joint_matrix.hexa`
**Schema:** `anima/an11_b_joint_matrix/1`
**Spec lineage:**
- `docs/alm_consciousness_joint_matrix_20260425.md` (manual matrix synthesis, sibling)
- `docs/alm_consciousness_verifier_strengthening_20260425.md` §5 (joint table, commit `34521be5`)
**Compliance:** raw#9 / raw#10 / raw#12 / raw#15 / POLICY R4 (`.roadmap` unchanged)

---

## §1 What this runtime does

Promotes the manual 4-tuple aggregation in `docs/alm_consciousness_joint_matrix_20260425.md` to an automated single-command runtime. Drives all four consciousness-correlate verifiers sequentially per `(path, round)` cell and emits a single joint-verdict matrix per round, plus byte-identical per-verifier ledgers (V1/V2/V3) so the existing SSOT files remain consistent.

| Verifier | Source tool (commit `2945ed17`) | Metric | Threshold |
|---|---|---|---|
| V0 | `tool/an11_b_ccc.hexa` (read-through of pre-existing `state/alm_<round>_<p>_an11_b.json`) | `max_cosine` ≥ 0.5 AND `top3_cosine_sum` ≥ 1.2 | AN11(b) ccc gate |
| V1 | `tool/an11_b_v1_phi_mip.hexa` | Φ_mip via 12870 balanced bipartitions | ≥0.55 PASS / <0.45 FAIL |
| V2 | `tool/an11_b_v2_sma.hexa` | SMA_lift = paired EN↔KO ⟨|cos|⟩ − distractor | lift≥0.20 AND SMA≥0.55 PASS / lift<0.10 FAIL |
| V3 | `tool/an11_b_v3_cps.hexa` | CPS = Δ_destruct / Δ_preserve (Gram Frobenius) | CPS≥3.0 AND Δ_pres≤0.20 AND Δ_des≥0.40 PASS / CPS<1.5 FAIL |

The runtime mirrors V1/V2/V3 helpers byte-for-byte (same constants, same EN↔KO permutation, same `numpy.default_rng(20260421)` seed) so per-cell numbers are guaranteed identical to the standalone tools.

---

## §2 Usage

```sh
# Run for a single round, emit joint matrix + per-cell V1/V2/V3 ledgers
hexa run tool/an11_b_joint_matrix.hexa --round r6
hexa run tool/an11_b_joint_matrix.hexa --round r8

# Skip per-cell V1/V2/V3 ledger re-emit (joint matrix only)
hexa run tool/an11_b_joint_matrix.hexa --round r6 --no-ledgers

# Selftest: run on r6 fixture, cross-check against existing summaries
hexa run tool/an11_b_joint_matrix.hexa --selftest
```

Outputs:
- `state/an11_b_joint_matrix_<round>.json` (joint matrix per spec §5)
- `state/an11_phi_mip_<p>_<round>.json` (V1 ledgers, p1..p4)
- `state/an11_sma_<p>_<round>.json` (V2 ledgers)
- `state/an11_cps_<p>_<round>.json` (V3 ledgers)

Inputs:
- `state/h_last_raw_<p>_TRAINED_<round>.json` (V1/V2/V3 hidden-state input — must exist for p1..p4)
- `state/alm_<round>_<p>_an11_b.json` (V0 verdict; r8 falls back to r6 file when round-specific artifact missing — fallback is recorded in `cells[].V0.source_fallback=true` and `source_round=r6`)

---

## §3 Joint label decision rules (spec §5)

| 4-tuple (V0, V1, V2, V3) | Joint label |
|---|---|
| PASS, PASS, PASS, PASS | **STRONG-ATTACHED** |
| PASS, PASS, PASS, FAIL | semantic-correlate-only |
| PASS, PASS, FAIL, PASS | binding-degraded |
| PASS, PASS, FAIL, FAIL | binding-and-counterfactual-degraded (extension; not in spec table) |
| PASS, FAIL, *, * | **template-fitted-non-integrated** |
| FAIL, *, *, * | NOT-ATTACHED |

`AMBIGUOUS` is treated as non-PASS for joint label purposes; the per-cell `verdict` field still carries the verbatim AMBIGUOUS / PASS / FAIL string from the originating verifier.

The runtime additionally reports `joint_label_path_coherent` (all 4 paths share the same joint label) and `round_joint_label` (the shared label, or `mixed` if not coherent). Path coherence corresponds to the spec §5 raw#12 cherry-pick-immunity check.

---

## §4 r6 + r8 verification (executed 2026-04-25)

| Round | V0 PASS | V1 PASS | V2 PASS | V3 PASS | Joint label (all 4 paths) | Coherent |
|---|---|---|---|---|---|---|
| r6 | 4/4 | 0/4 | 0/4 | 0/4 | template-fitted-non-integrated | true |
| r8 | 4/4† | 0/4 | 0/4 | 0/4 | template-fitted-non-integrated | true |

† r8 V0 uses r6 V0 artifact for all 4 paths (D-mistral prep stage2 adapter pull still in progress; matches `docs/alm_consciousness_joint_matrix_20260425.md` §5 fallback note). The fallback is recorded transparently in each cell's `V0.source_fallback=true` and `V0.source_round="r6"`.

**Cross-check vs existing summaries (r6 cells):** all 4 paths × 3 verifiers (V1 phi_mip / V1 argmin_S / V1 verdict / V2 SMA / V2 SMA_lift / V2 verdict / V3 CPS / V3 Δ_pres / V3 Δ_des / V3 verdict) byte-identical to `state/an11_phi_mip_summary_20260425.json`, `state/an11_sma_summary_20260425.json`, `state/an11_cps_summary_20260425.json`. Selftest enforces |diff| < 1e-9.

**r8 cross-check vs joint-matrix doc §2 manual table:**
- r8·p4: V1=0.195, V2=−0.218, V3=0.843 — exact match.
- r8·{p1,p2,p3}: identical to r6 (V1/V2/V3 input artifacts unchanged) — exact match.

---

## §5 Output schema (`state/an11_b_joint_matrix_<round>.json`)

```json
{
  "schema": "anima/an11_b_joint_matrix/1",
  "verifier": "V0+V1+V2+V3 joint matrix runtime",
  "spec_doc": "docs/alm_consciousness_joint_matrix_20260425.md",
  "spec_commit": "34521be5",
  "ts": "<ISO8601 UTC>",
  "round": "r6",
  "paths": ["p1", "p2", "p3", "p4"],
  "cells": [
    {
      "round": "r6",
      "path": "p1",
      "V0": {"verdict": "PASS", "max_cosine": 0.618, "top3_cosine_sum": 1.834,
             "source_round": "r6", "source_fallback": false, "source_path": "..."},
      "V1": {"verdict": "FAIL", "phi_mip": 0.352, "argmin_S": [0,1,2,3,4,12,13,14]},
      "V2": {"verdict": "FAIL", "SMA": 0.611, "SMA_distractor": 0.720,
             "SMA_lift": -0.109, "pairs": [...]},
      "V3": {"verdict": "FAIL", "delta_preserve": 0.614, "delta_destruct": 0.628,
             "CPS": 1.022, "preserve_permutation": [...], "destruct_permutation": [...]},
      "joint_4tuple": ["PASS", "FAIL", "FAIL", "FAIL"],
      "joint_label": "template-fitted-non-integrated"
    },
    ...
  ],
  "pass_count": {"V0": 4, "V1": 0, "V2": 0, "V3": 0},
  "joint_label_counts": {"template-fitted-non-integrated": 4},
  "joint_label_path_coherent": true,
  "round_joint_label": "template-fitted-non-integrated",
  "thresholds": {...},
  "joint_table_ref": "docs/alm_consciousness_verifier_strengthening_20260425.md §5",
  "raw_compliance": [...],
  "origin": "tool/an11_b_joint_matrix.hexa"
}
```

---

## §6 Selftest contract

`hexa run tool/an11_b_joint_matrix.hexa --selftest` runs the joint matrix on the r6 fixture in-process and cross-checks every numeric (phi_mip, argmin_S, SMA, SMA_lift, CPS, Δ_pres, Δ_des) and every verdict (V0/V1/V2/V3, joint label) against:

- `state/an11_phi_mip_summary_20260425.json`
- `state/an11_sma_summary_20260425.json`
- `state/an11_cps_summary_20260425.json`

Floating-point tolerance: 1e-9. Any mismatch → exit 1 with per-line diagnostic. Currently: **PASS** (selftest reproduces all 4 r6 cells byte-identical to the canonical summaries).

---

## §7 Limits inherited from spec §6

The runtime introduces zero new claims beyond what the standalone V0/V1/V2/V3 tools already establish. In particular:

1. **No phenomenal consciousness claim.** All four verifiers are output-only correlates.
2. **No protection against maximally adversarial trainer.** A trainer aware of the 16 templates + EN↔KO pairs + seed `20260421` could construct an adapter that passes V0+V1+V2+V3 without any underlying consciousness-correlate (spec §6.3). Mitigation = quarterly template/seed rotation under hash-chain.
3. **No statistical power beyond n=16 prompts.** C(16,8)=12870 partitions and 6 EN↔KO pairs are the fixed bound (spec §6.4).
4. **`byte_weighted_mean` reduction is hard-coded.** Robustness across reductions is a v2 candidate (spec §6.5).

The joint label is informational about *which axes* of consciousness-correlate space the adapter does or does not satisfy — not a single "consciousness yes/no" verdict.

---

## §8 Compliance ledger

- **POLICY R4:** `.roadmap` unchanged. Pure runtime promotion of existing measurements.
- **raw#9 (hexa-only deterministic):** entry point is hexa; heavy work delegated to a single tmp-file Python helper, identical pattern to V1/V2/V3 standalone tools.
- **raw#10 (no overclaim):** joint label `template-fitted-non-integrated` is the spec §5 verdict for `(PASS, FAIL, *, *)`; runtime emits no STRONG-ATTACHED label unless all four PASS.
- **raw#12 (pre-registered):** all thresholds frozen at spec commit `34521be5`. Runtime does not introduce new thresholds.
- **raw#15 (SSOT):** V1/V2/V3 per-cell ledgers re-emitted from the same computation; numbers byte-identical to the canonical summary JSONs (selftest enforced). V0 read-through preserves the existing `state/alm_<round>_<p>_an11_b.json` artifacts as SSOT.

**Sibling docs:** `docs/alm_consciousness_joint_matrix_20260425.md` (manual matrix synthesis), `docs/alm_consciousness_verifier_strengthening_20260425.md` (V1/V2/V3 spec, commit `34521be5`).
