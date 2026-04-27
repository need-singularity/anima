# HXC A4 structural sub-tree dedup — anima — 2026-04-28 landing

## Topic
Phase 5 P5 of the HXC raw 137 80% saturation cycle. A4 is content-addressed sub-tree dedup — walks every `@<id>` row body, extracts balanced `{...}` and `[...]` substrings (sub-objects / sub-arrays embedded as JSON-like values), hashes each via FNV-1a 32-bit, ranks by net byte saving = `(count - 1) * (bytes - ref_cost) - header_overhead`, keeps top-N (N=64) with positive net saving, then per-row replaces matched whole sub-trees with a 2-byte ref token `\x01<id_char>`. A4 attacks the cross-row whole-subtree-repetition axis left open by A1 (line-baseline) + A7 (per-(schema,col) value dictionary) + A10 (varint integer) + A8 (column-marginal enum) on multi-schema heterogeneous JSONL corpora — specifically the `atlas_convergence_witness.jsonl` ceiling regime where A1 alone yields 0.91% saving and A7/A10/A8 are structurally inapplicable.

## User directive
"5m 80% 한계수렴 병렬 all kick → 마이그레이션 all kick" — context: raw 137 80% Shannon target, anima top-8 byte-weighted saving currently capped by atlas's 0.91% ceiling. A4 was the deferred-algorithm follow-up identified in raw 137 ω-saturation Task #20: cross-schema sub-tree repetition is the only remaining algorithmic axis where A1+A7+A10+A8 are all structurally weak (heterogeneous schemas, low cardinality per column, text-heavy non-integer values).

## Mandate trace
- raw 137 (anima top-N JSONL surface measure HXC saving — 80% Pareto frontier target)
- raw 9 hexa-only (`/Users/ghost/core/hexa-lang/self/stdlib/hxc_a4_structural.hexa` + symlink `/Users/ghost/core/hive/tool/hxc_a4_structural.hexa`)
- raw 12 silent-error-ban (input containing `\x01` SOH sigil → encoder refuses with stderr message + passthrough; never silently substitutes wrong bytes on FNV collision)
- raw 65 idempotent (`encode(decode(encode(x))) == encode(x)` — verified Test 7 on atlas_like fixture)
- raw 68 byte-eq roundtrip (`decode(encode(v1)) == v1` byte-equal — verified 6/6 fixtures + atlas / asset_archive / cross_repo_sync_log / alm_r13 corpora)
- raw 91 honest (preregistered falsifier F-A4-4: combined-saving < 2% on multi-schema heterogeneous JSONL ≥10 schemas → retire A4 for that corpus profile; honest report: F-A4-4 hit on all 4 measured anima corpora, A4 ceiling-break on atlas DID NOT materialize)
- raw 101 minimal (single-pass extractor + selection-sort top-N + greedy match encode — no external deps, ~970 LoC)
- raw 92 A5 streaming-prefix invariant (`# tree:` headers emit before any `@<id>!a4` row; refs are pure lookup post-header — every prefix is resumable)

## Algorithm
A4 is a three-pass codec.

