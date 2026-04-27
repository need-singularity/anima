# HXC Phase 9 P0: A9 Hexa-Native Tokenizer Design

**Date**: 2026-04-28
**Phase**: 9 P0 design
**Unblocks**: raw 86 (hexa-native tokenizer deferred dependency)
**Targets**: 3 content classes blocked by absence of A9
- anima `alm_r13_4gate_pass_subset.jsonl` (980KB at 24%)
- hive `raw_addition_requests/registry.jsonl` (15KB at 1%)
- nexus `meta_engine_evolution_log.jsonl` (53KB at 5%) + 9 other small text-heavy files

## Problem statement

Current 10-algorithm catalog (A1+A4+A7+A8+A10+A11+A12+A13+A14+A15) handles
structural repetition (sub-trees, columns, rows) but NOT natural-language
text repetition. Long-form text fields (LLM training data, Korean prose,
narrative summaries) have lexical repetition (common words, prefixes) that
no current algorithm captures.

Empirical evidence:
- alm_r13 24% saving = pure A1 schema-hash dedup (no A4/A8/A12/A13 fire)
- raw_addition_requests 1% saving (5 rows, 15KB → 15KB-150B)
- meta_engine_evolution_log 5% (23 rows, 53KB → 50KB)

These corpora have content like:
- `"User asked how hive raw can leverage hexa-lang's new evolve_attr_seal..."`
- `"메타엔진 생애주기 log 첫 기록. 지도·창발 본체 dormant..."`
- `"axes_acted":["E2","K2","B1"],"axes_noop":["A1","A2","A3","A4","A5"]`

Common English words (`the`, `and`, `of`), Korean morphemes, repeated
identifiers (`raw`, `kick`, `failed`) appear hundreds of times but no
column-level or sub-tree-level repetition.

## A9 design: byte-pair encoding (BPE) variant

### Why BPE
- Pure algorithmic (no neural network → preserves raw 9 hexa-only)
- Captures lexical repetition at sub-word level
- Pre-trained tokenizer (cl100k or similar) gives 3-4× compression on
  English/Korean prose; fully data-driven build also viable
- Decode is deterministic byte-eq (raw 65 + 68 idempotent compatible)

### Algorithm spec

PASS 1 — corpus-wide vocabulary build:
- Read all rows in HXC v1 stream (post-A1)
- Initialize vocabulary as 256-byte alphabet (all ASCII + UTF-8 lead bytes)
- Iteratively find most-frequent adjacent byte-pair, merge into new token
- Repeat until vocabulary reaches V tokens (default V=4096)
- Each new merge gets a unique 2-byte symbol (0x80-0xFF first byte +
  arbitrary low byte for the 256+ token slots)

PASS 2 — encode each cell value:
- Greedy match longest token from vocabulary
- Replace matched substring with token symbol (2 bytes)
- Emit non-matched bytes as literal (single byte)

PASS 3 — emit vocabulary header:
- `# tokenizer:s<N> v=BPE-v1 size=<V>`
- `# tokens:s<N> 0=<bytes>;1=<bytes>;...;<V-1>=<bytes>`
- (Or compact base64 dump for large vocabularies)

### Encoding sigil

Use `^T` to mark A9-tokenized cells. Disambiguation: cells naturally
starting with `^T` get escape `^T^` prefix.

### Wire format example

```
v1 (post-A1):
@s1 "User asked how hive raw can leverage hexa-lang's evolve_attr..."

v2 (post-A1+A9):
# tokenizer:s1 v=BPE-v1 size=4096
# tokens:s1 0= 1=,| 2=":| ...
@s1 ^T<bytes representing tokens>
```

### Idempotency contract (raw 65 + 68)

- encode(decode(x)) == x for any A9 stream
- decode(encode(y)) == y for any HXC v1 stream
- Same input + same vocabulary → byte-identical output

### Falsifiers (raw 71)

- F-A9-1: saving < 0.10 byte-eq on synthetic English-text fixture → reject
- F-A9-2: encode/decode round-trip not byte-eq → reject
- F-A9-3: encode latency > 50ms per 1KB content → reject (would block
  hxc_migrate single-pass throughput)
