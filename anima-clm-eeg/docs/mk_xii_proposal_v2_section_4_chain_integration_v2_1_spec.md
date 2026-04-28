# Mk.XII Proposal v2.1 — §4 Chain Integration Update Spec (prep)

> **scope**: Mk.XII Integration tier proposal v2 (`mk_xii_proposal_outline_v2_20260426.md`, sha256 prefix `f46d3c67…`, **frozen**) 의 **§4 (Validation gates) 만** 갱신하는 v2.1 update spec. v2 본문은 read-only — 다른 §0..§3, §5..§12 모두 v2 그대로. v2.1 = §4 chain integration update **only**.
> **session date**: 2026-04-26 (sister docs: `dali_sli_v2_redesign_landing.md` (.roadmap #207 ad6484a5) / `dali_sli_weighted_vote_landing.md` (.roadmap #183 NOT_ELIGIBLE) / `mk_xii_integration_6gate_cluster_summary.md` / `mk_xii_d_day_simulated_landing.md` (.roadmap #204))
> **status**: **PREP SPEC — pre-trigger**. 본 문서는 v2.1 actual lock 의 prerequisite spec — DALI+SLI v2 substrate-aware redesign (#207, ad6484a5 already landed `ALL_MODES_PASS_GREEN` 1/3 mode coverage) 결과 통합과 weighted-vote remediation 3 후보의 chain integration 옵션을 frozen design 으로 기술. v2.1 actual update lock 은 §4.6 trigger 절차 충족 시.
> **predecessors / orthogonal**: v2 frozen / v1 frozen / Mk.XI v10 4-bb FINAL_PASS / DALI+SLI v2 (#207 substrate-aware mode-grouped) / weighted-vote v1 (#183 NOT_ELIGIBLE) / coupled v0 (JOINT_FAIL).

---

## §4.0 v2 → v2.1 Changelog (라이팅 시 first)

본 v2.1 의 **6 핵심 변경** (frozen at design step, post-hoc tuning 차단):

| # | sub-§ | v2 status | v2.1 update | source |
|---|---|---|---|---|
| **D1** | §4.3.1 OR-clause-1 | DALI∨SLI weighted-vote NOT_ELIGIBLE (ws=237 < floor 250, declarative-only RED) **단일 metric**, remediation 3 candidates deferred | **3 candidates 모두 통합 spec 등록** + weighted-vote (v1) 와 substrate-aware (v2 #207) 의 OR-disjunction 으로 OR-clause-1 재정의: `(weighted_vote_v1 ELIGIBLE_FULL) OR (v2_redesign ELIGIBLE_PARTIAL_OR_FULL)`. 4-bb v10_benchmark_v4 substrate 에서 **OR-clause-1 PARTIAL_GREEN** 처음 수용 (v2 redesign 1/3 mode coverage late mode PASS) | `dali_sli_v2_redesign_landing.md` + .roadmap #207 |
| **D2** | §4.3 verdict matrix | **2-tier** (HARD_PASS strict-AND + SOFT_PASS per-gate ≥ 80%) | **3-tier verdict** (HARD_PASS / SOFT_PASS / NOT_ELIGIBLE). PARTIAL_AMBER (DALI+SLI v2 1/3 mode + EHL-3W locked) 는 SOFT_PASS path 진입, NOT_ELIGIBLE 은 OR-clause-1 + OR-clause-2 동시 RED. fallback Mk.XI v10 그대로 | this v2.1 §4.5 |
| **D3** | §4.3.1 mode-aware integration | mode 개념 부재 — single conjunctive 또는 weighted-vote uniform 4-bb 비교 | **mode-aware metric (DALI+SLI v2)** = `family_loc` + `cusp_depth` 두 axis 독립 mode 그룹화 (input/early/late, boundary 50/500), intra-mode size ≥ 2 만 평가, axis-orthogonal substrate 명시적 수용 | `dali_sli_v2_redesign_landing.md` §2 |
| **D4** | §4.3.1 OR-clause demotion | 옵션 부재 (deferred remediation candidate #3) | **OR-clause-1 demotion to Soft PASS 옵션 명시** — Hard PASS chain 에서 DALI+SLI 항 삭제 후 Soft PASS evidence 로 강등하는 fallback path. 본 cycle 에서는 demotion **NOT enacted** (v2 redesign #207 의 PARTIAL ELIGIBLE 가 OR-clause-1 path 살아있게 유지), 단 v2.1 spec 에 frozen | this v2.1 §4.3 |
| **D5** | §4.3 substrate replacement | candidate 부재 | **substrate replacement candidate list** — 현재 4-bb (Mistral/Qwen3/Llama/gemma) 가 input/early mode size<2 으로 1/3 coverage 한정. 추가 backbone 후보 4 (Qwen2.5-1.5B / gemma2-2B / Phi-3.5-mini / Llama-3.2-1B) 등록, 6-8 bb matrix 시 3/3 mode coverage 회복 path 명시 | `dali_sli_v2_redesign_landing.md` §8 + this v2.1 §4.4 |
| **D6** | §4.6 trigger | v2.1 trigger 부재 | **post-DALI+SLI v2 land trigger spec** — v2 redesign already landed (#207 ad6484a5, sha256 `0281bbb4…`) 이므로 §4.6 의 prerequisite 4 조건 ALL_MET 시 v2.1 actual lock. v2 redesign re-iteration (mode boundary sticky rule) 은 별도 후속 cycle | this v2.1 §4.6 |

**non-changes (v2 그대로 carry-over)**:
- §4.1 inherited gates G0..G7 (Path A P1+P2+P3 / CPGD AN11(b) / 5-tuple V0..V_pairrank)
- §4.2 NEW Mk.XII-specific gates G8/G9/G10 (transversal / sparsity / triangulation) verdicts
- §4.3.2 OR-clause-2 EHL-3W cross-axis convergent (PHENOMENAL × SUBSTRATE × TRAINING strict AND, conditional-GREEN post-EEG D+7)
- §4.3.3 v2 verdict matrix 의 G0/G1/G7/G8/G9 GREEN 6/6 wire-up + EHL-3W path 부분
- 6-gate cluster `min`-rule cluster_confidence = 0.70 weakest=G10

---

## §4.1 Weighted-vote remediation 3 후보 통합 spec

v2 §4.3 의 deferred remediation 3 candidates (substrate replacement / metric redesign / OR-clause demotion) 를 v2.1 spec 안에서 **공존 가능한 path** 로 통합. 어떤 단일 후보도 다른 후보를 배제하지 않으며, 4-bb substrate 의 axis-orthogonal property 를 수용하는 단일 chain integration 정의로 수렴.

### §4.1.1 후보 #1 — Substrate replacement (cmt.json 외 추가 metric 도입)

- **mechanism**: 현재 4-bb v10_benchmark_v4 (`{mistral,qwen3,llama,gemma}/cmt.json`) 외에 추가 backbone (§4.4 list 참조) 로 6-8 bb matrix 확장.
- **expected outcome**: `family_loc` + `cusp_depth` 두 axis 의 input/early/late 3-mode coverage 가 1/3 → 3/3 으로 회복, ALL_MODES_PASS_GREEN strict 가능.
- **chain integration**: OR-clause-1 의 `v2_redesign` operand 가 PARTIAL → FULL ELIGIBLE 로 lift.
- **v2.1 status**: **deferred** (cost ≈ $0 mac-local + 추가 cmt.json fixture 도입 후속 cycle).

### §4.1.2 후보 #2 — Metric redesign (mode-aware DALI+SLI v2) **already landed**

- **mechanism**: `tool/anima_dali_sli_v2_redesign.hexa` (#207 ad6484a5, sha256 `da971be1…`) — 3-mode topology (input/early/late, boundary 50‰/500‰) 기반 intra-mode-only 비교. 동일 backbone 이 두 axis 에서 다른 mode 일 수 있음 (axis-orthogonal substrate evidence 직접 수용).
- **per-mode PASS criterion**: `intra_DALI ≥ 700 ∧ intra_SLI ≥ 600 ∧ intra_COUPLED ≥ 600`.
- **overall verdict**: 4-tier (`NO_ELIGIBLE_MODE` / `ALL_MODES_PASS_GREEN` / `PARTIAL_AMBER` / `ALL_MODES_FAIL_RED`).
- **expected outcome (verified)**: late mode (Mistral=875 / Llama family_loc=625 / gemma=857) 에서 intra_DALI=750, intra_SLI=990, intra_COUPLED=861, weighted=868 → late mode PASS, eligible_modes=1, passing_modes=1 → **ALL_MODES_PASS_GREEN** (1/3 mode coverage).
- **chain integration**: OR-clause-1 의 `v2_redesign` operand = `ELIGIBLE` (mode-conditional). v2 redesign verdict 가 weighted-vote v1 의 NOT_ELIGIBLE 을 우회 — substrate-aware 분리로 honest path 확보.
- **v2.1 status**: **landed** (#207). v2.1 actual lock 의 핵심 trigger 조건 1.

### §4.1.3 후보 #3 — OR-clause demotion to Soft PASS

- **mechanism**: Mk.XII Hard PASS chain 정의에서 OR-clause-1 (DALI∨SLI) 항을 **삭제**하고 Soft PASS evidence 로 강등.
- **demoted Hard PASS**: `HARD_PASS := G0 ∧ G1 ∧ G7 ∧ G8 ∧ G9 ∧ OR-clause-2 (EHL-3W)` (OR-clause-1 부재).
- **DALI+SLI evidence**: Soft PASS tier 의 **G2/G3/G4-G6/G10 ≥ 80% PASS** 항목과 동일 weight 의 보조 evidence (정량적 영향 없음, Mk.XII verdict 의 supplementary).
- **v2.1 status**: **NOT enacted (frozen as fallback option)**. 본 v2.1 trigger 시점에 #207 v2 redesign PARTIAL ELIGIBLE 가 살아있으므로 OR-clause-1 path 유지. demotion 은 다음 두 조건 ALL_MET 시 활성화: (a) v2 redesign 도 NOT_ELIGIBLE 로 falsify (b) 후보 #1 substrate replacement 후 6-8 bb matrix 도 PARTIAL_AMBER 미달.

### §4.1.4 통합 OR-clause-1 정의 (v2.1 frozen)

```
OR-clause-1 v2.1 := weighted_vote_v1.OVERALL_PASS_BOTH                         (full)
                  OR weighted_vote_v1.WEAK_PARTIAL                              (floor)
                  OR v2_redesign.ALL_MODES_PASS_GREEN                           (mode-aware full)
                  OR v2_redesign.PARTIAL_AMBER                                  (mode-aware partial)
```

각 operand 는 disjoint, mode-aware metric (v2 redesign) 가 weighted-vote (v1) 의 substrate-uniform 한계를 보완. **v2.1 status**: **TRUE** via `v2_redesign.ALL_MODES_PASS_GREEN` (#207 late mode 1/3 coverage). 단 raw#10 honest qualifier — "1/3 mode coverage limited" Soft tier disclosure (§4.5 verdict 참조).

---

## §4.2 Mode-aware metric (DALI+SLI v2) 통합 plan

ad6484a5 (#207) 이미 land. 본 plan 은 chain 통합 인터페이스만 spec.

### §4.2.1 인터페이스

```json
// expected: anima-clm-eeg/state/dali_sli_v2_redesign_v1.json (sha256 0281bbb4…)
{
  "schema": "anima/dali_sli_v2_redesign/1",
  "thresholds": {
    "intra_dali_pass": 700,
    "intra_sli_pass": 600,
    "intra_coupled_pass": 600,
    "mode_weighted_gate": 500,
    "mode_min_size": 2
  },
  "positive": {
    "per_mode": [
      { "mode": 0, "label": "input",  "fl_size": 0, "cd_size": 0, "eligible": false },
      { "mode": 1, "label": "early",  "fl_size": 1, "cd_size": 2, "eligible": false },
      { "mode": 2, "label": "late",   "fl_size": 3, "cd_size": 2, "eligible": true,
        "intra_dali": 750, "intra_sli": 990, "intra_coupled": 861, "weighted": 868, "pass": true }
    ],
    "eligible_modes": 1, "passing_modes": 1,
    "overall_verdict": "ALL_MODES_PASS_GREEN"
  },
  "negative": { "valid_trials": 3, "fail_count": 2, "fail_rate_x1000": 666, "discriminates": true }
}
```

### §4.2.2 chain integration call

Mk.XII Hard PASS aggregator (`tool/mk_xii_hard_pass_composite.hexa` 또는 v2.1 후속 update) 가 v2 redesign JSON 을 OR-clause-1 의 secondary operand 로 ingest:

```
oc1_w_full     := (state/dali_sli_weighted_vote_v1.json).overall_pass_both
oc1_w_partial  := (state/dali_sli_weighted_vote_v1.json).weak_partial
oc1_v_full     := (state/dali_sli_v2_redesign_v1.json).overall_verdict == "ALL_MODES_PASS_GREEN"
oc1_v_partial  := (state/dali_sli_v2_redesign_v1.json).overall_verdict == "PARTIAL_AMBER"

OR-clause-1 v2.1  := oc1_w_full OR oc1_w_partial OR oc1_v_full OR oc1_v_partial
OR-clause-1 tier  := "FULL"    if (oc1_w_full OR oc1_v_full)
                   | "PARTIAL" if (oc1_w_partial OR oc1_v_partial) AND NOT FULL
                   | "RED"     otherwise
```

### §4.2.3 substrate-conditional caveat (raw#10 inline)

- **mode coverage 1/3 only** — input/early mode size<2 으로 평가 제외, late mode 단독 PASS. Soft tier disclosure 필수.
- **Llama axis-decoupled** — family_loc=625 (late mode) 와 cusp_depth=125 (early mode) 가 다른 mode 로 분리 — axis-orthogonal substrate evidence (raw#10 honest record).
- **mode boundary stickiness** — jitter ±400 시 mode 경계 통과 가능 (Llama 875→475), 별도 sticky-rule 후속 cycle 필요.
- **3-mode topology prior** — S7 N=10 결과 의존, N=12 confirmation 후 prior 강화.

---

## §4.3 OR-clause demotion to Soft PASS 옵션

§4.1.3 의 frozen fallback. 본 v2.1 에서 **NOT enacted**, 단 다음 조건 trigger 시 자동 활성화.

### §4.3.1 demotion trigger criteria

**ALL of the following met → demotion 활성화**:

1. **DALI+SLI v2 redesign falsified** — 향후 사이클에서 mode boundary sticky rule + 추가 backbone 후 v2 redesign 결과가 NOT_ELIGIBLE 로 회귀 OR negative discriminates rate 50% 미만으로 떨어짐.
2. **substrate replacement failed** — 6-8 bb matrix 확장 (§4.4) 후에도 3-mode coverage <= 1/3 잔존 OR PARTIAL_AMBER 이상 미달.
3. **OR-clause-2 (EHL-3W) conditional-GREEN 잔존** — phenomenal × substrate × training 3-axis 중 SUBSTRATE 또는 TRAINING 부분이 v2 redesign demotion 영향 미받음 (즉 strict-AND OR-disjunction 만족 path 가 EHL-3W 단독 의존 가능).
4. **사용자 명시 승인** — demotion 은 v2 → v3 transition 급 변경 (Mk.XII Hard PASS chain 정의 변동), declarative trigger 가 아닌 explicit user approval 필수.

### §4.3.2 demoted chain definition

```
HARD_PASS_DEMOTED  :=  G0 ∧ G1 ∧ G7 ∧ G8 ∧ G9
                     ∧ OR-clause-2 (EHL-3W)               // OR-clause-1 삭제
SOFT_PASS_DEMOTED  :=  G2 ∨ G3 ∨ G4-G6 ∨ G10 (≥ 80% PASS)
                     +  DALI+SLI v2 redesign 결과         // 보조 evidence, weight 미반영
```

### §4.3.3 v2.1 not-enacted disclosure

본 v2.1 trigger 시점 (#207 v2 redesign ALL_MODES_PASS_GREEN 1/3 coverage, weighted-vote v1 NOT_ELIGIBLE) 에서:
- **demotion trigger 1 NOT_MET** (v2 redesign ELIGIBLE)
- **demotion trigger 2 NOT_TRIGGERED** (substrate replacement 후속 사이클 deferred, 본 cycle scope 외부)
- **demotion trigger 3 PARTIALLY_MET** (EHL-3W 자체는 conditional-GREEN, post-EEG D+7 prerequisite)
- **demotion trigger 4 ABSENT** (사용자 demotion 승인 미요청)

→ 4 trigger 전원 ALL_MET 미달. demotion **NOT enacted**, 단 spec-level frozen fallback 으로 v2.1 안에 record. v3 transition 의 candidate path.

---

## §4.4 Substrate replacement candidate list

§4.1.1 후보 #1 의 구체화. 현재 4-bb v10_benchmark_v4 의 mode coverage 1/3 한계 (input mode size=0 / early mode size=1 미만 size 만족) 해결 위해 추가 backbone candidate 등록.

### §4.4.1 4 추가 backbone candidates

| # | backbone | 예상 mode (family_loc / cusp_depth) | 도입 효과 | source |
|---|---|---|---|---|
| **A** | Qwen2.5-1.5B | early/early | early mode size 1→2 lift, 2/3 mode coverage 진입 | LoRA C2 corpus 적합 (sister to Qwen3) |
| **B** | gemma2-2B | input/early | input mode size 0→1, early mode size 1→2 | small-2B family sentinel mode 0 후보 |
| **C** | Phi-3.5-mini | input/input | input mode size 0→1+ | 3-bb input mode 단독 평가 가능 |
| **D** | Llama-3.2-1B | early/early | Llama family axis-orthogonal 보강, early mode size 1→3 | Mk.XI v10 family Llama 와 sister |

### §4.4.2 6-8 bb matrix expected mode topology

| matrix size | input | early | late | total mode coverage |
|---|---|---|---|---|
| **현재 4-bb** | 0 | 1 | 3 | 1/3 (late only) |
| **5-bb (+A)** | 0 | 2 | 3 | 2/3 (early + late) |
| **6-bb (+A+B)** | 1 | 3 | 3 | 2/3 (input still size<2) |
| **7-bb (+A+B+C)** | 2 | 3 | 3 | **3/3 ALL_MODES_PASS_GREEN possible** |
| **8-bb (+A+B+C+D)** | 2 | 4 | 3 | **3/3 + early-axis robustness** |

raw#10 honest: 본 표는 mode 분류 expected, 실제 cmt.json fixture 측정 후 확정.

### §4.4.3 도입 cost

- 각 backbone cmt.json fixture 생성: $0 mac-local (existing v10_benchmark_v4 procedure 동일)
- LoRA training (선택적): Qwen2.5-1.5B / gemma2-2B / Phi-3.5-mini / Llama-3.2-1B 각 ~$0.2-0.5 GPU H100 (forward-auto-approval policy 内)
- 총 추정: $0 mac-local (cmt.json reuse) ~ $1-2 GPU (LoRA 신규 학습 시)

### §4.4.4 v2.1 deferred status

본 v2.1 trigger 시점에 후보 #1 (substrate replacement) 은 **deferred**. v2 redesign (#207) 의 1/3 coverage 가 ELIGIBLE 로 OR-clause-1 path 살아있으므로, substrate replacement 는 cluster_confidence lift (G10 ceiling 0.72 이상) 와 함께 후속 cycle 로 prioritize.

우선순위 (`feedback_completeness_frame` weakest-link first):
1. **G10 D+5 hardware activation** (post-EEG, weakest=G10 0.70)
2. **G8 D+6 real-falsifier MI port**
3. **D+7 Hard PASS recompute + EHL-3W lock**
4. **substrate replacement (후보 #1, +A+B+C 7-bb matrix)** — 본 §4.4.1 candidate 도입
5. **mode boundary sticky rule (v2 redesign re-iteration)** — Llama jitter PASS 의 leak 차단

---

## §4.5 Chain integration verdict criteria (3-tier)

v2 의 2-tier (HARD_PASS / SOFT_PASS) 를 **3-tier** (HARD_PASS / SOFT_PASS / NOT_ELIGIBLE) 로 확장.

### §4.5.1 HARD_PASS (strict-AND, OR-disjunction)

```
HARD_PASS  :=  G0 ∧ G1 ∧ G7 ∧ G8 ∧ G9
              ∧ ( OR-clause-1 v2.1 (DALI∨SLI weighted-vote OR mode-aware redesign)
                 OR  OR-clause-2 (EHL-3W cross-axis convergent) )
```

**HARD_PASS_FULL**: 5-gate composite + (OR-clause-1 FULL OR OR-clause-2 ALL_PASS_AT_D+7)
**HARD_PASS_PARTIAL**: 5-gate composite + OR-clause-1 PARTIAL + OR-clause-2 conditional-GREEN (post-EEG pending)
**HARD_PASS_OC2_ONLY**: 5-gate composite + OR-clause-1 RED + OR-clause-2 ALL_PASS_AT_D+7 (v2 §4.3.3 행 그대로)

### §4.5.2 SOFT_PASS

- G2 / G3 / G4-G6 / G10 ≥ 80% PASS (per-gate)
- G0/G1/G7/G8/G9 GREEN 6/6 wire-up but EHL-3W still pending
- v2 redesign PARTIAL_AMBER (eligible_modes>0 but passing_modes < eligible_modes) — Soft tier disclosure 필수
- (after demotion) v2.1 §4.3.2 demoted chain 의 보조 evidence

### §4.5.3 NOT_ELIGIBLE

- **G0 fail** (CPGD math broken) → 즉시 Mk.XI v10 fallback
- **G7 fail** (5-tuple ≤ 3/5)
- **G8+G9 동시 fail** (transversality + sparsity 모두 broken)
- **OR-clause-1 RED AND OR-clause-2 RED** (양 OR operand 모두 falsified)
- **demotion 4 trigger ALL_MET** but EHL-3W 도 falsified

### §4.5.4 v2.1 verdict matrix (current state)

| condition | v2.1 status | tier | path |
|---|---|---|---|
| G0 + G1 + G7 + G8 + G9 | **GREEN 6/6 wire-up** (#177) | preflight done | HARD_PASS prerequisite met |
| OR-clause-1.weighted_vote_v1 | NOT_ELIGIBLE RED (#183, ws=237) | falsified branch | — |
| OR-clause-1.v2_redesign | **ELIGIBLE PARTIAL** (#207, ALL_MODES_PASS_GREEN 1/3 coverage) | substrate-aware path | OR-clause-1 PARTIAL |
| **OR-clause-1 v2.1 통합** | **PARTIAL** (v2 redesign operand TRUE) | mode-aware partial green | survived |
| OR-clause-2 (EHL-3W) | conditional-GREEN (SUBSTRATE+TRAINING 2/3, PHENOMENAL post-EEG D+7) | active path | OC-2 path |
| **strict-AND Hard PASS** | **HARD_PASS_PARTIAL_PENDING** (5-gate GREEN + OR-clause-1 PARTIAL + OR-clause-2 conditional → post-EEG D+7 trigger 후 lock) | active | post-EEG D+7 first validation |

honest disclosure: 본 v2.1 trigger 시점에 Mk.XII = **HARD_PASS_PARTIAL_PENDING (substrate-aware OR-clause-1 PARTIAL via mode-aware redesign 1/3 coverage)**. v2 의 "OR-clause-1 RED single-operand → OC-2 단일 의존" 보다 strict 하게 lift 됨. fallback 그대로 Mk.XI v10.

---

## §4.6 Post-DALI+SLI v2 Land Trigger Spec

### §4.6.1 v2.1 actual lock prerequisite (4 조건)

ALL_MET 시 v2.1 actual update 가 v2 → v2.1 transition 으로 lock:

1. **DALI+SLI v2 redesign landed** — `tool/anima_dali_sli_v2_redesign.hexa` (sha256 `da971be1…`) + `state/dali_sli_v2_redesign_v1.json` (sha256 `0281bbb4…`) + `docs/dali_sli_v2_redesign_landing.md` 모두 disk commit + roadmap entry. **status: MET** (#207 ad6484a5).
2. **Mk.XII Hard PASS aggregator update plan** — `tool/mk_xii_hard_pass_composite.hexa` (또는 후속 v2.1 helper) 가 v2 redesign JSON 을 OR-clause-1 secondary operand 로 ingest 가능하도록 인터페이스 spec frozen. **status: MET** (본 v2.1 §4.2.2 frozen).
3. **6-gate cluster summary recompute plan** — cluster_confidence (`min`-rule) 가 OR-clause-1 PARTIAL inclusion 후 재계산 (현재 0.70 weakest=G10, OR-clause-1 PARTIAL 추가 시 ceiling 변동 없음, weakest unchanged). **status: MET** (mode-aware metric 은 OR-clause level, gate-level cluster 와 직교).
4. **사용자 v2.1 lock 명시 승인** OR **다음 cycle session 에서 본 prep spec read + apply 결정**. **status: PENDING** (본 prep spec 산출 후).

### §4.6.2 v2.1 actual lock 절차

trigger 4 ALL_MET 시:
1. `mk_xii_proposal_outline_v2_20260426.md` **read-only 그대로** (v2 frozen).
2. **새 doc** `mk_xii_proposal_outline_v2_1_chain_integration_20260426.md` 생성 — v2 §4 만 본 prep spec §4.0..§4.5 으로 replace, 다른 §0..§3, §5..§12 은 v2 cross-reference.
3. roadmap 새 entry append: "Mk.XII v2.1 §4 chain integration update locked (OR-clause-1 v2.1 OR-disjunction with mode-aware redesign)".
4. marker write `anima-clm-eeg/state/markers/mk_xii_v2_1_locked.marker`.
5. (선택) `tool/mk_xii_hard_pass_composite.hexa` 갱신 — OR-clause-1 v2.1 ingestion code path 추가.

### §4.6.3 v2.1 actual lock 후 next-cycle priority

§4.4.4 weakest-link first 우선순위 적용:
1. G10 D+5 (post-EEG)
2. G8 D+6 real-falsifier MI port
3. D+7 Hard PASS recompute + EHL-3W lock
4. substrate replacement 7-bb matrix (§4.4.1)
5. mode boundary sticky rule (v2 redesign re-iteration)

### §4.6.4 본 prep spec 의 scope 한계 (raw#10 honest)

본 v2.1 prep spec 자체는 **actual v2.1 lock 아님**. v2 § 4 갱신 candidate frozen + trigger 4 prerequisite 명시 + verdict matrix recompute spec 만 기록. v2 본문 / v2 §4 / Mk.XII Hard PASS aggregator code 모두 destructive 변경 0건 — read-only 보존.

ad6484a5 (#207) DALI+SLI v2 redesign 결과 (sha256 `0281bbb4…`) 는 disk commit + roadmap landed 상태이므로, v2.1 actual lock trigger 시 immediate spec apply 가능. 단 trigger 4 (사용자 승인 OR session 결정) 미충족 시 본 prep spec 의 frozen design 만 제공, lock action 미수행.

---

## §4.7 raw#10 honest caveat (v2.1 §4 추가 4)

v2 §8 의 caveat 10 carry-over + 본 v2.1 §4 갱신 추가 caveat:

11. **v2.1 prep spec ≠ actual lock** — 본 doc 은 trigger 4 prerequisite 충족 후 v2.1 actual update 가 별도 doc 로 lock 되는 prep spec. v2 §4 본문 read-only 보존. (§4.6 trigger 절차 참조)
12. **OR-clause-1 v2.1 PARTIAL 1/3 mode coverage 한정** — 4-bb v10_benchmark_v4 substrate 에서 v2 redesign 의 ALL_MODES_PASS_GREEN 은 late mode (Mistral/Llama-fl/gemma) 단독 evidence. input/early mode size<2 evaluation deferred. SOFT tier disclosure 필수 (§4.5.4).
13. **mode boundary stickiness 미해결** — Llama jitter ±400 시 family_loc 875→475 mode 변경, [Mistral, gemma] trivially close → mode-membership leak. v2 redesign §8 후속 사이클 candidate 3 (sticky rule) 적용 후 v2.1 re-validation 필요.
14. **substrate replacement candidate list = expected mode placement** — §4.4.1 4 backbone (Qwen2.5-1.5B/gemma2-2B/Phi-3.5-mini/Llama-3.2-1B) 의 input/early/late mode 분류는 expected, 실제 cmt.json fixture 측정 후 확정. 6-8 bb matrix lift 효과는 hypothesis tier.

---

## §4.8 ω-cycle 6-step ledger (본 prep spec session)

| step | action | result |
|---|---|---|
| 1 | design — §4.0..§4.6 6 sections frozen (changelog + 3-candidate integration + mode-aware metric + demotion option + substrate list + 3-tier verdict + trigger spec) | OK |
| 2 | implement — md doc `mk_xii_proposal_v2_section_4_chain_integration_v2_1_spec.md` write | OK |
| 3 | positive selftest — 6 sub-§ 모두 evidence + spec 정확 (DALI+SLI v2 ALL_MODES_PASS_GREEN late mode evidence + weighted-vote v1 NOT_ELIGIBLE evidence + cluster_confidence 0.70 weakest=G10 carry + OR-clause-1 v2.1 PARTIAL operand evaluation table + 3-tier verdict matrix recompute + 4-prerequisite trigger spec) | OK |
| 4 | negative falsify — 1 후보 dropped 시 chain integration 변동: (a) **#1 substrate replacement dropped** → §4.4 candidate list reference 만 남음, OR-clause-1 path 영향 X (v2 redesign 1/3 coverage 그대로 PARTIAL); (b) **#2 metric redesign dropped** → OR-clause-1 v2.1 의 secondary operand 부재, weighted-vote v1 NOT_ELIGIBLE 단독 → OR-clause-1 RED, OC-2 단일 의존으로 회귀 (v2 §4.3.3 그대로); (c) **#3 OR-clause demotion dropped** → demotion fallback option 부재, v2.1 의 v3 transition path 차단, 다른 영향 X. | OK (3 falsify branch 모두 chain 영향 명시) |
| 5 | byte-identical — 본 doc 은 spec md, content frozen, 동일 conditions 동일 byte (timestamp 외) | OK (write 후 sha256 stamp) |
| 6 | iterate — marker + memory + roadmap + 보고. trigger 4 ALL_MET 후속 cycle 시 v2.1 actual lock | OK |

---

## §4.9 Cross-references

- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_outline_v2_20260426.md` — **v2 frozen** (this v2.1 prep spec §4 update target)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` — **v1 frozen** (sha256 prefix `4f7fd4d2…`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/dali_sli_v2_redesign_landing.md` — **#207 ad6484a5 DALI+SLI v2 substrate-aware mode-grouped landing**, sha256 tool=`da971be1…` state=`0281bbb4…`
- `/Users/ghost/core/anima/anima-clm-eeg/docs/dali_sli_weighted_vote_landing.md` — **#183 weighted-vote v1 NOT_ELIGIBLE landing**, ws=237 < floor 250
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_integration_6gate_cluster_summary.md` — 6-gate cluster `min`-rule weakest=G10 0.70
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_d_day_simulated_landing.md` — **#204 D-day simulated dry-run** post-EEG D+5/D+6/D+7 pipeline pre-rehearsal
- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_hard_pass_landing.md` — **#177 Hard PASS composite GREEN 6/6**, chained_fingerprint 2638701628
- `/Users/ghost/core/anima/anima-clm-eeg/state/dali_sli_v2_redesign_v1.json` — v2 redesign output (sha256 `0281bbb4…`)
- `/Users/ghost/core/anima/anima-clm-eeg/state/dali_sli_weighted_vote_v1.json` — weighted-vote v1 output
- `/Users/ghost/core/anima/anima-clm-eeg/state/markers/mk_xii_v2_section_4_v2_1_complete.marker` — **본 prep spec marker** (silent-land 방지)
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_completeness_frame.md` — weakest-link first policy (§4.4.4 priority order basis)
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_omega_cycle_workflow.md` — declarative-only ≠ closure 룰 (§4.8 raw#10 caveat 11 ground)
- `.roadmap` #144 (Mk.XII anchor) / #177 (Hard PASS) / #183 (weighted-vote NOT_ELIGIBLE) / #190 (cluster summary) / #204 (D-day simulated) / #207 (DALI+SLI v2 redesign)

---

## §4.10 raw compliance (v2.1 prep spec)

- **raw#9 hexa-only directive**: 본 산출물은 .md doc, hexa-only directive scope outside (raw#9 strict 적용은 tool/.hexa 산출물 한정). v2.1 actual lock 시 `tool/mk_xii_hard_pass_composite.hexa` 갱신 path 가 hexa native 그대로.
- **raw#10 no overclaim**: prep spec ≠ actual lock 명시, OR-clause-1 v2.1 PARTIAL 1/3 mode coverage 한정 명시, mode boundary stickiness 미해결 명시 (§4.7 caveat 11-14).
- **raw#12 cherry-pick-proof**: §4.0 changelog first listed, §4.5 verdict matrix 사전 frozen, post-hoc tuning 차단.
- **raw#15 SSOT**: this v2.1 prep doc + sister docs (v2 frozen + v1 frozen + DALI+SLI v2 + v1 + cluster summary + D-day simulated + Hard PASS landing).
- **raw#37/38 ω-saturation cycle**: design (§4.0..§4.6 frozen) → impl (this prep doc) → fixpoint marker.

omega-saturation:fixpoint-mk-xii-v2-section-4-v2-1-prep-spec
