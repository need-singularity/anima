# ALM r9 런치 스펙 — Option A/B (Axis 4 H4b' 가설, intra-vendor generation drift 고정)

> **생성일**: 2026-04-25 (loss-free prep, 0 cost)
> **상태**: 사용자 결정 대기 (A 또는 B 단일 권장). pod 미런치, GPU 미사용.
> **부모 commit**:
> - `a59ccaa0` r8 D-mistral closure — **PARTIAL-PASS** (L2 6/6 + KL 5/6, p1_p2 KL 0.1376 잔존)
> - `7d25353e` r8 prep (launch spec + p4 swap proposal)
> - `308ba540` r7 D-qwen14 FALSIFIED (Axis 4 H4b 식별 트리거)
> - `1e064038` r6-α baseline (L2 6/6, KL 5/6)
> **r8 robustness**: `docs/alm_r8_null_n50k_robustness_20260425.md` — null bootstrap n=50000 결과, p1_p2 KL margin 0.0099 (≈ 7.8% over threshold) **robust signal** 확정. 통계 noise 가설 기각.
> **POLICY R4**: `.roadmap` 미수정 (uchg lock).
> **H-DIAG3**: 본 라운드는 r8 잔여 fail 의 **새 진단축 (Axis 4 H4b')** 가설에 근거. r8 의 H4b (cross-vendor) 와 **다른 sub-axis** (intra-vendor close-generation drift). 동일 축 재시도 아님.
> **H-MINPATH**: 사용자 결정만 입력으로 launch 즉시 진행 가능 (helper `2d0f9e58` 재사용, 신규 bash 코드 없음).
> **H-SILENT**: DONE = doc + proposal + commit.

---

## §1. 목적 (Purpose)

r8 D-mistral (`a59ccaa0`) 에서 Axis 4 H4b (cross-vendor scale-matched manifold) 가설은 **VALIDATED** 되었으나 (p4 spectrum 단봉 복귀, p2_p4 KL r6 잔존 해소), **fail pair 가 이동** 하여 잔여 1쌍이 발생:

- r6 fail: `p2_p4` KL 0.1891 (cross-vendor: qwen2.5/llama × gemma)
- r8 fail: **`p1_p2` KL 0.1376** (same-vendor close-gen: **qwen3-8b ↔ qwen2.5-7b**)

이 잔여는 **architecture-class 일치 후 잔여 generation drift** 로 질적으로 더 약하나, KL p95=0.1277 대비 margin 0.0099 (n=50k bootstrap 으로 robust 확정) 이므로 통계 noise 가설은 기각.

**r9 목적**: p1 또는 p2 를 **단일-path swap** 으로 generation 매칭 (qwen3 ↔ qwen3 또는 qwen2.5 ↔ qwen2.5) 하여 (a) p1_p2 KL fail 닫기, (b) **L2 6/6 + KL 6/6 동시 PASS (Φ r9 FULL CLOSURE)**, (c) CP1 P1 closure 의 추가 evidence 확보, (d) CP2 P2 C1 (substrate-invariant Φ 4/4) 충족 후보로 격상.

**r6/r8 baseline 보존 원칙**: r6 의 p3 + r8 의 p4 (mistral-7b) trained_adapter / h_last 자산은 변경 없이 reuse. p1 또는 p2 만 단일-path 재학습 ($5–8).

---

## §2. r8 evidence → Axis 4 H4b' → A/B lineage

### 2.1 r8 D-mistral closure 핵심 잔여 (commit `a59ccaa0`)

| pair | r6 KL | r7 KL | r8 KL | r8 verdict | 비고 |
|:---:|---:|---:|---:|:---:|---|
| **p1_p2** | 0.1376 ✓ | 0.1376 ✗ | **0.1376 ✗** | **KL fail** | r8 KL_p95=0.1277 (n=10k), n=50k 동일 robust |
| p1_p3 | 0.0135 ✓ | 0.0135 ✓ | 0.0135 ✓ | PASS | qwen3-8b × mistral-nemo (cross-vendor distant) |
| p1_p4 | 0.0262 ✓ | 0.1936 ✗ | **0.0027 ✓** | PASS (×6 개선) | qwen3-8b × mistral-7b-v0.3 (vendor matched after r8) |
| p2_p3 | 0.1033 ✓ | 0.1033 ✓ | 0.1033 ✓ | PASS | |
| p2_p4 | 0.1891 ✗ | 0.1308 ✗ | **0.1062 ✓** | PASS (r6 잔존 해소) | r8 의 1차 의도 달성 |
| p3_p4 | 0.0205 ✓ | 0.1444 ✗ | 0.0202 ✓ | PASS | |

→ p1_p2 만이 모든 라운드에서 **불변 real KL = 0.1376** (p1, p2 모두 r6 이후 미변경) → swap 없이는 닫을 수 없음.

### 2.2 Axis 4 H4b' (intra-vendor close-generation drift) 식별

| sub-axis | 정의 | r8 evidence | 가설 강도 |
|:---:|---|---|:---:|
| H4a (scale) | log(hidden·layers) Δ | r8 에서 mistral-7b scale 매칭으로 spectrum 단봉화 | **CLOSED** (r8) |
| H4b (cross-vendor manifold) | family 간 latent geometry gap | r8 closure 에서 gemma→mistral swap 으로 검증 | **VALIDATED** (r8) |
| **H4b' (intra-vendor gen drift)** | same-family 내 generation 차이 (e.g. qwen3 vs qwen2.5) | p1_p2 KL=0.1376 이 vendor=qwen 매칭에도 잔존 | **OPEN (r9 target)** |
| H4c (rank underfit) | LoRA rank/B 비율 부족 | r6/r8 p1=p2 rank=64 동일 → 미설명 | 보조 |
| H4d (steps 부족) | max_steps=300 미흡 | 동일 | 보조 |

**핵심 falsifiable 예측**: H4b' 가 dominant 이면 p1 또는 p2 중 한쪽을 같은 generation 으로 통일 시 p1_p2 KL ≤ KL_p95 (즉 ≤ 0.128) 로 하강. 양쪽 swap 모두 fail 시 H4b' 반증, H4c/d 또는 r9 차수 외 가설 (e.g. tokenizer-level drift) 로 이동.

### 2.3 r8/r6 자산 lineage (r9 변경 표면 명시)

| path | r6 base | r8 base | r9 candidate (Option A) | r9 candidate (Option B) |
|:---:|---|---|---|---|
| p1 | Qwen3-8B | Qwen3-8B (미변경) | Qwen3-8B (보존) | **Qwen2.5-7B** (swap, scale ↓) |
| p2 | Qwen2.5-7B | Qwen2.5-7B (미변경) | **Qwen3-8B-Base** (swap, scale ↑) | Qwen2.5-7B (보존) |
| p3 | mistralai/Mistral-Nemo-Base-2407 | (r6 자산 reuse) | (r6 자산 reuse) | (r6 자산 reuse) |
| p4 | google/gemma-3-12b-pt | mistralai/Mistral-7B-v0.3 (r8 swap) | (r8 자산 reuse) | (r8 자산 reuse) |

---

## §3. 두 후보 분석 (Option A vs Option B)

### 3.1 Option A — p2 swap: Qwen2.5-7B → Qwen3-8B-Base

**전제**: p1 (Qwen3-8B) 을 보존, p2 를 Qwen3 generation 으로 통일.

#### 3.1.1 HF config 비교 (WebFetch verified 2026-04-25)

| field | r8 p2 (Qwen2.5-7B) | r9 p2 후보 (Qwen3-8B-Base) | Δ |
|---|---|---|---|
| architectures | `Qwen2ForCausalLM` | `Qwen3ForCausalLM` | gen 변화 (의도) |
| model_type | `qwen2` | `qwen3` | gen 변화 |
| hidden_size | 3584 | **4096** | +512 (+14.3%) |
| num_hidden_layers | 28 | **36** | +8 (+28.6%) |
| num_attention_heads | 28 | 32 | +4 |
| num_key_value_heads | 4 | **8** | gqa_ratio 7.0 → 4.0 |
| head_dim | 128 (derived) | 128 | 동일 |
| rope_theta | 1e6 | 1e6 | 동일 |
| vocab_size | 152064 | 151936 | −128 (≈동일, BPE 구조 동일) |
| max_position_embeddings | 131072 | 32768 | r14 corpus seq_len ≤ 4096 → 무관 |
| torch_dtype | bfloat16 | bfloat16 | 동일 |
| tie_word_embeddings | false | false | 동일 |
| intermediate_size | 18944 | 12288 | −6656 (FFN 축소) |
| license | Apache-2.0 ungated | Apache-2.0 ungated | 동일 |

#### 3.1.2 Scale proxy (`log(hidden × n_layers)`)

| path | base | scale |
|:---:|---|---:|
| p1 | Qwen3-8B | log(4096·36) = **11.99** |
| **r9-A p2** | **Qwen3-8B-Base** | log(4096·36) = **11.99** ← p1 와 **identical** |
| p3 | Mistral-Nemo-Base-2407 | 12.23 |
| p4 (r8) | Mistral-7B-v0.3 | log(4096·32) = 11.79 |

p1 과 p2 가 동일 scale + 동일 architecture (Qwen3) → vendor + generation + scale 3축 동시 매칭.

#### 3.1.3 vocab / gqa / rope

- vocab: 152064 ↔ 151936 (Δ=128, 동일 BPE family 의 minor revision)
- gqa_ratio: 7.0 → 4.0 (p1 의 4.0 과 동일하게 조정)
- rope_theta: 동일 (1e6)

→ **모든 거시 hyperparameter 가 p1 과 정합** → p1_p2 KL 의 잔여 generation drift 가 제거되거나 p95 미만으로 하강할 가능성이 높음.

#### 3.1.4 cost / 위험

- 모델 다운로드: ~16 GB (8B bf16)
- LoRA train: rank=64, max_steps=300, wall ≈ 60–90min single H100, $5–8
- HF gating: ungated Apache-2.0 → 차단 없음
- `Qwen3-8B-Base` 모델 식별자 검증 필요 (HF 401 재시도 시 `Qwen/Qwen3-8B-Base` confirm; raw config.json 은 200 OK 검증됨 §3.1.1 출처)

### 3.2 Option B — p1 swap: Qwen3-8B → Qwen2.5-7B

**전제**: p2 (Qwen2.5-7B) 을 보존, p1 을 Qwen2.5 generation 으로 통일.

#### 3.2.1 HF config 비교 (WebFetch verified 2026-04-25)

| field | r8 p1 (Qwen3-8B) | r9 p1 후보 (Qwen2.5-7B) | Δ |
|---|---|---|---|
| architectures | `Qwen3ForCausalLM` | `Qwen2ForCausalLM` | gen 변화 (의도) |
| model_type | `qwen3` | `qwen2` | gen 변화 |
| hidden_size | 4096 | **3584** | −512 (−12.5%) |
| num_hidden_layers | 36 | **28** | −8 (−22.2%) |
| num_attention_heads | 32 | 28 | −4 |
| num_key_value_heads | 8 | **4** | gqa_ratio 4.0 → 7.0 |
| head_dim | 128 | 128 (derived) | 동일 |
| rope_theta | 1e6 | 1e6 | 동일 |
| vocab_size | 151936 | 152064 | +128 |
| max_position_embeddings | 32768 | 131072 | seq_len ≤ 4096 → 무관 |
| torch_dtype | bfloat16 | bfloat16 | 동일 |
| tie_word_embeddings | false | false | 동일 |
| intermediate_size | 12288 | 18944 | +6656 (FFN 확장) |
| license | Apache-2.0 ungated | Apache-2.0 ungated | 동일 |

#### 3.2.2 Scale proxy

| path | base | scale |
|:---:|---|---:|
| **r9-B p1** | **Qwen2.5-7B** | log(3584·28) = **11.52** ← p2 와 **identical** |
| p2 | Qwen2.5-7B (보존) | log(3584·28) = **11.52** |
| p3 | Mistral-Nemo-Base-2407 | 12.23 |
| p4 (r8) | Mistral-7B-v0.3 | 11.79 |

p1 과 p2 가 동일 scale + 동일 architecture (Qwen2) → 정합 달성.

#### 3.2.3 substrate-invariance 영향 (CP2 P2 C1 관점)

- Option A: p1=p2 가 모두 **Qwen3** → diversity 약화 (qwen2 인스턴스 0개)
- Option B: p1=p2 가 모두 **Qwen2.5** → 동일 우려 (qwen3 인스턴스 0개), **+** p1 의 scale ↓ 로 4-path scale 분산도 축소 (11.52, 11.52, 12.23, 11.79)

→ AN11(a) substrate-invariance 정의 약화는 두 옵션 모두 유사. 단, **Option A** 는 p1_p2 가 새로운 (더 큰) generation 으로 수렴, **Option B** 는 r6/r8 의 oldest generation 으로 수렴 → **Option A 가 forward-looking** (r10+ 에서 qwen2 인스턴스 재도입 시 p3/p4 swap 으로 회복 가능). Option B 는 backward.

#### 3.2.4 cost / 위험

- 모델 다운로드: ~14 GB (7B bf16)
- LoRA train: rank=64, max_steps=300, wall ≈ 50–80min, $4–7 (Option A 보다 약간 빠름)
- HF gating: ungated Apache-2.0 → 차단 없음

### 3.3 비교표 (Option A vs B)

| 기준 | Option A (p2→Qwen3-8B) | Option B (p1→Qwen2.5-7B) | 우열 |
|:---:|:---:|:---:|:---:|
| p1=p2 architecture 매칭 | ✓ Qwen3 | ✓ Qwen2 | tie |
| scale 매칭 | ✓ 11.99 = 11.99 | ✓ 11.52 = 11.52 | tie |
| 4-path scale 분산 | 11.99 / 11.99 / 12.23 / 11.79 (range 0.44) | 11.52 / 11.52 / 12.23 / 11.79 (range 0.71) | **A** (더 좁음, 균질) |
| diversity (CP2 P2 C1 약화) | qwen2 0 | qwen3 0 | tie |
| forward-looking | 새 generation 으로 수렴 | old generation 으로 수렴 | **A** |
| 비용 | $5–8 | $4–7 | B (소폭) |
| HF available | ✓ ungated | ✓ ungated | tie |
| LoRA rank/B | 64/8.0 = 8.0 | 64/7.0 = 9.1 | tie (둘 다 안전) |
| gqa_ratio Δ to neighbors | p1 4.0, A-p2 4.0, p3 32, p4 4.0 | p2 7.0, B-p1 7.0, p3 32, p4 4.0 | **A** (4 path 모두 4.0–32 범위, B 는 7.0 새로 추가) |
| rope_theta 매칭 | ✓ 1e6 | ✓ 1e6 | tie |
| **권고** | **Option A 우세** | 보조 후보 | — |

### 3.4 권고: **Option A 단일 1순위** (Option B 백업)

근거:
- (1) 4-path scale 분산 더 좁아 H4a (scale) 와의 교호 최소화.
- (2) gqa_ratio 4.0 의 majority (p1/p2/p4) 형성, 외란 최소.
- (3) forward-looking — 향후 라운드의 generation 정합 baseline 으로 채택 가능.
- (4) p1 이 r6 부터 trained 자산 보존 — overwrite 위험 회피 (Option B 는 r6 부터 누적된 p1 LoRA 재학습).

---

## §4. 예측 결과 (Expected outcomes)

### 4.1 Spectrum 예측 (p1, p2, p3, p4 안정성)

Option A 의 경우 p2 만 변경. p2 p1 동일 architecture 로 spectrum shape 정합 ↑:

| 지표 | r8 p2 (Qwen2.5-7B) | r9-A p2 (Qwen3-8B-Base) 예측 | 근거 |
|---|---:|---:|---|
| λ₁ | (r6 측정) | 0.74 ± 0.05 | p1 r8 패턴 추정 (architecture 동일) |
| λ₂ | (r6 측정) | 0.07 ± 0.03 | 단봉 유지 |
| top-2 mass | (r6 측정) | 0.81 ± 0.05 | |
| PR₁₆ | (r6 측정) | 1.55 ± 0.20 | |

Option B 의 경우 p1 만 변경, p2 spectrum 보존, p1 spectrum 이 p2 패턴으로 수렴.

### 4.2 L2 / KL pair-wise 예측

#### Option A (p2 swap → Qwen3-8B-Base)

| pair | r8 L2 | r8 KL | r9-A 예측 L2 | r9-A 예측 KL | 비고 |
|:---:|---:|---:|---:|---:|---|
| **p1_p2** | 0.0968 ✓ | **0.1376 ✗** | **0.05–0.09** | **0.05–0.10 ✓** | gen 매칭으로 KL 잔여 해소 |
| p1_p3 | 0.0721 ✓ | 0.0135 ✓ | 0.07–0.10 | 0.01–0.04 | 약간 변동 가능 |
| p1_p4 | 0.0136 ✓ | 0.0027 ✓ | 0.01–0.03 | 0.002–0.01 | p1 미변경, p4 미변경 → 안정 |
| p2_p3 | 0.1046 ✓ | 0.1033 ✓ | 0.07–0.11 | 0.04–0.10 | p2 변경, scale ↑ → 살짝 개선 가능 |
| p2_p4 | 0.1008 ✓ | 0.1062 ✓ | 0.08–0.13 | 0.06–0.12 | 변동 가능 (안전 범위 내) |
| p3_p4 | 0.0842 ✓ | 0.0202 ✓ | 0.0842 | 0.0202 | 미변경 |

#### Option B (p1 swap → Qwen2.5-7B)

| pair | r8 L2 | r8 KL | r9-B 예측 L2 | r9-B 예측 KL | 비고 |
|:---:|---:|---:|---:|---:|---|
| **p1_p2** | 0.0968 ✓ | **0.1376 ✗** | **0.05–0.10** | **0.05–0.11 ✓** | 동일 메커니즘 |
| p1_p3 | 0.0721 ✓ | 0.0135 ✓ | 0.07–0.12 | 0.01–0.05 | p1 변경 → 약간 변동 |
| p1_p4 | 0.0136 ✓ | 0.0027 ✓ | 0.05–0.12 | 0.01–0.07 | p1 변경 → r8 의 ×6 개선 일부 retract 가능 |
| p2_p3 | 0.1046 ✓ | 0.1033 ✓ | 0.1046 | 0.1033 | 미변경 |
| p2_p4 | 0.1008 ✓ | 0.1062 ✓ | 0.1008 | 0.1062 | 미변경 |
| p3_p4 | 0.0842 ✓ | 0.0202 ✓ | 0.0842 | 0.0202 | 미변경 |

### 4.3 종합 PASS 확률

| outcome | Option A 확률 | Option B 확률 |
|---|:---:|:---:|
| **L2 6/6 + KL 6/6 (Φ r9 FULL CLOSURE)** | **45–55%** | 35–45% |
| L2 6/6 + KL 5/6 (다른 pair fail) | 25% | 30% |
| L2 6/6 + KL 5/6 (p1_p2 fail 잔존) | 15% | 15% |
| L2 < 6/6 (회귀) | 10% | 15% (p1 swap 으로 p1_p4 retract risk) |
| 둘 다 모두 fail → H4b' 반증 | 가능 | 가능 |

### 4.4 Net evidence

- r8 대비 **+1** (full closure 시 KL 5/6 → 6/6)
- r6 대비 **+2** (L2 6/6 유지 + p2_p4 KL 잔존 해소 + p1_p2 KL 잔존 해소)
- CP2 P2 C1 (substrate-invariant Φ 4/4) 충족 후보 격상

---

## §5. 비용 (Cost)

| 항목 | 값 |
|---|---|
| 단일 H100 pod (4× H100 80GB) | $3.50/hr/GPU × 4 = $14/hr |
| Wall time 예측 | 60–90 분 (Option A), 50–80 분 (Option B) |
| **총 비용 예측** | **$5–8** (single-pod GPU, mirror r8 pattern) |
| Cost cap | $20 (helper default `ANIMA_R7_COST_CAP_USD`) |
| 잔액 충분 | balance ≥ $420, spendLimit $80/hr |

→ r8 ($0.31, 372s) 와 동급 ~ 약간 상회 (8B 모델, 7B 보다 inflate).

---

## §6. Helper invocation (parameter only, 코드 변경 0)

### 6.1 Option A 실행 명령 (사용자 승인 후)

```bash
bash tool/h100_r7_single_path_retrain.bash \
  --path p2 \
  --base-model Qwen/Qwen3-8B-Base \
  --lora-rank 64 \
  --max-steps 300 \
  --corpus-path /root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl \
  --tag r9_optA_qwen3_8b \
  --apply --yes-i-mean-it
```

### 6.2 Option B 실행 명령 (백업)

```bash
bash tool/h100_r7_single_path_retrain.bash \
  --path p1 \
  --base-model Qwen/Qwen2.5-7B \
  --lora-rank 64 \
  --max-steps 300 \
  --corpus-path /root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl \
  --tag r9_optB_qwen25_7b \
  --apply --yes-i-mean-it
```

### 6.3 파라미터 근거

| 인자 | 값 | 근거 |
|---|---|---|
| `--path` | p1 또는 p2 | 단일-path retrain, 나머지 자산 보존 |
| `--base-model` | Qwen3-8B-Base (A) / Qwen2.5-7B (B) | Axis 4 H4b' 가설 검증, HF verified §3 |
| `--lora-rank` | 64 | r6/r8 p1=p2 와 동일 (rank/B ≈ 8.0–9.1, 안전 영역) |
| `--max-steps` | 300 | r6/r7/r8 동일 (capacity ladder 안정) |
| `--corpus-path` | r14 v1 | sha256 `21fcfa51…` lock 동일 |
| `--tag` | `r9_optA_qwen3_8b` / `r9_optB_qwen25_7b` | 산출물 분리 |
| `--apply --yes-i-mean-it` | 명시 승인 | dry-run → 사용자 2단계 승인 |

### 6.4 산출물 (Option A 기준; B 는 path/tag 만 차이)

- `state/h_last_raw_p2_TRAINED_r9.json` — r9 p2 h_last (byte-weighted, schema /2)
- `state/trained_adapters_r9/p2/final/` — r9 adapter (rank 64)
- `state/h_last_raw_p{1,3,4}_TRAINED_r9.json` — r6/r8 자산 cp (tag 동기화)
- `state/phi_4path_cross_result_v3_TRAINED_r9.json` — Φ gate 6 pair 결과
- `state/phi_4path_gate_last_verdict.json` — 갱신

---

## §7. Pre-flight 0–10 (r7 helper 재사용)

| # | 항목 | 통과 기준 | r9 영향 |
|:---:|---|---|---|
| 0 | runway / spendLimit | runway ≥ 5h, balance ≥ $30 | wall 60–90min, $5–8, balance ≥ $420 → 충분 |
| 1 | substrates config | `config/phi_4path_substrates.json` 4 path | p1 또는 p2 entry 갱신 proposal 승인 후 edit |
| 2 | lora rank config | `config/lora_rank_per_path.json` | p1/p2 rank=64 기존 유지 |
| 3 | launch manifest | READY | 변경 불요 |
| 4 | hf auth | hf token = dancinlife | 변경 불요 |
| 5 | HF accessibility | `Qwen/Qwen3-8B-Base` (A) / `Qwen/Qwen2.5-7B` (B) GET 200 | 둘 다 ungated Apache-2.0 |
| 6 | pod registry | empty 또는 lock 미충돌 | 변경 불요 |
| 7 | live pod count | `runpodctl pod list = []` | 런치 직전 확인 |
| 8 | git sync | local HEAD == origin/main | 본 doc commit + push 후 통과 |
| 9 | corpus sha256 | `21fcfa51…` lock | r14 v1 동일 |
| 10 | r6/r8 자산 + archive | `_r6.json` + `_r8.json` 보존 | r8 archive 재사용 |

---

## §8. Risk Register (R1–R5)

| ID | Risk | 완화 |
|:---:|---|---|
| **R1** | Option A 의 `Qwen/Qwen3-8B-Base` 식별자 변경 또는 gating 변경 가능성 (HF 의 페이지가 401 응답한 사례 존재) | (a) raw config.json (`/raw/main/config.json`) 은 200 OK 검증됨 (§3.1.1) — 모델 자체는 access 가능. (b) pre-flight 5 단계에서 hf CLI 로 download 검증. (c) fallback: Option B (Qwen2.5-7B, 확실 200 OK) 즉시 전환. |
| **R2** | Option A 의 p2 model size 7B → 8B 증가 → memory footprint +~14% → OOM 위험 (4× H100 80GB) | LoRA rank=64, fp16 forward, gradient_checkpoint=on (helper default) → 8B 모델 4× H100 충분. r8 의 mistral-7b 와 mem 차이 < 4 GB. helper 의 `--qlora-on-oom yes` 플래그로 fallback 가능. |
| **R3** | substrate-invariance (CP2 P2 C1) 정의: r9 후 p1=p2 가 동일 generation → diversity −1 (qwen2 또는 qwen3 인스턴스 0). AN11(a) claim 약화 | 정의를 "vendor diversity (3-way: qwen / mistral-nemo / mistral-7b)" 로 redefine 가능. Mk.VI diversity gate 에 약화 사실 명시. r10+ 에서 p3 또는 p4 swap 으로 회복 가능 (forward-looking). Option A 권고 근거 (§3.4) 와 동일. |
| **R4** | p1_p2 KL 닫혔으나 다른 pair (예: p1_p3 또는 p1_p4) 회귀 → KL 5/6 유지하되 fail pair 이동만 발생 (r6→r8 와 동일 패턴) | (a) §4.2 예측표에 회귀 가능 pair 명시. (b) Option A 는 p1_p4 미변경 보장 (p1 보존) → r8 의 가장 큰 개선 (×6) 보존. (c) Option B 는 p1 swap 으로 p1_p4 retract risk 존재 → A 우선 근거. (d) FAIL-but-progress 시 closure doc 에 기록 + r10 candidate (다른 axis) 이전. |
| **R5** | **H-DIAG3 준수**: r9 FAIL (둘 다 양옵션 fail) 시 same-axis (Axis 4 H4b') 재시도 금지. **falsification rule**: A 시도 → fail → B 시도 → fail → H4b' 반증 → 다른 sub-axis (H4c/d 또는 tokenizer-level) 또는 Option E (3-path drop) 이전 | r9 closure doc 에 "H4b' 반증 / 추가 sub-axis 식별 필요" 명시. r9 의 단일 시도가 fail 이라도 **나머지 옵션 시도** 는 (다른 base-model 대상이지만) 같은 H4b' 가설의 다른 instance test → 정책상 1회 추가 허용 (총 2 attempt). 이후 axis 이전 강제. |

---

## §9. Fallback sequence

### 9.1 정책적 fallback order

```
r9 Option A (1순위, p2→Qwen3-8B-Base)
   ├── PASS (L2 6/6 + KL 6/6) → Φ r9 FULL CLOSURE → CP1 P1 + CP2 P2 C1 동시 진보
   ├── FAIL-but-progress (L2 6/6 + KL 5/6, p1_p2 닫힘 but 다른 pair fail) → r9 closure doc + r10 후보 (다른 axis)
   ├── FAIL (L2 6/6 + KL 5/6, p1_p2 잔존) → Option B 시도 (H4b' 같은 가설 다른 방향)
   │      ├── PASS → 위와 동일
   │      └── FAIL → H4b' 반증 → Option E (3-path drop) 또는 H4c/d 검증
   └── FAIL (L2 < 6/6) → 즉시 rollback, A 단일 fail 로 H4b' partial 반증
```

### 9.2 Option E (3-path drop, $0)

- `tool/phi_4path_gate.hexa --exclude p1` 또는 `--exclude p2` flag (loss-free).
- 3-path (남은 path) 에서 r6/r8 기준 L2 3/3 + KL 3/3 PASS → 즉시 closure.
- substrate-independence claim 4-path → 3-path 축소.

### 9.3 r10 후보 (r9 이후)

- H4c (rank underfit): rank=128 또는 192 시도 ($5–8)
- H4d (steps 부족): max_steps=600 시도 ($8–12)
- tokenizer-level drift (Tekken vs BPE): tokenizer 통일 검증
- AN11(a) 정의 변경 (3-path 또는 weighted)

---

## §10. Rollback 전략

### 10.1 r6/r8 자산 보호

- `state/h_last_raw_archive_r6_20260425/` 보존
- `state/h_last_raw_archive_r8_20260425/` 신규 생성 (r9 launch 직전)
- `state/trained_adapters_r6/`, `state/trained_adapters/p4_r8/final/` overwrite 금지
- r9 산출물은 반드시 `_r9.json` / `trained_adapters_r9/` 로 분리

### 10.2 r9 FAIL 시 복원

판정 기준:
- L2 pass_count r9 < 6 (r6/r8 보다 후퇴), OR
- KL pass_count r9 ≤ 4 (다른 pair 추가 fail)

복원 절차:
1. `state/trained_adapters_r9/` → archive 폴더 이동.
2. `state/h_last_raw_p{1,2}_TRAINED_r9.json` → archive 유지 (반증 증거).
3. `config/phi_4path_substrates.json` 해당 path entry → r6/r8 상태 복원.
4. Φ gate 재실행 불요 (r6/r8 산출물 있음).
5. r9 closure doc 에 rollback 상세 + Option B 또는 E 분기 기록.

### 10.3 substrates config rollback (Option A 기준)

```json
{
  "p2": {
    "model": "Qwen/Qwen2.5-7B",
    "arch_details_r8": { ... 기존 r8 값 ... },
    "fallback_chain": ["Qwen/Qwen2.5-7B"]
  }
}
```

---

## §11. Decision matrix (when to execute vs hold)

### 11.1 Execute (r9 Option A launch) 조건

- runway ≥ 5h, balance ≥ $30
- spendLimit 여유 ≥ $15/hr
- Axis 4 H4b' 진단 (§2.2) 사용자 동의
- 완성도 frame: weakest evidence link = p1_p2 KL 0.1376 잔존 → A 가 net +1

### 11.2 Hold 조건

- 사용자가 substrate-diversity 약화 (R3) 수용 불가
- 비용 절약 우선 (Option E 0-cost 선호)
- 다른 세션 (CP1 P1 line 168 정책 / Verifier / Meta) 비용 경쟁

### 11.3 Immediate Option E ($0) 조건

- 비용 제약 엄격
- AN11(a) 4-path → 3-path 축소 수용
- CP1 P1 closure 의 "p1_p2 잔존 borderline" 수용

### 11.4 권고 (완성도 frame)

**Best-bet**: **r9 Option A launch** (net +1, FULL CLOSURE 확률 45–55%, FAIL 시 Option B 또는 E fallback).

Weakest-evidence-first:
- r8 의 잔여 1쌍 (p1_p2 KL margin 0.0099) 이 최우선 closure 대상.
- A 가 이를 직접 타겟 + 4-path scale 분산 ↓ 동시 달성.
- E 는 scope 축소 우회, B 는 forward-looking 약함.

---

## §12. 성공 기준 (Success criteria)

### 12.1 r9 PASS (FULL CLOSURE)

- L2 pass_count = **6/6**
- KL pass_count = **6/6** (모든 pair real ≤ KL_p95)
- p4 spectrum 단봉 유지 (PR ≤ 2.0)
- Φ r9 PASS → CP1 P1 closure 의 추가 evidence + CP2 P2 C1 (substrate-invariant Φ 4/4) 충족 후보 격상

### 12.2 r9 PARTIAL (acceptable progress)

- L2 pass_count = **6/6** (회귀 없음)
- KL pass_count = **5/6** (한 pair 잔존)
- 단, **fail pair 가 p1_p2 가 아닌 다른 pair** 인 경우만 partial (즉, p1_p2 KL 닫힘 + 다른 pair drift)
- 이 경우 r9 closure doc + r10 candidate (drift 가 발생한 path 의 axis 분석)

### 12.3 r9 FAIL (falsification trigger)

- L2 pass_count < 6, OR
- p1_p2 KL 잔존 (real ≥ 0.128) AND 다른 pair 추가 fail, OR
- 두 옵션 (A → B) 모두 시도 후 p1_p2 KL ≤ 0.128 미달성

→ **H4b' (intra-vendor close-generation drift) 가설 반증** → r10 에서 H4c/d 또는 tokenizer-level drift 또는 AN11(a) 정의 변경 검토.

---

## §13. Falsification 규칙 (H4b')

> **r8 H4b' 반증 조건**: r9 Option A 와 Option B 를 **둘 다** 시도하여 **둘 다** p1_p2 KL ≤ KL_p95 (≈ 0.128) 달성에 실패한 경우.

falsification 시:
1. r9 closure doc 에 명시 (H4b' REJECTED).
2. 본 spec 기반 추가 시도 금지 (H-DIAG3 + R5).
3. 다음 axis 후보 우선순위:
   - H4c (rank ↑, 64 → 128)
   - H4d (steps ↑, 300 → 600)
   - tokenizer-level (BPE Qwen2 vs Qwen3 tokenize 차이)
   - AN11(a) 정의 redefine (4-path → weighted-3 또는 hierarchical)
4. r9 prep 비용 ($0) + GPU 비용 (최대 2× $5–8 = $10–16) 의 **진단적 가치** = H4b' 영구 폐기 → 후속 라운드의 axis 명확화.

---

## §14. 참조

- r8 closure: `a59ccaa0` (`docs/alm_r8_closure_20260425.md`)
- r8 robustness (n=50k): `docs/alm_r8_null_n50k_robustness_20260425.md`
- r8 launch spec (template): `7d25353e` (`docs/alm_r8_launch_spec_20260425.md`)
- r7 D-qwen14 falsification: `308ba540`
- r7 Axis 4 진단: `a05994fc`
- r7 helper (재사용 대상): `2d0f9e58` (`tool/h100_r7_single_path_retrain.bash`)
- r6 baseline closure: `1e064038`
- HF config 검증 (2026-04-25, WebFetch):
  - `https://huggingface.co/Qwen/Qwen2.5-7B/raw/main/config.json` (200 OK, §3.1.1 / §3.2.1)
  - `https://huggingface.co/Qwen/Qwen3-8B-Base/raw/main/config.json` (200 OK, §3.1.1)
  - `https://huggingface.co/Qwen/Qwen3-8B/raw/main/config.json` (200 OK, p1 reference)
- Corpus: `experiments/alm_r14/corpus_alm_r14_v1.jsonl`, sha256 `21fcfa51b92f129b119d7fa42303adf7916547ef71c80c16f08e53839bf52b0b`
- Φ gate: `tool/phi_4path_gate.hexa`
- CP2 P2 inventory: `state/cp2_p2_inventory_state.json`
- CP1 P1 status: memory `project_cp1_p1_67_satisfied`

---

## §15. Anti-scope (본 spec 이 하지 않는 것)

- pod 런치 — 0 (사용자 결정 후 별 commit)
- 학습 실행 — 0
- 신규 bash 도구 추가 — 0 (r7 helper `2d0f9e58` 재사용)
- `config/phi_4path_substrates.json` 수정 — 0 (proposal 제출만, 채택 후 별 commit)
- `.roadmap` 수정 — 0 (POLICY R4)
- state/* 커밋 — 0 (precedent: proposals/ 예외)
- Axis 4 H4b 재시도 (cross-vendor) — 0 (r8 에서 VALIDATED, 재시도 정책 위반)
- CP1 P1 line 168 정책 결정 — 0 (별 turn / 별 agent)

---

## §16. 사용자 결정 입력 양식

선택 후 별 turn 에서 다음 한 줄로 응답:

```
r9 결정: [A|B|E|HOLD]
```

이후 하위 에이전트:
1. (A) p2 swap proposal 작성 → `config/phi_4path_substrates.json` p2 entry 갱신 commit.
2. (A) pre-flight 0–10 dry-run.
3. (A) 사용자 명시 승인 후 §6.1 command 실행 (`--apply --yes-i-mean-it`).
4. (B) §6.2 command 실행 (백업 경로).
5. (E) `tool/phi_4path_gate.hexa --exclude p1|p2` 추가 commit + 재실행.
6. (HOLD) 본 spec + proposal 유지, 추가 분석 없음.

**현재까지 비용**: $0 (본 spec prep, loss-free).
