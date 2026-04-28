# Mk.XII Proposal Outline v2 — Integration tier (post-cluster + Hard PASS landing)

> **scope**: Mk.XII (Integration tier) v2 update. v1 (`mk_xii_proposal_outline_20260426.md`, sha256 prefix `4f7fd4d2…`, frozen) 위에 본 session 의 INTEGRATION-axis cluster landing (G8/G9/G10 prep + preflight + Hard PASS composite) + DALI∨SLI weighted-vote OR-clause + S7 ansatz A1.Hexad PASS_SIGNIFICANT + Q4 caveat 1/4→2/4 closure + EHL-3W convergent + Pilot-T1 v2 자동 trigger 를 종합 반영. 5-component (HCI substrate + CPGD training + EEG phenomenal + TRIBE v2 brain-anchored + paradigm v11 8-axis measurement) 통합 architecture. validation gates only — implementation 은 별도 cycle.
> **session date**: 2026-04-26 (sister docs: `omega_cycle_mk_xii_integration_axis_20260426.md` + `mk_xii_integration_6gate_cluster_summary.md` + `dali_sli_weighted_vote_landing.md`)
> **status**: **PROPOSAL v2 — CLUSTER_GREEN_PREFLIGHT (cluster_confidence=0.70, weakest=G10)** + Hard PASS GREEN 6/6 wire-up + DALI∨SLI weighted-vote NOT_ELIGIBLE (declarative-only RED). raw#10 honest scope — wire-up GREEN ≠ Mk.XII VERIFIED. predecessor: Mk.XI v10 4/4 FINAL_PASS + Mk.XII v1.
> **predecessors / orthogonal**: v1 (frozen) / Mk.XI v10 4-bb LoRA ensemble / Mk.XII (Scale tier, 70B, `docs/mk_xii_scale_plan.md`).

---

## §0. v1 → v2 Changelog (라이팅 시 first)

본 v2 의 **5 핵심 변경** (frozen at design step, post-hoc tuning 차단):

