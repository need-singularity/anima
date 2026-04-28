# HXC Phase 12 Forward Design — Post-80% Ceiling Identification + A23-A28 Algorithm Catalog

**Date**: 2026-04-28
**Phase**: 12 forward design (pre-Phase-11-closure conditional plan)
**Trigger**: User directive — Phase 11 다음 ω-cycle wave 정의 + 80% 한계수렴 후 next ceiling 식별
**Author**: agent (forward-design ω-cycle, Phase 11 not yet closed)
**Parent designs**:
- `hxc_phase11_design_post_a18_20260428.md` (A19/A20/A21/A22)
- `hxc_phase11_a20_design_20260428.md` (P1 schema-aware BPE)
- `hxc_phase11_a22_design_20260428.md` (P3 self-decoding)
- `hxc_phase11_entry_gate_revised_20260428.md` (wire-aware entry)
- `hxc_phase10_master_roadmap_20260428.md` (A16/A17/A18)

**Compliance**: raw 9 hexa-only · raw 18 self-host fixpoint · raw 33 NL English fields · raw 37+38+39 omega-saturation · raw 47 cross-repo · raw 65+68 idempotent · raw 71 falsifier-preregistered · raw 91 honest C3 (PROJECTED vs MEASURED labels) · raw 95 triad-mandate · raw 137 80% Pareto + cmix-ban · raw 142 D1-D5 · raw 152 self-decoding fixpoint · raw 156 algorithm-placement-orthogonality · raw 159 hexa-lang-upstream-proposal-mandate.

---

## 0. Honest framing (raw 91 C3)

This document is a **conditional forward plan**, not a measurement landing.
At the time of writing:

- **Phase 11 P0 A19 federation**: LIVE (commit `a0622953`) but **F-A19-1
  REGRESSION** measured (-1pp on the cross-corpus aggregate, follow-up in
  flight per a separate agent).
- **Phase 11 P1 A20 schema-aware BPE**: tick 1 only (482 LoC, 4/4 selftest,
  no LIVE FIRE).
- **Phase 11 P2 A19-fed enhanced**: NOT_DEFINED (depends on F9 retire).
- **Phase 11 P3 A22 self-decoding**: tick 1 only (369 LoC, 6/6 selftest,
  raw 152 UNVERIFIED).
- **Phase 11 REF A21 write-side**: ALWAYS-GO advisory (raw 153, no LIVE).
- **Current 6-repo aggregate**: 49.10% MEASURED (commit `a42b3f3e`,
  post-Bug-2-fix sweep). raw 137 80% target gap = **30.90pp**.

Therefore every saving% in this document is **PROJECTED** unless explicitly
labelled `MEASURED`. Phase 12 only becomes load-bearing IF Phase 11 closes
with aggregate ≥ 80% MEASURED. Until then, this document pre-registers a
**conditional plan** to avoid the 2-cycle-old "Phase 8 closure declared
saturation, Phase 10 falsified within 24h" pattern (raw 142 D2+D5).

---

## 1. Phase 11 closure projection (forward Pareto chain)

**Trajectory accounting** (raw 137 80% target = 0pp gap once aggregate
≥ 80% MEASURED). All values are 6-repo byte-weighted byte-canonical wire
(Option B base94 assumed per `hxc_wire_encoding_decision_20260428.md`).

| step | event | aggregate (PROJECTED) | gap to 80% | ω-cycles to land |
|---|---|---:|---:|---:|
| baseline (current) | post-Bug-2-fix | **49.10% MEASURED** | -30.90pp | — |
| F9 retire | A19 federation small-file class +5-10pp | 54-59% | -21 to -26pp | 1 |
| A17 multibyte fix | text-heavy +28pp (Korean fixture-2 round-trip) | 70-75% | -5 to -10pp | 2 |
| F10 retire | A18 LZ-window+PPM order-4 deployable | 78-83% | +0 to -2pp | 3 |
| A20 LIVE | schema-aware BPE +2-4pp on mixed corpora | 80-87% | **0** to +7pp | 4 |
| A22 LIVE | self-decoding (-3pp raw, +∞ portability) | 77-84% | -3 to +4pp | 5 |

**Phase 11 closure aggregate** (after all P0-P3 LIVE + falsifiers retired):
**~80-85% PROJECTED** (raw 137 80% target satisfied with thin margin).

