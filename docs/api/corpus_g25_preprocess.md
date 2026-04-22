<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/corpus_g25_preprocess.hexa -->
<!-- entry_count: 22 -->

# `tool/corpus_g25_preprocess.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** � ALM r13 seed corpus G2+G5 repair

**Public/Internal entries:** 22

## Table of contents

- `fn arg_value`
- `fn arg_present`
- `fn fexists`
- `fn dexists`
- `fn now_stamp`
- `fn sha256_of_file`
- `fn atomic_write`
- `fn byte_at`
- `fn is_ascii_terminator_byte`
- `fn is_utf8_terminator_at`
- `fn last_terminator_end`
- `fn json_escape`
- `fn find_json_str_end`
- `fn extract_json_str`
- `fn replace_response_field_raw`
- `fn is_json_map`
- `fn load_config`
- `fn lcg_next`
- `fn cat_index`
- `fn process`
- `fn print_usage`
- `fn main`

## Entries

### `fn arg_value(argv, key, dflt)`

_(no docstring)_

### `fn arg_present(argv, key)`

_(no docstring)_

### `fn fexists(p)`

_(no docstring)_

### `fn dexists(p)`

_(no docstring)_

### `fn now_stamp()`

_(no docstring)_

### `fn sha256_of_file(p)`

_(no docstring)_

### `fn atomic_write(path, body)`

> atomic write: write to tmp then mv (raw#25 concurrent-git-lock safe)

### `fn byte_at(s, i)`

_(no docstring)_

### `fn is_ascii_terminator_byte(c)`

_(no docstring)_

### `fn is_utf8_terminator_at(s, end_excl)`

_(no docstring)_

### `fn last_terminator_end(s)`

> Scan from tail; return exclusive end offset of last terminator (or -1)

### `fn json_escape(s)`

_(no docstring)_

### `fn find_json_str_end(line, start)`

> Find end offset of JSON string value: scans forward from `start` and
> returns the index of the CLOSING unescaped double-quote.  Backslash
> escapes (\" \\ \n \r \t etc) are skipped over by advancing 2.

### `fn extract_json_str(line, key)`

> Extract value of a top-level string field "key":"value" from a single
> line of JSONL.  Returns the RAW (still-escaped) substring between the
> quotes (caller only needs this for terminator scan + passthrough).
> For exact field-name-boundary safety we require the needle to appear
> at the start of a key (preceded by `{` or `,`).

### `fn replace_response_field_raw(line, raw_resp_escaped)`

> Replace "response":"..." value with new RAW (already-JSON-escaped)
> substring.  Caller MUST pass a substring of the original escaped
> response (extract_json_str returns such a substring unchanged), so no
> re-escape is performed here.

### `fn is_json_map(v)`

_(no docstring)_

### `fn load_config(path)`

_(no docstring)_

### `fn lcg_next(state)`

_(no docstring)_

### `fn cat_index(cat)`

_(no docstring)_

### `fn process(input_path, output_path, report_path, cfg, seed_i)`

_(no docstring)_

### `fn print_usage()`

_(no docstring)_

### `fn main()`

_(no docstring)_

