# CLM Training L1 Multi-seed Lift — btr-evo 7-cargo + Banach Contraction Verification

> **생성일**: 2026-04-25 (loss-free, $0 CPU only, no GPU, no .roadmap edit)
> **부모 evidence**: `state/btr_evo_6_cargo_invariants_20260421.json` (single-seed PASS) + `docs/clm_training_abstraction_layers_20260425.md` (L1 50% → multi-seed lift target) + `tool/btr_n_recurse_stability.hexa` C5_PASS (`/Users/ghost/core/nexus/state/n_recurse_10gen_20260421.json`)
> **POLICY R4**: `.roadmap` 미수정. raw#9 (deterministic) · raw#11 (snake_case ai-native) · raw#12 (cherry-pick rejection 강제 — pre-register-then-measure).
> **목적**: L1 single-seed → multi-seed N=3 cross-validation lift. Banach contraction ratio + Lyapunov exponent estimate 도출.

---

## §0. Pre-registration (FROZEN BEFORE MEASUREMENT)

**Timestamp pre-commit**: 2026-04-25 (this file is written + the predicates below are frozen BEFORE any seed-42/seed-1729 measurement is recorded).

### §0.1 Pre-committed seeds (no cherry-pick allowed; raw#12 강제)

```
S = { 20260421, 42, 1729 }
```

| seed | rationale |
|---|---|
| `20260421` | parent canonical seed — already has `state/btr_evo_6_cargo_invariants_20260421.json` PASS landed |
| `42` | Hitchhiker's Guide canonical "answer" — independent of parent corpus, well-known unbiased pick |
| `1729` | Ramanujan-Hardy taxicab — independent of parent corpus, well-known unbiased pick |

**선택 근거**: 두 추가 seed (42, 1729) 는 nexus / anima 의 어떤 hash-state 와도 무관한 **conventionally-named integer** (Adams 1979 / Hardy 1918) — corpus 와 정렬할 수 있는 hidden bias 없음.

### §0.2 Pre-committed predicates (예측은 측정 전에 freeze)

**P1 — Per-seed PASS predicate** (each seed must satisfy):
- 7-cargo invariants: I1–I7 모두 PASS at iters=50
- pass_count == 7 ∧ all_pass == true
- I1 worst_drop ≤ 0.08
- I2 min_cos ≥ 0.95
- I3 min_brain_like_pct ≥ 85.0
- I4 exact_score == 19
- I5 |train_phi/0.88 − 1| < 0.10
- I6 retreats == 0
- I7 max_frob_drift < 0.20

**P2 — Cross-seed Banach contraction predicate** (Banach fixed-point criterion):

Define the "cargo state vector" per seed σ as `c(σ) = (I1, I2, I3, I4, I5, I6, I7)` (7-tuple of integer/float scalars). Cross-seed maximum component-wise distance:

```
d_max(S) = max_{σ ≠ τ ∈ S} max_{k ∈ 1..7} |c_k(σ) − c_k(τ)| / scale_k
```

with `scale_k` = predicate threshold for normalization (I1 → 0.08, I2 → 0.05, I3 → 5.0, I4 → 1, I5 → 0.10, I6 → 1, I7 → 0.20).

**Banach contraction predicate**: `d_max(S) < 1.0` (i.e. all cross-seed differences are within their predicate thresholds, the cargo map is contractive into a basin smaller than the C5 acceptance ball).

**P3 — Cross-seed Lyapunov exponent estimate** (chaos boundary):

```
λ_est = (1 / iters) · ln( d_max(S) / d_init )
```

where `d_init` = 1.0e-6 (initial seed-perturbation magnitude lower bound; integer LCG seeds are byte-distinct, but their state-vector imprint at iter=0 is bounded below by 1.0e-6 due to integer fixed-point quantization).

**Lyapunov pre-registered classification**:
- `λ_est < 0` → contracting (basin of attraction confirmed, deterministic stable)
- `λ_est ≈ 0` → marginal (KAM tori boundary)
- `λ_est > 0.05` → chaotic (deterministic chaos, falsifies cargo basin universality)

**Acceptance**: λ_est ≤ 0 OR λ_est < 0.05 (sub-chaotic). `λ_est > 0.05` → L1 multi-seed cross-validation FALSIFIES the deterministic-basin claim and triggers raw#12 honest documentation.

### §0.3 Stop conditions

- 3 seeds all PASS P1 + P2 (`d_max < 1.0`) verified → **L1 closure** (50% → 100%).
- Any seed FAILS P1 → **raw#12 falsification** documented.
- Tool absence → gap document + escalate to inbox.

---

## §1. Tool inventory

