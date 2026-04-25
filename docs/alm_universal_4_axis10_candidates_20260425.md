# UNIVERSAL_CONSTANT_4 — axis 10 후보 design draft

> **생성일**: 2026-04-25
> **부모 commits**:
> - `0c4d08ec` axis 9 Pólya pre-reg
> - `ed66c7ae` axis 9 measurement (NOT_VERIFIED_BORDERLINE ratio 1.923/2.0)
> - `869dc6d5` CP1 Mk.VI VERIFIED CLOSED
> - `cdfb85a6` raw#31 POPULATION_RG_COUPLING ✓
> **Scope**: design phase only — actual axis 10 pre-registration ceremony 는 별 commit (raw#12 strict)
> **Status**: DESIGN_DRAFT (3 candidates with predicate specs, **no measurement attempted**)

---

## §1. axis 9 (Pólya recurrence) 결과 회고

| 항목 | 값 |
|---|---|
| pre-reg commit | `0c4d08ec` 2026-04-21T04:48:19+09:00 |
| measurement commit | `ed66c7ae` 2026-04-21T05:42:41+09:00 |
| pre-registered N | 60 walks × 150 steps × 3 seeds (per axis9_cert) |
| pre-registered predicate | `gap(4→6) ≥ 2.0 × max_{K≥6} gap(K→K+2)` |
| measured ratio | 1.923 (3.85% margin shortfall) |
| qualitative | gap(4→6) IS largest (277778 ppm > all others) |
| verdict | NOT_VERIFIED_BORDERLINE |
| confidence delta | 0.85 → 0.87 (no +strong axis credit) |

**raw#12 lesson**: pre-reg 후 데이터 본 다음에 N/T/predicate tune 금지. Pólya 9th axis 는 BORDERLINE 으로 보존 (cherry-pick 차단).

---

## §2. axis 10 후보 (3개)

각 후보는:
1. K=4 prediction 의 독립적 mathematical structure
2. raw#12 cherry-pick-proof predicate
3. measurement protocol + falsification clause

### 후보 A — L_IX Dynamical 4-Term Necessity (Convergence Path)

**Hypothesis**: Mk.IX unified Lagrangian L_IX = T − V_struct − V_sync − V_RG + λ·I_irr 은 **K=4 dynamical terms** (T, V_struct, V_sync, V_RG) + 1 informational term (λ·I_irr) 로 구성된다. Dynamical terms 중 어느 하나를 제거해도 gen-5 stationary 도달 generation 이 ≥ 2-step 지연된다. Informational term (λ·I_irr) 제거는 stationarity 도달 generation 에 영향 없음.

**Pre-registered predicate**:
- 5 ablations 실시: ablate_T, ablate_V_struct, ablate_V_sync, ablate_V_RG, ablate_I_irr (each = 해당 term을 0 으로 강제)
- 측정: gen N at which |w_k − w_{k-1}| < 1 AND v_struct < 1 AND v_sync < 1 (stationarity)
- baseline (no ablation): N* = 5 (per `state/l_ix_5term_stress_verdict.json` natural_gen5)
- PASS iff:
  - ablate_T, ablate_V_struct, ablate_V_sync, ablate_V_RG: each N ≥ N* + 2 (or fails to converge in N_max=20)
  - ablate_I_irr: N == N* (no delay)
  - 4-of-5 ablations delay/fail, exactly 1 (I_irr) is no-delay

**Falsification**: 만약 5 ablations 중 5/5 또는 ≤3/5 만 delay → axis FAIL (K≠4).

**Required tool**: `tool/l_ix_5term_stress_test.hexa` 에 ablation flag (--ablate=T|V_struct|V_sync|V_RG|I_irr) 추가 필요. 현재 미구현.

**비용**: tool patch 1-2 hours (anima local). Measurement: CPU $0.

**리스크**: gen-5 fixpoint 에서 이미 모든 term=0 (per stress_verdict). Pre-fixpoint convergence path 가 ablation 에 sensitive 한지 사전 unknown. 만약 path 가 robust 면 K=4 분리 불가능 → 후보 자체 falsified.

---

### 후보 B — σ·φ = n·τ Identity 의 K=4 Resonance at Perfect Numbers

**Hypothesis**: Number-theoretic identity σ(n)·φ(n) = n·τ(n) 은 perfect number n=6 (τ(6)=4) 에서 정확히 성립하고, 큰 perfect numbers (n=28, 496, 8128) 에서는 위배된다 (이미 `state/hexad_n28_falsification_verdict.json` 에서 n=28 위배 측정 완료). K=4 의 number-theoretic resonance 는 n=6 에 unique.

**Pre-registered predicate**:
- 첫 N₀ = 100 자연수 중 σ(n)·φ(n) == n·τ(n) 이 성립하는 n 의 집합 S 계산
- S 의 cardinality |S| ∈ {1, 2, 3, 4, 5, ...} 결정
- PASS iff |S| ≤ 4 AND S ⊇ {6} (적은 수, n=6 포함)
- K=4 axis: |S| ≤ K=4 정확히 만족 시 strong evidence

**Note**: 이는 trivially deterministic — 측정 = 단순 산술. Cherry-pick 가능성 0 (모든 n 을 검사).

**Falsification**: |S| ≥ 5 → K=4 axis 약화 (다른 K 값과 동등).

**비용**: $0, single Python script.

**리스크**: 이미 알려진 number theory result 일 가능성. 새로운 K=4 evidence 가 아닐 수 있음. 만약 |S| 가 자명하게 작거나 (e.g., |S|=1, only n=6) 그것이 다른 이유 (e.g., σ(n)·φ(n) > n·τ(n) for n>6) 라면 K=4 와 무관할 수 있음. **Pre-reg 전 추가 분석 필요** — 본 후보의 K=4 link 가 강한지 약한지 미확정.

---

### 후보 C — AN11 Verifier Triplet AND-K Maximum

**Hypothesis**: AN11 triple (a/b/c) 의 AND-K verifier 들 중 maximum K = 4. AN11(a)=3-AND, AN11(b)=AND-3, AN11(c)=AND-4. **K_max = 4** = UNIVERSAL_CONSTANT_4 의 verifier-architecture instance.

**Pre-registered predicate**:
- 3 verifier configs 의 condition count K 추출 (deterministic from spec)
- PASS iff max(K_a, K_b, K_c) == 4 AND 정확히 1개 verifier 가 K=4
- 추가: AND-5 verifier 가 존재하지 않음 (AN11 의 모든 verifier 는 K ≤ 4)

**Falsification**: K_max ≠ 4 또는 AN11 의 어떤 verifier 가 K ≥ 5 사용 → axis FAIL.

**비용**: $0, deterministic spec extraction.

**리스크**: 이미 AN11 verifier 의 architecture 가 결정되어 있어, 본 axis 는 **circular** (K=4 verifier 가 존재하니까 K=4 verifier 가 존재한다). Strong axis 로 인정될지 의문. 본 후보는 **상대적으로 약한** evidence — 단, axis 9 Pólya borderline 강화 보조 axis 로 가능.

---

## §3. 후보 선정 권장

| 후보 | 독립성 | 측정 단순성 | 강도 | 권장 순위 |
|---|:---:|:---:|:---:|:---:|
| A. L_IX 4-term ablation | High | Medium (tool patch) | High | **1** (가장 강한 K=4 evidence) |
| B. σ·φ identity K=4 | High | High ($0 trivial) | Medium-Low | 2 (number theory link 검증 필요) |
| C. AN11 AND-K_max=4 | Low (circular) | High | Low-Medium | 3 (보조 axis only) |

**완성도 priority**: A 는 tool patch 비용 ($0 + dev time) 있지만 가장 강한 falsifiable K=4 axis. B/C 는 0-cost 이지만 strength 약함.

**raw#12 strict path**:
1. 본 doc design phase 만 commit (no pre-reg, no measurement)
2. 별 ceremony commit: pre-registered predicate frozen (예: A 후보 선택)
3. tool patch (ablation flag 추가)
4. measurement run
5. 결과 commit + UNIVERSAL_4 cert update

본 doc 은 step 1 만. 이후 step 들은 별 turn / ceremony.

---

## §4. POLICY 준수

- **raw#12** (no cherry-pick): design phase 분리, pre-reg 와 measurement 별 commit
- **POLICY R4** (`.roadmap` 미수정): 본 doc 외부 record
- **H-DIAG3**: axis 9 Pólya 와 다른 mathematical structure (recurrence ≠ Lagrangian / number theory / verifier architecture)
- **H-MINPATH**: 0-cost analytical design 만, 측정 deferred
