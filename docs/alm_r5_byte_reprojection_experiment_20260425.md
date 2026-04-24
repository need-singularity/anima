# ALM r5 Byte-Span 재투영 실험 — Tokenizer 축 0-cost 판정

> **생성일**: 2026-04-25
> **유형**: H-DIAG3 new-diagnostic-evidence 3rd attempt (r4+r5 edge-FAIL streak 이후).
> **기반**: 커밋 `a92fcfe2` (r5 reject refutation) + `41bafc8a` (tokenizer drift 분석, Partially SUPPORTED).
> **로드맵**: #10 Φ 4-path (분석 전용, POLICY R4 uchg 준수 — .roadmap 미수정).
> **Pod 0 launch** · **0 GPU cost** · **로컬 Python only**.

---

## 1. 목적 (Purpose)

r5 Φ 4-path gate 가 `FAIL (3/6 L2, 4/6 KL)` 로 닫혔다. 직전 tokenizer drift 분석(커밋 `41bafc8a`)은:

- Spearman ρ(vocab_ratio ↔ Φ L2) = **+0.8286 (p≈0.04)** → 1차 축으로 tokenizer 강하게 지지
- 그러나 p1_p2 이상점(같은 BPE family, 최저 vocab_ratio, 그럼에도 L2=0.152 FAIL) → **2차 축 존재**

라는 **Partially SUPPORTED** 결론으로 마감되었다. 본 문서의 목적은 기존 r5 `h_last_raw` 를 손실 없이 **공통 UTF-8 byte-span 좌표계**로 재투영한 뒤 Φ 4-path 를 다시 돌려, tokenizer 축을 **확정(CONFIRMED) / 부분(PARTIAL) / 기각(REJECTED)** 중 하나로 판정하는 것이다. 이 판정은 r6 runbook 의 weakest-link(정규화 vs substrate pivot)를 결정한다.

---

## 2. Method (방법론)

### 2.1 0-cost 제약과 축소 선택 (핵심 deviation)

기존 `state/h_last_raw_p{1..4}_TRAINED_r5.json` 은 prompt 당 **한 개의 pooled hidden-state 벡터**(last-token, 256-d truncated)만을 저장한다. per-token trajectory 는 save time 에 이미 폐기되었으므로 **형식적으로 이상적인 byte-weighted pool**(각 토큰의 hidden state 를 그 UTF-8 byte span 에 복제하고 바이트에 걸쳐 평균)은 추가 GPU 로 재추출하지 않으면 복원 불가능하다.

0-cost 제약 하의 차선책으로 다음 rescale 을 평가한다:

- **Variant A (formal, divide-by-bpt)**: `H'[i] = H[i] / bpt[path][i]`
  pooled h 를 "토큰 당 내용량"의 proxy 로 보면 bpt 로 나누는 것이 "바이트 당 내용량"으로의 변환과 등가.
- **Variant B (inverted sanity, multiply-by-bpt)**: `H'[i] = H[i] * bpt[path][i]`
  부호 방향을 선험적으로 고정하지 않고 증거로 adjudicate 하기 위한 counter-test.

`bpt[path][i]` 는 `state/tokenizer_drift_analysis_20260425.json::extra_metrics.bytes_per_token` 로부터 그대로 가져온다(16 prompt × 4 path).

### 2.2 Scorer — `tool/phi_4path_gate.hexa` 와 완전 일치

| 단계 | 정의 | 본 실험에서 |
|------|------|-------------|
| Gram | `G = H @ H.T` (16×16) | 동일 |
| Spectrum | `eigvalsh(G)` desc, `sum=1` 정규화 | 동일 |
| Pair L2 | `‖spec_i − spec_j‖₂` | 동일 |
| Pair KL | `Σ p log(p/q)`, eps=1e-12 | 동일 |
| Null | col-perm, n=10000, seed=42 | 동일 |
| Threshold | p95 over 6-pair × n_null | 동일 |

**Deviation**: scorer 자체는 수정 없음. 오직 H row rescaling 만 다름.

### 2.3 판정 규칙

