<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/btr_closed_loop.hexa -->
<!-- entry_count: 33 -->

# `tool/btr_closed_loop.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════

**Public/Internal entries:** 33

## Table of contents

- `struct Rng`
- `fn rng_new`
- `fn rng_step`
- `fn rng_unit`
- `struct EegState`
- `fn eeg_baseline`
- `fn virtual_eeg`
- `fn clamp_f`
- `fn abs_f`
- `struct StateVec`
- `fn normalize`
- `fn state_dist`
- `fn sqrt_approx`
- `struct TLWeights`
- `fn tl_weights_init`
- `fn tl_adjust`
- `fn student_phi`
- `fn channel_entropy`
- `fn plogp`
- `fn log2_approx`
- `struct NFOut`
- `fn neurofeedback_generate`
- `struct Tick`
- `fn run_loop`
- `struct Summary`
- `fn summarize`
- `fn bool_i`
- `fn f2s`
- `fn now_stamp`
- `fn emit_json`
- `fn tick_json`
- `fn parse_int`
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

### `struct EegState`

_(no docstring)_

### `fn eeg_baseline() -> EegState`

> Baseline "brain-like" reference (from current 85.6% validator)

### `fn virtual_eeg(rng: Rng, phi: float, nudge: float) -> EegState`

> Virtual EEG generator: deterministic perturbation of baseline,
> nudged by current Φ (higher Φ → more brain-like signature).

### `fn clamp_f(x: float, lo: float, hi: float) -> float`

_(no docstring)_

### `fn abs_f(x: float) -> float`

_(no docstring)_

### `struct StateVec`

_(no docstring)_

### `fn normalize(e: EegState) -> StateVec`

_(no docstring)_

### `fn state_dist(a: StateVec, b: StateVec) -> float`

_(no docstring)_

### `fn sqrt_approx(x: float) -> float`

_(no docstring)_

### `struct TLWeights`

_(no docstring)_

### `fn tl_weights_init() -> TLWeights`

_(no docstring)_

### `fn tl_adjust(prev: TLWeights, sv: StateVec) -> TLWeights`

> adjust channel weights from state_vec; preserve simplex (sum=1).
> lempel_ziv   → concept   (compressibility → concept salience)
> hurst        → context   (long-memory → context persistence)
> psd_slope    → meaning   (1/f slope → semantic criticality)
> autocorr     → auth      (stable self-reference → authorship)
> critical_exp → sig       (criticality → signature)

### `fn student_phi(w: TLWeights, sv: StateVec) -> float`

> ── virtual student Φ calculator (grad-injection proxy) ────────
> Φ is modeled as a weighted agreement between TL channel mass and
> EEG brain-likeness, plus a small baseline term. No tensor ops —
> deterministic closed form.  Target: Φ ∈ [0, 1].

### `fn channel_entropy(w: TLWeights) -> float`

_(no docstring)_

### `fn plogp(p: float) -> float`

_(no docstring)_

### `fn log2_approx(x: float) -> float`

_(no docstring)_

### `struct NFOut`

_(no docstring)_

### `fn neurofeedback_generate(phi: float, tension: float) -> NFOut`

> Mirrors anima-eeg/neurofeedback.hexa generate(phi, tension):
> volume clamp 0.3, brightness clamp 0.8, beat_freq 1..40 Hz.

### `struct Tick`

_(no docstring)_

### `fn run_loop(seed: int, iters: int) -> list`

_(no docstring)_

### `struct Summary`

_(no docstring)_

### `fn summarize(ticks: list) -> Summary`

_(no docstring)_

### `fn bool_i(b: int) -> string`

_(no docstring)_

### `fn f2s(x: float) -> string`

_(no docstring)_

### `fn now_stamp() -> string`

_(no docstring)_

### `fn emit_json(seed: int, iters: int, sum: Summary, ticks: list) -> string`

_(no docstring)_

### `fn tick_json(t: Tick) -> string`

_(no docstring)_

### `fn parse_int(s: string, dflt: int) -> int`

_(no docstring)_

### `fn main()`

_(no docstring)_

