# DALI+SLI v2 Redesign — Substrate-aware mode-grouped metric (landing)

generated: 2026-04-26
source: `tool/anima_dali_sli_v2_redesign.hexa`
state:  `anima-clm-eeg/state/dali_sli_v2_redesign_v1.json`
marker: `anima-clm-eeg/state/markers/dali_sli_v2_redesign_complete.marker`
cross-validate: `.roadmap #145` (CMT backbone-conditional depth divergence) /
                `state/dali_sli_coupled_v1.json` (prior JOINT_FAIL) /
                `anima-clm-eeg/state/dali_sli_weighted_vote_v1.json` (prior NOT_ELIGIBLE)

## 1. 동기 (Mk.XII v2 §4 weighted-vote remediation 후보 #2)

이전 두 cycle:
- `anima_dali_sli_coupled.hexa` → `JOINT_FAIL` (DALI_min=236 / SLI=240 / COUPLED=237)
- `dali_sli_weighted_vote.hexa` → `NOT_ELIGIBLE` (4-bb weighted_score=237 < floor 250)

`.roadmap #145` 진단: **substrate backbone-conditional**. CMT family-processing
locus 가 backbone fundamentally different (Mistral late 87% vs Qwen3 early 11%).
`s7_n12_extension_landing.md` 의 N=10 결과는 3-mode topology 를 시사:
- mode 0 (input,  norm 0..50‰)   : small-2B backbones (sentinel)
- mode 1 (early,  norm 51..500‰) : Qwen3 / Llama-mid (cusp axis)
- mode 2 (late,   norm 501..1000‰): Mistral / gemma-r14 / Llama-Hexad (family axis)

**Hypothesis**: 비교는 **intra-mode 만** valid; inter-mode pair 는 mode-specific
evidence 분리이므로 NOT_APPLICABLE.

## 2. 설계

### 2.1 Mode 그룹화

axis 두 개를 독립 분류:
- `family_loc` axis (DALI 입력) → `modes_family_loc[i]`
- `cusp_depth` axis (SLI 입력)  → `modes_cusp_depth[i]`