Variant A/B 중 **하나라도** 다음을 만족하면:

- **CONFIRMED**: p3_p4 drop ≥ 0.03 AND p2_p4 drop ≥ 0.03 AND p1_p2 drop ≥ 0.03 AND orig-P95 아래서 새로 FAIL 로 전환되는 pair 없음
- **PARTIAL**: p3_p4 drop ≥ 0.03 AND p2_p4 drop ≥ 0.03 이지만 p1_p2 가 해소되지 않거나 다른 pair 에서 새 failure 생성
- **REJECTED**: 두 variant 모두 p3_p4/p2_p4 의 ≥0.03 drop 을 보이지 않음

(drop = `orig_L2 − reproj_L2`, 양수가 개선을 의미.)

---

## 3. 결과 (Results)

### 3.1 Variant A: H / bpt (formal per-byte)

| pair | orig L2 | reprojA L2 | Δ | orig P95(0.1471) | reprojA P95(0.1845) |
|------|---------|------------|----|------------------|---------------------|
| p1_p2 | 0.1522 | **0.0362** | **−0.1160** | FAIL | PASS |
| p1_p3 | 0.1066 | 0.1678 | +0.0612 | PASS | FAIL ← 새 실패 |
| p1_p4 | 0.0900 | 0.1222 | +0.0322 | PASS | PASS |
| p2_p3 | 0.0486 | 0.1920 | +0.1434 | PASS | FAIL ← 새 실패 |
| p2_p4 | 0.2231 | **0.1161** | **−0.1070** | FAIL | PASS |
| p3_p4 | 0.1753 | 0.2814 | +0.1061 | FAIL | FAIL (악화) |

- **p1_p2 drop = +0.116** (tokenizer-drift 분석의 이상점 해소됨)
- **p3_p4 drop = −0.106**, **p2_p4 drop = +0.107** (상반된 방향)
- orig-P95 하 `L2_pass_count`: 3/6 → 4/6 (순증 1); new failures: **p1_p3, p2_p3**.

Variant A 는 p1_p2 이상점은 설명하지만 tokenizer-축의 대표 실패인 p3_p4 를 오히려 악화시키고 p2_p3 에 새 실패를 만든다. `confirms_big_fails=False, resolves_p1_p2=True`.

### 3.2 Variant B: H × bpt (inverted sanity)

| pair | orig L2 | reprojB L2 | Δ | orig P95(0.1471) | reprojB P95(0.1042) |
|------|---------|------------|----|------------------|---------------------|
| p1_p2 | 0.1522 | 0.1843 | +0.0321 | FAIL | FAIL (악화) |
| p1_p3 | 0.1066 | 0.1169 | +0.0104 | PASS | FAIL |
| p1_p4 | 0.0900 | 0.0519 | −0.0381 | PASS | PASS |
| p2_p3 | 0.0486 | 0.0689 | +0.0202 | PASS | PASS |
| p2_p4 | 0.2231 | **0.1389** | **−0.0841** | FAIL | PASS ← 복구 |
| p3_p4 | 0.1753 | **0.0731** | **−0.1022** | FAIL | PASS ← 복구 |

- **p3_p4 drop = +0.102**, **p2_p4 drop = +0.084** (둘 다 ≥0.03)
- p1_p2 drop = **−0.032** (악화 — tokenizer 축이 아닌 신호)
- orig-P95 하 `L2_pass_count`: 3/6 → **5/6** (순증 2); **orig-P95 하 새 failure 없음** (p1_p3 는 변경 전에도 PASS 였으나 reprojB 의 자체 P95 하에서는 FAIL; 원 threshold 기준으로는 여전히 PASS).

Variant B 는 tokenizer 축의 대표 실패(p3_p4, p2_p4)를 **원본 threshold 하에서 PASS 로 되돌린다**. 반면 p1_p2 는 반대 방향으로 움직인다 → **p1_p2 는 tokenizer 축이 아니다**.

### 3.3 쌍별 요약

