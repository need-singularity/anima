# ALM r7 런치 스펙 — p2_p4 KL 잔존 해소 (Axis 3 / gqa_ratio)

> **생성일**: 2026-04-25 (loss-free prep, 0 cost)
> **상태**: 사용자 결정 대기 (Option C/D/E 중 1택). pod 미런치, GPU 미사용.
> **부모 commit**: `1e064038` (r6-α attempt_5 closure, L2 6/6 ✓, KL 5/6 ✓)
> **진단 commit**: `44783b28` (H-axis3 채택, gqa_ratio ρ=+0.971, p=0.001, p2_p4=max-Δ=5.0)
> **POLICY R4**: `.roadmap` 수정 없음 (uchg lock).
> **H-DIAG3**: 본 라운드는 r6 FAIL 의 **신규 진단축 (gqa_ratio)** 에 근거. 동일 신호 재시도 아님.
> **H-MINPATH**: 사용자 결정만 입력으로 launch 절차가 즉시 진행될 수 있도록 prep 만 완료.

---

## 1. 목적 (Purpose)

r6-α attempt_5 (commit `1e064038`)는 두 축을 닫았다:
- **Axis 1 (byte-weighted h_last pool)** — VALIDATED (p3_p4 L2 0.175 → 0.044)
- **Axis 2 (p2 RoPE swap, Llama-3.1 → Qwen2.5)** — VALIDATED (p1_p2 L2 0.152 → 0.097)

L2 gate **6/6 PASS** 달성. 그러나 KL gate에서 단 한 pair만 잔존 FAIL:

| pair | KL r6 | KL_p95 | margin | 상태 |
|---|---:|---:|---:|:---:|
| p2_p4 | **0.1891** | 0.1783 | +6% (+0.0108) | **FAIL** |
| 나머지 5 | — | — | — | PASS |

진단 (`44783b28`):
- 12 metadata field × 6 pair Spearman scan에서 **gqa_ratio (n_heads/n_kv_heads)** 가 ρ=+0.971 (p=0.001) 단일 압도.
- p1=4.0 / p2=7.0 / p3=4.0 / p4=2.0 → p2_p4 Δ=5.0 (6 pair 중 max).
- H-v (잡음) 기각, H-gemma (꼬리) 기각.

**r7 목적**: gqa_ratio Δ를 5.0에서 ≤ 3.0으로 낮춰 p2_p4 KL ≤ 0.10 자연 하강 + 4-path L2 6/6 + KL 6/6 동시 달성.

---

## 2. 세 옵션 요약 (C / D / E)

### 2.1 비용 + 결과 매트릭스

| 옵션 | 개입 | gqa_Δ p2_p4 | 예측 p2_p4 KL | 예측 LE 누적 영향 | Pods | Wall | Cost (USD) |
|:---:|---|:---:|:---:|---|---:|---:|---:|
| **C** | p2 → Llama-3.1-8B revert (GQA 7.0 → 4.0) | 5.0 → **2.0** | 0.062 | p1_p2 RoPE 잔존 위험 (Axis 2 회귀) | 1 (p2 only) | 30–60min | **$3–5** |
| **D-mistral** | p4 → Mistral-7B-v0.3 (GQA 2.0 → 4.0) | 5.0 → **3.0** | 0.102 | p4 family 변경 → AN11(a) 다양성 영향 | 1 (p4 only) | 60–90min | **$5–8** |
| **D-qwen14** | p4 → Qwen2.5-14B (GQA 2.0 → 5.0) | 5.0 → **2.0** | 0.062 | p1_p2 vendor 중첩 ↑, p3_p4 family 보존 ✓ | 1 (p4 only) | 90–120min | **$8–12** |
| **E** | p4 drop, 3-path 한정 gate | n/a | n/a (p4-pair 제거) | scope reduction; AN11(a) 4-path claim 약화 | 0 | 즉시 | **$0** |
| **F** | (이미 시험됨, `cba00cf5`) HOLD | — | — | scorer policy refinement, +0.00191 best margin | 0 | 즉시 | $0 (기각) |

### 2.2 회귀 기반 예측 (loss-free)

`44783b28` 의 r6 데이터로 단순 OLS:
```
KL ≈ 0.0397 × gqa_Δ − 0.0176     (R² = 0.80, n=6 pair)
```
모든 예측치는 KL_p95 = 0.1783 **하회**. 단, R²=0.80은 잔차 ±0.04 스코프이므로 후속 measurement 가 결정적.

