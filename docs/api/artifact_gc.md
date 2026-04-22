<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/artifact_gc.hexa -->
<!-- entry_count: 15 -->

# `tool/artifact_gc.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 15

## Table of contents

- `fn _sh_quote`
- `fn _exec`
- `fn _exec_rc`
- `fn _file_exists`
- `fn _home`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn _file_size`
- `fn _file_age_days`
- `fn _list_files`
- `fn _basename`
- `fn _build_reference_haystack`
- `fn _referenced`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _exec(cmd: string) -> string`

_(no docstring)_

### `fn _exec_rc(cmd: string) -> int`

_(no docstring)_

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _home() -> string`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av, k) -> bool`

_(no docstring)_

### `fn _opt(av, k, d) -> string`

_(no docstring)_

### `fn _file_size(p: string) -> int`

_(no docstring)_

### `fn _file_age_days(p: string) -> int`

_(no docstring)_

### `fn _list_files(dir: string) -> array`

_(no docstring)_

### `fn _basename(p: string) -> string`

_(no docstring)_

### `fn _build_reference_haystack(roadmap_path: string, cert_index_path: string) -> string`

> Build a single haystack string from .roadmap (uchg, read-only) + cert index.

### `fn _referenced(path: string, hay: string) -> bool`

> A file is "referenced" iff its basename or relative path appears
> in the haystack (substring match, case-sensitive).

### `fn main()`

_(no docstring)_

