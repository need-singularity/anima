<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/hexad_closure_drill.hexa -->
<!-- entry_count: 23 -->

# `tool/hexad_closure_drill.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════

**Public/Internal entries:** 23

## Table of contents

- `fn extract_json_string`
- `fn extract_json_number`
- `fn now_stamp`
- `fn log_info`
- `fn log_warn`
- `struct SatPolicy`
- `fn load_policy`
- `fn seed_id`
- `fn seed_kind`
- `fn seed_text`
- `fn seed_expected`
- `fn has_invariant_marker`
- `fn has_primitive_absorption`
- `fn has_diagonal_identity`
- `fn classify_seed`
- `struct CatResult`
- `fn seed_file_for`
- `fn run_category`
- `fn bool_s`
- `fn list_of_str_json`
- `fn cat_result_json`
- `fn write_nextlayer_criteria`
- `fn main`

## Entries

### `fn extract_json_string(text: string, key: string) -> string`

_(no docstring)_

### `fn extract_json_number(text: string, key: string) -> string`

_(no docstring)_

### `fn now_stamp() -> string`

_(no docstring)_

### `fn log_info(msg: string)`

_(no docstring)_

### `fn log_warn(msg: string)`

_(no docstring)_

### `struct SatPolicy`

_(no docstring)_

### `fn load_policy() -> SatPolicy`

_(no docstring)_

### `fn seed_id(line: string) -> string`

_(no docstring)_

### `fn seed_kind(line: string) -> string`

_(no docstring)_

### `fn seed_text(line: string) -> string`

_(no docstring)_

### `fn seed_expected(line: string) -> string`

_(no docstring)_

### `fn has_invariant_marker(t: string) -> bool`

_(no docstring)_

### `fn has_primitive_absorption(t: string) -> bool`

_(no docstring)_

### `fn has_diagonal_identity(t: string) -> bool`

_(no docstring)_

### `fn classify_seed(line: string) -> string`

_(no docstring)_

### `struct CatResult`

_(no docstring)_

### `fn seed_file_for(idx: int, key: string) -> string`

_(no docstring)_

### `fn run_category(idx: int, key: string, label: string) -> CatResult`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn list_of_str_json(xs: list) -> string`

_(no docstring)_

### `fn cat_result_json(r: CatResult) -> string`

_(no docstring)_

### `fn write_nextlayer_criteria(closure_count: int, gate_passed: bool, round_n: string)`

_(no docstring)_

### `fn main()`

_(no docstring)_

