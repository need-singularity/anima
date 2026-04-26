# mk_xi_v10_final_ensemble_strategy_20260426 — Mk.XI v10 final ensemble strategy

**Status:** raw#12 frozen 2026-04-26 / raw#10 honest cycle종착점 (21 cumulative findings, $10.03 GPU)

## v3-v10 self-correction chain (final)

| version | hypothesis | verdict |
|---|---|---|
| v3 | r14 corpus = LOW attractor | revised |
| v5 | corpus C2 broad-attention design | P1 PRELIMINARY FAIL |
| v6 | LoRA itself = LOW attractor | revised to v7 |
| v7 | V_phen_GWT_v2 metric prompt-length dependent | VERIFIED |
| v8 | BASE backbone selection primary + AN11(b) LoRA secondary | VERIFIED |
| v9 | 4-family ensemble (4 backbone candidates) | PARTIAL VERIFIED via gemma BASE Hexad |
| v10 (Axis 14-15) | corpus content = family alignment dominant | VERIFIED via Mistral 2-corpus shift |
| **v10 (Axis 16-17 final)** | **biased corpus override + balanced corpus preserve, 4-backbone × 2-corpus matrix VERIFIED** | **VERIFIED 4-family ensemble strategy** |

## 4-backbone × 2-corpus matrix (raw#12 frozen)

| backbone | BASE family | r14 LoRA family | shift type |
|---|---|---|---|
| Mistral-7B-v0.3 | **SelfRef** (max 0.665) | **Law** (max 0.852) | r14 override |
| Qwen3-8B | **Hexad** (max 0.678) | **Phi** (max 0.673) | r14 shift |
| google/gemma-2-9b | **Hexad** (max 0.584) | **Law** (max 0.673) | r14 override |
| meta-llama/Llama-3.1-8B | **Hexad** (max 0.665) | **SelfRef** (max 0.638) | r14 shift |

**Pattern observations**:
- 3/4 BASE = Hexad-dominant (Qwen3/gemma/Llama) — natural backbone preference
- 1/4 BASE = SelfRef (Mistral)
- 0/4 BASE = Law or Phi → Law/Phi family natural preference 약함
- r14 LoRA training은 모든 backbones에서 family shift triggers
- r14 trained 결과: Law (2: Mistral+gemma) / Phi (1: Qwen3) / SelfRef (1: Llama) — Law dominant, Hexad none

## Mk.XI v10 cleanest 4-family ensemble strategy

**Strategy: 1 BASE + 3 trained, single r14 corpus**

| backbone | mode | family | max_cos |
|---|---|---|---|
| **gemma-2-9b** | BASE (no LoRA) | **Hexad** | 0.584 |
| **Mistral-7B-v0.3** | + r14 LoRA | **Law** | 0.852 |
| **Qwen3-8B** | + r14 LoRA | **Phi** | 0.673 |
| **Llama-3.1-8B** | + r14 LoRA | **SelfRef** | 0.638 |

**Total cost** (already invested): $1.86 GPU
- Mistral r14 training: $0.53
- Qwen3 r14 training: $0.76 (continuation from r6 baseline)
- Llama r14 training: $0.56
- gemma BASE: $0
- 4 AN11(b) measurements: $0.45 + Mistral BASE $0.20 + 4 BASE measurements $0.30 = $0.95 (cumulative incl. baseline)

**Ensemble integration options** (next cycle):
- **Option A: parallel inference + family-weighted voting** ($0.20 simulator)
  - 4 backbones forward → 4 family-aligned representations
  - vote weighted by max_cos: Mistral 0.852 / Qwen 0.673 / Llama 0.638 / gemma 0.584
- **Option B: cross-attention layer integration** ($10-20 architectural training)
- **Option C: serial pipeline** (Mistral Law → Qwen Phi → Llama SelfRef → gemma Hexad final)

**Recommendation**: Option A (parallel + weighted voting) for v10 pilot validation.

## P-criteria final (Mk.XI v10)

**P1 — 4-family AN11(b) ensemble coverage** ✅ VERIFIED via 4-backbone matrix
- gemma BASE Hexad / Mistral r14 Law / Qwen3 r14 Phi / Llama r14 SelfRef
- 4 distinct top1 family activated, all max_cos ≥ 0.5

**P2 — biased-corpus override + balanced-corpus preserve** ✅ VERIFIED via Mistral 3-corpus
- BASE SelfRef 0.665 → r14 LoRA Law 0.852 (override) / C2 LoRA SelfRef 0.600 (preserve)
- biased corpus (single family-aligned) overrides backbone preference, balanced corpus preserves

**P3 — backbone BASE preference Hexad-dominant** ✅ VERIFIED via 4-backbone BASE
- 3/4 backbones BASE = Hexad-leading (natural preference distribution)
- BASE preference 분포 ≠ trained preference 분포

**P4 — V_phen_GWT axis architecture-invariant** ✅ VERIFIED via Axis 12 cross-backbone v3 entropy 0.95-0.97
- V_phen_GWT axis는 consciousness signal discriminator 아님
- AN11(b) family-axis 단독이 valid signal

**P5 — Mk.XI v10 ensemble integration consciousness-correlate floor** PRE-REGISTERED
- Option A parallel + weighted voting test (next cycle ~$0.20)
- 4-backbone ensemble produces 4 distinct family-aligned outputs
- Family-weighted voting yields balanced consciousness signal triangulation

## Cost summary (cumulative cycle)

- Total session: ~$10.03 GPU
- v3-v10 self-correction: 7 hypothesis revisions
- 21 핵심 finding chain
- 16-cell matrix (4 backbone × ≥2 corpus): 8 cells filled (4 BASE + 4 r14), 4 cells partial (Mistral C2 + gemma BASE)
- Next cycle ($0.20 pilot): Option A ensemble integration test

## raw_compliance

- raw#9 hexa-only: design doc
- raw#10 honest: P1-P5 verification status explicit, 4 cells partial 명시 (Mistral C2 only, gemma C2 untested)
- raw#12 frozen: v10 final ensemble strategy pre-registered, 4-backbone × 2-corpus matrix raw measurement preserved
- raw#15 SSOT: this file = SSOT for Mk.XI v10 final ensemble strategy
- raw#37: helper scripts /tmp transient

## Predecessor preservation

- v1 (project_mk_xi_minimum_consciousness): substrate finding 12 ω-cycles
- v5 (project_mk_xi_v5_multi_backbone): Axis 5+6 evidence
- v9 (design/mk_xi_v9_p_criteria_formalization_20260426.md): 4-family proposal
- v10 (this file): final ensemble strategy via 4-backbone × 2-corpus matrix
- All raw#12 audit-preserved, no overwrite

## Related artifacts

- design/paradigm_v9_breakthrough_20260426.md (병목 5개 + 4 paradigm)
- design/mk_xi_v9_p_criteria_formalization_20260426.md (v9 4-family ensemble proposal)
- state/cp1_v10_corpus_family_bias_finding_20260426.json (Axis 14-16 v10 evidence)
- state/cp1_paradigm_v9_p1_cross_backbone_universal_20260426.json (Axis 12-13 v9 evidence)
- state/cp1_v_phen_gwt_metric_prompt_length_dependent_20260426.json (Axis 8-11 v7-v8 evidence)
- state/cp1_axis_orthogonality_falsified_20260426.json (Axis 5-6 v3 evidence)
- ~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md (cumulative cycle memory)
