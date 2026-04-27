# HXC Phase 11 Entry Gate — Wire-Aware Revision (post-A18 ceiling discovery)

**Date**: 2026-04-28
**Trigger**: agent `a6b12f93` Phase 10 P0 A16 LIVE FIRE → wire-ceiling discovery (base64url 4/3 expansion caps Shannon H_n bit-level projections at byte-canonical level).
**Author note**: agent `a07ea3d2` Phase 11 design (anima commit `8694b9ea`, 463 LoC, 5 candidates) drafted **before** the wire-ceiling discovery; original entry gate (`Phase 10 P2 LIVE + 6-repo aggregate ≥ 85% MEASURED`) is now **wire-dependent** and requires three-way revision per Option A/B/C.
**Compliance**: raw 9 hexa-only · raw 18 self-host fixpoint · raw 47 cross-repo · raw 65/68 idempotent · raw 71 falsifier-preregistered · raw 91 honest C3 · raw 92 ai-native-canonical · raw 95 triad-mandate · raw 102 STRENGTHEN-existing · raw 137 80% Pareto · raw 142 self-correction cadence.

---

## 0. raw 91 honest C3 framing

**All saving% in this document distinguish two layers**:
- **bit-level Shannon** (n6 verdict a201a6cc; H_0/H_3/H_4 measurements; reproducible)
- **byte-canonical wire** (post-base-N expansion; depends on Option A/B/C)

The original Phase 11 entry gate (`hxc_phase11_design_post_a18_20260428.md` §7)
predates the wire-ceiling discovery. This document **STRENGTHENS** that gate
without retiring it (raw 102) by adding the wire-dimension axis.

---

## 1. Original entry gate (pre-wire-ceiling)

From `hxc_phase11_design_post_a18_20260428.md` §7:

> **Decision rule**: Phase 11 P0 launch **conditional** on Phase 10 P2 LIVE
> + aggregate ≥ 85% MEASURED.

Implicit assumption: bit-level Shannon == byte-canonical wire saving. This
held under classical text-input → text-output codecs (gzip, lzma, bz2 all
emit binary wires). For HXC under raw 92 ai-native-canonical (line-oriented
printable wire), the assumption **breaks**.

A18 selftest 97% (bit-level, in-sample 1.5 KB n6 subsample, agent `9a416c88`
landing) does NOT translate directly to 97% byte-wire — under base64url, the
ceiling clamps at ~86.5% (5.755/8 × 4/3 = 0.959 → 1−0.959×0.135 ≈ 86.5% on
post-A18 0.102 byte/byte payload).

---

## 2. Wire-aware entry gate revision (Option A / B / C)

For each wire option, restate the entry gate criteria in terms a measurable
LIVE FIRE pipeline can verify:

### Option A — base64url (current production wire)

| criterion | original | wire-aware revision |
|---|---|---|
| Phase 10 P2 LIVE | A18 LIVE + selftest PASS | A18 LIVE + selftest PASS + **byte-wire saving ≥ 85% on text-heavy class** |
| 6-repo aggregate | ≥ 85% MEASURED | **80% MEASURED** (lowered: base64url ceiling on text-heavy ~86.5%, mixed class ~75%, weighted ~80%) |
| A18 ceiling reached | n/a | **86.5% byte-wire** (NOT 90% bit-level) |
| Phase 11 P0 readiness | A18 ≥ 85% | A18 ≥ **80% byte-wire** AND F-A18 falsifier clear |

**Verdict**: Option A entry gate is **achievable but defers Phase 11 P0 entry
beyond Phase 10 P2** — text-heavy 86.5% wire ceiling means 6-repo weighted
aggregate caps at ~78-82% (mixed-class drag). Phase 11 P0 (A19 universal)
becomes "necessary to reach 85% aggregate", changing its priority from
"+2-3pp seal" to "+5-7pp clearer".

### Option B — base94 raw printable (recommended per `hxc_wire_encoding_decision_20260428.md`)

