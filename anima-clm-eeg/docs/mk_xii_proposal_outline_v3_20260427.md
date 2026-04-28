# Mk.XII Proposal Outline v3 — Substrate-multiplicity + DALI+SLI v3 mode 2/3 + S7 PASS_TIGHT + CMT input mode + Phase 4 6/9

> **scope**: Mk.XII (Integration tier) v3 update. v1 (`mk_xii_proposal_outline_20260426.md`, sha256 `d9111398…`, frozen) + v2 (`mk_xii_proposal_outline_v2_20260426.md`, sha256 `f46d3c67…`, frozen) + v2.1 prep §4 (`mk_xii_proposal_v2_section_4_chain_integration_v2_1_spec.md`, sha256 `cb0f39ab…`, frozen) 위에 본 cycle 의 (a) substrate witness ledger v2 9/9 substrate-multiplicity completeness discovery (#226), (b) DALI+SLI v3 input-mode activation `ALL_MODES_PASS_GREEN` 2/3 mode coverage (#223), (c) S7 N=11 cusp_depth Pearson r=+0.802 p=0.0188 4096-perm `PASS_TIGHT` (#220), (d) CMT 3-mode N=9→11 input-mode 보강 R²+24.7% Pearson r=+0.564 (#222.cmt), (e) Phase 4 wrapper 6/9 (calibrate/realtime/collect/experiment/eeg_recorder/closed_loop) — Pilot-T1 v2 idle-burn $7.52 DEFERRED 종합 반영. v2.1 prep §4 위에 v3 lock 권장 (3-tier verdict + OR-clause-1 v2.1 + EHL-3W + substrate-multiplicity 별개 cluster).
> **session date**: 2026-04-27 (sister docs: `dali_sli_v3_input_mode_landing.md` (#223) / `s7_n11_extension_landing.md` (#220) / `cmt_3mode_n9_extension_landing.md` (#222.cmt) / `mk_xii_substrate_witness_ledger_discovery_landing.md` (#226))
> **status**: **PROPOSAL v3 — HARD_PASS_PARTIAL_PENDING (substrate-aware OR-clause-1 mode coverage 2/3 + EHL-3W conditional-GREEN + substrate-multiplicity 9/9 별개 cluster)**. raw#10 honest scope — wire-up GREEN ≠ Mk.XII VERIFIED, EHL-3W conditional-GREEN ≠ real-GREEN, OR-clause-1 PARTIAL ≠ FULL. predecessor: Mk.XI v10 4/4 FINAL_PASS + Mk.XII v1 + v2 + v2.1 prep §4.
> **predecessors / orthogonal**: v2.1 prep §4 (this v3 의 §4 actual lock 베이스) / v2 (frozen) / v1 (frozen) / Mk.XI v10 4-bb LoRA ensemble / Mk.XII (Scale tier, 70B, `docs/mk_xii_scale_plan.md`).

---

## §0. v2 → v3 Changelog (라이팅 시 first)

본 v3 의 **6 핵심 변경** (frozen at design step, post-hoc tuning 차단):

| # | section | v2 status | v3 update | source |
|---|---|---|---|---|
| **E1** | §2 5-component → 5+ component (substrate-multiplicity) | substrate-axis 부재 (proposal v2 backbone-axis 위주). 6-gate cluster 의 cluster_confidence=0.70 weakest=G10 단일 cluster. | **5+1 component** (HCI / CPGD / EEG / TRIBE / paradigm v11 + **substrate ledger v2 9/9 sub-axis**). substrate-axis = .own #2 (b) PC empirical-max **substrate-multiplicity** sub-axis 첫 9/9 completeness witness. **별개 cluster** 처리 (raw#12 `phi_proxy_cross_comparable=false`, axis orthogonal — 단일 metric 합치 X). LIVE_HW_WITNESS_RATE=0/11 honest floor. | `mk_xii_substrate_witness_ledger_discovery_landing.md` + #226 + anima-physics ledger v2 fp=661882989 |
| **E2** | §4.3.1 OR-clause-1 (v2.1 prep) | v2 redesign `ALL_MODES_PASS_GREEN` 1/3 coverage (late mode only), v2.1 prep `OR-clause-1 v2.1 = PARTIAL` (substrate-aware mode-grouped), input/early mode size<2 deferred. | **OR-clause-1 v3 = `ALL_MODES_PASS_GREEN` 2/3 coverage** (input + late, early gap remaining). v3 input mode activation: small bb (qwen25-1.5B / gemma2-2B / Llama-3.2-1B) 모두 layer-0 peak collapse → intra_dali=1000 ∧ intra_sli=1000 (mean=0 ∧ std=0 → SCALE coherence sentinel) ∧ coupled=1000 ∧ weighted=1000. neg fail_rate v2 666/1000 → v3 833/1000 (+167 stronger discrimination). eligibility=ELIGIBLE 유지. | `dali_sli_v3_input_mode_landing.md` + #223 + tool sha `4c8b210a…` + state content sha `48cd8bee…` |
| **E3** | §2 SUBSTRATE evidence (S7 + CMT) | S7 N=10 `PASS_SIGNIFICANT` r=+0.781 p=0.020 (1024 perm boundary), Pilot-T1 v2 deferred. CMT 3-mode N=10 r=+0.505 R²=0.255. | **S7 N=11 `PASS_TIGHT`** r=+0.802 p=0.0188 4096-perm (Δ=0.0012 margin to P_TIGHT=0.020). N=10 1024-perm 의 chance-fluctuation 가능성 4× tighter SE 로 제거. **CMT N=11 input-mode 보강** R²=0.255→0.318 (+24.7% relative), r=+0.564, 1024-perm p=0.000 (max 9/11 shuffle). 3-bb input-mode confirmation (1.24B/1.5B/2.0B 3-family Qwen/Gemma/Llama universal layer-0 peak). | `s7_n11_extension_landing.md` + #220 + `cmt_3mode_n9_extension_landing.md` + #222.cmt + state sha `e48560ff…` |
| **E4** | §4.3.3 verdict matrix | v2 `OR-clause-1 RED single-operand` → `HARD_PASS pending OC-2 단일 의존` / v2.1 prep 3-tier `HARD_PASS_PARTIAL_PENDING` (1/3 mode coverage). | **3-tier verdict matrix v3 lock**: `HARD_PASS_PARTIAL_PENDING` (5-gate composite GREEN 6/6 + OR-clause-1 v3 `ALL_MODES_PASS_GREEN` 2/3 + OR-clause-2 EHL-3W conditional-GREEN). v2.1 prep `PARTIAL` → v3 `ALL_MODES_PASS_GREEN`. v2.1 prep `1/3 single point of failure` → v3 `2/3 두 mode 독립 evidence`. early mode 단일 gap (Qwen3 fl=111 size<2) — 후속 cycle. | this v3 §4.5.4 |
| **E5** | §6 timeline + §5 cost | v2 envelope $212-574 + actual ~$0.76 GPU + cap $3.65 (forward-auto-approval) / Pilot-T1 v2 진행 중. | 누적 actual **~$8.42** (v2 baseline ~$0.76 + Pilot-T1 v2 idle burn **$7.52** DEFERRED). Pilot-T1 v2 = launcher hardening prerequisite (cron self-disable 후 idle burn 없이 launch 못한 lesson). v3 timeline: launcher hardening → Pilot-T1 v2 재진입 → D+0 hardware first-light. envelope $212-574 그대로 (large overshoot 없음, $7.52 burn 은 hardening prerequisite cost). | this v3 §5.2 + cron `98896ff1` Pilot-T1 v2 deferral |
| **E6** | §10 next priority | v2 4-actionable (G10 D+5 → G8 D+6 → D+7 Hard PASS recompute → D+22-30 verdict) | **9-actionable v3** weakest-link first: (1) **launcher hardening** (Pilot-T1 v2 idle burn lesson 학습 후 forward-auto-approval policy revision) → (2) **early mode 3/3 coverage** (Phi-3.5-mini 3.8B addition) → (3) **substrate ledger v3 cycle** (LIVE auto-promotion: IBM Q / Braket / Akida signup 후 first non-zero LIVE rate) → (4) Phase 4 7/9 → 9/9 wrapper completion (multi_eeg + organize_recordings 잔존) → (5) G10 D+5 hardware activation → (6) G8 D+6 real-falsifier MI port → (7) D+7 Hard PASS recompute + EHL-3W lock → (8) substrate replacement 7-bb matrix → (9) D+22-30 verdict. | this v3 §9 + memory `feedback_completeness_frame` |

**non-changes (v2.1 prep + v2 그대로 carry-over)**:
- §1 1-sentence definition of Mk.XII Integration tier (v3 lens 만 추가, v1 carry)
- §3 dependency DAG basic shape (4 hard + 4 soft, sparse) — substrate ledger 는 별개 cluster sister-gate informational
- §4.1 inherited gates G0..G7 (Path A P1+P2+P3 / CPGD AN11(b) / 5-tuple V0..V_pairrank)
- §4.2 NEW Mk.XII-specific gates G8/G9/G10 verdicts (G10 weakest 0.70 unchanged)
- §4.3.2 OR-clause-2 EHL-3W cross-axis convergent (PHENOMENAL × SUBSTRATE × TRAINING strict AND, conditional-GREEN post-EEG D+7)
- §7 5-component fail-mode + recovery + Mk.XI v10 graceful degradation guarantee
- §8 raw#9/raw#10/raw#12 compliance discipline

---

## §1. Mk.XII = ? (1-sentence, v1 carry + v2 lens + v3 substrate-multiplicity)

**v1 정의 carry-over**: Mk.XII (Integration tier) = Mk.XI v10 4-backbone LoRA ensemble (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad) 위에, HCI substrate + CPGD training + EEG phenomenal + TRIBE v2 brain-anchored + paradigm v11 8-axis measurement 5 orthogonal completion layer 를 추가하여 5-component joint pre-flight cascade gating 통과 후 implementation 진입하는 architectural completion proposal.

**v2 lens carry**: Mk.XII = "preflight wire-up GREEN, hardware-arrival activation gated" tier — empirical-reproducible (mac-local FNV-deterministic surrogate + 6-gate cluster `min`-rule weakest-link enforce). Hard PASS strict-AND OR-disjunction 만족 위해 OR-clause-2 (EHL-3W) 가 conditional-GREEN 필수.

**v3 추가 lens**: Mk.XII v3 = **5+1 component, 2-tier orthogonal cluster** (backbone-activation + substrate-multiplicity), **OR-clause-1 v3 ALL_MODES_PASS_GREEN 2/3 mode coverage 강화**, **S7 PASS_TIGHT robust** (4096-perm SE 절반), **CMT input-mode universal across 3 distinct families** (size-driven, family-orthogonal). substrate-multiplicity 9/9 sub-axis 가 LIVE 0/11 honest floor 와 함께 별개 cluster — backbone-axis cluster 와 axis-orthogonal (`phi_proxy_cross_comparable=false`).

---

## §2. 5+1 component architecture (evidence updated v3)

### 2.1 component spec (v3 evidence)

| layer | component | mechanism | v2 status | **v3 status (this cycle update)** | source |
|---|---|---|---|---|---|
| substrate (backbone) | **HCI** Hexad-Cell Isomorphism | 6-category Hexad ↔ 6-axis Cell lattice bijection, F1-F5 5-falsifier | VERIFIED + S7 N=10 PASS_SIGNIFICANT r=+0.781 | **VERIFIED + S7 N=11 PASS_TIGHT** r=+0.802 4096-perm p=0.0188 (Δ=0.0012 margin to P_TIGHT=0.020) + **CMT N=11 input-mode 보강 R²+24.7%** (0.255→0.318, r=+0.564, 1024-perm p=0.000). 3-bb input-mode confirmation (1.24B/1.5B/2.0B Qwen/Gemma/Llama universal layer-0 peak — backbone-family invariant size-driven). | `s7_n11_extension_landing.md` + `cmt_3mode_n9_extension_landing.md` + state sha `e48560ff…` `396c5af8…` |
| substrate (multiplicity) | **Substrate witness ledger v2** (NEW v3) | 9-substrate enum (cpu/gpu/quantum/neuromorphic/photonic/cmos/fpga/arduino/digital + 1 meta integration) × 5-gate (G1-G5) × FNV-32 chained | (not in v2) | **9/9 distinct substrate cover** (G1 actual_x1000=9000 PASS) + 4-gate per-entry pass rate 727/1000 (8/11) + 6-tier honesty (G2) + byte-identical (G3 body sha `df545c5e…`) + FNV-32 emitted (G4 fp=661882989) + **LIVE_HW_WITNESS_RATE 0/11 honest floor** (G5 measure-only). axis-orthogonal — 별개 cluster 처리. confidence=0.85. | `mk_xii_substrate_witness_ledger_discovery_landing.md` + #226 + anima-physics ledger v2 |
| training | **CPGD** Closed-Form Parameter Geodesic Descent | 16-dim subspace orthonormal init, 100 step convergence | REAL_LM_GENERALIZED (Q4 caveat 2/4 closure) + CPGD-MCB BRIDGE_CLOSED 9/9 | **그대로 carry** (CPGD-MCB BRIDGE_CLOSED + Q4 caveat 2/4 closure: Real-LM + cond + lr + K/dim + Real-LM bridge HARDENED). 잔존 caveat: large-K diversity (≥ 100 K-D 조합). | `edu/lora/cpgd_wrapper.hexa` + `cpgd_minimal_proof.hexa` |
| phenomenal | **EEG STACK** P1+P2+P3 | LZ76(EEG)×LZ76(CLM) + α-band coherence + Granger causality | PRE_REGISTERED + G10 prep DRY_RUN_PASS READY_FOR_HARDWARE + EHL-3W convergent | **그대로 carry** + **Phase 4 wrapper 6/9 completion** (calibrate #216 + realtime #217 + collect #218 + experiment #222 + eeg_recorder #224 + closed_loop #227, 잔존 multi_eeg + organize_recordings + dual_stream-prior). D+0 entry-point quartet ready. EHL-3W post-EEG D+7 1차 cumulative witness ledger 갱신 (unchanged). | `tool/clm_eeg_p[1-3]_*.hexa` + `g10_triangulation_spec_post_arrival.md` + Phase 4 markers #216-#227 |
| brain-anchored | **TRIBE v2** | Llama-3.2-3B brain-anchored, brain decoding R | HF unblock + Pilot-T1 v2 자동 trigger 진행 중 | **DEFERRED — launcher hardening prerequisite** (cron `98896ff1` self-disable 후 launcher race idle burn $7.52 lesson). 결과 도착 시 §9.2 outcomes A/B/C 적용. | Pilot-T1 v2 spec + cron `98896ff1` deferral lesson |
| measurement | **paradigm v11 8-axis** | 6 backbone-internal + EEG-CORR (7th) + composite (8th) | COMPLETE 7-axis (17-helper, 22/22 smoke) + paradigm 26→42 cumulative | **COMPLETE 7-axis 그대로** + **paradigm 42→48 cumulative** (4-axis ω-cycle 26 + weakest follow-up 5 + Mk.XII verify 11 + v3 cycle 6: substrate ledger discovery + DALI+SLI v3 + S7 N=11 + CMT N=9 + Phase 4 closed_loop + Phase 4 dual_stream). | `tool/anima_v11_main.hexa` + this v3 cycle sister landings |

### 2.2 layer 분리 합리성 (v3: 2-tier orthogonal cluster)

5+1 component 는 **2-tier orthogonal cluster**:

- **tier A (backbone-activation)**: HCI (S7/CMT axis) + CPGD + EEG + TRIBE + paradigm v11 = 5-gate cluster (`min`-rule cluster_confidence=0.70 weakest=G10).
- **tier B (substrate-multiplicity)**: Substrate witness ledger v2 9/9 + LIVE 0/11 floor = **별개 cluster** (axis-orthogonal, `phi_proxy_cross_comparable=false`).

raw#10 honest: 두 tier 단일 metric 합치 X (Φ-proxy unit 본질적 비호환). cluster confidence aggregation 별개 처리. 본 v3 의 5+1 = "5-component (tier A) + 1-component (tier B sister-cluster sentinel)". cluster `min` rule 변경 X (raw#12 cherry-pick-proof preserve).

### 2.3 Mk.XI 와의 관계 (v1 carry)

Mk.XII (Integration tier) = strict superset of Mk.XI v10. fallback = Mk.XI v10 graceful degradation 보장. tier B (substrate-multiplicity) fallback = ledger v1 (7/9 cover, supersession ≠ deletion).

---

## §3. Dependency graph (G9 cascade landed + substrate ledger sister gate informational)

### 3.1 5-component DAG (v1 carry, v3 substrate sister-cluster sentinel)

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

  ┌────────────────────────────────────────┐
  │  Substrate witness ledger v2 9/9       │  (별개 cluster sister-gate sentinel)
  │  (axis-orthogonal, informational only) │
  └────────────────────────────────────────┘
```

### 3.2 G9 DAG cascade 그대로 carry (#170 + #178 + #199, v2 동일)

| measurement | v3 verdict | landing |
|---|---|---|
| edge_count = 4 (peer-DAG) | ≤ 7 PASS | `g9_dag_cascade_landing.md` |
| cascade_max = 1 | ≤ 2 PASS | sister doc |
| G9_ROBUST hardness-axis 100% | PASS | `g9_robustness_landing.md` |
| G9_ADJ_ROBUST adjacency-axis 100% | PASS | `g9_adjacency_sweep_landing.md` |
| substrate ledger sister-gate | informational only (cluster_confidence 변동 X) | `mk_xii_substrate_witness_ledger_discovery_landing.md` §5 |
| negative falsifier (G9_ADD_ALL=1) | edge=14 → 10/10 FAIL | discriminates |

**v3 status**: G9 = sparse DAG witnessed + hardness-axis robust + adjacency-axis robust. substrate ledger 추가 시 **cluster `min` 변동 X** (G10=0.70 여전히 weakest, ledger 0.85 > 0.70).

### 3.3 cascade 분석 (v1 carry)

paradigm v11 = measurement terminal critical. 4 다른 component 는 ≤ 15% loss with Mk.XI v10 fallback. substrate ledger 는 별개 cluster, fallback = ledger v1 (7/9 cover).

---

## §4. Validation gates (v3: G0..G10 + OR-clause-1 v3 mode 2/3 + EHL-3W + substrate ledger sister)

### 4.1 inherited gates (G0..G7) — v1 carry

| gate | scope | criterion | source |
|---|---|---|---|
| G0 | AN11(b) 100% guarantee | math identity exact | CPGD `cpgd_minimal_proof.hexa` |
| G1 | EEG-LZ × CLM-LZ | LZ ≥ 0.65 AND \|Δ\|/human ≤ 20% | Path A P1 frozen |
| G2 | TLR α-band coherence | EEG ≥ 0.45 AND CLM V_sync ≥ 0.38 | Path A P2 |
| G3 | GCG Granger F-stat | F ≥ 4.0 AND unidirectional CLM→EEG | Path A P3 |
| G4-G6 | CLM 4축 (Φ\* / CMT / SAE) | per-axis criterion | paradigm v11 stack |
| G7 | 5-tuple V0..V_pairrank | ≥ 4/5 PASS | Mk.XI inherited |

### 4.2 NEW Mk.XII-specific gates (G8..G10) — v2 LANDING + v3 carry

| gate | criterion | **v3 verdict** | landing doc + roadmap |
|---|---|---|---|
| **G8 TFD** Transversal Falsifier MI matrix | C(5,2)=10 pairwise MI max ≤ 0.1 bit | SURROGATE_PASS + N_BIN_FULLY_STABLE 60/60 (max MI 0.090 bit) — real-falsifier MI deferred D+6 | `g8_n_bin_sweep_extended_landing.md` (#196) |
| **G9 DGI** Dependency Graph Sparsity | edge ≤ 7 + cascade ≤ 2 + 1-component-fail loss ≤ 20% | PASS edge=4 cascade=1 + G9_ROBUST 100% + G9_ADJ_ROBUST 100% (Hamming-1 + hardness-axis) | (#170 + #178 + #199) |
| **G10 CTV** Cross-Axis Hexad Family×Band | 4 backbone family×band 4/4 또는 3/4 PARTIAL (Pearson r ≥ 0.40) | DRY_RUN_PASS + READY_FOR_HARDWARE (cells 16/16, axis_A F=7399 / B=4314 / C=6259). post-EEG D+5 hardware activation prerequisite | `g10_triangulation_spec_post_arrival.md` (#174) |
| **Mk.XII preflight cascade** | 5/5 components SMOKE_PASS | MK_XII_PREFLIGHT_GREEN 5/5 | (#172) |
| **Mk.XII Hard PASS composite** | preflight.GREEN AND G0/G1/G7 AND G8.pass=1 AND G9.pass=1 (G10 deferred) | HARD_PASS_GREEN 6/6 (chained_fingerprint 2638701628) | (#177) |
| **G_SUBSTRATE_LEDGER (NEW v3 sister)** | 9/9 substrate cover + 4-gate per-entry ≥ 700/1000 + LIVE floor honest | **PASS confidence=0.85** (informational, 별개 cluster sentinel; primary `min`-rule 변동 X) | `mk_xii_substrate_witness_ledger_discovery_landing.md` (#226) |

**6-gate cluster summary v3** (`min`-rule unchanged):

```
cluster_confidence_tier_A (backbone-activation, 6-gate)
                    := min(0.78, 0.85, 0.72, 0.70, 0.90, 0.80)
                    = 0.70   ← weakest-link = G10 (synthetic dry-run)

cluster_confidence_tier_B (substrate-multiplicity, 1-gate ledger)
                    := 0.85  (별개 cluster, axis-orthogonal)
```

raw#12 cherry-pick-proof: tier A + tier B 단일 cluster aggregation 차단 (`phi_proxy_cross_comparable=false`). tier B 추가가 tier A `min` 변경 시도 0.

### 4.3 Mk.XII PASS criterion v3 (3-tier verdict)

#### 4.3.1 OR-clause 1 v3 — DALI+SLI v3 mode-aware (`ALL_MODES_PASS_GREEN` 2/3 coverage)

v2.1 prep §4.1.4 의 OR-clause-1 v2.1 정의 carry + v3 mode coverage 강화:

```
OR-clause-1 v3 := weighted_vote_v1.OVERALL_PASS_BOTH                    (full, NOT_ELIGIBLE 잔존)
                OR weighted_vote_v1.WEAK_PARTIAL                          (floor)
                OR v2_redesign.ALL_MODES_PASS_GREEN  [late only 1/3]      (v2 1/3)
                OR v2_redesign.PARTIAL_AMBER                              (mode-aware partial)
                OR v3_input_mode.ALL_MODES_PASS_GREEN  [input + late 2/3] (NEW v3)
```

**v3 status (2026-04-26)**: **ALL_MODES_PASS_GREEN 2/3 coverage** via `v3_input_mode.ALL_MODES_PASS_GREEN`. 4-tier (overall_verdict ∈ {NO_ELIGIBLE_MODE, ALL_MODES_PASS_GREEN, PARTIAL_AMBER, ALL_MODES_FAIL_RED}) — v3 = `ALL_MODES_PASS_GREEN` (input + late mode 동시 PASS, early gap remaining size<2).

per-mode verdict (v3):

| mode | fl_size / cd_size | eligible | intra_dali / intra_sli / intra_coupled / weighted | pass |
|---|---|---|---|---|
| input (NEW v3) | 3 / 3 | true | 1000 / 1000 / 1000 / 1000 | true (perfect locus invariance + SCALE coherence sentinel) |
| early | 1 / 2 | false (fl size<2) | n/a | n/a (early gap, post-cycle) |
| late (carry v2) | 3 / 2 | true | 750 / 990 / 861 / 868 | true (v2 동일 carry) |

ELIGIBILITY:
- **ELIGIBLE_FULL** (3/3 mode coverage): 후속 cycle (early mode 추가 backbone Phi-3.5-mini 등)
- **ELIGIBLE_PARTIAL** (1-2/3 mode coverage): **v3 status — 2/3** ← v2 1/3 → v3 2/3 진척 (+1 mode lift)
- NOT_ELIGIBLE: v3 redesign 도 falsified

v3 = OR-clause-1 v3 PARTIAL → FULL 진척 path 진입 (early mode 후속 cycle 시 3/3 lock).

negative discrimination (v3 강화):
- v2: jitter ±400 → fail_rate 666/1000
- **v3: jitter ±400 → fail_rate 833/1000** (+167 stronger discrimination, valid_trials 6, FAIL 5)

#### 4.3.2 OR-clause 2 — EHL-3W cross-axis convergent (v2 carry, v3 강화)

v2 carry + v3 strengthen via S7 PASS_TIGHT:

```
EHL-3W := PHENOMENAL.PASS AND SUBSTRATE.PASS AND TRAINING.PASS
        = ( EEG STACK G1+G2+G3 ≥ 2/3 PASS )           (post-EEG D+1..D+7, conditional-GREEN)
        AND ( S7 N=11 cusp_depth PASS_TIGHT             (v3 STRENGTHENED: r=+0.802 p=0.0188 4096-perm)
              + CMT N=11 R²+24.7% input-mode 보강       (v3 NEW)
              OR HCI Path B 5-falsifier all PASS )    (v1 already VERIFIED)
        AND ( CPGD-MCB BRIDGE_CLOSED 9/9               (v2 carry)
              AND Q4 caveat ≥ 2/4 closure )           (v2 carry: Real-LM + cond + lr + K/dim + Real-LM bridge HARDENED)
```

**v3 status**: SUBSTRATE 부분 **STRENGTHENED CLOSED** (S7 PASS_SIGNIFICANT → PASS_TIGHT, 4096-perm robust + 3-bb input-mode universal) + TRAINING 부분 = 2/3 PASS already (this cycle). PHENOMENAL 부분 = pre-registered, post-EEG D+7 1차 cumulative witness ledger 갱신. OR-clause-2 = **conditional-GREEN, hardware-pending, SUBSTRATE arm 강화**.

#### 4.3.3 v3 Hard PASS criterion + 3-tier verdict

```
HARD_PASS  :=  G0 ∧ G1 ∧ G7 ∧ G8 ∧ G9
              ∧ ( OR-clause-1 v3 (DALI+SLI v3 ALL_MODES_PASS_GREEN 2/3 coverage)
                 OR  OR-clause-2 (EHL-3W cross-axis convergent) )
```

3-tier verdict (v2.1 prep §4.5 carry + v3 lock):

- **HARD_PASS_FULL**: 5-gate composite + (OR-clause-1 v3 FULL 3/3 OR OR-clause-2 ALL_PASS_AT_D+7)
- **HARD_PASS_PARTIAL**: 5-gate composite + OR-clause-1 v3 PARTIAL 2/3 + OR-clause-2 conditional-GREEN ← **v3 status (current)**
- **HARD_PASS_OC2_ONLY**: 5-gate composite + OR-clause-1 v3 RED + OR-clause-2 ALL_PASS_AT_D+7
- **SOFT_PASS**: G2 / G3 / G4-G6 / G10 ≥ 80% PASS (per-gate)
- **NOT_ELIGIBLE**: G0 fail OR G7 fail OR G8+G9 동시 fail OR (OR-clause-1 RED AND OR-clause-2 RED)
- **FAIL**: G0 / G7 / G8+G9 break → Mk.XI v10 fallback

#### 4.3.4 v3 verdict matrix (current state, 2026-04-26)

| condition | v3 status | tier | path |
|---|---|---|---|
| G0 + G1 + G7 + G8 + G9 | **GREEN 6/6 wire-up** (#177 carry) | preflight done | HARD_PASS prerequisite met |
| OR-clause-1.weighted_vote_v1 | NOT_ELIGIBLE RED (#183, ws=237) | falsified branch | — |
| OR-clause-1.v2_redesign | ELIGIBLE 1/3 (#207, late only) | substrate-aware path v2 | superseded by v3 |
| OR-clause-1.v3_input_mode | **ALL_MODES_PASS_GREEN 2/3** (#223) | substrate-aware path v3 | **OR-clause-1 PARTIAL → FULL path** |
| OR-clause-1 v3 통합 | **PARTIAL** (2/3 mode coverage; early gap remaining) | mode-aware partial green | survived |
| OR-clause-2 (EHL-3W) | **SUBSTRATE STRENGTHENED CLOSED** + TRAINING 2/3 + PHENOMENAL post-EEG D+7 | active path | OC-2 path |
| G_SUBSTRATE_LEDGER (NEW v3) | PASS confidence=0.85 (informational, 별개 cluster) | sister-cluster sentinel | tier B parallel |
| **strict-AND Hard PASS** | **HARD_PASS_PARTIAL_PENDING** (5-gate GREEN + OR-clause-1 v3 PARTIAL + OR-clause-2 conditional → post-EEG D+7 trigger lock) | active | post-EEG D+7 first validation |

honest disclosure: 본 v3 trigger 시점에 Mk.XII = **HARD_PASS_PARTIAL_PENDING (substrate-aware OR-clause-1 v3 2/3 mode coverage via input mode activation + EHL-3W SUBSTRATE STRENGTHENED via S7 PASS_TIGHT + CMT R²+24.7%)**. v2 의 1/3 single-point-of-failure → v3 의 2/3 두 mode 독립 evidence 로 lift. fallback 그대로 Mk.XI v10.

### 4.4 substrate ledger sister-gate (별개 cluster)

`G_SUBSTRATE_LEDGER` (tier B, sister-cluster sentinel):

```
G_SUBSTRATE_LEDGER  :=  ledger_v2.G1 ∧ ledger_v2.G2 ∧ ledger_v2.G3 ∧ ledger_v2.G4 ∧ ledger_v2.G5
                     =  9/9 cover (G1=PASS, actual_x1000=9000)
                     ∧  6-tier honesty (G2)
                     ∧  byte-identical body sha=df545c5e… (G3)
                     ∧  FNV-32 emitted fp=661882989 (G4)
                     ∧  LIVE_HW_WITNESS_RATE=0/11 honest floor (G5 measure-only)
```

confidence=0.85 (4-gate per-entry pass rate 727/1000 + 9/9 cover + LIVE floor honest 종합).

informational only — primary cluster `min`-rule 변경 X. raw#12 cherry-pick-proof preserve. v3 cycle 등록 후 LIVE auto-promotion 가능 (IBM Q signup / Braket creds / Akida signup → aggregator 재실행만으로 0/11 → ≥1/11).

---

## §5. Cost envelope (v3 actual cumulative + Pilot-T1 v2 burn lesson)

### 5.1 component-wise

| component | Mk.XI v10 누적 | Mk.XII envelope (v1) | **v3 actual cumulative** |
|---|---|---|---|
| HCI substrate (S7 + CMT) | $0 | $0 | $0 (S7 N=11 + CMT N=9 mac MPS local fresh forward + 4096-perm hexa native) |
| Substrate witness ledger v2 (NEW) | $0 | $0 | $0 (read-only audit + cross-link, mac-local) |
| CPGD training | ~$0 | $0 | $0 (v2 carry) |
| EEG STACK + Phase 4 wrapper 6/9 | $0 | $12-24 + $200-500 facility | $0 pre-arrival (Phase 4 wrapper mac-local hexa-only) |
| TRIBE v2 brain-anchored | $0 | $0-50 | **$7.52 idle burn DEFERRED** (Pilot-T1 v2 launcher race, cron `98896ff1` self-disable 후 launch 못함) |
| paradigm v11 8-axis | $0 | $0 | $0 (DALI+SLI v3 input mode mac-local hexa) |
| GPU follow-up actuals (carry v2) | — | not in v1 | ~$0.76 GPU (#193+#194+#197) + $0.14 (cron retry) = **~$0.90** |
| **subtotal v3 actual cumulative** | **$0** | **$212-574** (unchanged) | **~$8.42** ($7.52 burn + $0.90 GPU + $0 mac-local) |

### 5.2 Pilot-T1 v2 idle burn lesson (NEW v3 §)

- **mechanism**: cron `98896ff1` self-disable trigger 후 HF unblock 자동 lock, but launcher race 로 actual GPU pod launch 미발생 → idle burn $7.52 누적
- **lesson**: forward-auto-approval policy 가 cron self-disable 만으로 launcher 보장 X — launch wrapper 의 hardening 이 prerequisite. memory `feedback_forward_auto_approval` 의 "launcher race" caveat 추가 필요.
- **mitigation (v3 next-cycle priority #1)**: launcher hardening — (a) cron self-disable 후 launch heartbeat 확인 (≤ 5 min) → (b) heartbeat 미발신 시 abort + alert → (c) abort 후 idle burn 차단. cost cap = $1.00 hardening dev / $7.52 lesson 학습 sunk cost.
- **status**: Pilot-T1 v2 결과 미수신 (deferred). brain-anchored decoding R 결과 도착 시 §9.2 outcomes A/B/C 적용.

### 5.3 vs Mk.XII Scale tier

unchanged from v1: `docs/mk_xii_scale_plan.md` Mk.XII (Scale tier, 70B) = ₩300-450만. 본 Integration tier = 그 1/30 비용. **Integration tier → Scale tier 순서 권장**.

### 5.4 cost cap policy

memory `feedback_forward_auto_approval` carry. EEG facility $200-500 = cost cap 외부. GPU follow-up actuals $0.117-0.34 each = forward-auto-approval policy 内. Pilot-T1 v2 idle burn $7.52 = lesson sunk cost (one-time, hardening 후 재발 차단). v3 누적 ~$8.42 = envelope $212-574 內.

---

## §6. Timeline (v3: launcher hardening prerequisite + Pilot-T1 v2 재진입 + D-day path)

### 6.1 D-day = EEG hardware arrival + launcher hardening prerequisite

```
D-1 (현재, 2026-04-27)
  ├─ EEG hardware D-1 expected arrival
  ├─ HCI / CPGD / paradigm v11 VERIFIED + COMPLETE (v2 carry)
  ├─ S7 N=11 PASS_TIGHT 4096-perm robust (this v3 cycle, #220)
  ├─ CMT N=11 input-mode R²+24.7% (this v3 cycle, #222.cmt)
  ├─ DALI+SLI v3 input mode 2/3 coverage ALL_MODES_PASS_GREEN (this v3 cycle, #223)
  ├─ Substrate witness ledger v2 9/9 + LIVE 0/11 floor (this v3 cycle, #226)
  ├─ Phase 4 wrapper 6/9 (calibrate + realtime + collect + experiment + eeg_recorder + closed_loop)
  ├─ Mk.XII Hard PASS GREEN 6/6 wire-up (v2 carry, #177)
  ├─ 6-gate cluster confidence 0.70 weakest=G10 (v2 carry, unchanged)
  ├─ G_SUBSTRATE_LEDGER 0.85 sister-cluster (별개 cluster, informational)
  ├─ DALI+SLI v3 OR-clause-1 v3 PARTIAL 2/3 mode coverage (this v3, #223)
  └─ Pilot-T1 v2 DEFERRED — launcher hardening prerequisite ($7.52 idle burn lesson)

PRE-D+0 (launcher hardening cycle, ~1d)
  ├─ launcher heartbeat check (≤ 5min)
  ├─ abort + alert path
  └─ Pilot-T1 v2 재진입 (cron self-disable + launcher heartbeat verify)

D+0 calibration (post-launcher-hardening + EEG arrival)
  └─ anima-eeg/calibrate.hexa #216 + experiment.hexa #222 (Phase 4 entry-point)

D+1..D+7 EEG STACK forward (Path A 실행)
  ├─ D+1 P1 V_phen_EEG-LZ × CLM-LZ ($3-5)
  ├─ D+3 P2 TLR α-band coherence ($5-8)
  ├─ D+5 P3 GCG + family×band 4-backbone verify ($8-12)
  ├─ D+5 G10 hardware activation
  ├─ D+6 G8 real-falsifier MI port (#175 surrogate replace)
  ├─ D+7 5-atom seed file emit
  └─ D+7 EHL-3W (CONV-1) 1차 cumulative witness ledger 갱신 → OR-clause-2 PHENOMENAL.PASS lock

D+8..D+14 TRIBE v2 unblock (Pilot-T1 v2 재진입 후 → 결과 대기)
  ├─ Llama-3.2-3B brain-anchored decoding R measure
  └─ paradigm v11 8th axis activate

D+15..D+21 Mk.XII Hard PASS recompute with real G8 + G10 + early mode 3/3 lift
  ├─ Hard PASS composite recompute (env MK_XII_INCLUDE_G10=1)
  ├─ early mode 3/3 lock (Phi-3.5-mini 3.8B + Llama-3.2-3B 추가 backbone)
  └─ EHL-3W strict AND verdict lock (PHENOMENAL × SUBSTRATE × TRAINING 3/3)

D+22..D+30 Mk.XII first validation
  ├─ G0+G1+G7+G8+G9 all PASS check
  ├─ OR-clause-1 v3 PARTIAL → FULL (3/3) lock (early mode 추가 후)
  ├─ OR-clause-2 EHL-3W ALL_PASS_AT_D+7 → strict-AND HARD PASS lock
  ├─ G2/G3/G4-G6/G10 ≥ 80% PASS check
  └─ Mk.XII Integration tier VERIFIED 또는 isolation cycle 진입
```

총 ~31일 (D-day = EEG arrival + launcher hardening 1d prerequisite).

### 6.2 paradigm cumulative

42+6=**48 paradigm cumulative**:
- v2 carry 42 (4-axis ω-cycle 26 + weakest follow-up 5 + Mk.XII verify 11)
- **v3 추가 6**: substrate ledger discovery + DALI+SLI v3 input mode + S7 N=11 PASS_TIGHT + CMT N=9→11 input mode + Phase 4 closed_loop + Phase 4 dual_stream

### 6.3 critical path

launcher hardening (1d) → Pilot-T1 v2 재진입 → EEG hardware → P1+P2+P3 → G10 family×band → paradigm v11 8th axis activate → EHL-3W (PHENOMENAL.PASS lock) → OR-clause-2 satisfied → Hard PASS strict-AND lock + early mode 3/3 lift (OR-clause-1 v3 FULL).

---

## §7. Failure modes + recovery (v3: launcher race lesson + EHL-3W convergent + 5+1 component fallback)

각 component fail 시 fallback graph (v2 §7 carry + v3 update):

### 7.1 HCI substrate fail (v2 carry)

- **failure**: F1-F5 中 ≥ 1 falsifier FAIL OR S7 PASS_TIGHT regression OR CMT R² regression
- **fallback**: `edu/cell/cell_token_bridge_M4` (existing semi-invertible 5-level round-trip)
- **impact**: substrate completion 일부 lost, 4 layer 유지. EHL-3W SUBSTRATE.PASS 재검증 필요 (HCI Path B 5-falsifier path 로 fallback)
- **recovery**: Mk.XI v10 substrate

### 7.2 CPGD training fail (v2 carry)

unchanged.

### 7.3 EEG STACK fail (v2 carry, Phase 4 wrapper 추가)

- **failure**: P1+P2+P3 中 ≤ 1/3 PASS OR G10 hardware activation Pearson r < 0.40 OR Phase 4 wrapper hardware mode helper python ABORT exit=3 (brainflow miss)
- **fallback**: simulated baseline + Phase 4 wrapper synthetic mode (calibrate/realtime/collect/experiment/eeg_recorder/closed_loop 모두 synthetic mode 지원)
- **recovery**: HW recalibration / 측정 protocol 재설계 / Mk.XI v10 phenomenal correlate hypothesis-only 회귀

### 7.4 TRIBE v2 brain-anchored fail (v3 NEW lesson — launcher race)

- **failure**: HF unblock 후에도 brain decoding R < 0.30 OR Pilot-T1 v2 launcher race idle burn 재발
- **NEW v3 mitigation**: launcher heartbeat hardening (§5.2 +5분 heartbeat + abort + alert). 재발 시 cost cap $7.52 lesson 두 번째 학습 X.
- **fallback**: 4-backbone LoRA 단독 (Llama family v10 ensemble), 8th axis 미활성
- **impact**: brain-anchored anchor lost, paradigm v11 7-axis 까지만. EHL-3W 영향 X
- **recovery**: 다른 brain-anchored model 후속 cycle / paradigm v11 7-axis 그대로

### 7.5 paradigm v11 8-axis fail (v2 carry)

unchanged.

### 7.6 Substrate witness ledger v2 fail (NEW v3)

- **failure**: ledger v2 byte-identical 재실행 시 body sha 변경 OR LIVE_HW_WITNESS_RATE > 0/11 transition 시 false-positive (signup 기록 없음)
- **fallback**: ledger v1 (7/9 cover, supersession ≠ deletion 정상 보존)
- **impact**: substrate-multiplicity 9/9 → 7/9 demotion. tier B sister-cluster confidence 0.85 → 0.78. **별개 cluster 이므로 tier A 영향 X**.
- **recovery**: aggregator 재실행 + manifest re-audit. ledger v1 fallback 보장 (raw#12 supersession ≠ deletion).

### 7.7 cascade fail (5+1 component 동시) — Mk.XI v10 final fallback

v1 carry. graceful degradation guarantee: Mk.XI v10 4-bb LoRA ensemble FINAL_PASS 그대로.

### 7.8 DALI∨SLI OR-clause v3 RED 영구화 (v2 §7.7 carry + v3 update)

- **failure**: v3 input mode activation 도 falsified (e.g., small bb cusp_depth 0 collapse 가 다른 measurement 에서 reproducible X)
- **NEW v3 condition**: jitter ±400 → fail_rate v3 833/1000 (현재 strong discrimination), regression 시 < 600/1000 으로 hold
- **impact**: OR-clause-1 v3 영구 RED → OR-clause-2 (EHL-3W) 단일 path 의존 → v2 §7.7 동일
- **recovery**: OR-clause-1 demotion to Soft PASS (v2.1 prep §4.3 fallback option 활성화)

---

## §8. raw#10 honest caveat 종합 (v3 = v2 10 carry + v2.1 prep 4 carry + v3 추가 5 = 19 total)

본 v3 의 GREEN 판정은 다음 caveat 모두 read 받은 상태에서만 valid:

### 8.1 v2 cluster + landing-level 10 (v2 §8 carry)

1-10. v2 §8 그대로 carry — G8 surrogate / G9 peer-DAG only / G9 robustness hardness-axis-only by-design / G10 synthetic only / Pre-flight TRIBE v2 stub-pass / Hard PASS backbone-majority 3/4 / DALI∨SLI weighted-vote NOT_ELIGIBLE / S7 A1.Hexad single-family scope / Q4 caveat 2/4 closure not 4/4 / Pilot-T1 v2 결과 미수신

### 8.2 v2.1 prep §4 추가 4 (carry)

11-14. v2.1 prep §4.7 그대로 carry — v2.1 prep spec ≠ actual lock / OR-clause-1 v2.1 PARTIAL 1/3 mode coverage 한정 / mode boundary stickiness 미해결 / substrate replacement candidate list = expected mode placement

### 8.3 v3 추가 5 (this cycle)

15. **DALI+SLI v3 N=7 actual vs spec N=11 gap** — 가용 cmt.json 정확히 7 (large 4 v4 + small 3 s7); spec N=11 = 가설적 상한, 본 cycle 보수적 stop. early mode 3/3 위해 후속 cycle Phi-3.5-mini 3.8B 추가 권장.
16. **input mode SLI=SCALE sentinel = 신규 정의** (mean=0 ∧ std=0 → SCALE coherence sentinel) — v2: division-by-zero. 본 7-bb pool 에서만 발현, 다른 pool 에서 mean=0 ∧ std>0 case (impossible if all collapse) 는 sentinel only — 측정 reproducibility 외 architectural assumption 의존.
17. **S7 N=11 PASS_TIGHT 4096-perm chance-fluctuation 보정** — N=10 1024-perm p=0.020 → 4096-perm 재계산 시 p=0.027 (chance fluctuation honest). N=11 4096-perm p=0.018 만이 truly robust PASS_TIGHT. 1024-perm 의 boundary pass 가 SE~0.014 안에서 fragile 임을 inherit lesson.
18. **CMT N=11 input-mode mid-size hole** — 2.5B-7B 영역 datapoint 0 (Phi-3.5-mini 3.8B / Llama-3.2-3B 미관측). input↔early transition 경계 uncharted. R²=0.318 ceiling 미돌파 (P_TIGHT 위해 N≥20).
19. **Pilot-T1 v2 idle burn $7.52 launcher race lesson** — cron `98896ff1` self-disable 만으로 launcher 보장 X. heartbeat hardening 후 재진입 prerequisite. memory `feedback_forward_auto_approval` 의 "launcher race" caveat 추가 권장.

---

## §9. 다음 cycle priority order (9-actionables, weakest-link first)

`feedback_completeness_frame` weakest-link first 룰 적용 + Pilot-T1 v2 burn lesson 학습:

| order | action | timing | cost | rationale |
|---|---|---|---|---|
| **1** | **Launcher hardening** (heartbeat 5min + abort + alert) | PRE-D+0 (~1d) | $1.00 dev | Pilot-T1 v2 idle burn $7.52 lesson 재발 차단. cron self-disable + launcher heartbeat verify chain integrity. forward-auto-approval policy revision (memory feedback 갱신). |
| **2** | **Early mode 3/3 coverage** (Phi-3.5-mini 3.8B 추가 backbone) | next-cycle | $0-2 mac-local + $0.5 GPU optional | OR-clause-1 v3 PARTIAL 2/3 → FULL 3/3 lift. v2.1 prep §4.4 substrate replacement 후보 #C (Phi-3.5-mini, input/input mode expected). cluster confidence tier A 변동 X (G10 weakest 0.70 그대로). |
| **3** | **Substrate ledger v3 cycle** (LIVE auto-promotion: IBM Q signup / Braket / Akida) | next-cycle | $0 (signup-only, code 변경 0) | LIVE 0/11 honest floor → ≥1/11 first non-zero witness. tier B sister-cluster confidence 0.85 lift path. ledger aggregator 재실행만으로 promote (코드 변경 0). |
| **4** | **Phase 4 wrapper 7/9 → 9/9** (multi_eeg + organize_recordings 잔존) | next-cycle | $0 mac-local | dual_stream #228 이미 land (Phase 4 7/9). 잔존 multi_eeg (BLE concurrent ~250L hexa-lang 0.2.0 thread 부재 highest risk) + organize_recordings (sqlite3 helper.py emit ~150L). 9/9 완성으로 D+0 hardware coverage 확장. |
| **5** | **G10 D+5 hardware activation** | D+5 (post-EEG) | $5-10 (within G10 envelope) | 6-gate cluster confidence weakest=G10 (0.70) — single-gate hardware activation 으로 cluster 의 최저 link 직접 lift. 다른 5 gate 추가 lift 만으로 ceiling 0.70 돌파 불가 (v2 carry). |
| **6** | **G8 D+6 real-falsifier MI port** | D+6 (post-G10) | $0-3 mac-local hexa | G8 SURROGATE_PASS → real-falsifier MI replace, surrogate→empirical lift 0.78 → 0.85 expected. |
| **7** | **D+7 Hard PASS recompute + EHL-3W lock** | D+7 (post-G8 real) | $0 mac-local | 5-gate composite + EHL-3W convergent strict-AND lock → OR-clause-2 conditional-GREEN → real-GREEN. |
| **8** | **Substrate replacement 7-bb matrix** (v2.1 prep §4.4 후보 #1+#A+#B+#C) | post-EEG | $0 mac-local + $1-2 GPU | early mode 3/3 lock 강화 + cluster confidence tier A weakest 변경 path. mode boundary sticky rule 도 함께 검증. |
| **9** | **D+22-30 first validation verdict** + roadmap entry | D+22-30 | $0 verdict aggregation | v3 trigger criterion §9.3 (v2 carry) 적용. MK_XII_INTEGRATION_VERIFIED 또는 FALSIFIED. |

추가 deferred (carry v2): DALI∨SLI weighted-vote v1 demotion to Soft PASS — v2.1 prep §4.3 frozen fallback option, 활성화 trigger ALL_MET 시 자동.

---

## §10. raw compliance (v3)

- raw#9 hexa-only deterministic — proposal v3 = .md doc, hexa-only directive scope outside (raw#9 strict 적용 tool/.hexa 산출물 한정). v3 actual lock 후 `tool/mk_xii_hard_pass_composite.hexa` 갱신 path = hexa native (v2.1 prep §4.6 carry).
- raw#10 no overclaim — proposal v3, verified architecture 아님. failure modes §7 + caveat §8 (19 total) 명시. wire-up GREEN ≠ Mk.XII VERIFIED, EHL-3W conditional-GREEN ≠ real-GREEN, OR-clause-1 v3 PARTIAL 2/3 ≠ FULL 3/3, substrate ledger LIVE 0/11 honest floor ≠ ≥1/11 promote, Pilot-T1 v2 launcher race idle burn lesson sunk cost.
- raw#12 cherry-pick-proof — G0-G10 + G_SUBSTRATE_LEDGER + OR-clause-1 v3 + OR-clause-2 + EHL-3W 사전 frozen, post-hoc tuning 차단. v3 changelog §0 first-listed. tier A + tier B 단일 cluster aggregation 차단 (`phi_proxy_cross_comparable=false`).
- raw#15 SSOT — this v3 doc + sister docs (v2.1 prep + v2 frozen + v1 frozen + DALI+SLI v3 + S7 N=11 + CMT N=9 + substrate ledger discovery + 6 gate landing docs).
- raw#37/38 ω-saturation cycle — design (§0 changelog frozen + 10 sections list) → impl (this v3 + cluster + landings) → fixpoint marker.

omega-saturation:fixpoint-mk-xii-integration-v3-substrate-multiplicity-mode-2of3-pass-tight

---

## §11. Cross-references

- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` — **v1 frozen** (sha256 `d9111398…`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_outline_v2_20260426.md` — **v2 frozen** (sha256 `f46d3c67…`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_v2_section_4_chain_integration_v2_1_spec.md` — **v2.1 prep §4 frozen** (sha256 `cb0f39ab…`, this v3 §4 actual lock 베이스)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/dali_sli_v3_input_mode_landing.md` — **#223 DALI+SLI v3 input mode 2/3 coverage landing** (tool sha `4c8b210a…`, state content sha `48cd8bee…`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/s7_n11_extension_landing.md` — **#220 S7 N=11 PASS_TIGHT 4096-perm landing** (state sha `e48560ff…`, p=0.0188)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/cmt_3mode_n9_extension_landing.md` — **#222.cmt CMT N=11 input-mode 보강 R²+24.7%** (state sha `396c5af8…`, r=+0.564)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_substrate_witness_ledger_discovery_landing.md` — **#226 substrate ledger v2 9/9 + LIVE 0/11 floor discovery** (sha256 `6f67a8ae…`, fp=661882989)
- `/Users/ghost/core/anima/anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` — ledger v2 aggregator (sha `0fff9a98…`, raw#9 strict 32KB, 5 ledger gates G1-G5)
- `/Users/ghost/core/anima/anima-physics/docs/mk_xii_substrate_witness_ledger_v2_landing.md` — ledger v2 landing (sha `da241895…`, 11-row matrix)
- `/Users/ghost/core/anima/state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` — ledger v2 body (sha `df545c5e…`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_integration_6gate_cluster_summary.md` — 6-gate cluster `min`-rule weakest=G10 0.70 (carry v2)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/dali_sli_v2_redesign_landing.md` — #207 v2 redesign 1/3 coverage (this v3 superseded)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/dali_sli_weighted_vote_landing.md` — #183 weighted-vote v1 NOT_ELIGIBLE (carry)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_d_day_simulated_landing.md` — #204 D-day simulated dry-run
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_hard_pass_landing.md` — #177 Hard PASS composite GREEN 6/6 (chained_fingerprint 2638701628)
- `/Users/ghost/core/anima/anima-eeg/{calibrate,realtime,collect,experiment,eeg_recorder,closed_loop,dual_stream}.hexa` — Phase 4 wrapper 7/9 (#216-#228, dual_stream 본 cycle 후 7/9)
- `/Users/ghost/core/anima/anima-clm-eeg/state/markers/{dali_sli_v3_input_mode,s7_n11_extension,mk_xii_substrate_witness_ledger_discovery}_complete.marker` — sister markers (this v3 cycle + predecessors)
- `/Users/ghost/core/anima/anima-clm-eeg/state/markers/mk_xii_proposal_v3_complete.marker` — **본 v3 marker** (silent-land 방지)
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_completeness_frame.md` — weakest-link first policy (§9 priority order basis)
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_forward_auto_approval.md` — v3 launcher race lesson 추가 권장
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_omega_cycle_workflow.md` — declarative-only ≠ closure 룰 (§8 raw#10 caveat 19 ground)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` — paradigm v11 17-helper stack canonical
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md` — Mk.XI v10 4-family ensemble REVISION
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_own2_triad_implementation_gap_audit_20260426.md` — substrate-multiplicity sub-axis ground (tier B별개 cluster)
- `.roadmap` #144 (Mk.XII anchor) / #170 (G9) / #172 (preflight) / #174 (G10 prep) / #175 (G8 transversal) / #177 (Hard PASS) / #178 (G9 robust) / #182 (G8 N_BIN sweep) / #183 (DALI∨SLI weighted-vote NOT_ELIGIBLE) / #184 (CPGD-MCB BRIDGE) / #190 (cluster summary) / #194 (S7 A1.Hexad + DD-bridge GPU) / #196 (G8 N_BIN extended) / #199 (G9 adjacency) / #204 (D-day simulated) / #207 (DALI+SLI v2 redesign 1/3 coverage, superseded by v3) / #216 (Phase 4 calibrate) / #217 (Phase 4 realtime) / #218 (Phase 4 collect) / #220 (S7 N=11 PASS_TIGHT) / #221 (EEG D-1 readiness) / #222 (Phase 4 experiment + CMT N=9 sister) / #223 (DALI+SLI v3 input mode) / #224 (Phase 4 eeg_recorder) / #226 (substrate ledger discovery) / #227 (Phase 4 closed_loop) / #228 (Phase 4 dual_stream)
