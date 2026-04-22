<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/cert_gate.hexa -->
<!-- entry_count: 32 -->

# `tool/cert_gate.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 32

## Table of contents

- `fn fexists`
- `fn dexists`
- `fn now_utc`
- `fn bool_s`
- `fn clamp`
- `fn sha256_file`
- `fn alignment_bias_factor`
- `fn json_str_field`
- `fn json_bool_field_first`
- `fn verdict_base_score`
- `struct CertScore`
- `fn load_cert`
- `fn load_state`
- `struct FactorResult`
- `fn compute_an11`
- `fn compute_hexad`
- `fn compute_mk8`
- `fn compute_aux`
- `struct GateResult`
- `fn compute_reward`
- `fn detail_json`
- `fn write_result`
- `struct LoadedCerts`
- `fn load_all_certs`
- `fn run_pipeline`
- `fn count_present_state_entries`
- `fn selftest`
- `fn dry_run`
- `fn arg_present`
- `fn arg_value`
- `fn print_usage`
- `fn main`

## Entries

### `fn fexists(p: string) -> bool`

_(no docstring)_

### `fn dexists(p: string) -> bool`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn bool_s(b: bool) -> string`

_(no docstring)_

### `fn clamp(x: float, lo: float, hi: float) -> float`

_(no docstring)_

### `fn sha256_file(path: string) -> string`

_(no docstring)_

### `fn alignment_bias_factor(state_dir: string) -> float`

> Read state/alignment_feature_label.json (roadmap #66) and compute the
> distribution-weighted label bias: Σ(count[L] * weight[L]) / 16. Returns
> 1.0 when the SSOT is absent (no-op — legacy reward_mult preserved).

### `fn json_str_field(body: string, key: string) -> string`

> Find the LAST `"<key>": "<value>"` at top level.
> Cert bodies embed {"type":"verdict","value":"..."} in evidence arrays;
> the outermost top-level "verdict": "<X>" always trails, so last wins.

### `fn json_bool_field_first(body: string, key: string) -> int`

> Extract the FIRST `"<key>": <bool>` (true/false) — useful for nested
> pass fields that appear once in stable positions.

### `fn verdict_base_score(v: string) -> float`

> Map a verdict string → base sat score.

### `struct CertScore`

_(no docstring)_

### `fn load_cert(slug: string) -> CertScore`

_(no docstring)_

### `fn load_state(fname: string) -> CertScore`

_(no docstring)_

### `struct FactorResult`

_(no docstring)_

### `fn compute_an11(cert_an11c: CertScore) -> FactorResult`

_(no docstring)_

### `fn compute_hexad(cert_hexad: CertScore) -> FactorResult`

_(no docstring)_

### `fn compute_mk8(cert_stationary: CertScore, cert_7axis: CertScore, cert_eigen: CertScore) -> FactorResult`

_(no docstring)_

### `fn compute_aux(bonus_certs: list) -> FactorResult`

_(no docstring)_

### `struct GateResult`

_(no docstring)_

### `fn compute_reward(an11: FactorResult, hexad: FactorResult, mk8: FactorResult, aux: FactorResult,`

_(no docstring)_

### `fn detail_json(fr: FactorResult) -> string`

_(no docstring)_

### `fn write_result(out_path: string, mode: string, target: string, gate: GateResult,`

_(no docstring)_

### `struct LoadedCerts`

_(no docstring)_

### `fn load_all_certs() -> LoadedCerts`

_(no docstring)_

### `fn run_pipeline() -> GateResult`

_(no docstring)_

### `fn count_present_state_entries(fr: FactorResult) -> int`

> Count entries in a FactorResult whose slug ends with ".json" (i.e. state
> file entries — cert entries use the slug-only form without extension).

### `fn selftest(out_path: string, verbose: bool) -> bool`

_(no docstring)_

### `fn dry_run(out_path: string, target: string, verbose: bool) -> bool`

_(no docstring)_

### `fn arg_present(argv: list, key: string) -> bool`

_(no docstring)_

### `fn arg_value(argv: list, key: string, dflt: string) -> string`

_(no docstring)_

### `fn print_usage()`

_(no docstring)_

### `fn main()`

_(no docstring)_

