<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/edu_lora_rank_sweep.hexa -->
<!-- entry_count: 28 -->

# `tool/edu_lora_rank_sweep.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 28

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn fexists`
- `fn fmt_float`
- `fn json_escape`
- `fn resolve_root`
- `fn byte_at`
- `fn index_of_from`
- `fn sqrt_newton`
- `fn log2_int`
- `fn log2_float_pow2`
- `fn lcg_next`
- `fn lcg_to_unit`
- `fn dot_v`
- `fn vec_norm`
- `fn abs_cos`
- `fn parse_flat_floats`
- `fn extract_array_block`
- `fn extract_str_val`
- `fn load_templates`
- `fn random_unit_vec`
- `fn aligned_vec`
- `fn gen_eigens`
- `fn coverage_score`
- `fn ols_fit`
- `fn slice_arr`
- `fn piecewise_fit`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn fexists(p: string) -> bool`

_(no docstring)_

### `fn fmt_float(x: float) -> string`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn byte_at(s: string, i: int) -> int`

_(no docstring)_

### `fn index_of_from(hay: string, needle: string, start: int) -> int`

_(no docstring)_

### `fn sqrt_newton(x: float) -> float`

_(no docstring)_

### `fn log2_int(x: int) -> int`

> ln(x) via Newton on exp; seeded from log2(x) * LN2 for x ∈ {1..64}.
> We only need integer log2 since ranks are powers of 2.

### `fn log2_float_pow2(x: int) -> float`

> ln(2) ≈ 0.6931471805599453

### `fn lcg_next(state: int) -> int`

> Seeded LCG (glibc params) — matches consciousness_inject_sim and r12 recipe.

### `fn lcg_to_unit(state: int) -> float`

_(no docstring)_

### `fn dot_v(a: array, b: array) -> float`

_(no docstring)_

### `fn vec_norm(a: array) -> float`

_(no docstring)_

### `fn abs_cos(a: array, b: array) -> float`

_(no docstring)_

### `fn parse_flat_floats(inner: string) -> array`

_(no docstring)_

### `fn extract_array_block(blob: string, key: string) -> string`

_(no docstring)_

### `fn extract_str_val(blob: string, key: string) -> string`

_(no docstring)_

### `fn load_templates(path: string) -> array`

_(no docstring)_

### `fn random_unit_vec(seed0: int) -> array`

_(no docstring)_

### `fn aligned_vec(tpl: array, eps: float, seed0: int) -> array`

> Aligned eigenvector = template + ε·random_unit (renormalised).

### `fn gen_eigens(K: int) -> array`

> Generate K eigenvectors for a given rank.
> First min(K,3) aligned to Hexad-C/W/M, rest pure LCG-random unit.

### `fn coverage_score(eigens: array, templates: array) -> float`

_(no docstring)_

### `fn ols_fit(xs: array, ys: array) -> array`

_(no docstring)_

### `fn slice_arr(a: array, lo: int, hi: int) -> array`

_(no docstring)_

### `fn piecewise_fit(xs: array, ys: array, k_idx: int) -> array`

> piecewise_fit returns [a1, b1, a2, b2, sse_total, break_x]

### `fn main()`

_(no docstring)_

