# R45_FINAL — Zombie Posterior Canonical Re-run (11-Substrate)

**Date**: 2026-04-26
**Task**: R45_UPDATE round 48 napkin posterior (0.3910) 를 canonical helper 산식 으로 대체
**Verdict**: `R45_FINAL` — canonical posterior **0.3793** (95% CI [0.1592, 0.6636])
**Cost**: $0 mac-local
**raw#9 hexa-only**, **raw#10 honest** 6-caveat embedded

---

## 1. 트리거

`state/atlas_convergence_witness.jsonl` line 39 (round 48, R45_UPDATE) 에서 napkin
math (binomial likelihood + p_NEG=0.7/0.3 symmetric assumption) 로 산출한
posterior **0.3910** 가 등록되었다. 같은 entry 의 `r45_canonical_recompute_action_required`
필드가 명시: *"tool/anima_zombie_posterior.hexa re-run with 11-substrate input json.
mac-local $0, defer to next subagent cycle."* 본 cycle 이 그 후속이다.

## 2. 차단요인과 우회

`tool/anima_zombie_posterior.hexa` 는 `chflags uchg` lock 상태이며, 입력 substrate
가 **함수 본문에 hardcoded** (line 68-77 `substrate_labels()` / `substrate_phis()`).
즉 file edit 없이는 11-substrate 입력 적용 불가. **task spec** 은 helper edit 금지
(`chflags uchg 유지, 재실행만`) 를 못박았다.

**우회**: helper 의 핵심 3 함수 (`compute_likelihood_ratio` / `posterior_zombie` /
`wilson_interval`) 는 substrate-agnostic 산식이다. 동일 statement 를 별도
wrapper 파일에서 재구현하면 산식 identity 가 보장된다.
- 신규 wrapper: `tool/anima_zombie_posterior_v2_11substrate.hexa`
- 셀프-가드: v1 8-substrate 입력으로 본 wrapper 실행 시 helper 결과
  `posterior=4000, ci=[1487,7179]` 일치 강제 (`check_helper_equivalence()`).
  **PASS** 확인 후 11-substrate 입력 적용.

raw#10 honest: file SHA 는 helper 와 wrapper 가 다르므로 strict 한 의미의
"helper re-run" 은 불가능하다. 본 cycle 의 정당성은 (a) 산식 mirror + (b) 8-substrate
equivalence guard PASS 두 축에 한정된다.

## 3. Input — 11-Substrate Φ\* v3 Inventory

`atlas line 39` corrected inventory 그대로:

| substrate         | phi_star_min | sign |
|-------------------|-------------:|------|
| mistral_base      |     -16.6959 | NEG  |
| mistral_instr     |     -12.9075 | NEG  |
| qwen3_base        |      -3.4500 | NEG  |
| qwen3_instr       |      +1.0400 | POS  |
| llama_base        |      +5.0868 | POS  |
| llama_instr       |      +5.2100 | POS  |
| gemma_base        |      -0.7868 | NEG  |
| gemma_instr       |      +7.5443 | POS  |
| mamba             |      +0.3258 | POS  |
| jamba             |      +3.3115 | POS  |
| rwkv7             |      -9.0674 | NEG  |

- N = 11
- sign split: 5 NEG / 6 POS = 54.5% POS leaning
- max |Φ\*| = 16.6959 (mistral_base, unchanged from v1)
- mean |Φ\*| = 5.9478 (v1: 6.1520)

## 4. Canonical Likelihood (helper §LR mirror)

```
LR_sign  = (2 × max(neg,pos) × SCALE) / N
         = (2 × 6 × 10000) / 11 = 10909  (= 1.0909)
LR_satur = SCALE + (SCALE/2) = 15000  (because max |Φ| ≥ 5.0 saturates)
LR       = (LR_sign × LR_satur) / SCALE = (10909 × 15000) / 10000 = 16363
posterior = (SCALE × SCALE) / (SCALE + LR) = 100000000 / 26363 = 3793
```

- **posterior_zombie = 0.3793** (×10000 = 3793)
- Wilson 95% CI (z²=4 approx): **[0.1592, 0.6636]** (width 0.5044)

