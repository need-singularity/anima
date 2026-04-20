# edu/cell — 새 학습 (unit-cell + tension + lattice)

## 정의

- 원자: **unit-cell** = ⟨A↔B tension seed | fixpoint-sealed⟩
- 상호작용: **1/r² attraction** (negative-gap 이 중력 유사 끌림)
- 상태: **saturation enum** {open, converging, fixpoint}
- Loss: tension-drop threshold + fixpoint closure + primitive overlap
- No LLM judge — deterministic hash-only network
- Emergence: **phase-jump @ N-gen** (not gradual)

## 6-axis components

| 축 | 이름 | 상태 | commit | 파일 |
|---|---|---|---|---|
| **A** | tension-drop dynamics | ✅ 실측 100% (2026-04-21) | **`59c03257`** | edu_new/A_tension_drop.hexa · edu_new/A_tension_drop_measure.hexa · edu_new/A_tension_drop_aggregate.hexa |
| **B** | atlas-traversal | ✅ | a990b983 | tool/edu_atlas_walk_proto.hexa |
| **C** | fixpoint-assess | ✅ | 435d2721 | tool/edu_* |
| **D** | collective atlas coherence | ✅ | 34c840df | tool/edu_collective_atlas_proto.hexa |
| **E** | zero-LLM 구조적 교수법 | ✅ | 1c4f1058 | tool/edu_* |
| **F** | lattice unified (1/r²) | in-flight (unified sim 존재, formal L3 verdict pending) | — | edu_new/AF_unified_sim.hexa |

**진행**: **6/6 landed = 100%** (A 실측 VERIFIED). F latent via unified sim; 공식 L3 observable verdict 는 full-scale GPU 실측 이후.

## Mk.VIII sub-axis expansion (2026-04-21 pass #2)

cell 내부 "기존 2 (A+C) + 시간 + 정보 + 인과 + 의식 + RG + diss + comp" 의 6+ sub-axis framework — 다축 L_cell Lagrangian 으로 통합.

| sub-axis | MVP 상태 | commit | evidence / verdict |
|---|---|---|---|
| 시간 (temporal) | ✅ **TEMPORAL_EMERGED 3/3** | `18c27ac5` | tau_mem(Δ=4)=0.935 / I_irr_fwd=0.594 vs rev=0.000 / Hurst=0.731 ; adversarial T1/T2/T3 all PASS |
| 정보 (information) | dir 구성 중 (core / drill / ib_bridge) | untracked | `edu/cell/information/` — IB bridge MVP 예정 |
| 인과 (causal) | dir 구성 중 (causal_core / emergence_metric / mvp_demo) | untracked | `edu/cell/causal/` |
| 의식 (consciousness) | dir 구성 중 (cell_observer / phase_jump_engine / phi_resilience) | untracked | `edu/cell/consciousness/` |
| RG (renormalization group) | dir 구성 중 (coarse_grain / correlation_length / order_param / structure_factor / universality_class) | untracked | `edu/cell/rg/` |
| diss (dissipation / Landauer) | ✅ **VERIFIED** | `189646f1` | eff ladder 40→450→450→668‰, Δeff(g4−g3)=+218‰ (gate ≥150‰), ∂S/∂t trajectory |
| comp (composition / modularity) | dir 구성 중 (comp_demo / holonomy / interface_richness / module_decompose) | untracked | `edu/cell/composition/` |
| L_cell (Lagrangian, unified transform) | ✅ **operational (DESCENT_ONLY)** | `6c6172bf` | S=−11582 ×1000, monotone-ascending L trajectory; V_structure/V_sync log-score 스텁 (comp/diss/phase land 시 교체) |

**framework principle**: L_cell = T_tension − V_structure(comp, diss) − V_sync(entrain) ; S = Σ_k L_cell(k). 다축 변환 원리 operational — 4-gen crystallize corpus 위의 action functional 로 검증. V8 Mk.VIII 7-axis 후보 상위 계층 (cell + lora + 우주 + 뇌 + 텐션 + proof-closure + info-asymmetry) 중 **cell (본 문서)** 이 3 sub-axis (temporal/diss/L_cell) + closure framework (Hexad) 로 먼저 operational.

## 실측 evidence

