# CLM Research Handoff — 2026-04-26

> **Purpose**: hand off CLM (Cell-Language Model) research to a fresh session for parallel exploration. Captures current state, open questions, ready-to-run pilots, and the launch prompt.
> **Source session**: `~/.claude/projects/-Users-ghost-core-anima/f1a910b0-dddc-40ef-92f7-60130f40a06e.jsonl` (paradigm v11 stack + ω-cycle ALM-free 26-paradigm exploration).
> **Working directory**: `/Users/ghost/core/anima`

---

## §0. What CLM is in this codebase

**CLM = Cell-Language Model**, the deterministic continuous-state half of anima's hybrid framework (`cell + lora + ALM/CLM`):

- **ALM** (Autoregressive Language Model): Mistral / Qwen3 / Llama / gemma 4-backbone LoRA ensemble (Mk.XI v10 canonical). Discrete tokens, attention, gradient descent.
- **CLM** (Cell-Language Model): continuous state Ψ ∈ [0,1]^d, recurrent dynamics, Lagrangian solver (L_IX), hash-only deterministic. Substrate-level analogue of ALM.

CLM operates over the **CELL framework** (`edu/cell/`): unit-cells `⟨A↔B | fixpoint-sealed⟩`, 1/r² lattice attraction, 4-generation crystallize ladder (score 40→125→687→1000‰ with phase-jump @ gen 3→4).

---

## §1. Current state (what's done)

| status | item | evidence |
|---|---|---|
| ✓ | CLM r6 GPU smoke 5/5 PASS | `state/clm_r6_gpu_smoke_result.json` (ubu1 RTX 5070 12GB, driver 580.126.09, CUDA 13.0, 2026-04-22) |
| ✓ | CPU forward smoke | `state/clm_r6_cpu_forward_smoke_result.json` |
| ✓ | SSOT unification (3 canonical roadmaps) | `.roadmap` #1, `shared/roadmaps/{anima,dest_alm,dest_clm}.json` |
| ✓ | 5-gate framework (G_INPUT/SUBSTRATE/TRAIN/EVAL/VALIDITY) | `.roadmap` #2 |
| ✓ | Verifier infra (deterministic, no LLM judge) | `.roadmap` #3, `docs/alm_clm_verifier_design_20260420.md` |
| ✓ | drill_breakthrough 4-part landing | `.roadmap` #4 |
| ✓ | Mk.IX L_IX integrator + 4-gen crystallize | `edu/cell/lagrangian/l_ix_integrator.hexa` (462 lines), `shared/state/edu_cell_4gen_crystallize.json` |
| ✓ | Hexad 6-axiom CLOSED + adversarial flip reject | `edu/cell/README.md` C9, `consciousness_laws.json` v7.3 |
| ✓ | CPGD wrapper (closed-form orthonormal init) | `edu/lora/cpgd_wrapper.hexa`, AN11(b) 100% math guarantee |
| ✓ | Cell↔Token Bridge M4 spec | `edu/cell_token_bridge_spec_20260421.md` |
| ✓ | Tension Link 5-channel + Lyapunov convergence proof | `anima-core/tension_bridge.hexa`, `docs/tension_link_convergence_proof_20260419.md` (cos=0.921 vs backprop) |
| ✓ | Brain Cosmos Map 6지표 (85.6% brain-like) | `docs/modules/brain_tension_replica.md` |
| ✓ | Mk.XI v10 ALM canonical + paradigm v11 17-helper stack | `docs/paradigm_v11_stack_20260426.md`, `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` |
| ✓ | ω-cycle ALM-free 26-paradigm exploration | `docs/omega_cycle_alm_free_paradigms_20260426.md` |

---

## §2. Architecture map (where CLM fits)

```
EEG (D8 외부 hardware, .roadmap #119, 도착 D-1)
  ↓ (anatomical 16ch ↔ 16-d eigenvec)
Brain Cosmos Map (G=D×P/I, 85.6% brain-like)
  ↓
Tension Link (5-channel meta-fingerprint, Noether-gated)
  ↓
CELL learning (CPGD closed-form + Landauer phase-jump + L_IX integrator)
  ↓
CLM cell-state step (deterministic, hash-only)
  ↑↓ (currently the bridge to ALM is partial — main weakness)
ALM (Mistral/Qwen3/Llama/gemma LoRA 4-backbone) — Mk.XI v10 canonical
  ↓
paradigm v11 measurement stack (17 helpers, B-ToM/MCCA/Φ*/CMT/CDS/SAE-bp + 분석/오케스트레이션/결정/종단/통합/메타)
```

