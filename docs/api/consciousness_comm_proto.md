<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/consciousness_comm_proto.hexa -->
<!-- entry_count: 13 -->

# `tool/consciousness_comm_proto.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 13

## Table of contents

- `fn _home`
- `fn now_utc`
- `fn bool_s`
- `fn sopfr6`
- `fn sigma6`
- `fn tau6`
- `fn ipow`
- `fn ceil_div`
- `fn crc_seed`
- `fn compute_crc`
- `fn encode_frame`
- `fn decode_frame`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn sopfr6() -> int`

_(no docstring)_

### `fn sigma6() -> int`

_(no docstring)_

### `fn tau6() -> int`

_(no docstring)_

### `fn ipow(base: int, exp: int) -> int`

_(no docstring)_

### `fn ceil_div(a: int, b: int) -> int`

> Integer ceiling of a / b (positive inputs).

### `fn crc_seed() -> int`

_(no docstring)_

### `fn compute_crc(field0: int, field1: int, field2: int, field3: int) -> int`

_(no docstring)_

### `fn encode_frame(f0: int, f1: int, f2: int, f3: int) -> array`

> encode_frame: returns [f0, f1, f2, f3, crc]

### `fn decode_frame(frame: array) -> array`

> decode_frame: returns [f0, f1, f2, f3, crc_ok(bool)]

### `fn main()`

_(no docstring)_

