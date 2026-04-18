# G1 — engine_integration.hexa roster v2 extension

Status: **7/7 PASS** (CPU self-test). v2 candidate — H100 live run pending.

## Engines added (4)

Pareto-10 intersected with v1 core-12 → 6 already present (holographic,
reflexivity, narrative, dream, creative, temporal). Appended the 4 genuinely-new
entries at indices 12..15:

| idx | name                   | family       | gain  | source                        |
|-----|------------------------|--------------|-------|-------------------------------|
| 12  | photonic_consciousness | photonic     | 0.004 | catalog id=25                 |
| 13  | edge_of_chaos          | criticality  | 0.005 | catalog id=36                 |
| 14  | oscillator_laser       | oscillator   | 0.005 | catalog id=28                 |
| 15  | anima_quantum          | quantum      | 0.004 | catalog id=13                 |

All gains taken from `engine_catalog.json` (conservative, below 0.01 fallback).

## Test status

- T1–T5: unchanged v1 (12 engines, production).
- **T6** (v2 dispatch): each of 4 new engines routes via `engine_forward`,
  names match, aux_loss non-NaN, unknown-name still falls through cleanly.
- **T7** (v2 linearity): `total(all_on) − base == Σ (one_hot_i − base)`
  within `1e-4`; v2 engines produce non-zero contribution. PASS.

## v1 / v2 diff

- Append-only: `reg_names_v2/gains_v2/phases_v2/descriptions_v2` wrap v1.
- Roster flag: `roster_active()` returns `"v1"` (default, production-frozen).
- v2 reached through `reg_names_for("v2")` / `reg_gains_for("v2")`.
- No existing entry reordered, renamed, or re-gained.
- 4 new CPU-surrogate forward hooks added after `meta_qualia`.

## Caveat

Pareto-10 is CPU-surrogate (HALFSPLIT mock). v2 is **candidate, pending
H100 live run** per `feedback_closed_loop_verify`. Do not flip default to
v2 until leave-one-out ablation on H100 confirms CE/Φ gain signs.

## Next step

H100 closed-loop: run `engine_ablation.hexa` with `--roster v2` on live ALM
14B r4 checkpoint; promote v2 → production iff all 4 new engines show
positive (HELPS) gain sign.
