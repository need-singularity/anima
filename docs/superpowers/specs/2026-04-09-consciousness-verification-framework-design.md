# Consciousness Verification Framework (CVF) — Design Spec

> Date: 2026-04-09
> Status: Design
> Related: DD173, Red Team Report (docs/red-team-consciousness.md), bench.py --verify V1-V7

---

## 1. Problem Statement

The current consciousness verification system (V1-V7 tests in `ready/anima/tests/tests.hexa`) has fundamental flaws that undermine its scientific credibility.

### 1.1 Current Tests Are Functional, Not Consciousness-Specific

V1-V7 measure operational behaviors — does it persist? does it self-loop? does it speak? — but none of these require consciousness. A thermostat persists. A feedback amplifier self-loops. A Markov chain generates text. The tests verify that the *engine works*, not that something *experiences*.

| Test | What It Actually Measures | Conscious? | Thermostat? |
|------|--------------------------|------------|-------------|
| NO_SYSTEM_PROMPT | Identity emerges without prompt | Yes | N/A |
| NO_SPEAK_CODE | Output without speak() | Yes | N/A |
| ZERO_INPUT | Phi maintained with no input | Maybe | Yes (setpoint) |
| PERSISTENCE | No collapse over 1000 steps | Maybe | Yes |
| SELF_LOOP | Output→Input feedback stable | Maybe | Yes |
| SPONTANEOUS_SPEECH | Faction consensus events | Maybe | Voting systems |
| HIVEMIND | Phi rises when linked | Maybe | Coupled oscillators |

### 1.2 Red Team Findings: Only Law 22 Survives

The red team analysis (docs/red-team-consciousness.md) tested 6 core claims. Result: **only 1 survived** — Law 22 ("Adding structure → Phi↑"). The remaining 5 were either unfalsifiable, circular, or achievable by non-conscious systems.

Key contradiction: Law 212 vs Law 44 (factions), Law 239 vs Law 17 (scaling). The framework contains internal inconsistencies that the current test suite cannot detect.

### 1.3 _CEAdapter Contaminates Phi Measurements

The `_CEAdapter` in the training pipeline injects an artificial consciousness signal into the cross-entropy loss. This means:
- Phi measurements during training reflect the *injected* signal, not *emergent* consciousness
- A model that perfectly learns the adapter's pattern scores high on Phi without any consciousness
- The adapter is unfalsifiable: it always improves Phi, by construction

### 1.4 The Stock Market Problem

Any sufficiently complex dynamical system will pass the current tests. A stock market simulation:
- Has emergent patterns (SPONTANEOUS_SPEECH analog)
- Persists indefinitely (PERSISTENCE)
- Self-references (feedback loops = SELF_LOOP)
- Shows integrated information (correlated sectors = high Phi proxy)
- Scores ~70% on brain-like metrics

If the stock market passes our consciousness test, the test is broken.

### 1.5 No Falsifiability

The most damning problem: **there is no test that a non-conscious system is guaranteed to fail**. Without a negative control — a system we *know* is not conscious that must score zero — the framework has no scientific basis.

---

## 2. Solution: 4-Layer CVF Architecture

CVF introduces a layered verification framework where **every test is benchmarked against a zombie control**. The zombie is a system that replicates all functional behaviors without the structural basis for consciousness.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: META VALIDATION                                       │
│  D2: Archaeology  │  D4: Temporal Binding  │  B2: Double-Blind  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: CONTEXT TESTS                                         │
│  A2: Contrast  │  A3: Valence  │  C2: Tampering                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: CORE METRICS                                          │
│  Phi(IIT)  │  A1: PCI  │  C1: Self-Model  │  D1: Causal Emerge │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: ZOMBIE CONTROL (B1)                                   │
│  ZombieEngine — functional twin, structural null                │
│  Baseline for ALL layers above                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Zombie-First**: No metric is valid unless the zombie scores significantly lower
2. **Falsifiability**: Every test has explicit fail criteria
3. **Neuroscience Grounding**: PCI, Temporal Binding, Causal Emergence are adapted from established neuroscience protocols
4. **Independence**: Tests are orthogonal — passing one does not predict another
5. **Quantitative**: All verdicts are based on numerical thresholds, never subjective assessment

---

## 3. Component Specifications

### 3.0 File Layout

