# hexa-lang module-loader top-level collision diagnostic — Tier-B 1 LANDING

**ts_utc**: 2026-04-27T17:58:00Z
**user directive verbatim**: `keep going kick`
**raw level allowed**: yes (raw 102 + prior cycle "raw level 허용")
**tier**: B (autonomous OK per raw 102 + prior cycle directive)
**paired roadmap id (proposed)**: `P-hexa-N-module-loader-collision-lint-20260427`
**witness JSON**: `/Users/ghost/core/anima/state/design_strategy_trawl/2026-04-27_hexa_lang_module_loader_collision_omega_cycle.json`

## TL;DR

Tier-B 1 landed. New lint tool `hexa-lang/tool/module_loader_collision_lint.hexa`
formalizes the path-end-check workaround pattern introduced by the Tier-A cycle
(commit `dc8b2940`) and detects four classes of stdlib module hygiene
violation. Selftest 4/4 fixtures PASS. Live scan against 22 stdlib modules
finds 1 real violation + 12 advisories, 0 false positives (after comment
stripping). Lint does NOT root-cause the nexus `ai_err_exit` Runtime error
9-attempt FAIL — that is a different bug (cross-host binary staleness +
env propagation, see `nexus/.raw-audit` BUG#3 + 2026-04-28 follow-up).

## Module-loader concat semantics — exact mechanism

`/Users/ghost/core/hexa-lang/self/module_loader.hexa` (566 lines) is an
iterative-DFS preprocessor. For each `use "self/stdlib/<name>"` directive
it resolves via 3-way (caller-relative → stdlib → project-root) and emits
the imported module body in post-DFS order BEFORE the host script body.

`ml_strip_and_clean` (lines 335-384) rewrites the concatenated source:

```
\nuse "        →  \n// [ml-stripped] use "
\nimport "     →  \n// [ml-stripped] import "
\npub fn       →  \nfn
\npub struct   →  \nstruct
...
```

**No top-level sandboxing.** Every non-fn / non-struct / non-enum /
non-let-const line at depth=0 in a module body emits VERBATIM and EXECUTES
at program start in source-order. This is the collision substrate.

### Collision in concrete form

Pre-Tier-A pattern (now banned by lint):

```hexa
// stdlib/foo.hexa (BAD):
pub fn helper() -> int { return 42 }
let _args = args()
if _args.contains("--selftest") {
    helper_selftest()
    exit(0)
}

// host.hexa:
use "stdlib/foo"
let _args = args()
if _args.contains("--selftest") {
    host_selftest()  // UNREACHABLE — foo's exit fired first
    exit(0)
}
```

After module_loader concat, the program runs:
1. `helper` fn definition
2. `let _args = args()` (foo's)
3. `if --selftest { exit(0) }` ← FIRES if user passed --selftest
4. `let _args = args()` (host's, never reached)
5. host's --selftest gate (never reached)

### The Tier-A workaround pattern (canonical)

`self/stdlib/shell_escape.hexa` lines 131-148:

```hexa
let _se_args = args()
let mut _se_selftest_flag = false
let mut _se_i = 0
while _se_i < len(_se_args) {
    if _se_args[_se_i] == "--selftest-shell-escape" { _se_selftest_flag = true }
    if _se_args[_se_i] == "--selftest" {
        // Only run when invoked DIRECTLY (script path ends with shell_escape.hexa).
        let mut _se_j = 0
        while _se_j < len(_se_args) {
            if _se_args[_se_j].ends_with("/stdlib/shell_escape.hexa") {
                _se_selftest_flag = true
            }
            _se_j = _se_j + 1
        }
    }
    _se_i = _se_i + 1
}
if _se_selftest_flag { exit(_se_selftest()) }
```

The path-end-check (`ends_with("/stdlib/shell_escape.hexa")`) ensures the
gate only fires when the module IS itself the script being run.

## Lint tool — `hexa-lang/tool/module_loader_collision_lint.hexa`

| Check | Severity | Description |
|---|---|---|
| C1 | Pre-condition | top-level `args()` / `exit(` / `--selftest` literal present in module body? |
| C2 | FAIL (violation) | when C1 trips, `.ends_with("/stdlib/<name>.hexa")` MUST appear in source |
| C3 | WARN (advisory) | module SHOULD provide module-specific `--selftest-<stem>` flag |
| C4 | WARN (advisory) | module SHOULD declare ≥1 `pub fn` (else import-useless) |

### Subcommands

| Invocation | Action |
|---|---|
| `hexa run tool/module_loader_collision_lint.hexa` | scan all stdlib modules; exit 1 on any C1+C2 violation |
| `... --selftest` | synthetic-fixture selftest (4 fixtures) |
| `... --list` | list stdlib modules examined |
| `... --file <path>` | scan single file |
| `... --caller-detect` | find callers under HEXA_LANG that import top-level-active stdlib modules |

### Comment stripping (false-positive fix)

First-iteration scan reported 3 violations: `law_io.hexa`, `module_gate.hexa`,
`test_stdlib_strengthening_demo.hexa`. The first two were FALSE POSITIVES —
docstrings contained the literal `// reason + exit(1)` which my brace-depth
scan saw at depth=0. Added `_strip_line_comment` to scrub `//` line comments
before the brace-counter runs. Reduced to 1 real violation.

## Selftest results

```
$ HEXA_LANG=/Users/ghost/core/hexa-lang \
    /Users/ghost/.hx/packages/hexa/hexa.real run \
    tool/module_loader_collision_lint.hexa --selftest
[mlc-lint selftest] 4/4 fixtures PASS (A clean / B bad C1+C2 / C good guarded / D C4 advisory)
```

| Fixture | Shape | Expected | Actual |
|---|---|---|---|
| A clean | `pub fn` only, no top-level | 0v / 0a | 0v / 0a PASS |
| B bad | top-level args/exit/--selftest, no guard | 1v (C1+C2) | 1v PASS |
| C good | top-level args/exit/--selftest WITH guard | 0v | 0v PASS |
| D empty | `fn` only (no `pub`) | 0v / ≥1a | 0v / 1a PASS |

**Note**: selftest verification uses `hexa.real` direct because the `~/.hx/bin/hexa`
resolver routes Mac → docker on this cwd, and the docker route swallows
stdout/stderr (Task #22 secondary finding, independently re-confirmed this
cycle). Production lint usage routes through the resolver normally; only the
print-driven selftest needs the direct path. Constraint compliance: the
resolver wrapper IS the production path; hexa.real is verification-only.

## Live stdlib scan — 22 modules

```
[mlc-lint] scanned 22 modules: 1 violation(s), 12 advisor(ies)
[mlc-lint] FAIL test_stdlib_strengthening_demo.hexa: C1+C2
[mlc-lint] WARN evolve / fraction / io / nan_sentinel / random / set_emu /
                sieve / simd / string_extras / string_utils / tensor_ops /
                test_stdlib_strengthening_demo: C4 (no pub fn)
```

### Violation detail

`self/stdlib/test_stdlib_strengthening_demo.hexa` — Task #22 demo file.
Top-level `--selftest` gate without path-end-check guard. Severity LOW
(demo, not imported by production tools). Remediation: relocate to
`self/stdlib/tests/` OR add the canonical guard pattern.

### Advisory summary (C4)

12 stdlib modules declare functions with bare `fn` instead of `pub fn`.
`ml_strip_and_clean`'s `\npub fn ` → `\nfn ` rewrite means non-pub fns
remain cross-module-callable in the concatenated output, but the convention
is broken — caller cannot read the export surface. Suggested fix: stdlib
audit pass to add `pub` to every export-intended fn.

## nexus `ai_err_exit` 9-attempt FAIL diagnosis

**Question**: did the lint root-cause this Runtime error?
**Answer**: NO — different root cause.

Evidence trail:

1. `/Users/ghost/core/nexus/cli/run.hexa` — 0 occurrences of `use "` or
   `ai_err_exit` (verified by `grep -c`). The string does not appear in
   the nexus run.hexa entry point.
2. `/Users/ghost/core/hexa-lang/self/stdlib/ai_err.hexa` — 0 top-level
   statements. Cannot collide.
3. `/Users/ghost/core/hive/tool/subagent_dispatch.hexa` line 63 imports
   `use "self/stdlib/ai_err"` correctly. 16+ `ai_err_exit` call-sites
   work on Mac.
4. `nexus/.raw-audit` BUG#3 (2026-04-27 ts=07:29:10Z) already root-caused:
   cross-host stdlib resolution. Mac sets `HEXA_LANG` globally; remote ssh
   shells inherit minimal env → use directive cannot resolve self/stdlib
   → Runtime error.
5. `nexus/.raw-audit` follow-up (2026-04-28 ts=01:05:01Z): hetzner
   `hexa_real` has older binary missing `ai_err_exit` stdlib function.
   Sub-V parity check verifies SHA but does not auto-rebuild/deploy.

**Actual root cause**: stale hetzner `hexa_real` binary + hexa-lang stdlib
rsync gap on ubu1. Lint detects a DIFFERENT class of bug (top-level
collision) and is orthogonal. Both are real; both block kick infra. This
cycle addresses the lint-detectable class only — kick rebuild + deploy is
separate work (Sub-BI follow-up, deferred).

## Falsifiers preregistered (raw 71)

| # | Claim | Test | Predicted | Verdict |
|---|---|---|---|---|
| F1 | lint catches missing guard | Fixture B selftest | 1 violation | PASS |
| F2 | lint passes guarded module | Fixture C selftest | 0 violations | PASS |
| F3 | lint catches Task #22 demo bug | live scan | flag demo file | PASS |
| F4 | lint passes import-pure ai_err | `--file ai_err.hexa` | 0 violations | PASS |
| F5 | lint --selftest is import-safe | host imports lint tool via use | host --selftest reaches host handler | DEFERRED (lint is a tool, not stdlib; no use "tool/..." pattern exists) |

## Compliance summary

| raw | rule | verdict |
|---|---|---|
| 9 | hexa-only file extensions | PASS — .hexa + .md + .json |
| 12 | silent-error-ban | PASS — every fail path emits cause/remedy/ref |
| 65 | idempotent | PASS — lint reads files only |
| 71 | falsifier preregistered | PASS — 5 falsifiers, 4 PASS / 1 DEFERRED |
| 91 | honesty | PASS — explicitly disclosed lint does NOT unblock kick |
| 101 | minimal | PASS — single tool file; existing stdlib unchanged |
| 102 | strengthen-existing | PASS — strengthens module_loader contract via lint |
| 105 | ai-cli-kick-autonomous-invocation | via parent cycle (Tier-B autonomous) |
| 100 line 51 | kick fallback | active — 9/9 FAIL recorded |
| 100 line 52 | resolver-only | PASS — production usage via resolver; selftest verification via hexa.real (Task #22 stdout suppression workaround) |

## Carry-forward findings (raw 87 paired-roadmap)

- **F-CF1**: 12 stdlib modules need `pub fn` migration. Next stdlib pass.
- **F-CF2**: resolver-routed `hexa run` (Mac→docker) silently suppresses
  stdout/stderr. Re-confirmed this cycle. Tier-B 2 candidate.
- **F-CF3**: nexus `ai_err_exit` on hetzner is stale binary + env
  propagation (BUG#3). Sub-BI rebuild + scp deploy required.
- **F-CF4**: docstring-mention false-positives may affect other lints.
  Audit `tool/*_lint.hexa` for similar `// reason + exit(...)` patterns.

## Files modified / created

| Path | Lines | Kind |
|---|---|---|
| `hexa-lang/tool/module_loader_collision_lint.hexa` | 348 | NEW lint tool |
| `anima/state/design_strategy_trawl/2026-04-27_hexa_lang_module_loader_collision_omega_cycle.json` | 116 | NEW witness |
| `anima/docs/hexa_lang_module_loader_collision_20260427_landing.md` | (this file) | NEW landing doc |

No existing files modified. Pure additive cycle.

## Main-thread decision pending

Commit + push the three artifacts (hexa-lang lint + anima witness + anima
landing doc) OR defer until a Tier-B 2+ batch lands. Recommendation: commit
NOW because the lint is selftest-verified, finds 1 real bug (the demo file)
and 12 valid advisories, and unblocks future stdlib audits. Push optional.
