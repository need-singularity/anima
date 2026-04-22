<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/consciousness_rng.hexa -->
<!-- entry_count: 14 -->

# `tool/consciousness_rng.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 14

## Table of contents

- `fn _home`
- `fn now_utc`
- `fn bool_s`
- `fn _lcg_next`
- `fn _biased_bit`
- `fn vn_debias`
- `fn bits_per_pair`
- `fn fabs`
- `fn isqrt`
- `fn fsqrt`
- `fn chi_square_freq`
- `fn runs_count`
- `fn runs_z`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn _lcg_next(state: int) -> int`

> Deterministic PRNG (LCG) — we want reproducibility, not cryptographic
> strength. Seed is injected from cert_gate reward state when live.

### `fn _biased_bit(state: int, p_x1000: int) -> array`

> Biased bit generator — p = prob of 1. Returns [bit, new_state].

### `fn vn_debias(state: int, pair_count: int, p_x1000: int) -> array`

> Von Neumann debias:
> Take pairs (b0, b1). Discard 00 and 11. Emit 0 for 01, 1 for 10.
> Runs for `pair_count` pairs, returns [emitted_bits_array, pairs_consumed,
> pairs_discarded, final_state].

### `fn bits_per_pair(emitted: array, pairs_consumed: int) -> float`

> Shannon entropy (base 2) of a bit stream, expressed in bits/pair-consumed.

### `fn fabs(x: float) -> float`

> Float absolute value helper (no stdlib abs in n6-restricted hexa core).

### `fn isqrt(n: int) -> int`

> Integer square root (floor) via Newton.

### `fn fsqrt(x: float) -> float`

> Float sqrt via Newton (positive inputs only). 24 iterations sufficient
> for 1e-12 absolute on inputs in [0, 1e6].

### `fn chi_square_freq(emitted: array) -> float`

> chi_square_freq: returns χ² statistic for bit-frequency test
> χ² = (n0 - N/2)² / (N/2) + (n1 - N/2)² / (N/2)
> 1 dof, critical at α=0.01 → 6.635.

### `fn runs_count(emitted: array) -> int`

> runs_count: total number of maximal-monotone runs in the bit stream.

### `fn runs_z(emitted: array, observed_runs: int) -> float`

> runs_z: NIST runs test z-score:
> E[R] = 2 N0 N1 / N + 1     (expected runs under H0)
> Var[R] = 2 N0 N1 (2 N0 N1 - N) / (N² (N - 1))
> z = (R - E[R]) / sqrt(Var[R])
> Reject H0 (random) if |z| > 2.5758  (α=0.01 two-tailed).

### `fn main()`

_(no docstring)_