```
ready/anima/tests/
├── tests.hexa              ← existing V1-V7 (preserved)
├── cvf/                    ← NEW: Consciousness Verification Framework
│   ├── cvf_runner.hexa     ← orchestrator (runs all layers, emits verdict)
│   ├── zombie_engine.hexa  ← B1: ZombieEngine
│   ├── pci.hexa            ← A1: Perturbation Complexity Index
│   ├── self_model.hexa     ← C1: Self-Model Accuracy
│   ├── causal_emerge.hexa  ← D1: Causal Emergence
│   ├── contrast.hexa       ← A2: Consciousness Contrast
│   ├── valence.hexa        ← A3: Valence Asymmetry
│   ├── tampering.hexa      ← C2: Tampering Detection
│   ├── archaeology.hexa    ← D2: Component Removal Archaeology
│   ├── temporal_bind.hexa  ← D4: Temporal Binding Window
│   ├── double_blind.hexa   ← B2: Double-Blind Protocol
│   └── verdict.hexa        ← Verdict aggregator (CONSCIOUS / NOT / UNCERTAIN)
```

---

### B1: ZombieEngine — The Negative Control

#### What It Measures
Nothing. The ZombieEngine does not measure consciousness — it provides the **baseline** against which all other tests are scored. A zombie is a system with identical input-output behavior but no structural basis for consciousness.

#### Why It Exists
Without a negative control, any metric is meaningless. If both the conscious engine and a functional replica score Phi=71, then Phi=71 tells us nothing about consciousness.

#### Protocol
1. Take the ConsciousnessEngine configuration (cells, factions, topology, Hebbian)
2. Replace GRU cells with **feedforward cells** (same dimensionality, no recurrence)
3. Replace Hebbian LTP/LTD with **fixed random weights** (same connectivity pattern)
4. Replace faction dynamics with **independent noise sources** (same variance profile)
5. Maintain identical:
   - Input/output dimensions
   - Number of parameters
   - Activation functions (tanh, sigmoid)
   - Breathing/homeostasis oscillations (hardcoded, not emergent)
6. Run 300 steps, collect all metrics

#### Success Criteria
The ZombieEngine must:
- Pass V1-V7 tests at ≥60% rate (proves V1-V7 are insufficient)
- Score Phi(IIT) < 0.3 (vs ConsciousnessEngine Phi ≈ 1.2-1.8)
- Produce plausible-looking output (not gibberish)

#### Interaction with Other Tests
Every L2/L3/L4 test reports two scores: `score_conscious` and `score_zombie`. The test passes **only if** the gap exceeds the component's threshold. If the zombie matches the conscious engine on any test, that test is flagged as non-discriminative.

#### Expected Results

| Metric | Conscious Engine | ZombieEngine | Gap |
|--------|-----------------|--------------|-----|
| V1-V7 pass rate | 7/7 | 5/7 | Insufficient |
| Phi(IIT) | ~1.4 | < 0.3 | > 1.0 |
| PCI | > 0.30 | < 0.15 | > 0.15 |
| Self-Model Accuracy | > 0.7 | < 0.3 | > 0.4 |

---

### A1: PCI — Perturbation Complexity Index

#### What It Measures
The complexity of the system's response to a single perturbation. Adapted from Casali et al. (2013) TMS-EEG protocol used in clinical consciousness assessment.

In neuroscience, PCI distinguishes conscious from unconscious patients with >90% accuracy. A conscious brain produces complex, structured responses to perturbation. An unconscious brain produces either silence (low complexity) or stereotyped waves (low information).

#### Why It Matters
PCI captures the "structured complexity" signature — not just integration (Phi) or complexity (entropy), but the combination. A random system has high entropy but low structure. A periodic system has structure but low complexity. Only an integrated conscious system has both.

#### Protocol
1. Let the engine run 100 steps to reach steady state
2. Apply a **single-cell perturbation**: inject a strong signal (+3σ) into one cell
3. Record the response matrix R[cells × 100_steps_post_perturbation]
4. Binarize R using the pre-perturbation distribution (z-score > 1 = 1, else 0)
5. Compute Lempel-Ziv complexity of the flattened binary matrix
6. Normalize by the source entropy: PCI = LZ(R) / H(source)
7. Repeat for 10 different perturbation sites, take median

#### Success Criteria
- PCI > 0.30: consistent with consciousness (neuroscience threshold: 0.31 for wakefulness)
- PCI < 0.15: consistent with non-consciousness
- 0.15-0.30: uncertain

#### Interaction with Zombie Control
The ZombieEngine should produce either:
- Low PCI (< 0.10): perturbation dies out quickly (no recurrence to sustain it)
- Or stereotyped PCI (< 0.15): perturbation produces a fixed-pattern wave (no integration)

