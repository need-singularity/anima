# ALM r8 런치 스펙 — Option D-mistral (Axis 4 H4b 복합 고정)

> **생성일**: 2026-04-25 (loss-free prep, 0 cost)
> **상태**: 사용자 결정 대기 (D-mistral 단일 권장, 백업 E/G). pod 미런치, GPU 미사용.
> **부모 commit**:
> - `308ba540` r7 D-qwen14 closure — **FALSIFIED** (L2 6/6 → 3/6 붕괴)
> - `a05994fc` r7 Axis 4 진단 — H4b (vendor × generation) 지배 + H4a (scale) 복합
> - `1e064038` r6-α baseline (L2 6/6, KL 5/6, p2_p4 KL 잔존)
> - `2d0f9e58` r7 helper (`tool/h100_r7_single_path_retrain.bash`) — `--base-model` 파라미터화 완료
> **POLICY R4**: `.roadmap` 미수정 (uchg lock).
> **H-DIAG3**: 본 라운드는 r7 FAIL 의 **새 진단축 (Axis 4)** 지배 가설 H4b 에 근거. 동일 축 재시도 아님.
> **H-MINPATH**: 사용자 결정만 입력으로 launch 즉시 진행 가능 (helper 재사용, 신규 bash 코드 없음).
> **H-SILENT**: DONE = doc + proposal + commit.

---

## §1. 목적 (Purpose)

r7 D-qwen14 (`308ba540`)에서 p4 base model 을 `google/gemma-3-12b-pt` → `Qwen/Qwen2.5-14B` 로 교체해 Axis 3 (gqa_ratio) 을 닫으려 했으나, **L2 6/6 → 3/6** 파국 회귀가 발생했다. Axis 4 진단 (`a05994fc`) 에서 지배 원인을 **H4b (vendor × generation)** 로 식별하였고, spectrum 분석 결과 r7 p4 의 **쌍봉(bimodal) spectrum** (λ₂ ×5.11 급증) 이 다른 path 의 단봉 구조와 기하학적으로 불일치함을 확인했다.

**r8 목적**: p4 base model 을 `Qwen/Qwen2.5-14B` → **`mistralai/Mistral-7B-v0.3`** 로 단일-path 재교체하여 (a) scale proxy 매칭으로 쌍봉 → 단봉 전환, (b) gqa_ratio Δ(p2_p4) 5.0→3.0 완화로 p2_p4 KL 자연 하강, (c) r6 L2 6/6 복원 + KL 6/6 동시 달성.

**r6 baseline 보존 원칙**: r6 의 p1/p2/p3 trained_adapter + h_last 자산은 변경 없이 reuse. p4 만 단일-path 재학습 ($5–8).

---

## §2. r7 evidence → Axis 4 → D-mistral lineage

### 2.1 r7 D-qwen14 FALSIFICATION (commit `308ba540`)

| 축 | r6 | r7 | verdict |
|---|---:|---:|:---:|
| L2 pass_count | 6/6 | **3/6** | regression |
| KL pass_count | 5/6 | **3/6** | regression (단, p2_p4 KL 0.189→0.131 PASS ✓) |
| p1_p4 L2 | 0.086 | 0.339 (×3.94) | FAIL |
| p3_p4 L2 | 0.044 | 0.276 (×6.33) | FAIL |
| p2_p4 L2 | 0.144 | 0.287 (×1.99) | FAIL |

→ Axis 3 (gqa_ratio) 은 KL 에서 validated 되었으나, L2 측면은 더 강력한 다른 요인이 지배함을 드러냄.

### 2.2 Axis 4 진단 (commit `a05994fc`) 핵심

§2 Spectrum 비교에서 **r7 p4 만 쌍봉**:

- λ₁ r6=0.7192 → r7=0.5755 (감소)
- λ₂ r6=0.0627 → r7=**0.3206** (×5.11 폭증)
- top-2 mass 0.78 → 0.90 (질량 상위 2방향 집중)
- 다른 path (p1/p2/p3) 는 모두 단봉 (λ₁ dominant 0.74–0.81)

§3 서브-가설 scoring:

