<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/anima_tui.hexa -->
<!-- entry_count: 50 -->

# `tool/anima_tui.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 50

## Table of contents

- `fn _str`
- `fn _exec_out`
- `fn _file_exists`
- `fn _dir_exists`
- `fn _now_utc`
- `fn _now_local_hms`
- `fn _epoch`
- `fn _epoch_ms`
- `fn _mtime`
- `fn _resolve_root`
- `fn _is_map`
- `fn _load_config_or_default`
- `fn _default_config`
- `fn _emit_default_config_if_absent`
- `fn _arg_value`
- `fn _arg_present`
- `fn _esc`
- `fn _ansi_clear`
- `fn _ansi_home`
- `fn _ansi_hide`
- `fn _ansi_show`
- `fn _ansi_alt_on`
- `fn _ansi_alt_off`
- `fn _glyph`
- `fn _verdict_to_glyph`
- `fn _bar`
- `fn _color_bar`
- `fn _pad_right`
- `fn _visible_len`
- `fn _read_true_closure`
- `fn _read_integrity`
- `fn _read_progression`
- `fn _read_debt`
- `fn _git_recent`
- `fn _active_bg`
- `fn _hr`
- `fn _title_line`
- `fn _section_progression`
- `fn _section_closure`
- `fn _section_integrity`
- `fn _section_commits`
- `fn _section_bg`
- `fn _section_sources`
- `fn _footer`
- `fn render_frame`
- `fn _mtime_signature`
- `fn _emit_heartbeat`
- `fn _teardown`
- `fn print_usage`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn _exec_out(cmd: string) -> string`

_(no docstring)_

### `fn _file_exists(path: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _dir_exists(path: string) -> bool`

_(no docstring)_

### `fn _now_utc() -> string`

_(no docstring)_

### `fn _now_local_hms() -> string`

_(no docstring)_

### `fn _epoch() -> string`

_(no docstring)_

### `fn _epoch_ms() -> int`

_(no docstring)_

### `fn _mtime(path: string) -> string`

_(no docstring)_

### `fn _resolve_root() -> string`

_(no docstring)_

### `fn _is_map(v) -> bool`

_(no docstring)_

### `fn _load_config_or_default(root: string)`

_(no docstring)_

### `fn _default_config()`

> Fallback config (used when config/anima_tui_config.json missing).
> raw#15 still honoured — this is a *bootstrap* default; the authoritative
> copy lives in the SSOT JSON file which is created on first run.

### `fn _emit_default_config_if_absent(root: string)`

_(no docstring)_

### `fn _arg_value(argv, key: string, dflt: string) -> string`

_(no docstring)_

### `fn _arg_present(argv, key: string) -> bool`

_(no docstring)_

### `fn _esc() -> string`

_(no docstring)_

### `fn _ansi_clear() -> string`

_(no docstring)_

### `fn _ansi_home() -> string`

_(no docstring)_

### `fn _ansi_hide() -> string`

_(no docstring)_

### `fn _ansi_show() -> string`

_(no docstring)_

### `fn _ansi_alt_on() -> string`

_(no docstring)_

### `fn _ansi_alt_off() -> string`

_(no docstring)_

### `fn _glyph(cfg, name: string) -> string`

_(no docstring)_

### `fn _verdict_to_glyph(cfg, verdict: string) -> string`

_(no docstring)_

### `fn _bar(pct: int, width: int) -> string`

_(no docstring)_

### `fn _color_bar(cfg, pct: int, width: int) -> string`

_(no docstring)_

### `fn _pad_right(s: string, width: int) -> string`

> Strip ANSI escape sequences for width calculation (rough: just ignore ESC[...m).

### `fn _visible_len(s: string) -> int`

_(no docstring)_

### `fn _read_true_closure(root: string)`

_(no docstring)_

### `fn _read_integrity(root: string)`

_(no docstring)_

### `fn _read_progression(root: string)`

_(no docstring)_

### `fn _read_debt(root: string) -> int`

_(no docstring)_

### `fn _git_recent(root: string, n: int) -> array`

_(no docstring)_

### `fn _active_bg(pattern: string) -> array`

_(no docstring)_

### `fn _hr(width: int, ch: string) -> string`

_(no docstring)_

### `fn _title_line(cfg, root: string, frame_idx: int, render_ms: int) -> string`

_(no docstring)_

### `fn _section_progression(cfg, data) -> string`

_(no docstring)_

### `fn _section_closure(cfg, tc, integrity, debt: int) -> string`

_(no docstring)_

### `fn _section_integrity(cfg, integrity) -> string`

_(no docstring)_

### `fn _section_commits(cfg, commits) -> string`

_(no docstring)_

### `fn _section_bg(cfg, procs) -> string`

_(no docstring)_

### `fn _section_sources(cfg, root: string, cfg_root) -> string`

_(no docstring)_

### `fn _footer(cfg, refresh_sec: int, watch_mode: bool) -> string`

_(no docstring)_

### `fn render_frame(cfg, root: string, frame_idx: int) -> string`

_(no docstring)_

### `fn _mtime_signature(root: string, sources) -> string`

_(no docstring)_

### `fn _emit_heartbeat(root: string, frame_idx: int, render_ms: int, mode: string)`

_(no docstring)_

### `fn _teardown(use_alt: bool)`

_(no docstring)_

### `fn print_usage()`

_(no docstring)_

### `fn main()`

_(no docstring)_

