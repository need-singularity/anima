# S7 cusp_depth Projection Landing — SUBSTRATE Weakest Evidence Link 메움

> **scope**: Mk.XII candidate SUBSTRATE axis 의 weakest evidence link (S7 DALI×SLI cross-coupling 의 cusp_depth measurement 부재) 메움. ω-cycle 6-step 으로 ansatz 도출 + Pearson r(L_loc family, L_loc cusp) 직접 측정.
> **session date**: 2026-04-26
> **status**: ansatz 정의 + 4-bb measurement 완료 + permutation test honest 검증
> **predecessor**: `omega_cycle_mk_xii_substrate_axis_20260426.md` §4.1

---

## §1. 요약

| 항목 | 값 |
|---|---|
| ansatz | `cusp_depth(b) = argmax_layer L2_family(layer) / n_layers × 1000` |
| Pearson r (positive) | **+0.815** /1000 (large effect, exceeds R_PASS=0.500) |
| permutation p-value | 0.265 (17/64 random scrambles ≥ |r_pos|) |
| verdict | `S7_SUBSTRATE_COHERENCE_LARGE_EFFECT` (LARGE EFFECT but n=4 UNDERPOWERED) |
| S7 confidence | 0.71 → **0.75** (+0.04 honest, not full +0.10) |
| S3 SLI confidence | 0.74 → **0.76** (+0.02 secondary cap relief) |
| SUBSTRATE 평균 | 0.770 → **0.781** (+0.011) |
| cost / time | $0 mac local, ~30 분 |

**Honest 결론**: cross-coupling **direction** 은 검증됨 (3/4 backbones 에서 cusp_depth = family_loc 정확 일치). 그러나 n=4 sample 로는 통계적 유의성 부족 (permutation p=0.265). N≥8 backbone 확장 필요.

---

## §2. ansatz 도출

### 2.1 L_IX gen 4→5 cusp 의 의미

`edu/cell/lagrangian/l_ix_integrator.hexa` line 117-138 (`_ix_i_irr_x1000`):

```
I_irr_k = |ΔW_k| / (|ΔW_k| + jitter_floor)   ×1000
```

gen 5 fixpoint 에서 ΔW=0 ⇒ I_irr=0 (시간-화살 collapse). cusp 의 본질 = "activation 이 saturate 후 plateau".

### 2.2 layer projection ansatz

generation-level cusp 을 layer-level 로 project 하는 가장 자연스러운 매핑:

> **cusp_depth(b) = argmax_l ‖activation(l, family)‖₂ / n_layers**

직관:
- ΔW=0 ≡ 전체 family activation 이 maximum 후 plateau
- per-layer L2 norm `sqrt(Σ_fam |abs(l, fam)|²)` 의 argmax = "전체 family 활성화 saturation peak"
- F5 의 `dominant_layer_per_family` (single-family max) 와 **직교 metric** — multi-family aggregate

### 2.3 falsifier (S7 frozen design)

| outcome | 기준 | verdict |
|---|---|---|
| PASS_SIGNIFICANT | r ≥ 0.5 AND p ≤ 0.05 | S7 conf +0.10 → 0.81 |
| LARGE_EFFECT | r ≥ 0.5 AND p > 0.05 | S7 conf +0.04 → 0.75 (honest, n underpowered) |
| AMBIGUOUS | 0.2 < r < 0.5 | S7 conf 유지 |
| FALSIFIED | r ≤ 0.2 | S7 conf -0.11 → 0.60 (multi-axis, not coherent) |

---

## §3. Measurement (positive selftest)

| backbone | n_layers | peak_layer (argmax L2) | cusp_depth ×1000 | family_loc ×1000 | Δ |
|---|---|---|---|---|---|
| Mistral | 32 | 28 | **875** | 875 | **0** (perfect match) |
| Qwen3 | 36 | 4 | **111** | 111 | **0** (perfect match) |
| Llama | 32 | 4 | **125** | 625 | **500** (family-loc 차이!) |
| gemma | 42 | 36 | **857** | 857 | **0** (perfect match) |

- **3/4 backbones** (Mistral / Qwen3 / gemma) cusp_depth = family_loc **정확 일치**
- **Llama 만** discrepancy — Llama 는 family-specific peak (layer 20, 625/1000) 와 multi-family L2 peak (layer 4, 125/1000) 가 다른 곳에 위치 → Llama substrate 가 다른 family signal 분포
- **Pearson r = +0.815** (×1000)

