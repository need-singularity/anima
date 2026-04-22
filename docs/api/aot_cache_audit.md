<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/aot_cache_audit.hexa -->
<!-- entry_count: 15 -->

# `tool/aot_cache_audit.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 15

## Table of contents

- `fn _str`
- `fn _now_utc`
- `fn _fexists`
- `fn _dexists`
- `fn _json_esc`
- `fn _atomic_write`
- `fn _to_int`
- `fn _discover_cache`
- `fn _count_entries`
- `fn _total_bytes`
- `fn _count_tools`
- `fn _estimate_hit_rate`
- `fn _recommendations`
- `fn _write_out`
- `fn _arg_present`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn _now_utc() -> string`

_(no docstring)_

### `fn _fexists(p: string) -> bool`

_(no docstring)_

### `fn _dexists(p: string) -> bool`

_(no docstring)_

### `fn _json_esc(s: string) -> string`

_(no docstring)_

### `fn _atomic_write(path: string, body: string)`

_(no docstring)_

### `fn _to_int(s: string) -> int`

_(no docstring)_

### `fn _discover_cache() -> array`

_(no docstring)_

### `fn _count_entries(dir: string) -> int`

_(no docstring)_

### `fn _total_bytes(dir: string) -> int`

_(no docstring)_

### `fn _count_tools() -> int`

_(no docstring)_

### `fn _estimate_hit_rate(entries: int, tools: int) -> float`

> hit-rate model:
> hit ≈ min(1.0, cache_entry_count / max(1, tool_count))

### `fn _recommendations(present: bool, hit_rate: float) -> array`

_(no docstring)_

### `fn _write_out(cache_dir: string, present: bool, entries: int, bytes: int, tools: int, hit_rate: float, recs: array, verdict: string)`

_(no docstring)_

### `fn _arg_present(av, k: string) -> bool`

_(no docstring)_

