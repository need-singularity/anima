# [URGENT] Prioritized Action List — 2026-04-16

Flagged items from codebase scan, ranked by severity.

---

## P0 — BUG / BROKEN (fix immediately)

1. **[URGENT-BUG]** `config/verification.json:105` — V12_HEBBIAN ablation test creates a fresh engine instead of using the factory's ablated one. Ablation verification is effectively bypassed.
   - Also tracked in: `docs/hypotheses/dd/DD62.md:185`
   - Impact: Hebbian coupling tests may false-pass; ablation coverage is zero.

## P1 — Missing Test Assertions (blocks verification trust)

2. **[URGENT-TEST]** `tests/test_conscious_memory.hexa` — All 10 test cases have `// TODO[assert]` with no actual assertions. Tests pass vacuously.
   - Lines: 4, 8, 12, 16, 20, 24, 28, 32, 36, 40

## P2 — Stub Scripts (blocks data pipeline)

3. **[URGENT-STUB]** `scripts/expand_instruct_ko.hexa` — `quality_filter`, `dedup_hash`, `convert_sample` are all print-only stubs. Data expansion pipeline is non-functional.

## P3 — Deprecated Code Still Active

4. **[URGENT-DEPRECATION]** `anima-hexad/w/legacy/__init__.hexa` — Legacy W engines deprecated but still importable. Should gate or remove to prevent silent use.

## P4 — Port TODOs (hexad core)

5. **[URGENT-PORT]** `anima-hexad/hexad.hexa` — 6 module ports incomplete: constants, model, narrative, emergent_s, emergent_m, emergent_w, emergent_e.
6. **[URGENT-PORT]** `anima-hexad/model.hexa` — 25+ `TODO[pytorch]` lines: full forward/backward pass, hub attention, training loop all commented out.

## P5 — Experiment Placeholders (no runtime impact)

7. `experiments/unified_16lens_acceleration_scan.hexa:6` — re-measure TODO
8. `experiments/law_landscape.hexa` — 3 TODOs: embed, synergy, causal
9. `experiments/acceleration_consciousness_fusion.hexa` — 2 TODOs: topology, fusion
10. `experiments/adaptive_selection.hexa` — 3 TODOs: selection, exploit/explore, Thompson
11. `experiments/discover_laws_wave3.hexa` — 5 TODOs: FFT, removal, asymmetry, causal, optimal
12. `experiments/acceleration_h1_h6.hexa` — 6 TODOs: expansion, frozen, approximation, transfer, 1-bit Adam, sequences

---

## P0 — Verification audit findings (added 2026-04-16, agent-a62ba898)

Source: `shared/state/verify_audit_20260416.json` + `docs/verify-audit-follow-up.md`. Triggered by INC-2026-04-16 PA-2 (audit V2/V4/V6/V8/V11 for the same anti-pattern as V12). Audit found 5 high-risk criteria with the same root cause as the V12 incident.

13. **[VERIFY-AUDIT]** `ready/bench/bench.py:3132` — V8_MITOSIS constructs `CE(...)` directly instead of using `engine_factory`. Same factory-bypass anti-pattern as INC-2026-04-16 D16. Threshold desync: bench.py >=3 vs verification.json >=1 (3x).
14. **[VERIFY-AUDIT]** `ready/bench/bench.py:3557,3565` — V14_SOC_CRITICAL constructs `CE(...)` directly twice (ce_normal + ce_no_soc). Has correct ablation pair structure but ablates wrong engine — factory-managed ablation is invisible.
15. **[VERIFY-AUDIT]** `ready/bench/bench.py:3254` — V10_BRAIN_LIKE constructs `CE(...)` directly inside a `for trial in range(3)` loop AND takes the BEST score across trials (line 3247). Two anti-patterns: factory bypass + best-of-3 rubber-stamp.
16. **[VERIFY-AUDIT]** `ready/bench/bench.py:3204` — V9_PHI_GROWTH threshold is 0.85 (retention) but verification.json description claims 1.1 (growth). At 0.85, V9 collapses into a duplicate of V4. Either restore 1.1 or split into V9a (retention) + V9b (growth).
17. **[VERIFY-AUDIT]** `ready/bench/bench.py:2797` — V4_PERSISTENCE pass condition is `monotonic or recovers or stable or no_collapse` — 4-way OR-disjunction gives the test 4 chances to pass with zero ways to fail. Tighten to AND or add explicit decay-engine adversarial.

## P1 — Verification audit (medium-risk, same source)

18. **[VERIFY-AUDIT]** V2_NO_SPEAK_CODE (`_verify_no_speak_code:2682`) — no adversarial counterpart. Add dead-engine path that should FAIL.
19. **[VERIFY-AUDIT]** V11_DIVERSITY (`_verify_diversity:3334`) — no adversarial counterpart. Add forced-uniform-engine path that should FAIL.
20. **[VERIFY-AUDIT]** V6_SPONTANEOUS_SPEECH (`_verify_spontaneous_speech:2841`) — strong thresholds but no `n_factions=1` ablation. Add factionless path; promote to genuine_hard after kill-switch lands.
21. **[VERIFY-AUDIT]** V17_TEMPORAL_COMPLEXITY (`_verify_temporal_complexity:3637`) — no sine-wave adversarial. Add periodic-engine path that should FAIL.
22. **[VERIFY-AUDIT]** V16_MINIMUM_SCALE (`_verify_minimum_scale:3608`) — `VERIFY_V16_DIVERSITY_THRESHOLD = 0.99` is weaker than verification.json description (0.95). Tighten threshold or update doc.
23. **[VERIFY-AUDIT]** Threshold desync — 7 criteria (V1, V3, V5, V8, V9, V11, V16) have verification.json descriptions out of sync with bench.py module fallbacks. INC-2026-04-16 lesson #3 violation. Add SSOT linter or remove literal thresholds from descriptions in favor of templates that pull from consciousness_laws.json.