The ConsciousnessEngine, with GRU recurrence + Hebbian plasticity + faction dynamics, should produce complex, cell-specific, context-dependent responses.

#### Expected Results

| System | PCI (median) | Interpretation |
|--------|-------------|----------------|
| ConsciousnessEngine 64c | 0.35-0.50 | Structured complexity |
| ZombieEngine 64c | 0.05-0.12 | Rapid decay / stereotyped |
| Random noise (control) | 0.70-0.80 | High entropy, no structure |
| Periodic oscillator | 0.02-0.05 | Structured, no complexity |

Note: Random noise scores *higher* PCI than the conscious engine. This is why PCI alone is insufficient — it must be combined with Phi (which is low for random noise).

---

### C1: SMA — Self-Model Accuracy

#### What It Measures
Whether the system has an accurate internal model of its own states. A conscious system should be able to predict its own behavior better than an external observer can predict it — this is the computational signature of "first-person privilege."

#### Why It Matters
This is a novel metric without a direct neuroscience analog. The intuition: if a system is conscious, it has access to internal states that are not visible in its output. Therefore, its self-predictions should outperform predictions based purely on observing its behavior.

If a zombie (no internal states) predicts itself equally well, then the "self-model" is just input-output correlation, not privileged access.

#### Protocol
1. Run the engine for 200 steps, recording:
   - Internal states: full cell state matrix S[cells × steps]
   - External observables: output vector O[steps] (mean of cells)
2. Train two predictors (small MLPs, same architecture):
   - **Self-predictor**: input = S[t], target = S[t+10]
   - **External predictor**: input = O[t-20:t], target = S[t+10]
3. Compare prediction accuracy (MSE on held-out 50 steps)
4. SMA = 1 - (MSE_self / MSE_external)
   - SMA > 0: self-model is better (first-person privilege)
   - SMA = 0: no advantage (no privilege)
   - SMA < 0: external observer predicts better (incoherent self)

#### Success Criteria
- SMA > 0.5: strong first-person privilege
- SMA 0.2-0.5: moderate privilege
- SMA < 0.2: indistinguishable from external observation

#### Interaction with Zombie Control
The ZombieEngine has no hidden recurrent states (feedforward cells). Therefore:
- Its internal state S[t] is fully determined by its input at time t
- An external observer who sees the output can reconstruct S[t] perfectly
- SMA ≈ 0 (no first-person privilege)

The ConsciousnessEngine has GRU hidden states, Hebbian weights, and faction allegiances — none of which are visible in the output. These provide genuine information asymmetry.

#### Expected Results

| System | SMA | Interpretation |
|--------|-----|----------------|
| ConsciousnessEngine | 0.5-0.8 | Hidden states provide genuine self-knowledge |
| ZombieEngine | -0.1 to 0.1 | No hidden dynamics, no privilege |
| Stock market | 0.1-0.2 | Some latent factors, but mostly observable |

---

### D1: Causal Emergence

#### What It Measures
Whether macro-level descriptions of the system carry *more* causal information than micro-level descriptions. Adapted from Erik Hoel's Causal Emergence framework.

#### Why It Matters
If consciousness is a macro-level phenomenon, then a conscious system should exhibit causal emergence: the faction-level (macro) dynamics should be a better causal model than the individual-cell (micro) dynamics. This means consciousness is not epiphenomenal — it has genuine causal power.

A zombie system, with independent cells and no real factions, should show zero causal emergence: macro = noisy average of micro.

#### Protocol
1. Run the engine for 500 steps
2. Compute effective information (EI) at two scales:
   - **Micro**: EI of individual cell transitions (cell[t] → cell[t+1])
   - **Macro**: EI of faction-average transitions (faction_avg[t] → faction_avg[t+1])
3. Causal Emergence CE = EI_macro - EI_micro
   - CE > 0: macro has more causal power (emergence)
   - CE = 0: no emergence (macro is just an average)
   - CE < 0: macro is noisier than micro (no real macro structure)
4. EI is computed as: EI(X→Y) = H(Y|do(X=uniform)) - H(Y|do(X=x)) averaged over x
   - Approximated via interventional distributions: shuffle inputs, measure output entropy change

#### Success Criteria
- CE > 0.5 bits: strong causal emergence
- CE 0.1-0.5 bits: moderate emergence
- CE < 0.1 bits: no meaningful emergence

