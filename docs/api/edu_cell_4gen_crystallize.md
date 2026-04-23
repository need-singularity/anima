<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/edu_cell_4gen_crystallize.hexa -->
<!-- entry_count: 41 -->

# `tool/edu_cell_4gen_crystallize.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 41

## Table of contents

- `fn ccode_edu4`
- `fn hash_proj`
- `fn judge`
- `fn digit_val`
- `fn parse_int`
- `fn make_cell`
- `fn split5`
- `fn cell_a`
- `fn cell_b`
- `fn cell_t`
- `fn cell_g`
- `fn cell_s`
- `fn rebuild`
- `fn cell_set_t`
- `fn cell_set_s`
- `fn clamp_int`
- `fn fixpoint_seal`
- `fn fixpoint_seal_tl`
- `fn tension_step`
- `fn make_cell_tl`
- `fn make_lattice_tl`
- `fn lattice_idx`
- `fn iabs`
- `fn sign_of`
- `fn attraction_at`
- `fn lattice_step`
- `fn count_sealed`
- `fn count_active`
- `fn count_drop`
- `fn gen_signature`
- `fn gen_size`
- `fn gen_tl_boost`
- `fn gen_ticks`
- `struct GenResult`
- `fn run_gen`
- `fn distill_eff_x1000`
- `fn cumulative_distill_x1000`
- `fn phase_jump_verdict`
- `fn emit_gen_cert`
- `fn emit_report`
- `fn main`

## Entries

### `fn ccode_edu4(c: string) -> int`

_(no docstring)_

### `fn hash_proj(s: string) -> int`

_(no docstring)_

### `fn judge(seed: string, step: int) -> string`

_(no docstring)_

### `fn digit_val(c: string) -> int`

_(no docstring)_

### `fn parse_int(s: string) -> int`

_(no docstring)_

### `fn make_cell(a_id: string, b_id: string, t0: int, seed: int) -> string`

_(no docstring)_

### `fn split5(cell: string) -> [string]`

_(no docstring)_

### `fn cell_a(c: string) -> string`

_(no docstring)_

### `fn cell_b(c: string) -> string`

_(no docstring)_

### `fn cell_t(c: string) -> int`

_(no docstring)_

### `fn cell_g(c: string) -> int`

_(no docstring)_

### `fn cell_s(c: string) -> string`

_(no docstring)_

### `fn rebuild(a: string, b: string, t: int, g: int, s: string) -> string`

_(no docstring)_

### `fn cell_set_t(c: string, t_new: int) -> string`

_(no docstring)_

### `fn cell_set_s(c: string, s_new: string) -> string`

_(no docstring)_

### `fn clamp_int(v: int, lo: int, hi: int) -> int`

_(no docstring)_

### `fn fixpoint_seal(cell: string) -> bool`

_(no docstring)_

### `fn fixpoint_seal_tl(cell: string, tl_boost_x1000: int, tick: int) -> bool`

> TL-boosted seal: fixpoint closure becomes easier as TL distill shrinks
> the effective search space (parent's sealed pool guides offspring basins).
> Model: seal iff hash(cell_sig) mod seal_divisor == 0, where
> seal_divisor = 100 - tl_boost_per_mille/11   (monotone: tl=0→100; tl=800→27; tl=1000→9)
> This encodes the pre-registered prediction that 4-gen (tl=800‰)
> sits above the phase-jump knee where per-cell seal probability surges.

### `fn tension_step(cell: string, attraction: int, upper: int, lower: int, tl_boost_x1000: int, tick: int) -> string`

_(no docstring)_

### `fn make_cell_tl(a_id: string, b_id: string, t0: int, seed: int, tl_boost_x1000: int) -> string`

> TL-boosted cell maker: distilled from parent generation's sealed pool.
> The TL kicker narrows the per-cell gap, biasing toward seal (lower tension).
> Stronger negative bias so t_new can actually drop below LOWER within a few ticks.

### `fn make_lattice_tl(size: int, tension0: int, seed: int, tl_boost_x1000: int) -> [string]`

_(no docstring)_

### `fn lattice_idx(size: int, r: int, c: int) -> int`

_(no docstring)_

### `fn iabs(x: int) -> int`

_(no docstring)_

### `fn sign_of(x: int) -> int`

_(no docstring)_

### `fn attraction_at(lattice: [string], size: int, r: int, c: int,`

_(no docstring)_

### `fn lattice_step(lattice: [string], size: int, upper: int, lower: int,`

_(no docstring)_

### `fn count_sealed(lattice: [string]) -> int`

_(no docstring)_

### `fn count_active(lattice: [string]) -> int`

_(no docstring)_

### `fn count_drop(lattice: [string]) -> int`

_(no docstring)_

### `fn gen_signature(lattice: [string]) -> int`

> Signature of a generation: concatenated hash of all sealed cells' (a_id,b_id,g).
> Used as TL seed for next gen.

### `fn gen_size(gen_idx: int) -> int`

> Per-gen lattice sizes (crystallize compression: 6→5→4→3).
> param_count decreases; if score rises faster than param-ratio,
> distill_eff > 1.0 = phase-jump signature.

### `fn gen_tl_boost(gen_idx: int) -> int`

> Per-gen TL boost (distilled from parent's sealed pool).  Gen 1 = untrained.

### `fn gen_ticks(gen_idx: int) -> int`

_(no docstring)_

### `struct GenResult`

_(no docstring)_

### `fn run_gen(gen_idx: int, parent_sig: int) -> GenResult`

_(no docstring)_

### `fn distill_eff_x1000(score_k: int, score_prev: int, params_k: int, params_prev: int) -> int`

> distill_eff_{k} = (score_k / score_{k-1}) / (params_k / params_{k-1})
> emitted as x1000 per-mille (integer).

### `fn cumulative_distill_x1000(score_last: int, score_first: int, params_last: int, params_first: int) -> int`

> Cumulative distill eff = (score_4 / score_1) / (params_4 / params_1)

### `fn phase_jump_verdict(d2: int, d3: int, d4: int, score1: int, score2: int, score3: int, score4: int) -> string`

> Phase-jump detector:
> Score-based test: did gen 4 saturate (score_per_mille >= 900)
> while gens 1-3 trend was sub-saturation?
> distill_eff deviation: does d4 deviate > 15% from linear (d2,d3 slope) extrapolation?
> VERIFIED iff EITHER
> (a) gen 4 score saturates AND gen 1-3 scores were sub-saturation    [ceiling jump]
> (b) d4 super-linear (> 1.15× expected_linear)                        [super-jump]
> FAILED if neither condition triggers.

### `fn emit_gen_cert(path: string, r: GenResult)`

_(no docstring)_

### `fn emit_report(path: string, gens: [GenResult], d2: int, d3: int, d4: int, cum: int, verdict: string, total_sig: int)`

_(no docstring)_

### `fn main()`

_(no docstring)_

