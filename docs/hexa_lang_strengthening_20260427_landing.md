# hexa-lang stdlib strengthening — ω-saturation cycle 2026-04-27 LANDING

**ts_utc**: 2026-04-27T17:31:15Z
**user directive verbatim Korean**: `hexa-lang 개선가능 kick`
**raw level allowed**: yes (raw 102 explicit user approval)
**paired roadmap id (proposed)**: `P-hexa-stdlib-omega-20260427`
**witness JSON**: `/Users/ghost/core/anima/state/design_strategy_trawl/2026-04-27_hexa_lang_strengthening_omega_cycle.json`

## TL;DR

Tier-A landed. Two canonical stdlib modules added to hexa-lang
(`self/stdlib/shell_escape.hexa`, `self/stdlib/flags.hexa`) plus
a demo file proving end-to-end import works. 19 selftest
assertions all PASS. 36 + 8 = 44 inline-duplicated helpers
across hive/anima/nexus tools become eligible for migration to
`use "self/stdlib/<name>"` form. Tier-B (5 items) and Tier-C
(3 items) registered as doc-only proposals pending main-thread
decision.

## Evidence — limits encountered THIS session

1. **`shell_escape` stdlib missing** — 36 hive tools each
   reimplemented `_shell_escape` with bytewise-identical code.
   `escalation_window_recovery.hexa` authoring failed with
   `Runtime error: undefined function: shell_escape`.
2. **`a[0..2]` slice syntax unsupported** — `a.substring(0, 2)`
   only canonical form. Frequent stumble in ai-native scripts.
3. **`argv()` runtime variation** — Mac stage0 `[bin, bin, ...]` /
   hetzner ssh `[hexa, run, script.hexa, ...]` / docker
   `[hexa, run, script, ...]`. 8+ tools each hand-rolled their
   own normalizer.
4. **module import** — works (use directive supported), but
   stdlib modules with their own `--selftest` handler collide
   with the host script's `--selftest` because top-level
   statements are concatenated by the loader.
5. **hexa-runner docker image lacks node** — kick rc=76
   `container-no-node` observed 7+ times this session.
6. **nexus run.hexa kick path** — `ai_err_exit undefined`
   Runtime error 3+ times.
7. **`/Users/ghost/core/hexa-lang/hexa run` direct path** — Mac
   jetsam SIGKILL; 124 GB hetzner OOM (raw 100 line 52). The
   `~/.hx/bin/hexa` resolver wrapper hides this only by routing
   away.
8. **hexa-strict main() auto-invoke** — `analyze.hexa` OOM
   mid-T10 + commit `05af4a3f` neurofeedback / rp_adaptive
   evidence: trailing `main()` call double-invokes.
9. **legacy `print` / `str` builtins** — neurofeedback /
   rp_adaptive_response still use these. Need migration to
   `println` / `to_string`.
10. **`.hexa-cache` invalidation hook missing** — manual
    `rm -rf .hexa-cache` required multiple times this session.

## Tier-A — implemented autonomous (raw 102 OK)

### Files added

| Path | Lines | Pub fns |
|---|---|---|
| `self/stdlib/shell_escape.hexa` | 148 | `shell_escape` |
| `self/stdlib/flags.hexa` | 240 | `flags`, `flags_or_default`, `flag_present`, `flag_value`, `flag_value_eq` |
| `self/stdlib/test_stdlib_strengthening_demo.hexa` | 54 | (demo + selftest) |

### Selftest results (raw 65 idempotent + raw 68 byte-eq)

```
$ /Users/ghost/.hx/bin/hexa_real run self/stdlib/shell_escape.hexa --selftest
shell_escape selftest: 9/9 PASS

$ /Users/ghost/.hx/bin/hexa_real run self/stdlib/flags.hexa --selftest
flags selftest: 8/8 PASS

$ /Users/ghost/.hx/bin/hexa_real run self/stdlib/test_stdlib_strengthening_demo.hexa --selftest
demo: imported shell_escape works (2/2 PASS)
demo: flags()/flag_present()/flag_value()/flag_value_eq() exported and callable
```

19 total assertions PASS. T9 of `shell_escape` selftest asserts
**byte equivalence** with the legacy 36-tool inline form via
`_se_legacy_reference()` embedded in the same file.

### Deduplication potential when callers migrate

- 36 `_shell_escape` inline copies → eliminate ~12 LoC each = ~432 LoC.
- 8 `_flags_only_argv` inline copies → eliminate ~22 LoC each = ~176 LoC.
- Total recoverable: ~608 LoC across hive + anima + nexus.

