<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/F_lattice_cpu_proxy.hexa -->
<!-- entry_count: 35 -->

# `tool/F_lattice_cpu_proxy.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** � Mk.VII C2 L3 emergence CPU proxy (N=16)

**Public/Internal entries:** 35

## Table of contents

- `fn char_code`
- `fn hash_proj`
- `fn judge`
- `fn _str`
- `fn digit_val`
- `fn parse_int`
- `fn iabs`
- `fn sign_of`
- `fn clamp_int`
- `fn isqrt`
- `fn log2k`
- `fn make_gap`
- `fn init_lattice`
- `fn lattice_step_num`
- `fn score_ppm`
- `fn sealed_ppm`
- `fn correlation_at`
- `fn correlation_decay`
- `fn power_law_alpha`
- `fn xi_over_e`
- `fn is_monotone_nondecreasing`
- `fn reached_ceiling`
- `fn linreg`
- `fn mean_int`
- `fn var_pop`
- `fn stddev_of`
- `fn fingerprint_of`
- `fn measure_one`
- `fn bool_str`
- `fn join_int`
- `fn emit_cert`
- `fn run_one_seed`
- `fn json_field`
- `fn parse_int_array`
- `fn main`

## Entries

### `fn char_code(c: string) -> int`

_(no docstring)_

### `fn hash_proj(s: string) -> int`

_(no docstring)_

### `fn judge(seed: string, step: int) -> string`

_(no docstring)_

### `fn _str(x) -> string`

> coerce exec() return to string for .trim() consumption.

### `fn digit_val(c: string) -> int`

_(no docstring)_

### `fn parse_int(s: string) -> int`

_(no docstring)_

### `fn iabs(x: int) -> int`

_(no docstring)_

### `fn sign_of(x: int) -> int`

_(no docstring)_

### `fn clamp_int(v: int, lo: int, hi: int) -> int`

_(no docstring)_

### `fn isqrt(n: int) -> int`

_(no docstring)_

### `fn log2k(n: int) -> int`

_(no docstring)_

### `fn make_gap(a_id: string, b_id: string, seed: int) -> int`

_(no docstring)_

### `fn init_lattice(size: int, t0: int, seed: int) -> [[int]]`

_(no docstring)_

### `fn lattice_step_num(L: [[int]], size: int, upper: int, lower: int,`

_(no docstring)_

### `fn score_ppm(L: [[int]]) -> int`

_(no docstring)_

### `fn sealed_ppm(L: [[int]]) -> int`

_(no docstring)_

### `fn correlation_at(ss: [int], size: int, r_target: int) -> int`

_(no docstring)_

### `fn correlation_decay(ss: [int], size: int) -> [int]`

_(no docstring)_

### `fn power_law_alpha(cs: [int]) -> int`

_(no docstring)_

### `fn xi_over_e(cs: [int]) -> int`

_(no docstring)_

### `fn is_monotone_nondecreasing(xs: [int]) -> bool`

> ─── O1 monotone + slope + R² ───────────────────────────────────────────
> Given a ladder xs[] in ppm (0..1000), test monotone non-decreasing and
> compute linear fit slope & R².  All integer arithmetic; slope in ppm/tick,
> R² in ppm (0..1000).

### `fn reached_ceiling(xs: [int]) -> bool`

_(no docstring)_

### `fn linreg(ys: [int]) -> [int]`

> Simple linear regression on (x_i, y_i) where x_i = i (index in ladder).
> Returns [slope_ppm_per_step, r_squared_ppm].

### `fn mean_int(xs: [int]) -> int`

_(no docstring)_

### `fn var_pop(xs: [int], mean: int) -> int`

_(no docstring)_

### `fn stddev_of(xs: [int], mean: int) -> int`

_(no docstring)_

### `fn fingerprint_of(ladder: [int], ss: [int]) -> int`

> ─── reproducibility fingerprint ────────────────────────────────────────
> A compact hash of (ladder || final_ss) per seed.  Two runs of the same
> seed must produce identical fingerprints → byte-identical reproducibility.

### `fn measure_one(side: int, seed: int, ticks: int) -> [[int]]`

> Run one seed: step `TICKS` times, sampling score_ppm every SAMPLE_STEP.
> Returns pack:
> [score_ladder, [final_sealed_ppm], final_ss, C_r_decay, [alpha, xi, fp]]

### `fn bool_str(b: bool) -> string`

_(no docstring)_

### `fn join_int(xs: [int]) -> string`

_(no docstring)_

### `fn emit_cert(path: string,`

_(no docstring)_

### `fn run_one_seed(seed: int, out_path: string)`

> ─── per-seed subprocess mode ───────────────────────────────────────────
> When invoked as `hexa run tool/F_lattice_cpu_proxy.hexa seed <SEED> <OUT>`,
> runs one seed and emits a compact JSON fragment to <OUT>.  Used by the
> main dispatcher to run seeds in separate processes (stage0 RSS budget).

### `fn json_field(src: string, key: string) -> string`

> Parse a field from a simple single-line JSON object. Returns "" if missing.
> Input like `{"seed":42,"ladder":[0,0,1],"alpha_x1000":500,...}`.
> Field must be "key":<value> where <value> ends at `,` or `}`.

### `fn parse_int_array(s: string) -> [int]`

_(no docstring)_

### `fn main()`

_(no docstring)_

