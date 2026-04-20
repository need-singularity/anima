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
