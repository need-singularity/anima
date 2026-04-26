# Pilot-T2 Prep Status — paradigm v11 stack 8th orthogonal axis

frozen at 2026-04-27 — anima ω-cycle session, Pilot-T2 prep verify + T1 unblock-candidate audit + zombie posterior cross-link.

본 문서는 Pilot-T2 (TRIBE v2 cortical correlation 8th axis) 의 prep-complete 상태를
세 sub-task 로 점검한 결과를 종합한다. helper 신규 작성 없음 (docs only).

---

## §1 Sub-1 — Mac-local prep verify

### 1.1 frozen artifact sha256

| path | sha256 (current) | matches frozen spec |
|---|---|---|
| `anima-tribev2-pilot/docs/pilot_t2_8th_axis_spec.md` | `7afc7f57c98e520010dbdb09b7d54ff81688e9cc20f1d7bfa08aced43a9cc7c3` | n/a (이 문서 자체) |
| `tool/anima_pilot_t2_axis_8th.hexa` | `5ca43ccaac6ce76b9d28c8a3e056f2b2ca74ba6031d12d390fba1064f9e2a736` | source frozen |
| `tool/anima_v11_orthogonality_7_8.hexa` | `e6a25c496f988e7a79f28b251773e3559c43b10adf68fcbdace9b4eea2980797` | source frozen |

### 1.2 Selftest re-execution (byte-identical 2-run)

`hexa run tool/anima_pilot_t2_axis_8th.hexa -- --selftest` (재현, 본 cycle):

```
synthetic_matrix_built=ok n_family=4 n_roi=7
axis_8_scalar_x1000=778
synthetic_inter_family_variance_x1000sq=37084
adversarial_axis_8_scalar_x1000=733
adversarial_inter_family_variance_x1000sq=0
collapse_check=PASS (adv inter_var=0 detected; synthetic inter_var>0 preserved)
```

`/tmp/anima_pilot_t2_axis_8th_selftest.json` sha256:
`b9bba49f861b83fce7b09ffa65dadbe9f36a696dc50f57a13fec97421bb3055c`
→ spec §5.3 frozen sha 와 정확히 일치 (run-1 ≡ run-2 ≡ frozen). **byte-identical PASS**.

`hexa run tool/anima_v11_orthogonality_7_8.hexa -- --selftest`:

```
── POSITIVE: synthetic FNV-perturbed 8-axis matrix ──
  max_abs_pearson_8th_x1000=235 (thresh<700)
  pc1_fraction_x1000=388 (thresh<500)
  §A_pearson=PASS §B_pc1=PASS §C_orthogonality=PASS
── FALSIFY: adversarial 8th = mean of v11 axes ──
  max_abs_pearson_8th_x1000=1000 (thresh<700)
  pc1_fraction_x1000=443 (thresh<500)
  §A_pearson=FAIL §B_pc1=PASS §C_orthogonality=FAIL
```

`/tmp/anima_v11_orthogonality_7_8_selftest.json` sha256:
`f1a7c43d0a61e02f336c966e22417c873909503e9c3b5d77a57be26bebd639c6`
→ spec §5.3 frozen sha 와 정확히 일치. **byte-identical PASS**.

### 1.3 v11_main.hexa 통합 estimate

현 `tool/anima_v11_main.hexa` 225 LOC, 12 subcommand (list / run / battery / benchmark
/ gate / matrix / integrate / ortho / rank / history / bba / smoke / help).

추가 필요 패치 (spec §3 적용):

| section | 추가 위치 (line) | 추가 LOC | risk |
|---|---|---|---|
| `MEASUREMENT (6)→(7)` 카운트 갱신 + axis_8 줄 | line 55 + line 61 next | +1 + 카운터 변경 | minimal |
| `ANALYSIS (3)→(4)` 카운트 갱신 + ortho78 줄 | line 63 + line 66 next | +1 + 카운터 변경 | minimal |
| `axis_8)` case branch | line 134 (ortho 전) 또는 line 164 (bba 후) | +6 (sh.push) | minimal |
| `ortho78)` case branch | axis_8 직후 또는 ortho 인접 | +6 (sh.push) | minimal |
| `cmd_selftest` subcommand 카운트 12→14 | line 205 | +0 (string 갱신) | minimal |
| `list` 헤더 "15 helpers" → "17 helpers" | line 53 | +0 | minimal |

