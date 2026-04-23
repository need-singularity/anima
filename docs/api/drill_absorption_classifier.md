<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/drill_absorption_classifier.hexa -->
<!-- entry_count: 10 -->

# `tool/drill_absorption_classifier.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** � η absorption / saturation classifier

**Public/Internal entries:** 10

## Table of contents

- `fn jget_str`
- `fn jget_bool`
- `fn jget_str_array`
- `fn read_iters`
- `fn list_contains_str`
- `fn overlap_ratio`
- `fn classify_state`
- `fn unique_tail_count`
- `fn compute_confidence`
- `fn run`

## Entries

### `fn jget_str(obj, key)`

_(no docstring)_

### `fn jget_bool(obj, key)`

_(no docstring)_

### `fn jget_str_array(obj, key)`

> Extract JSON string array: "primitives":["p1","p2","p3"] → preallocated list
> Returns (arr, n) via out slots; here we return a [items..., "", ...] pair.

### `fn read_iters(path)`

_(no docstring)_

### `fn list_contains_str(xs, xn, v)`

_(no docstring)_

### `fn overlap_ratio(seed_prims, sn, tail_prims, tn)`

_(no docstring)_

### `fn classify_state(hashes, n, k_window)`

_(no docstring)_

### `fn unique_tail_count(hashes, n, k_window)`

> unique-tail count over last (k_window + 1) hashes

### `fn compute_confidence(uniq, k_window, overlap)`

> confidence = stability_factor * primitive_overlap
> fixpoint + full overlap → ~1.00
> fixpoint + half overlap → ~0.50
> open     + any overlap  → low

### `fn run()`

_(no docstring)_