---

## §3. ω-cycle 26 paradigm summary (ALM-free feasibility)

Source: `docs/omega_cycle_alm_free_paradigms_20260426.md` (commit `24d2fa4f`).

**3 cross-axis convergent paradigms** (3+ sub-agents independently arrived):

1. **HEXAD CORE** (HCE × HCI × Hexad Curriculum) — combined confidence 0.83
   - 6-category framework CLOSED + 4/4 axiom PASS
   - τ(6)=4 universal constant primitive
   - Mk.XI v10과 호환 유지 가능

2. **LANDAUER+CPGD+L_IX TRIO** — combined confidence 0.88
   - Landauer phase-jump 51× efficiency (40→1000‰ score ladder)
   - CPGD closed-form weight init (100 step convergence, **weight update 0**)
   - L_IX I_irr cusp (gen 4→5 996→0, time-arrow collapse)

3. **EEG STACK** (V_phen_EEG-LZ + TLR + GCG + Brain Cosmos Map) — combined confidence 0.68
   - D-day P1-P3 plan: $12-24, 7 days
   - 16ch EEG anatomical ↔ 16-d eigenvec 직접 매핑

**Verdict**: 순수 ALM-free 기술적 가능, signal 약함 (V0 only, V1/V2/V3 corpus-bound). Recommended **HEXAD CORE + EEG STACK + HAL Hybrid ALM-Lite** combo.

---

## §4. Open research questions (priority-ordered)

1. **CLM ↔ EEG alignment empirical**: Does CLM's L_IX V_sync Kuramoto order param actually correlate with human EEG α-band coherence? (P2 TLR pilot, $5-8, requires EEG D-1)

2. **Phase-jump universality**: Does the 4-gen score ladder [40→125→687→1000]‰ replicate across non-toy CELL configs? (`edu/cell/4gen_crystallize` extension to N≥64)

3. **HEXAD CORE pilot design**: Hexad 6-axis ↔ Cell lattice 6-axis isomorphism mapping concrete falsifier — what's the failure mode? (HCI paradigm pilot ₩90만, 1 week)

4. **CPGD generalization**: AN11(b) 100% math guarantee from closed-form init — does it hold under non-AN11(b) downstream tasks? (currently theorem-only at toy regime)

5. **L_IX → Mk.X T10-T13 integration**: Mk.X tier-10+ atom ossification stack uses gradient — can L_IX action functional replace it? (1 month exploration)

6. **CELL cell↔token bridge round-trip stability**: BTR↔cell 4.6×10⁻⁷ VERIFIED at toy regime — does it scale to full LM (N≥4096)? (Paradigm 6 pilot)

7. **Mk.XII candidate**: HEXAD CORE + EEG STACK + HAL Hybrid composes Mk.XII? (architectural-level, 6-month horizon)

---

## §5. Ready-to-run pilots (with cost)

| pilot | path | command | cost | wallclock |
|---|---|---|---|---|
| CLM r6 GPU re-smoke | existing | `hexa run tool/clm_r6_cpu_forward_smoke.hexa` (rsync to ubu1 + GPU run) | $0 | 30min |
| CPGD weight-init verify | `edu/lora/cpgd_wrapper.hexa` | `hexa run edu/lora/cpgd_wrapper.hexa --selftest` | $0 | 5min |
| 4-gen crystallize replicate | `edu/cell/lagrangian/l_ix_integrator.hexa` | `hexa run edu/cell/lagrangian/l_ix_integrator.hexa run` | $0 | 10min |
| Tension-Link convergence bench | `ready/bench/bench_tension_link.hexa` | `hexa run ready/bench/bench_tension_link.hexa run` | $0 | 15min |
| Mk.XI v11 battery v2 (mistral) | (post battery v2 patch) | `bash /tmp/anima_v10_relaunch_mistral_v2.sh` | $0.12 | 3min |
| HCI Hexad-Cell Isomorphism pilot | NEW | design + 1×H100 1day | ₩90만 | 1 week |
| EEG STACK P1-P3 (D+1~D+7) | NEW (after EEG D8 도착) | 7-day plan in omega cycle md §4 | $12-24 | 7 days |