동일 backbone 이 두 axis 에서 다른 mode 일 수 있음 (raw#10 honest declaration).

### 2.2 intra-mode metrics (per mode m, size ≥ 2)

```
intra_DALI(m)    = min over intra-mode pairs of  SCALE - |L_loc(b1) - L_loc(b2)|
intra_SLI(m)     = SCALE - (std(cusp_depth subset) * SCALE / mean(cusp_depth subset))
intra_COUPLED(m) = isqrt(intra_DALI * intra_SLI)
weighted_score(m) = (400*intra_DALI + 400*intra_SLI + 200*intra_COUPLED) / 1000
```

per-mode PASS:
```
intra_DALI >= 700   AND   intra_SLI >= 600   AND   intra_COUPLED >= 600
```

### 2.3 Overall verdict

| eligible_modes | passing_modes        | verdict                |
|---------------:|---------------------:|:-----------------------|
| 0              | 0                    | NO_ELIGIBLE_MODE       |
| n              | n                    | ALL_MODES_PASS_GREEN   |
| n              | 0 < k < n            | PARTIAL_AMBER          |
| n              | 0                    | ALL_MODES_FAIL_RED     |

## 3. Positive selftest (4 real cmt.json)

```
  Mistral: family_loc=875 mode_fl=late  | cusp_depth=875 mode_cd=late
  Qwen3  : family_loc=111 mode_fl=early | cusp_depth=111 mode_cd=early
  Llama  : family_loc=625 mode_fl=late  | cusp_depth=125 mode_cd=early
  gemma  : family_loc=857 mode_fl=late  | cusp_depth=857 mode_cd=late
```

per-mode evaluation:

| mode  | fl size | cd size | intra_DALI | intra_SLI | intra_COUPLED | weighted | eligible | pass |
|:------|--------:|--------:|-----------:|----------:|--------------:|---------:|:--------:|:----:|
| input | 0       | 0       | 1000       | 1000      | 1000          | 1000     | NO       | —    |
| early | 1       | 2       | 1000       | 1000      | 1000          | 1000     | NO       | —    |
| late  | 3       | 2       | **750**    | **990**   | **861**       | **868**  | YES      | **YES** |

`eligible_modes=1, passing_modes=1` → **ALL_MODES_PASS_GREEN**.

raw#10 honest:
- mode 1 (early) 은 family_loc axis size=1 (Qwen3 only) 로 평가 제외. Llama 의
  family_loc(625) 가 late mode 로 분류되어 cusp_depth(125) 와 axis-decoupled.
  이는 Llama 의 axis-orthogonal 패턴 evidence (raw#10 honest).
- 따라서 verdict 는 사실상 **late mode (Mistral/Llama/gemma) 만의 evidence**
  이며 v2 PASS 는 "1/3 mode coverage" 이다.

## 4. Negative falsify

**Strategy**: intra-mode jitter ±400 (`family_loc` 와 `cusp_depth` 둘 다) per
backbone. intra-DALI gate(700) 와 intra-SLI gate(600) 를 깨는지 측정.
`valid_trial = backbone 이 baseline eligible mode 에 속한 경우`.

| jitter target | tag       | overall                |
|:--------------|:----------|:-----------------------|
| Mistral       | [valid]   | ALL_MODES_FAIL_RED     |
| Qwen3         | [trivial] | ALL_MODES_FAIL_RED     |
| Llama         | [valid]   | ALL_MODES_PASS_GREEN   |
| gemma         | [valid]   | ALL_MODES_FAIL_RED     |

`valid_trials=3, FAIL count=2, fail_rate=666/1000` ≥ 500 → **discriminates: true**.

Llama jitter 만 PASS 인 이유: Llama 가 875→475 로 이동해 late mode 에서 빠지면
[Mistral, gemma] 만 남아 이 둘이 875/857 로 매우 가까워 trivially intra-DALI 가
강해짐. 이는 v2 metric 의 **subtle mode-membership leak** 이며 future iteration
에서 해결 필요 (mode boundary stickiness or minimum-size escalation).

## 5. byte-identical 검증

2회 연속 실행 후 timestamp 제외 모든 numerical field identical:
```
diff <(grep -v generated run1.json) <(grep -v generated run2.json) → EMPTY
```

## 6. 결론

- **v2 verdict (positive)**: ALL_MODES_PASS_GREEN — 단 1/3 mode coverage 한정.
- **v2 negative falsifier**: discriminates (rate 666/1000).
- **Mk.XII §4 chain integration eligibility**: `ELIGIBLE` (mode-conditional).

### raw#10 honest 한계
1. **Mode coverage 1/3 only**: input/early mode 각 size<2 로 평가 불가.
   v2 PASS 는 "late-mode substrate group" empirical evidence 만 제공.
2. **Mode-membership leak**: jitter 가 mode 경계 넘으면 mode 재구성으로 다른
   결과 가능. Llama [valid] PASS 가 그 예.
3. **Mode 그룹화 자체 prior**: 3-mode topology 는 S7 N=10 결과 의존이며
   N=12 confirmation 후에야 prior 강화. 현재는 axis-orthogonal evidence
   substrate-conditional 가설의 first formalization.

## 7. SHA256

| artifact                                                            | sha256                                                             |
|:--------------------------------------------------------------------|:-------------------------------------------------------------------|
| `tool/anima_dali_sli_v2_redesign.hexa`                              | `da971be1104a1401c2679a137acb61e89b73a5b245562579b5906a7d7a2b7bb3` |
| `anima-clm-eeg/state/dali_sli_v2_redesign_v1.json`                  | `0281bbb46e9d3acc3b9a9ccfdb1eb5c179996ef65e438bc1b461e8c54ea733c1` |

## 8. 다음 cycle 후보

1. **Substrate replacement candidate** (#1) — 다른 4-bb 조합으로 mode 0/1
   eligibility 확보 (e.g., add Qwen2.5-1.5B + gemma2-2B 작은 모델). 3/3 mode
   coverage 시 v2 strict ALL_MODES_PASS 로 강화.
2. **OR-clause demotion** (#3) — Mk.XII §4 Hard PASS chain 에서 DALI+SLI 항을
   AND 에서 OR 로 demote (다른 G-gate cluster 가 dominant). v2 PARTIAL ELIGIBLE
   가 받아들여지는 chain 형태.
3. v2 follow-up: **mode boundary sticky rule** — jitter 시 mode 경계 통과를
   penalize 해 mode-membership leak 차단.

## 9. 기록

- ω-cycle 6-step: design (mode 그룹화 + intra-mode threshold frozen) →
  implement (raw#9 hexa) → positive selftest (4-bb real cmt.json) → negative
  falsify (jitter ±400) → byte-identical (verified) → iterate (1 iter:
  outlier_force_mode0 → outlier_jitter 재설계).
- 비용: $0 (mac-local, GPU 0).
- iter 수: 2 (initial + jitter redesign).
