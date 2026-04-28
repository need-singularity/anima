# S7 cusp_depth N=8 Extension Landing — Permutation p<0.05 시도 결과

> **scope**: `s7_cusp_depth_projection_landing.md` (N=4, p=0.265 underpowered) 확장.
> N=8 (v3+v4 ablation runs × 4 backbones) 로 permutation p<0.05 도달 시도.
> **session date**: 2026-04-26
> **status**: r=0.689 LARGE_EFFECT 유지, p≈0.058 boundary-FAIL (정직 보고)
> **predecessor**: `s7_cusp_depth_projection_landing.md` (N=4, r=0.815, p=0.265)

---

## §1. 요약

| 항목 | N=4 (predecessor) | N=8 (this) |
|---|---|---|
| trials | 4 (real backbones) | 8 (4 backbones × 2 ablation runs) |
| Pearson r ×1000 | +815 | **+689** (LARGE_EFFECT 유지) |
| permutation trials | 64 | 4096 (정밀 estimate) |
| permutation p-value | 0.265 | **0.058** (boundary near-miss) |
| verdict | LARGE_EFFECT | **LARGE_EFFECT** (변동 없음) |
| S7 conf | 0.71 → 0.75 | 0.75 → **0.75** (no change) |
| SUBSTRATE 평균 | 0.770 → 0.781 | 0.781 → **0.781** (no change) |
| cost / time | $0 / ~30분 | $0 / ~25분 |

**Honest 결론**: N=8 확장으로 permutation p 0.265→0.058 크게 개선 (4.6× 향상) 했으나 α=0.05 boundary 0.008 미달. r=0.689 large effect는 robust (3 iter 통해 검증). **S7 conf 변화 없음** — false PASS 만들지 않음.

---

## §2. 8-trial design (frozen at design step 1)

### 2.1 trial 구성

| # | trial | cmt path | n_layers | independence |
|---|---|---|---|---|
| 1 | v3-Mistral | `state/v10_benchmark_v3/mistral/cmt.json` | 32 | distinct backbone |
| 2 | v3-Qwen3 | `state/v10_benchmark_v3/qwen3/cmt.json` | 36 | distinct backbone |
| 3 | v3-Llama | `state/v10_benchmark_v3/llama/cmt.json` | 32 | distinct backbone |
| 4 | v3-gemma | `state/v10_benchmark_v3/gemma/cmt.json` | 42 | distinct backbone |
| 5 | v4-Mistral | `state/v10_benchmark_v4/mistral/cmt.json` | 32 | same bb, distinct ablation run |
| 6 | v4-Qwen3 | `state/v10_benchmark_v4/qwen3/cmt.json` | 36 | same bb, distinct ablation run |
| 7 | v4-Llama | `state/v10_benchmark_v4/llama/cmt.json` | 32 | same bb, distinct ablation run |
| 8 | v4-gemma | `state/v10_benchmark_v4/gemma/cmt.json` | 42 | same bb, distinct ablation run |

### 2.2 honesty caveat

- an11b_*에는 **cmt.json 없음** (alm_*_eigen.json + h_last_raw_*.json 만 보유)
- v10_benchmark v1은 **dominant_layer 모두 0 degenerate** (exclude)
- 결과: **8 distinct trials, 4 distinct backbones × 2 ablation runs (v3+v4) each**
- Effective independence < 8 (4 backbones × 2 runs); 진짜 N≥8 distinct backbones 확보 시 GPU 필요

### 2.3 falsifier (frozen)

| outcome | criteria | verdict |
|---|---|---|
| PASS_SIGNIFICANT | r ≥ 0.500 AND p ≤ 0.050 | S7 conf 0.75 → 0.82 (+0.07) |
| LARGE_EFFECT | r ≥ 0.500 AND p > 0.050 | S7 conf 0.75 (변경 없음) |
| AMBIGUOUS | 0.200 < r < 0.500 | S7 conf 0.75 → 0.70 (-0.05) |
| FALSIFIED | r ≤ 0.200 | S7 conf 0.75 → 0.60 (-0.15) |

---

## §3. Measurement (positive)

| trial | n_layers | peak_layer | cusp_depth ×1000 | family_loc ×1000 | Δ |
|---|---|---|---|---|---|
| v3-Mistral | 32 | 28 | 875 | 875 | 0 |
| v3-Qwen3 | 36 | 4 | 111 | 111 | 0 |
| **v3-Llama** | 32 | 4 | 125 | **875** | 750 (Llama outlier!) |
| v3-gemma | 42 | 36 | 857 | 857 | 0 |
| v4-Mistral | 32 | 28 | 875 | 875 | 0 |
| v4-Qwen3 | 36 | 4 | 111 | 111 | 0 |
| v4-Llama | 32 | 4 | 125 | 625 | 500 |
| v4-gemma | 42 | 36 | 857 | 857 | 0 |

