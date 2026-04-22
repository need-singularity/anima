<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/auto_changelog.hexa -->
<!-- entry_count: 25 -->

# `tool/auto_changelog.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 25

## Table of contents

- `fn _sh_quote`
- `fn _exec_out`
- `fn _exec_code`
- `fn _ts_iso`
- `fn _date_only`
- `fn _bool_s`
- `fn _file_exists`
- `fn _is_file`
- `fn _mkdir_p`
- `fn _json_escape`
- `fn flag_present`
- `fn _git_head_sha`
- `fn _git_head_short`
- `fn _git_last_semver_tag`
- `fn _git_log_commits`
- `fn classify_commit`
- `fn load_last_run`
- `fn write_last_run`
- `fn render_section`
- `fn group_by_type`
- `fn create_initial_changelog`
- `fn prepend_section`
- `fn count_lines`
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

### `fn _date_only() -> string`

_(no docstring)_

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

### `fn flag_present(name: string) -> bool`

_(no docstring)_

### `fn _git_head_sha() -> string`

_(no docstring)_

### `fn _git_head_short() -> string`

_(no docstring)_

### `fn _git_last_semver_tag() -> string`

_(no docstring)_

### `fn _git_log_commits(since: string) -> array`

> `git log <since>..HEAD --pretty=%H|%s|%aI`. Returns array of commit dicts.
> `since` may be empty → fall back to "-n 50" mode for the very first run.

### `fn classify_commit(subject: string) -> string`

_(no docstring)_

### `fn load_last_run()`

_(no docstring)_

### `fn write_last_run(sha: string, ts: string, sections_n: int)`

_(no docstring)_

### `fn render_section(short: string, date: string, by_type) -> string`

_(no docstring)_

### `fn group_by_type(commits: array)`

_(no docstring)_

### `fn create_initial_changelog(new_section: string)`

_(no docstring)_

### `fn prepend_section(new_section: string)`

> Prepend new section into existing changelog, after the header block.
> If the header block isn't found, inject one.

### `fn count_lines(s: string) -> int`

_(no docstring)_

### `fn run_selftest() -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

