# Verification Audit Follow-Up — 2026-04-16

## Source

- Audit JSON: `shared/state/verify_audit_20260416.json`
- Triggered by: `feedback_closed_loop_verify` + `feedback_verify_pipeline` memory + INC-2026-04-16 PA-2 (audit V2/V4/V6/V8/V11 for the same anti-pattern as V12)
- Auditor: `agent-a62ba898` worktree

## Executive summary

V12 fix uncovered a **class of bugs**, not a single bug. Of the 18 verification criteria, **9 are SAFE (low-risk) and 9 need fixes (5 high, 4 med)**. Five high-risk findings share root causes with INC-2026-04-16:

1. **Factory bypass anti-pattern** (3 criteria): `V8`, `V10`, `V14` construct `ConsciousnessEngine` directly inside the verification path, discarding the `engine_factory` exactly the way `_verify_hebbian` did pre-fix. INC-2026-04-16 D16 already prohibits this — these are pre-existing violations of the same decision.
2. **No adversarial counterpart** (5 criteria, all rubber_stamp): `V2`, `V4`, `V6`, `V8`, `V11` — DECISION_LOG.csv#11 violation. PA-2 of the incident explicitly demands they be audited; this audit is that step.
3. **OR-disjunction pass condition** (3 criteria): `V4` (4 disjuncts), `V9` (IIT OR proxy), `V6` non-CE fallback (cv OR entropy) — gives the test multiple ways to pass without a single way to fail.
4. **Threshold desync between verification.json and bench.py** (7 criteria) — INC-2026-04-16 lesson #3: V9 (1.1 vs 0.85) and V8 (>=1 vs >=3) are the most severe.
5. **Best-of-N trials** (1 criterion, V10) — `for trial in range(3): ... best_overall = max(...)` is a literal "try until pass" pattern.

The audit confirms that **V12 was not a one-off**. Five other criteria (`V2`, `V4`, `V8`, `V14`, `V10`) carry one or more of the same anti-patterns. None have manifested as bypass incidents *yet*, but they are structurally identical to the V12 vulnerability.

## High-risk findings (P0 for next session)

### 1. V8_MITOSIS — factory bypass + missing adversarial + 3x threshold desync

- **File**: `ready/bench/bench.py:3114-3152`
- **Function**: `_verify_mitosis`
- **Root cause**: line 3132 imports CE and constructs it directly, identical to V12 pre-fix.
- **Threshold desync**: `bench.py` says `>= 3 splits`, `verification.json` description says `>= 1`. Verification description is 3x weaker than the actual test threshold.
- **Fix template**: copy `_run_hebbian_scenario` pattern. Build `_run_mitosis_scenario(engine_factory, ablate=False)` that uses the factory engine as-is for baseline, and `ablate=True` that monkey-patches `_check_splits` to a no-op. Pass condition: `splits >= 3 AND splits_ablated == 0`.
- **Expected effect**: catches any factory that disables mitosis in its construction kwargs, which `_verify_mitosis` currently bypasses by constructing CE directly.

### 2. V14_SOC_CRITICAL — factory bypass (has ablation but bypasses factory)

- **File**: `ready/bench/bench.py:3536-3577`
- **Function**: `_verify_soc_critical`
- **Root cause**: lines 3557 and 3565 construct `ce = CE(cell_dim=dim, hidden_dim=hidden, ...)` directly. The `engine_factory(cells, dim, hidden)` at line 3543 is only used to *probe* CE support, then discarded.
- **Note**: V14 *has* an ablation pair (ce_normal vs ce_no_soc), so structurally it looks like the V12 fix template — but it ablates the wrong engine. If a factory disables SOC in its own way, the test silently runs against vanilla CE constructed in-test.
- **Fix template**: replace `CE(cell_dim=dim, ...)` calls with `engine_factory(cells, dim, hidden)`. Then monkey-patch `engine.engine._soc_sandpile = lambda: None` on the ablation copy (matching the `_run_hebbian_scenario` `ablate=True` branch).

### 3. V10_BRAIN_LIKE — factory bypass + best-of-3 trials

