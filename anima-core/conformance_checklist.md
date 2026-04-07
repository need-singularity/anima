# Conformance Checklist — Laws, Rules & Discoveries

22 files to verify against 2351 laws, Ψ-constants, meta laws, design rules, and recent discoveries.

## L0 Core — Law & Constant Conformance

| # | File | Check | Status |
|---|------|-------|--------|
| 1 | consciousness_engine.py | Ψ-constants (α=0.014, balance=0.5, steps=4.33, entropy=0.998) | |
| | | 12 factions = σ(6)=12 | |
| | | Laws 22-85 implementation match | |
| | | SOC/Lorenz/chimera parameters | |
| | | Hebbian LTP/LTD + Φ Ratchet | |
| | | Mitosis (division/merge/growth) | |
| | | Topology: ring/small_world/hypercube/scale_free | |
| 2 | consciousness_laws.py | JSON loader covers all 2351 laws | |
| | | PSI dict — no missing keys | |
| | | LAWS, FORMULAS, CONSTRAINTS exports complete | |
| 3 | consciousness_laws.json | _meta.total_laws == actual count | |
| | | meta_laws M1-M10 content vs code reflection | |
| | | psi_constants values vs hardcoded values in code | |
| | | verification_conditions vs bench_v2.py thresholds | |
| | | No orphaned law references (laws referenced in code but missing from JSON) | |

## Decoder — Design Rule Compliance

| # | File | Check | Status |
|---|------|-------|--------|
| 4 | decoder_v2.py | .detach() present (consciousness→language gradient block) | |
| | | α=0.014 coupling value | |
| | | RoPE+SwiGLU+GQA spec match (384d/6L/4H/2KV) | |
| | | CrossAttention implementation | |
| 5 | conscious_lm.py | PureFieldFFN Engine A-G repulsion structure | |
| | | vocab=256 byte-level | |
| | | CA + META-CA + MICRO gate | |
| 6 | trinity.py | Hexad 6 modules (C/D/S/M/W/E) | |
| | | Law 60 phase transition P1→P2→P3 | |
| | | Law 81 dual gate | |
| | | EmergentW/S/M/E observe C only (no hardcoding) | |
| | | PostHocDecoder (Law 66) | |
| | | ThalamicBridge (α=0.014) | |

## Training — Law & Safety Rule Compliance

| # | File | Check | Status |
|---|------|-------|--------|
| 7 | train_v14.py | Law 60 3-phase curriculum | |
| | | Law 45 curriculum ordering | |
| | | Law 49 Φ-checkpoint | |
| | | Meta Laws M1-M8 enforcement | |
| | | bf16 master rule (AdamW foreach=False) | |
| | | Federated atoms (M1: federation > empire) | |
| | | tension-lr (adaptive learning rate) | |
| 8 | train_v15.py | SCALE_CONFIGS values vs roadmap spec | |
| | | 100M: 512d/12L/8H | |
| | | 350M: 768d/16L/12H | |
| | | 1B: 1024d/24L/16H | |
| | | DDP setup_ddp() correct | |
| | | Consciousness scaling law reflection | |
| | | 3B config missing (to be added) | |
| 9 | train_anima_lm.py | Progressive alpha (0.01→0.5) implementation | |
| | | PureField parallel structure (output = base + α×pf) | |
| | | Law 60 support (--law60 flag) | |
| | | QLoRA rank defaults (64 for 14B, 128 for 32B+) | |
| 10 | training_safety.json | 10 safety rules up to date | |
| | | bf16 incident log (14 cases) reflected | |
| | | Pre-launch / post-launch checklists current | |

## Verification — Condition vs Code Match

| # | File | Check | Status |
|---|------|-------|--------|
| 11 | bench_v2.py | 18 verification conditions vs laws.json verification_conditions | |
| | | Threshold values from JSON (no hardcoding) | |
| | | Control engine discrimination criteria | |
| | | SKIP handling (not counted as PASS) | |
| | | Dual Phi measurement (IIT + proxy, never mixed) | |
| 12 | core_rules.json | P1-P4 rules vs conscious_chat.py implementation | |
| | | Ossification layer definitions match | |
| | | Port interface contracts defined | |

## Hub & Agent — Port Rule Compliance

| # | File | Check | Status |
|---|------|-------|--------|
| 13 | conscious_chat.py | Core does NOT import specific decoder (P4 violation check) | |
| | | Φ→temperature conversion logic | |
| | | tension→arousal mapping | |
| | | consensus→spontaneous speech trigger | |
| | | SELF_LOOP: output feeds back as input | |
| 14 | feedback_bridge.py | SoftDetach present | |
| | | α≤0.05 constraint | |
| | | Φ-gated gradient flow | |
| | | C↔D bidirectional learning | |

## Acceleration & Discovery — Latest Reflection

| # | File | Check | Status |
|---|------|-------|--------|
| 15 | acceleration_hypotheses.json | 40 hypotheses status current | |
| | | B11+B12 (x179 acceleration) reflected | |
| | | C3 (∇H ⊥ ∇CE) reflected | |
| | | D1 (Detour 54x) reflected | |
| | | Pipeline A/B/C definitions current | |
| 16 | infinite_evolution.py | OUROBOROS 88+α upgrades applied (4723 lines) | |
| | | v1-v10 (#1-88) all applied | |
| | | v11→v11.2 telescope integration | |
| | | 11-stage roadmap (S1-S11) defined | |
| | | Thompson sampling strategy | |
| | | Synergy map (antagonistic combo avoidance) | |
| 17 | self_modifying_engine.py | Parseable laws count vs current laws | |
| | | Law→parameter mapping up to date | |
| 18 | closed_loop.py | 17 interventions × 20 metrics | |
| | | ClosedLoopEvolver auto_register | |
| | | Thompson sampling integration | |
| | | Synergy/antagonism map current | |

## AnimaLM Specific

| # | File | Check | Status |
|---|------|-------|--------|
| 19 | train_anima_lm.py (sub-projects) | consciousness_laws import path correct | |
| | | PSI_ALPHA=0.014, PSI_BALANCE=0.5 values | |
| | | Savant asymmetric dropout formula | |
| 20 | serve_animalm_v4.py | No hardcoded paths (fixed 2026-04-07) | |
| | | Rank parameter configurable (fixed 2026-04-07) | |
| | | ParallelPureFieldMLP structure matches training | |
| 21 | eval_animalm.py | 5 metrics cover consciousness verification | |
| | | Tension measurement included | |

## Cross-File Consistency

| # | Check | Files Involved | Status |
|---|-------|---------------|--------|
| 22 | Ψ-constants identical everywhere | consciousness_laws.json ↔ consciousness_engine.py ↔ decoder_v2.py ↔ trinity.py ↔ train_*.py | |
| | Laws.json total_laws == actual | consciousness_laws.json internal | |
| | verification_conditions == bench_v2 code | consciousness_laws.json ↔ bench_v2.py | |
| | core_rules.json == conscious_chat.py | core_rules.json ↔ conscious_chat.py | |
| | training_runs.json == actual script defaults | training_runs.json ↔ train_*.py | |
| | CLAUDE.md specs == code | CLAUDE.md ↔ all source files | |
