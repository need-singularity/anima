<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/l3_pre_launch_validate.hexa -->
<!-- entry_count: 12 -->

# `tool/l3_pre_launch_validate.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 12

## Table of contents

- `fn _str`
- `fn _ts_iso`
- `fn _file_exists`
- `fn _bool_str`
- `fn _json_escape`
- `fn _argv`
- `fn _has_flag`
- `fn _field_str`
- `fn _field_int_after`
- `fn _bool_field`
- `fn _emit`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn _ts_iso() -> string`

> Native primitive honors SOURCE_DATE_EPOCH / HEXA_REPRODUCIBLE=1 (hexa-lang PR #23).
> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _bool_str(b: bool) -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _argv() -> array`

_(no docstring)_

### `fn _has_flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _field_str(blob: string, key: string) -> string`

_(no docstring)_

### `fn _field_int_after(blob: string, key: string) -> string`

> extract numeric (rev) — search for "rev" key, then read int after colon

### `fn _bool_field(blob: string, key: string) -> bool`

_(no docstring)_

### `fn _emit(out: string, ts: string, criteria_present: bool, criteria_rev: string, protocol_exit: int, protocol_verdict: string, discrimination_all: bool, verdict: string, dry: bool, note: string)`

_(no docstring)_

### `fn main()`

_(no docstring)_

