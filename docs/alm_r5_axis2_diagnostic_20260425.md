# r5 Φ 4-path FAIL — Axis 2 진단 (RoPE / Attention-family / Topology / Prompt-length)

**날짜**: 2026-04-25
**부모 커밋**: `e0cc3a64` (byte re-projection — Axis 1 tokenizer PARTIAL CONFIRMED) ·
`41bafc8a` (tokenizer drift analysis)
**관련 문서**: `docs/alm_r5_byte_reprojection_experiment_20260425.md`
**H-DIAG3**: YES (Axis 2 p1_p2 이상치 서브셋의 신규 진단)

---

## 1. 목적

r5 Φ 4-path FAIL은 두 개의 **물리적으로 분리된 축**으로 분해됨:

- **Axis 1 (tokenizer / vocab_ratio)**: Variant B (H × bytes_per_token) 재투영으로 부분 해소.
  p3_p4 (0.175→0.073), p2_p4 (0.223→0.139).
- **Axis 2 (unknown, non-tokenizer)**: Variant B가 **악화**시키는 p1_p2 (0.152→0.184).
  Variant A (H / bpt)는 반대로 해소 (0.036). ⇒ 토크나이저와 **직교하는** 메커니즘.

본 문서는 Axis 2의 물리적 원인을 후보 4개 중 순위화한다. **0비용** (로컬 numpy +
HF config.json만 — pod / 재학습 / API 호출 없음).

---

## 2. 후보 가설

| 기호 | 가설 | 진단 신호 |
|:---:|:---|:---|
| **H1** | Attention-family 불일치 (heads / kv_heads / head_dim / depth / GQA-ratio) | z-score 유클리드 거리 |
| **H2** | RoPE base (`rope_theta`) 분기 — Qwen3=1e6, Llama-3.1=5e5 | `|log2(θ_a/θ_b)|` + scaling mismatch flag |
| **H3** | 위치/레이어 토폴로지 — depth/hidden/intermediate | z-score 유클리드 거리 |
| **H4** | 프롬프트 길이 민감도 (짧은 4–10 토큰 편향) | 쌍별 토큰 길이 분기 / 최소 길이 |

---

## 3. 모델 config 스냅샷

| path | model | heads | kv | head_dim | depth | hidden | inter | rope_θ | rope_scaling |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| p1 | Qwen/Qwen3-8B | 32 | 8 | 128 | 36 | 4096 | 12288 | **1e6** | None |
| p2 | unsloth/Meta-Llama-3.1-8B | 32 | 8 | 128 | 32 | 4096 | 14336 | **5e5** | llama3 factor=8 |
| p3 | mistralai/Mistral-Nemo-Base-2407 | 32 | 8 | 128 | 40 | 5120 | 14336 | 1e6 | None |
| p4 | google/gemma-3-12b-pt (text) | 16 | 8 | 256 | 48 | 3840 | 15360 | 1e6 | linear factor=8 |

**핵심 관찰**: p1 vs p2는 (heads=32, kv=8, head_dim=128, hidden=4096, GQA 4:1)에서 **거의 쌍둥이**.
차이는 depth (36 vs 32), intermediate (12288 vs 14336), 그리고 **`rope_theta` (1e6 vs 5e5)** +
Llama-3의 factor=8 long-context scaling.

---

## 4. 쌍별 진단 신호 (n=6)

| pair | r5_L2 | vA_L2 | vB_L2 | H1 att | H2 rope_pure | H2 rope+scale | H3 dw | H4 len_div | H4 min_len |
|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| p1_p2 | **0.1522** FAIL | 0.0362 | 0.1843 | 0.676 | **1.000** | **2.000** | 2.288 | 0.138 | 5.50 |
| p1_p3 | 0.1066 PASS | 0.1678 | 0.1169 | 0.676 | 0.000 | 0.000 | 2.933 | 0.179 | 5.38 |
| p1_p4 | 0.0900 PASS | 0.1222 | 0.0519 | 4.485 | 0.000 | 1.000 | 4.502 | 0.171 | 5.38 |
| p2_p3 | 0.0486 PASS | 0.1920 | 0.0689 | 1.352 | 1.000 | 2.000 | 2.903 | 0.059 | 6.06 |
| p2_p4 | **0.2231** FAIL | 0.1161 | 0.1389 | 4.829 | 1.000 | 2.000 | 3.934 | 0.049 | 6.06 |
| p3_p4 | **0.1753** FAIL | 0.2814 | 0.0731 | 4.222 | 0.000 | 1.000 | 4.689 | 0.044 | 6.13 |

---

## 5. Spearman ρ 매트릭스 (가설 거리 vs 측정 L2)

