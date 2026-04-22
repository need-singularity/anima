<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/auto_tool_index.hexa -->
<!-- entry_count: 25 -->

# `tool/auto_tool_index.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 25

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
- `fn _parent_of`
- `fn _list_hexa`
- `fn _starts_with_slashes`
- `fn _strip_comment_prefix`
- `fn extract_description`
- `fn _md_cell`
- `fn render`
- `fn _atomic_write`
- `fn do_generate`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn _mktempdir`
- `fn _hash_after_strip_ts`
- `fn run_selftest`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _exec_code(cmd: string) -> int`

_(no docstring)_

### `fn _file_exists(path: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _dir_exists(path: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(dir: string) -> bool`

_(no docstring)_

### `fn _rm_rf(path: string) -> bool`

_(no docstring)_

### `fn _utc_now() -> string`

_(no docstring)_

### `fn _basename(path: string) -> string`

_(no docstring)_

### `fn _parent_of(path: string) -> string`

_(no docstring)_

### `fn _list_hexa(dir: string) -> array`

> List *.hexa files in tool dir (non-recursive), LC_ALL=C sort.

### `fn _starts_with_slashes(s: string) -> bool`

> ─── description extraction ──────────────────────────────────────────────
> Strategy: first non-empty comment line of form
> `// tool/<name>.hexa — <desc>`
> otherwise the first non-empty `// <text>` line. Strip leading `//` /
> `////` runs and any leading `═` border characters. Returns "" if none.

### `fn _strip_comment_prefix(s: string) -> string`

_(no docstring)_

### `fn extract_description(body: string) -> string`

_(no docstring)_

### `fn _md_cell(s: string) -> string`

> Markdown-escape a description for table cells.

### `fn render(tool_dir: string, ts: string) -> string`

_(no docstring)_

### `fn _atomic_write(path: string, body: string)`

_(no docstring)_

### `fn do_generate(tool_dir: string, out_path: string) -> int`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn _mktempdir() -> string`

_(no docstring)_

### `fn _hash_after_strip_ts(path: string) -> string`

_(no docstring)_

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

