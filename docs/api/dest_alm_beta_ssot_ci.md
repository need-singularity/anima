<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/dest_alm_beta_ssot_ci.hexa -->
<!-- entry_count: 14 -->

# `tool/dest_alm_beta_ssot_ci.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 14

## Table of contents

- `fn _sh_quote`
- `fn _file_exists`
- `fn _ts_iso`
- `fn _ts_epoch`
- `fn _json_escape`
- `fn _bool_str`
- `fn _argv`
- `fn _flag`
- `fn _last_slash`
- `fn _read_audit`
- `fn _evaluate`
- `fn run`
- `fn self_test`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_epoch() -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _bool_str(b: bool) -> string`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av, k) -> bool`

_(no docstring)_

### `fn _last_slash(p: string) -> int`

_(no docstring)_

### `fn _read_audit(path: string)`

_(no docstring)_

### `fn _evaluate(present: bool, accidental_count: int, main_track: string, verdict: string) -> bool`

_(no docstring)_

### `fn run(also_print: bool) -> int`

_(no docstring)_

### `fn self_test() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