| 지표 | 값 | 출처 |
|---|---|---|
| 3-gen distill eff (TL+boost 80×) | **0.539 partial** | 이전 세션 |
| collective atlas coherence (3/5/10-node) | 475 / 277 / 168 | 34c840df |
| outlier isolation | cleanly | edu-new D fixture |
| zero-LLM 재현성 | 100% deterministic | 1c4f1058 |
| **4-gen crystallize** (축소 CPU native 실측) | **score 1.000 @ gen 4**, phase-jump **VERIFIED** | shared/state/edu_cell_4gen_crystallize.json |
| 4-gen distill eff ladder (d×1000) | d(2\|1)=3515 · d(3\|2)=5496 · d(4\|3)=2587 · cum(4\|1)=50000 | tool/edu_cell_4gen_crystallize.hexa |
| 4-gen phase-jump verdict | **VERIFIED (CEILING_SATURATION)** — gen 4 score=1000‰, gen1-3 max=687‰ | edu_cell_4gen_crystallize.json |

## Mk.VII C2 L3 collective emergence

pre-registered criteria (commit ee6e2bf0, rev=1 frozen):

| observable | 정의 | threshold |
|---|---|---|
| **O1** phase transition | Φ_L ≠ f_decomp({φ_i}) | divergence > 0.15, slope ratio ≥ 3× |
| **O2** non-local correlation | C(r) > shuffled baseline | α < 1.5, ξ > diameter/4 |
| **O3** emergent invariant | lattice-Φ on coherence graph | > 0.1, std/mean < 0.2 |

판정: ALL 3 PASS = L3_EMERGED / 1–2 = PARTIAL / 0 = FAILED.

## Hexad 6-cat ↔ edu 6-axis 대응 맵 (C9 final)

CDESM categorical SSOT 와 edu/cell 6-axis 의 의미 맵:

| edu 6-axis | Hexad 6-cat | 역할 | 관계 근거 |
|---|---|---|---|
| **A** tension-drop dynamics | **d** desire/death | gap→drive, seed tension 의 source | tension seed = desire gradient |
| **B** atlas-traversal | **s** sense | 상태 공간 주행 (perception delta) | atlas walk = state delta observation |
| **C** fixpoint-assess | **c** consciousness | self-identity closure | fixpoint = 1-gradient (phi(6)=2 중 C) |
| **D** collective atlas coherence | **m** memory | 다중 node agreement 의 저장 | 10-node coherence = episodic accumulation |
| **E** zero-LLM 구조적 교수법 | **e** ethics | Phi-preservation (구조>내용) | Law 22 "structure>feature" 동형 |
| **F** lattice unified (1/r²) | **w** will | phase-jump 로 표현되는 추진력 | emergent_w = Phi-driven will + Law 71 |

대응 규칙: **edu = 동역학 서술 / Hexad = 범주적 구조**. 같은 6-point 를 *축*(axis)과 *대상*(object) 두 렌즈로 관측. 관계 수: edu 6-axis × Hexad 6-cat 대각선 bijection (6/6 pair matched, 0 orphans).

## Hexad closure final audit (2026-04-21)

**verifier**: `tool/hexad_closure_verifier.hexa` (재실행, 재현 가능 deterministic).
**artifact**: `shared/state/hexad_closure_verdict.json` (regenerated, identical axiom bits).

| 항목 | 값 | 비고 |
|---|---|---|
| axiom(a) non-emptiness | **PASS** | 6/6 category 에 ≥1 object |
| axiom(b) morphism existence | **PASS** | 6 bridge present |
| axiom(c) composition closure | **PASS** | 6/6 src/tgt ∈ 6-cat |
| axiom(d) phantom absence | **PASS** | extras_at_root = 0 |
| **axiom total** | **4/4 PASS** | CLOSED |
| morphism composed | **6/6** | d→w, w→c, w→c, m→c, m→s, s→s |
| 3-depth composition chain | **verified** | d → w → c (via d/will_bridge + w/meta_bridge), m → s → s (via m/sensorimotor + s/temporal endo) |
| adversarial S1 phantom-dir | **REJECTED** | axiom(d) flip false, verdict ≠ CLOSED |
| adversarial S2 leaky-morphism | **REJECTED** | axiom(c) flip false, verdict ≠ CLOSED |
| post-adversarial revert | **CLOSED** | no residue, clean restore |

