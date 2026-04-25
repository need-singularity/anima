# ALM r7 Axis 4 진단 — Architecture-class manifold gap 검증 (2026-04-25)

> **상태**: DIAGNOSTIC CLOSED — Axis 4 가설 구조화, 지배 서브-가설 선정, r8 권장 경로 결정.
> **POLICY**: `.roadmap` 미수정 (R4). `state/*` 미커밋. 본 doc + 재현 helper만 커밋.
> **Korean** 본문, **0-cost** (로컬 numpy 없이 Python 표준라이브러리만), **loss-free**,
> **H-DIAG3** (Axis 3 retry 아닌 신규 Axis 4 진단), **H-SILENT** (DONE = artifact + exit-rc).
>
> **부모 커밋**:
> - `308ba540` r7 D-qwen14 closure — FALSIFIED
> - `1e064038` r6-α attempt_5 baseline (L2 6/6, KL 5/6)
> - `44783b28` Axis 3 (gqa_ratio) 진단
> - `e3e29631` r14 closure (직전)

---

## §1. 목적

r7 D-qwen14 라운드 (commit `308ba540`) 는 단일-path p4 swap
(`google/gemma-3-12b-pt` → `Qwen/Qwen2.5-14B`, rank=96) 로 Axis 3 gqa_ratio gap
(Δ=5.0 → Δ=2.0) 을 닫으려 했으나:

- **KL 부분 valid**: p2_p4 KL 0.189 → 0.131 PASS ✓ (Axis 3 닫힘)
- **L2 catastrophic regression**:
  - p1_p4 L2 0.086 → 0.339 (**×3.94**)
  - p3_p4 L2 0.044 → 0.276 (**×6.33**)
  - p2_p4 L2 0.144 → 0.287 (×1.99)
- 종합 **FAIL (3/6 L2, 3/6 KL)** ← r6 6/6 L2 + 5/6 KL 에서 양 축 퇴보.

r7 closure (§5-B) 가 제시한 **Axis 4 = architecture-class manifold gap** 가설을
0-cost로 5개 서브-가설 (H4a/b/c/d/e) 로 분해하여 검증하고, 지배 원인을 선정한다.
이어서 r8 옵션 (C / D-mistral / E / G) 을 재평가하여 최소-비용 최대-evidence
경로를 도출한다.

---

## §2. r6 vs r7 spectrum 비교 (Phase 1)

입력: `state/phi_4path_cross_result_v3_TRAINED_r{6,7}.json` 의 `spectra`
(top-16 eigvals of Gram), `participation_ratio` dict.

### 2.1 Spectrum 요약 — p4 만 변화 (p1/p2/p3는 r6 자산 재사용)

| path | λ₁ r6 | λ₁ r7 | λ₂ r6 | λ₂ r7 | top-2 mass r6 | top-2 mass r7 | PR₁₆ r6 | PR₁₆ r7 |
|:---:|---:|---:|---:|---:|---:|---:|---:|---:|
| p1 Qwen3-8B | 0.8010 | 0.8010 | 0.0673 | 0.0673 | 0.8682 | 0.8682 | 1.544 | 1.544 |
| p2 Qwen2.5-7B | 0.8112 | 0.8112 | 0.1586 | 0.1586 | 0.9698 | 0.9698 | 1.463 | 1.463 |
| p3 Mistral-Nemo | 0.7376 | 0.7376 | 0.0984 | 0.0984 | 0.8360 | 0.8360 | 1.796 | 1.796 |
| **p4** (r6 Gemma3-12B → r7 Qwen2.5-14B) | **0.7192** | **0.5755** | **0.0627** | **0.3206** | **0.7819** | **0.8961** | **1.903** | **2.298** |

### 2.2 핵심 관찰 — r7 p4 는 "쌍봉(bimodal) spectrum"

- λ₁ 감소 (0.72 → 0.58) 하면서 λ₂ 폭증 (0.063 → **0.321**, **×5.11**)
- top-2 질량은 오히려 **상승** (0.78 → 0.90)
- PR₁₆ 도 상승 (1.90 → 2.30) — 즉 "effective rank는 늘어남"
- **그러나** λ₃..λ₁₆ 꼬리는 모두 감소 (r6 p4 0.032 → r7 p4 0.026)

