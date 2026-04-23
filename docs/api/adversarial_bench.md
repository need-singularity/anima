<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/adversarial_bench.hexa -->
<!-- entry_count: 26 -->

# `tool/adversarial_bench.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 26

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn bool_s`
- `fn fexists`
- `fn dexists`
- `fn resolve_root`
- `fn resolve_hexa_bin`
- `fn json_escape`
- `fn sha256_file`
- `fn sha256_str`
- `fn arg_present`
- `fn cfg_get_str`
- `fn extract_str_field`
- `fn mkdir_p`
- `fn rmrf_path`
- `fn copy_tree`
- `fn prepare_clean_sandbox`
- `fn prepare_flip_a`
- `fn prepare_flip_b`
- `fn prepare_flip_c`
- `struct VerifyResult`
- `fn run_verifier_in_sandbox`
- `fn short_sha`
- `fn print_row`
- `fn run_json`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn fexists(p: string) -> bool`

_(no docstring)_

### `fn dexists(p: string) -> bool`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn resolve_hexa_bin() -> string`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn sha256_file(path: string) -> string`

_(no docstring)_

### `fn sha256_str(s: string) -> string`

_(no docstring)_

### `fn arg_present(argv, key: string) -> bool`

_(no docstring)_

### `fn cfg_get_str(cfg: string, key: string) -> string`

_(no docstring)_

### `fn extract_str_field(blob: string, key: string) -> string`

_(no docstring)_

### `fn mkdir_p(p: string)`

_(no docstring)_

### `fn rmrf_path(p: string)`

_(no docstring)_

### `fn copy_tree(src: string, dst: string)`

_(no docstring)_

### `fn prepare_clean_sandbox(root: string, sandbox_clean_abs: string, src_hexad_abs: string)`

_(no docstring)_

### `fn prepare_flip_a(root: string, sb_src_abs: string, sb_dst_abs: string,`

_(no docstring)_

### `fn prepare_flip_b(root: string, sb_src_abs: string, sb_dst_abs: string,`

_(no docstring)_

### `fn prepare_flip_c(root: string, sb_src_abs: string, sb_dst_abs: string,`

_(no docstring)_

### `struct VerifyResult`

_(no docstring)_

### `fn run_verifier_in_sandbox(bin: string, root: string, verifier_rel: string,`

_(no docstring)_

### `fn short_sha(s: string) -> string`

_(no docstring)_

### `fn print_row(label: string, r: VerifyResult, clean_verdict: string, want_flip: bool)`

_(no docstring)_

### `fn run_json(r: VerifyResult) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

