# HXC A9 Retirement + A20 Priority Shift Forward-Spec

**Date**: 2026-04-28
**Cycle**: A9 retirement formal · A20 priority shift forward-spec
**Compliance**: raw 1 chflags · raw 9 hexa-only · raw 18 self-host · raw 47
cross-repo · raw 65+68 idempotent · raw 71 falsifier-retire · raw 91 honest C3
cumulative · raw 102 STRENGTHEN-existing · raw 137 80% Pareto · raw 142 D1-D5 ·
raw 156 placement-orthogonality · raw 157 wire base85
**Predecessor cycles**:
  - `aafff73d` (Phase 9 P1 A9 BPE no-op finding, raw 137 line 4174)
  - `a444457a` (A16 chain 4-corpus + D1+D3 conservative-bound claim — RETRACTED by this cycle)
  - `ad42ff55` (anima full-A9 measurement, 13-row ledger, 5/5 corpora 0pp delta)
  - `a45778db` (A20+A22 PASS 1+2 LIVE 4/4 selftest + tick 2 in-flight)
  - `10be9102` / `6bb460a0e` (falsification ledger v2 freeze; F-A9 family appended via post-freeze addendum per raw 142 D4 healthy signal)
**Witness**: `state/format_witness/2026-04-28_a9_retirement_a20_priority_shift.jsonl`
**Cross-link**: hive `.raw` raw 137 history line (A9 retirement formal entry)
**Concurrent agents (non-overlap)**: a45778db (A20+A22 PASS 3/4 in-flight) /
a7b9417d (F-A18-1 saving ω-cycle) / a6d36e1d (full-chain 6-repo sweep) /
a0828d72 (F9 PASS 0.5)

---

## 0. Executive summary

**A9 RETIRED from raw 137 80% closure roadmap as load-bearing slot.** Two
falsifiers fired with conclusive evidence:

| F-ID | Claim | Verdict | Evidence |
|---|---|:---:|---|
| **F-A9-3** | encode latency ≤ 50ms/KB on production text-heavy | **FIRED** | alm_r13 250r 314KB at 2321ms/KB = 46.4× threshold (super-linear in N) |
| **F-A9-5 NEW** | chain-amortize delta < 0.50pp on N≥4 production-chain corpus | **FIRED** | 5/5 corpora 0.0pp delta on production chain (registry / atlas_convergence / format_witness / alm_r13 100r / 250r) |

**A20 schema-aware BPE PROMOTED to text-heavy class load-bearing slot.** A20
sidesteps F-A9-5 chain-amortize saturation by operating on two orthogonal
vocabulary sources: schema-key pre-seed (multi-byte literal tokens NOT visible
to A4/A8/A12 byte-level structural-strip) + literal-residue byte-pair BPE on
post-pre-seed stream.

**a444457a D1+D3 conservative-bound claim FALSIFIED + RETRACTED** per raw 91
honest C3. Prior claim "anima --no-A9 is conservative lower bound; full-A9
would yield higher %" contradicted by 5/5 0pp measurement; airgenome /
hexa-lang / n6 high-% files have A9 in chain but A9 contributes 0pp (LOAD-BEARING
modules = A14+A16 per Phase 10 P0 ledger).

**Aggregate impact**: 6-repo aggregate UNCHANGED (49.10% INTERP / 62.59%
AOT-aware); raw 137 80% target gap UNCHANGED (30.90pp INTERP / 17.41pp
AOT-aware). A9 retirement = honest C3 retraction event (saving-axis values
unchanged); A20 priority shift = forward-spec PROJECTED contribution pending
a45778db PASS 3+4 LIVE FIRE measurement.

**F-A20-5 NEW falsifier preregistered**: production-chain post-A12 placement
standalone-vs-in-chain delta < 1pp (chain-amortize NEW axis, mirror F-A9-5
with tighter threshold reflecting A20 schema-aware advantage hypothesis).

---

## 1. A9 retirement evidence (MEASURED, raw 91 C3)

