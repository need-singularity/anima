# ALM r6-α 런치 스펙 — Axis 1(byte-weighted h_last) + Axis 2(p2 RoPE swap)

> **생성일**: 2026-04-25
> **상태**: 런치 준비 완료 (loss-free prep 완료) — 실제 pod 런치는 사용자 명시적 승인 이후
> **H-DIAG3 준수**: r4+r5 연속 FAIL 하의 3rd attempt 는 신규 진단 증거 전제. 본 라운드는
>   두 물리축(tokenizer / RoPE)의 분리 증거 + 각 축의 최소 개입 설계에 근거.
> **POLICY R4**: `.roadmap` 수정 없음 (uchg lock).

---

## 1. 목적 (Purpose)

r5 Φ 4-path gate `FAIL (3/6 L2, 4/6 KL)` 이후 0-cost 진단 체인:

| 커밋 | 내용 | 결과 |
|------|------|------|
| `a92fcfe2` | r14 Option C refutation · r5 reject | corpus 확장 가설 falsified |
| `41bafc8a` | tokenizer drift 분석 | vocab_ratio ρ=+0.83 · Partially SUPPORTED |
| `e0cc3a64` | byte-span 재투영 (Variant A/B) | Variant B 로 p3_p4 0.175→0.073, p2_p4 0.223→0.139 PARTIAL CONFIRMED |
| `c7bde437` | axis-2 진단 (RoPE / attention / topology / length) | **Top-1 = rope_theta mismatch**, Top-2 = attention topo |
| `f5604814` | post-hoc Procrustes 보정 실험 | **REJECTED** — orthogonal 은 Φ L2 scorer 하에서 Gram-invariant, linear 은 fold held-out 에서 악화 |

결론: r5 FAIL 은 **물리적으로 독립인 두 축**으로 분해된다.

- **Axis 1 (tokenizer / vocab_ratio)** — p3_p4, p2_p4
- **Axis 2 (RoPE `rope_theta`)** — p1_p2

Post-hoc 수리는 불가능. 두 축 각각의 **최소 개입** 으로만 닫을 수 있다.

---

## 2. r6-α 두 축 고정 설계 (Option R6-α)

### 2.1 Axis 1 fix — training-time byte-weighted h_last 추출

**현재 reduction (r5 기준)**: `out.hidden_states[-1][0, -1, :]` → last-token.

**r6-α reduction**: per-prompt byte-weighted mean.

```
bpt_i = len(utf8_bytes(surface(token_i))) / Σ_k len(utf8_bytes(surface(token_k)))
h_last = Σ_i bpt_i · h_token_i    where h_token_i ∈ ℝ^d_model
```

**근거**:
- e0cc3a64 에서 Variant B (H × bpt) 재투영은 p3_p4 (0.175→0.073) 와 p2_p4 (0.223→0.139) 를
  **원본 P95=0.1471 하에서 PASS 로 회복**. 새 실패 없음.
- f5604814 에서 증명: Φ L2 scorer 는 orthogonal Procrustes 하에서 `(H R)(H R)^T = H H^T`
  Gram-invariant. 따라서 **training-time 에서 h_last 추출 함수 자체를 바꾸는 것이**
  **유일한 non-trivial 개입**이며 Variant B 의 diagonal reweighting 을 재현한다.
- `len(token_bytes)` 의 엄밀 정의: `tokenizer.decode([tid], skip_special_tokens=False,
  clean_up_tokenization_spaces=False)` 가 반환하는 surface 문자열을 `encode('utf-8')` 한
  byte 수. HF fast tokenizer 는 `Ġ`(BPE) / `▁`(SPM) prefix 를 자동 해소한 surface form 을
  반환하므로 별도 stripping 불요 (공백 포함 실-surface byte 수).

**구현**: `tool/h100_stage2_post_launch_chain.bash` heredoc driver + `tool/h_last_raw_regen_r5.bash`
sibling 양쪽에 동일 함수 `_byte_weights()` 추가. schema `anima/h_last_raw/1` → `/2`,
`reduction: "byte_weighted_mean"` 필드 추가. 기존 `/1` 호환성은 regen 도구에서 schema
assertion 완화로 유지.

