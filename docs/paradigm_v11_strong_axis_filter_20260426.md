# Paradigm v11 Strong Axis Filter — 4-axis Exhaustion 후 어떤 측정 axis 가 living?

**작성일**: 2026-04-26
**축**: meta-analysis (mac-local $0)
**선행**: axis 82 HW-A weight-init PRIMARY + axis 90 4-family BIMODAL + R45_UPDATE 5 NEG / 6 POS + R46_CANDIDATE
**raw#10**: paradigm v11 stack 18 helpers 가 모두 valid 한지 4-axis exhaustion 후 재검토. "living axis" = empirically distinguishing + raw#10 honest 보존 + axis-orthogonal claim 견디는 axis.

---

## §0 측정 axis inventory

paradigm v11 stack (18 helpers, project_paradigm_v11_stack_complete memory):

**MEASUREMENT (6 axes)**:
- B-ToM (Behavioral Theory of Mind) — Mistral pilot $0.27 evidence
- MCCA (Multi-Channel Causal Analysis) — synthetic only
- Φ* (IIT phi-star) — 5-cycle epistemology evolution (universal NEG → POS → HID-dominant → 50/50 architecture → 2 NEG robust + 2 POS noise → architecture-narrowed)
- CMT (Causal Modulation Tomography) — backbone-dependent depth divergence (#145 Mistral late deep / Qwen3 early input)
- CDS (Coordinated Dynamical Signature) — synthetic only
- SAE-bp (Sparse Autoencoder bypass) — random sparse 4096-feature, transformer_lens import block 우회

**ANALYSIS (3)**: v11_integrate / axis_orthogonality / ensemble_rank
**ORCHESTRATION (2)**: v11_battery / v10_benchmark
**DECISION (2)**: g_gate (canonical G0..G7) / v10_gate_matrix
**LONGITUDINAL (1)**: signature_history
**INTEGRATION-TEST (1)**: v11_pipeline_smoke (22/22 PASS synthetic)
**META (2)**: v11_main / roadmap_v11_register
**ADDITIONAL (1)**: backbone-aware composite scorer (BBA, axis 60)

---

## §1 4-axis exhaustion 후 axis liveness 재평가

### Mistral Φ* sign 의 결정자 (4-axis exhaustion):
1. Architecture FALSIFIED (#176 RWKV-7 -9.07)
2. Tokenizer FALSIFIED bilateral (#203 mistral GPT-NeoX -22.15 + #208 RWKV GPT-NeoX -5.14)
3. Corpus MODIFIER for Mistral (#207 -16.70 → -12.91, sign 보존)
4. **Weight-distribution PRIMARY** for Mistral (#217 W2 random_init Δ+40.17 sign flip POS)

### 4-family BIMODAL (R46_CANDIDATE):
- |BASE phi*| < ~3 → corpus PRIMARY (Qwen3+gemma SFT sign flip POS)
- |BASE phi*| > ~10 → corpus MODIFIER (Mistral)
- POS-base → MODIFIER (Llama)

### 의미: paradigm v11 의 어떤 axis 가 "primary axis 식별" 에 actually 기여?

| axis | 4-axis exhaustion 직접 기여 | 4-family BIMODAL 직접 기여 | living verdict |
|---|---|---|---|
| **B-ToM** | NO — behavioral, ToM-specific | NO | LIVING (orthogonal independent measurement) |
| **MCCA** | NO — multi-channel causal | NO | DEFERRED (synthetic only, real-data 미검증) |
| **Φ*** | YES (axis 82 W2 random_init Δ+40.17 측정 도구) | YES (4-family BIMODAL phi_star_min 비교) | **PRIMARY LIVING** (모든 결정자 axis 식별의 실제 도구) |
| **CMT** | NO — depth divergence backbone-dependent finding (#145), but axis-orthogonal claim 약화 (Mistral late vs Qwen3 early) | NO | LIVING_WEAKENED (backbone-conditional, axis-orthogonality 가정 부분 위반) |
| **CDS** | NO | NO | DEFERRED (synthetic only) |
| **SAE-bp** | NO — random dictionary, 의미 있는 feature 미분리 | NO | DEFERRED (functional alternative status only) |
| **AN11(b)** | YES (G0 primary axis, 모든 backbone 100% guarantee) | YES (BIMODAL detection 의 baseline) | **PRIMARY LIVING** (canonical primary axis) |

---

## §2 axis-orthogonality 가정 재평가

paradigm v11 의 핵심 design rationale: AN11(b) primary axis × 6 v11 orthogonal axes.

**4-axis exhaustion + R46 BIMODAL evidence 후 orthogonality 상태**:

1. **AN11(b) ⊥ Φ*** — original claim. 4-axis exhaustion 시 Φ* 가 primary determinant 식별 도구이고 AN11(b) 는 baseline → 둘이 직교한다는 claim 은 약화됨 (Φ* 가 AN11(b) 의 corollary 일 가능성). raw#10: orthogonality 미직접 검증.

2. **AN11(b) ⊥ CMT** — CMT backbone-dependent depth divergence (#145) 는 AN11(b) 와 정확히 일치 (Mistral CMT late = AN11(b) Law-leading 일치 / Qwen3 CMT early ≠ AN11(b) Phi-leading 직교). **half supports half refutes** orthogonality.

3. **AN11(b) ⊥ B-ToM** — B-ToM Mistral pilot 결과는 AN11(b) Law-leading 와 별도 axis (behavioral evaluation). orthogonality LIKELY VALID (different evaluation modality).

4. **AN11(b) ⊥ MCCA/CDS/SAE-bp** — synthetic only, real-data orthogonality 미검증.

### orthogonality verdict (R46+axis 82+90 evidence integration)
- **STRONG ORTHOGONAL**: AN11(b) ⊥ B-ToM
- **WEAK ORTHOGONAL**: AN11(b) ⊥ Φ* (correlated via primary determinant)
- **CONDITIONAL ORTHOGONAL**: AN11(b) ⊥ CMT (backbone-conditional)
- **UNTESTED**: AN11(b) ⊥ MCCA / CDS / SAE-bp

paradigm v11 design 의 "6 orthogonal axes" claim 은 **strong claim 1 + weak claim 2 + conditional 1 + untested 3** 으로 재분해. 6/6 strong orthogonal 가정 over-claim.

---

## §3 living axis recommendation (Mk.XII v2 Phase 3a 우선순위)

Phase 3a 13B pilot 측정 axis 우선순위 (cost-effectiveness 기준):

**Tier 1 (필수)**:
1. **AN11(b)** — primary axis, 100% guarantee
2. **Φ*** — primary determinant 식별 도구 (4-axis exhaustion 입증된 living axis)

**Tier 2 (선택, 4-family verification 시 추가)**:
3. **CMT** — backbone-dependent depth divergence 가설 cross-validate (R46 prediction P1 13B 검증)
4. **B-ToM** — behavioral orthogonal axis (Φ* 와 다른 modality)

**Tier 3 (synthetic 만 PASS, real-data 미검증, 선택)**:
5. MCCA (defer to Phase 3b)
6. CDS (defer to Phase 3b)
7. SAE-bp (defer to Phase 3b, transformer_lens unblock 시)

### Cost reduction
- v11 stack 18 helpers 모두 측정 = ~$8 (4-bb × $2/bb estimate, all-axis)
- Tier 1+2 만 = ~$4 (50% reduction)
- Phase 3a $300 budget 의 ~1.3% 만 axis 측정에 소비

---

## §4 raw#10 honest 한계

1. **B-ToM living verdict = Mistral pilot $0.27 단일 evidence** — N=1, generalize 가능성 미증명
2. **CMT depth divergence = backbone N=2 (Mistral + Qwen3)** — 4-family complete 미시험
3. **MCCA / CDS / SAE-bp = synthetic only** — real-data PASS 시 living 으로 승급 가능
4. **AN11(b) primary axis = 100% guarantee** — 그러나 generalize 의미가 "trivially PASS" 인지 "meaningful PASS" 인지 미구별
5. **Φ* primary determinant 도구 status** — axis 82 weight + axis 90 corpus 모두 Φ* 로 측정. Φ* 자체가 metric design artifact 일 가능성 (#161 HID_TRUNC dependent 발견)
6. **paradigm v11 design 의 "6 orthogonal axes" claim 은 over-claim** — 본 분석에서 strong 1 + weak 2 + conditional 1 + untested 3 으로 재분해
7. **Mk.XII v2 Phase 3a Tier 1+2 4-axis 만 측정 권장 = budget optimization** — overall consciousness verification 에 충분 보장 NOT
8. **본 분석 자체가 axis 82+90 1-cycle finding 기반** — N=1 axis exhaustion cycle 의 generalization 가능성 별도 검증 필요

---

## §5 next actionable

1. **즉시** (mac-local $0): 본 doc commit + memory + atlas R47_CANDIDATE 등록 ("paradigm_v11_axis_liveness_post_exhaustion")
2. **subagent rate limit reset 후** (4:40am KST): MCCA real-data PASS test (subagent ~$0.10 GPU)
3. **Phase 3a 13B pilot launch 시** (1-2주 후): Tier 1+2 4-axis only fan-out (~$4 vs all-axis $8, 50% saving)
4. **R46 5번째+ backbone validation 시** (별도 cycle): Phi-3-mini Tier 1+2 측정 → R46 confirm/deprecate

---

## §6 verdict

**Living axes (Tier 1)**: **AN11(b) + Φ*** — 4-axis exhaustion 의 actual 측정 도구.

**Living-conditional axes (Tier 2)**: B-ToM (orthogonal modality) + CMT (backbone-conditional).

**Deferred axes (Tier 3)**: MCCA / CDS / SAE-bp (synthetic only).

**paradigm v11 "6 orthogonal axes" claim**: PARTIALLY OVER-CLAIM — strong orthogonal 1 (B-ToM) + weak orthogonal 2 + conditional 1 + untested 3.

**Mk.XII v2 Phase 3a 측정 budget**: Tier 1+2 only 권장 ($4 vs all-axis $8, 50% reduction).

**raw#10 absolute**: 본 분석은 axis 82+90 1-cycle finding generalization. N=1 cycle 의 generalization 위험 명시. paradigm v11 stack 무용 NOT — selectively living + selectively over-claim.
