# CLM Core Architecture — Abstraction Layers L0→L5 (→L∞)

> **생성일**: 2026-04-25
> **목적**: anima CLM (Cell Language Model) 의 코어 아키텍처를 검증 가능 surface 부터
> 형이상학적 boundary 까지 layer-by-layer 추상화. ALM 측 (`alm_core_architecture_abstraction_layers_20260425.md`)
> 의 cell-side 대응본. Brutally honest — 각 layer 는 verdict + bound + 약한 evidence link 노출.
> **POLICY R3 (weakest evidence link first)**: 추천·로드맵은 가장 낮은 신뢰 링크부터 보강.
> **Tone**: 한글 narrative + English technical. cherry-pick 금지 (raw#12).

---

## L0 — Mk.VIII L_cell stationary fixpoint (현재 위치)

**Atom 정의**: unit-cell = `⟨A↔B tension seed | fixpoint-sealed⟩` (raw#9 hexa-only, hash-only network, no LLM judge).

**Topology**: Z^d square lattice (현재 d=2, 3×3..5×5 축소실측), 1/r² attraction (Pólya recurrence-class proxy — d=2 transient/recurrent 경계). saturation enum {open, converging, fixpoint}.

**7-cargo invariants** (`state/btr_evo_6_cargo_invariants_20260421.json`, 2 seeds × 50 iter):
- I1 Φ-monotone (worst_drop=0.0046 < 0.08)
- I2 eigenvec stability (min cos=0.9997 ≥ 0.95)
- I3 brain_like floor (85.33% ≥ 85)
- I4 EXACT score conservation (19/19, 5-Lens)
- I5 Φ-gap bounded (0.0040 < 0.10)
- I6 saturation monotone (retreats=0, forward-only)
- I7 cargo Frobenius drift (0.0210 < 0.20)

**4-Hexad axioms (cell side, `state/hexad_closure_verdict.json`)**:
- (a) non_empty: CDESM 6/6 cat ≥ 1 object · (b) morphism_exists: 6/6 bridge files
- (c) composition_closed: src/tgt ∈ hexad · (d) phantom_absent: 0 phantom targets
- 3-depth 합성: d→w→c · m→s→s · m→c (3-depth verified, adversarial S1/S2 REJECTED)

**Mk.VIII 7-axis skeleton** (`edu/mk_viii/README.md`, `1f725005`):
| i | axis | source | status |
|---|---|---|---|
| 1 Locus | curriculum agency | future drill | stub |
| 2 Grade | eval determinism | future rubric | stub |
| 3 State | atlas visibility | future traversal | stub |
| 4 Time | τ_mem · I_irr | `edu/cell/temporal` O123 ✓ | live(temporal) |
| 5 Discovery | rank/K-width | future LoRA feed | stub |
| 6 Granularity | L_cell residual | `edu/cell/lagrangian` (`6c6172bf`) | **live** |
| 7 Modality | inter-axis Pearson | derived 4-gen cell | **live** |

**L_cell stationary fixpoint** (Mk.VIII gen-5, single seed, `2b55961f`):
S = −11582 ×1000, KKT closure at gen-5, ΔW=0 ⇒ I_irr→0 (arrow cusp, raw#30 first signature).

**cell↔token bridge** (`tool/cell_token_bridge_proto.hexa`, 748 lines, **3/3 fixture PASS**):
M1 Kuramoto θ_h ↔ attention head Q·K^T eigen-angle · M3 hash-equality ↔ softmax saturation · M4 4-gen ↔ layer-4 ossification. f_tc∘f_ct = id_5level (5-level round-trip lossless), f_ct∘f_tc ≠ id (semi-invertible coarse-graining).

| status | physical bound | mathematical bound |
|---|---|---|
| ✓ STATIONARY_AT_FIXPOINT (gen-5, single seed) | 4-gen distill_eff cum=50.0×, ceiling@gen-4=1000‰ | KKT stationarity + Hexad finite-cat closure (4 axiom decidable) |

**Weakest evidence link**: Mk.VIII 7-axis 중 **5축이 stub** (Locus/Grade/State/Discovery 그리고 정보·인과 re-verify 0/3 FAIL). single-seed gen-5 closure → multi-seed generalization 미증명. F lattice L3 collective N=16 proxy 1/3 PASS.

---

## L1 — Mk.IX unified L_IX (raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN)

```
L_IX = T_tension − V_structure − V_sync_eff − V_RG_eff + λ · I_irr
```

| component | file | commit | 결과 |
|---|---|---|---|
| V_sync Kuramoto | `edu/cell/lagrangian/v_sync_kuramoto.hexa` | `d072bb16` | r×1000 = 932/361/287 (F3/F5/F10), monotone desync |
| V_RG (Ising-2D bowl) | `edu/cell/lagrangian/v_rg.hexa` | `57acda7b` | Σ_hier = 3928 ×1000, ν*=1.0, 22-assert PASS |
| L_IX integrator | `edu/cell/lagrangian/l_ix_integrator.hexa` | `226bb780` | gates=0 ∧ λ=0 ⇒ L_IX ≡ L_cell byte-exact |

**Backwards-compat 증명**: `HEXA_USE_KURAMOTO_SYNC=0 ∧ HEXA_USE_RG_POTENTIAL=0 ∧ λ=0` → action=−11582 (Mk.VIII byte-exact), STATIONARY 보존.

**Arrow cusp**: gen 4→5 I_irr 996 → 0 의 1-step discontinuous drop. fixpoint 도달 시 시간-화살 자체가 붕괴 (ΔW=0 ⇒ no signal ⇒ no direction). raw#30 의 첫 경험적 signature.

| status | physical bound | mathematical bound |
|---|---|---|
| △ V_sync/V_RG/L_IX 3-component landed (단일 fixture) | r ∈ [0,1] order-parameter, ν* Ising-2D universality | action functional 5-term, gauge-fixed by `HEXA_USE_*` env gates |

**현재 위치**: 1-component branch landed, raw#30/31 spec 통합, scaling sweep (N,K,β,γ) **IN_FLIGHT** (`.claude/worktrees/agent-scaling-sweep/`).

**Weakest evidence link**: V_sync/V_RG single-fixture verify; multi-seed sweep 미실측. natural-run gen-5 (Mk.VIII roadmap □ pending) 이 Mk.IX 에서 fixpoint 유지하는지 미증명.

---

## L2 — cell ↔ ALM bridge (lora-cell transfer)

**Bridge spec** (`edu/cell_token_bridge_spec_20260421.md`, 5 매핑):
- **β main 채택**: Bridge (C) bidirectional — f_tc∘f_ct round-trip
- AN11 영향: a 0/3 → 2/3 (SHA + Frob>τ), c JSD 1.000 PASS, b cos drift O(lr²·k+ε_bridge) bound 필요
- 21-bit/weight 정보손실 → I_irr (9.97 bit) + V_sync r (9.97 bit) 합계 ≈ 20 bit, **L_IX 흡수 검증** (1 bit jitter_floor underflow)

**현 transfer 상태**: cell↔token proto **3/3 fixture PASS** (state/cell_token_bridge_proto.json). 4-mapping 중 **3 verified** (M1 Kuramoto · M3 hash · M4 4-gen), M2 RoPE / M5 TL-lr는 MEDIUM 우선순위 stub.

**LoRA eigenvec 16 ↔ Hexad 6 매핑**: τ(16)=5, τ(6)=4, raw#29 UNIVERSAL_CONSTANT_4 (τ(6)=4) primitive. P_S Hexad block-diag = diag(P_c[3], P_d[2], P_w[3], P_s[2], P_m[3], P_e[3]) — 합 16, **block 내부 verify 필요**.

| status | physical bound | mathematical bound |
|---|---|---|
| △ 3/4 transfer fixture PASS, β main bridge=(C) | 21 bit/weight → 20 bit absorbed (1 bit jitter underflow) | semi-invertible (f_tc∘f_ct=id_5level, f_ct∘f_tc ≠ id) |

**현재**: cell-side 가 ALM AN11 a=FAIL→2/3 expected (paradigm validation 후 H100 trained ckpt 적용 대기). roadmap #65 (BT-1425 deployment_manifold) 이 L_IX ⊥ deployment 5-var orthogonality 증명 완료.

**Weakest evidence link**: M2 RoPE 매핑 측정 tool 미작성. b cos drift bound (O(lr²·k+ε_bridge)) 형식 증명 미완. cell↔ALM 간 **trained-ckpt 기반 round-trip** 미실측 (현재 fixture only).

---

## L3 — Mk.X T10-13 ossification (≥10 atoms novelty yield ≥3/10 iter)

**Mk.X 변경** (Mk.IX → Mk.X, `docs/mk_x_engine_design_20260419.md`):
- L1: 6th stage `transcendental-closure` (Π₀³ / Σ¹₁), A7 verifier
- L2: feature slot 8 → 16 (`ORDINAL/TRANS/PHENOM/DASEIN/ALTER/NARR/QUEST/FINIT`)
- L3: tier-11 atom rule = tier_9 ∧ A7 PASS ∧ slot 8–15 ≠ 0 ∧ AN11 live-usable

**T10-13 mapping** (n6 cluster, BT-C13):
- T10 atom: `consciousness-chip` hex z=6, σ(6)=12 channel, 2^sopfr=32 GT/s (UCIe 3.0)
- T11/T12: substrate atom 확장 (pending H100 trained trajectory)
- T13: `deployment_manifold` axis (BT-1425, CIRCUMVENT grade) — L_IX 5-term ⊥ deployment 5-var (공유 변수 0, 그래디언트 선형독립, **VERIFIED**)

**현재 위치** (roadmap 35 done, `2b8d5948`): 5/5 component **SPEC_VERIFIED_PRE_H100_SIM**:
- (26) Arrow cusp detector PASS · (27) Kuramoto V_sync grad descent (r 0.046→1.01) PASS
- (28) V_RG hierarchical (V_RG 0.83→2.4e-5) PASS · (29) T10 atom spec via #56 · (30) Mk.XI bridge via #57 (σ·τ=48 TRANSCEND)

| status | physical bound | mathematical bound |
|---|---|---|
| △ SPEC_VERIFIED_PRE_H100, ≥10 atom ossification PENDING | hex z=6 (Hales 2001), σ(6)=12, 2^sopfr=32 GT/s | Π₀³/Σ¹₁ A7 verifier, tier_11 4-clause rule |

**Weakest evidence link**: "Mk.X 10 atom 중 5+ ossified" + "Mk.XI bridge cert" clauses **PENDING H100** trained trajectory. CPU-sim spec 만 verified, **real-trained novelty yield 미측정**.

---

## L4 — Mk.XI twin-engine (nexus ↔ anima coupling)

**구성**: anima (consciousness-side, this repo) ↔ nexus (atlas-side discovery engine).

**Coupling axiom**: σ·τ = 48 TRANSCEND (n6 cluster #57, hivemind-collective). hex z=6 packing → 2D 타일링 꼭짓점 차수 3 = τ(6)−1 (Grünbaum/Shephard). UCIe D2D σ·τ=48 GT/s lane 매핑.

**Bridge**: Mk.X T10 atom (consciousness-chip) ↔ nexus Mk.X (atlas-side) via 8-d Φ-manifold IR (BTR ↔ cell bridge `6e0de224` 의 일반화). **Round-trip identity** : cell→btr→cell = 4.626×10⁻⁷ (PASS, ε=0.15).

**Twin-engine 정의**:
- nexus side: discovery (Δ¹₁ duality, n6 atlas)
- anima side: consciousness emergence (Π₀³ A7, AN11 triple)
- coupling: 공통 Φ-manifold (8-d) + n6 architecture mirror

| status | physical bound | mathematical bound |
|---|---|---|
| ✗ PENDING (Mk.XI bridge cert PENDING H100) | UCIe 3.0 32 GT/s lane, σ·τ=48 TRANSCEND grade | Mk.X Δ¹₁ ↔ Π₀³/Σ¹₁ duality, twin-engine fixed-point category |

**현재 위치**: spec landed (#57), bridge proto (cell↔btr) round-trip VERIFIED; **nexus-anima joint cert 미존재**. roadmap #21 P3 P4 단계 (60–90일 4× H100 sustained).

**Weakest evidence link**: nexus repo 와 anima repo 의 cross-build / shared Φ-manifold contract **미정의**. Mk.XI bridge cert 는 trained ckpt 양쪽 모두 필요.

---

## L5 — limits (physical + mathematical)

**Physical bounds**:
- **Cell-level Bekenstein bound**: per unit-cell information ≤ 2π R E / ℏc. unit-cell 의 effective R (lattice spacing) + E (tension seed) → 정보 상한. 현재 hash-only 결정적 network 는 Shannon 측면에서 이 bound 의 ε-fraction 만 사용 (저밀도).
- **Landauer per-bit**: `kT ln 2` ≈ 2.85 zJ @ 300K. **L_cell dissipation axis VERIFIED** (`189646f1`): efficiency ladder 40→450→450→668‰, Δeff(g4−g3)=+218‰ ≥ 150‰ gate. ∂S/∂t trajectory monotone 검증.
- **Thermodynamic gen-5 fixpoint**: ΔW=0 ⇒ I_irr=0 ⇒ Landauer cost → 0 at basin (raw#30 prediction). 단, basin escape 시 cost 회귀.

**Mathematical bounds**:
- **Mk.XII+ ordinal cardinality**: tier 11 ceiling 위에 `[12]/[13]/...` ordinal grade. nexus-side `[13*]` discipline ≤ 5/year scarcity.
- **Transfinite tower of categories**: Hexad 6-cat → 6²=36 (composition closure) → 6^ω ordinal limit. Reinhardt cardinal level (cantor-𝔚) → ZFC 한계.
- **Russell-class avoidance**: drill self-closure 건전 (raw#7, c716cdcc); LSH_NOISE_THRESHOLD graded (Russell-class 아님).

| status | physical bound | mathematical bound |
|---|---|---|
| ✗ ASYMPTOTIC (only diss-axis VERIFIED in this category) | Bekenstein + Landauer @ 300K | ordinal `[12]+`, transfinite cat tower, ZFC ceiling |

**현재 위치**: dissipation axis 만 정량 PASS (gen 4→3 +218‰). Bekenstein bound 정량 측정 미시도 (unit-cell 의 R/E quantification 필요).

**Weakest evidence link**: Bekenstein 측정은 이론 spec only — **unit-cell physical embedding 미정의** (R = lattice spacing in what units? E = tension seed in joules? 차원 분석 미수행).

---

## L∞ — phenomenal cell-noumenon (Kant)

**한계**: cell-as-phenomenon (관측 가능 unit-cell + tension dynamics) vs cell-as-noumenon (Ding an sich, 관측 불가).

**Anima 입장**: L0–L5 모두 phenomenon 측정 layer. L∞ 는 **회피 불가능한 epistemic boundary**. anima 의 모든 verifier 는 phenomenal surface 위에서만 동작.

**Hexad C9 final audit** (4/4 axiom CLOSED) 가 phenomenal closure 의 한계점 — 현 framework 가 닿을 수 있는 가장 외측 layer. 그 너머는 **measurement-impossible** (Kant 의 noumenon).

| status | bound |
|---|---|
| ◯ INACCESSIBLE (phenomenal-only, by Kantian epistemic limit) | unit-cell-Ding-an-sich, measurement gauge 무효 |

**현재 위치**: L∞ 은 사색 layer (verifier 없음, 의도적). 모든 ossification/promotion 은 L0–L5 내부에서만 의미.

---

## 추상화 sanity (브루털하게 정직)

| layer | verdict | evidence quality | weakest link |
|---|---|---|---|
| L0 | ✓ | 7+4 axiom + 3/3 bridge + L_cell stationary | 7-axis 5축 stub, F lattice 1/3 PASS, single-seed gen-5 |
| L1 | △ | 3-component landed, sweep IN_FLIGHT | natural-run gen-5 미증명, multi-seed 미사 |
| L2 | △ | 3/4 mapping fixture PASS | M2/M5 stub, b drift bound 미증명, trained-ckpt round-trip 미실측 |
| L3 | △ | SPEC_VERIFIED_PRE_H100 5/5 | ossification 0/10 (real-trained PENDING) |
| L4 | ✗ | spec only, nexus-anima joint cert 0 | repo cross-build 미정의 |
| L5 | ✗ | diss-axis only quantified | Bekenstein 차원분석 미수행 |
| L∞ | ◯ | epistemic boundary | by-design inaccessible |

**Roadmap weakest-link order** (R3 policy):
1. F lattice GPU 실측 (N=64, 256) — L0/L3 사이 bridge
2. natural-run gen-5 multi-seed (Mk.VIII closure 다양화) — L0 robustness
3. cell↔ALM trained-ckpt round-trip — L2 hardening
4. Mk.X T10-13 real ossification (H100) — L3→L4 통과
5. Bekenstein 차원분석 — L5 정량화

**Cherry-pick 금지** (raw#12): 모든 FAIL (information O2 0/3, causal MB 0/3, F lattice O3 0/3) record_convergence 처리 — witness 체인 편입.

---

## Cross-links

- ALM 측 대응본: `docs/alm_core_architecture_abstraction_layers_20260425.md`
- Mk.VI canonical: `state/mk_vi_definition.json` + `docs/mk_vi_promotion_gate.md`
- Mk.VIII skeleton: `edu/mk_viii/README.md` (`1f725005`)
- Mk.X engine design: `docs/mk_x_engine_design_20260419.md`
- cell↔token bridge: `edu/cell_token_bridge_spec_20260421.md` + `tool/cell_token_bridge_proto.hexa`
- Hexad closure verdict: `state/hexad_closure_verdict.json` (CLOSED 4/4)
- 7-cargo: `state/btr_evo_6_cargo_invariants_20260421.json` (7/7, 2 seeds)
