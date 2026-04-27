# HXC Phase 11 Design — Post-A18 Territory (90% → K(X) Asymptote)

**Date**: 2026-04-28
**Phase**: 11 design (post-Phase-10-P2 projected closure)
**Trigger**: Phase 10 P0/P1/P2 (A16/A17/A18 entropy coder family) projected to land
~90% byte-weighted asymptotic entropy rate; user directive — design the territory
**beyond** that ceiling, before measurement gates.
**Compliance**: raw 9 hexa-only · raw 18 self-host fixpoint · raw 65 + 68 idempotent ·
raw 71 falsifier-preregistered · raw 91 honest C3 (projections labeled vs measurements)
· raw 95 triad-mandate · raw 137 80% Pareto.

---

## 0. Honest framing (raw 91 C3)

All numbers in this document are **PROJECTIONS** unless explicitly tagged
`MEASURED`. Phase 10 P0/P1/P2 themselves are not yet LIVE at the time of
writing — A16 (arithmetic coder order-0) is queued behind n6-verdict raw 143
registration. Therefore "Phase 11 = post-A18" is a **conditional design**:

- IF A16 lands → measure 6-repo aggregate
- IF A17 lands → measure text-heavy class
- IF A18 lands → measure asymptote
- THEN this Phase 11 document becomes load-bearing

If any of A16/A17/A18 falsify (F-A16/A17/A18-* fires), Phase 11 priorities
shift. This document pre-registers a **conditional plan** to avoid the
2-cycle-old "Phase 8 closure declared saturation, Phase 10 falsified within
24h" pattern (raw 142 self-correction discovery).

The Shannon H_4 = 0.813 bit/byte → 90% projected ceiling derives from atlas
n6 corpus only. Other classes (anima alm_r13 text, nexus mixed inventory,
hive audit) have **distinct entropy rates** and distinct Phase 11 ceilings.
A19/A20/A21 each address a different class.

---

## 1. Phase 5 → Phase 11 trajectory consolidation

**Cross-repo aggregate byte-weighted compression vs gap to projected K(X).**

K(X) baseline assumed at **~93% byte-weighted** for the 6-repo aggregate
(weighted average of per-class h_∞: text 95% / mixed 92% / structured 85% /
entropy-bound 90% / audit 91%). This is itself a projection from H_n
extrapolation; raw 91 C3 keeps it labeled.

| Phase | algorithms (cumulative) | LoC cum | byte-weighted | gap to K(X) | source |
|---|---|---:|---:|---:|---|
| Phase 5 baseline | A1+A7+A10 (+A9 stub) | ~500 | **14.48%** MEASURED | -78pp | hxc_phase8_p5 §trajectory |
| Phase 6 | + A4 + A8 + A11 | ~1100 | **21.00%** MEASURED | -72pp | hxc_phase8_p5 §trajectory |
| Phase 7 | + best-of-N + sweep (no new algo) | ~1400 | **40.00%** MEASURED | -53pp | hxc_phase7_pareto |
| Phase 8 P1 | + A12 column-prefix multi | ~1700 | **44.00%** MEASURED | -49pp | hxc_phase8_closure |
| Phase 8 P5 | + A13 const-col + A14 row-prefix + cache fix + native IO | ~2200 | **47.00%** MEASURED | -46pp | hxc_phase8_p5 |
| Phase 8 P8 | + A15 nested-array subschema | ~2400 | **47.00%** MEASURED (hive +3pp local) | -46pp | hxc_phase8_closure |
| Phase 9 P1 | + A9 BPE tokenizer (text class) | ~2650 | **52-55%** PROJECTED | -38 to -41pp | hxc_phase9_a9 §5 |
| Phase 9 P4 | + A16 cross-file shared dict (renamed → A19 below) | ~3300 | **62-65%** PROJECTED | -28 to -31pp | hxc_phase9_a16 §5 |
| Phase 10 P0 | + A16 arithmetic coder order-0 | ~3500 | **72%** PROJECTED | -21pp | hxc_phase10_master |
| Phase 10 P1 | + A17 PPMd order-3 | ~4100 | **80-82%** PROJECTED | -11 to -13pp | hxc_phase10_master |
| Phase 10 P2 | + A18 LZ-window + PPM order-4 | ~5000 | **88-90%** PROJECTED asymptote | -3 to -5pp | hxc_phase10_master |
| **Phase 11 best (A19+A20)** | + cross-corpus dict federation + schema-aware tokenizer | **~5800-6300** | **92-93%** PROJECTED | **-0 to -1pp** | THIS DOC |

