<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/api_surface_extract.hexa -->
<!-- entry_count: 28 -->

# `tool/api_surface_extract.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 28

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _file_exists`
- `fn _dir_exists`
- `fn _mkdir_p`
- `fn _rm_rf`
- `fn _utc_now`
- `fn _basename`
- `fn _strip_hexa_ext`
- `fn _list_hexa`
- `struct Entry`
- `fn _is_comment`
- `fn _strip_comment_marks`
- `fn _is_decl_start`
- `fn _decl_kind`
- `fn _trim_signature`
- `fn extract_entries`
- `fn extract_tool_desc`
- `fn render_for_tool`
- `fn _atomic_write`
- `fn do_generate`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn _hash_no_ts`
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

### `fn _dir_exists(p: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(p: string) -> bool`

_(no docstring)_

### `fn _rm_rf(p: string) -> bool`

_(no docstring)_

### `fn _utc_now() -> string`

_(no docstring)_

### `fn _basename(path: string) -> string`

_(no docstring)_

### `fn _strip_hexa_ext(name: string) -> string`

_(no docstring)_

### `fn _list_hexa(dir: string) -> array`

_(no docstring)_

### `struct Entry`

_(no docstring)_

### `fn _is_comment(line: string) -> bool`

_(no docstring)_

### `fn _strip_comment_marks(line: string) -> string`

_(no docstring)_

### `fn _is_decl_start(line: string) -> bool`

_(no docstring)_

### `fn _decl_kind(line: string) -> string`

_(no docstring)_

### `fn _trim_signature(line: string) -> string`

_(no docstring)_

### `fn extract_entries(body: string) -> array`

_(no docstring)_

### `fn extract_tool_desc(body: string) -> string`

> First-line tool description (mirrors auto_tool_index logic).

### `fn render_for_tool(tool_path: string, ts: string) -> string`

_(no docstring)_

### `fn _atomic_write(path: string, body: string)`

_(no docstring)_

### `fn do_generate(tool_dir: string, out_dir: string) -> int`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn _hash_no_ts(path: string) -> string`

_(no docstring)_

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

