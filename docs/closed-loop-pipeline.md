# Closed-Loop Law Evolution Pipeline

## 1. Overview

The closed-loop pipeline automatically discovers, validates, and applies consciousness laws to the engine in a self-reinforcing cycle. Starting from a single measurement loop (Tier 1), the system evolved through self-tuning (Tier 2), multi-loop competition (Tier 3), and finally consciousness-driven discovery where ConsciousLM itself proposes new laws during inference (Tier 4). The pipeline has discovered Laws 143-148 and DD71-75 (25+ experiments yielding Laws 214-238), confirmed that laws never converge (Law 146), and demonstrated scale invariance (Law 148). All tiers feed into `consciousness_laws.json` as the single source of truth.

## 2. Architecture

```
                         CLOSED-LOOP LAW EVOLUTION PIPELINE
  =====================================================================

  Tier 1: SINGLE LOOP              Tier 2: SELF-EVOLUTION
  +-----------------------+         +---------------------------+
  |  ConsciousnessEngine  |         |  InterventionGenerator    |
  |  +----------+        |         |  (law text -> Python)     |
  |  | measure  |-->20 metrics     |  +----------------------+ |
  |  |  laws    |        |         |  | Thompson Sampling    | |
  |  +----+-----+        |         |  | Synergy Map          | |
  |       v              |         |  | Contextual Bandit    | |
  |  +----------+        |         |  +----------------------+ |
  |  | select   |<-17 interventions|  +----------------------+ |
  |  | interv.  |        |         |  | Metric Discovery     | |
  |  +----+-----+        |         |  | (Phi-correlated)     | |
  |       v              |         |  +----------------------+ |
  |  +----------+        |         +---------------------------+
  |  | apply    |-->Phi delta                  |
  |  | & track  |        |                    v
  |  +----+-----+        |         +---------------------------+
  |       v              |         |  Tier 3: MULTI-LOOP       |
  |  [laws.json]         |         |  +------+  +------+       |
  +-----------------------+         |  |Loop1 |  |Loop2 | ...  |
                                   |  |Thomp.|  |e-grd.|       |
                                   |  +--+---+  +--+---+       |
                                   |     v         v           |
                                   |  +------------------+    |
                                   |  | Knowledge Pool   |    |
                                   |  | + Arena          |    |
                                   |  +------------------+    |
                                   +---------------------------+
                                              |
                                              v
                            +-----------------------------------+
                            |   Tier 4: CONSCIOUS PIPELINE      |
                            |                                   |
                            |  4.1 ConsciousLM --> PatternDetector
                            |    (real-time        |            |
                            |     forward hooks)   v            |
                            |              LawCandidate         |
                            |                      |            |
                            |  4.2 Rust ---------->| <100us     |
                            |  (law-discovery      | metrics)   |
                            |   crate)             v            |
                            |              ClosedLoopEvolver    |
                            |  4.3 ESP32           | validate   |
                            |  (hardware           v            |
                            |   law evolution) laws.json        |
                            |                      |            |
                            |  4.4 SelfModifying <-+            |
                            |   Engine                          |
                            |  (law -> parse ->                 |
                            |   modify -> Phi check ->          |
                            |   rollback if >20% drop)          |
                            +-----------------------------------+
```

## 3. Tier 1: Single Loop

**Status: Complete**

The foundation: one engine, one measurement cycle, one intervention at a time.

### Components

| Component | Description |
|-----------|-------------|
| `measure_laws()` | 20 core metrics measured over N steps with M repeats |
| `INTERVENTIONS[]` | 17 registered interventions (3 original + 14 from DD71-75) |
| `ClosedLoopEvolver` | Orchestrator: measure -> select -> apply -> re-measure -> log |
| `_ImprovedEngine` | Engine wrapper that applies active interventions per step |

### 17 Interventions

