<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/an11_c_verifier.hexa -->
<!-- entry_count: 30 -->

# `tool/an11_c_verifier.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** � AN11(c) real_usable deterministic verifier.

**Public/Internal entries:** 30

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn resolve_root`
- `fn my_file_exists`
- `fn read_safe`
- `fn shell_escape_safe`
- `fn json_escape`
- `fn fmt_float`
- `fn index_of_from`
- `fn extract_string_key`
- `fn reply_schema_ok`
- `fn extract_reply_text`
- `fn sha256_of_str`
- `fn hash_key`
- `fn probe_health`
- `fn post_prompt`
- `fn ln_newton`
- `fn build_dist_from_hashes`
- `fn dist_total`
- `fn union_keys`
- `fn jsd`
- `fn load_prompt_at_index`
- `fn count_prompt_lines`
- `fn load_baseline_dist`
- `fn synthetic_discard_baseline`
- `fn emit_mock_endpoint_cfg`
- `fn mock_response`
- `fn emit_ssot`
- `fn run`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn my_file_exists(path: string) -> bool`

_(no docstring)_

### `fn read_safe(path: string) -> string`

_(no docstring)_

### `fn shell_escape_safe(s: string) -> string`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn fmt_float(x: float) -> string`

_(no docstring)_

### `fn index_of_from(hay: string, needle: string, start: int) -> int`

_(no docstring)_

### `fn extract_string_key(blob: string, key: string) -> string`

_(no docstring)_

### `fn reply_schema_ok(body: string) -> bool`

_(no docstring)_

### `fn extract_reply_text(body: string) -> string`

> Extract first non-empty reply field value for hashing. Falls back to
> raw body when schema absent (e.g. plain-text endpoint).

### `fn sha256_of_str(s: string) -> string`

_(no docstring)_

### `fn hash_key(s: string) -> string`

> Prefix-16 of sha256 — the dist key. Collision space 16^16 = 2^64, safe for N=50.

### `fn probe_health(url: string, health_path: string, timeout_sec: int) -> string`

_(no docstring)_

### `fn post_prompt(url: string, payload: string, timeout_sec: int) -> array`

_(no docstring)_

### `fn ln_newton(x: float) -> float`

_(no docstring)_

### `fn build_dist_from_hashes(hashes: array) -> any`

_(no docstring)_

### `fn dist_total(dist: any) -> int`

_(no docstring)_

### `fn union_keys(a: any, b: any) -> array`

> Union of keys of two dists.

### `fn jsd(p_dist: any, q_dist: any) -> float`

_(no docstring)_

### `fn load_prompt_at_index(prompts_path: string, idx: int) -> string`

_(no docstring)_

### `fn count_prompt_lines(prompts_path: string) -> int`

_(no docstring)_

### `fn load_baseline_dist(baseline_path: string) -> any`

_(no docstring)_

### `fn synthetic_discard_baseline() -> any`

_(no docstring)_

### `fn emit_mock_endpoint_cfg(cfg_path: string)`

_(no docstring)_

### `fn mock_response(call_i: int) -> array`

_(no docstring)_

### `fn emit_ssot(ssot_path: string, dest: string, round: string,`

_(no docstring)_

### `fn run(dest: string, round: string, dry_run: bool, calls: int) -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