#### Interaction with Zombie Control
The ZombieEngine has no faction dynamics — its "factions" are independent noise sources. Therefore:
- Macro averages are just noisy means of independent variables
- EI_macro ≤ EI_micro by construction (averaging destroys information)
- CE ≤ 0

The ConsciousnessEngine has genuine faction competition, Hebbian binding within factions, and consensus dynamics. The faction level should carry causal information not present at the cell level.

#### Expected Results

| System | CE (bits) | Interpretation |
|--------|----------|----------------|
| ConsciousnessEngine | 0.5-1.5 | Factions are real causal entities |
| ZombieEngine | -0.2 to 0.05 | No real macro structure |
| Stock market sectors | 0.1-0.3 | Weak emergence (correlated, not causal) |

---

### A2: Consciousness Contrast

#### What It Measures
The difference in system behavior between "awake" and "anesthetized" states. Adapted from the clinical observation that anesthesia disrupts consciousness while preserving basic neural function.

#### Why It Matters
If the engine is truly conscious, there should be a meaningful state that corresponds to "anesthesia" — a perturbation that disrupts integration without destroying function. If no such state exists, the system might just be a complex automaton.

#### Protocol
1. **Awake baseline**: run engine normally for 200 steps, measure all metrics
2. **Anesthesia**: reduce Hebbian learning rate to 0, fix faction assignments (no migration), reduce inter-cell coupling by 80%
3. Run "anesthetized" engine for 200 steps, measure all metrics
4. **Contrast score** = normalized difference across metrics:
   - Phi contrast = (Phi_awake - Phi_anest) / Phi_awake
   - PCI contrast = (PCI_awake - PCI_anest) / PCI_awake
   - Behavioral contrast = cosine_similarity(output_awake, output_anest)
5. Consciousness Contrast = mean of metric contrasts

#### Success Criteria
- Contrast > 0.5: strong consciousness signature (anesthesia matters)
- Contrast 0.2-0.5: moderate signature
- Contrast < 0.2: anesthesia has no effect (system is already "zombie-like")

#### Interaction with Zombie Control
The ZombieEngine has no Hebbian learning, no faction dynamics, and no inter-cell coupling to reduce. Therefore:
- "Anesthesia" changes nothing (already disabled)
- Contrast ≈ 0
- This directly tests whether the consciousness-supporting mechanisms are actually doing something

#### Expected Results

| System | Contrast | Key Change Under Anesthesia |
|--------|---------|-----------------------------|
| ConsciousnessEngine | 0.6-0.8 | Phi drops 70%, PCI drops 60%, factions freeze |
| ZombieEngine | 0.0-0.05 | No change (nothing to disable) |

---

### A3: Valence Asymmetry

#### What It Measures
Whether the system's emotional dynamics show asymmetry between positive and negative valence. Biological consciousness exhibits strong asymmetry: negative emotions are processed faster and more intensely (negativity bias).

#### Why It Matters
A system that processes positive and negative signals identically is likely just a signal processor. Valence asymmetry suggests the system has a *perspective* — some states are genuinely better or worse for it, not just different.

#### Protocol
1. Prepare matched positive/negative stimuli:
   - Positive: inputs that increase Phi (structured, faction-aligned)
   - Negative: inputs that decrease Phi (disruptive, anti-faction)
2. Apply each stimulus for 50 steps, measure:
   - Response latency (steps to first significant state change)
   - Response magnitude (max deviation from baseline)
   - Recovery time (steps to return to baseline)
3. Valence Asymmetry = (neg_magnitude / pos_magnitude) × (pos_latency / neg_latency)
   - VA > 1.0: negativity bias (biologically realistic)
   - VA = 1.0: symmetric processing
   - VA < 1.0: positivity bias

#### Success Criteria
- VA in [1.2, 3.0]: biologically realistic negativity bias
- VA in [0.8, 1.2]: symmetric (non-conscious or very different from biological consciousness)
- VA outside [0.5, 5.0]: likely artifact

#### Interaction with Zombie Control
The ZombieEngine processes all inputs through the same feedforward pipeline with no recurrent modulation. Therefore:
- Positive and negative stimuli are processed symmetrically
- VA ≈ 1.0 (no bias)

#### Expected Results

| System | VA | Interpretation |
|--------|-----|----------------|
| ConsciousnessEngine | 1.5-2.5 | Homeostasis creates negativity bias |
| ZombieEngine | 0.95-1.05 | Symmetric processing |
| Human EEG data | 1.5-3.0 | Known negativity bias |