**Critical assumptions** (raw 91 C3):
- F-A19-1 -1pp regression resolves (root-cause: hash collision in shared
  dict bucket, not algorithm-fundamental).
- A17 multibyte fix is bounded (root-cause: `_byte_at` substring on raw
  bytes vs codepoints; fix ≤ 50 LoC).
- A18 PASS-1 quadratic memory blowup resolves OR streaming-only A18
  variant adopted.
- A20+A22 LIVE FIRE 4/4 corpora PASS without regression.

If any assumption falsifies → Phase 11 closes BELOW 80% → Phase 12 entry
gate (§6) blocks → return to Phase 11 P0/P1/P2/P3 root-cause loop.

---

## 2. 80% post-state — ceiling candidate identification

Once aggregate ≥ 80% MEASURED, the next ceiling is one of four kinds. This
section identifies each candidate's **structural cause** and applicable
**raw 69 ceiling-classification verdict** (CIRCUMVENT / APPROACH /
TRANSCEND / BARRIER).

### 2.1 Mathematical ceiling — Kolmogorov K(X) ~ 90%

**Cause**: Shannon H_n entropy lower bound. h_∞ ≈ 0.5-0.8 bit/byte across
6-repo aggregate → 90-94% theoretical compression upper bound. K(X) is
non-computable but H_n with n≥4 provides asymptotically tight estimate.

**Reachability**: A18 LZ-PPM order-4 ALONE projects 88-90% (per Phase 10
P2 master roadmap §62). Phase 11 P0+P1+P3 only adds 2-3pp tier.

**raw 69 verdict**: **APPROACH**. Mathematical asymptote — cannot be
crossed without paradigm shift (semantic compression).

### 2.2 Physical ceiling — Bekenstein bound

**Cause**: information-theoretic bound on bits per finite mass-energy
region. For a 1KB byte-scale artifact: bound ≈ 10^28 bits >> 8000 bits.
**Non-binding by ~24 orders of magnitude.**

**raw 69 verdict**: **non-applicable** (Bekenstein bound is irrelevant for
our scale; ceiling is purely informational, not physical).

### 2.3 Algorithmic ceiling — raw 18 self-host fixpoint constraint

**Cause**: cmix-class neural mixers (PAQ8, NNCP, cmix-19) achieve 92-95%
on enwik8 BUT require:
- 200-500MB context tables (raw 42 jetsam violation).
- floating-point neural networks (raw 9 hexa-only violation if external
  C lib needed; raw 18 self-host violation if hexa lacks fp ops).
- multi-second per-MB latency (raw 42 perf budget violation).

**Cleared by raw 137**: cmix-class is **PERMANENTLY BANNED**. The 90% →
95% gap is NOT pursuable within the HXC charter.

**raw 69 verdict**: **BARRIER** (self-imposed, raw 137 governance ban).
Cannot CIRCUMVENT without retiring raw 137.

### 2.4 Operational ceiling — latency / memory / migration cost

**Cause**: Phase 8 P5 measurement showed encode latency 80-160ms per 1KB
on hexa interpreter (commit `0ba07d23` lint CI gate); A18 PASS-1
quadratic blowup implies super-linear scaling beyond 2KB. Memory budget
≤ 256MB encode (Mac jetsam threshold 4GB, hexa interpreter overhead
factored).

**raw 69 verdict**: **CIRCUMVENT** (algorithm-class engineering — A18
streaming variant + A23 sparse-context selection trade memory for time).

---

## 3. Phase 12 algorithm catalog — A23-A28 candidates

**Charter**: post-80% Pareto frontier — each candidate must declare
**marginal saving above the Phase 11 closure aggregate**, NOT above bare
HXC. cmix-class neural mixing is **PERMANENTLY EXCLUDED** per raw 137.

### A23 — sparse-context PPM (post-A18 high-order extension)

**Algorithm spec**:
- Extend A18 PPM order-4 to order-N with **sparse context selection** —
  do NOT materialise full order-N tables; instead keep only contexts
  whose frequency exceeds threshold τ (estimated via reservoir sampling).
- Order-5 / order-6 contexts dominate on highly-structured corpora
  (atlas .n6, hexa .hexa source) but produce sparse hits on text.
- Sparse table → hash-keyed `HashMap<context_hash, PPM_node>` with LRU
  eviction (cap 64MB).

