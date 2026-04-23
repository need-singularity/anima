<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/dep_vuln_scan.hexa -->
<!-- entry_count: 18 -->

# `tool/dep_vuln_scan.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 18

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _file_exists`
- `fn _mkdir_p`
- `fn _ts_iso`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn _load_config`
- `fn _json_escape`
- `fn _parse_requirement_line`
- `fn _parse_manifest`
- `fn _list_hexa_files`
- `fn _scan_imports_in_file`
- `fn _match_advisories`
- `fn _emit_result`
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

### `fn _mkdir_p(dir: string) -> bool`

_(no docstring)_

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn _load_config(path: string)`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _parse_requirement_line(raw: string, comment_prefix: string) -> array`

_(no docstring)_

### `fn _parse_manifest(path: string, comment_prefix: string) -> array`

_(no docstring)_

### `fn _list_hexa_files(repo_root: string, root: string) -> array`

_(no docstring)_

### `fn _scan_imports_in_file(path: string) -> array`

_(no docstring)_

### `fn _match_advisories(deps: array, advisories: array) -> array`

_(no docstring)_

### `fn _emit_result(out_path: string, deps: array, hexa_imports: array, findings: array, real_db, ts: string)`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

