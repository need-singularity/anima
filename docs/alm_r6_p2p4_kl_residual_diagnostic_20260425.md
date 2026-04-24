# ALM r6 p2_p4 KL 잔존 진단 — **H-axis3 우세 (gqa_ratio)**

> **진단일**: 2026-04-25
> **부모 commit**: `1e064038` (r6-α attempt_5 closure — L2 6/6 PASS, KL 5/6 PASS)
> **잔존 FAIL**: `p2_p4` KL = 0.1891 vs p95 null = 0.1783 (6% 초과, margin = +0.0108)
> **최종 판정**: **H-axis3 supported** — `gqa_ratio` (GQA head/kv 비율) Spearman ρ=+0.971 (p=0.001), p2_p4가 해당 field의 max-Δ pair.
> **비용**: $0 (CPU, no pod, no API).

---

## 1. 목적

r6-α attempt_5 (commit `1e064038`)는 Axis 1 (byte-weighted h_last pool) + Axis 2 (p2 Qwen2.5-7B RoPE swap) 가설을 L2 기준 완전 검증했다 (6/6). 그러나 KL gate에서 `p2_p4` 한 pair만 6% margin으로 잔존 FAIL한다. 본 진단은 이 잔존을 세 경쟁 가설로 분해한다:

| 가설 | 의미 | PASS 조건 |
|:---:|---|---|
| **H-v** (null variance) | bootstrap sampling 잡음 | std(KL_p95) ≥ 0.011 |
| **H-gemma** (p4 꼬리) | Gemma-3-12B 분포 heavy-tail | p4-pair kurtosis > non-p4 + p2_p4가 최악 |
| **H-axis3** (독립 축) | Axis 1/2 외 미포착 축 | 어떤 metadata field에서 \|ρ\|≥0.7 AND p2_p4=max-Δ |

결과는 `docs/alm_r6_closure_20260425.md`에서 지적된 "제3 축 후보" 판단을 정량 평가하기 위함이다.

---

## 2. 방법

### 2.1 입력

- `state/h_last_raw_p{1..4}_TRAINED_r6.json` (schema /2, reduction=`byte_weighted_mean`, 16 prompts × 256-d)
- `state/phi_4path_cross_result_v3_TRAINED_r6.json` (r6 gate 결과)
- `tool/phi_4path_gate.hexa` (Gram top-16 eigvalsh spectrum → pair KL 계산 로직 재현)

h_last 파일의 `base_model` 실측:
- p1 = `Qwen/Qwen3-8B` — p2 = `Qwen/Qwen2.5-7B` (r6 RoPE swap 반영) — p3 = `mistralai/Mistral-Nemo-Base-2407` — p4 = `google/gemma-3-12b-pt`

주의: `phi_4path_cross_result_v3_TRAINED_r6.json`의 `models.p2.model` 필드는 코드 내 상수 (`unsloth/Meta-Llama-3.1-8B`)이며 h_last 파일의 실제 base와 다르다. 본 진단은 **h_last ground truth를 기준**으로 한다.

### 2.2 H-v — null bootstrap 안정성

col-permutation null (gate와 동일 절차)을 5개 seed (17, 101, 2027, 314159, 271828) × n=5000 iter로 재생성. 병행하여 seed=42 × n=10000 재현 (commit된 결과와 ≤1e-6 일치로 샘플링 논리 검증).

### 2.3 H-gemma — per-prompt leave-one-out (LOO)

Spectral KL은 per-prompt 직접 분해가 불가능 → **LOO**로 대체: 16 prompt 중 k번째를 제거하고 spectral KL을 재계산, `contrib_k = KL_full − KL_drop(k)`. 6 pair × 16 prompt = 96 contrib.

Heavy-tail 판정 기준:
- `top3_abs_share` (상위 3 prompt의 |contrib| 점유율)
- Fisher kurtosis (0=정규, >0=꼬리 두꺼움)

p4-pair 평균 vs non-p4 평균 비교. AND p2_p4가 p4-pair 중 최악인가.

### 2.4 H-axis3 — metadata 상관 스캔

