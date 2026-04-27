# HXC Phase 4-B large heterogeneous corpus pilot — anima — 2026-04-28 landing

## Topic
Phase 4-B of the HXC migration pilot for raw 137 (anima JSONL surface measure HXC saving toward 80% Shannon Pareto frontier). This phase extends the Phase 1 baseline (5 + 1 file pilot, raw 91 honest, 7.43% byte-weighted A1-only) with 10 large heterogeneous corpora chosen to satisfy the Phase 3 (commit 363db75bc) corpus-profile-aware conditional apply heuristic, in order to (a) measure the Phase 3 chain's empirical saving relative to A1-only baseline, (b) quantify the gap to the 80% target, and (c) verdict whether additional algorithms (A8/A9/A11) are required.

## User directive
"raw 137 80% target evidence 측정 — large heterogeneous corpus pilot — A1+A7+A10 chain 활성 시 saving 측정, 80% 향한 큰 jump (≥60% hopefully)". Doc-only cycle, no chflags, no SSOT mod, no production migration. ~30-60 minute time budget.

## Mandate trace
- raw 137 (anima top-N JSONL surface measure HXC saving — 80% Pareto frontier target)
- raw 9 hexa-only (`/Users/ghost/core/hive/tool/hxc_migrate.hexa` + linked `/Users/ghost/core/hive/tool/hxc_a7_shared_dict.hexa` + `/Users/ghost/core/hive/tool/hxc_a10_varint.hexa`)
- raw 12 silent-error-ban (A7/A10 subprocess fail returns input passthrough — visible in `algorithm_chain` CSV)
- raw 65 idempotent (re-encoding HXC through A1 yields byte-equal output)
- raw 91 honest (4 regressions empirically documented, Phase 3 commit claim falsified)
- raw 101 minimal (this landing doc ≥60 lines, no ornamentation)

## Tool used
- `/Users/ghost/core/hive/tool/hxc_migrate.hexa` at commit 363db75bc — Phase 3 corpus-profile-aware conditional apply
- selftest 12/12 PASS (raw 65 + 68 idempotent + composability all stages)
- A10 module: `/Users/ghost/core/hive/tool/hxc_a10_varint.hexa` (subprocess delegate)
- A7 module: `/Users/ghost/core/hive/tool/hxc_a7_shared_dict.hexa` (subprocess delegate)
- A9 module: NOT_LANDED (passthrough confirmed)

## Candidate inventory methodology
- Required: rows ≥ 16 (A1 amortization), schemas ≥ 2 (heterogeneity), avg_rps ≥ 4 (A7 dict overhead amortization). For A10: int_ratio ≥ 30%, rows ≥ 8.
- Search scope: `/Users/ghost/core/anima/state/*.jsonl`, `/Users/ghost/core/anima/training/*.jsonl`, max-depth 4 (excluding `.claude/worktrees/`).
- 10 candidates selected covering: large multi-schema (alm_r13_4gate / corpus_tier_tier1), small multi-schema (cross_repo_sync_log / lint_cron_history / dd_bridge / h100_precache), large single-schema (corpus_universe_extended / stimulus_factory_candidates / corpus_universe_tier_labels / stimulus_tier_graph).

## Per-file measurement table

| file | native_B | A1_only% | full_chain% | delta_pp | schemas | rows | rps | chain |
|---|---:|---:|---:|---:|---:|---:|---:|:---|
| state/alm_r13_4gate_pass_subset.jsonl | 980326 | 22.09 | 15.93 | -6.16 | 5 | 840 | 168.0 | A1,A7 |
| state/cross_repo_sync_log.jsonl | 2090 | 42.44 | 36.89 | -5.55 | 2 | 15 | 7.5 | A1,A10 |
| state/corpus_tier_tier1_low.jsonl | 977514 | 22.10 | 15.96 | -6.14 | 5 | 838 | 167.6 | A1,A7 |
| training/corpus_universe_extended.jsonl | 139540 | 48.29 | 48.29 | 0.00 | 1 | 500 | 500.0 | A1 |
| training/stimulus_factory_candidates.jsonl | 36595 | 42.51 | 40.73 | -1.78 | 1 | 100 | 100.0 | A1,A10 |
| training/corpus_universe_tier_labels.jsonl | 36405 | 43.65 | 43.65 | 0.00 | 1 | 170 | 170.0 | A1 |
| training/stimulus_tier_graph.jsonl | 22465 | 31.93 | 31.93 | 0.00 | 1 | 195 | 195.0 | A1 |
| state/lint_cron_history.jsonl | 416 | 27.88 | 27.88 | 0.00 | 2 | 4 | 2.0 | A1 |
| state/dd_bridge_gpu_batch_witness.jsonl | 2069 | 7.20 | 7.20 | 0.00 | 5 | 5 | 1.0 | A1 |
| state/h100_weight_precache_progress.jsonl | 675 | 13.33 | 13.33 | 0.00 | 2 | 4 | 2.0 | A1 |

