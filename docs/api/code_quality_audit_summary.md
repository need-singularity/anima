<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/code_quality_audit_summary.hexa -->
<!-- entry_count: 7 -->

# `tool/code_quality_audit_summary.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 7

## Table of contents

- `fn _shq`
- `fn _file_exists`
- `fn _ts_iso`
- `fn _json_esc`
- `fn _probe_int`
- `fn _probe_arr_len`
- `fn _arg_present`

## Entries

### `fn _shq(s: string) -> string`

_(no docstring)_

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _json_esc(s: string) -> string`

_(no docstring)_

### `fn _probe_int(path: string, key: string) -> int`

> Probe top-level int field; returns -1 when missing/unreadable.

### `fn _probe_arr_len(path: string, key: string) -> int`

> Probe length of a top-level array field; -1 when missing.

### `fn _arg_present(av: array, k: string) -> bool`

_(no docstring)_