→ 이는 **"2D subspace 붕괴"가 아니라 "상위 2개 방향에 질량 집중 + 꼬리 말림"**의
**쌍봉 분포** 패턴. 다른 path (p1/p2/p3) 의 spectrum은 λ₁ 단독 dominant (0.74–0.81)
인 **단봉(unimodal)** 구조이므로, **쌍별 L2 / KL 계산 시 p4 의 λ₂ 에너지가 어느
partner와도 정렬되지 않아** 거리가 급증한다.

**이것이 "3개 path 동시 폭증"을 single-path 교체로 설명하는 기본 기전이다.**

---

## §3. 서브-가설 테스트 (Phase 2)

아래 점수는 0-cost 증거 기반 0–3 정성 정량화 (state artifact
`r7_axis4_diagnostic_result_20260425.json` 에 전체 수치 보존).

### 3.1 H4a — Scale (hidden × layers)

**Metric**: `log(hidden × n_layers)` proxy.

| pair | partner scale | p4 scale r6 | p4 scale r7 | |Δscale gap r6→r7| | dL2 r6→r7 |
|:---:|---:|---:|---:|---:|---:|
| p1_p4 | 11.901 | 12.124 | 12.412 | **+0.288** | **+0.253** |
| p2_p4 | 11.516 | 12.124 | 12.412 | **+0.288** | +0.143 |
| p3_p4 | 12.230 | 12.124 | 12.412 | **+0.077** | **+0.232** |

**Spearman(|d_gap|, dL2) = −0.5** (n=3, 정보량 낮음). p3_p4 는 scale gap 변화가
가장 작음에도 dL2 두 번째로 큼 → **scale-only 는 monotonic 설명 불가**.

**Verdict**: H4a 부분 기여, **단독 원인 아님**. 점수 **2/3**
(scale 증가는 분명히 있으나 정렬 순서가 dL2와 안 맞음).

### 3.2 H4b — Vendor × Generation

**Metric**: (same_vendor, same_generation) ↔ dL2.

| pair | partner | same vendor | same gen | dL2 |
|:---:|:---|:---:|:---:|---:|
| p1_p4 | Qwen3-8B | ✓ | ✗ (qwen3 vs qwen2.5) | **+0.253** |
| p2_p4 | Qwen2.5-7B | ✓ | ✓ | +0.143 |
| p3_p4 | Mistral-Nemo | ✗ | ✗ | **+0.232** |

**Verdict**: same-vendor-same-gen (p2_p4) 가 dL2 최저. **"같은 family·세대는 L2
를 부분 보호한다"** 검증 PASS — 그러나 p1_p4 (same-vendor cross-gen)가 p3_p4
(cross-family) 보다 더 악화 → **vendor 공유만으론 세대 mismatch 리스크를 못 덮음**.
점수 **3/3** (검증 PASS) 이되 해석은 미묘: 원인이 vendor 공유 자체보다
**tokenizer / fine-tuning-recipe 공유에 의한 representation anchor 공유**일
가능성.

### 3.3 H4c — LoRA rank / param-size underfit

**Metric**: `rank / nominal_B` (per-path).

| round | path | model | rank | B | rank/B | 통과? |
|:---:|:---:|:---|---:|---:|---:|:---:|
| r6 | p1 | Qwen3-8B | 64 | 8 | 8.00 | ✓ |
| r6 | p2 | Qwen2.5-7B | 64 | 7 | 9.14 | ✓ |
| r6 | p3 | Mistral-Nemo | 96 | 12 | 8.00 | ✓ |
| r6 | p4 | Gemma3-12B | 128 | 12 | **10.67** | ✓ |
| **r7** | **p4** | **Qwen2.5-14B** | **96** | **14** | **6.86** | **✗** |

r7 p4 의 rank/B = 6.86 은 **r6에서 통과한 최저값 (8.00) 아래**.
**단, underfit 단독 가설의 반증**: underfit이면 λ₁ dominance가 유지되고 꼬리가
두꺼워져야 하는데, 실제는 λ₂ 가 폭증하는 **쌍봉** 구조로 질적으로 다른 패턴.
점수 **2/3** (수치적 risk 있으나 spectrum 패턴과 불일치).

### 3.4 H4d — Training steps 부족

**Metric (proxy)**: spectrum top-2 mass 변화, direct Frobenius 부재.

