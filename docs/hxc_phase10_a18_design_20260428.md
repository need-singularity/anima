# HXC Phase 10 P2 — A18 LZ-window + PPM order-4 Design

**Date**: 2026-04-28
**Phase**: 10 P2 (post-A17 PPMd order-3 ceiling discovery)
**Trigger**: A17 commit `a9ee2e43` measured 87% saving on text-heavy fixture; user
directive — push toward Shannon H_4 = 0.813 bit/byte → **90% asymptotic entropy**.
**Compliance**: raw 9 hexa-only · raw 18 self-host fixpoint · raw 65 + 68 idempotent ·
raw 71 falsifier-preregistered · raw 91 honest C3 · raw 137 cmix-ban (no neural mixer).

---

## 0. Honest framing (raw 91 C3 PARTIAL)

This document specifies the **complete** A18 algorithm. Implementation lands in
~5 cron ticks (estimated total ~900 LoC). **First tick** = this design doc +
~150 LoC of `hxc_a18_lz_ppm_order4.hexa` containing:

- LZ77 sliding-window data structure (struct + accessors)
- Match-finding stub (greedy parsing; lazy parsing deferred)
- PPM order-4 table extension stub (extends A17 4-table to 5-table)
- 1 selftest fixture (synthetic text repetition)
- PASS 1 build harness only — encode/decode emission DEFERRED

Subsequent ticks land LZ match emission, PPM order-4 encode/decode, integration
glue, 5+ selftest fixtures, and LIVE FIRE on Phase 10 P0/P1 corpora.

---

## 1. Algorithm rationale — why LZ + PPM order-4

A17 PPMd order-3 plateaus at ~84-87% on text-heavy because:
1. Order-3 misses long-range repetition (>3 bytes apart, common in struct/JSON).
2. Order-4 alone explodes the context tree memory (256^4 = 4G slots worst case)
   without the LZ prefilter — most order-4 contexts are sparse.

LZ77 sliding-window prefilter handles long-range repetition cheaply (offset+length
emission, O(1) table updates per byte). PPM order-4 then models the residual
short-range structure on top of the literal-byte fallback stream.

Combined target: 90% byte-weighted on n6 atlas + text-heavy (Shannon H_4 floor
= 0.813 bit/byte → 89.84% asymptote).

---

## 2. LZ77 sliding-window data structure

**Window**: 32 KB default (configurable via `A18_WINDOW_BITS`). Implemented as a
ring buffer over the input string `buf` with current position `p` and lookback
range `[max(0, p - W), p)`.

**Hash chain** (raw 18 self-host, integer-only):
- Hash function: `h(b0, b1, b2) = (b0 * 31 + b1) * 31 + b2` mod `A18_HASH_SIZE`
- `A18_HASH_SIZE = 16384` (2^14, fits in hexa native HashMap easily).
- `hash_head[h]` = most recent position with that 3-byte prefix (or -1 if none).
- `hash_prev[p]` = previous position with the same 3-byte prefix as position p.
- Insertion is O(1); match search walks `hash_prev` chain bounded by
  `A18_MAX_CHAIN = 32` (caps worst-case latency for F-A18-3 falsifier).

**Match emission** (LZ77 textbook):
- `match_len >= A18_MIN_MATCH` (3) → emit `(offset, length)` pair.
- Else → emit literal byte.
- Greedy parsing first; lazy parsing (1-byte lookahead) deferred to follow-on
  tick if F-A18-1 saving < 0.85 fires under greedy alone.

**Memory budget** (F-A18-4 target < 100MB on 10MB input):
- `hash_head`: 16384 * 4 B = 64 KB constant
- `hash_prev`: O(input_len) * 4 B = 40 MB on 10 MB input — within budget
- Window contents: 32 KB rolling — negligible

---

## 3. PPM order-4 extension from A17 order-3

A17 already builds 4 tables: order-0, order-1, order-2, order-3. A18 extends to
5 tables: order-0..order-4. Reuses A17's `_table_inc` / `_table_total` /
`_table_distinct` / `_table_count` primitives unchanged (raw 65 + 68
idempotent — A17 stream remains decodable by A18 decoder via order cap).

**Build pass**: same shape as A17 `a17_build`, but with `p >= 4` branch added
for order-4 context update. Time: O(N * 5) (5 table inc per byte). Memory: at
most 5 * (#distinct contexts) * fanout — empirically < 64 MB on 10 MB text.

**Lookup chain**: order-4 → order-3 → order-2 → order-1 → order-0 → raw.
Escape-method-D unchanged (P_esc = U / (T + U)).

**Streamability invariant**: same as A17 — incremental update during
encode/decode, no separate "training" pass.

---

## 4. Encoding sigil and stream layout

- `^L<bytes>` for LZ-prefiltered streams (literal/match emission)
- `^P<bytes>` for PPM order-4 residual streams
- A18 combined: `^L<lz-stream>^P<ppm-residual>` — two-segment stream

Sigil choice rationale: `^L` and `^P` are unused in A1-A17 catalog. `^L` matches
LZ family convention from gzip/lzma headers but uses our custom hexa-only encoding.

---

## 5. Falsifiers preregistered (raw 71)

| ID | Threshold | Purpose |
|---|---|---|
| F-A18-1 | saving < 0.85 on text-heavy fixture | core efficacy gate (90% target with margin) |
| F-A18-2 | encode/decode round-trip not byte-eq | idempotency (raw 65 + 68) |
| F-A18-3 | encode latency > 500ms per 1KB | LZ chain walk + PPM combined budget |
| F-A18-4 | window memory > 100MB on 10MB input | hash chain + window cap |

Failure modes: F-A18-1 fires → introduce lazy parsing; F-A18-3 fires → reduce
`A18_MAX_CHAIN`; F-A18-4 fires → reduce `A18_WINDOW_BITS` to 15 (16 KB).

---

## 6. Cron-tick LoC budget

| Tick | Scope | LoC | Cumulative |
|---|---|---:|---:|
| **1 (this)** | design doc + struct + match stub + PPM order-4 build + 1 selftest | **~150** | ~150 |
| 2 | LZ77 match emission + offset/length codec | ~200 | ~350 |
| 3 | PPM order-4 encode (range coder, escape chain) | ~250 | ~600 |
| 4 | PPM order-4 decode (mirror of encode) | ~150 | ~750 |
| 5 | LZ + PPM integration + 5 selftests + LIVE FIRE | ~150 | ~900 |

raw 91 honest C3: this tick lands ~150 / ~900 = 17% of final A18.

---

## 7. cmix exclusion (raw 137)

A18 deliberately excludes neural mixer / weighted ensemble. Raw 137 mandates no
cmix-class context mixing in the entropy coder family. A18 = pure LZ + finite-
order PPM (Cleary-Witten 1984 + Lempel-Ziv 1977 — both pre-neural-network era,
both raw 18 self-host compatible).

Phase 11 candidates explored DMC and statistical mixing as raw-137-compliant
extensions; those land separately (A20+) if A18 measurement closes within 3pp
of K(X).
