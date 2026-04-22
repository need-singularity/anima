<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/coverage_gate_ci.hexa -->
<!-- entry_count: 12 -->

# `tool/coverage_gate_ci.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 12

## Table of contents

- `fn _shq`
- `fn _file_exists`
- `fn _ts_iso`
- `fn _json_esc`
- `fn _short_path`
- `fn _resolve_baseline`
- `fn _added_since`
- `fn _probe_selftest`
- `fn _run_audit`
- `fn _arr_strings_to_json`
- `fn _write_out`
- `fn _arg_present`

## Entries

### `fn _shq(s: string) -> string`

_(no docstring)_

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _json_esc(s: string) -> string`

_(no docstring)_

### `fn _short_path(p: string) -> string`

_(no docstring)_

### `fn _resolve_baseline(av: array) -> string`

> Resolve baseline revision from argv / env / default.

### `fn _added_since(baseline: string) -> array`

> Return list of short-paths for tool/*.hexa added since `baseline`.

### `fn _probe_selftest(short: string) -> string`

> Check whether a tool file has a wired-up --selftest.
> Returns: "ok" | "no_selftest_flag" | "no_exit"

### `fn _run_audit(baseline: string) -> array`

_(no docstring)_

### `fn _arr_strings_to_json(a: array) -> string`

_(no docstring)_

### `fn _write_out(baseline: string, added: array, missing: array, pass: bool)`

_(no docstring)_

### `fn _arg_present(av: array, k: string) -> bool`

_(no docstring)_