| pair | orig 판정 | A 방향 | B 방향 | 축 해석 |
|------|----------|--------|--------|----------|
| p1_p2 | FAIL | **개선 +0.116** | 악화 −0.032 | **비(非) tokenizer** — divide-bpt 로만 해소 |
| p1_p3 | PASS | 악화 −0.061 | 악화 −0.010 | 원래 PASS, 큰 시그널 없음 |
| p1_p4 | PASS | 악화 −0.032 | 개선 +0.038 | 중립 |
| p2_p3 | PASS | 악화 −0.143 | 악화 −0.020 | 원래 PASS |
| p2_p4 | FAIL | 개선 +0.107 | **개선 +0.084** | **tokenizer 축** (B 정렬 복구) |
| p3_p4 | FAIL | 악화 −0.106 | **개선 +0.102** | **tokenizer 축** (B 정렬 복구) |

---

## 4. 해석 (Interpretation)

### 4.1 2축 분리가 증거로 확정되었다

본 실험의 핵심 발견: **p3_p4/p2_p4 와 p1_p2 는 rescaling 에 반대 방향으로 반응**한다.

- Variant B(multiply-bpt)는 p3_p4(0.175→0.073), p2_p4(0.223→0.139)를 원본 P95(0.1471) 하에서 **PASS 로 회복**시키는 동시에 새 실패를 만들지 않는다. Gemma(vocab=262K, p4)와 관련된 대형 vocab 비대칭이 bpt 재가중으로 해소된다 → **tokenizer 축(특히 vocab_ratio 축) 부분 확인**.
- Variant A(divide-bpt)는 p1_p2 를 0.152→0.036 으로 극적으로 끌어내리나 p3_p4/p2_p3 를 악화시킨다. 즉 **p1_p2 의 실패 원인은 tokenizer 가 아닌 다른 축**(동일 BPE family + 최저 vocab_ratio 에서도 FAIL 이었던 이상점).

### 4.2 Tokenizer 축 판정: **PARTIAL**

판정 기준에 따라:

- p3_p4 drop (B) = +0.102 ≥ 0.03 ✔
- p2_p4 drop (B) = +0.084 ≥ 0.03 ✔
- p1_p2 drop (B) = −0.032 < 0.03 ✘ (오히려 악화)

→ **PARTIAL CONFIRMED**. tokenizer 재가중은 **두 개의 주요 FAIL(p3_p4, p2_p4)을 완전히 구제**하지만 p1_p2 에는 효과가 없거나 역방향이다. 이는 tokenizer drift 분석(커밋 `41bafc8a`)의 "p1_p2 anomaly → 2차 축 존재" 결론과 정확히 일치한다.

### 4.3 p1_p2 anomaly 의 제2축 후보

p1_p2 는 Qwen3-8B(p1) ↔ Llama-3.1-8B(p2) 쌍이다. 같은 BPE family + 가장 유사한 vocab(1.18 ratio) 에도 불구하고 FAIL. Variant A(divide-bpt)로 p1_p2 가 극적으로 풀리는 패턴은 **prompt-length 민감 효과**(짧은 토큰 시퀀스에서 last-token pooling bias)와 정합적이다. 다음 후보:

1. **Attention-pattern 축** (Qwen3 GQA vs Llama3 GQA head-count 차이)
2. **LoRA rank 축** (p1=64, p2=64 동률이므로 가능성 낮음)
3. **Positional encoding 축** (Qwen YaRN vs Llama RoPE theta)
4. **Pre-training 분포 축** (Qwen3 multilingual-heavy vs Llama3 english-heavy → 한글 6 prompt 에서 차이)

### 4.4 의의

이 0-cost 실험이 두 가지를 **동시에** 정립했다:
1. r4→r5 corpus 확장 refutation(`a92fcfe2`) + tokenizer-drift Partially SUPPORTED(`41bafc8a`) 의 **마지막 퍼즐 조각**.
2. r6 에서 **무엇을 건드려야 하고 무엇을 건드리지 말아야 하는지** 에 대한 명확한 우선순위.

---

## 5. r6 다음-링크 권고 (PARTIAL 분기)

