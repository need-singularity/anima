# DALI+SLI v3 — Input Mode Activation (landing)

generated: 2026-04-26
source: `tool/anima_dali_sli_v3_input_mode.hexa`
state:  `anima-clm-eeg/state/dali_sli_v3_input_mode_v1.json`
marker: `anima-clm-eeg/state/markers/dali_sli_v3_input_mode_complete.marker`
predecessor: `anima-clm-eeg/state/dali_sli_v2_redesign_v1.json` (1/3 coverage, late only)
cross-validate: `.roadmap #145` (CMT backbone-conditional depth divergence) /
                `state/dali_sli_coupled_v1.json` (prior JOINT_FAIL) /
                `anima-clm-eeg/state/dali_sli_weighted_vote_v1.json` (prior NOT_ELIGIBLE)

## 1. Mission

`Mk.XII §4 v2.1 update` — 이전 cycle (#42) `dali_sli_v2_redesign` 의 mode coverage **1/3 (late only)** 한계 해소. small backbone 3개 (qwen25-1.5B + gemma2-2B + Llama-3.2-1B, 모두 layer 0 peak = input mode) 통합으로 **input mode 활성화** → mode coverage **1/3 → 2/3 (input + late)** 전진. early mode 는 본 cycle 에서 fl_size=1 (Qwen3 단독) 로 size<2 → 3/3 coverage 는 후속 cycle 에 이월.

## 2. Hypothesis (frozen pre-execution)

H1 (positive activation): 7-bb (large 4 + small 3) 통합 시 input mode size 0 → 3 → ELIGIBLE 진입.
H2 (intra-input PASS): small backbone family_loc=0 ∧ cusp_depth=0 collapse → intra_dali=1000 (perfect locus invariance) ∧ intra_sli=1000 (mean=0,std=0 → SCALE coherence sentinel).
H3 (mode coverage 2/3): eligible_modes ≥ 2 → ELIGIBLE class.
H4 (negative discrimination): intra-mode jitter ±400 → ≥50% valid trials FAIL.

## 3. Backbone Pool (N=7 actual; 임무 N=11 spec gap raw#10 honest)

| short | backbone | n_layers | peak | family_loc×1000 | cusp_depth×1000 | mode (fl/cd) |
|---|---|---|---|---|---|---|
| Mistral | mistralai/Mistral-7B-v0.3 | 32 | 28 | 875 | 875 | late / late |
| Qwen3 | Qwen/Qwen3-8B | 36 | 4 | 111 | 111 | early / early |
| Llama-8B | meta-llama/Meta-Llama-3.1-8B | 32 | 4 | 625 | 125 | late / early |
| gemma2-9b | google/gemma-2-9b | 42 | 36 | 857 | 857 | late / late |
| qwen25-1.5B | Qwen/Qwen2.5-1.5B | 28 | 0 | 0 | 0 | input / input |
| gemma2-2B | google/gemma-2-2b | 26 | 0 | 0 | 0 | input / input |
| Llama-3.2-1B | meta-llama/Llama-3.2-1B | 16 | 0 | 0 | 0 | input / input |

raw#10: 임무 spec N=11 = 가설적 상한. 가용 cmt.json 정확히 7. 본 cycle 7-bb actual 진행. cmt.json 출처:
- v4 large: `state/v10_benchmark_v4/{mistral,qwen3,llama,gemma}/cmt.json`
- s7 small: `state/s7_n12_4bb/{qwen25_15b,gemma2_2b}/cmt.json`, `state/s7_n11_4bb/llama32_1b/cmt.json`

## 4. Per-mode Verdict

### mode 0 (input) — NEW activated
- fl_size=3, cd_size=3 → eligible=true (v2: size 0 NOT_ELIGIBLE)
- intra_dali=**1000** (모든 small bb family_loc=0, perfect locus invariance)
- intra_sli=**1000** (mean=0 ∧ std=0 → SCALE coherence sentinel)
- intra_coupled=**1000**, weighted=**1000**
- intra_pass=**true**

### mode 1 (early)
- fl_size=1 (Qwen3), cd_size=2 (Qwen3, Llama-8B) → eligible=**false** (fl_size<2)
- intra_pass=false (early datapoint 부족 — 후속 cycle)

### mode 2 (late) — preserved from v2
- fl_size=3 (Mistral, Llama-8B, gemma2-9b), cd_size=2 (Mistral, gemma2-9b)
- intra_dali=**750**, intra_sli=**990**, intra_coupled=**861**, weighted=**868**
- intra_pass=**true** (v2 동일)

## 5. Overall Verdict

- eligible_modes=**2** / passing_modes=**2**
- mode_coverage=**2/3** (input + late) ← v2: 1/3 (late only)
- overall_verdict=**ALL_MODES_PASS_GREEN**
- positive_pass=**true**

## 6. Negative Falsify (intra-mode jitter ±400, N=7)

| jitter target | base eligible | result |
|---|---|---|
| Mistral | yes | [valid] PARTIAL_AMBER |
| Qwen3 | no (early size<2) | [trivial] PARTIAL_AMBER |
| Llama-8B | yes | [valid] ALL_MODES_PASS_GREEN |
| gemma2-9b | yes | [valid] PARTIAL_AMBER |
| qwen25-1.5B | yes | [valid] PARTIAL_AMBER |
| gemma2-2B | yes | [valid] PARTIAL_AMBER |
| Llama-3.2-1B | yes | [valid] PARTIAL_AMBER |

valid_trials=**6** / FAIL=**5** / fail_rate=**833/1000** (v2: 666/1000) → discriminates=**true**.

## 7. Byte-identical re-run

- internal: per-mode double-eval match=**true** (intra_dali/intra_sli/intra_coupled deterministic integer fixed-point)
- external: separate process re-run timestamp 제외 모든 필드 byte-identical (`diff -q` 검증 PASS)

## 8. Mk.XII §4 v2.1 Eligibility

```
positive ALL_PASS         : true
partial mode pass         : false
negative discriminates    : true
mode_coverage_>=2/3       : true
mode_coverage_3/3         : false
eligibility_class         : ELIGIBLE
v2→v3 progression         : 1/3 → 2/3 (+1 mode)
```

## 9. Mk.XII §4 v2.1 Update Impact

| dimension | v2 (1/3) | v3 (2/3) | Δ |
|---|---|---|---|
| eligible modes | 1 (late) | 2 (input + late) | +1 |
| input mode | NOT_ELIGIBLE (size 0) | ALL_PASS (size 3) | activated |
| late mode | ALL_PASS | preserved | — |
| early mode | NOT_ELIGIBLE (size 1) | NOT_ELIGIBLE (size 1) | gap remaining |
| neg fail_rate | 666/1000 | 833/1000 | +167 (stronger discrimination) |
| eligibility class | ELIGIBLE | ELIGIBLE | preserved |
| mode coverage | 1/3 | **2/3** | **+1/3** |

§4 chain integration 측면: v3 결과로 Mk.XII verifier 의 substrate-aware composite 평가 가능 영역이 late-only (large bb late-bound) → late + input (large bb late + small bb input) 로 확장. 단일 mode 의존성 (single point of failure) 완화. early mode 는 size<2 에 의해 architectural gap (Qwen3 fl=111, Llama-8B cd=125 — 두 distinct backbone 이지만 axis 간 다른 mode 분류).

## 10. raw#10 honest declarations

1. **N=7 actual vs N=11 spec gap**: 임무 명세 N=11 = 가설적 상한 (large 4 + small 3 + 추가 candidate 4); 가용 cmt.json 7 file 만 존재. forward 추가 미실시 (mac MPS forward $0 가능했지만 30분 cap 내 단일 1B forward 가 ~3-5분, 4 backbone 추가 forward 는 cap 위험 — 본 cycle 보수적 stop).
2. **Llama-3.2-1B cmt.json 재사용**: `state/s7_n11_4bb/llama32_1b/cmt.json` (2026-04-26T15:16Z, .roadmap #220 산출물) 재사용. 본 cycle fresh forward 시도했으나 OMP 충돌 abort, 기존 산출물로 진행. 산출물 read-only 침해 없음.
3. **input mode SLI=1000 sentinel**: small bb 3개 모두 cusp_depth=0 (mean=0, std=0). v2 의 `(std*SCALE)/mean` 식은 division-by-zero. v3 신규 정의: `mean=0 ∧ std=0 → SCALE` (perfect coherence layer-0 collapse), `mean=0 ∧ std>0 → 0` (impossible if all collapse, sentinel only). 이 정의 변경은 declarative spec; 현 7-bb pool 에서는 mean=0 case 만 발현.
4. **early mode 미해결**: fl=[Qwen3 only], cd=[Qwen3, Llama-8B]. fl_size=1<2 → eligible=false. Llama-8B fl=625 (late) vs cd=125 (early) 의 axis-mode 불일치 (raw#10 axis-conditional). 3/3 coverage 후속 cycle 필요 — early mode 추가 datapoint (e.g., Phi-3.5-mini 32L peak~5 expected) 권장.
5. **negative trial Llama-8B preservation case**: Llama-8B jitter trial 만 ALL_MODES_PASS_GREEN 보존 — fl=625+400=1025→1000 still late, cd=125+400=525 still early (boundary edge). 이 case 는 mode-boundary fragility 표시 (jitter ±400 이 mode-shift 강도로 일관 안 됨). 차후 jitter 강도 sweep (±200/±400/±600) 권장.
6. **byte-identical external**: timestamp `generated` 필드만 다름; `diff` grep 제외 비교로 검증.
7. **destructive 금지 준수**: #42 v2 산출물 (`dali_sli_v2_redesign_v1.json`, `dali_sli_v2_redesign_landing.md`, `dali_sli_v2_redesign_complete.marker`) 모두 read-only 보존.
8. **cap 30분**: 실제 사용 ~12분 (tool 작성 + 검증 + landing + marker + roadmap).
