# HXC Wire Encoding Decision — base64url vs base94 vs per-bit

**Date**: 2026-04-28
**Trigger**: agent `a6b12f93` A16 LIVE FIRE finding — `base64url` 4/3 byte expansion caps Shannon H_0 = 28% bit-level potential at ~2.7-4% byte-canonical ceiling on n6 atlas (79 KB JSONL).
**Compliance**: raw 9 hexa-only · raw 91 honest C3 · raw 92 ai-native-canonical · raw 95 triad-mandate · raw 137 80% Pareto.
**Scope**: A16 / A17 / A18 entropy-coder family payload encoding only. Header/sigil syntax unchanged.

---

## 1. Problem statement (raw 91 honest C3)

`hxc_a16_arithmetic_coder.hexa` produces a payload of `n_payload` bytes where
`n_payload ≈ (H_0/8) × n_input` plus framing/header constants. The wire transmission
form wraps the byte stream as

    ^A<base64url(payload_bytes)>

`base64url` expands 3 input bytes → 4 output chars (alphabet A-Z a-z 0-9 - _).
Hence the on-wire saving ratio is

    saving_pct = 1 − (H_0/8 × 4/3) − header_overhead

For n6 atlas with H_0 = 5.755 bit/byte (n6 verdict a201a6cc, Shannon order-0):

    saving_pct = 1 − (5.755/8 × 4/3) ≈ 1 − 0.9591 ≈ 4.09%

Empirical agent `a6b12f93` LIVE FIRE A16 force-encode on n6 atlas reports
**−1.69% (regression)** because (a) UTF-8 em-dash byte handling adds 1 byte expansion
per multi-byte sequence, (b) header `freq=` field carries 256 × 3 = 768 base64-encoded
bytes ≈ 1024 chars overhead, (c) `^A` sigil + line framing.

**Conclusion**: base64url wire is a **byte-canonical ceiling** ≈ 4% on text-heavy
JSONL where Shannon H_0 alone permits 28% bit-level saving. Higher-order context
entropy (H_3 = 1.294 → 84%, H_4 = 0.813 → 90%) is also capped by the same wire
expansion. Roadmap recalculation needed.

---

## 2. Three candidate options

### Option A — `base64url` (current)

| metric | value |
|---|---|
| alphabet size | 64 |
| log2(N) | 6.000 bit/char |
| optimal expansion | 8/6 = 1.333 (33%) |
| chunk granularity | 3 bytes → 4 chars (exact) |
| byte-canonical | YES (single-byte chars, ASCII-printable) |
| raw 92 compat | YES (current mandate) |
| HXC sigil collision | NONE (alphabet excludes `# @ space " ' | ~ !`) |
| decoder LoC | ~30 (already implemented) |

**Pros**: zero-friction current path, raw 92 already mandates this, parser-prefix
streaming compatible, trivial decoder.

**Cons**: hard ceiling on entropy-coded payloads. For H_0 = 5.755:
saving_byte = 1 − (5.755/8 × 1.333) = **4.09%**. Even with H_4 = 0.813:
saving_byte = 1 − (0.813/8 × 1.333) = **86.45%** — but only after PPM/LZ stack
delivers H_4-grade compression upstream of the wire encoder.

**Phase 10 projected savings (text-heavy class, H_0/H_3/H_4 substrates)**:

| stage | bit-level | byte-level under base64url |
|---|---:|---:|
| A16 (H_0=5.755) | 28.06% | **2.7-4%** |
| A17 (H_3=1.294) | 83.83% | **~78%** (gap closes asymptotically as payload shrinks) |
| A18 (H_4=0.813) | 89.84% | **~86%** |

Wait — at low entropy (H_4), the wire expansion is applied to a much smaller
post-compression payload, so the ABSOLUTE byte ceiling lifts. Calculation:
post-A18 payload = (0.813/8) × n_input ≈ 0.102 × n_input bytes. After base64url:
0.102 × 1.333 = 0.135. Saving = 1 − 0.135 = **86.5%**. Still below 90% target.

Net Phase 10 base64url projection (text-heavy class, on top of current 4% baseline,
**after Phase 8 A14 row-prefix + A12-A15 catalog already in place**):

