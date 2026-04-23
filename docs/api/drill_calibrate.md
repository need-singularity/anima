<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/drill_calibrate.hexa -->
<!-- entry_count: 13 -->

# `tool/drill_calibrate.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** tool/drill_calibrate.hexa -- drill criteria dynamic calibration

**Public/Internal entries:** 13

## Table of contents

- `fn is_loosening`
- `fn append_jsonl`
- `fn read_lines`
- `fn cmd_collect`
- `fn parse_field`
- `fn percentile`
- `fn cmd_suggest`
- `fn chain_prev_hash`
- `fn parse_field_str`
- `fn cmd_apply`
- `fn cmd_verify`
- `fn arg_get`
- `fn main`

## Entries

### `fn is_loosening(field: string, old_v: string, new_v: string) -> bool`

> Fields classified by direction. "loosen_up"   means: raising the value
> weakens the gate (e.g. absorption_rate_max). "loosen_down" means lowering
> the value weakens the gate (e.g. diagonal_agreement_min, depth_min,
> saturation_policy.diag_min).

### `fn append_jsonl(path: string, row: string)`

_(no docstring)_

### `fn read_lines(path: string) -> list<string>`

_(no docstring)_

### `fn cmd_collect(argv: list<string>) -> int`

_(no docstring)_

### `fn parse_field(row: string, field: string) -> float`

_(no docstring)_

### `fn percentile(values: list<float>, p: float) -> float`

_(no docstring)_

### `fn cmd_suggest(argv: list<string>) -> int`

_(no docstring)_

### `fn chain_prev_hash() -> string`

_(no docstring)_

### `fn parse_field_str(row: string, field: string) -> string`

_(no docstring)_

### `fn cmd_apply(argv: list<string>) -> int`

_(no docstring)_

### `fn cmd_verify(_argv: list<string>) -> int`

_(no docstring)_

### `fn arg_get(argv: list<string>, key: string, dflt: string) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

