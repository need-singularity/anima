<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/inference_optimization_smoke.hexa -->
<!-- entry_count: 11 -->

# `tool/inference_optimization_smoke.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 11

## Table of contents

- `fn knob_ids`
- `fn _str`
- `fn fexists`
- `fn read_safe`
- `fn slice_knob_block`
- `fn has_key`
- `fn key_is_true`
- `fn check_knob`
- `fn bool_s`
- `fn emit_result`
- `fn main`

## Entries

### `fn knob_ids() -> list`

> expected knob ids (mirrors the keys in config/inference_serve_optimization.json :: knobs)

### `fn _str(x) -> string`

_(no docstring)_

### `fn fexists(p: string) -> bool`

> stage0 hexa has no exec/env — use relative paths; callers must run from repo root.

### `fn read_safe(path: string) -> string`

_(no docstring)_

### `fn slice_knob_block(blob: string, knob_id: string) -> string`

> Locate the start of the knob block "knob_id" : { ... } and return its
> substring (between the matching braces). Returns "" if knob not declared.

### `fn has_key(block: string, key: string) -> bool`

> Probe whether a "key" appears in the knob block (any value type).

### `fn key_is_true(block: string, key: string) -> bool`

> Probe whether a "key" maps to "true" (literal). Bool only.

### `fn check_knob(blob: string, knob_id: string) -> list`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn emit_result(out_path: string, cfg_path: string, cfg_present: bool, rows: list, applied_count: int, pending_count: int, blocked_count: int, total: int, all_ok: bool)`

_(no docstring)_

### `fn main()`

_(no docstring)_

