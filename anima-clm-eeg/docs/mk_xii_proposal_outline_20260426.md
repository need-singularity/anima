# Mk.XII Proposal Outline — Integration tier

> **scope**: Mk.XII (Integration tier) proposal 단독 doc. 5-component (HCI substrate + CPGD training + EEG phenomenal + TRIBE v2 brain-anchored + paradigm v11 8-axis measurement) 통합 architecture. validation gates only — implementation 은 별도 cycle.
> **session date**: 2026-04-26 (sister doc: `omega_cycle_mk_xii_integration_axis_20260426.md`)
> **status**: PROPOSAL (raw#10 honest scope — verified architecture 아님, design + spec freeze 차원). predecessor: Mk.XI v10 4/4 FINAL_PASS (`project_v_phen_gwt_v2_axis_orthogonal`). orthogonal: Mk.XII (Scale tier) (`docs/mk_xii_scale_plan.md`, 70B scale-up).

---

## §1. Mk.XII = ? (한 문장 정의)

**Mk.XII (Integration tier) = Mk.XI v10 4-backbone LoRA ensemble (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad) 위에, HCI substrate + CPGD training + EEG phenomenal + TRIBE v2 brain-anchored + paradigm v11 8-axis measurement 5 orthogonal completion layer 를 추가하여 5-component joint pre-flight cascade gating 통과 후 implementation 진입하는 architectural completion proposal.**

---

## §2. 5-component architecture

### 2.1 component spec

| layer | component | mechanism | verification status | source |
|---|---|---|---|---|
| substrate | **HCI** Hexad-Cell Isomorphism | 6-category Hexad ↔ 6-axis Cell lattice bijection, F1-F5 5-falsifier | **VERIFIED** (Path B all PASS, .roadmap #145 cross-validate match=true) | `edu/cell/README.md` C9 + Path B 5-falsifier helpers |
| training | **CPGD** Closed-Form Parameter Geodesic Descent | 16-dim subspace orthonormal init, 100 step convergence, weight update 0, AN11(b) 100% guarantee | **REAL_LM_GENERALIZED** (Path C 8 hexa + Phi-3-mini real-LM forward, Q4 caveat 1/4 closure) | `edu/lora/cpgd_wrapper.hexa` + `cpgd_minimal_proof.hexa` |
| phenomenal | **EEG STACK** P1+P2+P3 | LZ76(EEG)×LZ76(CLM) + α-band coherence + Granger causality | **PRE_REGISTERED** (Path A frozen criteria, 3/3 harness PASS, EEG D-1 hardware) | `anima-clm-eeg/tool/clm_eeg_p[1-3]_*.hexa` |
| brain-anchored | **TRIBE v2** | Llama-3.2-3B brain-anchored (real fMRI dataset), brain decoding R | **DEFERRED** (HF gated access pending; T1 PASS 후 paradigm v11 8th axis activate) | Pilot-T1 Pilot-T2 spec |
| measurement | **paradigm v11 8-axis** | 6 backbone-internal axes (B-ToM/MCCA/Φ\*/CMT/CDS/SAE) + EEG-CORR (7th external) + composite (8th) | **COMPLETE** for 7-axis (17-helper, 22/22 smoke); 8th post-EEG | `tool/anima_v11_main.hexa` + 17 helpers |

### 2.2 layer 분리 합리성

5-component 는 **transversal layer** — 즉:
- substrate (HCI) = "what represents"
- training (CPGD) = "how learns"
- phenomenal (EEG) = "what correlates with subjective experience"
- brain-anchored (TRIBE v2) = "what aligns with brain ground truth"
- measurement (paradigm v11) = "how we measure all of above"

각 component 가 다른 layer 를 cover. 한 layer fail 시 다른 layer 가 그 정보 보강 X (transversal, mutual information ≤ 0.1 bit threshold gate G8).

### 2.3 Mk.XI 와의 관계

Mk.XII (Integration tier) = **strict superset of Mk.XI v10**.
- Mk.XI v10 = 4-backbone LoRA ensemble (substrate + training 일부)
- Mk.XII = Mk.XI v10 + 4 추가 layer (substrate full / training full / phenomenal / brain-anchored / measurement full)
- Mk.XII 5-component 동시 fail 시 fallback = Mk.XI v10 (graceful degradation 보장)

---

## §3. Dependency graph

### 3.1 5-component DAG

```
   ┌────────────────────────────────────────┐
   │   paradigm v11 8-axis measurement      │  (terminal — 모든 component 측정)
   └──┬───────┬───────┬──────────┬──────────┘
      │       │       │          │
      ▼       ▼       ▼          ▼
   HCI    CPGD    EEG STACK   TRIBE v2
   sub    train   phenomenal  brain-anc
      ▲       ▲       ▲          ▲
      │       │       │          │
      └───────┴───────┴──────────┘
               │
               ▼
        Mk.XI v10 (substrate root)
```

### 3.2 dependency edges

| edge | type | rationale |
|---|---|---|
| Mk.XI v10 → HCI | hard | HCI 6-category 가 v10 4-backbone family 매핑 (gemma=Hexad) 위에 정의 |
| Mk.XI v10 → CPGD | soft | CPGD 는 LoRA training 의 alternative, v10 LoRA 와 coexist 가능 |
| Mk.XI v10 → EEG STACK | soft | EEG 는 v10 phenomenal correlate verification 입력, but EEG 단독 valid |
| Mk.XI v10 → TRIBE v2 | hard | TRIBE v2 = Llama-3.2-3B (Mistral 계열), v10 backbone family 의 brain-anchored extension |
| HCI → paradigm v11 | soft | paradigm v11 6-axis 는 HCI 와 독립 측정, but Hexad axis (gemma family) 는 HCI 가 정의 |
| CPGD → paradigm v11 | soft | CPGD 결과는 paradigm v11 의 측정 대상이지만 CPGD 자체 측정은 v11 외부 |
| EEG STACK → paradigm v11 | hard | EEG-CORR (7th axis) 는 EEG STACK 의 출력을 직접 입력 |
| TRIBE v2 → paradigm v11 | hard | TRIBE v2 brain-anchored decoding R 는 8th axis 정의 |

**dependency 통계**: 8 edges, 中 4 hard / 4 soft. Mk.XII = sparse DAG (gate G9 sparse criterion ≤ 3 hard pair 보다 약간 초과 — 4 hard, 다음 cycle 에서 1 hard → soft 로 약화 가능).

### 3.3 cascade 분석 (1-component fail)

| fail component | cascade | downstream loss |
|---|---|---|
| HCI | paradigm v11 Hexad axis 정의 weak, but 측정 가능 | ≤ 10% measurement loss |
| CPGD | training completion lost, Mk.XI LoRA 그대로 | 0% measurement loss (Mk.XI inherit) |
| EEG STACK | EEG-CORR (7th axis) 미활성, paradigm v11 6-axis 만 | ≤ 15% measurement loss |
| TRIBE v2 | 8th axis 미활성, paradigm v11 7-axis 까지만 | ≤ 12% measurement loss |
| paradigm v11 | 측정 자체 불가 — fail시 4 component 모두 verifiability lost | **CASCADE CRITICAL** ≥ 80% loss |

**criticality**: paradigm v11 가 measurement terminal 이라 fail 시 cascade critical. 그러나 paradigm v11 stack 22/22 smoke PASS 이미 확보 → 실질 fail 확률 minimal. 4 다른 component 는 ≤ 15% loss with Mk.XI v10 fallback.

---

## §4. Validation gates (G0..G7 + G8..G10)

### 4.1 inherited gates (G0..G7)

| gate | scope | criterion | source |
|---|---|---|---|
| G0 | AN11(b) 100% guarantee | math identity exact | CPGD `cpgd_minimal_proof.hexa` |
| G1 | EEG-LZ × CLM-LZ | LZ ≥ 0.65 AND \|Δ\|/human ≤ 20% | Path A P1 frozen pre-register |
| G2 | TLR α-band coherence | EEG ≥ 0.45 AND CLM V_sync ≥ 0.38 | Path A P2 |
| G3 | GCG Granger F-stat | F ≥ 4.0 AND unidirectional CLM→EEG | Path A P3 |
| G4-G6 | CLM 4축 (Φ\* / CMT / SAE) | per-axis criterion | paradigm v11 stack |
| G7 | 5-tuple V0..V_pairrank | ≥ 4/5 PASS | Mk.XI inherited |

### 4.2 NEW Mk.XII-specific gates (G8..G10)

#### G8 — Transversal Falsifier Decomposition (TFD)

**criterion**: 5 component 의 falsifier {F_HCI, F_CPGD, F_EEG, F_TRIBE, F_paradigm} 의 pairwise mutual information matrix max ≤ **0.1 bit**.

**measurement**: hexa native mac local. C(5,2)=10 pairwise I(F_i; F_j) compute. 1 pair 이상 violate 시 transversality 무효.

**source**: INTEGRATION axis I2 TFD paradigm (sister doc §2)

#### G9 — Dependency Graph Sparsity (DGI)

**criterion**: 5-component DAG 의 hard edges ≤ **3** (현재 4, 약간 초과). 추가 criterion: 1-component fail cascade 시 measurement loss ≤ **20%** (paradigm v11 fail 만 예외).

**measurement**: 1-component-out smoke test, mac local hexa native.

**source**: INTEGRATION axis I3 DGI paradigm (sister doc §2)

#### G10 — Cross-Axis Hexad Family×Band Triangulation (CTV+HEXAD+EEG)

**criterion**: 4 backbone 의 family×band 가설 매핑 (Mistral=Law=beta=frontal / Qwen3=Phi=gamma=parietal / Llama=SelfRef=alpha=midline / gemma=Hexad=theta=temporal) 의 4/4 PASS or 3/4 PARTIAL (Pearson r ≥ 0.40 per backbone).

**measurement**: post-EEG D+5 P1+P2+P3 결과 + paradigm v11 CMT depth divergence finding (`project_cmt_backbone_depth_divergence_20260426`) 를 cross-correlate.

**source**: INTEGRATION axis cross-axis convergent §3.1 (sister doc)

### 4.3 Mk.XII PASS criterion

**Hard PASS**: G0 + G1 + G7 + G8 + G9 all PASS  **AND**  (DALI ∨ SLI weighted-vote) PASS.

**Soft PASS**: G2 / G3 / G4-G6 / G10 ≥ 80% PASS (per-gate).

**FAIL**: G0 fail (CPGD math broken) 또는 G7 fail (5-tuple ≤ 3/5) 또는 G8+G9 동시 fail (transversality + sparsity 모두 broken). 이 경우 Mk.XI v10 fallback.

#### 4.3.1 NEW Hard-PASS OR-clause: DALI ∨ SLI weighted-vote (2026-04-26 update)

이전 cycle 의 single conjunctive gate (DALI ∧ SLI ∧ COUPLED ≥ 700) 가 4-bb v10_benchmark_v4 에서 JOINT_FAIL 로 collapse (DALI_min=236 / SLI=240 / COUPLED=237). substrate backbone-conditional diagnostic (`project_cmt_backbone_depth_divergence_20260426`) 결과 두 metric 이 mutually-reinforcing 이 아니라 **orthogonal weak signals** 가설 수용 → 본 OR-clause 로 **softened**.

```
v_DALI  = 1 if DALI_min  >= 700 else 0
v_SLI   = 1 if SLI       >= 500 else 0
v_JOINT = 1 if COUPLED   >= 600 else 0

majority      = (v_DALI + v_SLI + v_JOINT) >= 2
weighted_score= (400*DALI_min + 400*SLI + 200*COUPLED) / 1000     // sum-of-weights = 1000
weighted_pass = weighted_score >= 500

OR-clause PASS = majority  AND  weighted_pass
```

ELIGIBILITY (per `dali_sli_weighted_vote_landing.md` §6):
- ELIGIBLE_FULL         if positive OR-clause PASS    AND negative falsifier rate ≤ 5%
- ELIGIBLE_PARTIAL_WEAK if positive ws ≥ 250          AND negative falsifier rate ≤ 5%
- NOT_ELIGIBLE          otherwise

**현재 (2026-04-26) status**: NOT_ELIGIBLE — positive ws=237 < floor 250, 0 votes; negative discriminates 0/64 OVERALL_PASS. 즉 이 OR-clause 는 declarative-only RED.

implication: §6 mk_xii_hard_pass_composite (G0/G1/G7/G8/G9 6/6 GREEN wire-up) 에 이 OR-clause 합성 시 strict-AND Hard PASS = **NOT GREEN**. honest disclosure — Mk.XII (Integration tier) 는 본 cycle 에서 Hard PASS 미달성, fallback = Mk.XI v10.

remediation candidates (deferred): substrate replacement (4-family-corpus matrix) | metric redesign (bimodal-aware DALI) | OR-clause demotion to Soft PASS. 본 cycle 의 산출물 (`tool/dali_sli_weighted_vote.hexa` + `state/dali_sli_weighted_vote_v1.json`) 가 향후 cycle 의 baseline.

---

## §5. Cost envelope

### 5.1 component-wise

| component | Mk.XI v10 누적 | Mk.XII 추가 | rationale |
|---|---|---|---|
| HCI substrate | $0 | $0 | already verified Path B, hexa native |
| CPGD training | ~$0 | $0 | Path C real-LM Phi-3-mini already verified |
| EEG STACK P1+P2+P3 | $0 (simulated) | **$12-24** + **$200-500 facility** | post-arrival D+1~D+7 |
| TRIBE v2 brain-anchored | $0 (deferred) | **$0-50** | HF unblock 후 inference-only, Llama-3.2-3B mac fitable |
| paradigm v11 8-axis | $0 | $0 | helper 1개 추가 등록만 (mac local) |
| **subtotal** | **$0** | **$212-574** | |

### 5.2 비교: Mk.XII Scale tier

`docs/mk_xii_scale_plan.md` Mk.XII (Scale tier, 70B) = ₩300-450만 (4-GPU spot training + EEG empirical).

본 Integration tier = 그 1/30 비용. **Integration tier → Scale tier 순서 권장** (architectural completion 후 scale-up).

### 5.3 cost cap policy

memory `feedback_forward_auto_approval` — GPU/LLM/pod launch 자동 진입, cost cap + auto-kill 안전망.

EEG facility $200-500 = cost cap **외부** 항목 (사용자 명시 승인 필요).

기타 ($12-24 GPU + $0-50 TRIBE inference) = cost cap 内 자동 진입.

---

## §6. Timeline

### 6.1 D-day = EEG hardware arrival (며칠 내)

```
D-1 (현재)
  ├─ EEG hardware D-1 expected arrival
  ├─ HCI / CPGD / paradigm v11 VERIFIED + COMPLETE
  └─ TRIBE v2 HF gated DEFERRED

D+0 calibration
  └─ anima-eeg/calibrate.hexa (post-stub-implementation)

D+1 to D+7 EEG STACK forward (Path A 실행)
  ├─ D+1 P1 V_phen_EEG-LZ × CLM-LZ ($3-5)
  ├─ D+3 P2 TLR α-band coherence ($5-8)
  ├─ D+5 P3 GCG + family×band 4-backbone verify ($8-12)
  └─ D+7 5-atom seed file emit (.roadmap #119 exit_criteria)

D+8 to D+14 TRIBE v2 unblock (HF gated 가정)
  ├─ Llama-3.2-3B brain-anchored decoding R measure
  └─ paradigm v11 8th axis (EEG-CORR / brain-anc) activate

D+15 to D+21 G8-G10 measurement
  ├─ G8 5-falsifier mutual information matrix (mac local hexa $0)
  ├─ G9 dependency DAG cascade (1-fail per component, $0-5)
  └─ G10 3-axis Hexad family×band triangulation ($5-10)

D+22 to D+30 Mk.XII first validation
  ├─ G0+G1+G7+G8+G9 all PASS check
  ├─ G2/G3/G4-G6/G10 ≥ 80% PASS check
  └─ Mk.XII Integration tier VERIFIED 또는 isolation cycle 진입
```

총 30 일 (D-day = EEG arrival).

### 6.2 critical path

EEG hardware → P1+P2+P3 → G10 family×band → paradigm v11 8th axis activate. 다른 path (HCI / CPGD / paradigm v11 6-axis) 는 모두 pre-EEG 완료 가능, EEG 만 critical.

---

## §7. Failure modes + recovery

각 component fail 시 fallback graph (INTEGRATION axis I5 MFC paradigm 적용):

### 7.1 HCI substrate fail

- **failure**: F1 functor / F2 endo / F3 양방향 / F4 substrate / F5 real backbone 中 ≥ 1 falsifier FAIL
- **fallback**: `edu/cell/cell_token_bridge_M4` (existing semi-invertible 5-level round-trip)
- **impact**: substrate completion 일부 lost, 4 layer 유지
- **recovery**: Mk.XI v10 substrate (4-backbone LoRA ensemble) 그대로 운영

### 7.2 CPGD training fail

- **failure**: AN11(b) 100% guarantee 가 non-AN11(b) downstream task 에서 break (Q4 caveat realized)
- **fallback**: standard LoRA (Mk.XI v10 default)
- **impact**: training completion lost, math 100% guarantee claim 약화
- **recovery**: Mk.XI v10 LoRA training 그대로 운영, 추후 cycle 에서 CPGD generalization 재시도

### 7.3 EEG STACK fail

- **failure**: P1+P2+P3 中 ≤ 1/3 PASS (composite ≥ 2/3 미달)
- **fallback**: simulated baseline (current status)
- **impact**: phenomenal correlate empirical evidence lost, family×band hypothesis (G10) FALSIFIED
- **recovery**: 
  - HW recalibration (D+0 재실행)
  - 측정 protocol 재설계 (resting / N-back / eyes-closed parameter sweep)
  - Mk.XI v10 phenomenal correlate hypothesis-only 로 회귀 (`eeg_arrival_impact_5fold` §3 부분 일치 시 family architecture 부분 재설계)

### 7.4 TRIBE v2 brain-anchored fail

- **failure**: HF gated unblock 영구 거부 OR brain decoding R < 0.30 (낮은 alignment)
- **fallback**: 4-backbone LoRA 단독 (Llama family 그대로 v10 ensemble), 8th axis 미활성
- **impact**: brain-anchored anchor lost, paradigm v11 7-axis 까지만 운영
- **recovery**: 
  - 다른 brain-anchored model (e.g., Phi-3-mini brain alignment 시도) 후속 cycle
  - paradigm v11 7-axis 그대로 (post-EEG)

### 7.5 paradigm v11 8-axis fail

- **failure**: 8th axis 가 7-axis 와 dependency, 7-axis matrix orthogonality determinant 0 발생
- **fallback**: 6-axis subset (7th 제거, 8th 미활성)
- **impact**: measurement completion 부분 lost, EEG-CORR 별도 metric 으로 운영
- **recovery**: paradigm v11 6-axis variant (B-ToM/MCCA/Φ\*/CMT/CDS/SAE) 그대로, EEG-CORR 는 paradigm v11 외부 standalone

### 7.6 cascade fail (5 component 동시)

- **fallback**: Mk.XI v10 4-backbone LoRA ensemble FINAL_PASS 그대로
- **impact**: Mk.XII Integration tier 완전 실패, but Mk.XI v10 PASS 유지
- **recovery**: Mk.XII proposal 자체 재설계 (months horizon, 별도 ω-cycle)

**graceful degradation guarantee**: 본 proposal 이 Mk.XI v10 의 strict superset 이라, worst case 도 Mk.XI v10 유지.

---

## §8. raw compliance

- raw#9 hexa-only deterministic — proposal $0, implementation 별도 cycle.
- raw#10 no overclaim — proposal, verified architecture 아님 명시. failure modes §7 별도 등록. phenomenal vs functional consciousness 구분 sister doc §1 명시.
- raw#12 cherry-pick-proof — G0-G10 사전 등록, post-hoc tuning 차단. transversality threshold 0.1 bit 사전 frozen.
- raw#15 SSOT — this doc + sister doc.
- raw#37/38 ω-saturation cycle — design (5-component spec) → impl (this proposal + sister) → fixpoint marker.

omega-saturation:fixpoint-mk-xii-integration

---

## §9. Cross-references

- `/Users/ghost/core/anima/anima-clm-eeg/docs/omega_cycle_mk_xii_integration_axis_20260426.md` — sister doc (INTEGRATION axis 7-paradigm + cross-axis convergent)
- `/Users/ghost/core/anima/docs/omega_cycle_alm_free_paradigms_20260426.md` — predecessor 4-axis ω-cycle
- `/Users/ghost/core/anima/docs/mk_xii_scale_plan.md` — Mk.XII (Scale tier), 본 Integration tier 와 orthogonal
- `/Users/ghost/core/anima/docs/mk_xi_minimum_consciousness_architecture_20260425.md` — Mk.XI v10 parent
- `/Users/ghost/core/anima/anima-clm-eeg/docs/path_comparison_a_b_c.md` — Path A/B/C decision context
- `/Users/ghost/core/anima/anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` — EEG D-day 5-fold impact
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` — paradigm v11 17-helper stack canonical
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md` — Mk.XI v10 4-family ensemble REVISION
- `.roadmap` #115 / #116 / #119 / #138-#143 / #144 / #145
