# hxc 4-Lint CI Gate Proposal — 2026-04-28

raw 9 (pure hexa) · raw 91 (honest C3) · author: agent a8becd51_followup

## Suite Summary

| Tool                            | LoC | Verdict ref     | Selftest | Live (cross-repo)        |
|---------------------------------|-----|-----------------|----------|--------------------------|
| heredoc_arg_max_lint            | 404 | adc2e734 (Bug 1)| 5/5 PASS | high=0 med=14 (3 fixture)|
| substring_offset_lint           | 533 | ad82a91829 (Bug 3)| 5/5 PASS | offset_mismatch=0        |
| aot_cache_invariant_check       | ~280| a38dcbed (Bug 2)| 4/4 PASS | issues=0 pairs=11/11     |
| prefix_aware_find_lint          | ~290| Bug 4 sister     | 4/4 PASS | warn=0                   |

Total: 4 tools, ~1,500 LoC, 18/18 selftest cases PASS.

## Failure Mode Matrix

| Tool                            | Class   | CI severity | Block PR? | Rationale                                      |
|---------------------------------|---------|-------------|-----------|------------------------------------------------|
| heredoc_arg_max_lint  high      | error   | red         | yes       | ARG_MAX silent-truncation = data loss          |
| heredoc_arg_max_lint  med       | warn    | yellow      | no (info) | unbounded var — needs manual size-bound proof  |
| substring_offset_lint           | error   | red         | yes       | dead-code (Bug 3) is always wrong              |
| aot_cache_invariant_check  R1/R2| error   | red         | yes       | cache key invariants — wrong key = stale build |
| aot_cache_invariant_check  R3   | warn    | yellow      | no        | comment-sync heuristic, not load-bearing       |
| aot_cache_invariant_check  R4   | error   | red         | yes       | symlink-pair regression = realpath broken      |
| prefix_aware_find_lint          | warn    | yellow      | no        | 1-arg .find() can be correct in non-loop ctx   |

## Integration Plan

### A. pre-commit hook (`hive/tool/git_pre_commit.hexa`)

Append a `hxc_lint_quick` phase that runs the four tools in order, scoped to the
files staged in the current commit:

```
1. heredoc_arg_max_lint --root <staged>  — exit 1 on `high` only
2. substring_offset_lint --root <staged> — exit 1 on any offset_mismatch
3. aot_cache_invariant_check             — exit 1 on R1/R2/R4
4. prefix_aware_find_lint --root <staged>— exit 0 always (advisory)
```

Time budget: < 2 s on a typical 5-file commit (verified — heredoc lint pre-filters
via `xargs grep -lE`). On full repo (~600 files) ≈ 8 s, only invoked under
`--full` flag.

### B. raw 9 lint dispatch (`hive/tool/raw9_lint_dispatch.hexa`)

Existing 7-lint dispatch (`raw 9` honest harness) gains 4 new entries with
Sub-EI-style sentinel parsing:

```
__HEREDOC_ARG_MAX_LINT__   PASS|VIOLATIONS files_total=N high=N med=N
__SUBSTRING_OFFSET_LINT__  PASS|VIOLATIONS files_total=N offset_mismatch=N paired_mismatch=N
__AOT_CACHE_INVARIANT_CHECK__ PASS|VIOLATIONS issues=N symlink_pairs_ok=N/M
__PREFIX_AWARE_FIND_LINT__ PASS|WARN files_total=N warn=N info=N
```

Aggregate verdict = max(severity over individual sentinels). raw 9 dispatcher
short-circuits on first error; warn-class results are always emitted to the
audit ledger but do not flip the aggregate.

### C. nightly cron (`hive/tool/com.hive.format-watch.plist`)

Add 03:00 daily run that scans all three roots (hive/tool, hexa-lang/self,
anima/tool) with `--json` and appends to
`state/format_witness/<YYYY-MM-DD>_lint_tools_full_scan.jsonl`. Drift detection:
diff today's violation count against rolling 7-day baseline — alert if a new
`high` or `offset_mismatch` appears.

### D. autonomous-loop integration

`autonomous_loop_self_improvement_lint.hexa` already crawls `state/format_witness/*`.
Add the new sentinel patterns to its parser so cycle metrics (e.g.
`heredoc_high_count_trend`) feed the next cycle's design strategy proposals.

## Severity Calibration (raw 91 honest C3)

- The current cross-repo scan finds **zero** `high`-class heredoc violations
  and **zero** offset mismatches. This is unusual — confirms that the manually-
  fixed Bug 1 (subagent_dispatch) and Bug 3 (A15) were the only canonical
  instances. The lint suite is therefore primarily a **regression preventer**,
  not a backlog burndown tool.
- `prefix_aware_find_lint` detected zero warnings cross-repo. Either the heuristic
  is too narrow (single-char, in-loop, no-guard) or the codebase already
  uniformly uses 2-arg or substring-guard idioms. Recommended: log false-negative
  candidates over 30 days and recalibrate.
- The 12 surviving `med` heredoc violations are migration candidates, not bugs.
  None measured exceed Darwin ARG_MAX (1,044,361 bytes per Bug 1 verdict).
  Migration to native `write_file()` is opportunistic.

## Roll-out Sequence

1. Land selftest-clean tools to `hive/tool/` (DONE, this PR).
2. Wire pre-commit hook (Phase A) — soft-warn for one week, observe false-positive
   rate. Promote to error after.
3. Wire raw 9 dispatch (Phase B) — concurrent with Phase A.
4. Wire nightly cron (Phase C) — week 2.
5. Autonomous-loop sentinel parsing (Phase D) — week 3, after baseline trend
   data accumulates.

## Witness Anchors

- `/Users/ghost/core/anima/state/format_witness/2026-04-28_lint_tools_full_scan.jsonl`
- `/Users/ghost/core/anima/state/format_witness/2026-04-28_bug1_a16_verdicts.jsonl` (heredoc lint upstream)
- main.hexa cache_schema_version="v6" comment-block (aot_cache lint anchor)
