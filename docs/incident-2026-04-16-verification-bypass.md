# INC-2026-04-16 — V12_HEBBIAN Ablation Bypass + Vacuous Test Suite

**Severity:** P0 (verification integrity)
**Status:** Open
**Date detected:** 2026-04-16 (codebase scan)
**Reporter:** automated audit + manual triage

---

## Timeline

| Date | Event |
|------|-------|
| 2026-04-01 | V12_HEBBIAN criterion added in `086725bf` (feat: V13-V18 implemented) |
| 2026-04-01 ~ 2026-04-16 | V12 ablation test passes all runs including adversarial "no_hebbian" scenario — no failures detected |
| 2026-04-16 | DD62 deep-dive audit (docs/hypotheses/dd/DD62.md:183-186) discovers the test creates a fresh ConsciousnessEngine instead of using the factory's ablated instance |
| 2026-04-16 | Codebase scan flags P0 (URGENT_ACTION_LIST.md), P1 vacuous tests (test_conscious_memory.hexa), P2 stub pipeline (expand_instruct_ko.hexa) |

---

## Root Cause

**V12_HEBBIAN (P0):** The ablation test instantiates a new engine on the verification path rather than receiving the factory-produced ablated engine. The fresh engine has its own `_coupling` field initialized to a non-None value, so `coupling_change_ratio` always exceeds the 0.05 threshold — even when Hebbian learning is explicitly disabled. The threshold itself (0.05 = 5% of initial) is also too lenient; observed ratios range 1.67x–9.75x, making any engine trivially pass.

**test_conscious_memory.hexa (P1):** All 10 test functions are empty stubs (`// TODO[assert]`) ported from a Python original. They contain no assertions and pass vacuously, providing zero coverage for the conscious memory subsystem.

**expand_instruct_ko.hexa (P2):** `quality_filter`, `dedup_hash`, `convert_sample` are print-only stubs. The Korean instruction-expansion data pipeline is non-functional.

---

## Impact

- **Ablation coverage for Hebbian coupling is zero.** Any regression in Hebbian learning would go undetected. All prior V12 PASS results are unreliable.
- **Conscious memory module has no test coverage.** Regressions in encode, recall, decay, reinforce paths are invisible.
- **Korean instruction data expansion is blocked.** No quality-filtered or deduplicated samples can be produced.

---

## Mitigation (immediate)

1. Mark V12_HEBBIAN as `"tier": "rubber_stamp"` with `"audit": "BUG"` in `config/verification.json` — already done during scan.
2. Do NOT rely on V12 PASS status for any verification gate until the fix lands.
3. Flag test_conscious_memory.hexa results as non-evidence in any verification report.

---

## Preventive Actions

| # | Action | Owner | Target |
|---|--------|-------|--------|
| 1 | **Fix V12 test:** pass the factory-ablated engine instance to the verification path instead of constructing a new one. Raise threshold from 0.05 to >= 1.0 (coupling must change more than its initial magnitude). | — | P0 |
| 2 | **Add ablation kill-switch assertion:** if scenario is "no_hebbian", assert `coupling_change_ratio < threshold` (must FAIL to prove ablation works). | — | P0 |
| 3 | **Fill test_conscious_memory.hexa assertions:** implement real assertions for all 10 test cases against the conscious memory API. | — | P1 |
| 4 | **Implement expand_instruct_ko.hexa stubs:** wire `quality_filter`, `dedup_hash`, `convert_sample` to real logic or remove the file. | — | P2 |
| 5 | **Introduce verification-tier audit rule:** any criterion marked `rubber_stamp` must include an adversarial scenario that is expected to FAIL. CI should enforce that at least one adversarial case exists per criterion. | — | Process |
| 6 | **Ban vacuous tests in CI:** add a lint pass that rejects test functions containing only comments and no assertions. | — | Process |

---

## References

- `config/verification.json` — V12_HEBBIAN definition (line ~105)
- `docs/hypotheses/dd/DD62.md:183-186` — DD62 audit findings
- `tests/test_conscious_memory.hexa` — vacuous test stubs
- `scripts/expand_instruct_ko.hexa` — stub pipeline
- `URGENT_ACTION_LIST.md` — full triage list