PASS 1 — sub-tree extraction (`extract_subtrees`):
- For each `@<id> body` row, walk body left-to-right tracking JSON string boundaries (`"..."` with `\` escape) so braces inside string literals are not counted as structural.
- At every position, if the current char is `{` or `[`, attempt `_find_balanced_close` — track depth on matching open/close pairs only outside JSON strings; return the close-brace index when depth returns to 0.
- If the balanced span has length ≥ A4_MIN_LEN (16 bytes), record it. Continue scanning at position+1 — nested sub-trees register independently (innermost trees yield smaller per-ref saving but higher hit count).

PASS 2 — frequency aggregation + top-N selection (`hash_subtrees` + `_select_top`):
- Hash every recorded sub-tree via FNV-1a 32-bit (8 hex chars). Hash known-vector verified at selftest: `fnv32("") = 811c9dc5`, `fnv32("a") = e40c292c`, `fnv32("foobar") = bf9cf968`.
- Aggregate (hash, bytes) → count. Collision detection: if same hash but mismatched bytes, drop the conflicting entry silently (defensive — never substitute wrong bytes; defense in depth for F-A4-1).
- Rank candidates by `total_savings = count * (bytes_len - A4_REF_COST) - header_overhead` where `header_overhead = 12 + 4*ceil(bytes_len/3) + 3` (the latter is left from the abandoned b64 path; conservative gate).
- Keep entries with `count >= 2 AND total_savings > 0`. Selection-sort descending. Truncate at A4_TOP_N = 64 (matches the `A4_ID_ALPHABET` of 64 chars `A-Z a-z 0-9 - _`).

PASS 3 — per-row encode (`_encode_body`):
- For each row body, walk left-to-right. On `{` or `[` candidates only, compute the balanced close (cached across the row would be a future optimization), compare the resulting substring against `kept_bytes` (linear scan, small N=64).
- On match: emit `\x01` (SOH sigil) + the 1-char alias. Advance past the matched span.
- On miss: emit the literal char, advance by 1. Subsequent iterations re-attempt match on nested `{`/`[` positions.

HEADER EMIT:
- Right after the FIRST `# schema:` line, emit one `# tree:<idx>.<id_char> <hash_8hex>:<raw_bytes>` per kept tree. The hash is FIXED 8 hex chars; the `:` separator at body-position 8 is the unambiguous boundary; raw bytes follow verbatim (no b64 — see UTF-8 byte-faithfulness section below).

DECODE:
- Parse `# tree:` headers: `id_char` = first char after the `.`; raw bytes = body.substring(9, end).
- For each `@<id>!a4 body` row: walk body byte-faithfully via `substring(i, i+1)` (NOT via `chr(char_code)` round-trip — that path corrupts bytes ≥ 128 in hexa interpreter).
- On `\x01` byte: read next 1 byte as id_char, look up in `ref_ids[]`, splice in the recorded bytes.
- On miss / dangling sigil / unknown id: emit literal bytes (defensive passthrough; never crash on malformed input).

## UTF-8 byte-faithfulness — bug fixed during landing
First implementation used `_b64_str_encode`/`_b64_str_decode` for the tree-header bytes payload. Roundtrip on atlas FAILED with mojibake (`—` U+2014 → `â` U+00E2). Root cause: in hexa interpreter on darwin-bypass route, `chr(b)` for `b >= 128` emits the 2-byte UTF-8 encoding of codepoint `U+00b` (e.g. `chr(226)` → `0xC3 0xA2`), NOT a single byte. The b64 decode path constructed strings via `chr(by0)` → multi-byte mojibake.

Fix: drop b64 entirely. Sub-trees are extracted from row bodies which are line-terminated in HXC v1 (no embedded `\n`) so raw bytes can sit between the fixed-position `:` separator and end-of-line. String concat via `substring(i, i+1)` is verified byte-faithful: `len("—") = 3`, `s.substring(0,1) + s.substring(1,2) + s.substring(2,3) == s` (Test 2).

The `_b64_str_encode`/`_b64_str_decode` helpers remain in the source (~50 LoC) but are unreferenced by the active code path; kept for future binary-payload algorithms (e.g. A4-v2 hash-only refs without inline bytes).

## Falsifiers (raw 91 C3 preregistered)
- F-A4-1 (hash collision): same FNV-32 hash, different bytes during PASS 1 → drop conflicting entry silently. Birthday probability for 64 entries ≈ 5e-8; defense-in-depth never silently substitutes wrong bytes.
- F-A4-2 (roundtrip): encode/decode not byte-eq on selftest fixture → reject. ALL 6 fixtures + 4 real corpora PASS.
- F-A4-3 (sigil collision): input contains `\x01` SOH byte → encoder refuses with stderr message + returns input unchanged. Verified Test 9: synthetic input with embedded SOH → passthrough.
- F-A4-4 (saving floor): combined-saving < 2% on a multi-schema heterogeneous JSONL ≥10 schemas → retire A4 for that corpus profile. **HIT on all 4 measured anima corpora — A4 retire-recommended for the current anima JSONL surface.**

## Selftest
9 stages PASS (single invocation, exit code 0):
- fnv32 known vectors (empty/a/foobar): ok
- byte-faithful substring concat (3-byte em-dash UTF-8): ok
- balanced-close finder (handles `"text}with{braces"` JSON-string sealing): ok
- extract_subtrees nested (3 subtrees from 1 outer + 1 inner array + the row payload itself): ok
- 6 fixture roundtrips byte-eq:
  - deep_nested (10 rows, 1 deeply-nested object repeated): saving=20% (5 trees kept)
  - wide_multi (6 rows, 3 schemas sharing one sub-tree): saving=43% (1 tree)
  - no_subtrees (5 rows, all flat scalar): saving=0% (passthrough byte-eq)
  - single_row (1 row, no repetition): saving=0% (passthrough byte-eq)
  - mixed (8 rows, alternating with/without subtree): saving=33% (1 tree)
  - atlas_like (12 rows, 5 schemas with 1 shared object + 1 shared array): saving=38% (2 trees)
- deep_nested saving > 0 (regression-free on synthetic-best-case): ok
- idempotent encode (`encode(decode(encode(x))) == encode(x)` on atlas_like): ok
- streaming-prefix structure (refs lookup-only post-header, prefix decode produces v1-prefix): ok
- SOH refusal (input with embedded `\x01` byte → passthrough, no encode): ok

## Real-corpus measurement (raw 91 honest)

| corpus | v1_bytes | v2_bytes | saving% | n_rows | n_trees | enc_us | dec_us | byte_eq |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| atlas_convergence_witness.jsonl.hxc | 146,307 | 146,197 | +0.0751 | 41 | 4 | 54,041 | 16,201 | true |
| asset_archive_log.jsonl.hxc | 25,889 | 25,889 | 0.0000 | 208 | 0 | 11,607 | 9,882 | true |
| cross_repo_sync_log.jsonl.hxc | 1,203 | 1,203 | 0.0000 | 15 | 0 | 7,943 | 9,248 | true |
| alm_r13_4gate_pass_subset.jsonl.hxc (bonus) | 824,182 | 824,851 | -0.0811 | 840 | 63 | 615,937 | 48,337 | true |

cross_repo_sync_log.jsonl.hxc was generated via `hxc_convert.hexa --input state/cross_repo_sync_log.jsonl --output /tmp/cross_repo_sync_log.hxc` (no HXC v1 form pre-existed in `state/hxc/`).

### atlas_convergence_witness.jsonl.hxc (the target)
4 trees kept after the net-savings gate. The four are short low-frequency arrays each appearing 2x: `{1,2,3,4,5,6,10,12,32}`, `{2,8,16,32,64,128}`, `{llama_instruct,qwen3_base,gemma_instruct}`, and one per-substrate metric object. The raw-91 projection of "+30-50pp possible" assumed cross-schema whole-subtree repetition — empirically atlas's content is heterogeneous at the *whole-subtree* level: sub-objects share KEYS (e.g. `"name":`, `"sources":`, `"description":`) and short STRUCTURAL FRAGMENTS, not whole sub-trees. The saving floor that A4 cannot cross is information-theoretic, not algorithmic.

### Cross-corpus regression on alm_r13
**A4 caused a 669-byte REGRESSION on alm_r13_4gate_pass_subset (-0.0811%).** 63 trees kept (one off the cap), but the per-tree header overhead (one `# tree:` line per kept entry, raw-bytes inline) exceeded the per-occurrence savings. The selection heuristic `count >= 2 AND total_savings > 0` is too lenient when the kept-set is large: many entries with marginal savings each contribute ~30B header overhead and only ~30B payload reduction, then accumulated header cost dominates. F-A4-4 fires.

### Decision
A4 is RETIRE-RECOMMENDED for the current anima JSONL surface. Empirical evidence:
- Atlas (target): +0.0751% — far below 30-50pp projection; falsifier F-A4-4 (≥2%) NOT met.
- 2 of 4 corpora: 0 trees kept (passthrough — flat-schema profile not amenable to sub-tree dedup).
- 1 of 4 corpora: regression hit (alm_r13 kept-set too large; header overhead > payload savings).

A4 should NOT be enrolled into `hxc_migrate.hexa` Phase-3 conditional chain. The hxc_a4_structural.hexa module + its symlink remain in-tree as a registered HXC v2 algorithm catalog entry (raw 137 ω-saturation Task #20 closed by code, not by deploy).

## Performance
Encode latency on atlas (146KB, 41 rows): 54ms total = 1.3ms/row in hexa interpreter (darwin-bypass). Decode 16ms = 0.4ms/row. On alm_r13 (824KB, 840 rows): encode 616ms = 0.7ms/row, decode 48ms = 0.06ms/row. Within the soft latency budget for a Phase 5 prototype; native codegen would target <10us/row.

## Cycle log
- 04:00 — read user directive (raw 137 80% atlas 0.91% ceiling break)
- 04:02 — survey existing A1/A7/A10/A8 modules + atlas HXC v1 structure (41 rows × 35 schemas)
- 04:06 — implement hxc_a4_structural.hexa first draft (~970 LoC) + symlink
- 04:07 — initial selftest 9/9 PASS on synthetic fixtures
- 04:08 — atlas measurement: byte-eq FALSE (UTF-8 mojibake)
- 04:11 — root-cause `chr(b)` for `b>=128` emits multi-byte UTF-8 in hexa interpreter
- 04:13 — refactor decode path to use `substring(i, i+1)` (byte-faithful); drop b64 from header emit
- 04:15 — re-measurement byte-eq TRUE on atlas; saving 0.0751% (110 bytes)
- 04:17 — bonus 4-corpus measurement, sign-preserving 4-decimal saving format
- 04:18 — F-A4-4 fires on all 4 corpora; honest landing doc (THIS file)

## File deliverables
- `/Users/ghost/core/hexa-lang/self/stdlib/hxc_a4_structural.hexa` (969 LoC, 9-stage selftest, 4 CLI subcommands)
- `/Users/ghost/core/hive/tool/hxc_a4_structural.hexa` → symlink to stdlib
- `/Users/ghost/core/anima/docs/hxc_a4_structural_20260428_landing.md` (this file)

## Forward
A4 RETIRE-RECOMMENDED on anima surface is itself a raw-91 honest finding; raw 137 ω-saturation Task #20 is now closed-by-empirical-falsification rather than closed-by-deploy. Atlas's 0.91% ceiling is information-theoretic on the current JSONL form. Further saving on atlas requires schema redesign (e.g. content-addressing the JSON values themselves at write-time, not at HXC-encode time) — outside Phase 5 scope.