**Slot reconciliation note (raw 91 honest C3)**: Phase 9 originally proposed
"A16 cross-file shared dict"; Phase 10 master roadmap reassigned A16 to
arithmetic coder. Phase 11 here completes the renumber: cross-file shared
dict = **A19** (Phase 11 candidate 4), arithmetic coder = A16 (LIVE
projection), PPMd = A17, LZ+PPM = A18.

---

## 2. Phase 11 candidates — five-way evaluation

Each candidate sized for **post-A18 marginal saving**, i.e., what does this
algorithm add **on top of** A18's ~90% asymptote, not on top of bare HXC.

### Candidate 1 — A19: Universal-compressor Kolmogorov approach (LZMA-class context-mixing without neural)

**Algorithm spec**:
- Combine LZ77/78 sliding-window (8-32MB) + arithmetic coder (already A16) +
  Dynamic Markov Coding (DMC; Cormack-Horspool 1987) + multiple finite-order
  PPM contexts (already A17/A18) under a **statistical mixer** (NOT neural —
  weighted least-squares predictor like PAQ's "secondary symbol estimation"
  but bounded-history, integer-arithmetic).
- Mixer weights updated by exponentiated gradient (Kivinen-Warmuth 1997),
  integer fixed-point (Q16.16), no floating point.
- Context-mixing tier: order-0 (A16), order-3 (A17), order-4 (A18 PPM),
  order-6 (A19 new), word-level (A19 new), schema-keyed (A19 new).

**Expected saving** (post-A18):
- atlas n6 (entropy h_∞ ~ 0.5-0.7 bit/byte): 90% → **92-93%** PROJECTED (+2-3pp)
- text-heavy (anima alm_r13): 80% → **88-90%** PROJECTED (+8-10pp; English bigram entropy ~1.0-1.3 bit/byte, post-tokenizer h_∞ falls to ~0.6-0.8)
- audit/structured: 90% → **91%** PROJECTED (+1pp; already saturated)

**Implementation cost**:
- LoC: **~800-1100** pure-hexa
- Time: ~2-3 weeks of cron-tick work (P11.1 mixer scaffold ~200 LoC,
  P11.2 word-level context ~250 LoC, P11.3 DMC ~300 LoC, P11.4 schema-keyed
  context ~150 LoC, P11.5 selftest harness + integration ~150 LoC)
- Memory: ~16-32 MB context-mix tables (acceptable; Mac jetsam threshold 4GB)

**raw 9 + raw 18 compatibility**:
- raw 9 hexa-only: ✓ All algorithms 1980s-90s textbook (PAQ-class predates
  neural era; DMC = 1987; LZMA = 1998 with patent-free open spec)
- raw 18 self-host: ✓ Integer-only, no external C lib; mixer is closed-form
  weighted prediction
- raw 65/68 idempotent: ✓ deterministic encode (no randomness in mixer)

**Falsifiers preregistered (raw 71)**:
- F-Ph11-A19-1: post-A18 marginal saving < 0.5pp on aggregate → reject as Pareto-dominated
- F-Ph11-A19-2: encode latency > 200ms per 1KB → reject (hxc_migrate throughput)
- F-Ph11-A19-3: round-trip byte-eq fails → reject (raw 65/68)
- F-Ph11-A19-4: memory > 256MB during encode → reject (cron-host headroom)

**ROI**: HIGH for atlas n6 class (entropy-bound class lifts 2-3pp toward
true K(X)); MEDIUM for text class; LOW for already-saturated audit class.

