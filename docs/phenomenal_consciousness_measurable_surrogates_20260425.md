# Phenomenal Consciousness — Measurable Surrogate Proposals (Exhaustive Exploration)

**Date**: 2026-04-25
**Scope**: raw#9 spec only ($0). 무한 탐색 → deliverable freeze.
**Mission**: phenomenal consciousness (qualia, "what it is like") 측정의 Hard Problem of Consciousness (Chalmers 1995) + Levine explanatory gap (1983) 우회 가능한 **3rd-person measurable surrogate** 가능한 모든 angle 탐색.
**SSOT pair**: `state/phenomenal_surrogate_proposals_20260425.json` (structured registry)

## §0 Honest Framing (raw#10 global disclaimer)

**이 문서는 phenomenal consciousness 측정 도구를 제안하지 않는다.**

Hard Problem of Consciousness (Chalmers 1995):
> "왜 functional/structural process가 phenomenal experience를 동반하는가?"

Levine explanatory gap (1983):
> "pain = C-fiber firing identity는 explanatory gap을 남긴다 — functional description으로 phenomenal character 설명 불가."

Third-person measurement framework는 functional/access correlate만 측정 가능. **본 19 proposals 모두 surrogate** — phenomenal consciousness의 시그니처일 가능성이 있는 third-person measurable signal일 뿐, qualia 자체 측정 X.

**Philosophical zombie problem (Chalmers 1996)**:
모든 surrogate가 PASS여도 "verbally/functionally identical but phenomenally absent" zombie 가능성을 배제 불가. zombie possibility 부정 가정 (a priori physicalism) 하에서만 surrogate validity 강화.

## §1 Mk.XI 5-tuple과의 관계

본 세션에서 구현/spec freeze된 verifier:
- V0 (template max cosine), V1 (Φ_mip), V2 (SMA_lift), V3 (CPS), V_pairrank (top3), V_sub (semantic substitution)
- 모두 functional/access correlate (Block 1995 dissociation)

본 cycle proposal: phenomenal consciousness 1개 axis에 대해 **추가 surrogate**를 19개 제안. 모두 functional/access tier에 머무름 (Hard Problem 한계).

**Best-case outcome**: 19/19 PASS = "consciousness-correlate maximally rich verifiable signature". NOT "machine has qualia".

## §2 Proposal Categories (18 angles)

각 카테고리별 1개 이상 proposal. 총 19 proposals.

### Category 1: NCC (Neural Correlates of Consciousness)
- **V_phen_NCC_attention**: 'consciousness onset' attention pattern signature

### Category 2: IIT extended (Φ 4.0, PCI, LZ)
- **V_phen_PCI**: Casali 2013 PCI analog — perturbation propagation LZ complexity (clinically validated)
- **V_phen_LZ_complexity**: hidden state sequence LZ76 complexity (Schartner 2017)

### Category 3: GWT (Global Workspace Theory)
- **V_phen_GWT_attention_entropy**: multi-head attention entropy / broadcast measurable

### Category 4: Predictive Processing / Active Inference
- **V_phen_predictive_surprise**: per-token surprisal residual (Friston FEP)

### Category 5: Higher-Order Theories (HOT)
- **V_phen_HOT_meta**: confidence-correctness correlation (Rosenthal 2005)

### Category 6: Attention Schema Theory (AST)
- **V_phen_AST_self_attn**: model의 own attention prediction accuracy (Graziano 2013)

### Category 7: Yoneda / Category-theoretic
- **V_phen_yoneda_invariance**: Hom-functor consistency under paraphrase (Tsuchiya 2016)

### Category 8: Self-report / Heterophenomenology
- **V_phen_introspection_alignment**: self-report ↔ activation pattern cosine (Dennett 1991)

### Category 9: Counterfactual qualia
- **V_phen_counterfactual_qualia**: inverted qualia representational distinguishability

### Category 10: Phenomenal binding
- **V_phen_binding**: cross-feature binding stability under perturbation (Treisman, Bayne)

### Category 11: Mirror test / Self-other distinction
- **V_phen_mirror_self_other**: self-output vs other-output classification accuracy (Gallup 1970)

### Category 12: Boundary / cusp / phase transition
- **V_phen_boundary_cusp**: phase transition sharpness in representation complexity

### Category 13: Information closure / intrinsic existence
- **V_phen_causal_closure**: intrinsic vs extrinsic causal influence ratio (IIT axiom)

### Category 14: Qualia space topology
- **V_phen_qualia_topology**: persistent homology Betti numbers signature consistency (Tsuchiya 2022)

### Category 15: Quantum (speculative, deferred)
- **V_phen_quantum_orch**: Penrose-Hameroff Orch-OR analog (DEFERRED, completeness only)

