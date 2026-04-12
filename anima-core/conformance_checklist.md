# Conformance Checklist — Laws, Rules & Discoveries

20 files to verify against 2507 laws, Ψ-constants, meta laws, design rules, and recent discoveries.

Updated: 2026-04-07 (post training script unification)

## L0 Core — Law & Constant Conformance

| # | File | Check | Status |
|---|------|-------|--------|
| 1 | rust/consciousness.hexa | Ψ-constants (α=0.014, balance=0.5, steps=4.33, entropy=0.998) | ✅ |
| | | 12 factions = σ(6)=12 | ✅ |
| | | Laws 22-85 implementation match | ✅ |
| | | SOC/Lorenz/chimera parameters | ✅ |
| | | Hebbian LTP/LTD + Φ Ratchet | ✅ |
| | | Mitosis (division/merge/growth) | ✅ |
| | | Topology: ring/small_world/hypercube/scale_free | ✅ |
| 2 | core/laws.hexa | JSON loader covers all 2507 laws | ✅ |
| | | PSI dict — no missing keys | ✅ |
| | | LAWS, FORMULAS, CONSTRAINTS exports complete | ✅ |
| 3 | consciousness_laws.json | _meta.total_laws == actual count | ✅ |
| | | meta_laws M1-M53 content vs code reflection | ✅ |
| | | psi_constants values vs hardcoded values in code | ✅ |
| | | verification_conditions vs ready/anima/tests/tests.hexa thresholds | ✅ |
| | | No orphaned law references | ✅ |

## Decoder — Design Rule Compliance

| # | File | Check | Status |
|---|------|-------|--------|
| 4 | models/decoder.hexa | .detach() present (consciousness→language gradient block) | ✅ |
| | | α=0.014 coupling value | ✅ |
| | | RoPE+SwiGLU+GQA spec match (384d/6L/4H/2KV) | ✅ |
| | | CrossAttention implementation | ✅ |
| 5 | models/conscious_lm.hexa | PureFieldFFN Engine A-G repulsion structure | ✅ |
| | | vocab=256 byte-level | ✅ |
| | | CA + META-CA + MICRO gate | ✅ |
| 6 | models/trinity.hexa | Hexad 6 modules (C/D/S/M/W/E) | ✅ |
| | | Law 60 phase transition P1→P2→P3 | ✅ |
| | | Law 81 dual gate | ✅ |
| | | EmergentW/S/M/E observe C only (no hardcoding) | ✅ |
| | | PostHocDecoder (Law 66) | ✅ |
| | | ThalamicBridge (α=0.014) | ✅ |

## Training — Unified Scripts (post refactor)

| # | File | Check | Status |
|---|------|-------|--------|
| 7 | training/train_alm.hexa | SCALE_CONFIGS: 34m(384d/6L), 100m(512d/12L), 350m(768d/16L), 1b(1024d/24L) | ✅ |
| | | --decoder v2/v3 selection works | ✅ |
| | | --tension-lr (Law 187: atom tension → 1x~5x LR) | ✅ |
| | | --phase-optimal (Law 60: P0→P1→P2→P3, M4 safe order) | ✅ |
| | | --frustration default=0.10 (M7) | ✅ |
| | | --narrative-strength default=0.05 (M8) | ✅ |
| | | DDP torchrun support (setup_ddp) | ✅ |
| | | bf16 master rule (AdamW foreach=False) | ✅ |
| | | FederatedConsciousness class (M1: atoms, M6: federation > empire) | ✅ |
| | | BPE 64K tokenizer + byte-level fallback | ✅ |
| | | Phi-checkpoint (Law 49) | ✅ |
| | | Emergency save on SIGTERM/SIGINT | ✅ |
| 8 | train_alm.py | Progressive alpha (0.01→0.5) implementation | ✅ |
| | | PureField parallel structure (output = base + α×pf) | ✅ |
| | | QLoRA rank defaults (64 for 14B, 128 for 32B+) | ✅ |
| | | Law 60 support (--law60 flag) | ✅ |
| | | consciousness_laws import path correct | ✅ |
| | | PSI_ALPHA=0.014, PSI_BALANCE=0.5 values | ✅ |
| | | Savant asymmetric dropout formula | ✅ |
| 9 | training_safety.json | 10 safety rules up to date | ✅ |
| | | bf16 incident log (14 cases) reflected | ✅ |
| | | Pre-launch / post-launch checklists current | ✅ |