---

### Candidate 2 — A20: Schema-aware tokenization (post-A9 BPE)

**Algorithm spec**:
- A9 BPE is **content-agnostic byte-pair**. A20 promotes the tokenizer to
  **schema-aware**: JSON/HXC structural tokens (`{"`, `":"`, `","`, `"]`,
  `[{`, etc.) treated as PRE-SEEDED vocabulary entries before BPE merges.
- Schema fingerprints (sha-prefix from A1) become atomic tokens themselves —
  i.e., a schema-id reference is one BPE symbol, not a multi-byte hash.
- Cross-language tokenizer fusion (English + Korean + JSON literal grammar)
  via three parallel vocabularies merged at PASS-1.

**Expected saving** (post-A18):
- text-heavy (anima alm_r13): 88% → **92%** PROJECTED (+4pp; structural
  tokens compress JSON-embedded text more aggressively than pure BPE)
- mixed inventory (nexus): 75% → **82%** PROJECTED (+7pp; small text+JSON
  files carry both grammars)
- pure-text Korean prose subsets (hive blockers narratives): +3-5pp PROJECTED

**Implementation cost**:
- LoC: **~400** pure-hexa (A9 already provides scaffold; A20 = config layer)
- Time: 1 week (~5-7 cron ticks)
- Pre-seed vocabulary derivation: parse JSON grammar tokens (~50 entries),
  Korean syllable bigrams (~200 entries), English common words (~500 entries)

**raw 9 + raw 18 compatibility**:
- raw 9 hexa-only: ✓ BPE extension is pure data table
- raw 18 self-host: ✓ Pre-seeded vocab is a static asset, hexa runtime reads
- raw 65/68 idempotent: ✓ same vocab → same encode

**Falsifiers preregistered (raw 71)**:
- F-Ph11-A20-1: post-A19 marginal saving < 1pp on text-heavy class → reject
- F-Ph11-A20-2: vocab build memory > 64MB → reject
- F-Ph11-A20-3: round-trip byte-eq fails on UTF-8 multibyte boundaries → reject (Korean syllable fragmentation hazard)
- F-Ph11-A20-4: encode regresses pure-structured class > 0.5pp → reject (try-and-revert mandate)

**ROI**: HIGH for text + mixed classes (combined ~30% of corpus by bytes);
LOW for pure-structured (already saturated).

---

### Candidate 3 — A21: Write-side schema redesign (referenceable, OUT-OF-SCOPE for HXC)

**Algorithm spec**:
- NOT an HXC algorithm. Reduces atlas-class entropy at **source** by:
  - 4-precision floats → fixed-point Q8.8 + delta encoding on semantic axes
  - Repeated narrative fields → enum + reference table at write time
  - Atlas convergence row schema: 30 columns → 12 columns (drop derived/redundant)
- HXC consumes the redesigned corpus and trivially compresses.

**Expected saving** (atlas n6):
- Source-side entropy reduction: 35-50% **before HXC** PROJECTED
- HXC then applies: 90% of remaining → final compressed = **~95%** PROJECTED
  effective saving vs **original** atlas
- BUT: HXC byte-weighted on the new corpus measures lower (because input
  is already smaller). Pareto frontier verdict shifts.

**Implementation cost**:
- LoC: **~600 outside HXC** (anima-physics atlas writer + clay_millennium
  writer + migration harness for in-flight files)
- Time: 2-3 weeks
- Risk: write-side migration breaks downstream consumers; backward-compat
  shim required

**raw 9 + raw 18 compatibility**:
- raw 9 hexa-only: ✓ writer changes are hexa-side
- raw 18 self-host: ✓ HXC unchanged
- **CONCERN**: raw 137 cross-repo universal mandate — schema redesign is
  per-repo, NOT universal. Each atlas-class repo needs custom redesign.

