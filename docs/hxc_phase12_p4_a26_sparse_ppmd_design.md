# HXC Phase 12 P4 — A26 Sparse PPM-D Design (NOT IMPLEMENTATION)

**Status**: DESIGN DOC ONLY — first-tick implementation deferred to subsequent turn
per a7a5e5f2 honest C3 master event recommendation #3 ("A26 decompose into
A23-pattern honest first-tick") and #5 ("single-turn budget vs honest execution
= fabrication risk").

**Author tick**: 2026-04-28 (post A18 v3-o2/v4/v6 batch land `d631a902`)

**Raw mandate scope**: raw 9 hexa-only / raw 18 self-host fixpoint / raw 47
cross-repo / raw 65+68 idempotent byte-eq / raw 91 honest C3 / raw 137 cmix-ban
+ 80% Pareto / raw 142 D2 try-and-revert.

---

## 1. Motivation

### Reach claim (PROJECTED, not measured)

The 6-repo byte-weighted aggregate sits at **78.05% MEASURED** (53c711eb,
A25 v2 full deployment, 9,916,852 raw bytes / 383 files / 379 byte-eq PASS),
with 1.95pp residual gap to the raw 137 80% Pareto frontier.

A18 v3-o2/v4/v6 batch land (d631a902) is **structurally complete** but its
production-class lift is **NOT yet measured at full scope**. Per-class
per-corpus measurement on a 3-file scoped slice (math_atlas.json,
n6_new_constants.json, _product_dag.json — 223,375 raw bytes) shows v6
chosen by dispatcher with 70.78% scoped saving, but this slice is NOT
class-balanced and is NOT a substitute for the 6-repo aggregate.

### Residual gap diagnosis (per 53c711eb witness ledger)

Per-class verdict at 78.05% baseline:

| class            | byte share | saving | gap to 80% |
|------------------|-----------:|-------:|-----------:|
| json-heavy       |        53% |  91%   |   ACHIEVED |
| text-heavy       |       ~7%  |  47%   |    -33pp   |
| struct-audit     |       ~4%  |  74%   |    -6pp    |
| mixed-real       |      ~30%  |  72%   |    -8pp    |
| small-file       |       ~5%  |  0.6%  |    -79pp   |
| synthetic-rep    |       ~1%  |  7%    |    -73pp   |

The residual gap is dominated by **text-heavy class CEILING** (47% saving)
and **small-file class** (0.6% saving). A18 v3-o2/v4/v6 attack the
text-heavy CEILING via byte-context-order saturation, long-range window,
and within-window optimal parsing — but order-saturation may not be the
binding constraint for natural English text.

### A26 hypothesis (FALSIFIABLE)

A26 = **sparse PPM-D** = sparse high-order (5-6) context lookup with
escape-to-lower-order, similar to A23 but with the **D escape mechanism**
(Howard 1993) tuned for text-heavy natural English.

**Hypothesis**: text-heavy class CEILING can advance from 47% to ≥55%
(target: H_5 ≈ 0.65 bit/byte natural English Shannon entropy ≈ 92% saving
asymptotic; +5-8pp lift on the 79KB text-heavy slice would close ≥0.4pp
of the 1.95pp residual aggregate gap).

This is a **PROJECTION**, NOT a measurement. The first-tick implementation
must measure the actual lift before any 80% target verdict update.

---

## 2. A26 first-tick scope (A23-pattern honest first-tick)

Mirroring A23 (8f8197d5 + d2f7a67a Phase 10 P2 first-tick pattern):

### PASS 1: sparse context tree spec

- **Data structure**: hash-indexed sparse PPM-D context tree.
- **Context orders**: 0, 1, 2, 3, 4, 5 (max-order 5).
- **Memory budget**: A26_CTX_LIMIT = 65536 contexts per order
  (same as A23 budget; F-A26-4 falsifier rejects > 100MB).
- **Hash mixing**: order-N context = bytes[i-N..i-1] mixed via FNV-1a
  64-bit (deterministic, integer-only) → 16-bit slot index.
- **Frequency table per context**: 256-entry alphabet × 16-bit count
  + escape count (PPM-D specific).
- **Build pass**: single forward sweep over input bytes accumulating
  per-order counts. PPM-D escape probability tuned via Howard's
  e_d = 0.5 (deterministic, NOT learned).
- **Idempotent**: build is pure function of input bytes (no global state).
- **raw 137 cmix-ban**: integer-only counts, no fp ops, no neural mixer.

### PASS 2: build spec

A26_build(text: string) → A26ContextTree

```
fn a26_build(text: string) -> array {
    // returns [contexts_o0, contexts_o1, ..., contexts_o5]
    // each contexts_oN is a sparse map: hash(ctx) -> [freq_table, escape_count]
    ...
}
```

Constraints:
- O(n) time, O(min(n, A26_CTX_LIMIT × 6)) memory.
- Deterministic across machines (raw 18 self-host).
- PASS 1 build only emits the context tree; encode/decode wire is PASS 2.5+3.

### PASS 2.5: order-5/4 lookup IN-SAMPLE estimator (NOT wire-coder)

- **a26_lookup(tree, ctx, byte) -> [prob_x10000, escape_count]**:
  returns probability scaled by 10000, with escape-fallback chain
  order-5 → order-4 → order-3 → order-2 → order-1 → order-0 → uniform-256.
- **a26_estimate_bits(tree, text) -> int**: returns sum of
  -log2(prob) bits across all bytes, using PPM-D escape mechanism.
