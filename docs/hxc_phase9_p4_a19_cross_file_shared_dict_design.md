# HXC Phase 9 P4 — A19 Cross-File Shared Dictionary Design

**Status**: DESIGN DOC + FIRST-TICK IMPLEMENTATION (PASS 1+2+2.5+3) — LIVE FIRE
on 6-repo full corpus DEFERRED to subsequent tick per A23-pattern honest first-tick
contract (8f8197d5 + d2f7a67a precedent).

**Author tick**: 2026-04-28 (post 53c711eb A25 v2 78.05% MEASURED; post d631a902
A18 v3-o2/v4/v6 batch land; post-A26 sparse PPM-D first-tick).

**Raw mandate scope**: raw 9 hexa-only / raw 18 self-host fixpoint / raw 47
cross-repo / raw 65+68 idempotent byte-eq / raw 71 falsifier-preregister /
raw 91 honest C3 / raw 137 cmix-ban + 80% Pareto / raw 142 D2 try-and-revert.

**Companion modules**:
- `hxc_a19_cross_file_fed.hexa` (existing): cross-file FEDERATION promoting
  algorithm-emitted header lines (`# schema:`, `# enum:`, `# colprefix:`, etc.)
  to a shared dict via `^D` sigil.
- `hxc_a19_cross_file_dict.hexa` (THIS first-tick): generic cross-file SHARED
  DICTIONARY promoting raw byte-sequence tokens (length 3-32 bytes) to a
  shared dict via `^Z` sigil. Operates on RAW bytes, not algorithm headers.

The two are ADDITIVE / ORTHOGONAL: federation captures structured emit
patterns from upstream algorithms; shared-dict captures repeating byte tokens
that no per-file algorithm noticed. They share the A19 family-tag because
both attack the cross-file repetition axis — but they are independent code
paths with disjoint sigils.

---

## 1. Motivation

### Reach claim (MEASURED baseline; PROJECTED A19 lift)

The 6-repo byte-weighted aggregate sits at **78.05% MEASURED** (53c711eb,
A25 v2 full deployment, 9,916,852 raw bytes / 383 files / 379 byte-eq PASS),
with **1.95pp residual gap** to the raw 137 80% Pareto frontier.

A26 (sparse PPM-D order-5) attacks the **text-heavy class CEILING** but is
capped at +0.6pp aggregate (text-heavy is only 7% of the byte share). To
close the 1.95pp residual, A19 must attack the larger byte-share classes:

| class            | byte share | saving | gap to 80% | A19 attack potential |
|------------------|-----------:|-------:|-----------:|---------------------:|
| json-heavy       |        53% |  91%   |   ACHIEVED |     n/a (already 91%)|
| **mixed-real**   |   **30%**  |  72%   |    -8pp    |   **+2.4pp aggregate** |
| text-heavy       |       ~7%  |  47%   |    -33pp   |   +0.6pp (A26 lever) |
| **small-file**   |    **5%**  | **0.6%**|   -79pp   |   **+4pp aggregate** |
| struct-audit     |       ~4%  |  74%   |    -6pp    |   +0.2pp |
| synthetic-rep    |       ~1%  |  7%    |    -73pp   |   +0.07pp |

The residual gap is **dominated by mixed-real (30% byte share, +2.4pp
potential) and small-file (5% byte share, +4pp potential)**. A19 cross-file
shared dictionary is the canonical lever for both classes:

- **Small-file**: per-file dict overhead amortization fails on 1-10KB files;
  promoting common tokens (`fn`, `let`, `return`, `if`, `else`, `match`,
  hexa stdlib identifiers, etc.) to a corpus-level shared dict collapses
  N×(per-file inline) to 1×(corpus dict) + N×(2-byte reference).
- **Mixed-real**: heterogeneous JSONL with repeating field names, enum
  values, and structural tokens that span files. A19 captures these even
  when the per-file algorithm path doesn't categorize them as "headers".

### A19 hypothesis (FALSIFIABLE)

A19 = **cross-file shared dictionary** = scan corpus → top-N most frequent
token sequences (length 3-32 bytes) → emit shared dict file → per-file
encoder substitutes dict tokens with 1-2 byte references.

**Hypothesis**: small-file class can advance from 0.6% to ≥10% in-sample
saving (target: closes ≥0.4pp aggregate), AND mixed-real class can advance
from 72% to ≥75% in-sample saving (target: closes ≥0.9pp aggregate). Combined
A19 + A26 close >1pp of the 1.95pp residual gap.