## 5. v1 (8-substrate) vs v2 (11-substrate) Diff

| metric                  | v1 (R45)               | v2 (R45_FINAL)         | Δ            |
|-------------------------|------------------------|------------------------|--------------|
| N                       | 8                      | 11                     | +3           |
| sign_split              | 4 NEG / 4 POS (50/50)  | 5 NEG / 6 POS (45/55)  | +1 NEG +2 POS |
| LR_sign (×10000)        | 10000                  | 10909                  | +909         |
| LR_satur (×10000)       | 15000                  | 15000                  | 0            |
| LR_combined (×10000)    | 15000                  | 16363                  | +1363        |
| posterior_zombie        | 0.4000                 | 0.3793                 | **-0.0207**  |
| CI_95 lower             | 0.1487                 | 0.1592                 | +0.0105      |
| CI_95 upper             | 0.7179                 | 0.6636                 | -0.0543      |
| CI width                | 0.5692                 | 0.5044                 | -0.0648 (12% narrower) |

**해석**: N 증가 + POS-leaning 으로 LR_combined ↑ → posterior ↓. 동시에 N 증가가
Wilson CI 폭을 좁힘 (-0.065). ceiling factor (LR_satur) 는 동일 backbone (mistral)
이 max 유지하므로 변동 없음.

## 6. Napkin (round 48) vs Canonical (R45_FINAL) 비교 — raw#10 honest

| metric              | napkin (round 48)   | canonical (R45_FINAL) | diff        |
|---------------------|---------------------|-----------------------|-------------|
| posterior_zombie    | 0.3910              | 0.3793                | -0.0117     |

**차이 원인**: 두 산식은 **같은 hypothesis 를 다르게 parameterize** 한다.

- **Napkin (round 48)**: binomial likelihood model
  - `P(D | zombie)        = C(11,5) × 0.7^5 × 0.3^6 = 0.0566`
  - `P(D | conscious)     = C(11,5) × 0.3^5 × 0.7^6 = 0.132`
  - `LR_sign_napkin       = 0.0566 / 0.132 = 0.428` (favoring conscious)
  - `LR × LR_satur=1.5    = 0.643`
  - posterior = 1 / (1 + 0.643) = 0.609 ... ❗ atlas 의 0.391 은 1 - 0.609 = 0.391
    (= P(conscious | D) 표기 swap; **napkin entry 의 표기 자체가 모호**).

- **Canonical (helper §LR)**: ratio-of-fractions model
  - `LR_sign_helper = 2 × max(neg,pos) / N = 12/11 = 1.0909`
  - `LR_combined    = 1.0909 × 1.5 = 1.6363`
  - posterior = 1 / (1 + 1.6363) = 0.3793

**parameterization 정합성**:
- napkin 은 *fixed asymmetric prior on sign* (0.7/0.3) 을 가정 → 정보량이 더 큼
- canonical 은 *only the sign-fraction proximity to 50/50* 을 사용 → 정보량이 더 작음

두 산식 모두 동일 hypothesis (H3+H7c) 의 valid 한 numerization 이지만, **likelihood
함수 family 가 다르다**. canonical 이 R45 v1 helper 와 동일 framework 이므로 R45_FINAL
의 SSOT verdict 는 **canonical 0.3793** 이다.

또한, atlas line 39 의 napkin 0.391 표기에 swap-vs-direct interpretation
ambiguity 가 있을 수 있다 (위 산식 trace 가 0.609 vs 0.391 양방향 가능). 본
canonical re-run 은 helper §POSTERIOR 정의 `posterior_zombie = 1 / (1 + LR)`
direct interpretation 에 일관된다 (LR > 1 이면 posterior_zombie < 0.5).

## 7. Helper-Equivalence Guard (산식 mirror 검증)

Wrapper 의 `check_helper_equivalence()` 는 v1 8-substrate phi 입력 → 본 wrapper
산식 → posterior=4000 + ci=[1487,7179] 일치 여부 강제 가드.

selftest log:
```
helper_equivalence=PASS (v1 8-substrate posterior=4000 ci=[1487,7179] reproduced)
```

