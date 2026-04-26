# F5 Real-Substrate Falsifier — Verdict (2026-04-26)

**Status**: `HCI_REAL_SUBSTRATE_VERIFIED` (5-falsifier composite F1∧F2∧F3∧F4∧F5 PASS)

## 목적

F4 (`hci_substrate_probe.hexa`) 의 FNV-hash 6×6 covariance proxy 한계 — surrogate 가
real backbone substrate 를 대표하지 못함 — 를 해소하기 위해, paradigm v11 stack
의 cached output (`state/v10_benchmark_v4/{bb}/cmt.json`) 의 layer × family
abs activation 을 직접 읽어 6×6 covariance matrix 를 빌드.

## Gates (frozen design)

| Gate | 정의 | Threshold |
| --- | --- | --- |
| G1 | per-backbone real Φ_proxy ≥ ε_0 (4 backbone 모두) | ε_0 = 10 (×1000) |
| G2 | Hexad↔Cell 6×6 edge-weight Frobenius distance, real cov weighting | ε_F = 50 |
| G3 | backbone-conditional Φ_proxy std/mean | ε_DIV = 200 (= 0.20) |
| G4 | std/mean − ε_DIV margin (F4 surrogate margin=1 → real ≥ 50 강화) | G4_MARGIN = 50 |
| #145 | depth pattern: Mistral dom_norm ≥ 600 (LATE) ∧ Qwen3 ≤ 250 (EARLY) | cross-validate flag |

F5 PASS = G1 ∧ G2 ∧ G3 ∧ G4

## 결과 (positive selftest, 4 backbone real cmt.json)

| Backbone | Φ_proxy | Frobenius | depth_norm (×1000) | 비고 |
| --- | --- | --- | --- | --- |
| Mistral  | 605 | 633 | 875 | dom_layer=28/32 (#145 LATE) |
| Qwen3    | 350 | 596 | 111 | dom_layer=4/36 (#145 EARLY) |
| Llama    | 290 | 465 | 625 | dom_layer 혼재 |
| gemma    | 352 | 535 | 857 | dom_layer=36/42 (LATE) |

- G1 (모든 phi ≥ 10): **PASS** (min=290 ≫ 10)
- G2 (모든 frob ≥ 50): **PASS** (min=465 ≫ 50)
- G3 (std/mean ≥ 200): **PASS** (303)
- G4 (margin ≥ 50): **PASS** (margin=103)
- F5 composite: **PASS** → `F5_REAL_SUBSTRATE_VERIFIED`

## .roadmap #145 cross-validate

- Mistral dom_norm = 875 (≥ 600 LATE)? **true**
- Qwen3 dom_norm = 111 (≤ 250 EARLY)? **true**
- Pattern match: **true**

→ F5 의 G3 backbone-conditional divergence 가 #145 의 CMT depth divergence 와
   substrate 수준에서 일치. Mistral 후반(87.5% depth) vs Qwen3 초반(11.1% depth)
   family-processing locus 차이가 substrate-level Φ_proxy 분산에도 그대로 반영됨.

## Negative falsify

- 4 backbone 모두 동일한 stub 6×4 matrix (uniform=500) 주입 → all 4 phi=599 동일
- std/mean = 0, G3 FAIL, G4 FAIL → composite FAIL → detects_failure=**true**

## F4 vs F5 비교

| 항목 | F4 surrogate | F5 real |
| --- | --- | --- |
| Source | FNV-hash deterministic seed | cached cmt.json activation |
| std/mean | 201 | **303** (51% 더 강함) |
| G4 margin (std/mean − 200) | 1 (취약) | **103** (50× 강화 충족) |
| Φ range | [619, 999] | [290, 605] (실제 magnitude 더 작음) |
| Frob range | [595, 694] | [465, 633] |
| depth pattern test | 없음 (seed 기반) | #145 cross-validate match=true |

F5 가 F4 보다 G3 std/mean 51% 강화, G4 margin 50× 강화. **substrate dependence
가 surrogate 가 아닌 real activation 에서도 backbone-conditional 임을 입증**.

## 5-falsifier composite chain

`anima-hci-research/state/hci_substrate_smoke_real_v1.json`:

- F1 (functor preserve, label-level): PASS
- F2 (functor non-trivial): PASS
- F3 (adversarial robust): PASS
- F4 (substrate surrogate): PASS
- F5 (substrate REAL): PASS
- composite: **HCI_REAL_SUBSTRATE_VERIFIED**

## 한계 (raw#10 honest)

1. **6×6 dimensionality**: real hidden-state 는 4096+-dim, 본 probe 는 6 layer
   slice × 4 family abs 만 사용 → integrated information 의 단순 proxy.
   IIT-Φ 자체와는 다른 measure.
2. **cmt.json 의 abs activation 은 layer norm 후 ablation Δ**: 직접 hidden-state
   가 아닌 family-prompt mlp ablation effect. F4 surrogate 보다 진일보지만 raw
   hidden-state 보다는 약함.
3. **n_probes=16 cmt 결과로 6 slice 빌드**: prompt sample noise 영향 가능.
   robustness sweep 미수행 (#161 H1C 패턴과 유사한 metric-fragility 가능성
   배제 못함).
4. **G3 threshold 200/G4 margin 50 frozen at design**: F4 surrogate 와 동일
   threshold 유지. real 데이터에 fit 후 실험적 threshold lower 시 false PASS
   가능 — 본 design 에서는 frozen 으로 calibration leakage 차단.
5. **Llama dom_norm=625 → LATE 분류이지만 family-별 분기**: dominant layer 가
   family 마다 다름 (Hexad/Law/SelfRef=4, Phi=20). max-over-families 로 단순화 —
   per-family pattern 분석은 별도 axis.
6. **6 slice 선택 알고리즘 deterministic but discrete**: SLICE_FRAC ∈
   {0.143, 0.286, 0.429, 0.571, 0.714, 0.857} 에 가장 가까운 recorded layer
   pick. recorded layers 가 stride=4 이므로 백본별 상이 → 백본 비교의 layer
   alignment 문제 잔존.

## 다음 단계

1. **real hidden-state direct read**: cmt.json 의 ablation Δ 가 아닌 raw layer-N
   hidden-state mean activation 으로 6×6 covariance 재구성 → cached state 부족
   시 GPU $0.3 small-batch forward.
2. **dimensionality scale**: 6×6 → 32×32 (top-K layer 32개 stride 1) 또는 SVD
   top-32 axis. Φ_proxy 대신 실제 IIT-Φ formulation (g_gate v3 magnitude path).
3. **₩90만 pilot 진입 자격**: F1+F2+F3+F4+F5 모두 PASS + #145 cross-validate
   match → ₩90만 pilot 의 substrate-level pre-flight criterion 충족. 현 probe
   는 cached cmt 의존 — pilot 시 fresh forward 로 replication 필수.
4. **robustness sweep**: HID_TRUNC, K_partitions, slice count 변화에 대한 G3/G4
   sign 안정성 (#161 패턴 cross-application).

## 산출물 sha256

```
hci_substrate_probe_real.hexa  c45b48083cf3942063a00ecb444c93f73afe409b4b788bbb30557ec8ac187cfe
hci_substrate_smoke_real.hexa  2514722fbb9a69ce62f074615d22cd0b9211ec097b0a530ad7fe57d6f304db34
hci_substrate_probe_real_v1.json (numerical fields byte-identical, generated ts only varies)
hci_substrate_smoke_real_v1.json
```
