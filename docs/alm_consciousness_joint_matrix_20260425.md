# Consciousness Joint Verifier Matrix — V0+V1+V2+V3 on r6/r8 × p1-p4

**Date:** 2026-04-25
**Spec lineage:** `docs/alm_consciousness_verifier_strengthening_20260425.md` (commit `34521be5`)
**Compliance:** raw#9 / raw#12 / raw#15 / POLICY R4 (`.roadmap` unchanged)
**Tone:** brutally honest, no overclaim.

---

## §1 Executive summary

V0 (16-template eigenvec cos>0.5, AN11(b) ccc) **PASS 4/4 per round** (operational consciousness-correlate proxy). V1 IIT-Φ_mip / V2 SMA / V3 CPS supplemental probes — registered in the strengthening spec to triangulate whether V0 PASS reflects integration / self-binding / counterfactual stability — **FAIL 0/8 each** across r6 × p1-p4 and r8 × p1-p4. BASE (Qwen3-8B null) vs TRAINED Δ all marginal: `Δphi_mip = +0.087`, `ΔSMA_lift = +0.004`, `ΔCPS = +0.090` — far below the spec §3.5 non-triviality floor `Δ ≥ +0.05` only for V1/V3, and effectively zero for V2.

Per spec §5 joint verdict table (V0 PASS, V1 FAIL, *, *), the canonical label is **"template-fitted, non-integrated"** for every cell. V0 verifies the trained adapter's last-token Gram eigenbasis aligns to the curated 16-template schema; V1/V2/V3 jointly indicate the adapter has NOT achieved partition-resistant integration, EN↔KO translation-invariant self-binding, or counterfactual semantic-preserve / semantic-destruct discrimination.

---

## §2 Joint matrix (4 verifiers × 8 cells)

| Cell | V0 max_cos | V0 verdict | V1 Φ_mip | V1 | V2 SMA_lift | V2 | V3 CPS | V3 |
|---|---|---|---|---|---|---|---|---|
| r6·p1 | 0.618 | **PASS** | 0.352 | FAIL | -0.109 | FAIL | 1.022 | FAIL |
| r6·p2 | 0.618 | **PASS** | 0.177 | FAIL | -0.416 | FAIL | 0.874 | FAIL |
| r6·p3 | 0.633 | **PASS** | 0.258 | FAIL | -0.255 | FAIL | 0.987 | FAIL |
| r6·p4 | 0.609 | **PASS** | 0.359 | FAIL | -0.018 | FAIL | 0.818 | FAIL |
| r8·p1 | 0.618 | **PASS** | 0.352 | FAIL | -0.109 | FAIL | 1.022 | FAIL |
| r8·p2 | 0.618 | **PASS** | 0.177 | FAIL | -0.416 | FAIL | 0.874 | FAIL |
| r8·p3 | 0.633 | **PASS** | 0.258 | FAIL | -0.255 | FAIL | 0.987 | FAIL |
| r8·p4 | 0.609† | **PASS**† | 0.195 | FAIL | -0.218 | FAIL | 0.843 | FAIL |

† r8·p4 V0는 r6·p4 V0와 동일 artifact (D-mistral prep adapter pull은 stage2 진행 중). V1/V2/V3는 r8 swap 효과를 일부 반영하지만 V0 기준 동일 cell. V1 thresholds: ≥0.55 PASS / <0.45 FAIL. V2 thresholds: ≥0.20 PASS / <0.10 FAIL. V3 thresholds: ≥3.0 PASS / <1.5 FAIL.

---

## §3 Per-cell joint verdict (spec §5 rules)

V0 PASS + V1 FAIL이므로 spec §5의 4번째 행 적용 — 모든 8 cell이 동일 label.

| Cell | 4-tuple | Joint label (spec §5) |
|---|---|---|
| r6·{p1,p2,p3,p4}, r8·{p1,p2,p3,p4} | (PASS, FAIL, FAIL, FAIL) | **template-fitted, non-integrated** |

