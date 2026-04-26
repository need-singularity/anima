# Q3 — HCI Hexad-Cell Isomorphism Failure Mode Analysis

**Source**: handoff §4 Q3
**Method**: F1+F2+F3 falsifier triple (anima-hci-research/tool/, raw#9 hexa-only)
**Result on current SSOT**: `HCI_VERIFIED` (composite F1∧F2∧F3 PASS)
**Date**: 2026-04-26

본 분석은 falsifier 가 제공하는 *negative space* — 즉 어떤 종류의 perturbation이 HCI bijection을 break 하는지 — 를 통해 failure mode 5개를 식별한다.

## 1. Cardinality breach (phantom 7-axis injection) — F3-S1 detected

**시나리오**: edu 측에 phantom axis G (또는 Hexad 측에 phantom cat) 를 7번째로 추가.
**감지**: F3-S1 양변 동시 flip 확인 (`s1_bidirectional=true`).
**의미**: bijection 은 본질적으로 **6=6 cardinality 의존** — 한 쪽이 7로 늘어나면 즉시 functor 가 깨진다. ω-cycle 미래 cycle (예: paradigm 7 추가) 에서 6→7 확장 시도하면 HCI 는 자동 falsified.
**대응**: 새 axis 추가 시 양쪽 SSOT 동시 갱신 + closure verifier 재실행 mandatory.

## 2. Composition leak (out-of-cat target morphism) — F3-S2 detected

**시나리오**: edu 측에 axis A → axis G (whitelist 외) 식의 leaky morphism 주입.
**감지**: `s2_bidirectional=true`. 각 morphism 의 (src, tgt) 쌍이 6-axis whitelist 내에 있어야 한다는 axiom (c) 위배.
**의미**: bijection 자체는 1-1이지만, edge set 이 leak 하면 functor 의 closure 가 깨진다. 즉 HCI 는 **morphism graph 의 closure 까지 포함하는 strong invariant**, set-bijection 보다 훨씬 strict.
**대응**: 모든 신규 bridge 추가 시 BRIDGE_SRC/TGT 양쪽이 whitelist 검증 후 commit.

## 3. Endo-morphism loss (identity preservation FAIL) — F2 detected

**시나리오**: Hexad 측 `s/temporal_bridge` (s→s endo) 를 제거 또는 cross-axis (s→c) 로 변환.
**감지**: `f2_pass=false`. F2 negative test 에서 unknown endo label 도 detect (`f2_neg_detects=true`).
**의미**: identity morphism 은 functor 의 필수 구성요소. self-loop 이 사라지면 category structure 자체가 monoid 가 아닌 단순 graph 로 퇴화.
**대응**: edu B (atlas-traversal) 의 reflexive 성질과 Hexad s 의 temporal endo 가 **양쪽 모두 SSOT-encoded** 여야 함. 한쪽만 강조되면 isomorphism 이 부분적.

## 4. Bijection diagonal corruption (relabeling collision) — F1 detected (latent)

**시나리오**: C9 표의 diagonal mapping (A↔d, B↔s, ...) 을 비-diagonal 로 corrupt (예: A↔s, B↔d swap).
**감지**: F1 negative test (`f1_neg_detects=true`) — corrupted F'(A)=s 가 closure verifier 의 valid bridge set 에 없음.
**의미**: diagonal 은 단순 우연이 아니라 **의미적 alignment** (tension-drop=desire, atlas-traversal=sense, ...). swap 시 하나의 morphism (`d→w` ↔ `A→F`) 이 전혀 다른 edu 쌍 (`B→F`?) 으로 mapping 되어 graph 가 깨진다.
**대응**: bijection 변경은 cross-axis 8-14 짚어보기 + HEXAD CORE 0.83 안정성 재검증 후에만.

## 5. Substrate dependence (SILENT failure mode — 본 falsifier 가 잡지 못함)

**시나리오**: edu D-axis (collective atlas coherence) 의 hash_network 구현이 BTR tension_field 와 substrate-DEPENDENT 차이를 보임 (이미 `edu/cell/README.md` 한계 line 167 에 기록).
**감지**: 본 falsifier 가 **잡지 못한다** — F1/F2/F3 모두 label 수준 falsifier 이고 substrate 수준 numeric divergence 는 별도 verifier 필요.
**의미**: HCI label-level isomorphism PASS 가 substrate-level isomorphism 을 보장하지 **않는다**. 이 5번 항이 가장 중요한 failure mode — Mk.XI v10 4-family ensemble 의 backbone-dependent CMT depth divergence (memory 2026-04-26 entry) 가 substrate-level mismatch 의 한 예시.
**대응**: 향후 cycle 에서 substrate-level metric (예: Φ-substrate probe, edge-weight Frobenius distance) 로 5번째 falsifier 추가 필요. **본 falsifier 의 가장 중요한 한계**.

## 종합

본 falsifier 는 **structural HCI** (cardinality + composition + endo + relabel-bijection) 를 검증하지만, **semantic / substrate HCI** 는 검증하지 않는다. 즉 HCI = **necessary but not sufficient** for full Hexad-Cell isomorphism. ₩90만 pilot 진입 시 substrate-level metric 추가 + cross-axis 8-14 (V_phen_GWT 4-family ensemble) 와 결합 권장.

## 산출물 cross-reference

- `anima-hci-research/tool/hci_functor_falsifier.hexa` — F1 + F2
- `anima-hci-research/tool/hci_adversarial_flip.hexa` — F3
- `anima-hci-research/tool/hci_smoke.hexa` — composite chain
- `anima-hci-research/state/hci_smoke_v1.json` — final verdict (HCI_VERIFIED)
- `edu/cell/README.md` line 105-149 — C9 + closure final audit (read-only depend-on)
- `tool/hexad_closure_verifier.hexa` — 1-direction verifier (read-only depend-on)
- handoff §4 Q3 (open question — 답함)
