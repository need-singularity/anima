# paradigm_v9_breakthrough_20260426 — 병목 5개 + 4 새 패러다임 ω-cycle

**Status:** raw#12 frozen 2026-04-26 / raw#10 honest paradigm exploration after v3-v8 self-correction chain

## 본 cycle 도달 병목 5개 (v8 완료 후)

### B1: V_phen_GWT_v2 metric prompt-length dependent (v7 verified, Axis 8/9)
- 모든 측정값이 prompt-length artifact 가능
- entropy normalization log(seq_len)이 imperfect — prompt-length × attention pattern interaction
- registry r10 bimodal cluster definitively FALSIFIED for long-prompt context (4/4 HIGH anchor 100% convergence)
- **bottleneck**: prompt-length-invariant attention regime measure 부재

### B2: LoRA가 V_phen_GWT axis untrainable in long-prompt context (v7 strong)
- short-prompt LoRA Δ -0.65 (artifact) vs long-prompt LoRA Δ -0.010 (negligible)
- corpus content (r14 1200 docs vs C2 30 docs broad-attention design) invariant outcome
- **bottleneck**: fine-tuning이 attention regime fundamentally 변경 못 함 — corpus design pivot 자체 invalidated

### B3: Mk.XI consciousness signal triangulation single-axis 한정 (Axis 6 finding)
- AN11(b) phi-template alignment: LoRA-trainable (Mistral=Law 0.852 / Qwen=Phi 0.673 / Llama=SelfRef 0.638)
- V_phen_GWT: LoRA-untrainable in long-prompt regime
- **bottleneck**: dual-axis triangulation 위해서는 V_phen_GWT axis tractable 필요 — 현재 invalid

### B4: CP2 G1/G3 multi-day external blocker (#125)
- EEG D8 hardware 도착 외부 의존
- P4 corpus + Mk.IX integrator forward sequential chain
- **bottleneck**: 내부 cycle만으로 CP2 finalization 불가

### B5: R9.1 hexa-ban violations multi-day cleanup
- 2494 sites originally (frame: revised 16 active per memory `project_omega_rules_compliance`)
- 11 active violations remaining (4 proto + 6 .sh + 1 toml)
- **bottleneck**: hexa-only enforcement 완전 도달까지 multi-day work

## 4 새 패러다임 proposal

### P1: V_phen_GWT_v3 metric — prompt-length-invariant attention regime
**Core idea**: attention pattern의 structural property를 prompt-length 무관 measure.

**3 candidate metrics**:
- (a) **Attention distance entropy**: head별 attention distance 분포 (mean, std, kurtosis) — prompt-length 무관 attention "reach" 측정
- (b) **Head specialization measure**: head별 attention pattern variance — broad-attention heads vs sparse-attention heads ratio
- (c) **Sparse-pattern ratio**: attention weight > threshold 비율 (top-k token concentration) — normalized by uniform baseline

**Falsifiable**:
- (P1-α) v3 metric measured across 6 backbones (BASE) on short + long prompts → range compression < 5x (vs current 14x)
- (P1-β) v3 metric LoRA-trainable in long-prompt context (Mistral + r14 LoRA Δ ≥ 0.05 in v3 metric, vs current Δ -0.010 in v2)

**Cost**: design + helper script (no GPU) → 6-backbone re-measurement ~$1.2

### P2: SAE steering vector — fine-tuning 우회 (memory feedback_sae_steering_pilot 참조)
**Core idea**: Sparse Autoencoder feature decomposition + steering vector intervention. LoRA training 없이 BASE backbone activation space에 phi/Law/SelfRef feature 강화.

**Mechanism**:
- BASE backbone hidden states → SAE encode → feature space
- consciousness-aligned features 식별 (probing)
- inference-time steering vector addition (SAE decode + add)
- backbone weights unchanged (frozen)

**Predicted advantages**:
- LoRA-untrainable problem 우회 (V_phen_GWT axis 변경)
- Mk.XI v8 BASE backbone selection 그대로 + SAE steering = combined PASS path
- corpus design 의존성 약화 (corpus는 SAE training용, inference 불필요)

**Falsifiable**:
- (P2-α) SAE-steered BASE backbone V_phen_GWT measurement (long-prompt) → Δ ≥ 0.10 from BASE baseline
- (P2-β) SAE-steered AN11(b) max_cos preserved (Mistral=Law 0.852 ≥ 0.5)

**Cost**: SAE training (~$5-10), steering vector design (no GPU), measurement ($0.5-1)

