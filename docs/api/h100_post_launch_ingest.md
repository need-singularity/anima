<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/h100_post_launch_ingest.hexa -->
<!-- entry_count: 20 -->

# `tool/h100_post_launch_ingest.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 20

## Table of contents

- `fn _sh_quote`
- `fn _file_exists`
- `fn _ts_iso`
- `fn _ts_epoch`
- `fn _json_escape`
- `fn _bool_str`
- `fn _argv`
- `fn _flag`
- `fn _json_field_str_safe`
- `fn _resolve_per_path_artifact`
- `fn _per_path_verdict`
- `fn _phi_aggregate_verdict`
- `fn _rollup_overall`
- `fn _render_verdict`
- `fn _last_slash`
- `fn run`
- `fn _mk_path`
- `fn _mk_phi`
- `fn self_test`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_iso() -> string`

> Native primitives honor SOURCE_DATE_EPOCH / HEXA_REPRODUCIBLE=1 (hexa-lang PR #23).
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

### `fn _json_field_str_safe(path: string, key: string) -> string`

_(no docstring)_

### `fn _resolve_per_path_artifact(path_id: string, exact_name: string) -> string`

_(no docstring)_

### `fn _per_path_verdict(path_id: string, exact_name: string)`

_(no docstring)_

### `fn _phi_aggregate_verdict()`

_(no docstring)_

### `fn _rollup_overall(p1, p2, p3, p4, phi) -> string`

_(no docstring)_

### `fn _render_verdict(p1, p2, p3, p4, phi, overall: string, ts: string) -> string`

_(no docstring)_

### `fn _last_slash(p: string) -> int`

_(no docstring)_

### `fn run(emit_path: string, also_print: bool) -> int`

_(no docstring)_

### `fn _mk_path(present: bool, verdict: string)`

_(no docstring)_

### `fn _mk_phi(present: bool, verdict: string)`

_(no docstring)_

### `fn self_test() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

