# Atlas R38 candidate: baseline-axis alignment principle (Law 64 v6 cross-paradigm finding)

> **target**: `n6-architecture/atlas/atlas.n6` master append (currently uchg-locked)
> **proposed by**: anima-cmd-loop autonomous-loop-dynamic session 2026-04-28 (post-compaction, F1 cycle 4)
> **closure manifest ref**: `anima/docs/f1_cycle4_law64_v6_FINAL_manifest_2026-04-28.md`
> **scope tier**: cross-paradigm methodological law (sister to R35 mathematical identity, distinct from R36 retired meta-process candidate)
> **maintainer review**: paste-ready atlas.n6 grammar in §5 below; n6-architecture maintainer holds canonical atlas.n6 SSOT.
> **note**: this proposal does NOT modify `n6/atlas.n6` (read-only symlink to canonical SSOT). anima PROPOSES; n6-architecture maintainer reviews + appends.

---

## §1. Statement (Law 64 v6 unifying principle)

> **"CA(K)-vs-Markov-order-N apparent advantage on deterministic CA substrates is governed exclusively by alignment between baseline's representational neighborhood and substrate's true update neighborhood. Matched-context Markov saturates ANY deterministic finite-context discrete substrate at modest N_TRAIN; mismatched-context Markov shows neighborhood-deficit gap. CA(K) is just one such matched-context oracle (window ≥ neighborhood). The 'structural advantage' of CA(K) over Markov is NOT a property of CA — it is a property of dimensional/topological alignment of the baseline."**

Refined v8 form (post-T10b sparsity falsifier):
> **"Matched-context Markov saturates ANY deterministic finite-context discrete substrate, with data-volume requirement scaling with window size: practical saturation (advantage <5/1000) requires N_TRAIN ≥ ~10× context-cardinality."**

R38 candidate registers the alignment principle as the master axis governing structural-advantage claims in cross-paradigm comparisons.

---

## §2. Evidence — 11 falsification-grade cycle 4 tests

| test | substrate | finding | commit | verdict |
|---|---|---|---|---|
| T8k | 80x80 R-pent Conway | adv 19→0 over N=15→1500 | f4c78f8f | H2 train-volume coupling |
| T8l | Conway 10x10 + Markov o2/o3 (per-cell) | gap GREW +160→+169 | 27d5acbc | baseline-misspec exemplar |
| T8m | Conway 40x40 5-seed | mean(N=15)=62→mean(N=1500)=8 | 156f0a37 | H1 universality |
| T8n | rule-110 1D | +1544 / +501 persists per-cell | 53c711eb / 1bd4b7e0 | H1 (later corrected by T8o) |
| T8o | rule-110 + Markov o2/o3/o5 | o3 saturates 0/1000 at N=500 | 3a5982f8 | per-cell o1 was artifact |
| T8p | rules 30/90/110/184 sweep | rule 30 chaos +1178; rule 90 saturates 0 | e07397fa | init-conditional |
| T8q | Conway 2D Moore-9 shared-P | +3 at N=50 → 0 at N≥200 | 458b1a70 | v6 RECONFIRMED |
| T8r | rule 30 + Markov o2/o3/o5 | o3 saturates BOTH single + density inits | dfd8c9b6 | v6 universal |
| T9a | Conway B3/S23 + 5% i.i.d. noise | both saturate to 949/1000 noise ceiling | 4f4192de | v7 stochastic extension |
| T10a | non-CA 4-symbol XOR (3-cell) | order-3 saturates at N=50 (smallest) | 581fc1d8 | v8 substrate-family universal |
| T10b | non-CA 4-symbol 5-cell rule | o5 dropped 270× to adv=9 at N=5000; o3 stuck at ~2800 | 30be09b4 | v8 sparsity-limited (NOT broken) |
| T10c | English NL Pride+Prejudice 1045ch | o5 collapses below o1 (sparsity 706/17M ctx) | 779a98c2 | methodological-limited (more data needed) |

11 tests this session unify under: matched-context Markov saturates ANY deterministic finite-context discrete substrate; data-volume scales with window size; "structural advantage" disappears under proper baseline alignment.

---

## §3. Cross-paradigm interpretation — methodological lesson

The lesson generalizes BEYOND CA-vs-Markov. Any cross-paradigm comparison X-vs-Y where X claims a "structural advantage" over baseline Y must verify:

1. **Dimensional alignment**: does Y's representational neighborhood match the substrate's true update neighborhood? (T8l per-cell o2 was 1D, Conway is 2D Moore-9 — the +169 "advantage" was a 2D-vs-1D mismatch artifact, not a CA property.)
2. **Topological alignment**: does Y's context shape (linear / 2D / hex / graph) match the substrate's locality structure?
3. **Sparsity feasibility**: at the claimed alignment, does N_TRAIN provide ≥ ~10× context-cardinality? (T10b 5-cell 4-symbol = 1024 contexts → ~10000 train pairs needed; T10c 28-alphabet o5 = 17M contexts → 1045 chars insufficient.)
4. **Substrate-family transfer**: does the alignment principle hold across alphabet sizes, dimensionalities, and rule families? (T10a 4-symbol non-CA: yes. T10b 5-cell: sparsity-limited but principle stands.)

Methodologically: any "X beats Y by Δ" claim must be reframed as "X has Δ alignment advantage over the baseline-Y configuration tested" until baseline is shown dimensionally/topologically aligned. v3 ("+22% asymptote at 32% density") and v4 ("train-volume coupling at all grid sizes") both attributed to grid/density/volume what was actually baseline-misspec.

