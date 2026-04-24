# ALM r5 Procrustes 사후 보정 실험 — Tokenizer 축 0-cost 수리 가능성 판정

> **생성일**: 2026-04-25
> **유형**: H-DIAG3 new-diagnostic-evidence, **retraining 착수 직전 최소 경로(minimum path)** 진단.
> **기반**:
> - `e0cc3a64` (byte-reprojection Variant B → p3_p4/p2_p4 PARTIAL CONFIRMED)
> - `41bafc8a` (tokenizer drift ρ=+0.83 Partially SUPPORTED)
> - `a92fcfe2` (r5 edge-FAIL refutation)
> **로드맵**: #10 Φ 4-path (분석 전용, POLICY R4 uchg — `.roadmap` 미수정).
> **Pod 0 launch** · **0 GPU cost** · **로컬 NumPy only**.

---

## 1. 목적 (Purpose)

r5 Φ 4-path FAIL 의 **두 물리축**(tokenizer vs attention-family) 중 tokenizer 축(p3_p4 0.175 / p2_p4 0.223)이 **재학습 없이** 추론 시점의 단일 선형 보정(orthogonal Procrustes 또는 unconstrained linear head)만으로 PASS(< 0.1471) 로 회복되는가?

본 실험은 r6 로드맵의 분기점이다:

| 판정 | r6 최소 경로 |
|------|-------------|
| **FULL_CONFIRMED** (ortho 만으로 PASS) | serve pipeline 에 `H @ R*` 한 줄 추가, GPU 재학습 전무 |
| **PARTIAL_CONFIRMED** (linear 필요, held-out 성립) | 작은 alignment head (256×256 + bias) 만 재학습, GPU-hr ≪ 1 |
| **REJECTED** | 실제 재학습 필수 — matched-tokenizer 4-path 재구성 |

---

## 2. Method (방법론)

### 2.1 입력

- `state/h_last_raw_p{1,2,3,4}_TRAINED_r5.json` (4 path × 16 prompt × 256-d)
- 비교 기준: `state/phi_4path_cross_result_v3_TRAINED_r5.json` (baseline Φ L2, L2_p95=0.1471)
- 직전 실험 비교: `state/r5_byte_reprojection_result_20260425.json` (Variant B L2)

### 2.2 K-fold cross-validation (k=4)

n=16 prompt 를 k=4 fold 로 분할 → 각 fold 당 12 train / 4 test.
`np.random.default_rng(seed=42)` 로 셔플. 4 fold 전체에 대해 mean±sd 집계.

### 2.3 두 가지 정렬 방법

**Orthogonal Procrustes** (feature 공간에서 직교 회전):
```
R* = argmin_R ‖B - A R‖_F   s.t.  R^T R = I
    closed-form: SVD(A^T B) = U Σ V^T, R* = U V^T
```

**Unconstrained linear** (shear/scale 허용, 비정규):
```
R = pinv(A) @ B
```

양방향(A→B, B→A) 모두 적합. 256-dim feature 이므로 R ∈ ℝ^{256×256}.

### 2.4 평가 축 (4가지 metric)

1. **per-vector L2 (test 4 prompt)**: 각 held-out prompt 에서 `‖h_A R* - h_B‖_2` 평균. 이것이 "post-hoc 적용 시 해당 prompt 의 vector 가 실제로 정렬되는가" 의 직접 지표.
2. **spec_L2 full-16 (Φ scorer 호환)**: 전체 16 prompt 에 transform 을 적용 후 `spec(H_A R*)` 와 `spec(H_B)` 의 L2. r5 Φ gate(L2_p95=0.1471)와 직접 비교 가능한 SSOT metric.
3. **spec_L2 fold-4 (held-out only)**: test 4 prompt 로 구성한 작은 Gram 의 spectrum L2. held-out 일반화의 honest proxy.
4. **spec_KL**: 위와 동형.

### 2.5 Cross-pair generalization

p3_p4 에서 적합한 R\* 를 p2_p4 에 (shared path=p4 경유) 전이. 구체적으로 p4 에 `R*^T` 를 적용해 "p4 공통 보정"이 다른 pair 에서도 유효한지 확인. 반대 방향(p2_p4 → p3_p4) 도 동형 수행.

### 2.6 판정 규칙 (엄밀)

- **FULL_CONFIRMED**: `spec_L2_full16_ortho_mean(p3_p4) < 0.1471` AND `spec_L2_full16_ortho_mean(p2_p4) < 0.1471`.
- **PARTIAL_CONFIRMED**: linear 기반 held-out(`spec_L2_fold_linear_mean`)이 threshold 미만 AND raw 보다 개선 AND cross-pair vec_L2 honest 개선.
- **REJECTED**: 위 둘 다 실패.

---

## 3. 핵심 이론적 고찰 — Gram-invariance 정리

**정리**: `H ∈ ℝ^{n×d}` 에 대해 임의의 직교행렬 `R ∈ ℝ^{d×d}` (`R^T R = I`)에 대하여

```
(H R)(H R)^T = H R R^T H^T = H H^T = G
```