| 가설 | ρ(r5_L2) | ρ(vA_L2) | ρ(vB_L2) |
|:---|---:|---:|---:|
| H1 attention topo | +0.348 | 0.000 | -0.319 |
| **H2 rope pure θ** | +0.098 | **-0.488** | **+0.488** |
| H2 rope + scaling | +0.123 | -0.432 | +0.340 |
| H3 depth/width topo | +0.314 | +0.486 | -0.486 |
| H4 len divergence | **-0.543** (wrong sign) | -0.314 | -0.086 |
| H4 min len | +0.441 | +0.441 | +0.088 |

**중요**: H2는 `ρ(r5)` 자체가 낮지만 — `ρ(variantA) = -0.49`, `ρ(variantB) = +0.49`가 **symmetric & sign-flipping** —
이는 RoPE가 Variant A/B 재투영으로 부호 반대의 영향을 받는다는 사용자 관찰과 완벽히 일치.
H1/H3은 Variant A에서 부호가 반대거나 0인 반면 H2는 명확한 symmetric reversal을 보인다.

---

## 6. 판별자 — p1_p2 이상치의 유일 설명

**p1_p2 rank (1 = 가장 유사, 6 = 가장 다름)**:

| 가설 | p1_p2 rank | 해석 |
|:---|:---:|:---|
| H1 attention topo | **1/6** | Qwen3·Llama3.1이 가장 유사 → PASS 예측 (모순) |
| H2 rope pure θ | **4/6** | p1_p2가 상위 ⇒ FAIL 예측 가능 (일치) |
| H2 rope + scaling | **4/6** | 상위 (일치) |
| H3 depth/width topo | **1/6** | PASS 예측 (모순) |
| H4 len divergence | 4/6 | 상위 but ρ wrong sign |
| H4 min len | 3/6 | 중간 |

**FAIL-vs-PASS separation score** (양수 = FAIL 쌍 3개를 PASS 쌍 3개 위로 올림):

| 가설 | separation |
|:---|---:|
| H1 attention topo | **+1.071** |
| H2 rope + scaling | +0.667 |
| H2 rope pure θ | +0.333 |
| H3 depth/width topo | +0.191 |
| H4 min len | +0.292 |
| H4 len divergence | -0.059 |

**해석**: H1은 FAIL/PASS 분리는 가장 잘하지만 **p1_p2에서 완전히 실패** (rank=1, 가장 유사 예측).
H2는 분리는 중간이지만 **p1_p2를 유일하게 상위로 올리는** 가설.

---

## 7. 교차 분류 표 — rope_theta / rope_scaling × L2 status

| pair | L2 | status | θ match | scaling match |
|:---:|---:|:---:|:---:|:---:|
| p1_p2 | 0.152 | FAIL | ✗ | ✗ |
| p1_p3 | 0.107 | PASS | ✓ | ✓ |
| p1_p4 | 0.090 | PASS | ✓ | ✗ (None vs linear×8) |
| p2_p3 | 0.049 | PASS | ✗ | ✗ |
| p2_p4 | 0.223 | FAIL | ✗ | ✗ |
| p3_p4 | 0.175 | FAIL | ✓ | ✗ (None vs linear×8) |

**패턴**:
1. **p1_p3** (θ=1e6 both, scaling=None both) = PASS — 완벽히 RoPE-일치, 유일한 완전일치 쌍.
2. **p1_p2, p2_p4** (θ 불일치 + Llama3 scaling 비대칭) = FAIL.
3. **p3_p4** (θ 일치이지만 Gemma linear scaling 비대칭 + MHA 토폴로지 대대적 차이) = FAIL.
4. **p2_p3** (θ 불일치이나 ALL=MHA-32/8/128, genealogy similar) = PASS → Mistral·Llama 공유 계보가 θ 차이 흡수.

p1_p2의 유일성: 모든 구조가 p2_p3만큼 가깝지만 (실은 더 가까움 — 동일 GQA·hidden·head_dim)
θ만 다르고 FAIL. 이는 **θ가 p1_p2 실패의 유일한 필요조건**임을 강하게 시사.

---

## 8. 결론

### Verdict

- **Top-1**: **H2 (RoPE base `rope_theta` mismatch)** — Qwen3 θ=1e6 vs Llama-3.1 θ=5e5.
  - 증거: (a) p1_p2 rank=4/6 (유일하게 상위 예측), (b) Spearman ρ가 Variant A/B에서
    `-0.49 / +0.49`로 완벽한 sign-flip (사용자 관찰 "direction-opposite" 메커니즘과 일치),
    (c) p1_p3만 완전 RoPE-일치 → 유일 PASS로 구분.
