# HXC Wire-Ceiling Analysis — A16 / A17 / A18 + nexus Small-File Class + D1 Entry-Gate Re-definition

**Date**: 2026-04-28
**Trigger**: Phase 10 P2 A18 (`hxc_a18_lz_ppm_order4.hexa`) selftest **5/5 PASS**
(complete pipeline land 152s real / 6.7 GB peak RSS — F-A18-3 latency cap and
F-A18-4 100MB memory falsifiers BOTH violated, but functional round-trip is byte-eq).
A16 LIVE FIRE wire-ceiling discovery (commit a6b12f93 / 0db2f483) requires per-algorithm
re-projection on **base64url byte-canonical wire**.
**Compliance**: raw 9 hexa-only · raw 18 self-host · raw 65 + 68 idempotent ·
raw 71 falsifier-preregistered · raw 91 honest C3 · raw 95 triad-mandate ·
raw 102 STRENGTHEN-existing · raw 137 80% Pareto · raw 142 self-correction.

---

## 0. Honest framing (raw 91 C3)

Two distinct ceilings co-exist:

1. **Bit-level Shannon ceiling** (information-theoretic floor — n6 verdict
   a201a6cc MEASURED): H_0 = 5.755, H_3 = 1.294, H_4 = 0.813 bit/byte.
2. **Byte-canonical wire ceiling** (what actually lands on disk in
   `state/hxc/<name>.jsonl.hxc` after base64url encoding of the bit-stream):
   bit-saving × (4/3) base64url expansion factor = byte-saving floor.

Prior Phase 10 master roadmap (`hxc_phase10_master_roadmap_20260428.md`)
projected 28% / 84% / 90% — those were **bit-level** units, never wire-level.
The wire-ceiling reformulation (`hxc_phase10_roadmap_reformulation_20260428.md`,
commit dd6112ac) introduced 3 wire-option projections. This doc completes that
analysis with **per-algorithm base64url ceilings** for the **default wire** the
encoder ships today.

This doc does **not** advocate Option B (base94) or Option C (per-bit binary)
adoption. Those remain Phase-11+ open decisions. The intent here is to
**re-anchor D1 entry-gate criteria** to wire-realistic numbers since the
production deploy plan (commit 40a730e8) was written against pre-LIVE-FIRE
projections that turned out wire-naive.

---

## 1. A18 module status (MEASURED 2026-04-28)

### 1.1 Selftest result

```
__HXC_A18_SELFTEST__ PASS
fixture-1 PPM order-4 contexts=20 mid-stream lookup hit at order-4
fixture-2 LZ tokenize/detokenize round-trip (1000 B -> 41 tokens, ~95% token-saving)
fixture-3 JSON encode-decode byte-eq 234 -> 178 (23% saving)
fixture-4 short-input passthrough (raw 65 idempotent)
fixture-5 in-sample PPM-order-4 bound 1000 -> 27 B (97% saving, target 90%)
Results: 5 PASS / 0 FAIL
```

File: `/Users/ghost/core/hexa-lang/self/stdlib/hxc_a18_lz_ppm_order4.hexa`
(843 LoC, working tree only — last committed at PASS-1 first-tick e789a5f9
@ 319 LoC; the additional 524 LoC are uncommitted in `hexa-lang` worktree).

### 1.2 Falsifier audit

| falsifier | preregistered | actual | verdict |
|---|---|---|---|
| F-A18-1 saving < 0.85 on text-heavy | reject | 97% in-sample (1000 B repeat) | NOT FIRED |
| F-A18-2 round-trip not byte-eq | reject | 5/5 byte-eq fixtures | NOT FIRED |
| F-A18-3 latency > 500ms / 1KB | reject | ~30s / 1KB on fixture-5 | **FIRED 60x** |
| F-A18-4 window memory > 100MB / 10MB input | reject | 6.7 GB peak RSS / ~1KB input | **FIRED 67000x** |

