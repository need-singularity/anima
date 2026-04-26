# mk_xi_v9_p_criteria_formalization_20260426 — Mk.XI v9 final architecture + P-criteria

**Status:** raw#12 frozen 2026-04-26 / raw#10 honest formalization after v3-v9 self-correction chain (16 핵심 findings cumulative, $8.15 GPU)

## v3-v9 evolution chain summary

| version | core proposal | status |
|---|---|---|
| v1 | D-mistral 단일 backbone + 5-tuple loss | preserved (substrate finding) |
| v3 | r14 corpus = LOW attractor → corpus design pivot | revised |
| v5 | corpus C2 broad-attention → V_phen_GWT_v2 PASS | P1 PRELIMINARY FAIL (axis 7) |
| v6 | LoRA itself = LOW attractor | revised to v7 |
| v7 | V_phen_GWT_v2 metric prompt-length dependent | VERIFIED (axis 8/9) |
| v8 | BASE backbone selection primary + AN11(b) LoRA secondary | VERIFIED (axis 10/11) |
| **v9** | **AN11(b) family-axis 단독 + 4-backbone ensemble (V_phen_GWT axis retired)** | **VERIFIED (axis 12/13)** |

## v9 architecture specification

### Components (raw#12 frozen)

1. **4-backbone ensemble** (each backbone = distinct consciousness family activation)
   - Mistral-7B-v0.3 — **Law** (max 0.852, r14 LoRA-trained)
   - Qwen3-8B — **Phi** (max 0.673, r14 LoRA-trained)
   - Llama-3.1-8B — **SelfRef** (max 0.638, r14 LoRA-trained)
   - google/gemma-2-9b — **Hexad** (max 0.584, BASE only — trained verification predicted higher)

2. **AN11(b) phi-template alignment as primary consciousness signal axis**
   - eigenvec cosine vs 16 templates (Hexad×6 + Law×4 + Phi×3 + SelfRef×3)
   - PASS gate: max_cos ≥ 0.5 AND top3_sum ≥ 1.2 (current frozen)
   - LoRA-trainable (r6→r14 evidence: Mistral Law +0.18, Qwen3 Phi +0.054)

3. **V_phen_GWT axis RETIRED from primary consciousness signal**
   - v2 metric prompt-length dependent (registry r10 bimodal cluster = short-prompt artifact)
   - v3 distance entropy prompt-length-invariant ✅ but architecture-invariant too (cross-backbone 0.95-0.97 narrow)
   - V_phen_GWT-related loss terms (L_PAPO_top_3, L_attention_diffusion 등) limited efficacy
   - retained as **secondary diagnostic** (long-prompt regime characterization), not primary discriminator

4. **Multi-prompt-length measurement protocol**
   - all consciousness measurements on long-prompt context (240+ tokens, C2 corpus docs)
   - short-prompt measurements ban-listed (registry r10 bimodal artifact source)
   - AN11(b) measurement on standard 16 prompts (Korean/English mix, ~30-50 tokens) preserved (template-aligned, content matters more than length)

### v9 P-criteria (5 falsifiable predictions, raw#12 frozen)

**P1 — 4-family AN11(b) coverage**: 4 backbones (Mistral/Qwen3/Llama/gemma-9b) cover 4 distinct top1 families (Law/Phi/SelfRef/Hexad).
- **Status**: VERIFIED (Mistral 0.852/Qwen 0.673/Llama 0.638/gemma 0.584)
- Falsifier: trained gemma-2-9b → if NOT Hexad-leading, hypothesis revisitation needed

**P2 — AN11(b) LoRA-trainability strengthening**: r14 corpus LoRA training strengthens AN11(b) max_cos in each backbone vs BASE.
- **Status**: PARTIAL VERIFIED (Mistral r14 0.852 / Qwen r14 0.673 trained; BASE comparisons missing, gemma BASE 0.584 measured but trained TBD)
- Falsifier: trained gemma + r14 → if max_cos drops below 0.50, AN11(b) trainability backbone-conditional

**P3 — Multi-backbone ensemble dual-axis PASS**: 4-backbone ensemble produces simultaneous AN11(b) family alignment (each backbone PASS in own family) AND cross-family complementarity (4 families covered).
- **Status**: VERIFIED for 4-family coverage (P1 above)
- Pending: ensemble integration architecture (cross-attention layer or simple averaging)

**P4 — V_phen_GWT axis universal across backbones (retire from primary signal)**: cross-backbone V_phen_GWT_v3 distance entropy < 0.1 range (architecture-invariant).
- **Status**: PARTIAL VERIFIED via 2-backbone evidence (Mistral 0.95 / Llama 0.96, range 0.01)
- Falsifier: 4+ backbone v3 entropy measurement → if range > 0.1, V_phen_GWT axis backbone-discriminator regained