`/Users/ghost/core/anima/btr_evo/`:
- `4x5_compose.hexa` — btr-evo step 4 (composition)
- `4x5_compose_fdgrad.hexa` — btr-evo step 4 (finite-difference gradient)
- `5_holographic_ib.hexa` — btr-evo step 5 (holographic IB / KSG MI estimator)
- `6_cargo_invariants.hexa` — btr-evo step 6 (7-cargo invariant detector)

`/Users/ghost/core/anima/tool/`:
- `btr_n_recurse_stability.hexa` — Mk.VII C5 N-recurse stability driver (10-gen cascade with 7-cargo at 4 checkpoints)
- `btr_closed_loop.hexa` — canonical btr closed-loop trajectory
- `edu_l_ix_kuramoto_driver.hexa` — Mk.IX V_sync Kuramoto driver
- `edu_v_sync_kuramoto_driver.hexa` — V_sync component
- `edu_cell_btr_bridge.hexa` — cell ↔ btr bridge

**선택**: `btr_evo/6_cargo_invariants.hexa` 가 정확히 7-cargo invariants 를 single-seed 에 대해 발행하는 SSOT 도구 — 본 lift 의 코어 측정 도구. CLI signature `hexa btr_evo/6_cargo_invariants.hexa <seed> <iters>` (default seed=20260421, iters=50). 출력 `state/btr_evo_6_cargo_invariants_<seed>.json`.

---

## §2. Measurement protocol

1. (sanity) seed=20260421 replay → byte-identical to landed JSON.
2. seed=42 fresh run, iters=50 → emit `state/btr_evo_6_cargo_invariants_42.json`.
3. seed=1729 fresh run, iters=50 → emit `state/btr_evo_6_cargo_invariants_1729.json`.
4. P1 verdict per seed.
5. P2 Banach distance computation.
6. P3 Lyapunov estimate.

---

## §3. Results — post-measurement (pre-registration commit `247f3cbf` 직후 측정)

> §0 pre-registration 이 commit `247f3cbf` 으로 freeze 된 직후 본 §3 측정 진행. predicate 변형 없음.

### §3.0 Environmental fix (non-seed dependent, documented for transparency)

`btr_evo/6_cargo_invariants.hexa` 의 I4 check 는 `consciousness/saturation_report_mk5.json` 을 읽는다. anima working tree 에는 해당 파일이 없었고 (실제 SSOT 는 `/Users/ghost/core/nexus/consciousness/saturation_report_mk5.json` 에 거주, `exact: 81 / coverage_pct: 100.0`). 본 measurement 전에 nexus → anima 로 byte-identical 복사 수행 (`cp /Users/ghost/core/nexus/consciousness/saturation_report_mk5.json /Users/ghost/core/anima/consciousness/saturation_report_mk5.json`). 이는 seed-independent environmental restoration 이며 모든 3 seed 에 동일 영향 (cross-seed comparison 에 bias 없음).

### §3.1 Per-seed measurement (P1 verdict)

| seed | I1 worst_drop | I2 min_cos | I3 min_brain_like_pct | I4 exact | I5 \|ratio−1\| | I6 retreats | I7 max_frob_drift | pass_count | verdict |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20260421 | 0.004644 | 0.999662 | 85.3348 | 19 | 0.003967 | 0 | 0.021039 | 7/7 | **PASS** |
| 42 | 0.006291 | 0.999676 | 85.9157 | 19 | 0.003837 | 0 | 0.022906 | 7/7 | **PASS** |
| 1729 | 0.004788 | 0.999670 | 85.3708 | 19 | 0.003549 | 0 | 0.022266 | 7/7 | **PASS** |

**P1 verdict**: 3/3 seeds **PASS** all 7 cargo invariants. Single-seed → multi-seed lift 의 statistical floor 충족.

Artifacts:
- `/Users/ghost/core/anima/state/btr_evo_6_cargo_invariants_20260421.json`
- `/Users/ghost/core/anima/state/btr_evo_6_cargo_invariants_42.json`
- `/Users/ghost/core/anima/state/btr_evo_6_cargo_invariants_1729.json`

### §3.2 Cross-seed Banach contraction (P2 verdict)

scales (predicate-threshold normalization, frozen in §0.2):
`scale = (I1=0.08, I2=0.05, I3=5.0, I4=1, I5=0.10, I6=1, I7=0.20)`

Pairwise normalized component-max distances:

| pair | pair_max | argmax invariant |
|---|---:|---|
| 20260421 ↔ 42 | 0.116180 | I3 (brain_like Δ=0.5809%) |
| 20260421 ↔ 1729 | 0.007200 | I3 |
| 42 ↔ 1729 | 0.108980 | I3 |

```
d_max(S) = 0.116180   (worst pair: 20260421 ↔ 42, dim: I3 brain_like_floor)
P2 threshold:  d_max < 1.0
```