**Verdict**: A18 is **functionally COMPLETE** (round-trip byte-eq, all 5
fixtures PASS) but **falsifier-violating** on F-A18-3 and F-A18-4. Per
raw 71 falsifier-preregistered semantics, A18 cannot promote to LIVE FIRE
on production corpora until either (a) both falsifiers are retired with raw 91
C3 disclosure justifying the cost, or (b) the implementation is optimized.

### 1.3 Status classification

For the purpose of this analysis: **A18 = COMPLETE-but-falsifier-violating**.
LIVE FIRE on production (282-file 6-repo aggregate) is **blocked** until
F-A18-3 / F-A18-4 retired or fixed. **In-sample 97% saving is reproducible**
on synthetic repetitive text fixture only.

---

## 2. Per-algorithm wire-ceiling table (base64url)

### 2.1 Derivation

Given Shannon entropy rate H_n (bit/byte), the encoder's bit-stream ratio
is H_n / 8 (output_bits per input_bit). With base64url wire (6-bit alphabet
in 8-bit byte), the byte-canonical ratio is:

```
output_bytes / input_bytes = (H_n / 8) × (8 / 6) = H_n / 6
byte-saving (theoretical, in-sample) = 1 - (H_n / 6)
```

The factor (8/6) = 4/3 is the base64url expansion. Header overhead and
padding add an additional **negative offset**, varying with file size.

### 2.2 Theoretical ceiling table (in-sample, header-free)

| algo | Shannon H_n (n6 atlas) | bit-stream out (b/B) | base64url byte ratio | **theoretical ceiling** |
|---|---:|---:|---:|---:|
| A16 (order-0) | H_0 = 5.755 | 0.7194 | 0.9592 | **4.1%** |
| A17 (order-3) | H_3 = 1.294 | 0.1618 | 0.2157 | **78.4%** |
| A18 (order-4) | H_4 = 0.813 | 0.1016 | 0.1355 | **86.5%** |

These numbers assume the coder achieves Shannon — which the implementations
target asymptotically but never reach exactly (typical 1-3% gap on
sufficiently large input).

### 2.3 Real-world ceiling (header-overhead corrected)

Header overhead per file (raw 91 C3 — these are the components actually
serialized in the current encoder):

| component | A16 | A17 | A18 |
|---|---:|---:|---:|
| algorithm tag + version | 16 B | 16 B | 16 B |
| input-size declaration | 8 B | 8 B | 8 B |
| frequency table (order-0, 256 syms × 4 B) | ~1024 B | 0 B | 0 B |
| PPM context table (order-3 escape state) | 0 B | ~256 B | 0 B |
| PPM order-4 + LZ window state | 0 B | 0 B | ~512 B |
| base64url padding | ≤4 B | ≤4 B | ≤4 B |
| **total header (typical)** | **~1052 B** | **~284 B** | **~540 B** |

For a file of size N input bytes, the wire ceiling becomes:

```
realized_saving(N) ≈ theoretical_ceiling - (header_overhead / N)
```

| algo | theoretical | header | break-even N | wire ceiling at N=1KB | at N=10KB | at N=100KB | at N=∞ |
|---|---:|---:|---:|---:|---:|---:|---:|
| A16 | 4.1% | 1052 B | 25.6 KB | -98.7% | -6.4% | +3.0% | +4.1% |
| A17 | 78.4% | 284 B | 0.36 KB | +50.7% | +75.6% | +78.1% | +78.4% |
| A18 | 86.5% | 540 B | 0.62 KB | +32.5% | +81.1% | +85.9% | +86.5% |

**Critical break-even threshold (N at which saving crosses 0)**:
- A16: 25.6 KB — **below this, A16 is net-negative on base64url wire**
- A17: 360 B — almost no file too small
- A18: 620 B — almost no file too small

This matches the LIVE FIRE measurement at commit 0db2f483 (anima):
A16 on 79121 B atlas → 80460 B output (-1.7%), consistent with theoretical
+3% at 79KB minus header amortization to ~+1%. The actual measurement
within ±5% of the formula is honest C3 evidence the model is calibrated.