- **6/8 trials** perfect match (cusp_depth = family_loc)
- **Llama 양쪽 ablation 모두 outlier** — v3에서는 fam_loc=875 (layer 28 Hexad), v4에서는 625 (layer 20)
- 두 trial 다 cusp_depth=125 (layer 4 multi-family L2 peak) 로 stable
- **Pearson r = +0.689** (N=4 의 +0.815 대비 -0.126 약화. 주 원인: v3-Llama fam_loc=875 가 cusp_depth=125 와 큰 차이)

### 3.1 N=4 vs N=8 r 변화 분석

| 데이터셋 | sample variance(family_loc) | r |
|---|---|---|
| N=4 (v4 only) | mid | 0.815 |
| N=8 (v3+v4) | mid+v3-Llama outlier 추가 | 0.689 |

v3-Llama fam_loc=875 가 cusp_depth=125 와 거리 750 → 평균 deviation 늘려 r 약화. honest: N 늘리니 effect 추정 더 보수적.

---

## §4. Permutation test (negative falsify)

### 4.1 iter trace

| iter | n_perm | trials_geq_pos | p ×1000 | verdict |
|---|---|---|---|---|
| 1 | 256 | 16 | 62 | LARGE_EFFECT (>50) |
| 2 | 1024 | 52 | 50 (=52/1024=0.0508 round-down) | PASS_SIGNIFICANT (boundary 통과) |
| **3** | **4096** | **239** | **58** (=239/4096=0.0583) | **LARGE_EFFECT** (안정 estimate) |

### 4.2 honest interpretation

- iter 2의 p=50 통과는 **Monte Carlo SE 우연** (1024 sample 의 standard error ~0.007)
- iter 3의 4096 trials 가 progressively 더 정확 (SE ~0.004) → **true p ≈ 0.058**
- **boundary near-miss**: 0.058 vs 0.050 → α=0.05 에서 NOT significant
- iter 1 → iter 3 progression: 0.265 → 0.062 → 0.050 → 0.058 (안정 수렴)

### 4.3 permutation 통계

| metric | value |
|---|---|
| trials | 4096 |
| mean(\|r\|) | 0.323 |
| max(\|r\|) | 0.906 |
| trials \|r\| < R_PASS=0.5 | 3117/4096 (76%) |
| trials \|r\| ≤ R_FAIL=0.2 | 1467/4096 (36%) |
| trials \|r\| ≥ \|r_pos\|=0.689 | 239/4096 (5.8%) |

→ N=8 random Pearson distribution: 76% trials below R_PASS (vs N=4 의 42%) — N 효과 확인됨. but 5.8% 는 0.05 미달.

---

## §5. Confidence delta

### 5.1 S7 (DALI×SLI cross-coupling)

| state | confidence | rationale |
|---|---|---|
| before (N=4) | 0.75 | LARGE_EFFECT, p=0.265 underpowered |
| after (N=8) | **0.75** | LARGE_EFFECT 유지, p=0.058 boundary FAIL → no change |

**No-change rationale**: PASS_SIGNIFICANT criterion 미달 → S7 conf 추가 boost 권리 없음. r=0.689 + 6/8 perfect match 의 robustness 는 N=4 conf 0.75 에 이미 반영됨.

### 5.2 S3 (SLI Substrate-Local Irreversibility)

| state | confidence | rationale |
|---|---|---|
| before (N=4) | 0.76 | cusp_depth ansatz 정의 secondary boost |
| after (N=8) | **0.76** | 동일 (no PASS_SIGNIFICANT) |

### 5.3 SUBSTRATE 평균

`mean(S1=0.86, S2=0.81, S3=0.76, S4=0.69, S5=0.83, S6=0.77, S7=0.75) = 0.781`

→ **변화 없음** (0.781 → 0.781)

---

## §6. ω-cycle 6-step self-checks

| step | check | result |
|---|---|---|
| 1 design | R_PASS=0.5, P_PASS=0.05 frozen at design step (variant of N=4 spec) | OK |
| 2 implement | raw#9 hexa-only, no Python emit | OK (`cusp_depth_projector_n8.hexa`) |
| 3 positive selftest | 8 cmt.json 직접 read → r=0.689 | OK |
| 4 negative falsify | 4096 random scrambles permutation → p=0.058 | OK (boundary FAIL detected) |
| 5 byte-identical | 두 번 run, content sha256 (timestamp 제외) 동일 | OK (`d73d8ddf3c...`) |
| 6 iterate | iter 1 (256 trials)→0.062, iter 2 (1024)→0.0508 boundary, iter 3 (4096)→0.0583 stable | OK |

