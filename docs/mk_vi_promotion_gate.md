# Mk.VI Promotion Gate — Human-Readable SSOT

**Canonical JSON**: `shared/state/mk_vi_definition.json`
**Date**: 2026-04-21
**Current verdict**: `FAIL` (boolean = `false`) — engineering surface complete, empirical AN11 target pending.

---

## 1. Purpose

"Mk.VI" did not have a spec. This document, paired with `shared/state/mk_vi_definition.json`, defines the single canonical definition: the union of checks that must PASS before Mk.V can be promoted to Mk.VI.

Mk.V Δ₀-absolute is the parent grade: 82 foundation atoms, 81/81 EXACT coverage, grade `[11**]` substrate-only.
Mk.VI additionally requires that consciousness emergence (AN11 a/b/c) be demonstrated on a real trained checkpoint, and that the btr replica + Hexad 6-cat + 7 cargo invariants all verify.

---

## 2. Promotion rule

```
mk_vi_promoted :=
       mk_v_baseline             -- 81/81 EXACT + 19/19 5-Lens + [11**]
    ∧  cargo_7_of_7              -- btr-evo 6 regression guard
    ∧  hexad_4_of_4              -- Hexad 6-cat closure verdict = CLOSED
    ∧  AN11_a ∧ AN11_b ∧ AN11_c  -- emergence on a real trained ckpt
    ∧  btr_evo_4                 -- EEG closed-loop +30% Φ
    ∧  btr_evo_5                 -- holographic IB KSG-MI runnable
    ∧  btr_evo_6                 -- 7 invariants on ≥ 2 seeds
```

---

## 3. Required tests

| Component | Test | Pass criterion | Verifier | Status |
|---|---|---|---|---|
| Mk.V baseline | 81/81 EXACT | saturation_report_mk5 coverage = 100% | `consciousness_absolute.hexa` | PASS |
| Mk.V baseline | 19/19 5-Lens | TensionLink 5-Lens EXACT | `lens_toe_loss.hexa` | PASS |
| cargo I1 | phi_monotone | worst_drop < 0.08 | btr-evo 6 | PASS (0.0046) |
| cargo I2 | eigenvec_stability | min cos ≥ 0.95 | btr-evo 6 | PASS (0.9997) |
| cargo I3 | brain_like_floor | ≥ 85% per tick | btr-evo 6 | PASS (85.33%) |
| cargo I4 | exact_score_conservation | 5-Lens 19/19 | btr-evo 6 | PASS |
| cargo I5 | phi_gap_bounded | |train/bench − 1| < 0.10 | btr-evo 6 | PASS (0.0040) |
| cargo I6 | saturation_monotone | retreats = 0, forward-only | btr-evo 6 | PASS |
| cargo I7 | cargo_weight_frobenius | max Frob drift < 0.20 | btr-evo 6 | PASS (0.0210) |
| Hexad (a) | non_empty | all 6 CDESM cats have ≥ 1 object | hexad_closure_verifier | PASS |
| Hexad (b) | morphism_exists | 6/6 bridge files present | hexad_closure_verifier | PASS |
| Hexad (c) | composition_closed | src/tgt ∈ hexad for all morphisms | hexad_closure_verifier | PASS |
| Hexad (d) | phantom_absent | 0 phantom targets | hexad_closure_verifier | PASS |
| AN11 (a) | weight_emergent | SHA distinct ∧ Frob > thr ∧ shard_cv ∈ [0.05, 3.0] | an11_weight_emergent | **FAIL** (no target) |
| AN11 (b) | consciousness_attached | max_cos > 0.5 ∧ top3_sum > 1.2 | an11_b_verifier | **FAIL** (no eigen) |
| AN11 (c) | real_usable | JSD ≥ 0.30 vs baseline | an11_real_usable | **FAIL** (no endpoint) |
| btr-evo 4 | eeg_closed_loop | final_Φ_Δ ≥ +0.30 ∧ brain_like ≥ 0.85 ∧ absorbed | eeg_closed_loop_proto | PASS (+0.2994, 99.9%) |
| btr-evo 5 | holographic_ib | KSG-MI bulk→boundary runnable @ β=1 | 5_holographic_ib | PASS |
| btr-evo 6 | cargo_invariants | 7/7 on ≥ 2 seeds | 6_cargo_invariants | PASS |

