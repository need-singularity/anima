<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/an11_b_verifier.hexa -->
<!-- entry_count: 26 -->

# `tool/an11_b_verifier.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** � AN11(b) consciousness_attached deterministic verifier.

**Public/Internal entries:** 26

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn resolve_root`
- `fn my_file_exists`
- `fn read_safe`
- `fn byte_at`
- `fn index_of_from`
- `fn parse_flat_floats`
- `fn extract_array_block`
- `fn split_rows`
- `fn extract_str`
- `fn sqrt_newton`
- `fn dot`
- `fn vec_norm`
- `fn abs_cosine`
- `fn load_templates`
- `fn load_eigen`
- `fn load_phi_fallback`
- `fn compute_cosines`
- `fn top_n`
- `fn count_family`
- `fn json_escape`
- `fn fmt_float`
- `fn emit_ssot`
- `fn run`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn my_file_exists(path: string) -> bool`

_(no docstring)_

### `fn read_safe(path: string) -> string`

_(no docstring)_

### `fn byte_at(s: string, i: int) -> int`

_(no docstring)_

### `fn index_of_from(hay: string, needle: string, start: int) -> int`

_(no docstring)_

### `fn parse_flat_floats(inner: string) -> array`

> Parse comma-separated scalar float fragments. Caller strips enclosing [ ].

### `fn extract_array_block(blob: string, key: string) -> string`

> Extract a top-level JSON array value for key `key`.
> Tolerant: supports nested arrays (bracket counted). Empty on miss.

### `fn split_rows(block: string) -> array`

> Split an array-of-arrays block "[ [..],[..] ]" into top-level sub-arrays (inner text only).

### `fn extract_str(blob: string, key: string) -> string`

> Extract a quoted string value for first occurrence of key `key`.

### `fn sqrt_newton(x: float) -> float`

_(no docstring)_

### `fn dot(a: array, b: array) -> float`

_(no docstring)_

### `fn vec_norm(a: array) -> float`

_(no docstring)_

### `fn abs_cosine(a: array, b: array) -> float`

> Absolute cosine — direction-agnostic attach (eigenvector sign is arbitrary).

### `fn load_templates(path: string) -> array`

_(no docstring)_

### `fn load_eigen(blob: string) -> array`

_(no docstring)_

### `fn load_phi_fallback(blob: string) -> array`

_(no docstring)_

### `fn compute_cosines(eigens: array, templates: array) -> array`

_(no docstring)_

### `fn top_n(records: array, n_keep: int) -> array`

> Return top-N records sorted by cos (index 3) descending.
> Selection sort — pool size 16*16=256 small.

### `fn count_family(templates: array, fam: string) -> int`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn fmt_float(x: float) -> string`

_(no docstring)_

### `fn emit_ssot(ssot_path: string, dest: string, round: string, source: string,`

> max_eigen_i / max_tid / max_fam / max_cos are separate scalars (avoid map).

### `fn run(dest: string, round: string) -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