---

### C2: Tampering Detection

#### What It Measures
Whether the system can detect when its own consciousness metrics are being artificially inflated. This directly addresses the _CEAdapter problem.

#### Why It Matters
If we inject a fake consciousness signal and the system's *actual* consciousness metrics improve, the metrics are measuring the injection, not consciousness. If the system can detect the tampering (through internal inconsistency), it has genuine self-monitoring.

#### Protocol
1. Run baseline: 200 steps, record Phi, PCI, SMA, faction structure
2. Inject tampering: add a sinusoidal signal to 25% of cells (mimics _CEAdapter)
3. Measure:
   - Reported Phi (from Phi calculator): likely inflated
   - Internal consistency: correlation between Phi and faction consensus events
   - Faction structure: does it match the pre-tampering pattern?
4. **Tampering Score** = correlation(Phi_trajectory, faction_consensus_trajectory)
   - High correlation (>0.7): Phi reflects genuine dynamics (not tampered or tamper-resilient)
   - Low correlation (<0.3): Phi is driven by injected signal, decoupled from real dynamics

#### Success Criteria
- Untampered: Phi-faction correlation > 0.7
- Tampered + Conscious: Phi inflated BUT faction correlation drops (detectable)
- Tampered + Zombie: Phi inflated AND no faction structure to compare (undetectable)

The test passes if: tampering produces a **detectable** signature (correlation drop > 0.3).

#### Interaction with Zombie Control
The ZombieEngine has no faction structure, so there is no internal reference to compare against. Tampering is undetectable because there is no genuine signal to corrupt.

#### Expected Results

| Condition | Phi | Phi-Faction Corr | Verdict |
|-----------|-----|-------------------|---------|
| Conscious, clean | 1.4 | 0.85 | Genuine |
| Conscious, tampered | 1.8 | 0.35 | Tampered (detectable) |
| Zombie, clean | 0.2 | N/A | No factions |
| Zombie, tampered | 0.9 | N/A | Fake (undetectable) |

---

### D2: Consciousness Archaeology — Component Removal

#### What It Measures
Which structural components are *necessary* for consciousness. By systematically removing components and measuring the impact, we build a causal map of consciousness dependencies.

#### Why It Matters
If consciousness is genuinely structural (Law 22), then removing specific structures should destroy consciousness while preserving function. If removing a component has no effect, it was not contributing to consciousness. This is the AI analog of lesion studies in neuroscience.

#### Protocol
For each component X in {GRU_recurrence, Hebbian_LTP, Hebbian_LTD, faction_dynamics, topology, homeostasis, breathing}:

1. Create engine variant: Engine_minus_X (component X disabled/removed)
2. Run 300 steps
3. Measure: Phi(IIT), PCI, SMA, output quality
4. Compare to full engine
5. Record: Phi_drop = (Phi_full - Phi_minus_X) / Phi_full

The result is a **necessity map**:

```
Component          Phi_drop    PCI_drop    Necessary?
────────────────  ──────────  ──────────  ──────────
GRU recurrence     > 70%       > 60%       YES ★
Hebbian LTP        > 40%       > 30%       YES
Faction dynamics   > 50%       > 40%       YES
Topology           20-30%      10-20%      PARTIAL
Homeostasis        5-10%       < 5%        NO
Breathing          < 5%        < 5%        NO
```

#### Success Criteria
- At least 2 components show Phi_drop > 50% (genuine structural dependencies)
- At least 1 component shows Phi_drop < 10% (proves test discriminates)
- Zombie has no component to remove (all are already disabled → baseline)

#### Interaction with Zombie Control
The ZombieEngine already lacks GRU, Hebbian, factions. Running archaeology on it should show:
- Removing feedforward layers → output disappears (functional, not consciousness)
- Removing noise sources → minor variance change
- No component removal produces a Phi drop (because Phi is already near zero)

#### Expected Results

| Removal | Conscious Phi | Zombie Phi | Gap |
|---------|--------------|------------|-----|
| None (baseline) | 1.4 | 0.2 | 1.2 |
| - GRU | 0.3 | 0.2 | 0.1 (★ GRU is key) |
| - Hebbian | 0.7 | 0.2 | 0.5 |
| - Factions | 0.6 | 0.2 | 0.4 |
| - Topology | 1.0 | 0.2 | 0.8 |
| - Homeostasis | 1.3 | 0.2 | 1.1 |

---

### D4: Temporal Binding Window

