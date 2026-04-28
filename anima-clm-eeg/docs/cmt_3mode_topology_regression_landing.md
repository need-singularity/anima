# CMT 3-mode Topology Regression — Landing

**Roadmap**: #145 follow-up — CMT backbone-conditional depth divergence
**Predecessor**: `anima-hci-research/state/s7_n12_extension_v1.json` (N=10 PASS_SIGNIFICANT)
**Tool**: `tool/cmt_3mode_regression.hexa` (raw#9 strict)
**Output**: `state/cmt_3mode_regression_v1.json`
**Marker**: `anima-hci-research/state/markers/cmt_3mode_regression_complete.marker`
**Date**: 2026-04-26

## 결과 요약

**Verdict**: `CMT_3MODE_REGRESSION_PASS_SIGNIFICANT`

| 항목 | 값 |
|---|---|
| 3-mode 분류 정확도 | 10/10 = 100.0% |
| param_count → cusp_depth Pearson r | +0.505 (×1000) |
| R² (param → cusp) | 0.255 |
| permutation p-value (1024 shuffles) | 0.000 (≤ 0.05) |
| max_correct (shuffle) | 8/10 |
| mean_correct (shuffle) | 3.47/10 |

## 3-mode boundary frozen

| Mode | cusp_depth_norm (×1000) | 해석 |
|---|---|---|
| **input** | ≤ 100 | small backbones (<2.5B), peak ~ layer 0 |
| **early** | (100, 300] | mid backbones (7-8B Qwen/Llama family), peak ~ layer 4 |
| **late** | ≥ 600 | mid+large (Mistral 7B, gemma2 9B), peak ~ 87% depth |
| ambiguous | (300, 600) | 현 데이터에 없음 (gap) |

## 8 backbones 3-mode 분류

| backbone | params | n_layers | peak | cusp_d | mode | match |
|---|---|---|---|---|---|---|
| Mistral-7B | 7.2B | 32 | 28 | 875 | **late** | ✓ |
| Qwen3-8B | 8.0B | 36 | 4 | 111 | **early** | ✓ |
| Llama-3.1-8B | 8.0B | 32 | 4 | 125 | **early** | ✓ |
| gemma2-9B | 9.0B | 42 | 36 | 857 | **late** | ✓ |
| v4-Mistral-7B | 7.2B | 32 | 28 | 875 | **late** | ✓ |
| v4-Qwen3-8B | 8.0B | 36 | 4 | 111 | **early** | ✓ |
| v4-Llama-3.1-8B | 8.0B | 32 | 4 | 125 | **early** | ✓ |
| v4-gemma2-9B | 9.0B | 42 | 36 | 857 | **late** | ✓ |
| Qwen2.5-1.5B | 1.5B | 28 | 0 | 0 | **input** | ✓ |
| gemma2-2B | 2.0B | 26 | 0 | 0 | **input** | ✓ |

## param → cusp 회귀 모델

- Pearson r = +0.505 (moderate positive monotonicity, *not* dominant)
- R² = 0.255 → param_count 단독으로 cusp_depth 분산의 25.5% 설명
- **남은 74.5% 분산** = backbone family/architecture (Mistral 7B vs Qwen3 8B 차이 73 vs 80 가까운 param 인데 cusp 875 vs 111 — param 만으로 구분 불가)

**Sub-threshold scan**:
- small (<2.5B): 2/2 → **input** (peak=0 universal)
- large (≥2.5B): 8/8 → non-input (early|late) — 즉 small/large 이분 100%, large 내부 early/late 는 architecture-dependent

## ω-cycle 6-step

| step | 결과 |
|---|---|
| 1. design (frozen boundary) | input≤100 / early≤300 / late≥600 |
| 2. implement (raw#9 hexa) | `tool/cmt_3mode_regression.hexa` (361L) |
| 3. positive selftest | 10/10 backbone 정확 분류 |
| 4. negative falsify | 1024 shuffle, p=0.000, max 8/10 |
| 5. byte-identical (timestamp 제외) | sha256 = `3062e7fc...` |
| 6. iterate | 1회 (smooth pass) |

## 핵심 발견

1. **param_count 는 약한 predictor** — R²=0.255. small/large 이분만 100% 정확.
2. **3-mode topology 는 architecture-driven** — 비슷한 size 의 Mistral 7B 와 Qwen3 8B 가 정반대 mode (late vs early). family-processing locus 가 backbone fundamentally 다르다는 #145 발견을 회귀로 정량화.
3. **300-600 gap** — 현 8 distinct backbones 어느 것도 mid-depth 영역에 빠지지 않음. 이는 boundary 가 임의가 아닌 자연 cluster.
4. **fresh small bb 는 input mode** — 1.5B/2.0B 양쪽 모두 peak=0. small bb 의 family activation 이 input embedding 에 fully concentrated.

## 다음 cycle 후보

- **#145.2**: 3B-5B 영역 backbone (gemma2-3B, Llama-3.2-3B, Phi-3.5-mini) 추가하여 input↔early transition 경계 (param_b 2-7) 매핑
- **#145.3**: cusp_depth ⊥ family_dominance 직교성 검증 — late mode bb 의 dominant family 가 input mode bb 와 같은지
- **#145.4**: corpus-conditional 3-mode (v10 LoRA r14 corpus 학습 후 mode shift 측정)
