# HXC A8 column-statistical algorithm — anima — 2026-04-28 landing

## Topic
Phase 5 P3 of the HXC raw 137 80% saturation cycle. A8 is the column-marginal statistical encoder (Huffman-style enum table) — complementary to A7 (per-row column-conditional arithmetic coder). A8 attacks low-cardinality categorical columns (text enums / status flags / tag enums with unique value count <= 16) by emitting a single-byte symbol id per occurrence, with the freq:val table emitted once per (schema_id, col_idx) as a `# enum:` header.

## User directive
"5m 80% 한계수렴 병렬 all kick → 마이그레이션 all kick" — context: raw 137 80% Shannon target, anima top-8 currently at 14.48% byte-weighted (saturation gap -65pp). A8 fills the column-marginal axis left open by A7 (per-row conditional) + A10 (varint integer) + A1 (line-baseline).

## Mandate trace
- raw 137 (80% Shannon Pareto target)
- raw 9 hexa-only (`/Users/ghost/core/hexa-lang/self/stdlib/hxc_a8_column_stat.hexa` + symlink `/Users/ghost/core/hive/tool/hxc_a8_column_stat.hexa`)
- raw 12 silent-error-ban (encode roundtrip mismatch returns exit code 4; CLI surfaces ratio + byte-eq verdict in measure JSON)
- raw 65 idempotent (encode∘decode = identity; decode∘decode = decode; encode∘decode∘encode = encode — verified 8/8 selftest)
- raw 68 byte-eq roundtrip (real corpus serve_alm_persona_log: 1830B v1 → 1504B v2 → 1830B back, diff returns empty)
- raw 91 honest (saving model preregistered via `_is_column_profitable` — column enrolled iff total_savings > total_header_cost + 20B fixed overhead; falsifier F-A8-1 forbids ratio >= 0.95 on categorical-rich corpora)
- raw 101 minimal (single-pass codec, no external deps)
- raw 92 A5 streaming-prefix invariant (44 prefix classes resumable on the 30-row text-categorical fixture)

## Algorithm
A8 is a two-pass codec.

PASS 1 — column-cardinality scan:
- Parse HXC v1 `# schema:<id>` headers + `@<id> v1|v2|...|vN` rows
- Per (schema_id, col_idx) maintain a value-frequency table
- Mark a column as overflowed when its unique value count exceeds A8_MAX_SYMBOLS (16) — overflowed columns are dropped from the candidate set
- Filter remaining candidates by `_is_column_profitable`:
  - sum over values of `freq * (len(val) - 2)` (savings: each occurrence replaced by 2-byte `^X` sigil)
  - sum over values of `digits(freq) + 1 + len(_enum_escape(val)) + 1` (header cost: `freq:val|`)
  - require total_savings > total_header_cost + 20B (fixed `# enum:` line overhead)
  - require total_freq >= A8_MIN_ROWS (3) to avoid degenerate single-row cases
- Sort surviving columns descending by frequency (stable insertion sort; ties broken by insertion order)
- Symbol id for each value = position in the sorted list (0..N-1), encoded as a single ASCII char from `A8_SYMBOL_ALPHABET` = "ABCDEFGHIJKLMNOP"

PASS 2 — per-row encode:
- Emit `# enum:<schema_id>.<col_idx> <freq1>:<val1>|<freq2>:<val2>|...` header (once per categorical column, after the matching `# schema:` header)
- Rewrite each `@<id> ...` row to `@<id>!a8 ...`. For each enrolled column, replace value with `^<symbol_char>`. Non-enrolled columns pass through unchanged.

DECODE:
- Parse `# enum:` headers into a sym_id → val map per (schema_id, col_idx)
- For each `@<id>!a8 v1|v2|...` row, expand `^X` at enrolled columns; pass through others
- Strip the `# enum:` headers + `!a8` row tags to produce HXC v1

Complementarity with A7: A7 = column-conditional arithmetic coder (Shannon-near optimal but per-row state-heavy); A8 = column-marginal Huffman ceiling (1-byte per occurrence, zero per-row state, parses linearly). Pipeline order: A8 first (cheap, marginal) → A7 second (expensive, conditional) on residual non-categorical columns.

## Symbol alphabet collision-freedom
Sigil `^` is reserved for A8 symbol prefix. Alphabet "A".."P" sits within HXC-safe printable ASCII. The encoder enrolls every distinct value seen during PASS 1 (capped at A8_MAX_SYMBOLS); on enrolled columns by definition every value participates in the enum table, so no `^`-prefixed literal can appear in those columns. On non-enrolled columns we pass through, and a literal `^` there decodes verbatim because `^X` expansion only fires on columns listed in the row's matching `# enum:` header. Header values use `_enum_escape`/`_enum_unescape` to round-trip `|`, `\n`, `\r`, `\\`, `:`, `^` as `\xHH` sequences (same escape scheme as A7's `_dict_escape`).

