# HXC Phase 9 P4: A16 Cross-File Shared Dictionary Design

**Date**: 2026-04-28
**Phase**: 9 P4 design (P4.0)
**Unblocks**: nexus 96-file mixed-inventory corpus (43% → 60-70% projection)
**Companion algorithm**: A9 hexa-native tokenizer (Phase 9 P0/P1)
**Targets**:
- nexus 96 files avg 6KB — 43% byte-weighted (-37pp gap to 80%)
- n6-architecture 69 files (atlas + clay_millennium) — 4% byte-weighted (-76pp; entropy-bound, but per-file overhead removable)
- hive 53 files triad_audit / honesty_triad / blockers — 69% byte-weighted (-11pp)

## 1. Problem statement

Phase 8 closure surfaced a saturation point on **many-small-files** corpora:
each file individually carries schema, enum, column-prefix, constant-column,
and row-prefix dictionary headers. For nexus where avg file size is 6KB,
the per-file dictionary tax can amount to 800-1500 bytes — 13-25% of raw
content — and this overhead is paid 96 times with near-zero amortization
across files.

n6 sub-agent verdict on `tools/concat-lzma.sh`-style cross-file compression:
**concat-lzma achieves +17pp byte-weighted savings over per-file lzma** on
identical corpora, purely from cross-file shared-dictionary effects. HXC's
own per-file dictionaries replicate this same waste at a more granular
level (schema-header / enum-table / column-prefix / row-prefix layers).

**Hypothesis (raw 71 candidate)**: a repo-level shared dictionary,
referenced by each per-file HXC stream, will collapse the per-file overhead
multiplier from N×(per-file dict) to 1×(repo dict) + N×(small reference),
unlocking the 43% → 80% gap on nexus and similar corpora.

## 2. Algorithm spec

### Sigil

`^D<dict_id>` — shared-dict reference, where `<dict_id>` indexes into the
repo-level shared dictionary file. Disambiguation: cells starting with
literal `^D` get escape `^D^` prefix.

### PASS 1 — corpus scan

- Walk all `*.jsonl` (or other configured) files under target corpus root
- For each file, extract:
  - schema fingerprint set
  - enum value set per column
  - column-prefix candidate set (top-K by frequency)
  - constant-column projection
  - row-prefix candidate set
- Aggregate union across all files; mark each pattern with `(occurrence_count, file_count, total_bytes)`
- Time complexity: O(corpus_total_bytes)

### PASS 2 — dict build

- Score each candidate by `total_bytes_saved = (occurrence_count × pattern_bytes) − reference_overhead`
- Retain only candidates with `file_count >= 2` (single-file pattern stays in per-file dict)
- Emit shared dictionary file `state/hxc/_shared_dict.hxc`:
  ```
  # hxc-shared-dict v1
  # corpus: <root_path>
  # built: <iso8601>
  # algo: A16 v1
  D0 schema=<sha-prefix> "<canonical_schema_string>"
  D1 enum=<col_id> "<enum_value>"
  D2 colprefix=<col_id> "<prefix_bytes>"
  D3 const=<col_id> "<value>"
  D4 rowprefix "<prefix_bytes>"
  ...
  Dn ...
  # checksum: <sha256-of-dict-body>
  ```
- Time complexity: O(unique_pattern_count × log(N))

### PASS 3 — per-file encode

- Each file's HXC encoder loads `_shared_dict.hxc` into memory
- For each schema/enum/prefix/const/row-prefix that matches a shared-dict
  entry, emit `^D<dict_id>` instead of inlining the full pattern
- Patterns NOT in shared dict fall back to per-file inline dictionary
  (legacy A1+A4+A8+A12+A13+A14 path) — additive, not replacement
- Per-file footer records `# shared-dict-ref: <path> checksum=<sha>` for
  decode-time verification

### PASS 4 — decode

- Decoder reads per-file footer to find `_shared_dict.hxc` path + checksum
- Loads + checksum-validates shared dict
- Builds id → pattern reverse map
- Substitutes `^D<id>` references with the original pattern
- Per-file inline dict patterns continue working as before (backward compat)

### Compatibility