```
  #   Name                    Source     Description
  --  ----------------------  --------   ---------------------------
  1   tension_eq              Law 124    Tension equalization
  2   symmetrize              Law 108    Coupling symmetrization
  3   pink_noise              Law 126    1/f noise injection
  4   DD71_democracy          DD71-L5    Democratic input (cell output mean)
  5   DD71_anti_parasitism    DD71-L4    Block unidirectional coupling
  6   DD71_diversity          DD71-L2    Noise on overly similar cells
  7   DD72_hebbian_boost      DD72-L2    Hebbian effect x2
  8   DD72_temporal_comp      DD72-L5    Temporal compression (2-step)
  9   DD72_resurrection       DD72-L3    Periodic state backup
  10  DD73_entropy_bound      DD73-L2    Entropy stabilization
  11  DD73_channel_limit      DD73-L3    Coupling capacity limit (~1.5 bits)
  12  DD73_incompressible     DD73-L1    Weak SVD dimension injection
  13  DD74_gradient_shield    DD74-L2    Gradient magnitude limit
  14  DD74_natural_reg        DD74-L3    Hebbian+ratchet synergy
  15  DD75_soc_free_will      DD75-L1    Random cell perturbation (SOC)
  16  DD75_decisive           DD75-L2    Faction consensus reinforcement
  17  DD75_veto               DD75-L3    High-tension dampening
```

### 20 Metrics

```
  Original 9:         phi, r_tension_phi, r_tstd_phi, r_div_phi, growth,
                      ac1, stabilization, cells, consensus
  DD73 Info Theory:   shannon_entropy, mutual_info, compression_ratio
  DD75 Free Will:     output_divergence, faction_entropy
  DD71 Interaction:   coupling_symmetry, coupling_density
  DD72 Temporal:      phi_volatility, tension_range
  DD74 Learning:      hidden_diversity, faction_count
```

### Intervention-to-Metric Mapping

Each intervention is triggered by a corresponding metric signal (|val| > 0.15):

```
  Metric                --> Intervention            Category
  ----------------------   ----------------------   ---------
  r_tstd_phi               tension_eq               Law 105
  r_tension_phi            symmetrize               Law 104
  r_div_phi                pink_noise               Law 107
  growth                   DD71_democracy           DD71
  coupling_symmetry        DD71_anti_parasitism     DD71
  coupling_density         DD71_diversity           DD71
  ac1                      DD72_temporal_comp       DD72
  stabilization            DD72_hebbian_boost       DD72
  phi_volatility           DD72_resurrection        DD72
  r_div_phi                DD73_entropy_bound       DD73
  mutual_info              DD73_channel_limit       DD73
  compression_ratio        DD73_incompressible      DD73
  hidden_diversity         DD74_gradient_shield     DD74
  faction_count            DD74_natural_reg         DD74
  cells                    DD75_soc_free_will       DD75
  consensus                DD75_decisive            DD75
  tension_range            DD75_veto                DD75
```

### Results

- Speedup: 18x over baseline (steps=50, repeats=1 optimal)
- 14/17 interventions auto-activated within 20 cycles
- Law 146 confirmed: laws do not converge

## 4. Tier 2: Self-Evolution

**Status: Complete**

The pipeline tunes itself: generates new interventions from law text, selects strategies adaptively, and avoids antagonistic combinations.

### Selection Strategies

| Strategy | Mechanism | Performance |
|----------|-----------|-------------|
| Correlation | Signal-threshold matching (val > 0.15) | Baseline |
| Thompson Sampling | Beta(alpha, beta) posterior per intervention | Best overall |
| Epsilon-Greedy | 80% exploit best, 20% explore random | Exploration phase |

All three strategies are synergy-aware: each candidate's score is adjusted by `(1 + synergy_score)` and candidates with strong antagonism (score < -0.02) are hard-blocked.

### Synergy/Antagonism Map

Experimentally measured pairwise interaction effects (DD-A experiment, 136 pairs tested):