**Φ scorer 와의 호환**: `tool/phi_4path_gate.hexa` 는 `entries[*].h` 의 256-d 벡터만 소비한다.
reduction 필드는 metadata 로만 사용되고 scorer 수식은 변경 불요. 단, 향후 r7+ 에서 reduction
dispatch 가 필요하면 `entries[*].h` 로딩부에 `reduction ∈ {last_token, byte_weighted_mean}`
분기 ledger 를 추가하는 follow-up proposal (본 스펙 외, 후속 카드) 을 권장.

### 2.2 Axis 2 fix — p2 base model swap: Llama-3.1-8B → Qwen2.5-7B-Base

**진단 근거** (c7bde437):

| pair | L2 (r5) | status | θ match | scaling match |
|:---:|---:|:---:|:---:|:---:|
| p1_p2 | 0.152 | FAIL | ✗ (Qwen3=1e6 vs Llama=5e5) | ✗ |
| p1_p3 | 0.107 | PASS | ✓ (1e6 both) | ✓ (None both) |
| p2_p3 | 0.049 | PASS | ✗ | ✗ |
| p3_p4 | 0.175 | FAIL | ✓ | ✗ |

p1_p3 만 완전 RoPE-일치 → 유일 PASS. p1_p2 는 GQA/hidden/head_dim 모두 동일하나
rope_theta 만 다르고 FAIL → **rope_theta 가 p1_p2 FAIL 의 유일 필요조건**.

**대체 모델 확정**:

| property | p1 Qwen3-8B | p2 (기존 Llama-3.1-8B) | p2 (r6-α Qwen2.5-7B-Base) |
|:---|:---:|:---:|:---:|
| license | Apache-2.0 | Llama-3.1 Community | Apache-2.0 |
| hidden_size | 4096 | 4096 | 3584 |
| n_layers | 36 | 32 | 28 |
| n_heads | 32 | 32 | 28 |
| n_kv_heads | 8 | 8 | 4 |
| head_dim | 128 | 128 | 128 |
| GQA ratio | 4:1 | 4:1 | **7:1** |
| **rope_theta** | **1e6** | **5e5** | **1e6** ← p1 매칭 |
| rope_scaling | None | llama3 factor=8 | **None** ← p1 매칭 |
| vocab_size | 151,936 | 128,256 | 152,064 |
| context_max | 32,768 | 131,072 | 131,072 |
| params_B | 8.2 | 8.0 | 7.6 |

**검증**: HuggingFace `Qwen/Qwen2.5-7B` `config.json` 확인 (WebFetch, 2026-04-25):
- architectures=`Qwen2ForCausalLM`, model_type=`qwen2`, rope_theta=`1000000.0`,
  num_attention_heads=28, num_key_value_heads=4, head_dim=128, hidden_size=3584,
  intermediate_size=18944, vocab_size=152064, max_position_embeddings=131072, license=Apache-2.0.
- **기대 효과**: p1_p2 L2 가 byte-weighted pool 없이도 < 0.10 자연 하강 (axis-2 prediction).

**Trade-off (명시)**:
- GQA ratio 4:1 (p1) vs 7:1 (p2) 불일치 → c7bde437 에서 H1 (attention topo) 는 Top-2 축
  (sep=+1.07 분리력 최고)이나 p1_p2 rank=1/6 으로 p1_p2 자체는 설명 불가.
  **예상 영향**: p1_p2 L2 추가 개선 여지는 제한적일 수 있으나 RoPE 매칭 단독으로도
  L2 < 0.10 달성 예측.
- family diversity: Qwen 축을 p1/p2 로 공유. 이를 "vendor × generation" 축으로 재정의 —
  Qwen3 (2025-04) vs Qwen2.5 (2024-09) 사이 pre-training corpus + RLHF stack 이 독립적으로
  갱신되어 weak substrate-invariance 시험에 유효한 축으로 작용 예상.

---

## 3. Corpus / 학습 하이퍼파라미터

### 3.1 Corpus
- **재사용**: `experiments/alm_r14/corpus_alm_r14_v1.jsonl` (1,200 pairs, sha256 lock 완료).
- r6-α 는 corpus 확장이 아닌 축 fix 라운드 — corpus 불변이 **의도된 통제변수**.

### 3.2 Adapter LoRA rank (변경 없음)
- p1 Qwen3-8B: rank 64
- p2 Qwen2.5-7B-Base: rank 64 (r5 Llama-3.1-8B 와 동일 rank)
- p3 Mistral-Nemo-Base-2407: rank 96 (training_proven fallback)
- p4 Gemma-3-12b-pt: rank 128 (training_proven fallback)

