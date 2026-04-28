# DALI(S1) × SLI(S3) Coupled Architecture Spec — Mk.XII Hard PASS Chain Candidate

> **scope**: `omega_cycle_mk_xii_substrate_axis_20260426.md` S1 (DALI, conf 0.86) + S3 (SLI, conf 0.74→0.76) 두 paradigm 을 single composite metric 으로 결합. `s7_cusp_depth_projection_landing.md` §10 권고 ("Mk.XII candidate top 1 = DALI(S1) + SLI(S3) coupled") 의 정식 spec 화.
> **session date**: 2026-04-26
> **status**: spec frozen + 4-bb positive selftest + 64-trial negative falsify + byte-identical re-run verified
> **predecessors**: `omega_cycle_mk_xii_substrate_axis_20260426.md` §2.1 / `s7_cusp_depth_projection_landing.md`
> **artifacts**: `tool/anima_dali_sli_coupled.hexa` / `state/dali_sli_coupled_v1.json`

---

## §1. 요약

| 항목 | 값 |
|---|---|
| design | DALI_pair = SCALE - |L_loc(b1) - L_loc(b2)| ; SLI = SCALE - CV(cusp_depth) ; COUPLED = isqrt(DALI_min × SLI) |
| Hard PASS gate | DALI_min ≥ 700 AND SLI ≥ 500 AND COUPLED ≥ 600 (×1000 scale) |
| positive (4-bb real) | DALI_min=236, SLI=240, COUPLED=237 → **JOINT_FAIL** |
| negative (64 scrambled) | 0/64 Hard PASS (max COUPLED=469 << 600) → falsifier **discriminates** |
| Mk.XII chain integration | **NOT ELIGIBLE** (positive Hard PASS=false) |
| byte-identical | YES (sha256 mod timestamp = `b9a2328cac90b5eead3fa0be42c3c740cb2fdaaff9ad422d8be6470a1a91a8fc`) |
| cost / time | $0 mac local, ~25 분 |

