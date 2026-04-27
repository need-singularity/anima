# HXC Phase 11 P1 — A20 Schema-Aware Tokenizer Design

**Date**: 2026-04-28
**Phase**: 11 P1 (post-A18 territory; A20 = schema-aware BPE)
**Parent design**: `hxc_phase11_design_post_a18_20260428.md` §2 candidate 2
**Trigger**: Phase 11 P1 launch; first ~150 LoC tick (PASS 1 + PASS 2 + 1 selftest)
**Compliance**: raw 9 hexa-only · raw 18 self-host fixpoint · raw 65 + 68
idempotent · raw 71 falsifier-preregistered (4 falsifiers · F-A20-1..4) · raw
91 honest C3 (projections labeled vs measurements)

---

## 0. Honest framing (raw 91 C3)

A20 is a **post-A9 BPE extension**, not a replacement. A9 BPE
(`hxc_a9_tokenizer.hexa`) builds a content-agnostic byte-pair vocabulary per
schema. A20 prepends a **schema-token pre-seed pass** that boosts vocab
quality on mixed JSON / text / Korean corpora by recognising structural keys
extracted from `# schema:` headers (HXC v1 grammar).

All saving numbers below are **PROJECTIONS** until F-A20-1 measurement
gates fire. This document covers design + first ~150 LoC tick (PASS 1
schema-token extraction + PASS 2 vocab build with pre-seed). PASS 3 encode +
PASS 4 decode + integration deferred to subsequent ticks.

---

## 1. Algorithm spec

### Differential vs A9 BPE

| stage | A9 (baseline) | A20 (schema-aware) |
|---|---|---|
| PASS 1 | corpus → row body bytes | corpus → row body bytes **+ schema-key extraction from `# schema:` header** |
| PASS 2 | byte-pair argmax merge V iterations | **schema-keys pre-seeded as token IDs 256..256+K-1**, then byte-pair argmax merge V-K iterations |
| PASS 3 | greedy longest-match encode | **identical to A9** (vocab is union of pre-seed + merges) |
| PASS 4 | symbol stream → byte expand | **identical to A9** (vocab table includes pre-seed expansions) |

### PASS 1 — schema-key extraction

Input: HXC v1 stream lines.
Output: per-schema array<string> of structural key names.

Procedure (~80 LoC):
1. Scan lines for `# schema:sN key1 key2 ...` header pattern.
2. Tokenise the post-`sN ` portion on whitespace → array of key names.
3. For each key, also derive the **JSON-quoted-key form** `"<key>":` (a 4+
   byte literal that recurs in JSON-encoded row bodies).
4. Optionally derive the **HXC pipe-delimited form** `|"<key>":` for embedded
   nested fields.
5. Deduplicate and emit as schema_pre_seed[s_idx] = array of byte sequences.

### PASS 2 — vocab build with pre-seed

Procedure (~70 LoC):
1. For each schema, allocate token IDs 256..256+K-1 to the K pre-seed
   sequences (sorted longest-first for greedy encode determinism).
2. **Apply pre-seed merges to row symbol streams** — wherever the pre-seed
   byte sequence appears as a contiguous run, replace with the new symbol.
   This is a multi-byte merge (A9 only does pair merges) — A20 generalisation.
3. Continue normal byte-pair argmax merge for remaining (V - K) slots,
   identical to A9.
4. Emit vocab as `[token_id, byte_seq_array]` entries — same shape as A9, so
   PASS 3/4 reuse A9 functions verbatim.

---

## 2. 4 falsifiers preregistered (raw 71)

- **F-A20-1**: marginal saving < 0.05 (5pp) vs A9 baseline on mixed JSON+text
  fixture → reject (no benefit beyond A9)
- **F-A20-2**: encode/decode round-trip not byte-eq → reject (raw 65/68
  violation)
- **F-A20-3**: schema-token false-positive rate > 5% (extracted keys that
  do not appear as substrings in any row body) → reject (PASS 1 noisy)
- **F-A20-4**: vocab build memory > 100MB → reject (jetsam risk; cron-host
  budget)

---

## 3. Tick 1 scope (~150 LoC)

| component | LoC est | status this tick |
|---|---:|---|
| header + constants + re-use of A9 helpers | ~20 | DONE |
| PASS 1 schema-key extraction | ~80 | DONE |
| PASS 2 vocab build with pre-seed | ~70 | DONE |
| PASS 3 encode (reuse A9) | ~30 | DEFERRED |
| PASS 4 decode (reuse A9) | ~30 | DEFERRED |
| selftest fixture (synthetic mixed JSON+text) | ~50 | 1 of 4 DONE |
| main() + CLI dispatch | ~40 | PARTIAL stub |

Tick 1 deliverable: PASS 1 + PASS 2 LIVE, 1 selftest fixture PASS, main()
prints PARTIAL marker.

Remaining estimate ~250-300 LoC across 2-3 follow-up ticks.

---

## 4. Self-host + cross-repo (raw 9 / 18 / 47)

- raw 9 hexa-only: ✓ pure-hexa, no external libs
- raw 18 self-host: ✓ identical wire format as A9 (decoder vocab table is
  the SoT; pre-seed is a build-time-only optimisation invisible to decoder)
- raw 47 cross-repo: deferred to integration tick (apply across nexus +
  anima + hive corpora)

---

raw 9 · raw 18 · raw 65 + 68 · raw 71 (4 falsifiers) · raw 91 C3 ·
parent: a07ea3d2 / 8694b9ea Phase 11 design.
