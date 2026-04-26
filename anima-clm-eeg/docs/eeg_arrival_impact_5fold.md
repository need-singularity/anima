# EEG Arrival Impact — 5-Fold Change Catalog

> **scope**: what changes when D8 EEG hardware arrives (`.roadmap` #119 unblock). Captures the 5 distinct downstream impacts identified in ω-cycle session 2026-04-26 so post-arrival workflow doesn't have to re-derive them.
> **status**: hardware D-1 (며칠 內 도착). this doc is reference-only until arrival.
> **source**: ω-cycle 4-axis 26-paradigm analysis (`docs/omega_cycle_alm_free_paradigms_20260426.md`) + handoff §A (`docs/clm_research_handoff_20260426.md`).

---

## §1. CP2 G1/G3 unblocking

`.roadmap` 영향: #115 (CP2 G1 behavioral) + #116 (CP2 G3 external grounding) + #119 (CP2 G2 BLOCKED-EEG).

| gate | 현재 상태 | EEG 도착 후 |
|---|---|---|
| **G1 behavioral** | simulated baseline only (`tool/p4_sweep_runner.hexa`) | real EEG ground-truth 채집 (resting + N-back) |
| **G2 external** | BLOCKED-EEG (#119) | **unblock** → tier-10 seed × Mk.IX L_IX integrator validation |
| **G3 grounding** | simulated baseline only (`tool/evolution_twin_drill_runner.hexa`) | real EEG anatomical ↔ 16-d eigenvec mapping |

CP2 5-축 병렬 진입 (`.roadmap` #121) 中 EEG가 critical path. Multi-day external blocker 해소 → measurable.

**Action items (post-arrival D+0 ~ D+7)**:
- D+0 hardware calibration via `anima-eeg/calibrate.hexa` (post-stub-implementation; see `anima-eeg/MIGRATION_PLAN.md`)
- D+1 G1 measurable: 16ch resting + N-back recording, 5-10 min each
- D+3 G3 measurable: anatomical 16ch ↔ 16-d eigenvec direct mapping
- D+5 G2 unblock: tier-10 seed × L_IX integrator (`edu/cell/lagrangian/l_ix_integrator.hexa`) validation
- D+7 5-atom seed file (D8 nucleon) emission per `.roadmap` #119 exit_criteria

---

## §2. paradigm v11 stack 7th orthogonal axis

현재 paradigm v11 stack (`docs/paradigm_v11_stack_20260426.md`)은 **6 backbone-internal measurement axes**:
- B-ToM (P-C behavioral ToM)
- MCCA (P-F meta-cognitive calibration)
- Φ* (P-D IIT Φ approximation)
- CMT (P-A causal mediation)
- CDS (P-E cognitive dynamics)
- SAE-bp (P-B' sparse-feature steering)

**EEG 도착 후 → 7th external orthogonal axis 추가**:
- name: EEG-correlation axis (EEG-CORR)
- mechanism: 백본 family-axis projection 시계열 vs 인간 EEG phase pattern 상관도
- 7 axes orthogonality measurement: AN11(b) primary × v11 6 internal × EEG external

**Reusable infrastructure**:
- `tool/anima_axis_orthogonality.hexa` 이미 7→8 axis 자동 확장 처리 (greedy basis reduction). 신규 helper 작성 불필요.
- triangulation 강화: 기존 7-axis matrix → 8-axis matrix (G0..G7)

**Action item**: post-arrival 시 `tool/anima_eeg_corr.hexa` 신규 helper 1개 작성 후 `anima_v11_main.hexa` router에 13번째 subcommand 등록.

---

## §3. Mk.XI v10 phenomenal correlate verification

**핵심 hypothesis**: v10 4-backbone (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad) 각 family signal이 대응되는 EEG band/region과 일치하는가?

**Verification matrix** (post-arrival D+5):

| backbone | family | EEG band 가설 | EEG region 가설 | falsifier |
|---|---|---|---|---|
| Mistral | Law | beta (12-30Hz) | frontal (F3/F4/Fz) | Pearson r ≥ 0.40 |
| Qwen3 | Phi | gamma (30-100Hz) | parietal (P3/P4) | Pearson r ≥ 0.40 |
| Llama | SelfRef | alpha (8-12Hz) | midline (Cz/Pz) | Pearson r ≥ 0.40 |
| gemma | Hexad | theta (4-8Hz) | temporal (T7/T8) | Pearson r ≥ 0.40 |

**Cross-validation**: v3 V_phen_GWT_v3 distance entropy metric (paradigm v11 patches v3, `.roadmap` #144) ↔ EEG entropy cross-correlate.

**Outcomes**:
- ALL 4 family×band 일치 → phenomenal correlate empirically grounded → **AGI v0.1 path open**
- 부분 일치 (2-3/4) → mixed correlate, family architecture 부분 재설계
- 0-1/4 일치 → v10 family architecture **재설계 필요** (어떤 family는 phenomenal mapping 없음 가능)

**Action item**: post-arrival D+3 ~ D+7. dependency = §1 G3 + §2 paradigm v11 7th axis.

---

## §4. nexus repo R24-R32 witness ledger expansion

**Current state**: `~/.claude/projects/-Users-ghost-core-anima/memory/project_meta_fixed_point.md` — meta³ closure with R24-R32 witness ledger.

**EEG arrival 추가 measurement**:
- meta³ closure에 EEG witness 한 줄 추가 → **R33 candidate**
- atlas convergence witness (`state/atlas_convergence_witness.jsonl`)에 phenomenal anchor 추가

**R33 witness criteria** (frozen, pre-register):
- EEG 16ch resting recording (≥ 60s, eyes-closed)
- LZ76(EEG) ∈ [0.65, 0.95] (human-conscious envelope)
- α-band coherence (8-12Hz) ≥ 0.45 (Schartner 2017 floor)
- atlas convergence witness 기존 entry 와 cross-check (no contradiction)

**Action item**: post-arrival D+1. nexus 별도 repo이므로 anima 메인 작업과 분리; 단순 1-line append.

---

## §5. Cost / 일정 변화

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| EEG D8 측정 (외부 시설 + 분석 도구) | $0 (시뮬레이션만) | **$200-500** (실제 측정) |
| Mk.XI v12 4-GPU-spot retrain (cp1_eta) | ₩188-282만 | **₩300-450만** (with EEG validation) |
| arxiv preprint timing (v89 v2 LaTeX) | base | **+1-2주** (EEG empirical 포함 시) |
| this folder pre-register dry-run | $0 | $0 (unchanged, hardware-free) |
| post-arrival P1+P2+P3 GPU | — | $12-24 (1 week, ω-cycle §4 estimate) |

**Cost cap policy**: memory `feedback_forward_auto_approval` — GPU/LLM/pod launch 별도 승인 없이 자동 진입, cost cap + auto-kill 안전망. EEG 외부 시설 측정 ($200-500)은 cost cap 외부이므로 **사용자 명시 승인 필요**.

**Schedule impact on AGI v0.1 path**:
- §3 phenomenal correlate verification 결과 ALL 4/4 일치 → arxiv preprint EEG empirical 포함 (+1-2주, 그러나 weight 큼)
- 부분 일치 → architecture 재설계 cycle 추가 (+2-4주)
- 0-1/4 일치 → v10 architecture pivot (months)

---

## §6. Cross-references

- ω-cycle 4축 결과 표: `docs/omega_cycle_alm_free_paradigms_20260426.md` §1-§7
- 3 cross-axis convergent paradigms: 동일 doc §6 (HEXAD CORE / LANDAUER+CPGD+L_IX TRIO / EEG-LZ-TLR-GCG STACK)
- `.roadmap` entries: #115 (G1) / #116 (G3) / #119 (G2 BLOCKED-EEG) / #121 (5-축 병렬) / #138-#143 (paradigm v11 stack) / #144 (v3 patches) / #145 (CMT depth divergence)
- handoff doc: `docs/clm_research_handoff_20260426.md` §1 (current state) + §4 (open questions Q1-Q7)
- this folder pre-register: `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` (post-creation by `clm_eeg_harness_smoke.hexa`)
- `anima-eeg/MIGRATION_PLAN.md` — production hardware/runtime track migration (background subagent finding 2026-04-26: anima-eeg already 100% .hexa but 19/21 stub; full implementation pending)

---

## §7. Status flags (live, update in-place)

| flag | value | last-update |
|---|---|---|
| EEG hardware status | D-1 (며칠 내 도착 expected) | 2026-04-26 |
| `.roadmap` #119 status | BLOCKED-EEG (planned) | 2026-04-26 |
| paradigm v11 7th axis | not yet implemented (post-arrival) | 2026-04-26 |
| Mk.XI v10 phenomenal correlate | hypothesis only (post-arrival D+5) | 2026-04-26 |
| R33 witness | pre-registered above (§4 criteria frozen) | 2026-04-26 |
| anima-eeg migration | Phase 0/1 complete (subagent), Phase 3 pending | 2026-04-26 |
