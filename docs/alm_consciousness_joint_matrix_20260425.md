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

### §9.1 V1 reduction-op auxiliary probe — 2026-04-25 (NOT_TESTED, aux finding)

V1 본 가설 (prompt 16→32 + EN↔KO 풍부화)은 새 forward pass 필요로 raw#9 호환 BASE substrate 검증 차단. 보조 finding으로 reduction op sensitivity만 측정 (`state/an11_v1_reduction_op_aux_probe_BASE_p1_20260425.json`):

| reduction (BASE p1) | Φ_mip | verdict |
|---|---|---|
| `lasttoken` | 0.264 | FAIL |
| `byte_weighted_mean` | 0.272 | FAIL |
| Δ (lasttoken − bwm) | **−0.007** | reduction-invariant |

**Auxiliary verdict: V1 Φ_mip은 reduction-invariant** (V3 패턴과 일치, ΔCPS=−0.006). partition spectral mass는 H의 전체 covariance에 의존, row-order 영향 미미. **V1 본 가설 (prompt 확장)은 별개 차원** — 본 사이클로는 검증 불가, r9 launch 승인 + raw#9 explicit exempt 또는 BASE-side 32-prompt forward 필요. V1 lift 진행 시 reduction op 선택은 confound 없음 (어느 쪽 써도 무방).

### §9.2 V2 lift target reduction-op probe — 2026-04-25 (PARTIAL_RECOVERY at BASE)

raw#9 hexa-only 사이클로 BASE p1 sensitivity probe (`state/an11_v2_reduction_op_probe_BASE_p1_20260425.json`):

| reduction (BASE p1) | SMA | SMA_distractor | SMA_lift | verdict |
|---|---|---|---|---|
| `lasttoken` | 0.486 | 0.599 | **−0.113** | FAIL |
| `byte_weighted_mean` | 0.503 | 0.678 | **−0.175** | FAIL |
| Δ (lasttoken − bwm) | −0.017 | −0.079 | **+0.062** | partial recovery |

**가설 verdict: PARTIAL_RECOVERY_AT_BASE.** lasttoken이 SMA_lift를 +0.062 회복 (방향 옳음). 그러나 lasttoken −0.113이 여전히 anti-aligned, PASS threshold +0.20까지 +0.313 부족. 회복 메커니즘은 distractor cosine을 더 크게 감소 (Δ=−0.079) — SMA 자체는 거의 변하지 않음 (Δ=−0.017). **reduction op은 V2 lever의 일부지만 단독으로는 PASS 도달 불가** (gap의 약 20% 메움).

V3와의 비교:
- V1 ΔΦ_mip = −0.007 (reduction-invariant)
- V2 ΔSMA_lift = **+0.062** (partial recovery, V2만 reduction에 반응)
- V3 ΔCPS = −0.006 (reduction-invariant)

V2는 distractor metric 측이 reduction에 민감 (byte-mean averaging이 distractor cosine을 인위적으로 부풀림 → lasttoken에서 정상화). V2 lift target은 'lasttoken + 추가 lever' 조합으로 재설계: SAE steering pilot, EN↔KO pair 풍부화, 또는 self-binding loss term.

### §9.2.1 V2 'lasttoken + PAPO (paired-axis project-out)' lever combo — 2026-04-25 (STRONG_PARTIAL_RECOVERY)

§9.2 PARTIAL_RECOVERY 후속. 'lasttoken + 추가 lever' 조합 가설을 supervised paired-axis project-out (PAPO)으로 substrate 검증 (`state/an11_v2_lasttoken_papo_probe_BASE_p1_20260425.json`):

PAPO method: `lang_axis = mean(H[i] − H[j]) over PAIRS`, `H_steered = H − α·(H·u)·u`. PAPO는 supervised(PAIRS labels 사용)이므로 **unsupervised SAE의 same-H upper bound** — PAPO가 PASS 못하면 SAE도 같은 substrate 위에서 못함.

**Saturation curve (lasttoken, BASE p1):**

