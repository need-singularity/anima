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

## §3. Results (filled after measurement)

§3 의 결과는 본 문서의 §0 (pre-registration) 이 git 에 안전하게 저장된 다음 채워진다 — predicate 가 결과를 본 후 변형되는 것을 방지.

(see post-measurement §3 below)