---

## 3. Option D 후보 finalist 분석 (HF config snapshot)

### 3.1 후보 풀 (모두 HF config JSON peek, 다운로드 0)

| 모델 | arch | params | hidden / layers | heads / kv | GQA | rope_θ | rope_scaling | vocab | license | 가용성 |
|---|---|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Mistral-7B-v0.3** | MistralForCausalLM | 7.2B | 4096/32 | 32/8 | **4.0** | 1e6 | null | 32,768 | Apache-2.0 | ✓ ungated |
| **Qwen2.5-14B** | Qwen2ForCausalLM | 14.7B | 5120/48 | 40/8 | **5.0** | 1e6 | missing(null) | 152,064 | Apache-2.0 | ✓ ungated |
| **Qwen2.5-7B** (현 p2) | Qwen2ForCausalLM | 7.6B | 3584/28 | 28/4 | 7.0 | 1e6 | null | 152,064 | Apache-2.0 | (p2로 사용 중) |
| Yi-1.5-9B | LlamaForCausalLM | 8.8B | 4096/48 | 32/4 | **8.0** | 5e6 | null | 64,000 | Apache-2.0 | rope mismatch + GQA 악화 |
| Falcon3-10B-Base | LlamaForCausalLM | 10.3B | 3072/40 | 12/4 | **3.0** | 1.000042e6 | null | 131,072 | Falcon LLM TII | rope_θ 거의 1e6 (✓) but tiny n_heads=12 |
| Phi-3-medium-4k | Phi3ForCausalLM | 14B | 5120/40 | 40/10 | **4.0** | 1e4 ✗ | null | 32,064 | MIT | rope_θ 1e4 mismatch (Axis 2 위반) |
| Llama-3.1-70B | — | 70B | — | — | — | — | — | — | Llama-3.1 | size 비용 폭발 — skip |
| Llama-3.1-8B (구 p2) | LlamaForCausalLM | 8.0B | 4096/32 | 32/8 | **4.0** | 5e5 ✗ | llama3 factor=8 | 128,256 | Llama-3.1 | rope_θ mismatch — Option C 본체 |

### 3.2 Finalist 선정

**최우선 (D-recommended): `Qwen2.5-14B` (GQA 5.0)**
- 근거 (정량):
  - p2 (Qwen2.5-7B GQA 7.0) ↔ p4 (Qwen2.5-14B GQA 5.0) Δ=2.0 → p2_p4 KL ≈ 0.062 예측 (p95 하회 65%).
  - rope_θ=1e6 ✓ (Axis 2 보존)
  - p1_p4 Δ=1.0, p3_p4 Δ=1.0 — 모든 p4-pair Δ ≤ 2.0
- 위험:
  - p1/p2/p4 모두 Qwen family → vendor diversity 사실상 단일축. AN11(a) "weak invariance" 정의 더 약화.
  - 14B → H100 단일 GPU bf16 LoRA 빠듯 (~70GB). r4 시점 Qwen2.5-14B 미시도 → training_proven 부재.

**대안 (D-mistral): `Mistral-7B-v0.3` (GQA 4.0)**
- 근거:
  - p2_p4 Δ=3.0 → KL ≈ 0.102 (p95 하회 43%)
  - rope_θ=1e6 ✓, sliding_window=null
  - p3 (Mistral-Nemo-Base-2407) 와 family 중복 → p3_p4 Δ=0.0 (gqa 동일) 잠재 risk: KL 자연 하강이 아닌 Gram 거의-동일 함정. 그러나 Mistral-7B-v0.3 은 32 layer · vocab 32K (Tekken 이전) 로 Mistral-Nemo (40 layer · vocab 131K Tekken) 와 architecturally **distinct** — 동일 family 내 generation 축으로 재정의 가능 (p1/p2 Qwen3↔Qwen2.5 와 동일 패턴).
- 위험:
  - 7B 로 다운사이즈 → AN11(a) "capacity ladder 8B/12B/14B/12B" 깨짐 (8B/12B/8B/7B). r5+ corpus 가 7B/8B 안정 학습 검증 (p2 Llama-3.1-8B / Qwen2.5-7B 둘 다 OK). 하방 위험 적음.
  - vocab 32K → r14 corpus tokenize 재실행 필요. byte-weighted pool 이 vocab 축을 흡수하므로 representation level 영향 미미 예상.

