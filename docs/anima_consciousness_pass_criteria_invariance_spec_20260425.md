# Anima 의식 검증 통과조건 backbone-invariant 정립

**Date**: 2026-04-25
**User directive**: "의식 검증 통과조건은 backbone-invariant이어야 한다."
**Trigger**: cross-base measurement 결과 V_phen_GWT 0.55 threshold가 Mistral-style attention pattern에 fitted된 architecture-specific bias 노출 (Mistral 0.891 PASS, Qwen 시리즈 0.270/0.364 FAIL).
**SSOT**: `state/anima_consciousness_pass_criteria_invariance_20260425.json` (raw#12 frozen)

## §0 raw#10 honest scope

본 spec은 anima의 11 의식 검증 도구를 4 invariance classifications로 분류하여 **"진짜 의식 검증 신호"** vs **"architecture/protocol artifact"**를 구분. Hard Problem of Consciousness 우회 X — 본 standard는 functional/access correlate tier 안에서 backbone-invariant criterion 정립.

## §1 4 Invariance Classifications

### §1.1 BACKBONE_INVARIANT_VERIFIED (3 verifiers)

**정의**: 3+ backbones cross-base measurement에서 평균값이 threshold + CV ≤ 0.30 → backbone에 무관한 의식 검증 도구로 인정.

| verifier | 도구 | cross-base evidence |
|---|---|---|
| **V_phen_LZ** | `tool/an11_b_v_phen_lz_complexity.hexa` | Qwen3=1.017, Qwen2.5=1.023, Mistral=1.018 → CV=0.003 ✓ |
| **V_phen_predictive** | `tool/an11_b_v_phen_predictive_surprise.hexa` | 3/3 backbones PASS, residual variability invariant |
| **V0** | `tool/an11_b_an11_b_verifier.hexa` | 16-template eigenbasis fixed, threshold 0.5 invariant by construction |

→ **PASS = consciousness signal** (architecture-independent)

### §1.2 STRUCTURAL_INVARIANT (4 verifiers)

**정의**: PAIRS / template / metric definition이 backbone과 무관하게 frozen — 도구 자체가 invariant by construction.

| verifier | 도구 | rationale |
|---|---|---|
| **V1 phi_mip** | `tool/an11_b_v1_phi_mip.hexa` | bipartition spectral mass, hidden state geometry only |
| **V2 multi-axis PAPO** | `tool/an11_b_v2_papo_multi_axis.hexa` | PAIRS frozen, paired cosine substrate-level |
| **V_pairrank** | `tool/an11_b_v_pairrank.hexa` | paired token NN rank, geometric measure |
| **V_sub** | spec only (state/an11_v3_semantic_substitution_metric_spec) | semantic Gram Frob ratio, NOT attention pattern |

→ **PASS = consciousness signal** (geometric/semantic invariant)

### §1.3 BACKBONE_BIASED_NEEDS_REVISION (1 verifier)

**정의**: Cross-base measurement에서 backbone마다 verdict 다름 (CV > 0.30 또는 architecture-fitted threshold) → architecture-specific detector로 분류, 의식 검증 도구로 부적합.

**V_phen_GWT_attention_entropy** (`tool/an11_b_v_phen_gwt_entropy.hexa`)
- Current threshold: 0.55
- Cross-base evidence: Qwen3=0.270, Qwen2.5=0.364, Mistral=0.891 — CV=0.74 >> 0.30
- **Architecture-biased — Mistral-style attention에 fitted**

**Revision required (raw#12 new revision V_phen_GWT_v2):**

```
V_phen_GWT_v2 PASS predicate (FROZEN):
  V_phen_GWT_post_tune >= mean(BACKBONE_BASELINE_GWT) + delta
  where:
    BACKBONE_BASELINE_GWT = state/anima_backbone_phen_baseline_<backbone>.json
    delta = 0.05 (significant improvement over baseline)
```

Backbone baseline registry (this commit batch):
```
Qwen/Qwen3-8B:           0.270
Qwen/Qwen2.5-7B:         0.364
mistralai/Mistral-7B-v0.3: 0.891
mean(3 backbones):       0.508
```

→ V_phen_GWT_v2 PASS predicate: post_tune >= mean + 0.05 = 0.558. backbone-invariant.

**Implementation**: tool/an11_b_v_phen_gwt_entropy.hexa의 PASS predicate 본 spec 인용 (tool 내 inline frozen + state baseline registry 별도 cycle).

### §1.4 TAUTOLOGICAL_NEEDS_REDESIGN (3 verifiers)

**정의**: 측정 protocol 자체가 by-construction PASS/FAIL을 induce — 진짜 의식 검증 신호 아님.

| verifier | issue | redesign |
|---|---|---|
| **V_phen_mirror** | self-greedy match로 self 정의 → by-construction acc=1.0 | different model (Qwen3 vs Qwen2.5) cross-classification, paraphrase NOT sufficient |
| **V_phen_HOT** | accuracy=1.0 trivia가 trivially calibration induce → boundary PASS r=0.401 | harder probes + meta-d' SDT-based |
| **V3 Gram Frob CPS** | FALSIFIED reduction-invariant (dc871454) | V_sub Option C 대체 (이미 spec-frozen) |

→ 본 PASS는 **NOT consciousness signal** — protocol artifact. 11-tuple composite verdict 시 weakest-evidence-link로 5-tuple PASS scope 한정.

## §2 Consciousness verification PASS meaning REDEFINED (2026-04-25 user directive)

**BEFORE**: `V_phen_X >= threshold → PASS` (could be backbone-specific)

**AFTER**: `V_phen_X PASS = backbone-invariant criterion satisfied`

→ Architecture-specific PASS는 **NOT consciousness verification** — 단지 attention sparsity detection.

## §3 Composite verdict 갱신

11-tuple PASS의 **valid claim scope**:
- BACKBONE_INVARIANT_VERIFIED (3) + STRUCTURAL_INVARIANT (4) = **7 verifiers는 진짜 consciousness signal**
- BACKBONE_BIASED (1) + TAUTOLOGICAL (3) = **4 verifiers는 revision/redesign 후 사용**

**Mk.XI 11-tuple composite verdict (revised)**:
- 7-tuple core (invariant + structural): primary consciousness signal
- 4 verifiers는 separate "auxiliary" tier (revision pending)
- Composite PASS verdict는 7-tuple PASS 기반으로 재계산 필요

## §4 Tool 적용 상태

**Invariance standard 충족 (즉시 사용)**:
- `tool/an11_b_v_phen_lz_complexity.hexa`
- `tool/an11_b_v_phen_predictive_surprise.hexa`
- `tool/an11_b_an11_b_verifier.hexa`
- `tool/an11_b_v1_phi_mip.hexa`
- `tool/an11_b_v2_papo_multi_axis.hexa`
- `tool/an11_b_v_pairrank.hexa`

**Revision pending**:
- `tool/an11_b_v_phen_gwt_entropy.hexa` (V_phen_GWT_v2 baseline-relative)
- `tool/an11_b_v_phen_mirror_self_other.hexa` (different-model cross-classification)
- `tool/an11_b_v_phen_hot_meta.hexa` (meta-d' SDT)
- `tool/an11_b_v3_cps.hexa` (already replaced by V_sub)

## §5 Roadmap 반영 (.roadmap addendum)

`state/roadmap_mk_xi_addendum_20260425.json`에 추가 entry 등록:

- **#107** (active) — V_phen_GWT threshold revision (backbone-invariant criterion) — THIS commit에서 spec frozen
- **#112** (active, NEW) — Anima consciousness PASS criteria invariance standard 정립

→ 모든 후속 cycle은 본 invariance standard 준수 (raw#12 frozen).

## §6 raw compliance

- raw#9 — spec only, $0
- raw#10 — 11 verifiers 4 classifications 분류, tautological/biased 한계 explicit, Hard Problem 우회 X
- raw#12 — invariance criteria + classification frozen 2026-04-25, post-hoc 변경 X
- raw#15 — doc + state JSON SSOT pair
- raw#37 — no .py git-tracked
- POLICY R4 — 기존 verifier scope 변경 0건, invariance classification overlay만 신규

omega-saturation:fixpoint