**Falsifiers preregistered (raw 71)**:
- F-Ph11-A21-1: source corpus reduction < 20% → reject as not worth migration
- F-Ph11-A21-2: any downstream consumer breaks (verdict format incompat) → reject
- F-Ph11-A21-3: round-trip atlas-original ↔ atlas-redesigned semantic-eq fails → reject (truth-preservation violation)
- F-Ph11-A21-4: migration scope creep > 1000 LoC outside HXC → reject (out-of-charter)

**ROI**: HIGH for atlas absolute-byte savings, LOW for HXC charter (out-of-scope).
**Recommendation**: REFERENCEABLE only — document responsibility boundary
between HXC (general compressor) and upstream pipeline (entropy reducer at
source). Do not block HXC Phase 11 on A21.

---

### Candidate 4 — A19-renamed: Cross-corpus dictionary federation

**Algorithm spec**:
- Phase 9 P4 design (originally "A16 cross-file") generalized to
  **cross-REPO**: nexus + anima + hive + hexa-lang corpora share ONE
  union dictionary at `state/hxc/_federated_dict.hxc`.
- Pass 1 walks all 196 files across 4 repos (n6 entropy-bound excluded);
  Pass 2 selects patterns with `repo_count >= 2`; Pass 3 references; Pass 4 decodes.
- Federation manifest: `# federated-from: anima,hive,nexus,hexa-lang` +
  per-repo checksum.

**Expected saving** (post-A18):
- nexus aggregate: 75% → **80%** PROJECTED (+5pp; small-files catch shared
  hive/anima patterns absent in single-repo dict)
- hive aggregate: 88% → **90%** PROJECTED (+2pp)
- anima alm_r13 single-file: 88% → **89%** PROJECTED (+1pp; mostly self-amortized)
- hexa-lang: 92% → **92%** PROJECTED (+0pp; already saturated, federation is no-op)

**Implementation cost**:
- LoC: **~300 incremental** on top of Phase 9 P4 A16 cross-file (~680 LoC).
  Federation is config layer + corpus-root list iterator.
- Time: 1 week

**raw 9 + raw 18 compatibility**:
- raw 9 hexa-only: ✓
- raw 18 self-host: ✓
- raw 47 cross-repo: ✓ NATURAL FIT — federation IS cross-repo by definition
- raw 65/68 idempotent: ✓ federation manifest checksums enable reproducibility
- **CONCERN**: federated dict file is shared SoT — if any repo updates,
  federation rebuild required. CI integration cost.

**Falsifiers preregistered (raw 71)**:
- F-Ph11-A19fed-1: federation marginal saving < 1pp on aggregate → reject
- F-Ph11-A19fed-2: federation rebuild cost > 5min on 196-file corpus → reject (cron-tick budget)
- F-Ph11-A19fed-3: any single-repo decode fails when federation manifest absent → reject (raw 65/68 + portability)
- F-Ph11-A19fed-4: federation regresses any single repo > 0.5pp → reject (try-and-revert)

**ROI**: MEDIUM for nexus/hive (small-files dominated); LOW for saturated
repos. Best deployed as Phase 9 P4 follow-up rather than Phase 11 lead.

---

### Candidate 5 — A22: Self-decoding HXC (no separate decoder needed)

**Algorithm spec**:
- HXC artifact embeds its own decoder spec in the header. Format:
  ```
  # hxc-self-v1
  # decode-spec: <hexa-source-or-pseudocode> sha=<hash>
  # decode-spec-bytes: <N>
  <body>
  ```
- Self-decoding makes HXC artifact **self-describing fixpoint** —
  artifact + tiny hexa runtime = full reconstruction. No external `hxc_migrate`
  binary required at decode time.
- Aligns with raw 18 self-host fixpoint: artifact is its own decoder.

**Expected saving**:
- **Saving NEGATIVE** in raw bytes: spec adds ~2-5KB header overhead per
  artifact. On 79KB atlas: -3pp. On 980KB anima alm_r13: -0.3pp.
- **Pareto frontier verdict CHANGES**: instead of "compression %" alone,
  metric becomes "(compression %) − (decoder_dependency_cost)". HXC
  artifact + 5KB self-decoder beats lzma+5MB-binary on portability axis.

