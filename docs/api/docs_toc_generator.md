<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/docs_toc_generator.hexa -->
<!-- entry_count: 33 -->

# `tool/docs_toc_generator.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 33

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _file_exists`
- `fn _dir_exists`
- `fn _mkdir_p`
- `fn _rm_rf`
- `fn _ts_compact`
- `fn _list_md_files`
- `fn _basename`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn _is_alpha_code`
- `fn _is_digit_code`
- `fn slugify`
- `fn extract_headings`
- `fn _strip_trailing_hashes`
- `fn _render_file_block`
- `fn _md_escape`
- `fn render_toc`
- `fn _backup_if_present`
- `fn _atomic_write`
- `fn generate_toc`
- `fn _parent_of`
- `fn _mktempdir`
- `fn _hash_file`
- `fn _write_file`
- `fn _expected_s1`
- `fn _expected_s2`
- `fn _s1_write_fixtures`
- `fn run_selftest`
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

### `fn _dir_exists(path: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(dir: string) -> bool`

_(no docstring)_

### `fn _rm_rf(path: string) -> bool`

_(no docstring)_

### `fn _ts_compact() -> string`

_(no docstring)_

### `fn _list_md_files(dir: string) -> array`

> List *.md files (non-recursive) inside dir, sorted by path (LC_ALL=C).

### `fn _basename(path: string) -> string`

> Relative path = basename (docs_dir is the single root we scan).

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn _is_alpha_code(cc: int) -> bool`

> Use char_code ranges — string relational ops aren't reliable across
> the hexa toolchain for single-char strings.

### `fn _is_digit_code(cc: int) -> bool`

_(no docstring)_

### `fn slugify(s: string) -> string`

> GH slug: lowercase; keep a-z 0-9 _; spaces -> '-'; drop everything else.
> Consecutive hyphens preserved (matches GitHub).

### `fn extract_headings(body: string) -> array`

> ─── heading extraction ───────────────────────────────────────────────────
> Extract H1 / H2 only.  ATX-style headings:  ^#  <text>   or  ^##  <text>.
> We ignore setext headings (underline) and code-fence blocks.
> Returns array of heading maps: [{"level": 1|2, "text": "...", "slug": "..."}]

### `fn _strip_trailing_hashes(s: string) -> string`

_(no docstring)_

### `fn _render_file_block(rel: string, headings: array) -> string`

> Render a single file block.
> ## <rel>
> - [H1](rel#slug)
> - [H2](rel#slug)

### `fn _md_escape(s: string) -> string`

> Escape `]` and `[` in heading text for markdown link anchors.

### `fn render_toc(docs_dir: string, self_out_path: string) -> string`

> Build complete TOC body.  Empty dir -> header + empty note.

### `fn _backup_if_present(path: string) -> string`

_(no docstring)_

### `fn _atomic_write(path: string, body: string)`

_(no docstring)_

### `fn generate_toc(docs_dir: string, out_path: string) -> int`

_(no docstring)_

### `fn _parent_of(path: string) -> string`

_(no docstring)_

### `fn _mktempdir() -> string`

_(no docstring)_

### `fn _hash_file(path: string) -> string`

_(no docstring)_

### `fn _write_file(path: string, body: string)`

_(no docstring)_

### `fn _expected_s1() -> string`

_(no docstring)_

### `fn _expected_s2() -> string`

_(no docstring)_

### `fn _s1_write_fixtures(dir: string)`

_(no docstring)_

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