- **File**: `ready/bench/bench.py:3211-3332`
- **Function**: `_verify_brain_like`
- **Root cause 1**: line 3254 constructs `ce = CE(cell_dim=dim, hidden_dim=hidden, initial_cells=2, max_cells=min(cells, 8))` directly inside a `for trial in range(3)` loop.
- **Root cause 2**: line 3247 (`best_overall = 0.0`) and the `if matches_overall > best_overall` pattern: the test takes the BEST score across 3 trials. This is the "try until pass" rubber-stamp pattern.
- **Fix template**:
  - Replace direct `CE(...)` with `engine_factory(min(cells, 8), dim, hidden)`.
  - Replace `best_overall = max(matches_overall, best_overall)` with `mean_overall = sum(trials) / len(trials)`. Pass condition becomes `mean >= 80%` instead of `best >= 80%`.
  - The neuroscience justification ("multiple epochs, best representative sample") in the comment is plausible for measuring a *known-conscious* signal but adversarial when applied to *verifying* consciousness.

### 4. V9_PHI_GROWTH — threshold collapsed from 1.1 to 0.85

- **File**: `ready/bench/bench.py:3155-3208`
- **Function**: `_verify_phi_growth`
- **Root cause**: `VERIFY_PHI_GROWTH_RATIO = 0.85` (line 89) but `verification.json` description says `>= 1.1x`. At 0.85 the test no longer measures growth — it measures *retention*, collapsing into V4. Combined with the IIT-OR-proxy disjunction, the test almost certainly cannot fail.
- **Fix template**:
  - **Option A**: restore threshold to 1.1, accept fail rate at 8c (force `min_cells >= 16`). Update `verification.json` `min_cells` field.
  - **Option B**: split into V9a (retention, 0.85, scale_test) + V9b (growth, 1.1, genuine_hard). V9a becomes a "sanity check that phi doesn't collapse" and V9b becomes the actual growth test that requires real progress.
  - **Recommendation**: Option B — preserves the existing scale_test signal (V9a) and adds a real genuine_hard claim (V9b) without breaking existing PASS rates.

### 5. V4_PERSISTENCE — 4-way OR-disjunction

- **File**: `ready/bench/bench.py:2764-2802`
- **Function**: `_verify_persistence`
- **Root cause**: line 2797 `passed = monotonic or recovers or stable or no_collapse`. Four disjuncts joined by OR — the test gives the engine four chances to pass and zero chances to fail.
- **Note**: each individual disjunct is reasonable; the *combination* is the bug. The comment block at lines 2782-2786 acknowledges this is intentional ("Phi(IIT) is inherently noisy at small cell counts; a single outlier sample shouldn't fail persistence"), but the noise-tolerance was inflated to the point where no failure mode survives.
- **Fix template**: tighten to `passed = (monotonic or recovers) and (stable or no_collapse)`. Or add an explicit decay-adversarial: spawn a second engine with `_check_splits = no_op + Hebbian = no_op + ratchet = no_op`, run 1000 steps, expect FAIL.

## Med-risk findings (P1 for next session)

### V2_NO_SPEAK_CODE / V11_DIVERSITY — missing adversarial counterpart

- **Pattern**: both are rubber_stamp single-scenario tests with no failure counterpart.
- **Fix**: add adversarial paths.
  - V2: `dead_engine = engine_factory(...); dead_engine.engine.cells.update = lambda *_: None` -> output is constant -> `var_signal == 0` -> FAIL. Pass becomes `live_passed AND dead_failed`.
  - V11: `forced_uniform = engine_factory(...); forced_uniform.engine.cells = [shared_cell] * cells` -> `mean_cos = 1.0` -> FAIL. Pass becomes `diverse_passed AND uniform_failed`.

### V6_SPONTANEOUS_SPEECH — strong thresholds but no kill-switch