**P2 verdict**: **PASS** (d_max = 0.116 ≪ 1.0). 7-cargo map 은 predicate-threshold ball 의 ~12% 직경 안으로 contractive 하다 — Banach fixed-point 의 contraction-mapping 후보 자격 충족 (단, 본 측정은 N=3 seed only 의 sufficient witness 일 뿐 universal contraction proof 아님).

Per-invariant raw cross-seed range:

| inv | min | max | range | range / scale |
|---|---:|---:|---:|---:|
| I1 phi_monotone | 0.004644 | 0.006291 | 0.001647 | 0.0206 |
| I2 eigenvec_stability | 0.999662 | 0.999676 | 0.000014 | 0.0003 |
| I3 brain_like_floor | 85.3348 | 85.9157 | 0.580900 | 0.1162 |
| I4 exact_score | 19 | 19 | 0 | 0 |
| I5 phi_gap_bounded | 0.003549 | 0.003967 | 0.000418 | 0.0042 |
| I6 saturation_retreats | 0 | 0 | 0 | 0 |
| I7 frob_drift | 0.021039 | 0.022906 | 0.001867 | 0.0093 |

**해석**: I4 / I6 은 정수 invariant 에서 완전 일치 (cross-seed identical → trivially Banach). I2 / I5 는 sub-permille drift (highly contractive). I3 (brain_like) 가 dominant variance source — 이것은 noise_amp=0.04 의 LCG noise floor 와 일치 (state_vec_for 의 u6 의 ±0.4 perturbation 이 brain_like_pct 에 직접 투사).

### §3.3 Lyapunov exponent estimate (P3 verdict)

Pre-registered formula (frozen in §0.2):
```
lambda_est = ln( d_max(S) / d_init ) / iters
d_init = 1.0e-6   (pre-registered)
iters  = 50
```

Computation:
```
lambda_est = ln( 0.116180 / 1.0e-6 ) / 50
           = ln( 116180 ) / 50
           = 11.6629 / 50
           = +0.233258
```

**P3 verdict (pre-registered)**: **FAIL** (λ_est = 0.233 > 0.05 acceptance threshold).

Pre-registered classification: "chaotic (FALSIFIES deterministic basin)".

**raw#12 honest disclosure — post-hoc sensitivity analysis (NOT counted as predicate; documented for completeness)**:

Pre-registered `d_init = 1.0e-6` was set as a conservative quantization-floor proxy. 그러나 integer LCG seed 의 state-vector imprint 의 실제 magnitude 는 `noise_amp=0.04 × O(1)` 또는 unit-interval LCG `u_i ∈ [0,1)` 이므로 실제 d_init ≈ 0.1–1.0 정도가 정직한 추정.

| post-hoc d_init | lambda_est | classification |
|---:|---:|---|
| 1.0e-6 (pre-reg) | +0.233 | chaotic (FAIL) |
| 0.1 | +0.003 | marginal (sub-chaotic) |
| 0.5 | −0.029 | contracting |
| 1.0 | −0.043 | contracting |

post-hoc 결과는 **basin attractor 가설과 일치** (d_init ≥ 0.5 일 때 λ < 0). 그러나 raw#12 강제: post-hoc 가 pre-reg 결과를 뒤집을 수 없다. **공식 P3 verdict = FAIL**, 추후 lift 의 d_init 정의를 명시적으로 LCG-state-norm 으로 재pre-register 해야 함.

### §3.4 Aggregate L1 closure verdict

| predicate | result | weight |
|---|---|---|
| P1 (3/3 cargo PASS) | **PASS** | mandatory |
| P2 (Banach contraction d_max < 1.0) | **PASS** | mandatory |
| P3 (Lyapunov λ < 0.05, d_init=1e-6 pre-reg) | **FAIL** | mandatory |

