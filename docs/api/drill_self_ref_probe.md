<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/drill_self_ref_probe.hexa -->
<!-- entry_count: 13 -->

# `tool/drill_self_ref_probe.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 13

## Table of contents

- `fn fabs`
- `fn to_f`
- `fn now_stamp`
- `fn fmt_f`
- `fn str_contains`
- `fn hash_proj`
- `fn module_fallback`
- `fn aggregate_seed`
- `fn theta_diagonal`
- `fn probe_one`
- `fn overall_verdict`
- `fn emit_probe_json`
- `fn main`

## Entries

### `fn fabs(x: float) -> float`

_(no docstring)_

### `fn to_f(x: int) -> float`

_(no docstring)_

### `fn now_stamp() -> string`

_(no docstring)_

### `fn fmt_f(x: float) -> string`

_(no docstring)_

### `fn str_contains(s: string, sub: string) -> bool`

_(no docstring)_

### `fn hash_proj(s: string) -> int`

> 31-polynomial hash (mirrors drill_breakthrough_runner::hash_proj)

### `fn module_fallback(seed_id: string, seed_text: string, mod_name: string)`

_(no docstring)_

### `fn aggregate_seed(seed_id: string, seed_text: string)`

_(no docstring)_

### `fn theta_diagonal(sig1: string, sig2: string) -> float`

_(no docstring)_

### `fn probe_one(id: string, path: string, sha: string)`

_(no docstring)_

### `fn overall_verdict(probes) -> string`

_(no docstring)_

### `fn emit_probe_json(p) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

