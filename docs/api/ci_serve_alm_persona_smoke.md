<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/ci_serve_alm_persona_smoke.hexa -->
<!-- entry_count: 15 -->

# `tool/ci_serve_alm_persona_smoke.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 15

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
- `fn _read_stripped`
- `fn _json_field_str_safe`
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

### `fn _read_stripped(path: string) -> string`

_(no docstring)_

### `fn _json_field_str_safe(path: string, key: string) -> string`

_(no docstring)_

### `fn _evaluate(exit_code: int, json_verdict: string, txt_verdict: string) -> bool`

_(no docstring)_

### `fn run(also_print: bool) -> int`

_(no docstring)_

### `fn self_test() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

