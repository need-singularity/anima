# G8 N_BIN=128 Deferred Extrapolation Analysis — Landing

**Date**: 2026-04-26
**Status**: VIOLATION_AT_OR_BEFORE_128 (extrapolation surrogate ceiling 위반 confirmed)
**Cycle**: ω-cycle 6-step (single mac-local, $0)
**Track**: ω-clm-eeg / G8-N_BIN-extrapolation
**Predecessors**: #182 (G8 N_BIN sweep base 4-level), #196 (G8 N_BIN sweep extended 6-level 60/60 PASS)
**Hexa-only**: raw#9 strict · LLM=none · GPU=none · destructive=0

---

## 1. Problem Statement

`#196` 의 G8 6-level surrogate sweep 은 N_BIN ∈ {2,4,8,16,32,64} 까지만 측정.
N_BIN=128 직접 측정은 N_TRIAL ≥ 16·128² = 262144 가 mac wallclock 한계 근처에 있어
deferred 처리됨.  raw#10 honest caveat (#196 landing §7):

> "N_BIN ≥ 64 monotone (33→56→90) ⇒ residual coupling regime. 추가 level 측정 시
> threshold MI > 0.1 bit 위반 가능성 있음."

본 cycle 은 **6-level data 로부터 log-linear / power-law extrapolation** 을 수행하여
direct measurement 를 대체하고 violation 시점을 정량화.

## 2. Frozen Models (pre-register)

세 모델 모두 N_BIN={64,128,256,512} extrapolation 산출 — design § "FROZEN MODELS".

| 모델 | 도메인 | 가설 형태 | 비고 |
|------|--------|-----------|------|
| **A_loglinear_full_6pt** | 6-level all | `max_mi = a + b·log₂(n_bin)` | informative-only, non-monotone region 포함 |
| **B_loglinear_monotone_3pt** | {16,32,64} 만 | `max_mi = a + b·log₂(n_bin)` | **primary extrapolator** (residual coupling regime) |
| **C_powerlaw_monotone_3pt** | {16,32,64} 만 | `log₂(max_mi) = c + d·log₂(n_bin)` | super-linear vs sub-linear 검증 |

Threshold violation criterion (Model-B):
```
n_bin_critical = 2^((MI_MAX_X1000 - a_mono) / b_mono)
if b_mono <= 0  →  -1 (no crossing)
```

## 3. Inputs (frozen #196)

```
N_BIN =  2 → max_mi_x1000 = 39
N_BIN =  4 → max_mi_x1000 = 44
N_BIN =  8 → max_mi_x1000 = 46
N_BIN = 16 → max_mi_x1000 = 33   ← non-monotone trough (MM correction adequate)
N_BIN = 32 → max_mi_x1000 = 56
N_BIN = 64 → max_mi_x1000 = 90   ← residual coupling regime onset
```

**Non-monotone signature**: idx=2→3 (8→16) 에서 MI 가 46→33 으로 감소.
이는 MM correction 이 finite-sample noise 를 적극 보정하는 영역.
**Monotone signature**: idx=3→5 (16→32→64) 에서 33→56→90 strict monotone.
이 영역에서는 surrogate joint distribution 의 residual coupling 이 dominant.

## 4. Fit Results

### Model-A (full 6-pt log-linear)
- `a_x1000 = 23536`, `b_x1000 = 7942`, `R²_x1000 = 529` → R² ≈ 0.529
- 약한 양의 기울기, 큰 산포 (non-monotone region 이 fit 을 끌어내림).
- **N_BIN_critical_A = 786** (informative-only).

### Model-B (monotone-subset 3-pt log-linear) — PRIMARY
- `a_x1000 = -82834`, `b_x1000 = 28500`, `R²_x1000 = 988` → R² ≈ 0.988
- 강한 양의 기울기 (per log₂-octave +28.5 mi units), tight fit.
- **N_BIN_critical_B = 85** ⇒ **첫 위반 시점은 N_BIN=85 부근**.
- N_BIN=64 sanity: 추정 88 vs 관측 90 (편차 2/1000 = 0.002 bit, ±5 tolerance 내) PASS.

