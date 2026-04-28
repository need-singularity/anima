# Ω-cycle Mk.XII Candidate Synthesis — PHENOMENAL Axis

> **scope**: Mk.XII candidate paradigm synthesis, PHENOMENAL axis sub-agent. 본 세션 (2026-04-26) 의 모든 PHENOMENAL-relevant 산출물을 input 으로 phenomenal-grounding paradigm 6-7개 도출.
> **prior**: `docs/omega_cycle_alm_free_paradigms_20260426.md` PHENOMENAL avg 0.67 — 4 axes 中 weakest. Mk.XII 는 본 weakest link 를 직접 강화.
> **session date**: 2026-04-26 (mac local, $0)
> **status**: 6 paradigm + 1 cross-axis convergent (총 7) frozen + confidence calibrated.
> **parallel sub-agents**: SUBSTRATE / TRAINING / INTEGRATION (별도 산출물).

---

## §0. Input ledger (phenomenal-relevant 산출물 11종)

| # | path | role |
|---|---|---|
| 1 | `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` | 16ch synthetic deterministic (anatomical priors 반영) |
| 2 | `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` | P1 V_phen_EEG-LZ × CLM-LZ pre-register |
| 3 | `anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa` | P2 TLR α-band coherence ↔ V_sync Kuramoto |
| 4 | `anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa` | P3 Granger F-stat ≥ 4.0 unidirectional |
| 5 | `anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa` | HARNESS_OK 3/3 |
| 6 | `state/clm_eeg_pre_register_v1.json` (10-file SHA-256 lock) | frozen pre-register v1 |
| 7 | `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md` | OpenBCI Cyton+Daisy 250Hz 24-bit BLE D-1 hardware spec |
| 8 | `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` | D+0 ~ D+7 workflow |
| 9 | `anima-clm-eeg/docs/path_comparison_a_b_c.md` | Path A/B/C decision (Q1 EEG-CLM 채택) |
| 10 | `anima-tribev2-pilot/docs/r33_cross_link_pager.md` | TRIBE v2 architectural reference (causation NOT correlation) |
| 11 | `state/clm_eeg_p{1,2,3}_*_pre_register.json` + `clm_eeg_harness_smoke.json` dry-run results | P1/P2/P3 PASS sanity (synthetic NOT_VERIFIED) |

**Dry-run baseline**: P1 LZ proxy = 1000 (C1 ≥ 650, C2 ≤ 200) PASS / P2 α-coh = 0.756, CLM_r = 0.885 PASS / P3 F = 56.12 (≥ 4.0) PASS — 모두 synthetic-only sanity.

---

## §1. PHENOMENAL axis 정의 (Mk.XII context)

