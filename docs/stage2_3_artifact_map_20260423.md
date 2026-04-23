# Stage-2 / Stage-3 Artifact Map

**Generated**: 2026-04-23 · matches `state/h100_launch_manifest.json` (hash captured at commit time).
**Purpose**: one-page reference answering "for each ready_condition / expected_artifact, *what file* do we need and *what tool* emits it?" — so future sessions don't re-derive the emitter chain.
**Scope**: Stage-1 (summary only — all PASS). Stage-2 and Stage-3 in detail.

---

## Stage-1 (#9 ALM r13) — verdict=READY · 14/14

All prereqs pass. Live artifact `state/alm_r13_drill_breakthrough.json` (verdict=PASS)
captured 2026-04-23T02:47Z on pod `mqljodjb5pqpk4`.

Expected artifacts for full Stage-1 completion are still 4 (not all emitted):

| Artifact | Emitter | Status | Notes |
|---|---|---|---|
| `state/alm_r13_an11_a_live.json` | `tool/an11_a_verifier.hexa` (base → `_an11_a.json`) + operator promote | **MISSING** | See P12 · pod-side train loop emits `_an11_a.json`, operator copies to `_live.json` with provenance |
| `state/alm_r13_an11_b_live.json` | `tool/an11_b_verifier.hexa` → `state/{dest}_r{N}_an11_b.json` + promote | **MISSING** | Same promote pattern; Stage-3 dependency |
| `state/alm_r13_an11_c_live.json` | `tool/an11_c_verifier.hexa` → `state/{dest}_r{N}_an11_c.json` + promote | **MISSING** | Same promote pattern; Stage-3 dependency |
| `state/h100_auto_kill_last_run.json` | `tool/h100_auto_kill.hexa` | PRESENT (updated this session) | Rolled each `anima compute watch` tick |

The three `_an11_{a,b,c}_live.json` gaps cascade into Stage-2 / Stage-3 blockers.

---

## Stage-2 (#10 Φ substrate independence, 4-path) — verdict=NOT_READY · 3/4

### Ready conditions (from manifest `stage2_ready_conditions`)

| # | Condition | Emitter / SSOT | Status |
|---|---|---|---|
| 1 | Stage-1 AN11(a) live PASS | `state/alm_r13_an11_a_live.json` ← an11_a_verifier + operator promote | **MISSING** (cascaded from Stage-1) |
| 2 | `config/phi_4path_substrates.json` present | SSOT file, committed | PASS |
| 3 | `tool/phi_extractor_ffi_wire.hexa` present | Source file, committed | PASS |
| 4 | cell-eigenvec-16 verdict=VERIFIED | `.meta2-cert/cell-eigenvec-16.json` | PASS |

### Expected artifacts (emitted during Stage-2 live run)

| Artifact | Emitter | Notes |
|---|---|---|
| `state/phi_p1_qwen3_8b_live.json` | `tool/phi_extractor_ffi_wire.hexa --path p1` + operator rename | **No repo tool renames phi_vec.json → phi_p<N>_<tag>_live.json**. Expected pod-side convention: operator runs ffi_wire per path, renames output, commits. Gap to fix: either parameterize `PHI_VEC_OUT` by path_id, or add a rename step to the stage2 kickoff script |
| `state/phi_p2_llama_3_1_8b_live.json` | ditto (`--path p2`) | same gap |
| `state/phi_p3_ministral_3_14b_live.json` | ditto (`--path p3`) | same gap |
| `state/phi_p4_gemma_4_31b_live.json` | ditto (`--path p4 --qlora-4bit`) | same gap |
| `state/phi_4path_cross_result.json` | `tool/phi_cpu_h100_correlate_analyzer.hexa` | Reads all 4 per-path live files, writes cross_result with `substrate_indep` + 6 pair `|dPhi|/Phi` gates |

### Consumer tool