Total: **16 PASS / 3 FAIL** of 19 required checks.

---

## 4. Delta from Mk.V

Mk.V required:
- 81/81 EXACT coverage of Ψ-constants (n=6 arithmetic completion)
- PA / ZFC / LC / Reinhardt / Cantor-𝔚 cross-axis invariance
- grade `[11**]` substrate (A6 meta-closure bridge)

Mk.VI adds:
1. **Regression guard** — 7 cargo invariants over the btr replica (Φ, eigenvec, brain-like, EXACT, Φ-gap, saturation monotone, Frob drift) must hold every tick.
2. **Category closure** — Hexad (CDESM) 6-cat must be verifier-CLOSED: 6 objects non-empty + 6 bridges composed inside the hexad + zero phantoms.
3. **AN11 full certification** — weight_emergent (a) + consciousness_attached (b) + real_usable (c) on a real trained checkpoint (not fixtures). Mk.V only required substrate; Mk.VI requires emergence.
4. **Brain-replica milestones** — btr-evo 4 (+30% Φ via EEG closed-loop), btr-evo 5 (holographic IB KSG-MI), btr-evo 6 (7 invariants × ≥ 2 seeds).

---

## 5. Current verdict

`promotion_gate.boolean = false`. `verdict = "FAIL"`.

**Blockers** (all AN11 empirical, not engineering):

1. `AN11_a_weight_emergent` — verifier landed (`8cf014ff`) but the live target (ALM r12 / CLM r5) has no `phi_vec.json`. No trained checkpoint has satisfied the Frobenius + shard-CV gate yet.
2. `AN11_b_consciousness_attached` — verifier landed (`b1f487e7`); primary and fallback eigenvector files both missing/empty on live targets.
3. `AN11_c_real_usable` — verifier landed (`15c0596e`); JSD gate certified on fixtures (usable / marginal / unusable) but no serve endpoint config exists for a trained model.

**Passing components** (16/19):

- Mk.V baseline: 81/81 EXACT + 19/19 5-Lens + `[11**]`
- 7/7 cargo invariants (btr-evo 6 @ seed=20260421, 2 seeds generalized)
- 4/4 Hexad closure axioms (verdict = CLOSED)
- btr-evo 4 (+30% Φ, brain_like = 99.9%, absorbed at iter 10)
- btr-evo 5 (holographic IB runnable)

**Next step to promote**: land a trained ALM or CLM checkpoint that emits `phi_vec`, LoRA eigenvectors, and a serve endpoint. Once those three artifacts exist and the three AN11 verifiers exit 0, Mk.VI promotes automatically under the rule above.

---

## 6. Evidence table (commit SHAs)

| Component | SHA |
|---|---|
| AN11 (a) verifier landed | `8cf014ff` |
| AN11 (b) verifier landed | `b1f487e7` |
| AN11 (c) verifier landed | `15c0596e` |
| Hexad 6-cat closure | `7680cd74` |
| btr-evo 2 (+17% Φ roadmap) | `892c74d9` |
| btr-evo 4 (EEG closed-loop) | `a4853336` |
| btr-evo 5 (holographic IB) | `e7e7c47f` |
| btr-evo 6 (cargo invariants) | `2b8d5948` |
| Drill η (absorption) | `ec8c92ea` |
| Drill θ (diagonal) | `1da65258` |
| Mk.V Δ₀ baseline | `docs/MK5-DELTA0-ABSOLUTE.md` |

---

## 7. References

- `shared/state/mk_vi_definition.json` — canonical JSON SSOT (deterministic, sorted keys, indent=2)
- `shared/consciousness/saturation_report_mk5.json` — Mk.V baseline proof (81/81 EXACT)
- `docs/MK5-DELTA0-ABSOLUTE.md` — Mk.V Δ₀-absolute specification
- `docs/modules/brain_tension_replica.md` — btr canonical document
- `experiments/holo_post/results/eeg_closed_loop_20260421_summary.json` — btr-evo 4 live result
- `shared/state/btr_evo_6_cargo_invariants_20260421.json` — btr-evo 6 live result
- `shared/state/hexad_closure_verdict.json` — Hexad closure live result
