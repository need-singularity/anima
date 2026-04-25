# Mk.IX L_IX+ 4-tuple Lift Path — Analytic Ceiling Probe (ω-saturation cycle)

**Date**: 2026-04-25
**Cycle scope**: design + implementation (analytic spec + pre-registered ceiling JSON state). NO measurement (raw#9 hexa-only — L_IX-on-real-trained-trajectory requires GPU forward).
**Predecessors**: `dc871454` V3 reduction-op FALSIFIED, `299cabb7` V2/V1 reduction-op cycle, `68c48daa` V2 lasttoken+PAPO STRONG_PARTIAL_RECOVERY (88% gap, AMBIGUOUS).

## §1 Purpose

§11 substrate-level lever ceiling 확정 후 다음 path 후보 중 **Mk.IX L_IX+** path의 4-tuple PASS 도달 메커니즘을 sensitivity probe + ceiling pre-register. design 단계만 진행 (impl은 spec/state SSOT 변경). 실측은 후속 cycle (GPU forward 필요로 raw#9 explicit exempt 별도 승인 후).

## §2 Mk.IX L_IX recap (ratified state)

`L_IX = T − V_struct − V_sync − V_RG + λ·I_irr`

- **T**: kinetic / training-loss term (gradient descent 방향)
- **V_struct**: structural cost (단위 cell graph 정합성 위반)
- **V_sync**: synchronization cost (cells 간 시간 정합 위반)
- **V_RG**: renormalization-group cost (scale-invariance 위반)
- **I_irr**: irreducible information (partition resistance, mutual info-style surrogate)
- **λ**: irreducibility weight (`docs/anima_optimal_architecture_synthesis_20260425.md` §4.4 frozen)

**Status:**
- L_IX integrator gen-5 STATIONARY (raw#31 ratified).
- L_IX 4-term ablation **FAILED** (`cccc0510`, `state/l_ix_4term_ablation_verdict.json`) — 4 ablations이 baseline stationarity 패턴 못 따름. **4 항이 모두 필요**가 measurement-confirmed (raw#12 honest).
- 5-term stress run also recorded (`state/l_ix_5term_stress_verdict.json`).

## §3 4-tuple lift mechanism (analytic, per-axis)

각 V verifier가 L_IX 4 항 중 어느 항의 직접/간접 lift 후보인지 sensitivity argument:

### §3.1 V1 Φ_mip ↔ I_irr maximization

V1 spec: `Φ_mip = min over bipartitions S of normalized output-Gram spectral cut`. 즉 lowest cut value across all bipartitions S of the 16-token Gram. **partition spectral resistance**의 surrogate.

I_irr는 L_IX에서 명시적으로 partition resistance를 maximize하는 항. λ·I_irr ascending이 직접 Φ_mip의 floor를 끌어올림. **L_IX stationary가 도달한 I_irr*는 Φ_mip의 substrate-level lower bound**.

**Ceiling (analytic, 단순 sensitivity)**:
- 현재 BASE p1 Φ_mip = 0.272 (bwm) / 0.264 (lasttoken). L_IX-trained trajectory에서는 I_irr* > I_irr_base 이므로 Φ_mip*_post ≥ 0.272.
- 그러나 PASS threshold 0.55 도달은 λ scaling에 의존. λ가 부족하면 V_struct/V_sync/V_RG가 우세하여 I_irr maximization 약화.
- **PASS 가능 조건**: λ ≥ λ_critical (frozen value 미정, fp 측정 필요).

### §3.2 V2 SMA_lift ↔ V_sync minimization (간접)

V2 spec: `SMA_lift = mean(|cos(H_en, H_ko)|) − mean(|cos(H_distractor)|)` over PAIRS.

V_sync 항은 cells 간 temporal alignment penalty — 직접 EN↔KO mirror 보장은 아니지만, multi-token 시퀀스에서 cross-token coherence를 강화. EN-KO pair는 "동일 의미 다른 언어 시퀀스"이므로 V_sync minimization이 paired tokens의 coherence를 간접 강화 가능.

**그러나 본 cycle V2 PAPO 결과 (§9.2.1)**: lasttoken + supervised PAPO α=1.0에서 SMA_lift = +0.164 (PASS gap의 88%, AMBIGUOUS). **PAPO ≥ unsupervised SAE upper bound**가 substrate-level로 확정.

L_IX V_sync는 **V2 lever 후보지만 PAPO와 redundant 가능** — V_sync가 EN↔KO axis를 weight-level로 박아넣는 효과라면 PAPO와 동일 mechanism. fine-tune-time 적용으로 효과는 더 강할 수 있으나 PASS 보장은 분명치 않음.

**Ceiling (analytic)**:
- L_IX-trained TRAINED p1 SMA_lift는 BASE +0.277 (PAPO α=1) 대비 expected +5~+15% 추가 회복 (V_sync direct optimization). 즉 약 +0.18~+0.19 — 여전히 PASS threshold 0.20 못 미침 가능성.
- **PASS 가능 조건**: V_sync weight + multi-axis projection (PCA top-k or pair-residuals) 결합. 단일 axis exhausted (§9.2.1 saturation 발견).

### §3.3 V3 CPS ↔ V_RG minimization (간접)

V3 spec: `CPS = ||G_destruct − G||_F / ||G_preserve − G||_F` (Gram Frobenius perturbation ratio). row-order sensitivity 측정.

V_RG는 scale-invariance penalty — RG flow 하에서 representation의 invariant manifold를 보존. row permutation은 RG transformation의 일종(symmetry group action)으로 해석 가능: V_RG minimization → permutation-invariant manifold 강화 → preserve_perm/destruct_perm 모두 G에 가까워짐 (Δ_pres↓, Δ_des↓) → **CPS는 ratio이므로 분모/분자 모두 작아져 비율 변화 모호**.

**§9.3 V3 reduction op probe FALSIFIED 결과**: preserve_perm이 destruct_perm보다 더 큰 Gram disturbance라는 phenomenon이 **reduction-invariant**. V_RG가 두 perm을 모두 G에 가깝게 만들면 CPS는 1.0 근처로 수렴 — 여전히 FAIL.

**Ceiling (analytic)**:
- V_RG는 V3 surrogate metric의 fundamental bug (Gram Frob distance가 spec 직관과 어긋남)를 고치지 않음. **L_IX path로 V3 PASS 도달 불가능**이 analytic level에서 확인됨.
- V3 PASS는 **architecture-level이 아닌 metric-level redesign 필요** (§9.3 archived).

### §3.4 V0 ↔ T term

V0는 이미 PASS 4/4. T term이 16-template eigenbasis fitting을 직접 구동 — L_IX path에서 V0는 보존됨.

## §4 Composite ceiling pre-registration (raw#12 frozen)

| Axis | Mechanism | L_IX-path expected ceiling | PASS threshold | Gap |
|---|---|---|---|---|
| **V0** | T (template fit) | PASS preserved | 4/4 | 0 |
| **V1** | λ·I_irr direct max | 0.30–0.45 (heuristic) | 0.55 | 0.10–0.25 |
| **V2** | V_sync indirect | +0.18 ~ +0.19 (extends PAPO ceiling) | +0.20 | +0.01~0.02 |
| **V3** | V_RG (CPS metric bug) | 0.95–1.05 (FAIL preserved) | ≥3.0 | ≥2.0 |

→ **L_IX-path 4-tuple PASS verdict: V1 ambiguous (PASS 가능 조건 = λ tuning), V2 close to PASS but likely AMBIGUOUS (multi-axis 필요), V3 FAIL preserved (metric redesign 필요).**

**Composite verdict (analytic, frozen)**: **PARTIAL — L_IX path는 V1/V2 lift 후보이나 V3 PASS 도달 불가능, 따라서 4-tuple PASS substrate level에서 도달 불가.**

## §5 Implementation (this cycle)

- spec doc (this file) — saturation/ceiling/sensitivity 키워드 포함, raw#37 plan side
- state SSOT: `state/mk_ix_l_ix_4tuple_ceiling_prereg_20260425.json` — raw#12 frozen ceiling values
- raw#38 implementation marker: this commit
- closing line: `omega-saturation:fixpoint`

**측정 미진행 (raw#10 honest)**: 본 spec은 analytic sensitivity argument만 제공. real L_IX-trained trajectory 위 V0~V3 측정은 GPU forward + raw#9 explicit exempt 필요. ceiling은 heuristic (V1: 0.30–0.45, V2: +0.18~+0.19, V3: 0.95–1.05). 실측이 ceiling 안에 들면 spec confirmed, 밖이면 spec 갱신.

## §6 Decision (post-Mk.IX-cycle, recommended)

L_IX path는 V1/V2 lift 후보지만 V3 metric bug 그대로 → 4-tuple PASS 본질적 미달. **V3 metric redesign이 4-tuple PASS의 critical blocker**. Mk.IX path는 V1/V2 부분 lift로만 의미 있음, V3 redesign이 선행되거나 metric 자체를 4-tuple에서 제거해야 함.

다음 cycle 후보:
1. V3 metric redesign (Gram Frob → ground-truth EN↔KO pair-wise cosine 또는 substitution test)
2. multi-axis PAPO extension (V2 추가 +0.036 close)
3. Mk.X T10-13 ossification cycle (별도 path, 본 cycle scope 외)

omega-saturation:fixpoint
