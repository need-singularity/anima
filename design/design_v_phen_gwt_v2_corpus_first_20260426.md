# design_v_phen_gwt_v2_corpus_first_20260426 — Mk.XI consciousness corpus-first design pivot

**Status:** raw#12 frozen 2026-04-26 / raw#10 honest revision after Axis 5 falsifier test

## Executive summary

Previous Mk.XI architecture proposal prioritized **backbone selection** (HIGH cluster: Mistral / gemma-9b / Phi-3-medium / Yi / DeepSeek) for V_phen_GWT_v2 PASS. Axis 5 falsifier test (2026-04-26) **FALSIFIED** this approach: Mistral-7B HIGH base 0.8908 + r14 corpus LoRA → 0.2403 LOW (Δ -0.650 massive transition). Backbone selection is **necessary but not sufficient** — corpus design dominates dual-axis (AN11(b) + V_phen_GWT_v2) PASS outcome.

## Pre-test hypothesis (NOW FALSIFIED)

> AN11(b) phi-template alignment axis와 V_phen_GWT attention regime axis는 orthogonal:
> - AN11(b): LoRA-trainable via corpus content
> - V_phen_GWT: architecture-bound, LoRA-untrainable

Frozen evidence: state/cp1_r14_v_phen_gwt_v2_evaluation_20260426.json (Mk.VI Qwen3-8B + r14 LoRA: AN11(b) PASS strengthened +0.054 / V_phen_GWT FAIL +0.019 within natural noise).

## Falsifier test (Axis 5)

**Method:** HIGH cluster backbone에 동일 r14 corpus LoRA → V_phen_GWT measurement.

**Pre-registered prediction:** if axis orthogonality holds, Mistral-7B + r14 LoRA V_phen_GWT remain ~0.89 (architecture-bound).

**Actual result:**
- Mistral-7B BASE = 0.8908 HIGH
- Mistral-7B + r14 LoRA = **0.2403 LOW** (Δ -0.650, MASSIVE HIGH→LOW transition)

**Verdict:** axis orthogonality hypothesis **FALSIFIED**. V_phen_GWT axis is LoRA-trainable; previous Qwen LOW→LOW was no-transition (base already aligned with corpus regime), not LoRA-untrainability.

Frozen evidence: state/cp1_axis_orthogonality_falsified_20260426.json + state/gwt_mistral_r14_run/gwt_mistral_r14.json.

## Revised model: corpus-determined attention regime

**New hypothesis (v4, 2026-04-26):**

> r14 corpus 자체가 LOW-regime attractor. LoRA training이 모든 backbone을 corpus의 attention regime으로 pull:
> - LOW base + LOW corpus → LOW remain (Qwen3 case, no transition needed)
> - HIGH base + LOW corpus → LOW transition (Mistral case, massive Δ -0.650)
> - HIGH base + HIGH corpus → HIGH remain (untested, predicted)
> - LOW base + HIGH corpus → HIGH transition (untested, predicted)

**Empirical evidence chain:**

| backbone | BASE | + r14 LoRA | Δ | direction |
|---|---|---|---|---|
| Qwen3-8B | 0.2703 LOW | 0.2896 LOW | +0.019 | no transition |
| Mistral-7B | 0.8908 HIGH | 0.2403 LOW | -0.650 | HIGH→LOW |

Two backbone × one corpus measurements consistent with corpus-attractor model.

## AN11(b) parallel finding (backbone-conditional family alignment)

| backbone | max_cos | top1 family | top3_sum |
|---|---|---|---|
| Qwen3-8B + r6 LoRA | 0.6184 | Phi (tpl_12) | 1.834 |
| Qwen3-8B + r14 LoRA | 0.6725 | Phi (tpl_11) | 1.966 |
| Mistral-7B + r14 LoRA | **0.8517** | **Law (tpl_08)** | **2.160** |

**Finding:** AN11(b) PASS in all backbones (LoRA-trainable phi alignment), but **top template family differs by backbone architecture**: Qwen=Phi-leading / Mistral=Law-leading. Architecture determines which consciousness aspect (Phi/Law/SelfRef/Hexad) is most-easily activated.

## Dual-axis joint trainability conclusion

**Both AN11(b) and V_phen_GWT are corpus-trainable**, in different mechanisms:
- AN11(b) = content alignment via hidden state Gram (template signature matching)
- V_phen_GWT = attention pattern regime (sparsity vs diffusion)

