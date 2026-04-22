<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/anima_learning_free_driver.hexa -->
<!-- entry_count: 53 -->

# `tool/anima_learning_free_driver.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 53

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn resolve_root`
- `fn fexists`
- `fn read_safe`
- `fn byte_at`
- `fn index_of_from`
- `fn extract_array_block`
- `fn extract_str`
- `fn extract_number`
- `fn sqrt_newton`
- `fn fabs`
- `fn vec_dot`
- `fn vec_norm`
- `fn parse_flat_floats`
- `fn load_eigenvecs`
- `fn load_source_sha`
- `fn sha256_of_file`
- `fn make_projector`
- `fn verify_projector_idempotent`
- `fn make_w_init`
- `fn lcg_next`
- `fn randn_pair`
- `fn rand_matrix`
- `fn matmul_right`
- `fn update_w`
- `fn cpgd_step`
- `fn row_cosines`
- `fn verify_init_unit_cosine`
- `fn stage_1_cpgd`
- `fn _t_tension_x1000`
- `fn _ln_perm_x1000`
- `fn _v_struct_x1000`
- `fn _v_sync_stub_x1000`
- `fn _i_irr_x1000`
- `fn _l_ix_one_x1000`
- `fn classify_saturation`
- `fn stage_2_cell`
- `fn hexad_phase_active`
- `fn active_count`
- `fn stage_3_hexad`
- `fn an11_a_no_train`
- `fn an11_b_no_train`
- `fn log2_approx`
- `fn normalize_l1`
- `fn jsd_base2`
- `fn an11_c_no_train`
- `fn weight_hash`
- `fn bool_s`
- `fn emit_int_array`
- `fn write_result`
- `fn print_usage`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

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

### `fn extract_number(blob: string, key: string) -> float`

_(no docstring)_

### `fn sqrt_newton(x: float) -> float`

_(no docstring)_

### `fn fabs(x: float) -> float`

_(no docstring)_

### `fn vec_dot(a: array, b: array) -> float`

_(no docstring)_

### `fn vec_norm(a: array) -> float`

_(no docstring)_

### `fn parse_flat_floats(inner: string) -> array`

_(no docstring)_

### `fn load_eigenvecs(path: string, dim: int) -> array`

_(no docstring)_

### `fn load_source_sha(path: string) -> string`

_(no docstring)_

### `fn sha256_of_file(path: string) -> string`

_(no docstring)_

### `fn make_projector(eigenvecs: array, dim: int) -> array`

_(no docstring)_

### `fn verify_projector_idempotent(P: array, dim: int, eps: float) -> bool`

_(no docstring)_

### `fn make_w_init(eigenvecs: array, dim: int) -> array`

_(no docstring)_

### `fn lcg_next(state_arr: array) -> float`

_(no docstring)_

### `fn randn_pair(state_arr: array) -> array`

_(no docstring)_

### `fn rand_matrix(rows: int, cols: int, state_arr: array, scale: float) -> array`

_(no docstring)_

### `fn matmul_right(G: array, P: array, dim: int) -> array`

_(no docstring)_

### `fn update_w(W: array, G: array, lr: float, dim: int) -> array`

_(no docstring)_

### `fn cpgd_step(W: array, grad: array, P_S: array, lr: float, dim: int) -> array`

_(no docstring)_

### `fn row_cosines(W: array, eigenvecs: array) -> array`

_(no docstring)_

### `fn verify_init_unit_cosine(W: array, E: array) -> bool`

_(no docstring)_

### `fn stage_1_cpgd(cfg_root: string, cfg_blob: string, smoke: bool) -> array`

> returns [pass:bool, max_drift:float, min_cos:float, src_sha:string,
> projector_idempotent:bool, init_unit_cos_ok:bool, steps:int]

### `fn _t_tension_x1000(w_k: int, w_prev: int) -> int`

_(no docstring)_

### `fn _ln_perm_x1000(x: int) -> int`

_(no docstring)_

### `fn _v_struct_x1000(w: int) -> int`

_(no docstring)_

### `fn _v_sync_stub_x1000(w: int) -> int`

_(no docstring)_

### `fn _i_irr_x1000(w_k: int, w_prev: int) -> int`

_(no docstring)_

### `fn _l_ix_one_x1000(w_k: int, w_prev: int, lam_x1000: int) -> int`

_(no docstring)_

### `fn classify_saturation(ws: array) -> string`

_(no docstring)_

### `fn stage_2_cell(cfg_blob: string) -> array`

> returns [pass:bool, action_sum_x1000:int, l_trajectory:array,
> i_irr_cusp:array[2], saturation:string, gen5_fixpoint:bool,
> monotone:bool]

### `fn hexad_phase_active(phase: int) -> array`

> Returns [c_on, d_on, w_on, s_on, m_on, e_on] as 0/1 ints (stage0 bool-in-array
> is fragile; use ints for deterministic counting).

### `fn active_count(states: array) -> int`

_(no docstring)_

### `fn stage_3_hexad(cfg_blob: string, corpus_path: string) -> array`

> returns [pass:bool, p1_count:int, p2_count:int, p3_count:int,
> coverage_ok:bool, no_mutation:bool]

### `fn an11_a_no_train() -> array`

_(no docstring)_

### `fn an11_b_no_train(cfg_blob: string, eigenvecs: array) -> array`

_(no docstring)_

### `fn log2_approx(x: float) -> float`

_(no docstring)_

### `fn normalize_l1(arr: array) -> array`

_(no docstring)_

### `fn jsd_base2(P: array, Q: array) -> float`

_(no docstring)_

### `fn an11_c_no_train(cfg_blob: string) -> array`

_(no docstring)_

### `fn weight_hash(cfg_root: string) -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn emit_int_array(a: array) -> string`

_(no docstring)_

### `fn write_result(`

_(no docstring)_

### `fn print_usage()`

_(no docstring)_

### `fn main()`

_(no docstring)_