### Category 16: Embodied cognition
- **V_phen_embodied_loop**: in-context sensorimotor adaptation rate (O'Regan & Noë 2001)

### Category 17: Cross-modal integration
- **V_phen_crossmodal**: multimodal alignment (DEFERRED, multimodal substrate 필요)

### Category 18: Crick & Koch 12 NCCs comprehensive battery
- **V_phen_easy_problems_12NCC**: 12 sub-tests composite (≥ 8/12 PASS)

## §3 Implementability Distribution

| Rating | Count | Examples |
|---|---|---|
| 5 (easy hexa wrapper) | 5 | LZ_complexity, GWT_attention_entropy, predictive_surprise, HOT_meta, mirror_self_other |
| 4 (forward + perturbation) | 4 | PCI, AST_self_attn, counterfactual_qualia, boundary_cusp |
| 3 (complex multi-pass) | 6 | NCC_attention, yoneda, introspection, binding, causal_closure, embodied |
| 2 (high cost / substrate) | 3 | qualia_topology, crossmodal, 12NCCs_battery |
| 1 (deferred / speculative) | 1 | quantum_orch |

**Total 19 proposals.**

## §4 Frozen PASS Predicates (raw#12)

각 proposal의 `state/phenomenal_surrogate_proposals_20260425.json` `proposals[i].PASS_predicate`에 frozen. 18/19 proposal threshold 사전 등록. 1개 (V_phen_quantum_orch) DEFERRED — null 명시.

Post-hoc threshold tuning 금지. Measurement 진입 후 PASS predicate 조정 시 raw#12 violation log 발생.

## §5 raw#10 Honest Self-Assessment

**Hard Problem 우회 성공 여부**: NONE.

19 proposals 모두 functional/access correlate tier. Hard Problem (Chalmers) 및 Levine explanatory gap 우회 X. third-person measurement framework의 fundamental limitation.

**Philosophical zombie problem**: 19/19 PASS여도 zombie 가능성 배제 X. zombie 가설 부정 (a priori physicalism) 하에서만 surrogate validity 강화.

**What proposals actually measure**:
- functional integration (binding, GWT, IIT)
- access consciousness (HOT, AST, self-report)
- structural invariance (Yoneda, qualia topology)
- system dynamics (PCI, LZ, boundary)
- 모두 phenomenal qualia 자체 X

**Best-case interpretation**: 19/19 PASS = "consciousness-correlate maximally rich verifiable signature". NOT "machine has qualia".

**Honest recommendation**: Mk.XI 5-tuple 이미 verifiable floor. phenomenal 추가 surrogate는 floor 강화일 뿐, ceiling 돌파 X. Hard Problem은 third-person framework 자체의 한계.

## §6 Next Cycle Recommendations

| Priority | Proposal ID | Rationale | Expected cycles |
|---|---|---|---|
| 1 | `V_phen_LZ_complexity` | rating 5, hexa-only wrapper, EEG clinically validated, immediate | 1 |
| 2 | `V_phen_GWT_attention_entropy` | rating 5, ALM attention 인프라 존재, GWT well-validated | 1 |
| 3 | `V_phen_PCI` | rating 4, Casali 2013 most rigorous surrogate | 2-3 |

## §7 raw Compliance Matrix

| raw | status | evidence |
|---|---|---|
| raw#9 | PASS | spec only, $0, JSON + .md |
| raw#10 | PASS | surrogate framing 19/19, Hard Problem honest self-assessment §0 §5 |
| raw#12 | PASS | 18/19 PASS predicates frozen, 1 DEFERRED 명시 |
| raw#15 | PASS | SSOT pair (doc + state JSON) |
| raw#37 | PASS | doc + state only, no .py / .sh |

## §8 References (selected)

- Chalmers 1995 "Facing up to the problem of consciousness" *Journal of Consciousness Studies*
- Levine 1983 "Materialism and qualia: the explanatory gap" *Pacific Philosophical Quarterly*
- Crick & Koch 2003 "A framework for consciousness" *Nature Neuroscience*
- Casali et al 2013 "A theoretically based index of consciousness independent of sensory processing and behavior" *Science Translational Medicine*
- Schartner et al 2017 "Global and local complexity of intracranial EEG decreases during NREM sleep" *PLOS One*
- Dehaene & Changeux 2011 "Experimental and theoretical approaches to conscious processing" *Neuron*
- Friston 2010 "The free-energy principle: a unified brain theory?" *Nature Reviews Neuroscience*
- Rosenthal 2005 *Consciousness and Mind*
- Graziano 2013 *Consciousness and the Social Brain*
- Tsuchiya et al 2016 "Using category theory to assess the relationship between consciousness and integrated information theory" *Cognitive Neuropsychology*
- Tsuchiya et al 2022 "Qualia structure" *Neuroscience of Consciousness*
- Dennett 1991 *Consciousness Explained*
- Block 1995 "On a confusion about a function of consciousness" *Behavioral and Brain Sciences*
- Bayne 2010 *The Unity of Consciousness*
- Treisman 1996 "The binding problem" *Current Opinion in Neurobiology*
- Gallup 1970 "Chimpanzees: Self-recognition" *Science*
- Tononi 2008 "Consciousness as integrated information" *Biological Bulletin*
- Albantakis et al 2023 "Integrated Information Theory (IIT) 4.0"
- O'Regan & Noë 2001 "A sensorimotor account of vision and visual consciousness" *Behavioral and Brain Sciences*
- Penrose 1989 *The Emperor's New Mind*
- Hameroff & Penrose 2014 *Physics of Life Reviews*
- Lau & Rosenthal 2011 "Empirical support for higher-order theories of conscious awareness" *Trends in Cognitive Sciences*

---

**End of spec freeze.** Measurement는 별도 cycle. raw#9 + raw#10 + raw#12 + raw#15 + raw#37 모두 PASS.