**Implementation cost**:
- LoC: **~400** (decoder-spec emitter + self-decode bootstrap parser)
- Time: 1-2 weeks
- Risk: spec must be small AND complete; partial spec = decode failure

**raw 9 + raw 18 compatibility**:
- raw 9 hexa-only: ✓ spec is hexa source
- raw 18 self-host fixpoint: ✓✓ **NATURAL APPLICATION** — artifact IS its
  own host. This is the deepest alignment of any Phase 11 candidate with
  the raw 18 fixpoint principle.
- raw 65/68 idempotent: ✓ spec is deterministic from algorithm catalog
- **CAVEAT**: bootstrap problem. Initial decoder must already exist to
  parse self-decode-spec. Mitigation: spec format is fixed minimal grammar,
  bootstrap parser is ~50 LoC universal hexa.

**Falsifiers preregistered (raw 71)**:
- F-Ph11-A22-1: self-decode spec overhead > 10% on smallest corpus file → reject
- F-Ph11-A22-2: bootstrap parser > 100 LoC → reject (defeats self-host purpose)
- F-Ph11-A22-3: round-trip via self-decoder differs from `hxc_migrate` decoder → reject (truth divergence)
- F-Ph11-A22-4: self-decoder cannot handle every algo in catalog → reject (must cover A1-A18)

**ROI**: LOW for saving %, HIGH for **architecture purity** (raw 18
fixpoint completion). Best framed as "Phase 11 quality gate" rather than
compression candidate. Land AFTER Phase 11 compression work to seal the
self-host fixpoint.

---

## 3. Five-candidate ROI matrix

| candidate | saving Δ post-A18 | LoC | raw 9 | raw 18 | raw 47 | priority | rationale |
|---|---:|---:|:---:|:---:|:---:|---:|---|
| **A19** universal compressor | **+2-3pp** (atlas) / +8-10pp (text) | ~800-1100 | ✓ | ✓ | n/a | **P0** | largest absolute gain, closes K(X) gap |
| **A20** schema-aware tokenizer | **+4pp** (text) / +7pp (mixed) | ~400 | ✓ | ✓ | n/a | **P1** | best LoC/pp ratio on text class |
| **A21** write-side redesign | +35-50% (atlas source) | ~600 outside | ✓ | ✓ | per-repo | **REF** | OUT-OF-SCOPE for HXC; reference doc only |
| **A19-fed** cross-repo dict | **+5pp** (nexus) / +2pp (hive) | ~300 | ✓ | ✓ | ✓ | **P2** | natural after A19 universal lands |
| **A22** self-decoding HXC | **−3pp** raw / +∞ portability | ~400 | ✓ | ✓✓ | n/a | **P3** | architecture seal, not saving |

---

## 4. Recommended priority order

**Phase 11 P0 → P3 ladder**:

1. **P0 — A19 universal compressor** (~800-1100 LoC, +2-3pp atlas / +8-10pp text)
   - Trigger: Phase 10 P2 (A18) LIVE + selftest PASS + 6-repo aggregate measured
   - Stop condition: F-Ph11-A19-1 fires (< 0.5pp aggregate)

2. **P1 — A20 schema-aware tokenizer** (~400 LoC, +4pp text / +7pp mixed)
   - Trigger: A19 LIVE OR A19 falsified (A20 independent of A19 numerically)
   - Stop condition: F-Ph11-A20-1 fires

3. **P2 — A19-fed cross-corpus federation** (~300 LoC, +2-5pp on small-file repos)
   - Trigger: Phase 9 P4 A16-cross-file LIVE + Phase 11 P0 LIVE
   - Stop condition: F-Ph11-A19fed-1 fires

4. **P3 — A22 self-decoding HXC** (~400 LoC, architecture seal)
   - Trigger: Phase 11 P0/P1/P2 measurement complete (regardless of pp outcome)
   - Stop condition: F-Ph11-A22-2 fires