- r6 p4 top-2 mass = 0.7819 (잘 퍼진 spectrum, PR₁₆=1.90)
- r7 p4 top-2 mass = 0.8961 (+0.114)

해석: 300 step이 14B에는 부족하여 **전체 rank spread 미달성**. 그러나 PR₁₆가
**오히려 증가** (1.90 → 2.30) 하므로 "단순 미학습" 은 아니며, **특정 2개 방향에
조기 포화 + 나머지 방향 미학습**의 부분 관찰.

**0-cost 한계**: adapter Frobenius (AN11(a)) 직접 측정 필요 — **NEEDS-GPU-IF-RESOLVE**
표시. 점수 **2/3**.

### 3.5 H4e — byte_weighted_mean pooling 붕괴

**Metric**: 동일 hidden 폭을 가진 path 존재성 검증.

- r7 p4 hidden = 5120, r6 p3 (Mistral-Nemo) hidden = **5120** 이며 r6에서
  6/6 L2 + 5/6 KL 전 통과.
- 따라서 **hidden=5120 자체**가 byte-weighted pool을 깨뜨린다고 보기 어려움.
- 잔존 의심: Qwen2.5-14B tokenizer 의 byte-per-token variance 가 다를 가능성
  (직접 비교 NEEDS-GPU). 현재 증거 약함.

점수 **0/3**.

---

## §4. Axis 4 지배 서브-가설 verdict

| 서브-가설 | 점수 | 핵심 증거 |
|:---|:---:|:---|
| **H4b vendor×gen** | **3** | same-vendor+same-gen (p2_p4) dL2 최저. 그러나 vendor-only (p1_p4) 보호 실패 |
| H4a scale | 2 | p4 Δscale=+0.288 명백하나 Spearman=−0.5로 순서 불일치 |
| H4c rank underfit | 2 | rank/B=6.86 (최저 통과값 이하) 이지만 spectrum 패턴은 "쌍봉"으로 underfit과 불일치 |
| H4d steps 부족 | 2 | top-2 mass +0.11, PR₁₆ +0.39 → 특정 방향 조기 포화 + 나머지 미학습 |
| H4e pooling | 0 | hidden=5120 인 p3가 r6 통과 → 원인 부족 |

### 4.1 통합 해석 — "vendor × generation + scale 복합 + 학습 capacity 제한"

단독 dominant 로 H4b 를 선정하지만, **점수만의 결정이 아니라** §2 의 쌍봉
spectrum 관찰과 종합 시 다음 **복합 모형**이 가장 설명력 높음:

> **R7의 Qwen2.5-14B 는 (i) 다른 3 path 와 vendor/generation 공유가 부분적이어서
> representation anchor 가 어긋나고, (ii) scale gap 이 커서 상위 두 방향
> (λ₁, λ₂) 에 에너지가 집중된 쌍봉 구조로 학습 포화하여, (iii) 단봉 구조의
> p1/p2/p3 와의 쌍별 L2 가 기하학적으로 증가한다. 이를 rank=96 / 300 step
> (r7 capacity) 로 극복하지 못한다.**

즉 Axis 4 는 하나의 축이 아니라 **(H4b ∥ H4a) ⊗ (H4c ∧ H4d) 의 교호 효과**.
단일 요인 수정으로는 closure 어려움.

### 4.2 Falsifiable 핵심 예측

- 만약 p4 를 **scale 근접 + 다른 vendor** (예: Mistral-7B-v0.3, 7B class) 로
  바꾸면 **쌍봉→단봉 전환**이 일어나 L2 6/6 복구 가능.
- 만약 p4 를 **Qwen2.5-14B 유지 + rank·step 배증** (G 경로) 해도 쌍봉이 유지되면
  L2 악화 지속 — H4c/d 가 주원인이 아니라는 방증.

---

## §5. r8 옵션 재평가

### 5.1 Option C — p2 Qwen2.5-7B → Llama-3.1-8B 환원

- **Axis 2 (rope_theta) 재발**: Qwen θ=1e6 vs Llama θ=5e5. r5 진단에서 H2 dominant 였던 축.
- **Axis 4 완화 효과**: 거의 없음 — p4 (Qwen2.5-14B) 문제는 그대로.
- **예측**: p1_p2 L2/KL 재회귀, p4 pair들 변화 미미. 4/6 ~ 5/6 수준.
- **Net evidence**: −1. **비추천**.

