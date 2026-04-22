<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/cell_token_bridge_proto.hexa -->
<!-- entry_count: 33 -->

# `tool/cell_token_bridge_proto.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 33

## Table of contents

- `fn _str`
- `fn resolve_root`
- `fn fexists`
- `fn read_safe`
- `fn byte_at`
- `fn index_of_from`
- `fn extract_array_block`
- `fn extract_scalar_after`
- `fn parse_flat_floats`
- `fn parse_flat_ints`
- `fn sqrt_newton`
- `fn fabs`
- `fn iabs`
- `fn ilog2_floor`
- `fn load_eigenvecs_nested`
- `fn load_eigenvec_source_sha`
- `fn load_config`
- `fn bucket_of`
- `fn f_ct`
- `fn row_cosine`
- `fn f_tc`
- `fn round_trip_cos`
- `fn bridge_i_irr_bits`
- `fn is_bucket_midpoint`
- `fn eval_fixture_round_trip`
- `fn probe_drift_100step`
- `fn emit_int_array`
- `fn emit_detail_row`
- `fn emit_fixture_result`
- `fn extract_object_blocks`
- `fn extract_str_field`
- `fn load_fixtures`
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

### `fn extract_scalar_after(blob: string, key: string) -> string`

_(no docstring)_

### `fn parse_flat_floats(inner: string) -> array`

_(no docstring)_

### `fn parse_flat_ints(inner: string) -> array`

_(no docstring)_

### `fn sqrt_newton(x: float) -> float`

_(no docstring)_

### `fn fabs(x: float) -> float`

_(no docstring)_

### `fn iabs(x: int) -> int`

_(no docstring)_

### `fn ilog2_floor(x: int) -> int`

> integer log2 floor of a positive int, capped at 30

### `fn load_eigenvecs_nested(path: string) -> array`

_(no docstring)_

### `fn load_eigenvec_source_sha(path: string) -> string`

_(no docstring)_

### `fn load_config(root: string) -> array`

_(no docstring)_

### `fn bucket_of(w_per_mille: int) -> int`

_(no docstring)_

### `fn f_ct(w_per_mille: int, eigenvecs: array) -> array`

_(no docstring)_

### `fn row_cosine(a: array, b: array) -> float`

_(no docstring)_

### `fn f_tc(h: array, eigenvecs: array) -> int`

_(no docstring)_

### `fn round_trip_cos(h: array, eigenvecs: array) -> float`

> round_trip: f_tc ∘ f_ct
> given an already-embedded h, we round-trip by re-bucketing via f_tc then
> re-embedding via f_ct and measuring the cosine.  Lossless for the 5
> canonical embeddings; lossy near the per-mille boundaries (adversarial).

### `fn bridge_i_irr_bits(ws: array) -> int`

> bridge_i_irr_bits: Σ_{k∈[1..4]} log₂(|ΔW_k| + 1)
> matches spec §3 21-bit budget reasoning: ≤ 4 steps × 21 bits/step = 84.

### `fn is_bucket_midpoint(w: int) -> bool`

> Detect the "500‰ exact 2↔3 boundary" midpoint ambiguity (spec §4 C).
> A value w ∈ (0, 1000) is a bucket-midpoint (ambiguous between two
> adjacent 5-level centers) iff  (w + 100) % 200 == 0.
> For the canonical 5-level bucket centers {0, 200, 400, 600, 800, 1000}
> the midpoints are exactly {100, 300, 500, 700, 900}.  These are the
> positions where the integer-truncation bucket(w/200) AND the alternate
> round-up bucket ceil(w/200) have equal claim, and f_tc cannot recover
> w losslessly.

### `fn eval_fixture_round_trip(ws: array, eigenvecs: array, cos_thr: float, bits_budget: int) -> array`

> Build h-sequence from ws via f_ct, round-trip each, collect cos_min.
> raw#12 verdict criterion (matches spec §6 + spec §4 ablation C):
> BRIDGE_OK iff
> (a) cos_min ≥ cos_thr              (h-level round-trip floor)
> (b) i_irr_bits ≤ i_irr_bits_budget (21-bit × 4 step = 84 bit ceiling)
> (c) no ws[k] is a bucket-midpoint  (adversarial 500‰ → FAIL)
> This lets identity (all 1000‰) and ladder ([40,125,687,1000,1000]) pass
> while forcing adversarial ([500,500,500,500,500]) to FAIL exactly as the
> spec pre-registered.

### `fn probe_drift_100step(eigenvecs: array, ws_start: array, steps: int, lr: float) -> array`

_(no docstring)_

### `fn emit_int_array(a: array) -> string`

_(no docstring)_

### `fn emit_detail_row(row: array) -> string`

_(no docstring)_

### `fn emit_fixture_result(fixture_id: string,`

_(no docstring)_

### `fn extract_object_blocks(block: string) -> array`

_(no docstring)_

### `fn extract_str_field(obj: string, key: string) -> string`

_(no docstring)_

### `fn load_fixtures(root: string) -> array`

_(no docstring)_

### `fn main()`

_(no docstring)_