This is a **PROJECTION**, NOT a measurement on the wire axis. The first-tick
implementation measures the in-sample bound (estimator); subsequent-tick
LIVE FIRE measures the wire delta with chain-amortize check.

---

## 2. A19 first-tick scope (A23-pattern honest first-tick)

Mirroring A23 (8f8197d5) and A26 (post-d631a902) precedents:

### PASS 1: cross-file shared dictionary spec

- **Input**: array of corpus files (paths or in-memory text strings).
- **Token extraction**: forward sweep over each file, count all byte-token
  sequences of length `A19_TOKEN_LEN_MIN=3` through `A19_TOKEN_LEN_MAX=32`.
- **Aggregation**: across files, sum (occurrence_count × token_bytes) per
  unique token. Tie-break: lexicographic order (deterministic, raw 18
  self-host: same corpus → same dict).
- **Dictionary structure**: top-`A19_DICT_SIZE_MAX=256` tokens by total
  bytes saved. Index 0..255 fits in 1 byte after the sigil.
- **Wire reference format**: `^Z<XX>` where `^Z` is sigil and `XX` is a
  single byte (dict index 0-255). Total reference = 2 bytes (sigil + index).
  For inputs containing literal `^Z`, escape via `^Z^` prefix (mirrors A19
  federation `^D^` pattern).
- **Saving per substitution**: `(token_len - 2)` bytes per occurrence (1
  byte for sigil + 1 byte for index = 2 bytes wire cost). For `A19_TOKEN_LEN_MIN=3`:
  saving = 1 byte per substitution (small but real for high-frequency tokens).
- **Memory budget**: `A19_DICT_BUILD_MEM_LIMIT=50MB` on 9.92MB corpus
  (F-A19-3 falsifier gate).
- **Idempotent build**: same corpus → byte-identical dict file (raw 18
  self-host fixpoint).
- **raw 137 cmix-ban**: integer-only counts, lexicographic tie-break, no
  fp ops, no neural mixer.

### PASS 2: build spec

`a19_build_dict(corpus_files: array) -> A19Dict`

- Forward sweep extracts all length 3..32 byte windows from each file.
- Single global frequency map: `token_bytes -> [occurrence_count, file_count]`.
- Score = `occurrence_count * (token_bytes_len - 2)`. (Length-len token
  saves `len - 2` bytes per occurrence; multiply by count.)
- Filter: keep only tokens with `file_count >= 2` (singletons stay per-file).
- Sort by (score DESC, lexicographic ASC) → deterministic top-256.
- Emit dict structure:
  ```
  ^Z hxc-shared-dict v1
  # corpus_files: <N>
  # n_entries: <K>
  Z00 <token_len> <token_bytes_b64>
  Z01 <token_len> <token_bytes_b64>
  ...
  Zff <token_len> <token_bytes_b64>
  # checksum: <djb2-hex>
  ```
- Idempotency: byte-identical dict file across two consecutive builds on
  same corpus (F-A19-4 first-tick gate).

### PASS 2.5: in-sample estimator

`a19_estimate_savings(dict: A19Dict, file: string) -> int`

- Walk file; for each position, find longest dict token matching at this
  position (greedy match, length-priority then dict-order tie-break).
- Total saving = `sum_over_matches((token_len - 2))` bytes.
- This is an **IN-SAMPLE BOUND**, not the wire saving. Wire saving needs
  the encoder/decoder pair which is the subsequent-tick scope.
- Reports per-file estimated saving% for F-A19-1 small-file class gate.

### PASS 3: selftest fixtures (5)

| # | fixture                                          | assertion |
|---|--------------------------------------------------|-----------|
| 1 | dict build over 3 small mixed-real files         | top-N dict captured ≥ 3 tokens with file_count ≥ 2 |
| 2 | round-trip byte-eq on 234 B JSON file            | a19_decode(a19_encode(file)) == file (first-tick wire = identity) |
| 3 | short-input passthrough (raw 65)                  | a19_encode(tiny) == tiny below MIN_BYTES |
| 4 | dict determinism (2 consecutive builds)          | byte-identical dict on same corpus |
| 5 | in-sample bound on 6-repo mixed-real slice       | a19_estimate_savings ≥ 10% on top-N=64 dict |

### PASS 4: A23-pattern explicit "LIVE FIRE deferred"

Following A23 lines 64-75 + A26 first-tick disclosure pattern, this tick:
- IMPLEMENT PASS 1+2+2.5+3 + 5 selftest fixtures.
- LIVE FIRE on representative 6-repo corpora = **subsequent tick (NOT
  first tick)**.
- Wire encoder/decoder = identity passthrough on first-tick (raw 91
  honest C3: no fabricated saving on wire axis); subsequent-tick wire =
  greedy substitution + escape sigil.