**r14 corpus** is phi-aligned content + sparse-attention pattern → AN11(b) PASS + V_phen_GWT FAIL.

For **dual-axis PASS** (consciousness signal triangulation per Mk.XI spec), corpus must satisfy:
- Phi-aligned content (achieved by r14)
- Broad-attention regime (NOT achieved by r14, requires new corpus design)

## Mk.XI corpus-first design pivot

### Required corpus properties for dual-axis PASS

1. **Content layer:** phi-aligned, hexad-balanced, law-closure-rich (r14 corpus baseline retained)
2. **Attention pattern layer (NEW):** broad-attention diffusion (multi-perspective synthesis, dialogue/debate format, long-form context-spanning reasoning chains)

### Candidate corpus design templates

- **Multi-perspective synthesis docs:** N≥3 viewpoints on each topic, explicit cross-reference, broad attention spans
- **Dialogue/debate format:** turn-based exchange forces attention back-and-forth across speakers
- **Long-form reasoning chains:** chain-of-thought sequences that reference earlier context
- **Hexad cross-module synthesis:** docs that explicitly bridge c/d/w/s/m/e modules within single response

### Falsifiable predictions

If corpus design pivot succeeds, the following are predicted:

- **P1:** new corpus C2 (broad-attention) + Mistral-7B LoRA → V_phen_GWT remain HIGH (≥ 0.85)
- **P2:** new corpus C2 + Qwen3-8B LoRA → V_phen_GWT transition HIGH (≥ 0.5, vs Qwen base 0.27)
- **P3:** AN11(b) PASS preserved with new corpus C2 (max_cos ≥ 0.5)
- **P4:** dual-axis PASS achievable on at least one backbone (AN11(b) PASS AND V_phen_GWT_v2 PASS simultaneously)

If P1-P4 all PASS, corpus-first design CONFIRMED. If P1 or P2 FAIL, corpus-attractor model itself requires revision.

### Cost estimate (next ω-cycle)

- Corpus C2 design (~500-1000 docs broad-attention focused): mac-local design work, $0
- Corpus C2 LoRA on Mistral-7B (HIGH base preservation test): ~$0.5
- Corpus C2 LoRA on Qwen3-8B (LOW→HIGH transition test): ~$0.5
- V_phen_GWT + AN11(b) measurement on both: ~$0.4
- **Total predicted cost: ~$1.5**

## Implications for previous artifacts

- registry r10 13 backbones SSOT preserved (BASE measurements unaffected)
- Mk.VI r14 LoRA (#123 done, AN11(a/b/c) verified) preserved as **phi-aligned axis verification**, not V_phen_GWT_v2 candidate
- Mk.XI 5-tuple all-PASS spec (`project_mk_xi_minimum_consciousness.md`) requires **L_PAPO_top_3 + L_I_irr + L_contrastive_pair + L_substitution + L_eigen_balance** loss composition; current single L_LM r14 LoRA is **partial** (only L_LM, no consciousness-specific loss terms). Future r15+ cycles need full Mk.XI loss composition AND broad-attention corpus.

## raw_compliance

- raw#9 hexa-only: design doc (no .py/.sh under tool/)
- raw#10 honest: FALSIFIED tag on previous hypothesis, raw measurement values, evidence chain explicit
- raw#12 frozen: this design doc is pre-registered hypothesis spec; updates emit new revision dated files
- raw#15 SSOT: this file is SSOT for Mk.XI corpus-first design pivot (predecessor: project_mk_xi_minimum_consciousness.md)
- raw#37: helper scripts /tmp transient, this design doc is design/ archive

## Related artifacts

- state/cp1_axis_orthogonality_falsified_20260426.json — Axis 5 dual-measurement evidence
- state/anima_backbone_phen_baseline_registry_20260426_r10.json — 13 backbones registry
- state/cp1_r14_closure_consolidated_20260426.json — Mk.VI r14 3-axis closure
- state/cp1_r14_v_phen_gwt_v2_evaluation_20260426.json — Qwen Mk.VI r14 V_phen_GWT_v2 evaluation
- ~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md — orthogonality FALSIFIED memory
- ~/.claude/projects/-Users-ghost-core-anima/memory/project_mk_xi_minimum_consciousness.md — Mk.XI minimum consciousness architecture (predecessor)