| algo | A16 stacking |
|---|---|
| A1 (schema delta) | YES — A16 promotes schema-headers to shared dict |
| A4 (sub-tree dedup) | YES — A16 promotes shared sub-trees to shared dict |
| A7 (shared-dict arithmetic) | NATURAL FUSION — A16 generalizes A7 to repo level |
| A8 (column-stat enum) | YES — A16 promotes shared enum tables |
| A10 (bit-packed varint) | ORTHOGONAL |
| A11 (cross-row delta) | ORTHOGONAL |
| A12 (column-prefix multi) | YES — A16 promotes shared col-prefix dicts |
| A13 (constant-column elim) | YES — A16 promotes shared const values |
| A14 (row-prefix) | YES — A16 promotes shared row-prefix patterns |
| A15 (nested-array subschema) | YES — A16 promotes shared sub-schemas |
| A9 (BPE tokenizer) | **FUSION** — A9 vocabulary IS a shared dict (see §5) |

## 3. Corpus analysis (Pass-1 measurement)

### nexus (96 files, ~576KB total)

| metric | value |
|---|---:|
| total bytes (current raw) | ~576 KB |
| total bytes (Phase 8 final HXC) | ~328 KB (43% saved) |
| per-file dict overhead avg | ~900 B |
| 96 files × dict overhead | ~86 KB (15% of raw) |
| common schemas across files | ~12 distinct |
| common enum values | ~80 across 12 schemas |
| common header sigils (`# schema:`, `# enum:`, ...) | ~6 fixed |
| projected A16 saving (raw) | ~70 KB additional (overhead → 1× repo dict ~16 KB) |
| **projected A16 byte-weighted** | **55-58%** (+12-15pp over Phase 8) |
| projected A9 + A16 fusion | **65-70%** (+22-27pp over Phase 8) |

### n6-architecture (69 files: atlas + clay_millennium)

| metric | value |
|---|---:|
| total bytes (current raw) | ~3.2 MB |
| total bytes (Phase 8 final HXC) | ~3.07 MB (4% saved) |
| per-file dict overhead avg | ~600 B |
| 69 files × dict overhead | ~41 KB (1.3% of raw) |
| common prefix patterns (atlas IDs, clay theorem refs) | ~30 |
| common sub-tree patterns | ~10 |
| projected A16 saving (raw) | ~30 KB (~1pp byte-weighted) |
| **projected A16 byte-weighted** | **5-6%** (+1-2pp; n6 is entropy-bound) |
| projected A9 + A16 fusion | **8-10%** (BPE catches morpheme repetition; ceiling remains low) |

n6 remains entropy-bound; A16 is not the unblock. Listed for completeness.

### hive (53 files: triad_audit + honesty_triad + blockers)

| metric | value |
|---|---:|
| total bytes (current raw) | ~520 KB |
| total bytes (Phase 8 final HXC) | ~161 KB (69% saved) |
| per-file dict overhead avg | ~1.2 KB |
| 53 files × dict overhead | ~64 KB (12% of raw) |
| common schemas (triad_audit / honesty_triad / blockers) | ~5 distinct |
| common enum values (verdict, axis, severity) | ~40 |
| common sub-trees (signed-witness blocks) | ~8 |
| projected A16 saving (raw) | ~40 KB additional |
| **projected A16 byte-weighted** | **74-77%** (+5-8pp over Phase 8) |
| projected A9 + A16 fusion | **77-80%** (+8-11pp; hits 80% target) |

## 4. Implementation phases

| phase | LoC | description |
|---|---:|---|
| **P4.0** | 0 | THIS design document |
| P4.1 | 150 | corpus scanner — Pass 1 walk + pattern aggregation |
| P4.2 | 200 | dict builder — Pass 2 scoring + shared-dict file emit |
| P4.3 | 150 | per-file encode — Pass 3 reference resolution + sigil emit |
| P4.4 | 100 | decode — Pass 4 dict load + reference expansion |
| P4.5 | 80 | hxc_migrate `--corpus-mode` CLI option + selftest harness |
| **TOTAL** | **~680** | pure-hexa, raw 9 hexa-only compliant |

Each phase is independently testable, can land across multiple cron ticks
(60-90 min per phase). Phase 9 P4 minimal viable = P4.1 + P4.2 + P4.3 + P4.4
(no CLI integration) ≈ 600 LoC ≈ 5-6 hours.

## 5. A9 + A16 fusion analysis