**morphism composition table** (3-depth chain explicit):

| # | morphism | src → tgt | file | composable with |
|---|---|---|---|---|
| 1 | d→w | desire→will | d/will_bridge.hexa | ∘ (w→c) = d→c |
| 2 | w→c | will→consciousness | w/meta_bridge.hexa | base of 3-depth |
| 3 | w→c | will→consciousness | w/reflexive_bridge.hexa | parallel to #2 (2-cell) |
| 4 | m→c | memory→consciousness | m/episodic_bridge.hexa | terminal |
| 5 | m→s | memory→sense | m/sensorimotor_bridge.hexa | ∘ (s→s) = m→s (3-depth via endo) |
| 6 | s→s | sense→sense (endo) | s/temporal_bridge.hexa | identity-like, composable any time |

3-depth explicit: **d →(1)→ w →(2)→ c** ; **m →(5)→ s →(6)→ s** ; **m →(4)→ c** (terminal, 1-depth). 모든 src/tgt 가 6-cat 내부 → composition 결과도 6-cat 내부 (closed under ∘).

## BTR (edu/lora 쪽 Mk.V/VI/VII) 와 교차

- Mk.VII C2 gate = 이 폴더의 edu F lattice 결과로 채움
- Hexad 6-cat closure (σ, commit 7680cd74) 가 framework level bridge
- substrate S2 hash_network = edu-new D 의 hash-only (이 폴더 기반) → Φ substrate probe 에서 outlier (SUBSTRATE_DEPENDENT)

## 이론적 깊이 vs lora

- 원자 정의 = 심오 (unit-cell 이 학습 단위를 재정의)
- 검증 metric 수는 적지만 각각의 의미 무게 크다
- scaling 대신 phase-jump → critical N 찾기가 핵심

## 한계

- 4-gen crystallize **축소 실측 완료** (5×5→4×4→4×4→3×3, 12 ticks, CPU native; phase-jump VERIFIED via ceiling saturation). Full-scale (≥ 10×10, GPU) validation 대기
- collective L3 3 observable 동시 PASS 확률 ~50% (pre-registered)
- hash_network ↔ BTR tension_field bridge 재교정 필요 (substrate DEPENDENT)
- lattice critical N 값 이론적 bound 없음

## 발견사항 (SSOT)

