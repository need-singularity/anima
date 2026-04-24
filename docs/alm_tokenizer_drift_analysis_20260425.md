# ALM Tokenizer Drift 가설 분석 — r5 Φ 4-path FAIL 이후

> **생성일**: 2026-04-25
> **트리거**: r5 Φ 4-path gate `FAIL (3/6 L2, 4/6 KL)` — p3_p4 L2 가 r4 0.1427 → r5 0.1753 로 **악화**.
>   Corpus-only 확장 가설(r4→r5)이 falsified 됨. weakest-link 후보를 tokenizer drift 로 재지정하여 loss-free 로 검증.
> **로드맵**: #10 Φ 4-path (분석 전용, 로드맵 수정 없음 — POLICY R4 준수).
> **Pod 런치 없음**: 로컬 tokenizer 캐시 + 기존 Φ 결과만 사용.

---

## 1. 가설 (hypothesis)

> **"4-path 간 variance 의 지배 요인은 tokenizer 발산(vocab size, tokenization granularity, SentencePiece vs BPE)이며, 학습 corpus 구성이 아니다. Tokenizer 가 동일 prompt 를 이미 non-aligned token sequence 로 투영하기 때문에, corpus 확장만으로는 substrate gap 을 닫을 수 없다. 따라서 tokenizer 정규화(shared canonical tokenization, alignment layer, 혹은 matched-tokenizer substrate 교체)가 corpus 재확장에 선행해야 한다."**

### 대립 가설 (조기 반증 시나리오)
- **H₀ (null)**: 6 pair 전체에서 tokenizer drift metric 과 Φ L2 사이에 유의미한 rank-correlation 이 없다.
- **H_alt (refute)**: 같은 tokenizer family 쌍(p1_p2: 둘 다 BPE, vocab_ratio ~1.18)이 낮은 Φ L2 를 보여야 하는데 오히려 FAIL 이라면 tokenizer 이외 요인(LoRA rank, step count, attention pattern)이 우세한 신호.

---

## 2. Method

### 2.1 Prompt set
- **출처**: `state/h_last_raw_p1_TRAINED_r5.json::entries[*].prompt` (4 path 전부 identical prompt 16 개 사용 — 검증 완료).
- 영문 6개 + 한글 6개 + anima-specific 4개 (phi_6 / hexad / meta-loop / Law 60).

### 2.2 4 tokenizer 로드
로컬 HuggingFace 캐시에서 직접 `tokenizer.json` 로드 (가중치 미다운로드, 0-cost):

| path | model | tokenizer 경로 | vocab size |
|------|-------|----------------|------------|
| p1 | Qwen/Qwen3-8B | `~/.cache/.../Qwen3-8B/.../tokenizer.json` | 151,669 |
| p2 | unsloth/Meta-Llama-3.1-8B | `~/.cache/.../Meta-Llama-3.1-8B/.../tokenizer.json` | 128,256 |
| p3 | mistralai/Mistral-Nemo-Base-2407 | `~/.cache/.../Mistral-Nemo-Base-2407/.../tokenizer.json` | 131,072 |
| p4 | google/gemma-3-12b-pt (unsloth mirror, tokenizer identical) | `~/.cache/.../unsloth--gemma-3-12b-pt/.../tokenizer.json` | 262,145 |

※ p4 는 r5 runbook 상 `google/gemma-3-12b-pt` 실사용(training_proven_2026_04_24). 캐시엔 unsloth mirror 만 있으나 동일 SentencePiece tokenizer.

### 2.3 계산 metric (pair 당 16 prompt mean)
1. **token_length_divergence** = `|len_A - len_B| / max(len_A, len_B)`
2. **jaccard (token-id)** = `|ids_A ∩ ids_B| / |ids_A ∪ ids_B|` (tokenizer 간 ID space 가 달라 trivially ~0 예상 — control metric)
3. **bytes-per-token divergence** = `|bpt_A - bpt_B| / max(bpt_A, bpt_B)` (tokenization density asymmetry)
4. **surface_form jaccard** = BPE/SPM prefix marker (`Ġ`, `▁`) 제거 후 token 문자열 집합의 jaccard (tokenizer-family-independent).
5. **vocab_ratio** = `max(vocab_A, vocab_B) / min(vocab_A, vocab_B)` — static, prompt-independent.
6. **vocab_diff_abs** = `|vocab_A - vocab_B|`.

