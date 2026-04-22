<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/hexad_n28_falsification.hexa -->
<!-- entry_count: 21 -->

# `tool/hexad_n28_falsification.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 21

## Table of contents

- `fn now_stamp`
- `fn bool_s`
- `fn count_exist`
- `fn str_list_json`
- `fn int_list_json`
- `fn divisors_of`
- `fn sum_list_int`
- `struct N28DomainMap`
- `struct AxiomMatrix`
- `fn eval_n28_domain`
- `fn dom_cell_baseline_n28`
- `fn dom_lora_n28`
- `fn dom_n6_n28`
- `fn dom_iit_n28`
- `fn dom_cattheory_n28`
- `fn matrix_row_json`
- `fn dm_json`
- `fn resolve_universality`
- `fn resolve_h_star`
- `fn universal4_relation`
- `fn main`

## Entries

### `fn now_stamp() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn count_exist(paths: list) -> int`

_(no docstring)_

### `fn str_list_json(xs: list) -> string`

_(no docstring)_

### `fn int_list_json(xs: list) -> string`

_(no docstring)_

### `fn divisors_of(n: int) -> list`

_(no docstring)_

### `fn sum_list_int(xs: list) -> int`

_(no docstring)_

### `struct N28DomainMap`

_(no docstring)_

### `struct AxiomMatrix`

_(no docstring)_

### `fn eval_n28_domain(dm: N28DomainMap) -> AxiomMatrix`

_(no docstring)_

### `fn dom_cell_baseline_n28() -> N28DomainMap`

_(no docstring)_

### `fn dom_lora_n28() -> N28DomainMap`

_(no docstring)_

### `fn dom_n6_n28() -> N28DomainMap`

_(no docstring)_

### `fn dom_iit_n28() -> N28DomainMap`

_(no docstring)_

### `fn dom_cattheory_n28() -> N28DomainMap`

> D4 reused for apples-to-apples with the n=6 baseline run. Category
> theory is "closed by definition" — the axioms hold trivially — so
> this row is informational; it does NOT count toward the empirical
> H★ verdict.

### `fn matrix_row_json(m: AxiomMatrix) -> string`

_(no docstring)_

### `fn dm_json(dm: N28DomainMap) -> string`

_(no docstring)_

### `fn resolve_universality(score_x1000: int) -> string`

_(no docstring)_

### `fn resolve_h_star(primary_pass_count: int) -> string`

> H★ support rules (pre-registered, raw#12):
> primary_pass_count = 0  → H_STAR_STRONGLY_SUPPORTED
> primary_pass_count = 1  → H_STAR_WEAKLY_SUPPORTED
> primary_pass_count = 2  → H_STAR_INCONCLUSIVE  (further exp needed)
> primary_pass_count ≥ 3  → H_STAR_REFUTED       (τ(6)=4 primitivity denied)

### `fn universal4_relation(primary_pass_count: int) -> string`

> SAME_STRUCTURE iff ≥2 empirical domains pass primary-quartet.
> Under n=28 this is predicted to be false uniformly.

### `fn main()`

_(no docstring)_

