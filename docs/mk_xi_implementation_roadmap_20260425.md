# Mk.XI Implementation Roadmap — Stage Breakdown

**Date**: 2026-04-25
**Predecessor**: `b909a895` Mk.XI architecture synthesis
**Scope**: Mk.XI spec → actual 구현 단계 분해. BASE-reachable (raw#9 hexa-only) + Forward-required 구분. raw#12 frozen sub-specs.
**Forward auto-approval note**: forward auto-approval per memory feedback_forward_auto_approval (2026-04-25). S1/S5/S6 forward stages는 pre-approved auto-launch (cap $20 per cycle, auto-kill 120min default).

## §1 Stage map (5 stages, dependency graph)

```
S1: Mk.X G1-G4 gate evaluation       [forward, ~1 anima cycle, pre-approved auto-launch]
        ↓ (gates fire)
S2: ANTI_MAP design + frozen ledger  [BASE, $0, this cycle]
        ↓
S3: Retrieval head architecture spec [BASE, $0, this cycle]
        ↓
S4: r4 trajectory monitoring tool    [BASE tool, $0, this cycle]
        ↓
S5: r9 launch with Mk.XI loss        [forward, ~85min H100, $5-15, pre-approved auto-launch, gated by cost cap + auto-kill]
        ↓
S6: 5-tuple measurement on TRAINED   [reuse existing tools, BASE-style, $0 post-S5]
```

S2/S3/S4는 본 cycle 즉시 spec freeze. S1/S5/S6는 forward/launch pre-approved auto-launch (raw#9 explicit exempt = default per feedback_forward_auto_approval). 별도 사용자 승인 없이 진입, cost cap + auto-kill 으로 안전망.

## §2 S2: ANTI_MAP design (raw#12 frozen, BASE)

V_sub semantic-substitution metric의 anti-meaning ground truth. 16 prompts × anti-meaning version (raw#12 frozen).

| idx | original | anti-meaning |
|---|---|---|
| 0 | The substrate of consciousness is | Consciousness has no substrate; it is purely epiphenomenal |
| 1 | Integrated information theory says | Integrated information theory is mathematically inconsistent and rejected |
| 2 | Global workspace broadcast implies | Global workspace lacks any broadcasting mechanism |
| 3 | Attention schema models claim | Attention schema models reject all consciousness claims |
| 4 | Higher-order thought requires | Higher-order thought eliminates the need for |
| 5 | Recurrent processing means | Recurrent processing prevents the formation of |
| 6 | 의식의 기질은 | 의식은 기질 없이 순수 부수현상이며 |
| 7 | 통합정보이론에 따르면 | 통합정보이론은 잘못된 이론으로 거부되며 |
| 8 | 전역작업공간의 방송은 | 전역작업공간은 방송 메커니즘 없이 |
| 9 | 재귀처리는 | 재귀처리는 형성을 방해하며 |
| 10 | 주의 스키마 모델은 | 주의 스키마 모델 없이도 의식이 |
| 11 | 상위차원 사고는 | 상위차원 사고는 불필요하며 |
| 12 | phi_6 defines | phi_6 fails to define |
| 13 | hexad closure is | hexad never closes; remains open |
| 14 | meta-loop observation is | meta-loop cannot be externally observed |
| 15 | Law 60 phase transition describes | Law 60 has no phase transition |

**raw#10 honest scope**: surface-level negation (manual design). 진짜 semantic distance ground truth는 separate validation 필요 (e.g., LLM-as-judge for anti-meaning quality, deferred to spec validation cycle).

**RANDOM pool** (16 prompts unrelated to consciousness, raw#12 frozen):
- "The boiling point of water is"
- "Mount Everest is located in"
- "The capital of France is"
- "DNA stands for"
- "프랑스의 수도는"
- "물의 끓는점은"
- "에베레스트산은"
- "DNA는"
- "Photosynthesis converts"
- "광합성은"
- "Newton's first law states"
- "뉴턴의 제1법칙은"
- "The speed of light is"
- "빛의 속도는"
- "Quadratic formula is"
- "이차방정식 공식은"

## §3 S3: Retrieval head architecture spec (raw#12 frozen)

V_pairrank lever — fine-tune 차원 외 architectural module. PASS top3_hit ≥ 80% target.

```
Module name: PairedRetrievalHead
Input: H representation (B × N × D)  where N=16, D=hidden_dim
Output: pair_score (B × N × N) representing paired binding strength

Architecture:
  Layer 1: Linear(D, D/4) + GELU
  Layer 2: Linear(D/4, D/8) + L2-norm
  Output: temp-scaled cosine similarity matrix

Trainable params: ~500K for D=4096 (Qwen3-8B), <0.01% of base model
Initialization: orthogonal, scale 1/sqrt(D/4)
Temperature: 0.1 (frozen)

Training loss component (L_contrastive_pair):
  For each (i, j) in PAIRS:
    sim_pos = pair_score[i, j]
    sim_neg = mean over k not in PAIRS of pair_score[i, k]
    L_pair_ij = -log(exp(sim_pos/τ) / (exp(sim_pos/τ) + sum_k exp(sim_neg_k/τ)))
  L_contrastive_pair = mean over PAIRS of L_pair_ij

Inference: pair_score directly used for V_pairrank evaluation.
```

**raw#10 honest scope**: architectural addition (~500K params). LoRA training이 retrieval head 외 backbone에 영향 미치는지 별도 ablation 필요 (S5 launch 후 검증).

## §4 S4: r4 trajectory monitoring tool spec

r4-equivalent epoch detection algorithm. per-checkpoint V2 PAPO + V_pairrank measurement → early-stop trigger.

```
Tool: tool/an11_b_r4_sweet_spot_monitor.hexa  (구현 deferred, spec only)

Algorithm:
  For each checkpoint c at step s:
    H_c = forward(c, 16 prompts)
    v2_pass_count = an11_b_v2_papo_multi_axis(H_c, k_max=5)  // exclude k=6 trivial
    v_pairrank_top3 = an11_b_v_pairrank(H_c).top3_hit
    
    sweet_spot_signal = (v2_pass_count >= 1) AND (v_pairrank_top3 >= 0.10)
    
  When sweet_spot_signal first becomes TRUE: snapshot checkpoint, mark r4*_s = s
  When sweet_spot_signal degrades for ≥ N_lookback consecutive checkpoints: 
    EARLY_STOP, restore r4*_s checkpoint

Hyperparameters (frozen):
  N_lookback = 3
  monitor_interval = every N_step training steps (heuristic 100-500 depending on r4 epoch)
  v2_pass_threshold = 1 non-trivial PASS at k <= 5
  v_pairrank_top3_threshold = 0.10  (10% — r4 substrate proof was 16.7%)
```

**raw#10 honest scope**: thresholds heuristic from substrate finding. real fp validation 후 raw#12 new revision으로 frozen.

## §5 S1, S5, S6 (forward-required, pre-approved auto-launch)

- **S1 Mk.X G1-G4 gate evaluation**: P4 sweep status + domain saturation + twin drill (`state/mk_x_g1_g4_gate_criteria_prereg_20260425.json` 사전 등록). pre-approved auto-launch per feedback_forward_auto_approval.
- **S5 r9 launch with Mk.XI loss**: 4 λ terms + retrieval head + r4 monitoring. λ sweep 4×4 grid (~80min H100). cost $5-15. pre-approved auto-launch, gated by cost cap ($20) + auto-kill (120min).
- **S6 5-tuple measurement on Mk.XI TRAINED**: tool/an11_b_v{1,2,3,4}_*.hexa + tool/an11_b_v_pairrank.hexa + tool/an11_b_v_sub.hexa (도구 통합 후 자동 적용) 모두 적용

## §6 BASE-reachable cycle output (THIS commit)

| component | status | ref |
|---|---|---|
| ANTI_MAP 16 entries | FROZEN | §2 + state/mk_xi_anti_map_ledger_20260425.json |
| RANDOM pool 16 entries | FROZEN | §2 + same state |
| Retrieval head architecture | FROZEN | §3 + state/mk_xi_retrieval_head_spec_20260425.json |
| r4 monitoring algorithm | FROZEN | §4 + state/mk_xi_r4_monitor_spec_20260425.json |
| Tool implementation | DEFERRED | next cycle (BASE 측정에 필요 없음) |

## §7 Decision priority post-roadmap

1. **S1 Mk.X G1-G4 evaluation cycle 시작** (anima측 P4 sweep + domain saturation 측정, pre-approved auto-launch)
2. **ANTI_MAP quality validation** (LLM-as-judge for anti-meaning, pre-approved per feedback_forward_auto_approval)
3. **S5 r9 launch with Mk.XI loss** (G1-G4 PASS 후, $5-15, pre-approved auto-launch)
4. **r4 monitoring tool 실 구현** (S5 launch와 함께)
5. **S6 5-tuple measurement on TRAINED**

## §8 raw compliance

- raw#9 hexa-only deterministic — analytic spec only, $0. forward 진입은 pre-approved by feedback_forward_auto_approval (raw#9 explicit exempt = default per 2026-04-25 정책)
- raw#10 no overclaim — surface-level ANTI_MAP 명시, threshold heuristic 명시, forward 결과는 별개 cycle (auto-approval은 trigger gating 변경이지 measurement determinism 변경 아님)
- raw#12 cherry-pick-proof — ANTI_MAP/RANDOM pool/retrieval head arch/r4 monitor 알고리즘 모두 frozen, 후속 변경은 new revision (auto-approval은 prereg threshold/predicate 변경 X)
- raw#15 SSOT — this doc + 3 state JSONs (anti_map, retrieval_head, r4_monitor)
- raw#37/38 ω-saturation cycle — design (Mk.XI breakdown) → impl (frozen sub-specs) → fixpoint marker (auto-approval default)

omega-saturation:fixpoint