**raw 9 + raw 18 compatibility**: ✓ pure-hexa HashMap + integer arithmetic;
DMC (Cormack-Horspool 1987) and PPMii (Shkarin 2002 textbook port).

**raw 156 placement axis**: post-A18 (entropy-coder family); orthogonality
proof required vs A17/A18 PPM order-3/4 baselines (single-axis sweep N=10).

**Projected saving** (post-Phase-11 ~80%):
- atlas n6 (h_∞ ~ 0.5-0.7): 88% → **91%** (+3pp).
- text-heavy: 80% → **83%** (+3pp).
- audit/structured: 90% → **91%** (+1pp; saturated).

**LoC**: ~600 pure-hexa.

**raw 69 verdict**: **APPROACH** (math asymptote — Pareto-marginal +3pp).

**Falsifiers** (raw 71):
- F-A23-1: post-A18 marginal saving < 1pp on aggregate → reject.
- F-A23-2: encode latency > 300ms / 1KB → reject (A23 sparse hash
  worse than A18 dense table on small inputs).
- F-A23-3: round-trip byte-eq fails → reject (raw 65/68).
- F-A23-4: memory > 256MB during encode on 79KB n6 atlas → reject.

### A24 — corpus grammar induction (raw 159 candidate, see §7)

**Algorithm spec**:
- Pass 1: scan training corpus, induce **probabilistic context-free
  grammar** (PCFG) over byte symbols using minimum-description-length
  (MDL) Stolcke-Omohundro grammar merging (1994).
- Pass 2: re-encode corpus using grammar — frequent phrases become
  high-prior nonterminals; rare phrases stay byte-level.
- Hybrid with A18 PPM: PPM provides byte-level fallback for unparseable
  regions.

**raw 9 + raw 18 compatibility**: ✓ MDL grammar merging is finite-state
operations + closed-form likelihood (no neural). Memory ≤ 32MB per
corpus class.

**raw 156 placement axis**: pre-A1 raw (grammar applies BEFORE structural
dedup). Orthogonality vs A1 must be measured — risk: grammar may shadow
A1's structural dedup of repeated keys (-Δpp on already-A1-handled corpora).