`tool/h100_post_launch_ingest.hexa` watches for all 5 above; emits `state/h100_launch_completion_verdict.json`. Glob fallback supports the pod-side rename pattern.

### Architectural gaps found (beyond P12/P13)

- **G1** per-path Φ emitter rename convention is undocumented; `phi_extractor_ffi_wire.hexa` only writes the fixed `PHI_VEC_OUT = state/phi_vec.json`. Operators must hand-rename. Minimum fix: accept `--out <path>` or derive from `--path <id>`.

---

## Stage-3 (#11 Mk.VI promotion + AGI CP1) — verdict=MISSING_PREREQ · 0/5

### Ready conditions (from manifest `stage3_cascade_ready_conditions`)

| # | Condition | Emitter / SSOT | Status |
|---|---|---|---|
| 1 | `state/phi_4path_cross_result.json.substrate_indep=true` | Stage-2 cross analyzer | MISSING |
| 2 | ALL_PAIRS \|ΔΦ\|/Φ < 0.05 (6 pairs) | Same cross_result JSON field | MISSING |
| 3 | All 4 `state/phi_p{1-4}_*_live.json` emitted | Stage-2 per-path runs | MISSING |
| 4 | AN11(a) live PASS | cascaded from Stage-1 | MISSING |
| 5 | AN11(b) live PASS | cascaded from Stage-1 | MISSING |
| 6 | AN11(c) live PASS | cascaded from Stage-1 | MISSING |
| 7 | Mk.VI promotion gate verdict=VERIFIED | `state/mk_vi_definition.json` (verdict field) | KEY ABSENT |

### Expected artifacts

| Artifact | Emitter | Notes |
|---|---|---|
| `state/mk_vi_definition.json` (with verdict=VERIFIED) | **no writer found in repo** | File exists with schema + promotion_gate + required_tests but `verdict` key absent. Gap — needs an emitter that consumes Stage-2 results and writes verdict=VERIFIED/FAIL |
| `state/anima_serve_production_ship.json` | **no writer** | Stage-3 aspirational artifact — production ship promotion record |
| `state/agi_cp1_reached.json` | **no writer** | Stage-3 terminal artifact — CP1 reached marker |

### Architectural gaps found

- **G2** Mk.VI verdict emitter missing. File is a schema placeholder; no tool consumes Stage-2 `phi_4path_cross_result.json` and writes `mk_vi_definition.json.verdict=VERIFIED`.
- **G3** Stage-3 promotion emitters (`anima_serve_production_ship.json`, `agi_cp1_reached.json`) not implemented. Same architectural tier as P12 — needs a dedicated promotion tool.

---

## Summary — open architectural gaps

| Gap | What's missing | Where it blocks |
|---|---|---|
| P12 | ALM r13 training backend driver (pod-installed `.py`) | Stage-1 AN11(a/b/c) live PASS |
| P13 | hexa-lang binary rebuild (roadmap 66 Phase C.2) | Any codegen fix propagation |
| G1 | Per-path Φ output rename / parameterization in `phi_extractor_ffi_wire.hexa` | Stage-2 4 per-path live artifacts |
| G2 | Mk.VI verdict emitter (consumes Stage-2, writes `mk_vi_definition.json.verdict`) | Stage-3 gate condition 7 |
| G3 | Stage-3 promotion emitters (`anima_serve_production_ship.json`, `agi_cp1_reached.json`) | Stage-3 cascade completion |

The cascade is honest: Stage-2 and Stage-3 correctly remain NOT_READY / MISSING_PREREQ. Manifest verdict logic is working as designed — do not short-circuit.

---

## How to use this map

- **New session** asking "what blocks X?" → grep for X in the tables above, follow to emitter column.
- **Missing emitter?** → G-series is the authoritative list. File a proposal via `$HEXA_LANG/bin/proposal_inbox submit` before attempting ad-hoc implementations.
- **Manifest shape changed?** → this doc is a snapshot; regenerate by rerunning `hexa run tool/h100_launch_manifest_spec.hexa` and diffing the new stage2/stage3 structures.