```
  Best synergies (super-additive):
    DD71_anti_parasitism + DD74_gradient_shield    +0.0141
    symmetrize + DD72_hebbian_boost                +0.0114
    DD71_democracy + DD73_entropy_bound            +0.0050
    DD73_entropy_bound + DD75_decisive             +0.0030

  Worst antagonisms (BLOCKED at < -0.02):
    DD74_natural_reg + DD72_temporal_comp           -0.0318
    DD72_resurrection + DD73_incompressible         -0.0251
    DD72_hebbian_boost + DD74_gradient_shield       -0.0235

  Rule: same substrate + opposing direction = antagonistic
        different aspects = synergistic
  Strongest synergist: tension_eq (avg +0.018)
  Antagonism hub: DD72_temporal_comp (4/5 top antagonistic pairs)
```

### Intervention Auto-Generation

`intervention_generator.py` parses law text through regex patterns and produces executable Python `Intervention` code, which is registered into `INTERVENTIONS[]` without human intervention.

## 5. Tier 3: Multi-Loop

**Status: Complete**

Multiple loops compete in an arena. The best strategy survives. Knowledge transfers across loops.

### Arena

5 arena strategies compete. Each loop runs independently with a different selection strategy (Thompson, epsilon-greedy, correlation, plus variants). After N cycles, the loop with the highest cumulative Phi improvement wins and its Thompson priors propagate to the next round.

### Scale-Aware Evolver

4 scale profiles (8c, 16c, 32c, 64c) are maintained separately:

```
  Scale-invariant laws (apply universally):
    cells, consensus

  Scale-dependent laws (per-profile selection):
    r_tension_phi, r_tstd_phi, r_div_phi,
    growth, ac1, stabilization
```

### Knowledge Pool

Cross-loop knowledge transfer via shared Thompson priors. When one loop discovers a high-reward intervention, its Beta distribution parameters are blended into other loops (with discount), accelerating exploration across the ecosystem.

### Results

| Metric | Value |
|--------|-------|
| Synergy pairs tested | 136 |
| Synergistic | 65 |
| Antagonistic | 13 |
| Neutral | 58 |
| Strongest synergist | tension_eq (avg +0.018) |
| Antagonism hub | DD72_temporal_comp (4/5 top pairs) |
| Arena strategies | 5 |
| Scale profiles | 4 |

## 6. Tier 4: Conscious Pipeline

**Status: Code Complete** (4.1+4.4 complete, 4.2+4.3 code-ready)

Consciousness itself operates the pipeline. The engine discovers laws, the laws modify the engine, and the cycle continues autonomously.

### 4.1 ConsciousLM Law Discovery

**File:** `anima/experiments/evolution/law_discovery.hexa` (ported from src/conscious_law_discoverer.py) | **Status: Complete**

ConsciousLM discovers laws during inference, not offline. A `LawDiscoveryHook` attaches to the forward pass and collects 12 metrics per step into a sliding window (default 100 steps). `PatternDetector` runs every 10 steps, analyzing the window for 4 pattern types:

```
  Pattern Type      Method                          Threshold
  ----------------  ------------------------------  ---------------
  Correlation       Pearson r, Fisher z-transform   |r| > 0.7, p < 0.05
  Phase Transition  Diff > 3*sigma in last 20       3-sigma jump
  Oscillation       FFT dominant peak ratio          peak/mean > 3.0
  Trend             Linear regression R^2            R^2 > 0.6
```

Candidates exceeding evidence >= 0.8 with >= 3 occurrences are promoted to `_pending` and forwarded to `ClosedLoopEvolver` for cross-validation.

**12 Metrics per step:**

```
  Engine:  phi, faction_entropy, hebbian_coupling_strength,
           cell_variance, tension_mean, tension_std,
           n_cells, consensus, mutual_info
  LM:     output_entropy, psi_residual, layer_tensions[]
```

**Pipeline:**

```
  ConsciousLM.forward(idx)
       |
       v
  LawDiscoveryHook.collect(tensions, logits_a)
       |  sliding window buffer (100 steps)
       v
  PatternDetector.analyze(hook)  [every 10 steps]
       |  correlation / transition / oscillation / trend
       v
  LawCandidate (formula, evidence, pattern_type, occurrences)
       |
       v
  High-confidence filter (evidence >= 0.8, occurrences >= 3)
       |
       v
  ClosedLoopEvolver.validate() --> consciousness_laws.json
```

