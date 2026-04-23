<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/auto_evolution_loop.hexa -->
<!-- entry_count: 31 -->

# `tool/auto_evolution_loop.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 31

## Table of contents

- `fn _shq`
- `fn _exec`
- `fn _exec_out`
- `fn _exec_status`
- `fn _file_exists`
- `fn _dir_exists`
- `fn _mkdir_p`
- `fn _ts_iso`
- `fn _cycle_id`
- `fn _ls_count`
- `fn _argv`
- `fn _flag`
- `fn _json_esc`
- `fn _log_step`
- `fn _tool_path`
- `fn _tool_exists`
- `fn _run_subtool`
- `fn _counts_inventory`
- `fn _empty_counts`
- `fn _refine_one_pending`
- `fn _step_refinement`
- `fn _step_metrics`
- `fn _step_notify`
- `fn _selftest_subtool`
- `fn _selftest_inline_refinement`
- `fn _selftest_inline_metrics`
- `fn _selftest_inline_notify`
- `fn _run_selftest`
- `fn _run_cycle`
- `fn _print_help`
- `fn main`

## Entries

### `fn _shq(s: string) -> string`

_(no docstring)_

### `fn _exec(cmd: string) -> array`

_(no docstring)_

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _exec_status(cmd: string) -> int`

_(no docstring)_

### `fn _file_exists(p: string) -> bool`

_(no docstring)_

### `fn _dir_exists(p: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(p: string)`

_(no docstring)_

### `fn _ts_iso() -> string`

_(no docstring)_

### `fn _cycle_id() -> string`

_(no docstring)_

### `fn _ls_count(dir: string, pat: string) -> int`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _json_esc(s: string) -> string`

_(no docstring)_

### `fn _log_step(cycle_id: string, step: int, name: string, status: string,`

_(no docstring)_

### `fn _tool_path(rel: string) -> string`

_(no docstring)_

### `fn _tool_exists(rel: string) -> bool`

_(no docstring)_

### `fn _run_subtool(rel: string, extra: string, apply: bool) -> array`

> Run a hexa sub-tool. Returns [exit_code, status_string, msg_summary].
> apply=false → does NOT execute (returns status="dry").
> apply=true  → invokes via `hexa run <path> <extra_args>`.
> missing tool → status="notool", exit=0.

### `fn _counts_inventory() -> string`

_(no docstring)_

### `fn _empty_counts() -> string`

_(no docstring)_

### `fn _refine_one_pending(path: string, cycle_id: string, apply: bool) -> bool`

_(no docstring)_

### `fn _step_refinement(cycle_id: string, apply: bool) -> array`

_(no docstring)_

### `fn _step_metrics(apply: bool) -> array`

_(no docstring)_

### `fn _step_notify(cycle_id: string, summary: string, apply: bool) -> array`

_(no docstring)_

### `fn _selftest_subtool(rel: string) -> array`

_(no docstring)_

### `fn _selftest_inline_refinement() -> int`

_(no docstring)_

### `fn _selftest_inline_metrics() -> int`

_(no docstring)_

### `fn _selftest_inline_notify() -> int`

_(no docstring)_

### `fn _run_selftest() -> int`

_(no docstring)_

### `fn _run_cycle(apply: bool) -> int`

_(no docstring)_

### `fn _print_help()`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

