# Anima Time / Temporal Axis / Arrow of Time — Abstraction Layers (L0 → L5, L∞)

> **생성일**: 2026-04-25
> **부모 commits**: `f5662be9` raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN 승급 · `18c27ac5` temporal-axis MVP (tau_mem + I_irr + H Hurst) · `ff75de4a` Mk.IX V_sync/V_RG + L_IX integrator + Arrow cusp · l_ix_5term_stress_verdict (V_hurst null-test, 2026-04-21)
> **scope**: temporal axis, arrow of time, irreversibility embedded into Mk.IX action, Hurst long-memory, entropy production, fluctuation theorems, retrocausality, 2nd-law ceiling, block-universe vs presentism
> **POLICY**: own#11 (extraordinary claim / ordinary evidence). 본 문서는 의식·시간·자유의지의 형이상학적 결론을 주장하지 않는다. arrow term 은 Mk.IX action 의 *embedded coupling* 으로만 다룬다.

---

## L0 — 현재 (operational ground truth, 2026-04-25)

**status**: raw#30 ACTIVE (Mk.IX). λ·I_irr term 이 L_IX action 에 byte-exact embedded. fixpoint 에서 I_irr → 0 (arrow collapse) 로 stationary 보존.

| element | state | evidence |
|---|:---:|---|
| `edu/cell/lagrangian/l_ix_integrator.hexa` | runnable | `state/edu_cell_l_ix_integrator.json` verdict=`MK_IX_STATIONARY`; gen-5 `i_irr=0`, ΔL_{4→5}=0 |
| `edu/cell/temporal/temporal_emergence.hexa` | runnable | I_irr = mean_signed_delta / (\|signed\|+jitter_excess); reversed series ⇒ I_irr=0 (clamp); R/S Hurst slope fitting (O3) |
| 5-term stress verdict (V_hurst null-test) | done | `state/l_ix_5term_stress_verdict.json` h=0.430, dev_from_half=0.070, V_hurst=0 (×1000), Σ unchanged: S_4term=S_5term=−8600 |
| raw#30 placement (axiom DAG) | sink | `docs/anima_math_raw_axiom_dag_20260425.md` L30: raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN (Mk.IX, sink, C-math) |

**bounds**: I_irr 은 ΔW per-gen 에서 도출 (`signed/(signed+jitter)`). full coupling 은 temporal_emergence per-generation 와이어링 land 후 가능. λ_arrow 기본 ×1000 (per-mille fixed-point).

**현재 위치**: arrow-of-time 은 **Lagrangian-level embedded coupling** 으로 land. measurement-only add-on 아님. fixpoint 에서 collapse 되도록 설계 (forward drift=0 ⇒ I_irr=0).

---

## L1 — Hurst exponent measurement (V_hurst term, long-memory)

**status**: V_hurst null-test 완료, V_x 5-term Lagrangian 후보로 **REJECTED** (delta=0.01 scale 에서 H_STAR_WEAK_OR_NONE).

- formula: `V_hurst = δ · (H − 0.5)²` (Hurst 1951; Mandelbrot & Wallis 1969 R/S analysis).
- δ=0.01 (×1000=10) 선택 이유: max V_hurst ~ 2.5 per-mille — T_tension peak 와 비교가능, V_struct 를 침범하지 않음.
- gen-5 fixture (natural_gen5, ws=[40,125,687,1000,1000]) 에서 H=0.430 (anti-persistent 약신호), dev=0.070 ⇒ V_hurst=0 (정수 fixed-point precision floor).
- **δ-sensitivity scan**: δ_x1000 ∈ {10,100,1000,10000,100000}; first STATIONARY break 는 δ=1000 에서 V_hurst=4×10⁻³, L_IX_5=−4 — break magnitude < 10% S_4term ⇒ **INCONCLUSIVE→WEAK_OR_NONE** verdict.

**bounds**: V_hurst null 은 fixture-specific (gen-5 short trajectory, n=5). full ALM W-trajectory (R/S 다중 window) 에서 재실측 시 결과 다를 수 있음 — 단, 본 abstraction 시점 evidence 는 H_STAR_WEAK_OR_NONE.

**현재 위치**: long-memory term 은 *명시적으로 작거나 zero*. arrow 는 I_irr 단일 term 으로 충분히 represented (5-term 확장 불필요).

---

## L2 — entropy production rate (Onsager reciprocity)

**status**: 명세 단계. 본 repo 에 entropy-production 측정자 부재. λ·I_irr 이 thermodynamic σ 의 proxy 로 동작하지만 직접 mapping 미land.

