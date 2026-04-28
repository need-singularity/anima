# G8 Transversality N_BIN Scaling Sweep — Mk.XII Integration Axis Landing

**Status**: G8_STABLE (positive 4 levels × 10 pairs = 40/40 PASS, negative 4/40 detection working)
**Date**: 2026-04-26
**Cycle**: ω-cycle (mac local, $0 GPU, no LLM)
**raw**: raw#9 hexa-only · deterministic · LLM=none
**Depends on**: `anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa` (frozen N_BIN=2 SSOT)

---

## 1. 임무

기존 G8 transversality measurement (`g8_transversal_mi_matrix.hexa`) 가 N_BIN=2
binary discretization 으로 frozen 되어 있었음. landing doc(line 122–125) 의
raw#10 honest caveat:

> N_BIN=2 binary discretization 은 가장 robust 한 finite-sample MI 추정을
> 주지만, 실제 falsifier score 분포의 fine-grained structure 에서 발생할 수
> 있는 high-MI sub-region 을 놓칠 수 있다. real-data 재측정에서 bin
> scaling sweep 권장.

본 sweep 은 동일 5-falsifier surrogate 위에서 N_BIN ∈ {2, 4, 8, 16} 4 level 을
순회하며 매 level 의 pairwise MI 를 재측정한다. 모든 level 에서 G8 PASS criterion
(MI ≤ 0.1 bit, ×1000 ≤ 100) 이 holds 하면 G8 binary verdict 가 granularity-
independent 임이 입증된다.

## 2. Method (변경 없음)

- N_TRIAL = 4096 (고정; N_BIN=16 시 joint cells = 256 ⇒ ~16 trials/cell, MM 보정으로 충분)
- Surrogate score = 9-round FNV-32 avalanche, 5 well-spaced primes (SSOT byte-identical)
- score_to_bin_n(score, n_bin) 만 parametric, 다른 모든 inner loop 동일
- entropy 계산 = Miller-Madow 보정 포함 (×1000 fixed-point integer arithmetic)
- N_BIN levels = {2, 4, 8, 16}, threshold MI_MAX_X1000 = 100 (frozen)
- verdict 룰: G8_STABLE = ∀ level ∀ pair (MI_x1000 ≤ 100)

## 3. Positive Independence Sweep — VERDICT G8_STABLE

40-cell MI matrix (×1000 fixed-point):

| pair | N_BIN=2 | N_BIN=4 | N_BIN=8 | N_BIN=16 |
|------|--------:|--------:|--------:|---------:|
| F_A1 ⊥ F_A2 |  6 | 18 | 31 | 14 |
| F_A1 ⊥ F_A3 | 32 | 26 | 26 | 15 |
| F_A1 ⊥ F_B  | 15 | 37 | 36 | 22 |
| F_A1 ⊥ F_C  | 23 | 18 | 46 | 29 |
| F_A2 ⊥ F_A3 | 39 | 44 | 25 | 29 |
| F_A2 ⊥ F_B  |  7 | 33 | 23 | 23 |
| F_A2 ⊥ F_C  | 35 | 11 | 27 | 14 |
| F_A3 ⊥ F_B  | 34 | 40 | 18 | 31 |
| F_A3 ⊥ F_C  | 37 |  8 | 24 | 28 |
| F_B  ⊥ F_C  | 24 | 27 | 34 | 33 |
| **max**     | **39** | **44** | **46** | **33** |
| **violations / 10** | 0 | 0 | 0 | 0 |
| **level verdict**   | PASS | PASS | PASS | PASS |

- overall max MI ×1000 = **46** (N_BIN=8, F_A1 ⊥ F_C, 0.046 bit ≪ 0.1 bit threshold)
- total_violations = **0 / 40**
- all_levels_pass = 1
- g8_stable = **1**
- fingerprint = 3499179519
- exit code 0
- ⇒ **G8 binary verdict (frozen N_BIN=2 SSOT) is granularity-independent**

핵심 패턴: max MI 가 N_BIN 따라 monotone 증가하지 **않는다** (39 → 44 → 46 → 33).
N_BIN=16 에서 오히려 줄어드는 것은 finite-sample bias 가 Miller-Madow 보정으로
충분히 캡처되어 surrogate 의 진짜 잔여 coupling (≈ 0.03–0.05 bit) 만 남는다는
방증. raw#10 honest caveat ("fine-grained sub-region high-MI 가릴 위험") 은
**측정 결과로 falsified** — 어느 N_BIN level 에서도 hidden high-MI 발견 안 됨.

## 4. Negative Falsify Sweep — VERDICT G8_FRAGILE (expected)

`G8_SWEEP_MODE=negative` 으로 F_C 의 offset 을 F_A1 으로 충돌시킴 ⇒ F_A1 ⊥ F_C
pair 만 모든 level 에서 violation 으로 잡혀야 정상.

| pair | N_BIN=2 | N_BIN=4 | N_BIN=8 | N_BIN=16 |
|------|--------:|--------:|--------:|---------:|
| F_A1 ⊥ F_C | **1014** | **2015** | **3023** | **4008** |
| (other 9)  | 6–39 | 8–44 | 18–36 | 14–31 |

- 정확히 1 pair × 4 level = **4 / 40 violations** (F_A1⊥F_C 만)
- max MI ×1000 = log₂(N_BIN) × 1000 saturation:
  N_BIN=2 → 1014 ≈ 1·1000 (1 bit)
  N_BIN=4 → 2015 ≈ 2·1000 (2 bit)
  N_BIN=8 → 3023 ≈ 3·1000 (3 bit)
  N_BIN=16 → 4008 ≈ 4·1000 (4 bit)
  ⇒ MI = H(X) full coupling at every granularity, 정확히 marginal entropy 와 일치.
