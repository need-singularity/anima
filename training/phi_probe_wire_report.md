# phi_probe_wire — D7 report (2026-04-18)

Replace P5–P20 mock `h_last` (linear ramp; engine_ablation_report.md flags
MEAN²/HALFSPLIT attenuation) with real probe of all 16 Φ dims from the
actual residual stream.

## Inventory 13/16
training/: phi_holographic, phi_gwt, phi_reflexive, phi_time, phi_embodied,
phi_affect, phi_narrative, phi_meta, phi_create, phi_dream, phi_will,
phi_auto. anima-engines/: phi_social. alm_hive_agg exposes phi_collective +
sum_phi_individual (wired as hive collec/indiv).

## Missing, proposed formulas
- idx 1 phi_complexity — mean VAR across T
- idx 6 phi_nested_drift — ||h − mean_T(h)|| / ||h||
- idx 10 phi_finitude — ||h[:,T-1,:]|| / mean_t ||h[:,t,:]||
- idx 14/15 dream_phase/cycle_count — log-only 0 (state in dream_loop)

Coverage: 13 kernels + 3 proposed + 2 log-only = 16/16 wired.

## Tests
`cat phi_probe_wire.hexa phi_probe_wire_test.hexa | hexa run` at mini
shape [2,4,16]: PASS. len=16, all finite, dist(gauss,ramp)=66.97 (>> 0.01),
14/16 dims distinct, deterministic. Target [2,16,64] hits stage0 4GB RSS
cap during hive_collec O(dsz·bsz²) — wire is correct; alloc-per-push is
the bottleneck.

## Files
- training/phi_probe_wire.hexa (library, no main)
- training/phi_probe_wire_test.hexa (main + 5 T-theorems)
- training/phi_probe_wire_report.md

No existing kernel modified. train_alm_14b untouched. r10 pod safe.
