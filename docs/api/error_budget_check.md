<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/error_budget_check.hexa -->
<!-- entry_count: 14 -->

# `tool/error_budget_check.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 14

## Table of contents

- `fn ebc_argv`
- `fn ebc_flag`
- `fn ebc_opt`
- `fn ebc_file_exists`
- `fn ebc_now_utc`
- `fn ebc_pluck_int`
- `fn ebc_pluck_bool`
- `fn ebc_split_lines`
- `fn ebc_ratio_ppm`
- `fn ebc_ppm_to_str`
- `fn ebc_eval_min`
- `fn ebc_evaluate`
- `fn ebc_self_test`
- `fn main`

## Entries

### `fn ebc_argv() -> array`

_(no docstring)_

### `fn ebc_flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn ebc_opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn ebc_file_exists(p: string) -> bool`

_(no docstring)_

### `fn ebc_now_utc() -> string`

_(no docstring)_

### `fn ebc_pluck_int(line: string, key: string) -> int`

_(no docstring)_

### `fn ebc_pluck_bool(line: string, key: string) -> int`

> Returns -1 missing, 0 false, 1 true

### `fn ebc_split_lines(text: string) -> array`

_(no docstring)_

### `fn ebc_ratio_ppm(num: int, den: int) -> int`

_(no docstring)_

### `fn ebc_ppm_to_str(ppm: int) -> string`

_(no docstring)_

### `fn ebc_eval_min(obs_ppm: int, obj_ppm: int) -> string`

> For ratio-min indicators (success-style):
> verdict = PASS  if observed_ratio >= objective_min
> WARN  if observed_ratio >= objective_min * (1 - 0.5*budget)
> BREACH otherwise

### `fn ebc_evaluate(cfg_path: string, samples_path: string, out_path: string) -> int`

_(no docstring)_

### `fn ebc_self_test() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