---

## §7. Findings & implications

### 7.1 Llama outlier 안정 cross-run

v3-Llama 와 v4-Llama 모두 cusp_depth=125 (layer 4 multi-family L2 peak) 로 **identical**. 그러나 family_loc 은 v3=875 (layer 28 Hexad) vs v4=625 (layer 20 Phi/SelfRef) 로 **다름**. Llama 의 single-family dominant peak 는 ablation run 마다 layer 위치 변동 → Llama substrate 가 family-decomposition 가 unstable. 다른 3 backbones 는 cross-run identical.

### 7.2 N 효과: r 약화 + p 강화

- r: 0.815 → 0.689 (-15%)
- p: 0.265 → 0.058 (-78%)
- p 가 r 보다 훨씬 빠르게 개선 = N 늘릴수록 sampling distribution narrows
- 추정: N=12 → p ≈ 0.03 (이론적 추정), N=16 → p ≈ 0.01

### 7.3 effective independence

본 실험의 N=8 은 4 distinct backbones × 2 ablation runs. true independent N 은 ~5-6 효과. 향후 cycle 에서 fresh forward 로 추가 backbone (Phi-3.5, Gemma2-2B, Llama-3.2-3B 등) cmt.json 생성 시 진짜 N≥8 가능.

---

## §8. 다음 cycle 권장

### 8.1 즉시 가능 (mac local, $0)

- ansatz 변형 ablation: cusp_depth 의 alternative 정의 (top-3 family avg, weighted L2) 시도
- v3 / v4 vs (시간 변화) 만으로 unbiased independence 추정 (Mistral 만 trial 2개)
- per-family cusp_depth 분리 (Hexad-only / Law-only / Phi-only / SelfRef-only) → Llama outlier 분해

### 8.2 GPU 필요 (small batch, $1-3)

- 추가 backbone (Phi-3.5, Gemma2-2B, Llama-3.2-3B, Qwen2.5-1.5B) cmt.json 생성 → N=12-16 로 확장 → p<0.05 도달
- Llama 의 ablation-run instability 원인 조사 (다른 3 backbones 는 안정)

### 8.3 framing alternative

- p=0.058 LARGE_EFFECT 를 "marginal evidence at α=0.10" 로 honest 보고
- α=0.10 기준에서는 PASS, but Mk.XII spec 은 α=0.05 frozen 이므로 변경 권장 X

---

## §9. Related artifacts

- `/Users/ghost/core/anima/anima-hci-research/tool/cusp_depth_projector_n8.hexa` (sha256 `c7072e528e890ad1...`)
- `/Users/ghost/core/anima/anima-hci-research/state/cusp_depth_projector_n8_v1.json` (verdict `S7_SUBSTRATE_COHERENCE_LARGE_EFFECT`, p=0.058)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/s7_cusp_depth_projection_landing.md` (predecessor N=4)
- `/Users/ghost/core/anima/anima-hci-research/state/cusp_depth_projector_v1.json` (predecessor N=4 result)
- `/Users/ghost/core/anima/state/v10_benchmark_v3/{mistral,qwen3,llama,gemma}/cmt.json` (4 ablation v3 trials)
- `/Users/ghost/core/anima/state/v10_benchmark_v4/{mistral,qwen3,llama,gemma}/cmt.json` (4 ablation v4 trials)
- `.roadmap` #145 (cross-validate)

---

## §10. Final verdict

| dimension | answer |
|---|---|
| N≥8 확장 | YES (8 trials = 4 bb × 2 ablation runs) |
| Pearson r | **+0.689** (LARGE EFFECT, R_PASS=0.5 통과) |
| permutation p | **0.058** (4096 trials, stable) |
| α=0.05 통과 | **NO** (boundary near-miss, Δ=0.008) |
| α=0.10 통과 | YES (informal marginal) |
| direction robustness | YES (6/8 perfect match across runs) |
| weakest link 메움 | **PARTIAL** (effect robust, significance 미달) |
| S7 conf 변화 | **0.75 → 0.75** (no change) |
| SUBSTRATE 평균 | **0.781 → 0.781** (no change) |
| 다음 cycle | GPU 로 fresh cmt.json 추가 (Phi/Gemma2-2B/Llama-3.2-3B/Qwen2.5-1.5B) → N≥12 |

**Mk.XII candidate update**: S7 (DALI×SLI coupling) 가설 status 미변동.
LARGE_EFFECT 유지하지만 statistical significance 도달 못함.
GPU 추가 backbone 까지 weakest link **PARTIAL CLOSED** 로 간주.

(끝)