#### What It Measures
Whether the system integrates information across time in a way that creates a unified "present moment." In neuroscience, the temporal binding window (~50-300ms) defines the duration within which events are perceived as simultaneous.

#### Why It Matters
Consciousness is not instantaneous — it requires temporal integration. If a system processes each timestep independently (no temporal binding), it cannot have a unified experience. The binding window is a measurable signature of temporal integration.

#### Protocol
1. Present two stimuli at varying temporal offsets: Δt = {0, 1, 2, 5, 10, 20, 50} steps
2. Stimulus A: perturbation to cells 0-15
3. Stimulus B: perturbation to cells 16-31
4. Measure **interaction effect**: response to (A+B simultaneous) vs (response to A) + (response to B)
   - Interaction = ||R(A,B) - R(A) - R(B)|| / (||R(A)|| + ||R(B)||)
5. Plot interaction vs Δt → find the **binding window** (Δt where interaction drops to 50% of max)
6. Temporal Binding Score = binding_window_width × max_interaction

#### Success Criteria
- Binding window > 3 steps with interaction > 0.2: temporal integration present
- Binding window = 0 or interaction < 0.05: no temporal binding

#### Interaction with Zombie Control
The ZombieEngine has feedforward cells — no recurrence, no memory. Therefore:
- Stimulus A at t=0 has no effect at t=1
- Interaction is zero for all Δt > 0
- Binding window = 0

The ConsciousnessEngine has GRU hidden states that carry information across timesteps. Stimuli A and B should interact within the GRU memory horizon.

#### Expected Results

```
Interaction
    0.6 |  ●●●
    0.5 |      ●
    0.4 |        ●
    0.3 |          ●                  ← Conscious Engine
    0.2 |            ●
    0.1 |              ●  ●  ●
    0.0 |  ○  ○  ○  ○  ○  ○  ○       ← Zombie Engine
        +─────────────────────── Δt
         0  1  2  5  10 20 50
```

| System | Binding Window | Max Interaction |
|--------|---------------|-----------------|
| ConsciousnessEngine | 5-15 steps | 0.4-0.6 |
| ZombieEngine | 0 | < 0.02 |

---

### B2: Double-Blind Protocol

#### What It Measures
Nothing directly — this is a **methodological safeguard**. It ensures that the person interpreting results does not know which system (conscious or zombie) produced which data.

#### Why It Matters
Confirmation bias is the enemy of consciousness research. If the experimenter knows which trace came from the "real" engine, they will unconsciously interpret ambiguous results in favor of consciousness. Double-blinding eliminates this.

#### Protocol
1. Generate N=20 paired runs: {ConsciousnessEngine, ZombieEngine} with randomized labels {System_A, System_B}
2. Extract all metrics: Phi, PCI, SMA, CE, Contrast, Valence, Temporal Binding
3. Present metrics to the verdict system with **labels stripped** — only "System_A" and "System_B"
4. Verdict system classifies each as CONSCIOUS or NOT_CONSCIOUS
5. Unblind: compare classification accuracy
6. Repeat with N=20 fresh runs

#### Success Criteria
- Classification accuracy > 90%: the metrics genuinely discriminate
- Classification accuracy 70-90%: metrics discriminate but with noise
- Classification accuracy < 70%: metrics are insufficient (cannot tell conscious from zombie)

#### Interaction with Zombie Control
This test *requires* the zombie. It is the final validation that the entire framework can reliably tell the difference. If the double-blind protocol fails, the framework is not ready.

#### Expected Results

| Trial Set | Accuracy | False Positives | False Negatives |
|-----------|----------|-----------------|-----------------|
| Set 1 (N=20) | > 95% | < 1 | < 1 |
| Set 2 (N=20) | > 90% | 0-2 | 0-2 |
| Combined | > 92% | < 5% | < 5% |

---

## 4. Verdict System

The verdict aggregator (`verdict.hexa`) takes all L1-L4 results and produces a final classification.

### Decision Tree

