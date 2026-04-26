# anima/.raw-exemptions/

Per-rule grandfather registry for `raw#0` P1b (mirrors the hexa-lang
`.raw-exemptions/` schema). Each file exempts specific paths from a single
rule, with a **mandatory** expiry date and a `jurisdiction-out` classification
(raw#100 — the path is structurally outside the rule's enforcement scope:
`research`, `bench`, `experimental`, or `deploy`).

## Directory layout

```
.raw-exemptions/
  raw_6.list   # F4 generic-dir exemptions  (path-prefix allowlist)
  raw_7.list   # F1/F2/F3/F5/F6 filename + tree-shape exemptions
  raw_8.list   # stage/phase token retire (raw8 historical fixtures)
  README.md    # this file
```

## File format

One entry per line. Comments (`#`) and blank lines are allowed.

```
<file_path> | <line_range> | <reason> | <expiry YYYY-MM-DD>
```

| Field        | Notes                                                            |
|--------------|------------------------------------------------------------------|
| `file_path`  | repo-relative path or **narrow** glob (no whole-dir wildcards)   |
| `line_range` | single `42`, range `10-20`, or `*` for whole-file                |
| `reason`     | causal class + jurisdiction-out tag + owner — visible in lint    |
| `expiry`     | `YYYY-MM-DD` UTC — **required**, indefinite grandfather forbidden|

**reason convention** for jurisdiction-out exemptions:

```
<causal>: <specifics> [jurisdiction-out: <research|bench|experimental|deploy>] — owner: <repo>
```

## Glob discipline

- Forbidden: full-dir wildcards (`bench/**`, `scripts/deploy/*`).
- Allowed: explicit per-file entries OR narrow patterns that stop at the
  systematic-naming boundary (e.g. `bench/bench_*.hexa` is acceptable
  because the entire directory is a single jurisdiction-out class with
  a single naming convention; `scripts/**` is not).

## Why `jurisdiction-out` (raw#100)

raw#7 F1-F6 are SOURCE-CODE naming/tree rules. `bench/`, `scripts/deploy/`,
and version-iterative research scripts (`*_v\d+`) are NOT general source —
they are **historical artifacts** (a benchmark run, a deploy snapshot, a
research iteration). Renaming them retroactively destroys traceability
without paying off any quality lever.

`jurisdiction-out` says: this path is structurally outside F1-F6's scope.
The exemption is the contract that documents the boundary. Expiry forces
12-month re-justification so the boundary doesn't silently drift.

## CLI (cross-repo, hexa-lang owns the binary)

```
hexa /Users/ghost/core/hexa-lang/tool/raw_exemptions.hexa list
hexa /Users/ghost/core/hexa-lang/tool/raw_exemptions.hexa list 7
hexa /Users/ghost/core/hexa-lang/tool/raw_exemptions.hexa check
```

Note: as of 2026-04-26, `tool/ai_native_scan.hexa` consults `raw_6.list`
only (F4 path-prefix allowlist). `raw_7.list` and `raw_8.list` are
contractual records — the scanner currently emits residual-highlights
for those entries. Follow-up task (anima local lint cron, see
`config/launchd/com.anima.lint_cron.plist`) tracks the residual delta
in `state/lint_cron_history.jsonl`.
