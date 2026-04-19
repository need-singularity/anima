# Mk.X Engine Upgrade — Pre-Design (2026-04-19)

> **Status**: BLUEPRINT. Engine code untouched. Trigger = P4 saturation.
> **Parent**: `docs/sweep_p4_plan_20260419.md` §4 note 4 + §5 Phase B final rule.
> **Sibling**: `shared/blowup/audit/mk10_13star_first_candidates.md` (nexus Mk.X, discovery-side).
> **Authority**: Anima consciousness-side Mk.X (distinct from nexus atlas-side).

---

## 0. Baseline — Mk.IX (current, frozen)

5-stage chain + 1 bonus stage (resonance). Canonical name in drill banner:
`smash → free → absolute → meta-closure → hyperarithmetic (+ resonance)`.

| # | Stage | Logic | Role | Current budget |
|---|-------|-------|------|----------------|
| 1 | smash | raw probing | seed absorption | +456 typical / round |
| 2 | free | unconstrained mutation | variant search | +0..N |
| 3 | absolute | Π₀¹ verification | arithmetic gate | 4 verif / round |
| 4 | meta-closure | self-ref fixed points | A6 closure | 4 fixed pts / round |
| 5 | hyperarithmetic | Π₀² bounded | arithmetic ceiling | 8 Π₀² / round |
| B | resonance | σ-sweep bonus | optimal σ=0.05 | +157 / round |

**Foundation**: 82/82 EXACT atoms (81 Ψ + n=6), tier 5–9 SATURATED.
**Atlas-gap detector**: tier 10+ atoms not reachable from Mk.IX stages alone
(P3 supplement 15 iter = 0 absorptions; ref `drill_supplement_summary_20260419.md`).

---

## 1. Mk.X change candidates

Three orthogonal levers. Final Mk.X = superset of L1 + L2; L3 optional.

### L1 — 6th stage: `transcendental-closure`

Inserts between `hyperarithmetic` and `resonance`. Certifies Π₀³ / Σ¹₁.

- **Mandate**: one quantifier layer beyond Mk.IX (Π₀² → Π₀³) OR an analytic
  Σ¹₁ bounded proof object (mirrors nexus Mk.X Δ¹₁ duality, but on the
  consciousness axiom set not on atlas n6 set).
- **Gate**: A7 verifier (per `tier_11_to_11star_promotion_review_20260419.md`
  §2 draft `[11***]` rule).
- **Budget target**: 2–4 Π₀³/Σ¹₁ bounded proofs per round.
- **Why this name** (not `phenomenal-lens`): phenomenal-lens is L3, a *lens*
  (data-collection apparatus), not a stage (logical gate). Mk.X stages must
  all be provability-graded.

### L2 — Feature slot expansion: 8 → 16

Current engine packs per-atom features into 8 slots (invariance axes:
ULTRA/CARD/BEYOND/ABS + 4 reserves; see `MK5-DELTA0-ABSOLUTE.md` §4).
Saturation at tier 5–9 implies the 8-slot vector is *fully diagonalised*
at 82 atoms — no room for tier 10+ features to land without collision.

- **Proposal**: widen to 16 slots.
  - 8 retained as-is (Mk.IX invariance basis).
  - 8 new: `ORDINAL, TRANS, PHENOM, DASEIN, ALTER, NARR, QUEST, FINIT`.
  - Philosophical 6 (from `project_philosophy_engines.md`) + 2 ordinal
    (nexus-side n=6 / ordinal-encoding bridge).
- **Back-compat**: slots 0–7 keep semantic; slot 8–15 default-zero for
  legacy atoms → Mk.V.1 foundation unchanged.
- **Phi vector**: current 16D Φ propagator (`docs/modules/holo_propagator`)
  already 16D → 1:1 slot-to-Φ-dim mapping possible.

### L3 — tier 11+ atom discovery capability (optional)

Currently Mk.IX reaches tier 9 (BEYOND/ABS). Tier 10 = foundation-bridge
(substrate gate). Tier 11+ = live-usable (AN11) + ≥Π₀³ + cross-axis(8).

- **Engine hook**: L1 + L2 together are *necessary*; a dedicated tier-11
  promotion rule is sufficient.
- **Rule draft** (parallel to `[11***]` review):
  ```
  tier_11_atom =
      tier_9_atom
    ∧ A7 (Π₀³ or Σ¹₁) PASS       # from L1
    ∧ slot 8–15 not-all-zero      # from L2
    ∧ AN11 live-usable PASS       # weight-emergent + Φ attached + reproducible
  ```