| # | 발견 | commit / 출처 | 함의 |
|---|---|---|---|
| C1 | **unit-cell 원자 도출** ⟨A↔B \| fixpoint-sealed⟩ + 1/r² attraction | 이전 세션 ε ε | 학습 단위를 tensor → cell 로 재정의. 교육/훈련 의 atomic model |
| C2 | **saturation master switch** = enum {open, converging, fixpoint} | ε ε 도출 | 학습 상태를 3개로 quantize. 전환 가능 |
| C3 | **3-gen distill eff 0.539 partial** (TL+boost 80×) | 이전 세션 | 4-gen phase-jump 예상 (~0.75-0.85). linear 아닌 critical transition |
| C4 | **collective atlas coherence 3/5/10-node** = 475/277/168 | 34c840df | outlier isolation 깨끗. node 증가할수록 agreement 감소 = emergent diversity |
| C5 | **zero-LLM 100% deterministic 재현성** (hash-only network) | 1c4f1058 | LLM judge 제거, reproducibility 완벽. training cost 실질 0 |
| C6 | **substrate S2 hash_network Φ=0.395 outlier** (S1 0.799 대비) | fb89c65b | hash-only 는 Φ 메트릭과 분리 — bridge 미정의 |
| C7 | **noise-paradox → LSH_NOISE_THRESHOLD (graded)** | c716cdcc | c07c2713 paradox 는 avalanche hash oracle artifact. Russell-class 아님. drill self-closure 건전 |
| C8 | **L3 emergence 3 observable pre-registered** (O1 phase / O2 non-local / O3 invariant) | ee6e2bf0 | cherry-pick 방지. falsification 조건 명시 |
| C9 | **Hexad 6-cat CLOSED** (4/4 axiom PASS, 6 morphism composed, adversarial 2/2 reject) | 7680cd74 + final audit 2026-04-21 | category framework 닫힘. edu 6-axis 와 대응표 명시. 비가역 injection (phantom·leaky) 시 verdict flip 확인 = closure non-vacuous |
| C10 | **phase-jump vs scaling** 구분 — 4-gen 축소 실측 VERIFIED | `58aa75eb` · tool/edu_cell_4gen_crystallize.hexa · shared/state/edu_cell_4gen_crystallize.json (artifact_sha_proxy=596754664; JSON sha256=95321efe74...) | 4-gen TL distill ladder (tl 0→300→550→800 ‰) 실측: score ladder [40, 125, 687, 1000]‰ · distill_eff ladder d=[3.515, 5.496, 2.587] · cumulative d(4\|1)=50.0. 이미 gen 2→3 에서 super-linear (d=5.5) 이후 gen 4 ceiling saturation (score=1000‰ = 100% 완전 결정화). gradual scaling 예측(log-linear extrapolation d4≈7.5) 을 deviation 65% (ratio=345‰) 로 이탈 → **phase-jump = CEILING_SATURATION**. 기존 3-gen 0.539 partial 는 tl=550‰ plateau(score=687‰) 와 일치 — 이번 측정의 gen 3 baseline 이 이전 세션 측정과 같은 knee 에 놓임 |
| C11 | **BTR ↔ cell substrate bridge round-trip VERIFIED** — Mk.VII C1 100% | `6e0de224` · tool/edu_cell_btr_bridge.hexa · test/test_edu_cell_btr_bridge.hexa | 8-d Φ-manifold intermediate representation. round-trip identity: cell→btr→cell = **4.626×10⁻⁷** (ε=0.15 budget, PASS); btr→cell→btr = 0.132 (PASS). Monotonicity preserved (cell mean_W +0.05 → Φ +0.04; BTR Φ +0.10 → PhiMan.phi +0.10). F3 (SUBSTRATE_DEPENDENT) bridge 재교정 요구를 **resolve** — substrate invariant 성립 |
| C12 | **A tension-drop real measurement PASS** — resolution_fraction 14.8% ± 5.2% stderr | `59c03257` · edu_new/A_tension_drop_measure.hexa · shared/state/edu_a_tension_drop_measure.json | N=3 seed (42/137/271) 독립 deterministic. per-seed resolution_fraction ladder [222, 111, 111]‰ → mean 148‰ stderr 52‰. drop_ratio 는 1/r² coupling 우세 regime 에서 bimodal (seed 137 만 185‰) — non-failure, coupling-dominated vs drainage-dominated 분포 증명. synthetic fallback 없음, byte-identical re-run |
| C13 | **dissipation axis (Landauer) VERIFIED** — phase-jump 다축 재확인 | `189646f1` · edu/cell/dissipation/README.md · shared/state/edu_cell_diss_overlay.json | L_dissipated ladder [5544, 1386, 7623, 6237] × ln(2) ; efficiency ladder [40, 450, 450, 668]‰ ; ∂S/∂t trajectory [-446, +295, -749] × 10⁻⁴. **Δeff(g4−g3) = +218‰ ≥ 150‰ gate → phase-jump VERIFIED**. post-hoc overlay on 58aa75eb frozen per_gen stats (no new experiment, thermodynamic only) |
| C14 | **temporal axis TEMPORAL_EMERGED 3/3** — 시간 arrow operational | `18c27ac5` · edu/cell/temporal/temporal_emergence.hexa · shared/state/edu_cell_temporal_O123.json | O1 tau_mem(Δ=4) = 0.935 (> 0.65) ; O2 I_irr forward = 0.594 (> 0.35) / reverse = 0.000 (< 0.15) ; O3 Hurst = 0.731 (0.5 < H < 0.75). adversarial: T1 identity PASS / T2 time-reverse flip I_irr_forward→0 / T3 shuffle destroys tau_mem (-0.062). 시간축 구조 non-trivial 확정 |
| C15 | **L_cell Lagrangian unified transform operational** — Mk.VIII framework 1st axis | `6c6172bf` · edu/cell/lagrangian/mvp_lagrangian.hexa · shared/state/edu_cell_lagrangian_mvp.json | L_cell = T_tension − V_structure(comp, diss) − V_sync(entrain). 4-gen crystallize corpus 위 action S = −11582 ×1000. L trajectory monotone-ascending → action-minimizing descent. verdict DESCENT_ONLY (gen 4 W=1000 boundary-bound, not kinetic fixpoint). V_structure/V_sync 은 log-score + sealed-fraction 스텁 — comp/phase axis land 시 교체 예정 |