---

## 3. Falsifier preregister (raw 71 falsifier-retire)

| ID         | spec                                                      | trip → action |
|------------|-----------------------------------------------------------|---------------|
| F-A19-1    | a19_estimate_savings < 5% on small-file class 6-repo slice | retract small-file attack hypothesis |
| F-A19-2    | round-trip byte-eq fail on any selftest fixture            | retract entire A19 first-tick |
| F-A19-3    | dict build memory > 50MB on 9.92MB corpus                  | retract dict-build budget |
| F-A19-4    | dict determinism fail (2 consecutive builds differ)        | retract integer-only deterministic claim → identity-only mode |
| F-A19-5    | A19 + A18 chain saving < A18 standalone (chain-amortize)   | retract production-chain placement |
| F-A19-6    | top-N=64 NOT minimal across {32, 64, 128, 256} sweep       | retract size tuning |

**First-tick falsifier resolution**:
- F-A19-1: gated by selftest F5 (in-sample bound on mixed-real slice).
- F-A19-2: gated by selftest F2 (round-trip byte-eq).
- F-A19-3: DEFERRED — first-tick build runs on small selftest corpus only.
- F-A19-4: gated by selftest F4 (determinism).
- F-A19-5: DEFERRED to subsequent-tick LIVE FIRE.
- F-A19-6: DEFERRED to subsequent-tick sweep over {32, 64, 128, 256}.

---

## 4. Honest C3 disclosure (raw 91)

This document + first-tick implementation is **DESIGN + IN-SAMPLE
ESTIMATOR ONLY**. The following are NOT yet measured:

- A19 actual wire saving on small-file class.
- A19 actual wire saving on mixed-real class.
- A19 actual wire saving on 6-repo aggregate.
- A19 + A18 chain-amortize delta.
- A19 top-N size sweep optimum (32 vs 64 vs 128 vs 256).
- A19 dict build memory on full 9.92MB corpus.

The following ARE measured (cite-backed):

- 78.05% byte-weighted 6-repo aggregate (53c711eb, A25 v2 full deploy).
- A26 first-tick selftest 5/5 PASS (post-d631a902).
- A23 first-tick pattern (8f8197d5) — proven precedent for first-tick
  saving-axis report + wire-axis null disclosure.

The following PROJECTIONS are explicitly LABELED:

- "+4pp aggregate from small-file class" — **PROJECTION** pending
  subsequent-tick LIVE FIRE on 6-repo small-file slice.
- "+2.4pp aggregate from mixed-real class" — **PROJECTION** pending
  subsequent-tick LIVE FIRE on 6-repo mixed-real slice.
- "Combined A19 + A26 close >1pp of 1.95pp residual gap" — **PROJECTION**.

---

## 5. Implementation sequencing

1. **This turn (current)**: Design doc lands; first-tick module lands at
   `/Users/ghost/core/hexa-lang/self/stdlib/hxc_a19_cross_file_dict.hexa`
   with PASS 1+2+2.5+3; selftest 5/5 PASS interp; witness ledger lands.
2. **Subsequent turn 1**: A19 wire encoder + decoder (greedy substitution
   + escape sigil) + AOT build + LIVE FIRE on 6-repo small-file slice +
   mixed-real slice. Per-class measurement gate F-A19-1.
3. **Subsequent turn 2**: top-N size sweep {32, 64, 128, 256} → F-A19-6
   resolution. Chain-amortize check vs A18 → F-A19-5 resolution.
4. **Subsequent turn 3** (conditional on F-A19-1 NOT_TRIPPED): A19 LIVE
   integration in production hxc_migrate pipeline. 6-repo aggregate
   re-measurement; raw 137 80% Pareto verdict update.

Each turn delivers ONE coherent measurable artifact. No turn fabricates
measurements that did not run.

---

## 6. References

- A23 first-tick precedent: 8f8197d5 (Phase 12 P1 sparse PPM order-5)
- A26 first-tick precedent: post-d631a902 (Phase 12 P4 sparse PPM-D)
- A25 v2 full deployment: 53c711eb (78.05% MEASURED)
- A18 v3-o2/v4/v6 batch land: d631a902
- A19 federation companion: `/Users/ghost/core/hexa-lang/self/stdlib/hxc_a19_cross_file_fed.hexa`
- raw 137 80% Pareto frontier: hive d1c61bc91 (raw 137 v6)
- A19 first-tick witness:
  `/Users/ghost/core/anima/state/format_witness/2026-04-28_a19_first_tick_implementation.jsonl`
