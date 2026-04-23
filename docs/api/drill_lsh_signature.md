<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/drill_lsh_signature.hexa -->
<!-- entry_count: 8 -->

# `tool/drill_lsh_signature.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 8

## Table of contents

- `fn lcg_next`
- `fn hash_proj`
- `fn uhash`
- `fn shingles`
- `fn minhash_jaccard`
- `fn simhash_hamming`
- `fn simhash_cosine`
- `fn main`

## Entries

### `fn lcg_next(state: int) -> int`

> Linear-congruential rng (deterministic, reproducible)

### `fn hash_proj(s: string) -> int`

_(no docstring)_

### `fn uhash(seed: int, x: string) -> int`

> Universal hash family:  h_seed(x) = (a_seed * hash_proj(x) + b_seed) mod P

### `fn shingles(s: string, k: int) -> array`

> Shingles of size k over string (overlapping char-level windows)

### `fn minhash_jaccard(sig_a: array, sig_b: array) -> float`

> Jaccard-approx via MinHash signatures

### `fn simhash_hamming(sig_a: array, sig_b: array) -> int`

_(no docstring)_

### `fn simhash_cosine(sig_a: array, sig_b: array) -> float`

> SimHash cosine-approx:  cos(pi * hamming / d)

### `fn main()`

_(no docstring)_