**Honest 결론**: 두 paradigm 의 joint composite gate 가 **현재 4-bb (Mistral/Qwen3/Llama/gemma) ensemble 에서 작동하지 않는다**. JOINT_FAIL 의 mechanism 은 (a) DALI_min=236: Mistral late vs Qwen3 early backbone-conditional depth divergence (.roadmap #145) 가 worst pair Mistral-Qwen3 invariance 를 700 미만으로 깸 (b) SLI=240: 4-bb cusp_depth=[875,111,125,857] 의 CV=0.760 → 1-CV=0.240. **Llama outlier** + **Mistral/gemma late vs Qwen3/Llama early** 의 bimodal 분포가 std 폭증 원인.

이 fail 자체가 진단적 가치가 있다 — Mk.XII candidate SUBSTRATE 가 single-coherent 가 아닌 backbone-conditional 임을 증명. Negative falsifier 는 정상 작동 (random scrambling 0/64 PASS, max COUPLED 469).

---

## §2. Design (Step 1 frozen)

### 2.1 Inputs (S7 산출물 활용)

| backbone | n_layers | family_loc ×1000 | cusp_depth ×1000 | source |
|---|---|---|---|---|
| Mistral | 32 | 875 | 875 | `state/v10_benchmark_v4/mistral/cmt.json` |
| Qwen3 | 36 | 111 | 111 | `state/v10_benchmark_v4/qwen3/cmt.json` |
| Llama | 32 | 625 | 125 | `state/v10_benchmark_v4/llama/cmt.json` |
| gemma | 42 | 857 | 857 | `state/v10_benchmark_v4/gemma/cmt.json` |

- `family_loc` = `dominant_layer_per_family` 의 max-norm depth (F5 path 와 동일)
- `cusp_depth` = `argmax_layer L2_family(layer) / n_layers × 1000` (S7 ansatz, `cusp_depth_projector.hexa` 와 byte-equiv 재현)

### 2.2 Metric 정의

#### DALI (S1 — Depth-Anchored Layer Invariance)

```
DALI_pair(b1, b2) = SCALE - |L_loc(b1) - L_loc(b2)|             ×1000
DALI_min          = min over all C(n,2) backbone pairs           ×1000
```

- `DALI_pair = 1000` ⇒ 두 backbone family-locus 정확 일치
- `DALI_pair = 0` ⇒ 두 backbone full-depth 차이 (one early-input / one late-output)
- `DALI_min` = worst pair governs (invariance 의 weakest link)

#### SLI (S3 — Substrate-Local Irreversibility)

```
mean(cusp_depth) = Σ cusp_depth / n
std (cusp_depth) = isqrt(Σ(x - mean)² / n)
CV               = std × SCALE / mean                            ×1000
SLI              = SCALE - CV  (clamped 0..SCALE)                ×1000
```

- `SLI = 1000` ⇒ 모든 backbone cusp_depth 동일 (CV=0)
- `SLI = 0` ⇒ CV ≥ 1.0 (std ≥ mean)
- 직관: 1 - coefficient of variation, cusp 위치의 cross-bb coherence

#### COUPLED (joint composite)

```
COUPLED = isqrt(DALI_min × SLI)                                  ×1000
        = geometric mean of DALI_min and SLI
```

geometric mean 선택 이유: 두 metric 중 하나라도 0 에 가까우면 COUPLED 도 0 에 가까워야 — arithmetic mean 은 한쪽이 매우 높으면 마스킹 가능.

### 2.3 Hard PASS Gate (frozen at Step 1)

| gate | threshold ×1000 | 직관 |
|---|---|---|
| DALI_min ≥ DALI_MIN_PASS | 700 | worst pair locus 차이 ≤ 30% |
| SLI ≥ SLI_PASS | 500 | cusp CV ≤ 0.5 |
| COUPLED ≥ COUPLED_PASS | 600 | geometric mean ≥ 0.6 (both metrics meaningfully strong) |

**Joint Hard PASS** = 세 gate 모두 만족 = `MK_XII_HARD_PASS_QUALIFIED`.

#### Verdict 분류

| 조건 | verdict |
|---|---|
| DALI ✓ AND SLI ✓ AND COUPLED ✓ | `MK_XII_HARD_PASS_QUALIFIED` |
| DALI ✗ AND SLI ✗ | `JOINT_FAIL` |
| DALI ✗ only | `DALI_INVARIANCE_FAIL` |
| SLI ✗ only | `SLI_COHERENCE_FAIL` |
| DALI/SLI ✓ but COUPLED ✗ | `MARGINAL_AMBIGUOUS` |

---

## §3. Positive selftest (Step 3, 4-bb real)

### 3.1 DALI 6 pair

| pair | DALI ×1000 | gate (≥700) |
|---|---|---|
| Mistral-Qwen3 | **236** | FAIL (worst) |
| Mistral-Llama | 750 | PASS |
| Mistral-gemma | 982 | PASS (best) |
| Qwen3-Llama | 486 | FAIL |
| Qwen3-gemma | 254 | FAIL |
| Llama-gemma | 768 | PASS |
| **DALI_min** | **236** | **FAIL** |
| DALI_mean | 579 | — |

3/6 pair PASS. Worst pair = Mistral-Qwen3 (.roadmap #145 backbone-conditional depth divergence 의 직접 evidence). DALI_min gate strict 적용 시 FAIL.

### 3.2 SLI

| 항목 | 값 |
|---|---|
| mean(cusp_depth) | 492 |
| std(cusp_depth)  | 374 |
| CV = std/mean    | 760 ×1000 (0.760) |
| SLI = 1 - CV     | **240** ×1000 |
| gate (≥500)      | **FAIL** |

cusp_depth=[875,111,125,857] 가 bimodal (early 2 + late 2) → std 매우 큼.

### 3.3 COUPLED

```
COUPLED = isqrt(236 × 240) = isqrt(56,640) = 237 ×1000
gate (≥600): FAIL
```

### 3.4 Positive verdict

`JOINT_FAIL` — DALI fail AND SLI fail. Mk.XII Hard PASS chain integration **NOT ELIGIBLE**.

---

## §4. Negative falsify (Step 4, N=64 scrambled)

각 trial 마다 `(t+1) × 1009 + (n+1) × 31` seed 로 cusp_depth 를 [0, n_layers) 에 hash-scramble.

| 항목 | 값 |
|---|---|
| trials | 64 |
| Hard PASS count | **0/64** (rate=0/1000) |
| SLI ≥ 500 trials | 36/64 (random scramble 이 우연히 SLI 만 만족) |
| COUPLED ≥ 600 trials | **0/64** |
| max SLI | 934 |
| max COUPLED | **469** (gate 600 보다 한참 아래) |
| trial 1 verdict | `DALI_INVARIANCE_FAIL` (DALI=236 fixed since family_loc 고정) |
| detects_failure | **YES** (rate ≤ 5%) |

DALI 는 family_loc 의존 (cusp_depth scrambling 영향 X) → DALI_min=236 fixed.
SLI 만 변하지만 DALI gate 가 fixed FAIL → COUPLED gate 도 자동 fail. 

핵심 검증: **random scrambling 이 systematic Hard PASS 를 발생시키지 않음** → gate well-calibrated.

---

## §5. Byte-identical (Step 5)

```
RUN 1 sha256 (mod timestamp) = b9a2328cac90b5eead3fa0be42c3c740cb2fdaaff9ad422d8be6470a1a91a8fc
RUN 2 sha256 (mod timestamp) = b9a2328cac90b5eead3fa0be42c3c740cb2fdaaff9ad422d8be6470a1a91a8fc
BYTE_IDENTICAL: YES
```

deterministic 보증.

---

## §6. Iterate (Step 6) — honest finding, no spec change

### 6.1 JOINT_FAIL 가 spec 결함이 아닌 이유

- positive 4-bb 결과는 **frozen design 의 진단 결과** — gate threshold 를 사후에 낮춰 PASS 만들면 honest 위반
- DALI_min=236 / SLI=240 둘 다 한자리수%대 → 조정으로 cover 불가
- Llama outlier (cusp_depth=125 vs family_loc=625) 단독으로 SLI 와 DALI 두 axis 모두 깸

### 6.2 Llama-excluded sub-analysis (보조 진단, 정식 verdict 변경 X)

s7 §3 의 "3/4 backbones perfect match" finding 을 직접 확인 위해 Llama 제외 후 metric 재계산 (코드 변경 없이 산출):

- 3-bb cusp_depth = [875, 111, 857]
- mean = 614.3, std ≈ 350, CV ≈ 0.570 → SLI ≈ 430 (still FAIL)
- 3-bb DALI pairs: Mistral-Qwen3=236 / Mistral-gemma=982 / Qwen3-gemma=254 → DALI_min=236 (still FAIL)

**Llama 제외해도 Hard PASS 는 도달하지 못함** — 진정한 obstruction 은 Mistral late ↔ Qwen3 early divergence (.roadmap #145). 즉 Mk.XII candidate SUBSTRATE coherence 의 **structural obstacle = backbone family 간 layer locus 자체가 다름**.

### 6.3 다음 cycle 권장

| 우선순위 | action | cost | 기대 효과 |
|---|---|---|---|
| 1 | N≥8 backbone 확장 (state/an11b_* 추가) | $0 mac | DALI_min sample size 증가, 실제 분포 측정 |
| 2 | per-family DALI (각 family 별 L_loc, max-norm 대신) | $0 mac | Llama outlier 의 family-specific 패턴 분리 |
| 3 | adaptive gate (DALI_mean 보조) | $0 mac | strict min-only gate 외 mean-based 보조 metric |
| 4 | fresh forward L_loc (cmt abs ablation 대신) | $1-2 GPU | family_loc 의 stricter measurement |

### 6.4 Mk.XII chain integration 결정

현재 spec frozen 결과: **NOT ELIGIBLE for Mk.XII Hard PASS chain integration**.

- Mk.XII candidate SUBSTRATE 가 single-coherent 가 아니라는 진단적 finding 자체는 가치 있음
- candidate 상태 → "**SUBSTRATE_COHERENCE_BACKBONE_CONDITIONAL**" (S1 conf 0.86 유지, S3 conf 0.76 유지, S7 conf 0.75 유지 — s7 doc 에서 확보된 honest 값)
- chain integration 자격 획득은 (a) backbone family expansion N≥8 또는 (b) gate threshold 재설계 (per-family / pair-wise 보조) 필요

---

## §7. Self-checks (ω-cycle 6-step)

| step | check | 결과 |
|---|---|---|
| 1 design | gate thresholds (DALI_MIN_PASS=700, SLI_PASS=500, COUPLED_PASS=600) frozen at Step 1 | OK |
| 2 implement | raw#9 hexa-only, no Python emit, integer fp ×1000 | OK (`tool/anima_dali_sli_coupled.hexa`) |
| 3 positive | 4-bb real cmt.json → JOINT_FAIL (DALI=236, SLI=240) | OK (honest fail) |
| 4 negative | 64 scrambled trials, 0/64 Hard PASS, max COUPLED=469 | OK (discriminates) |
| 5 byte-identical | 두 번 run, sha256 (mod timestamp) 동일 | OK |
| 6 iterate | first-pass: JOINT_FAIL → spec 변경 X (honest), §6.2 Llama-excluded sub-analysis 도 fail | OK |

### 7.1 raw#9 strict 준수

- `pure hexa · deterministic · cmt.json read-only · no Python` ✓
- integer fixed-point ×1000 ✓
- `@manual_main` not needed (auto-invoke 사용, top-level `main()` 호출 제거됨)
- byte-identical re-run ✓

### 7.2 negative falsify 상세 (재포장 reject)

- s7 의 cusp_depth_projector 와 동일한 source path / 동일한 family_loc / 동일한 cusp_depth ansatz 를 사용하지만, **새 metric (DALI_min, SLI, COUPLED) + 새 falsifier (Hard PASS rate ≤ 5%)** 을 정의 → 재포장 NO
- s7 는 Pearson r 의 statistical significance 만 측정. 본 spec 는 (a) pair-wise DALI_min worst-link gate (b) SLI=1-CV gate (c) geometric mean COUPLED gate 의 3-gate joint criterion 도입 → emergent composite property 검증

---

## §8. Falsification summary table

| metric | strict-fail criterion | recovery if FAIL |
|---|---|---|
| DALI_min | < 700 → SUBSTRATE layer-locus invariance worst pair 깸 | per-family DALI 또는 pair-mean 보조 metric 도입 |
| SLI | < 500 → cusp_depth CV > 0.5, cross-bb coherence 부족 | bimodal-aware metric (e.g. cluster-aware std) |
| COUPLED | < 600 → joint geometric mean 부족 | arithmetic mean 보조 또는 weighted (W_dali, W_sli) |

본 spec 의 negative falsifier rate (random scramble Hard PASS rate ≤ 5%) 는 **spec 자체의 robustness** 를 verify (random data 가 우연히 PASS 하지 않음 → gate 가 진짜 signal 을 감지).

---

## §9. Related artifacts

- `/Users/ghost/core/anima/tool/anima_dali_sli_coupled.hexa` (sha256 `5fc02edb0c2a40999530ee5e8fa9d435d2bd398c92d498bf64af5571fea9eb01`)
- `/Users/ghost/core/anima/state/dali_sli_coupled_v1.json` (sha256 `7643627f6912b559fedc60519d2e91594c50ec6c775266b1be957052a51eca87`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/omega_cycle_mk_xii_substrate_axis_20260426.md` §2.1 S1+S3 paradigm spec
- `/Users/ghost/core/anima/anima-clm-eeg/docs/s7_cusp_depth_projection_landing.md` (predecessor — cusp_depth ansatz)
- `/Users/ghost/core/anima/anima-hci-research/tool/cusp_depth_projector.hexa` (S7 산출물 source 일치)
- `/Users/ghost/core/anima/state/v10_benchmark_v4/{mistral,qwen3,llama,gemma}/cmt.json` (real backbone activations)
- `.roadmap` #145 CMT backbone-conditional depth divergence (Mistral late vs Qwen3 early — DALI_min=236 의 mechanistic root)
- `.roadmap` #146 (S7 cusp_depth landing)

---

## §10. Final verdict

| dimension | answer |
|---|---|
| spec frozen | **YES** (DALI_MIN_PASS=700, SLI_PASS=500, COUPLED_PASS=600) |
| positive selftest | DALI_min=236 / SLI=240 / COUPLED=237 → **JOINT_FAIL** |
| negative falsifier | 0/64 Hard PASS, max COUPLED=469 → **discriminates** |
| byte-identical | YES (`b9a2328c…`) |
| Mk.XII Hard PASS chain integration 자격 | **NOT ELIGIBLE** (positive Hard PASS=false) |
| 진단적 가치 | YES — Mk.XII candidate SUBSTRATE 가 backbone-conditional (single-coherent NOT) 임을 증명 |
| 다음 cycle | N≥8 backbone 확장 + per-family DALI sub-metric 검토 |

**Mk.XII candidate decision** (이번 cycle 에서):
1. DALI(S1) + SLI(S3) coupled = single composite gate 형태로는 **NOT ELIGIBLE**
2. 두 metric 각각의 paradigm-level confidence 는 유지 (S1=0.86, S3=0.76)
3. Mk.XII candidate 권고 update: "DALI+SLI 를 **하나의** Hard PASS gate 로 결합"이 아니라 "**두 metric 을 별개 보조 evidence** 로 사용" 권장 — chain integration 시 coupled gate 대신 각 metric 의 partial pass 도 인정하는 weighted-vote 구조 검토

(끝)