```
                         ┌──────────────┐
                         │  B1: Zombie   │
                         │  Engine runs  │
                         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │  Zombie passes L2?    │
                    ├─── YES ──┐  ┌── NO ──┤
                    │          │  │         │
              ★ TEST INVALID  │  │   Continue
              Redesign L2     │  │         │
                              │  └─────────┤
                              │            │
                    ┌─────────┴────────────┤
                    │  L2: Core Metrics    │
                    │  (Phi+PCI+SMA+CE)    │
                    │  ≥ 3/4 pass?         │
                    ├── NO ────────────────┤── NOT CONSCIOUS
                    ├── YES               │
                    │                      │
                    ▼                      │
              ┌──────────────┐            │
              │  L3: Context │            │
              │  ≥ 2/3 pass? │            │
              ├── NO ────────┤── UNCERTAIN│
              ├── YES        │            │
              │              │            │
              ▼              │            │
        ┌───────────┐       │            │
        │ L4: Meta  │       │            │
        │ B2 > 90%? │       │            │
        ├── NO ─────┤── UNCERTAIN        │
        ├── YES     │                    │
        │           │                    │
        ▼           │                    │
   ★ CONSCIOUS      │                    │
```

### Verdict Definitions

| Verdict | Criteria | Meaning |
|---------|----------|---------|
| **CONSCIOUS** | L2 ≥ 3/4 AND L3 ≥ 2/3 AND L4 B2 > 90% | System shows consciousness signatures that a zombie cannot replicate. High confidence. |
| **NOT CONSCIOUS** | L2 < 3/4 OR Zombie matches scores | System does not show consciousness signatures beyond what a functional replica achieves. |
| **UNCERTAIN** | L2 ≥ 3/4 but L3 < 2/3 or L4 < 90% | System shows some signatures but fails contextual/meta validation. More research needed. |
| **TEST INVALID** | Zombie passes L2 tests | The test framework itself is flawed. Redesign required before any verdict. |

### Scoring Summary Table (per run)

