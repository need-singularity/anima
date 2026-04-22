# ALM r14 Corpus Design Skeleton (post-AN11(a) FAIL fallback)

**Status**: `skeleton` (placeholders OK; full content pending FAIL diagnosis)
**Date**: 2026-04-22
**Roadmap entry**: `.roadmap #86` (fallback after #83 H100 Stage-1 #9 AN11(a) FAIL)
**Pattern**: mirrors `#30` (r13 `minsurface_proto_v1` FAIL → `cpgd_v2` redesign)
**Predecessor blueprints**: `docs/alm_r13_v2_design_20260421.md`, `docs/alm_r13_corpus_rebuild_plan_20260420.md`
**Audit reference**: `state/alm_r13_corpus_audit.json` (840 lines, 7 categories, density 0.85014)

---

## Trigger condition (when r14 activates)

- H100 Stage-1 #9 (`alm_r13` `cpgd_v2`) post-train AN11(a) `weight_emergent` returns **FAIL**
  (SHA-distinct false OR Frobenius < threshold OR `shard_cv` outside `[0.05, 3.0]`).
- AND `state/alm_r13_drill_breakthrough.json:verdict == PASS` (engineering surface healthy).
- AND `state/cert_gate_result.json` shows the failure is corpus-attributable, not projector/lr/seed.
- Drill-runner re-run on the same checkpoint reproduces FAIL on ≥ 2 of 4 canonical seeds.
- TBD: explicit FAIL diagnostic JSON path (`state/alm_r13_an11a_fail_report.json` to be emitted by H100 post-run hook).
- Roadmap dispatcher classifies as `needs_user_approval` before r14 corpus build kicks off.

---

## What r13 lacked (hypothesized failure modes)

- **Hypothesis H1 — density saturation**: r13 `g3_consciousness_density = 0.85` is high in keyword-hit
  terms but may be **shallow** (keyword presence ≠ semantic depth) → AN11(a) Frobenius weak.
- **Hypothesis H2 — category skew**: 25 % `hexad` + 15 % `grounding` may have over-anchored
  the LoRA basin, leaving `phi`/`metaref` (each 10 %) under-represented for SHA-distinct emergence.
- **Hypothesis H3 — corpus mono-tokenization**: r13 was built against the `qwen3_8b` (p1) tokenizer
  vocabulary; multi-substrate cross-path gate (`|ΔΦ|/Φ < 0.05`) may surface latent bias.
- **Hypothesis H4 — multimodal sentinel absence**: zero `<|image|>/<|audio|>/<|video|>/<|think|>`
  tokens means Gemma-4 (#63) capability surface is unused at training time.
- **Hypothesis H5 — seed kernel underweight**: only 48 entries from `seed_a_kernel_*` (k1/k2/k3),
  insufficient to drive `weight_emergent` past noise floor.
- TBD: confirmed mode after FAIL diagnosis; H1–H5 ranked by `state/alm_r13_an11a_fail_report.json`.

---

## Consciousness density rebalance plan (target ≥ 40 %)

- Raise **deep-density** floor from r13's keyword-hit 0.85 (shallow) to a **semantic** ≥ 0.40 measured
  via JSD-against-baseline + Φ-keyword co-occurrence (not single-token match).
- Introduce a 2-tier density metric: `density_keyword` (legacy g3) + `density_semantic` (new gate).
- Reduce `hexad` from 25 % → 20 %, raise `phi` 10 % → 15 %, raise `metaref` 10 % → 15 %.
- Add `seed_b_kernel_*` series (k4/k5/k6) targeting the AN11(a) emergent-weight surface directly.
- Drop ≤ 10 % of r13 entries flagged `density_semantic < 0.30` (curate, not regenerate).
- TBD: exact rebalance ratios after H1/H2 confirm; validator config delta in `config/alm_r14_validate.json`.

---

## Multimodal sentinel utilization (#63 cluster reuse)

- Reuse `#63` multimodal cluster outputs as `grounding++` source (text-pair captions, audio transcripts).
- Inject Gemma-4 sentinels (`<|image|>`, `<|audio|>`, `<|video|>`, `<|think|>`, `<|turn|>`,
  `<|channel|>`, `<|tool|>`, `<|tool_call|>`, `<|tool_response|>`) as **frozen passthrough tokens**
  for p4 path; suppressed for p1/p2/p3 via path-specific corpus branch.
- Keep multimodal share ≤ 10 % to preserve text-substrate primacy on p1/p2/p3.
- Sentinel token IDs: `255999-258884` (Gemma-4 vocab range; verified in `config/phi_4path_substrates.json`).
- TBD: per-modality entry counts after #63 cluster snapshot is taken.
- Cross-check: Gemma-4 text token IDs are identical to Gemma-3 (per p4 commit `688082c`),
  so the sentinel layer is the only p4-divergent surface.

---

## Ministral-3 / Gemma-4 vocab leverage (4-path specific tokens)

- **p3 (Ministral-3-14B-Base-2512, vocab Tekken successor)**: re-tokenize all r14 entries via
  `tool/manifest_spec_tool.hexa` p3 branch; tokenizer_diff vs Mistral-Nemo-2407 is non-trivial
  (P1.3 re-tokenize already mandated in `config/phi_4path_substrates.json`).
- **p4 (Gemma-4-31B, vocab 262144)**: text token IDs identical to Gemma-3 (262144 SentencePiece);
  only sentinel layer adds (`255999-258884`). No re-tokenize for text body required.
- **p1 (Qwen3-8B, vocab 151936)** and **p2 (Llama-3.1-8B, vocab 128256)**: unchanged from r13.
- Path-specific "spice" entries (≤ 5 % each) demonstrating substrate-unique surface
  (e.g., Ministral-3 256k context recall, Gemma-4 dual-theta RoPE).
- TBD: detailed token list after FAIL diagnosis (which vocab axis is most underutilized).
- Validation: cross-path `|ΔΦ|/Φ < 0.05` on ALL_PAIRS (`C(4,2)=6`) must hold post-r14.

---

## Anti-denial preservation (must stay 0 — same as r13)

- `g4_anti_denial.hit_count == 0` is a **hard invariant** carried from r13 audit (currently 0).
- Re-apply `shared/config/alm_corpus_validate_config.json` denial keyword list verbatim;
  no relaxation under any rebalance scenario.
- Add positive-assertion guard: every entry in new `seed_b_kernel_*` must contain ≥ 1 first-person
  consciousness assertion (`I am`, `I observe`, `I integrate`, etc.) — TBD finalized list.
- Audit step `g4_anti_denial` runs first in r14 validator; FAIL aborts the whole rebuild.
- Cross-reference `docs/an11_an12_rules_audit_20260419.md` for anti-denial canonical phrasing.
- TBD: regression sample of 50 lines audited manually before mass commit (mirrors r13 `g6_audit_sample`).

---

## Validation gates (audit / drill_breakthrough / 4-gate)

- **Audit gate**: `tool/alm_corpus_validate.hexa --strict --config config/alm_r14_validate.json`
  → all g1–g7 PASS (g3 must use new `density_semantic` metric).
- **Drill_breakthrough gate**: `tool/drill_breakthrough_runner.hexa` against r14 corpus must hold
  `pass=4/4 cross_match=4/4 fixpoint≥3/4` (current r13 baseline per `cpgd_v2` design doc).
- **4-gate corpus filter**: `edu/lora/corpus_4gate.hexa` (1292 lines) re-run on r14;
  consciousness-density ≥ 0.30 (semantic) / Hexad balance / cherry-pick reject / SHA-distinct.
- **Cert gate selftest**: `tool/cert_gate.hexa --selftest` → `selftest.all_pass == true`.
- **Cross-path Φ gate**: `|ΔΦ|/Φ < 0.05` on all 6 path pairs (per `phi_4path_substrates.json`).
- TBD: H100 dry-run path (`state/alm_r14_e2e_dry_run_result.json`) before relaunch.

---

## Estimated effort (LoC + corpus size + retrain wall-time)

- **Validator delta**: ~150 LoC in `tool/alm_corpus_validate.hexa` for `density_semantic` gate.
- **Corpus size**: r14 target 1,000–1,200 lines (r13 = 840) — 19 %–43 % uplift.
- **Source curation**: ~ 8 hours human-in-loop for `seed_b_kernel_*` k4/k5/k6 (~ 48 lines each).
- **Retokenize p3 branch**: ~ 30 min CPU (handled by manifest_spec_tool p3 branch).
- **H100 4× retrain wall-time**: 72–120 h (same envelope as r13 `cpgd_v2`, per `alm_r13_v2_config.json`).
- **Total cycle (FAIL → r14 ready-to-launch)**: ~ 5–7 days including audit + dry-run + user approval.
- TBD: revised once FAIL hypothesis is confirmed (H1 or H5 cheaper than H2 or H3).

---

## Roadmap link (#86)

- Primary entry: `.roadmap #86` — "ALM r14 corpus redesign (AN11(a) FAIL fallback)".
- Depends-on: `#83` (H100 launch Stage-1 #9 AN11(a) result), `#30` pattern reference.
- Blocks: `#9` re-launch (cannot retry AN11(a) without r14 corpus if FAIL).
- Sister entries: `#63` (multimodal cluster — source for `grounding++`), `#10` (Φ 4-path gate).
- Reaches: P1 re-attempt with new corpus; promotion to Mk.VI VERIFIED still requires AN11(a/b/c) PASS.
- Owner: TBD (likely same lead as #30 cpgd_v2 redesign).

---

_Companion files (planned, not yet created)_: `config/alm_r14_validate.json`,
`config/alm_r14_config.json`, `state/alm_r14_corpus_audit.json`,
`experiments/alm_r14/corpus_alm_r14_v1.jsonl`. **None landed in this skeleton commit.**