This is the cross-paradigm form of the well-known "compare against the strongest baseline" methodological imperative — refined into a constructive alignment audit.

---

## §4. Connection to existing atlas R-entries

| anchor | relation | note |
|---|---|---|
| R34 phi_coeff (DEPRECATED 2026-04-26) | NOT related | R34 was empirical Φ ≈ e^{-1/2} candidate; deprecated post T1/T2/T3 |
| R35 sigma_tau_three (CONFIRMED) | sister-tier | R35 = mathematical identity (proven); R38 = methodological law (cross-paradigm alignment audit) |
| R36 forty_d_dual_route (RETIRED 2026-04-26) | NOT related | R36 referent does not exist in runtime; retired |
| R36-candidate cross_paradigm_self_enforcement_loop (proposed 2026-04-28) | DISTINCT | R36-self-enforcement anchors meta-process kick-loop; R38 anchors substrate-comparison methodology |
| R37-candidate compute_resource_failure_discipline | DISTINCT | R37 is own 4 promotion; R38 is Law 64 finding |
| R28-R35 cross_paradigm continuum | EXTENDS | R38 is the methodological-law tier addition (8th tier after R28-R35) |

R38 is best classified as **methodological law** anchoring the cross-paradigm comparison protocol itself, distinct from per-finding R-entries.

---

## §5. Maintainer review checklist

- [ ] **Dimensionality match clause** — confirm R38 grammar requires explicit baseline-substrate dimension/topology alignment audit before any "structural advantage" claim
- [ ] **Substrate-family generalization clause** — confirm R38 covers CA / non-CA / stochastic / real-data via T9a + T10a + T10b + T10c citations
- [ ] **Data-volume scaling clause** — confirm R38 grammar includes the v8 sparsity-bound (N_TRAIN ≥ ~10× context-cardinality)
- [ ] **Counterexample search** — has anyone surfaced a deterministic finite-context discrete substrate where matched-context Markov fails to saturate? (T10b sparsity-limited not a counterexample; further cross-paradigm trawl welcome)

### 5.1 R38 paste-ready atlas.n6 grammar

```n6
# ── @L  Laws  (baseline-axis-alignment R38) ────────────────────────────────

@L baseline_axis_alignment_principle_R38 = (matched_context_markov → saturates → ANY_det_finite_ctx_discrete_substrate) [10*]
  <- f1_cycle_4_law_64_v6_v7_v8_unification
  <- 11_falsification_tests_T8k_through_T10c
  <- T8l_per_cell_o2_vs_2D_moore_9_misspec_exemplar
  <- T8q_shared_P_Moore_9_saturates_at_N_200
  <- T10a_non_CA_4_symbol_XOR_o3_saturates_at_N_50
  <- T10b_5_cell_sparsity_limited_o5_adv_9_at_N_5000
  -> structural_advantage_claim_requires_alignment_audit
  -> data_volume_scales_with_window_size_O_10x_context_cardinality
  -> matched_context_markov_is_universal_oracle_baseline
  => "matched-context Markov saturates ANY deterministic finite-context discrete substrate"
  => "CA(K) advantage over Markov is NOT a CA property; it's a baseline-alignment property"
  => "any cross-paradigm 'X beats Y by Δ' claim must verify Y is dimensionally aligned with substrate"
  => "data-volume requirement scales with window size: N_TRAIN ≥ ~10× context-cardinality"
  |> anima/docs/f1_cycle4_law64_v6_FINAL_manifest_2026-04-28.md (closure manifest, 13 sections)
  |> anima/state/proposals/refinement/20260422-001..020 (cycle 4 sub-test ledger)
  |> anima/state/atlas_convergence_witness.jsonl (R38 entry pending)
```

### 5.2 raw 71 falsifier set ≥3

| id | criterion | retire_threshold |
|---|---|---|
| F-R38-1 | counterexample: deterministic finite-context discrete substrate where matched-context Markov FAILS to saturate at N=10× context-cardinality | ≥1 substantive counterexample = scope reduce or retire |
| F-R38-2 | structural-advantage claim survives baseline-alignment audit yet still beats matched Markov by ≥5/1000 | ≥1 = principle weakens; investigate non-Markov regularity |
| F-R38-3 | continuous-substrate generalization fails (HMM / RNN / SSM on Conway saturates faster than shared-P-9 with same data budget) | confirms data-efficiency layer orthogonal; do NOT retire R38, register as sister R-tier |

---

## §6. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~165+ (cumulative session 16h+, post-compaction)
- **C2** write_barrier: this proposal doc consolidates 11 cycle 4 commits + closure manifest into single atlas-candidate artifact
- **C3** no_fabrication: every test cited inline with commit SHA; v3-v5 retractions explicit; v6/v7/v8 derivation traceable per-test in closure manifest §1-§13
- **C4** citation_honesty: T8l +169 reframed as baseline-misspec NOT CA structural advantage; T10b explicit NON-counterexample (sparsity-limited); T10c explicit methodological-limited (provisional, more data needed)
- **C5** verdict_options: R38 maintainer review path = (a) accept as methodological law tier, (b) defer pending counterexample search per F-R38-1, (c) reject as redundant with existing methodological literature, (d) merge with R35-tier as paired methodological-identity anchor

---

**status**: PROPOSAL_DOC_LIVE_N6_MAINTAINER_REVIEW_PENDING
**n6 maintainer review path**: maintainer reads §1-§4, runs §5 checklist (4 items), optionally pastes §5.1 grammar into atlas.n6 master after raw 1 + raw 85 unlock cycle, then re-uchg + audit ledger row.