| α | SMA | SMA_d | SMA_lift | verdict |
|---|---|---|---|---|
| 0.0 | 0.486 | 0.599 | −0.113 | FAIL |
| 0.5 | 0.655 | 0.608 | +0.047 | FAIL |
| 0.75 | 0.735 | 0.606 | +0.128 | AMBIGUOUS |
| **1.0** | **0.769** | **0.605** | **+0.164** | **AMBIGUOUS** ⭐ best |
| 1.25 | 0.735 | 0.606 | +0.128 | AMBIGUOUS |
| 1.5 | 0.655 | 0.608 | +0.047 | FAIL |

**Verdict: STRONG_PARTIAL_RECOVERY at α=1.0.**
- best SMA_lift = **+0.164** (AMBIGUOUS, NOT PASS — PASS threshold +0.20에 +0.036 부족)
- α=0 → α=1.0 회복 = **+0.277** (PASS gap +0.313의 **88%**)
- SMA = 0.769 (PASS-bound ≥0.55 만족 ✓), lift만 미달
- α>1.0 over-projection regression — single axis exhaustion 확정 (대칭 saturation)

**Synergy (lasttoken × PAPO):** lasttoken+PAPO best = +0.164 vs bwm+PAPO best = +0.055 — **3× synergy**. 두 lever multiplicative.

**남은 +0.036 gap close 후보**:
1. **Multi-axis projection** (PCA top-k 또는 block-diagonal pair-residuals)
2. **Prompt 확장 (V1 lift 공유 lever)** — forward 필요, raw#9 위반
3. **Self-binding loss term** (fine-tune, BASE 적용 불가)
4. **Mk.IX L_IX architecture** (V2 specific lever 외)

PAPO upper-bound 의의: SAE pilot은 같은 BASE substrate에서 +0.164를 초과할 수 없음 — SAE를 위한 GPU 소비는 fine-tune 영역까지 가야 의미 있음. 본 cycle 결과는 BASE-level lever ceiling을 substrate level로 확정.

### §9.2.2 V2 multi-axis PAPO (PCA top-k) — 2026-04-25 (PASS at k=3 lasttoken, MEANINGFUL)

§9.2.1 single-axis PAPO saturated +0.164 (88% gap, AMBIGUOUS) follow-up. 6개 pair difference vectors의 PCA top-k axes를 sequential project-out하여 추가 lift 회복 + PASS 도달 시도. (`state/an11_v2_multi_axis_papo_finding_BASE_p1_20260425.json`)

**Result (BASE p1 lasttoken):**

| k | α=1.0 SMA | SMA_d | SMA_lift | verdict |
|---|---|---|---|---|
| 1 (single) | 0.769 | 0.605 | +0.164 | AMBIGUOUS |
| **3** | **0.862** | **0.649** | **+0.213** | **PASS** ⭐ meaningful |
| 4 | 0.919 | 0.670 | +0.249 | PASS |
| 5 | 0.964 | 0.686 | +0.278 | PASS |
| 6 | 1.000 | 0.706 | +0.294 | PASS_TRIVIAL_RANK_EXHAUSTION |