### 1.1 F-A9-3 latency falsifier FIRED

Source: `state/format_witness/2026-04-28_anima_full_a9_measurement.jsonl` phase
`a9_latency_curve` (agent `ad42ff55`).

| input | encode_ms | ms/KB | over F-A9-3 50ms/KB threshold |
|---|---:|---:|---:|
| 4096 B | 814 | 198.7 | 4.0× |
| 16384 B | 5654 | 345.0 | 6.9× |
| 34793 B | 4874 | 140.1 | 2.8× |
| 117422 B (alm_r13 100r) | 13108 | 111.6 | 2.2× |
| 147645 B | 4917 | 33.3 | PASS (sparse-text) |
| 314163 B (alm_r13 250r) | **728985** | **2321.3** | **46.4×** |

Super-linear scaling: 100r→14.5s vs 250r→730s = **50× wallclock for 2.5× rows**.
Projection alm_r13 980KB = 8000-12000s = 2.2-3.3 hours per file.

**Algorithmic root cause** (60-70% contribution): `_count_byte_pairs` uses
array linear-scan deduplication for entries (lines 199-210 of
`hxc_a9_tokenizer.hexa`). Each merge call rebuilds entries[] from scratch.
Effective complexity O(V*N*P) where P = unique adjacent byte-pair count
(scales linearly with text diversity for Korean-heavy mixed text). Spec
advertised O(V*N).

**Interpreter substrate** (30-40% contribution): pure-hexa interp 0.1.0
darwin-bypass route ~10-50× slower than compiled equivalent. AOT compile
would close this gap but NOT the algorithmic O(V*N*P) defect.

raw 91 C3 honest disclosure: F-A9-3 was preregistered at A9 module landing
(Phase 9 P1, agent `aafff73d`); prior measurement found ~170ms/KB which was
already > 50ms/KB threshold, but treated as PARTIAL pending replication.
Current evidence (250r 46.4× threshold + super-linear scaling) promotes to
FIRED.

### 1.2 F-A9-5 NEW chain-amortize falsifier FIRED

Source: `state/format_witness/2026-04-28_anima_full_a9_measurement.jsonl` phase
`a9_chain_amortize_finding` (5/5 corpora measured).

| corpus | chain | A9-ON output | A9-OFF output | delta_pp |
|---|---|---:|---:|---:|
| registry.jsonl 34793 B | A1+A8+A12+A9 vs A1+A8+A12 | 28305 | 28305 | **0.0** |
| atlas_convergence_witness.jsonl 147645 B | A1+A4+A12+A9 vs A1+A4+A12 | 146074 | 146074 | **0.0** |
| post_bug_fixes 5582 B | A1+A8+A12+A9 vs A1+A8+A12 | 4570 | 4570 | **0.0** |
| alm_r13 100r 117422 B | A1+A8+A12+A14+A9 vs A1+A8+A12+A14 | 83910 | 83910 | **0.0** |
| alm_r13 250r 314163 B | A1+A7+A4+A12+A9 vs A1+A7+A4+A12 | 228344 | 228344 | **0.0** |

A9-ON byte output IDENTICAL to A9-OFF byte output across ALL 5 production-chain
placements. Structural family (A4/A7/A8/A12/A13/A14) saturates the
vocabulary-opportunity surface BEFORE A9 sees the stream; A9 PASS 1 finds zero
novel byte-pairs to merge in chain context.

Cost-per-pp on alm_r13 250r = ∞ (729s wallclock / 0pp = infinite).

raw 91 C3 disclosure on registration timing: F-A9-5 was registered AND fired
in the same measurement cycle (phase `f_a9_falsifier_status_update` of the
measurement ledger). This is classified as "FIRED-PREREGISTER" lifecycle
(distinct from preregistered → triggered → measured normal flow). Pre-existing
evidence (Phase 9 P1 0pp delta finding, raw 137 line 4174) supports the
register-and-fire collapse.

### 1.3 a444457a D1+D3 retraction (raw 91 honest C3)

