<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/F_lattice_correlation.hexa -->
<!-- entry_count: 10 -->

# `tool/F_lattice_correlation.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** � O2 correlation helpers (stand-alone module)

**Public/Internal entries:** 10

## Table of contents

- `fn iabs`
- `fn sign_of`
- `fn clamp_int`
- `fn log2k`
- `fn correlation_at`
- `fn correlation_decay`
- `fn power_law_alpha`
- `fn xi_over_e`
- `fn assert_c`
- `fn main`

## Entries

### `fn iabs(x: int) -> int`

_(no docstring)_

### `fn sign_of(x: int) -> int`

_(no docstring)_

### `fn clamp_int(v: int, lo: int, hi: int) -> int`

_(no docstring)_

### `fn log2k(n: int) -> int`

> integer log2 × 1000 approximation (small-argument table + bit-shift fallback).

### `fn correlation_at(ss: [int], size: int, r_target: int) -> int`

> ─── correlation: C(r) on parallel state array ─────────────────────────
> ss[] = flat row-major state codes: 0=active, 1=drop, 2=sealed.
> C(r) = mean over cell-pairs at Manhattan distance r of indicator
> { both non-active AND same state }.  Returned in ppm (0..1000).

### `fn correlation_decay(ss: [int], size: int) -> [int]`

> correlation_decay(ss, size) → [C(1), C(2), …, C(size/2)] in ppm.

### `fn power_law_alpha(cs: [int]) -> int`

> Power-law fit: α × 1000 via 2-point log-linear (first and last r).
> C(r) ~ r^(-α)  ⇒  α = (log C(1) - log C(r_max)) / log(r_max).
> Returns 0 if any sample is zero or if C decreases to zero (no decay detected).

### `fn xi_over_e(cs: [int]) -> int`

> ξ (correlation length) × 1000, defined as smallest r where C(r) ≤ C(1)/e.
> Uses e≈2.718 → C(1)/e ≈ C(1) * 368/1000 (integer arithmetic).
> If no r satisfies, extrapolate linearly on the last segment.

### `fn assert_c(name: string, cond: bool) -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