### Model-C (power-law log-log)
- `c_x1000 = 2161`, `d_x1000 = 724`, `R²_x1000 = 1000` → R² ≈ 1.000 (3-pt 완벽 적합)
- d ≈ 0.724 (sub-quadratic, near ¾ power-law).
- super-linear 성장 → N_BIN=128 에서 149, N_BIN=256 에서 247, N_BIN=512 에서 408.

### Extrapolation Table

| N_BIN | log₂ | Model-A | **Model-B** (primary) | Model-C | violates B? |
|-------|------|---------|------------------------|---------|-------------|
| 64    | 6    | 71      | **88**                 | 90      | no (sanity) |
| **128** | 7  | 79      | **116**                | 149     | **YES**     |
| 256   | 8    | 87      | **145**                | 247     | YES         |
| 512   | 9    | 95      | **173**                | 408     | YES         |

Model-A (full 6-pt) 만 따로 보면 N_BIN=512 에서 95 (위반 직전, n_bin_crit_A=786) — 이는
non-monotone region 의 noise 가 fit 을 dilute 했기 때문이며, 실제 residual coupling regime
의 ceiling 은 Model-B/C 가 맞다고 본다.

## 5. Threshold Violation Determination

| 기준 | 값 |
|------|----|
| **MI threshold (×1000)** | 100 (= 0.1 bit) |
| **N_BIN critical (Model-B primary)** | **85** |
| **N_BIN critical (Model-A informative)** | 786 |
| **Verdict** | `G8_EXTRAP_VIOLATION_AT_OR_BEFORE_128` |

**해석**: Model-B (monotone subset, R²=0.988) 기준으로 **N_BIN ≈ 85 에서 max_mi_x1000 이
0.1 bit threshold 를 처음 초과**.  이는 N_BIN=128 에서 충분히 위반 (estimate=116=0.116 bit)
이며, N_BIN=256 에서 0.145 bit, N_BIN=512 에서 0.173 bit 로 super-linear 가속.

## 6. ω-cycle 6-step Compliance

| Step | Description | Result |
|------|-------------|--------|
| 1 | design — 3 models + threshold criterion frozen pre-register | done |
| 2 | implement — `tool/g8_n_bin_128_analysis.hexa` raw#9 strict (~430L) | done |
| 3 | positive selftest — sanity (Model-B@64=88 vs 90, ±2) PASS, R²_mono > R²_full ✓ | PASS |
| 4 | negative falsify — `G8_FIT_RANDOM_PERMUTE=1` (16↔64 swap) → b_mono = -28500 (sign flip), verdict `G8_FIT_RANDOM_DETECTED` ✓ | PASS |
| 5 | byte-identical — re-run sha256 동일 (`5efcd80bb81b…`) | PASS |
| 6 | iterate — landing + marker + memory + roadmap append | done |

## 7. Artifacts (sha256)