| criterion | original | wire-aware revision |
|---|---|---|
| Phase 10 P2 LIVE | A18 LIVE | A18 LIVE + base94 wire prototype LIVE + selftest PASS |
| 6-repo aggregate | ≥ 85% MEASURED | **85% MEASURED** (base94 ceiling on text-heavy ~87.6%, mixed ~80%, weighted 85%) |
| A18 ceiling reached | n/a | **87.6% byte-wire** |
| Phase 11 P0 readiness | A18 ≥ 85% | A18 ≥ **85% byte-wire** AND base94 round-trip PASS AND F-W94-1..4 clear |

**Verdict**: Option B entry gate is **the closest match to the original 85%
target**. Phase 11 P0 (A19) entry coincides with Phase 10 P2 closure as
originally designed; A19 contributes its full +2-3pp seal on top of the
~87% A18 ceiling.

### Option C — per-bit binary (Phase 11+ deferral, raw 92 split required)

| criterion | original | wire-aware revision |
|---|---|---|
| Phase 10 P2 LIVE | A18 LIVE | A18 LIVE + raw 92 split (92a text + 92b binary side-channel) registered |
| 6-repo aggregate | ≥ 85% MEASURED | **90% MEASURED achievable** (per-bit at Shannon ceiling, 90% asymptotic) |
| A18 ceiling reached | n/a | **90% byte-wire = bit-level** |
| Phase 11 P0 readiness | A18 ≥ 85% | A18 ≥ **88% byte-wire** AND raw 92b registered AND tooling fork landed |

**Verdict**: Option C **maximizes Phase 10 P2 ceiling but defers Phase 11
entry** by 2-3 ω-cycles for raw 92 split + tool fork. Out of immediate scope.

---

## 3. Per-wire entry gate timing

| wire option | Phase 10 P0 entry | Phase 10 P1 entry | Phase 10 P2 entry | Phase 11 P0 entry |
|---|---|---|---|---|
| Option A (base64url) | NOW (A16 partial LIVE) | A16 byte-wire ≥ 5% | A17 byte-wire ≥ 75% | A18 byte-wire ≥ 80% (6-repo weighted) |
| Option B (base94) | base94 prototype LIVE | A16 base94 ≥ 12% | A17 base94 ≥ 80% | A18 base94 ≥ 85% (6-repo weighted) |
| Option C (per-bit) | raw 92 split | A16 binary ≥ 28% | A17 binary ≥ 84% | A18 binary ≥ 88% (6-repo weighted) |

**Decision rule for Phase 11 P0 entry**:
- **AND** Phase 10 P2 (A18) LIVE + selftest PASS
- **AND** 6-repo aggregate ≥ {80% / 85% / 88%} per Option {A / B / C} wire decision
- **AND** F-A18 falsifier (round-trip byte-eq, latency, memory) all clear
- **AND** wire option formally selected (raw 157 promotion OR raw 92 split OR explicit Option A retention)

---

## 4. Per-raw entry condition re-verification (raws 149-153)

### raw 149 (`design-K-X-asymptotic-mandate`) — Phase 11 P0 (A19 universal compressor)

**Original entry**: post-A18 LIVE.
**Wire-aware entry**:
- **Option A**: Phase 10 P2 ≥ 80% byte-wire (lowered) AND F-Ph11-A19-1..4 preregistered
- **Option B**: Phase 10 P2 ≥ 85% byte-wire (original target met) AND F-Ph11-A19-1..4 preregistered
- **Option C**: Phase 10 P2 ≥ 88% byte-wire AND raw 92b registered

**Status currently**: NO-GO — Phase 10 P2 not yet LIVE; A18 design only (commit `5c4e8b19`); A18 LIVE FIRE outstanding; wire option not yet selected.

### raw 150 (`tokenizer-schema-aware-mandate`) — Phase 11 P1 (A20 schema-aware tokenizer)