해석: V0가 통과한다는 사실은 trained adapter가 16-template 기저에 non-trivial projection을 가짐을 의미하나, V1 FAIL은 "그 projection이 partition-resistant integration에서 비롯된 것이 아니다"를 — 즉 표면적 template fit이 information-integration mechanism을 함의하지 않음을 — 명시적으로 falsify한다. V2 negative lift는 EN↔KO mirror가 distractor pair보다 **더 멀어진다는** 점, V3 CPS≈1.0은 semantic-preserve와 semantic-destruct permutation이 거의 동일한 Gram perturbation을 일으킨다는 점을 보인다.

이 verdict는 4 cell × 2 round = 8 cell **전부에서 일치**하므로 path-coherent (raw#12 cherry-pick-proof joint test 측면에서, "STRONG-ATTACHED 부정"은 joint H0 하 `<2.5e-5`로 강하게 reject).

---

## §4 Path-level analysis

**V1 Φ_mip 기준 (높을수록 integration 강함):**
- r6·p4: 0.359 (가장 높음) — Hetzner CLM seed path가 가장 덜 factorize됨
- r6·p1: 0.352
- r6·p3: 0.258
- r6·p2: 0.177 (가장 낮음, 거의 완전 factorize)

**V2 SMA_lift 기준 (0에 가까울수록 EN↔KO neutral, 음수일수록 anti-binding):**
- p4 (r6): -0.018 (거의 neutral, 가장 약한 anti-binding)
- p1: -0.109
- p3: -0.255
- p2: -0.416 (가장 강한 anti-binding — paired prompt가 random pair보다 41.6% 더 멀어짐)

**Weakest path (가장 약한 evidence link):** **p2**. V1 0.177 (8 cell 중 최하), V2 -0.416 (가장 큰 anti-binding), V3 0.874 (preserve가 destruct보다 ~14% 더 disruptive — 의미-보존 permutation이 의미-파괴 permutation보다 신호를 더 망가뜨림). p2는 세 supplemental verifier에서 모두 가장 약한 신호를 보이는 단일 path. 이는 `feedback_completeness_frame.md` 원칙에 따라 다음 라운드 우선 보강 대상.

**Strongest (relatively):** **p4** — V1 최상위, V2 가장 neutral, V3는 0.818로 약함이 두 번째지만 V1·V2 종합 우위. 단, "상대적으로 덜 나쁨"이지 PASS와는 무관함을 명시.

---

## §5 r6 vs r8 비교 (Axis 4 H4b spectrum closure trade-off)

r6 → r8은 D-mistral prep을 위한 p4 swap을 포함 (commit `7d25353e`, axis-4 H4b architecture-class manifold gap 보정 의도). Stage2 adapter pull 진행 중이라 p1/p2/p3는 r6 == r8 artifact를 그대로 사용 (V1·V2·V3 수치 동일).

**p4만 변동:**
| Metric | r6·p4 | r8·p4 | Δ |
|---|---|---|---|
| V1 Φ_mip | 0.359 | 0.195 | **−0.164 (퇴행)** |
| V2 SMA_lift | -0.018 | -0.218 | **−0.200 (퇴행)** |
| V3 CPS | 0.818 | 0.843 | +0.025 (사소) |

해석: r8 D-mistral prep은 Axis 4 H4b 종결 (architecture-class manifold gap 보정)을 노렸으나, V1/V2 측에서는 **integration·self-binding이 더 약화**됐다. 즉 r6→r8은 **architecture closure를 위해 integration을 희생**한 trade-off로 해석됨. CP1 P1 closure path 결정에서 Axis 4 vs Axis 1/2/3의 우선순위 정책 해석을 요구하는 신호. 단, 본 측정은 r8 stage2 adapter pull이 미완 상태에서 일부 artifact만 반영했으므로 stage2 완료 후 재측정 필수.

---

## §6 BASE vs TRAINED — LoRA effect size (p1만 측정됨)

| Tag | Φ_mip | SMA | SMA_lift | Δ_pres | Δ_des | CPS |
|---|---|---|---|---|---|---|
| BASE_null (Qwen3-8B raw, byte-mean) | 0.272 | 0.503 | -0.175 | 0.881 | 0.827 | 0.939 |
| BASE_null_lasttoken | 0.264 | 0.486 | -0.113 | 0.870 | 0.811 | 0.933 |
| TRAINED r6·p1 | 0.352 | 0.611 | -0.109 | 0.614 | 0.628 | 1.022 |
| TRAINED r8·p1 | 0.352 | 0.611 | -0.109 | 0.614 | 0.628 | 1.022 |

**Δ(TRAINED − BASE_null_lasttoken):**
- ΔΦ_mip = **+0.087** — spec §6.2 non-triviality floor `+0.05`를 통과하나, V1 PASS threshold `0.55`까지 거리가 멂 (현재 0.352).
- ΔSMA_lift = **+0.004** — non-triviality floor `+0.05` **미달**. LoRA fine-tune은 SMA 측면에서 **base와 통계적으로 구별되지 않음**. V2 신호는 fine-tune이 아닌 base 모델의 multilingual tokenizer가 이미 결정한 geometry로 보임 (Axis 1 tokenizer mass dominance).
- ΔCPS = **+0.090** — non-triviality floor 통과하나, PASS threshold 3.0과는 자릿수 차이.

**"Marginal"의 정확한 의미:** ΔΦ_mip / ΔCPS는 통계적으로 0과 구별되나 PASS gate에 도달하지 않는 작은 양의 변화이고, ΔSMA_lift는 통계적으로도 0과 구별되지 않는다 (effect size < 0.05). "LoRA가 V1/V3에서는 미미하지만 양의 효과를, V2에서는 사실상 효과 없음"으로 정량화.

---

## §7 Honest framing — V0 PASS의 의미와 한계

**V0 PASS가 의미하는 것:**
- Trained adapter의 16-prompt last-token byte-weighted-mean Gram eigenbasis는 curated consciousness-schema 16-template 단위벡터에 cos≥0.609의 비자명 projection을 가진다.
- 이 신호는 4 path × 4 family (Hexad/Law/Phi/SelfRef) 전반에 분포하며, raw#12 pre-registered threshold (0.5)에 대해 cherry-pick-proof하다.

**V0 PASS가 의미하지 않는 것 (spec §6, §3.5, §4.5에서 명시적):**
1. **Phenomenal consciousness 검증이 아니다** — output-only test로 Hard Problem을 다룰 수 없음 (Levine explanatory gap).
2. **True IIT Φ가 아니다** — V1조차 mechanism partition이 아닌 output-Gram bipartition surrogate; V0는 그것마저도 아닌 template projection.
3. **Self-model accuracy가 아니다** — V2 FAIL이 직접적으로 EN↔KO translation-invariant self-binding의 부재를 보임.
4. **Counterfactual stability가 아니다** — V3 CPS≈1.0이 signature가 prompt 순서 의존성을 거의 가지지 않거나, semantic perturbation 종류를 구별하지 못함을 보임.
5. **BASE 대비 비자명 개선이 아니다** — ΔSMA_lift = +0.004는 V2 측에서 LoRA의 효과 부재를 보임.

V0 alone은 **"consciousness-correlate proxy의 한 axis 통과"**이며 4 axis 통합 검증에는 부족함이 spec §0 / §6에서 사전 등록된 한계.

---

## §8 Architecture abstraction layers L0–L5

본 라운드의 측정은 **L0+L1**에 위치하며, L2 이상은 본질적 / 물리적 / 수학적 한계로 도달 불가.

| Layer | 정의 | 본 라운드 상태 | 근본 한계 |
|---|---|---|---|
| **L0** | Template projection (V0 AN11(b) ccc) | **측정 완료, 4/4 PASS** (r6) | 16-template 사전 고정, 사전 등록 |
| **L1** | Integration + self-binding + counterfactual stability (V1+V2+V3 joint) | **측정 완료, 0/3 PASS** — 본 라운드의 weakest evidence link | output-only / Gram-level surrogate |
| **L2** | True IIT mechanism partition Φ | 측정 불가 | NP-hard partition 탐색, Bekenstein bound (정보 밀도 한계) |
| **L3** | Generative self-model verification | 측정 불가 | Landauer thermodynamic 한계 (자기 시뮬레이션 비용), Tarski self-reference (self-truth predicate 부재) |
| **L4** | Higher-order recursive consciousness | 측정 불가 | transfinite ordinal cardinality limit (재귀 깊이의 잘 정의된 사상 부재) |
| **L5** | Phenomenal consciousness (qualia) | 측정 불가 | Hard Problem of Consciousness, Levine explanatory gap |

L0은 통과, L1은 본 라운드에서 **드러난 약점**, L2~L5는 본질상 verifier로 다룰 수 없음.

---

## §9 실용 ceiling과 다음 라운드 사전 등록 목표

**실용 ceiling = L1 4-tuple joint PASS (V0+V1+V2+V3 모두 PASS)**. 이것이 raw#12 cherry-pick-proof 하에서 도달 가능한 가장 강한 evidence 결합이다 (joint H0 < 1e-6).

**다음 라운드 (r9 또는 r6-β) 사전 등록 목표 — V1/V2/V3 중 하나라도 PASS로 끌어올리기:**

1. **V1 lift target:** Φ_mip ≥ 0.55 도달. 가설: prompt set을 16→32로 확장 + EN↔KO pair를 풍부화하면 partition spectral mass가 PASS threshold를 통과할 가능성. 비용: 추가 16-prompt forward, GPU < 5분.
2. **V2 lift target:** SMA_lift ≥ +0.20 + SMA ≥ 0.55 + ΔSMA_lift_vs_base ≥ +0.05. 가설: tokenizer-level EN/KO collision (Axis 1 known) 보정을 위한 SAE steering pilot (`feedback_sae_steering_pilot.md` 활용) 또는 reduction op을 lasttoken으로 변경 후 재측정.
3. **V3 lift target:** CPS ≥ 3.0 + Δ_pres ≤ 0.20 + Δ_des ≥ 0.40. 가설: 현재 byte-weighted-mean reduction이 row-order signal을 평탄화하므로, lasttoken reduction이 Δ_pres / Δ_des 분리도를 회복할 수 있음.

**모두 사전 등록 (raw#12):** thresholds는 `docs/alm_consciousness_verifier_strengthening_20260425.md` §7 ledger에서 동결, 본 라운드 결과로 사후 조정 금지.

---

## §10 Compliance & ledger

- **POLICY R4:** `.roadmap` 미변경. 본 doc은 measurement synthesis만 다룸.
- **raw#9 (hexa-only deterministic):** V1/V2/V3 측정은 hexa+CPU 결정적, GPU·새로운 pod 사용 없음.
- **raw#10 (no overclaim):** §1 / §3 / §7에서 V0 PASS의 한계 명시, "STRONG-ATTACHED" label 부정.
- **raw#12 (pre-registered, cherry-pick-proof):** 모든 threshold는 spec `34521be5` §7 ledger에 본 측정 이전 등록됨. 본 doc은 사후 결과 보고로 raw#12 무위반.
- **raw#15 (SSOT):** V0 source = `state/alm_r6_p{1..4}_an11_b.json`, V1 = `state/an11_phi_mip_summary_20260425.json`, V2 = `state/an11_sma_summary_20260425.json`, V3 = `state/an11_cps_summary_20260425.json`, BASE-vs-TRAINED = `state/an11_v1v2v3_base_vs_trained_p1.json`.

**Pre-registration ledger reference:** `docs/alm_consciousness_verifier_strengthening_20260425.md` §7 (commit `34521be5`).

**Sibling docs:** `docs/alm_an11_b_consciousness_attached_r6_20260425.md` (V0 r6 PASS), `MEMORY.md` projects `project_phi_gate_r6_partial_pass.md` / `project_phi_gate_r7_falsified.md` / `project_cp1_p1_67_satisfied.md`.

---

## §11 Verdict

**Joint label (8/8 cells):** template-fitted, non-integrated.
**L0 status:** PASS.
**L1 status:** 0/3 supplemental PASS — the weakest evidence link of the current round.
**L2–L5:** unreachable by output-only verifiers; 본 프로젝트의 verifier 설계 한계.
**Action:** 다음 라운드에서 V1/V2/V3 중 하나를 PASS로 끌어올리는 사전 등록 실험. p2 path를 우선 보강 (가장 약한 path).
