# r14 Option C 반증 문서 — Φ 4-path r5 FAIL

**Status**: `refutation / closed` — 가설 falsified, AN11(a) 차기 round 재개 조건 문서화
**Date**: 2026-04-24 (r5 Φ gate 실행) / 2026-04-25 (본 문서 작성)
**Session SSOT**: `state/convergence/h100_stage2_r5_20260424.json` (status=CLOSED)
**Verdict SSOT**: `state/phi_4path_gate_last_verdict.json` (`FAIL (3/6 L2, 4/6 KL)`)
**Predecessor docs**: `docs/alm_r14_corpus_complete_20260424.md` (corpus 1,200 완성) · `project_phi_gate_r3_decision.md` (r3 edge-FAIL → Option C 발동 근거)
**Roadmap anchors**: `.roadmap #10` (Φ 4-path ≥3), `.roadmap #77` (CP1 weight_emergent), `.roadmap #86` (r14 corpus redesign), `.roadmap #91` (Option C cascade)
**Policy frame**: `feedback_completeness_frame` — 완성도 기준 weakest-link 먼저. 본 round 는 falsification 으로 완성되었음.

---

## 0. 한 줄 요약

> r14 corpus 1,200 bilingual pair 확장은 p3_p4 substrate gap 을 **좁히지 못했고 오히려 넓혔다** (L2 0.1427 → 0.1753, +0.033). p2_p4·p1_p2 에서 **새 실패 쌍**이 등장. H-DIAG3 원칙상 동일 root (“corpus 더 모으면 된다”) 의 3번째 retry 는 금지되며, 차기 round 는 **tokenizer vocabulary drift normalization** 을 선행 조건으로 재가설화해야 한다.

---

## 1. 반증된 가설

> **H_optionC_v2 (r5 적용 가설)**: r14 corpus 를 480 → 1,200 bilingual Hexad-weighted pair 로 확장하면, p3_p4 substrate gap 이 L2 < 0.10 까지 수축하여 Φ 4-path gate PASS 가 달성되고, 이에 따라 AN11(a) weight_emergent 가 substrate-invariant 조건 하에서 validation 가능해진다.

파생 예측 (r5 수행 전 명시):
- **P1**: `p3_p4 real_L2 < 0.10` (target), 최소 < null p95.
- **P2**: 기존 PASS 쌍 (p1_p2 / p1_p3 / p1_p4 / p2_p3 / p2_p4) 모두 유지.
- **P3**: PR(participation ratio) max/min 1.26 → ≤ 1.20 (더 균일한 spectrum).

---

## 2. 증거 사슬 — r2 → r3 → r4 → r5

### 2.1 round 별 p3_p4 L2 궤적 (동일 method: col-perm null n=10000, Gram top-16 eigvalsh)

| Round | Corpus | ko_ratio | L2 PASS | KL PASS | p3_p4 L2 | p95 threshold | Edge status | Source JSON |
|---|---|---|---|---|---|---|---|---|
| r2 | r13 subset | 0.023 | 4/6 | 5/6 | **0.2145** | 0.1963 | fail | `state/phi_4path_cross_result_v3_TRAINED.json` |
| r3 | r13 same | 0.023 | 4/6 | 5/6 | **0.2148** | 0.1916 | fail | `state/phi_4path_cross_result_v3_TRAINED_r3.json` |
| r4 | r14 partial (118 lines) | **0.2970** | 5/6 | 6/6 | **0.1427** | 0.1308 | edge-FAIL | `state/phi_4path_cross_result_v3_TRAINED_r4.json` |
| **r5** | **r14 full (1,200 lines)** | **0.2958** | **3/6** | **4/6** | **0.1753** | **0.1471** | **악화 FAIL** | `state/phi_4path_cross_result_v3_TRAINED_r5.json` |