A9 (Phase 9 P1) BPE vocabulary build is **already corpus-scope-flexible**:
- Single-file mode: PASS 1 scans one file, emits per-file vocabulary header
- Cross-file mode: PASS 1 scans entire corpus, emits ONE shared vocabulary

The shared-vocabulary mode IS A9 + A16 fusion. No additional code beyond
extending A9 PASS 1 to accept a corpus-root parameter and routing the
output to `_shared_dict.hxc` (same file format A16 already emits).

### Projected fusion impact

| corpus | Phase 8 final | A9 single-file | A9 + A16 cross-file |
|---|---:|---:|---:|
| nexus aggregate | 43% | 50% | **65-70%** |
| nexus meta_engine_evolution_log (53KB) | 5% | 25% | **45%** |
| hive aggregate | 69% | 73% | **77-80%** |
| anima alm_r13 (980KB single-file) | 24% | 50% | **55%** (single-file dominates) |
| n6 atlas-convergence | 4% | 6% | **8-10%** (entropy ceiling) |

Cross-repo aggregate Phase 9 P4 projection: **48% → ~62-65%** (+14-17pp).

## 6. Falsifiers preregistered (raw 71)

| id | condition | action |
|---|---|---|
| **F-A16-1** | byte-weighted saving < 0.05 on multi-file corpus (nexus or hive) | reject A16; per-file dict was already optimal |
| **F-A16-2** | shared dict file missing/checksum-mismatch at decode time | hard fail OR fallback to per-file embed (configurable) |
| **F-A16-3** | encode latency > 100ms per 1KB content | reject; would block hxc_migrate single-pass throughput |
| **F-A16-4** | round-trip byte-eq fails on multi-file corpus | reject; raw 65 + 68 idempotent violation |

Tier-2 (advisory, not blocking):
- A16 should not REGRESS any single-file corpus (try-and-revert preserved)
- shared dict must be self-describing (decode possible without external schema)
- `_shared_dict.hxc` must be hexa-readable plain text (not binary)

## 7. raw candidate proposed

**raw NNN: `algorithm-cross-file-shared-dictionary-mandate`**

Statement: For any corpus with ≥10 files averaging <16KB, HXC migration
MUST attempt cross-file shared dictionary (A16) before declaring final
saving. If A16 produces <0.05 additional byte-weighted saving, fall back
to per-file dict (try-and-revert). Many-small-files saturation is a
known anti-pattern (Phase 8 closure root cause); raw mandates the
mitigation path.

Rationale:
- Phase 8 saturation root cause #1: per-file dict overhead non-amortized
- n6 sub-agent verdict: concat-lzma +17pp on multi-file corpora
- HXC catalogue completeness: A1-A15 cover within-file repetition; A16
  closes cross-file repetition gap
- Compatible with raw 9 hexa-only, raw 18 self-host, raw 65/68 idempotent,
  raw 91 honest C3

Fallback contract: if shared dict produces NET worse compression (e.g.,
overhead > savings on tiny corpora), encoder MUST revert to per-file mode
without manual intervention. Try-and-revert is mandatory, not optional.

## 8. Phase 9 P4 verdict

A16 cross-file shared dictionary is the **second universal unblock** for
many-small-files saturation, complementary to A9 hexa-native tokenizer.
Combined deployment (A9 + A16 fusion) projects:
- nexus: 43% → 65-70% (+22-27pp)
- hive: 69% → 77-80% (+8-11pp; HITS 80% target)
- 6-repo aggregate: 48% → 62-65% (+14-17pp)

Trade-offs (raw 91 honest C3):
- One additional file per corpus (`_shared_dict.hxc`) — must be
  shipped/synced alongside per-file HXC streams
- Decode requires shared-dict availability — single-file portability
  reduced (mitigated by F-A16-2 fallback-to-embed mode)
- Build-time cost: corpus scan O(total_bytes) added to migration path
  (acceptable; offline batch operation)

Phase 9 P4 implementation can be scheduled across 5 cron ticks
(P4.1 → P4.5, ~60-90 min each), totaling ~680 LoC pure-hexa.

raw 9 hexa-only · raw 18 self-host · raw 65 + 68 idempotent · raw 71
falsifier-preregistered · raw 91 honest C3 · raw 137 cross-repo universal
mandate · raw NNN (proposed) cross-file shared dictionary mandate.
