<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/edu_v_sync_kuramoto_driver.hexa -->
<!-- entry_count: 13 -->

# `tool/edu_v_sync_kuramoto_driver.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** tool/edu_v_sync_kuramoto_driver.hexa

**Public/Internal entries:** 13

## Table of contents

- `fn poly_hash_int32`
- `fn mix3`
- `fn cos_perm_x1000`
- `fn sin_perm_x1000`
- `fn isqrt_x1000`
- `fn threshold`
- `fn build_node_hashes`
- `fn digit_char`
- `fn str_itoa`
- `fn fold_nodes_to_theta`
- `fn r_order_param`
- `fn v_sync_kuramoto`
- `fn run_fixture`

## Entries

### `fn poly_hash_int32(h: int, v: int) -> int`

> ---- polynomial hash (identical math to v_sync_kuramoto.hexa) --------------

### `fn mix3(seed_id: int, tag: int, idx: int) -> int`

> Two-arg seed hash: h(seed_id, tag, idx) without strings.

### `fn cos_perm_x1000(theta_perm: int) -> int`

> ---- cos / sin lookup (identical to v_sync_kuramoto.hexa) ------------------

### `fn sin_perm_x1000(theta_perm: int) -> int`

_(no docstring)_

### `fn isqrt_x1000(m: int) -> int`

_(no docstring)_

### `fn threshold(i: int, profile_id: int) -> int`

> ---- profile threshold (same semantics as atlas proto; int profile ID) -----
> profile IDs:
> 0 = "math_tight"  (math concepts 0..9 : t=99, else : 5)
> 1 = "math"        (math 0..9 : 95, else : 40)
> 2 = "logic"       (logic 10..19 : 95, else : 40)
> 3 = "music"       (music 20..29 : 95, else : 40)
> 4 = "biology"     (biology 30..39: 95, else : 40)
> 5 = "systems"     (systems 40..49: 95, else : 40)
> 6 = "uniform"     (all : 60)
> 7 = "shallow"     (all : 25)

### `fn build_node_hashes(seed_id: int, profile_id: int) -> list`

> ---- build learner atlas (hash-only, deterministic) ------------------------
> visited[i] true iff mix3(seed_id, TAG_VISIT=1, i) mod 100 < threshold
> node_hash of concept i = mix3(0, TAG_NODE=2, i)

### `fn digit_char(d: int) -> string`

> ---- itoa (digit-to-string, nested else-if) --------------------------------

### `fn str_itoa(n: int) -> string`

_(no docstring)_

### `fn fold_nodes_to_theta(nodes: list, nn: int) -> int`

> ---- Kuramoto primitives (inline, byte-equivalent to v_sync_kuramoto.hexa) -

### `fn r_order_param(thetas: list, nn: int) -> int`

_(no docstring)_

### `fn v_sync_kuramoto(thetas: list, nn: int, k_x1000: int) -> int`

_(no docstring)_

### `fn run_fixture(name: string, seed_ids: list, profile_ids: list, nn: int) -> string`

> ---- per-fixture driver ----------------------------------------------------

