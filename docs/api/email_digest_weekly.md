<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/email_digest_weekly.hexa -->
<!-- entry_count: 12 -->

# `tool/email_digest_weekly.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** � ROI #81 weekly email digest (text only)

**Public/Internal entries:** 12

## Table of contents

- `fn _sh_quote`
- `fn _file_exists`
- `fn _json_escape`
- `fn _argv`
- `fn _has`
- `fn _now_iso`
- `fn _git_log_recent`
- `fn _roadmap_summary`
- `fn _cost_estimate_usd`
- `fn _build_text`
- `fn _self_test`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _argv() -> array`

_(no docstring)_

### `fn _has(av, k) -> bool`

_(no docstring)_

### `fn _now_iso() -> string`

_(no docstring)_

### `fn _git_log_recent() -> string`

_(no docstring)_

### `fn _roadmap_summary() -> array`

> Returns [done_count, active_count, planned_count, mean_pct, total]

### `fn _cost_estimate_usd() -> int`

> Returns approximate $ cost from launch manifest (sum of all stage gpu_count * $3/hr * duration_days * 24).

### `fn _build_text() -> string`

_(no docstring)_

### `fn _self_test()`

_(no docstring)_

### `fn main()`

_(no docstring)_