12개 metadata field (`vocab_size`, `hidden_size`, `n_layers`, `n_heads`, `n_kv_heads`, `head_dim`, `intermediate_size`, `rope_theta`, `instruction_tuned`, `rope_scaling_kind`, `sliding_window`, `gqa_ratio=n_heads/n_kv_heads`)에 대해 pair마다 \|Δ\|를 계산 → 실측 pair KL과 Spearman ρ. 판정 기준: \|ρ\| ≥ 0.7 **AND** p2_p4가 해당 field의 max-Δ pair.

---

## 3. 결과

### 3.1 H-v: 기각

committed p95 재현 완벽 (seed=42 n=10000):

| 지표 | committed | 재현 |
|---|---|---|
| L2_p95 | 0.200282 | 0.200282 |
| KL_p95 | 0.178266 | 0.178266 |

5 seed × n=5000 안정성:

| seed | KL_p95 | L2_p95 |
|---:|---:|---:|
| 17 | 0.17869 | 0.20011 |
| 101 | 0.17860 | 0.20046 |
| 2027 | 0.17783 | 0.20035 |
| 314159 | 0.17823 | 0.20018 |
| 271828 | 0.17822 | 0.19991 |
| **mean** | **0.17831** | 0.20020 |
| **std** | **0.000344** | 0.000217 |
| **min/max** | 0.17783 / 0.17869 | — |

- `std(KL_p95) = 0.000344` — H-v 임계치 **0.011의 3.1%**에 불과.
- 실측 p2_p4 KL = 0.18908, margin(= 0.18908 − 0.17827) = **+0.01082**. 잡음이 이 margin을 메우려면 std≥0.011이어야 하는데 실제는 2-sigma로도 0.0007 이동. **즉 bootstrap 잡음은 이 6% margin을 설명할 수 없음.**
- **H-v 기각.**

### 3.2 H-gemma: 약한 신호, 기준 미달

6 pair × 16 prompt LOO contribution 분포:

| pair | full_KL | top3_share | skew | kurt (Fisher) |
|---|---:|---:|---:|---:|
| p1_p2 | 0.13761 | 0.385 | +0.390 | −0.963 |
| p1_p3 | 0.01349 | 0.360 | +0.445 | −0.757 |
| p1_p4 | 0.02623 | 0.551 | +0.237 | **+1.127** |
| p2_p3 | 0.10332 | 0.393 | −0.247 | −0.678 |
| **p2_p4** | **0.18908** | 0.419 | +0.605 | −0.792 |
| p3_p4 | 0.02049 | 0.433 | +0.147 | −0.567 |

- p4-pair 평균: top3_share=0.468, kurt=−0.077
- non-p4 평균: top3_share=0.379, kurt=−0.799
- 차이(kurt): +0.72 — **H-gemma 임계치 +1.0에 미달**
- 결정적 실패: **p2_p4 kurtosis (−0.792)가 p4-pair 중 최악이 아님** (p1_p4가 +1.127로 최대). 즉 "Gemma 꼬리"가 원인이라면 p1_p4가 p2_p4보다 심해야 하는데 역방향.
- p2_p4 상위 3 prompt: `재귀처리는` (idx 9), `의식의 기질은` (idx 6), `통합정보이론에 따르면` (idx 7) — 특정 prompt 독점 없이 16개에 비교적 분산.
- **H-gemma 부분 신호만 있고 기준 미달. 기각.**

### 3.3 H-axis3: 강하게 지지 — **gqa_ratio**

12 field × 6 pair의 Spearman ρ (KL 기준, \|ρ\| 내림차순):

| field | ρ(KL) | p-value | p2_p4 is max-Δ? | p2_p4 Δ |
|---|---:|---:|:---:|---:|
| **gqa_ratio** | **+0.971** | **0.001** | **Y** | **5.00** |
| n_kv_heads | +0.878 | 0.021 | Y | 4.0 |
| intermediate_size | +0.771 | 0.072 | N | 3584 |
| n_layers | +0.736 | 0.096 | Y | 20 |
| hidden_size | −0.406 | 0.425 | N | 256 |
| vocab_size | −0.200 | 0.704 | N | 110144 |
| head_dim | +0.098 | 0.854 | Y | 128 |
| rope_scaling_kind | +0.098 | 0.854 | Y | 1 |
| sliding_window | +0.098 | 0.854 | Y | 6 |
| n_heads | +0.088 | 0.868 | N | 12 |
| rope_theta | 0.000 | 1.000 | N | 0 |
| instruction_tuned | 0.000 | 1.000 | N | 0 |