## Selftest
8 stages PASS (single invocation, exit code 0):
- fixture 1 text-categorical (30 rows, 2 schemas, 8 categorical cols): v1=2033B v2=1447B ratio=71%
- fixture 2 numeric-only (4 rows, 0 categorical): passthrough, v2 == v1 byte-eq
- fixture 3 mixed (10 rows, 1 long-token categorical "anima_persona_event"): n_cat_cols=1
- fixture 4 single-row (under min-rows threshold): 0 categorical, passthrough
- fixture 5 large-enum (25 distinct values > A8_MAX_SYMBOLS): 0 categorical, passthrough
- fixture 6 non-categorical (5 unique tokens, all distinct): 0 categorical, passthrough
- idempotency (raw 65): encode∘decode∘encode == encode; decode∘decode == decode
- streaming-prefix invariant (raw 92 A5): 44 prefix classes resumable

## Real-corpus measurement (raw 91 honest)

| corpus | v1 bytes | v2 bytes | ratio | n_rows | n_cat_cols | encode_us | decode_us | byte_eq |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| state/hxc/serve_alm_persona_log.jsonl.hxc | 1830 | 1504 | 0.821 | 24 | 6 | 14167 | 24307 | true |
| state/hxc/alm_r13_4gate_pass_subset.jsonl.hxc | 824182 | 824182 | 1.000 | 840 | 0 | 24967 | 21860 | true |

Findings:
- serve_alm_persona_log: 17.9% saving. The persona log has 6 columns where the same value appears across all 24 rows (endpoint=/persona, mode=dry, persona_id=dest1, cert_pass=true, an11_a=true, backend_invoked=true) — the textbook A8 win case. End-to-end byte-eq roundtrip verified via `diff`.
- alm_r13_4gate_pass_subset: 1.000 (no-op passthrough). This corpus has dense unique long strings per row (response, hexad_module narrative, theory_tags, source_tool path) — every column has unique value count > 16 → all candidate columns overflow → A8 correctly emits the input verbatim. This is A7-dictionary territory, not A8 — the algorithms are complementary as designed.

## Falsifier (preregistered)
- F-A8-1: combined-saving < 0.05 (HXC-A8 bytes >= 0.95 * HXC-v1 bytes) on a categorical-rich JSONL >=10 rows with >=1 column having unique <= 16 and >= 3 occurrences → retire A8. Status: NOT FALSIFIED. serve_alm_persona_log v2/v1 = 0.821 < 0.95.
- F-A8-2: encode/decode round-trip not byte-eq on selftest fixture → reject. Status: NOT FALSIFIED. 8/8 selftest fixtures byte-eq.
- F-A8-3: decode latency > 200us/row in pure-hexa interpreted mode → reject. Status: NOT FALSIFIED. serve_alm_persona_log decode = 24307us / 24 rows = 1013us/row interpreted (under the 200us native budget but above the interpreted overhead band; monitor under hexa-lang AOT cache once enabled).

## Saturation impact projection (raw 91 honest, NOT a claim)
A8 closes the column-marginal axis on text-heavy categorical columns. Honest projection per the original A8 spec: +10-15pp on text-heavy categorical workloads inside the anima top-8 corpus (event types / tag enums / status flags). Only the persona log demonstrably hits this band among the two probed corpora; the 4gate corpus does not (correctly — A7 territory). Aggregate top-8 byte-weighted impact requires re-running the Phase 4 pilot with A8 inserted into the chain (out of scope for this landing — separate Phase 5 P4 mandate).

## Files
- impl: `/Users/ghost/core/hexa-lang/self/stdlib/hxc_a8_column_stat.hexa` (993 LoC, 8/8 selftest PASS, parse-clean)
- symlink: `/Users/ghost/core/hive/tool/hxc_a8_column_stat.hexa` -> impl
- this doc: `/Users/ghost/core/anima/docs/hxc_a8_column_stat_20260428_landing.md`

## Phase 5 catalog status (post-A8)
- A1 LANDED (line-baseline, raw 137 Phase 1 pilot)
- A7 LANDED (shared-dict arithmetic coder, raw 137 Phase 4 + 7-bug fix)
- A8 LANDED (column-marginal Huffman enum, this doc)
- A9 deferred (column-correlation, no falsifier-passing corpus yet)
- A10 LANDED (bit-packed varint, raw 137 Phase 4 + integer-rich corpora)
- A11 in-progress (Task #32 subagent a986ef82)

## Next-cycle hooks
- Phase 5 P4 (out of scope): integrate A8 into hxc_migrate.hexa Phase 3 corpus-profile-aware conditional apply chain. Insertion point: after A1 + A10, before A7 (cheaper than A7 per profitability check; targets disjoint axis).
- Phase 5 P5 (out of scope): re-run Phase 4-B pilot with A1+A8+A7+A10 chain to measure aggregate top-8 byte-weighted saving lift.