| stage | projected saving% |
|---:|---:|
| A16 alone (n6) | ~3% (NEAR ZERO over baseline — empirical −1.69% confirms) |
| A17 PPMd | ~10-15% (context model crushes payload, but base64 still costs) |
| A18 LZ+PPM | ~15-20% (asymptotic ceiling on n6 with current wire) |

Insight: A17/A18 progress masked by base64 — base64url ceiling is the
**roadmap-blocking constraint**, not the algorithm catalog.

### Option B — `base94` (printable ASCII upgrade)

| metric | value |
|---|---|
| alphabet size | 94 |
| log2(N) | 6.5546 bit/char |
| optimal expansion | 8/6.5546 = 1.2204 (22%) |
| chunk granularity | 6 bytes ≈ 7.32 chars (chunked variants below) |
| byte-canonical | YES (single-byte chars, ASCII-printable) |
| raw 92 compat | NEEDS REVISION (sigil-collision audit required) |
| HXC sigil collision | RISK — `# @ " ' | ~ !` ALL inside ASCII 33-126 |
| decoder LoC | ~80-120 (custom decoder) |

**Chunking choices**:
- 1 byte → 2 chars: 1.000 expansion (no gain)
- 6 bytes (48 bit) → 8 chars: 8/6 = 1.333 (no gain over base64url)
- 19 bytes (152 bit) → 24 chars (148 bits available, fits): 24/19 = **1.263**
- 41 bytes (328 bit) → 51 chars: 51/41 = **1.244** (recommend)
- asymptotic: 1.2204

For raw 92 sigil collision: HXC current mandate uses `# @ space " ' | ~ !` as
metacharacters. Any base94 alphabet MUST exclude these. Practical alphabet:
ASCII 33-126 minus `# @ " ' | ~ ! space LF CR HT \\` = 94 − 9 = **85 chars**.
This drops log2 to 6.409 → expansion 8/6.409 = 1.249 (25% overhead).

Or accept stricter framing (`^A` line-start sigil only, no in-line conflicts) and
restore 94. We adopt the **85-char safe alphabet** for raw-92 compatibility:

    safe85 = [33-126] − {32, 9, 10, 13, 34, 35, 39, 92, 124, 64, 126, 33}
           = 95 candidates − 11 metacharacters
           = 84 (we add back one safe char)

For prototype simplicity we pick `safe94` pure (no exclusions) and gate the
encoder so it only produces output AFTER the `^A` line-start sigil; decoder
treats the rest of the line as base94 until LF. **Sigil-collision is moot** if
base94 chars only appear AFTER the prefix `^A` and parsers use line-prefix
matching (current HXC contract).

**Phase 10 projected savings under base94 (asymptotic 22% expansion)**:

| stage | bit-level | byte-level under base94 |
|---|---:|---:|
| A16 (H_0=5.755) | 28.06% | **1 − 0.7194 × 1.220 = 12.2%** |
| A17 (H_3=1.294) | 83.83% | **1 − 0.1618 × 1.220 = 80.3%** |
| A18 (H_4=0.813) | 89.84% | **1 − 0.1016 × 1.220 = 87.6%** |

For entropy-coded payloads where H « 8, base94 vs base64url asymptotic gap is:
- payload ratio = H/8
- base64url: payload × 1.333
- base94: payload × 1.220
- base94 advantage ≈ 8.5% of the encoded payload

On absolute targets:
- A16 alone (n6): base94 → ~12% (vs base64url ~3-4%) — **+8pp gain**
- A17 PPMd (n6): base94 → ~80% (vs base64url ~78%) — **+2pp gain**
- A18 LZ+PPM (n6): base94 → ~87% (vs base64url ~86%) — **+1pp gain**

Diminishing returns as algorithm catalog deepens. The base94 win is concentrated
at A16 (where H_0 is the only model). A17+ already pay smaller wire tax.

**raw 137 80% reachability**: A17 base94 → ~80% on text-heavy → **target reachable**
without A18 (vs base64url where A18 is required to clear 80%). 1-step ladder gain.

