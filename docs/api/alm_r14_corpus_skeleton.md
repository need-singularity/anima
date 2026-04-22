<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/alm_r14_corpus_skeleton.hexa -->
<!-- entry_count: 16 -->

# `tool/alm_r14_corpus_skeleton.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 16

## Table of contents

- `fn _str`
- `fn fexists`
- `fn dexists`
- `fn ensure_dir`
- `fn now_utc`
- `fn atomic_write`
- `fn sample_pairs`
- `fn write_skeleton`
- `fn count_lines`
- `fn count_substr`
- `fn count_ascii_proxy`
- `fn ko_byte_ratio`
- `fn ko_half_text`
- `fn en_half_text`
- `fn selftest`
- `fn main`

## Entries

### `fn _str(x)`

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

### `fn sample_pairs()`

_(no docstring)_

### `fn write_skeleton()`

_(no docstring)_

### `fn count_lines(p)`

_(no docstring)_

### `fn count_substr(s, needle)`

> count occurrences of a substring (non-overlapping)

### `fn count_ascii_proxy(s)`

> approximate korean byte ratio: byte_len / nonwhitespace_byte_len (Hangul is
> 3 bytes UTF-8, ASCII is 1; ratio ≥ 0.30 by char would map to high byte
> share). We approximate via (n - ascii_proxy) / n on the KO half only.

### `fn ko_byte_ratio(s)`

_(no docstring)_

### `fn ko_half_text()`

> extract _ko text per line concat

### `fn en_half_text()`

_(no docstring)_

### `fn selftest()`

_(no docstring)_

### `fn main()`

_(no docstring)_