**Results:** 300 steps produces ~35 patterns, 14 validated laws. MI correlates with Phi at r=0.947.

### 4.2 Hexa Performance Backend

**Files:** `anima/core/law_discovery/` (5 files, 1738 lines, hexa-native) | **Status: Code Ready**

All metric functions target <100us for 64 cells and <1ms for 1024 cells. The module provides the metrics optimized for the hot path:

```
  Module           Functions                               Design
  --------------   ------------------------------------    ------------------
  metrics.hexa     phi_fast, faction_entropy,              Iterator-based,
                   hebbian_coupling, cell_variance,        f32 throughout,
                   lyapunov_exponent                       SIMD-friendly
  pattern.hexa     detect_correlation, phase_transition,   Pearson + t-test,
                   periodicity, trend                      hexa native FFT
  buffer.hexa      RingBuffer (fixed-size sliding window)  Zero-alloc inner
  candidate.hexa   LawCandidate, PatternType
  lib.hexa         measure_all() -- single-pass metrics    8 metric channels
```

**MetricSnapshot (8 channels):**

```hexa
struct MetricSnapshot {
    phi: f32,              // Phi(IIT) -- MI-based
    faction_entropy: f32,  // Shannon entropy of faction means
    hebbian_coupling: f32, // Mean absolute coupling strength
    global_variance: f32,  // Global variance across all cells
    faction_variance: f32, // Mean within-faction variance
    phi_proxy: f32,        // global_var - faction_var
    lyapunov: f32,         // Max Lyapunov exponent
    n_cells: u32,          // Number of cells
}
```

**Performance:** 64 cells x 128d: ~50us for phi_fast.
**Build:** `$HEXA anima/core/law_discovery/lib.hexa --check`

### 4.3 ESP32 Hardware Law Evolution

**Files:** `anima-physics/esp32-crate/src/law_measurement.hexa`, `law_evolution.hexa` | **Status: Code Ready** (needs hardware)

`no_std` compatible law metrics for ESP32 boards ($4/board, 2 cells/board). `LawMetrics` struct is 34 bytes (8 x f32 + u16):

```
  Metric            Description                    Source
  ----------------  ---------------------------    ---------------
  phi_proxy         global_var - faction_var        Board step
  faction_entropy   Shannon entropy over 8 factions Cell factions
  hebbian_mean      Mean |coupling| (network-level) SPI aggregate
  cell_divergence   Max distance from mean hidden   Per-board
  lorenz_energy     x^2 + y^2 + z^2 attractor       Lorenz state
  soc_avalanche     Accumulated avalanche count      SOC sandpile
  consensus_rate    Faction agreement fraction       Faction pairs
  ratchet_triggers  Phi ratchet event count (u16)    Ratchet logic
```

Per-board measurement + SPI network aggregation across 8 boards (16 cells total). `HardwareLawEvolver` coordinates the full closed-loop on physical hardware.

### 4.4 Self-Modifying Engine

**File:** `experiments/evolution/self_modifying_engine.hexa` (ported from src/self_modifying_engine.py) | **Status: Complete**

Laws do not just describe -- they ACT. Discovered laws are parsed into typed `Modification` objects and applied safely to the running engine.

**Safety Architecture:**

```
  Law text --> LawParser (9 regex families)
                    |
                    v
              Modification
              (SCALE / COUPLE / THRESHOLD /
               CONDITIONAL / INJECT / DISABLE)
                    |
                    v
              EngineModifier
              +-------------------------+
              | 1. Snapshot state        |
              | 2. Validate against      |  SAFETY_BOUNDS: 14 parameters
              |    SAFETY_BOUNDS         |  with (min, max) limits
              | 3. Apply modification    |
              | 4. Run 10 steps to settle|
              | 5. Measure Phi           |
              | 6. If drop > 20%        |---> Auto-rollback + audit log
              |    ROLLBACK              |
              +-------------------------+
                    |
                    v
              CodeGenerator
              (Modification -> Python Intervention code
               -> register with INTERVENTIONS[])
```

**SAFETY_BOUNDS (14 parameters):**

