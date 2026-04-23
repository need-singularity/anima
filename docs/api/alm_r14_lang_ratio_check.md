<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/alm_r14_lang_ratio_check.hexa -->
<!-- entry_count: 23 -->

# `tool/alm_r14_lang_ratio_check.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 23

## Table of contents

- `fn _str`
- `fn _sh_quote`
- `fn fexists`
- `fn dexists`
- `fn ensure_dir`
- `fn now_utc`
- `fn atomic_write`
- `fn json_escape`
- `fn bytes_file`
- `fn non_ascii_bytes`
- `fn non_ascii_bytes_str`
- `fn total_bytes_str`
- `fn ws_bytes`
- `fn count_lines`
- `fn ko_half_concat`
- `fn en_half_concat`
- `fn char_equiv_ratio`
- `fn raw_byte_ratio`
- `fn audit_full`
- `fn audit_string`
- `fn emit_audit`
- `fn selftest`
- `fn main`

## Entries

### `fn _str(x)`

_(no docstring)_

### `fn _sh_quote(s)`

_(no docstring)_

### `fn fexists(p)`

_(no docstring)_

### `fn dexists(p)`

_(no docstring)_

### `fn ensure_dir(d)`

_(no docstring)_

### `fn now_utc()`

_(no docstring)_

### `fn atomic_write(path, body)`

_(no docstring)_

### `fn json_escape(s)`

_(no docstring)_

### `fn bytes_file(p)`

> byte count of file (wc -c)

### `fn non_ascii_bytes(p)`

> non-ASCII byte count via LC_ALL=C grep -c '[\x80-\xFF]' — counts LINES with
> any high byte, which is insufficient. Instead use `tr -d '[:ascii:]' | wc -c`.
> Since on macOS [:ascii:] in tr is locale-dependent, we substitute the
> canonical "strip 0x00-0x7F" range explicitly via LC_ALL=C.

### `fn non_ascii_bytes_str(s)`

> non-ASCII byte count on a string written to stdin via printf

### `fn total_bytes_str(s)`

_(no docstring)_

### `fn ws_bytes(p)`

> whitespace byte count (spaces, tabs, newlines, CR)

### `fn count_lines(p)`

> count lines in file (non-empty)

### `fn ko_half_concat(p)`

_(no docstring)_

### `fn en_half_concat(p)`

_(no docstring)_

### `fn char_equiv_ratio(non_ascii_b, ascii_non_ws_b)`

> char-equivalent Korean ratio from byte counts

### `fn raw_byte_ratio(non_ascii_b, non_ws_b)`

> raw byte ratio (not char-calibrated)

### `fn audit_full(p)`

_(no docstring)_

### `fn audit_string(s)`

_(no docstring)_

### `fn emit_audit(lines_n, full_a, ko_a, en_a)`

_(no docstring)_

### `fn selftest(lines_n, full_a, ko_a)`

_(no docstring)_

### `fn main()`

_(no docstring)_