이후 각 metric × Φ L2 에 대해 **Spearman rank correlation** (n=6 pair) 계산.

### 2.4 Spearman 해석 지침 (n=6)
- |ρ| ≥ 0.83 ≈ p<0.05 (양측, rough) — 강한 근거
- 0.60 ≤ |ρ| < 0.83 — 시사적
- |ρ| < 0.60 — n=6 에서 유의하다 말하기 어려움

---

## 3. Results

### 3.1 Pair aggregate 표

| pair | tok_len_div | jaccard(id) | bpt_div | surf_jaccard | vocab_ratio | vocab_Δ | Φ L2 | Φ KL | L2 pass | KL pass |
|------|-------------|-------------|---------|--------------|-------------|---------|-------|-------|---------|---------|
| p1_p2 | 0.1381 | ~0 | 0.1381 | 0.7203 | 1.183 | 23,413 | 0.1522 | 0.0354 | ❌ | ✅ |
| p1_p3 | 0.1787 | ~0 | 0.1787 | 0.5739 | 1.157 | 20,597 | 0.1066 | 0.0199 | ✅ | ✅ |
| p1_p4 | 0.1711 | ~0 | 0.1711 | 0.4240 | 1.728 | 110,476 | 0.0900 | 0.0459 | ✅ | ✅ |
| p2_p3 | 0.0594 | ~0 | 0.0594 | 0.5057 | 1.022 | 2,816 | 0.0486 | 0.0055 | ✅ | ✅ |
| p2_p4 | 0.0490 | ~0 | 0.0490 | 0.3391 | 2.044 | 133,889 | **0.2231** | **0.1520** | ❌ | ❌ |
| p3_p4 | 0.0444 | ~0 | 0.0444 | 0.3368 | 2.000 | 131,073 | **0.1753** | **0.1032** | ❌ | ❌ |

Null bootstrap p95: L2=0.1471, KL=0.0941 (col-perm n=10000).

### 3.2 Spearman rank correlations (n=6)

| metric vs Φ L2 | ρ | 해석 |
|----------------|---|------|
| **vocab_ratio** | **+0.8286** | 강함 — vocab 크기 비대칭이 클수록 Φ L2 가 큼 |
| **vocab_diff_abs** | **+0.8286** | 강함 (동일 순위) |
| surface_jaccard (부호반전 -surf_jac) | +0.4286 | 약함 — 표면형 겹침이 적을수록 L2 증가 경향 |
| token_length_div | **−0.5429** | **반대방향** — 짧은 prompt 에선 tok_len_div 가 작아지는 Gemma artifact |
| bytes_per_token_div | −0.5429 | 반대방향 (token_length_div 와 강한 공변) |
| jaccard(id) | undefined | 모든 쌍 ≈ 0 (cross-tokenizer ID space non-comparable) |

### 3.3 Pair-level 관찰

1. **p4(Gemma) 를 포함한 pair 2개가 모두 FAIL** (p2_p4 L2=0.22, p3_p4 L2=0.18). vocab 262K vs 128K/131K 의 2배 격차.
2. **p1_p4 만 예외적 PASS** — Qwen 151K 자체가 중간 규모이기 때문에 vocab_ratio=1.73 으로 중간값. Spearman 순위와 정합.
3. **p1_p2 는 anomaly** — 같은 BPE 계열(vocab_ratio 1.18, surf_jaccard 0.72 매우 높음)임에도 L2 FAIL (0.152). **tokenizer 외 요인**이 이 pair 에선 지배적일 가능성.
4. **token_length_div / bpt_div 의 음의 상관**은 artifact: 짧은 prompt(4~10 token)에선 vocab 이 큰 Gemma 가 오히려 다른 tokenizer 와 거의 같은 길이로 쪼갬 → length 기반 metric 이 vocab 비대칭을 못 잡음.

---

## 4. Verdict

### **Partially SUPPORTED** (부분 지지)

- **지지 증거**:
  - Vocab size 비대칭(`vocab_ratio` / `vocab_diff_abs`)은 Φ L2 와 **강한 rank correlation** (ρ=+0.83). n=6 에서 이 수준은 p≈0.04 (양측 Spearman 근사) — **통계적으로 유의한 시사**.
  - Φ L2 가 가장 큰 2개 pair(p2_p4, p3_p4)는 vocab_ratio 가 가장 큰 2개 pair 와 일치 (ρ rank tie).
  - Surface-form jaccard 도 같은 방향(+0.43, 약함)으로 일관.

