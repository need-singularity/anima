<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/cert_dag_generator.hexa -->
<!-- entry_count: 50 -->

# `tool/cert_dag_generator.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 50

## Table of contents

- `fn _str`
- `fn _sh_quote`
- `fn _file_exists`
- `fn _dir_exists`
- `fn _mkdir_p`
- `fn _now_iso`
- `fn _ls_glob`
- `fn _sha256_of_string`
- `fn _argv`
- `fn _flag`
- `fn _opt`
- `fn _repo_root`
- `fn _is_map`
- `fn _is_array`
- `fn _is_string`
- `fn _map_has`
- `fn _map_get_str`
- `fn _map_get_arr`
- `fn _json_escape`
- `fn _extract_cert_entry`
- `fn _entry_slug`
- `fn _entry_current`
- `fn _entry_prev`
- `fn _entry_depends`
- `fn _entry_verified_by`
- `fn _entry_reaches`
- `fn _entry_cross`
- `fn _entry_path`
- `fn _scan_cert_paths`
- `fn _index_of_slug`
- `fn _index_of_hash`
- `fn _resolve_ref`
- `fn _build_edges`
- `fn _byte_at`
- `fn _str_cmp`
- `fn _sort_strings`
- `fn _sort_edges_canonical`
- `fn _topo_and_cycles`
- `fn _emit_dag_json`
- `fn _build_dag`
- `fn _run_real_scan`
- `fn _mk_entry`
- `fn _arr_contains`
- `fn _idx_in`
- `fn _selftest_s1`
- `fn _selftest_s2`
- `fn _selftest_s3`
- `fn _run_selftest`
- `fn _print_help`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn _sh_quote(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/sh_quote.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _file_exists(p: string) -> bool`

> INLINE_DEPRECATED[H42]: see shared/util/file_exists.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _dir_exists(p: string) -> bool`

_(no docstring)_

### `fn _mkdir_p(p: string) -> bool`

_(no docstring)_

### `fn _now_iso() -> string`

_(no docstring)_

### `fn _ls_glob(pat: string) -> array`

_(no docstring)_

### `fn _sha256_of_string(s: string) -> string`

_(no docstring)_

### `fn _argv() -> array`

_(no docstring)_

### `fn _flag(av: array, k: string) -> bool`

_(no docstring)_

### `fn _opt(av: array, k: string, d: string) -> string`

_(no docstring)_

### `fn _repo_root() -> string`

_(no docstring)_

### `fn _is_map(v) -> bool`

_(no docstring)_

### `fn _is_array(v) -> bool`

_(no docstring)_

### `fn _is_string(v) -> bool`

_(no docstring)_

### `fn _map_has(m, k: string) -> bool`

_(no docstring)_

### `fn _map_get_str(m, k: string, dflt: string) -> string`

_(no docstring)_

### `fn _map_get_arr(m, k: string) -> array`

> Safely pull an array field by key; if absent or scalar, return [].

### `fn _json_escape(s: string) -> string`

> INLINE_DEPRECATED[H42]: see shared/util/json_escape.hexa for canonical impl — kept inline (hexa stage0 loader)

### `fn _extract_cert_entry(path: string) -> array`

> ─── cert entry extraction ────────────────────────────────────────────────
> Each cert JSON is normalised into a "cert entry" map:
> { slug, current_hash, prev_hash, depends_on:[], verify:[], reaches:[],
> cross_refs:[], source_path }
> Fallbacks preserve back-compat across cert generations:
> slug          ← slug | file-stem
> current_hash  ← current_hash | cert_sha | mk8_cert_sha | commit | proof_hash
> prev_hash     ← prev_hash | prev_index_sha | hash_chain_prev
> Returns [] if the file is not a JSON map or cannot be parsed.

### `fn _entry_slug(e: array) -> string`

_(no docstring)_

### `fn _entry_current(e: array) -> string`

_(no docstring)_

### `fn _entry_prev(e: array) -> string`

_(no docstring)_

### `fn _entry_depends(e: array) -> array`

_(no docstring)_

### `fn _entry_verified_by(e: array) -> array`

_(no docstring)_

### `fn _entry_reaches(e: array) -> array`

_(no docstring)_

### `fn _entry_cross(e: array) -> array`

_(no docstring)_

### `fn _entry_path(e: array) -> string`

_(no docstring)_

### `fn _scan_cert_paths(repo: string) -> array`

_(no docstring)_

### `fn _index_of_slug(nodes: array, slug: string) -> int`

_(no docstring)_

### `fn _index_of_hash(nodes: array, h: string) -> int`

_(no docstring)_

### `fn _resolve_ref(nodes: array, token: string) -> string`

> Resolve a reference token (either a slug or a hex sha) to a node slug.
> Returns "" if unresolved.

### `fn _build_edges(entries: array, nodes: array) -> array`

> Build edges from entries. Returns edges = array of ["src","dst","kind"].

### `fn _byte_at(s: string, i: int) -> int`

> ─── lexicographic string comparison — byte-wise, deterministic ──────────
> Returns:
> -1 if a <lex  b
> 0 if a ==    b
> +1 if a >lex  b
> Implemented explicitly so that cert_dag is portable across hexa builds
> whose built-in string </> operator may not be byte-lexicographic.

### `fn _str_cmp(a: string, b: string) -> int`

_(no docstring)_

### `fn _sort_strings(arr: array) -> array`

_(no docstring)_

### `fn _sort_edges_canonical(edges: array) -> array`

_(no docstring)_

### `fn _topo_and_cycles(nodes: array, edges: array) -> array`

> ─── Kahn's algorithm (topo sort + cycle detection) ───────────────────────
> Input:  nodes (array of [slug,hash,path]), edges (array of [src,dst,kind]).
> Output: [ topo_order_slugs:array, cycle_sccs:array-of-array ].
> Cycle handling: any node not emitted by Kahn has ≥1 in-edge remaining;
> we group these residual nodes into one synthetic SCC list (implementation
> keeps it simple — production-grade SCC would run Tarjan; for cert DAGs a
> coarse residual set is sufficient for the "cycles_n ≥ 1" alarm contract).

### `fn _emit_dag_json(repo: string, nodes: array, edges: array, topo: array,`

_(no docstring)_

### `fn _build_dag(entries: array) -> array`

> Compose DAG from a list of (already extracted) cert entries.
> Returns a positional array:
> [nodes, edges_sorted, topo, cycles, proof_hash]

### `fn _run_real_scan() -> int`

_(no docstring)_

### `fn _mk_entry(slug: string, current_hash: string, prev_hash: string,`

_(no docstring)_

### `fn _arr_contains(a: array, x: string) -> bool`

_(no docstring)_

### `fn _idx_in(a: array, x: string) -> int`

_(no docstring)_

### `fn _selftest_s1() -> bool`

> S1 — 4-node linear chain.  A → B → C → D (prev_hash chain + depends_on).
> Expectation: topo_order resolves in A,B,C,D order and cycles_n == 0.

### `fn _selftest_s2() -> bool`

> S2 — cycle A→B→A.  Expectation: cycles_n ≥ 1 and topo_order is empty or
> partial (strict: does NOT contain A or B since both are inside the cycle).

### `fn _selftest_s3() -> bool`

> S3 — real .meta2-cert scan.  Expectation: DAG produced, cycles_n == 0,
> nodes_n > 0.  Uses the live repo (read-only).

### `fn _run_selftest() -> int`

_(no docstring)_

### `fn _print_help()`

_(no docstring)_

### `fn main() -> int`

_(no docstring)_

