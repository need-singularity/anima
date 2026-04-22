<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/cert_watch.hexa -->
<!-- entry_count: 32 -->

# `tool/cert_watch.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 32

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _file_exists`
- `fn _is_file`
- `fn _dir_exists`
- `fn _mkdir_p`
- `fn _dirname`
- `fn _ts_iso`
- `fn _ts_epoch`
- `fn _sha256_of_file`
- `fn _sha256_of_string`
- `fn _file_mtime`
- `fn _file_size`
- `fn _list_json`
- `fn _json_escape`
- `fn _load_config`
- `fn _cfg_paths`
- `fn _cfg_state_path`
- `fn _cfg_invoke`
- `fn _load_state`
- `fn _state_lookup`
- `fn _render_state`
- `fn _load_log`
- `fn _render_log`
- `fn _last_entry_sha`
- `fn _invoke_verify`
- `fn _baseline_first_run`
- `fn run_poll`
- `fn _selftest`
- `fn _usage`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _exec_code(cmd: string) -> int`

_(no docstring)_

### `fn _file_exists(path: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _is_file(path: string) -> bool`

_(no docstring)_

### `fn _dir_exists(path: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(dir: string) -> bool`

_(no docstring)_

### `fn _dirname(path: string) -> string`

_(no docstring)_

### `fn _ts_iso() -> string`

> INLINE_DEPRECATED[H42]: see shared/util/ts_iso.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _ts_epoch() -> string`

_(no docstring)_

### `fn _sha256_of_file(path: string) -> string`

_(no docstring)_

### `fn _sha256_of_string(s: string) -> string`

_(no docstring)_

### `fn _file_mtime(path: string) -> string`

> Portable mtime (seconds since epoch). Try BSD stat, fall back to GNU stat.

### `fn _file_size(path: string) -> string`

> Portable size in bytes.

### `fn _list_json(dir: string) -> array`

> List *.json regular files directly under `dir` (non-recursive).

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _load_config(path: string)`

_(no docstring)_

### `fn _cfg_paths(cfg) -> array`

_(no docstring)_

### `fn _cfg_state_path(cfg, key: string, dflt: string) -> string`

_(no docstring)_

### `fn _cfg_invoke(cfg)`

> First invoke_chain entry (single supported chain step).

### `fn _load_state(path: string)`

_(no docstring)_

### `fn _state_lookup(state, path: string)`

> Map-style lookup by path through entries array (no native dict for
> loaded state so we scan). Returns entry or empty dict.

### `fn _render_state(entries: array) -> string`

> Build a fresh state blob from entries array.

### `fn _load_log(path: string) -> array`

_(no docstring)_

### `fn _render_log(events: array) -> string`

_(no docstring)_

### `fn _last_entry_sha(events: array) -> string`

_(no docstring)_

### `fn _invoke_verify(invoke, path: string)`

> ─── meta2_hashchain_verify integration (present_or_mock) ────────────
> Return dict: {mode: "present"|"mock"|"skip", exit: N}

### `fn _baseline_first_run(prior_state) -> bool`

_(no docstring)_

### `fn run_poll(cfg_path: string) -> int`

_(no docstring)_

### `fn _selftest() -> int`

_(no docstring)_

### `fn _usage()`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