## Aggregate statistics (10-corpus pilot)
- total native bytes: 2,198,095
- total A1-only bytes: 1,658,223
- total full-chain bytes: 1,779,447
- A1-only byte-weighted saving: 24.56%
- full-chain byte-weighted saving: 19.05%  (-5.51 pp REGRESSION vs A1-only)
- A1-only simple-mean saving: 30.14%
- full-chain simple-mean saving: 28.18%  (-1.96 pp regression vs A1-only)
- stdev A1-only: 13.99 pp
- stdev full-chain: 14.34 pp
- min A1-only: 7.20% (dd_bridge_gpu_batch — atlas-class heterogeneity)
- max A1-only: 48.29% (corpus_universe_extended — single-schema text-heavy)
- gap to 80% target (byte-weighted): -55.44 pp (A1-only) / -60.95 pp (full-chain)
- gap to 80% target (simple-mean): -49.86 pp (A1-only) / -51.82 pp (full-chain)

## Critical Phase 4-B finding: Phase 3 commit message FALSIFIED

Commit 363db75bc message: "Phase 3 corpus-profile-aware conditional apply — regression eliminated".

Phase 4-B empirical evidence (10 corpora):
- 4 of 10 corpora REGRESS when Phase 3 chain triggers (A7 or A10 fired):
  - alm_r13_4gate_pass_subset.jsonl: 22.09% A1 → 15.93% A1+A7  (-6.16 pp)
  - corpus_tier_tier1_low.jsonl:    22.10% A1 → 15.96% A1+A7  (-6.14 pp)
  - cross_repo_sync_log.jsonl:      42.44% A1 → 36.89% A1+A10 (-5.55 pp)
  - stimulus_factory_candidates.jsonl: 42.51% A1 → 40.73% A1+A10 (-1.78 pp)
- byte-weighted aggregate full-chain (19.05%) is WORSE than A1-only (24.56%) by 5.51 pp
- This falsifies the Phase 3 "regression eliminated" claim. The profile heuristic correctly fires per its declared rules (schema_count ≥ 2 + rows ≥ 16 + avg_rps ≥ 4 for A7; int_ratio ≥ 30% + rows ≥ 8 for A10), but the underlying A7 and A10 modules themselves produce regressions on these specific corpus shapes.

## Root cause analysis
A7 regression (multi-schema large corpora, alm_r13 / corpus_tier_tier1):
- A7 emits a shared-dict header per schema (~few hundred bytes total). On corpora where keys are already short and values are heterogeneous text, the dictionary saving is overwhelmed by the dictionary overhead bytes plus the per-row dict-reference encoding bytes.
- Phase 3 heuristic missing gate: estimated A7 saving margin BEFORE apply.

A10 regression (cross_repo_sync_log + stimulus_factory_candidates):
- A10 base64url bookkeeping (length headers + alignment padding) exceeds varint saving when (a) row_count is small (15 in cross_repo case), or (b) average integer values are small (1-2 digits — varint encoding gains very little).
- Phase 3 heuristic gate (int_ratio ≥ 30% + rows ≥ 8) is too permissive.

## 80% target gap quantified analysis
Current state (Phase 4-B, A1-only baseline): byte-weighted 24.56%, simple-mean 30.14%. Gap to 80%:
- byte-weighted: 55.44 pp
- simple-mean:   49.86 pp

