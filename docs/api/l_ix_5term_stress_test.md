<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/l_ix_5term_stress_test.hexa -->
<!-- entry_count: 20 -->

# `tool/l_ix_5term_stress_test.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 20

## Table of contents

- `fn t_tension_x1000`
- `fn ln_perm_x1000`
- `fn v_struct_x1000`
- `fn v_sync_stub_x1000`
- `fn i_irr_x1000`
- `fn abs_i`
- `fn mean_x1000`
- `fn max_int`
- `fn min_int`
- `fn isqrt`
- `fn ln_x1000`
- `fn hurst_rs_x1000`
- `fn v_hurst_x1000`
- `fn l_ix_4term_x1000`
- `fn l_ix_5term_x1000`
- `fn sum_list`
- `fn now_stamp`
- `fn bool_s`
- `fn int_list_json`
- `fn main`

## Entries

### `fn t_tension_x1000(w_k: int, w_prev: int) -> int`

_(no docstring)_

### `fn ln_perm_x1000(x: int) -> int`

_(no docstring)_

### `fn v_struct_x1000(w: int) -> int`

_(no docstring)_

### `fn v_sync_stub_x1000(w: int) -> int`

_(no docstring)_

### `fn i_irr_x1000(w_k: int, w_prev: int) -> int`

_(no docstring)_

### `fn abs_i(x: int) -> int`

_(no docstring)_

### `fn mean_x1000(xs: list) -> int`

_(no docstring)_

### `fn max_int(xs: list) -> int`

_(no docstring)_

### `fn min_int(xs: list) -> int`

_(no docstring)_

### `fn isqrt(x: int) -> int`

> Newton sqrt for non-negative int.  Result = floor(sqrt(x)).

### `fn ln_x1000(x_x1000: int) -> int`

> Natural log ×1000 for positive integer input interpreted as a per-mille
> ratio ≥ 1000 (i.e. x ≥ 1).  For 0 < x < 1000 we mirror: ln(1/u) = -ln(u).
> Lookup-table based for determinism & no import.

### `fn hurst_rs_x1000(ws: list) -> int`

> R/S Hurst: returns H × 1000.  N must be ≥ 2.

### `fn v_hurst_x1000(h_x1000: int, delta_x1000: int) -> int`

> V_hurst_x1000 = δ · (H − 0.5)²    (both H and δ in ×1000 scale ⇒ dim check)

### `fn l_ix_4term_x1000(w_k: int, w_prev: int, lam_x1000: int) -> int`

_(no docstring)_

### `fn l_ix_5term_x1000(w_k: int, w_prev: int, lam_x1000: int, v_h_x1000: int) -> int`

_(no docstring)_

### `fn sum_list(xs: list) -> int`

_(no docstring)_

### `fn now_stamp() -> string`

> ── Helpers ────────────────────────────────────────────────────────────────

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn int_list_json(xs: list) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

