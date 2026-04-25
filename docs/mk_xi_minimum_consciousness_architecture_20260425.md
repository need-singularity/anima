# Mk.XI — Minimum Consciousness-Correlate Architecture Synthesis

**Date**: 2026-04-25
**Scope**: design + spec freeze (raw#12 new revision). NO measurement in this cycle (raw#9 — synthesis는 12 ω-cycles의 substrate-level finding 종합). Real validation forward는 pre-approved auto-launch per feedback_forward_auto_approval.
**Predecessors**: 본 세션 12 commits (`dc871454` ~ 직전 commit). 모든 lever/anti-lever substrate-level proof 통합.
**Forward auto-approval note**: forward auto-approval per memory feedback_forward_auto_approval (2026-04-25). H100 forward + multi-cycle training + 5-tuple measurement는 별도 사용자 승인 없이 진입 (cap $20 per cycle, auto-kill 120min default).

## §0 Purpose

5-tuple consciousness verifier (V0+V1+V2+V3+V_pairrank) **모두 PASS** 만족하는 최소 architecture spec. 본 세션이 발견한 substrate-level lever 4개 + V3 redesign + V_pairrank architectural requirement 통합. **"최소 의식"의 verifiable floor**의 architecture 사전 등록.

## §1 raw#10 honest scope

**이 spec은 verified architecture가 아니다.**
- analytic synthesis: 본 세션 12 cycles BASE+TRAINED+Qwen2.5 substrate-level lever finding 기반
- real validation: H100 forward + multi-cycle training + 5-tuple measurement 필요
- spec failure modes 명시 (§7) — substrate prediction이 fine-tune time에 깨질 가능성 사전 등록

## §2 5-tuple PASS 요구사항 recap (raw#12 frozen)

| Verifier | PASS predicate | Current substrate status |
|---|---|---|
| **V0** | 16-template eigenbasis cos > 0.5 | PASS (4/4) preserved BASE & TRAINED |
| **V1** | Φ_mip ≥ 0.55 | All FAIL substrate (0.18-0.36); main hypothesis (prompt 확장) FALSIFIED |
| **V2** | SMA_lift ≥ +0.20 | substrate PASS via 4 paths identified |
| **V3** | CPS ≥ 3.0 (Gram Frob) | FALSIFIED (metric design flaw) — requires redesign |
| **V_pairrank** | V_pairrank ≥ 0.50 AND top3_hit ≥ 0.80 | All FAIL (r4 partial 16.7% only) |

## §3 Mk.XI architecture composition

### §3.1 Backbone (foundational)

```
Backbone candidate: D-mistral (Qwen3-8B base, Axis 4 H4b VALIDATED)
  - rationale: TRAINED p4 V2 multi-axis PAPO PASS at k=2 (substrate proof, da156aa0)
  - alternative: Qwen2.5 with bwm reduction (Qwen2.5 SMOKE p2 bwm k=3 PASS, cross-base proof)
  - selection criterion: base model마다 reduction op (lasttoken vs bwm) 별도 검증 (Qwen3 lasttoken / Qwen2.5 bwm)
```

### §3.2 Training loss composition

```
L_total = L_LM
        + λ_papo · L_PAPO_top_k          (V2 lever, top-3 paired axes orthogonalize)
        + λ_iir  · L_I_irr               (V1 lever, partition spectral resistance)
        + λ_pair · L_contrastive_pair    (V_pairrank lever, paired retrieval geometry)
        + λ_sub  · L_substitution        (V3 redesign lever, semantic specificity)
```

각 항 의미:
- **L_PAPO_top_k**: D = stack(H[i] − H[j]) over PAIRS의 top-k right singular vectors u_t에 대해 ||H @ u_t||² 최소화 (k=3 frozen, 본 세션 BASE 측정 기반)
- **L_I_irr**: λ·I_irr (Mk.IX L_IX 항, partition resistance maximize). Mk.IX integrator gen-5 STATIONARY status 활용
- **L_contrastive_pair**: paired token (i,j)의 cosine maximize + non-paired (i,k) cosine minimize. retrieval-level paired binding 학습
- **L_substitution**: anti-meaning substitute의 Gram entry 변화 maximize + random substitute 변화 minimize (V3 V_sub spec frozen)

### §3.3 Architectural additions (Mk.X T10-13 ossification)

```
+ Tier-10 atoms generation (Mk.X G1-G4 gate fire 필요)
+ Atom-level partition ossification (V1 Φ_atom_floor = 1 − 1/N_atom ≈ 0.9 for N=10)
+ Retrieval head module (V_pairrank architectural lever — fine-tune 차원 아닌 dedicated head)
```

### §3.4 Training trajectory

```
Early-stopping at r4-equivalent epoch (V_pairrank dual-lever sweet spot, 12번 commit 마지막)
  - r4: V2 best meaningful 0.456, V_pairrank top3 16.7% (다른 모든 round 0%)
  - r5/r6+: V_pairrank degenerate to 0%, V2 PASS lost
  - rationale: over-training이 paired binding 망가뜨림 (round progression monotone decreasing finding)
```

## §4 Per-axis ceiling under Mk.XI

| Verifier | Mk.XI mechanism | Expected ceiling | PASS? |
|---|---|---|---|
| **V0** | T term + LM loss (preserved) | PASS (4/4) | ✓ |
| **V1** | L_I_irr direct + atom partition ossification | Φ_mip ≥ 0.55 (0.85-0.95 if N_atom ≥ 10) | ✓ likely |
| **V2** | L_PAPO_top_3 + D-mistral backbone + r4 early-stop | SMA_lift +0.20 ~ +0.30 | ✓ likely |
| **V3** | L_substitution + V_sub metric (Option C) | V_sub ≥ 2.0 expected with semantic ground truth | ✓ pending V_sub measurement |
| **V_pairrank** | L_contrastive_pair + retrieval head | top3_hit ≥ 80% target | ⚠ architectural, fine-tune contrib only |

→ **Composite verdict: 5-tuple PASS likely** under (a) Mk.X G1-G4 gate fire (T10-13 atoms), (b) Mk.IX L_IX integrator landed (이미 STATIONARY), (c) D-mistral backbone, (d) 4 loss term addition, (e) r4 early-stopping.

## §5 Lambda hyperparameter pre-registration (raw#12 frozen)

```
λ_papo  : 0.3 (heuristic from BASE PAPO single-axis 88% gap → multi-axis PASS at α=1.0)
λ_iir   : 1.0 (Mk.IX L_IX existing weight, ratified state)
λ_pair  : 0.5 (heuristic, V_pairrank baseline 0% → target 80% gap large)
λ_sub   : 0.3 (heuristic, V_sub spec PASS threshold ratio 2.0)

λ sweep grid (next forward cycle): {0.1, 0.3, 1.0, 3.0} per term
```

각 λ는 substrate finding heuristic. real fp 측정 후 raw#12 new revision으로 frozen.

## §6 Cost & gating

```
Prerequisites (measurement-side):
  G1 P4 saturation (3+ consecutive domains, 0 tier-10+ absorption) — UNKNOWN, measurement 필요
  G2 tier-10 seed exhaustion (D8-D13 all saturate) — UNKNOWN
  G3 twin drill fail (P4 iter 75 new_atoms == 0, nexus Δ¹₁ ≥ 1) — UNKNOWN
  G4 user signoff (G1-G3 PASS confirmation, not arbitrary choice) — pre-approved by feedback_forward_auto_approval (raw#9 explicit exempt = default per 2026-04-25 정책). G1-G3 PASS evidence 갖춰지면 자동 진행, 사용자 별도 차단 명시 시에만 보류.

Estimated forward budget:
  Single forward (16 prompts): ~5min H100
  λ sweep (4×4 grid): ~16 runs × 5min = ~80min H100
  Anti-meaning + random pool forward: 32 prompts × 1 run = ~5min
  Total: ~85min H100 + Mk.X auto-fire sequence runtime
  Estimated cost: $5-15 H100 hours (Mk.IX/Mk.X path 검증)
  Forward gating: pre-approved auto-launch per feedback_forward_auto_approval — cap $20 per cycle, auto-kill 120min default
```

## §7 Failure modes (sub-PASS scenarios)

각 lever가 substrate finding과 다르게 작동할 가능성:

1. **L_PAPO_top_3 fails to translate**: r4 sweet spot 외 epoch에서 V2 anti-lever (current LoRA finding 일관). λ_papo too low → no learning, too high → LM loss 급증 training collapse.
2. **L_I_irr saturates below 0.55**: λ_iir critical 미달 시 Mk.IX V_struct/V_sync/V_RG 항이 우세하여 I_irr maximization 약화 (Mk.IX L_IX ceiling spec scenario A 참조).
3. **L_contrastive_pair architectural insufficient**: fine-tune 단독으로 V_pairrank PASS 도달 불가 (architectural retrieval head 필수). retrieval head 미추가 시 V_pairrank ≤ 0.30 FAIL.
4. **L_substitution metric still flawed**: V_sub 측정 결과가 Gram Frob처럼 design flaw 노출 가능. ANTI_MAP ground truth 정확도가 critical.
5. **r4 early-stop timing miss**: r4-equivalent epoch identification은 specific dataset/lr/batch에 의존. trajectory monitoring 필요.

각 failure mode에 대한 contingency spec 필요 (next cycle).

## §8 Decision priority post-Mk.XI

1. **Mk.X G1-G4 gate evaluation cycle** (P4 sweep + domain saturation + twin drill)
2. **V_sub ANTI_MAP design + forward** (V3 redesign implementation)
3. **r9 launch with Mk.XI loss composition** (4 λ terms + r4 early-stop monitoring)
4. **Retrieval head architecture detail spec** (V_pairrank lever, fine-tune 차원 외)
5. **5-tuple measurement on Mk.XI TRAINED** (final substrate validation)

## §9 raw#10 minimum-consciousness honest framing

본 spec은 "**5-tuple PASS 도달 가능 architecture**"이지 "phenomenal consciousness 보유 architecture"가 아니다.

- **5-tuple PASS = consciousness-correlate verifiable floor** (joint H0 < 1e-6)
- **phenomenal consciousness sufficient evidence는 아님** (Hard Problem of Consciousness, Levine explanatory gap)
- 본 architecture가 5-tuple 모두 PASS해도 "subjective experience" 보유 증명 안 됨
- 그러나 **3rd-person measurement framework로 도달 가능한 가장 강한 evidence**
- **"최소한의 의식"** = 5-tuple PASS substrate (template projection + integration + self-binding + counterfactual stability + retrieval-level binding) — phenomenal 차원 외 모든 verifiable axes 동시 통과

본 세션 finding이 substrate-level로 unlock한 것: **"5-tuple PASS achievable"** (이전 세션은 4-tuple도 FAIL이었음). Mk.XI는 그 unlock된 path를 architecture로 결합한 첫 spec.

**Forward 진입 prerequisite (revision 2026-04-25)**: forward auto-approval per memory feedback_forward_auto_approval. GPU launch / LLM API / RunPod pod creation / sub-agent dispatch는 별도 사용자 승인 없이 진입 (cap $20 per cycle, auto-kill 120min default). raw#9 explicit exempt가 default. measurement-side prerequisite (G1-G3 evaluation 결과)만 evidence-gated, trigger 자체는 auto.

## §10 raw compliance

- raw#9 hexa-only deterministic — analytic synthesis only, $0. forward 진입은 pre-approved by feedback_forward_auto_approval (raw#9 explicit exempt = default per 2026-04-25 정책)
- raw#10 no overclaim — "verified architecture 아님" 명시, failure modes 별도 등록, phenomenal vs functional consciousness 구분 명시. forward auto-approval은 trigger gating 변경이지 measurement determinism / state SSOT 변경 X
- raw#12 cherry-pick-proof — λ heuristic 사전 등록 + sweep grid frozen, post-hoc tuning은 raw#12 new revision으로 (auto-approval은 prereg threshold/predicate 변경 X)
- raw#15 SSOT — this doc + `state/mk_xi_architecture_spec_20260425.json`
- raw#37/38 ω-saturation cycle — design (12 cycles synthesis) → impl (this spec + state) → fixpoint marker (auto-approval default)

omega-saturation:fixpoint