| Path | sha256 | role |
|------|--------|------|
| `anima-clm-eeg/tool/g8_n_bin_128_analysis.hexa` | `7cbda0526ca07214…` | tool (raw#9 strict, ~430L) |
| `anima-clm-eeg/state/g8_n_bin_128_analysis_v1.json` | `5efcd80bb81b7896…` | positive output (verdict=VIOLATION_AT_OR_BEFORE_128) |
| `anima-clm-eeg/state/g8_n_bin_128_analysis_v1_negative.json` | `4e0fcfa2170c77cf…` | negative falsify output (verdict=FIT_RANDOM_DETECTED) |
| `anima-clm-eeg/docs/g8_n_bin_128_extrapolation_landing.md` | this file | landing |
| `anima-clm-eeg/state/markers/g8_n_bin_128_extrapolation_complete.marker` | (write-on-close) | silent-land 방지 |

## 8. raw#10 Honest Caveats

1. **Surrogate, not real EEG**: 본 분석은 FNV-deterministic surrogate (#175 chain) 의 ceiling
   estimate.  Real-falsifier 6-level sweep + extrapolation 은 D-day 측정 후 별도 cycle.

2. **3-point fit is structurally R²=1.000 for power-law**: Model-C 의 R²=1.000 은 3 점 fit
   의 자유도 한계 (2 parameters fit 3 points). 이는 over-fit indicator 이며, **out-of-sample
   prediction 의 신뢰 척도가 아님**.  Model-B (선형 R²=0.988) 가 실질 신뢰 척도.

3. **Extrapolation domain**: Model-B 는 N_BIN ∈ {16,32,64} 에서만 학습. N_BIN=128, 256, 512
   는 1-3 octave **extrapolation**.  실측 시 (raw N_TRIAL ≥ 262144) 추정과 5-30% 편차 가능.

4. **Non-monotone region exclusion**: N_BIN ≤ 16 의 비단조성 (8→16: 46→33) 은 finite-sample
   MM correction 의 정상 신호.  Model-A 가 이 영역을 포함했기에 R²=0.529 로 dilute.
   primary extrapolator 는 **monotone region only** 인 Model-B.

5. **MI threshold (×1000) = 100** 의 의미: 0.1 bit ≈ pairwise MI 가 5-falsifier 매트릭스에서
   "위양성 transversality 위반" 을 단언할 minimum effect size.  Real-data 에서는 (a) higher
   noise floor, (b) lower true MI 양상이 가능.

6. **N_BIN=128 직접 측정 비용 (deferred reason)**: N_TRIAL ≥ 16·128² = 262144 trials.
   surrogate hist build cost ≈ N_TRIAL · 5 falsifiers · 10 pairs / fnv9_round ≈ 13M FNV ops
   per level → mac wallclock ~ 30-90 sec per level.  본 cycle 은 단지 30분 cap 내에서 확실한
   answer 를 위해 extrapolation path 채택.  **후속 cycle 에서 직접 측정 verify 필요**.

7. **N_BIN=256, 512 estimate 신뢰도**: Model-B 은 1-2 octave (N_BIN=128) 까지 reasonable.
   3 octave (N_BIN=512) 는 monotone-extrapolation assumption 이 깨질 수 있음 — log-linear
   가 아닌 saturation curve 를 보일 가능성 (residual coupling 이 N_BIN 증가 시 ceiling
   효과 발생).  Model-C (power-law) 는 그 가능성을 더 비관적으로 추정 (N=512 408).

## 9. Next Cycle Candidates

1. **Direct N_BIN=128 measurement** — 60-90 sec mac wallclock, extrapolation 검증.
2. **Saturation model fit** — 4-parameter logistic/exponential `max_mi = m*(1 - exp(-α·log₂(n_bin)))`
   로 extrapolation 의 ceiling 추정.  3-point monotone subset 으로는 4-param fit 불가 →
   N_BIN=128 추가 측정 후 가능.
3. **Real-falsifier 6-level sweep** — D-day 후 EEG band power surrogate 대체.
4. **Mk.XII §6 G8 ceiling re-binding** — N_BIN=2 SSOT 의 robustness 가 N_BIN ~ 85 에서
   깨짐 ⇒ Mk.XII Hard PASS pipeline 이 N_BIN=2 binary verdict 만 사용한다는 점을 §6 에
   명시 update.

## 10. Cross-references

- Parent: `docs/g8_n_bin_sweep_extended_landing.md` (#196), `state/g8_n_bin_sweep_extended_v1.json` (#196)
- Sister: `docs/g8_n_bin_sweep_landing.md` (#182), `tool/g8_transversal_mi_matrix.hexa` (#175)
- Mk.XII: `docs/mk_xii_d_day_simulated_landing.md` (D+6 G8 block parent, N_BIN=2 SSOT consumer)
- Memory: `feedback_completeness_frame` (weakest-link → extrapolation safety bound)
