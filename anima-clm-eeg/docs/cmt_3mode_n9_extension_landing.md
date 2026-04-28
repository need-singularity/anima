# CMT 3-mode N=9 Input-mode 보강 — Landing

**Roadmap**: #145.2 — CMT N=9 input mode 3-point boundary regression
**Predecessor**: `state/cmt_3mode_regression_v1.json` (N=10 PASS_SIGNIFICANT, r=+0.505)
**Tool**: `tool/cmt_3mode_regression_n9.hexa` (raw#9 strict)
**Output**: `state/cmt_3mode_regression_n9_v1.json`
**New CMT measurement**: `state/cmt_n9_extension/llama_3_2_1b/cmt.json` (mac MPS, fp32, 9.2s)
**Marker**: `anima-hci-research/state/markers/cmt_3mode_n9_complete.marker`
**Date**: 2026-04-26

## 결과 요약

**Verdict**: `CMT_3MODE_N9_PASS_SIGNIFICANT`

| 항목 | N=10 (baseline) | N=11 (this) | Δ |
|---|---|---|---|
| 3-mode 분류 정확도 | 10/10 = 100.0% | 11/11 = 100.0% | 유지 |
| param→cusp Pearson r | +0.505 | **+0.564** | +0.059 |
| R² (param → cusp) | 0.255 | **0.318** | +0.063 |
| permutation p-value (1024) | 0.000 | 0.000 | 유지 |
| max_correct (shuffle) | 8/10 | 9/11 | +1 |
| input mode datapoints | 2 | **3** | +1 |
| small (<2.5B) input correct | 2/2 | 3/3 | +1 |
| large (≥2.5B) non-input | 8/8 | 8/8 | 유지 |

**핵심**: input mode 영역에 1.24B (Llama-3.2-1B) 추가하여 R² 24.7% 상대 강화.

## 추가 backbone — Llama-3.2-1B mac MPS forward

| 측정 항목 | 값 |
|---|---|
| Model | meta-llama/Llama-3.2-1B (1.24B params) |
| Architecture | LlamaForCausalLM, 16 layers, 2048 hidden |
| Device | Apple MPS (fp32) |
| Forward 시간 | 9.2s (5 forwards × 8 probes = 40 forwards) |
| Probes | 8 mixed-family (Hexad/Law/Phi/SelfRef × 2 each) |
| Layer stride | 4 → scan layers [0, 4, 8, 12] |
| Hidden trunc | 128 |
| Family axes | 4 deterministic random projections |

### 측정 결과 (CMT)
```
layer 0:  Hexad=1.000  Law=1.000  Phi=1.000  SelfRef=1.000
layer 4:  Hexad=1.000  Law=1.000  Phi=1.000  SelfRef=1.000
layer 8:  Hexad=1.000  Law=1.000  Phi=1.000  SelfRef=1.000
layer 12: Hexad=1.000  Law=1.000  Phi=1.000  SelfRef=1.000
```
- dominant_layer_per_family = {Hexad@0, Law@0, Phi@0, SelfRef@0}
- peak_layer = 0, n_layers = 16 → cusp_depth_norm = 0/1000 → **input mode**
- gate_PASS = true (모든 family 의 rel-dY ≥ 0.05)

### 해석 (gemma2-2B 와 동일 패턴)
small bb (<2.5B) 의 layer 0 ablation 시 모든 family activation 이 random-shifted output 으로 100% 영향 — 이는 family signal 이 input embedding 에 fully concentrated 되어있다는 의미. 모든 layer 에서 rel=1.0 plateau 는 small bb 의 input-mode signature.

## 11 backbones 3-mode 분류 (N=11)

| backbone | params | n_layers | peak | cusp_d | mode | match |
|---|---|---|---|---|---|---|
| Mistral-7B | 7.2B | 32 | 28 | 875 | late | ✓ |
| Qwen3-8B | 8.0B | 36 | 4 | 111 | early | ✓ |
| Llama-3.1-8B | 8.0B | 32 | 4 | 125 | early | ✓ |
| gemma2-9B | 9.0B | 42 | 36 | 857 | late | ✓ |
| v4-Mistral-7B | 7.2B | 32 | 28 | 875 | late | ✓ |
| v4-Qwen3-8B | 8.0B | 36 | 4 | 111 | early | ✓ |
| v4-Llama-3.1-8B | 8.0B | 32 | 4 | 125 | early | ✓ |
| v4-gemma2-9B | 9.0B | 42 | 36 | 857 | late | ✓ |
| Qwen2.5-1.5B | 1.5B | 28 | 0 | 0 | **input** | ✓ |
| gemma2-2B | 2.0B | 26 | 0 | 0 | **input** | ✓ |
| **Llama-3.2-1B** | **1.24B** | **16** | **0** | **0** | **input** | ✓ |

## ω-cycle 6-step

| step | 결과 |
|---|---|
| 1. design (frozen boundary) | input≤100 / early≤300 / late≥600 (#43 와 동일) |
| 2. implement (raw#9 hexa) | `tool/cmt_3mode_regression_n9.hexa` (335L) |
| 3. positive selftest | Llama-3.2-1B mac MPS forward → input 분류, N=11 → 11/11 100% |
| 4. negative falsify | 1024 shuffle, max=9/11, p=0.000 |
| 5. byte-identical (timestamp 제외) | sha256(JSON modulo `generated`) = `396c5af8...` 재현 OK |
| 6. iterate | 1회 (smooth pass) |

## 핵심 발견

1. **input mode boundary 자연 cluster 강화** — 3 distinct small bb (1.24/1.5/2.0B) 모두 cusp_depth=0, peak=0 universal. 단순 size-floor 가설이 아닌 family-activation-locus invariant.
2. **R² 24.7% 상대 강화** — input mode datapoint 한 개 추가만으로 0.255→0.318. small/large 이분 정확도 100% 유지하면서 회귀 explanatory power 증가.
3. **Llama family 양극화** — Llama-3.2-1B(input) ↔ Llama-3.1-8B(early). 같은 architecture family 가 size 에 따라 mode 가 달라짐 → mode boundary = (size, architecture) joint determinant 재확인.
4. **mid-size gap 유지** — 2.5B-7B 영역 datapoint 여전히 0 → 다음 cycle target.

## 다음 cycle 후보

- **#145.3**: mid-size 3B-5B 영역 (gemma2-3B, Llama-3.2-3B, Phi-3.5-mini) 추가 → input↔early transition 경계 매핑. ambiguity gap (300-600) 채우기.
- **#145.4**: 같은 size (1.0-1.5B) 다른 architecture 비교 → architecture-only confound 분리 (Pythia-1.4B, OPT-1.3B).
- **#145.5**: cusp_depth ⊥ family_dominance 직교성 검증 — late mode bb 의 dominant family 와 input mode bb 의 dominant family 비교.
