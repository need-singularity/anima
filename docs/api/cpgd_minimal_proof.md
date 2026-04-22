<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/cpgd_minimal_proof.hexa -->
<!-- entry_count: 38 -->

# `tool/cpgd_minimal_proof.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 38

## Table of contents

- `fn _str`
- `fn resolve_root`
- `fn fexists`
- `fn read_safe`
- `fn byte_at`
- `fn index_of_from`
- `fn extract_array_block`
- `fn extract_str`
- `fn parse_flat_floats`
- `fn parse_strings_block`
- `fn sqrt_newton`
- `fn fabs`
- `fn vec_dot`
- `fn vec_norm`
- `fn load_eigenvecs`
- `fn load_template_ids`
- `fn load_source_sha`
- `fn make_projector`
- `fn verify_projector_idempotent`
- `fn make_W_init`
- `fn lcg_next`
- `fn randn_pair`
- `fn rand_matrix`
- `fn matmul_right`
- `fn update_W`
- `fn cpgd_step`
- `fn row_cosines`
- `fn verify_init_unit_cosine`
- `fn dry_run_10step`
- `fn format_float_fixed`
- `fn canonical_payload`
- `fn sha256_of_string`
- `fn emit_float_array`
- `fn emit_string_array`
- `fn write_result`
- `fn run_once`
- `fn selftest_minimal`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn fexists(path: string) -> bool`

_(no docstring)_

### `fn read_safe(path: string) -> string`

_(no docstring)_

### `fn byte_at(s: string, i: int) -> int`

_(no docstring)_

### `fn index_of_from(hay: string, needle: string, start: int) -> int`

_(no docstring)_

### `fn extract_array_block(blob: string, key: string) -> string`

_(no docstring)_

### `fn extract_str(blob: string, key: string) -> string`

_(no docstring)_

### `fn parse_flat_floats(inner: string) -> array`

_(no docstring)_

### `fn parse_strings_block(block: string) -> array`

_(no docstring)_

### `fn sqrt_newton(x: float) -> float`

_(no docstring)_

### `fn fabs(x: float) -> float`

_(no docstring)_

### `fn vec_dot(a: array, b: array) -> float`

_(no docstring)_

### `fn vec_norm(a: array) -> float`

_(no docstring)_

### `fn load_eigenvecs(path: string) -> array`

_(no docstring)_

### `fn load_template_ids(path: string) -> array`

_(no docstring)_

### `fn load_source_sha(path: string) -> string`

_(no docstring)_

### `fn make_projector(eigenvecs: array) -> array`

_(no docstring)_

### `fn verify_projector_idempotent(P: array) -> bool`

_(no docstring)_

### `fn make_W_init(eigenvecs: array) -> array`

_(no docstring)_

### `fn lcg_next(state_arr: array) -> float`

_(no docstring)_

### `fn randn_pair(state_arr: array) -> array`

_(no docstring)_

### `fn rand_matrix(rows: int, cols: int, state_arr: array) -> array`

_(no docstring)_

### `fn matmul_right(G: array, P: array) -> array`

> ─── matrix ops ────────────────────────────────────────────────────────────
> G' = G · P_S  (projects each row onto S; P_S is symmetric so row-proj ≡ col-proj)

### `fn update_W(W: array, G: array, lr: float) -> array`

_(no docstring)_

### `fn cpgd_step(W: array, grad: array, P_S: array, lr: float) -> array`

> CPGD step:  W_new = W - lr · (G · P_S)

### `fn row_cosines(W: array, eigenvecs: array) -> array`

_(no docstring)_

### `fn verify_init_unit_cosine(W: array, E: array) -> bool`

> Verify cos(W_init[i], v_i) ≈ 1 within EPS_COS_INIT

### `fn dry_run_10step(eigenvec_path: string, lr: float) -> array`

> ─── dry-run orchestration ─────────────────────────────────────────────────
> Returns [step_count, min_per_tpl [16], max_drift, all_above, src_sha, tpl_ids,
> idem_ok, init_unit_cos_ok, cos_history_step_last]

### `fn format_float_fixed(x: float) -> string`

_(no docstring)_

### `fn canonical_payload(step_count: int, min_per_tpl: array,`

_(no docstring)_

### `fn sha256_of_string(s: string) -> string`

_(no docstring)_

### `fn emit_float_array(a: array) -> string`

_(no docstring)_

### `fn emit_string_array(a: array) -> string`

_(no docstring)_

### `fn write_result(out_path: string,`

_(no docstring)_

### `fn run_once(lr: float) -> array`

_(no docstring)_

### `fn selftest_minimal() -> bool`

_(no docstring)_

### `fn main()`

_(no docstring)_

