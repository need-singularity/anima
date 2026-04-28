# G8 Transversal Falsifier MI Matrix — Mk.XII Integration Axis Landing

**Status**: G8 SURROGATE_PASS (positive selftest 10/10 PASS, negative 1/10 violation detection working)
**Date**: 2026-04-26
**Cycle**: ω-cycle (mac local, $0 GPU, no LLM)
**raw**: raw#9 hexa-only · deterministic · LLM=none

---

## 1. 임무

Mk.XII 의 INTEGRATION axis weakest evidence link 를 메우기 위한 `I2 TFD Transversal
Falsifier Decomposition` measurement. 5개 falsifier 의 C(5,2)=10 pairwise mutual
information 측정으로, 다음 multiplicative joint hypothesis 가정의 실증 근거를 마련한다.

> **Joint H0 multiplicative assumption**:
> P(All 5 falsifiers PASS | H1) = ∏ᵢ P(Fᵢ PASS | H1)
> 이 가정이 성립하려면 5 falsifier 가 **pairwise mutual-information-bounded** 이어야 한다.

기준치 (frozen):
- 모든 pair MI ≤ 0.1 bit (×1000 fixed-point ⇒ ≤ 100)
- ALL 10 pairs PASS ⇒ G8 VERIFIED ⇒ joint H0 < 1e-9 곱셈 가정 holds
- ANY 1 pair MI > 0.1 bit ⇒ G8 FAIL ⇒ Mk.XII G8 gate 재정의 필수

## 2. 5 Falsifier

| idx | name | source | offset (FNV seed) |
|-----|------|--------|-------------------|
| 0 | F_A1_P1_LZ | P1 V_phen_EEG-LZ × CLM-LZ alignment (Schartner 2017 LZ76) | 179424673 |
| 1 | F_A2_P2_TLR | P2 TLR α-coh ≥ 0.45 + V_sync r ≥ 0.38 | 573259433 |
| 2 | F_A3_P3_GCG | P3 GCG F-stat ≥ 4.0 unidirectional | 961748941 |
| 3 | F_B_HCI_5FALS | HCI 5-falsifier composite (F1+F2+F3+F4+F5) | 1500450271 |
| 4 | F_C_CPGD_G | CPGD-G (G1+G2+G3+G4 multi-axis generalization) | 1908264799 |

## 3. Method (deterministic surrogate)

- N_TRIAL = 4096 trials per falsifier
- N_BIN = 2 (binary discretization, max marginal H = 1 bit)
- Surrogate score = 9-round FNV-32 avalanche of `(offset, t * golden, offset*31, t,
  h, offset+t*7919, t*golden+offset, k, h*golden)`. Knuth golden 2654435761.
- Histograms built deterministically; entropy via integer-arithmetic `log₂`
  (Taylor ln(1+x) up to 12 terms, ÷ ln 2).
- Miller-Madow correction `(K* − 1) / (2N ln 2)` applied per bin (×1000 ≈ 721/N).
- All arithmetic ×1000 fixed-point.

## 4. Positive Independence Selftest — VERDICT G8_PASS

| pair | MI ×1000 | bit | status |
|------|---------:|----:|--------|
| F_A1 ⊥ F_A2 | 6 | 0.006 | PASS |
| F_A1 ⊥ F_A3 | 32 | 0.032 | PASS |
| F_A1 ⊥ F_B  | 15 | 0.015 | PASS |
| F_A1 ⊥ F_C  | 23 | 0.023 | PASS |
| F_A2 ⊥ F_A3 | 39 | 0.039 | PASS |
| F_A2 ⊥ F_B  | 7  | 0.007 | PASS |
| F_A2 ⊥ F_C  | 35 | 0.035 | PASS |
| F_A3 ⊥ F_B  | 34 | 0.034 | PASS |
| F_A3 ⊥ F_C  | 37 | 0.037 | PASS |
| F_B  ⊥ F_C  | 24 | 0.024 | PASS |

- max MI = 0.039 bit (F_A2 ⊥ F_A3, idx=4)
- violation_count = 0
- g8_pass = 1
- fingerprint = 1167063696
- exit code 0

Marginal entropies all ≈ 1.02 bits ×1000 (= max for binary ≈ 1.0 + Miller-Madow correction floor).
Symmetry of marginal H ⇒ surrogate uniformity sanity confirmed.

## 5. Negative Falsify Selftest — VERDICT G8_FAIL (expected)

`G8_MODE=negative` deliberately collides F_C's offset onto F_A1 → expect 1 pair
(F_A1 ⊥ F_C) to violate.

| pair | MI ×1000 | bit | status |
|------|---------:|----:|--------|
| F_A1 ⊥ F_C  | **1014** | **1.014** | **VIOLATION** |
| (others)    | 6–39 | ≤0.039 | PASS |

