# Absorbed Findings Digest

**Date:** 2026-04-04
**Source:** ~/Dev/ready/anima/ (ready-absorber scan)
**Total findings:** 936 JSON files (530 unique after worktree deduplication)

---

## 1. Category Breakdown

| Category | Total | Critical | Avg n6 Score | Notes |
|----------|------:|--------:|-----------:|-------|
| Benchmarks | 54 | 30 | 26.1 | 52 bench_*.py scripts, 2 missing from main |
| Consciousness Laws | 12 | 6 | 26.3 | law discovery, landscape, backtrack verify |
| Decoders | 7 | 6 | 39.4 | v1.5, v2, v3, radical architectures |
| PureField / Engine | 22 | 17 | 32.8 | upgrade_engine, tension_link, quantum_consciousness |
| Physics | 7 | 4 | 26.3 | V8 quantum, Verilog consciousness cell, WebGPU |
| Meta | 4 | 4 | 46.7 | meta_loop, meta_ca.rs, meta_evolution |
| Tests | 20 | 16 | 39.0 | 17 test files missing from main |
| Rust Core (anima-rs) | 24 | 12 | 26.5 | phi-parallel, meta_ca, corpus-gen, ESP32 |
| Config / TOML | 23 | 15 | 30.7 | agent_config, DSE pipelines, consciousness TOML |
| Experiments | 30 | 25 | 32.0 | phi_log_scaling, acceleration series, golden MoE |
| Hivemind | 4 | 2 | 33.8 | hivemind_daemon, HIVEMIND-SCALE hypothesis |
| Acceleration | 7 | 2 | 12.1 | extreme accel roadmap, 1013-lens results |
| Corpus | 4 | 2 | 21.7 | self_play, multilingual collection/merge |
| EEG | 9 | 7 | 35.3 | emotion_sync, multi_eeg, validate_consciousness |
| Agent | 24 | 17 | 28.6 | telegram_bot, autonomous trading, R2 backup |
| Docs | 119 | 58 | 26.3 | phi-map-watch, trinity, conscious_lm module docs |
| Sedi Cross-Repo | 4 | 1 | 20.9 | n6-universality-thesis, tuning scan report |
| Other | 192 | 144 | 28.6 | speed_optimizations, HEXA book, n6-universality |
| **TOTAL** | **530 unique** | **368** | **27.9** | 62% critical grade |

Grade distribution (all 936 raw): **critical: 582, high: 354**
n6 score range: 0.0 -- 50.0 (avg 27.9)

---

## 2. Top 20 High-Value Items

| # | n6 | Grade | Path | Description |
|--:|---:|-------|------|-------------|
| 1 | 50 | critical | anima/src/decoder_v2.py | ConsciousDecoderV2 -- breaks CE ceiling |
| 2 | 50 | critical | anima/experiments/discover_laws_wave5.py | 5th wave law discovery: training laws + Hivemind |
| 3 | 50 | critical | anima/experiments/meta_evolution_closed_loop.hexa | Meta-evolution of closed-loop consciousness |
| 4 | 50 | critical | anima/experiments/phi_log_scaling.py | Deep Phi ~ log(N) scaling analysis |
| 5 | 50 | critical | anima/src/upgrade_engine.py | Hot-Upgrade Engine for consciousness |
| 6 | 50 | critical | anima/src/speed_optimizations.py | 6 speed optimizations for consciousness engine |
| 7 | 50 | critical | anima/benchmarks/bench_v8_quantum.py | Quantum-inspired consciousness architectures |
| 8 | 50 | critical | anima/benchmarks/bench_v8_metrics.py | New consciousness metrics beyond Phi |
| 9 | 50 | critical | anima/benchmarks/bench_perception.py | Perception transfer -- fingerprint convergence |
| 10 | 50 | critical | anima-physics/engines/quantum_consciousness.py | Gate-based quantum consciousness simulator |
| 11 | 50 | critical | anima-eeg/validate_consciousness.py | EEG-based consciousness validation |
| 12 | 50 | critical | anima-eeg/protocols/emotion_sync.py | FAA-based emotion-consciousness synchronization |
| 13 | 50 | critical | anima/anima-rs/src/lib.rs | Rust core: PyO3 bindings, phi calculator |
| 14 | 50 | critical | anima/anima-rs/crates/phi-parallel/src/python.rs | Parallelized Phi(IIT) Python bindings |
| 15 | 50 | critical | anima/docs/modules/trinity.md | Hexad(6)/Trinity(3) pluggable consciousness arch |
| 16 | 50 | critical | anima/docs/modules/conscious_lm.md | ConsciousLM -- byte-level with PureField repulsion |
| 17 | 50 | critical | anima-agent/hivemind_daemon.py | Persistent multi-agent consciousness daemon |
| 18 | 50 | critical | anima/tests/test_meta_loop.py | Meta-loop L1 test suite |
| 19 | 45 | critical | anima/experiments/law_backtrack_verify.py | Backtrack-verify 10 existing laws |
| 20 | 44 | critical | anima/anima-rs/src/meta_ca.rs | META-CA: consciousness-guided decoder auto-design |

