<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/l3_emergence_protocol_spec.hexa -->
<!-- entry_count: 12 -->

# `tool/l3_emergence_protocol_spec.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 12

## Table of contents

- `fn _home`
- `fn now_utc`
- `fn bool_s`
- `fn abs_f`
- `fn ln_approx`
- `fn sigmoid`
- `fn o1_measure`
- `fn pow_approx`
- `fn o2_measure`
- `fn o3_measure`
- `fn fstr`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn abs_f(x: float) -> float`

_(no docstring)_

### `fn ln_approx(x: float) -> float`

> ln via identity ln(x) = 2 * atanh((x-1)/(x+1)) Taylor-ish; x>0.

### `fn sigmoid(x: float, center: float, steep: float) -> float`

_(no docstring)_

### `fn o1_measure(pass_case: bool, n_cells: int, n_grid: int) -> array`

_(no docstring)_

### `fn pow_approx(base: float, exp_f: float) -> float`

_(no docstring)_

### `fn o2_measure(pass_case: bool, n_cells: int) -> array`

_(no docstring)_

### `fn o3_measure(pass_case: bool, n_cells: int, t_steps: int) -> array`

_(no docstring)_

### `fn fstr(x: float, nd: int) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