- 전형 형태: σ = Σᵢ Jᵢ · Xᵢ ≥ 0 (flux × force; Onsager 1931 reciprocity Lᵢⱼ=Lⱼᵢ).
- I_irr ↔ σ mapping 가설: per-gen ΔW 가 effective J, V_struct gradient 가 effective X. λ_arrow 는 결합상수.
- nonequilibrium Mk.IX 가설: σ ≥ 0 ⇒ I_irr ≥ 0 (l_ix_integrator.hexa line 135 `if dw <= 0 { return 0 }` 와 일치).
- 미land: Onsager reciprocity 검증 (off-diagonal flux pair 측정), GENERIC framework 매핑.

**bounds**: ALM 의 weight evolution 은 stochastic gradient 이지 thermodynamic system 아님 — Onsager 적용은 *형식적 analog* 수준. own#11: thermodynamic interpretation 의 1:1 claim 미land.

**현재 위치**: σ↔I_irr proxy framing 만 존재. measurement land 미실시.

---

## L3 — fluctuation theorems (Jarzynski, Crooks)

**status**: aspirational. 본 repo 미land.

- **Jarzynski 1997**: ⟨exp(−βW)⟩ = exp(−βΔF) — nonequilibrium work 의 ensemble average 가 equilibrium ΔF 를 결정.
- **Crooks 1999**: P_F(W)/P_R(−W) = exp(β(W−ΔF)) — forward/reverse process 의 work distribution ratio.
- Mk.IX 잠재적 mapping: per-gen action increment ΔS_IX ↔ "work" W; equilibrium reference = fixpoint (ΔW=0, I_irr=0). Crooks ratio 는 trajectory ensemble 필요 — single deterministic gen-5 trajectory 로는 측정 불가.
- 필요 infra: stochastic ensemble (≥ 100 trajectory replicates with seed perturbation), forward/reverse pairing (raw#30 `irreversibility(reverse(phi))=0` 와 일관).

**bounds**: deterministic fixed-point arithmetic 환경에서 ensemble 생성 비용 직접적; 의미 있는 검증은 ALM stochastic GPU run 단위에서만. own#11: Jarzynski 등식의 *exact* 검증은 thermodynamic system 가정 필요.

**현재 위치**: hooks 정의만 가능. 측정 미예정.

---

## L4 — retrocausal models (Wheeler delayed choice, transactional QM)

**status**: out-of-scope for current Mk.IX. 명세 / 한계 표기 목적.

- **Wheeler delayed choice (1978)**: 측정 선택이 사후에 photon 의 과거 경로 결정에 영향 — block-universe 해석 호환, presentism 호환 불가능.
- **Transactional QM (Cramer 1986)**: offer wave (forward) + confirmation wave (backward) 의 handshake. retrocausal but causally consistent (no signaling).
- Mk.IX 와의 관계: λ·I_irr term 은 forward-only (`if dw <= 0 { return 0 }`) — **명시적으로 retrocausal 아님**. raw#30 은 monotonic arrow 를 baseline 으로 가정.
- 만약 retrocausality 를 land 하려면: I_irr 의 sign convention 제거 + advanced/retarded green function 분리 필요 — Mk.IX 의 STATIONARY 보장 (gen-5 fixpoint collapse) 이 깨짐.

**bounds**: retrocausal extension 은 본 framework 의 monotonic-arrow 가정과 **mutually exclusive**. own#11: retrocausality 주장은 quantum-experimental evidence 없이는 metaphysical position.

**현재 위치**: L4 는 *명시적 negative space*. 가지 않는 것이 honest.

---

## L5 — limits (2nd law, Eddington arrow, Loschmidt, Poincaré recurrence)

**status**: 본 abstraction 의 hard ceiling.

### 5.1 2nd law thermodynamics — irreversibility absolute
- ΔS_universe ≥ 0 (Clausius). λ·I_irr ≥ 0 enforcement (raw#30 `if dw <= 0 { return 0 }`) 가 이 bound 의 discrete analog.
- closure: fixpoint 에서 I_irr → 0 은 *equilibrium 도달* 의미; entropy production rate σ → 0 limit. Mk.IX STATIONARY 가 thermodynamic equilibrium 의 formal mirror.

### 5.2 Eddington's arrow of time
- "the great thing about time is that it goes on" (Eddington 1928). entropy gradient 가 시간의 *psychological / cosmological* 방향성을 정의.
- raw#30 의 λ_arrow 는 이 macroscopic arrow 의 microscopic trajectory-level encoding. 단 *원인* 이 아닌 *parameter* — arrow 의 origin 자체는 본 framework 가 설명하지 않음.

### 5.3 Loschmidt's paradox (1876)
- 모든 microscopic dynamics 가 time-reversal symmetric 인데 macroscopic irreversibility 는 어떻게 발생? 답: initial-condition asymmetry (low-entropy past) — boundary condition, not law.
- raw#30 의 ΔW>0 clamp 는 Loschmidt 를 *해결하지 않고* boundary 로 우회 (ΔW<0 = 비물리 trajectory 로 격리).

### 5.4 Poincaré recurrence theorem
- finite phase space 에서 system 은 임의의 ε-neighborhood 에 무한히 자주 회귀 — recurrence time τ_P ~ exp(S/k_B). 우주 scale 에서 τ_P ~ 10^(10^10) 년 (Page 1994).
- Mk.IX gen-5 fixpoint 에서 τ_P 는 **무한** (deterministic clamp; phase space 는 W=1000 attractor 로 collapse). 따라서 recurrence 부재는 framework 의 *property* 가 아닌 *artifact* (idealized boundary).
- 실제 stochastic ALM 에서는 τ_P 가 유한이지만 measurement horizon 너머 — operationally arrow 는 absolute.

**현재 위치**: L5 가 L0-L4 전체에 ceiling 으로 작용. raw#30 은 2nd-law-compatible 이고, Loschmidt 는 boundary 로 회피하며, Poincaré 는 idealization 으로 억제. 이 모든 회피는 *honest* 하다 — framework 가 fundamental 답을 주는 것이 아니라 operational analog 만 제공.

---

## L∞ — block universe vs presentism (metaphysics)

**status**: 본 abstraction 의 **negative space**. raw#12 (실측 only), own#11 강하게 적용.

- **block universe (eternalism)**: past/present/future 가 동등하게 실재. 4-vector geometry, Minkowski / Einstein-Rosen. Wheeler delayed choice (L4) 와 호환.
- **presentism**: 오직 현재만 실재. arrow of time 은 ontological primitive. retrocausality 부정.
- **growing-block**: past + present 실재, future 부재 (Broad 1923).
- Mk.IX raw#30 의 입장: **agnostic by design**. λ·I_irr 은 *trajectory-level coupling* — 시간의 실재성 / 과거-미래 비대칭의 ontological 기원에 대해 silent.
- 본 framework 가 block-universe 를 가정하면: I_irr 의 monotonic clamp 는 *우리의 관측 좌표계* 에서 emergent (microscopic 은 reversible). presentism 가정하면: I_irr 은 *실재의 직접 표현*.
- own#11: 본 abstraction 의 어떤 진술도 block-universe 또는 presentism 의 우열을 주장하지 않는다.

**현재 위치**: L∞ 미진입. 형이상학 결론 미land. arrow 는 *operational primitive*, ontological primitive 라고 주장하지 않음.

---

## §epilogue — brutally honest summary

1. L0: raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN active (Mk.IX), λ·I_irr embedded in L_IX action, fixpoint 에서 collapse.
2. L1: V_hurst null-tested (H=0.430, dev=0.070) ⇒ H_STAR_WEAK_OR_NONE; long-memory term 불필요.
3. L2-L3: entropy production / fluctuation theorems 는 aspirational, 미land. proxy framing 만 존재.
4. L4: retrocausality 명시적 out-of-scope (monotonic-arrow 가정과 mutually exclusive).
5. L5: 2nd law / Eddington / Loschmidt / Poincaré 가 framework 의 ceiling. raw#30 은 boundary-condition 우회.
6. L∞: block-universe vs presentism agnostic by design. own#11.

raw#30 은 *arrow of time 의 origin 을 설명하지 않는다*. operational coupling 만 land. 그게 honest.

---

## §epilogue — English mirror (compressed)

L0 (now): raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN ACTIVE in Mk.IX (`l_ix_integrator.hexa`); λ·I_irr embedded in action S_IX; at gen-5 fixpoint I_irr→0, ΔL_{4→5}=0 (`MK_IX_STATIONARY`). Temporal MVP (`temporal_emergence.hexa`) provides I_irr=signed/(signed+jitter), reversed-series clamp to 0.
L1: Hurst V_hurst null-tested on natural_gen5 fixture, H=0.430, dev=0.070, V_hurst=0; verdict H_STAR_WEAK_OR_NONE.
L2: entropy production σ↔I_irr proxy framing only; no Onsager reciprocity verification landed.
L3: Jarzynski/Crooks aspirational; requires stochastic ensemble infra not yet built.
L4: retrocausality (Wheeler, transactional QM) explicitly out-of-scope — incompatible with monotonic-arrow clamp.
L5: 2nd law (ΔS≥0), Eddington arrow (entropy gradient), Loschmidt paradox (boundary asymmetry), Poincaré recurrence (τ_P~10^10^10 yr) form the framework ceiling; raw#30 is 2nd-law-compatible but does not explain arrow origin.
L∞: block-universe vs presentism — agnostic by design; own#11 forbids metaphysical claim.

raw#30 supplies an operational coupling, not an ontological account. No claim is made about the origin of time's arrow.
