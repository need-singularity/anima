<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/drill_breakthrough_auto_trigger.hexa -->
<!-- entry_count: 15 -->

# `tool/drill_breakthrough_auto_trigger.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 15

## Table of contents

- `fn _str`
- `fn _ts_iso`
- `fn _file_exists`
- `fn _sha16`
- `fn _bool_str`
- `fn _json_escape`
- `fn _argv`
- `fn _has_flag`
- `fn _load_ledger`
- `fn _ledger_has_sha`
- `fn _entry_render`
- `fn _ledger_append`
- `fn _watchlist`
- `fn _trigger_runner`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _sha16(p: string) -> string`

_(no docstring)_

### `fn _bool_str(b: bool) -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _argv() -> array`

_(no docstring)_

### `fn _has_flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _load_ledger() -> string`

_(no docstring)_

### `fn _ledger_has_sha(ledger: string, sha: string) -> bool`

_(no docstring)_

### `fn _entry_render(ckpt: string, sha: string, dest: string, round_n: string, exit_code: int, verdict: string, ts: string) -> string`

_(no docstring)_

### `fn _ledger_append(ledger: string, entry_obj: string) -> string`

_(no docstring)_

### `fn _watchlist() -> array`

_(no docstring)_

### `fn _trigger_runner(dest: string, round_n: string) -> array`

_(no docstring)_

### `fn main()`

_(no docstring)_