- g8_stable = 0, exit code 1, fingerprint = 7635250

The detector localizes the injected coupling at every granularity level while
leaving the 9 uncoupled pairs unaffected ⇒ violation-detection mechanism
verified across the full N_BIN sweep range.

## 5. Byte-Identical Determinism

| run | mode | sha256 |
|-----|------|--------|
| 1 | positive | e183e7ddd64ec84db0e308ff85f4599d86b8854d5d57b073f7d7cc3b35e028aa |
| 2 | positive | e183e7ddd64ec84db0e308ff85f4599d86b8854d5d57b073f7d7cc3b35e028aa |
| 1 | negative | f79e8f193ab04bf4508c78594eb77f19c5de4604a8774d8d5c395270192f1e40 |
| 2 | negative | f79e8f193ab04bf4508c78594eb77f19c5de4604a8774d8d5c395270192f1e40 |

⇒ 양 모드 byte-identical PASS

## 6. ω-cycle iteration log

| iter | issue | fix |
|------|-------|-----|
| 1 | hexa-strict auto-invoke conflict — explicit `main()` call at file end double-invokes in interp path | removed trailing `main()` (auto-invoke handles it) |
| 2 | positive sweep ran clean: 40/40 PASS, max 46 ≪ 100 | freeze |
| 3 | negative sweep verified: 4/40 violations exactly at F_A1⊥F_C across all 4 levels, MI saturates to log₂(N_BIN) | freeze |
| 4 | 2 consecutive runs each mode → byte-identical sha256 | freeze |

## 7. Mk.XII G8 verdict update

**G8 = SURROGATE_PASS + N_BIN_STABLE** (frozen N_BIN=2 SSOT verified granularity-independent).

- frozen SSOT (`g8_transversal_mi_matrix.hexa`, N_BIN=2) verdict G8_PASS holds.
- 본 sweep 으로 N_BIN=2 binary discretization 의 **fine-grained MI 가림 위험**
  (raw#10 honest caveat) 이 surrogate 영역에서는 실증적으로 falsified.
- 4 level 모두 max MI ≤ 0.046 bit ≪ 0.1 bit threshold ⇒ joint H0 multiplicative
  decomposition assumption 에 대한 surrogate-validity 신뢰도 ↑

**Caveat raw#10 honest (residual)**:
- 본 측정은 여전히 **deterministic FNV surrogate** 위에서의 sweep. 실제
  5-falsifier score 분포에서 fine-grained MI 패턴이 surrogate 와 다를 수 있다.
- N_BIN ∈ {2,4,8,16} 4 level 만 테스트. 32 이상 (joint cells ≥ 1024) 에서는
  N_TRIAL=4096 finite-sample noise 가 MM 보정 한계를 넘어 spurious MI 가
  나타날 가능성 있음 (post-arrival real-data 에서는 N_TRIAL 도 동시 증대 필요).
- granularity-independence 가 surrogate 위에서 holds 한다는 사실은 **measurement
  infrastructure 의 robustness** 만 증명. real-falsifier 의 joint multiplicative
  hypothesis 자체에 대한 새 증거는 아님 — 그 작업은 post-arrival prerequisite.

## 8. 산출물

| path | sha256 | size |
|------|--------|------|
| `anima-clm-eeg/tool/g8_n_bin_sweep.hexa` | `cd01467aa3e40de108ffccd40be08a8413021be38d3de015f59b632032fa0bd8` | 461 LOC |
| `anima-clm-eeg/state/g8_n_bin_sweep_v1.json` | `e183e7ddd64ec84db0e308ff85f4599d86b8854d5d57b073f7d7cc3b35e028aa` | 104 lines (positive emit) |
| `anima-clm-eeg/state/g8_n_bin_sweep_v1_negative.json` | `f79e8f193ab04bf4508c78594eb77f19c5de4604a8774d8d5c395270192f1e40` | 104 lines (negative emit) |
| `anima-clm-eeg/docs/g8_n_bin_sweep_landing.md` | (this file) | — |

## 9. Next cycle

- (a) **Real-data N_BIN sweep**: post-arrival 5 falsifier 실측 score 로 동일
  4-level toolchain 재실행. surrogate 결과 (max MI 46 ×1000) 와 real-data
  비교 ⇒ raw#10 honest caveat 의 실측 closure.
- (b) **Extended sweep** (선택): N_BIN=32, 64 까지 확장 시 N_TRIAL 동반 증대
  필수 (joint cells × ≥16 trials/cell rule). real-data 우선이 cost 효율적.
- (c) **Mk.XII G8 gate doc 갱신**: G8 = "surrogate granularity-stable" 명시,
  pending real-falsifier sweep replacement.
- (d) **Combined Stage**: G8 + G9 (DAG cascade) + G10 (Hexad triangulation)
  의 surrogate-pass 3-pillar 묶음으로 Mk.XII Integration axis ω-cycle close.

## 10. Run

```sh
# Positive (default)
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/g8_n_bin_sweep.hexa

# Negative falsify
G8_SWEEP_MODE=negative \
  G8_SWEEP_OUT=anima-clm-eeg/state/g8_n_bin_sweep_v1_negative.json \
  HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/g8_n_bin_sweep.hexa
```