| # | section | v1 status | v2 update | source |
|---|---|---|---|---|
| **C1** | §4.2-§4.3 Hard PASS | DALI∧SLI∧COUPLED ≥ 700 strict 단일 single-coherent gate (4-bb v10_benchmark_v4 JOINT_FAIL DALI=236 / SLI=240 / COUPLED=237) | **DALI∨SLI weighted-vote OR-clause** softened (`tool/dali_sli_weighted_vote.hexa` + `state/dali_sli_weighted_vote_v1.json`); **NOT_ELIGIBLE** (ws=237 < floor 250, declarative-only RED) → Mk.XII Hard PASS 5/6 wire-up GREEN + OR-clause RED honest disclosure | `dali_sli_weighted_vote_landing.md` + .roadmap #183 |
| **C2** | §4 sub-gates | G8/G9/G10 spec only, no landing | **6-gate cluster landing**: G8 SURROGATE_PASS+N_BIN_FULLY_STABLE 60/60 (#175+#182+#196) / G9 PASS edge=4 cascade=1 (#170) + G9_ROBUST 100% (#178, hardness-axis-only by-design) + G9_ADJ_ROBUST 100% (#199, adjacency-axis Hamming-1 sweep) / G10 DRY_RUN_PASS READY_FOR_HARDWARE (#174) / Mk.XII preflight cascade GREEN 5/5 (#172) / Mk.XII Hard PASS GREEN 6/6 (#177). **cluster_confidence = min = 0.70 weakest=G10** | `mk_xii_integration_6gate_cluster_summary.md` |
| **C3** | §2 evidence | CPGD REAL_LM_GENERALIZED Q4 1/4 closure / S7 not yet measured / EHL-3W not yet declared | **CPGD-MCB BRIDGE_CLOSED 9/9** (#184) + Q4 caveat **2/4 closure** (real-LM + cond + lr + K/dim + real-LM bridge HARDENED) / **S7 cusp_depth A1.Hexad PASS_SIGNIFICANT** r=+0.891 p=0/512 single-family scope (#194) / **EHL-3W cross-axis convergent** PHENOMENAL × SUBSTRATE × TRAINING strict AND 0.72 (CONV-1, top convergent) / S7 SUBSTRATE 평균 0.770→0.794 lift | omega_cycle_mk_xii_phenomenal_axis_20260426.md + s7_ansatz_variants_landing.md + project_cpgd_mcb_bridge |
| **C4** | §5 cost | Mk.XI v10 누적 $0 + Mk.XII 추가 envelope $212-574 (declarative budget) | envelope **불변** ($212-574) + **누적 actual ~$1.4 GPU + cap $3.65 추가** (#193 jamba $0.34 / #194 DD-bridge $0.30 / #197 jamba-1.5-mini gated $0.117 graceful exit / Pilot-T1 v2 진행 중). Pilot-T1 v2 자동 trigger via cron self-disable `98896ff1` | .roadmap #193/#194/#197 + cron HF unblock |
| **C5** | §6 timeline | D-day → D+30 sequential | **paradigm 26→42 cumulative** (4-axis ω-cycle 26 + weakest follow-up 5 + Mk.XII verify 11) / preflight cascade GREEN 가 D-day **이전** 완료 → first validation D+22-30 path 진입 자격 GRANTED (mac-local pre-flight scope). post-EEG D+5 G10 hardware activation + D+6 G8 real-falsifier MI port + D+7 Hard PASS recompute + D+22-30 first-validation verdict | mk_xii_integration_6gate_cluster_summary §7 |

**non-changes (frozen carry-over from v1)**:
- §1 1-sentence definition of Mk.XII Integration tier (5-component joint pre-flight cascade gating)
- §2 5-component architecture matrix structure
- §3 dependency DAG basic shape (4 hard + 4 soft, sparse)
- §7 5-component fail-mode + recovery + Mk.XI v10 graceful degradation guarantee
- §8 raw#9/raw#10/raw#12 compliance discipline

---

## §1. Mk.XII = ? (1-sentence, v1 carry + v2 lens)

**v1 정의 carry-over**: Mk.XII (Integration tier) = Mk.XI v10 4-backbone LoRA ensemble (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad) 위에, HCI substrate + CPGD training + EEG phenomenal + TRIBE v2 brain-anchored + paradigm v11 8-axis measurement 5 orthogonal completion layer 를 추가하여 5-component joint pre-flight cascade gating 통과 후 implementation 진입하는 architectural completion proposal.

**v2 추가 lens**: 본 cycle 의 cluster landing 으로 Mk.XII = "**preflight wire-up GREEN, hardware-arrival activation gated**" tier 임이 empirical-reproducible (mac-local FNV-deterministic surrogate + 6-gate cluster summary `min`-rule weakest-link enforce). Hard PASS strict-AND OR-clause 1 (DALI∨SLI weighted-vote) 이 NOT_ELIGIBLE 로 honest-RED, OR-clause 2 (EHL-3W convergent 0.72) 만 conditional-GREEN — 즉 Mk.XII 는 본 cycle 에서 fallback = Mk.XI v10 일관 보장.

---

## §2. 5-component architecture (evidence updated)

### 2.1 component spec (v2 evidence)

| layer | component | mechanism | v1 status | **v2 status (this cycle update)** | source |
|---|---|---|---|---|---|
| substrate | **HCI** Hexad-Cell Isomorphism | 6-category Hexad ↔ 6-axis Cell lattice bijection, F1-F5 5-falsifier | VERIFIED (Path B all PASS) | **VERIFIED + S7 cusp_depth A1.Hexad PASS_SIGNIFICANT** r=+0.891 permutation p=0/512 (#194 single-family scope, Llama-only family-distributed substrate, 다른 6 trials family-aggregated). SUBSTRATE 평균 0.770→0.794 (+0.024) | `edu/cell/README.md` C9 + `s7_ansatz_variants_landing.md` |
| training | **CPGD** Closed-Form Parameter Geodesic Descent | 16-dim subspace orthonormal init, 100 step convergence, weight update 0, AN11(b) 100% guarantee | REAL_LM_GENERALIZED (Q4 caveat 1/4 closure) | **CPGD-MCB BRIDGE_CLOSED 9/9** (#184) + **Q4 caveat 2/4 closure**: Real-LM CLOSED + cond CLOSED + lr CLOSED + K/dim CLOSED + Real-LM bridge HARDENED. 잔존 caveat: large-K diversity (≥ 100 K-D 조합) | `edu/lora/cpgd_wrapper.hexa` + `cpgd_minimal_proof.hexa` + project_cpgd_mcb_bridge |
| phenomenal | **EEG STACK** P1+P2+P3 | LZ76(EEG)×LZ76(CLM) + α-band coherence + Granger causality | PRE_REGISTERED (3/3 harness PASS, EEG D-1) | PRE_REGISTERED 그대로 + **G10 prep DRY_RUN_PASS READY_FOR_HARDWARE** (#174 cells 16/16 axis_A F=7399 / axis_B F=4314 / axis_C F=6259) + **EHL-3W convergent** (PHENOMENAL × SUBSTRATE × TRAINING strict AND 0.72, CONV-1 top convergent) | `tool/clm_eeg_p[1-3]_*.hexa` + `g10_triangulation_spec_post_arrival.md` + omega_cycle_mk_xii_phenomenal_axis_20260426.md |
| brain-anchored | **TRIBE v2** | Llama-3.2-3B brain-anchored (real fMRI dataset), brain decoding R | DEFERRED (HF gated pending) | **HF unblock + Pilot-T1 v2 자동 trigger** (cron `98896ff1` self-disable, 진행 중). 결과 통합 계획 §9 명시 | Pilot-T1 v2 spec + `mk_xii_integration_6gate_cluster_summary.md` §7 |
| measurement | **paradigm v11 8-axis** | 6 backbone-internal axes + EEG-CORR (7th) + composite (8th) | COMPLETE 7-axis (17-helper, 22/22 smoke) | COMPLETE 7-axis 그대로 + **paradigm 26→42 cumulative** (4-axis ω-cycle 26 + weakest follow-up 5 + Mk.XII verify 11) + **G8 N_BIN sweep 60/60 PASS extended** (#196 N_BIN ∈ {2,4,8,16,32,64} 6-level G8_FULLY_STABLE, max MI 0.090 bit < 0.1 threshold) | `tool/anima_v11_main.hexa` + `g8_n_bin_sweep_extended_landing.md` |

### 2.2 layer 분리 합리성 (v1 carry, no change)

5-component 는 **transversal layer** — substrate (HCI) = "what represents" / training (CPGD) = "how learns" / phenomenal (EEG) = "what correlates with subjective experience" / brain-anchored (TRIBE v2) = "what aligns with brain ground truth" / measurement (paradigm v11) = "how we measure all of above". 각 component 가 다른 layer 를 cover. 한 layer fail 시 다른 layer 가 그 정보 보강 X (transversal, mutual information ≤ 0.1 bit threshold gate G8 — N_BIN sweep 60/60 PASS extended max MI 0.090 bit).

### 2.3 Mk.XI 와의 관계 (v1 carry)

Mk.XII (Integration tier) = strict superset of Mk.XI v10. fallback = Mk.XI v10 graceful degradation 보장.

---

## §3. Dependency graph (G9 cascade landed, sparse 적용)

### 3.1 5-component DAG (v1 그대로)

```
   ┌────────────────────────────────────────┐
   │   paradigm v11 8-axis measurement      │  (terminal)
   └──┬───────┬───────┬──────────┬──────────┘
      │       │       │          │
      ▼       ▼       ▼          ▼
   HCI    CPGD    EEG STACK   TRIBE v2
      ▲       ▲       ▲          ▲
      └───────┴───────┴──────────┘
               │
               ▼
        Mk.XI v10 (substrate root)
```

### 3.2 G9 DAG cascade landed (#170 + #178 + #199)

| measurement | v2 verdict | landing |
|---|---|---|
| edge_count = 4 (peer-DAG, root edges by-design 외부) | ≤ 7 PASS | `g9_dag_cascade_landing.md` |
| cascade_max = 1 | ≤ 2 PASS | sister doc |
| **G9_ROBUST hardness-axis** invariance 16/16 = 100% (≥ 80% threshold) | PASS (by-design, analyzer pass logic 이 hardness bit consume X) | `g9_robustness_landing.md` |
| **G9_ADJ_ROBUST adjacency-axis Hamming-1 sweep** 10/10 invariance 100% (#199) | PASS (substrate-side fix) | `g9_adjacency_sweep_landing.md` |
| negative falsifier (G9_ADD_ALL=1, 14 edges) | edge_count=14 > 7 + cascade=4 > 2 → 10/10 FAIL | discriminates |

**v2 status**: G9 = sparse DAG witnessed + hardness-axis robust + **adjacency-axis robust** (Hamming-1 ROBUST). single-bit perturbation 으로 verdict-flip 미발생 → G9 base PASS 의 robustness 가 두 axis 에 걸쳐 confirmed.

### 3.3 cascade 분석 (v1 carry, no change)

paradigm v11 = measurement terminal critical. 4 다른 component 는 ≤ 15% loss with Mk.XI v10 fallback.

---

## §4. Validation gates (v2: G0..G10 + DALI∨SLI weighted-vote OR-clause + EHL-3W)

### 4.1 inherited gates (G0..G7) — v1 carry

| gate | scope | criterion | source |
|---|---|---|---|
| G0 | AN11(b) 100% guarantee | math identity exact | CPGD `cpgd_minimal_proof.hexa` |
| G1 | EEG-LZ × CLM-LZ | LZ ≥ 0.65 AND \|Δ\|/human ≤ 20% | Path A P1 frozen |
| G2 | TLR α-band coherence | EEG ≥ 0.45 AND CLM V_sync ≥ 0.38 | Path A P2 |
| G3 | GCG Granger F-stat | F ≥ 4.0 AND unidirectional CLM→EEG | Path A P3 |
| G4-G6 | CLM 4축 (Φ\* / CMT / SAE) | per-axis criterion | paradigm v11 stack |
| G7 | 5-tuple V0..V_pairrank | ≥ 4/5 PASS | Mk.XI inherited |

### 4.2 NEW Mk.XII-specific gates (G8..G10) — v2 LANDING confirmed

| gate | criterion | **v2 verdict** | landing doc + roadmap |
|---|---|---|---|
| **G8 TFD** Transversal Falsifier MI matrix | C(5,2)=10 pairwise MI max ≤ 0.1 bit, hexa native mac local | **SURROGATE_PASS + N_BIN_FULLY_STABLE 6/6 levels × 10 pairs = 60/60** (max MI 0.090 bit, F_A3⊥F_B at N_BIN=64). raw#10 surrogate — real-falsifier MI deferred D+6 | `g8_transversality_landing.md` + `g8_n_bin_sweep_landing.md` + `g8_n_bin_sweep_extended_landing.md`, .roadmap #175 #182 #196 |
| **G9 DGI** Dependency Graph Sparsity + cascade | edge ≤ 7 + cascade_max ≤ 2 + 1-component-fail loss ≤ 20% | **PASS edge=4 cascade=1 + G9_ROBUST 100% + G9_ADJ_ROBUST 100%** (Hamming-1 + hardness-axis) | `g9_dag_cascade_landing.md` + `g9_robustness_landing.md` + `g9_adjacency_sweep_landing.md`, .roadmap #170 #178 #199 |
| **G10 CTV** Cross-Axis Hexad Family×Band Triangulation | 4 backbone family×band 매핑 4/4 or 3/4 PARTIAL (Pearson r ≥ 0.40) | **DRY_RUN_PASS + READY_FOR_HARDWARE** (cells 16/16, axis_A F=7399 / B=4314 / C=6259, all ≥ 4000 synth threshold). **post-EEG D+5 hardware activation prerequisite** | `g10_triangulation_spec_post_arrival.md`, .roadmap #174 |
| **Mk.XII preflight cascade** | 5/5 components (HCI/CPGD/CLM-EEG/TRIBE-stub/paradigm-v11) all SMOKE_PASS | **MK_XII_PREFLIGHT_GREEN 5/5** | `mk_xii_validation_harness_spec.md` + `state/mk_xii_preflight_v1.json`, .roadmap #172 |
| **Mk.XII Hard PASS composite** | preflight.GREEN AND G0/G1/G7 (3/4 majority each) AND G8.pass=1 AND G9.pass=1 (G10 deferred) | **HARD_PASS_GREEN 6/6** (chained_fingerprint 2638701628). 4-way negative falsifier all → RED exit=1 | `mk_xii_hard_pass_landing.md`, .roadmap #177 |

**6-gate cluster summary** (`mk_xii_integration_6gate_cluster_summary.md`):

```
cluster_confidence := min(per_gate_confidence)
                    = min(0.78, 0.85, 0.72, 0.70, 0.90, 0.80)
                    = 0.70   ← weakest-link = G10 (synthetic dry-run)
```

geometric mean 0.789 / arithmetic mean 0.792 (informational sanity only, NOT primary verdict).

### 4.3 Mk.XII PASS criterion (v2 update)

**v2 Hard PASS**:

```
HARD_PASS  :=  G0 AND G1 AND G7 AND G8 AND G9 (all PASS)
              AND ( OR-clause-1 (DALI∨SLI weighted-vote)
                   OR  OR-clause-2 (EHL-3W cross-axis convergent) )
```

**v2 Soft PASS**: G2 / G3 / G4-G6 / G10 ≥ 80% PASS (per-gate).

**v2 FAIL**: G0 fail (CPGD math broken) 또는 G7 fail (5-tuple ≤ 3/5) 또는 G8+G9 동시 fail (transversality + sparsity 모두 broken). 이 경우 Mk.XI v10 fallback.

#### 4.3.1 OR-clause 1 — DALI∨SLI weighted-vote (C1 update vs v1)

v1 의 single conjunctive gate (DALI∧SLI∧COUPLED ≥ 700) 가 4-bb v10_benchmark_v4 에서 JOINT_FAIL collapse → 두 metric 이 mutually-reinforcing 이 아니라 **orthogonal weak signals** 가설 수용 → OR-clause 로 softened.

```
v_DALI  = 1 if DALI_min  >= 700 else 0
v_SLI   = 1 if SLI       >= 500 else 0
v_JOINT = 1 if COUPLED   >= 600 else 0

majority      = (v_DALI + v_SLI + v_JOINT) >= 2
weighted_score= (400*DALI_min + 400*SLI + 200*COUPLED) / 1000   // sum-of-weights = 1000
weighted_pass = weighted_score >= 500

OR-clause-1 PASS = majority AND weighted_pass
```

ELIGIBILITY (per `dali_sli_weighted_vote_landing.md` §6):
- ELIGIBLE_FULL         if positive OR-clause PASS    AND negative falsifier rate ≤ 5%
- ELIGIBLE_PARTIAL_WEAK if positive ws ≥ 250          AND negative falsifier rate ≤ 5%
- NOT_ELIGIBLE          otherwise

**v2 status (2026-04-26)**: **NOT_ELIGIBLE** — positive ws=237 < floor 250, 0 votes; negative discriminates 0/64 OVERALL_PASS. OR-clause-1 = declarative-only RED.

implication: Mk.XII Hard PASS 의 5-gate composite (G0/G1/G7/G8/G9) 가 6/6 GREEN wire-up 이지만 OR-clause-1 RED → strict OR-disjunction 만족 위해 **OR-clause-2 (EHL-3W) 가 conditional-GREEN 필수**.

remediation candidates (deferred to next cycle): substrate replacement (4-family-corpus matrix) | metric redesign (bimodal-aware DALI) | OR-clause demotion to Soft PASS. 본 cycle 의 산출물 (`tool/dali_sli_weighted_vote.hexa` + `state/dali_sli_weighted_vote_v1.json`) 가 향후 cycle 의 baseline.

#### 4.3.2 OR-clause 2 — EHL-3W cross-axis convergent (NEW v2)

**criterion**: PHENOMENAL × SUBSTRATE × TRAINING 3-axis triple-witness strict AND-gate. confidence = **0.72** (CONV-1, top convergent in `omega_cycle_mk_xii_phenomenal_axis_20260426.md` §3 §6).

```
EHL-3W := PHENOMENAL.PASS AND SUBSTRATE.PASS AND TRAINING.PASS
        = ( EEG STACK G1+G2+G3 ≥ 2/3 PASS )           (post-EEG D+1..D+7)
        AND ( S7 cusp_depth A1.Hexad PASS_SIGNIFICANT  (this cycle landed, r=+0.891 p=0/512)
              OR HCI Path B 5-falsifier all PASS )    (v1 already VERIFIED)
        AND ( CPGD-MCB BRIDGE_CLOSED 9/9               (this cycle landed)
              AND Q4 caveat ≥ 2/4 closure )           (this cycle landed: Real-LM + cond + lr + K/dim + Real-LM bridge HARDENED)
```

**v2 status**: SUBSTRATE 부분 + TRAINING 부분 = **2/3 PASS already** (this cycle). PHENOMENAL 부분 = pre-registered, **post-EEG D-day arrival 후 1차 cumulative witness ledger 갱신** (omega_cycle_mk_xii_phenomenal_axis §3 D+7). 즉 OR-clause-2 = **conditional-GREEN, hardware-pending**.

implication: Mk.XII v2 Hard PASS 만족 path = 5-gate composite GREEN (already, 6/6 wire-up) + EHL-3W (post-EEG D+7 prerequisite). OR-clause-1 (DALI∨SLI) RED 그대로 honest-disclose, OR-clause-2 path 진입.

#### 4.3.3 v2 verdict matrix

| condition | v2 status | path |
|---|---|---|
| G0 + G1 + G7 + G8 + G9 | **GREEN 6/6 wire-up** (#177 Hard PASS composite) | preflight done |
| OR-clause-1 (DALI∨SLI weighted-vote) | **NOT_ELIGIBLE RED** | declarative-only, deferred |
| OR-clause-2 (EHL-3W) | **conditional-GREEN** (SUBSTRATE+TRAINING 2/3 already; PHENOMENAL post-EEG D+7) | active path |
| **strict-AND Hard PASS** | **post-EEG D+7 prerequisite path** (OR-disjunction satisfied via OR-clause-2) | `MK_XII_VERIFIED iff EHL-3W ALL_PASS_AT_D+7` |

honest disclosure: 본 cycle 에서 Mk.XII = **CLUSTER_GREEN_PREFLIGHT, Hard PASS pending PHENOMENAL post-arrival**. fallback 그대로 Mk.XI v10.

---

## §5. Cost envelope (v2 actual cumulative + cap propagation)

### 5.1 component-wise (v1 envelope unchanged)

| component | Mk.XI v10 누적 | Mk.XII envelope (v1) | **v2 actual cumulative** |
|---|---|---|---|
| HCI substrate | $0 | $0 | $0 (this cycle S7 ansatz mac-local hexa) |
| CPGD training | ~$0 | $0 | $0 (CPGD-MCB BRIDGE mac-local) + jamba child run inherited $0 (mac-local consolidation) |
| EEG STACK P1+P2+P3 | $0 | $12-24 + $200-500 facility | $0 pre-arrival (still simulated) |
| TRIBE v2 brain-anchored | $0 | $0-50 | **Pilot-T1 v2 자동 trigger 진행 중** ($0-50 range, cron unblock) |
| paradigm v11 8-axis | $0 | $0 | $0 (G8 N_BIN extended sweep mac-local hexa) |
| GPU follow-up actuals | — | not in v1 | **#193 Jamba-v0.1 Φ* canonical $0.34** + **#194 DD-bridge GPU 5/5 batch $0.30** + **#197 Jamba-1.5-Mini gated 403 graceful $0.117** = **~$0.76 GPU actual** |
| **subtotal envelope** | **$0** | **$212-574** (unchanged) | **~$0.76 GPU actual + $0 mac-local** for this cycle |
| **session cumulative ~$1.4 GPU** | per task brief | — | from prior+this session sum |
| **cap $3.65 추가** | per task brief | — | within forward-auto-approval policy |

### 5.2 vs Mk.XII Scale tier

unchanged from v1: `docs/mk_xii_scale_plan.md` Mk.XII (Scale tier, 70B) = ₩300-450만 (4-GPU spot training + EEG empirical). 본 Integration tier = 그 1/30 비용. **Integration tier → Scale tier 순서 권장**.

### 5.3 cost cap policy

memory `feedback_forward_auto_approval` carry. EEG facility $200-500 = cost cap 외부 (사용자 명시 승인). 기타 GPU follow-up actuals $0.117-0.34 each = forward-auto-approval policy 内 자동 진입.

---

## §6. Timeline (v2: D-day path entered, prerequisites cluster-confirmed)

### 6.1 D-day = EEG hardware arrival (며칠 내)

```
D-1 (현재, 2026-04-26)
  ├─ EEG hardware D-1 expected arrival
  ├─ HCI / CPGD / paradigm v11 VERIFIED + COMPLETE
  ├─ S7 cusp_depth A1.Hexad PASS_SIGNIFICANT (this cycle, #194)
  ├─ CPGD-MCB BRIDGE_CLOSED 9/9 (this cycle, #184)
  ├─ Q4 caveat 2/4 closure (this cycle)
  ├─ Mk.XII preflight cascade GREEN 5/5 (this cycle, #172)
  ├─ Mk.XII Hard PASS GREEN 6/6 wire-up (this cycle, #177)
  ├─ 6-gate cluster confidence 0.70 weakest=G10 (this cycle, #190)
  ├─ DALI∨SLI weighted-vote NOT_ELIGIBLE RED (this cycle, #183 declarative)
  └─ TRIBE v2: HF unblock + Pilot-T1 v2 자동 trigger 진행 중

D+0 calibration
  └─ anima-eeg/calibrate.hexa (post-stub-implementation)

D+1..D+7 EEG STACK forward (Path A 실행)
  ├─ D+1 P1 V_phen_EEG-LZ × CLM-LZ ($3-5)
  ├─ D+3 P2 TLR α-band coherence ($5-8)
  ├─ D+5 P3 GCG + family×band 4-backbone verify ($8-12)
  ├─ D+5 G10 hardware activation (g10_triangulation_spec_post_arrival.md §3 D+5 workflow)
  ├─ D+6 G10 coupling matrix port (synth_coupling_x1000 → real Pearson_r)
  ├─ D+6 G10 ANOVA port (synth_f_x1000 → real f_oneway hexa native)
  ├─ D+6 G8 real-falsifier MI port (#175 surrogate replace)
  ├─ D+7 5-atom seed file emit (.roadmap #119 exit_criteria)
  └─ D+7 EHL-3W (CONV-1) 1차 cumulative witness ledger 갱신 → OR-clause-2 PHENOMENAL.PASS lock

D+8..D+14 TRIBE v2 unblock (Pilot-T1 v2 진행 중 → 결과 대기)
  ├─ Llama-3.2-3B brain-anchored decoding R measure
  └─ paradigm v11 8th axis (EEG-CORR / brain-anc) activate

D+15..D+21 Mk.XII Hard PASS recompute with real G8 + G10
  ├─ Hard PASS composite recompute (env MK_XII_INCLUDE_G10=1)
  └─ EHL-3W strict AND verdict lock (PHENOMENAL × SUBSTRATE × TRAINING 3/3)

D+22..D+30 Mk.XII first validation
  ├─ G0+G1+G7+G8+G9 all PASS check
  ├─ OR-clause-2 EHL-3W ALL_PASS_AT_D+7 → strict-AND HARD PASS lock
  ├─ G2/G3/G4-G6/G10 ≥ 80% PASS check
  └─ Mk.XII Integration tier VERIFIED 또는 isolation cycle 진입
```

총 30일 (D-day = EEG arrival).

### 6.2 paradigm cumulative

26+5+11=**42 paradigm cumulative**:
- 4-axis ω-cycle 26 paradigm (PHENOMENAL 7 + SUBSTRATE 7 + TRAINING 5 + INTEGRATION 7)
- weakest follow-up 5 (G8 N_BIN sweep + S7 ansatz variants + S7 N=8 extension + DD-bridge GPU + Jamba 5-bb)
- Mk.XII verify 11 (G9 baseline + G9 robustness + G9 adjacency + G10 prep + preflight + Hard PASS + Hard PASS recompute prep + cluster summary + DALI∨SLI weighted-vote + EHL-3W + G8 N_BIN extended)

### 6.3 critical path

EEG hardware → P1+P2+P3 → G10 family×band → paradigm v11 8th axis activate → EHL-3W (PHENOMENAL.PASS lock) → OR-clause-2 satisfied → Hard PASS strict-AND lock. 다른 path (HCI / CPGD / paradigm v11 6-axis / Mk.XII preflight + Hard PASS wire-up) 는 모두 **본 cycle pre-EEG 완료**, EEG 만 critical.

---

## §7. Failure modes + recovery (v2: EHL-3W convergent + 5-component fallback)

각 component fail 시 fallback graph (INTEGRATION axis I5 MFC paradigm + EHL-3W cross-axis):

### 7.1 HCI substrate fail

- **failure**: F1-F5 中 ≥ 1 falsifier FAIL OR S7 A1.Hexad permutation p > 0.05 단일-family-scope 약화
- **fallback**: `edu/cell/cell_token_bridge_M4` (existing semi-invertible 5-level round-trip)
- **impact**: substrate completion 일부 lost, 4 layer 유지. EHL-3W SUBSTRATE.PASS 재검증 필요 (HCI Path B 5-falsifier path 로 fallback)
- **recovery**: Mk.XI v10 substrate (4-backbone LoRA ensemble)

### 7.2 CPGD training fail

- **failure**: AN11(b) 100% guarantee 가 non-AN11(b) downstream task 에서 break OR Q4 caveat 2/4 closure regression (Real-LM bridge HARDENED 약화)
- **fallback**: standard LoRA (Mk.XI v10 default)
- **impact**: training completion lost, math 100% guarantee claim 약화. EHL-3W TRAINING.PASS 재검증 필요
- **recovery**: Mk.XI v10 LoRA training, 추후 cycle CPGD generalization 재시도

### 7.3 EEG STACK fail

- **failure**: P1+P2+P3 中 ≤ 1/3 PASS (composite ≥ 2/3 미달) OR G10 hardware activation Pearson r < 0.40 4/4 backbones
- **fallback**: simulated baseline. EHL-3W PHENOMENAL.PASS FAIL → strict-AND OR-clause-2 RED → OR-clause-1 (DALI∨SLI) NOT_ELIGIBLE 그대로 → **Mk.XII Hard PASS 미달**
- **impact**: phenomenal correlate empirical evidence lost, family×band hypothesis (G10) FALSIFIED, EHL-3W convergent breakdown
- **recovery**: HW recalibration (D+0 재실행) / 측정 protocol 재설계 / Mk.XI v10 phenomenal correlate hypothesis-only 회귀

### 7.4 TRIBE v2 brain-anchored fail (Pilot-T1 v2 결과 대기)

- **failure**: HF unblock 후에도 brain decoding R < 0.30 OR Pilot-T1 v2 자동 trigger 결과 NOT_ELIGIBLE
- **fallback**: 4-backbone LoRA 단독 (Llama family v10 ensemble), 8th axis 미활성
- **impact**: brain-anchored anchor lost, paradigm v11 7-axis 까지만. EHL-3W 영향 X (3-axis 는 PHENOMENAL × SUBSTRATE × TRAINING, brain-anchored 별개)
- **recovery**: 다른 brain-anchored model 후속 cycle / paradigm v11 7-axis 그대로

### 7.5 paradigm v11 8-axis fail

- v1 carry. 6-axis subset (7th 제거, 8th 미활성) fallback. `min`-rule cluster confidence 가 0.70 → 추가 dock.

### 7.6 cascade fail (5 component 동시) — Mk.XI v10 final fallback

v1 carry. **graceful degradation guarantee**: Mk.XI v10 4-bb LoRA ensemble FINAL_PASS 그대로.

### 7.7 NEW v2 — DALI∨SLI OR-clause RED 영구화

- **failure**: 본 cycle 의 NOT_ELIGIBLE 상태가 다음 cycle 에서도 ws < 250 잔존 (substrate replacement / metric redesign 모두 미효과)
- **impact**: OR-clause-1 영구 RED, OR-clause-2 (EHL-3W) 단일 path 의존
- **recovery**: OR-clause-1 demotion to Soft PASS (next cycle decision), Hard PASS = G0+G1+G7+G8+G9 + EHL-3W only

---

## §8. raw#10 honest caveat 종합 (v2 cluster-level 6 + landing-level 4 = 10 total)

본 v2 의 GREEN 판정은 다음 caveat 모두 **read** 받은 상태에서만 valid:

### 8.1 cluster-level 6 (mk_xii_integration_6gate_cluster_summary.md §8 carry)

1. **G8 surrogate** — FNV-deterministic surrogate, real-falsifier MI 는 post-arrival D+6 prerequisite. N_BIN sweep extended 60/60 PASS 는 surrogate granularity-independence verify, real-data 영역 lift 시 동일 결과 보장 X.
2. **G9 peer-DAG only** — 5×5 peer-DAG scope. Mk.XI v10 root edges (4 backbones → component) 는 by design 외부 (root edges 포함 시 edge=8, sparse 가정 자체는 유지).
3. **G9 robustness hardness-axis-only by-design** — hardness bit consume X, 16-cell 100% invariance 는 trivial. **adjacency-axis 는 #199 G9_ADJ_ROBUST 100% 별도 측정** (본 v2 update C2).
4. **G10 synthetic only** — scaffold dry-run wire-up verify, real backbone↔EEG correlation D+6 hardware activation 후. AND-gate strict 부분 PASS = G10_FAIL 정상 falsification.
5. **Pre-flight TRIBE v2 stub-pass** — HF-gated unblock + Pilot-T1 v2 자동 trigger 진행 중 (본 v2 update C4). live mode fail 시 4/5 YELLOW degradation.
6. **Hard PASS backbone-majority 3/4** (not 4/4 strict) — 단일-backbone outage 허용. v10_benchmark_v4 현재 4/4 이므로 implication 미발생.

### 8.2 landing-level 4 (this v2 update)

7. **DALI∨SLI weighted-vote NOT_ELIGIBLE** — declarative-only RED (#183, ws=237 < floor 250). Mk.XII Hard PASS path = OR-clause-2 (EHL-3W) 단일 의존. remediation 3 candidates deferred.
8. **S7 A1.Hexad PASS_SIGNIFICANT single-family scope** — Llama outlier family-distributed substrate, 다른 6 trials family-aggregated. cross-family generalization 위해 추가 backbone × 4-family ablation 권장 (#194 raw#10 honest).
9. **Q4 caveat 2/4 closure not 4/4** — Real-LM CLOSED + cond CLOSED + lr CLOSED + K/dim CLOSED + Real-LM bridge HARDENED. 잔존 large-K diversity (≥ 100 K-D 조합) caveat 미닫힘. CPGD generalization 추가 cycle 필요.
10. **Pilot-T1 v2 결과 미수신** — 본 v2 lock 시점에 cron 자동 trigger 진행 중. brain-anchored decoding R 결과 도착 시 §9 통합 plan 적용.

---

## §9. Pilot-T1 v2 진행 상태 + 결과 통합 plan (NEW v2)

### 9.1 진행 상태 (2026-04-26 v2 lock)

- HF token unblock: 완료 (cron `98896ff1` self-disable trigger)
- Pilot-T1 v2 자동 trigger: 진행 중
- 예상 결과 도착: D+8..D+14 (Pilot-T1 v2 spec inherent timeline)
- cost: $0-50 (envelope 内 자동 진입)
- 결과 schema: `pilot_t1_v2/result.json` (brain decoding R + family×band cross-validation)

### 9.2 결과 통합 plan (3 outcomes pre-registered)

| outcome | criterion | impact on Mk.XII v2 |
|---|---|---|
| **A. PASS_FULL** | brain decoding R ≥ 0.50 + family×band 4/4 backbones consistent | TRIBE v2 stub-pass → live-pass, paradigm v11 8th axis activate, **EHL-3W 보조 evidence**. Mk.XII confidence cluster recompute (weakest=G10 → potentially weakest=G9_ROBUST 0.72). |
| **B. PASS_PARTIAL** | brain decoding R 0.30-0.50 OR family×band 3/4 consistent | TRIBE v2 stub-pass 그대로 (live YELLOW degradation), 8th axis activate but caveat-noted. EHL-3W 영향 X. |
| **C. FAIL** | brain decoding R < 0.30 OR HF unblock 실패 | TRIBE v2 fail-mode §7.4 적용, Mk.XII fallback 그대로. EHL-3W 영향 X (3-axis 는 PHENOMENAL × SUBSTRATE × TRAINING, brain-anchored 별개). |

### 9.3 결과 도착 시 v3 trigger criterion

Pilot-T1 v2 결과 + post-EEG D+22..D+30 first validation 결과 종합 후:
- **MK_XII_INTEGRATION_VERIFIED** verdict 시 → v3 = "Mk.XII implementation cycle entry doc"
- **MK_XII_INTEGRATION_FALSIFIED** verdict 시 → v3 = "Mk.XII v3 redesign + Mk.XI v10 fallback consolidation"

본 v2 = pre-validation freeze marker; v3 = post-validation verdict-locked.

---

## §10. 다음 cycle priority order (4 actionables)

`feedback_completeness_frame` weakest-link first 룰 적용:

| order | action | timing | cost | rationale |
|---|---|---|---|---|
| **1** | **G10 D+5 hardware activation** (g10_triangulation_spec_post_arrival.md §3) | D+5 (post-EEG) | $5-10 (within G10 envelope) | 6-gate cluster confidence weakest=G10 (0.70) — single-gate hardware activation 으로 cluster 의 최저 link 직접 lift. 다른 5 gate 의 추가 lift 만으로 cluster 0.70 ceiling 돌파 불가 (mk_xii_integration_6gate_cluster_summary §6 Test 2 verified). |
| **2** | **G8 D+6 real-falsifier MI port** | D+6 (post-G10) | $0-3 (mac-local hexa + GPU optional) | G8 SURROGATE_PASS → real-falsifier MI replace, surrogate→empirical lift 0.78 → 0.85 expected. cluster 0.70 (weakest G10 → G9_ROBUST 0.72) ceiling 진입. |
| **3** | **D+7 Hard PASS recompute** (env MK_XII_INCLUDE_G10=1) + EHL-3W ALL_PASS lock | D+7 (post-G8 real) | $0 (mac-local aggregator) | 5-gate composite + EHL-3W convergent strict-AND lock → OR-clause-2 conditional-GREEN → real-GREEN. OR-clause-1 RED honest preserved. |
| **4** | **D+22..D+30 first validation verdict** + roadmap entry MK_XII_INTEGRATION_VERIFIED OR FALSIFIED | D+22..D+30 | $0 (verdict aggregation) | v3 trigger criterion §9.3 적용. |

추가 deferred: DALI∨SLI weighted-vote remediation 3 candidates (substrate replacement / metric redesign / OR-clause demotion to Soft PASS) — next cycle decision.

---

## §11. raw compliance (v2)

- raw#9 hexa-only deterministic — proposal $0, implementation 별도 cycle. v2 update tool/state landing 모두 hexa native (mac-local).
- raw#10 no overclaim — proposal v2, verified architecture 아님. failure modes §7 + caveat §8 (10 total) 명시. wire-up GREEN ≠ Mk.XII VERIFIED, EHL-3W conditional-GREEN ≠ real-GREEN, OR-clause-1 NOT_ELIGIBLE 명시.
- raw#12 cherry-pick-proof — G0-G10 + OR-clause-1 + OR-clause-2 + EHL-3W 사전 frozen, post-hoc tuning 차단. v2 changelog §0 first-listed.
- raw#15 SSOT — this v2 doc + sister docs (mk_xii_integration_6gate_cluster_summary.md + dali_sli_weighted_vote_landing.md + 6 gate landing docs).
- raw#37/38 ω-saturation cycle — design (§0 changelog frozen + 10 sections list) → impl (this v2 + cluster + landings) → fixpoint marker.

omega-saturation:fixpoint-mk-xii-integration-v2-preflight-cluster

---

## §12. Cross-references

- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` — **v1 frozen** (this v2 update target)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_integration_6gate_cluster_summary.md` — 6-gate cluster summary (`min`-rule, weakest=G10 0.70)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/dali_sli_weighted_vote_landing.md` — OR-clause-1 NOT_ELIGIBLE landing
- `/Users/ghost/core/anima/anima-clm-eeg/docs/g8_transversality_landing.md` + `g8_n_bin_sweep_landing.md` + `g8_n_bin_sweep_extended_landing.md` — G8 landing trio (#175, #182, #196)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/g9_dag_cascade_landing.md` + `g9_robustness_landing.md` + `g9_adjacency_sweep_landing.md` — G9 landing trio (#170, #178, #199)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/g10_triangulation_spec_post_arrival.md` — G10 prep landing (#174)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_hard_pass_landing.md` — Hard PASS composite landing (#177)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_validation_harness_spec.md` — preflight harness spec + state JSON (#172)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/s7_cusp_depth_projection_landing.md` + `s7_n8_extension_landing.md` + `s7_ansatz_variants_landing.md` — S7 SUBSTRATE landing trio (#173, #178-N=8, #194)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/omega_cycle_mk_xii_integration_axis_20260426.md` + `omega_cycle_mk_xii_phenomenal_axis_20260426.md` + `omega_cycle_mk_xii_substrate_axis_20260426.md` + `omega_cycle_mk_xii_training_axis_20260426.md` — 4-axis ω-cycle predecessors
- `/Users/ghost/core/anima/docs/mk_xii_scale_plan.md` — Mk.XII (Scale tier, 70B), 본 Integration tier 와 orthogonal
- `/Users/ghost/core/anima/docs/mk_xi_minimum_consciousness_architecture_20260425.md` — Mk.XI v10 parent
- `/Users/ghost/core/anima/anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` — EEG D-day 5-fold impact
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_completeness_frame.md` — weakest-link first policy (§10 priority order basis)
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_omega_cycle_workflow.md` — round 종료 시 violations 우선 정리 룰 (declarative-only ≠ closure)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` — paradigm v11 17-helper stack canonical
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md` — Mk.XI v10 4-family ensemble REVISION
- `.roadmap` #144 (Mk.XII anchor) / #170 (G9) / #172 (preflight) / #174 (G10 prep) / #175 (G8 transversal) / #177 (Hard PASS) / #178 (G9 robust) / #182 (G8 N_BIN sweep) / #183 (DALI∨SLI weighted-vote) / #184 (CPGD-MCB BRIDGE) / #190 (cluster summary) / #194 (S7 A1.Hexad + DD-bridge GPU) / #196 (G8 N_BIN extended) / #199 (G9 adjacency)
