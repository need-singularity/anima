<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/latency_histogram.hexa -->
<!-- entry_count: 16 -->

# `tool/latency_histogram.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 16

## Table of contents

- `fn lh_argv`
- `fn lh_flag`
- `fn lh_opt`
- `fn lh_file_exists`
- `fn lh_pluck_latency`
- `fn lh_split_lines`
- `fn lh_collect`
- `fn lh_sort_asc`
- `fn lh_percentile`
- `fn lh_min`
- `fn lh_max`
- `fn lh_mean`
- `fn lh_now_utc`
- `fn lh_emit`
- `fn lh_self_test`
- `fn main`

## Entries

### `fn lh_argv() -> array`

_(no docstring)_

### `fn lh_flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn lh_opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn lh_file_exists(p: string) -> bool`

_(no docstring)_

### `fn lh_pluck_latency(line: string) -> int`

_(no docstring)_

### `fn lh_split_lines(text: string) -> array`

_(no docstring)_

### `fn lh_collect(in_path: string) -> array`

_(no docstring)_

### `fn lh_sort_asc(arr: array) -> array`

_(no docstring)_

### `fn lh_percentile(sorted: array, p_num: int, p_den: int) -> int`

_(no docstring)_

### `fn lh_min(sorted: array) -> int`

_(no docstring)_

### `fn lh_max(sorted: array) -> int`

_(no docstring)_

### `fn lh_mean(arr: array) -> int`

_(no docstring)_

### `fn lh_now_utc() -> string`

_(no docstring)_

### `fn lh_emit(out_path: string, in_path: string, samples: array) -> int`

_(no docstring)_

### `fn lh_self_test() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