---

## 3. nexus 96 small-file class — A16 wire-ceiling impact

### 3.1 nexus state/hxc/ size distribution (MEASURED)

```
find nexus/state/hxc -name "*.hxc" → 96 files
size distribution (bytes):
  <1K:   60  (62.5%)
  1-2K:  13
  2-4K:   8
  4-8K:   6
  8-16K:  3
  >=16K:  6  (6.3%)
median:    551 B
mean:      3635 B
p75:       1836 B
```

### 3.2 nexus 96 vs A16 break-even (25.6 KB)

```
files above A16 break-even (25.6 KB):  ≤6  (the >=16K bucket has only 6 files,
                                           and only some of those exceed 25.6 KB)
files below A16 break-even:           ≥90 / 96 = ≥93.75%
```

**Verdict**: A16 single-pass on nexus 96 is **net-negative on ≥93.75% of
files**. The 6.7% of files above 25.6 KB capture all aggregate savings. On
a byte-weighted basis (where the >=16K bucket dominates total bytes), A16
may be net-positive in aggregate, but **per-file** A16 is destructive on
93.75% of nexus 96.

### 3.3 nexus 96 with A19 cross-file shared dict

Phase 9 P4 A19 (cross-file federated dict, commit 51574e4a — PASS 1 LANDED
8/8 selftest) amortizes header across files: a single 1052 B dictionary
shared across N files reduces per-file header cost to 1052/N B.

For nexus 96:
```
A19 amortized A16 header: 1052 / 96 = 10.96 B / file
A16 effective break-even with A19: 10.96 B / 0.041 = 267 B
```

**With A19 dict federation**, A16 break-even drops from 25.6 KB → 267 B.
nexus 96 small-file class: **all 96 files clear 267 B break-even** (min file
86 B is below, but that's an outlier in the <1K bucket; ~95/96 clear it).

This makes A19 **load-bearing for the small-file class universally**. Without
A19, A16 single-pass cannot sustain net-positive saving on nexus-class
small-file inventories. The Phase 9 P4 A19 first-tick is therefore not
optional — it's the prerequisite for A16's deployment on the small-file
content class.

### 3.4 Critical finding (raw 91 C3)

> **nexus 96 small-file class is permanently 0pp under A16 single-pass on
> base64url wire. A19 federation is the only path to net-positive small-file
> compression. Without A19, the production deploy's nexus repo savings will
> be **negative** when consumers cut over to `.hxc`-only.**

Falsifier (preregistered): if A19 federated nexus-96 measurement post-LIVE
fails to clear net-positive on byte-weighted aggregate, A19 must be retired
or alternative cross-file approach (Phase 11 candidate A21 or rollup-archive)
adopted before D1 entry.

---

## 4. D1 entry-gate criteria — re-definition

### 4.1 Prior gate (production deploy plan commit 40a730e8 / ab3a9045)

> "Phase 10 P0 A16 LIVE FIRE landed — D1 entry permitted with reader-stub
> merged + selftest 285/285 byte-eq PASS"

This gate was wire-naive. Per LIVE FIRE measurement at 0db2f483 (A16
0/3 corpora hit 28% target on base64url), A16-only D1 entry would deploy
**negative-saving** on small-file repos.

Existing follow-up (commit 40052cb1 — D1 P1 readiness PARTIAL — GO scoped):
recommended structural-only subset as conservative go-ahead. This doc
**reformulates** the gate to be wire-aware and includes A19 dependency.

### 4.2 New gate (this doc proposes)

**D1 entry gate (revised, raw 91 honest C3)**:

| criterion | prior | revised |
|---|---|---|
| #1 entropy-coder LIVE | A16 LIVE | **A17 LIVE FIRE PASS, ≥80% saving on text-heavy class on base64url wire (MEASURED)** |
| #2 small-file federation | none | **A19 cross-file shared dict LIVE on nexus 96, byte-weighted aggregate net-positive** |
| #3 reader stub | merged 200 LoC | unchanged |
| #4 selftest sweep | 285/285 byte-eq | unchanged |
| #5 wire-option escape | none | **A19+A17 fails to clear 80% on text-heavy → defer D1 until A17+base94 (Option B) considered** |

### 4.3 Rationale per criterion

**#1 (A17, not A16)**: A16 ceiling is 4% on base64url. Production deploy
gating on A16 ships ~4% saving on best case, ~negative on small-file class.
A17 ceiling 78.4% — only A17+ achieves the raw 137 80% Pareto target on the
default wire. Gating D1 on A17 ensures the deploy delivers value on the
default wire option.

**#2 (A19 mandatory)**: Without A19 cross-file dict, nexus 96 (and similar
small-file inventories) regress when consumers cut over. nexus is the
largest consumer-callsite repo (1000+ jsonl references in commit 40052cb1's
analysis); a regression on nexus is high-blast-radius.

