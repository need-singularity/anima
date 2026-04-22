<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/cert_incremental_verify.hexa -->
<!-- entry_count: 23 -->

# `tool/cert_incremental_verify.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 23

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _ts_iso`
- `fn _bool_s`
- `fn _file_exists`
- `fn _is_file`
- `fn _mkdir_p`
- `fn _json_escape`
- `fn _sha256_of_file`
- `fn _git_head_sha`
- `fn _git_diff_names`
- `fn flag_present`
- `fn load_last_run`
- `fn write_last_run`
- `fn append_log_event`
- `fn load_dag`
- `fn _path_in_set`
- `fn select_direct_slugs`
- `fn expand_dependents`
- `fn verify_cert`
- `fn run_selftest`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _exec_code(cmd: string) -> int`

_(no docstring)_

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _bool_s(b: bool) -> string`

_(no docstring)_

### `fn _file_exists(path: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _is_file(path: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(d: string) -> bool`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _sha256_of_file(path: string) -> string`

_(no docstring)_

### `fn _git_head_sha() -> string`

_(no docstring)_

### `fn _git_diff_names(from_sha: string, to_sha: string) -> array`

_(no docstring)_

### `fn flag_present(name: string) -> bool`

_(no docstring)_

### `fn load_last_run()`

_(no docstring)_

### `fn write_last_run(epoch_sha: string, ts: string, slugs: array)`

_(no docstring)_

### `fn append_log_event(ev_dict)`

_(no docstring)_

### `fn load_dag()`

_(no docstring)_

### `fn _path_in_set(path: string, set: array) -> bool`

_(no docstring)_

### `fn select_direct_slugs(dag, changed_files: array) -> array`

> Return list of slugs whose source_path matches (substring or suffix-match)
> any of the changed-files set. We use endswith comparison because cert_dag
> stores absolute paths whereas git diff yields repo-relative paths.

### `fn expand_dependents(dag, seed_slugs: array) -> array`

> Transitive closure: any cert that depends on a needs_reverify cert via
> edges (src → dst) inherits the reverify mark. Iterate to fixpoint.

### `fn verify_cert(node) -> string`

_(no docstring)_

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