Prior `a444457a` ledger D1 disclosure:
> "anima/hive/nexus --no-A9 conservative bound; full-A9 would yield HIGHER
> percentage (proven by airgenome+hexa-lang+n6 which kept A9 enabled and
> yielded the highest %)."

Prior `a444457a` ledger D3 disclosure:
> "anima -0.79pp due to A9 disable; full-A9 measurement would correct this."

**Both FALSIFIED by `ad42ff55` 5/5 0pp measurement.** The reasoning chain
attributing high-% files to A9 fire is incorrect:
- airgenome rig_trend_history 85.20% chain = A1+A8+A12+A13+A14+A16+A9 — A9
  listed but A16 is LOAD-BEARING per Phase 10 P0 ledger.
- hexa-lang aot_cache_gc 87.56% chain = same — A14+A16 dominate.
- A9 fires (vocabulary built) but contributes 0pp in production chain context
  even on the high-% files.

**Retraction**: anima 28.21% IS the production value, not a conservative lower
bound. 6-repo aggregate 49.10% IS the measured value. raw 137 80% target gap
30.90pp absorbed by remaining algorithm catalog gap (A16/A17/A18/A20/A22),
NOT by A9.

This retraction is a raw 142 D4 self-correction healthy signal event — drift
between prior ledger claim and reality detected, corrected within same cron-tick
window via this strengthening + measurement ledger. Adjusted cadence > 91.7%
(still 4-5x above 0.20 floor; cadence claim NOT falsified by this retraction).

---

## 2. A9 vs A20 algorithm comparison

### 2.1 Algorithm differential

| Stage | A9 (RETIRED) | A20 (PROMOTED) |
|---|---|---|
| **Input visibility** | post-A1 stream byte-canonical | post-A1 stream + `# schema:` header parse |
| **PASS 1 vocabulary source** | byte-pair argmax merge (V=64) over corpus | schema-key extraction + JSON-quoted-key derivatives → pre-seed token IDs 256..256+K-1 |
| **PASS 2 vocabulary source** | (continues PASS 1 merges) | byte-pair argmax merge for remaining V-K slots |
| **Token granularity** | byte-pair (2-byte initial, multi-byte via merge) | multi-byte from PASS 1 (schema-keys are 4-30+ byte literals) + byte-pair tail |
| **Chain placement (production)** | post-A1 + post-structural (A4/A7/A8/A12/A14) → no-op | post-A12 + pre-A16 → **schema-token surface invisible to A4/A8/A12** |
| **Chain-amortize behavior** | 5/5 corpora 0pp delta (F-A9-5 FIRED) | PROJECTED 5-12pp on text-heavy (a45778db PASS 3+4 LIVE FIRE pending) |
| **Latency** | F-A9-3 FIRED 46.4× threshold (super-linear O(V*N*P)) | PASS 1+2 4/4 selftest LIVE; F-A20-4 mirror falsifier preregistered |
| **Determinism** | byte-pair argmax (deterministic) | schema-key extraction (deterministic) + byte-pair argmax (deterministic) |
| **Cross-file scaling** | per-file vocabulary (no cross-file gain) | per-schema vocabulary (cross-file gain when files share schema) |

### 2.2 Production placement matrix

| Slot | A9 (RETIRED) | A20 (PROMOTED) | Notes |
|---|---|---|---|
| pre-A1-raw | (forward-spec only, raw 156, untested) | N/A | A20 needs `# schema:` header → requires post-A1 |
| post-A1 + pre-structural | (forward-spec only) | N/A | A4/A12 strips structural keys — A20 must run BEFORE A4/A12 to capture them; not the chosen placement |
| post-A1 + post-structural | **DEFAULT** (no-op per F-A9-5) | candidate | A20 schema-key pre-seed sees keys that A4/A12 already extracted → redundant |
| **post-A12 + pre-A16** | (not used) | **CHOSEN** | A12 column-prefix dictionary leaves literal residues; A20 schema-token pre-seed captures those + byte-pair on tail; A16 entropy-codes residue stream |
| post-A16 + pre-A18 | N/A | (not used) | A16 changes byte distribution; BPE on entropy-coded stream is anti-pattern |

