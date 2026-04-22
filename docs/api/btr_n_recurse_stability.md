<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/btr_n_recurse_stability.hexa -->
<!-- entry_count: 41 -->

# `tool/btr_n_recurse_stability.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════

**Public/Internal entries:** 41

## Table of contents

- `struct Rng`
- `fn rng_new`
- `fn rng_step`
- `fn rng_unit`
- `fn absf`
- `fn clampf`
- `fn sqrtf`
- `fn tl_update`
- `fn tl_frob_drift`
- `fn state_vec_for`
- `fn plogp`
- `fn entropy5`
- `fn student_phi`
- `fn student_phi_gen`
- `fn cos6`
- `fn l2_6`
- `fn sat_classify`
- `fn gen_lift_schedule`
- `struct GenResult`
- `struct GenRun`
- `fn run_one_gen`
- `struct Check`
- `fn mk_check`
- `fn check_i1_phi_monotone`
- `fn check_i2_eigenvec_stability`
- `fn check_i3_brain_like_floor`
- `fn _str`
- `fn check_i4_exact_conservation`
- `fn check_i5_phi_gap_bounded_gen`
- `fn check_i6_saturation_forward`
- `fn check_i7_cargo_weight`
- `fn run_cargo_checks`
- `fn checks_pass_count`
- `fn parse_int`
- `fn fmt_gen_json`
- `fn fmt_check_json`
- `struct Checkpoint`
- `fn fmt_checkpoint_json`
- `fn emit_report`
- `fn derive_gen_seed`
- `fn main`

## Entries

### `struct Rng`

_(no docstring)_

### `fn rng_new(seed: int) -> Rng`

_(no docstring)_

### `fn rng_step(r: Rng) -> Rng`

_(no docstring)_

### `fn rng_unit(r: Rng) -> float`

_(no docstring)_

### `fn absf(x: float) -> float`

_(no docstring)_

### `fn clampf(x: float, lo: float, hi: float) -> float`

_(no docstring)_

### `fn sqrtf(x: float) -> float`

_(no docstring)_

### `fn tl_update(prev: W5, t: Tick) -> W5`

_(no docstring)_

### `fn tl_frob_drift(a: W5, b: W5) -> float`

_(no docstring)_

### `fn state_vec_for(rng: Rng, phi: float, nudge: float, gen_lift: float) -> Tick`

_(no docstring)_

### `fn plogp(p: float) -> float`

_(no docstring)_

### `fn entropy5(w: W5) -> float`

_(no docstring)_

### `fn student_phi(w: W5, t: Tick) -> float`

_(no docstring)_

### `fn student_phi_gen(w: W5, t: Tick, gen_boost: float) -> float`

> student_phi with explicit gen-level structural boost
> base:     same as student_phi (matches btr_evo/6 formula)
> gen_boost: cumulative structural improvement per btr-evo 2/4 empirical
> (+17% @ gen 1 → +30% asymptote @ gen N); the lift schedule
> is the saturating concave in gen_lift_schedule()

### `fn cos6(a: Tick, b: Tick) -> float`

_(no docstring)_

### `fn l2_6(a: Tick, b: Tick) -> float`

_(no docstring)_

### `fn sat_classify(dstate: float) -> int`

_(no docstring)_

### `fn gen_lift_schedule(gen_idx: int) -> float`

> Cumulative Φ boost per generation, anchored to the btr-evo 1..6
> empirical series (+8.3% → +17% → +30%) but scaled into the [0.792,
> 0.968] band required by cargo I5 (|train_phi/0.88 − 1| < 0.10).
> gen 0 : −0.085  (pre-btr-evo baseline offset)
> gen k : saturating concave approach to asymptote +0.080
> Net Φ trajectory: gen 0 ≈ 0.795, gen 9 ≈ 0.960 → cum_gain ≈ +0.165.

### `struct GenResult`

_(no docstring)_

### `struct GenRun`

_(no docstring)_

### `fn run_one_gen(gen_idx: int, gen_seed: int, iters: int, w_init: W5, phi_init: float) -> GenRun`

_(no docstring)_

### `struct Check`

_(no docstring)_

### `fn mk_check(id: string, name: string, passed: bool, value: float, thresh: float, note: string) -> Check`

_(no docstring)_

### `fn check_i1_phi_monotone(ticks: list) -> Check`

_(no docstring)_

### `fn check_i2_eigenvec_stability(ticks: list) -> Check`

_(no docstring)_

### `fn check_i3_brain_like_floor(ticks: list) -> Check`

_(no docstring)_

### `fn _str(x) -> string`

_(no docstring)_

### `fn check_i4_exact_conservation() -> Check`

_(no docstring)_

### `fn check_i5_phi_gap_bounded_gen(ticks: list, bench_phi: float) -> Check`

> I5 (gen-aware variant)
> The upstream btr_evo/6 I5 pins bench_phi = 0.88 (single-gen converged
> baseline). For N-recurse, each generation has its own expected Φ per
> the gen_lift_schedule (pre-registered at this file's head). We pass
> the gen-specific expected Φ as bench_phi and preserve the same ±10%
> gap semantics. The 816× artifact regression guard and the [0.50,
> 1.00] in-band floor are unchanged.

### `fn check_i6_saturation_forward(ticks: list) -> Check`

_(no docstring)_

### `fn check_i7_cargo_weight(ticks: list) -> Check`

_(no docstring)_

### `fn run_cargo_checks(ticks: list, bench_phi: float) -> list`

_(no docstring)_

### `fn checks_pass_count(cs: list) -> int`

_(no docstring)_

### `fn parse_int(s: string, dflt: int) -> int`

_(no docstring)_

### `fn fmt_gen_json(r: GenResult, first: bool) -> string`

_(no docstring)_

### `fn fmt_check_json(c: Check, first: bool) -> string`

_(no docstring)_

### `struct Checkpoint`

_(no docstring)_

### `fn fmt_checkpoint_json(cp: Checkpoint, first: bool) -> string`

_(no docstring)_

### `fn emit_report(seed: int, n_gens: int, gen_iters: int, k_interval: int, gen_results: list, checkpoints: list, per_step_drops: list, max_drop: float, cum_gain: float, brain_like_min: float, cargo_all_pass: bool, verdict_pass: bool) -> string`

_(no docstring)_

### `fn derive_gen_seed(parent_seed: int, gen_idx: int) -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