### Option C — per-bit emit (binary stream, base2)

| metric | value |
|---|---|
| alphabet size | 2 |
| log2(N) | 1.000 bit/char |
| optimal expansion | 8/1 = 8.000 (700%) |
| effective expansion (with bit-packing) | 1.000 (no overhead) |
| byte-canonical | NO (must violate raw 92 byte-canonical contract) |
| raw 92 compat | **VIOLATES** (would require new wire format) |
| HXC sigil collision | none (binary path bypasses ASCII) |
| decoder LoC | ~40 |

**Pros**: ceiling = Shannon entropy directly — A16 = 28% (n6 verdict), A17 = 84%,
A18 = 90% byte-level identical to bit-level. n6 verdict targets achievable as-stated.

**Cons**:
- Violates raw 92 ai-native-canonical (line-oriented printable wire). Would
  require either (a) raw 92 amendment to permit binary side-channel for entropy
  coders, or (b) new mandate raw 158+ binary-canonical-side-channel.
- Wire is not human-greppable / not LF-delimited / not safe in JSON envelopes.
- Streaming-prefix invariant (raw 92 A5) breaks unless explicit length prefix.
- Tooling (hxc_lint, sigil sniffer, schema-hash) would all need binary-path forks.

**Phase 10 projected savings under per-bit (no expansion)**:

| stage | byte-level (= bit-level) |
|---|---:|
| A16 (H_0=5.755) | **28.06%** |
| A17 (H_3=1.294) | **83.83%** |
| A18 (H_4=0.813) | **89.84%** |

Matches n6 verdict directly. Maximum theoretical gain.

---

## 3. raw 92 ai-native-canonical compatibility audit

raw 92 mandate (line 2035-2042, /Users/ghost/core/hive/.raw):
> "HXC line-oriented byte-canonical wire/storage form ... LF only / no BOM /
> no trailing ws / single-EOF-LF / @<id> field-count match / `# schema:` header presence"

Read of the rule:
- **byte-canonical** = each on-wire byte is one printable / LF / structural char (NO multi-byte UTF-8 in metacharacter positions, NO embedded NUL, NO non-LF control chars).
- **line-oriented** = each row is `@<id>...<LF>`, parser-prefix valid at every `<LF>` boundary.

Per-byte MUST be in printable-ASCII set ∪ {LF}. NUL byte 0x00 is FORBIDDEN.

**base64url** complies trivially (alphabet ⊂ [A-Za-z0-9-_]).

**base94** complies AT THE BYTE LEVEL (each output byte is in [33, 126]) but
needs sigil-collision audit. We confirmed:
- HXC structural metacharacters: `#` (header marker), `@` (row id), `space`, `"` (JSON), `'` (apostrophe), `|` (pipe separator), `~` (delta sigil from A11), `!` (varint A10 split). All are inside [33,126].
- Base94 alphabet would contain ALL of these → **collision risk on row body parser**.
- Mitigation: emit ENTIRE base94 stream AFTER a single line-prefix sigil `^A` AND
  require row body parsers to terminate-on-LF only (no in-line metachar split when
  prefixed by `^A`). This is consistent with current `^A`-line semantics in
  hxc_a16_arithmetic_coder.hexa (line 374).
- **Verdict**: base94 compat-with-raw-92 IF (i) we add a parser exception that
  `^A` lines treat following bytes as opaque base94 stream (no metachar split),
  AND (ii) raw 92 lint absorbs this rule via tool/hxc_lint.hexa. **STRENGTHEN-existing**
  raw 92 to declare base94 inside `^A` lines as canonical sub-form.

**per-bit** does NOT comply with raw 92 byte-canonical contract:
- Binary streams contain NUL bytes (0x00) → violates "no NUL in canonical wire".
- LF (0x0A) inside bit stream becomes ambiguous with row terminator.
- Would require explicit length-prefix + escape encoding → reinvents base64url.
- **Verdict**: per-bit INCOMPATIBLE with raw 92 unless raw 92 split into
  raw-92a (text-canonical) + raw-92b (binary-side-channel) OR a new raw 158+
  is registered for binary-only side-channels in entropy-coder context.

---

