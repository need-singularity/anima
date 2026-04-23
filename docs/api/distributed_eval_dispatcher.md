<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/distributed_eval_dispatcher.hexa -->
<!-- entry_count: 5 -->

# `tool/distributed_eval_dispatcher.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 5

## Table of contents

- `fn _home`
- `fn now_utc`
- `fn bool_s`
- `fn shard_of`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn shard_of(slug: string, n_shards: int) -> int`

> Deterministic shard assignment: stable string hash mod n_shards.
> Uses sum-of-ord (good enough for spec smoke; real impl would use sha256).

### `fn main()`

_(no docstring)_

