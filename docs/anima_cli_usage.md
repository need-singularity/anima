# anima CLI — usage & cheatsheet

Single entry point for every anima operation. Compute-agnostic (no H100
lock-in in the CLI surface — the `compute` namespace wraps the legacy
`h100_*` tools so future accelerator classes plug in without renaming).

Top-level dispatcher: `bin/anima` (bash, ~165 lines).
Topic modules: `tool/anima_cli/<topic>.hexa` (thin orchestrators).

## Layout

```
bin/anima                         bash dispatcher (top-level)
tool/anima_cli/_common.hexa       shared helpers (vendored into topics)
tool/anima_cli/compute.hexa       pod lifecycle (compute-agnostic)
tool/anima_cli/weight.hexa        weight precache
tool/anima_cli/proposal.hexa      proposal stack
tool/anima_cli/cert.hexa          breakthrough cert chain
tool/anima_cli/roadmap.hexa       roadmap engine
tool/anima_cli/serve.hexa         serving layer
tool/anima_cli/paradigm.hexa      three-paradigm unified dashboard
```

## Global invocation

| Command            | Effect                                              |
| ------------------ | --------------------------------------------------- |
| `anima`            | global dashboard (alias of `anima status`, 4 lines) |
| `anima --version`  | `anima 0.1.0`                                       |
| `anima --help`     | top-level help (topic list + examples)              |
| `anima <topic>`    | topic-level help (list subcommands)                 |
| `anima status`     | global dashboard (4 summary lines)                  |
| `HEXA_REPRODUCIBLE=1 anima ...` | timestamps → REDACTED (deterministic) |

### Sample `anima status`

```
anima  (2026-04-22T15:54:06Z)
compute   : stage1=READY  stage2=NOT_READY  balance=$135.842
weight    : status=n/a  paths=?
proposal  : pending=71  approved=11  rejected=4  archived=0
roadmap   : done=0/72  blocked=0
```

## Topics & subcommands

### `anima compute` — pod lifecycle (compute-agnostic)

| Subcmd              | Action                                            |
| ------------------- | ------------------------------------------------- |
| `status`            | pods + stage verdicts + burn + balance (1-page)   |
| `start <stage>`     | read kickoff_command from launch manifest (echo)  |
| `stop <pod\|all>`   | `runpodctl pod delete`                            |
| `watch`             | idle/credit/drift poll (wraps `h100_auto_kill`)   |
| `cost`              | session + cumulative USD spend                    |
| `recover <pod>`     | wraps `h100_pod_resume.bash`                      |
| `ingest`            | wraps `h100_post_launch_ingest.hexa`              |
| `preflight`         | stage-2 dry-run (6-step pre-flight; verdict)      |

```
$ anima compute status
anima compute status  (2026-04-22T15:53:11Z)
─────────────────────────────────────────────
pods      : 0 running
stage1    : READY
stage2    : NOT_READY
stage3    : MISSING_PREREQ
last_run  : ABORTED — pod bootstrap blocker (...)
balance   : $135.842 / thr $1000  alert=false
```

### `anima weight` — weight precache

| Subcmd             | Action                                             |
| ------------------ | -------------------------------------------------- |
| `status`           | summarize `state/h100_weight_precache_completion.json` |
| `apply [--path P]` | wraps `h100_weight_precache.bash --apply`          |
| `strategy`         | `jq .` of `config/h100_weight_precache_strategy.json` |

### `anima proposal` — proposal stack

| Subcmd                                  | Wraps                             |
| --------------------------------------- | --------------------------------- |
| `review [--top N] [--id X] [--kind K]`  | `proposal_review.hexa`            |
| `approve <id> [--reason ...]`           | `proposal_approve.hexa`           |
| `reject <id> [--reason ...]`            | `proposal_reject.hexa`            |
| `implement <id>`                        | `proposal_implement.hexa`         |
| `archive <id>`                          | `proposal_archive.hexa`           |
| `dashboard`                             | `proposal_dashboard.hexa`         |
| `cluster`                               | detect → consolidate              |
| `cycle`                                 | auto-threshold → conflict scan    |

### `anima cert` — breakthrough cert chain

| Subcmd                    | Wraps                                |
| ------------------------- | ------------------------------------ |
| `verify`                  | `cert_gate.hexa`                     |
| `verify --incremental`    | `cert_incremental_verify.hexa`       |
| `graph`                   | `cert_graph_gen.hexa`                |
| `dag`                     | `cert_dag_generator.hexa`            |

### `anima roadmap` — roadmap engine

| Subcmd                       | Action                                |
| ---------------------------- | ------------------------------------- |
| `status [repo]`              | total / done / active / blocked counts |
| `entries [--track T|--phase P]` | `.id \t .status \t .title` rows    |
| `blockers`                   | BLOCKED entries                       |
| `roi`                        | entries with `.roi_score`             |

### `anima serve` — serving layer

| Subcmd            | Action                                        |
| ----------------- | --------------------------------------------- |
| `persona [--dry]` | wraps `serve_alm_persona.hexa` (CP1 dest1)    |
| `api`             | shows `docs/api/openapi.yaml` + README link   |

### `anima paradigm` — three-paradigm unified dashboard

| Subcmd             | Action                                            |
| ------------------ | ------------------------------------------------- |
| `status`           | full multi-section dashboard (compute/proposal/cert/roadmap) |
| `status --short`   | 4-line summary (alias used by `anima status`)     |

## Selftest

Every topic module accepts `--selftest` and exits 0/1 deterministically:

```
$ for m in compute weight proposal cert roadmap serve paradigm; do
    hexa run tool/anima_cli/${m}.hexa --selftest
  done
PASS anima_cli/compute selftest
PASS anima_cli/weight selftest
PASS anima_cli/proposal selftest
PASS anima_cli/cert selftest
PASS anima_cli/roadmap selftest
PASS anima_cli/serve selftest
PASS anima_cli/paradigm selftest
```

## Design constraints

- **raw#9**  hexa-only for logic; `bin/anima` is pure bash glue (no `.py`).
- **raw#10** deterministic; `HEXA_REPRODUCIBLE=1` redacts timestamps.
- **raw#11** snake_case everywhere.
- **raw#15** no hardcoded paths; resolved via `ANIMA` env / `git rev-parse`.
- **V8 SAFE_COMMIT** additive — no existing `tool/*` file was modified.
- **Idempotent** — every subcommand is safe to re-run.
- **Compute-agnostic naming** — CLI surface has no `h100` tokens; the
  legacy tool filenames are retained to avoid touching working code.

## Path resolution

`ANIMA_ROOT` is resolved in this order:
1. `$ANIMA` environment variable (if set and directory exists)
2. Parent of `bin/anima` (if it contains `tool/anima_cli`)
3. `git rev-parse --show-toplevel`
4. Fallback: `$HOME/core/anima`

`HEXA_BIN` is resolved in this order:
1. `$HEXA_BIN` env var (if executable)
2. `/Users/ghost/.hx/bin/hexa`
3. `command -v hexa`

## Exit codes

| Code | Meaning                                         |
| ---- | ----------------------------------------------- |
| 0    | success / PASS / empty-graceful                 |
| 1    | subtool FAIL or missing required file           |
| 2    | unknown topic / subcommand / malformed input    |