즉 **Gram 행렬이 불변**이고, 따라서 `eigvalsh(G)` 도 불변이며, **Φ scorer 가 내는 spectrum L2 도 그대로**다.

이는 실험 **전에** 이미 다음을 함의한다: **오직 orthogonal Procrustes 만으로는 Φ 4-path L2 를 원리적으로 감소시킬 수 없다**. 실험은 이 이론을 숫자로 재확인하는 동시에, **unconstrained linear** 로만 성공 가능성이 있는지를 다룬다.

---

## 4. 결과 (Results)

### 4.1 per-pair 핵심 표 (4-fold mean)

| pair | baseline L2 | Variant B L2 | ortho full-16 L2 | linear full-16 L2 | **fold raw spec L2** | **fold linear spec L2** | vec L2 raw | vec L2 ortho | vec L2 linear |
|------|-------------|--------------|------------------|-------------------|----------------------|-------------------------|------------|--------------|---------------|
| **p3_p4** | 0.1753 FAIL | 0.0731 ✔ | **0.1753** (동일) | 0.0434±0.015 (overfit) | 0.1057 | **0.1824±0.037** (악화) | 72.78 | 55.33 | 16.71 |
| **p2_p4** | 0.2231 FAIL | 0.1389 ✔ | **0.2231** (동일) | 0.0451±0.012 (overfit) | 0.1034 | **0.1630±0.019** (악화) | 44.04 | 25.62 | 15.94 |
| p1_p3 (control) | 0.1066 PASS | 0.1169 | **0.1066** (동일) | 0.0423±0.018 (overfit) | 0.1016 | 0.1282±0.057 | 70.35 | 57.42 | 39.63 |

**관찰 1 (Gram-invariance 숫자 확인)**: `spec_L2_ortho_full` = `spec_L2_raw_full` 까지 10 자리 일치. 직교 정렬은 Φ gate 에 물리적으로 영향을 줄 수 없음이 숫자로 증명.

**관찰 2 (unconstrained linear = overfit)**: full-16 linear L2 가 놀랍게 0.04 대로 내려가지만, 이는 65,536 파라미터를 12개 샘플에 맞추는 **미결정계(underdetermined)** 의 산술적 결과. **held-out fold 에서 오히려 raw 보다 악화**: p3_p4 0.106→0.182, p2_p4 0.103→0.163. 일반화 0.

**관찰 3 (pointwise vec_L2 의 환상)**: ortho 도 raw 대비 vec L2 를 24~42% 낮추고 linear 는 64~77% 낮춘다. 그러나 이것은 Φ gate 기준이 아니며, 아래 cross-pair 에서 무너진다.

### 4.2 Cross-pair generalization — 과적합의 결정적 증거

| source → target | 공유 경로 | spec L2 raw | spec L2 ortho | spec L2 linear | vec L2 raw | vec L2 ortho | **vec L2 linear** |
|-----------------|----------|-------------|---------------|----------------|------------|--------------|-------------------|
| p3_p4 → p2_p4 | p4 | 0.2231 | 0.2231 | 0.0487 | 44.04 | 42.47 | **77.40 ↑↑** |
| p2_p4 → p3_p4 | p4 | 0.1753 | 0.1753 | 0.0474 | 72.78 | 72.60 | **77.46 ↑** |

linear 는 전역 spec_L2 는 한 pair 에서 fit 한 값이 다른 pair 에도 그대로 적용되어 마치 통과하는 듯 보이지만, **per-prompt vec_L2 는 raw 대비 악화**(44→77, 72→77). 즉 학습된 변환이 "이 substrate 쌍의 구체적 prompt 대응"이 아니라 "통합 Gram 을 같게 만드는 임의 방향"을 찍었다 — 일반화 제로.

### 4.3 표 요약 (판정 가능 여부)

| 지표 | p3_p4 | p2_p4 | threshold 미만? |
|------|-------|-------|-----------------|
| ortho full-16 spec L2 | 0.1753 | 0.2231 | ✘ ✘ (Gram-invariance 로 원리적 불가) |
| linear full-16 spec L2 | 0.0434 | 0.0451 | ✔ ✔ (그러나 overfit — 신뢰 불가) |
| **linear fold held-out spec L2** | **0.1824** | **0.1630** | ✘ ✘ (raw 보다 악화) |
| cross-pair vec_L2 generalization | 77.40 > 44.04 | 77.46 > 72.78 | ✘ ✘ (raw 보다 악화) |

---

## 5. 판정 (Verdict)

### **REJECTED**

근거:
1. **Orthogonal Procrustes 는 이론/숫자 모두 Φ gate L2 를 변화시킬 수 없다** — Gram-invariance (§3).
2. **Unconstrained linear (256×256=65K params / 12 sample)** 는 **미결정계**이며 train-set 에서만 trivially 0 에 가깝게 fit. **Held-out fold 에서 raw 보다 오히려 악화**(p3_p4 0.106→0.182, p2_p4 0.103→0.163).
3. **Cross-pair generalization 실패** — p3_p4 에서 적합한 R\* 를 p2_p4 에 전이하면 per-prompt vec_L2 가 44→77 로 악화. "단일 rotation fits all" 가설 기각.