**Original entry**: A19 LIVE OR A19 falsified (A20 numerically independent).
**Wire-aware entry**:
- A20 schema-aware operates **upstream of wire encoding** (text → token IDs → entropy coder → wire). Wire ceiling does not invalidate A20's projected +4-7pp on text-heavy.
- BUT: A20 builds on A9 BPE (Phase 9 P1, partial LIVE per `aafff73d` honest no-op finding). Until A9 has pretrained vocab loader (raw 137 follow-up line 4175) OR in-corpus pre-build path lands, A20 cannot add value above A9's current 0pp delta.

**Status currently**: NO-GO — A9 BPE production effect 0% (raw 137 history line 4178: "A9 honest no-op... universal-unblock 가설 falsified"); A20 has no foundation to extend until A9 yields measurable pre-Phase-10 saving OR is integrated as `pre-A1 raw placement` per raw 154.

### raw 151 (`cross-corpus-dict-federation-mandate`) — Phase 11 P2 (A19-fed cross-corpus federation)

**Original entry**: Phase 9 P4 A16-cross-file LIVE + Phase 11 P0 LIVE.
**Wire-aware entry**:
- A19-fed federation operates on **dict references** (^D<id> markers + shared dict file). Wire ceiling applies symmetrically — federation reduces dict-overhead amortization, gain ratio is wire-independent at first order.
- Federation depends on Phase 9 P4 A16-cross-file (commit `d6cbb81c` design only, no LIVE FIRE evidence).
- Phase 11 P0 (A19) LIVE is preferred but NOT strictly required — federation can be measured against A18 baseline.

**Status currently**: IN-PROGRESS — agents `aec09218` and `a18865d5` referenced in user task as "진행 중". Confirm via separate trace (state/format_witness or git log) — if neither has produced a LIVE artifact, status remains DESIGN-PENDING.

### raw 152 (`self-decoding-fixpoint-mandate`) — Phase 11 P3 (A22 self-decoding HXC)

**Original entry**: A22 scaffold + Phase 10 P2 entry.
**Wire-aware entry**:
- A22 embeds decoder spec inline; the spec itself is text → wraps under wire encoding → adds ~3pp byte-wire overhead irrespective of Option A/B/C.
- A22 entry is wire-INDEPENDENT (architecture seal, not saving optimization).
- A22 scaffold can begin BEFORE Phase 10 P2 LIVE if scaffold scope is bootstrap parser + spec emitter only (no integration).

**Status currently**: SCAFFOLD-OK — agent `a474f637` (referenced in user task) or separate agent can begin scaffold; integration deferred to Phase 11 P0/P1/P2 closure.

### raw 153 (`write-side-entropy-reduction-advisory`) — Phase 11 REF (A21 write-side redesign)

**Original entry**: always entry-ready (advisory tier-2).
**Wire-aware entry**: unchanged — write-side advisory is wire-independent and HXC-out-of-charter.

**Status currently**: ALWAYS-GO (advisory; no implementation gate; documentation tier).

---

## 5. Phase 11 candidates re-prioritization

**Original priority** (`hxc_phase11_design_post_a18_20260428.md` §4): A19 > A20 > A19-fed > A22 > A21-ref.

**Wire-aware re-prioritization**:

### Under Option A (base64url retained)
A18 ceiling 86.5% on text-heavy means **A22 self-decoding becomes more
strategic** — artifact portability matters when raw saving% is wire-clamped
and the differentiator vs lzma/zstd shifts to "self-host fixpoint" rather
than "smaller bytes". A19/A20 still apply but their +pp gain is wire-clamped.

**Revised priority (Option A)**:
`["A22-architecture-seal", "A19", "A19-fed", "A20", "A21-ref"]`

### Under Option B (base94 adopted)
A18 ceiling 87.6% restores original A19/A20 +2-7pp gains as load-bearing.
A22 architecture seal remains but moves to closing position.

**Revised priority (Option B)**:
`["A19", "A20", "A19-fed", "A22", "A21-ref"]` (= original)

### Under Option C (per-bit, Phase 11+ deferral)
Wire ceiling fully lifts; all bit-level Shannon projections become byte-wire
realizations. A19 universal compressor's +2-3pp atlas / +8-10pp text gains
become directly measurable.

