<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/h100_post_launch_cascade.hexa -->
<!-- entry_count: 19 -->

# `tool/h100_post_launch_cascade.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 19

## Table of contents

- `fn _sh_quote`
- `fn _file_exists`
- `fn _ts_iso`
- `fn _ts_epoch`
- `fn _json_escape`
- `fn _bool_str`
- `fn _argv`
- `fn _flag`
- `fn _last_slash`
- `fn _read_verdict_field`
- `fn _read_stage2_pods`
- `fn _read_stage3_kickoff`
- `fn _decide_action`
- `fn _render_pods_array`
- `fn _render_runbook`
- `fn _render_proposal`
- `fn run`
- `fn self_test`
- `fn main`

## Entries

### `fn _sh_quote(s: string) -> string`

_(no docstring)_

### `fn _file_exists(p: string) -> bool`

_(no docstring)_

### `fn _ts_iso() -> string`

_(no docstring)_

### `fn _ts_epoch() -> string`

_(no docstring)_

### `fn _json_escape(s: string) -> string`

_(no docstring)_

### `fn _bool_str(b: bool) -> string`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av, k) -> bool`

_(no docstring)_

### `fn _last_slash(p: string) -> int`

_(no docstring)_

### `fn _read_verdict_field(key: string) -> string`

_(no docstring)_

### `fn _read_stage2_pods() -> array`

_(no docstring)_

### `fn _read_stage3_kickoff() -> string`

_(no docstring)_

### `fn _decide_action(overall: string) -> string`

_(no docstring)_

### `fn _render_pods_array(pods: array) -> string`

_(no docstring)_

### `fn _render_runbook(action: string, pods: array, stage3: string) -> string`

_(no docstring)_

### `fn _render_proposal(verdict: string, action: string, pods: array, stage3: string, ts: string) -> string`

_(no docstring)_

### `fn run(emit_path: string, also_print: bool) -> int`

_(no docstring)_

### `fn self_test() -> int`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