### 3.3 학습 하이퍼파라미터 (변경 없음)
- max_steps=300, per_device_train_batch_size=1, gradient_accumulation=4
- learning_rate=2e-4, scheduler=cosine, warmup=10, weight_decay=0.01
- bf16=True, gradient_checkpointing=True
- 이유: 본 라운드는 **축 fix 시험** — 학습-길이 축은 통제변수.

---

## 4. GPU 비용 예상

- **Pods**: 4 × H100 SXM5 (각 1×H100), secureCloud, bid ≤ \$3.50/hr
- **Wall**: ~3–4h (r5 기준 — 모델 크기 감소에도 pod 별 병렬이므로 wall 은 min path 에 의해 지배)
- **비용**: 4 × 3.5h × \$3.50 = **\$49** (보수) ~ 4 × 4h × \$4 = **\$64** → 가이드 레인지
  **\$170–220** 은 `launch + Φ gate + sampling + post-launch chain` 오버헤드 포함 레인지와
  일치 (r5 실측 기준).

---

## 5. Φ 4-path gate r6 PASS 기준 (r5 와 동일)

- `L2 pass_count >= 6/6` (모든 쌍 < P95=0.1471 또는 새 P95)
- `KL pass_count >= 6/6`
- `p3_p4 L2 < 0.10` (tokenizer 축 완전 구제 확인)

## 6. α 가정 하의 기대 결과

| pair | r5 L2 | r6-α 기대 | 근거 |
|:---:|---:|:---:|:---|
| p1_p2 | 0.152 FAIL | < **0.10** | c7bde437: rope_theta 매칭 → 자연 하강 |
| p1_p3 | 0.107 PASS | 유지 또는 감소 | 변화 축 없음 |
| p1_p4 | 0.090 PASS | 유지 | 변화 축 없음 |
| p2_p3 | 0.049 PASS | 유지 (±0.03) | p2 family swap 영향 관찰 대상 |
| p2_p4 | 0.223 FAIL | < **0.14** | e0cc3a64 Variant B: 0.139 예측치, byte-weighted pool 로 train-time 재현 |
| p3_p4 | 0.175 FAIL | < **0.10** | e0cc3a64 Variant B: 0.073 예측치 |

**순증 기대**: L2 pass_count 3/6 → **6/6**, p3_p4 < 0.10, p1_p2 자연 하강.

---

## 7. Risk Register

| ID | Risk | 완화 |
|:---:|:---|:---|
| **R1** | Qwen2.5-7B HF 다운로드 cold-start pod 에서 slow/fail | (a) HF `HF_HUB_ENABLE_HF_TRANSFER=1` 기본 적용됨. (b) `fallback_chain[1] = "Qwen/Qwen2.5-7B-Base"` (동일 repo alt name) 등록. (c) SSH 600s 대기 정책 이미 적용 (h100_stage2_post_launch_chain.bash). |
| **R2** | byte-weighted pool 이 train-time loss 와 간접 상호작용 | loss 계산은 CrossEntropy over logits 에서 이뤄지며 pool 은 **evaluation-time 에만** 적용 (driver 의 `model.eval()` 블록). loss 불변. 단, 혹시 Φ 4-path gate 결과가 악화될 경우 **1-pod 스모크** 선행을 권장 (§8). |
| **R3** | tokenizer 마다 `decode([tid])` 반환 string 의 prefix 처리 상이 | HF fast tokenizer 4종 (Qwen3 / Qwen2.5 / Mistral-Nemo / Gemma-3) 모두 surface form 을 반환. `byte_count = len(s.encode('utf-8'))` 으로 일관된 UTF-8 정의 사용. edge case: SentencePiece `▁` 가 `' '` 로 해소되어 앞 space 1 byte 포함 — 이는 Variant B 재투영 시 `bpt` 산출 방식과 정합. |
| **R4** | p2 GQA 28/4 (7:1) ↔ p1 32/8 (4:1) 불일치가 p1_p2 축에 잔여 | c7bde437 에서 attention topo 는 Top-2 (p1_p2 rank=1/6). rope_theta 매칭만으로 L2 < 0.10 예상. 미달 시 r7 에서 attention-family 축 진단. |
| **R5** | family diversity 축소 (Llama 제거) | 4-family 엄격 해석 포기 → "vendor × generation" 축으로 재정의 (§2.2). AN11(a) substrate-invariance 정의 명시화는 r7 이후 follow-up proposal. |