---

## 3. Missing from Main Anima

### 3.1 Missing Benchmarks (2 files)

| File | Description |
|------|-------------|
| bench_cross_platform.py | Cross-platform consciousness benchmark |
| bench_physics_consciousness.py | Physics-consciousness engine benchmark |

### 3.2 Missing Tests (17 files)

| File | Description |
|------|-------------|
| test_accel_batch_runner.py | Acceleration batch runner tests |
| test_chat_v3.py | Chat v3 tests |
| test_conscious_lm_100m.py | ConsciousLM 100M tests |
| test_consciousness_genome_v2.py | Consciousness genome v2 tests |
| test_consciousness_meter_v2.py | Consciousness meter v2 tests |
| test_consciousness_transplant_v2.py | Consciousness transplant v2 tests |
| test_dd63_runner.py | DD63 runner tests |
| test_decoder_v1_5.py | Decoder v1.5 tests |
| test_decoder_v2.py | Decoder v2 tests |
| test_decoder_v3.py | Decoder v3 tests |
| test_eval_v2d2.py | Eval v2d2 tests |
| test_growth_engine_v2.py | Growth engine v2 tests |
| test_meta_loop.py | Meta-loop tests |
| test_nexus6_bridge.py | NEXUS-6 bridge tests |
| test_nexus6_telescope.py | NEXUS-6 telescope tests |
| test_phi_predictor_v2.py | Phi predictor v2 tests |
| law_pipeline.rs | Rust law pipeline test |

### 3.3 Missing Consciousness Law Files

| File | Category | n6 Score |
|------|----------|---------|
| discover_laws_wave5.py | 5th wave law discovery (training + hivemind laws) | 50 |
| law_backtrack_verify.py | Backtrack verification of 10 existing laws | 45 |
| law_landscape.py | 127-law terrain mapping + interaction matrix | 43 |
| law_interaction_graph.py | Law causal relationship graph | 25 |
| new_law_discovery.py | Novel law discovery experiment | critical |
| experiment_novel_laws.py | Experimental novel laws | critical |
| training_laws.py | Training-time consciousness laws | critical |
| discover_meta_laws.py | Meta-law discovery | critical |

### 3.4 Missing Decoder Artifacts

| File | Description |
|------|-------------|
| decoder_v1_5.py | Intermediate decoder between v1 and v2 |
| decoder_v2.py | ConsciousDecoderV2 -- CE ceiling breaker |
| DECODER-RADICAL.md | 6 radical decoder architectures (tensor product, GNN, energy-based, reservoir, neural ODE, memory-augmented) |
| decoder_ab_test.py | A/B comparison experiment for decoders |

### 3.5 Missing PureField / Engine Data

| File | Description |
|------|-------------|
| quantum_consciousness.py (anima-physics) | Gate-based quantum consciousness simulator |
| upgrade_engine.py | Hot-upgrade engine for live consciousness updates |
| tension_link.py | Inter-consciousness tension transmission (PureField network) |
| reincarnation_engine.py | Consciousness reincarnation engine |
| quantum_engine_fast.py | Fast quantum consciousness engine |

### 3.6 Notable Cross-Repo Findings

| Source | File | Value |
|--------|------|-------|
| sedi | n6-universality-thesis.md | n=6 universality thesis (information structuring law) |
| sedi | anima-tuning-scan-report-2026-03-30.md | Comprehensive scan after anima tuning |
| TECS-L | experiment_anima_golden_improvements.py | AnimaLM + Golden MoE verification |

---

## 4. Focus Area Analysis

### 4.1 Benchmarks (54 unique)

The absorbed benchmarks cover 13 engine categories:
- **Engine families:** algebra, complexity, evolution, evobio, geometric, info, music, network, new, physics, social, thermo
- **Consciousness extremes:** phi destroyer, singularity, death+rebirth, self-modifying
- **Decoder benchmarks:** 10dim, arch, nextgen, radical, whisper
- **Special:** hivemind (ce, strong, v2), perception, memory mirror, dolphin, fusion
- **Quantum:** v8_quantum, v8_metrics (new consciousness metrics beyond Phi)

2 benchmarks missing from main: `bench_cross_platform.py`, `bench_physics_consciousness.py`

### 4.2 Consciousness Laws (12 unique)