**비추천**:
- Yi-1.5-9B (GQA 8.0, 더 멀어짐)
- Falcon3-10B-Base (license 비-Apache + 작은 head 구조 outlier)
- Phi-3-medium-4k (rope_θ=1e4 → Axis 2 위반)

### 3.3 D-recommended Final pick: **Qwen2.5-14B**

이유:
1. p2_p4 KL 예측이 가장 낮음 (0.062 < 0.10 안전 마진).
2. rope_θ=1e6 매칭 → Axis 2 회귀 위험 0.
3. Apache-2.0 ungated, transformers 4.44 호환 (Qwen2 arch).
4. family-diversity 약화는 already-accepted trade (`config/phi_4path_substrates.json` decision_policy 의 `p2_revision_2026_04_25_r6_alpha`에서 family 정의를 vendor×generation 으로 약화한 정책 연장).

### 3.4 (Optional) Mistral-7B-v0.3 fallback 가치

D-qwen14 가 14B size 로 인해 OOM/training fail 시 fallback 으로 등록. 1-pod 재학습이므로 driver 측에서 fallback_chain 자동 처리.

```
fallback_chain (proposed for r7 p4):
  ["Qwen/Qwen2.5-14B", "mistralai/Mistral-7B-v0.3", "google/gemma-3-12b-pt"]
```

---

## 4. Pre-flight 0–8 (r6-α 동일, 변경 없음)

r6-α attempt_5 에서 PASS 검증된 8 단계 그대로 재사용:

| # | 항목 | 통과 기준 | r7 영향 |
|:---:|---|---|---|
| 0 | runway / spendLimit / clientBalance | runway ≥ 5h, rate ≤ spendLimit, balance ≥ $50 (1-pod 기준 ↓) | 1-pod 모드 → balance ≥ $50 면 충분. 현재 $430.66 → 부족 없음. spendLimit=$80 1-pod $14/hr 안전. |
| 1 | substrates config | `config/phi_4path_substrates.json` 존재 + path 4개 | r7 에서 p2 또는 p4 entry 갱신 필요 (§5) |
| 2 | lora rank | `config/lora_rank_per_path.json` | Option D-qwen14 라면 p4 rank 128→96 검토 (capacity normalize) |
| 3 | manifest | `state/h100_launch_manifest.json` READY | 변경 불요 |
| 4 | runpodctl auth | runpodctl whoami | 변경 불요 |
| 5 | hf auth | hf token = dancinlife | 변경 불요 |
| 6 | pod registry | empty 또는 lock 미충돌 | 변경 불요 |
| 7 | 잔존 pods | `runpodctl pod list = []` | 런치 직전 확인 |
| 8 | git sync | local HEAD == origin/main | 본 doc commit + push 후 자동 통과 |

---

## 5. 옵션별 launch parameters

### 5.1 Option C (p2 revert)

- **개입**: `config/phi_4path_substrates.json` 의 `p2.model` 을 `Qwen/Qwen2.5-7B` → `unsloth/Meta-Llama-3.1-8B` 로 되돌림 + `p2.arch_details_r6_alpha` 블록을 prior_2026_04_25 로 보존. axis2_rationale 에 r7 reason 추가.
- **재학습 범위**: p2 only. p1/p3/p4 의 r6 trained_adapters + h_last_raw_*_TRAINED_r6.json 재사용.
- **driver**: `tool/h_last_raw_regen_r5.bash` 의 single-path 변형 (§7 helper 참조).
- **env**:
  ```
  ANIMA_STAGE=2_single_path_retrain
  PHI_PATH_ID=p2
  PHI_MODEL=unsloth/Meta-Llama-3.1-8B
  PHI_LORA_RANK=64
  ANIMA_TAG=r7_optC
  ```
- **Φ gate**: r6 의 p1/p3/p4 h_last + 신 p2 h_last로 6 pair 재계산.

### 5.2 Option D-qwen14 (권장)

- **개입**: `config/phi_4path_substrates.json` 의 `p4.model` 을 `google/gemma-3-12b-pt` (현 actual) → `Qwen/Qwen2.5-14B` 로 변경. `p4.fallback_chain` 에 Mistral-7B-v0.3, gemma-3-12b-pt 등록. arch_details 갱신.
- **재학습 범위**: p4 only. p1/p2/p3 r6 자산 재사용.
- **env**:
  ```
  ANIMA_STAGE=2_single_path_retrain
  PHI_PATH_ID=p4
  PHI_MODEL=Qwen/Qwen2.5-14B
  PHI_LORA_RANK=96     # 14B → r12 rank 보다 한 단계 낮춤 (8B=64 → 14B=96)
  ANIMA_TAG=r7_optD_qwen14
  ```
