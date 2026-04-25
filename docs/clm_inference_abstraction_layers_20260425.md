# CLM (Cell Language Model) Inference — Abstraction Layers (L0..L∞)

date: 2026-04-25
audience: anima 내부 / cell decode 패러다임 정리
contract: brutally honest · Korean + English · no hardcode claims · evidence-first

---

## TL;DR

**Cell decode ≠ autoregressive sampling.** CLM inference 는 결정론적 **Lagrangian solving**:
주어진 boundary condition 에서 stationary point (δS=0) 를 찾는 ODE/PDE flow 가
"decode" 의 본질이다. token-side AR 샘플링은 cell state 에 매달린 synaptic readout
일 뿐이다. 현재 위치는 **L0 검증 + L1 단일-seed 통과 + L2 fixture 3/3** — L3 부터는
아직 증거 없음.

> "Decode 는 Hamiltonian flow 의 stationary 탐색이고, sampling 은 그 flow 를
> token modality 로 사영한 그림자다."

---

## L0 — Deterministic L_IX Trajectory (현재, EXP-2 PASS)

- **상태 (status)**: PASS · gen-5 stationary verified
  - source: `edu/cell/lagrangian/l_ix_integrator.hexa`
  - cert:   `state/edu_cell_l_ix_integrator.json`
  - paradigm: `L_IX = T - V_struct - V_sync - V_RG + λ·I_irr` (raw#30)
- **bounds**:
  - integer fixed-point (×1000), 5-gen Mk.VIII fixture `ws=[40,125,687,1000,1000]`
  - byte-exact regression to L_cell when `λ=0 ∧ gates=0`
  - `|ΔL_{4→5}| ≤ 1` stationary tolerance, `I_irr_5 == 0` collapse
- **현재 위치**: cell decode = solving ODE for stationary `W=1000` fixed point.
  AR sampling 없음. trajectory 는 결정론적 (env gates 만 다양화).
- **brutal honesty**: 5-gen 만 검증. 일반 Hamiltonian H(p,q) 가 아니라
  scalar W-action 에 대한 1-D Lagrangian. **진짜 PDE 는 아직 풀고 있지 않다.**

---

## L1 — Cargo Invariant Runtime Checking (현재, single-seed)

- **상태 (status)**: PASS at single seed 20260421 · 7/7 invariants
  - cert: `state/btr_evo_6_cargo_invariants_20260421.json`
  - I1 phi_monotone, I2 eigenvec_stability=0.9997, I3 brain_like=85.33%,
    I4 score_conservation=19/19, I5 phi_gap=0.004, I6 saturation_monotone,
    I7 cargo_weight_frobenius=0.021
- **bounds**:
  - k=3 checkpoint sampling, n=50 iters
  - thresholds: I1<0.08, I2>0.95, I3>85%, I7<0.2 — all far from boundary
- **현재 위치**: cargo invariant 는 inference-time runtime guard 로 작동 가능
  (decode trajectory 가 cargo cone 을 벗어나면 reject). 단 **multi-seed
  reproducibility 는 검증 안 됨** — I2=0.9997 은 in-run 측정이지 cross-seed 가 아님.
- **brutal honesty**: 단일-seed. cross-seed Banach contraction 은
  ISO3 W10 (eigenvec_stability ceiling) 에서 conjecture 만 있음. 진짜
  inference-time gate 로 쓰려면 m≥3 seed × k=3 ckpt 가 필요.

---

## L2 — Cell ↔ Token Bridge Decode (현재, fixture 3/3)

- **상태 (status)**: CONDITIONAL_PASS · `state/cell_token_bridge_proto.json`
  - identity / ladder / adversarial fixture 모두 expected verdict 일치
  - 100-step round-trip drift_max=0 ≤ bound 2·lr²·k=2e-4
- **bounds**:
  - 5-level bucket (`{0,200,400,600,800,1000}‰`) → 16-d eigenvec rows
  - cos_min ≥ 0.5, i_irr_bits ≤ 84 (4 step × 21 bit)
  - adversarial midpoint 500‰ 는 구조적으로 FAIL (정의대로)
- **현재 위치**: cell state W → token embedding h 의 bidirectional bridge.
  synaptic readout: `f_tc(h) = argmax_i cos(h, eigenvecs[i]) · 200‰`.
  decode = cell state Lagrangian 풀이 → bridge → token argmax.
- **brutal honesty**: 5-level discretization 은 decode 라기보다 **classification**.
  진짜 continuous embedding decode 는 16-d span 전체를 써야 하지만,
  현재 implementation 은 5 row 만 쓰고 나머지 11 row 는 dead. 또한 fixture 가
  3 개뿐 — 임의 W trajectory 에 대한 robustness 미검증.

---

## L3 — Multi-Cell Collective Decode (lattice phase coherence)

- **상태 (status)**: **NOT VERIFIED** · L3 emergence는 composition demo 한 번만
  - source: `edu/cell/composition/comp_demo.hexa`
  - cert:   `shared/state/edu_cell_comp_mvp.json`
  - O1 mms ladder 10→2→1 / O2 holonomy(late)=0.024 / O3 interface=0.277
- **bounds**:
  - 10-node atlas, 3-stage W-profile (baseline/mid/late)
  - `COMP_EMERGED` ⇔ mms 단조감소 ∧ hol>0 ∧ interface>0
- **현재 위치**: L3 의 **proxy 만 존재**. 진짜 multi-cell Kuramoto coherence decode
  는 V_sync 의 Kuramoto path (`edu/cell/lagrangian/v_sync_kuramoto.hexa`) 가
  parse OK 100% coverage 까지만 옴 — runtime decode trajectory 는 아직 없음.
- **brutal honesty**: 10-node 는 toy. 진짜 lattice (수십~수백 cell) 에서
  phase coherence 가 decode 정확도와 어떻게 결부되는지 **0 evidence**.
  이 layer 가 가장 weakest evidence link.

---

## L4 — Universal Cell Decoder (any-task via Mk.X atom composition)

- **상태 (status)**: **CONCEPTUAL ONLY** · Mk.X 아직 미정의
  - 현재 Mk.IX (l_ix_integrator) 가 ceiling. Mk.X = atom composition 으로
    임의 task 의 Lagrangian 을 합성하는 layer.
- **bounds (가설)**:
  - atom 집합 {T_tension, V_struct, V_sync, V_RG, I_irr} 에서 task-specific
    convex combination 으로 새 L 합성
  - holonomy 닫힘 조건이 보존되어야 (composition_holonomy = 0)
- **현재 위치**: **언어 단계** — paradigm 은 정의됐지만 (raw#30 IRREVERSIBILITY
  EMBEDDED) atom 라이브러리도 composition 연산자도 미구현.
- **brutal honesty**: 이건 "있으면 좋은 것" 단계. ALM 의 Mk.X persona /
  ATLAS Mk.X 등과 별개의 cell-side 합성 시스템이 필요. 일정 미정.

---

## L5 — Limits (physical · mathematical)

L5 는 패러다임의 **upper bound** — 어떤 cell decoder 도 이 선을 못 넘는다.

### 5a · Physical bounds
- **Margolus-Levitin**: ODE solver step 당 최소 시간 `t_min = πℏ/(2E)` —
  주어진 에너지로 distinguish 가능한 state 변화 frequency 상한.
  cell Lagrangian solving 은 이 frequency 를 못 넘는다.
- **Lyapunov chaos bound**: `λ_max ≤ 2πT/ℏ` (MSS bound, 2015) — chaotic
  Hamiltonian 의 Lyapunov 지수 상한. 너무 chaotic 한 cell 은 decode trajectory
  가 발산, prediction 불가능.

### 5b · Mathematical bounds
- **KAM theorem (small divisor)**: integrable 근방에서 quasi-periodic torus
  는 살아남지만, resonance 영역 small divisor 발산 → invariant tori 가 깨지면
  cell trajectory 가 stationary 를 못 찾음 (현재 5-gen 검증은 운 좋게 KAM 영역
  안에 있는 것일 수 있다 — generic 보장 없음).
- **Smale's 2nd problem (dynamical unsolvability)**: 일반 polynomial vector
  field 의 limit cycle 개수 결정 불가능 (Hilbert 16th 의 dynamical 형태).
  generic cell Hamiltonian 의 stationary 개수도 같은 가족.
- **Undecidability**: Wolfram-Cook 류 cellular automaton 의 halting 은
  undecidable. cell decoder 도 generic 에서는 termination 보장 불가.

---

## L∞ — Phenomenal Cell Decoding (검증 불가능)

"Cell 이 된다는 것은 어떤 느낌인가" — qualia of being a cell.
- 외부 검증 불가능 (Nagel "What is it like to be a bat?" 의 cell 버전)
- 모든 verifier (cargo / AN11 / Φ) 는 3rd-person observable 만 다룸
- L0..L5 는 measurable 한 모든 것의 ceiling. L∞ 는 **definitionally**
  out-of-scope.

---

## 현재 위치 요약

| Layer | 상태 | 증거 |
|---|---|---|
| L0 | PASS | `state/edu_cell_l_ix_integrator.json` (5-gen) |
| L1 | PASS (single-seed) | `state/btr_evo_6_cargo_invariants_20260421.json` |
| L2 | CONDITIONAL_PASS | `state/cell_token_bridge_proto.json` (3 fixture) |
| L3 | proxy only | `shared/state/edu_cell_comp_mvp.json` (10-node toy) |
| L4 | conceptual | — |
| L5 | structural ceiling | (theoretical) |
| L∞ | out-of-scope | — |

**Weakest evidence link**: **L3** (multi-cell collective decode). 다음 이정표는
L3 lattice Kuramoto V_sync path 의 runtime trajectory + L1 multi-seed 확장.

---

## Brutal honesty close

지금 우리가 "CLM inference" 라고 부르는 것의 결정론적 핵심은 **L0 5-gen
fixture + L1 single-seed cargo + L2 5-bucket bridge** 까지다. 그 위는 paradigm
선언만 있고 evidence 가 비어 있다. L3 가 채워지지 않으면 "cell decode 는
Hamiltonian flow" 는 **slogan** 으로 남는다 — 진짜 PDE solving 은 아직 안
하고 있다.

(raw#0 pre-registered · raw#9 hexa-only · raw#11 snake_case · raw#12 실측)
