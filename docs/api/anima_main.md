<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/anima_main.hexa -->
<!-- entry_count: 27 -->

# `tool/anima_main.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 27

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn bool_s`
- `fn fexists`
- `fn dexists`
- `fn resolve_root`
- `fn resolve_hexa_bin`
- `fn json_escape`
- `fn atomic_write`
- `fn is_json_map`
- `fn load_config`
- `fn arg_value`
- `fn arg_present`
- `fn status_glyph`
- `fn pct_bar`
- `fn args_to_cmd`
- `fn run_tool`
- `fn run_component`
- `fn run_phase`
- `fn compute_closure_pct`
- `fn status_tree`
- `fn render_active_issues_section`
- `fn render_integrity_section`
- `fn render_progression_section`
- `fn emit_result_ssot`
- `fn print_usage`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn fexists(p: string) -> bool`

_(no docstring)_

### `fn dexists(p: string) -> bool`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn resolve_hexa_bin() -> string`

_(no docstring)_

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn atomic_write(path: string, body: string)`

_(no docstring)_

### `fn is_json_map(v) -> bool`

_(no docstring)_

### `fn load_config(path: string)`

_(no docstring)_

### `fn arg_value(argv, key: string, dflt: string) -> string`

_(no docstring)_

### `fn arg_present(argv, key: string) -> bool`

_(no docstring)_

### `fn status_glyph(verdict: string) -> string`

_(no docstring)_

### `fn pct_bar(pct: int) -> string`

_(no docstring)_

### `fn args_to_cmd(args_arr) -> string`

_(no docstring)_

### `fn run_tool(bin: string, tool_rec) -> array`

_(no docstring)_

### `fn run_component(bin: string, cfg, comp_key: string) -> array`

_(no docstring)_

### `fn run_phase(bin: string, cfg, phase_key: string) -> array`

_(no docstring)_

### `fn compute_closure_pct(results) -> int`

_(no docstring)_

### `fn status_tree(cfg) -> array`

_(no docstring)_

### `fn render_active_issues_section()`

_(no docstring)_

### `fn render_integrity_section()`

_(no docstring)_

### `fn render_progression_section()`

> ─── Phase Progression (3-stage OS-level: check → plan → live adjust) ──────
> Reads 3 SSOT files (all optional — gracefully degrades):
> shared/config/phase_progression_config.json  (phase registry)
> state/true_closure_cert.json          (Stage 1 check 100%)
> state/phase_N_flow_ready.json         (Stage 2 plan 100% per phase)
> state/phase_progression_cert.json     (Stage 3 live tick result)

### `fn emit_result_ssot(out_path: string, mode: string, mode_arg: string,`

_(no docstring)_

### `fn print_usage()`

_(no docstring)_

### `fn main()`

_(no docstring)_