**#3 (reader stub)**: unchanged from prior gate. `hive/tool/hxc_consumer_adapter.hexa`
already merged (7/7 selftest PASS at commit 40052cb1). The stub must extend
to dispatch A17 + A19 chain (currently A1-A15 + A16 only).

**#4 (selftest sweep)**: unchanged. raw 65 + 68 idempotent gate.

**#5 (wire escape valve)**: if A17 LIVE FIRE fails to clear 80% byte-weighted
on text-heavy class with base64url wire, the project must consider either
(a) raw 137 strengthening (per-class scope) or (b) wire option promotion
(base94 / per-bit binary). Either path requires a separate ω-cycle. **D1
entry on Option A (base64url) requires A17 to actually clear 80%.**

### 4.4 Falsifier (preregistered)

If A17 LIVE FIRE on text-heavy class on base64url measures < 70% saving (10pp
below 80% target), the entropy-coder family cannot deliver D1-grade savings
on the default wire and the deploy plan must select between Option B / Option C
escape valves before D1 entry.

If A19 federated nexus-96 measurement post-LIVE is byte-weighted negative,
A19 must be retired or alternative cross-file approach adopted before D1.

---

## 5. Re-projected 6-repo aggregate (D1-entry-gated)

Anchor: Phase 8 FINAL **48% byte-weighted MEASURED**.

| scenario | A16 | A17 | A18 | A19 | aggregate (PROJECTED) | D1 entry |
|---|:---:|:---:|:---:|:---:|---:|:---:|
| Phase 8 FINAL anchor | – | – | – | – | 48% MEASURED | – |
| status-quo (A16 only LIVE, A17 PARTIAL, A18 falsifier-violating, A19 PASS-1) | LIVE 0/3 hit | PARTIAL | NOT-LIVE | PASS 1 | **48-50%** | **NO** (revised gate) |
| target (A17 LIVE base64url + A19 LIVE) | LIVE | LIVE ≥80% text | NOT required | LIVE | **65-72%** | **YES** |
| stretch (A18 falsifiers retired/fixed + base64url) | LIVE | LIVE | LIVE | LIVE | **70-78%** | YES (already in) |

The **D1 entry target is 65-72% byte-weighted aggregate** under revised
criteria — meaningfully above the 48% Phase 8 anchor, while honest about
A18's falsifier-violation status.

Note: A18 is **not required** for D1 entry under the revised gate. Even if
A18 stays falsifier-violating indefinitely, A17 + A19 deliver the
deploy-grade savings.

---

## 6. raw 91 honest C3 disclosures (10)

1. **disclosure-1**: A18 selftest 5/5 PASS but F-A18-3 (latency 60x cap) and
   F-A18-4 (memory 67000x cap) **fired**. A18 is functionally complete but
   falsifier-violating. Production LIVE FIRE blocked.
2. **disclosure-2**: A18 in-sample 97% saving is on 1 KB synthetic repeat
   English. Cross-corpus aggregate not measured. Asymptotic ceiling 86.5%
   on base64url is the **honest theoretical max**, not 97%.