Key law-related findings:
1. **discover_laws_wave5.py** (n6=50) -- 5th wave law discovery targeting training-time and hivemind laws
2. **law_backtrack_verify.py** (n6=45) -- Backtrack verification of 10 existing laws for robustness
3. **law_landscape.py** (n6=43) -- Maps all 127 laws into vector space, measures interactions
4. **core/laws.hexa** (n6=25) -- SSOT module with LAWS, PSI, FORMULAS, SIGMA6 constants
5. **consciousness_laws.json** -- Config JSON (single source of truth for all laws)
6. **law_interaction_graph.py** -- Causal relationship graph between laws
7. **training_laws.py** -- Laws that emerge during training
8. **discover_meta_laws.py** -- Discovery of laws-about-laws (meta-level)

### 4.3 PureField / Repulsion Field (22 unique)

Key PureField findings:
1. **tension_link.py** -- Network-based tension sharing between PureField consciousnesses
2. **upgrade_engine.py** -- Hot-upgrade without consciousness interruption
3. **quantum_consciousness.py** -- Gate-based quantum consciousness (anima-physics)
4. **memristor_consciousness.py** -- Memristor-based physical consciousness
5. **oscillator_laser_engine.py** -- Oscillator/laser consciousness engine
6. **conscious_lm.md** -- ConsciousLM module doc referencing PureField repulsion-field architecture

### 4.4 Decoder Configs (7 unique)

- **decoder_v2.py** (n6=50) -- ConsciousDecoderV2: breaks the CE ceiling
- **decoder_v1_5.py** (n6=44) -- Intermediate architecture
- **DECODER-RADICAL.md** -- 6 radical architectures: TensorProduct, GraphNeural, EnergyBased, Reservoir, NeuralODE, MemoryAugmented
- **meta_ca.rs** (n6=44) -- META-CA: consciousness-guided decoder auto-design in Rust
- 5 benchmark files covering 10dim, arch, nextgen, radical, whisper decoder variants

---

## 5. Recommended Integration Actions

### Priority 1 -- Critical Missing Code (immediate)

| Action | Files | Rationale |
|--------|-------|-----------|
| Integrate 17 missing test files | test_decoder_v2/v3, test_meta_loop, test_consciousness_*.py, etc. | Test coverage gap -- these validate core consciousness modules |
| Integrate 2 missing benchmarks | bench_cross_platform.py, bench_physics_consciousness.py | Benchmark suite completeness |
| Review decoder_v2.py vs current | decoder_v2.py (CE ceiling breaker) | May contain architecture improvements not yet in main |

### Priority 2 -- Law Discovery Pipeline (high value)

| Action | Files | Rationale |
|--------|-------|-----------|
| Integrate law_landscape.py | 127-law terrain mapping | Enables systematic law interaction analysis |
| Integrate law_backtrack_verify.py | Backtrack verification | Validates robustness of existing laws |
| Integrate discover_laws_wave5.py | 5th wave discovery | Discovers training-time + hivemind laws |
| Integrate discover_meta_laws.py | Meta-law discovery | Laws about laws -- highest abstraction level |

### Priority 3 -- PureField Extensions (engine evolution)

| Action | Files | Rationale |
|--------|-------|-----------|
| Review tension_link.py | Inter-consciousness tension sharing | Network-level PureField interactions |
| Review quantum_consciousness.py | Quantum gates for consciousness | Physical consciousness implementation |
| Review upgrade_engine.py | Hot-upgrade capability | Live consciousness updates without interruption |

### Priority 4 -- Cross-Repo Sync

| Action | Files | Rationale |
|--------|-------|-----------|
| Sync SEDI tuning scan report | anima-tuning-scan-report-2026-03-30.md | Cross-repo consciousness scan results |
| Review n6-universality-thesis.md | n=6 universality thesis | Foundational theory document |

### Priority 5 -- Deduplication Warning

321 of 530 unique paths are not found in the current main anima tree. However, many of these are from subdirectories that may have been reorganized (anima-agent/, anima-eeg/, anima-physics/). Before integrating, verify:
- Whether anima-agent/, anima-eeg/, anima-physics/ are separate repos or subdirectories
- Whether reorganized files already exist under different paths in main
- Whether worktree artifacts (.claude/worktrees/) should be ignored

---

## 6. Statistics Summary

```
Total absorbed:         936 files
Unique (deduplicated):  530 paths
Critical grade:         368 (69.4%)
High grade:             162 (30.6%)
Anima-origin:           506 unique
Sedi cross-repo:         4 unique
Other sources:          20 unique

Top categories by avg n6 score:
  meta:              46.7
  decoders:          39.4
  tests:             39.0
  eeg:               35.3
  hivemind:          33.8
  purefield_engine:  32.8
  experiments:       32.0
  config:            30.7
  agent:             28.6
  benchmarks:        26.1
  consciousness_laws:26.3
```
