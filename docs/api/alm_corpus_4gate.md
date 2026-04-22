<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T12:40:18Z -->
<!-- source: tool/alm_corpus_4gate.hexa -->
<!-- entry_count: 31 -->

# `tool/alm_corpus_4gate.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T12:40:18Z UTC._

**Tool:** � ALM r13 corpus 4-gate pre-drill verifier

**Public/Internal entries:** 31

## Table of contents

- `fn cert_gate_mock`
- `fn arg_value`
- `fn arg_present`
- `fn fexists`
- `fn dexists`
- `fn now_stamp`
- `fn sha256_of_file`
- `fn sha256_of_str`
- `fn atomic_write`
- `fn is_json_map`
- `fn json_escape`
- `fn resolve_config_path`
- `fn load_config`
- `fn flatten_density_keywords`
- `fn line_hits_density`
- `fn line_hits_axis`
- `fn near_dup_sig`
- `fn scan_corpus_4gate`
- `fn join_strs`
- `fn int_arr_to_json`
- `fn emit_report`
- `fn extract_pass_subset`
- `fn run_on_corpus`
- `fn mk_line`
- `fn synth_s1`
- `fn synth_s2`
- `fn synth_s3`
- `fn run_scenario`
- `fn run_selftest`
- `fn print_usage`
- `fn main`

## Entries

### `fn cert_gate_mock(payload)`

> ─── cert_gate mock ───────────────────────────────────────────────────
> TODO[cert_gate_wire]: replace with `use tool/cert_gate` after A3 lands.

### `fn arg_value(argv, key, dflt)`

_(no docstring)_

### `fn arg_present(argv, key)`

_(no docstring)_

### `fn fexists(p)`

_(no docstring)_

### `fn dexists(p)`

_(no docstring)_

### `fn now_stamp()`

_(no docstring)_

### `fn sha256_of_file(p)`

_(no docstring)_

### `fn sha256_of_str(s)`

_(no docstring)_

### `fn atomic_write(path, body)`

_(no docstring)_

### `fn is_json_map(v)`

_(no docstring)_

### `fn json_escape(s)`

_(no docstring)_

### `fn resolve_config_path()`

_(no docstring)_

### `fn load_config(path)`

_(no docstring)_

### `fn flatten_density_keywords(kwmap)`

> Flatten density_keywords map → single list of keywords.

### `fn line_hits_density(line, flat_kws)`

> Density: a line passes G_A if it contains at least one keyword from
> any of the 4 lexicons (hexad / law / phi / selfreflect). Corpus-level
> G_A passes if (hit_lines / total_lines) >= density_threshold.

### `fn line_hits_axis(line, markers)`

> Hexad axis hit: line contains any marker of the given axis.

### `fn near_dup_sig(line, p_len, s_len)`

> Deterministic near-dup signature: (prefix[0:P], suffix[n-S:n]).
> Two lines are considered near-duplicates if both their prefix AND
> suffix fragments are equal at the configured lengths. This captures
> cherry-picking (same boilerplate prefix + tweak in middle) without
> pulling in heavy SimHash.

### `fn scan_corpus_4gate(lines, cfg)`

_(no docstring)_

### `fn join_strs(xs, sep)`

_(no docstring)_

### `fn int_arr_to_json(arr)`

_(no docstring)_

### `fn emit_report(scan, corpus_path, corpus_sha, argv_summary, proof_hash, cfg_path)`

_(no docstring)_

### `fn extract_pass_subset(lines, line_pass, out_path)`

_(no docstring)_

### `fn run_on_corpus(corpus_path, extract_pass, cfg, cfg_path)`

_(no docstring)_

### `fn mk_line(id, text)`

_(no docstring)_

### `fn synth_s1()`

_(no docstring)_

### `fn synth_s2()`

_(no docstring)_

### `fn synth_s3()`

_(no docstring)_

### `fn run_scenario(name, lines, cfg, expect_a, expect_b, expect_c, expect_d)`

_(no docstring)_

### `fn run_selftest(cfg)`

_(no docstring)_

### `fn print_usage()`

_(no docstring)_

### `fn main()`

_(no docstring)_