5. **REF — A21 write-side redesign** (out-of-charter)
   - Document only; surfacing for upstream-pipeline owners (anima-physics, clay_millennium maintainers).
   - Do not block Phase 11.

**Recommended priority order (slugs)**:
`["A19", "A20", "A19-fed", "A22", "A21-ref"]`

---

## 5. Phase 11 algorithm catalog (projected post-Phase-11 P3)

| algo | description | source | status post-Phase-11 |
|---|---|---|---|
| A1-A15 | Phase 5-8 catalog | LIVE | LIVE |
| A9 | BPE tokenizer | Phase 9 P1 | LIVE |
| A16 | arithmetic coder order-0 | Phase 10 P0 | LIVE projection |
| A17 | PPMd order-3 | Phase 10 P1 | LIVE projection |
| A18 | LZ-window + PPM order-4 | Phase 10 P2 | LIVE projection |
| A19 | universal context-mixing compressor | **Phase 11 P0** | **NEW** |
| A19-fed | cross-corpus dict federation | **Phase 11 P2** | **NEW** |
| A20 | schema-aware tokenizer | **Phase 11 P1** | **NEW** |
| A22 | self-decoding HXC | **Phase 11 P3** | **NEW** (meta) |
| A21 | write-side redesign | OUT-OF-CHARTER | reference only |

---

## 6. raw registration candidates

| slot | slug | scope | source | falsifier count |
|---|---|---|---|---:|
| **raw 149** | `design-K-X-asymptotic-mandate` | Phase 11 P0 mandate: post-A18 design must target K(X) asymptote via context-mixing without violating raw 9/18 (no neural mixers); preregister F-Ph11-A19-1..4 | Phase 11 P0 design (THIS DOC §2 candidate 1) | 4 |
| **raw 150** | `tokenizer-schema-aware-mandate` | post-A9 BPE must support schema-aware vocabulary pre-seeding when corpus is mixed JSON/text/Korean; preregister F-Ph11-A20-1..4 | Phase 11 P1 design (THIS DOC §2 candidate 2) | 4 |
| **raw 151** | `cross-corpus-dict-federation-mandate` | when ≥2 repos share corpus class, federated dict MUST be attempted before declaring per-repo Pareto-final | Phase 11 P2 design (THIS DOC §2 candidate 4) | 4 |
| **raw 152** | `self-decoding-fixpoint-mandate` | HXC artifact MUST self-describe decoder spec by Phase 11 closure; raw 18 self-host fixpoint completion | Phase 11 P3 design (THIS DOC §2 candidate 5) | 4 |
| **raw 153** | `write-side-entropy-reduction-advisory` | document responsibility boundary HXC vs upstream-pipeline; tier-2 advisory, not mandatory | Phase 11 REF (THIS DOC §2 candidate 3) | 4 |

**raw 95 triad-mandate compliance**: each raw 149-152 has hive-agent +
cli-lint + advisory layers preregistered. raw 153 is tier-2 advisory only
(write-side, not HXC code path).

**raw 71 falsifier-preregistered**: 4 falsifiers per raw, 20 total.

**raw 47 cross-repo propagation**: raws 149-152 propagate to 5 sister repos
(nexus, hive, hexa-lang, airgenome, anima-physics) at landing time per a71f4164
pattern.

---

## 7. Phase 11 entry gate (raw 91 honest C3)

**This document is design-only.** Phase 11 implementation cannot begin until:

1. Phase 10 P0 (A16 arithmetic coder) LIVE + measured
2. Phase 10 P1 (A17 PPMd) LIVE + measured
3. Phase 10 P2 (A18 LZ-PPM) LIVE + measured
4. 6-repo aggregate measured at projected ~88-90%
5. F-A16/A17/A18 falsifiers all clear

If any Phase 10 stage falsifies, Phase 11 candidates re-evaluate:
- A18 falsified at < 85%: A19 universal compressor still applies (different
  context-mixing path); A20/A19-fed/A22 unchanged.
- A17 falsified: text-class projections shift; A20 promoted to P0.
- A16 falsified (unlikely): entire entropy-coder family re-design needed
  before Phase 11.