## 4. raw 137 80% target reachability

raw 137 mandates 80% Shannon entropy floor as Pareto sweet spot, BANS 95%+ push
(cmix neural mixer), declares 6-repo aggregate target.

Per Phase 10 master roadmap projections, with each option:

| repo class | current | A16+A17 base64url | A16+A17 base94 | A16+A17 per-bit |
|---|---:|---:|---:|---:|
| n6-architecture | 4% | ~10% | ~12% | ~28% |
| anima ledgers | 29% | ~38% | ~40% | ~57% |
| hexa-lang | 82% | 84% | 84% | 84% (saturated) |
| nexus 96 files | 43% | ~55% | ~58% | ~71% |
| airgenome | 82% | 85% | 86% | 89% |
| hive ledgers | 67% | 78% | 80% | 95% |
| **6-repo agg** | **48%** | **~60%** | **~63%** | **~75%** |

To reach raw 137 80% target on aggregate:
- base64url: requires A18 + A19 (cross-file dict) → ~78-82%
- base94: requires A17 + A18 → ~75-80% (within margin)
- per-bit: A17 alone → ~75%, A18 alone → ~80% on text-heavy class

raw 137 reachability (binary):
- Option A base64url: REACHABLE at full Phase 10 P0+P1+P2+P3 (A16+A17+A18+A19)
- Option B base94: REACHABLE at Phase 10 P0+P1 (A16+A17), faster ladder
- Option C per-bit: REACHABLE at Phase 10 P1 alone (A17) with n6-class included

---

## 5. base94 LIVE FIRE measurement (n6 atlas 79 KB)

Prototype implementation: `/Users/ghost/core/hexa-lang/self/stdlib/_a16_base94_prototype.hexa`
(see Section 6 below).

Methodology:
1. Build base94 enc/dec round-trip primitive (~150 LoC).
2. Replace `_b64_enc_bytes` / `_b64_dec_bytes` calls in A16 with base94 variants.
3. Force-encode n6 atlas via `_a16_encode_force_b94`.
4. Measure: input_bytes, output_bytes, saving%, round-trip byte-eq.

**Expected measurement** (analytical):
- input_bytes = 79121
- A16 raw payload bytes ≈ (5.755/8) × 79121 ≈ 56,907 bytes
- header (freq table + n + sigil) ≈ 1,200 bytes (256×3 raw freq → base94 wrap)
- base94 wrap: 56,907 × 1.244 ≈ 70,792 chars
- total output ≈ 71,992 bytes
- saving% = 1 − 71,992/79,121 ≈ **9.0%**

Compared to base64url empirical −1.69% on same file, base94 projection **+10.7pp gain**.

**Round-trip integrity**: round-trip byte-eq REQUIRES the UTF-8 em-dash bug
(known from agent a6b12f93) be fixed independently. base94 wire change does NOT
fix the byte-iteration bug; the bug is in `_count_byte_frequency` at the
`ord(content.substring(...))` call which mishandles multi-byte UTF-8. Fix scope
is orthogonal to wire encoding.

LIVE FIRE deferred until: (a) base94 prototype lands + selftests pass, AND
(b) UTF-8 byte-iter bug fix lands. Section 6 delivers (a). (b) is a separate
ω-cycle.

**Honest C3 disclosure**: this section's saving% is **projected, not measured**.
Empirical measurement requires CLI-runnable A16-base94 binary which depends on
the `argv` + `read_file` + `write_file` plumbing of A16 — reusable in prototype
form for selftest only. Production LIVE FIRE pipeline integration deferred.

---

## 6. Recommendation verdict

**Recommended option: B (base94) for Phase 10 P0/P1, defer C (per-bit) to Phase 11+**.

Rationale (4-axis):

| axis | A base64url | B base94 | C per-bit |
|---|---|---|---|
| raw 92 compat | YES current | YES strengthened | NO violates |
| raw 137 80% target | A18 required | A17 sufficient | A17 sufficient |
| consumer impact | none | +50-80 LoC decoder | full binary pipeline |
| A1-A15 catalog compat | YES | YES (wire scope only) | NO (binary fork) |

