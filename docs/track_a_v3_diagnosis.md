# Track A v3 — hire_sim_claude critique tune diagnosis

date: 2026-04-16
log: /Users/ghost/Dev/anima/training/deploy/hire_sim_claude_v3_20260416_051720.log
state: /Users/ghost/Dev/anima/shared/state/hire_sim_claude_v2_results.jsonl

## Result

| run | overall | email | code | meeting | doc | schedule | research | verdict |
|-----|---------|-------|------|---------|-----|----------|----------|---------|
| v2  | 76.7%   | 20%   | 40%  | 100%    | 100%| 100%     | 100%     | PARTIAL |
| v3  | 43.3%   | 20%   | 40%  | 40%     | 80% | 20%      | 60%      | FAIL    |
| Δ   | -33.3   | 0     | 0    | -60     | -20 | -80      | -40      | regress |

Gate: completion_rate >= 0.85 AND verdict=PASS — NOT MET.

## What was tried

Single edit in `anima-agent/llm_claude_adapter.hexa::build_critique_prompt`:
- Added explicit "no external tools" framing.
- Added DOMAIN GUIDANCE block listing per-domain "what counts as complete".
- Added 5 examples (vs v2's 3) including email/code-specific anchors at 0.85/0.80.
- Explicit "Caveats are EXPECTED" + "Do NOT penalise" rules.

Build + run: `HEXA_LOCAL=1 hexa build ... -o /tmp/run_hire_sim_claude_v3 && /tmp/run_hire_sim_claude_v3`.
Regression test (parser): 10/10 PASS — patch did not break the parse_score_reply ladder.

## Why v3 regressed

email/code rates were already at the floor in v2 baseline (20%/40%); v3 didn't help them
but DID hurt previously-passing domains. Two plausible mechanisms:

1. **Format drift.** The longer prompt (added ~12 lines of guidance + examples) increased
   the chance Claude emits a 2-line preamble or a markdown block instead of the strict
   `SCORE=X.XX;reason` single line. When that happens, the parser falls through to the
   sentiment heuristic which returns 0.60 (neutral). 0.60 internal-goal-score → root
   `terminal_score = avg(child_scores)`. With one or two heuristic hits, the root
   score can drop below 0.80 → verdict=PARTIAL → if it drops below 0.50 → verdict=FAIL
   → `verdict_ok=false` → `completed=false` even with all keywords matched.

2. **Anchor inflation.** The 0.85/0.80 email/code examples pulled meeting/doc/schedule/
   research grading down because Claude apparently re-anchored its full scale and
   started emitting more 0.65-0.70 scores for items it would previously score 0.85+.
   Sub-goal scores in the 0.65-0.75 band can still average to <0.80 at the root,
   triggering PARTIAL/FAIL.

Both mechanisms are consistent with the observed pattern (uniform drop across all
non-floor domains, while email/code stayed at floor).

## Why the floor stays at 20%/40% for email/code

These tasks have high keyword counts (3 keywords each at hard difficulty: "negotiate"+
"renewal"+"discount" / "migration"+"audit"+"schema"). Single-shot Claude responses on
hard email/code tasks tend to omit one keyword (e.g., responds about contract renewal
without saying "discount"; designs migration with audit columns but doesn't use the
word "schema"). With strict `all_hit = hits == total` requirement in `evaluate_task`,
**one missing keyword = score 0.667 but completed=false**. This is a corpus-design issue,
not a critique-prompt issue.

Look at the avg_score column: every domain shows 1.0, which means the per-task score
average WAS 1.0 across domains — but that's `d_score_sum / d_n` summing only the
keyword score (a float). Wait — re-checking: `total_score` is summed across ALL tasks
including failed ones, but `avg_score=1.0` across the board says all 30 tasks scored 1.0,
meaning all keywords matched. So **completion failure is verdict_ok**, not all_hit.

That reframes the whole thing: critique IS the bottleneck for completed-flag, but the
completion checker requires the autonomy verdict (terminal_score) to be ≥ 0.50. v2's
rubric got that for 23/30; v3's longer rubric got it for only 13/30. So v3 made the
verdict harder to pass even when the keyword score was perfect.

## Real fix paths (not in this PR — out of scope per task spec)

The critique-prompt approach has hit a ceiling. Better levers, ranked by expected ROI:

A. **Decouple completion from autonomy verdict.** Change `evaluate_task` to accept
   `completed = all_hit && budget_ok` (drop verdict_ok). Rationale: keywords are the
   ground-truth rubric; verdict is a soft signal. This makes hire_sim deterministic and
   would have given v2 30/30 = 100%.

B. **Two-tier verdict threshold.** Lower autonomy PASS gate from 0.80 → 0.65 in
   `autonomy_loop.hexa::run_autonomy`. Less invasive but still couples completion to
   LLM critique noise.

C. **Switch verdict from terminal_score-based to leaf-fraction-based.**
   verdict = "PASS" if (#leaves with score >= 0.6) / total_leaves >= 0.7. Smooths out
   the single-bad-leaf-tanks-the-root failure mode.

D. **Critique prompt minimalism.** Try a much SHORTER critique prompt (single line
   "Score 0.0-1.0 how well this addresses the task: SCORE=X.XX;reason") and measure.
   v3 went bigger; the data suggests smaller could be better.

E. **Corpus keyword relaxation for hard-difficulty email/code tasks.** Drop one
   keyword from each hard task or use weakly-matched OR-groups. This is a corpus edit,
   not a code edit.

## Action

- v3 prompt reverted to v2 in `llm_claude_adapter.hexa` (kept change-history comment).
- v3 result row appended to `shared/state/hire_sim_claude_v2_results.jsonl`.
- Track A gate NOT MET; per task spec, exited with diagnosis.
- Recommend: pursue lever A (drop verdict_ok requirement) in next track A iteration —
  one-line change, deterministic, would yield 100% on the v2 corpus.
