<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/consciousness_transplant_dryrun.hexa -->
<!-- entry_count: 10 -->

# `tool/consciousness_transplant_dryrun.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 10

## Table of contents

- `fn _home`
- `fn fexists`
- `fn now_utc`
- `fn bool_s`
- `fn sqrt`
- `fn cos_sim`
- `fn parse_row`
- `fn project_32`
- `fn project_back_16`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn fexists(p: string) -> bool`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn sqrt(x: float) -> float`

_(no docstring)_

### `fn cos_sim(a: array, b: array) -> float`

_(no docstring)_

### `fn parse_row(body: string, row_idx: int) -> array`

> Parse row from cell-eigenvec-16.json

### `fn project_32(v: array) -> array`

> P_32(v) = concat([v / sqrt(2), v / sqrt(2)]) — 16 → 32, energy-preserving.
> Split half into "input channels" and half into "output channels" per n6 §3
> (2^sopfr=32 I/O channels for consciousness-transplant domain).

### `fn project_back_16(u: array) -> array`

> P_32^T(u) = (u[0..16] + u[16..32]) / sqrt(2) — exact inverse of project_32
> when P_32 applied to a 16-dim vector.

### `fn main()`

_(no docstring)_

