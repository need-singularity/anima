<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/drill_ext_resolve.hexa -->
<!-- entry_count: 6 -->

# `tool/drill_ext_resolve.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** � raw#14 .ext SSOT resolver helper

**Public/Internal entries:** 6

## Table of contents

- `fn str_index_of`
- `fn str_contains`
- `fn extract_nested_string`
- `fn expand_home`
- `fn resolve_ref`
- `fn main`

## Entries

### `fn str_index_of(hay, needle, from)`

_(no docstring)_

### `fn str_contains(s, sub)`

_(no docstring)_

### `fn extract_nested_string(text, outer_key, inner_key)`

> Extract the first JSON string value following a "<key>" occurrence whose
> enclosing "<object_key>" block also appears. We just search forward from
> the object key for the target key, skipping nested braces.

### `fn expand_home(path)`

> ~ → $HOME expansion (stage0 has env()).

### `fn resolve_ref(ref_name)`

_(no docstring)_

### `fn main()`

_(no docstring)_