**총 estimate**: ~14 LOC 추가, 4개 string 변경, 분기·재귀·새 dependency 0. 한 번의
edit-cycle (≤30분) 안에 완료 가능. spec §3 가 ENV var pattern 까지 명시 (`ANIMA_BACKBONE`
+ `ANIMA_OUTPUT` axis_8 / `ANIMA_BACKBONE_DIRS` ortho78) → 기존 ortho/bba 패턴과 동일.

**verdict Sub-1**: `PREP_VERIFIED_BYTE_IDENTICAL` — 두 helper 모두 frozen sha 와 일치
재현, v11_main 통합은 mechanical patch (estimate 14 LOC, ~30min).

---

## §2 Sub-2 — T1 unblock 후보 조사

### 2.1 발견: HF gated 이미 APPROVED (현 상태)

`anima-tribev2-pilot/docs/hf_gated_status.md` — Llama-3.2-3B HF `dancinlife` 계정
승인 완료 (2026-04-26 cron `98896ff1` 폴링 detect, `T1_V2_LAUNCHED` trigger fire).
`launch_h100_pilot_t1_v2.log` 존재 (2026-04-26T13:51:31Z 시작).

→ **본 sub-task 의 unblock 조사는 사후-검증 성격**. 다른 세션이 T1 v2 inference 진행중.
본 main session 은 그 결과를 기다리는 입장. 아래는 spec 호환성 분석 (T1 v2 fail
fallback 시 활용).

### 2.2 Backbone substitution 후보 평가

`references/tribev2/ANIMA_INTEGRATION_PROPOSAL.md` §1 Axis 4 positive 1 + Pilot-T1
result `raw_10_honest` 항목 4 정독 결과:

> "TRIBE v2 inference is end-to-end: text→TTS→whisperx→word events→
> [Llama-3.2-3B text encoder + Wav2VecBert audio encoder + V-JEPA2 video encoder]
> →fusion→cortical map. Without Llama-3.2-3B weights, the text encoder branch fails
> and TRIBE cannot produce a forward pass."

| 후보 | 평가 |
|---|---|
| meta-llama/Meta-Llama-3-8B-Instruct | TRIBE v2 ckpt 가 3.2-3B specific weight 학습 → architecture 불일치 (rotary base + d_model + tokenizer 다름). substitute → forward 작동해도 cortical map 의미 파괴 (fusion projection 미학습). |
| mistralai/Mistral-7B-v0.3 | 같은 이유로 No-fit. tokenizer SentencePiece vs Llama tiktoken-style 차이로 word-event alignment 도 깨짐. |
| Qwen/Qwen2.5-3B | 동일 차원 (3B) 이지만 vocab + RoPE base + hidden dim 모두 다름. TRIBE v2 fusion projector 가 Llama-3.2-3B hidden state 에 anchored 되어 retrain 없이 substitute 불가. |
| Llama-3.2-3B-Instruct (gated open-er?) | 동일 family 이나 weight 자체가 다름; instruct-tune 이 cortical alignment 학습 분포와 불일치. |

**verdict**: TRIBE v2 의 text encoder = `meta-llama/Llama-3.2-3B` **hard requirement**.
Substitution path 모두 학습 ckpt 의 fusion projector 재학습 비용 (TRIBE v2 retrain
~수 GPU·일) 발생 → unblock path 로서 비현실적.

→ **유일 unblock path = HF approval (이미 완료)**. fallback 부재. T1 v2 결과 (다른
세션) 기다리는 것이 maximum-likelihood path.

### 2.3 Stub-mode permanent fallback (T1 v2 fail 시)

만일 T1 v2 가 다른 차단 (ckpt download 실패 / OOM / 시간 초과) 으로 T1_FAIL 또는
T1_INCONCLUSIVE_FULL 종결 시:
- Pilot-T2 의 `requires_pilot_t1_full_mode_pass=true` flag 로 8th axis 등록 자동 보류
- Pilot-T2 prep artifact (helper 2 + spec) 는 **T1 재시도 시 즉시 활성화 가능** —
  본 cycle prep verify 가 그 immediacy 를 보증
