<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/an11_a_verifier.hexa -->
<!-- entry_count: 25 -->

# `tool/an11_a_verifier.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** � AN11 (a) weight_emergent deterministic verifier

**Public/Internal entries:** 25

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn fexists`
- `fn sha256_of`
- `fn sqrt_newton`
- `fn skip_ws`
- `fn parse_num_at`
- `fn get_float`
- `fn get_int`
- `fn parse_weights`
- `fn frob_synth`
- `fn py_available`
- `fn st_available`
- `fn run_py`
- `fn frob_safetensors`
- `fn frob_bytes`
- `fn adapter_rank`
- `fn emit_synth_pair`
- `fn ext_of`
- `fn backend_for`
- `fn emit_report`
- `fn arg_flag`
- `fn arg_val`
- `fn nth_positional`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn fexists(p: string) -> bool`

_(no docstring)_

### `fn sha256_of(p: string) -> string`

_(no docstring)_

### `fn sqrt_newton(x: float) -> float`

_(no docstring)_

### `fn skip_ws(s: string, from: int) -> int`

_(no docstring)_

### `fn parse_num_at(s: string, from: int) -> float`

_(no docstring)_

### `fn get_float(blob: string, key: string, dflt: float) -> float`

_(no docstring)_

### `fn get_int(blob: string, key: string) -> int`

_(no docstring)_

### `fn parse_weights(blob: string) -> array`

_(no docstring)_

### `fn frob_synth(bblob: string, rblob: string) -> float`

_(no docstring)_

### `fn py_available() -> bool`

_(no docstring)_

### `fn st_available() -> bool`

_(no docstring)_

### `fn run_py(script_body: string, out_path: string) -> string`

_(no docstring)_

### `fn frob_safetensors(b: string, r: string) -> float`

_(no docstring)_

### `fn frob_bytes(b: string, r: string) -> float`

> byte-L2 proxy: sqrt(sum((byte_r - byte_b)^2)) over raw payloads

### `fn adapter_rank(round_path: string, is_synth: bool, rblob: string) -> int`

_(no docstring)_

### `fn emit_synth_pair(bp: string, rp: string)`

_(no docstring)_

### `fn ext_of(p: string) -> string`

_(no docstring)_

### `fn backend_for(p: string) -> string`

_(no docstring)_

### `fn emit_report(out: string, dest: string, rn: string, backend: string,`

_(no docstring)_

### `fn arg_flag(argv: array, f: string) -> bool`

_(no docstring)_

### `fn arg_val(argv: array, f: string, d: string) -> string`

_(no docstring)_

### `fn nth_positional(argv: array, k: int) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