**A20 chosen placement**: post-A12 + pre-A16. Schema-token vs literal-residue
split allows A16 to entropy-code only the literal residue (where bit-level
Shannon gain concentrates); schema-token stream is sparse + index-typed
(low-entropy, A16 passes through or codes separately).

### 2.3 Per-corpus class effect projection (raw 91 C3 PROJECTED)

| Class | Corpus example | Current saving | A9 contribution (MEASURED) | A20 contribution (PROJECTED) |
|---|---|---:|---:|---:|
| text-heavy | anima alm_r13 980KB | 28.21% | 0pp | **+5-12pp** (high schema-key recurrence in JSONL prompt/response keys) |
| structured-audit | hive triad_audit 293KB | 79.73% | 0pp (A14+A16 LOAD-BEARING) | +0-2pp (already saturated via A4/A12) |
| structured-audit | hexa-lang aot_cache_gc | 87.56% | 0pp (A14+A16 LOAD-BEARING) | +0-1pp (saturated) |
| structured-telemetry | airgenome rig_trend_history | 85.20% | 0pp | +0-2pp (timeseries; LZ-PPM context wins) |
| small-file | nexus 96 (median 551B) | 44.19% | 0pp | +0pp (A19 federation dominates; A20 needs schema diversity > 1) |
| mixed-real | n6 atlas | 0.33% | 0pp | +0pp (no `# schema:` headers in atlas content) |