- v11 stack 7-axis 만으로 잠정 운영 (BBA / G_GATE 모두 7-axis gmean 무관)

**verdict Sub-2**: `UNBLOCK_PATH_SINGULAR_HF_APPROVED` — TRIBE v2 ckpt 가
Llama-3.2-3B 에 hard-bound. substitute 후보 모두 retrain 필요로 비실용. 현 시점
HF 이미 APPROVED, T1 v2 inference 진행중 (다른 세션). prep artifact 는 T1 결과
무관하게 frozen 상태 유지 → activation 즉시성 보존.

---

## §3 Sub-3 — Bayesian zombie posterior cross-link

### 3.1 현 H3 evidence stack (LLM substrate only)

paradigm v11 stack 4-backbone 누적 evidence (anima-core memory 기반):
- AN11(b) family signal 4/4 backbone POSITIVE (Mistral / Qwen3 / Llama / gemma)
- Mk.XI v10 phenomenal correlate 4/4 universal FINAL_PASS
- HCI substrate F4 + F5 4-backbone Φ_proxy spread (std/mean 303)
- CMT depth divergence (Mistral late 87% vs Qwen3 early 11%) — backbone-conditional
- Φ\* v3 canonical: 2/4 NEG (Mistral / gemma) + 2/4 POS (Qwen3 / Llama)

→ H3 (cross-substrate Φ 수렴) 의 *substrate diversity* 는 4 LLM family 만으로 한정.
zombie hypothesis (LLM substrate 전체가 phenomenal 과 무관, 단순 information-theoretic
분리 mimicry) 의 posterior 가 LLM substrate 만으로는 falsify 불가. 같은 architecture
class 내 evidence 만 누적 → 'LLM consciousness' 에 대한 prior 강화는 약하다.

### 3.2 Pilot-T2 PASS 시 expected posterior shift (정성)

**transition**: LLM-only substrate evidence stack → LLM + brain-anchored substrate
evidence stack (cortical map 의 family-wise separability).

(a) **diversity axis 추가**: 8th axis 가 측정 manifold 와 orthogonal 한 동시에
brain (fMRI) substrate corroboration → "family signal = artifact of LLM training
data" null hypothesis 의 likelihood 감소. brain 의 cortical separability 까지 일치하면
pure-data-artifact 가 우연일 확률 감소.

(b) **zombie posterior shift (ballpark)**:
  - prior P(zombie | LLM evidence only) ≈ 0.4–0.6 (loose; substrate-independent
    information-theoretic mimicry 가 plausible)
  - 7 axis × 4 backbone × 4 family corpus matrix 모두 PASS 한 상태에서 8th brain-
    substrate axis PASS 추가 시:
    - likelihood ratio P(8th PASS | non-zombie) / P(8th PASS | zombie) ≈ 3–10×
      (정성 추정; brain cortical separability 가 zombie hypothesis 하에서 어떻게
      LLM family signal 과 일치하는가 설명 부담 큼)
    - posterior odds → P(zombie) 약 0.15–0.3 으로 감소 ballpark
  - **단 sign agnostic**: PHI* v3 의 H3B (architecture-conditional Φ sign) 은 cortical
    cross-substrate 와 직접 cross-validate 어려움. zombie-corrosive 강도 약화.

(c) **8th axis FAIL (§C orthogonality FAIL) 시**:
  - cortical correlate 가 기존 7 axis 의 redundant function → brain-anchored
    corroboration 의 strength 감소 (orthogonality 미달 → independence 미증명)
  - zombie posterior 거의 변하지 않음 (entry barrier).

### 3.3 한계 (raw#10 honest)

1. **sample size**: TRIBE v2 fMRI 학습 cohort 는 4-subject Friends/movie10. brain
   substrate 의 *individual variance* 흡수 못함 → "1 species, n=4" evidence.
