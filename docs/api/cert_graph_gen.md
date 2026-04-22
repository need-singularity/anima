<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/cert_graph_gen.hexa -->
<!-- entry_count: 28 -->

# `tool/cert_graph_gen.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 28

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _file_exists`
- `fn _dir_exists`
- `fn _mkdir_p`
- `fn _rm_rf`
- `fn _utc_now`
- `fn _basename`
- `fn _parent_of`
- `fn _list_jsons`
- `fn slug_norm`
- `fn json_string_array`
- `fn json_string_field`
- `struct Edge`
- `fn _sort_strings`
- `fn build`
- `fn render_md`
- `fn _json_escape`
- `fn render_json`
- `fn _atomic_write`
- `fn do_generate`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn _hash_no_ts`
- `fn run_selftest`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _exec_code(cmd: string) -> int`

_(no docstring)_

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _dir_exists(p: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(p: string) -> bool`

_(no docstring)_

### `fn _rm_rf(p: string) -> bool`

_(no docstring)_

### `fn _utc_now() -> string`

_(no docstring)_

### `fn _basename(path: string) -> string`

_(no docstring)_

### `fn _parent_of(path: string) -> string`

_(no docstring)_

### `fn _list_jsons(dir: string) -> array`

_(no docstring)_

### `fn slug_norm(s: string) -> string`

> ─── slug normalization ──────────────────────────────────────────────────
> Lowercase + underscores → hyphens. "UNIVERSAL_CONSTANT_4" →
> "universal-constant-4" matches the on-disk slug. Pure-numeric IDs (e.g.
> "22" from depends_on) pass through unchanged with a "rm#" prefix marking
> them as roadmap-id refs.

### `fn json_string_array(body: string, key: string) -> array`

> ─── minimal JSON array-of-string extractor ──────────────────────────────
> Locate `"<key>"` then the next `[ ... ]` and split string elements.
> Tolerates whitespace and nested objects (we count depth on `[]` and `{}`).

### `fn json_string_field(body: string, key: string) -> string`

_(no docstring)_

### `struct Edge`

_(no docstring)_

### `fn _sort_strings(a: array) -> array`

_(no docstring)_

### `fn build(cert_dir: string) -> any`

_(no docstring)_

### `fn render_md(g: any, cert_dir: string, ts: string) -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn render_json(g: any, cert_dir: string, ts: string) -> string`

_(no docstring)_

### `fn _atomic_write(path: string, body: string)`

_(no docstring)_

### `fn do_generate(cert_dir: string, md_out: string, json_out: string) -> int`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn _hash_no_ts(path: string) -> string`

_(no docstring)_

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

