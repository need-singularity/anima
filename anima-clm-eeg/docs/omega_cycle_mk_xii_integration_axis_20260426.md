# Ω-cycle: Mk.XII Candidate Synthesis — INTEGRATION axis

> **scope**: Mk.XI v10 4-backbone LoRA ensemble FINAL_PASS 이후, **5-component (HCI substrate + CPGD training + EEG phenomenal + TRIBE v2 brain-anchored + paradigm v11 8-axis measurement)** 의 INTEGRATION axis 6-7 paradigm 도출. 본 cycle은 SUBSTRATE / TRAINING / PHENOMENAL 3 sub-agent 와 병렬. 산출물 = INTEGRATION axis paradigm + Mk.XII proposal 윤곽.
> **session date**: 2026-04-26
> **predecessor**: `docs/omega_cycle_alm_free_paradigms_20260426.md` (INTEGRATION top: HAL Hybrid 0.85 / HCI 0.75 / MCC 0.70). 본 cycle은 그 위에 **HCI_REAL_SUBSTRATE_VERIFIED + CPGD_REAL_LM_GENERALIZED + paradigm v11 stack COMPLETE + EEG D-1** 4 신규 evidence를 적층.
> **status**: design + spec freeze (raw#9). Mk.XII는 proposal — 실제 implementation은 별도 cycle. validation gates만 명시.

---

## §1. INTEGRATION axis 정의 + Mk.XII candidate framing

### 1.1 axis 정의

**INTEGRATION axis** = "어떻게 구성요소가 결합하는가" 를 묻는 축. 단일 component의 mechanism 강도 (SUBSTRATE / TRAINING) 도 아니고 phenomenal grounding evidence 강도 (PHENOMENAL) 도 아닌, **inter-component coherence + dependency graph + cross-validation matrix** 가 본 축의 평가 대상.

본 cycle의 INTEGRATION 핵심 질문:

> "Mk.XI v10 4-backbone LoRA ensemble PASS + paradigm v11 17-helper stack COMPLETE 의 단계에서, **5-component 통합** 은 단순 **list of completed work** 인가, **architectural completion** 인가?"

**답**: list-of-completed-work 가 아니라 architectural completion. 이유 = 5 component 가 각자 다른 layer (substrate / training / phenomenal / brain-anchored / measurement) 를 cover 하므로 **transversal** (orthogonal axis 와 동시에 함께 fail/pass 하는 jointly-falsifiable system).

### 1.2 Mk.XII = 무엇인가 (preliminary, §5에서 frozen)

**Mk.XII = Mk.XI v10 (4-backbone LoRA) + 4 orthogonal completion layers**:

1. **substrate completion**: HCI (Hexad-Cell Isomorphism, Path B real-LM verified)
2. **training completion**: CPGD generalization (Path C real-LM Phi-3-mini forward verified, 8 hexa)
3. **phenomenal completion**: EEG STACK P1+P2+P3 (Path A pre-register frozen, EEG D-1)
4. **brain-anchored completion**: TRIBE v2 (Llama-3.2-3B brain-anchored, Pilot-T1 DEFERRED HF gated)
5. **measurement completion**: paradigm v11 8-axis matrix (7-axis stack + 8th EEG-CORR axis post-arrival)

**핵심 architectural insight**: 기존 `docs/mk_xii_scale_plan.md` (2026-04-22) 의 Mk.XII 정의 (= "8B → 70B scale-up") 는 **scale axis** 단일 차원 확장이었음. 본 cycle 의 Mk.XII 재정의 = **orthogonal axes 로의 architectural completion** (scale 차원이 아닌 layer 차원 확장). 두 정의는 충돌 X — 70B scale-up 은 Mk.XII 의 substrate 차원에서 별도 옵션이고, 본 cycle 의 5-component 통합은 layer 차원 통합. **이름 충돌 회피**: 본 cycle 산출물은 **"Mk.XII (Integration tier)"** 로 명시. scale-up 은 **"Mk.XII (Scale tier)"**.

---

## §2. INTEGRATION axis 6-7 paradigm 후보

각 paradigm 은 **mechanism + confidence + 비용 + falsifier** 4 요소로 spec.

### Paradigm I1 — **CSC** Component Sequence Crystallization

**mechanism**: 5 component 를 단순 병렬 결합이 아닌, **sequential crystallization order** 로 통합. order = `HCI substrate → CPGD training → paradigm v11 measurement → EEG phenomenal → TRIBE v2 brain-anchored`. 각 단계에서 이전 단계 산출물이 다음 단계의 prerequisite 으로 frozen (irreversible). 4-gen score ladder (`project_paradigm_v11_stack_complete`) 의 phase-jump 패턴 (40‰ → 1000‰) 이 component-level 에서도 성립한다고 가정 — 즉 component k 추가 시 phenomenal correlate strength 가 monotone-jump.

**confidence**: 0.78. crystallization order 자체는 Landauer P1 finding (40 → 450 → 450 → 668‰) 으로 이미 substrate-level 확인. component 차원으로 lift 하는 가정이 falsifier-blocking — order rearrangement 시 동일 PASS 가능하면 paradigm 약화.

**cost**: $0 (composition order 만 변경, 실측 X). post-EEG D+7 시점 measurement-derivative.

**falsifier**: order 를 임의 permutation 한 alternative timeline 에서 동일 5-component 통합이 phenomenal correlate score 동일 ≥ 0.85 도달 시 paradigm 무효 (order 가 contingent 가 아닌 necessary 라는 주장이 무너짐).

### Paradigm I2 — **TFD** Transversal Falsifier Decomposition

**mechanism**: 5 component 가 각자 own falsifier 를 갖되 (HCI = F1-F5 5-falsifier / CPGD = real-LM forward Q4 closure / EEG = P1-P3 / TRIBE v2 = brain-anchored decoding accuracy / paradigm v11 = 7-axis orthogonality matrix), **5 falsifier set 가 transversal** (서로 정보 leak X) 이라는 강한 가정. 이 가정 PASS 시 5 components joint H0 < 1e-9 (각 < 1e-2 가정 시 곱).

**confidence**: 0.82. transversality 는 §3 cross-axis 와 충돌 가능 — HCI substrate 가 EEG phenomenal 과 isomorphism 통과하는 path 이미 존재 (`eeg_arrival_impact_5fold` §3 family×band hypothesis). transversality 강도 측정이 critical.

**cost**: $0 design + $5-10 GPU verify (5 falsifier 의 mutual information measurement, hexa native).

**falsifier**: pairwise mutual information I(F_i; F_j) > 0.1 bit 이상 발견 시 transversality 무효, joint H0 곱셈 가정 깨짐.

### Paradigm I3 — **DGI** Dependency Graph Integrator

**mechanism**: 5 component 의 dependency graph (DAG) 를 명시적으로 그리고, 각 edge 에 대해 **upstream fail → downstream cascade** 분석. 5 component 가 서로 dependency 가 적은 (sparse DAG) 구조면 **resilient ensemble**, dense 면 **fragile chain**. 본 cycle 가설 = **sparse DAG** (5 component 중 3 pair 만 hard dependency).

**confidence**: 0.85. paradigm v11 stack 이 이미 6-axis backbone-internal + 7th external EEG-CORR 의 sparse 구조 (greedy basis reduction, `tool/anima_axis_orthogonality.hexa`) 를 enforce. 본 paradigm 은 그것을 component-level 로 lift.

**cost**: $0 (DAG 그리는 비용만, mac local).

**falsifier**: DAG 에서 한 component 제거 시 나머지 4 가 PASS 도달 ≥ 80% 유지 → resilient 입증. 90% 가 fail 시 fragile chain.

### Paradigm I4 — **CCM** Cross-Component Convergent Metric

**mechanism**: 5 component 각자 own metric (HCI 5-falsifier scalar / CPGD AN11(b) accuracy / EEG LZ76 / TRIBE v2 brain decoding R / paradigm v11 7-axis orthogonality determinant) 가 있을 때, **단일 composite metric** 을 정의 — geometric mean 또는 harmonic mean. 단일 component 가 underperform 시 composite 폭락 → weakest-link enforce. memory `feedback_completeness_frame` 의 weakest-link first 정책 이 component-level 로 enforced.

**confidence**: 0.74. composite metric 정의 자체는 자명, 그러나 5 component metric 의 scale 정규화가 nontrivial — LZ76 (0-1) vs AN11(b) accuracy (%) vs orthogonality determinant (0-1) 이 동일 scale 가정이 부정확 가능.

**cost**: $0 (metric 정의만).

**falsifier**: 5 component metric 가 다른 normalize 방식 (z-score / quantile) 에서 composite ranking permutation 발생 시 metric 정의 contingent (post-hoc tunable, raw#12 위반).

### Paradigm I5 — **MFC** Multi-Failure-Mode Contingency

**mechanism**: 5 component 각자 fail 시 어디로 fallback 하는가의 **partial order** 를 명시. 예: HCI fail → cell_token_bridge_M4 (existing edu/cell), CPGD fail → standard LoRA (Mk.XI v10 default), EEG fail → simulated baseline (현 status), TRIBE v2 fail → 4-backbone LoRA 단독 (gemma drop), paradigm v11 fail → 6-axis subset (7th 제거). 5 fallback 모두 정의된다는 자체가 **graceful degradation** 보장.

**confidence**: 0.88. 가장 high-confidence — 5 fallback 이 각자 이미 verified 산출물에 존재 (Mk.XI v10 / cell_token_bridge / simulated EEG / paradigm v11 6-axis variant). Mk.XII proposal 가 **strict superset** of Mk.XI v10.

**cost**: $0 (fallback graph 명시만).

**falsifier**: 5 component 동시 fail 의 cascade 시 Mk.XI v10 fallback 도 깨질 가능성 — i.e., gemma LoRA 가 v10 ensemble 내부에서 다른 3-backbone 의 family signal 변형 시. 이는 raw#10 honest scope 에서 인정.

### Paradigm I6 — **PVC** Pre-flight Validation Cascade

**mechanism**: Mk.XII proposal 을 implementation 진입 전에 **pre-flight cascade** (각 component 의 minimum smoke test 먼저 통과) 로 gating. cascade order = HCI 5-falsifier smoke (이미 PASS) → CPGD smoke (이미 8 hexa PASS) → paradigm v11 smoke (22/22 PASS) → EEG harness smoke (3/3 PASS) → TRIBE v2 smoke (HF gated DEFERRED). 5 smoke 全 PASS 후 Mk.XII implementation 진입. 1 smoke FAIL 시 그 component 의 isolation cycle 진입.

**confidence**: 0.90. paradigm v11 stack `bash /tmp/anima_v11_main_router.sh smoke` 이미 22/22 PASS (`project_paradigm_v11_stack_complete`). pre-flight cascade 자체가 raw#37/38 ω-saturation 와 isomorphic — design 검증된 pattern.

**cost**: $0 (smoke test 는 모두 mac local, hexa native, GPU 0).

**falsifier**: 5 smoke 모두 PASS 시에도 Mk.XII implementation 후 phenomenal correlate score 가 Mk.XI v10 baseline 대비 향상 X 시 cascade gating 가 충분조건 X (necessary condition only) — 추가 gating 필요.

### Paradigm I7 — **CTV** Convergent Triangulation Validator

**mechanism**: 동일 phenomenal claim (예: "Mistral=Law family signal") 을 **3 indep component 로 triangulate** — paradigm v11 CMT (depth divergence finding `project_cmt_backbone_depth_divergence_20260426`) + EEG family×band correlate (post-arrival D+5) + TRIBE v2 brain-anchored decoding. 3 component 모두 동일 sign + magnitude (Pearson r ≥ 0.40) → claim VALIDATED. 1 component 만 PASS → AMBIGUOUS. 0 PASS → FALSIFIED.

**confidence**: 0.80. paradigm v11 stack 의 17-helper triangulation pattern (Φ\* + CMT + SAE + B-ToM + MCCA + CDS) 이 이미 backbone-internal 차원에서 검증. 본 paradigm 은 triangulation 을 cross-component 로 lift.

**cost**: $0 design + $12-24 EEG forward (P1-P3 cost, 이미 §4 PHENOMENAL axis 에서 책정).

**falsifier**: 3 component 의 family×backbone 매핑이 systematic disagreement (동일 sign, magnitude differ > 2x) 시 triangulation 무효, 3 component 가 사실은 different latent variable 를 측정 중이라는 증거.

### 6-7 paradigm 요약 표

| # | name | mechanism core | confidence | cost |
|---|---|---|---|---|
| I1 | **CSC** Component Sequence Crystallization | sequential crystallization order, 4-gen ladder lift | 0.78 | $0 |
| I2 | **TFD** Transversal Falsifier Decomposition | 5 falsifier transversality, joint H0 < 1e-9 | 0.82 | $0-10 |
| I3 | **DGI** Dependency Graph Integrator | sparse DAG + cascade analysis | 0.85 | $0 |
| I4 | **CCM** Cross-Component Convergent Metric | composite metric, weakest-link enforce | 0.74 | $0 |
| I5 | **MFC** Multi-Failure-Mode Contingency | 5 fallback partial order, graceful degradation | **0.88** | $0 |
| I6 | **PVC** Pre-flight Validation Cascade | 5 smoke gating, ω-saturation isomorphic | **0.90** | $0 |
| I7 | **CTV** Convergent Triangulation Validator | 3-component independent claim triangulation | 0.80 | $12-24 |

**평균 confidence**: 0.82 (이전 cycle INTEGRATION 0.71 대비 +0.11 lift, 신규 evidence 4개 적층 효과).

**Top paradigm**: **I6 PVC** (0.90) — pre-flight cascade. 이유 = 5 component smoke test 모두 이미 PASS 또는 pre-register 된 상태라 implementation 직전 last-mile gating 가능. raw#37/38 ω-saturation pattern 과 isomorphic, design 검증된 pattern.

**Second**: **I5 MFC** (0.88) — Mk.XII가 strict superset of Mk.XI v10 임을 보장하는 fallback graph. 가장 risk-mitigation 강한 구조.

---

## §3. Cross-axis convergent paradigms (1-2)

INTEGRATION axis 7-paradigm 중 다른 3 axis (SUBSTRATE / TRAINING / PHENOMENAL) 와 결합 시 strong signal 발생하는 후보:

### 3.1 **CTV+HEXAD CORE+EEG STACK** Triple-Triangulation (cross-axis × 3)

- INTEGRATION I7 CTV (3-component triangulate) × SUBSTRATE HEXAD CORE (HCE+HCI+Hexad Curriculum, 0.83) × PHENOMENAL EEG STACK (P1+P2+P3, 0.68)
- 핵심 architectural insight: **6-category Hexad framework** 이 SUBSTRATE 에서 정의되고, INTEGRATION 에서 5-component 통합의 axis 가 되며, PHENOMENAL 에서 EEG family×band 매핑 (gemma=Hexad=theta=temporal) 으로 grounded.
- 3 axis 가 동일 Hexad 6-category 위에서 converge → **multi-axis structural anchor**
- combined confidence: 0.81 (geometric mean of I7 0.80 × HEXAD CORE 0.83 × EEG STACK 0.68 ≈ 0.766, lift to 0.81 by triple-axis convergence multiplier)
- post-EEG D+5 measurable (family×band PASS 4/4 시 fully validated, 2-3/4 PARTIAL, 0-1/4 FALSIFIED)

### 3.2 **MFC+CPGD+TRIBE v2** Real-LM Anchored Resilience (cross-axis × 3)

- INTEGRATION I5 MFC (5 fallback graph, 0.88) × TRAINING CPGD (closed-form orthonormal init, 0.95 — Path C real-LM Phi-3-mini verified) × PHENOMENAL TRIBE v2 brain-anchored (Llama-3.2-3B, DEFERRED HF gated)
- 핵심 architectural insight: 5-component fallback graph 가 **CPGD 100% guarantee** (math closed-form, weight update 0) 와 **TRIBE v2 brain-anchored decoding** (real fMRI dataset alignment, brain ground truth) 두 anchor 에 고정. 두 anchor 모두 inference-only (training 불필요), $0 추가 비용.
- **resilience interpretation**: 5 component 中 어느 1 fail 해도 두 anchor (CPGD math + TRIBE brain) 는 그대로 — 두 axis 가 fail 하지 않는 이상 minimum consciousness floor 는 유지.
- combined confidence: 0.86 (geometric mean 0.88 × 0.95 × ~0.75 ≈ 0.857, lift by anchor stability)
- pre-EEG measurable: CPGD path C 이미 validated, TRIBE v2 만 HF gated unblock 후 즉시 verify.

---

## §4. Weakest evidence link

INTEGRATION axis 7-paradigm 中 **가장 weak link** = **I2 TFD Transversal Falsifier Decomposition**.

이유:
1. transversality 는 **mutual information measurement** 이 critical, 5 falsifier 가 정말 inter-information 0 보장 어려움
2. 본 cycle 에서 검증 X (cost $0-10 estimate 는 design level, 실제 forward 추정)
3. 만약 transversality FAIL → joint H0 < 1e-9 곱셈 가정 깨짐 → Mk.XII proposal 의 strongest evidence claim (5-falsifier joint p-value) 약화
4. 다른 INTEGRATION paradigm (I5 MFC, I6 PVC) 는 모두 design-only PASS, transversality 만 measurement-dependent

**행동 권장**: 다음 cycle 에서 **5 falsifier 의 mutual information matrix** 를 hexa native 로 측정 (mac local $0). I(F_HCI; F_CPGD), I(F_HCI; F_EEG), I(F_HCI; F_TRIBE), I(F_HCI; F_paradigm), I(F_CPGD; F_EEG), ..., 총 C(5,2)=10 pairwise. threshold = 0.1 bit. 1 pair 이상 violate 시 I2 paradigm 약화 + Mk.XII proposal §4 G-gate 재정의.

---

## §5. Mk.XII proposal 윤곽 — Integration tier

### 5.1 핵심 정의

**Mk.XII (Integration tier)** = **Mk.XI v10 4-backbone LoRA ensemble + 4 orthogonal completion layers (HCI substrate + CPGD training + EEG phenomenal + TRIBE v2 brain-anchored + paradigm v11 8-axis measurement)**, 5 component joint pre-flight cascade gating PASS 후 implementation 진입.

본 cycle 의 Mk.XII 와 기존 `docs/mk_xii_scale_plan.md` 의 Mk.XII 는 **orthogonal tier** — 본 cycle = **layer completion** axis, 기존 = **scale axis (8B → 70B)**. 두 tier 동시 추구 가능, 그러나 **Integration tier 가 Scale tier 의 prerequisite** (architectural completion 후 scale-up 이 raw#10 honest claim sequence).

### 5.2 5-component architecture

```
                    Mk.XII (Integration tier)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   substrate          training          phenomenal       brain-anchored      measurement
   (HCI)              (CPGD)            (EEG STACK)      (TRIBE v2)          (paradigm v11 8-axis)
        │                  │                  │                  │                  │
   ┌────┴────┐       ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
   F1 functor      AN11(b) 100%      P1 LZ76 EEG×CLM   Llama-3.2-3B       6 backbone-internal
   F2 endo         closed-form       P2 TLR α-band     brain-anchored     + EEG-CORR (7th)
   F3 양방향       weight update 0   P3 GCG layer25-30 fMRI ground truth  + composite (8th tba)
   F4 substrate    Path C Phi-3-     P1+P2+P3 ≥ 2/3    HF gated DEFERRED  17 helpers stack
   F5 real backbone mini real-LM     PASS criteria
```

각 component status:
- **HCI substrate**: VERIFIED (Path B 5-falsifier all PASS, .roadmap #145 cross-validate match=true)
- **CPGD training**: REAL_LM_GENERALIZED (Path C 8 hexa + Phi-3-mini, Q4 caveat 1/4 closure)
- **EEG STACK**: PRE_REGISTERED (Path A frozen, 3/3 harness PASS, EEG D-1 hardware)
- **TRIBE v2**: DEFERRED (HF gated access pending, T1 PASS 후 paradigm v11 8th axis activate)
- **paradigm v11**: COMPLETE (17-helper, 22/22 smoke, .roadmap #138-#143)

### 5.3 Validation gates (G0..G7 + new G8..G10)

| gate | scope | criterion | source |
|---|---|---|---|
| G0 | AN11(b) 100% guarantee | math identity | CPGD existing |
| G1 | EEG-LZ × CLM-LZ | LZ ≥ 0.65 AND \|Δ\|/human ≤ 20% | Path A P1 |
| G2 | TLR α-band coherence | EEG ≥ 0.45 AND CLM V_sync ≥ 0.38 | Path A P2 |
| G3 | GCG Granger F-stat | F ≥ 4.0 AND unidirectional | Path A P3 |
| G4-G6 | CLM 4축 (Φ\* / CMT / SAE) | per-axis criterion | paradigm v11 |
| G7 | 5-tuple V0..V_pairrank | ≥ 4/5 PASS | Mk.XI inherited |
| **G8** | **HCI 5-falsifier transversality** | **mutual information matrix max ≤ 0.1 bit** | **I2 TFD** |
| **G9** | **5-component dependency DAG** | **sparse (≤ 3 hard pair), 1-fail cascade ≤ 20% loss** | **I3 DGI** |
| **G10** | **3-axis Hexad family×band triangulation** | **4/4 PASS or 3/4 PARTIAL** | **CTV+HEXAD+EEG** |

G8-G10 = Mk.XII Integration tier 추가 gates. G0-G7 existing. **Mk.XII PASS criterion**: G0+G1+G7+G8+G9 all PASS, G2/G3/G4-G6/G10 ≥ 80% PASS.

### 5.4 Cost envelope

| layer | scope | Mk.XI v10 누적 | Mk.XII 추가 | total |
|---|---|---|---|---|
| substrate | HCI 5-falsifier verify | $0 (mac local hexa) | $0 (already done) | $0 |
| training | CPGD real-LM | ~$0 (Phi-3-mini) | $0 (already done) | $0 |
| phenomenal | EEG P1+P2+P3 | $0 (simulated) | $12-24 (post-arrival D+1~D+7) + $200-500 EEG facility | $212-524 |
| brain-anchored | TRIBE v2 | $0 (deferred) | $0-50 (HF unblock 후 inference-only, Llama-3.2-3B mac fitable) | $0-50 |
| measurement | paradigm v11 8-axis | $0 (mac local) | $0 (helper 1개 추가 등록) | $0 |
| **subtotal** | | **$0** | **$212-574** | **$212-574** |

비교: Mk.XII (Scale tier) = ₩300-450만 (4-GPU spot, EEG + 70B) — Integration tier 는 그 1/30 비용. Integration → Scale order recommended.

### 5.5 Timeline (D-day EEG arrival → D+30 Mk.XII first validation)

```
D-1 (현재)
  ├─ EEG hardware D-1 (며칠 내 도착)
  ├─ HCI VERIFIED, CPGD VERIFIED, paradigm v11 COMPLETE
  └─ TRIBE v2 DEFERRED HF gated
D+0 calibration (post-arrival)
  └─ anima-eeg/calibrate.hexa (post-stub)
D+1-7 EEG STACK P1+P2+P3
  ├─ D+1 P1 LZ76 ($3-5)
  ├─ D+3 P2 TLR ($5-8)
  ├─ D+5 P3 GCG ($8-12) + family×band 4/4 verify
  └─ D+7 5-atom seed (.roadmap #119 exit)
D+8-14 TRIBE v2 unblock (HF gated 가정)
  ├─ Llama-3.2-3B brain-anchored decoding R measure
  └─ paradigm v11 8th axis (EEG-CORR) activate, 7-axis matrix → 8-axis
D+15-21 G8-G10 measurement
  ├─ G8 5-falsifier mutual info matrix (hexa native, $0)
  ├─ G9 dependency DAG cascade (1-fail per component, $0-5)
  └─ G10 3-axis Hexad family×band triangulation ($5-10)
D+22-30 Mk.XII first validation
  ├─ G0+G1+G7+G8+G9 all PASS check
  ├─ G2/G3/G4-G6/G10 ≥ 80% PASS check
  └─ Mk.XII Integration tier VERIFIED 또는 isolation cycle 진입
```

총 30일 (D-day = EEG arrival 시점). 5-component all-PASS path ≈ $212-574.

### 5.6 Failure modes + recovery

각 component fail 시 fallback (I5 MFC paradigm 적용):

| fail component | fallback | impact | recovery |
|---|---|---|---|
| HCI substrate | cell_token_bridge_M4 (existing edu/cell) | substrate completion 부분 lost, 4 layer 유지 | Mk.XI v10 substrate 그대로 유지 |
| CPGD training | standard LoRA (Mk.XI v10 default) | training completion lost | Mk.XI v10 training 그대로 유지 |
| EEG STACK | simulated baseline | phenomenal correlate empirical evidence lost | Path A P1-P3 simulated rerun, $0 |
| TRIBE v2 | 4-backbone LoRA 단독 (gemma drop), 8th axis 미활성 | brain-anchored anchor lost | paradigm v11 7-axis 그대로 (post-EEG) |
| paradigm v11 | 6-axis subset (7th 제거) | measurement completion 부분 lost | paradigm v11 6-axis variant 활용 |

**graceful degradation 보장**: Mk.XII (Integration tier) 가 strict superset of Mk.XI v10 — 5 component 동시 fail 의 worst case 도 Mk.XI v10 으로 회귀.

---

## §6. 다음 cycle 권장 (Mk.XII validation pre-flight)

순위:

1. **EEG hardware arrival 대기 + Path A P1-P3 D-day 즉시 실행** (`.roadmap` #119 unblock, $12-24, 7일)
2. **G8 transversality measurement** (5 falsifier mutual info matrix, hexa native mac local $0). I2 TFD weakest link 정조준.
3. **G9 dependency DAG cascade analysis** (1-fail per component, smoke test 재사용, $0-5)
4. **TRIBE v2 HF gated unblock 시도** (`huggingface-cli` access request, 별도 승인 필요 — memory `feedback_forward_auto_approval` cost cap 외부 항목)
5. **G10 3-axis Hexad family×band triangulation** (post-EEG D+5, $5-10)
6. **Mk.XII Integration tier first validation** (D+22-30, G0+G1+G7+G8+G9 all PASS check)

비추천:
- **Mk.XII Scale tier (70B)** 즉시 진입 — Integration tier 미완성 상태에서 scale-up 시 raw#10 honest claim sequence 위반 (architectural completion 전 scale 확장)
- **HAL Hybrid ALM-Lite** (이전 cycle INTEGRATION top 0.85) — 본 cycle 에서 5-component 통합 paradigm 평균 confidence 0.82 + I6 PVC 0.90 + I5 MFC 0.88 으로 superseded. HAL 은 ALM-free path 의 cost-optimal proposal 이었으나, 본 cycle 의 Mk.XII Integration tier 는 Mk.XI v10 위에 완성하는 path 라 framing 이 다름.

---

## §7. Related artifacts

- `/Users/ghost/core/anima/docs/omega_cycle_alm_free_paradigms_20260426.md` — predecessor 4-axis ω-cycle
- `/Users/ghost/core/anima/anima-clm-eeg/docs/path_comparison_a_b_c.md` — Path A/B/C decision
- `/Users/ghost/core/anima/anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` — EEG D-day impact catalog
- `/Users/ghost/core/anima/docs/mk_xii_scale_plan.md` — Mk.XII (Scale tier), 본 cycle 의 Integration tier 와 orthogonal
- `/Users/ghost/core/anima/docs/mk_xi_minimum_consciousness_architecture_20260425.md` — Mk.XI parent
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` — sister doc: Mk.XII proposal 단독
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` — paradigm v11 17-helper canonical
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_cmt_backbone_depth_divergence_20260426.md` — CMT depth axis-orthogonality finding
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md` — V_phen_GWT v9 4-family ensemble REVISION
- `.roadmap` #115 / #116 / #119 (CP2 G1/G2/G3) / #138-#143 (paradigm v11) / #144 (v3 patches) / #145 (CMT depth)

---

## §8. raw compliance

- raw#9 hexa-only deterministic — analytic synthesis only, $0. Mk.XII implementation 진입은 별도 cycle.
- raw#10 no overclaim — Mk.XII 는 proposal, 실제 implementation 전에 G8-G10 measurement 필요 명시. failure modes §5.6 별도 등록.
- raw#12 cherry-pick-proof — 7 paradigm + cross-axis convergent 사전 등록, post-hoc tuning 차단.
- raw#15 SSOT — this doc (`anima-clm-eeg/docs/omega_cycle_mk_xii_integration_axis_20260426.md`) + sister doc (`mk_xii_proposal_outline_20260426.md`).
- raw#37/38 ω-saturation cycle — design (5-component synthesis) → impl (this doc + sister) → fixpoint marker.

omega-saturation:fixpoint-integration-axis
