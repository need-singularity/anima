<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/h100_launch_manifest_spec.hexa -->
<!-- entry_count: 31 -->

# `tool/h100_launch_manifest_spec.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 31

## Table of contents

- `fn _sh_quote`
- `fn _file_exists`
- `fn _ts_iso`
- `fn _ts_epoch`
- `fn _json_escape`
- `fn _sha256_file`
- `fn _sha256_str`
- `fn _argv`
- `fn _flag`
- `fn _json_field_str`
- `fn _mk_file`
- `fn _mk_jfield`
- `fn _mk_jfield_any`
- `fn _eval_prereq`
- `fn _stage1_prereqs`
- `fn _stage2_prereqs`
- `fn _stage3_prereqs`
- `fn _rollup`
- `fn _stage_verdict`
- `fn _is_cascade_prereq`
- `fn _cascade_blocked`
- `fn _stage1_def`
- `fn _stage2_def`
- `fn _stage3_def`
- `fn _render_prereq`
- `fn _render_prereq_list`
- `fn _render_stage_json`
- `fn run`
- `fn _last_slash`
- `fn self_test`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_iso() -> string`

> Native primitives honor SOURCE_DATE_EPOCH / HEXA_REPRODUCIBLE=1 (hexa-lang PR #23).
> Replaces previous `date -u` exec — re-emit is now byte-stable when env set.
> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_epoch() -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _sha256_file(p: string) -> string`

_(no docstring)_

### `fn _sha256_str(s: string) -> string`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av, k) -> bool`

_(no docstring)_

### `fn _json_field_str(path: string, key: string) -> string`

_(no docstring)_

### `fn _mk_file(path: string, label: string)`

_(no docstring)_

### `fn _mk_jfield(path: string, key: string, want: string, label: string)`

_(no docstring)_

### `fn _mk_jfield_any(path: string, key: string, want_csv: string, label: string)`

_(no docstring)_

### `fn _eval_prereq(p)`

_(no docstring)_

### `fn _stage1_prereqs() -> array`

_(no docstring)_

### `fn _stage2_prereqs() -> array`

_(no docstring)_

### `fn _stage3_prereqs() -> array`

_(no docstring)_

### `fn _rollup(prereq_verdicts)`

_(no docstring)_

### `fn _stage_verdict(roll, cascade_blocked: bool) -> string`

_(no docstring)_

### `fn _is_cascade_prereq(p) -> bool`

> Detect if failure is caused purely by cascade (post-previous-stage artifacts).
> We mark a prereq as cascade-live if its path contains "_live.json" or is
> phi_4path_cross_result.json.

### `fn _cascade_blocked(prereq_verdicts, prereqs) -> bool`

_(no docstring)_

### `fn _stage1_def()`

_(no docstring)_

### `fn _stage2_def()`

_(no docstring)_

### `fn _stage3_def()`

_(no docstring)_

### `fn _render_prereq(v) -> string`

_(no docstring)_

### `fn _render_prereq_list(prereq_verdicts) -> string`

_(no docstring)_

### `fn _render_stage_json(stage_num: int, def_obj, prereq_verdicts, roll, verdict: string) -> string`

_(no docstring)_

### `fn run(emit_path: string, also_print: bool) -> int`

_(no docstring)_

### `fn _last_slash(p: string) -> int`

_(no docstring)_

### `fn self_test() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