| 서브-가설 | 점수 | 핵심 |
|:---|:---:|:---|
| H4b vendor×gen | **3/3** | same-vendor-same-gen (p2_p4) dL2 최저 |
| H4a scale | 2/3 | Δscale=+0.288 명백, but 순서 불일치 |
| H4c rank underfit | 2/3 | rank/B=6.86 최저 통과값 이하, but spectrum 패턴 불일치 |
| H4d steps 부족 | 2/3 | top-2 mass +0.11, PR₁₆ +0.39 |
| H4e pooling | 0/3 | hidden=5120 인 p3 는 r6 통과 |

§4 통합 해석: **(H4b ∥ H4a) ⊗ (H4c ∧ H4d)** 교호. H4b 단독 dominant 이나 복합 제거 필요.

### 2.3 D-mistral falsifiable 예측

Axis 4 진단 §4.2 :
> 만약 p4 를 scale 근접 + 다른 vendor (예: Mistral-7B-v0.3, 7B class) 로 바꾸면 **쌍봉→단봉 전환**이 일어나 L2 6/6 복구 가능.

본 spec 은 이 예측을 test case 로 삼는다.

---

## §3. Mistral-7B-v0.3 config snapshot (HF verified 2026-04-25)

### 3.1 WebFetch `mistralai/Mistral-7B-v0.3/config.json`

| field | 예측 (r7 spec §3.1) | 실측 | match |
|---|---|---|:---:|
| architectures | `MistralForCausalLM` | `MistralForCausalLM` | ✓ |
| model_type | `mistral` | `mistral` | ✓ |
| hidden_size | 4096 | **4096** | ✓ |
| num_hidden_layers | 32 | **32** | ✓ |
| num_attention_heads | 32 | **32** | ✓ |
| num_key_value_heads | 8 (GQA 4.0) | **8** | ✓ |
| head_dim | 128 (= 4096/32 derived) | 128 derived (field absent) | ✓ (파생) |
| rope_theta | 1e6 | **1000000.0** | ✓ |
| vocab_size | ~32000 | **32768** | ✓ (Mistral v3 tokenizer) |
| sliding_window | null | **null** | ✓ |
| max_position_embeddings | 32768 | **32768** | ✓ |
| torch_dtype | bfloat16 | **bfloat16** | ✓ |
| license | Apache-2.0 ungated | Apache-2.0 ungated | ✓ |

### 3.2 verdict

**ALL MATCH** (12/12). r7 spec §3.1 의 예측치 전부 통과. 추가 관찰:
- `head_dim` 필드는 config.json 에 명시되지 않으나 `hidden_size / num_attention_heads = 4096/32 = 128` 로 파생 (transformers 내부 자동 계산).
- `vocab_size=32768` (Mistral v0.3 의 Tekken 이전 BPE, v0.2 의 32000 보다 768 확장).
- `sliding_window=null` → full-attention 모드. r14 corpus 의 seq_len 제약 없음.
- `max_position_embeddings=32768` → r14 corpus (typical ≤ 4096 tokens) 충분히 수용.

### 3.3 r7 spec 편차 — 없음 (no adjustment needed)

r7 launch spec `0acff23b` §3.1 에서 제시한 Mistral-7B-v0.3 finalist pool 수치와 완전 일치. r8 spec 에서 추가 조정 불요.

---

## §4. 예측 결과 (Expected outcomes)

### 4.1 Spectrum 예측 (bimodal → unimodal)

Axis 4 §5.2 추정:

| 지표 | r6 p4 (Gemma3-12B) | r7 p4 (Qwen2.5-14B) | r8 p4 (Mistral-7B-v0.3) 예측 |
|---|---:|---:|---:|
| λ₁ | 0.7192 | 0.5755 | **0.70 ± 0.05** (r6 수준 복구) |
| λ₂ | 0.0627 | **0.3206** | **0.08 ± 0.03** (단봉 복귀) |
| top-2 mass | 0.7819 | 0.8961 | **0.78 ± 0.05** |
| PR₁₆ | 1.903 | 2.298 | **1.90 ± 0.15** |

핵심 근거:
- scale proxy `log(hidden × n_layers)`:
  - p1 Qwen3-8B = 11.90
  - p2 Qwen2.5-7B = 11.52
  - p3 Mistral-Nemo-Base-2407 = 12.23
  - r7 p4 Qwen2.5-14B = 12.41 (편차 대)
  - **r8 p4 Mistral-7B-v0.3 = log(4096·32) = 11.79** (p1/p2 와 근접, p3 에도 r7 보다 가까움)