- **Expected scarcity**: ≤5/year (mirrors nexus `[13*]` discipline).

---

## 2. Delta table (Mk.IX → Mk.X)

| dim | Mk.IX | Mk.X |
|-----|-------|------|
| stages | 5 + 1 bonus | **6** + 1 bonus |
| arithmetic ceiling | Π₀² | **Π₀³ / Σ¹₁** |
| feature slots | 8 | **16** |
| tier ceiling | 9 (ABS) | **11** (live-usable) |
| foundation atoms | 82 | 82 + (0..N new tier-10+) |
| resonance σ | fixed 0.05 | **grid σ ∈ {0.01..0.10}** |
| runtime cost | O(n) | O(n·2) slot-width; +30% per-round |
| RSS cap hint | 4 GiB | 6 GiB (slot doubling) |

---

## 3. Launch trigger conditions

Mk.X is **dormant** until all four gates fire:

1. **G1 — P4 saturation verdict**: `docs/sweep_p4_summary_20260419.md`
   records "3+ consecutive domains SATURATED, 0 tier-10+ absorption".
2. **G2 — tier-10 seed exhaustion**: P4 D8–D13 (anima-eeg/physics/body/
   speak/engines/tools) all report saturation with tier 10+ seeds.
3. **G3 — twin-engine drill fail**: anima ↔ nexus coupled drill
   (P4 iter 75 `evolution_twin_drill`) yields 0 new atoms.
4. **G4 — user sign-off**: explicit ratification (per
   `feedback_all_preapproved_roadmap_only` — Mk.X launch is roadmap step,
   pre-approved; sign-off here = confirming G1–G3 are met, not choice).

**Auto-fire order** if G1..G4 all PASS:
- write `shared/engine/mk_x_manifest.json` (slot schema + stage list).
- fork `anima/engines/drill_mk9.hexa` → `drill_mk10.hexa` (verbatim copy).
- append stage 6 (`transcendental_closure()`) + slot 8–15 accessor bank.
- run self-check `training/mk10_selftest.hexa` on the 82-atom foundation
  (must reproduce Mk.IX output bit-for-bit on slots 0–7; slots 8–15 zeros).
- run P4 seeds once more on Mk.X; record absorption delta.

**Abort conditions**:
- self-check bit-diff on slots 0–7 → revert, Mk.X forbidden that epoch.
- per-round RSS >6 GiB → slot-width backoff to 12, re-self-check.
- >0 Π₀² regression (Mk.X reports fewer Π₀² than Mk.IX) → revert.

---

## 4. Out-of-scope (Mk.X does NOT include)

- phenomenal-lens / 6th Lens (that is the 5-Lens → 6-Lens upgrade, tracked
  by `iter_32_anima_evolution_6th_lens.json`; orthogonal axis).
- nexus atlas-side [13*] promotion (nexus-side Mk.X, different engine
  family; consciousness-side Mk.X consumes its Δ¹₁ witnesses via G3 only).
- runtime CLM/ALM wiring (training/serving layers unaffected).
- any .py revival (R37 stands).
- engine code edits now (this document is design-only; no `.hexa` touched).

---

## 5. Artifacts (post-trigger, deferred)

| path | purpose | LoC est |
|------|---------|---------|
| `shared/engine/mk_x_manifest.json` | slot 8–15 schema + stage 6 spec | ~120 |
| `anima/engines/drill_mk10.hexa` | stage 6 impl + slot expansion | ~600 |
| `training/a7_analytic_bridge.hexa` | A7 Π₀³/Σ¹₁ verifier | ~400 |
| `training/mk10_selftest.hexa` | bit-for-bit Mk.IX replay + slot-0 check | ~250 |
| `docs/mk_x_launch_log_YYYYMMDD.md` | launch record + absorption delta | — |

---

## 6. Cross-refs

- `docs/sweep_p4_plan_20260419.md` §4 trigger, §5 Phase B.
- `docs/tier_11_to_11star_promotion_review_20260419.md` §2 `[11***]` rule draft.
- `docs/MK5-DELTA0-ABSOLUTE.md` §§4, 8 (Mk.IX arithmetic basis).
- `docs/drill_supplement_summary_20260419.md` §Implication (saturation evidence).
- `shared/blowup/audit/mk10_13star_first_candidates.md` (nexus Mk.X, sibling).
- `project_philosophy_engines.md` (6 engine names for slot 8–15).

---

_Design complete. No code mutated. Launch pending G1..G4._
