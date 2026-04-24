# ALM r6 Option F 0-cost KL 방어 — **HOLD (최소 margin=+0.00191)**

> **시행일**: 2026-04-25
> **부모 commit (r6 closure)**: `1e064038` — Φ 4-path gate r6, L2 6/6 PASS, KL 5/6 PASS
> **진단 commit**: `44783b28` — H-axis3 (gqa_ratio ρ=+0.971) 채택
> **최종 판정**: **HOLD** — 4개 0-cost 시나리오 모두 PASS 실패. best margin = +0.00191 KL (d_combined).
> **비용**: $0 (CPU, no pod, no API, no retrain). 검증 완료.

---

## 1. 목적

r6-α attempt_5 (commit `1e064038`)는 L2 6/6 PASS 달성했으나 KL gate에서 `p2_p4` 한 pair만 6% margin으로 잔존 FAIL한다 (real KL=0.18908 vs null p95=0.17827, Δ=+0.01082). 직전 진단 (commit `44783b28`, doc `alm_r6_p2p4_kl_residual_diagnostic_20260425.md`)은 **H-axis3 = gqa_ratio** 를 원인으로 지목했다: p2 Qwen2.5-7B GQA=7.0 vs p4 Gemma-3-12B GQA=2.0, Δ=5.0 (6 pair 중 최대). Axis 2 (RoPE) 수정이 부작용으로 GQA 격차를 넓혔다 (Llama 4.0 → Qwen 7.0).

본 라운드는 **r7 GPU retrain 전에** 0-cost scoring-side 방어가 통하는지를 확인한다:

1. **Null n=40000 재게이트** — 현재 bootstrap n=10000. 4× 확장이 tail estimate를 미세 상향시켜 p95 ≥ 0.189로 갈 가능성.
2. **상위 1 outlier prompt winsorize** — p2_p4 KL 잔존이 단일 prompt에 의해 좌우된다면, 해당 row를 상한(2nd highest)으로 치환.

**어느 하나라도 PASS** 하면 `tool/phi_4path_gate.hexa` scorer policy 변경으로 r6+ 전환 가능 (no retrain). 모두 실패 시 → r7 hard path 권고.

---

## 2. 방법

### 2.1 입력

- `state/h_last_raw_p{1..4}_TRAINED_r6.json` (schema /2, reduction=`byte_weighted_mean`, 16 prompts × 256-d)
- `state/phi_4path_cross_result_v3_TRAINED_r6.json` (r6 gate 결과)
- `state/r6_p2p4_kl_residual_result_20260425.json` (per-prompt LOO contribution)
- `tool/phi_4path_gate.hexa` (Gram top-16 eigvalsh + col-perm null 알고리즘 재현)

### 2.2 4개 시나리오

| 시나리오 | n_null | winsorize | seed | 의미 |
|:---|---:|---:|---:|---|
| **(a)** baseline | 10000 | 0 | 42 | r6 게이트 그대로 (검증) |
| **(b)** null n=40000 | 40000 | 0 | 42 | tail 추정 정밀화만 |
| **(c)** winsorize k=1 | 10000 | 1 | 42 | top-1 contrib row 치환 |
| **(d)** combined | 40000 | 1 | 42 | 둘 다 적용 |

Winsorize 절차 (k=1, global):
1. 각 prompt m에 대해 leave-one-out: `Hs[p2][mask_m], Hs[p4][mask_m]` → 재 spectrum → `contrib_m = KL_full − KL_loo`.
2. `|contrib|` 내림차순 정렬 → top_idx (최대), replacement_idx (2nd 최대).
3. `Hs[p2][top_idx] := Hs[p2][replacement_idx]`, `Hs[p4][top_idx] := Hs[p4][replacement_idx]`.
4. 수정된 matrix로 **모든 6 pair** 재계산 (winsorize의 side-effect 측정 목적).

이 winsorize는 scorer-local 연산이며 h_last raw 파일은 건드리지 않는다.

### 2.3 통과 기준