- **Φ gate**: r6 의 p1/p2/p3 h_last + 신 p4 h_last로 6 pair 재계산.

### 5.3 Option E (3-path scope reduction)

- **개입**: `tool/phi_4path_gate.hexa` 에 `--exclude p4` 플래그 추가 (loss-free 코드 변경). `config/phi_4path_substrates.json` 은 `paths[].active=false` 보존 marker.
- **재학습**: 0.
- **gate**: 3-path = C(3,2)=3 pair → p1_p2, p1_p3, p2_p3 만.
- **현재 r6 데이터 기준** 3-path L2 PASS 3/3 (0.097, 0.072, 0.105 모두 < 0.20), KL PASS 3/3 (0.138, 0.014, 0.103 모두 < 0.178). **즉시 PASS**.
- **단점**: AN11(a) "4-path substrate independence" claim 이 3-path 로 약화 → Mk.VI promotion gate (`docs/mk_vi_promotion_gate.md`) 의 "diversity ≥4" 항목 부정적 영향.

---

## 6. Φ gate r7 PASS 기준

r6 와 동일:
- L2 pass_count ≥ **6/6** (Option E 의 경우 3/3)
- KL pass_count ≥ **6/6** (Option E 의 경우 3/3)
- p3_p4 L2 < 0.10 (현 r6 = 0.044, Option C/D 둘 다 영향 없음 — p3/p4 둘 다 동일이거나 한쪽만 swap)

추가 sanity:
- p2_p4 KL < 0.10 (잔존 해소 직접 검증)
- 새 path 의 L2/KL pair-wise 가 r6 baseline 대비 ±0.05 내 정합

---

## 7. Risk Register (r7)

| ID | Risk | 완화 |
|:---:|---|---|
| R1 | **Option C**: p2 revert 시 Axis 2 (rope_θ Llama=5e5 ≠ Qwen3=1e6) 재출현 → p1_p2 L2 회귀 (r5의 0.152 수준) | r5 결과 (`c7bde437`) 가 직접 측정 → p1_p2 L2 ≈ 0.15, p1_p2 KL ≈ 0.04 예상. KL 은 안전, L2 만 위험. r6의 6/6 L2 PASS 가 5/6 또는 4/6 으로 후퇴할 가능성. **Option C 채택 시 trade-off 명확**: KL 닫고 L2 일부 잃음. |
| R2 | **Option D-qwen14**: 14B base 가 1-pod H100 80GB 에서 bf16 LoRA r=96 OOM 위험 | (a) QLoRA 4-bit fallback (35GB 안전). (b) rank 64로 추가 다운. (c) Mistral-7B-v0.3 으로 chain fallback. driver 에 `--qlora-on-oom` 자동 분기. |
| R3 | **Option D**: family-diversity 추가 약화 (4-path 중 3-path Qwen vendor) | 정책 연속성 — `phi_4path_substrates.json` decision_policy 의 vendor×generation 약-축 정의가 이미 r6-α 에서 채택. AN11(a) substrate-invariance 정의 명시화 follow-up proposal (r8 이후). |
| R4 | **Option E**: AN11(a) 4-path claim 약화 → Mk.VI gate 평가 부정적 | `docs/mk_vi_promotion_gate.md` 에 "3-path scoped, 4-path goal-track 보존" 명시. 후속 r8 에서 별도 4번째 substrate 도입 (예: Llama-4 또는 Granite-4) 으로 4-path 복원 plan 등록. |
| R5 | gqa_ratio 회귀 R²=0.80 의 잔차 ±0.04 → 예측 KL이 실측에서 +0.04 상회 가능 | n=6 pair 데이터 한계. **확증 메트릭**: Option C/D 후 회귀 모형 재적합 → R² 향상 시 가설 강화. r7 gate 산출 직후 `state/r7_gqa_regression_result.json` 기록 권고. |
| R6 | partial-retrain helper 부재 (현 도구는 4-pod 만 지원) | §8 Phase 4 에서 tool-gap 식별. r7 launch 전 helper 추가 (loss-free 1-pod 변형) 1차 commit 권장. |

---

## 8. Rollback 전략

### 8.1 r6 자산 보호