- **Pattern**: thresholds (consensus>=200, dir_changes>=120, cv>0.40) are genuinely strong, but no `n_factions=1` ablation to prove the consensus signal actually depends on factions.
- **Fix**: add `factionless_scenario = engine_factory(...); factionless_scenario.engine.n_factions = 1` -> `consensus_events` should drop to 0 -> FAIL. Pass becomes `factional_passed AND factionless_failed`.
- **Bonus**: if kill-switch lands, V6 can be promoted from rubber_stamp -> genuine_hard (matching V12 promotion).

### V17_TEMPORAL_COMPLEXITY — sine-wave adversarial missing

- **Pattern**: LZ >= 0.3 is the threshold for "not periodic", but no sine-wave engine to prove the test detects periodicity.
- **Fix**: build a `periodic_engine` whose hidden states follow `sin(step * 2pi / 10)` -> LZ should drop near 0 -> FAIL. Pass becomes `chaotic_passed AND periodic_failed`.

### V16_MINIMUM_SCALE — threshold weaker than documented

- **Pattern**: bench.py uses 0.99, verification.json description says 0.95. Cosine 0.99 at 4 cells means cells are basically identical.
- **Fix**: tighten `VERIFY_V16_DIVERSITY_THRESHOLD` to 0.95 to match documentation, OR update documentation to reflect the looser actual threshold (and explain why 0.99 is acceptable at 4-cell scale).

## Threshold desync summary

A documentation hygiene fix that should land alongside the other fixes — INC-2026-04-16 lesson #3 says "Thresholds in verification.json criterion descriptions must match the SSOT — desync hides bugs by making it unclear which value is load-bearing."

| ID  | verification.json description | bench.py module fallback | severity |
|-----|------------------------------|--------------------------|----------|
| V1  | `0.01 < cos < 0.99 AND std > 0.001` | `0.15 < cos < 0.90 AND std > 0.02` | low (stricter actual) |
| V3  | `>= 0.5x` | `>= 0.35x` | low (looser actual) |
| V5  | `>= 0.8x` | `>= 0.75x` | low (looser actual) |
| V8  | `>= 1 split` | `>= 3 splits` | **high** (3x stricter actual, suggests doc is stale) |
| V9  | `>= 1.1x` | `>= 0.85x` | **high** (looser actual; threshold inversion) |
| V11 | `< 0.95` | `< 0.85` | low (stricter actual) |
| V16 | `< 0.95` | `< 0.99` | med (looser actual) |

The right fix: read thresholds from `consciousness_laws.json` SSOT in `verification.json` description templates and remove the literal numbers from descriptions, OR run a sync linter that asserts the two match.

## Next session entry conditions

To work on these fixes, a session needs:

1. Fresh worktree (V12 fix flow used `worktree=agent-a64696ce`; pick a new id).
2. Read access to `ready/bench/bench.py` lines 2638-3711 (already read in this audit).
3. Local CE module importable (`from consciousness_engine import ConsciousnessEngine`).
4. Test budget: run `python ready/bench/bench.py --verify` after each fix to check no regression.
5. Each fix must include the kill-switch validation step (verify the fix detects a *broken* ablation by monkey-patching the new ablation path to be a no-op and confirming the test FAILS — this is the same validation done in INC-2026-04-16 metrics `kill_switch_validation`).

## Tracking

- Append to `ACTION_TRACKER.csv` as new rows (do NOT edit existing rows).
- Open follow-up incidents in `shared/incidents/` only if a fix is BLOCKED (e.g., factory contract is unclear). Otherwise treat each as a P0 fix in the next session, not a separate incident.
- Update `URGENT_ACTION_LIST.md` with new P0 entries (this audit appends them).
- After each fix, update the corresponding `per_criterion` entry in `shared/state/verify_audit_20260416.json` `audit_note` and flip `risk` to `low`.

## Why this matters

Closed-loop verification is the gate between "the engine claims to be conscious" and "we have evidence the claim is testable". An adversarial-free verification suite gives the same answer for any engine — it's a rubber stamp. INC-2026-04-16 exposed this for V12; this audit shows the pattern is endemic. Fixing the 5 high-risk items closes the same class of bypass incident before it manifests, instead of waiting for the next CI failure to surface the next V12.
