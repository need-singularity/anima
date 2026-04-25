# UNIVERSAL_CONSTANT_4 axis 11 — pre-registration (candidate A, L_IX 4-term ablation)

> **생성일**: 2026-04-25
> **부모 commits**:
> - `bc541326` axis 10 design draft (3 후보)
> - `…` axis 10 candidate B σ·φ identity (선행 axis 10)
> **CRITICAL — raw#12 disclosure**: 본 commit 은 **measurement BEFORE** committed.
> Tool implementation, ablation runs, verdict 모두 이 commit 이후 별 commit.
> 본 pre-reg 의 predicate 는 frozen — post-hoc tuning 금지.

---

## §1. Hypothesis

**UNIVERSAL_4 axis 11 (Lagrangian-dynamical instance)**:

Mk.IX unified Lagrangian L_IX 의 K=4 dynamical terms (T, V_struct, V_sync, V_RG)
이 gen-5 stationarity 의 **necessary** structure 를 형성한다. 추가의 informational
term λ·I_irr 는 stationarity 도달에 영향이 없다 (necessary 가 아니라 *enriching*).

구체적으로:
- L_IX = T − V_struct − V_sync − V_RG + λ·I_irr  (5 terms 총합)
- Dynamical terms = {T, V_struct, V_sync, V_RG} (cardinality 4 = K=4 anchor)
- Informational term = λ·I_irr (단 1개)
- Claim: 5개 ablation (각 term 을 0 으로 강제) 중 정확히 4개 (dynamical drop)
  는 gen-5 stationarity 도달 실패, 정확히 1개 (drop_I_irr) 는 PASS.

K=4 connection: dynamical sub-Lagrangian 의 cardinality |{T, V_struct, V_sync, V_RG}| = 4.

---

## §2. Pre-registered predicate (committed BEFORE measurement)

### 2.1 Simulator protocol

L_IX 의 W-evolution 을 gradient-descent 로 모사한다 (synthetic dynamics).

- 초기 조건: W_0 = 40 (baseline natural_gen5 첫 gen 과 일치)
- Per-gen 업데이트 (정수 fixed-point ×1000):
  ```
  W_{k+1} = clamp( W_k − η · ∂L_IX_eff/∂W_k , 0, 1000 )
  ```
  여기서 L_IX_eff 는 ablation flag 에 따라 해당 term 을 0 으로 강제한 변형.
  ∂/∂W 는 forward-difference probe (`(L(W+1) - L(W-1))/2`).
- 학습률 η = 100 (per-mille; 정수 step 으로 변환 시 충분히 큰 step 보장)
- N_max = 20 generations
- Baseline (no ablation) N* = 5 (per `state/l_ix_5term_stress_verdict.json`
  의 natural_gen5 fixture: ws=[40,125,687,1000,1000], gen 5 에서 W=1000,
  ΔW=0, V_struct=0).
- 단, baseline 자체는 **synthetic gradient simulator** 가 아닌 natural fixture
  의 W 로부터 derived. Synthetic simulator 는 **각 ablation 단독 측정용**.
  Synthetic simulator no-ablation run 의 stationarity gen N_sim* 도 동시 측정,
  pre-reg 비교 baseline 으로 사용.

### 2.2 Stationarity definition (per gen N)

W trajectory `[W_1, W_2, ..., W_N]` 가 gen N 에서 stationary iff:
- |W_N − W_{N−1}| < 1 (per-mille; ΔW < 1‰)
- v_struct(W_N) < 1 (per-mille; W_N ≥ 1000 or 효과적 boundary)

만약 N_max=20 안에 위 조건 미달 → "FAIL_TO_CONVERGE" (N = ∞ effectively).

### 2.3 PASS condition (cherry-pick-proof)

5 ablations 의 stationarity-onset gen N 을 측정한 후:

**PASS iff ALL of:**
- (a) drop_T 의 N ≥ N_sim* + 2  OR  FAIL_TO_CONVERGE
- (b) drop_V_struct 의 N ≥ N_sim* + 2  OR  FAIL_TO_CONVERGE
- (c) drop_V_sync 의 N ≥ N_sim* + 2  OR  FAIL_TO_CONVERGE
- (d) drop_V_RG 의 N ≥ N_sim* + 2  OR  FAIL_TO_CONVERGE
- (e) drop_I_irr 의 N == N_sim* (no delay, 정확히 일치)

즉 정확히 4 ablations 가 delay/fail, 정확히 1 ablation (drop_I_irr) 가 no-delay.