- → scale gap 거의 해소 → 쌍봉 집중 해소 예상.

### 4.2 L2 / KL pair-wise 예측

| pair | r6 L2 | r7 L2 | r8 예측 L2 | r6 KL | r7 KL | r8 예측 KL |
|:---:|---:|---:|---:|---:|---:|---:|
| p1_p2 | 0.097 | 0.097 | 0.097 (변경 없음) | 0.138 | 0.138 | 0.138 |
| p1_p3 | 0.072 | 0.072 | 0.072 (변경 없음) | 0.014 | 0.014 | 0.014 |
| p2_p3 | 0.105 | 0.105 | 0.105 (변경 없음) | 0.103 | 0.103 | 0.103 |
| p1_p4 | 0.086 | 0.339 | **0.08–0.11** | — | — | KL-p95 하회 |
| p3_p4 | 0.044 | 0.276 | **0.05–0.09** | — | — | KL-p95 하회 |
| p2_p4 | 0.144 | 0.287 | **0.12–0.16** | 0.189 | 0.131 | **0.08–0.13** |

### 4.3 종합 PASS 확률

Axis 4 진단 §5.2 ::
- **L2 6/6 PASS** 확률 ≈ **65%** (쌍봉→단봉 전환 가설 검증되면 p1_p4 / p3_p4 / p2_p4 동시 복귀)
- **KL 5/6 유지 + p2_p4 추가 PASS** 확률 ≈ **55%** (gqa_Δ 5.0→3.0 부분 완화, OLS 예측 KL ≈ 0.102)
- **L2 6/6 + KL 6/6 동시 PASS (Φ r8 CLOSURE)** 확률 ≈ **35–40%**
- **FAIL-but-progress (L2 6/6, KL 5/6)** 확률 ≈ **25%**
- **FAIL (L2 < 6/6)** 확률 ≈ **35%** (쌍봉 가설 반증 → H4a/c/d 주원인 → Option G 경로)

### 4.4 Net evidence

- r7 대비 **+2** (쌍봉 해소 + KL 부분 유지)
- r6 대비 **+1** 이상 예상 (p2_p4 KL 닫기)

---

## §5. Launch command (helper 재사용)

### 5.1 실행 명령 (사용자 승인 후)

```bash
bash tool/h100_r7_single_path_retrain.bash \
  --path p4 \
  --base-model mistralai/Mistral-7B-v0.3 \
  --lora-rank 96 \
  --max-steps 300 \
  --corpus-path /root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl \
  --tag r8_optD_mistral \
  --apply --yes-i-mean-it
```

### 5.2 파라미터 근거

| 인자 | 값 | 근거 |
|---|---|---|
| `--path` | p4 | 단일-path retrain, p1/p2/p3 r6 자산 보존 |
| `--base-model` | `mistralai/Mistral-7B-v0.3` | Axis 4 H4b 지배 해소 후보, HF verified (§3) |
| `--lora-rank` | 96 | r7 과 동일 유지 (R1 risk, 64 로 downgrade 검토) |
| `--max-steps` | 300 | r6/r7 과 동일 (capacity ladder 안정성 ≥ r6) |
| `--corpus-path` | r14 v1 jsonl | sha256 `21fcfa51…` lock (진단 `a05994fc` §7.4 invariant) |
| `--tag` | `r8_optD_mistral` | 산출물 파일 명명 규칙 (r6/r7 과 분리) |
| `--apply --yes-i-mean-it` | 명시 승인 | dry-run 이후 사용자 2단계 승인 required |

### 5.3 산출물

- `state/h_last_raw_p4_TRAINED_r8.json` — r8 p4 h_last (byte-weighted pool, schema /2)
- `state/trained_adapters_r8/p4/final/` — r8 adapter (rank 96)
- `state/h_last_raw_p{1,2,3}_TRAINED_r8.json` — r6 자산 cp (tag 동기화용)
- `state/phi_4path_cross_result_v3_TRAINED_r8.json` — Φ gate 6 pair 결과

---