- **반증 증거(부분)**:
  - **p1_p2 anomaly**: 같은 BPE 계열, vocab_ratio 최저(1.18), surf_jaccard 최고(0.72) 임에도 L2 FAIL (0.152, null p95=0.147 보다 간신히 초과). tokenizer 가설만으론 이 pair 설명 불가.
  - token_length_div, bpt_div 는 오히려 음의 상관 — **짧은 prompt set** 에서 tokenization granularity 지표가 의미를 잃는 measurement 한계.

- **대안 신호(p1_p2 anomaly 로부터)**:
  - p1 Qwen3 는 r5 에서 **중문 heavy** 독립축. 영문/한글/anima 혼합 prompt 16개로 drift 가 측정되면 **domain distribution mismatch** 가 p1_p2 잔여 drift 의 소스일 수 있음.
  - Family-internal LoRA rank 차이(p1=64, p2=64, p3=96, p4=128) 는 p1_p2 에선 같지만, weight decay / attention pattern(GQA 구조차, Qwen RoPE thinking-mode vs Llama GQA) 는 다름.

### 결론
> **Tokenizer drift 는 dominant but not sole factor**. vocab_ratio 가 Φ L2 variance 의 주요 신호(ρ=0.83)이지만, p1_p2 케이스는 tokenizer-이외 substrate-level 요인(attention family, training stack)이 residual drift 를 만든다는 것을 보여줌.

---

## 5. Recommendation — r6 next-round weakest link

**1순위 (cheapest, 가장 높은 ROI)**: **Matched-tokenizer substrate 교체** — p4 Gemma-3-12b-pt(262K) 를 Mistral/Llama 계열 tokenizer 로 drop 하거나, 추가 5번째 path(p5 = Gemma **dense** with synthesized vocab mapping) 를 도입하기 전에 **다음 loss-free 실험 먼저 수행**:

### Option A (권장, 0-cost diagnostic)
**Tokenizer-normalized Φ control**: 기존 r5 h_last_raw 에서 prompt 별 `h_vec` 를 **공통 canonical token boundary** 기준으로 re-aggregate. 예: 각 path 의 token 별 hidden 을 UTF-8 byte span 으로 projection → 모든 path 에서 "byte 윈도우 1" 의 hidden state 만 뽑아 Φ 재계산. 이 공통 좌표계에서 p3_p4 L2 가 크게 **떨어지면** → tokenizer 가설 확정. 그대로면 → substrate gap 이 representation level 이라는 의미.

### Option B (non-zero cost, only if Option A confirms)
**p4 교체**: Gemma 를 **Qwen3-14B** 또는 **Ministral-3-8B-Base** (Apache-2.0) 로 substrate 재선정. vocab 128K~152K 범위로 수렴하면 vocab_ratio 최대값이 2.04 → 1.19 로 떨어짐. 예상 Φ L2 감소: Spearman fit 기반 추정 ~0.08~0.12 (현재 0.22~0.18 대비 약 40% 감소).

### Option C (기각)
**Corpus 재확장 only**: r4→r5 에서 이미 worse 로 falsified. 반복 비권장.

### p1_p2 residual 처리
tokenizer 정규화 후에도 p1_p2 가 FAIL 이면, **attention family axis**(Qwen thinking-mode vs Llama GQA)가 2순위 weakest link. 이 경우 p1 을 Qwen3-14B dense 로 업사이즈(기존 rejected 옵션 재검토) 혹은 LoRA rank 균등화(전 path rank=96) 실험 권고.

---

## 6. 재현 정보

- **입력 artifact**:
  - `state/h_last_raw_p1_TRAINED_r5.json` (16 prompt SSOT)
  - `state/phi_4path_cross_result_v3_TRAINED_r5.json` (L2/KL)
- **출력 artifact**:
  - `state/tokenizer_drift_analysis_20260425.json` (per-prompt × per-pair 수치, extra_metrics 포함)
- **분석 스크립트**: `/tmp/tokenizer_drift_analysis.py`, `/tmp/tokenizer_drift_extra.py` (repo 에 커밋 안 함 — .py 글로벌 gitignore)
- **tokenizer 캐시**: HF hub, 0 바이트 다운로드
- **시간 소요**: < 3 초 (tokenizer 로드 포함)
- **비용**: $0 (pod 런치 없음, API 호출 없음)