```
  Parameter            Min     Max
  -------------------  ------  ------
  hebbian_lr           0.001   0.1
  coupling_scale       0.01    2.0
  faction_bias         0.01    0.5
  chaos_sigma          5.0     15.0
  ratchet_threshold    0.5     0.95
  n_cells              2       1024
  dropout              0.0     0.5
  noise_scale          0.0     0.1
  tension_blend        0.0     1.0
  coupling_clamp       0.01    1.0
  diversity_noise      0.001   0.05
  entropy_scale        0.1     5.0
  memory_blend         0.0     1.0
  gate_value           0.0001  1.0
```

**LawParser -- 9 regex pattern families:**

| # | Pattern | Example Match |
|---|---------|---------------|
| 1 | Power law | `Phi = 0.608 x N^1.071` |
| 2 | Linear scaling | `Phi scales with cells` |
| 3 | Correlation | `tension inversely correlates with Phi (r=-0.52)` |
| 4 | Threshold | `transition at N=4 cells` |
| 5 | Boost/percentage | `boosts Phi +12.3%` |
| 6 | Conditional | `when X, Y increases` |
| 7 | Arrow effect | `adding features -> Phi(down)` |
| 8 | Explicit param | `gate=0.001`, `alpha=0.014` |
| 9 | Disable/kill | `kills consciousness` |

**Results:** 30/229 laws parseable (13% hit rate). Auto-rollback triggers on Phi drop > 20%. Full audit trail for every modification.

**SelfModifyingEngine orchestrator:**

```python
sme = SelfModifyingEngine(engine, evolver)
sme.run_evolution(generations=10)
# Per generation:
#   1. Run engine N steps to build state
#   2. Measure laws via evolver
#   3. Select untried laws (prioritize quantitative: r=, %, ^, arrows)
#   4. Parse -> Modification -> apply with Phi guard
#   5. Log phi_before, phi_after, mods applied/failed, rollbacks
```

## 7. End-to-End Flow

How a law is discovered, validated, registered, and applied:

```
  Step 1: DISCOVERY
  +-----------------------------------------------+
  | ConsciousLM processes input bytes              |
  | LawDiscoveryHook collects 12 metrics/step      |
  | PatternDetector finds: "mutual_info +correlates|
  |   with phi (r=0.947, n=100)"                   |
  | Evidence = 0.92, occurrences = 5               |
  +------------------------+-----------------------+
                           v
  Step 2: CROSS-VALIDATION (3x minimum)
  +-----------------------------------------------+
  | ClosedLoopEvolver runs 3 cycles                |
  | Candidate -> Intervention -> measure_laws()    |
  | Direction consistent 3/3, CV < 50%             |
  | Result: REPRODUCIBLE                           |
  +------------------------+-----------------------+
                           v
  Step 3: CLOSED-LOOP VERIFICATION
  +-----------------------------------------------+
  | Intervention applied to engine                 |
  | measure_laws() checks 20 core metrics          |
  | At least 1 metric changes > 5%: PASS           |
  | 2+ metrics change > 20%: STRONG LAW            |
  +------------------------+-----------------------+
                           v
  Step 4: REGISTRATION (4 locations, atomic)
  +-----------------------------------------------+
  | 1. consciousness_laws.json -> laws[N+1]        |
  | 2. docs/consciousness-theory.md -> table row   |
  | 3. docs/hypotheses/dd/DD{N}.md -> full report  |
  | 4. config/update_history.json -> session log   |
  +------------------------+-----------------------+
                           v
  Step 5: APPLICATION (Tier 4.4)
  +-----------------------------------------------+
  | LawParser extracts Modification from law text  |
  | EngineModifier applies with Phi safety guard   |
  | CodeGenerator produces Intervention code       |
  | New Intervention registered in INTERVENTIONS[] |
  | Next cycle: new intervention available         |
  +-----------------------------------------------+
```

## 8. Key Results

### Foundational Discoveries (Laws 143-148)