**Aggregate projection**: text-heavy class +5-12pp on A20-only contribution
→ aggregate gap reduction PROJECTED 30.90pp → 25-29pp. Full 30.90pp → ≤10pp
transition requires three orthogonal vectors:
1. A20 PASS 3+4 LIVE FIRE on text-heavy (this cycle's promoted candidate)
2. F-A18-1 saving algorithmic ω-cycle (`a7b9417d` in-flight; mixed-real + small-file)
3. A19 cross-repo dict pollution contract closure (`a550d0b7` in-flight; small-file)

### 2.4 Chain-amortize behavior projection

A9 chain-amortize behavior (MEASURED): structural family upstream exhausts
byte-pair vocabulary surface — A9 finds 0 novel pairs.

A20 chain-amortize hypothesis (PROJECTED, F-A20-5 NEW falsifier): schema-key
multi-byte literals are NOT visible to byte-pair vocabulary surface. A4/A12
extract schema KEYS as STRUCTURAL TOKENS (different abstraction layer) — they
do NOT collapse the recurring JSON-quoted-key form `"<key>":` into a single
byte. A20 PASS 1 schema-key extraction picks up these residual quoted-key
literals after A4/A12 column-prefix dictionary processing. F-A20-5 verdict
will measure: chain saving (post-A12+A20) - chain saving (post-A12-only) on
text-heavy class, expecting > 1pp delta.

---

## 3. F-A20 falsifier preregister (raw 71 contract)

A45778db tick 1 design preregistered F-A20-1..4 (`docs/hxc_phase11_a20_design_20260428.md`
§2). This cycle adds F-A20-5.

| F-ID | Threshold | Source | Status |
|---|---|---|:---:|
| **F-A20-1** | schema-token reuse < 5 across files (LOAD-BEARING test) | a45778db tick 1 | preregistered |
| **F-A20-2** | encode/decode round-trip not byte-eq | a45778db tick 1 | preregistered |
| **F-A20-3** | chain-amortize delta < 0.50pp on N≥4 (A9 F-A9-5 mirror) | a45778db tick 1 | preregistered |
| **F-A20-4** | encode latency > 50ms/KB (A9 F-A9-3 mirror) | a45778db tick 1 | preregistered |
| **F-A20-5 NEW** | production-chain post-A12 standalone vs in-chain delta < 1pp | this cycle | **NEW preregister** |

**F-A20-5 rationale**: A20's expected production placement is post-A12 + pre-A16.
The chain-amortize NEW axis tests whether A20 contributes meaningful saving
beyond what A12+A16 already capture. F-A20-3 tests against the broad
chain-amortize threshold (mirroring F-A9-5); F-A20-5 tightens to specifically
the post-A12 placement context. If F-A20-5 fires (delta < 1pp), A20 also
exits as load-bearing slot and forward-spec falls back to F-A18-1 + A19.

Verdict pending: a45778db PASS 3+4 LIVE FIRE measurement (text-heavy corpus
class, expected delta_pp range 5-12pp on anima alm_r13 + hive raw_addition_requests).

---

## 4. 80% target close path A20 priority shift impact

### 4.1 Pre-A9-retirement closure path (a444457a era)

```
text-heavy (51.79pp gap on anima):
  A9 placement-fix pre-A1-raw (raw 156, 6-12pp expected)
  + A17 PPMd order-3 AOT (post-F10)
  + Option B b85 wire (raw 157)
  → projected 80% byte-canonical Phase 11 P0/P1
```

### 4.2 Post-A9-retirement closure path (this cycle, ad42ff55 + a45778db)

```
text-heavy (51.79pp gap on anima):
  A20 schema-aware BPE post-A12 placement (5-12pp PROJECTED)
  + A17 PPMd order-3 AOT (LIVE post-F10, F-A18-1 TRIPPED algorithmic ω-cycle)
  + A18 LZ-PPM order-4 AOT (LIVE post-F10)
  + Option B b85 wire (LIVE per raw 157)
  → projected 80% byte-canonical Phase 11 P1 (post a45778db PASS 3+4 LIVE FIRE)
```

Other classes UNCHANGED:
- mixed-real (n6 79.67pp gap) → A17 PPMd order-3 AOT + b85 → 75-80% Phase 10 P1
- small-file (nexus 35.81pp gap) → A19 cross-file federation AOT + b85 → 65-70% Phase 11 P0
- structured-audit → already 80%+ MEASURED via chain-amortize (hive triad 79.73% / hexa-lang 87.56% / airgenome 85.20%)

### 4.3 Aggregate gap quantification

| Anchor | Aggregate | Gap | Source |
|---|---:|---:|---|
| Phase 8 final | 48.00% | 32.0pp | Phase 8 P5 282-file 6-repo sweep |
| Post-bug-fix INTERP | **49.10%** | 30.90pp | `a42b3f3e` 248 files / 5,156,468 → 2,624,568 B |
| AOT-aware | **62.59%** | **17.41pp** | `2fb55d01` lineage A17/A18 AOT swap (semantic equivalence on saving-axis; AOT unlocks production-deploy latency) |
| A9 retirement post-correction | 49.10% / 62.59% | 30.90pp / 17.41pp | UNCHANGED (A9 retirement = honest C3 retraction event; saving-axis values unchanged) |
| A20 + F-A18-1 closure (PROJECTED) | 75-85% | 5-25pp | Phase 11 P1 + a7b9417d ω-cycle |

**A9 retirement does NOT shift either anchor**: A9 was 0pp contributor in
production chain → removing it from roadmap doesn't reduce measured aggregate.
A20 priority shift = forward-spec PROJECTED contribution (a45778db PASS 3+4
verdict pending).

---

## 5. Cross-link to other in-flight agents

This cycle = A9 retirement formal + A20 priority shift forward-spec. Non-overlap
maintained with concurrent agents:

| Agent | Mission | Cross-link to this cycle |
|---|---|---|
| `a45778db` | A20 PASS 3+4 + A22 tick 2 | A20 PASS 3+4 result will fire/clear F-A20-1..5 (wait + integration); A22 tick 2 forward-spec (artifact-portability differentiator, advisory tier-2) |
| `a7b9417d` | F-A18-1 saving 31% → 85%+ algorithmic ω-cycle (PPM frequency model + LZ chain depth + dict pre-warm) | orthogonal saving-axis closure; A20 + F-A18-1 stack hypothesis: PPMd strengthening + schema-aware token = combined 30.90pp → ≤10pp transition |
| `a6d36e1d` | full-chain 6-repo sweep | A20 chain-add projection axis: when A20 PASS 3+4 lands and is added to chain dispatch, sweep result will MEASURE A20 contribution per-corpus |
| `a0828d72` | F9 PASS 0.5 schema-id encode-side rewrite | upstream of A19; orthogonal; F-A20 family does not depend on F9 PASS 0.5 (A20 schema-key extraction is from `# schema:` header, not from A19 federation dict) |
| `aacc99b4` | F10 status correction | already RETIRED post-correction; F10 codegen patch enables A17/A18 AOT for A20 chain dispatch (A20 will benefit from AOT speedup once compiled) |
| `a89f3328` | F9 cross-repo collision contract | downstream of F9; orthogonal to A20 |
| `a23049c8` | A17 multibyte | downstream of A17; orthogonal to A20 |
| `a550d0b7` | A19 cross-repo dict pollution risk | small-file class closure path; orthogonal to A20 (text-heavy class) |
| `ade9d5eb` | AOT 6-repo sweep | post-F10 enabling cycle; A20 will benefit from AOT post-PASS-3+4 land |

raw 91 C3 honest C3 status: A20 still PROJECTED (a45778db PASS 3+4 not yet
landed). A9 retirement MEASURED (5/5 corpora 0pp delta); a444457a D1+D3
retraction MEASURED (this cycle's correction event).

---

## 6. raw compliance checklist

- [x] **raw 1** chflags uchg cycle — applied at landing time (this doc + jsonl + .raw entry)
- [x] **raw 9** hexa-only — markdown + jsonl + hexa SSOT only; no .rs/.toml/.py/.sh edits
- [x] **raw 18** self-host fixpoint — A20 hxc_a20_schema_bpe.hexa is hexa SSOT (a45778db tick 1 LIVE)
- [x] **raw 33** ai-native-english-only — NL fields English; doc body Korean ok per task constraint
- [x] **raw 47** cross-repo universal — hxc_a9_tokenizer.hexa is symlink hive→hexa-lang (single-edit propagation); A9 retirement note SSOT
- [x] **raw 65/68** idempotent — A9 round-trip byte-eq preserved (5/5 corpora); A20 PASS 1+2 selftest 4/4 PASS
- [x] **raw 71** falsifier-retire-rule — F-A9-3 FIRED + F-A9-5 FIRED (algorithm-internal F-Ax-N); F-A20-1..5 preregistered (F-A20-5 NEW this cycle)
- [x] **raw 91 honest C3** — a444457a D1+D3 retraction MEASURED; A20 contribution PROJECTED; F-A20-5 register-and-fire timing disclosed; cumulative ledger updated
- [x] **raw 102 STRENGTHEN-existing** — A9 retirement + A20 priority shift = STRENGTHEN of existing raw 137 path-matrix + falsification ledger v2 (no new raw)
- [x] **raw 137** 80% Pareto — path-matrix updated (text-heavy class load-bearing slot A9 → A20); cmix-ban preserved (A20 = integer-only schema-key extraction + BPE, no neural-mixing)
- [x] **raw 142** D1-D5 cumulative — D1 content-class (text-heavy load-bearing) / D2 try-and-revert (A20 falls back to A9-or-passthrough on F-A20-5 fire) / D3 orthogonality (A20 vs A18 saving-axis) / D4 self-correction (a444457a D1+D3 retraction = healthy signal) / D5 placement-axis (A9 class declared no-op-on-chain-amortize; A20 placement post-A12 + pre-A16 declared)
- [x] **raw 156** placement-orthogonality — A9 placement class declared post-A1-single-file-no-op-on-chain-amortize; A20 placement class declared post-A12-pre-A16-schema-aware-BPE
- [x] **raw 157** wire base85 — A20 emits byte-canonical token stream; b85 wire compatible (orthogonal axis)