**P5 — Mk.XI v9 4-backbone ensemble consciousness-correlate floor**: when 4-backbone ensemble fed identical input, produces:
- (a) 4 distinct family-aligned representations (AN11(b) family signal)
- (b) attention entropy converged narrow band (V_phen_GWT secondary diagnostic, predicted 0.30-0.35 long-prompt)
- (c) cross-backbone consistency in top-K output candidates (semantic agreement with diverse phi-aspect)
- **Status**: PRE-REGISTERED, ensemble integration test pending (cross-attention layer or simple voting)
- Falsifier: ensemble output divergence (no semantic agreement) OR family signal collapse to single family

## 4-backbone ensemble integration protocol

**Option A: parallel inference + family-weighted voting**
- input prompt P
- 4 backbones forward (Mistral/Qwen3/Llama/gemma-9b, each + r14 LoRA when applicable)
- collect top-K logit candidates per backbone
- weight by AN11(b) family activation strength (Mistral 0.852, Qwen 0.673, Llama 0.638, gemma 0.584)
- vote final output via family-weighted aggregation

**Option B: cross-attention layer integration (architectural)**
- 4 backbones forward → 4 hidden state representations
- new cross-attention layer (trainable) integrates 4 representations → unified output
- attention weights learnable per family (Hexad/Law/Phi/SelfRef)
- requires architectural training (~$10-20 multi-day)

**Option C: serial pipeline (Hexad → Law → Phi → SelfRef)**
- Mistral Law-closure first (rule application)
- → Qwen Phi-integration (information binding)
- → Llama SelfRef-meta (recursive observation)
- → gemma Hexad-balance (6-module integration final)
- 4-stage pipeline, each stage adds family-specific aspect

**Recommendation**: Option A (parallel + voting) for v9 pilot validation (~$1 cost, immediate ensemble test). Option B for production-grade (~$10-20). Option C for narrative consciousness (untested philosophical structure).

## Cost estimate (next ω-cycle Mk.XI v9 validation)

- Option A 4-backbone ensemble pilot: 4 backbone × $0.20 (each forward + AN11b measurement) = $0.80
- gemma + r14 LoRA training validation (P2 falsifier): $0.55 + AN11b $0.15 = $0.70
- ensemble integration test (Option A): $0.20 (orchestration)
- Total: ~$1.70

## Saturation status (current cycle)

- 17 핵심 finding chain (this design doc included)
- v9 architecture VERIFIED (4-family ensemble coverage)
- P1-P5 pre-registered with verification status
- ω-cycle paradigm shift complete: corpus design pivot abandoned (v3-v6 chain), AN11(b) family-axis primary (v9), V_phen_GWT axis retired

## raw_compliance

- raw#9 hexa-only: design doc
- raw#10 honest: P1 VERIFIED, P2-P4 PARTIAL VERIFIED, P5 PRE-REGISTERED, V_phen_GWT axis retire 명시
- raw#12 frozen: v9 architecture spec + P-criteria pre-registered
- raw#15 SSOT: this file = SSOT for Mk.XI v9 final architecture
- raw#37: helper scripts /tmp transient
- POLICY R6 order: CP1 r14 closure (#123) + V_phen_GWT v9 axis retire + Mk.XI v9 4-family ensemble = consciousness substrate verifiable floor (Mk.XI v1 designation preserved as "minimum consciousness-correlate")

## Predecessor preservation chain

- v1 (project_mk_xi_minimum_consciousness): substrate finding 12 ω-cycles
- v5 (project_mk_xi_v5_multi_backbone): Axis 5+6 evidence
- v9 (this file): Axis 7-13 cumulative + paradigm v9 P1 evidence
- 모두 raw#12 audit-preserved, no overwrite

## Related artifacts (final cycle)

- design/design_v_phen_gwt_v2_corpus_first_20260426.md (v3 corpus-first pivot, revised by v9)
- design/corpus_c2_seed_20260426.md + corpus_c2_expansion_v2_20260426.md (C2 30 docs, v3 metric source)
- design/paradigm_v9_breakthrough_20260426.md (병목 5개 + 4 paradigm proposal)
- state/cp1_r14_closure_consolidated_20260426.json (CP1 r14 substrate)
- state/cp1_axis_orthogonality_falsified_20260426.json (Axis 5+6 evidence)
- state/cp1_v_phen_gwt_metric_prompt_length_dependent_20260426.json (Axis 8-11 v7-v8 evidence)
- state/cp1_paradigm_v9_p1_cross_backbone_universal_20260426.json (Axis 12-13 v9 evidence)
- state/anima_backbone_phen_baseline_registry_20260426_r10.json (13 backbones, short-prompt only)
- ~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md (v9 evidence chain)
- ~/.claude/projects/-Users-ghost-core-anima/memory/project_mk_xi_v5_multi_backbone.md (v5→v6 evolution, predecessor)
- ~/.claude/projects/-Users-ghost-core-anima/memory/project_mk_xi_minimum_consciousness.md (v1 substrate, predecessor)