### 5.2 Option D-mistral — p4 Qwen2.5-14B → Mistral-7B-v0.3

설정: hidden=4096, n_layers=32, heads=32, kv=8, GQA=4.0, θ=1e6.

- **Axis 2 rope**: 모든 path θ=1e6 동급 유지. Risk 낮음.
- **Axis 3 gqa_ratio**: Δ(p2 7.0, p4 4.0) = 3.0 — r6 Δ=5.0 대비 40% 완화.
  p2_p4 KL 개선 기대 (0.19 → 0.10~0.14 예상).
- **Axis 4 scale**: p4 scale proxy = log(4096·32) = 11.79, p1 = 11.90, p2 = 11.52,
  p3 = 12.23 → **p1/p2와 근접**, p3 와도 r6보다 가까움. **쌍봉 붕괴 예상**.
- **Axis 4 vendor/gen**: 모든 pair cross-family 이지만 scale 매칭으로 보상.
  p3_p4 는 같은 "Mistral family" (다른 세대: Nemo 12B vs v0.3 7B) 로 부분 anchor 공유.
- **예측**: L2 6/6 PASS 확률 ~65%, KL 5/6 유지 + p2_p4 PASS 가능성 ~55%.
- **Net evidence**: **+2**. **1순위 권장**.

### 5.3 Option E — 3-path drop (p4 제거)

- **비용**: $0 즉시 PASS.
- **희생**: substrate-independence claim 이 "4-path cross-family" 에서
  "3-path (Qwen3 / Qwen2.5 / Mistral-Nemo)" 로 축소. Qwen 2개 포함으로
  vendor-independence 주장 약화.
- **Net evidence**: 0 (safe fallback). **D-mistral FAIL시 백업**.

### 5.4 Option G (NEW) — r7-bis (Qwen2.5-14B 유지, rank+step 증가)

- 설정: Qwen2.5-14B rank=128 또는 192, max_steps=600, 기타 동일. 단일-path, $5-8.
- **Target**: H4c + H4d 동시 반증.
- **예측 outcome**: top-2 mass 가 0.78 대 미만으로 복귀하면 spectrum 정상화 →
  L2 회귀 완화. 만약 그래도 쌍봉 유지면 H4a+H4b 가 주원인으로 확정
  (강한 diagnostic 가치).
- **PASS 확률**: ~35-45% (scale gap 구조적 해소 안 됨).
- **Net evidence**: +1 (진단 가치 우수하나 closure 확률 낮음). **2순위**.

### 5.5 Option F-bis — scorer policy refinement

- HOLD 상태 유지. Evidence axis 가 아닌 accounting 축이므로 Axis 4 에 무관.

### 5.6 옵션 요약

| 옵션 | 비용 | L2 6/6 확률 | KL closure 확률 | net evidence | 우선순위 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **D-mistral** | $5–8 | ~65% | ~55% | **+2** | **1** |
| G (r7-bis) | $5–8 | ~35% | ~40% | +1 | 2 |
| E (3-path drop) | $0 | 100% (축소) | 80% | 0 | 3 (백업) |
| C (p2 Llama) | $5–8 | ~40% | ~45% | −1 | 4 |

---

## §6. 권장 r8 최소 경로

### 6.1 권장: **D-mistral 단일-path retrain**

- **swap**: p4 `Qwen/Qwen2.5-14B` → `mistralai/Mistral-7B-v0.3`
- **rank**: 96 유지 (rank/B = 96/7 = 13.7 → 충분)
- **steps**: 300 유지
- **예상 비용**: $5-8 (r7과 동급, 오히려 7B라 더 빠를 가능성)
- **예상 outcome**:
  - L2 6/6 PASS (특히 p1_p4 / p3_p4 쌍봉 해소로 회귀 반전)
  - p2_p4 KL 0.10~0.14 (PASS 가능성 55%)
  - 전체 verdict PASS or FAIL-but-progress (1 pair KL)

### 6.2 D-mistral FAIL 시 대응 순서

1. **Option E (3-path drop)**: $0 즉시 closure, p4 제거.
2. **Option G (r7-bis)**: 추가 $5-8, Qwen2.5-14B rank/step 증가로
   H4c/d 개별 반증 확인.