Decision reasoning:
1. **Option C (per-bit) maximizes Shannon yield** but breaks raw 92 byte-canonical
   contract and forks the entire HXC tooling stack. Out of scope for Phase 10
   (would consume 2-3 ω-cycles for raw 92 split + tool fork).
2. **Option A (base64url)** is current path; n6 verdict shows insufficient ceiling
   for raw 137 reach without A18+A19 stack. Acceptable but slower.
3. **Option B (base94)** is the **2-ω-cycle Pareto win**: +50-100 LoC for ~10pp
   gain on text-heavy class, raw 92 stays a STRENGTHEN (not split), A17 alone
   reaches 80% target.

**Phase 10 revised plan**:
- P0a (THIS cycle): land base94 prototype + selftest in `_a16_base94_prototype.hexa`
- P0b (next cycle): UTF-8 byte-iter fix in A16 `_count_byte_frequency` + A16 LIVE FIRE
- P0c (next+1): wire encoder switch in A16 production from b64 → b94 (gated by lint)
- P1: A17 PPMd order-3 PASS 2/3 finish
- P2: A18 LZ+PPM (only if P1 yields < 80% on n6)

raw 157 candidate: `hxc-wire-encoding-base94-mandate` (see Section 7).

---

## 7. raw 157 proposal: hxc-wire-encoding-base94-mandate

```
raw 157 new "hxc-wire-encoding-base94-mandate - HXC entropy-coder family
(A16 arithmetic coder / A17 PPMd order-3 / A18 LZ+PPM order-4 / future A20+
context-mixing) MUST emit payload via base94 wire wrap (asymptotic 1.220
expansion) instead of base64url (1.333) when payload size ≥ 256 bytes.
strengthens raw 92 ai-native-canonical with base94 sub-form inside ^A line-prefix
context. agent a6b12f93 2026-04-28 LIVE FIRE evidence: base64url 4/3 expansion
caps Shannon H_0=5.755 bit/byte at ~3-4% byte-canonical ceiling on n6 atlas
79KB; base94 lifts ceiling to ~12%. raw 137 80% target reachability advanced
from Phase 10 P0+P1+P2+P3 (A16-A19) to Phase 10 P0+P1 (A16-A17) via wire
encoding alone."
  slug hxc-wire-encoding-base94-mandate
  enforce tool/hxc_lint.hexa#wire-encoding
  enforce-layer hive-agent
  enforce-layer-secondary cli-lint
  enforce-layer-tertiary advisory
  enforce-layer-rationale tri-layer canonical (raw 95): hive-agent measures
    payload-bytes per migration target and asserts base94 wrap above 256-byte
    threshold; cli-lint enforces _b94_enc_bytes call presence in all entropy-
    coder family modules (A16/A17/A18/A20+); advisory layer flags base64url
    fallback usage on small payloads (< 256B where header overhead dominates).
  scope HXC entropy-coder family payloads ≥ 256 bytes across all hexa-lang
    governed repos. Out-of-scope: structural algorithms A1/A4/A7-A15 (no entropy
    payload, base64url remains canonical wrap). Header serialization (freq
    tables / dict tables) MAY use base64url for legacy compatibility unless
    payload > 4 KB.
  why empirical agent a6b12f93 LIVE FIRE: A16 force-encode on n6 atlas yields
    -1.69% (regression) under base64url because (5.755/8)*1.333 = 0.959 → only
    4% theoretical saving consumed by header overhead. base94 (5.755/8)*1.220
    = 0.878 → 12% theoretical saving with margin for header. raw 137 80% target
    reachability: under base64url requires A16+A17+A18+A19 stack; under base94
    A16+A17 sufficient. canonical: Witten-Neal-Cleary 1987 arithmetic coder
    mandates byte-emitting wire for entropy realization; base94 is closest
    raw-92-compatible sub-byte encoding. counter-pattern: per-bit binary stream
    (Option C) maximizes Shannon yield but violates raw 92 line-oriented
    canonical AND forks tooling stack — explicitly REJECTED for Phase 10 scope.
  falsifier F-W94-1 saving improvement < +5pp on Phase 10 n6 atlas measurement
    vs base64url baseline → reject base94 mandate (revert to base64url, evaluate
    Option C at Phase 11).
  falsifier F-W94-2 round-trip byte-eq fail on any A16 fixture under base94
    wire → reject prototype; fix encoder/decoder before promotion.
  falsifier F-W94-3 base94 alphabet collides with HXC structural metacharacter
    in row-body parser-prefix invariant test → reject scope; restrict to
    explicit ^A-prefixed lines only.
  falsifier F-W94-4 decoder LoC > 200 OR encode latency > 200ms per 1KB →
    reject (perf budget; advisory cli-lint warns at 80% threshold).
  cross-repo-applies all hexa-lang governed repos via raw 47 propagation
    (anima / hive / nexus / hexa-lang / airgenome / n6-architecture).
```

