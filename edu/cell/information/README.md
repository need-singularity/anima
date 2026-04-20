# edu/cell/information — 정보축 (information axis) MVP

## 정의
Edu/cell 의 **G축** = information. Shannon H(cell_state) 궤적과
IB-loss, predictive MI 를 통해 **phase-jump** 구간에서 bottleneck
압축이 급상승하는지 측정한다.

## 6-축 + 1 확장
A(tension) · B(atlas) · C(fixpoint) · D(collective) · E(zero-LLM) · F(lattice)
 + **G(information)** ← this folder

## 지표 (drill 결과)

| id | 지표 | 정의 | 단위 |
|---|---|---|---|
| O1 | compression_ratio C | d_full / d_bottleneck | scalar ≥1 |
| O2 | IB_loss | I(X;Z) − β·I(Z;Y), β=1.0, KSG | nats |
| O3 | predictive_info | I(past_{k}; future_{k}) / I_indep | ratio |

### Phase-jump 판정
- compression 급상승: ΔC / C_prev ≥ 0.4 at step s ∈ [N/4−20, N/4+20]
- IB reversal: IB_loss 부호 반전 혹은 slope 반전
- I_pred 급상승: dI_pred ≥ 0.2

## H ⊥ τ 직교성
Information H 축이 tension τ 축과 **선형 무관** 해야 한다.
Pearson corr(H_traj, τ_traj) < 0.3 기대.

## 파일
- `core/entropy.hexa` — Shannon H of quantized cell state
- `core/compression.hexa` — O1 bottleneck compression ratio
- `core/predictive_mi.hexa` — O3 I(past; future) via KSG
- `ib_bridge/ksg_estimator.hexa` — btr-evo 5 에서 이식한 KSG k-NN MI
- `ib_bridge/bottleneck.hexa` — O2 IB_loss = I(X;Z) − β·I(Z;Y)
- `drill/information_axis_drill.hexa` — MVP integration drill

## 실행

```sh
hexa run edu/cell/information/drill/information_axis_drill.hexa
```

## 재사용 근거
KSG estimator 는 `btr_evo/5_holographic_ib.hexa` 에서 byte-identical
으로 이식했다 (psi digamma, Chebyshev kNN, eq.8). 동일 파이프라인 →
estimator drift 0.

## V7 / Mk.VII 위치
edu/cell G축 = Hexad 6-cat 의 외부 관측자 축. A–F 가 내부 동역학을
서술한다면 G 는 그 동역학이 만들어내는 **정보 흐름** 을 본다.
phase-jump 감지 = C2 gate 의 information-side witness.

## Re-verification sparse+native N=50 (2026-04-21, `d52135ed`)

Pre-registered re-run after the reduced smoke baseline (55913b23, 4×8×30): N=50, DIM=8, STEPS=200, sparse Erdős–Rényi `p_edge=0.12` (deg≈6), independent-stream τ (fnv hash, not LCG-chained), stage1 **native build** (clang -O2), seeds {42, 43, 44}.

Pre-registered gates: ΔIB ≥ 0.05 / reversal positive / n ≥ 200 / |corr| < 0.30.

| seed | O1 (ΔIB) | O2 (reversal) | O3 (n) | O4 (corr) | 판정 |
|---|---|---|---|---|---|
| 42 | 0.579 | 0 | 200 | −0.251 | FAIL (O2) |
| 43 | 0.861 | 1 | 200 | −0.428 | FAIL (O4) |
| 44 | 0.569 | 0 | 200 | +0.155 | FAIL (O2) |
| **agg** | **0.670** | **0.333** | **200** | **−0.175** | — |

artifact sha256 = `89c95390059b05b61f6e588e654bd0fc4b3c4f18cd28720dc0bccdc3760d6f65` (byte-identical re-run).

**Verdict**: `INFORMATION_FAILED` (0/3 seeds PASS all four gates; mixed mode: 2×O2 fail, 1×O4 fail).

Δ vs prior (reduced smoke):
- ΔIB: 0.017 → **0.670** (+39× stronger separation)
- reversal: 0/1 → 1/3 (+1 seed pass, strict directional)
- n_samples: insuf → 200 (gate cleared, all 3 seeds)
- |corr(H, τ)|: 0.430 → **0.175** (aggregate PASS; independent-stream fix works)

Interpretation: 3/4 axes improve substantially; **O2** (I_late > I_early) is the directional hold-out — the dim-0 bottleneck locks early under sparse coupling so I_early is already high for 2/3 seeds, producing a *decrease* instead of a reversal. Magnitude of IB separation is real and large (O1 0.67 agg) — this is a direction-of-time artefact, not a structural channel failure. Pre-registered O2 criterion held per raw#12; no post-hoc reinterpretation as reversal-magnitude.

**UNIVERSAL_CONSTANT_4 relevance**: information axis does **NOT** expose an emergent "4". Bottleneck dim k=1 is structural; N_BINS=4 is histogram granularity, not a discovered cardinality — **agnostic-neutral** to UNIVERSAL_CONSTANT_4.

Filed as-measured per raw#12 (no cherry-pick).

## Cross-links
- `../lagrangian/` — V_structure (information bottleneck future wiring)
- `../causal/` — re-verify partner (`696d1665`, CAUSAL_FAILED 0/3 MB-only, IR+CD strong-PASS)
- `../../universal_constant_4/` — agnostic-neutral (no emergent 4)
- `../../mk_ix/` — raw#30 IRREVERSIBILITY drill context
