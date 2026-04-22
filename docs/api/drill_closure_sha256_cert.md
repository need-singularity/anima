<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/drill_closure_sha256_cert.hexa -->
<!-- entry_count: 13 -->

# `tool/drill_closure_sha256_cert.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 13

## Table of contents

- `fn fabs`
- `fn to_f`
- `fn now_stamp`
- `fn fexists`
- `fn sha256_of_file`
- `fn sha256_of_string`
- `fn str_contains`
- `fn hash_proj`
- `fn module_fallback`
- `fn aggregate_seed`
- `fn build_meta_cert`
- `fn emit_cert_json`
- `fn main`

## Entries

### `fn fabs(x: float) -> float`

_(no docstring)_

### `fn to_f(x: int) -> float`

_(no docstring)_

### `fn now_stamp() -> string`

_(no docstring)_

### `fn fexists(p: string) -> bool`

_(no docstring)_

### `fn sha256_of_file(p: string) -> string`

_(no docstring)_

### `fn sha256_of_string(s: string) -> string`

> sha256 of an arbitrary string — write to /tmp, shasum, unlink.

### `fn str_contains(s: string, sub: string) -> bool`

_(no docstring)_

### `fn hash_proj(s: string) -> int`

> 31-polynomial hash — mirrors drill_breakthrough_runner::hash_proj

### `fn module_fallback(seed_id: string, seed_text: string, mod_name: string)`

_(no docstring)_

### `fn aggregate_seed(seed_id: string, seed_text: string)`

_(no docstring)_

### `fn build_meta_cert(label: string)`

_(no docstring)_

### `fn emit_cert_json(cert, stamp: string) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