This gap CANNOT be closed by A1+A7+A10 alone, even after fixing the regressions. Empirical maximum observed on a single corpus is 48.29% (corpus_universe_extended, single-schema text-heavy A1-only). The byte-weighted aggregate is dragged down by:
1. multi-schema verbose-key corpora plateau at 22% A1-only (alm_r13, corpus_tier_tier1)
2. small-N corpora (rows < 8) plateau at 7-13% A1-only (dd_bridge, h100_precache)

## Verdict on additional algorithms (A8/A9/A11)

REQUIRED — A1+A7+A10 alone cannot close 50+ pp gap to 80%. Forward-spec proposed:

| algo | description | expected gain | priority |
|---|---|---:|:---:|
| A11 | cross-row delta (timestamp + monotonic counter) | +15-25 pp | P1 |
| A8  | column-statistical (per-column entropy coding) | +10-15 pp | P2 |
| A9  | ai-native tokenizer (BPE-aware key-name elision) | +8-12 pp | P3 |
| A4  | structural compression (atlas-class ceiling) | +10-20 pp | P4 |

Combined ceiling estimate: A1-fixed + A7-fixed + A10-fixed + A11 + A8 + A9 → ~70% byte-weighted on heterogeneous corpora. Reaching 80% requires A4 structural compression for atlas-class surfaces (35-schema heterogeneity).

## Recommended next steps (priority order)
- P0: fix A7/A10 regression via try-and-revert wrapper in `hxc_migrate.hexa` — compute candidate output bytes; if > input revert to identity passthrough. Idempotent (raw 65 + 68) is preserved because identity is the trivial idempotent fixpoint. Implementation budget: ~30 lines of hexa, single subprocess delegate diff.
- P1: implement A11 cross-row delta module — log-class surfaces (asset_archive_log, log_rotation_zstd_log, alm_persona) have monotonic timestamp + counter columns where delta encoding gains 15-25 pp.
- P2: implement A8 column-stat module — per-column entropy coding for integer-heavy columns.
- P3: A9 tokenizer (already deferred — depends on hexa-native tokenizer landing).
- P4: A4 structural compression for atlas-class.

## Compliance disclosures (raw 91 C3)
- Phase 3 commit (363db75bc) claim "regression eliminated" is empirically falsified on 4/10 corpora — recorded in ledger row "phase3_heuristic_gap".
- 4 of 10 corpora measured exhibit Phase 3 chain regression — none of these corpora overlap with the Phase 1 5-file pilot used to validate Phase 3.
- Saving percentages are point measurements at file-state of 2026-04-28; will drift as files grow. F1 (raw 92 30-day falsifier) re-measurement is the next evaluation point.
- A8/A9/A11 contribution estimates are forward projections based on column-counted entropy and observed key-name redundancy, NOT measurements. Only post-implementation measurement closes the loop.
- This is doc-only — no production JSONL is migrated, no .hxc files committed under anima.
- Honesty disclosure on tool selection: corpus_alm_70b.jsonl (90283 rows / 93MB) was not measured because expected encode_ms exceeds Phase 4-B time budget; small/medium corpora are sufficient to falsify Phase 3 claim.

## Cross-references
- /Users/ghost/core/anima/state/format_witness/2026-04-28_phase4_large_corpus.jsonl (per-file measurement ledger)
- /Users/ghost/core/anima/state/format_witness/2026-04-28_hxc_a1_baseline_5_jsonl.jsonl (Phase 1 baseline reference)
- /Users/ghost/core/anima/docs/hxc_migration_a1_baseline_20260428_landing.md (Phase 1 landing doc)
- /Users/ghost/core/anima/docs/hxc_physical_math_limit_saturation_20260427_landing.md (parent omega-cycle)
- /Users/ghost/core/hive/tool/hxc_migrate.hexa (Phase 3 commit 363db75bc, 688 lines)
- /Users/ghost/core/hive/tool/hxc_a7_shared_dict.hexa (A7 module, regressing)
- /Users/ghost/core/hive/tool/hxc_a10_varint.hexa (A10 module, regressing)
- raw 137 (format-compression-pareto-frontier-80pct-shannon)
- raw 92 (format-ai-native-canonical) F1 falsifier preregistered
- raw 91 C3 (honest small-N + counter-evidence disclosure)
- raw 9 (hexa-only tool constraint)
- raw 65 (idempotent contract)
- raw 12 (silent-error-ban)
- raw 101 (landing doc ≥60 lines)