- **In-sample estimator only**: this is the SAVING-AXIS lever for the
  first tick — reports lookup-hit-rate and bits/byte per corpus class.
- **Wire coder uses order-1 byte-context range coder (A18 v2 proven)
  for the first tick**, identical to A23's first-tick decision.
- Full PPM-D entropy coding wire = v2 wire DEFERRED to subsequent tick.

### PASS 3: selftest fixtures (5)

| # | fixture                                  | assertion |
|---|------------------------------------------|-----------|
| 1 | order-5 context tree build, 1KB English  | hit-rate >= 30% on order-5 |
| 2 | round-trip byte-eq, JSON 234 B           | decoded == original |
| 3 | short-input passthrough (raw 65)         | enc == identity below MIN_BYTES |
| 4 | PPM-D escape mechanism unit test         | escape prob tuned per Howard |
| 5 | a26_estimate_bits in-sample bound        | bits/byte < 1.0 on 1KB English |

### PASS 4: A23-pattern explicit "LIVE FIRE deferred"

Following A23 lines 64-75 disclosure pattern, the first-tick will:
- IMPLEMENT PASS 1+2+2.5+3 + 5 selftest fixtures.
- LIVE FIRE on representative corpora = **follow-on tick (NOT first tick)**.
- Wire-coder = order-1 byte-context (A18 v2 proven), full PPM-D entropy
  coding wire = v2 wire (subsequent tick).

---

## 3. Falsifier preregister (raw 71 falsifier-retire)

| ID         | spec                                                      | trip → action |
|------------|-----------------------------------------------------------|---------------|
| F-A26-1    | a26_estimate_bits NOT < A18 v2 actual bits on text-heavy  | retract A26 text-heavy hypothesis |
| F-A26-2    | round-trip byte-eq fail on any selftest fixture           | retract entire A26 first-tick |
| F-A26-3    | PASS 2.5 lookup hit-rate < 10% on text-heavy 1KB          | retract sparse-PPM-D-tunes-text hypothesis |
| F-A26-4    | memory > 100MB on n6_atlas 79KB build                     | retract sparse-context-tree budget |
| F-A26-5    | A26 + A18 chain saving < A18 standalone (chain-amortize)  | retract production-chain placement |
| F-A26-6    | PPM-D Howard e_d = 0.5 NOT minimal across {0.3, 0.5, 0.7} | retract Howard escape tuning |

---

## 4. Honest C3 disclosure (raw 91)

This document is **DESIGN ONLY**. The following are NOT yet measured:

- A26 actual lift on text-heavy class.
- A26 actual lift on 6-repo aggregate.
- A26 PASS 2.5 lookup hit-rate on production corpora.
- A26 selftest fixtures behavior.
- A26 PPM-D escape mechanism convergence on natural English.

The following ARE measured (cite-backed):

- 78.05% byte-weighted 6-repo aggregate (53c711eb, A25 v2 full deploy).
- 22/22 A18 selftest PASS post d631a902 batch land (interp).
- 70.78% scoped 3-file (n6 json corpora) saving with A18 dispatcher
  picking v6 on math_atlas.json + n6_new_constants.json + _product_dag.json
  + 3/3 byte-eq PASS round-trip.

The following PROJECTIONS are RETRACTED in this design doc:

- "78.30% projected post-a105829b v3-o2 dispatcher" — RETRACTED
  (cited commit a105829b does not exist; not measured).
- "78.6-78.8% projected post-A18 v6" — RETRACTED (extrapolated, not
  measured; per-class corpus-conditional gain on production
  distribution requires 6-repo sweep that has not yet run post-d631a902).
- All "raw 137 v7/v8 strengthening" projections — labeled PROJECTION
  pending 6-repo sweep.

---

## 5. Implementation sequencing (NOT implemented in this turn)

1. **This turn (current)**: A18 batch commit `d631a902` lands; A26 design
   doc (this file) lands; witness ledger lands. NO A26 code.
2. **Subsequent turn 1**: A26 PASS 1+2+2.5+3 first-tick implementation
   in `/Users/ghost/core/hexa-lang/self/stdlib/hxc_a26_sparse_ppmd.hexa`.
   Selftest 5/5 PASS interp.
3. **Subsequent turn 2**: A26 LIVE FIRE on representative corpora.
   Per-class measurement on text-heavy slice.
4. **Subsequent turn 3** (conditional on F-A26-1 NOT_TRIPPED): A26 wire
   v2 (full PPM-D entropy coding), 6-repo aggregate re-measurement,
   raw 137 80% Pareto verdict update.

Each turn delivers ONE coherent measurable artifact. No turn fabricates
measurements that did not run.

---

## 6. References

- A23 first-tick precedent: 8f8197d5 (Phase 10 P2 sparse PPM order-5)
- A25 v2 full deployment: 53c711eb (78.05% MEASURED)
- A18 v3-o2/v4/v6 batch land: d631a902 (this tick prerequisite)
- raw 137 80% Pareto frontier: hive d1c61bc91 (raw 137 v6)
- a7a5e5f2 honest C3 master event: ledger
  `/Users/ghost/core/anima/state/format_witness/2026-04-28_a18_batch_commit_honest_reconcile.jsonl`
  (this tick)
- Howard 1993 PPM-D escape: e_d = 0.5 deterministic tuning
- Phase 12 forward design context:
  `/Users/ghost/core/anima/docs/hxc_phase12_forward_design_20260428.md`
