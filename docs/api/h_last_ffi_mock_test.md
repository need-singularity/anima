<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/h_last_ffi_mock_test.hexa -->
<!-- entry_count: 11 -->

# `tool/h_last_ffi_mock_test.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 11

## Table of contents

- `fn hidden_dim_for`
- `fn substrate_tag`
- `fn mix_int`
- `fn prompt_hash`
- `fn sqrt_newton`
- `fn h_last_extract_mock`
- `fn rms_of`
- `fn vec_eq`
- `fn det_checksum`
- `fn verify_substrate`
- `fn main`

## Entries

### `fn hidden_dim_for(substrate_id: string) -> int`

_(no docstring)_

### `fn substrate_tag(substrate_id: string) -> string`

_(no docstring)_

### `fn mix_int(h: int, v: int) -> int`

_(no docstring)_

### `fn prompt_hash(prompt: string) -> int`

_(no docstring)_

### `fn sqrt_newton(x: float) -> float`

_(no docstring)_

### `fn h_last_extract_mock(prompt: string, layer_idx: int, hidden_dim: int) -> array`

_(no docstring)_

### `fn rms_of(v: array) -> float`

_(no docstring)_

### `fn vec_eq(a: array, b: array) -> bool`

_(no docstring)_

### `fn det_checksum(v: array) -> int`

> Cheap bytewise checksum so result JSON has a comparable det_checksum for
> the H100 follow-up to verify byte-identical output across local + pod.

### `fn verify_substrate(substrate_id: string) -> array`

_(no docstring)_

### `fn main()`

_(no docstring)_