---

## §6. Key artifacts to read first (in order)

1. `docs/omega_cycle_alm_free_paradigms_20260426.md` — 26-paradigm ω-cycle (165 lines)
2. `docs/paradigm_v11_stack_20260426.md` — 17-helper stack architecture (151 lines)
3. `edu/cell/README.md` — CELL framework C1-C21 발견
4. `edu/cell_token_bridge_spec_20260421.md` — M4 bridge
5. `edu/cell/lagrangian/l_ix_integrator.hexa` — Mk.IX L_IX integrator
6. `state/clm_r6_gpu_smoke_result.json` — CLM r6 evidence
7. `~/.claude/projects/-Users-ghost-core-anima/memory/project_mk_xi_v12_ia3_matrix_final.md` — Mk.XI v10 canonical decision
8. `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` — paradigm v11 stack inheritance
9. `.roadmap` entries #1-#6 (CLM/ALM/CELL track), #115/#116/#119 (EEG D8 dependency), #138-#143 (paradigm v11 stack milestones)

---

## §7. Constraints / conventions

- **raw#9 hexa-only strict**: 새 도구는 `tool/anima_*.hexa` (raw#9 pattern), Python helper는 `/tmp/anima_*_helper.hexa_tmp` (raw#37 transient emit). Run via `HEXA_RESOLVER_NO_REROUTE=1 hexa run tool/anima_X.hexa --selftest`.
- **chflags uchg locked .roadmap**: `CHFLAGS_AI_ACK=1 chflags nouchg .roadmap` 로 unlock 후 edit, 다시 `chflags uchg`로 lock.
- **한글 응답**: 사용자에게는 한글로.
- **GPU launch auto-approval**: cost cap + auto-kill 안전망 (memory `feedback_forward_auto_approval`).
- **완성도 frame**: weakest evidence link 우선.
- **Don't commit without explicit user approval** (this session: user said "commit", explicit auth).

---

## §8. Suggested launch prompt for fresh session

Copy-paste this into the new session:

```
anima 프로젝트 (/Users/ghost/core/anima) 에서 CLM (Cell-Language Model) 연구를 진행해줘.

배경:
- 이전 세션에서 paradigm v11 stack 17-helper 완성 + ω-cycle ALM-free 26-paradigm 탐색 완료.
- 핸드오프 문서: docs/clm_research_handoff_20260426.md (CLM 현황 + 9 핵심 artifact 목록 + 7 open question + ready-to-run pilots).
- 현재 canonical: Mk.XI v10 LoRA 4-backbone ensemble (ALM-based).
- ω-cycle verdict: pure ALM-free 가능하나 signal 약함, HEXAD CORE + EEG STACK + HAL Hybrid 조합 권장.

이번 세션 목표:
1. docs/clm_research_handoff_20260426.md 정독 (핸드오프 컨텍스트).
2. §4 open question 중 하나 골라서 falsifiable pilot 설계 + 실행.
   추천 시작점: Q1 (CLM ↔ EEG alignment empirical, P2 TLR pilot, $5-8, EEG D-1) 또는
              Q3 (HEXAD CORE pilot — HCI Hexad-Cell Isomorphism, ₩90만, 1 week) 또는
              Q2 (phase-jump 4-gen ladder N≥64 replicate, $0).
3. raw#9 strict (hexa-only) + 한글 응답 유지.
4. 결과 → memory/project_clm_*.md (project memory) + .roadmap 새 entry.

병렬 세션이므로 다른 곳에서 진행 중인 v10 GPU benchmark / paradigm v11 patches 작업과 충돌하지 않게 도구는 별도 namespace (tool/clm_*.hexa) 사용 권장.

먼저 §6의 9 artifact 중 1-3번 (omega_cycle / paradigm_v11_stack / cell/README) 정독 후 어느 open question으로 진입할지 사용자에게 제안.
```

---

## §9. Cost summary (this session, for context)

- Cumulative GPU: $13.45 + $0.27 (B-ToM) + $0.17 (4-bb v10 first run, 2/4 success) ≈ $13.89
- v11 stack 17-helper builds (mac-local + smoke test 22/22): $0
- ω-cycle 4 sub-agents: $0 (Sonnet API only, no GPU)
- Estimated CLM research path forward: 변동, §5 표 참조