## 5 falsifiers preregistered (raw 71)

| id | claim | falsifier | result |
|---|---|---|---|
| F1 | `shell_escape` byte-identical to legacy form | T9 string-eq | PASS |
| F2 | `flags()` strips Mac stage0 `[bin, bin, ...]` | T6 of flags selftest | PASS |
| F3 | `flags()` strips Linux `[hexa, run, script.hexa, ...]` | T7 of flags selftest | PASS |
| F4 | `use "self/stdlib/<name>"` brings pub fns into caller scope | demo --selftest | PASS |
| F5 | stdlib selftest does not double-fire when host has --selftest | demo --selftest output | PASS_AFTER_FIX (collision found, mitigation landed) |

## 5 orthogonal axes (raw 48; pairwise corr < 0.7)

scope (stdlib_only) · risk (tier_A_zero_breakage) · evidence_count
(36+8 callsites) · selftest_coverage (19 assertions) · cognitive
load (2 use lines vs 30 inline LoC).

## raw 72 tri-axis ordinal-theoretic ceiling

- **FORMAL**: hexa parser strength — module concat preserves
  top-level order; selftest path-end gate avoids double-fire.
- **PHYSICAL**: interpreter resource — `shell_escape` is
  `O(len(s))`, `flags()` is `O(len(args()))`, both bounded.
  No alloc pathology.
- **COMPUTATIONAL**: stdlib decidability — every fn terminates
  by bounded counter. No recursion. Halting trivial.

## raw 106 multi-realizability (genus naming + ≥3 channels + ≥2 frameworks + counter-example)

- **Genus**: `stdlib_canonicalization_under_concatenative_module_loader`.
- **Channels (3)**: (1) stdlib expand — pub fns landed; (2) module
  import validated — demo proves callable end-to-end; (3) selftest
  gate pattern — path-end-check is the new canonical pattern.
- **Frameworks (2)**: PL theory (namespace + import resolution
  semantics) + systems engineering (stdout routing, cache
  invalidation, resolver fallback).
- **Counter-example**: stdlib modules requiring side-effects on
  EVERY import (e.g. global initializer) MUST NOT use the
  path-end gate — it would suppress required init. The pattern
  is correct only for selftests.

## Tier-B (5 items) — proposal-only, pending main-thread review

1. `Tb1_module_loader_top_level_collision_diagnostic` — first-class
   `__main__` semantics for stdlib modules (4-6h).
2. `Tb2_stdlib_selftest_naming_convention` — codify
   `--selftest-<module>` rule (1-2h).
3. `Tb3_hexa_runner_docker_image_with_node` — fix kick rc=76 (4-6h).
4. `Tb4_nexus_run_hexa_ai_err_exit_fix` — single-line import (1-2h).
5. `Tb5_hexa_strict_double_invoke_detector` — main() collision lint
   (4-6h).

## Tier-C (3 items) — proposal-only, larger redesigns

1. `Tc1_interpreter_pathological_allocation_cap` — arena allocator
   + per-script memory ceiling + bounded stack (16-24h). raw 100
   line 52 evidence is fundamental.
2. `Tc2_hexa_cache_invalidation_correctness` — module-import
   dependency graph in cache key (8-12h).
3. `Tc3_stage1_promotion_build_hexa_v2` — bytecode VM audit then
   promotion (16-24h+).

## raw 91 honest C3 disclosure

- 8th nexus kick FAIL (rc=3 / rc=0 ai_err_exit / rc=76 container-no-node).
- raw 100 line 2391 falsifier TRIGGERED 100% this session.
- raw 100 line 51 fallback used (Claude Code Agent direct invocation).
- raw 105 ai-cli-kick-autonomous-invocation alignment maintained.
- Resolver-routed `/Users/ghost/.hx/bin/hexa run` for the new
  stdlib files **suppresses stdout** on Mac stage0 → docker
  hexa-runner path. Workaround: invoke `hexa_real` directly for
  the selftests above. Listed as a real gap (resolver stdout
  loss); not blocking Tier-A correctness because direct-binary
  invocation produces full PASS evidence.
- Selftest collision (F5) was a real bug encountered during this
  cycle. The mitigation landed; the underlying issue is enrolled
  as Tb1/Tb2.

## Main-thread decisions required

- Commit Tier-A artifacts to hexa-lang main? (no breakage; pure
  additions).
- Schedule mechanical migration PRs (36 `_shell_escape` + 8
  `_flags_only_argv` callsites)?
- Register `P-hexa-stdlib-omega-20260427` in roadmap.
- Pick which Tier-B / Tier-C items to schedule.