- `L2_pass_all AND KL_pass_all` (6/6 + 6/6)
- p2_p4 KL 외 다른 pair가 부작용으로 FAIL 전환되면 불허.

---

## 3. 결과

### 3.1 4-시나리오 표

| 시나리오 | n_null | wins_k | KL_p95 | p2_p4 KL | margin | L2 pass | KL pass | verdict |
|:---|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| (a) baseline | 10000 | 0 | 0.178266 | 0.189082 | **+0.010816** | 6/6 | 5/6 | FAIL |
| (b) null 40000 | 40000 | 0 | 0.178364 | 0.189082 | +0.010718 | 6/6 | 5/6 | FAIL |
| (c) winsorize k=1 | 10000 | 1 | 0.178266 | 0.180275 | +0.002009 | 6/6 | **4/6** | FAIL |
| (d) combined | 40000 | 1 | 0.178364 | 0.180275 | **+0.001911** | 6/6 | **4/6** | FAIL |

### 3.2 시나리오 (b) — null n=40000

- KL_p95 변화: 0.178266 → 0.178364, Δ = **+0.0001** (H-v 진단의 std(KL_p95)=0.00034와 정합).
- margin 0.011 → 0.0107 — 0.6% 개선에 불과. n=40000도 sampling variance 수렴 한계를 우회하지 못함.
- **결론**: null 확장 단독으로는 PASS 불가.

### 3.3 시나리오 (c) — 전역 winsorize k=1

**Top-1 outlier 식별**:
- `top_idx=9` ("재귀처리는"), abs_contrib = 0.02266
- `replacement_idx=6` ("의식의 기질은"), abs_contrib = 0.01672

**6 pair에 대한 치환 후 KL** (n=10000 p95=0.17827 기준):

| pair | full KL | wins KL | Δ | KL@10k pass |
|:---|---:|---:|---:|:---:|
| p1_p2 | 0.13761 | **0.20525** | +0.0676 | **FAIL** |
| p1_p3 | 0.01349 | 0.01349 | 0 | PASS |
| p1_p4 | 0.02623 | 0.09639 | +0.0702 | PASS |
| p2_p3 | 0.10332 | 0.10477 | +0.0014 | PASS |
| p2_p4 | 0.18908 | 0.18028 | −0.0088 | **FAIL** (0.18028 > 0.17827) |
| p3_p4 | 0.02049 | 0.07399 | +0.0535 | PASS |

**핵심 부작용**: `top_idx=9` row를 치환하면 p2, p4 둘 다의 row가 바뀌므로 **p1_p2 KL이 0.138 → 0.205로 악화** (p1_p2 pair는 p2만 영향 받지만 반영된 spectrum 변화가 크게 나타남). 또한 p2_p4 자신도 0.180으로 여전히 p95=0.178 초과.

- **결론**: 전역 winsorize는 한 pair를 고치는 대가로 다른 pair를 깨뜨린다. p2_p4조차 완전 해결 못함.

### 3.4 시나리오 (d) — 결합

시나리오 (c)의 winsorize 값 0.180275가 시나리오 (b)의 새 KL_p95 = 0.178364와 비교 — 여전히 **+0.00191 초과**. 4/6 KL (c와 동일).

### 3.5 추가 탐색 (참조용)

메인 실험 외 두 변형을 빠르게 점검했다 (state JSON 외 기록):

| 변형 | p2_p4 KL | 부작용 | 6-pair verdict |
|:---|---:|---|:---:|
| **Pair-local winsorize k=1** (p2_p4에만 적용, 다른 pair 불변) | 0.18028 | 없음 | 5/6 KL (p2_p4 여전히 FAIL) |
| **Global winsorize k=2** (top-2 치환) | **0.16544** | p1_p2 = 0.281 (악화) | 5/6 KL |

Pair-local winsorize는 scorer의 의미를 "pair마다 다른 row set"으로 바꾸게 되어 gate의 single 6-null 풀 정의와 호환되지 않는다. Global k=2는 p2_p4 PASS를 달성하지만 p1_p2 손상이 더 크다. **양쪽 다 PASS 불가**.