- F-A9-4: vocabulary build memory > 100MB during PASS 1 → reject (Mac
  jetsam SIGKILL risk)

## Implementation phases

### Phase 9 P1: minimal BPE (vocabulary build + encode)

~250 LoC pure-hexa:
- byte-pair frequency counting (hash map + 2-byte key)
- iterative merge selection (max-heap or argmax-scan)
- greedy encode with longest-prefix-match
- hexa-native: pure string + array operations, no external library

Selftest fixtures:
- English text repetition (3× compression projection)
- Korean morpheme repetition (2.5× projection)
- Mixed JSON text (1.8× projection)
- Round-trip byte-eq verification

### Phase 9 P2: vocabulary-from-pretrained-source

Optional Tier-2 enhancement: load existing cl100k-style vocabulary if
available. Skips PASS 1 corpus scan, uses pre-built tokenizer for
generalized text. Saves significant runtime on small corpora.

### Phase 9 P3: integration with hxc_migrate

Add A9 plug-in slot in secondary stacking pass:
```hexa
if _A9_available() && len(profile) > 5 && parse_int(profile[5]) >= 4 {
    let pre = len(stage)
    let trial = _A9_apply(stage)
    if len(trial) < pre && len(trial) > 0 { stage = trial; chain.push("A9") }
}
```

Try-and-revert preserved (raw 65 + 68 idempotent).

### Phase 9 P4: cross-file vocabulary (optional, A9+A16 hybrid)

For corpora with shared text across files (nexus 96 small files), build
ONE shared vocabulary across all files, emit once at corpus level. This
is the natural A9 + A16 fusion — same dictionary serves both purposes.

## Projected impact

### Single-file projections

| corpus | current | A9 P1 projection | A9 P3 | A9 P4 (cross-file) |
|---|---:|---:|---:|---:|
| anima alm_r13 (980KB) | 24% | 50% | 55% | 60% |
| hive raw_addition_requests (15KB) | 1% | 30% | 35% | 50% (with corpus dict) |
| nexus meta_engine_evolution (53KB) | 5% | 25% | 30% | 45% |

### Cross-repo aggregate projections (Phase 9 P3 deployment)

| repo | Phase 8 FINAL | Phase 9 projection | Δ |
|---|---:|---:|---:|
| anima | 29% | 50% | +21pp |
| hive | 69% | 73% | +4pp |
| nexus | 43% | 50% | +7pp |
| hexa-lang | 82% | 84% | +2pp |
| airgenome | 82% | 82% | 0pp |
| n6-architecture | 4% | 6% | +2pp |
| **6-repo aggregate** | **48%** | **~58-60%** | **+10-12pp** |

## Phase 9 implementation cost

- Phase 9 P1 (minimal BPE): ~3-4 hours, ~250 LoC
- Phase 9 P2 (pretrained vocab): ~2 hours, ~150 LoC (optional)
- Phase 9 P3 (hxc_migrate integration): ~30 min, ~30 LoC
- Phase 9 P4 (cross-file fusion): ~3-4 hours, ~200 LoC
- Total Phase 9 minimal viable: ~3.5 hours, ~280 LoC for P1+P3
- Total Phase 9 full: ~10 hours, ~630 LoC for all phases

## Phase 9 P0 verdict

A9 hexa-native tokenizer is the **universal unblock** for 3 separate content
classes (LLM training corpus, NL summary fields, mixed JSON-with-Korean-text).
Single algorithm closes ~10-12pp byte-weighted gap across cross-repo aggregate.

Trade-offs (raw 91 honest C3):
- BPE encode latency: ~1-5ms per KB on pure-hexa interpreted runtime —
  may approach F-A9-3 threshold on large corpora
- Vocabulary memory: ~1-4MB for V=4096 vocabulary — well below F-A9-4
  threshold of 100MB
- Round-trip byte-eq: deterministic and trivially provable

Phase 9 P1 implementation can be scheduled across multiple cron ticks
(~3-4 hours total). Each tick can land 50-80 LoC of the BPE module
(byte-pair counter → merge selector → encoder → decoder → selftest fixtures).

raw 9 hexa-only · raw 65 + 68 idempotent · raw 91 honest C3 · raw 86 unblock ·
raw 137 cross-repo universal mandate.