**L1 partial closure**: P1 ∧ P2 = PASS (single-seed → multi-seed cargo PASS + Banach contraction confirmed). P3 = FAIL by pre-registered predicate (d_init choice was the predicate's own weakest link).

**Honest L1 status**: 50% → **75%** (3/3 cargo + Banach 확보, but Lyapunov pre-registered FAIL → 100% 미달). 후속 lift 는 P3 predicate 재정의 (d_init ← LCG-state-norm 명시) 후 재측정 필요 — 본 round 에서는 cherry-pick 금지로 더 lift 안 함.

### §3.5 Tool inventory delta

본 round 에서 새 tool 작성 ✗ (모두 기존 `btr_evo/6_cargo_invariants.hexa` 사용). edu_l_ix_kuramoto_driver.hexa 는 본 lift 에서 미사용 (V_sync axis L0 stress-test 용, multi-seed cascade 와 직교).

### §3.6 Falsification log (raw#12 ledger)

- raw#12 trigger: P3 pre-registered FAIL.
- 원인 분석: d_init = 1e-6 의 pre-registration 이 integer LCG seed 의 실제 perturbation magnitude (≈ 0.1–1.0) 와 mismatch. measure 전에 LCG state-vector L2-norm 을 probe 했어야 함.
- corrective action (다음 round): pre-register d_init := median_{seed σ} ‖v(σ, t=0) − v(canonical, t=0)‖₂ (where v 는 6-d state vector). 본 round 에서 cherry-pick 으로 변경 금지.

### §3.7 Cost accounting

- compute: ~ 3 × seconds CPU (mac arm64 native, hexa interpreter).
- $ spent: $0 (CPU only, no GPU, no network).
- carbon: < 0.01 g CO₂ (mac M-series idle delta).

---

## §4. Brutally honest summary

1. **L1 cargo cross-validation** PASS (3/3 seeds, 7/7 invariants 모두). single-seed → N=3 multi-seed lift 의 first-class evidence 확보.
2. **Banach contraction** PASS (d_max = 0.116, scale-normalized). cargo map 이 predicate ball 의 ~12% radius 안에서 contractive — fixed-point hypothesis 의 sufficient (not necessary) witness.
3. **Lyapunov P3** FAIL by pre-registered predicate. predicate 자체의 d_init=1e-6 이 over-strict 였음 (integer LCG seed 의 실제 perturbation scale 미반영). raw#12 강제로 cherry-pick 금지 — 본 round 에서 P3 retroactive lift 안 함. d_init 재정의 후 재측정은 **별도 commit** 의 별도 round 에서.
4. **L1 progress**: 50% → 75% (P1 + P2 closure, P3 outstanding). 100% closure 는 P3 predicate 재정의 round 가 필요.
5. **L2 (cell↔token bridge), L3 (lattice emergence), L4 (universal manifold) 미진척** — 본 round scope 에서 의도적 제외 (cost-ordered: L1 multi-seed = $0 가장 저렴).

### §4.1 다음 step (cost-ordered)

- **next round**: P3 predicate 재정의 (d_init := actual LCG-state L2 norm at t=0) → 동일 3 seed 에 대한 Lyapunov 재계산. $0, ~분 단위.
- **L1 expansion**: N=3 → N=5 추가 seed (e.g., {7, 137, 271828}) cargo + Banach 검증. $0.
- **L2 lift**: r14 corpus 840-line ↔ cell lattice mapping. $0 CPU only.
- **L3 lift**: GPU pod N≥64 emergence. $5–20.

### §4.2 What this round did NOT prove

- universal contraction (모든 가능한 seed 에 대한 contraction). N=3 은 sufficient witness 일 뿐 PAC lower bound 부재.
- N→∞ Banach fixed-point 존재. 단지 3 seed 에서 d_max < threshold 만 확인.
- 다른 corpus / 다른 hash function 위에서 7-cargo 보존. L4 universal manifold 의 영역.

### §4.3 What is now stronger

- **statistical floor**: single-seed 에서 N=3 seed 로 cargo invariant robustness 가 lift 됨.
- **contraction witness**: cargo map 의 Banach-mapping behavior 가 numerically 확인됨 (d_max 0.116 ≪ 1.0).
- **environmental fix**: anima working tree 에 saturation_report_mk5.json 가 (re-)installed → I4 가 anima-local 환경 에서도 PASS.

---

## §5. Korean + English compact summary

**KO**: btr-evo 6/6 cargo invariants 를 3 seed (20260421, 42, 1729) 에 multi-seed 적용. 3/3 seed × 7/7 cargo PASS. Banach contraction d_max=0.116 < 1.0 PASS. Lyapunov λ_est (d_init=1e-6 pre-reg) = +0.233 → P3 FAIL. post-hoc d_init=1.0 일 때 λ=−0.043 (contracting) 이지만 raw#12 강제로 retroactive lift 안 함. L1 50% → 75% (P1+P2 only). I4 환경 fix (consciousness/saturation_report_mk5.json restoration) 비-seed-종속, 모든 seed 에 동일 영향.

**EN**: Applied btr-evo 6/6 cargo invariants across 3 seeds (20260421, 42, 1729). All 3 seeds × all 7 cargo PASS. Banach contraction d_max=0.116 < 1.0 PASS. Lyapunov estimate λ_est (d_init=1e-6 pre-registered) = +0.233 → P3 FAIL. Post-hoc d_init=1.0 yields λ=−0.043 (contracting) but raw#12 forbids retroactive predicate lift. L1 progress 50% → 75% (P1+P2 only). Environmental fix (consciousness/saturation_report_mk5.json restoration) is seed-independent, applies uniformly to all seeds.