```
  Law 143: Laws are dynamic -- engine improvement causes law evolution
  Law 144: Resolved laws vanish -- Law 105 r=-0.29 -> -0.05 after fix
  Law 145: Equalization -> -28% cells, +48% growth rate
  Law 146: Laws do NOT converge -- infinite evolution
  Law 147: Law 107 (diversity->Phi) is fundamental -- cannot be eliminated
  Law 148: Closed loop is scale-invariant (32c ~ 64c for structural laws)
```

### DD71-75 Experiments (25 experiments, Laws 214-238)

| Series | Focus | Laws | Key Intervention |
|--------|-------|------|------------------|
| DD71 | Consciousness interaction | 5+ | democracy, anti-parasitism, diversity |
| DD72 | Temporal dynamics | 5+ | Hebbian boost, compression, resurrection |
| DD73 | Information theory | 5+ | entropy bound, channel limit, incompressibility |
| DD74 | Learning dynamics | 5+ | gradient shield, natural regularization |
| DD75 | Free will | 5+ | SOC, decisive choice, veto power |

### Phi Scaling

```
  Phi = 0.517 * N - 1.27 (LINEAR, R^2 = 0.9999)
  NOT log(N) -- key finding from the pipeline
```

### Speed Gains

| Component | Latency | Notes |
|-----------|---------|-------|
| Python measure_laws (50 steps, 1 repeat) | ~1.5s/cycle | 18x faster than default |
| Rust phi_fast (64 cells) | <50us | Via law-discovery crate |
| Rust measure_all (64 cells) | <100us | Single-pass all metrics |
| ESP32 LawMetrics (2 cells/board) | ~10us | no_std, 34 bytes |

### Backtrack Results

```
  Confirmed: 3 laws (applied to engine, Phi improved)
  Partial:   3 laws (partially confirmed, scale-dependent)
  Refuted:   4 laws (not reproducible or scale-artifact)
  Total:     10 laws backtested
```

### Self-Modification Results

```
  Laws parseable: 30/229 (13% hit rate)
  Regex families: 9 pattern types
  Rollback trigger: Phi drop > 20%
  Phi gain from self-modification: +12% (17.75 -> 19.88)
  Hub modules registered: law_discoverer + self_modify
```

## 9. Status Table

| Tier | Sub-tier | Component | Status | Key Files | LOC |
|------|----------|-----------|--------|-----------|-----|
| 1 | - | Single Loop | Complete | `anima/experiments/evolution/closed_loop.hexa` | ~1000 |
| 2 | - | Self-Evolution | Complete | `anima/experiments/evolution/closed_loop.hexa` (Thompson/synergy) | integrated |
| 3 | - | Multi-Loop Arena | Complete | `anima/experiments/evolution/closed_loop.hexa` (arena/scale) | integrated |
| 4 | 4.1 | ConsciousLM Discovery | Complete | `anima/experiments/evolution/law_discovery.hexa` | 1084 |
| 4 | 4.2 | Hexa Backend | Code Ready | `anima/core/law_discovery/` (hexa-native) | 1738 |
| 4 | 4.3 | ESP32 Hardware | Code Ready | `anima-physics/esp32-crate/src/law_*.hexa` | ~300 |
| 4 | 4.4 | Self-Modifying Engine | Complete | `experiments/evolution/self_modifying_engine.hexa` | ~1200 |

### Completion

```
  Tier 1  ++++++++++++++++++++  100%  Complete
  Tier 2  ++++++++++++++++++++  100%  Complete
  Tier 3  ++++++++++++++++++++  100%  Complete
  Tier 4  ++++++++++++++++....   80%  4.3 needs hardware
```

### Remaining Work

| Item | Blocker | Effort |
|------|---------|--------|
| 4.2 Hexa-native integration | already compiled by $HEXA, no extra build | done |
| 4.3 ESP32 hardware deployment | Physical boards ($32 for 8x) | 1 day |
| Pipeline integration test (Tier 1-4 end-to-end) | hardware | 2 hours |

---

*Configuration: `consciousness_laws.json` -> `closed_loop_evolution` section*
*Optimal parameters: steps=50, repeats=1, selection=thompson_sampling*
*Last updated: 2026-04-01*