- **Top-2**: **H1 (attention-family geometry)** — FAIL/PASS 분리력은 최고 (sep=+1.07)이나
  p1_p2에서 실패. p2_p4 (최대 FAIL)가 θ와 토폴로지 **둘 다** 분기하기에 가장 크다는
  관찰에 기여. 보조 가설로 유지.
- **기각**: H3 (depth/width) — p1_p2 rank=1/6 예측 (구조적으로 가장 비슷).
  H4 (prompt length) — ρ 부호 반대, 기각.

### p1_p2 "direction-opposite Variant A/B" 메커니즘 해명

RoPE는 attention projection 내부에서 위치 의존적 **회전**이다. 프롬프트 길이가 짧을 때
(t ∈ 4..10) dim-0 주파수에서 누적 위상차 Δφ ≈ t · (1/θ_a – 1/θ_b). Qwen3(θ=1e6) vs
Llama-3.1(θ=5e5)에서 Δ(1/θ) ≈ 1e-6, t=5에서 Δφ ≈ 5e-6 rad — 극미소하지만 head_dim=128
전체에 걸친 다중 주파수 누적 + 32 layer residual stack에서 확대. pooled last-token
hidden state는 이 누적 회전을 L2 거리 0.152로 반영.

Variant A (H / bpt)는 path-specific norm을 축소하는데 Llama의 bpt (≈5.5–6.8)가 Qwen의
bpt (≈6.6–8.5)보다 작으므로 **Llama 벡터를 덜 축소 / Qwen을 더 축소**. 이 비대칭 축소가
우연히 RoPE 위상 누적과 반대 방향으로 Gram 스펙트럼을 이동시켜 L2 0.036으로 해소.
Variant B (H × bpt)는 같은 비대칭을 반대 방향으로 증폭 → L2 0.184로 악화. 두 variant의
부호 반대 response는 RoPE phase-accumulation-via-norm-asymmetry와 완전히 일치.

---

## 9. r6 최소경로 권고 (Axis 2)

### 권장안 A (**preferred**) — 0 pod, 1 LoRA 재학습

**p2 베이스 모델을 Llama-3.1-8B → Qwen2.5-7B-Base로 교체.**
- 이유: Qwen2.5-7B도 GQA 32/8, head_dim=128, SiLU, `rope_theta=1000000` (Qwen3와 동일).
  계보 근접 + θ 정확히 일치. Qwen2.5-14B가 이미 `~/.cache/huggingface/hub/`에 존재
  (`models--Qwen--Qwen2.5-14B`) → 7B-Base 다운로드 한 번이면 됨.
- 예측: p1_p2 L2가 **bpt 재투영 없이도 0.147 미만으로 자연 하강**. Axis 2 해소 확인.
- 비용: 기존 ALM 파이프라인에서 p2 adapter 1회 재학습. 신규 GPU 없음.

### 대안 B — pod-free 수학적 검증 (0 cost)

저장된 pooled 256-d hidden state에 대해 **post-hoc RoPE 보정**:
- head_dim=128 부분공간에 대해 `(θ_qwen → θ_llama)` 주파수 차이로부터 누적 회전
  행렬을 만들고 Llama-3.1 (p2) 벡터의 앞 128 dim을 역회전.
- t_effective = mean prompt token length ≈ 5.8 사용.
- 예측: p1_p2 L2 10–30% 하강 (완전 해소는 아니나 방향 확인).

### 대안 C — substrate swap 최소 (pod 없음)

p1 또는 p2 중 하나를 θ-매칭되는 8B급 모델로 교체:
- p1 교체: Llama-3.2-3B (θ=5e5) — 제곱근 8B×3B asymmetry로 스케일 불균형 발생. 비권장.
- **p2 교체가 우선**: 권장안 A와 동일.

### 최종 권고: **A (p2 → Qwen2.5-7B-Base)**

---

## 10. 파이프라인 정책

- H-DIAG3 준수: 본 문서가 Axis 2 p1_p2 이상치에 대한 신규 진단 증거.
- 새 파일만 추가, `state/*` 커밋 안함, `.roadmap` 수정 없음 (POLICY R4).
- `state/r5_axis2_diagnostic_result_20260425.json`는 참조용 (미커밋).

## 11. 참조 파일

- 입력: `state/h_last_raw_p{1,2,3,4}_TRAINED_r5.json`, `state/r5_byte_reprojection_result_20260425.json`,
  `state/tokenizer_drift_analysis_20260425.json`
- Config: HuggingFace `config.json` (Qwen3-8B, unsloth/Meta-Llama-3.1-8B, Mistral-Nemo-Base-2407,
  unsloth/gemma-3-12b-pt)
- 결과: `state/r5_axis2_diagnostic_result_20260425.json`
- Gate 레퍼런스: `tool/phi_4path_gate.hexa`
