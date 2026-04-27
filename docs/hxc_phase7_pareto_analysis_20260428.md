# HXC Phase 7 Pareto Frontier Analysis — Honest 80% Gap

**Date**: 2026-04-28
**Phase**: 7 (best-of-N + secondary stacking)
**Witness**: `state/format_witness/2026-04-28_migration_phase7_actual.jsonl`

## Aggregate

| Metric | Value |
|---|---:|
| Total input bytes | 1,178,369 |
| Total HXC bytes | 926,046 |
| Bytes saved | 252,323 |
| Byte-weighted saving | **22.00%** |
| raw 137 target | 80.00% |
| Gap | **-58.00pp** |

## Per-corpus Pareto category

| corpus | bytes | % of total | saving | category |
|---|---:|---:|---:|---|
| `alm_r13_4gate_pass_subset` | 980,326 | **83.2%** | 24% | DOMINANT-TEXT-HEAVY |
| `atlas_convergence_witness` | 147,645 | 12.5% | 1% | INFORMATION-FLOOR |
| `asset_archive_log` | 33,913 | 2.9% | 39% | HEADROOM-CATEGORICAL |
| `log_rotation_zstd_log` | 9,088 | 0.8% | 43% | HEADROOM-CATEGORICAL |
| `serve_alm_persona_log` | 4,111 | 0.3% | 64% | NEAR-TARGET |
| `corpus_tier_tier3_high` | 2,812 | 0.2% | 10% | TINY-OVERHEAD |
| `dist_native_build_periodic` | 258 | <0.1% | 0% | TINY-OVERHEAD |
| `cert_incremental_log` | 216 | <0.1% | 2% | TINY-OVERHEAD |

## Information-theoretic ceiling diagnosis

**alm_r13 (83% of total bytes)** is the dominant byte-weight factor. Achieving 80% on alm_r13 alone would require dropping it from 980K to 196K — a 4.99× compression ratio on text-heavy LLM training corpus. Current 24% reflects pure-hexa A1+A8+A4 stack. To reach 80% on this corpus class, A9 hexa-native tokenizer (raw 86 follow-up, blocked) is the required missing primitive — projects +30-50pp on tokenizable text per LLM tokenization theory (cl100k vocab compresses English 3-4× before entropy coding).

**atlas_convergence (12.5% of total)** sits at A1 baseline 0.91% with all downstream algos rejecting via try-and-revert. This is the information-theoretic entropy floor for atlas's content shape (4 schemas × small N rows × text-heavy fields × short structural fragments without whole-subtree repetition). Per Phase 5 P5 A4 agent honest finding (anima/docs/hxc_a4_structural_20260428_landing.md): atlas's 0.91% ceiling is information-theoretic, not algorithmic — further saving requires schema redesign at write-time, outside HXC scope.

**Headroom-categorical (asset_archive, log_rotation)**: these have low-cardinality enum columns where A8 fires correctly. Could push toward 60-70% with per-column Huffman + entropy coding, but ROI per LoC is small (combined 3.7% of total bytes).

**Near-target (serve_alm 64%)**: closest to 80% target. 6 columns with constant values across 24 rows — textbook A8 win.

## raw 137 80% target reachability

**Achievable byte-weighted with current algorithm catalog**: ~22% (Phase 7).

**Path to 80% byte-weighted**:
1. **A9 hexa-native tokenizer** (raw 86 dependency, blocked) — projects byte-weighted lift to ~45-55% by attacking alm_r13's 83% byte share. ROI: +23-33pp per implementation.
2. **Schema redesign for atlas-class corpora** — outside HXC scope, write-side concern.
3. **Pure-hexa entropy coding** (arithmetic coder, ~500 LoC) — projects +5-10pp byte-weighted on already-compressed streams.

**Honest verdict (raw 91 C3)**: 80% byte-weighted target is NOT reachable on current 8-corpus selection without A9 unblock. The corpus mix is dominated by text-heavy LLM training data (alm_r13) which intrinsically requires tokenizer-class compression. Atlas's information-theoretic floor (0.91%) is a hard stop for that 12.5% slice.

**Recommendation**: keep raw 137 80% as aspirational target, accept 22% as Phase 7 achievable ceiling, prioritize Phase 8 A9 tokenizer as the primary remaining ROI lever. Alternative interpretation of raw 137: per-corpus 80% achievable for non-text-heavy corpora (serve_alm 64% already near target; A8 perfecting on asset_archive could push 70%+).

## Falsifiers (raw 71 contract)

- **F-Phase7-1** (saving < 0.05 byte-weighted): NOT FIRED, 22.00% well above floor.
- **F-Phase7-2** (any single corpus regression > 5%): NOT FIRED, try-and-revert wrapper preserves baseline (dist_native_build 0% identity passthrough on otherwise-regressing chain).
- **F-Phase7-3** (decode round-trip not byte-eq): DEFERRED — hxc_migrate emits encode-only; decode tested at module level (selftest A1/A4/A7/A8/A10/A11 all PASS byte-eq).
- **F-Phase7-4** (encode latency > 10s on any corpus): NOT FIRED, alm_r13 (largest at 980K) measured ~3s.

## Cross-references

- Phase 6 wiring: hive `c79c14aa3`
- Phase 7 best-of-N: hive `ae1a08a63`
- Phase 7 actual migration: anima `3b4881c7`
- A11 landing: anima/docs/hxc_a11_cross_row_delta_20260428_landing.md
- A8 landing: anima/docs/hxc_a8_column_stat_20260428_landing.md
- A4 landing (honest falsification): anima/docs/hxc_a4_structural_20260428_landing.md
- A7+A10 fixes: hexa-lang `a88289e9` + `2cd4fd85`
- raw 137 cross-repo HXC mandate: hive/.raw raw 137
- raw 86 A9 tokenizer dependency: hive/.raw raw 86

## raw 102 disposition

Phase 7 closure: STRENGTHEN-existing on raw 137 measurement axis evidence (autonomous per raw 103 STRENGTHEN-existing path). No new raw addition. P-format-1 roadmap entry already updated with Phase 6+7+8+9 history (commit hive `f4553ab3b`). This document is the canonical witness for the 80% target gap analysis at Phase 7 closure.
