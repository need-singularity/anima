<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/drill_breakthrough_runner.hexa -->
<!-- entry_count: 29 -->

# `tool/drill_breakthrough_runner.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** tool/drill_breakthrough_runner.hexa -- drill_breakthrough verifier (LIVE)

**Public/Internal entries:** 29

## Table of contents

- `fn ext_resolve`
- `fn out_path`
- `fn str_index_of`
- `fn str_contains`
- `fn digest_str`
- `fn hex_char_val`
- `fn hex_to_int`
- `fn hash_proj`
- `fn to_f`
- `fn fabs`
- `fn clamp01`
- `fn parse_float_field`
- `fn parse_int_field`
- `fn parse_bool_field`
- `fn jget_quoted`
- `fn parse_seeds`
- `fn module_fallback`
- `fn dfs_trace`
- `fn classify_frames`
- `fn saturation_mask`
- `fn aggregate_seed`
- `fn cross_run`
- `fn fmt_f`
- `fn emit_agg_json`
- `fn emit_seed_json`
- `fn now_stamp`
- `fn audit_integrity_ok`
- `fn run_all_seeds`
- `fn main`

## Entries

### `fn ext_resolve(ref_name)`

> raw#14 .ext SSOT resolve — no hardcode (raw#15). nexus canonical, anima follower.

### `fn out_path(dest: string, round_n: string) -> string`

_(no docstring)_

### `fn str_index_of(hay: string, needle: string, from: int) -> int`

_(no docstring)_

### `fn str_contains(s: string, sub: string) -> bool`

_(no docstring)_

### `fn digest_str(s: string) -> string`

> Deterministic string-digest using native sha256 (hex string). When the
> builtin is absent, fall back to an exec-shasum of a tmp file. Returns a
> 64-char hex string on success, empty on total failure.

### `fn hex_char_val(c: string) -> int`

> Convert the first 12 hex chars of a digest to an integer (non-negative).
> Uses substring comparisons — avoids byte_at.

### `fn hex_to_int(hex: string, n_nibbles: int) -> int`

_(no docstring)_

### `fn hash_proj(s: string) -> int`

> hash_proj — deterministic non-negative int projection of a string.
> Replaces byte_at/char_at reliance; uses sha256-hex + hex_to_int.

### `fn to_f(x: int) -> float`

_(no docstring)_

### `fn fabs(x: float) -> float`

_(no docstring)_

### `fn clamp01(x: float) -> float`

_(no docstring)_

### `fn parse_float_field(body: string, key: string, default_v: float) -> float`

_(no docstring)_

### `fn parse_int_field(body: string, key: string, default_v: int) -> int`

_(no docstring)_

### `fn parse_bool_field(body: string, key: string, default_v: bool) -> bool`

_(no docstring)_

### `fn jget_quoted(obj: string, key: string) -> string`

_(no docstring)_

### `fn parse_seeds(body: string) -> array`

_(no docstring)_

### `fn module_fallback(seed_id: string, seed_text: string, mod_name: string, run_tag: string) -> array`

> DETERMINISTIC CONTRACT (criteria.cross_run_policy.random_state_derivation):
> random_state = hash(seed + run_tag) but the ORACLE MUST collapse
> two runs to identical output. So run_tag is computed into a
> random_state int and then DISCARDED — it never flows into the
> judgment salt. This is the invariant the 2-run cross tests.

### `fn dfs_trace(seed_id: string, seed_text: string, run_tag: string, depth_min: int, k_window: int) -> array`

_(no docstring)_

### `fn classify_frames(frames: array, k_window: int) -> string`

_(no docstring)_

### `fn saturation_mask(seed_id: string, mod_frames: array, k_window: int) -> string`

_(no docstring)_

### `fn aggregate_seed(seed_id: string, seed_text: string, run_tag: string,`

_(no docstring)_

### `fn cross_run(seed_id: string, seed_text: string,`

_(no docstring)_

### `fn fmt_f(x: float) -> string`

_(no docstring)_

### `fn emit_agg_json(indent: string, agg: array) -> string`

_(no docstring)_

### `fn emit_seed_json(indent: string, seed: array, cross: array,`

_(no docstring)_

### `fn now_stamp() -> string`

_(no docstring)_

### `fn audit_integrity_ok(strict: bool) -> bool`

_(no docstring)_

### `fn run_all_seeds(dest: string, round_n: string) -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