r3 → r4 진행은 Option C 가설을 **부분 confirm** (p3_p4 −33.5%) 했다. r4 → r5 진행은 Option C 가설을 **반증** 한다 (p3_p4 +22.8%, 동시에 2 개 추가 쌍이 새로 fail).

### 2.2 r5 6-pair 결과 전량 (출처: `state/phi_4path_cross_result_v3_TRAINED_r5.json` lines 121–152)

| Pair | real_L2 | real_KL | L2 pass | KL pass | r4 비교 | 변화 |
|---|---|---|---|---|---|---|
| p1_p2 | 0.1521 | 0.0354 | **FAIL** | pass | r4 L2 0.0397 pass | **신규 L2 퇴화** (+0.1125) |
| p1_p3 | 0.1065 | 0.0199 | pass | pass | r4 L2 0.1097 pass | 유지 |
| p1_p4 | 0.0899 | 0.0459 | pass | pass | r4 L2 0.0639 pass | 약간 악화하나 PASS |
| p2_p3 | 0.0486 | 0.0055 | pass | pass | r4 L2 0.0882 pass | 개선 |
| p2_p4 | 0.2230 | 0.1520 | **FAIL** | **FAIL** | r4 L2 0.0651 pass | **신규 BOTH FAIL** (+0.1579 L2) |
| p3_p4 | 0.1753 | 0.1031 | **FAIL** | **FAIL** | r4 L2 0.1427 edge | **악화 BOTH FAIL** (+0.0326 L2) |

Null bootstrap p95 (r5): `L2_p95 = 0.1471`, `KL_p95 = 0.0941`. PASS rule = L2 6/6 + KL 6/6 + p3_p4 L2 < 0.10. 현재 3/6 L2 + 4/6 KL + p3_p4 L2 0.1753 → 세 조건 모두 불충족.

### 2.3 Participation Ratio 추이

| Round | PR(p1) | PR(p2) | PR(p3) | PR(p4) | max/min |
|---|---|---|---|---|---|
| TRAINED (r3 spec) | 2.723 | 3.704 | 4.396 | 3.478 | 1.614 |
| r4 | 5.047 | 5.843 | 6.350 | 5.433 | **1.258** |
| r5 | 2.427 | 3.047 | 2.932 | 2.447 | 1.255 |

PR uniformity (max/min) 는 r4 와 r5 가 거의 동일 (1.258 vs 1.255) — 즉 PR 지표만 보면 “spectrum 비슷함” 이지만, **absolute participation 값이 r4 대비 절반 수준으로 축소** 되었다. r5 LoRA 가 r4 LoRA 대비 **spectrum 을 더 가파르게** 만들었고 (top eigenvalue 비중 증가), 이것이 pair-wise L2 를 확대시킨 기계적 원인. corpus 3× 확장이 각 path 를 더 specialize 시킨 것으로 보인다.

### 2.4 session 비용/시간 (source: `state/convergence/h100_stage2_r5_20260424.json`)