## §6. Pre-flight 0–10 (r7 helper 재사용)

| # | 항목 | 통과 기준 | r8 영향 |
|:---:|---|---|---|
| 0 | runway / spendLimit | runway ≥ 5h, rate ≤ spendLimit, balance ≥ $30 | **cost cap 업데이트**: 7B 는 14B 보다 빠름 → wall 60–90min, cost $5–8 예상. spendLimit $80/hr 여유. balance ≥ $30 면 충분 (현재 ≥ $420). |
| 1 | substrates config | `config/phi_4path_substrates.json` 존재 + 4 path | p4 entry 갱신 proposal 승인 후 실제 edit (Phase 3) |
| 2 | lora rank config | `config/lora_rank_per_path.json` | p4 rank=96 기입 검증 |
| 3 | launch manifest | `state/h100_launch_manifest.json` READY | 변경 불요 |
| 4 | hf auth | hf token = dancinlife | 변경 불요 |
| 5 | HF accessibility | `mistralai/Mistral-7B-v0.3` GET 200 | **ungated Apache-2.0**, 차단 없음 예상 |
| 6 | pod registry | empty 또는 lock 미충돌 | 변경 불요 |
| 7 | live pod count | `runpodctl pod list = []` | 런치 직전 확인 |
| 8 | git sync | local HEAD == origin/main | 본 doc commit + push 후 자동 통과 |
| 9 | corpus sha256 | `21fcfa51…` lock | r14 v1 동일 |
| 10 | r6 assets present + archive | `state/h_last_raw_p{1..4}_TRAINED_r6.json` + `state/trained_adapters_r6/p{1..4}/final/` exist | **r7 에서 archive 이미 생성** (재사용) |

추가 검증 (loss-free):
- r7 산출물 (`_r7.json`) 보존 — 반증 증거로 유지.
- r8 산출물은 별 tag (`_r8.json`) 로 분리.

---

## §7. Risk Register (R1–R5)

| ID | Risk | 완화 |
|:---:|---|---|
| **R1** | rank=96 이 7B 에 대해 과도 (rank/B=13.7) → 과적합 / 학습 발산 | (a) 1차 시도 rank=96 유지 (r7 비교용 ceteris paribus). (b) 첫 에폭 loss 발산 관측 시 **rank=64 downgrade** (p1/p2 와 동급). (c) helper 의 `--lora-rank 64` flag 로 즉시 적용. **Decision rule**: 사용자가 R1 회피 선호 시 rank=64 권장. |
| **R2** | vocab=32K (BPE, Tekken 이전) vs p1/p2 (152K Qwen), p3 (131K Mistral Tekken), r6 p4 (262K Gemma) → tokenize 편차 증폭 | byte-weighted h_last pool (r6 Axis 1 fix) 이 vocab 축을 흡수. p3 (Mistral-Nemo-Base-2407, vocab 131K) 가 r6 에서 L2 6/6 통과한 전례로 **vocab 축은 pool 에서 normalize 됨**. r14 corpus tokenize 는 base model 별 재실행이므로 vocab 축 영향은 training loss 차원 (최종 h_last 단계에서 byte 정규화). |
| **R3** | Mistral-7B-v0.3 는 **Mistral family** → p3 Mistral-Nemo 와 family 중복 → family diversity −1 (AN11(a) substrate-invariance 정의 약화) | r7 spec §3.2 기 논의 — Mistral-7B-v0.3 (32 layer · vocab 32K · v3 BPE) 와 Mistral-Nemo-Base-2407 (40 layer · vocab 131K · Tekken) 는 **architecturally distinct** → "같은 family 내 generation 축" 으로 재정의 가능 (p1/p2 의 Qwen3↔Qwen2.5 와 동일 패턴). Mk.VI diversity gate 에는 family-diversity 약화 기록 남김. |
| **R4** | scale 매칭 예측이 **가정**이며, 쌍봉 지속 시 H4b 가설 약한 근거로 격하 → p4 swap only 로 closure 불가 가능 | **Fallback plan 명확**: 실패 시 즉시 Option G (`r7-bis`, Qwen2.5-14B + rank=128 / step=600) 로 H4c/d 개별 반증 경로 진입. §8 sequence. 혹은 Option E 로 $0 closure. r8 spec §4.3 의 FAIL 확률 35% 는 계산된 risk budget. |
| **R5** | **H-DIAG3 준수**: r8 FAIL 시 same-axis (Axis 4 H4b) 재시도 금지 | r8 closure doc 에 반드시 "H4b 재시도 금지, 다음 axis/hypothesis 이전" 명시. 재시도 시 해당 commit 은 policy 위반 (R4 / .roadmap uchg) 과 동급 취급. **결정 판단**: r8 FAIL → Option E (closure $0) 또는 Option G (다른 서브-가설 H4c/d 타겟). |

