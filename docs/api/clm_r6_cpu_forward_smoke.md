<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/clm_r6_cpu_forward_smoke.hexa -->
<!-- entry_count: 25 -->

# `tool/clm_r6_cpu_forward_smoke.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 25

## Table of contents

- `fn _home`
- `fn fabs`
- `fn is_nan`
- `fn is_finite`
- `struct Rng`
- `fn rng_new`
- `fn rng_next`
- `fn rng_unit`
- `fn rng_bipolar`
- `fn det_rand`
- `fn det_tokens`
- `fn softmax`
- `fn ln_safe`
- `fn ce_loss_single`
- `fn phi_holo_proxy`
- `fn phi_gwt_proxy`
- `struct CorpusDesc`
- `fn corpus_try_open`
- `fn corpus_byte_window`
- `fn embed_lookup`
- `fn project`
- `fn descent_step_inplace`
- `struct SmokeRun`
- `fn run_smoke`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn fabs(x: float) -> float`

_(no docstring)_

### `fn is_nan(x: float) -> bool`

_(no docstring)_

### `fn is_finite(x: float) -> bool`

_(no docstring)_

### `struct Rng`

_(no docstring)_

### `fn rng_new(seed: int) -> Rng`

_(no docstring)_

### `fn rng_next(r: Rng) -> Rng`

_(no docstring)_

### `fn rng_unit(r: Rng) -> float`

_(no docstring)_

### `fn rng_bipolar(r: Rng) -> float`

_(no docstring)_

### `fn det_rand(n: int, seed: int) -> array`

> Build an array of n bipolar floats from seed, deterministic.

### `fn det_tokens(n: int, vocab: int, seed: int) -> array`

> Build an array of n deterministic int tokens in [0, vocab).

### `fn softmax(x: array) -> array`

_(no docstring)_

### `fn ln_safe(x: float) -> float`

> Safe ln (uses builtin ln but guards on <= 0).

### `fn ce_loss_single(logits: array, target: int) -> float`

_(no docstring)_

### `fn phi_holo_proxy(logits: array) -> float`

_(no docstring)_

### `fn phi_gwt_proxy(logits: array) -> float`

_(no docstring)_

### `struct CorpusDesc`

_(no docstring)_

### `fn corpus_try_open(path: string) -> CorpusDesc`

_(no docstring)_

### `fn corpus_byte_window(desc: CorpusDesc, offset: int, n_bytes: int) -> array`

> Read a byte window via dd (bounded size for smoke).

### `fn embed_lookup(w_embed: array, vocab: int, d_model: int, token: int) -> array`

_(no docstring)_

### `fn project(w_proj: array, d_model: int, vocab: int, h: array) -> array`

_(no docstring)_

### `fn descent_step_inplace(w_proj: array, d_model: int, vocab: int,`

> Sparse positive descent on the target column only, IN-PLACE:
> For each d_model row k, bump W_proj[k, target] by +eta * h[k].
> This is the exact negative-gradient direction for CE on the target
> class (ignoring the smaller off-target corrections), and it
> monotonically reduces CE for the current (token, target) pair.
> Cost: O(d_model) index-assignments per step, no array rebuild.

### `struct SmokeRun`

_(no docstring)_

### `fn run_smoke(seed: int, n_steps: int, corpus_path: string, verbose: bool, use_corpus: bool) -> SmokeRun`

_(no docstring)_

### `fn main()`

_(no docstring)_