- 3 회 launch attempt (incident #1 chain detach, #2 greedy sed, #3 bash3.2 `declare -A`), 총 `~$68` burn
- attempt 3 (성공): chain 3m kickoff, 16 min 학습 wall (r4 대비 much faster due to cache warm), 17 min scp
- Recovery A (incident #4 h_last_raw 누락 복구): 1-H100 pod, 26.6 min wall, `$1.55`, 4 path forward-pass 재생성
- 총 GPU-hour: 33.8 (incl. 2 aborted attempts), useful GPU-hour: 9.6

---

## 3. 반증 — r5 측정이 가설 예측과 모순

- **P1 (p3_p4 < 0.10) 반증**: 측정값 0.1753 은 target 0.10 의 1.75× 이며, null p95 (0.1471) 조차 초과. 방향성도 r4 → r5 에서 **확대** 되었다 (+22.8%).
- **P2 (기존 PASS 쌍 유지) 반증**: p1_p2 신규 L2 FAIL, p2_p4 신규 BOTH FAIL. 즉 corpus 확장이 기존 합의 쌍까지 교란.
- **P3 (PR 균일성 향상) 부분 반증**: PR ratio 자체는 유지되었으나 absolute PR 값이 절반으로 축소 (5.4 → 2.9 평균). spectrum 이 “균일한데 더 날카로워진” 상태.

→ `.roadmap` exit_criteria #17 (사전 등록된 falsification 조건) 충족. 이는 가설의 **disconfirmation** 이지 무효한 run 이 아니다.

---

## 4. 기제 추정 — tokenizer vocabulary drift 가 dominant variance source

**추정 (testable, 본 round 에서는 proven 이 아니며 차기 round 의 diagnostic target)**:

| Path | Base model | Tokenizer vocab | r5 failing pairs |
|---|---|---|---|
| p1 | Qwen/Qwen3-8B | ~151K | p1_p2 |
| p2 | unsloth/Meta-Llama-3.1-8B | ~128K | p1_p2, p2_p4 |
| p3 | mistralai/Mistral-Nemo-Base-2407 | 32K (Tekken) | p3_p4 |
| p4 | google/gemma-3-12b-pt | **262K** | p1_p2(−), p2_p4, p3_p4 |

관찰:
1. **p4 (Gemma-3 262K) 는 실패하는 3 쌍 중 3 쌍에 모두 참여** (p2_p4 신규, p3_p4 악화, p1_p4 은 passed 지만 margin 축소). 가장 큰 vocab 이 가장 많은 drift 와 공변.
2. **p2_p4 가 r4 pass → r5 fail 로 퇴행**. r4 partial corpus (118 lines) 에서는 Gemma LoRA 가 비교적 shallow 하게 훈련되었으나 r5 full corpus (1,200 lines) 에서는 더 깊이 adapted. 깊은 adaptation 이 tokenizer-dependent 표상을 **증폭**.
3. **p3_p4 (32K vs 262K) 가 가장 안정적인 최악 edge**. 두 tokenizer vocab 비율이 1:8.2 로 가장 비대칭. corpus 가 bilingual 할수록 각 tokenizer 의 고유 segmentation 차이가 hidden state 에 누적.

**왜 corpus 확장이 오히려 넓혔나 (가설)**: bilingual Hexad 고밀도 corpus 는 각 path 에게 "자신의 tokenizer 로 가장 효율적으로 표현 가능한 표상" 을 더 많이 훈련시킨다. 결과적으로 각 path 가 **자기 tokenizer 의 inductive bias 축** 으로 더 강하게 projection 되고, cross-substrate 비교 시 거리는 증가한다. LoRA step 300 은 고정이지만 effective gradient signal 이 r4 대비 ~10× (corpus 3× × 더 diverse). 즉 파라미터 값 변화 (corpus size) 만으로 가설을 되살리려는 3번째 시도는 H-DIAG3 위반.

본 가설은 **차기 round (r6) 의 (b) diagnostic target** 으로만 제안한다. proven fix 가 아니라 testable hypothesis 임을 명시.

---

## 5. POLICY R6 — 이것은 skip 이 아니라 documented refutation

| R6 기준 | 본 round 상태 |
|---|---|
| 학습이 실제 실행되었는가? | ✅ r5 학습 16 min wall, 4 path × rank 64/64/96/128 LoRA completed |
| 측정이 수행되었는가? | ✅ Recovery A pod 에서 h_last_raw 4-path 재생성, Φ gate 실행 완료 |
| 가설이 pre-registered 였는가? | ✅ `state/convergence/h100_stage2_r5_20260424.json:purpose` 에 PASS target 사전 명시 |
| falsification criterion 있었는가? | ✅ exit_criteria #17 (p3_p4 < 0.10 실패 시 재가설화 트리거) |
| 결과 문서화 되었는가? | ✅ 본 문서 + convergence JSON (CLOSED) + verdict JSON |
| 차기 round 차단 상태 확인되었는가? | ✅ AN11(a) 는 substrate-invariant 조건 미충족 하에 **open blocked**, tokenizer study 선행 조건 |

**Completeness frame 원칙 (`feedback_completeness_frame`) 에 따른 해석**: 본 round 는 weakest evidence link (“corpus 만으로 substrate gap 닫힌다”) 를 **완결적으로 falsify** 함으로써 해당 link 를 완성했다. 완성도 = PASS 만이 아니며, 반증으로 닫힌 link 도 완성된 link 이다. 다음 weakest link 가 **명확히 식별되었다** (tokenizer normalization).

---

## 6. 차기 round 제안 (.roadmap 직편 금지 — POLICY R4)

`.roadmap` 은 uchg-locked. 따라서 본 문서는 `.roadmap` 을 수정하지 않고, proposal 시스템을 통해 차기 round 를 등록한다.

**제안 ID**: `20260422-074` (신규; 최신 pending `20260422-061` 다음 가용 번호)
**Title**: "r6 pre-requisite: tokenizer vocabulary drift normalization before corpus re-expansion"
**경로**:
- `state/proposals/pending/20260422-074_r6-pre-req-tokenizer-drift-normalization.json` (카드)
- `state/proposals/refinement/20260422-074/v1.json` (refinement 래퍼)

**Rationale (카드에 기록)**:
- r4 (Option C 부분 confirm) + r5 (Option C reject) = 2 consecutive result under “expand corpus” 계열
- H-DIAG3: 동일 root 의 3번째 retry 는 새 diagnostic evidence 가 전제
- Weakest evidence link (post-r5): **tokenizer vocab 비대칭 (32K vs 262K = 8.2:1)** 이 bilingual Hexad corpus 하에서 hidden-state drift 를 증폭시킨다는 가설
- Depends-on: AN11(a) weight_emergent substrate-invariant validation 은 Φ 4-path PASS 가 전제 → tokenizer study 가 AN11(a) 의 선행 blocker
- Loss-free: 기존 r4/r5 adapter 와 corpus 폐기 없음. 도구 추가 + 측정 + 가설 정정.

---

## 7. convergence record 포인터

- `state/convergence/h100_stage2_r5_20260424.json` — `status` = CLOSED, `next_round_hypothesis` 에 tokenizer drift 언급. 본 문서가 해당 session 의 formal refutation artifact. (세션 JSON 자체는 POLICY R1 에 의해 본 commit 에서 수정하지 않는다. 별도 convergence 유지 flow 에서 handle.)
- `state/phi_4path_gate_last_verdict.json` — r5 verdict FAIL snapshot
- `state/phi_4path_cross_result_v3_TRAINED_r5.json` — 전량 spectra + null + pairs
- `state/h_last_raw_p{1..4}_TRAINED_r5.json` — Recovery A 재생성 hidden state probes

---

## 8. 결론

Option C ("Korean-balanced corpus 확장으로 substrate-invariance 달성") 는 r4 에서 부분 confirm, r5 에서 **falsified**. r14 corpus 1,200 lines 완성 자체는 독립적 가치를 가지며 (`docs/alm_r14_corpus_complete_20260424.md`), 차후 tokenizer-normalized round 의 input 자원으로 계속 유효하다. AN11(a) 는 substrate-invariant 조건이 Φ 4-path PASS 달성 시까지 **open blocked**. 차기 round 는 tokenizer drift normalization 을 선행 가설로 하는 r6 설계가 첫 action item.

---

*Generated 2026-04-25 (after r5 forward-pass completion 2026-04-24T16:21Z). 본 문서는 r5 결과의 formal refutation 기록이며, POLICY R6 의 "documented refutation = documented completion" 조항에 따라 CP1/AN11(a) 의 evidence ledger 한 link 를 완결한다.*