### 6.3 r8 설계 주의사항 (실행 아님, anti-scope 준수)

- **r8 launch 는 사용자 결정 사항** — 본 doc은 설계 권고만 제공.
- helper (`tool/h100_r7_single_path_retrain.bash`) 재사용 가능
  (`--base-model mistralai/Mistral-7B-v0.3` 로 파라미터만 변경).
- pre-flight 10 체크 (HF access, corpus sha256 등) r7 과 동일.
- state archive: r6/r7 자산 유지 + r8 별도 tag (`r8_optD_mistral`).

---

## §7. 재현 가이드

### 7.1 입력 artifact

- `state/phi_4path_cross_result_v3_TRAINED_r6.json` — r6 spectrum + gate
- `state/phi_4path_cross_result_v3_TRAINED_r7.json` — r7 spectrum + gate
- `state/h_last_raw_p{1..4}_TRAINED_r{6,7}.json` — path별 base_model ground-truth

### 7.2 Python helper (0-cost, stdlib only)

스크립트 위치: `/tmp/r7_axis4_diag.py` (세션 로컬, 비커밋).
주요 단계:

1. 두 라운드 result JSON 로드.
2. 각 path `spectra` 에서 λ₁/λ₂/top-2 mass / PR₁₆ / entropy-eff-rank /
   log-decay 계산.
3. pair별 dL2 / dKL 산출.
4. H4a (scale proxy), H4b (vendor/gen), H4c (rank/B), H4d (top-2 mass
   변화), H4e (hidden 공유 path 검증) 각 서브-가설 수치화.
5. 종합 score → dominant 선정.
6. r8 옵션 matrix 작성.
7. `state/r7_axis4_diagnostic_result_20260425.json` (미커밋) 출력.

재현:

```bash
python3 /tmp/r7_axis4_diag.py
# WROTE state/r7_axis4_diagnostic_result_20260425.json
```

### 7.3 주의 — result JSON 의 `models` block stale label

`phi_4path_cross_result_v3_TRAINED_r{6,7}.json` 의 `models` 블록은 r5 시절
레이블이 일부 잔존하여 (r6 p2 가 Llama-3.1-8B 로, r7 p4 가 gemma-3-12b-pt 로
표기) ground-truth 와 불일치. 정확한 base_model 식별은 반드시
`state/h_last_raw_p{1..4}_TRAINED_r{6,7}.json` 의 `base_model` 필드 사용.

실제 r6/r7 모델 구성:

| path | r6 model | r7 model |
|:---:|:---|:---|
| p1 | Qwen/Qwen3-8B | Qwen/Qwen3-8B |
| p2 | Qwen/Qwen2.5-7B | Qwen/Qwen2.5-7B |
| p3 | mistralai/Mistral-Nemo-Base-2407 | mistralai/Mistral-Nemo-Base-2407 |
| p4 | google/gemma-3-12b-pt (rank 128) | Qwen/Qwen2.5-14B (rank 96) |

### 7.4 invariant

- r14 corpus sha256: `21fcfa51b92f129b119d7fa42303adf7916547ef71c80c16f08e53839bf52b0b`
- byte-weighted h_last pool (r6 Axis 1 fix)
- 16 prompt × 256 hidden-dim truncation

---

## §8. Anti-scope

- r8 launch 없음 (설계만).
- r6/r7 h_last / adapter 파일 수정 없음.
- Axis 3 D-qwen14 변형 재시도 없음.
- `.roadmap` 미수정 (POLICY R4).
- `state/*` 미커밋 (진단 결과 JSON 은 세션 로컬).
- 새 pod / GPU / API 호출 없음.

---

## §9. 진단 갱신 로그

| ts (UTC) | 내용 |
|---|---|
| 2026-04-25 | Phase 1 spectrum 비교: r7 p4 쌍봉 구조 식별 (λ₂ ×5.11) |
| 2026-04-25 | Phase 2 H4a~e 서브-가설 수치화, dominant=H4b (복합 해석 §4.1) |
| 2026-04-25 | Phase 3 r8 옵션 matrix (D-mistral 1순위, G 2순위) |
| 2026-04-25 | doc commit (본 라인) + state JSON 출력 (미커밋) |
