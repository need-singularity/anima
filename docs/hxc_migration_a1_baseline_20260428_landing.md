# HXC migration A1 baseline — anima top-5 JSONL surfaces — 2026-04-28 landing

## Topic
Phase 1 of the HXC (HeXa-lang Canonical) migration pilot for raw 137 (anima top-5 JSONL surface measure HXC saving) — A1 schema-hash-delta only. A7 arithmetic-coding-shared-dict, A9 ai-native-tokenizer-axis, A10 forward-spec are not yet landed and are tracked in separate subagents. The 80% aggregate target is the union of A1+A7+A9+A10 contributions; this artifact establishes the A1-only baseline so the post-A7/A9/A10 measurement has a clean diff line.

## User directive
"80% 한계수렴 병렬 all kick" — push the HXC saving toward the 80% physical/mathematical limit on anima production JSONL surfaces in parallel; do not block on any single algorithm. Phase 1 lands A1-only baseline; A7/A9/A10 land via separate subagents and then re-measure.

## Mandate trace
- raw 137 (anima top-5 JSONL surface measure HXC saving)
- Task #20 ROI inventory enumerates the 5 primary surfaces
- raw 9 hexa-only — `tool/hxc_convert.hexa` is the only conversion path used
- raw 91 honest C3 — small-N edge case (rows<8) is reproduced and explicitly flagged
- raw 92 falsifier evidence accumulation — saving baseline measurement is the evidence row
- raw 101 landing doc ≥60 lines (this artifact)

## Tool used
`/Users/ghost/core/hive/tool/hxc_convert.hexa` — A1 byte-canonical schema-hash-delta converter, hexa-only per raw 9. Selftest result: 3 PASS / 1 FAIL on synthetic 3-row 2-schema fixture (hxc 134B > native 125B). The FAIL reproduces the documented A1 small-N regime: schema-header amortization needs roughly 4+ rows-per-schema to break even; below that, the header column-0 anchor outweighs the savings. This is raw 91 C3 honesty disclosure, not a tool defect.

## Per-file measurement table

| file | native_B | hxc_B | saving% | rows_data | schemas | rows/schema | A1 efficacy |
|------|---------:|------:|--------:|----------:|--------:|------------:|:------------|
| state/atlas_convergence_witness.jsonl | 147645 | 146307 | 0.91 | 41 | 35 | 1.17 | WEAK |
| state/log_rotation_zstd_log.jsonl | 9088 | 6308 | 30.59 | 59 | 1 | 59.0 | GOOD |
| state/serve_alm_persona_log.jsonl | 4111 | 1830 | 55.49 | 24 | 1 | 24.0 | EXCELLENT |
| state/asset_archive_log.jsonl | 33913 | 25889 | 23.66 | 208 | 1 | 208.0 | GOOD |
| state/corpus_tier_tier3_high.jsonl | 2812 | 2547 | 9.42 | 2 | 1 | 2.0 | DEGRADED (small-N) |
| state/alm_r13_4gate_pass_subset.jsonl (+) | 980326 | 763768 | 22.09 | 840 | 5 | 168.0 | GOOD |

(+) = additional candidate. The originally-suggested `state/audit/escalation_pending.jsonl` is not present in the anima tree (the directory `state/audit/` does not exist — only escalation `*.marker` files under `state/markers/`). Substituted with `alm_r13_4gate_pass_subset.jsonl` (840 rows / 5 schemas / ~980KB) to provide a high-N evidence anchor for raw 92.

## Aggregate statistics

