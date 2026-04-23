<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/an11_ensemble.hexa -->
<!-- entry_count: 21 -->

# `tool/an11_ensemble.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 21

## Table of contents

- `fn _str`
- `fn _ts_iso`
- `fn _file_exists`
- `fn _bool_str`
- `fn _json_escape`
- `fn _argv`
- `fn _has_flag`
- `fn _get_val`
- `fn _read_or_empty`
- `fn _field_str`
- `fn _glob_latest`
- `fn _resolve_branch`
- `fn _load_branch`
- `fn _extract_weight`
- `fn _verdict_for_score`
- `fn _synth_branch`
- `fn _branch_obj`
- `fn _emit`
- `fn push_str_noop`
- `fn _ckpt_key`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _bool_str(b: bool) -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _argv() -> array`

_(no docstring)_

### `fn _has_flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _get_val(av: array, k: string, dflt: string) -> string`

_(no docstring)_

### `fn _read_or_empty(p: string) -> string`

_(no docstring)_

### `fn _field_str(blob: string, key: string) -> string`

_(no docstring)_

### `fn _glob_latest(pattern: string) -> string`

_(no docstring)_

### `fn _resolve_branch(branch: string) -> string`

_(no docstring)_

### `fn _load_branch(branch: string) -> array`

_(no docstring)_

### `fn _extract_weight(spec: string, key: string, dflt: float) -> float`

_(no docstring)_

### `fn _verdict_for_score(score: float) -> string`

_(no docstring)_

### `fn _synth_branch(verdict: string) -> array`

_(no docstring)_

### `fn _branch_obj(branch: string, rec: array) -> string`

_(no docstring)_

### `fn _emit(out_path: string, ts: string, dry: bool, weights: array, a_rec: array, b_rec: array, c_rec: array, weighted_score: float, ensemble_verdict: string, note: string)`

_(no docstring)_

### `fn push_str_noop(s: string) -> string`

> helper: no-op string concat (placeholder to keep emit shape consistent)

### `fn _ckpt_key(path: string) -> string`

> helper: extract ckpt key from source path basename (e.g. "alm_r0", "alm_r12", "alm_r13_an11_a_live").
> Used to detect cross-branch source mismatch — ensemble weighted score is only
> meaningful when a/b/c sources share the same training round.

### `fn main()`

_(no docstring)_