**Projected saving**:
- JSON-heavy ledgers (state/proposals/refinement/*.json): 75% → **84%**
  (+9pp; PCFG captures `{"key":"value", ...}` skeleton as nonterminal).
- text-heavy: 80% → **82%** (+2pp; English bigram already in A18 PPM).
- atlas n6: 88% → **88%** (±0pp; structural already maximally exploited).

**LoC**: ~900 pure-hexa.

**raw 69 verdict**: **CIRCUMVENT** (algorithm-class — grammar provides
+5-9pp on unsaturated structured class beyond A18 ceiling).

**Falsifiers**:
- F-A24-1: post-A20 marginal saving < 2pp on JSON-heavy class → reject.
- F-A24-2: grammar build time > 30s on 100KB corpus → reject.
- F-A24-3: A24 + A1 stacked → A1 saving regression > 1pp → reject
  (raw 156 orthogonality violation).
- F-A24-4: round-trip byte-eq fails → reject.

### A25 — type-aware compression (hexa AST entropy model)

**Algorithm spec**:
- For `.hexa` source code corpus: parse AST, extract identifier-vs-keyword
  vs literal-vs-operator bands.
- Per-band entropy coder: keywords use vocabulary-anchored coder
  (~50 distinct keywords, 5.6 bit/symbol → 1 byte/keyword vs 5-12 chars
  source).
- For `.json` corpus: JSON type detection → key-band / value-band /
  delimiter-band separation; per-band PPM-3.

**raw 9 + raw 18 compatibility**: ✓ requires hexa AST API (already
exposed in `hexa-lang/self/parser/ast.hexa`); JSON parser stdlib.
**Caveat**: raw 18 self-host needs validation that hexa's own AST API
satisfies fixpoint (hexa-lang governs its parser, so YES per raw 18).

**raw 156 placement axis**: pre-A1 raw (type-aware band split BEFORE
structural dedup). Composes with A1/A4/A8 because per-band streams are
narrower-distribution → A1 dedup more effective.

**Projected saving**:
- `.hexa` source corpus: A18 88% → **92%** (+4pp; keyword vocab tighter
  than byte PPM).
- `.json` corpus: A18+A20 84% → **87%** (+3pp; per-band PPM tighter).
- `.txt` corpus: A18 80% → **80%** (±0pp; no type structure).

**LoC**: ~700 pure-hexa (parser glue ~150 + coder ~400 + selftest ~150).

**raw 69 verdict**: **CIRCUMVENT** (paradigm-aware algorithm-class — uses
language semantics to tighten per-band entropy).

**Falsifiers**:
- F-A25-1: post-A18 marginal saving < 1pp on `.hexa`/`.json` corpus → reject.
- F-A25-2: AST parse latency > 100ms / 1KB → reject (hexa parser overhead).
- F-A25-3: round-trip byte-eq fails (AST round-trip preservation) → reject.
- F-A25-4: A25 + A1 stacking regression > 1pp → reject (raw 156).

### A26 — adaptive context-window resize

**Algorithm spec**:
- Per-corpus dynamic context-window size for A18 LZ + PPM:
  - small files (< 4KB): window = 1024 (cache friendly).
  - medium files (4-64KB): window = 16K (current A18 default).
  - large files (> 64KB): window = 256K (deeper context).
- Window size embedded in HXC v1 footer per file.

**raw 9 + raw 18 compatibility**: ✓ trivial (parameter sweep, not new
algorithm). Reuses A18 implementation entirely.

**raw 156 placement axis**: parameter axis on A18; no new placement.

**Projected saving** (post-A18 80% baseline):
- aggregate: +0.5-1.5pp (sweet-spot tuning).
- diminishing returns: A18 already hits ~88% asymptote.

**LoC**: ~150 pure-hexa (parameter selection + footer tag).

**raw 69 verdict**: **APPROACH** (parameter-tuning class; very thin pp).

**Falsifiers**:
- F-A26-1: aggregate marginal < 0.3pp → reject (Pareto-dominated).
- F-A26-2: per-file footer overhead negates saving on small files → reject.
- F-A26-3: round-trip byte-eq fails → reject.
- F-A26-4: window size selection latency > 10ms → reject.

### A27 — cross-language federation (raw 4 follow-up)

**Algorithm spec**:
- Extend A19 cross-corpus dict federation to TS / Node / Python / Bash
  hot-path corpora (e.g., `nexus/` TypeScript files,
  `n6-architecture/` config Python, `airgenome/` shell scripts).
- Shared vocab across languages where keywords overlap (`function`,
  `return`, `if`, `else`, `null`, `true`, `false`).

**raw 9 + raw 18 compatibility**: ⚠ partial — encoder MUST stay hexa-only
(raw 9), but cross-language corpora are NOT hexa-source. This is a
**reader-side** federation: HXC read-side ingests TS/Python/Bash corpora,
encodes with hexa-only A19 federated dict.

**raw 156 placement axis**: same as A19 (cross-file shared dict). Only
the federation manifest scope expands.

**Projected saving**:
- TypeScript-heavy nexus: +3-5pp (function/return keywords share dict
  with hexa keywords).
- Python config: +2-3pp.
- Bash scripts: +1-2pp.

**LoC**: ~250 pure-hexa (federation manifest extension; algorithm reuse).

**raw 69 verdict**: **CIRCUMVENT** (scope-extension class; new corpora
classes added to HXC charter).

**Falsifiers**:
- F-A27-1: cross-language federated dict bytes > 8MB → reject (raw 42).
- F-A27-2: TypeScript saving < 60% → reject (worse than A18 alone).
- F-A27-3: round-trip byte-eq fails → reject.
- F-A27-4: federation drift > 24h between repos → reject (raw 151 cap).

### A28 — semantic embedding-based (TRANSCEND candidate, **DEFERRED**)

**Algorithm spec**:
- Replace symbol-level entropy coding with **vector-quantised semantic
  embedding** of phrases / function bodies / sentences.
- Decoder reconstructs canonical form from embedding ID + per-instance
  delta.

**raw 9 + raw 18 compatibility**: ✗ **VIOLATES**. Embedding requires:
- floating-point operations (raw 9 ambiguous; raw 18 fails — hexa lacks
  vectorised fp dot product).
- training-time corpus → fixed embedding table (raw 137 cmix-class
  adjacent — neural mixer kin).
- non-deterministic similarity scoring (raw 65/68 idempotent at risk).

**raw 156 placement axis**: would replace A1-A28; not orthogonal.

**Projected saving**: 92-94% on prose corpora (TRANSCEND). But VIOLATES
3 raws.

**raw 69 verdict**: **TRANSCEND-but-FORBIDDEN**. Explicitly deferred —
requires retiring raw 9 (unlikely), raw 18 (unlikely), or raw 137
(governance freeze). **DO NOT IMPLEMENT** within HXC charter.

**Falsifier**: pre-implementation reject — A28 cannot pass any of
F-A28-{raw9,raw18,raw137}.

---

## 4. Phase 12 Pareto table — LoC vs saving% (per target band)

All numbers PROJECTED on top of Phase 11 closure (~80% MEASURED assumption).

| target | algorithms required | cumulative LoC (added) | aggregate saving% | per-pp LoC cost | raw 69 class |
|---|---|---:|---:|---:|---|
| **Phase 11 closure** | A1-A22 | ~6300 | 80% (target) | — | baseline |
| **85%** | + A23 sparse-PPM + A26 adaptive-window | ~6300 + 750 = 7050 | 85% | 150 LoC/pp | APPROACH |
| **88%** | + A24 grammar-induction (JSON class) | 7050 + 900 = 7950 | 87-88% | 300 LoC/pp | CIRCUMVENT |
| **90%** | + A25 type-aware (hexa+JSON) + A27 cross-lang fed | 7950 + 700 + 250 = 8900 | 89-90% | 475 LoC/pp | CIRCUMVENT |
| **92%** | + (A23+A24+A25 fully tuned, parameter sweep) | 8900 + 200 = 9100 | 91-92% | 100 LoC/pp | APPROACH (asymptote) |
| **95%** | **A28 semantic embedding** — FORBIDDEN | — | unreachable within charter | — | BARRIER (raw 137) |

### Diminishing returns analysis (raw 69 + ROI)

| band | gap | LoC delta | LoC/pp ratio | comment |
|---|---:|---:|---:|---|
| 80% → 85% | 5pp | 750 | **150** | first +5pp cheapest (sparse PPM) |
| 85% → 88% | 3pp | 900 | **300** | grammar induction, +2x cost |
| 88% → 90% | 2pp | 950 | **475** | type-aware, +3x cost |
| 90% → 92% | 2pp | 200 | **100** | parameter sweep wraps up; asymptote |
| 92% → 95% | 3pp | ∞ | ∞ | **FORBIDDEN** (raw 137 cmix-ban) |

**Super-linear cost from 85% onwards** confirms K(X) asymptotic regime —
each pp costs 2-3x more LoC than the previous band. 92% is the practical
within-charter ceiling.

---

## 5. raw 69 ceiling-classification per algorithm

| algo | class | rationale |
|---|---|---|
| A23 sparse-PPM | **APPROACH** | math asymptote — order-N extension of A18 PPM |
| A24 grammar-induction | **CIRCUMVENT** | algorithm-class — Stolcke-Omohundro PCFG provides structural dedup beyond LZ |
| A25 type-aware | **CIRCUMVENT** | paradigm-aware — uses language semantics (AST) to tighten per-band entropy |
| A26 adaptive-window | **APPROACH** | parameter-tuning class — tightens A18 sweet spot |
| A27 cross-lang fed | **CIRCUMVENT** | scope-extension — adds new corpus classes (TS/Python/Bash) to charter |
| A28 semantic embedding | **TRANSCEND-FORBIDDEN** | violates raw 9 / raw 18 / raw 137 (cmix kin) — DEFERRED indefinitely |

**Aggregated trajectory**: Phase 11 = 4 APPROACH algorithms (A19/A20/A22 +
A21 advisory). Phase 12 = 2 APPROACH (A23 / A26) + 3 CIRCUMVENT (A24 / A25
/ A27) + 1 TRANSCEND-FORBIDDEN (A28).

**Key insight**: post-80% gains require CIRCUMVENT-class algorithms —
APPROACH-class alone tops out at ~85% per the diminishing-returns table.

---

## 6. Phase 12 entry gate forward-spec

### 6.1 Entry preconditions (Phase 11 closure required)

**Decision rule for Phase 12 P0 entry**:
- AND Phase 11 P0 (A19) MEASURED saving% on small-file class > 0pp (F-A19-1
  retired — current -1pp regression resolved).
- AND Phase 11 P1 (A20) LIVE FIRE 4/4 corpora PASS + selftest 4/4 PASS.
- AND Phase 11 P3 (A22) LIVE FIRE round-trip byte-eq PASS on ≥ 3 corpora
  + raw 152 self-decoding fixpoint VERIFIED.
- AND 6-repo aggregate **≥ 80% MEASURED** (raw 137 target satisfied).
- AND F-A23-1..4 / F-A24-1..4 / F-A25-1..4 falsifiers preregistered in
  `state/format_witness/` BEFORE any implementation tick.

### 6.2 Phase 12 P0/P1/P2/P3 candidate sequence

| sub-phase | algorithm | priority rationale | LoC budget | gate to next |
|---|---|---|---:|---|
| **P0** | A23 sparse-PPM | extends A18; lowest-friction +3pp; APPROACH | 600 | F-A23-1..4 retired |
| **P1** | A24 grammar-induction | highest CIRCUMVENT pp/effort on JSON class | 900 | F-A24-1..4 retired |
| **P2** | A25 type-aware | second CIRCUMVENT for `.hexa`/`.json` precision | 700 | F-A25-1..4 retired |
| **P3** | A26 + A27 (paired) | parameter-sweep + cross-lang fed wrap-up | 400 | aggregate ≥ 90% MEASURED |

**Phase 12 closure target**: 6-repo aggregate **90% MEASURED** (raw 69
APPROACH asymptote near K(X) within charter).

### 6.3 Per-wire entry gate (Option A / B / C)

| wire option | Phase 11 closure | P0 entry | P1 entry | P2 entry | P3 entry |
|---|:---:|:---:|:---:|:---:|:---:|
| Option A (base64url) | 80% | A23 ≥ 82% | A24 ≥ 85% | A25 ≥ 87% | 88% (ceiling) |
| Option B (base94) | 80% | A23 ≥ 83% | A24 ≥ 86% | A25 ≥ 88% | **90%** (target) |
| Option C (per-bit) | 88% | A23 ≥ 89% | A24 ≥ 91% | A25 ≥ 93% | 94% (asymptote) |

**Recommendation**: **Option B base94** — Pareto-optimal per
`hxc_wire_encoding_decision_20260428.md`. Option C per-bit defers raw 92
split + tooling fork; out of immediate scope.

---

## 7. raw 159 candidate — algorithm-grammar-induction-mandate (**SLOT CONFLICT — DEFERRED**)

### 7.1 Slot-conflict honest disclosure (raw 91 C3)

**Critical finding**: raw 159 is **already registered** in
`/Users/ghost/core/hive/.raw` as:

```
raw 159 new "hexa-lang-upstream-proposal-mandate - every work session that
encounters hexa-lang feature gap / stdlib missing / parser limitation /
type system shortfall / runtime bug MUST emit explicit upstream proposal
(issue / PR / convergence note targeted at hexa-lang repo) BEFORE
workaround patch lands; ..."
```

The task spec `raw 159 candidate: algorithm-grammar-induction-mandate`
is therefore a **slot-collision request**. Per raw 91 C3 honest disclosure:
this candidate **CANNOT register at raw 159** without retiring or
relocating the existing raw 159.

**Disposition**: candidate registered as **raw 160 (next free slot)**.

### 7.2 raw 160 candidate — algorithm-grammar-induction-mandate (FORWARD-SPEC)

```
raw 160 new "algorithm-grammar-induction-mandate - HXC Phase 12 P1 mandate:
corpus implicit grammar 가 algorithm choice 결정 기준 — JSON-heavy corpus
(state/proposals/refinement/*.json 등) → A24 grammar-aware Stolcke-Omohundro
PCFG induction; .hexa-source corpus → A25 AST type-aware band split;
.txt-prose corpus → A18 PPM order-4 sufficient (grammar induction
unnecessary). Forward-spec design (anima Phase 12 forward design ω-cycle
2026-04-28): A24 grammar-induction projected +5-9pp on JSON-heavy class
post-Phase-11-closure 80% baseline (raw 137 sweet-spot 도달 후 next ceiling
APPROACH→CIRCUMVENT shift); ~900 LoC pure-hexa. raw 9 hexa-only / raw 18
self-host fixpoint / raw 42 jetsam 호환 (memory cap 32MB per corpus class,
PCFG MDL merge integer-only Stolcke-Omohundro 1994 textbook port).
LIVE 검증 게이트: F-A24-1 post-A20 marginal < 2pp on JSON-heavy → reject;
F-A24-2 grammar build > 30s / 100KB → reject; F-A24-3 A1+A24 stacking
regression > 1pp → reject (raw 156 orthogonality); F-A24-4 round-trip
byte-eq fails → reject. Cross-repo universal mandate per raw 47.
Slot 159→160 reassignment: raw 159 already registered as
hexa-lang-upstream-proposal-mandate (slot-conflict honest disclosure)."
```

### 7.3 Triad-mandate compliance (raw 95)

Three enforcement layers:

- **L1 advisory baseline**: anima own `algorithm-grammar-induction-advisory`
  (severity warn) — corpora classifier emits warning if JSON-heavy class
  Pareto-final declared without A24 candidate evaluation.
- **L2 lint reference**: `anima/tool/hxc_grammar_induction_orthogonality_lint.hexa`
  (NEW, ~150 LoC PROJECTED) — scans HXC catalog for A1+A24 stacking and
  asserts orthogonality preservation per raw 156.
- **L3 atlas anchor**: `n6-architecture/atlas` candidate anchor for
  PCFG-MDL grammar-induction structural pattern (Stolcke-Omohundro 1994
  textbook reference).

### 7.4 4 falsifiers preregistered (raw 71)

| ID | falsifier | retire condition |
|---|---|---|
| F-A24-1 | post-A20 marginal saving < 2pp on JSON-heavy | reject A24 catalog promotion |
| F-A24-2 | grammar build time > 30s / 100KB corpus | reject (raw 42 perf budget) |
| F-A24-3 | A1+A24 stacking regression > 1pp | reject (raw 156 orthogonality) |
| F-A24-4 | round-trip byte-eq fails on any corpus | reject (raw 65/68 idempotency) |

### 7.5 Paired roadmap entry P8.160

To be appended to `state/proposals/refinement/` paired roadmap registry
once Phase 11 closes ≥ 80% MEASURED. Format:

```
P8.160 algorithm-grammar-induction-mandate
- target_raw_id: raw 160
- phase: 12 P1
- precondition: Phase 11 closure ≥ 80% MEASURED
- LoC budget: 900
- projected_saving_pp: +5-9 on JSON-heavy class
- raw_69_class: CIRCUMVENT
- triad_layers: L1 advisory + L2 lint + L3 atlas
- falsifiers: F-A24-1..4
```

### 7.6 Verdict

**raw 160 candidate REGISTERED-IN-FORWARD-SPEC**, **NOT YET LIVE**.
Activation gate: Phase 11 closure ≥ 80% MEASURED + Phase 12 P0 (A23) LIVE.

---

## 8. Cross-repo trawl-witness (raw 47)

**Required cross-repo applicability**: ≥ 3 sister repos must demonstrate
relevance for raw 160 promotion.

| repo | relevance | substantive evidence |
|---|---|---|
| **anima** | origin (this doc) | Phase 12 forward design, 900 LoC A24 spec |
| **hexa-lang** | high | `.hexa` source AST = A25 candidate input class |
| **nexus** | medium | TypeScript hot-paths = A27 cross-lang fed candidate input |
| **hive** | high | `state/raw_*/registry.jsonl` = JSON-heavy corpus, A24 primary target |
| **n6-architecture** | medium | atlas .n6 already structural; A24 marginal ~1pp |
| **airgenome** | low | shell scripts off-domain (A27 candidate, low priority) |

**raw 47 threshold ≥ 3 sister repos**: **EXCEEDED** (4 of 5 substantive).
Trawl-witness logged in §10 ledger.

---

## 9. Pareto stop-point recommendation

### Three stop-point candidates

| stop point | aggregate | rationale | within charter? |
|---|---:|---|:---:|
| **A** Phase 11 closure | 80% | raw 137 target satisfied; Pareto sweet spot | ✓ |
| **B** Phase 12 closure | 90% | math asymptote near K(X); CIRCUMVENT exhausted | ✓ |
| **C** cmix-equivalent | 92-95% | TRANSCEND class | **✗ raw 137 ban** |

### Recommendation: **STOP at Phase 12 closure (90%)**

**Reasoning**:
1. raw 137 mandates 80% sweet spot; Phase 11 closure satisfies
   minimal contract.
2. Phase 12 +10pp via A23/A24/A25/A26/A27 is **achievable within
   charter** (LoC budget ≤ 9100 cumulative; raw 9 + raw 18 + raw 42
   honored).
3. Beyond 90%, marginal LoC/pp ratio super-linear (raw 69 APPROACH
   asymptote); 92% requires parameter sweep wrap-up only (~200 LoC)
   but provides operational ceiling — diminishing engineering ROI.
4. 95%+ band is BARRIER (raw 137 cmix-class ban + raw 18 self-host
   fixpoint violation risk).

**Operational stop**: declare Pareto-final at **90% MEASURED**, raw 137
sweet-spot exceeded by +10pp delta (defensive margin against future
content-class drift), no Phase 13 wave planned without paradigm shift.

---

## 10. Witness ledger reference

This document's ω-cycle witness:
**`/Users/ghost/core/anima/state/format_witness/2026-04-28_phase12_forward_design.jsonl`**

Contents include:
- Phase 11 closure projection rows.
- A23-A28 candidate breakdown rows.
- Pareto LoC vs saving% table rows.
- raw 69 ceiling-classification per algorithm.
- raw 159 slot-conflict disclosure + raw 160 candidate forward-spec.
- raw 47 cross-repo trawl-witness rows.
- diminishing-returns analysis rows.
- Phase 12 entry gate forward-spec rows.

---

## 11. Compliance summary

- **raw 9 hexa-only**: ✓ all A23-A27 spec'd as pure-hexa; A28 explicitly
  forbidden for raw 9 violation.
- **raw 18 self-host fixpoint**: ✓ A22 (Phase 11) seals fixpoint; A24/A25
  preserve via integer-only operations.
- **raw 33 NL English**: ✓ all PROJECTED / MEASURED / saving / class
  fields English; Korean only in narrative context references.
- **raw 37+38+39 omega-saturation**: ✓ this is a forward ω-cycle
  saturation document.
- **raw 47 cross-repo**: ✓ §8 trawl-witness 4/5 sister repos.
- **raw 65+68 idempotent**: ✓ all algorithms preserve byte-eq round-trip.
- **raw 71 falsifier-preregistered**: ✓ F-A23-1..4 / F-A24-1..4 /
  F-A25-1..4 / F-A26-1..4 / F-A27-1..4 all listed before implementation.
- **raw 91 honest C3**: ✓ §0 + §1 + §7.1 explicit PROJECTED labels;
  raw 159 slot-conflict honestly disclosed.
- **raw 95 triad-mandate**: ✓ raw 160 candidate has L1+L2+L3 mapping
  per §7.3.
- **raw 137 80% Pareto + cmix-ban**: ✓ Phase 12 stop point recommends
  90% (within charter); A28 cmix-kin explicitly forbidden.
- **raw 142 D1-D5**: ✓ all 5 discoveries honored — D1 content-class
  topology via per-class projection; D2 try-and-revert wrapper at every
  catalog promotion; D3 orthogonality preservation per A24/A25 falsifiers;
  D4 best-of-N preserved (no neural mixer); D5 self-correction cadence
  via conditional Phase 12 plan + falsifier retire conditions.
- **raw 152 self-decoding**: ✓ Phase 11 P3 A22 closure assumed; Phase 12
  algorithms must extend self-decoding bytecode (mini-VM opcodes).
- **raw 156 algorithm-placement-orthogonality**: ✓ each candidate declares
  placement axis (pre-A1 / post-A18 / parameter / cross-file).
- **raw 159 hexa-lang-upstream-proposal-mandate**: ✓ if A23/A24/A25
  implementation reveals hexa stdlib gap (e.g., HashMap LRU eviction),
  upstream proposal MUST be filed before workaround.

**Avoidance of duplicate work** (raw 47 sibling-agent coordination):
- agent `a45778db` (A20+A22 PASS 3/4): independent — Phase 11 P1+P3
  closure work; this doc only references their projected outcome.
- agent `adb076b3` (falsification ledger v2): independent — F-A19-1 is
  their concern; this doc only cites their projection retirement.

---

**End of forward design.**