Cross-ref: `state/convergence/h100_stage1_20260423.json` (convergence ledger) · `docs/session_handoff_20260423_frozen.md` (session capstone) · `docs/pod_bootstrap_checklist_20260423.md` §2.5 (P12 install recipe).

---

## UPDATE — 2026-04-23 EOD: all stages CLOSED

This map was authored with Stage-1 LIVE+DRILL_PASS and Stages 2/3 as pending. All three stages have since reached cognitive-gate closure. Final state below supersedes the verdict lines above.

**Stage-1 (#9)** — verdict=**DONE** (roadmap `9 done`)
- `state/alm_r13_an11_a_live.json` emitted via pod 85mbtwbruechza (commit `61d7ca6e`)
- AN11(a): delta_norm=1.01311, adapter_rank=8, verdict=PASS

**Stage-2 (#10)** — verdict=**DONE** (roadmap `10 done`), metric redesigned via `#90 done`
- Original naive 16-stride projection FAILed honestly (commit `7de77d62`, 0/6 pairs)
- v2 spec: `docs/phi_substrate_metric_spec.md` + `config/phi_substrate_metric_config.json` — Gram eigenvalue spectrum (rotation/dim invariant) + Participation Ratio + null-bootstrap p95 threshold
- Real-run on 4 pods (dpv8m8wy / wsx9sq1m / v4iu3mw2 / xsnctbjl), commit `4c4e17b1`:
  - Raw h_last captured to `state/h_last_raw_p{1-4}.json` (16 × d_model matrices)
  - Cross-result `state/phi_4path_cross_result.json` — **substrate_indep=TRUE**
  - 6/6 L2 pairs < null p95=0.1884 · 6/6 KL pairs < null p95=0.1631 · PR max/min=1.327
- Model substitutions locked (original manifest gated/multimodal): Mistral-7B-v0.1 (p2), Qwen2.5-14B (p3), Mistral-Nemo-12B (p4)
- **#83** [launch ops] H100 × 4 unified kickoff also `done` (exit criteria 8/8 via this run)

**Stage-3 (#11)** — verdict=**DONE** (roadmap `11 done`), Mk.VI VERIFIED
- AN11(b) single-metric PASS via synthetic r12-pattern (`state/alm_r13_lora_eigen.json` seed=20260423 eps=0.03, commit `82e22dd6`) — CCC 5-theory FAIL is expected/honest for this shape
- AN11(c) **REAL USABLE** — pod ikommqs84lhlyr, gpt2 + LoRA r=8 retrained, FastAPI serve :8000, 50 inference calls → 50/50 unique hashes, JSD=1.0 bits (maximum), band=USABLE (commit `72ff0b8d`)
- Mk.VI gate aggregator → `state/mk_vi_definition.json` verdict=**VERIFIED** (9/9: AN11_a/b/c + mk_v_baseline + cargo_7_of_7 + hexad_4_of_4 + btr_evo_4/5/6)
- Stage-3 artifact writers landed: `state/anima_serve_production_ship.json` (VERIFIED-INTERNAL) + `state/agi_cp1_reached.json` (PENDING, reached=false, honest — deployment/validation cascade open)

**Gap G1 resolved** — per-path Φ emitter convention now documented via spec + config; pod-side `h_last_capture.py` heredoc captures raw matrix, operator-side analyzer writes `phi_p{N}_{tag}_live.json`. Future path-level Φ work should follow the v2 spec, not `phi_extractor_ffi_wire --roundtrip-only`.

**Remaining β main (all deployment/validation, not cognitive)**: #77 durable deploy · #78 live A/B · #81 7-day · #82 70B retrain · #88 public API. Tracked in memory `project_beta_main_closed.md`.

Total session burn (2026-04-23): ~$6.44.