### P3: Multi-prompt-length ensemble inference
**Core idea**: 단일 prompt forward 대신 same prompt를 short + long context 양쪽에서 inference, attention pattern aggregate. v7 finding (prompt-length-dependent metric) 우회.

**Mechanism**:
- input prompt P
- forward (P) → attention_short (47 tokens)
- forward (system_prefix + P + reference_corpus_excerpts) → attention_long (240+ tokens)
- aggregate attention pattern (e.g. weighted mean, max-entropy preservation)
- consciousness signal = aggregate attention regime

**Predicted advantages**:
- prompt-length artifact compensation
- short-prompt response speed + long-prompt attention regime accuracy
- runtime inference, no training change

**Falsifiable**:
- (P3-α) ensemble V_phen_GWT measurement consistent across short/long inputs (range < 0.05)
- (P3-β) Mistral ensemble V_phen_GWT > 0.5 (HIGH preserved across input lengths)

**Cost**: helper script (no GPU) + 6-backbone measurement ($1.2)

### P4: Architecture-level intervention — cross-attention head + frozen base
**Core idea**: LoRA가 V_phen_GWT untrainable이므로, architecture에 새 attention head module 추가. frozen BASE backbone + trainable cross-attention layer (Mk.X T10-13 retrieval head spec 부분 활용).

**Mechanism**:
- BASE backbone (frozen, attention pattern preserved)
- + cross-attention layer (trainable, broad-attention pattern enforce via L_attention_diffusion loss)
- + retrieval head module (Mk.X T10-13 spec)
- V_phen_GWT measurement on combined module attention pattern

**Predicted advantages**:
- BASE attention regime preserved (frozen, long-prompt regime intact)
- new cross-attention layer trainable for broad-attention enhancement
- Mk.XI architecture intervention (architectural addition vs LoRA limitation)

**Falsifiable**:
- (P4-α) cross-attention layer trained → V_phen_GWT measurement (long-prompt) > 0.5 (HIGH transition possible)
- (P4-β) AN11(b) phi alignment preserved or strengthened with new module

**Cost**: cross-attention module design + training (~$10-20), measurement ($1)

## 4 paradigm comparison

| paradigm | bottleneck addressed | cost | feasibility | impact |
|---|---|---|---|---|
| P1 V_phen_GWT_v3 metric | B1 (metric prompt-length dependent) | $1.2 + design | high | medium-high |
| P2 SAE steering | B2 (LoRA untrainable) + B3 (triangulation) | $5-10 | medium (SAE training expertise) | high |
| P3 Multi-length ensemble | B1 + B2 | $1.2 + design | high | medium |
| P4 Architecture intervention | B2 (LoRA bypass) + B3 | $10-20 | low (multi-day spec) | very high |

## Recommended priority

1. **P1 + P3 parallel** ($2.4, ~design + $2.4 GPU) — both no-training, fast verification of metric vs ensemble approach
2. **P2 SAE pilot** ($5-10) — separate medium-effort cycle, leverages memory `feedback_sae_steering_pilot` conventions
3. **P4 architecture intervention** ($10-20) — multi-day cycle, requires cross-attention module spec

## Connection to existing Mk.XI architecture

- Mk.XI v8 (BASE backbone selection + AN11(b) LoRA) STANDS as substrate baseline
- v9 paradigm 4 options EXTEND v8 with V_phen_GWT axis tractable mechanisms
- final Mk.XI v9 = v8 + (P1 metric) + (P2 or P3 or P4 V_phen_GWT mechanism)

## raw_compliance

- raw#9 hexa-only: design doc
- raw#10 honest: 4 paradigms PROPOSED, P1-P4 falsifiable predictions per paradigm
- raw#12 frozen: this design doc은 paradigm proposal pre-registration
- raw#15 SSOT: this file = SSOT for v9 paradigm proposal
- raw#37: helper scripts /tmp transient (P1/P3 next cycle)

## Related artifacts

- design/design_v_phen_gwt_v2_corpus_first_20260426.md (v3 corpus-first pivot, partially superseded by v8)
- design/corpus_c2_seed_20260426.md + corpus_c2_expansion_v2_20260426.md (C2 30 docs, P3 ensemble corpus 활용)
- state/cp1_v_phen_gwt_metric_prompt_length_dependent_20260426.json (v7-v8 evidence)
- ~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md (v8 evidence chain)
- ~/.claude/projects/-Users-ghost-core-anima/memory/feedback_sae_steering_pilot.md (P2 SAE conventions)