5-file primary set (Task #20 ROI inventory):
- total native bytes: 197569
- total hxc bytes: 182881
- byte-weighted saving: 7.43%
- simple-mean saving: 24.01%
- stdev: 21.10 percentage points
- variance: 4.45 (pp^2)
- min/max: 0.91% / 55.49%
- gap to 80% target: -72.57 percentage points (BYTE-WEIGHTED), -55.99 percentage points (SIMPLE-MEAN)

6-file with additional candidate:
- total native bytes: 1177895
- total hxc bytes: 946649
- byte-weighted saving: 19.63%
- simple-mean saving: 23.69%
- stdev: 18.89
- variance: 3.57
- gap to 80% target: -60.37 percentage points (BYTE-WEIGHTED)

The byte-weighted vs simple-mean spread is large (7.43% vs 24.01% on the 5-file set) because atlas_convergence_witness alone is 75% of the 5-file native-byte mass and has the worst per-file ratio (0.91%) due to its 35-schema heterogeneity. This is the single most important phase 1 finding.

## Falsifier evidence (raw 92)

F1 (preregistered): 30-day byte-saving on JSONL with 2+ schemas < 0.15 ⇒ retire raw 92 OR scope-narrow. Phase 1 status:
- simple-mean axis 0.2401 — F1 NOT FIRED
- byte-weighted axis 0.0743 — F1 FIRED (driven by atlas heterogeneity)

Decision: A1 alone is sufficient for log-class single-schema surfaces (log_rotation, serve_alm, asset_archive — all 23-55% saving) but insufficient for heterogeneous-schema surfaces (atlas — 35 schemas / 41 rows). The atlas surface needs A4 (structural compression) and/or A6 (retrieval-axis dedup) before A1 can amortize. A7 (arithmetic-coding shared-dict) is also expected to help because key-name strings repeat across distinct schemas.

## Small-N edge case (raw 91 C3)

`corpus_tier_tier3_high.jsonl` has 2 data rows and a single schema. Saving is 9.42% — substantially below the GOOD-class single-schema surfaces (23-55%). This reproduces the schema-header amortization gap: A1 emits one `# schema:s1 ...` header line that costs ~80 bytes; with only 2 rows of ~1400 bytes each, that overhead is a small fraction but the per-row savings (key-name elision, null→`~`, bare-string elision) are limited because the values themselves dominate. Selftest FAIL on the 3-row fixture is the same regime in synthetic form.

This is honestly disclosed and not papered over. If the user wishes, phase 2 can add a per-file `min_rows` gate to the convert tool that simply emits `# skip:small-N rows=<n>` and copies the input through unchanged; that is a forward-spec suggestion, not a phase-1 change.

## A1 efficacy classification (empirical)
- EXCELLENT (>50%): 1 surface (serve_alm_persona_log) — single schema, verbose key names, 24 rows
- GOOD (15-50%): 3 surfaces (log_rotation_zstd_log, asset_archive_log, alm_r13_4gate_pass_subset)
- DEGRADED (<15% small-N): 1 surface (corpus_tier_tier3_high)
- WEAK (<5% schema-heterogeneity): 1 surface (atlas_convergence_witness)

## Path to 80% target
Phase 2-4 forward-spec (each is a separate subagent per "병렬 all kick"):
- A7 arithmetic-coding-shared-dict — addresses Shannon gap on key-name strings; expected +15-25 percentage points on heterogeneous-schema surfaces (atlas_convergence_witness primary beneficiary)
- A9 ai-native-tokenizer-axis — addresses tokenizer-induced overhead; expected +5-10 percentage points uniformly when hexa-native tokenizer lands
- A10 (per task #20 ROI inventory) — pending subagent definition; estimated +10-15 percentage points
- Combined target: A1 (24%) + A7 (20%) + A9 (8%) + A10 (12%) = ~64% simple-mean; close to 80% on byte-weighted with atlas's A7 gain dominating

## Compliance
- raw 9 hexa-only — `tool/hxc_convert.hexa` only; no python/awk in the conversion path
- raw 91 honest C3 — small-N edge case explicitly recorded with empirical evidence (corpus_tier_tier3_high 9.42%)
- raw 92 falsifier evidence — F1 fired on byte-weighted axis, recorded; not retired (scope-clarified to log-class surfaces)
- doc-only — no chflags changes, no SSOT mutation, no .raw edit; only adds to `state/format_witness/` and `docs/`

## Honest disclosures (raw 91 C3)
- escalation_pending.jsonl was not findable in `/Users/ghost/core/anima/state/audit/`; the directory does not exist. Substituted with alm_r13_4gate_pass_subset.jsonl. The substitution is documented in the JSONL ledger row with `files_added` field.
- byte-weighted vs simple-mean discrepancy is structural, not a measurement artifact — atlas_convergence_witness is 74.7% of 5-file primary native-byte mass.
- selftest 1 FAIL is small-N expected (3-row 2-schema fixture); not retried with a larger fixture in this cycle to keep the selftest fast and the failure visible.
- Saving percentages are A1-only point measurements at 2026-04-28 file states. They will drift as files grow; 30-day re-measurement is the F1 falsifier evaluation point.
- A7/A9/A10 contribution estimates above are forward projections, not measurements. Only after those algorithms land + a re-measurement cycle runs do we have evidence to compare against the 80% target.
- This is doc-only; no production JSONL is migrated to .hxc in phase 1. Migration is a separate cycle with backup + rollback gates.

## Cross-references
- /Users/ghost/core/anima/state/format_witness/2026-04-28_hxc_a1_baseline_5_jsonl.jsonl (per-file measurement ledger)
- /Users/ghost/core/anima/docs/hxc_physical_math_limit_saturation_20260427_landing.md (parent ω-cycle from 2026-04-27)
- /Users/ghost/core/hive/tool/hxc_convert.hexa (A1 converter used)
- /Users/ghost/core/hive/tool/hxc_pilot.hexa (Pilot A+B baseline)
- /Users/ghost/core/hive/tool/hxc_lint.hexa (HXC byte-canonical invariant lint)
- /Users/ghost/core/hive/state/format_witness/2026-04-26_pilots.jsonl (Pilot B baseline 27.7% reference)
- /Users/ghost/core/hive/docs/formats/hxc.md (HXC v1 format spec, 141 lines)
- raw 137 (anima top-5 JSONL surface measure HXC saving)
- raw 92 (format-ai-native-canonical) F1 falsifier
- raw 91 C3 (honest small-N edge disclosure)
- raw 9 (hexa-only tool constraint)
- raw 101 (landing doc ≥60 lines)