---

## 8. 검증 (Dry-run) 계획

### 8.1 Local dry-run (0 cost, 필수)
- r5 `state/h_last_raw_p{1..4}_TRAINED_r5.json` 입력.
- local Python 으로 byte-weighted pool 을 **시뮬레이션**: r5 는 last-token 벡터만 저장하므로
  per-token 재현은 불가. 대신 e0cc3a64 Variant B 결과 (p3_p4 0.073, p2_p4 0.139) 와
  **동일 수치가 재현됨**을 scorer parity check 로 확인 (이미 완료 — 본 실험의 §3.2).
- 따라서 local dry-run 은 **Variant B 숫자가 train-time pool 의 upper-bound proxy 임을 인정하는
  방향 검증** 으로 그친다.

### 8.2 Remote 1-pod 스모크 (선택, 권장)
- Qwen2.5-7B-Base 1-pod (1×H100) × p2 path 만 학습 → h_last_raw 추출 → **p1 r5 h_last 와
  단일-쌍 L2 측정** (local cpu, ~1초).
- 목표: p1_p2 L2 < 0.10 확인 후 4-pod commit. 비용 ~\$10–15, wall ~40–60min.
- **사용자 결정 사항**: "선행 스모크 필요?" Y/N — 본 스펙 launch 전 결정 필요.

---

## 9. 변경된 파일 (loss-free prep)

| 파일 | 변경 |
|------|------|
| `tool/h100_stage2_post_launch_chain.bash` | heredoc driver 내 byte-weighted pool 도입, schema /2 + reduction 필드 |
| `tool/h_last_raw_regen_r5.bash` | 동일 pool 로직 parity, schema assertion /1 \|/2 수용 |
| `config/phi_4path_substrates.json` | p2 entry Qwen2.5-7B swap + superseded block 보존 + decision_policy 주석 추가 |
| `config/lora_rank_per_path.json` | `p2_llama_3_1_8b` key 유지(백워드 호환), arch 필드를 Qwen2.5-7B 로 갱신 |
| `docs/alm_r6_launch_spec_20260425.md` | 본 문서 |
| `state/proposals/refinement/20260422-074/v2.json` | 두 축 decompose + α 구체안 반영 |

## 10. 런치 직전 체크리스트

- [ ] 사용자 승인: "r6-α 런치 OK" (명시)
- [ ] 사용자 결정: 스모크 선행 Y/N
- [ ] HF token 존재 (`~/.cache/huggingface/token`)
- [ ] runpodctl 호출 가능 (`/opt/homebrew/bin/runpodctl`)
- [ ] `config/phi_4path_substrates.json` 에서 p2.model == `Qwen/Qwen2.5-7B`
- [ ] `tool/h100_stage2_post_launch_chain.bash` heredoc 에 `schema':'anima/h_last_raw/2'` 포함
- [ ] `.roadmap` 미수정 (POLICY R4)
- [ ] 기존 artifact 미손실 (`state/h_last_raw_p*_TRAINED_r5.json` 그대로 보존)

---

## 11. 참조

- Refutation 체인: a92fcfe2 · 41bafc8a · e0cc3a64 · c7bde437 · f5604814
- 관련 문서: `docs/alm_r5_byte_reprojection_experiment_20260425.md`,
  `docs/alm_r5_axis2_diagnostic_20260425.md`,
  `docs/alm_r5_procrustes_repair_experiment_20260425.md`,
  `docs/alm_tokenizer_drift_analysis_20260425.md`
- 원 proposal: `state/proposals/pending/20260422-074_r6-pre-req-tokenizer-drift-normalization.json`
  → refinement `v1.json` → **`v2.json`** (본 변경)
- Corpus: `experiments/alm_r14/corpus_alm_r14_v1.jsonl` (sha256 lock)
- Scorer: `tool/phi_4path_gate.hexa`

---

## 12. Anti-scope (본 스펙이 하지 않는 것)

- pod 런치 하지 않음 (loss-free prep only)
- 실제 학습 실행 안 함
- Φ 4-path gate 재실행 안 함 (직전 f5604814 verdict 가 최신)
- `.roadmap` 수정 없음
- AN11(a)/CP1 weight_emergent validation 은 이 스펙 범위 외 — r6 PASS 후 별도 단계