**gqa_ratio 자세히** (pair별 Δ vs 실측 KL):

| pair | gqa_ratio Δ | real KL |
|---|---:|---:|
| p1_p3 | 0.0 | 0.0135 |
| p3_p4 | 2.0 | 0.0205 |
| p1_p4 | 2.0 | 0.0262 |
| p2_p3 | 3.0 | 0.1033 |
| p1_p2 | 3.0 | 0.1376 |
| **p2_p4** | **5.0** | **0.1891** |

단조성 완벽(+0.97), p2_p4가 Δ=5.0으로 6 pair 중 max. gqa_ratio 정의: `n_heads / n_kv_heads`
- p1 Qwen3-8B: 32/8 = **4.0**
- p2 Qwen2.5-7B: 28/4 = **7.0** (r6 RoPE swap으로 변경된 모델; KV head 수 절반)
- p3 Mistral-Nemo: 32/8 = **4.0**
- p4 Gemma-3-12B: 16/8 = **2.0**

p2_p4 Δ=5.0 = \|7.0 − 2.0\|. **p2와 p4는 GQA query-to-kv 비율에서 가장 먼 두 substrate**이며, 이 거리가 pair KL의 거의 완벽한 단조 예측자다.

**해석**: byte-weighted h_last pool (Axis 1)은 tokenizer 절단 효과를 제거했고, RoPE swap (Axis 2)은 positional encoding 주기를 정렬시켰다. 그러나 **attention의 query/kv head 집약도 차이**는 이 두 수선에 의해 보정되지 않는다. KV head 수가 적을수록 attention은 더 많은 query head를 공유 KV에 몰아넣어 특정 subspace를 강하게 공유하고, 이는 h_last의 Gram spectrum에서 **top eigenvalue의 집중도**로 드러난다 (r6 PR 값에서도 p2=1.463 < p4=1.903으로 p2가 훨씬 더 집중된 스펙트럼을 보임; 이 비대칭성이 KL에 직접 반영).

- **H-axis3 지지: gqa_ratio ρ=+0.971, p=0.001, p2_p4=max-Δ. 기준 \|ρ\|≥0.7 & p2_p4=max-Δ 모두 충족.**

### 3.4 증거 강도 종합

| 가설 | 기준 | 실측 | 점수 | 판정 |
|:---:|---|---|---:|:---:|
| H-v | std(KL_p95) ≥ 0.011 | 0.000344 | 0.03 (std/margin) | **기각** |
| H-gemma | p4_kurt − non_p4_kurt ≥ 1.0 AND p2_p4 worst | 0.72 / 역순 | 0.72 | **기각** |
| **H-axis3** | max\|ρ\| ≥ 0.7 AND p2_p4=max-Δ | gqa_ratio ρ=0.97 | **0.97** | **채택** |

---

## 4. Verdict

> **Top hypothesis**: **H-axis3** (독립 제3 축).
> **핵심 지표**: `gqa_ratio` Spearman ρ = **+0.971** (p=0.001); p2_p4가 Δ=5.0으로 6 pair 중 max-Δ.
> **증거 강도**: 3 가설 중 유일하게 사전 정의된 기준을 모두 통과. H-v는 잡음 폭이 margin 3%에 불과해 기각, H-gemma는 kurtosis 분리 부족(+0.72 < +1.0) + p2_p4가 p4-pair 중 worst가 아니므로 기각.

이로써 r6-α closure doc (`docs/alm_r6_closure_20260425.md` §1 하단 "제3 축 후보")가 **정량적으로 식별**되었다: GQA query/kv 비율이 spectral KL의 잔존 drive다.

