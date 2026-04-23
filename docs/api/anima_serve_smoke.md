<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/anima_serve_smoke.hexa -->
<!-- entry_count: 12 -->

# `tool/anima_serve_smoke.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 12

## Table of contents

- `fn _home`
- `fn now_utc`
- `fn bool_s`
- `fn json_escape`
- `fn handler_health`
- `fn handler_an11_verify`
- `fn handler_chat_completions`
- `fn ledger_get`
- `fn ledger_has`
- `fn type_check`
- `fn verify_endpoint`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn handler_health(ts: string) -> array`

_(no docstring)_

### `fn handler_an11_verify(sample_id: string) -> array`

_(no docstring)_

### `fn handler_chat_completions(prompt: string) -> array`

_(no docstring)_

### `fn ledger_get(ledger: array, key: string) -> string`

_(no docstring)_

### `fn ledger_has(ledger: array, key: string) -> bool`

_(no docstring)_

### `fn type_check(ledger: array, key: string, want: string) -> bool`

_(no docstring)_

### `fn verify_endpoint(ledger: array, required: array) -> array`

> Verify an endpoint: for each (key, want_type) pair confirm key present +
> type match. Returns [pass_bool, checks_passed, checks_total].

### `fn main()`

_(no docstring)_

