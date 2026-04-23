<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/dist_native_build_periodic.hexa -->
<!-- entry_count: 17 -->

# `tool/dist_native_build_periodic.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 17

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _file_exists`
- `fn _dir_exists`
- `fn _mkdir_p`
- `fn _utc_now`
- `fn _epoch_s`
- `fn _parent_of`
- `fn _json_escape`
- `fn _append_jsonl`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn do_run`
- `fn run_selftest`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _exec_code(cmd: string) -> int`

_(no docstring)_

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _dir_exists(p: string)  -> bool`

_(no docstring)_

### `fn _mkdir_p(p: string)     -> bool`

_(no docstring)_

### `fn _utc_now() -> string`

_(no docstring)_

### `fn _epoch_s() -> int`

_(no docstring)_

### `fn _parent_of(path: string) -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _append_jsonl(log_path: string, line: string) -> bool`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn do_run(script: string, workdir: string, log_path: string, dry: bool) -> int`

_(no docstring)_

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