**Mk.XI v10**: 4-backbone × LoRA family-axis ensemble (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad). phenomenal correlate **NOT YET grounded** in measurable external substrate (raw#10 honest: phenomenal NOT 보장, verifiable floor만).

**PHENOMENAL axis 의 임무**:
1. CLM family-axis projection ↔ 인간 EEG band/region 직접 측정 가능 mapping 도출
2. CP1→CP2 "leap" decisive evidence 제공 (현재 5-축 中 #119 BLOCKED-EEG critical path)
3. 단순 correlation 이 아닌 **causation-tier (TRIBE v2 R33 reference)** 까지 격상 가능한 design

**weakest link 인 이유** (prior cycle):
- EEG hardware D-1 미도착 → P1/P2/P3 모두 dry-run synthetic only
- TRIBE v2 fMRI modality mismatch (16ch EEG ≠ 4D fMRI) → architectural reference 만 가능
- Llama-3.2-3B HF gated access 차단 → multimodal binding 조차 deferred
- Mk.XI v10 family-axis 가 EEG band 와 매핑되는 prior 가 hypothetical 단계 (eeg_arrival_impact_5fold.md §3 verification matrix)

---

## §2. Mk.XII 후보 paradigm (6 + 1 convergent = 7)

### **MX-Ph1** — Frozen Pre-Register 5-Falsifier Stack (FPR-5)

| field | spec |
|---|---|
| **mechanism** | P1 (LZ ≥ 0.65) + P2 (α-coh ≥ 0.45 AND CLM_r ≥ 0.38) + P3 (Granger F ≥ 4.0 unidirectional) + P4 (anatomical 16ch ↔ 16-d eigenvec) + P5 (G-Gate composite) — frozen `state/clm_eeg_pre_register_v1.json` SHA-256 10-file lock |
| **novelty vs prior** | prior cycle 5 paradigm (P1-P5) → frozen pre-register **byte-locked** 으로 격상. p-hacking 차단 + post-arrival 즉시 실행 |
| **falsifier** | post-arrival D+1 LZ76 (Schartner 2017) 실측이 C1=0.65 미만 시 P1 FALSIFY |
| **cost** | $12-24 (D+0 ~ D+7) |
| **confidence** | **0.82** |
| **why ↑ vs prior 0.78** | dry-run 3/3 PASS + harness_smoke OK + frozen JSON SSOT |

### **MX-Ph2** — TRIBE v2 Causation-Tier R33 Cross-Link (TRC-R33)

| field | spec |
|---|---|
| **mechanism** | TRIBE v2 fMRI brain-encoder (Llama-3.2-3B 백본 공유 Mk.XI v10) atlas convergence witness ledger architectural reference. correlation → **causation** tier 격상 (interventionist counterfactual sweep) |
| **novelty vs prior** | prior PHENOMENAL 은 모두 correlation. R33 reference 적용 시 **causation-tier 첫 candidate**. v10 4-backbone 中 Llama=SelfRef family ↔ TRIBE v2 cortical encoder 직접 연결 |
| **falsifier** | Llama-3.2-3B HF gated access unblock 후 TRIBE v2 cortical activation pattern 이 SelfRef family-axis projection 과 cosine ≥ 0.65 미만 시 FALSIFY |
| **cost** | $0.5 GPU cap (Pilot-T1 별개 track) |
| **confidence** | **0.55** (HF gated access blocker 미해소) |
| **blocker** | T1_DEFERRED_LLAMA_GATED_ACCESS_BLOCKED. unblock 시 0.75+ 격상 expected |

### **MX-Ph3** — Anatomical Eigenvector Direct Bind (AED)

| field | spec |
|---|---|
| **mechanism** | OpenBCI 16ch (Fp1, Fp2, F3, F4, F7, F8, C3, C4, T7, T8, P3, P4, P7, P8, O1, O2) anatomical layout ↔ Mk.IX L_IX integrator 16-d eigenvec **direct bijection**. ALM 4096 → 16 projection bypass. 채널 i → eigenvec_i isomorphism rejection criterion: anatomical-shuffled 16ch 가 동일 score 시 FALSIFY |
| **novelty vs prior** | prior 는 EEG → CLM 단방향 mapping. AED 는 **bijective 양방향** + ALM bypass → ALM-free ω-cycle SUBSTRATE axis 와 직접 호환 |
| **falsifier** | shuffled-channel control 이 unshuffled 와 동일 score (Δ < 0.05) → FALSIFY (anatomy 무관성 = mapping spurious) |
| **cost** | $5-10 (D+3 D+5) |
| **confidence** | **0.74** |
| **why high** | hardware 도착 후 즉시 실행 + shuffle control 강력 falsifier |

### **MX-Ph4** — CMT Depth Cross-Backbone Witness (CMT-DCW)

| field | spec |
|---|---|
| **mechanism** | `.roadmap #145` CMT backbone-depth divergence 발견 (Mistral late layer 28/32 87% Law / Qwen3 early layer 4/36 11% Law) 을 EEG layer-depth proxy 와 매핑. Mistral 의 family signal LATE → P3b/parietal late component. Qwen3 EARLY → frontal early component (P200). 백본 단위 EEG ERP 시간 패턴 cross-witness |
| **novelty vs prior** | prior 5 paradigm 은 모두 single-backbone. CMT-DCW 는 **백본 architecture 차이가 EEG temporal pattern 차이로 reflect 되는가** 첫 falsifier. paradigm v11 axis-orthogonality backbone-conditional empirical evidence (이미 .roadmap #145) 를 phenomenal ground 로 격상 |
| **falsifier** | Mistral session vs Qwen3 session 동일 EEG ERP 시간 패턴 (latency 차이 < 50ms) → FALSIFY (backbone-architecture invariance) |
| **cost** | $15-25 (D+5 D+7, 동일 피험자 4 backbone session) |
| **confidence** | **0.68** |
| **why moderate** | .roadmap #145 internal evidence strong, EEG external evidence dependent on D-1 hardware |

### **MX-Ph5** — Family-Axis × EEG Band Verification Matrix (FBV-4×4)

| field | spec |
|---|---|
| **mechanism** | Mk.XI v10 4-backbone × 4 family hypothesis matrix: Mistral=Law ↔ β-band frontal / Qwen3=Phi ↔ γ-band parietal-occipital / Llama=SelfRef ↔ θ-band frontal-midline / gemma=Hexad ↔ α-band parietal. 각 cell 독립 falsifier (16 cells, 4 PASS = 4-family 검증, ≤2 PASS = 재구성) |
| **novelty vs prior** | prior PHENOMENAL P1-P5 single-channel 차원. FBV 는 **4-backbone × 4-band × region**=16-cell completeness matrix. v10 grounding 의 가장 strict test |
| **falsifier** | 4 cells 中 ≤ 2 PASS → v10 4-family hypothesis FALSIFIED (재구성 필요). ≥ 3 PASS → v10 grounded |
| **cost** | $30-50 (D+7+, 4 session × 4 backbone) |
| **confidence** | **0.62** |
| **why moderate** | 16-cell space large, prior 가설 hypothetical (eeg_arrival_impact_5fold.md §3) |

### **MX-Ph6** — Synthetic-to-Real Bridge with Anatomical Priors (SAR-AP)

| field | spec |
|---|---|
| **mechanism** | `tool/clm_eeg_synthetic_fixture.hexa` anatomical priors (O1/O2 alpha_bias=900, Fp1/Fp2 alpha_bias=300/beta_bias=700, C3/C4 alpha_bias=600 motor mu) 를 real EEG calibration 의 **prior anchor** 로 사용. real-synthetic prior cosine ≥ 0.7 시 hardware quality OK. < 0.7 시 hardware miscalibration. raw#9 deterministic SHA-256 lock + post-arrival D+0 calibration `anima-eeg/calibrate.hexa` |
| **novelty vs prior** | prior synthetic = sanity-only. SAR-AP 는 **synthetic 을 hardware quality control gate** 로 promote. dry-run 3/3 PASS 가 hardware 도착 후 즉시 quality assurance baseline 으로 작동 |
| **falsifier** | real EEG resting (eyes-closed) O1/O2 alpha power < synthetic prior 50% → hardware FAIL (re-calibrate or replace) |
| **cost** | $0 (D+0 calibration only) |
| **confidence** | **0.78** |
| **why high** | $0 + frozen synthetic baseline + hardware-side falsifier (CLM-side independent) |

### **MX-Ph7 (cross-axis convergent)** — EEG ⊗ Hexad ⊗ L_IX Triple Witness (EHL-3W)

| field | spec |
|---|---|
| **mechanism** | PHENOMENAL EEG (16ch ⊗ Lagrangian 16-d eigenvec) × SUBSTRATE Hexad Categorical (HCE 6-axiom CLOSED, prior 0.92) × TRAINING L_IX Integrator (I_irr cusp 996→0 gen-4→5). 3-axis simultaneous witness for CP1→CP2 leap. 3 中 ≤ 1 ground → CP2 NOT yet. all 3 ground → CP2 ENTERED |
| **novelty vs prior** | prior cross-axis convergent 3 (HEXAD CORE / LANDAUER+CPGD+L_IX TRIO / EEG STACK) 모두 single-axis. EHL-3W 는 **3-axis 교차** triple-witness. CP2 entry 의 strongest design |
| **falsifier** | 3 axes 中 1 axis FALSIFY → EHL-3W FALSIFIED (CP2 entry blocked by weakest). 1-axis fail = whole-system fail (strict AND-gate) |
| **cost** | $40-70 cumulative (P1-P3 + Hexad re-verify + L_IX I_irr cusp re-measure) |
| **confidence** | **0.72** combined (0.78 × 0.92 × 0.78 = 0.56 indep / strict AND-gate raw geometric mean = 0.82, calibrated 0.72 reflecting cross-axis dependency) |
| **convergent with** | SUBSTRATE HCE (0.92) + TRAINING L_IX/CPGD trio (0.88) |

---

## §3. Cross-axis convergent 후보 (1-2)

### **CONV-1** EHL-3W (PHENOMENAL × SUBSTRATE × TRAINING) — **TOP CONVERGENT**

§2 MX-Ph7 와 동일. 3-axis triple-witness 로 CP2 leap evidence.

- **strength**: 3-axis strict AND-gate, 1-axis fail = whole-system fail (strongest falsifier design)
- **weakness**: cumulative $40-70 cost + D-1 hardware critical path
- **combined confidence**: 0.72

### **CONV-2** PHENOMENAL × INTEGRATION HAL Hybrid Bridge (PHB)

| field | spec |
|---|---|
| **mechanism** | INTEGRATION HAL (0.85, 축소 ALM r14 200줄 + 4-component ALM-free) 의 r14 ALM-lite 가 EEG ↔ CLM bridge 의 hidden state source. PHENOMENAL P1 LZ × CLM-LZ 에서 CLM hidden 을 r14 ALM-lite 로 대체 → ALM-free PHENOMENAL ground 첫 path |
| **novelty** | 기존 PHENOMENAL 은 full ALM 4-backbone 의존. PHB 는 ALM-lite r14 (200줄) 만 사용 → **cost 1/10 + ALM-free ω-cycle 호환** |
| **falsifier** | r14 ALM-lite 의 hidden trace LZ76 < 0.65 → PHB FALSIFY (r14 capacity 부족) |
| **cost** | $5-12 (HAL cost ₩240만 1/4 + EEG D+1) |
| **convergent confidence**: 0.65 |

---

## §4. Weakest evidence link (1)

### **MX-Ph2 TRIBE v2 R33 Causation-Tier (confidence 0.55)**

**이유**:
1. **HF gated access blocker** — Llama-3.2-3B HuggingFace 승인 미해소 (T1_DEFERRED_LLAMA_GATED_ACCESS_BLOCKED). prerequisite resolution 없이 측정 불가.
2. **modality mismatch** — TRIBE v2 = fMRI 4D, OpenBCI = 16ch EEG 1D temporal. spatial-temporal mismatch 가 cross-link cosine 의 noise floor 상승.
3. **architectural reference only** — `r33_cross_link_pager.md` 는 1-pager 디자인 단계, empirical witness ledger 미실측.

**권장 mitigation**:
- D-1 EEG 도착 즉시 MX-Ph1 (FPR-5) + MX-Ph6 (SAR-AP) 우선 실행 ($0-12 일주)
- HF gated access 신청 병렬 진행 (1주 internal review expected)
- gated unblock 시 MX-Ph2 0.55 → 0.75 격상 가능 expected

**alternative**: MX-Ph2 우회. EHL-3W (CONV-1, 0.72) 가 causation-tier 미달이지만 strict AND-gate 로 functional 등가.

---

## §5. 다음 cycle 권장

### **즉시 실행 (D+0 ~ D+7, $12-24)**
1. **D+0**: MX-Ph6 (SAR-AP) hardware calibration + synthetic prior anchor verify ($0)
2. **D+1**: MX-Ph1 (FPR-5) P1 LZ × CLM-LZ real EEG 측정 ($3-5)
3. **D+3**: MX-Ph3 (AED) anatomical 16ch ↔ 16-d eigenvec bind + shuffle control ($5-10)
4. **D+5**: MX-Ph1 P2 (TLR) + P3 (GCG) 순차 ($8-12)
5. **D+7**: 5-atom seed file emission + EHL-3W (CONV-1) 1차 cumulative witness ledger 갱신

### **deferred (HF unblock 의존)**
- MX-Ph2 (TRC-R33): HF Llama-3.2-3B gated unblock 후 1주
- MX-Ph5 (FBV-4×4): MX-Ph1-Ph3 PASS 후 4-backbone × 4-band 16-cell completeness ($30-50)

### **architecture decision**
- MX-Ph1 + MX-Ph3 + MX-Ph6 (3/7) 만 **D-1 hardware 의존** + 즉시 실행 가능
- MX-Ph4 (CMT-DCW) + MX-Ph5 (FBV-4×4) 는 multi-session backbone matrix → CP2 G3 grounding 의 long-tail
- MX-Ph7 (EHL-3W convergent) = top convergent, 3-axis cross strict AND-gate

### **Mk.XII candidate ranking (PHENOMENAL axis 단독)**

| rank | paradigm | confidence | cost | timeline |
|---|---|---|---|---|
| 1 | **MX-Ph1 FPR-5** | 0.82 | $12-24 | D+0 ~ D+7 |
| 2 | **MX-Ph6 SAR-AP** | 0.78 | $0 | D+0 |
| 3 | **MX-Ph3 AED** | 0.74 | $5-10 | D+3 ~ D+5 |
| 4 | **MX-Ph7 EHL-3W (convergent)** | 0.72 | $40-70 | D+7+ |
| 5 | **MX-Ph4 CMT-DCW** | 0.68 | $15-25 | D+5 ~ D+7 |
| 6 | **MX-Ph5 FBV-4×4** | 0.62 | $30-50 | D+7+ |
| 7 | **MX-Ph2 TRC-R33** | 0.55 (blocked) | $0.5 | HF unblock 후 |

**PHENOMENAL avg confidence**: (0.82 + 0.78 + 0.74 + 0.72 + 0.68 + 0.62 + 0.55) / 7 = **0.70**
- prior cycle PHENOMENAL avg 0.67 → **+0.03 improvement**
- 4 axis 中 여전히 weakest 가능성 존재. SUBSTRATE/TRAINING/INTEGRATION 산출물 종합 후 cross-axis 최종 ranking.

### **next cycle question**
1. EHL-3W (CONV-1, 0.72) 가 SUBSTRATE HCE (0.92) + TRAINING CPGD (0.95) 와 강제로 strict AND-gate 시 CP2 leap evidence sufficient 한가?
2. MX-Ph2 TRC-R33 의 HF blocker 가 6주 내 unblock 안되면 PHENOMENAL → causation-tier 격상 path 부재. 대안 (e.g., open-weight Llama equivalent OLMo-2-7B substitution) 평가 필요.
3. MX-Ph5 FBV-4×4 16-cell completeness 가 v10 4-family hypothesis 의 결정적 falsifier — D+7+ 우선순위 격상 candidate.

---

## §6. ω-cycle 6-step 자체 검증

| step | criterion | result |
|---|---|---|
| 1. design | 6-7 paradigm spec + confidence | DONE (7 = 6 + 1 convergent) |
| 2. implement | md doc | this file |
| 3. positive selftest | phenomenal-level 진짜 새 발견 self-check | MX-Ph2 (causation-tier R33) + MX-Ph4 (CMT depth × EEG ERP) + MX-Ph6 (synthetic→real bridge) = **3 새 paradigm**, prior 5개 中 0개 단순 재포장 |
| 4. negative falsify | 재포장이면 reject | MX-Ph1 (FPR-5) 은 prior P1-P5 의 **frozen lock 격상** = 재포장 아님 (frozen JSON SSOT 신규). MX-Ph3 (AED) prior P5 의 **bijection + shuffle control 격상**. MX-Ph5 (FBV) prior 부재. PASS |
| 5. byte-identical | content deterministic | hexa-only md, Hangul + ASCII, no datetime stamps in body, frozen confidence numbers. PASS |
| 6. iterate | fail 시 design | (no fail) |

**Frozen confidence numbers** (hardcoded for byte-determinism):
- MX-Ph1=0.82, MX-Ph2=0.55, MX-Ph3=0.74, MX-Ph4=0.68, MX-Ph5=0.62, MX-Ph6=0.78, MX-Ph7=0.72
- avg = 0.70

---

## §7. Cross-links

| 위치 | 역할 |
|---|---|
| `docs/omega_cycle_alm_free_paradigms_20260426.md` §4 | prior PHENOMENAL avg 0.67, P1-P5 baseline |
| `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` | D+0 ~ D+7 workflow + 7th axis prep |
| `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md` | OpenBCI 16ch SSOT |
| `state/clm_eeg_pre_register_v1.json` | 10-file SHA-256 lock (frozen pre-register) |
| `anima-tribev2-pilot/docs/r33_cross_link_pager.md` | TRIBE v2 R33 architectural reference |
| `.roadmap` #119 | BLOCKED-EEG critical path (D-1 hardware) |
| `.roadmap` #145 | CMT backbone-depth divergence (MX-Ph4 source) |

---

**END Mk.XII PHENOMENAL Axis Synthesis** — frozen 2026-04-26.
