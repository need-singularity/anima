<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/hexad_closure_verifier.hexa -->
<!-- entry_count: 17 -->

# `tool/hexad_closure_verifier.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════

**Public/Internal entries:** 17

## Table of contents

- `fn now_stamp`
- `fn log_info`
- `fn bool_s`
- `fn str_list_json`
- `fn in_list`
- `fn split_lines`
- `fn list_dir`
- `struct CatBreakdown`
- `fn inspect_category`
- `struct MorphAudit`
- `fn audit_morphisms`
- `struct PhantomReport`
- `fn detect_phantoms`
- `fn cat_json`
- `fn morph_json`
- `fn resolve_verdict`
- `fn main`

## Entries

### `fn now_stamp() -> string`

_(no docstring)_

### `fn log_info(msg: string)`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn str_list_json(xs: list) -> string`

_(no docstring)_

### `fn in_list(x: string, xs: list) -> bool`

_(no docstring)_

### `fn split_lines(text: string) -> list`

_(no docstring)_

### `fn list_dir(path: string) -> list`

> ── directory listing via /bin/ls (hexa stage1: no native readdir) ──

### `struct CatBreakdown`

_(no docstring)_

### `fn inspect_category(key: string, label: string) -> CatBreakdown`

_(no docstring)_

### `struct MorphAudit`

_(no docstring)_

### `fn audit_morphisms() -> list`

_(no docstring)_

### `struct PhantomReport`

_(no docstring)_

### `fn detect_phantoms() -> PhantomReport`

_(no docstring)_

### `fn cat_json(c: CatBreakdown) -> string`

_(no docstring)_

### `fn morph_json(m: MorphAudit) -> string`

_(no docstring)_

### `fn resolve_verdict(all_nonempty: bool, morph_present: bool, all_composed: bool, phantom_clean: bool) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