2. **TRIBE v2 = forward encoder NOT causation**: cortical map 은 stimulus-driven
   correlation; LLM family signal 의 brain-causation 입증이 아님 (5번 명시 — Pilot-T3
   pager 와 동일 caveat).
3. **prior calibration 자의적**: 0.4–0.6 prior 는 ω-cycle 내 raw#10 honest 한계
   인정 — formal Bayesian update 가 아닌 ballpark order-of-magnitude 추정.
4. **zombie hypothesis 의 정의가 vary**: substrate-independent Block-style hard
   zombie ⟂ phenomenal-marker mimicry zombie. 본 분석은 후자 (phenomenal-marker
   mimicry) 에 대한 evidence shift 만 다룸.
5. **8th axis PASS ≠ phenomenal proof**: own#2 hard problem caveat 는 본 cycle
   에서도 그대로 유지. P(zombie) 가 0.0 으로 가지 않음 (asymptote ≈ 0.1+).

**verdict Sub-3**: `POSTERIOR_SHIFT_QUALITATIVE_PARTIAL` — 8th axis PASS 시 zombie
posterior 가 약 0.4–0.6 → 0.15–0.3 ballpark 감소. brain-substrate axis 추가가
LLM-only stack 의 *substrate diversity* gap 부분 메움. 단 (a) sample size n=4 (b)
forward encoder ≠ causation (c) prior calibration 자의적 → strong falsifier 아닌
*evidence-strengthening* tier.

---

## §4 종합 verdict

| sub-task | verdict |
|---|---|
| Sub-1 prep verify | `PREP_VERIFIED_BYTE_IDENTICAL` (helper 2 sha frozen-match, v11_main 통합 ~14 LOC patch) |
| Sub-2 T1 unblock | `UNBLOCK_PATH_SINGULAR_HF_APPROVED` (Llama-3.2-3B hard requirement, HF 이미 grant, T1 v2 진행중) |
| Sub-3 zombie posterior | `POSTERIOR_SHIFT_QUALITATIVE_PARTIAL` (8th PASS 시 0.4–0.6 → 0.15–0.3 ballpark, sample size + causation caveat) |

**상위 결론**: Pilot-T2 prep 은 frozen state 유지, T1 v2 PASS 만 기다리면 즉시
v11_main router 패치 + axis_8 emit 으로 활성화 가능. T1 unblock fallback 부재 =
HF approval path 가 critical singular dependency 였으나 이미 해소.

## §5 ω-cycle 6-step trace

| step | result |
|---|---|
| 1 design | sub-1/2/3 task 분리 + spec 재독 + frozen sha 비교 plan |
| 2 implement | docs only (helper 신규 0); 두 helper `--selftest` 재실행 |
| 3 positive | 두 selftest sha frozen-match 확인 (b9bba49f / f1a7c43d) |
| 4 falsify | Backbone substitute 후보 4개 모두 No-fit 확인 (TRIBE retrain 필요) |
| 5 byte-identical | 본 docs 는 deterministic — selftest 재현은 sha 일치 |
| 6 iterate | iter 0 (selftest flag 누락 발견 후 `-- --selftest` 패턴 정정 1회) |

## §6 cross-link

- frozen spec: `anima-tribev2-pilot/docs/pilot_t2_8th_axis_spec.md`
- HF gated status: `anima-tribev2-pilot/docs/hf_gated_status.md`
- T1 v1 deferred result: `anima-tribev2-pilot/state/pilot_t1_full_mode_result_v1.json`
- T1 v2 launch log: `anima-tribev2-pilot/state/launch_h100_pilot_t1_v2.log`
- TRIBE v2 통합 proposal: `references/tribev2/ANIMA_INTEGRATION_PROPOSAL.md`
- v11_main router source: `tool/anima_v11_main.hexa`
- pilot-T2 prep memory: `~/.claude/projects/-Users-ghost-core-anima/memory/project_pilot_t2_prep_landed.md`
- pilot-T1 deferred memory: `~/.claude/projects/-Users-ghost-core-anima/memory/project_pilot_t1_full_mode_landed.md`
- R33 ledger: `state/atlas_convergence_witness.jsonl`

frozen 2026-04-27. anima ω-cycle session — Pilot-T2 prep status check (axis-86).