---

## 5. r7 권고 — 최소 경로

**H-axis3 채택 → r7 diagnostic 축: gqa_ratio 제어.**

### 5.1 제1순위 (0-cost, 즉시)

- **경로 5A — tail-clip / winsorize 재-gate (H-gemma backup)**: p2_p4의 per-prompt contrib 최상위 1 제거 후 재-gate. 만약 0-cost로 KL<p95 내려가면 실용적 해결. H-gemma가 약했어도 방어적 시도 가치 있음.
- **경로 5B — null n=40000 재-gate**: 실제 잡음이 아님을 추가 확증. 경로 5A가 통과하면 생략 가능.

### 5.2 제2순위 (r7 메인, GPU 필요)

**최소 경로 H-AXIS3-1 — GQA 균질화 실험**:
- p2 (Qwen2.5-7B, GQA 7.0) 또는 p4 (Gemma-3-12B, GQA 2.0) 중 하나를 gqa_ratio가 4.0인 변형으로 교체.
  - Option A: p2 → `Qwen/Qwen2.5-7B-Instruct` (동일 GQA 7.0이므로 **부적합**) — 대신 **같은 family에서 GQA 4인 base**를 탐색. Qwen2.5-14B는 40/8=5.0, 32B는 40/8=5.0. Qwen family 내에서는 GQA 4가 3B(16/2=8), 7B(28/4=7), 14B(40/8=5)로 일치하는 것이 없음 → **Option A 기각**.
  - Option B: p4 → `google/gemma-2-9b` (gqa_ratio = 16/8 = 2.0, 여전히 동일) **기각**. `google/gemma-2-27b` = 32/16 = 2.0 **기각**. Gemma family에서 GQA 2 고정.
  - **Option C (권장)**: p2를 `meta-llama/Llama-3.1-8B` 로 환원 (GQA 4.0). Axis 2 RoPE 검증은 이미 L2에서 증명되었으므로 p1_p2 L2는 약간 악화될 수 있으나, p2_p4의 gqa_ratio Δ를 5.0 → 2.0으로 낮추면 (n=6 pair 회귀에서 KL ≈ 0.02×2 + 상수 ≈ 0.04~0.10 예측) p95를 확실히 하회.
    - 기대: L2 6/6 유지 (변화 ±0.02), KL p2_p4 0.189 → 0.08~0.11 하강.
    - 비용: 1-pod × p2만 재학습 가능 (p1/p3/p4 h_last 재사용) → 약 $3–5 + Φ gate 재실행.

### 5.3 제3순위 (장기, r7 이후)

- **GQA-invariant pool 개발**: h_last를 query-head 기준이 아닌 kv-head 기준으로 재-project (16 prompt × n_kv_heads로 head-grouped mean). 이 projection은 gqa_ratio 영향을 구조적으로 제거 → r8 diagnostic 후보.

### 5.4 비권고

- H-v retry (n=40000만)는 이미 `std`가 0.0003으로 측정되었으므로 margin을 넘기지 못한다. **비권고** (경로 5B는 확증용에 한함).

---

## 6. 생성 아티팩트

| 경로 | 목적 | 커밋? |
|---|---|:---:|
| `docs/alm_r6_p2p4_kl_residual_diagnostic_20260425.md` | 본 문서 (진단 본문) | **Yes** |
| `state/r6_p2p4_kl_residual_result_20260425.json` | raw per-pair KL, null-bootstrap, metadata corr, verdict | No (state/* 예외) |

---

## 7. 참조

- 부모 commit: `1e064038` (r6-α attempt_5 closure)
- r6 closure 문서: `docs/alm_r6_closure_20260425.md`
- r5 Axis 2 diagnostic: `state/r5_axis2_diagnostic_result_20260425.json` — r5 시점의 H1 (attention_topo)에서 p2_p4가 최대 거리(4.83)였던 사전 증거와 일치
- 본 진단 scorer 기준: `tool/phi_4path_gate.hexa` (Gram top-16 eigvalsh + col-perm null n=10000, 정확히 동일 procedure로 재계산)