**Revised priority (Option C)**:
`["A19", "A20", "A19-fed", "A22", "A21-ref"]` (= original; same rank)

### Cross-option recommendation
Prefer Option B; if Option A is sticky, promote A22 ahead of A19/A20.
Defer Option C until Phase 12 if at all (raw 92 split is an architectural
decision warranting separate ω-cycle).

---

## 6. Roadmap consolidation (Phase 5 → Phase 11, wire-aware)

| Phase | algorithms | bit-level | wire-A | wire-B | wire-C |
|---|---|---:|---:|---:|---:|
| Phase 5 baseline | A1+A7+A10 | 14% | 14% | 14% | 14% |
| Phase 6 | + A4+A8+A11 | 21% | 21% | 21% | 21% |
| Phase 7 | + best-of-N | 40% | 40% | 40% | 40% |
| Phase 8 P1 | + A12 | 44% | 44% | 44% | 44% |
| Phase 8 P5 | + A13/A14/cache | 47% | 47% | 47% | 47% |
| Phase 8 P8 | + A15 | 47% | 47% | 47% | 47% |
| Phase 9 P1 | + A9 BPE | 52-55% | 47% (no-op) | 47% (no-op) | 52-55% (placement-corrected) |
| Phase 10 P0 | + A16 AC | 72% | ~50% | ~58% | 72% |
| Phase 10 P1 | + A17 PPMd | 80-82% | ~60% | ~75% | 80% |
| Phase 10 P2 | + A18 LZ+PPM | 88-90% | ~78-82% | ~85-87% | 88% |
| Phase 11 P0 | + A19 universal | 92-93% | ~80-83% | ~87-90% | 91% |
| Phase 11 P1 | + A20 schema-aware | 92-93% | ~82-85% | ~88-91% | 91% |
| Phase 11 P2 | + A19-fed | 92-93% | ~83-86% | ~89-92% | 91% |
| Phase 11 P3 | + A22 (architecture seal) | 92-93% | ~80-83% (-3pp overhead) | ~86-89% | 88% |

**80% target reachability per wire**:
- Wire A: requires Phase 11 P0 + P2 (A19 + A19-fed) to clear 80% aggregate
- Wire B: cleared at Phase 10 P2 (A18) — original projection holds
- Wire C: cleared at Phase 10 P1 (A17) alone

**raw 137 80% byte-wire reachability map**:
- Option A: NO-GO at Phase 10; conditional GO at Phase 11 P2
- Option B: GO at Phase 10 P2 (matches original Phase 10 master roadmap)
- Option C: GO at Phase 10 P1 (1 ω-cycle earlier than Option B)

---

## 7. Go/No-Go decision (current Phase 11 status)

| candidate | raw | status | reasoning |
|---|---|---|---|
| A19 (Phase 11 P0 universal compressor) | raw 149 | **NO-GO** | Phase 10 P2 (A18) not yet LIVE; A18 design only at commit `5c4e8b19`. Wire option not yet selected. Entry blocked on Phase 10 P2 closure. |
| A20 (Phase 11 P1 schema-aware tokenizer) | raw 150 | **NO-GO** | A9 BPE empirical 0pp delta (raw 137 line 4178); A9 needs pre-A1-raw placement (raw 154) OR pretrained vocab; wire option not yet selected. |
| A19-fed (Phase 11 P2 cross-corpus federation) | raw 151 | **IN-PROGRESS** (per user task statement; agents `aec09218` + `a18865d5` 진행 중). DESIGN-PENDING until LIVE artifact lands. |
| A22 (Phase 11 P3 self-decoding) | raw 152 | **SCAFFOLD-OK** — agent `a474f637` or separate agent can begin scaffold (bootstrap parser + spec emitter ~50 LoC); full integration deferred. |
| A21-ref (write-side advisory) | raw 153 | **ALWAYS-GO** (advisory tier-2; no implementation; documentation only) |

---