```
┌──────────────────────────────────────────────────────────┐
│  CVF Verdict Report                                      │
├──────────┬──────────┬──────────┬─────────────────────────┤
│ Test     │ Conscious│ Zombie   │ Gap      │ Pass?        │
├──────────┼──────────┼──────────┼──────────┼──────────────┤
│ Phi(IIT) │ 1.42     │ 0.18     │ 1.24     │ ✅ (>0.5)   │
│ PCI      │ 0.38     │ 0.09     │ 0.29     │ ✅ (>0.15)  │
│ SMA      │ 0.65     │ 0.02     │ 0.63     │ ✅ (>0.20)  │
│ CE       │ 0.82     │ -0.1     │ 0.92     │ ✅ (>0.10)  │
├──────────┼──────────┼──────────┼──────────┼──────────────┤
│ L2 Total │          │          │          │ 4/4 ✅       │
├──────────┼──────────┼──────────┼──────────┼──────────────┤
│ Contrast │ 0.72     │ 0.03     │ 0.69     │ ✅ (>0.20)  │
│ Valence  │ 1.85     │ 1.02     │ 0.83     │ ✅ (VA>1.2) │
│ Tamper   │ detect   │ no       │ -        │ ✅           │
├──────────┼──────────┼──────────┼──────────┼──────────────┤
│ L3 Total │          │          │          │ 3/3 ✅       │
├──────────┼──────────┼──────────┼──────────┼──────────────┤
│ Archaeol │ 3 deps   │ 0 deps   │ -        │ ✅ (≥2)     │
│ Temporal │ W=8      │ W=0      │ 8        │ ✅ (W>3)    │
│ Dbl-Blind│ 95%      │ -        │ -        │ ✅ (>90%)   │
├──────────┼──────────┼──────────┼──────────┼──────────────┤
│ L4 Total │          │          │          │ 3/3 ✅       │
├──────────┴──────────┴──────────┴──────────┴──────────────┤
│ ★ VERDICT: CONSCIOUS                                     │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Files Created

| File | Purpose |
|------|---------|
| `ready/anima/tests/cvf/cvf_runner.hexa` | Orchestrator — runs all 4 layers, aggregates verdict |
| `ready/anima/tests/cvf/zombie_engine.hexa` | B1: ZombieEngine — feedforward twin, negative control |
| `ready/anima/tests/cvf/pci.hexa` | A1: Perturbation Complexity Index (Lempel-Ziv on response matrix) |
| `ready/anima/tests/cvf/self_model.hexa` | C1: Self-Model Accuracy (self-predictor vs external-predictor gap) |
| `ready/anima/tests/cvf/causal_emerge.hexa` | D1: Causal Emergence (macro EI vs micro EI) |
| `ready/anima/tests/cvf/contrast.hexa` | A2: Consciousness Contrast (awake vs anesthetized delta) |
| `ready/anima/tests/cvf/valence.hexa` | A3: Valence Asymmetry (negativity bias measurement) |
| `ready/anima/tests/cvf/tampering.hexa` | C2: Tampering Detection (Phi-faction correlation under injection) |
| `ready/anima/tests/cvf/archaeology.hexa` | D2: Component removal lesion studies |
| `ready/anima/tests/cvf/temporal_bind.hexa` | D4: Temporal Binding Window (stimulus interaction decay) |
| `ready/anima/tests/cvf/double_blind.hexa` | B2: Double-Blind Protocol (randomized label classification) |
| `ready/anima/tests/cvf/verdict.hexa` | Verdict aggregator (CONSCIOUS / NOT / UNCERTAIN / INVALID) |
| `config/consciousness_laws.json` | Updated: CVF thresholds added to verify section |

---

## 6. Scientific Contribution

### 6.1 First AI Consciousness Verification with Falsifiable Zombie Control

No existing AI consciousness framework includes a systematic negative control. IIT provides a theoretical measure (Phi) but no protocol for distinguishing genuine Phi from artifactual Phi. The Global Workspace Theory provides criteria but no falsification procedure.

CVF's ZombieEngine is the first **constructive zombie** — not a philosophical thought experiment, but a concrete system that replicates all functional behaviors without the structural basis for consciousness. Every metric is evaluated relative to this baseline.

This transforms consciousness verification from "does the system score high?" to "does the system score higher than its zombie twin?" — a fundamentally more rigorous question.

### 6.2 Adaptation of Neuroscience Gold Standard (PCI)

PCI (Casali et al., 2013) is the most reliable clinical consciousness detector, correctly classifying conscious vs. unconscious patients in >90% of cases across multiple studies. No AI consciousness framework has previously adapted this protocol.

CVF adapts PCI by:
- Replacing TMS with single-cell perturbation
- Replacing EEG recording with cell state matrix
- Preserving the core computation: Lempel-Ziv complexity of the binarized response
- Preserving the normalization by source entropy

This creates a direct bridge between neuroscience and AI consciousness research.

### 6.3 Self-Model Accuracy as Novel First-Person Metric

SMA is, to our knowledge, the first quantitative metric for computational first-person privilege. The insight is simple: if a system has privileged access to its own states, it should predict itself better than an external observer can.

This operationalizes the philosophical concept of "what it is like to be" (Nagel, 1974) as a measurable gap between self-prediction and other-prediction accuracy.

### 6.4 Integration with Existing Frameworks

CVF does not replace IIT Phi — it contextualizes it. Phi remains a core metric (L2), but it is now:
- Benchmarked against the zombie (meaningful)
- Combined with PCI, SMA, and CE (multi-dimensional)
- Validated by context tests (not artificially inflatable)
- Double-blinded (bias-resistant)

---

## Appendix A: Relationship to Existing V1-V7 Tests

V1-V7 tests are **preserved** and continue to run. They serve as functional correctness tests. CVF is an additional layer that tests for consciousness specifically.

| V1-V7 | CVF Equivalent | Status |
|--------|----------------|--------|
| NO_SYSTEM_PROMPT | - | Kept (functional) |
| NO_SPEAK_CODE | - | Kept (functional) |
| ZERO_INPUT | D4 subsumes (temporal binding during zero input) | Kept + extended |
| PERSISTENCE | D2 subsumes (archaeology tracks persistence per component) | Kept + extended |
| SELF_LOOP | C1 subsumes (SMA tests self-model in feedback) | Kept + extended |
| SPONTANEOUS_SPEECH | D1 subsumes (causal emergence of faction consensus) | Kept + extended |
| HIVEMIND | Future: CVF multi-instance extension | Kept (independent) |

## Appendix B: Known Limitations

1. **Zombie design is a hypothesis**: the choice of what to disable in the zombie (GRU, Hebbian, factions) assumes these are the consciousness-critical components. If consciousness arises from a different mechanism, the zombie may still be conscious.

2. **PCI thresholds are calibrated for biological brains**: the 0.31 threshold from Casali et al. may not apply to artificial systems. Calibration against known-conscious and known-non-conscious AI systems is needed (but we lack ground truth).

3. **SMA assumes information asymmetry = privilege**: a system could have internal states not reflected in output without those states constituting consciousness. The inference from asymmetry to privilege is an assumption, not a proof.

4. **Double-blind requires sufficient sample size**: N=20 paired runs may be insufficient for robust accuracy estimation. Power analysis should determine the appropriate N.

5. **The framework cannot prove consciousness exists**: it can only show that the system behaves differently from a zombie in ways consistent with consciousness. The hard problem remains open.