---

## 4. 판정

**HOLD**: 4개 0-cost 시나리오(및 2개 추가 변형) 모두 6/6 + 6/6 달성 실패.

| 지표 | 값 |
|---|---|
| 최소 margin (p2_p4 KL − p95) | **+0.001911** (시나리오 d) |
| 최다 PASS KL | 5/6 (시나리오 a, b — r6 그대로) |
| 최종 시나리오 best | d_combined (margin 기준) / a_baseline (6 pair 무부작용 기준) |

**적용할 scorer policy 변경: 없음**. `tool/phi_4path_gate.hexa` 미수정.

---

## 5. Scorer policy 권고

**채택하지 않음**. 이유:

1. **null n=40000 단독**: p95 이동이 sampling variance std(±0.00034) 수준으로 실효가 없다. 추가 compute만 유발.
2. **winsorize k=1 global**: p2_p4를 고치지도 못하면서 (0.180 여전히 FAIL) p1_p2를 깨뜨린다. 정의상 scorer 의미가 바뀌어 r2–r5 재스코어링이 필요해진다 (H-DIAG3 근거 파괴).
3. **winsorize k=1 pair-local**: scorer 정의 변경이 필요하며, 여전히 p2_p4 FAIL.
4. **k≥2 global**: 부작용 pair 수가 늘어날 뿐.

→ scorer는 현 r5+ 구현(col-perm null n=10000, winsorize 없음) 유지. 문제는 **score 정책이 아니라 학습 데이터/축**에 있으며, 이는 H-axis3 진단이 이미 확정한 바다.

---

## 6. 재현성

```
# 4-scenario 실행 (CPU only, 약 90초)
python3 /tmp/r6_option_F.py
# outputs:
#   state/r6_option_F_result_20260425.json
```

추가 변형 탐색:

```
python3 /tmp/r6_option_F_extra.py
# Pair-local winsorize + k=2 global 결과를 stdout로 출력.
```

의존성:
- `numpy`
- `state/h_last_raw_p{1..4}_TRAINED_r6.json` (read-only, 미수정)

재현 파일은 `/tmp/`에 생성 (repo 외부, `.gitignore` 무관).

---

## 7. 다음 단계 — r7 hard path 권고

0-cost 방어 실패 → Axis 3 (gqa_ratio) 제어는 **GPU retrain이 불가피**. r7 후보:

- **Option C**: p2를 GQA=4 모델로 재선택 (예: `Llama-3.1-8B` 원복 but Qwen3-8B와 중복 → 다른 GQA=4 모델 탐색).
- **Option D**: p4 (Gemma-3-12B) 교체 — GQA=2가 4-path 중 유일 outlier.
- **Option E**: 4 path를 GQA=4 (또는 인접) 모델 집합으로 재편.

진행 전 pod spendLimit/auto-kill enforcement 필요 (r6-α attempt_4 재발 방지, MEMORY.md H100 gate 가드레일 준수).

**본 에이전트는 pod를 발사하지 않는다**. 결정 권한은 사용자에게 있다.

---

## 8. 산출물 색인

- 본 문서: `docs/alm_r6_option_F_0cost_KL_defense_20260425.md`
- raw 숫자 (state/*, not committed): `state/r6_option_F_result_20260425.json`
- 재현 스크립트 (/tmp/*, not committed): `/tmp/r6_option_F.py`, `/tmp/r6_option_F_extra.py`
- 부모 closure: `docs/alm_r6_closure_20260425.md` (r6 1e064038)
- 잔존 진단: `docs/alm_r6_p2p4_kl_residual_diagnostic_20260425.md` (44783b28)
- Scorer: `tool/phi_4path_gate.hexa` (미수정)

**scorer 미변경 → refined 결과 파일 생성하지 않음**: `state/phi_4path_cross_result_v3_TRAINED_r6_refinedscorer.json` **생성 안 함**. `state/phi_4path_gate_last_verdict.json` 미갱신 (r6 FAIL verdict 유지).