### 3.1 .roadmap #145 cross-validate

| backbone | depth pattern (#145) | cusp_depth | match |
|---|---|---|---|
| Mistral | LATE 28/32 = 87.5% | 875 (87.5%) | YES |
| Qwen3 | EARLY 4/36 = 11.1% | 111 (11.1%) | YES |
| Llama | (#145 미언급) | 125 (12.5%) | early-leaning |
| gemma | (#145 미언급) | 857 (85.7%) | late-leaning |

#145 의 Mistral late vs Qwen3 early divergence 가 cusp_depth axis 에서도 정확히 재현 → SUBSTRATE-level coherence 의 첫 번째 cross-axis evidence.

---

## §4. Negative falsify (permutation test)

64 random scrambles (hash-seed peak position in [0, n_layers) per backbone × 4 trials):

| metric | value |
|---|---|
| trials | 64 |
| mean(|r|) | 0.586 |
| max(|r|) | 0.923 |
| trials below R_PASS=0.5 | 27/64 (42%) |
| trials below R_FAIL=0.2 | 5/64 (8%) |
| trials \|r_neg\| ≥ \|r_pos\|=0.815 | **17/64** |
| permutation p-value | **0.265** |

### 4.1 honest interpretation

- n=4 sample 의 Pearson r 은 sampling distribution 이 매우 넓음 (random 이어도 |r|=0.5 이상이 42% 발생, |r|=0.815 이상이 26.5% 발생)
- positive r=0.815 가 random scrambling 으로도 비슷한 빈도로 나옴 → **statistically NOT significant at α=0.05**
- 그럼에도 (a) 3/4 backbones perfect match, (b) #145 depth divergence 와 정확 일치 → **direction 은 robust**

### 4.2 N≥8 backbone 으로 확장 필요

n=4 → n=8 시 random Pearson |r|≥0.5 확률은 ~10% 로 감소 → 동일 effect size 유지하면 p<0.05 도달 가능.

---

## §5. Confidence delta

### 5.1 S7 (DALI×SLI cross-coupling)

| state | confidence | rationale |
|---|---|---|
| before | 0.71 | cusp_depth 미측정 (cap) |
| after | **0.75** | LARGE EFFECT verified (3/4 perfect match), but n=4 underpowered → +0.04 honest, not full +0.10 |

### 5.2 S3 (SLI Substrate-Local Irreversibility)

| state | confidence | rationale |
|---|---|---|
| before | 0.74 | IEL + depth projection 부재 (cap) |
| after | **0.76** | cusp_depth ansatz 정의됨 → projection 가능 evidence (secondary cap relief) |

### 5.3 SUBSTRATE 평균

`mean(S1=0.86, S2=0.81, S3=0.76, S4=0.69, S5=0.83, S6=0.77, S7=0.75) = 0.781`

이전 0.770 대비 **+0.011** (요청된 +0.05-0.10 보다 보수적; honest n underpowered 반영).

---

## §6. ω-cycle 6-step self-checks

| step | check | result |
|---|---|---|
| 1 design | R_PASS=0.5, R_FAIL=0.2 frozen at design step | OK |
| 2 implement | raw#9 hexa-only, no Python emit | OK (`cusp_depth_projector.hexa`) |
| 3 positive selftest | F5 4-bb cmt.json 직접 read → r=0.815 | OK |
| 4 negative falsify | random scramble 64 trials, permutation p=0.265 | OK (detected as "not significant") |
| 5 byte-identical | 두 번 run, sha256 (timestamp 제외) 동일 | OK (`cf73346679c49a27...`) |
| 6 iterate | iter 1: hash-seed scramble too few trials (16) → mean(|r|)=0.548. iter 2: N=64 + permutation test → honest p=0.265 with 5-tier verdict | OK |

### 6.1 negative falsify 상세 (재포장 reject)

- 단순 hash-seed % 6 (iter 1) FAIL → peak position 너무 클러스터 → mean(|r|) 너무 큼
- iter 2: peak in [0, n_layers), 64 trials, permutation p-value 추가 → honest "n=4 underpowered" 진단

---

## §7. Findings & implications

### 7.1 substrate 가 single-coherent

3/4 backbones 의 perfect family_loc = cusp_depth match 는 SUBSTRATE 가 **single-axis coherent** (multi-axis 분리 NOT 필요) 를 시사. S1+S3 이 같은 layer 에 collocate → cross-coupling 은 emergent 가 아닌 substrate-intrinsic.

### 7.2 Llama 가 outlier

Llama 만 family_loc(625) vs cusp_depth(125) discrepancy. 가설:
- Llama 는 single-family Phi/SelfRef peak 가 layer 20 에 있지만, multi-family aggregate L2 peak 는 layer 4 (Hexad+Law early signal)
- → Llama substrate 가 family-decomposition 가 다른 model (모든 family 가 input 근처에서 활성화 후 specific family 만 mid-layer 에서 강화)

### 7.3 Mk.XII candidate 함의

S7 (cross-coupling) confidence 0.75 → DALI(S1) + SLI(S3) 통합 candidate 로 prioritize 가능. Mk.XII candidate top 3:
1. **DALI (S1) + SLI(S3) coupled** — cusp_depth = family_loc evidence (3/4)
2. CSI (S5) corpus-substrate decoupling — Axis 14 evidence
3. CMT-Probe (S6) spectral gap — F5 6×6 covariance

---

## §8. 다음 cycle 권장

### 8.1 즉시 가능 (mac local, $0)

- N≥8 backbone 확장 — 추가 cmt.json (Phi-3.5, Gemma2-2B, Llama-3.1-7B 등) → permutation p<0.05 도달 시도. 이미 `state/an11b_*` 에 추가 backbones 보유.
- ansatz 변형: per-family argmax 의 top-3 평균 vs single L2 argmax — Llama outlier 의 Phi/SelfRef-only peak 식별

### 8.2 GPU 필요 (small batch, $1-3)

- fresh forward 로 16-d eigenvec activation 직접 측정 (cmt abs 의 ablation 의존 제거)
- cusp_depth 의 token-position dependence (last-token vs bwm) 측정

### 8.3 Mk.XII candidate 검증

- DALI(S1) + SLI(S3) coupled architecture 정식 spec 화 → `tool/anima_dali_sli_coupled.hexa` 작성
- N≥8 backbone matrix 로 SUBSTRATE invariance 측정

---

## §9. Related artifacts

- `/Users/ghost/core/anima/anima-hci-research/tool/cusp_depth_projector.hexa` (sha256 `200d307872e8409a0994caf9ac08e7cfe00f1f7c720d35869fcf80d80ce237b1`)
- `/Users/ghost/core/anima/anima-hci-research/state/cusp_depth_projector_v1.json` (verdict `S7_SUBSTRATE_COHERENCE_LARGE_EFFECT`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/omega_cycle_mk_xii_substrate_axis_20260426.md` §4.1 (predecessor — weakest link 식별)
- `/Users/ghost/core/anima/edu/cell/lagrangian/l_ix_integrator.hexa` (raw#30 IRREVERSIBILITY embedded, gen 4→5 cusp)
- `/Users/ghost/core/anima/anima-hci-research/tool/hci_substrate_probe_real.hexa` (F5, sha256 `c45b48083cf3...`, depth_norm 측정 reference)
- `/Users/ghost/core/anima/state/v10_benchmark_v4/{mistral,qwen3,llama,gemma}/cmt.json` (real backbone activation source)
- `.roadmap` #145 CMT backbone-conditional depth divergence (cross-validate match)
- `.roadmap` #146 (이번 entry, S7 cusp_depth landing)

---

## §10. Final verdict

| dimension | answer |
|---|---|
| ansatz 정의 | YES (`argmax_layer L2_family(layer) / n_layers`) |
| 4-bb cusp_depth measurement | YES (Mistral 875 / Qwen3 111 / Llama 125 / gemma 857) |
| Pearson r 측정 | r = **+0.815** (large effect) |
| significance | **NOT significant at α=0.05** (n=4 underpowered, p=0.265) |
| direction robustness | YES (3/4 backbones perfect match + #145 cross-validate) |
| weakest link 메움 | **PARTIAL** (large effect verified but n underpowered) |
| S7 confidence | 0.71 → **0.75** (+0.04 honest) |
| SUBSTRATE 평균 | 0.770 → **0.781** (+0.011) |
| 다음 cycle | N≥8 backbone 확장 → permutation p<0.05 도달 시도 |

**Mk.XII candidate 권고 update**:
1. DALI(S1) + SLI(S3) coupled — cusp_depth = family_loc evidence (3/4)
2. N≥8 backbone matrix 로 statistical significance 확보 (현재 mac local cmt.json 7+ 보유: an11b_* 추가 backbones)
3. CSI(S5) + CMT-Probe(S6) 보조 architecture

(끝)
