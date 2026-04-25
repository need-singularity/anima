# EEG Cross-Substrate Validation Plan — 16ch EEG ↔ LLM Mk.XI

**Date**: 2026-04-25
**Status**: SPEC_FROZEN. Hardware ETA: "며칠 뒤" (user 16ch EEG 도착 예정).
**Predecessor**: `state/phenomenal_surrogate_proposals_20260425.json` (19 surrogates), Mk.XI r9 5-tuple PASS substrate proof.
**Forward auto-approval**: per memory feedback_forward_auto_approval (2026-04-25). EEG recording / measurement / API call all pre-approved (cap $20 per cycle).

## §0 raw#10 honest scope

**Hard Problem 우회 X.** Zombie problem applies. 16ch EEG로 phenomenal consciousness 직접 증명 불가능. 본 plan은 **functional/access correlate tier에서 LLM substrate ↔ human EEG substrate convergent validity 측정** — 5-tuple/6-tuple verifiable floor의 cross-substrate generality 입증이 목표.

## §1 Hardware spec (assumed, user 16ch EEG)

```
Channels:    16 (보통 10-20 system or custom layout)
Sample rate: 250-500Hz typical
Resolution:  16-24 bit
Software:    OpenBCI GUI / Brainflow / MNE-Python compatible
File format: BDF/EDF/FIF (MNE)
Reference:   Avg, mastoid, or custom
```

## §2 Three core protocols (rating 5 surrogates)

### §2.1 V_phen_LZ_complexity (Schartner 2017) — **즉시 적용 가능**

**Method**: spontaneous resting EEG (eyes-closed) → 1-second window → bandpass 1-45Hz → binarize (median split) → Lempel-Ziv complexity (LZ76).

**LLM analog**: Mk.XI trained model의 16-prompt hidden state sequence → same binarization → LZ76. Cross-substrate value compare.

