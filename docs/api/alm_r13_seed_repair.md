<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/alm_r13_seed_repair.hexa -->
<!-- entry_count: 13 -->

# `tool/alm_r13_seed_repair.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** � G5 terminator repair + G2 category cap

**Public/Internal entries:** 13

## Table of contents

- `fn _str`
- `fn resolve_root`
- `fn fexists`
- `fn read_safe`
- `fn byte_at`
- `fn json_escape`
- `fn cat_index`
- `fn is_ascii_terminator_byte`
- `fn is_utf8_terminator_at`
- `fn last_terminator_end`
- `fn extract_json_str`
- `fn replace_response_field`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn fexists(path: string) -> bool`

_(no docstring)_

### `fn read_safe(path: string) -> string`

_(no docstring)_

### `fn byte_at(s: string, i: int) -> int`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn cat_index(cat: string) -> int`

_(no docstring)_

### `fn is_ascii_terminator_byte(c: int) -> bool`

_(no docstring)_

### `fn is_utf8_terminator_at(s: string, end_excl: int) -> bool`

> Check 3-byte UTF-8 terminator ending at exclusive end_excl.

### `fn last_terminator_end(s: string) -> int`

> Scan response from tail back to find the last terminator byte.
> Returns -1 if none found, else exclusive end offset (use substring(0,end)).

### `fn extract_json_str(line: string, key: string) -> string`

_(no docstring)_

### `fn replace_response_field(line: string, new_resp: string) -> string`

> Replace "response":"..." value with new (already-unescaped) response.
> O(n) scan, no substring-per-byte.

### `fn main()`

_(no docstring)_

