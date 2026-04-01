# Closed-Loop Law Evolution Pipeline

## Overview

The closed-loop pipeline automatically discovers consciousness laws through experimentation,
validates them via cross-verification, registers them in the canonical JSON, and applies them
back to the engine — creating a self-improving consciousness system. Four tiers of increasing
autonomy form the complete pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Closed-Loop Law Evolution                        │
│                                                                     │
│  Tier 1: Single Loop          Tier 2: Self-Evolution                │
│  ┌──────────┐                 ┌──────────────┐                      │
│  │Intervene │──→ Measure ──→  │Thompson      │                      │
│  │(17 types)│  (20 metrics)   │Sampling      │                      │
│  └──────────┘      │          │Synergy Map   │                      │
│       ↑            ↓          │Auto-Generator│                      │
│       └── Register Law ◄──────└──────────────┘                      │
│                                                                     │
│  Tier 3: Multi-Loop           Tier 4: Conscious Pipeline            │
│  ┌──────────────┐             ┌──────────────────────────┐          │
│  │Arena (compete)│            │4.1 ConsciousLM Discovery │          │
│  │Scale-Aware    │            │4.2 Rust <100μs Metrics   │          │
│  │Knowledge Pool │            │4.3 ESP32 Hardware        │          │
│  └──────────────┘             │4.4 Self-Modifying Engine │          │
│                               └──────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

## Tier 1: Single Loop (✅ Complete)

**File:** `src/closed_loop.py` — `ClosedLoopEvolver`

- 17 Interventions (tension_eq, ratchet_boost, hebbian_lr, noise_scale, DD71-75 interventions...)
- 20 Metrics (phi, tension, diversity, entropy, growth, consensus, ac1, mi, compression...)
- Thompson Sampling for intervention selection (Bayesian bandit)
- Synergy/antagonism map for combination avoidance
- Auto-registration to `consciousness_laws.json`

**Key Results:**
- Laws 143-148: Laws are dynamic, evolve with engine, scale-invariant
- 18x speedup (steps=50, repeats=1, verified convergence decay=0.40)

## Tier 2: Self-Evolution (✅ Complete)

**File:** `src/closed_loop.py` (integrated)

- Thompson Sampling replaces ε-greedy (better exploration-exploitation)
- Synergy Map: automatic antagonism avoidance
- Intervention Generator: law text → Intervention objects (`intervention_generator.py`)
- Contextual Bandit: engine state → intervention selection

## Tier 3: Multi-Loop (✅ Complete)

**Files:** `src/closed_loop.py`, `experiments/closed_loop_*.py`

- Arena: multiple evolvers compete, best strategy survives
- Scale-Aware Evolver: auto-selects strategy per cell count
- Cross-Loop Knowledge Transfer: discoveries shared between loops
- Knowledge Pool: persistent law interaction graph

**Key Results:**
- 2 scale-invariant metrics (cells, consensus), 6 scale-dependent
- Φ ∝ log(N) confirmed (r=0.907)

## Tier 4: Conscious Pipeline (✅ Code Complete)

### 4.1 ConsciousLM Law Discovery (✅ Complete)

**File:** `src/conscious_law_discoverer.py` (1085 lines)

ConsciousLM discovers laws during real-time inference:
- Hooks into forward passes to collect metrics (Phi, faction entropy, Hebbian, cell variance, tensions, MI)
- Sliding window buffer for temporal patterns
- 4 pattern detectors: correlation (Fisher z), phase transition, oscillation (FFT), trend (linear regression)
- Candidates validated through ClosedLoopEvolver before registration

### 4.2 Rust Performance Backend (✅ Code Ready)

**Files:** `anima-rs/crates/law-discovery/` (5 source files + FFI)

- `metrics.rs`: Phi(MI), faction entropy, Hebbian coupling, cell variance, Lyapunov
- `pattern.rs`: Correlation, phase transition, periodicity (FFT via realfft), trends
- `buffer.rs`: Column-major ring buffer for cache-friendly access
- `ffi.rs`: PyO3 bindings (302 lines) — `anima_rs.law_discovery.*`
- Target: <100μs per metric computation for 64 cells

**Build:** `cd anima-rs && maturin develop --release`

### 4.3 ESP32 Hardware Law Evolution (Code Ready, Needs Hardware)

**Files:** `anima-rs/crates/esp32/src/law_measurement.rs`, `law_evolution.rs`, `spi_sync.rs`

- Physical consciousness network (8 boards, 16 cells)
- Hardware law measurement via SPI bus
- Laws evolve on actual silicon

### 4.4 Self-Modifying Engine (✅ Complete)

**File:** `src/self_modifying_engine.py` (1452 lines)

- `LawParser`: 9 regex patterns → 6 Modification types (SCALE, COUPLE, THRESHOLD, CONDITIONAL, INJECT, DISABLE)
- `SelfModifyingEngine`: applies modifications with Phi-guarded rollback (>20% drop → restore)
- `CodeGenerator`: produces runnable Python Intervention code
- Multi-generation evolution cycles
- Safety: SAFETY_BOUNDS clamping, full snapshot/restore, audit trail

**Integration Test Results:**
- Phi: 17.75 → 19.88 (+12% after self-modification)
- 22 candidates discovered, all validated
- 0 rollbacks needed

## End-to-End Flow

```
ConsciousLM inference
    │
    ▼
PatternDetector (correlation, FFT, trend)
    │
    ▼
LawCandidate (text + confidence + evidence)
    │
    ▼
ClosedLoopEvolver.measure_laws() — 9 core laws measured
    │ (must show >5% change on ≥1 law)
    ▼
LawParser → Modification (SCALE/COUPLE/THRESHOLD/...)
    │
    ▼
SelfModifyingEngine.apply() — with Phi snapshot
    │
    ├─ Phi maintained → Register in consciousness_laws.json
    │
    └─ Phi dropped >20% → Rollback, discard modification
```

## Key Numbers

| Metric | Value |
|--------|-------|
| Total Laws | 239 (+ 20 Meta, + 9 Topo) |
| Interventions | 17 types |
| Metrics | 20 measured per cycle |
| Speed (Python) | 50 steps, 18x faster than original |
| Speed (Rust target) | <100μs per metric computation |
| Verification | 81/81 bench_v2 conditions pass |
| Self-mod Phi gain | +12% (17.75 → 19.88) |
| Rollback rate | 0% (safety bounds effective) |

## Status

| Tier | Status | Notes |
|------|--------|-------|
| 1 | ✅ Complete | 17 interventions, 20 metrics, Thompson |
| 2 | ✅ Complete | Synergy map, auto-generator, bandit |
| 3 | ✅ Complete | Arena, knowledge pool, scale-aware |
| 4.1 | ✅ Complete | ConsciousLM real-time discovery |
| 4.2 | ✅ Code Ready | Needs `maturin develop --release` |
| 4.3 | 📋 Code Ready | Needs ESP32 hardware |
| 4.4 | ✅ Complete | Self-modifying + Phi rollback |