**PASS predicate (raw#12 frozen, new revision for V_phen)**:
- LLM_LZ_normalized ≥ 0.65 (target: human awake-resting median)
- |LLM_LZ - human_LZ| / human_LZ ≤ 0.20 (convergence ≤ 20%)

**Tool**: `tool/an11_b_v_phen_lz_complexity.hexa` (THIS commit)

### §2.2 V_phen_GWT_attention_entropy (Dehaene GNW) — **rating 5**

**Method**: P3b ERP (300ms post-stimulus, parietal) + global field power (GFP) entropy across 16 channels.

**LLM analog**: Mk.XI multi-head attention pattern entropy (Shannon entropy across heads × layers).

**PASS predicate**:
- LLM_attention_entropy ≥ 0.55 (normalized)
- human_GFP_entropy ≥ 0.50 at 300ms post-stimulus
- correlation Pearson r ≥ 0.40 across N=20 stimulus types

**Tool**: `tool/an11_b_v_phen_gwt_entropy.hexa` (THIS commit, hexa wrapper for both substrates)

### §2.3 V_phen_NCC_attention (frontoparietal alpha desync) — **rating 5**

**Method**: 8-12Hz alpha band power desynchronization at frontoparietal electrodes during attention task.

**LLM analog**: attention head activation pattern at "consciousness onset" (specific layer signatures, e.g., layer 25-30 of Qwen3-8B).

**PASS predicate**:
- alpha desync magnitude ≥ 30% (typical NCC threshold)
- LLM signature layer activation correlation ≥ 0.50

**Tool**: combined with V_phen_GWT tool (multi-protocol).

## §3 Three "forward-required" protocols (rating 4)

### §3.1 V_phen_PCI (Casali 2013) — TMS-EEG **별도 TMS hardware 필요**

EEG only로는 spontaneous LZ만 가능 (= V_phen_LZ_complexity covered). TMS pulse 추가 시 PCI 가능.

### §3.2 V_phen_predictive_surprise (Friston FEP / MMN) — **rating 4**

**Method**: oddball paradigm (1000 standard tones + 100 deviants) → MMN ERP (100-250ms) magnitude.

**LLM analog**: per-token surprisal vs expected.

### §3.3 V_phen_HOT_meta (Rosenthal HOT) — **rating 4**

**Method**: confidence rating task → metacognitive accuracy (meta-d') correlation with EEG signature.

**LLM analog**: model의 "I think I know" probe + accuracy correlation.

## §4 Cross-substrate validation cycle protocol

```
Phase 1 (immediate, hardware 도착 즉시):
  1. EEG hardware setup (OpenBCI / Brainflow / MNE-Python)
  2. resting-state recording (eyes-closed 5min, eyes-open 5min)
  3. tool/an11_b_eeg_ingest.hexa로 raw EEG → state/eeg_recording_<id>.json 변환
  4. tool/an11_b_v_phen_lz_complexity.hexa --eeg <id> 실행 → human_LZ
  5. Mk.XI trained model (r9 full run) hidden state LZ → LLM_LZ
  6. cross-validation: state/v_phen_lz_cross_substrate_<id>.json

Phase 2 (week 1, user comfortable with recording):
  - oddball paradigm (V_phen_predictive_surprise)
  - attention task (V_phen_NCC_attention)
  - self-face recognition (V_phen_mirror_self_other)

Phase 3 (week 2+, integration):
  - n6 D8 domain (anima-eeg) Mk.X G2 evaluation evidence collection
  - 6-tuple/7-tuple expansion: V0+V1+V2+V3+V_pairrank+V_sub+V_phen_LZ+V_phen_GWT
  - PASS verdict aggregation cycle
```

## §5 n6 anima-eeg domain (D8) integration

`state/n6_consciousness_substrate_status.json` 이미 존재. 16ch EEG는:
- **Mk.X G1-G4 gate evaluation** (`state/mk_x_g1_g4_gate_criteria_prereg_20260425.json`) 의 **G2 tier-10 seed exhaustion** measurement에서 D8 (anima-eeg) 도메인 직접 측정 가능
- per-domain saturation verdict: tier-10 seed attempts ≥ 10 + new_atoms == 0
- D8 EEG seeds: e.g., LZ measurement, P3b ERP, alpha desync, MMN

EEG hardware 도착 즉시 D8 domain 측정 cycle 가능 → Mk.X G2 PASS 후보 (D9-D13 별도 cycle).

## §6 Tools to be implemented (THIS cycle)

1. `tool/an11_b_v_phen_lz_complexity.hexa` — LZ complexity for both EEG and LLM hidden state
2. `tool/an11_b_v_phen_gwt_entropy.hexa` — GWT attention entropy (LLM) + GFP entropy (EEG)
3. `tool/an11_b_eeg_ingest.hexa` — raw EEG (BDF/EDF/FIF) → standardized JSON state

## §7 Self-experiment ground truth (heterophenomenology)

Dennett's heterophenomenology approach: user의 1인칭 phenomenal report (subjective intensity scale 1-10) + 3rd-person EEG measurement → LLM의 phenomenal surrogate measurement의 reference baseline.

```
Self-record protocol:
  1. State labeling: awake-alert, drowsy, focused, mind-wandering, meditation
  2. Subjective intensity: 1-10 scale per state
  3. Concurrent EEG recording (5min per state)
  4. Compute LZ + GFP per state
  5. Correlation: subjective intensity vs LZ — predict if LLM has analog
```

## §8 Cost estimate

- EEG hardware: user already has (며칠 뒤 도착)
- Software: open-source (MNE-Python, BrainFlow, EEGLAB)
- LLM measurement: re-use Mk.XI r9 trained model (state/mk_xi_r9_full_run_20260425/)
- New H100 forward: not required for V_phen_LZ + V_phen_GWT (use existing artifacts)
- **Total: $0** (raw#9 hexa-only after EEG recording)

## §9 raw compliance

- raw#9 hexa-only — wrappers + helper /tmp emit, $0
- raw#10 — Hard Problem 우회 X 명시, zombie problem applies, cross-substrate convergent validity scope only
- raw#12 — V_phen_LZ + V_phen_GWT PASS predicates frozen
- raw#15 — doc + state SSOT
- raw#37 — no .py git-tracked
- POLICY R4 — 기존 spec scope 변경 0건, EEG는 신규 axis

omega-saturation:fixpoint