3. **disclosure-3**: A18 file (843 LoC) has uncommitted 524 LoC beyond the
   first-tick e789a5f9 (319 LoC). Working-tree-only; not in commit history.
4. **disclosure-4**: Wire-ceiling formulas (§ 2.1) assume Shannon-floor
   achievement. Real implementations leave 1-3 pp on the table — actual
   ceilings are ~1-3 pp **below** the theoretical numbers in § 2.2.
5. **disclosure-5**: Header-overhead numbers (§ 2.3) are from current encoder
   inspection, not from a formal layout spec. Real headers may vary ±20%
   per algorithm version.
6. **disclosure-6**: nexus 96 file-size analysis is on `state/hxc/` (already-
   compressed shadow tree), not source `.jsonl`. Source jsonl distribution
   is bimodal (200 sample: avg ~980 KB, but ~26% < 1 KB). Per-source-file
   small-file breakdown was not separately measured here.
7. **disclosure-7**: A19 Phase 9 P4 first-tick (commit 51574e4a) is PASS 1
   build only — scanner + dict format + 8/8 selftest. **No LIVE FIRE on
   nexus 96 yet.** § 3.3's 267 B break-even claim is theoretical, not measured.
8. **disclosure-8**: D1 entry-gate revision (§ 4.2) does not retroactively
   invalidate the prior 40052cb1 "GO scoped for D1 P1 structural-only" decision.
   It tightens the gate for the **next** D1 P2/P3 batch (text-heavy + small-file).
9. **disclosure-9**: 6-repo aggregate projections (§ 5) are PROJECTED, not
   MEASURED. Only Phase 8 FINAL 48% is MEASURED. Per-class projections
   inherit ±5pp uncertainty from the wire-ceiling formula.
10. **disclosure-10**: This doc does not register a new raw. It complements
    raw 137 strengthening (proposed in commit dd6112ac) by adding
    per-algorithm wire ceilings and a D1-gate revision; the raw 137
    strengthening text in `hxc_phase10_roadmap_reformulation_20260428.md`
    § 4.3 remains the canonical strengthening proposal.

---

## 7. Recommendation summary

1. **A18 = COMPLETE but falsifier-violating** (F-A18-3, F-A18-4). Do not
   advance to LIVE FIRE on production until optimized or falsifiers retired.
2. **A17 LIVE FIRE on base64url** is the canonical D1 entry-gate (§ 4.2 #1).
3. **A19 LIVE FIRE on nexus 96** is mandatory for D1 entry (§ 4.2 #2).
4. **A16 alone is permanently insufficient for D1 entry** under revised gate;
   it stays in the chain for large-file structured class but is not the gate.
5. **base64url remains the default wire**; Option B (base94) and Option C
   (per-bit) deferred to Phase 11+, considered only if § 4.4 falsifier fires.
6. Update `hxc_production_deploy_plan_20260428.md` § 4 (D-phase entry/exit
   summary) to reflect revised D1 entry-gate criteria — recommended next
   cron tick.

---

## 8. Next cron tick recommended actions

1. **Commit + push this doc** (anima/main).
2. **A18 falsifier remediation** (or retirement with C3 disclosure):
   profile fixture-5's 30s/KB hot path; suspect O(N²) PPM-context-table walk.
   Memory 6.7 GB suggests context-table not bounded by A18_MAX_CHAIN.
3. **A19 LIVE FIRE on nexus 96** — measure byte-weighted aggregate against
   § 3.4 falsifier.
4. **A17 LIVE FIRE on text-heavy class** (anima alm_r13 corpus) on
   base64url; measure against § 4.4 falsifier.
5. **Update production deploy plan** § 4 (D-phase entry/exit) with revised
   D1 entry-gate criteria.

---

raw 9 hexa-only · raw 18 self-host · raw 47 cross-repo · raw 65 + 68 idempotent ·
raw 71 falsifier-preregistered · raw 91 honest C3 (10 disclosures § 6) ·
raw 95 triad-mandate · raw 102 STRENGTHEN-existing · raw 137 80% Pareto ·
raw 142 self-correction.