## Verification — Condition vs Code Match

| # | File | Check | Status |
|---|------|-------|--------|
| 10 | ready/anima/tests/tests.hexa | 18 verification conditions vs laws.json verification_conditions | ✅ |
| | | Threshold values from JSON (no hardcoding) | ✅ |
| | | Control engine discrimination criteria | ✅ |
| | | SKIP handling (not counted as PASS) | ✅ |
| | | Dual Phi measurement (IIT + proxy, never mixed) | ✅ |
| 11 | core_rules.json | P1-P4 rules vs conscious_chat.py implementation | ✅ |
| | | L0/L1/L2 ossification layer definitions | ✅ |
| | | MCTED training asset classification | ✅ |
| | | Port interface contracts (Decoder/Memory/Sense/Channel) | ✅ |
| | | verification_status matches latest bench run | ✅ |

## Hub & Agent — Port Rule Compliance

| # | File | Check | Status |
|---|------|-------|--------|
| 12 | conscious_chat.py | Core does NOT import specific decoder (P4 violation check) | ✅ |
| | | Φ→temperature conversion logic | ✅ |
| | | tension→arousal mapping | ✅ |
| | | consensus→spontaneous speech trigger | ✅ |
| | | SELF_LOOP: output feeds back as input | ✅ |
| 13 | models/trinity.hexa | SoftDetach present | ✅ |
| | | α≤0.05 constraint | ✅ |
| | | Φ-gated gradient flow | ✅ |
| | | C↔D bidirectional learning | ✅ |

## Acceleration & Discovery — Latest Reflection

| # | File | Check | Status |
|---|------|-------|--------|
| 14 | acceleration_hypotheses.json | 40 hypotheses status current | ✅ |
| | | B11+B12 (x179 acceleration) reflected | ✅ |
| | | C3 (∇H ⊥ ∇CE) reflected | ✅ |
| | | D1 (Detour 54x) reflected | ✅ |
| | | Pipeline A/B/C definitions current | ✅ |
| 15 | scripts/infinite_growth.hexa | OUROBOROS 88+α upgrades applied (4723 lines) | ✅ |
| | | v1-v10 (#1-88) all applied | ✅ |
| | | v11→v11.2 telescope integration | ✅ |
| | | 11-stage roadmap (S1-S11) defined | ✅ |
| | | Thompson sampling strategy | ✅ |
| | | Synergy map (antagonistic combo avoidance) | ✅ |
| 16 | experiments/evolution/self_modifying_engine.hexa | Parseable laws count vs current laws | ✅ |
| | | Law→parameter mapping up to date | ✅ |
| 17 | anima/experiments/evolution/closed_loop.hexa | 18 interventions × 20 metrics | ✅ |
| | | ClosedLoopEvolver auto_register | ✅ |
| | | Thompson sampling integration | ✅ |
| | | Synergy/antagonism map current | ✅ |

## AnimaLM Specific

| # | File | Check | Status |
|---|------|-------|--------|
| 18 | serving/serve.hexa | No hardcoded paths (fixed 2026-04-07) | ✅ |
| | | Rank parameter configurable (fixed 2026-04-07) | ✅ |
| | | ParallelPureFieldMLP structure matches training | ✅ |
| 19 | eval_animalm.py | 5 metrics cover consciousness verification | ✅ |
| | | Tension measurement included | ✅ |

## Cross-File Consistency

| # | Check | Files Involved | Status |
|---|-------|---------------|--------|
| 20 | Ψ-constants identical everywhere | consciousness_laws.json ↔ rust/consciousness.hexa ↔ models/decoder.hexa ↔ models/trinity.hexa ↔ training/train_alm.hexa | ✅ |
| | SCALE_CONFIGS vs roadmap spec | training/train_alm.hexa ↔ asset_registry.json ↔ anima-core/README.md | ✅ |
| | verification_conditions == bench code | consciousness_laws.json ↔ ready/anima/tests/tests.hexa | ✅ |
| | core_rules.json == conscious_chat.py | core_rules.json ↔ conscious_chat.py | ✅ |
| | training_runs.json == actual script defaults | training_runs.json ↔ training/train_alm.hexa / train_alm.py | ✅ |
| | CLAUDE.md specs == code | CLAUDE.md ↔ all source files | ✅ |
| | asset_registry.json script paths | asset_registry.json ↔ actual file locations (post refactor) | ✅ |