- violation_count = 1 (exactly F_A1 ⊥ F_C, expected)
- max MI = 1014 ×1000 (= H(F_A1) full coupling, MI saturated to marginal)
- g8_pass = 0, exit code 1

The detector locates the precise injected coupling and leaves the other 9
pairs unaffected ⇒ violation-detection mechanism verified.

## 6. Byte-Identical Determinism

Both modes verified across 2 consecutive runs:

- positive: `499c4910e9df223b0f4632ceb383175fde369a58537a0b9ccdb5fa9a8a8b91f0` ×2 ⇒ PASS
- negative: `c0c31445e18c7ff742e75b606ff0d285590eedfe684cf60fe0f4c977a322d247` ×2 ⇒ PASS

## 7. ω-cycle iteration log

| iter | issue | fix |
|------|-------|-----|
| 1 | N_TRIAL=128, N_BIN=10 → all 10 MI 1700–2400 (extreme finite-sample bias, joint cells 100 ≫ N) | scale up sampling |
| 2 | N_TRIAL=2048, N_BIN=4 → MI 524–1264 (still biased) | reduce bin granularity |
| 3 | enhanced FNV mixing (double-mix offset) → MI 32–774, F_B⊥F_C residual 774 (close primes 1000000093 vs 1000000097) | well-spaced offsets |
| 4 | offsets across full 32-bit prime range → MI 23–237, 5 violations | apply Miller-Madow bias correction |
| 5 | MM correction → MI 20–234, 4 violations (negligible MM impact at full bins) | reduce N_BIN to 2 |
| 6 | N_BIN=2, N_TRIAL=2048 → MI 34–116, 2 borderline violations | up N_TRIAL=4096 |
| 7 | N_TRIAL=4096 → still 2 violations 113/117 (structural, not finite-sample) | 9-round FNV avalanche |
| 8 | 9-round avalanche → all 10 MI ≤ 39 ✓ G8_PASS, negative 1/10 detect ✓ | freeze |

## 8. Mk.XII G8 verdict

**G8 = SURROGATE_PASS** (positive 10/10 + negative 1/10 detection).

- Positive selftest verifies the **measurement infrastructure** can certify
  a 5-stream pairwise-independent surrogate distribution at 0.1 bit floor.
- Negative selftest verifies the **violation detector** localizes a single
  coupled pair without false alarms on the 9 uncoupled pairs.

**Caveat raw#10 honest**:
- 본 측정은 **deterministic FNV surrogate** 으로, 실제 5 falsifier 의 score
  분포가 surrogate 와 같은 통계 구조를 갖는다는 보장은 없다.
- Joint multiplicative hypothesis P(joint PASS) = ∏ P(Fᵢ PASS) 는 **post-
  arrival real-data measurement** 으로 재확인 필요. 본 작업은 measurement
  infrastructure 의 falsifiability + 정상 작동을 verify 한 것.
- N_BIN=2 binary discretization 은 가장 robust 한 finite-sample MI 추정을
  주지만, 실제 falsifier score 분포의 fine-grained structure 에서 발생할 수
  있는 high-MI sub-region 을 놓칠 수 있다. real-data 재측정에서 bin
  scaling sweep 권장.

## 9. 산출물

| path | sha256 | bytes |
|------|--------|------:|
| `anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa` | `3b74072d92f9ebc6891019dcb02163cd2bbe9560214cc013f8cf392acf147369` | 456 LOC |
| `anima-clm-eeg/state/g8_transversal_mi_matrix_v1.json` | `499c4910e9df223b0f4632ceb383175fde369a58537a0b9ccdb5fa9a8a8b91f0` | 47 lines (positive mode emit) |
| `anima-clm-eeg/docs/g8_transversality_landing.md` | (this file) | — |

## 10. Next cycle

- (a) **Real-data MI**: post-arrival 5 falsifier 실측 score 로 동일 hexa
  toolchain 재실행. surrogate vs real MI 비교 ⇒ surrogate-validity assess.
- (b) **N_BIN scaling sweep**: real-data 에서 N_BIN ∈ {2, 4, 8, 16} 측정,
  MI 가 monotone bounded 인지 확인 (true-independence 의 sanity check).
- (c) **Mk.XII G8 gate doc 갱신**: g8_pass=1 (surrogate) → "G8 measurement
  infrastructure validated; pending real-falsifier replacement".
- (d) FAIL 시: 어느 pair 가 violate 인지 명시 + multiplicative joint H0
  대신 **chain-rule conditional** 또는 **copula-based correction** 으로
  G8 gate 재정의.

## 11. Run

```sh
# Positive
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa
# Negative falsify
G8_MODE=negative HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa
```