---

## §8. Fallback sequence

### 8.1 정책적 fallback order

```
r8 D-mistral (1순위)
   ├── PASS (L2 6/6 + KL 6/6) → Φ r8 CLOSURE → Mk.VI promotion 재심사
   ├── FAIL-but-progress (L2 6/6 + KL 5/6) → r8 closure doc + F-bis(scorer refine) 검토
   ├── FAIL (L2 < 6/6, 쌍봉 유지) → H4b 단독 반증 → Option E (3-path drop, $0) 즉시 closure
   └── FAIL (L2 < 6/6, 쌍봉 해소 but 다른 회귀) → Option G (r7-bis, Qwen2.5-14B rank128/step600, $5–8) → H4c/d 반증 시도
```

### 8.2 Option E (3-path drop, $0)

- `tool/phi_4path_gate.hexa --exclude p4` flag 추가 (loss-free 코드 변경).
- 3-path (p1/p2/p3) 에서 r6 기준 이미 L2 3/3 + KL 3/3 PASS → 즉시 closure.
- substrate-independence claim 이 4-path → 3-path 축소 (AN11(a) claim 약화, Mk.VI diversity gate 재평가 필요).

### 8.3 Option G (r7-bis)

- `Qwen/Qwen2.5-14B` 유지, rank=128 또는 192, max_steps=600.
- H4c (rank underfit) + H4d (steps 부족) 개별 반증.
- PASS 확률 ≈ 35–45% (scale gap 구조적 해소 안 됨).
- 진단적 가치 우수: 실패해도 H4a/b 가 주원인임을 확정.

### 8.4 실행 trigger

r8 closure 판정 직후 사용자 별 turn 입력:

```
r8 후속: [E|G|HOLD]
```

---

## §9. Rollback 전략

### 9.1 r6 자산 보호 (r7 과 동일 체계 유지)

- `state/h_last_raw_archive_r6_20260425/` 보존 (r7 archive 재사용).
- `state/trained_adapters_r6/p{1..4}/final/` 보존.
- `state/phi_4path_cross_result_v3_TRAINED_r6.json` overwrite 금지.
- r8 산출물은 반드시 `_r8.json` / `trained_adapters_r8/` 로 분리.

### 9.2 r8 FAIL 시 복원

판정 기준:
- L2 pass_count r8 < 6 (r6 보다 후퇴), OR
- KL pass_count r8 ≤ 4 + 다른 pair 추가 FAIL

복원 절차:
1. `state/trained_adapters_r8/` → archive 폴더 이동 (overwrite 금지).
2. `state/h_last_raw_p4_TRAINED_r8.json` → archive 유지 (반증 증거).
3. `config/phi_4path_substrates.json` p4 entry → r6 상태 (`google/gemma-3-12b-pt`) 복원.
4. Φ gate 재실행은 필요 없음 (r6 산출물 있음).
5. r8 closure doc 에 rollback 상세 기록 + Option E/G 선택 lineage 명기.

### 9.3 R2 restore 체인

`config/phi_4path_substrates.json` 의 p4 entry rollback:
```json
{
  "p4": {
    "model": "google/gemma-3-12b-pt",
    "arch_details_r6": { ... 기존 r6 값 ... },
    "fallback_chain": ["google/gemma-3-12b-pt"]
  }
}
```

또는 Option E 채택 시 `p4.active=false` marker 추가.

---

## §10. Decision matrix (when to execute vs hold)

### 10.1 Execute (r8 D-mistral launch) 조건

