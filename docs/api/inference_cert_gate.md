<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/inference_cert_gate.hexa -->
<!-- entry_count: 29 -->

# `tool/inference_cert_gate.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 29

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn resolve_root`
- `fn file_exists`
- `fn read_safe`
- `fn json_escape`
- `fn fmt_float`
- `fn sha256_of_str`
- `fn sha256_of_file`
- `fn index_of_from`
- `fn extract_string_key`
- `fn extract_float_key`
- `fn parse_dist_blob`
- `fn normalize_probs`
- `fn union_keys`
- `fn lookup_prob`
- `fn ln_newton`
- `fn jsd_from_probs`
- `fn load_config`
- `fn emit_ssot`
- `fn run_gate`
- `fn _mk_tmp_cfg`
- `fn _selftest`
- `fn s1_ok_false_fix`
- `fn _print_help`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn file_exists(path: string) -> bool`

_(no docstring)_

### `fn read_safe(path: string) -> string`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn fmt_float(x: float) -> string`

_(no docstring)_

### `fn sha256_of_str(s: string) -> string`

_(no docstring)_

### `fn sha256_of_file(path: string) -> string`

_(no docstring)_

### `fn index_of_from(hay: string, needle: string, start: int) -> int`

_(no docstring)_

### `fn extract_string_key(blob: string, key: string) -> string`

_(no docstring)_

### `fn extract_float_key(blob: string, key: string, fallback: float) -> float`

_(no docstring)_

### `fn parse_dist_blob(blob: string) -> array`

_(no docstring)_

### `fn normalize_probs(probs: array) -> array`

_(no docstring)_

### `fn union_keys(ka: array, kb: array) -> array`

> union of keys across two distributions (preserves order of first, then
> appends novel keys from second).

### `fn lookup_prob(keys: array, probs: array, k: string) -> float`

_(no docstring)_

### `fn ln_newton(x: float) -> float`

_(no docstring)_

### `fn jsd_from_probs(p_keys: array, p_probs: array,`

_(no docstring)_

### `fn load_config(cfg_path: string) -> array`

_(no docstring)_

### `fn emit_ssot(out_path: string,`

_(no docstring)_

### `fn run_gate(cfg_path: string,`

_(no docstring)_

### `fn _mk_tmp_cfg(mode: string, threshold: float) -> string`

_(no docstring)_

### `fn _selftest() -> int`

_(no docstring)_

### `fn s1_ok_false_fix()`

> placeholder helper so a mid-function assert doesn't compile-flag — never
> called in the happy path. Keeps the selftest block linear.

### `fn _print_help()`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