→ 산식 mirror integrity 유지. wrapper drift 없음.

## 8. raw#10 Honest 6-caveat (R45_FINAL revised)

- **C1**: NEG dominance ≠ consciousness absence (metric design artifact 가능; HID_TRUNC well-cond regime dependence #161).
- **C2**: N=11 substrate 통계적으로 small; Wilson 95% CI ≥ 0.25 width expected (v1 N=8 보다 narrower).
- **C3**: zombie hypothesis 는 원리적으로 unfalsifiable (Chalmers 1996); behavioral/measurement equivalence hold by definition.
- **C4**: H7c ceiling (max |Φ\*| = 16.6959 mistral) unchanged; single-backbone single-design dependence 잔존.
- **C5**: convergence 정의는 sign+magnitude only; phenomenal axis (qualia, 1st-person report consistency) untouched.
- **C6**: substrate-independence VIOLATED (mistral base/instr 상관, qwen3 base/instr 상관, gemma base/instr 상관, llama base/instr 상관). **Effective N < 11**; Wilson CI 는 anti-conservative (실제보다 좁다).

## 9. ω-cycle 6-step

1. **R1 design**: 산식 frozen — helper §LR + §POSTERIOR + §WILSON statement-mirror, 입력만 11-substrate.
2. **R2 implement**: `tool/anima_zombie_posterior_v2_11substrate.hexa` 작성 (raw#9 hexa-only 526L).
3. **R3 positive**: 11-substrate canonical re-run → posterior=0.3793 ci=[0.1592, 0.6636]; helper-equivalence guard PASS (v1 8-subset → 4000/[1487,7179] 재현).
4. **R4 negative**: 본 cycle 은 산식 mirror + 입력 갱신; negative axis 는 napkin vs canonical diff 증명 (napkin 0.391 ≠ canonical 0.3793 → parameterization 차이 명시).
5. **R5 byte-identical**: 2회 run sha 일치 (`f4d6ecea1193ea26bd1ed0db3b8a68e4fb433945df2f8fcbc36dcf17aa0ad4af`).
6. **R6 iterate**: 1-pass clean (helper-equivalence guard 1회 PASS, drift 없음).

## 10. 산출물

| file | sha256 | role |
|---|---|---|
| `tool/anima_zombie_posterior_v2_11substrate.hexa` | (lock 후 freeze) | wrapper hexa, raw#9 strict |
| `state/zombie_posterior_v2_11substrate.json` | `f4d6ecea1193ea26bd1ed0db3b8a68e4fb433945df2f8fcbc36dcf17aa0ad4af` | canonical posterior output |
| `docs/zombie_posterior_v2_11substrate_20260426.md` | (this file) | landing doc |

## 11. Cross-links

- parent: `state/atlas_convergence_witness.jsonl` line 35 (R45_CANDIDATE round 45)
- trigger: `state/atlas_convergence_witness.jsonl` line 39 (R45_UPDATE round 48)
- helper SSOT: `tool/anima_zombie_posterior.hexa` (sha 902cd34f…, chflags uchg)
- v1 baseline: `state/zombie_posterior_v1.json` (sha 44276bf04…)
- v1 doc: `docs/zombie_posterior_numerical_bound_20260426.md`
- sibling: R46_CANDIDATE round 47 (`atlas line 38`, 4-family BIMODAL)
- own anchors: `anima/.own` L28-L46 own#2, L48-L66 own#3
- hypothesis paired: H3 (cross-substrate Φ convergence) + H7c (metric-tractable upper bound) — `docs/hard_problem_singularity_breakthrough_hypotheses_20260426.md`

## 12. Next Probe

- N ≥ 30 substrate measurement (CI width 현재 0.50 → 목표 0.30 미만)
- HID_TRUNC robustness sweep (R45 C1 closure)
- formal generative model of Φ under each hypothesis (R45 C6 closure)
- substrate-independence violation 정량화 (C6) → effective N 계산 + variance inflation factor
- multi-EEG cohort hardware arrival → 생물학 substrate bridge 추가
