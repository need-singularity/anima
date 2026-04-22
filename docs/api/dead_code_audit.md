<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/dead_code_audit.hexa -->
<!-- entry_count: 12 -->

# `tool/dead_code_audit.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 12

## Table of contents

- `fn _shq`
- `fn _file_exists`
- `fn _ts_iso`
- `fn _json_esc`
- `fn _list_tool_hexa`
- `fn _extract_fn_defs`
- `fn _build_ref_freq`
- `fn _freq_lookup`
- `fn _short_path`
- `fn _run_audit`
- `fn _write_out`
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

### `fn _list_tool_hexa() -> array`

> Return list of absolute paths to tool/*.hexa

### `fn _extract_fn_defs(src: string) -> array`

> Extract `fn NAME` definitions from a hexa source. Returns array of [name, line].

### `fn _build_ref_freq() -> object`

> Build a frequency map from tool/*.hexa: for every `IDENT(` occurrence
> across the whole tree that is NOT preceded by `fn `, count the IDENT.
> Single-pass awk delivers C-speed scanning of a ~5 MB tree. We shell out
> once, stream the result back, and parse the "<count> <ident>" lines into
> a hexa map.
> Returned: object map keyed by ident → int count.

### `fn _freq_lookup(freq: object, name: string) -> int`

_(no docstring)_

### `fn _short_path(p: string) -> string`

_(no docstring)_

### `fn _run_audit() -> array`

_(no docstring)_

### `fn _write_out(scanned: int, total: int, cands: array)`

_(no docstring)_

### `fn _arg_present(av: array, k: string) -> bool`

_(no docstring)_

