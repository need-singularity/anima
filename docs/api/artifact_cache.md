<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/artifact_cache.hexa -->
<!-- entry_count: 24 -->

# `tool/artifact_cache.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 24

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _ts_iso`
- `fn _bool_s`
- `fn _file_exists`
- `fn _is_file`
- `fn _mkdir_p`
- `fn _json_escape`
- `fn _sha256_of_file`
- `fn _sha256_of_string`
- `fn cache_key`
- `fn _slot_dir`
- `fn _slot_result_path`
- `fn _slot_meta_path`
- `fn cache_get`
- `fn cache_has`
- `fn cache_put`
- `fn cache_index_append`
- `fn flag_present`
- `fn arg_after`
- `fn args_after`
- `fn run_selftest`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _exec_code(cmd: string) -> int`

_(no docstring)_

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _bool_s(b: bool) -> string`

_(no docstring)_

### `fn _file_exists(path: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _is_file(path: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(d: string) -> bool`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _sha256_of_file(path: string) -> string`

_(no docstring)_

### `fn _sha256_of_string(s: string) -> string`

_(no docstring)_

### `fn cache_key(input_files: array) -> string`

_(no docstring)_

### `fn _slot_dir(key: string) -> string`

_(no docstring)_

### `fn _slot_result_path(key: string) -> string`

_(no docstring)_

### `fn _slot_meta_path(key: string) -> string`

_(no docstring)_

### `fn cache_get(key: string) -> string`

> cache_get: returns cached payload string. Caller checks empty == miss.

### `fn cache_has(key: string) -> bool`

_(no docstring)_

### `fn cache_put(key: string, value: string, inputs: array) -> bool`

> cache_put: writes payload + meta atomically into the cache slot.

### `fn cache_index_append(key: string, hit: bool, source: string)`

> Append (key, ts, hit_bool) to the index. The index is the proof-of-use
> ledger: tools that wanted a key, whether it hit, and when.

### `fn flag_present(name: string) -> bool`

_(no docstring)_

### `fn arg_after(name: string) -> string`

_(no docstring)_

### `fn args_after(name: string) -> array`

> All trailing positional args after `--key`.

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