**r5 에 존재하는 데이터만으로는 post-hoc 선형 보정으로 tokenizer 축을 수리할 수 없다.**

Variant B 의 byte-span rescaling 이 동일한 H 로부터 PASS 를 만든 것과의 차이: Variant B 는 **각 prompt 별 스칼라 `bpt[prompt,path]` 를 row-wise 로 곱해 Gram 자체를 변형**(대각행렬 곱은 Gram-invariance 파괴)했다. Procrustes 의 feature-wise 회전/선형은 그런 per-prompt 정보를 갖지 않는다. 즉 **bpt re-weighting 은 prompt-specific reweighting 이지 feature-space transform 이 아니다** — r6 에서 같은 수준의 회복을 얻으려면 이 per-prompt byte 정보가 re-extraction 을 통해 모델에 주입되어야 한다.

---

## 6. r6 최소 경로 권고 (REJECTED 분기)

### 6.1 우선순위 1 — Matched-tokenizer 4-path 재구성 (실재 재학습 필수)

**왜**: post-hoc 보정이 실패했으므로 tokenizer drift 는 **학습 시점부터 normalize 되어야** 한다.

**두 옵션**:

- **Option A: Gemma 262K 교체** — p4 를 Llama-3.1-8B / Mistral-Nemo / Qwen3-8B 군의 작은 vocab (≤128K) 으로 교체하여 vocab_ratio 를 [1.0, 2.1] 범위로 제한. substrate 다양성 손실 trade-off.
- **Option B: vocab adapter pre-training** — Gemma 262K 를 유지하되 p4 입력 단에 "canonical BPE → Gemma BPE" re-tokenization alignment adapter 를 한글/영문 대규모 corpus 로 사전 학습. substrate 유지, 추가 학습비용.

### 6.2 우선순위 2 — per-prompt byte-weighted h_last_raw 재추출 (0-cost 의존 끊기)

재학습 전 검증 단계로 r6 에서 다음을 수행:
1. r5 가 이미 쓴 4 adapter 로 **per-token hidden state trajectory** 를 재추출(이전엔 last-token pool 만 저장 — 폐기된 정보 복원).
2. Variant B 의 이론적 분석(byte-span 복제 후 byte-평균)을 실제 per-token data 로 구현하여 PASS 달성 확인.
3. 이것이 성공해야 Option B 의 adapter 재학습이 유의미함을 확인할 수 있다.

GPU-hr 비용: 16 prompt × 4 model forward-only inference → 약 0.2 GPU-hr on H100.

### 6.3 p1_p2 attention-axis 진단은 본 실험 범위 밖 (parallel sibling)

본 실험은 tokenizer 축 전용. p1_p2 (attention-family 축) 는 동시간 다른 진단 agent 가 별도 실행 중.

### 6.4 r6 한 줄 요약

> **r6 는 post-hoc 보정을 건너뛰고 matched-tokenizer + per-token byte-weighted h_last_raw 재추출 기반으로 직행하라.** Procrustes/linear alignment 는 12 sample / 65K params 한계로 held-out 에서 무너지므로 재학습 budget 낭비 방지를 위해 이 경로는 폐기한다.

---

## 7. Reproducibility

### 7.1 입력

- `state/h_last_raw_p{1,2,3,4}_TRAINED_r5.json`
- `state/phi_4path_cross_result_v3_TRAINED_r5.json` (baseline 비교)
- `state/r5_byte_reprojection_result_20260425.json` (Variant B 비교)

### 7.2 출력

- raw 결과: `state/r5_procrustes_repair_result_20260425.json` (4-fold per-pair × 2-method × 양방향 전수 + cross-pair; 상태 산출물, 미트래킹)
- 문서: `docs/alm_r5_procrustes_repair_experiment_20260425.md` (이 파일)

### 7.3 seed / 복잡도

- k=4, seed=42 (`np.random.default_rng`). 4 fold × 3 pair × 2 method × 2 dir = 48 fit/eval cycles; 매 cycle 은 256×256 SVD 1회 + pinv 1회. 전체 <1 초 on M-series CPU.
- 재현 스크립트는 repo 내 `*.py` 글로벌 .gitignore 로 제외 (`/tmp/r5_procrustes_repair.py` 로 실행). §2 의 공식만으로 동일 수치 재현 가능.

### 7.4 Φ scorer parity

본 실험의 `spectrum_of(H)` 는 `tool/phi_4path_gate.hexa` 의 구현(L112-L120)과 byte-identical.

---

## 8. 변경 요약 (한 줄)

r5 tokenizer 축 수리의 0-cost 최소경로(orthogonal Procrustes / unconstrained linear)는 **held-out 일반화에서 모두 REJECTED**: 직교회전은 Gram-invariance 로 Φ L2 를 바꿀 수 없고, unconstrained linear 는 12 sample / 65K params 미결정계로 fold-held-out 에서 raw 보다 악화 + cross-pair 일반화 실패. r6 는 matched-tokenizer + per-token byte-weighted 재추출 경로로 직행.