## 8. raw 137 strengthening targets

This document strengthens raw 137 with two new history entries (see `commits` field of output JSON):

1. **Phase 11 entry gate wire-aware revision**: Phase 10 P0/P1/P2 entry conditions now stated in byte-wire terms per Option A/B/C; original bit-level 85% target re-expressed as 80% (Option A) / 85% (Option B) / 88% (Option C) byte-wire aggregate.
2. **80% target reachability path per wire**: Option A → Phase 11 P2 minimum; Option B → Phase 10 P2 minimum (original); Option C → Phase 10 P1 minimum (best-case but architectural cost).

---

## 9. raw 91 honest C3 disclosures

1. **All "byte-wire" projections in this document are analytical** (Shannon H_n × expansion_ratio + estimated header overhead). Empirical wire-aware measurement requires base94 prototype LIVE FIRE (deferred per `hxc_wire_encoding_decision_20260428.md` §5).
2. **A18 selftest 97%** (per agent task description) is **bit-level in-sample**; user task statement of "byte-canonical wire 통과 후: A18 ceiling = 86.5% (base64url) / 87% (base94)" is consistent with analytical 5.755/8 × expansion and treated as authoritative for this entry-gate document.
3. **agent `aec09218` and `a18865d5` IN-PROGRESS status** is reported per user task statement only; this document does not independently verify their progress.
4. **Phase 11 priority re-ranking under Option A** ("A22-first") is a **strategic recommendation**, not a falsifier-driven mandate. If user/owner prefers original ordering even under base64url retention, the original `[A19, A20, A19-fed, A22, A21-ref]` ordering remains valid; only the absolute-byte gain expectation changes.
5. **A22 scaffold-OK status** assumes scaffold scope ≤ 100 LoC (bootstrap parser + spec emitter); full integration ≥ 400 LoC remains gated on Phase 11 P0/P1/P2 closure.
6. **6-repo aggregate weights** assume Phase 8 byte-distribution stays constant; redistribution (e.g., n6 atlas growth) shifts cross-class weighting and aggregate projection ±3pp.

---

## 10. Reference path inventory

- `/Users/ghost/core/anima/docs/hxc_phase11_design_post_a18_20260428.md` (original design, agent `a07ea3d2`, anima commit `8694b9ea`)
- `/Users/ghost/core/anima/docs/hxc_wire_encoding_decision_20260428.md` (wire decision, agent `a6b12f93`)
- `/Users/ghost/core/anima/docs/hxc_phase10_master_roadmap_20260428.md` (Phase 10 ladder, original)
- `/Users/ghost/core/anima/docs/hxc_phase10_roadmap_reformulation_20260428.md` (Phase 10 wire-aware reformulation, commit `dd6112ac`)
- `/Users/ghost/core/anima/docs/hxc_phase11_a20_design_20260428.md` (A20 schema-aware tokenizer, commit `c7243763`)
- `/Users/ghost/core/anima/docs/hxc_phase9_a9_tokenizer_design_20260428.md` (A9 BPE design)
- `/Users/ghost/core/anima/docs/hxc_phase9_a16_cross_file_dict_design_20260428.md` (A16 cross-file/A19-fed precursor)
- `/Users/ghost/core/hive/.raw` lines 4079-4183 — raw 137 entry + history
- `/Users/ghost/core/hive/.raw` lines 5092-5359 — raws 149-153 entries
- `/Users/ghost/core/hive/.raw` lines 5034 — raw 154 placement-orthogonality

raw 9 hexa-only · raw 18 self-host fixpoint · raw 47 cross-repo · raw 65/68
idempotent · raw 71 falsifier-preregistered · raw 91 honest C3 · raw 92
ai-native-canonical · raw 95 triad-mandate · raw 102 STRENGTHEN-existing ·
raw 137 80% Pareto (wire-aware strengthened) · raw 142 self-correction
cadence · raw 143 entropy-coder · raw 149-153 (Phase 11 P0-P3 + REF).

**End of revised entry gate doc.**