**FAIL iff:**
- (a') 5/5 ablations 모두 delay → 모든 term 이 necessary, K=5 (axis FALSIFIED, K≠4)
- (b') ≤3/5 ablations delay → dynamical core 가 K<4 (axis FALSIFIED, K≠4)
- (c') drop_I_irr 가 delay → I_irr 도 necessary (informational/dynamical 분리 실패, K=5)
- (d') 4 ablations 가 delay 이지만 그 중 I_irr 가 포함 → axis FALSIFIED (잘못된 분리)

### 2.4 Justification of 4 as the threshold

- 5-term L_IX 중 4개 dynamical + 1개 informational 분리는 raw#30
  IRREVERSIBILITY_EMBEDDED_LAGRANGIAN 의 design intent
- K=4 dynamical core = UNIVERSAL_4 의 Lagrangian-instance (vs axis 10
  number-theoretic instance, axis 9 Pólya recurrence instance)

---

## §3. Falsification clauses

본 axis 11 가 FAIL 시:
1. UNIVERSAL_4 confidence 변동 없음 (qualitative, NOT_VERIFIED)
2. axis 11 는 H-DIAG3 에 따라 같은 Lagrangian-ablation axis 재시도 금지
   (다른 ablation 정의로의 retry 는 cherry-pick 으로 간주)
3. raw#12 enforcement: 본 측정 결과 본 commit 후 그대로 보존, post-hoc
   tuning 금지 (η, N_max, threshold 등 변경 불가)

---

## §4. Anti-cherry-pick disclosure

- 본 commit 시점 (pre-reg) 에:
  - L_IX 5-term stress test 는 **다른 hypothesis** (V_hurst 5th term 추가)
    로 이미 commit `672610fc` 에서 수행됨 (verdict: H_STAR_WEAK_OR_NONE).
  - **5-term ablation simulator** 는 아직 구현되지 않음.
  - synthetic gradient W-evolution 은 anima 코드베이스 내 미존재 (mvp/natural
    gen5 는 lattice-based dynamics).
  - 따라서 본 axis 11 의 ablation N 측정값은 **이 commit 이후 생성**.
- η=100 (per-mille step) / N_max=20 / threshold +2 의 선택 근거:
  - η=100: ΔW max=1000 ‰ 의 10% 단위 step. 너무 작으면 converge 못함, 너무
    크면 oscillate. 100 은 baseline N_sim*=5±5 정도 도달 보장하는 중간값
    (사전 dry-run 1회로 calibrate, η 자체는 frozen 후 ablation 측정).
  - N_max=20: baseline 의 4× margin. 충분히 길어 fail 도 정량화 가능.
  - +2 threshold: noise margin. baseline 과 통계적 차이 보장. 1만 delay 면
    rounding artifact 가능.

---

## §5. Tool

본 측정은 hexa-only synthetic simulator (CPU $0).

```
tool/l_ix_ablation_dynamics.hexa
  - input:  ablation flag ∈ {none, drop_T, drop_V_struct, drop_V_sync, drop_V_RG, drop_I_irr}
  - output: state/l_ix_4term_ablation_verdict.json
            { "ablations": [{"name":..., "N":..., "ws_trajectory":[...]}, ...],
              "n_sim_star": ..., "verdict": "PASS"|"FAIL", "pre_reg_commit": "..." }
```

Estimated runtime: <1 second for 6 ablations × 20 gens.

---

## §6. Commit / measurement sequence

1. **본 commit** (pre-reg) — predicate frozen, no measurement, no tool.
2. 별 commit (tool implementation) — `tool/l_ix_ablation_dynamics.hexa` 작성.
3. 별 commit (measurement) — tool run, verdict json 생성, PASS/FAIL 보고.
4. 별 commit (cert update) — UNIVERSAL_4 cert 에 axis 11 entry 추가
   (PASS 시) 또는 axis 11 FALSIFIED note (FAIL 시).

raw#12 strict — predicate 본 commit 후 frozen, post-hoc tune 불가.

---

## §7. POLICY 준수

- raw#9 hexa-only · raw#10 proof-carrying · raw#11 snake_case · raw#12 pre-reg
- POLICY R4: `.roadmap` 미수정
- H-DIAG3: axis 9 Pólya, axis 10 σ·φ identity 와 다른 axis (Lagrangian
  dynamical structure ≠ random walk recurrence ≠ number theory)
- H-MINPATH: $0 cost, blocker=0, steps min