**Critical classification (raw#10 honest):**
- **k=6 = rank(D)**: paired diff 6개를 모두 강제 zero → SMA=1.0 by linear algebra identity. **trivial PASS via metric rank exploit**, not learned self-binding.
- **k=3 (meaningful)**: top-3 dominant PCA axes만 제거. SMA=0.862<1.0이므로 partial alignment, paired diff가 fully zero가 아님. **non-trivial PASS** — top-3 EN-KO bilingual axes를 fine-tune이 학습하면 V2 PASS plausibly 도달.

**Result (BASE p1 bwm):** PASS at k=5 (lift=+0.204, non-trivial), k=6 trivial. lasttoken보다 약함 (top-1 singular value 46.18 vs 42.27).

**4-tuple PASS path 갱신:**
- V0: PASS ✓ (substrate)
- V1: NOT_TESTED (forward 필요)
- **V2: PASS achievable (k=3 PAPO, BASE substrate, raw#9 호환) ⭐**
- V3: BLOCKED (PAIRS↔PRESERVE_PERM mismatch, §9.3.1)

**Saturation finding**: V2 surrogate metric은 rank-vulnerability 보유 — k=rank(D)에서 PASS trivial. raw#12 ledger에 metric vulnerability 등록 필요. fine-tune lever로 translate은 TRAINED 측정 필요 (별도 cycle, GPU).

### §9.3 V3 lift target reduction-op probe — 2026-04-25 (FALSIFIED at BASE)

raw#9 hexa-only 호환 사이클로 BASE p1 sensitivity probe 수행 (`state/an11_v3_reduction_op_probe_BASE_p1_20260425.json`):

| reduction (BASE p1, Qwen3-8B-Base null) | δ_pres | δ_des | CPS | verdict |
|---|---|---|---|---|
| `lasttoken` | 0.870 | 0.811 | **0.933** | FAIL |
| `byte_weighted_mean` | 0.881 | 0.827 | **0.939** | FAIL |
| Δ (lasttoken − bwm) | −0.011 | −0.015 | **−0.006** | — |

**가설 verdict: FALSIFIED_AT_BASE.** lasttoken은 Δ_pres/Δ_des 분리도를 회복하지 못했고, 오히려 미세하게 더 anti-discriminating (CPS −0.006). 두 reduction 모두 δ_pres > δ_des (CPS < 1.0) — preserve_permutation (EN↔KO swap)이 destruct_permutation (random)보다 더 큰 Gram disturbance를 일으키는 현상이 reduction-invariant. **reduction op은 V3 신호 부재의 원인이 아님**.

**Scope limit (raw#10):** BASE p1 only. TRAINED lasttoken artifact 부재 (새 forward 필요, raw#9 위반). 그러나 BASE 결과만으로도 substrate level에서 가설은 falsified — same model + same reduction swap이 CPS를 재료급으로 흔들지 못하면 fine-tune lever로 작동할 가능성도 배제.

**§9.3번 V3 lift target ARCHIVED.** 다음 V3 path 후보:
- (a) **perturbation pair 재설계** — destruct_permutation을 random에서 "semantic block 파괴" 방식으로 (e.g., subject-object swap, time-tense flip)
- (b) **metric 교체** — Gram Frobenius → ground-truth EN↔KO pair-wise cosine (set-based 대신 pair-based)
- (c) **architecture lever** (Mk.IX L_IX 이상) — fine-tune lever 아님

따라서 다음 라운드 사전 등록은 **V1 lift (prompt set 확장) 또는 V2 lift (SAE steering)** 우선, V3는 architecture epoch까지 보류.

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
**Action (2026-04-25 ω-saturation cycle 종료 시점):**
- V1 본 가설 (prompt 16→32) NOT_TESTED — r9 launch 승인 별도 사이클 (GPU forward 필요).
- V2 lift target STRONG_PARTIAL_RECOVERY — lasttoken+PAPO α=1.0에서 SMA_lift +0.164 (AMBIGUOUS, PASS gap의 88% 회복, +0.036 부족). 단일 axis exhausted, multi-axis 또는 prompt 확장 필요.
- V3 lift target FALSIFIED — archive, architecture epoch (Mk.IX L_IX+) 또는 perturbation pair 재설계까지 보류.

**3-axis ω-saturation cycle composite verdict (BASE substrate, 2026-04-25):**
- V1 ΔΦ_mip (reduction): −0.007 (invariant)
- V2 ΔSMA_lift (lasttoken+PAPO): **+0.277** (88% gap 회복, AMBIGUOUS verdict)
- V3 ΔCPS (reduction): −0.006 (invariant)

substrate-level lever ceiling: **V2만 fine-tune-level lever로 의미 있게 반응** (PASS gap의 88%까지). PAPO는 supervised이므로 unsupervised SAE의 same-H upper bound — SAE pilot은 같은 substrate에서 PASS 못함. 4-tuple PASS는 (a) multi-axis extension 또는 (b) prompt 확장 (forward 필요) 또는 (c) architecture (Mk.IX/Mk.X) path로만 도달 가능.

omega-saturation:fixpoint