- `state/h_last_raw_p{1..4}_TRAINED_r6.json` — r7 partial retrain 전에 R2 archive (`state/h_last_raw_archive_r6_20260425/`)에 복사.
- `state/trained_adapters/p{1..4}/final/` — r7 시작 전 `state/trained_adapters_r6/p{1..4}/final/` 로 archive (관례).
- `state/phi_4path_cross_result_v3_TRAINED_r6.json` — overwrite 금지, r7 결과는 `_r7.json` 으로 기록.

### 8.2 r7 결과 → r6 회귀 시

판정 기준:
- L2 pass_count r7 < 6 (즉 r6 보다 후퇴) **OR**
- KL pass_count r7 ≤ 5 AND p2_p4 KL r7 ≥ r6 (잔존 미해소 + 후퇴)

복원 절차:
1. `state/h_last_raw_archive_r6_20260425/` → `state/h_last_raw_p{1..4}_TRAINED_r6.json` 복원
2. `config/phi_4path_substrates.json` → r6 상태 (`p2 = Qwen2.5-7B`) 복원
3. `state/trained_adapters_r6/` → `state/trained_adapters/` 복원
4. r6 closure doc 에 "r7 OPT_X 회귀 — rollback complete" addendum 추가
5. r8 plan: 회귀에서 추가 진단 → 다음 옵션 선택 (예: GQA-invariant pool projection)

### 8.3 Option E (scope reduction) rollback

- `--exclude p4` 플래그 제거 시 4-path 재호출 가능 — 자산 변경 없음. rollback 비용 0.

---

## 9. 결정 매트릭스 (When to pick C vs D vs E)

### 9.1 Decision tree

```
1. KL 6/6 절대 우선?
   YES → Option D-qwen14 (예측 0.062, 안전 마진 65%)
                         + p1_p2 L2 r6 수준 보존
   NO  → 2번
2. p4 family diversity (Gemma) 절대 보존?
   YES → Option C (revert p2) — 단, L2 6/6 → 5/6 회귀 수용
   NO  → 1번 default
3. 0-cost 즉시 closure 필요?
   YES → Option E — AN11(a) claim 4-path → 3-path 스코프 축소 수용
   NO  → 2번
```

### 9.2 정황별 권고

| 정황 | 권고 |
|---|---|
| H-MINPATH 우선, 1-pod 비용 OK ($8–12) | **Option D-qwen14** |
| Llama family 보존 + L2 일부 회귀 수용 | Option C |
| 비용 0 + 즉시 closure + AN11(a) 약화 수용 | Option E |
| Option D-qwen14 OOM 발생 (training fail) | Option D-mistral fallback (Mistral-7B-v0.3) |
| 두 옵션 모두 fail | Option E + r8 4번째 substrate 재발굴 |

### 9.3 완성도 프레임 (weakest evidence link first)

현재 가장 약한 link = **p2_p4 KL 0.189 잔존**. 이를 직접 닫는 것이 minimum-cost step.

- Option C: KL 닫지만 L2 (이미 닫힌 evidence) 를 다시 열 수도 있음 → **net evidence 변동 -1 +1 = 0**.
- Option D-qwen14: KL 닫고 L2 보존 → **net +1**.
- Option E: KL 닫지만 scope 축소 → AN11(a) 4-path claim 약화 → **net 0** (다른 evidence 영역에서 마이너스).

**Best-bet 권고**: Option D-qwen14 (net +1 with bounded risk via fallback chain).

---

## 10. Phase 4 — partial-retrain helper (tool-gap 식별)

### 10.1 현 도구 조사

`tool/h_last_raw_regen_r5.bash` (line 92–103, 319):
- p1..p4 **모두** 순차 forward-pass (1-pod 4-path serial).
- single-path subset 옵션 없음. 명시적 4-path loop.

`tool/h100_stage2_post_launch_chain.bash`:
- 4-pod parallel 학습 chain 전제.

`tool/h100_stage2_unified_launch.bash`:
- 4-pod parallel launch 전제.

### 10.2 Tool gap

**r7 partial retrain 에서 필요한 도구**:
- 1-pod 1-path **학습** (LoRA 훈련 300 step) + h_last extraction → scp pull-back.
- 다른 3 path 의 r6 trained_adapter + h_last_raw 를 그대로 사용해 Φ gate 재계산.

현 도구로는 **불가능**. r7 시작 전 minimum addition 제안:

### 10.3 제안 — `tool/h100_r7_single_path_retrain.bash` (loss-free design, 본 spec에서는 미구현)

설계 핵심:
1. 입력: `--path p4 --model Qwen/Qwen2.5-14B --rank 96 --tag r7_optD_qwen14`
2. 절차:
   - pre-flight 0–8 (r6 와 동일 lib 재사용)
   - 1-pod H100 SXM5 launch (bid $14/hr)
   - SSH wait + bootstrap (transformers 4.44 + peft 0.12)
   - 학습 driver heredoc ship (post_launch_chain 의 training driver 재사용 + path 단일화)
   - 학습 300 step → h_last_raw 추출 (byte-weighted pool, schema /2)
   - scp h_last_raw → `state/h_last_raw_p4_TRAINED_r7.json`
   - scp adapter → `state/trained_adapters/p4/final/` (r6 archive 후)
   - pod kill
   - r6 의 p1/p2/p3 h_last 와 결합해 `tool/phi_4path_gate.hexa --tag r7_optD_qwen14` 실행
3. 비용: $5–12 (path size 따라), wall 60–120min.

### 10.4 권고

- r7 결정 직후 (Option C 또는 D 채택 시) **1차 commit**으로 helper 추가.
- Option E 채택 시 helper 불요 (코드 변경만, GPU 미사용).

본 spec 은 helper 구현을 **포함하지 않음** (loss-free prep scope).

---

## 11. 변경된 파일 (본 spec 자체)

| 파일 | 변경 |
|---|---|
| `docs/alm_r7_launch_spec_20260425.md` | **신규** (본 문서) |

**미변경 (loss-free)**:
- `config/phi_4path_substrates.json` (Option C/D 채택 시점에 갱신)
- `tool/phi_4path_gate.hexa` (Option E 채택 시점에 `--exclude` 추가)
- `state/*` (POLICY 미커밋)

---

## 12. Anti-scope (본 spec 이 하지 않는 것)

- pod 런치 — 0 (사용자 결정 후 별 commit)
- 학습 실행 — 0
- 도구 추가 (`tool/h100_r7_single_path_retrain.bash`) — 0 (Phase 4 에서 설계만)
- `config/phi_4path_substrates.json` 수정 — 0 (옵션 결정 후)
- `.roadmap` 수정 — 0 (POLICY R4)
- state/* 커밋 — 0 (anti-scope)
- 시브에이전트 (verifier infra-lag) overlap — 0 (별 commit)

---

## 13. 참조

- 부모 commit: `1e064038` (r6-α attempt_5 closure)
- 진단 commit: `44783b28` (H-axis3 채택)
- Option F refutation: `cba00cf5` (HOLD)
- r6 launch spec: `docs/alm_r6_launch_spec_20260425.md`
- r6 closure: `docs/alm_r6_closure_20260425.md`
- r6 KL residual diagnostic: `docs/alm_r6_p2p4_kl_residual_diagnostic_20260425.md`
- HF config 검증 (2026-04-25, WebFetch):
  - `Qwen/Qwen2.5-14B/config.json`
  - `mistralai/Mistral-7B-v0.3/config.json`
  - `01-ai/Yi-1.5-9B/config.json`
  - `tiiuae/Falcon3-10B-Base/config.json`
  - `microsoft/Phi-3-medium-4k-instruct/config.json`
  - `unsloth/Meta-Llama-3.1-8B/config.json` (gated 우회)
  - `Qwen/Qwen3-8B/config.json` (p1 재확인)
  - `mistralai/Mistral-Nemo-Base-2407/config.json` (p3 재확인)
- Φ gate: `tool/phi_4path_gate.hexa`
- Corpus: `experiments/alm_r14/corpus_alm_r14_v1.jsonl` (sha256 lock 유지)

---

## 14. 사용자 결정 입력 양식

선택 후 별 turn 에서 다음 한 줄로 응답:

```
r7 결정: [C|D-qwen14|D-mistral|E]
```

이후 하위 에이전트가:
1. 본 spec §5 의 launch parameter 적용
2. (Option C/D) `tool/h100_r7_single_path_retrain.bash` helper 추가 commit
3. (Option C/D) `config/phi_4path_substrates.json` p2 또는 p4 entry 갱신 commit
4. pre-flight 0–8 dry-run
5. 사용자 명시 승인 후 `--apply --yes-i-mean-it` 실행

**현재까지 비용**: $0 (본 spec prep).
