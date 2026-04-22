<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/drill_self_ref_noise_probe.hexa -->
<!-- entry_count: 16 -->

# `tool/drill_self_ref_noise_probe.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 16

## Table of contents

- `fn fabs`
- `fn to_f`
- `fn now_stamp`
- `fn fmt_f`
- `fn str_contains`
- `fn hash_proj`
- `fn lcg_next`
- `fn noise_gaussian`
- `fn noise_bitflip`
- `fn noise_envdelta`
- `fn apply_noise`
- `fn module_fallback`
- `fn aggregate_seed`
- `fn theta_diagonal`
- `fn overall_verdict`
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

_(no docstring)_

### `fn lcg_next(state: int) -> int`

> Linear congruential fallback rng (deterministic; we only need low-order bits)

### `fn noise_gaussian(seed_text: string, level: float, salt: string) -> string`

> gaussian noise on hex stream — approximate N(0, sigma) via sum-of-uniforms

### `fn noise_bitflip(seed_text: string, level: float, salt: string) -> string`

> bit-flip: flip round(level*24) bits at deterministic positions

### `fn noise_envdelta(seed_text: string, level: float, salt: string) -> string`

> env-delta: append level-scaled env/timestamp drift token

### `fn apply_noise(kind: string, seed_text: string, level: float, salt: string) -> string`

_(no docstring)_

### `fn module_fallback(seed_id: string, seed_text: string, mod_name: string)`

_(no docstring)_

### `fn aggregate_seed(seed_id: string, seed_text: string)`

_(no docstring)_

### `fn theta_diagonal(sig1: string, sig2: string) -> float`

_(no docstring)_

### `fn overall_verdict(grid) -> string`

> NOISE_ABSORBED     — every cell ABSORBED
> NOISE_PARADOX      — within any single noise kind, ABSORBED and DIVERGE co-present
> (or cross-kind disagreement at same level)
> NOISE_THRESHOLD_N  — pure monotonic threshold (only ABSORBED below N, DIVERGE at/above)

### `fn main()`

_(no docstring)_

