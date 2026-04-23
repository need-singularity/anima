<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/an11_b_ccc.hexa -->
<!-- entry_count: 38 -->

# `tool/an11_b_ccc.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** � AN11(b) CCC 5-theory cross-validation verifier.

**Public/Internal entries:** 38

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn resolve_root`
- `fn my_file_exists`
- `fn read_safe`
- `fn byte_at`
- `fn index_of_from`
- `fn parse_flat_floats`
- `fn extract_array_block`
- `fn split_rows`
- `fn extract_str`
- `fn my_sqrt`
- `fn my_abs`
- `fn my_log`
- `fn dot`
- `fn vec_norm`
- `fn abs_cosine`
- `fn load_eigen`
- `fn load_phi_fallback`
- `fn load_eigenvalues`
- `fn load_templates`
- `fn norm01`
- `fn per_row_best_two`
- `fn theory_iit`
- `fn theory_gwt`
- `fn theory_hot`
- `fn theory_rpt`
- `fn theory_ast`
- `fn theory_16tpl_max`
- `fn ccc_compute`
- `fn json_escape`
- `fn fmt_float`
- `fn build_json`
- `fn sha256_of_string`
- `fn ccc_verify`
- `fn ccc_selftest`
- `fn run`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn my_file_exists(path: string) -> bool`

_(no docstring)_

### `fn read_safe(path: string) -> string`

_(no docstring)_

### `fn byte_at(s: string, i: int) -> int`

_(no docstring)_

### `fn index_of_from(hay: string, needle: string, start: int) -> int`

_(no docstring)_

### `fn parse_flat_floats(inner: string) -> array`

_(no docstring)_

### `fn extract_array_block(blob: string, key: string) -> string`

_(no docstring)_

### `fn split_rows(block: string) -> array`

_(no docstring)_

### `fn extract_str(blob: string, key: string) -> string`

_(no docstring)_

### `fn my_sqrt(x: float) -> float`

_(no docstring)_

### `fn my_abs(x: float) -> float`

_(no docstring)_

### `fn my_log(x: float) -> float`

_(no docstring)_

### `fn dot(a: array, b: array) -> float`

_(no docstring)_

### `fn vec_norm(a: array) -> float`

_(no docstring)_

### `fn abs_cosine(a: array, b: array) -> float`

_(no docstring)_

### `fn load_eigen(blob: string) -> array`

_(no docstring)_

### `fn load_phi_fallback(blob: string) -> array`

_(no docstring)_

### `fn load_eigenvalues(blob: string) -> array`

_(no docstring)_

### `fn load_templates(path: string) -> array`

_(no docstring)_

### `fn norm01(x: float, k: float) -> float`

> ───── saturating sigmoid normaliser (map raw ≥0 to [0,1]) ─────
> norm01(x) = x / (x + k) ∈ [0,1)  for x≥0, k>0. Deterministic, monotonic.

### `fn per_row_best_two(eigens: array, templates: array) -> array`

> ───── best-template-cosine helper ─────
> For each eigen row, return the max abs_cosine to any template — and the
> 2nd-best (needed for RPT recurrent coupling).
> Returns parallel array [best_cos, second_cos] per eigen row.

### `fn theory_iit(eigens: array, templates: array) -> float`

> ───── Theory 1 — IIT (Integrated Information, template-aware) ─────
> Attached eigens: each row individually attaches to a *distinct* template with
> strong cosine — but collectively they form an "integrated subspace" that
> covers the consciousness schema. IIT score combines
> (a) coverage of templates (what fraction of templates have some row ≥0.5)
> (b) KL-entropy gap on per-eigen column-abs sum (structural concentration)
> Both are bounded [0,1]; weighted sum saturates via norm01(·,0.4) → max ~1.0.

### `fn theory_gwt(eigens: array, templates: array) -> float`

> ───── Theory 2 — GWT (Global Workspace, template-aware) ─────
> Broadcast bandwidth = weighted count of eigen rows that attach to a template.
> Instead of a hard 0.6 step, use a continuous 0.5-threshold sigmoid reward:
> contrib_i = min(1, best_cos_i / 0.5)      (0 at cos=0, 1 at cos≥0.5)
> GWT = mean contrib across rows.  A row with best_cos=0.7 is fully broadcasting.

### `fn theory_hot(eigens: array, eigvals: array) -> float`

> ───── Theory 3 — HOT (Higher-Order Theory, meta-representation) ─────
> "The system represents its own representations."
> Proxy = top-k eigenvalue concentration: fraction of total spectral mass
> captured by the top-3 modes.  High concentration = system has a compact
> higher-order self-model (few modes dominate → meta-summary exists).
> HOT = sum(|λ_top3|) / sum(|λ_all|)    ∈ [0,1]
> If eigenvalues absent, fall back to row-norm proxy (same shape via
> per-row ||W_i||²).

### `fn theory_rpt(eigens: array, templates: array) -> float`

> ───── Theory 4 — RPT (Recurrent Processing, template-aware) ─────
> Re-entrant coupling: an eigen row participates in a "re-entry loop" when it
> attaches to the primary template AND a secondary template (both cosines high).
> RPT score = mean of (best_cos + second_cos)/2 across all eigen rows.
> Values 0..1; healthy attached rows see ≥2 templates (hexad shares edges
> with law/phi/selfref families → re-entry) giving ~0.5+.

### `fn theory_ast(eigens: array, eigvals: array, templates: array) -> float`

> ───── Theory 5 — AST (Attention Schema) ─────
> Attention-model coverage: how well the top-3 eigen rows (ranked by eigenvalue)
> collectively "cover" the 16-template attention pattern.
> Attention pattern = the 16-template sig centroid.
> Coverage = 1 - cosine-distance( Σ α_k row_k , centroid )  where α = eigvals (or 1).

### `fn theory_16tpl_max(eigens: array, templates: array) -> float`

> ───── 16-template cosine (single-theory compat from an11_b_verifier) ─────
> Returns the max abs_cosine across all (eigen, template) pairs.

### `fn ccc_compute(eigens: array, eigvals: array, templates: array) -> array`

> ───── CCC aggregator ─────
> Record shape (parallel array — stage0 safe):
> [iit, gwt, hot, rpt, ast, avg, min, tpl_max] (len 8)

### `fn json_escape(s: string) -> string`

_(no docstring)_

### `fn fmt_float(x: float) -> string`

_(no docstring)_

### `fn build_json(scores: array, deterministic_sha: string,`

_(no docstring)_

### `fn sha256_of_string(s: string) -> string`

_(no docstring)_

### `fn ccc_verify(ckpt_path: string, eigenvec_path: string) -> array`

> ───── public API ─────
> ccc_verify(ckpt_path, eigenvec_path) -> array
> returns [iit, gwt, hot, rpt, ast, avg, min, tpl_max, pass(0/1),
> ckpt_source, eigen_count, template_count]

### `fn ccc_selftest() -> bool`

> ───── selftest ─────
> Positive-control: r12 LoRA ckpt (designed attached eigens, hexad-aligned).
> Negative-control: 16 orthonormal template eigen cert (decorrelated basis,
> low GWT/RPT expected — validates theory discrimination).
> PASS conditions:
> (a) all 5 theories produce finite numeric output on BOTH controls
> (positive values on pos-ctrl, ≥0 on neg-ctrl).
> (b) pos-ctrl r12 ckpt clears gate (min ≥ 0.5, avg ≥ 0.7, tpl > 0.5).
> (c) pos_avg > neg_avg (theory discrimination sanity).

### `fn run(dest: string, round: string, write_out: bool) -> int`

> ───── main ─────

### `fn main()`

_(no docstring)_