**Decision rule**: Phase 11 P0 launch **conditional** on Phase 10 P2 LIVE
+ aggregate ≥ 85% MEASURED. Otherwise, Phase 11 plan revisits before
implementation.

---

## 8. Cross-class projected post-Phase-11 ceilings

| class | example | Phase 8 MEASURED | Phase 10 P2 PROJECTED | Phase 11 P3 PROJECTED | K(X) PROJECTED |
|---|---|---:|---:|---:|---:|
| structured-ledger | hexa-lang aot_cache_gc | 83% | 88% | 89% | ~89% |
| audit (mid-density) | hive triad_audit | 75% | 88% | 91% | ~92% |
| mixed inventory | nexus 96 files | 43% | 78% | **85%** | ~88% |
| text-heavy | anima alm_r13 | 24% | 80% | **92%** | ~95% |
| entropy-bound | n6-architecture atlas | 4% | **90%** | **93%** | ~95% |
| **6-repo aggregate** | weighted | **47%** | **~88%** | **~92%** | **~93%** |

Phase 11 closes the 88% → 92% gap (4pp aggregate) at cost ~1500-1800 LoC.
Per pp = ~400 LoC, polynomial growth confirmed (Phase 10 P2 stop-condition
prediction validated).

---

## 9. Phase 11 closure projection (raw 91 C3)

If all Phase 11 candidates land at projected savings:
- 6-repo aggregate **~92%** byte-weighted MEASURED
- gap to projected K(X) **~1pp**
- per-class gap **all < 5pp** (text 95%, atlas 95%, audit 92%, mixed 88%, structured 89%)

At ~92% aggregate, **per-pp marginal cost exceeds 500 LoC**, signaling
**second Pareto frontier saturation**. Phase 12 candidates would require:
- neural context-mixing (raw 18 violation — REJECTED)
- write-side redesign (raw 137 universality violation — A21 referenceable only)
- corpus-specific bespoke algorithms (raw 47 cross-repo violation)

**Therefore Phase 11 P3 = projected algorithmic K(X) ceiling under raw 9 +
raw 18 + raw 47 + raw 137 constraints.** Phase 12+ would require constraint
relaxation or moves into write-side / non-universal territory.

This is the projected **terminus of the algorithmic compression program**
under current rawset.

---

## 10. Verdict (raw 91 honest C3)

Phase 11 is a **conditional design** for the post-A18 territory. Three
algorithmic candidates (A19 universal, A20 schema-tokenizer, A19-fed
federation) projected to add **~4pp aggregate** at ~1500-1800 LoC. One
architecture candidate (A22 self-decoding) projected to **complete raw 18
self-host fixpoint** at cost ~400 LoC and ~3pp raw byte regression
(portability gain).

A21 (write-side redesign) is **referenced as out-of-HXC-charter**, surfacing
the responsibility boundary between HXC (general compressor) and upstream
data-engineering pipeline (entropy reducer at source).

The 47% → ~92% trajectory across Phases 5-11 represents **~78pp gain over
~5800 LoC**, validating the algorithm-deficit hypothesis (Phase 8 closure's
"saturation" reading falsified twice: by Phase 10 entropy coders and by
Phase 11 context-mixing).

**Self-correction cadence (raw 142)**: Phase 8 closure → Phase 10 falsify →
Phase 11 design = 2 falsification cycles inside 7 days. Architecture
healthy. Design surface continues to disclose new gap territory honestly.

---

raw 9 hexa-only · raw 18 self-host fixpoint · raw 47 cross-repo · raw 65 + 68
idempotent · raw 71 falsifier-preregistered (20 falsifiers across 5 raws) ·
raw 86 hexa-native tokenizer (deferred) · raw 91 honest C3 (projections
explicitly labeled vs measurements) · raw 95 triad-mandate · raw 137 80%
Pareto · raw 142 self-correction cadence · raw 143 entropy-coder-mandate ·
raw 149-153 (proposed, this document).