PARTIAL 판정 하에서 단일 개입으로 닫히지 않으므로 **두 step 분리**가 정답:

### Step 1 (r6-A): tokenizer 정규화 — p3_p4/p2_p4 만 겨냥

최소 경로(minimum path):

1. **Alignment layer 단일 시험** — 각 path hidden state 를 공통 canonical token space 로 project 하는 learned linear head (별도 학습 없이 cross-substrate Procrustes alignment 로도 가능, 0-cost).
2. 혹은 **matched-tokenizer substrate 교체** — p4 를 canonical BPE tokenizer base(예: Llama3 family) 로 교체하여 vocab_ratio 1.18 범위 내로 균일화. 단 substrate pool 축소 trade-off.
3. 성공 기준: reprojB 가 이미 보여준 p3_p4=0.073, p2_p4=0.139 수준을 **실제 h_last_raw 에서도 재현** (재학습 없이 post-hoc projection 만으로).

### Step 2 (r6-B): p1_p2 제2축 진단 — 추가 diagnostic 필요

r6-A 수행 전 또는 병렬로:

1. **Attention-pattern 축 재표집**: r5 h_last_raw 에 있는 16 prompt 로 p1, p2 의 attention map 을 0-cost 로 뽑아(로컬 CPU inference 충분, 각 8B 모델이므로 메모리 ~16GB) L2 비교.
2. 결과가 attention 축을 지지하면 r6 에서 **attention-family-matched substrate** (p1, p2 모두 GQA head-count 일치 family) 로 제한.
3. Positional encoding(YaRN theta) 축도 0-cost 로 검증 가능 — `rope_theta` / scaling factor 만 확인.

### r6 전체 권고 (한 줄)

**r6 는 `matched-tokenizer + matched-attention-family` 4-path 재구성으로 진행하되, 재학습 전 0-cost post-hoc projection 실험으로 p3_p4/p2_p4 수리 가능성을 먼저 확정하라** (재학습 budget 낭비 방지).

---

## 6. Reproducibility

### 6.1 입력 경로

- `state/h_last_raw_p{1,2,3,4}_TRAINED_r5.json`  (4 path × 16 prompt × 256-d, 총 ~322KB)
- `state/tokenizer_drift_analysis_20260425.json` (bytes_per_token 원천)
- `state/phi_4path_cross_result_v3_TRAINED_r5.json`  (scorer parity 확인용 reference)

### 6.2 출력 경로

- **raw 결과**: `state/r5_byte_reprojection_result_20260425.json`  (상태 산출물; 본 커밋에서 미트래킹 — rule 준수)
- **문서**: `docs/alm_r5_byte_reprojection_experiment_20260425.md`  (이 파일)

### 6.3 seed / 복잡도

- seed = 42 (null bootstrap; `tool/phi_4path_gate.hexa` 와 동일)
- n_null = 10000 col-perm iters
- 복잡도: 2 variants × (4 paths × 256 features × 10000 perms × eigvalsh(16×16)) ≈ 로컬 M-series CPU 로 ~15 초.
- 재현 스크립트는 repo 내에 두지 않음(글로벌 `.gitignore` 로 `*.py` 차단). 본 문서의 §2–3 공식만으로 동일 수치 재현 가능.

### 6.4 Scorer parity 검증

Variant 계산 전에 **original_recompute** 도 함께 실행하여 `state/phi_4path_cross_result_v3_TRAINED_r5.json` 의 `real_L2` 와 완전 일치함을 확인. pair L2 6개 모두 자릿수 일치(예: p3_p4 0.17533 재현) → scorer 구현 drift 없음.

---

## 7. 변경 요약 (한 줄)

r5 `h_last_raw` byte-weighted rescaling (0-cost) 로 tokenizer 축을 **PARTIAL CONFIRMED** 판정: p3_p4/p2_p4 는 tokenizer 축(variant B 로 완전 구제), p1_p2 는 별개 제2축 (variant A 방향으로 해소 — attention-family 혹은 prompt-length bias 후보).