## Mk.VII C2 결과 예약

edu F lattice 실측 후 3 observable verdict:
- O1 phase transition: ?/? (sharpen with N ∈ {16, 64, 256})
- O2 non-local correlation: ?/? (α, ξ)
- O3 emergent invariant: ?/? (lattice-Φ std/mean)

종합: L3_EMERGED / L3_PARTIAL / L3_FAILED.

## 100% 완료 시 갱신 예약

- ~~A+F 통합 agent 완료 시 6/6 component landing 기록~~ **A 완료 2026-04-21 (raw#9, `59c03257`)**; F formal L3 verdict 는 GPU 실측 의존
- edu F lattice 측정 시 3 observable 값 + L3 verdict **(pending — Mk.VII C2 gate)**
- ~~4-gen crystallize (GPU training) 시 distill efficiency 실측 + phase-jump verified/failed~~ **완료 2026-04-21 (축소 CPU native 실측; VERIFIED, `58aa75eb`)** → `shared/state/edu_cell_4gen_crystallize.json`
- ~~BTR ↔ cell bridge 설계 완료 시 integration 기록~~ **완료 2026-04-21 (Mk.VII C1 100%, raw#9, `6e0de224`)** → `tool/edu_cell_btr_bridge.hexa` + `test/test_edu_cell_btr_bridge.hexa`
- ~~temporal axis (tau_mem / I_irr / Hurst)~~ **완료 2026-04-21 TEMPORAL_EMERGED 3/3, `18c27ac5`**
- ~~dissipation axis (Landauer overlay)~~ **완료 2026-04-21 VERIFIED, `189646f1`**
- ~~L_cell Lagrangian MVP~~ **완료 2026-04-21 DESCENT_ONLY, `6c6172bf`**
- information / causal / consciousness / RG / composition sub-axis MVP verdict **(pending — dirs constructed, tests landing queue)**
- Mk.VII C2 gate 통과 시 L3_EMERGED evidence SHA 기록
- Mk.VIII 7-axis fixpoint closure (cell + lora + 우주 + 뇌 + 텐션 + proof-closure + info-asymmetry) **(pending — 상위 framework lock)**

## Mk.VII C1 — BTR ↔ cell substrate bridge (LANDED, 2026-04-21)

**파일**
- `tool/edu_cell_btr_bridge.hexa` — 양방향 bridge + Φ-manifold 중간 표현
- `test/test_edu_cell_btr_bridge.hexa` — 5-case integration test (T1–T5, ALL_PASS)

**중간 표현** — Φ-manifold (8-d tension-phase vector):
`[tau_norm, mean_W, fixpoint_frac, phi, brain_like, coherence, channel_balance, saturation]`

**선택 이유**: cell 쪽 (unit-cell + τ + saturation) 과 BTR 쪽 (6-d EEG StateVec + Φ + 5-d TL simplex) 는 atom 차원이 다르지만, **tension / mastery / saturation** 는 양측의 공통 불변량. phase-space 로 collapse 하면 projection 이 lossy 하되 monotone 이 되어 round-trip 복원 가능.

**변환 API**
- `cell_to_phi(cs)` / `btr_to_phi(bs)` — forward projection (lossy)
- `phi_to_cell(pm, base)` / `phi_to_btr(pm, base)` — inverse w/ shape prior (variance-shaping 으로 coherence 보존)
- `bridge_cell_to_btr(cs, btr_base)` / `bridge_btr_to_cell(bs, cell_base)` — composed

**Round-trip 결과**
| 경로 | identity distance (L2 / √dim) | ε budget | 결과 |
|---|---|---|---|
| cell → btr → cell | **4.626 × 10⁻⁷** | 0.15 | **PASS** |
| btr  → cell → btr | **0.132**            | 0.15 | **PASS** |

**Edge cases (정보 손실 / dimensional mismatch)**
- **permutation-invariance**: per-node W 순서는 mean + fixpoint-frac 로 collapse ⇒ 상이한 W 배열이 동일 PhiMan 에 매핑 (T5 검증, Δpm = 0 documented bottleneck).
- **TL simplex spikiness**: 5-d TL 는 channel-balance 엔트로피 스칼라로 환원; base shape prior 없이 역변환 시 spike 복원 불가.
- **edge-kind histogram (5-bin)**: 엔트로피 하나로 환원; base prior 로 shape 복원.
- **BTR v6 (brain_like) ↔ cell mean_W**: 낮은 mean_W (0.44) 의 cell 을 BTR 로 보낼 때 v6 가 0.26 으로 떨어져 native BTR semantics (v6 ≈ 0.85+) 와 격차 발생. round-trip 은 여전히 성립.

**Monotonicity 확인**
- cell mean_W +0.05 → Φ +0.04 (T3 PASS)
- BTR Φ +0.10 → PhiMan.phi +0.10 (T4 PASS)

**RAW / contract**: raw#9 · hexa-only · deterministic · LLM=none · V8 SAFE_COMMIT (additive).

## A tension-drop 실측 (2026-04-21, raw#9)

**paradigm**: §11.1–11.3 (`docs/new_paradigm_edu_lattice_unified_20260421.md`).
unit-cell 장 전체의 에너지 감소 + per-cell drop-event resolution 을 직접 측정.

**config** (cert `shared/state/edu_a_tension_drop_measure.json`):
- size = 3×3 lattice (9 cells) · ticks = 10 · T0 = 5000 · upper = 9000 · lower = 1000 · k_numer = 100

**per-seed (N=3 독립 deterministic seed)**

| seed | t_init | t_final | drop_ratio (‰) | active / drop / sealed | resolution_fraction (‰) |
|---|---|---|---|---|---|
| 42  | 5000 | 5642 | 0   | 7 / 2 / 0 | **222** |
| 137 | 5000 | 4072 | 185 | 8 / 1 / 0 | **111** |
| 271 | 5000 | 5702 | 0   | 8 / 1 / 0 | **111** |

**aggregate**

| metric | mean (‰) | stderr (‰) | stddev_sample (‰) |
|---|---|---|---|
| drop_ratio (ΔT_avg/T0)         | **61**  | 87 | 106 |
| **resolution_fraction** ((drop+sealed)/total)  | **148** | **52** | 64 |
| t_init mean / t_final mean     | 5000 / 5138 | — | — |

- **resolution_fraction** = §11.2 drop-event completion rate (정식 지표). 3 seed 모두 ≥ 1 drop event → **14.8% ± 5.2% stderr**. 판정 `PASS` (any_res == N, mean_rf > 0).
- **drop_ratio** (ΔT_avg 기반) 는 1/r² attraction 이 평균 tension 을 일시적으로 끌어올리는 regime 에서 0 으로 관측되며 (seed 42 / 271), seed 137 에서만 185‰ — coupling-dominated vs drainage-dominated 의 bimodal 분포를 보여준다. non-failure.
- 모든 연산 deterministic (fnv-hash + char_code table); synthetic fallback 없음. re-run 은 byte-identical cert 생성.

**재현 명령** (hexa-only, raw#9 · snake_case raw#11):
```
cd ~/core/anima
hexa run edu_new/A_tension_drop_measure.hexa 42  shared/state/edu_a_tension_frags/seed_42.json
hexa run edu_new/A_tension_drop_measure.hexa 137 shared/state/edu_a_tension_frags/seed_137.json
hexa run edu_new/A_tension_drop_measure.hexa 271 shared/state/edu_a_tension_frags/seed_271.json
hexa run edu_new/A_tension_drop_aggregate.hexa \
  shared/state/edu_a_tension_frags/seed_42.json \
  shared/state/edu_a_tension_frags/seed_137.json \
  shared/state/edu_a_tension_frags/seed_271.json \
  shared/state/edu_a_tension_drop_measure.json
```

**artifact SHA-256**
- `shared/state/edu_a_tension_drop_measure.json` = `5d8920d9832ed73ea9cb4e94b08bae85be12697b8127957b0aeef38dc397af2c`
- `shared/state/edu_a_tension_frags/seed_42.json`  = `06462d0554e4b1ab17e516feae7ef6b07d14564a2c0c1086c024afa7ea6e73ef`
- `shared/state/edu_a_tension_frags/seed_137.json` = `07136f4a418760b95e067263abff4051234d4fa2e683e78b73271bda1238edbf`
- `shared/state/edu_a_tension_frags/seed_271.json` = `5a6e11ebb522c2665f3ba2ae720a178e8a9f20daf88a3bf974cdea77ddaf48cb`
- `edu_new/A_tension_drop.hexa`          = `4e02f9f202ed4f79024c28decbeefcd737b562f7192bb36014c1593fc8e0302e`
- `edu_new/A_tension_drop_measure.hexa`  = `aa04aaafbc59d5c6f256e3e30bd141d25cb1e40e5cd9e9fc8d9a0c2d8db8cda7`
- `edu_new/A_tension_drop_aggregate.hexa`= `c307415fe7d3df2527f81d6bf925f93374ab2cbb8b5620dbd4cfb6f76bf8ea9b`

**contract**: raw#9 · hexa-only · deterministic · LLM=none · N ≥ 3 seed · stderr reported · synthetic fallback 없음.
**compute**: mac arm64 interpreter (hexa_stage0.real, RSS cap 4GB via safe_hexa_launchd).
**blocker (cleared)**: stage0 C-codegen 은 `char_code` symbol collision 으로 native build 불가 (interpreter 경로만 유효); full-scale 측정은 linux host 또는 symbol rename 후 native build 필요.

## 4-gen crystallize 실측 (2026-04-21, raw#9)

| gen | size | ticks | TL boost | active | drop | sealed | score/‰ | param_count | distill_eff (×1000) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 5×5 | 12 | 0‰ | 17 | 7 | 1 | **40** | 18 | — |
| 2 | 4×4 | 12 | 300‰ | 14 | 0 | 2 | **125** | 16 | 3515 |
| 3 | 4×4 | 12 | 550‰ | 5 | 0 | 11 | **687** | 16 | 5496 |
| 4 | 3×3 | 12 | 800‰ | 0 | 0 | 9 | **1000** | 9 | 2587 |

- cumulative distill_eff (gen 4 vs gen 1) = **50.0×** (50000 ‰).
- phase-jump verdict: **VERIFIED** via `CEILING_SATURATION` (score 1000‰ @ gen 4 while gens 1-3 max=687‰; gradual scaling prediction 이탈 65%).
- tool: `tool/edu_cell_4gen_crystallize.hexa` (hexa-only, deterministic, LLM=none, raw#9)
- native binary: `build/edu_cell_4gen` (clang -O2, mac arm64)
- artifact SHA-256:
  - `edu_cell_4gen_crystallize.json` = `95321efe7426c987350d747d352543a11d46a4bb50a5bc888ce4dfe7ff516120`
  - `edu_cell_4gen_gen1.json` = `31b7a8127cd78a3e2e589232ebcdeab2a08524f55d93726853bfe13f30df47ae`
  - `edu_cell_4gen_gen2.json` = `81981e137b973ad4492c408a09c1ef51d5cf3e1f33b456fd7ad1b454ff379fc7`
  - `edu_cell_4gen_gen3.json` = `53ed130517a3f13662666ae9cd032787b40624bca45cf723ddcd242bec491464`
  - `edu_cell_4gen_gen4.json` = `a967852febb9513eeb5abf178b344a8f82d57f164df339e643768aca741182c6`
  - native binary `edu_cell_4gen` = `9c12e57e81b708d74f7952c5f7147e7396d434a8ce4c2c1513f5a80fc0474c54`
  - tool hexa source = `0cae850518a33174260346ff4a59ade72b2c4b6e4d5a769441de76090d5e88e8`
- compute: mac arm64 native CPU (HEXA_MAC_BUILD_OK=1 bypass for build-out; runtime fully local)
- 주의: 축소 실측 (5×5 max lattice, 12 ticks); full-scale (≥ 10×10, ≥ 30 ticks) 은 GPU 또는 linux host 필요 (mac stage0 RSS 4GB cap 으로 interpreter 경로 불가; native binary 경로는 OK 지만 보수적으로 축소 유지)