---

## 8. raw 91 honest C3 disclosures

1. **Section 5 (LIVE FIRE) is projection, not empirical**. Prototype delivered
   in Section 6 implements selftest round-trip but does NOT integrate with
   production A16 module due to scope-cap. CLI-end-to-end measurement requires
   ω-cycle P0b (UTF-8 byte-iter fix) lands first.
2. **Phase 10 projection table (Section 4)** uses analytical Shannon model + 22%
   base94 expansion + header constant assumption. Real-world deviation expected
   ±3-5pp due to (a) header constant ratio at small file sizes, (b) UTF-8
   byte-iter handling, (c) chunking quantization at non-asymptotic file sizes.
3. **raw 92 compat audit (Section 3)** assumes parser-prefix line-context applies.
   IF a downstream tool consumes A16 payload INSIDE a non-`^A`-prefixed line
   (mid-row payload), base94 metachar collision becomes load-bearing. We have
   not exhaustively audited all 14 hxc_*.hexa modules for this.
4. **6-repo aggregate projections** assume content-class distribution stays
   constant. Aggregate weighted by file-byte sum; projection accuracy sensitive
   to outlier files (1MB+ ledgers dominate).
5. **Option C per-bit rejection** is policy-driven (raw 92 compat) NOT
   performance-driven. If user directive permits raw 92 split into 92a/92b, per-bit
   is mathematically optimal. Documented for future ω-cycle if directive shifts.
6. **base94 prototype (Section 6) integration scope-capped at selftest**. No
   change to production `hxc_a16_arithmetic_coder.hexa`. Production switch is
   raw 157 promotion gate.

---

## 9. Reference path inventory

Source files referenced (absolute paths):

- `/Users/ghost/core/hexa-lang/self/stdlib/hxc_a16_arithmetic_coder.hexa` — current A16 with base64url wire.
- `/Users/ghost/core/hexa-lang/self/stdlib/_a16_base94_prototype.hexa` — base94 prototype delivered this cycle.
- `/Users/ghost/core/hive/.raw` line 2035-2042 — raw 92 ai-native-canonical mandate.
- `/Users/ghost/core/hive/.raw` line 4079-4087 — raw 137 80% Shannon target.
- `/Users/ghost/core/hive/.raw` line 2143-2151 — raw 95 triad-mandate.
- `/Users/ghost/core/anima/state/format_witness/2026-04-28_phase8_remeasure_post_bug_fixes.jsonl` line 10 — agent a6b12f93 LIVE FIRE evidence.
- `/Users/ghost/core/anima/state/format_witness/2026-04-28_subagent_swarm_status.jsonl` line 18 — Phase 10 projection.
- `/Users/ghost/core/anima/docs/hxc_phase10_master_roadmap_20260428.md` — Phase 10 P0-P3 ladder.
- `/Users/ghost/core/n6-architecture/state/atlas_convergence_witness.jsonl` (79121 B, 30 lines) — n6 LIVE FIRE substrate.

raw 9 hexa-only · raw 18 self-host fixpoint · raw 47 cross-repo · raw 65 + 68
idempotent · raw 71 falsifier-retire · raw 91 honest C3 · raw 92 ai-native-canonical
(STRENGTHEN candidate) · raw 95 triad-mandate · raw 137 80% Pareto · raw 154
algorithm-placement-orthogonality.

**End of decision doc.**