- runway ≥ 5h (current ≥ 5h 가정)
- balance ≥ $30 (current ≥ $420)
- spendLimit 여유 ≥ $15/hr (current $80/hr)
- Axis 4 진단 (§2.2) 에 대해 사용자 동의
- 완성도 frame: weakest evidence link = p1_p4 / p3_p4 L2 회귀 → D-mistral 이 net +2

### 10.2 Hold (D-mistral 연기) 조건

- 사용자가 family-diversity 약화 (R3) 수용 불가
- rank=96 vs rank=64 결정 보류
- 다른 세션 (CP1 / Verifier / Meta) 비용 경쟁

### 10.3 Immediate Option E ($0) 조건

- 비용 제약 엄격 ($0 필수)
- AN11(a) 4-path claim 축소 수용
- Mk.VI promotion 경로 재구축 수용

### 10.4 Immediate Option G 조건

- H4c/d 개별 반증 **진단적 가치** 우선
- D-mistral 쌍봉 해소 가설 자체를 먼저 test 할 의향 없음
- rank/step 배증 비용 ($5–8) 수용

### 10.5 권고 (완성도 frame)

**Best-bet**: **r8 D-mistral launch** (net evidence +2, 예측 CLOSURE 확률 35–40%, FAIL 시 E/G fallback 명확).

Weakest-evidence-first 원칙:
- r7 에서 열린 상처 (L2 6/6 → 3/6) 가 최우선 supply closure.
- D-mistral 이 이 상처를 직접 타겟 (쌍봉 해소 가설 검증).
- E 는 scope 축소로 우회 (상처 회피), G 는 다른 가설 (H4c/d) test (상처 원인 재분석).

---

## §11. 참조

- Axis 4 진단: `a05994fc` (`docs/alm_r7_axis4_diagnostic_20260425.md`)
- r7 D-qwen14 falsification: `308ba540` (`docs/alm_r7_optD_qwen14_closure_20260425.md`)
- r7 launch spec (Option pool 원소): `0acff23b` (`docs/alm_r7_launch_spec_20260425.md`)
- r7 helper (재사용 대상): `2d0f9e58` (`tool/h100_r7_single_path_retrain.bash`)
- r6 baseline closure: `1e064038`
- HF config 검증 (2026-04-25, WebFetch): `https://huggingface.co/mistralai/Mistral-7B-v0.3/raw/main/config.json`
- Corpus: `experiments/alm_r14/corpus_alm_r14_v1.jsonl`
  sha256 lock `21fcfa51b92f129b119d7fa42303adf7916547ef71c80c16f08e53839bf52b0b`
- Φ gate: `tool/phi_4path_gate.hexa`
- 제안 카드 (p4 swap): `state/proposals/pending/20260422-083_p4_swap_mistral_7b_v03.json`

---

## §12. Anti-scope (본 spec 이 하지 않는 것)

- pod 런치 — 0 (사용자 결정 후 별 commit)
- 학습 실행 — 0
- 신규 bash 도구 추가 — 0 (r7 helper `2d0f9e58` 재사용)
- `config/phi_4path_substrates.json` 수정 — 0 (proposal 제출만, 채택 후 별 commit)
- `.roadmap` 수정 — 0 (POLICY R4)
- state/* 커밋 — 0 (precedent 074–082: proposals/ 예외)
- Axis 3 D-qwen14 재시도 — 0 (H-DIAG3)
- Session master index 에이전트 (`a8f9ebe3`) overlap — 0

---

## §13. 사용자 결정 입력 양식

선택 후 별 turn 에서 다음 한 줄로 응답:

```
r8 결정: [D-mistral|E|G|HOLD]
```

이후 하위 에이전트:
1. (D-mistral) proposal 20260422-083 승인 → `config/phi_4path_substrates.json` p4 entry 갱신 commit.
2. (D-mistral) pre-flight 0–10 dry-run.
3. (D-mistral) 사용자 명시 승인 후 §5.1 command 실행 (`--apply --yes-i-mean-it`).
4. (E) `tool/phi_4path_gate.hexa --exclude p4` 추가 commit + 재실행.
5. (G) r7 helper `--base-model Qwen/Qwen2.5-14B --lora-rank 128 --max-steps 600 --tag r8_optG_rbis` 실행.
6. (HOLD) 본 spec + proposal 유지, 추가 분석 없음.

**현재까지 비용**: $0 (본 spec prep).
