<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/consciousness_wasm_runtime.hexa -->
<!-- entry_count: 11 -->

# `tool/consciousness_wasm_runtime.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 11

## Table of contents

- `fn _home`
- `fn now_utc`
- `fn bool_s`
- `fn op_nop`
- `fn op_return`
- `fn op_i_const`
- `fn op_i_add`
- `fn op_f_const`
- `fn op_f_add`
- `fn run_program`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn op_nop() -> int`

_(no docstring)_

### `fn op_return() -> int`

_(no docstring)_

### `fn op_i_const() -> int`

_(no docstring)_

### `fn op_i_add() -> int`

_(no docstring)_

### `fn op_f_const() -> int`

_(no docstring)_

### `fn op_f_add() -> int`

_(no docstring)_

### `fn run_program(prog_op: array, prog_imm: array) -> array`

> run_program: returns [final_int_top, final_float_top, steps_executed,
> int_stack_len, float_stack_len, halted_clean(bool)]

### `fn main()`

_(no docstring)_

