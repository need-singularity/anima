<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/edu_cell_btr_bridge.hexa -->
<!-- entry_count: 18 -->

# `tool/edu_cell_btr_bridge.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 18

## Table of contents

- `fn _fabs`
- `fn _sqrt`
- `fn _ln_small`
- `fn _plog2p`
- `fn _norm_entropy`
- `fn cell_state_default`
- `fn btr_state_default`
- `fn cell_to_phi`
- `fn btr_to_phi`
- `fn phi_to_cell`
- `fn phi_to_btr`
- `fn bridge_cell_to_btr`
- `fn bridge_btr_to_cell`
- `fn l2_list`
- `fn identity_distance_cell`
- `fn identity_distance_btr`
- `fn _fmt`
- `fn main`

## Entries

### `fn _fabs(x: float) -> float`

_(no docstring)_

### `fn _sqrt(x: float) -> float`

_(no docstring)_

### `fn _ln_small(p: float) -> float`

_(no docstring)_

### `fn _plog2p(p: float) -> float`

_(no docstring)_

### `fn _norm_entropy(ps: list) -> float`

> normalized entropy over a probability vector (sum should be ~1).
> Returns H / log2(|dim|).

### `fn cell_state_default() -> list`

_(no docstring)_

### `fn btr_state_default() -> list`

_(no docstring)_

### `fn cell_to_phi(cs: list) -> list`

_(no docstring)_

### `fn btr_to_phi(bs: list) -> list`

_(no docstring)_

### `fn phi_to_cell(pm: list, base: list) -> list`

_(no docstring)_

### `fn phi_to_btr(pm: list, base: list) -> list`

_(no docstring)_

### `fn bridge_cell_to_btr(cs: list, btr_base: list) -> list`

_(no docstring)_

### `fn bridge_btr_to_cell(bs: list, cell_base: list) -> list`

_(no docstring)_

### `fn l2_list(a: list, b: list) -> float`

_(no docstring)_

### `fn identity_distance_cell(cs: list) -> float`

_(no docstring)_

### `fn identity_distance_btr(bs: list) -> float`

_(no docstring)_

### `fn _fmt(x: float) -> string`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

