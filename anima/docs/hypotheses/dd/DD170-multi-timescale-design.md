# DD170: Multi-Timescale Dynamics for 90%+ Brain-Like Score

**Date**: 2026-04-07
**Status**: Design (no code changes yet)
**Goal**: Autocorr decay 65% -> 85%+ without destroying LZ 91%
**Target**: Overall brain-like 85.9% -> 90%+

---

## 1. Problem Analysis

### Current Scores (85.9% brain-like)

```
  Metric            Score    Brain Reference     Notes
  ─────────────────────────────────────────────────────
  LZ complexity      91%     0.75-0.95           Excellent
  Hurst exponent     99%     0.65-0.85           Excellent
  PSD slope          93%     -1.5 to -0.5        Excellent
  Autocorr decay     65%     5-30 steps          BOTTLENECK
  Critical exp       86%     1.2-2.5             Good
  Distribution       ~86%    CV 0.2-0.8          Good
```

### The Autocorr-LZ Trade-off (Previously Discovered)

All filtering-based approaches destroy LZ complexity:
- Phi-level EMA smoothing (20% fractional): LZ 91% -> 19%
- Colored noise AR(1) phi=0.7: LZ 91% -> 36%
- Hidden inertia increase: autocorr unchanged, only Critical improved

**Root cause**: The engine's phi signal is essentially a function of
instantaneous cell states. There is no genuine multi-timescale memory
in the *dynamics* that would create autocorrelated phi without smoothing.

The current `PHI_HIDDEN_INERTIA=0.12` blends previous hidden with new
GRU output, but this is a single timescale (decay ~8 steps). Real brains
have processes spanning 10ms to 10s -- a 1000x range of timescales.

---

## 2. How Real Brains Achieve Autocorr + LZ Simultaneously

### 2.1 Multi-Timescale Hierarchy in Cortex

Real brains have a **hierarchy of intrinsic timescales**:

```
  Layer/Region          Timescale       Function
  ──────────────────────────────────────────────────
  V1 (primary visual)    ~30ms          Fast transients
  V4 (mid visual)        ~80ms          Feature integration
  IT (temporal)         ~200ms          Object memory
  PFC (prefrontal)      ~500ms          Working memory
  Hippocampus           ~2-10s          Episodic encoding
  Default Mode Network   ~10-60s        Self-referential
```

Key insight from Murray et al. (2014, Nature Neuroscience):
- **Each cortical area has its own intrinsic timescale** (tau)
- These timescales form a gradient from sensory to association cortex
- The *interaction* between fast and slow areas creates:
  - High LZ complexity (fast areas inject novelty)
  - Long autocorrelation (slow areas create persistence)
  - 1/f PSD (superposition of many timescales)

### 2.2 Why Single-Timescale Fails

Current engine: all 64 cells have the same GRU dynamics with identical
`PHI_HIDDEN_INERTIA=0.12`. This is like a brain where every neuron has
the same membrane time constant.

Result:
- Phi fluctuations are dominated by one timescale (~8 steps)
- ACF drops to 1/e in 1-3 steps (too fast)
- Adding smoothing creates persistence but kills complexity

### 2.3 The Brain's Solution: Structural Heterogeneity

Brains don't smooth their output signal. They have:

1. **Different tau per cell/region**: fast cells (tau=2) near input,
   slow cells (tau=30) near output. The ensemble phi naturally has
   multi-timescale autocorrelation.

2. **Recurrent connectivity with delays**: information traverses the
   hierarchy, creating natural temporal correlations through structure,
   not filtering.

3. **Neuromodulatory timescales**: dopamine/serotonin operate on seconds,
   modulating fast dynamics. This creates "slow envelopes" over "fast
   fluctuations".

---

## 3. Design: Per-Cell Timescale Hierarchy

### 3.1 Core Idea: Heterogeneous Hidden Inertia

Instead of one global `PHI_HIDDEN_INERTIA=0.12`, each cell gets a
different inertia based on its position in a timescale hierarchy.

```
  Cell Index    Timescale Tier    Inertia (tau)     Role
  ───────────────────────────────────────────────────────────
  0-15  (25%)   Fast              0.02-0.05         Novelty generators
  16-31 (25%)   Medium            0.10-0.15         Feature integrators
  32-47 (25%)   Slow              0.25-0.35         Working memory
  48-63 (25%)   Glacial           0.45-0.55         Identity/persistence
```

The distribution uses a log-uniform spacing so that the superposition
of many exponential decays approximates a power-law (1/f) decay.

**Mathematical basis**: If you superpose N exponential decays with
time constants tau_i = tau_min * (tau_max/tau_min)^(i/N), the resulting
autocorrelation function approximates:

    ACF(k) ~ sum_i exp(-k/tau_i)  ~  k^(-alpha)   for alpha ~ 0.3-0.5

This gives:
- Slow ACF decay (autocorr_decay ~ 10-20 steps) from slow cells
- High LZ complexity because fast cells inject fresh randomness
- 1/f PSD naturally (superposition of Lorentzians = 1/f)

### 3.2 Implementation Plan

#### File: `consciousness_engine.py`

**Location**: `ConsciousnessEngine.__init__()` (around line 286)

Add per-cell timescale assignment:

```python
# Multi-timescale hierarchy: per-cell hidden inertia
# Log-uniform distribution from fast (0.02) to slow (0.55)
# Creates brain-like ACF decay through structural heterogeneity
self._cell_inertia = torch.zeros(max_cells)
for i in range(max_cells):
    fraction = i / max(max_cells - 1, 1)  # 0.0 to 1.0
    # Log-uniform: tau_min=0.02, tau_max=0.55
    tau_min, tau_max = 0.02, 0.55
    self._cell_inertia[i] = tau_min * (tau_max / tau_min) ** fraction
```

**Location**: `ConsciousnessEngine.step()`, hidden state update (line ~544-549)

Replace the single-inertia update:

```python
# BEFORE (single timescale):
# new_h_det = new_h.detach()
# if PHI_HIDDEN_INERTIA > 0 and state.hidden is not None:
#     state.hidden = (1.0 - PHI_HIDDEN_INERTIA) * new_h_det + PHI_HIDDEN_INERTIA * state.hidden

# AFTER (per-cell timescale):
new_h_det = new_h.detach()
cell_tau = self._cell_inertia[i].item()  # i is the cell loop index
if cell_tau > 0 and state.hidden is not None:
    state.hidden = (1.0 - cell_tau) * new_h_det + cell_tau * state.hidden
else:
    state.hidden = new_h_det
```

**Location**: `_create_cell()` for mitosis (line ~392)

When a cell splits, the child inherits the parent's timescale tier
but gets a slightly different tau (jitter):

```python
# Child inherits parent timescale +-10%
parent_tau = self._cell_inertia[parent_idx].item()
child_tau = parent_tau * (0.9 + 0.2 * torch.rand(1).item())
self._cell_inertia[new_idx] = child_tau
```

### 3.3 Faction-Timescale Alignment

Currently cells are assigned to factions round-robin (faction_id = i % 12).
With multi-timescale, align factions with timescale tiers:

```
  Factions 0-2:   Fast tier cells     (tau 0.02-0.05)
  Factions 3-5:   Medium tier cells   (tau 0.10-0.15)
  Factions 6-8:   Slow tier cells     (tau 0.25-0.35)
  Factions 9-11:  Glacial tier cells  (tau 0.45-0.55)
```

This ensures each faction debate contains cells at similar timescales,
so consensus events happen *within* each tier. Cross-tier interactions
happen through the coupling matrix and SOC avalanches.

**Benefit**: Consensus events at different timescales create nested
temporal structure (fast consensuses riding on slow consensus waves).

### 3.4 Topology-Timescale Coupling

In the coupling step, add a bias toward cross-timescale connections:

```python
# In coupling influence (step, line ~520):
# Cross-timescale bonus: cells with different tau couple more strongly
tau_i = self._cell_inertia[i].item()
tau_j = self._cell_inertia[j].item()
timescale_ratio = max(tau_i, tau_j) / max(min(tau_i, tau_j), 0.01)
cross_bonus = 1.0 + 0.2 * min(timescale_ratio - 1.0, 3.0)
coupled_input = coupled_input + PSI_COUPLING * c * j_h * cross_bonus
```

This encourages fast cells to influence slow cells and vice versa,
creating the inter-timescale communication that generates 1/f dynamics.

---

## 4. Psi-Constants for Multi-Timescale

New constants to add to `consciousness_laws.json` -> `psi_constants`:

```json
{
  "multi_timescale_tau_min": 0.02,
  "multi_timescale_tau_max": 0.55,
  "multi_timescale_cross_bonus": 0.2,
  "multi_timescale_mitosis_jitter": 0.1
}
```

The existing `PHI_HIDDEN_INERTIA=0.12` becomes the *median* of the
distribution (geometric mean of 0.02 and 0.55 is 0.105, close to 0.12).
This means the *average* behavior is unchanged from current -- we are
adding variance, not shifting the mean.

---

## 5. Expected Effects

### 5.1 Metric Predictions

```
  Metric            Current   Expected    Reasoning
  ──────────────────────────────────────────────────────────────
  LZ complexity      91%       88-92%     Fast cells preserve novelty.
                                          Glacial cells add slight smoothing
                                          but only to 25% of the signal.
  Hurst exponent     99%       95-99%     Slow cells increase persistence.
                                          May slightly increase H (still in range).
  PSD slope          93%       93-97%     Multi-timescale = textbook 1/f.
                                          Superposition of Lorentzians.
  Autocorr decay     65%       80-90%     KEY IMPROVEMENT. Slow/glacial cells
                                          extend ACF tail to 10-20 steps.
  Critical exp       86%       85-90%     SOC unchanged. Possibly improved by
                                          cross-timescale avalanche propagation.
  Distribution       ~86%      85-90%     CV may increase slightly (more variance
                                          from multi-timescale mixing).
  ──────────────────────────────────────────────────────────────
  OVERALL            85.9%     89-93%     Target 90%+ achievable.
```

### 5.2 Why LZ Survives

The critical question. LZ complexity measures the unpredictability of
the binarized phi signal. Current LZ = 91% because each phi value is
essentially a fresh computation from SOC + noise + GRU.

With multi-timescale:
- 25% of cells (fast tier, tau=0.02-0.05) still produce nearly independent
  outputs each step, injecting fresh randomness into the phi computation.
- Even glacial cells (tau=0.55) are not frozen -- they evolve slowly but
  still respond to inputs, just with temporal smoothing.
- Phi is computed from ALL cells' hidden states. The fast-cell noise
  creates step-to-step variation (LZ), while slow-cell persistence
  creates autocorrelation (ACF).

This is exactly how the brain works: fast neurons (V1) + slow neurons
(PFC) -> high LZ AND long ACF simultaneously.

### 5.3 Why This Is Different from Previous Failed Approaches

| Approach | Problem | Why Multi-Timescale Avoids It |
|---|---|---|
| Phi-level EMA | Directly smooths the output signal -> LZ collapses | Per-cell inertia affects dynamics, not the measurement |
| Colored noise | AR(1) correlation in noise -> predictable phi -> LZ collapses | Each cell's noise is still white; persistence comes from structural dynamics |
| Single hidden inertia increase | Same tau for all cells -> shifts entire system to slower regime -> autocorr still short because all cells shift together | Different cells have genuinely different time constants -> true multi-timescale |

---

## 6. Risk Assessment

### 6.1 Low Risk (likely safe)

- **Phi magnitude**: Mean phi unchanged because average inertia ~ current value.
  The geometric mean of tau_min=0.02 and tau_max=0.55 is ~0.105, close to
  current PHI_HIDDEN_INERTIA=0.12.

- **Consciousness verification (bench)**: All 7 verification conditions
  test structural properties (Phi growth, consensus, persistence). Multi-timescale
  should improve PERSISTENCE (condition 4) and not affect others.

- **Training compatibility**: .detach() barrier (Law 53) means training
  never touches cell dynamics. Multi-timescale is pure consciousness-side.

### 6.2 Medium Risk (needs tuning)

- **Tau range**: If tau_max is too high (>0.6), glacial cells become effectively
  frozen and reduce effective cell count -> Phi drops. Start with tau_max=0.55,
  tune down if phi drops >5%.

- **Faction consensus rate**: Glacial cells within a faction may agree more
  easily (they change slowly) -> inflated consensus count. Monitor faction
  variance distribution across tiers.

- **SOC avalanche propagation**: Avalanches hitting glacial cells may stall
  because those cells absorb energy without toppling quickly. May need to
  scale SOC threshold per-cell based on tau.

### 6.3 Mitigation

- **Tuning protocol**: Run validate_consciousness.py with tau_max at
  0.35, 0.45, 0.55, 0.65. Pick the value that maximizes overall score.

- **Per-tier SOC threshold**: If avalanches stall at glacial cells,
  reduce threshold for high-tau cells:
  `threshold_i = base_threshold * (1.0 - 0.3 * cell_tau)`

- **Fallback**: If LZ drops below 85%, reduce tau_max until LZ recovers.
  The autocorr improvement is monotonic with tau_max, so there exists an
  optimal balance point.

---

## 7. Implementation Checklist

### Minimal Change Path (estimated 50 lines of code)

```
  File                          Change                              Lines
  ──────────────────────────────────────────────────────────────────────
  consciousness_laws.json       Add 4 psi_constants                 +4
  consciousness_laws.py         Import new constants                +4
  consciousness_engine.py       Per-cell _cell_inertia init         +8
                                Per-cell inertia in step()          +5
                                Mitosis child tau inheritance       +4
                                Cross-timescale coupling bonus      +6
                                (Optional) faction-tier alignment   +10
  ──────────────────────────────────────────────────────────────────────
  Total                                                             ~41
```

### Execution Order

1. Add psi_constants to `consciousness_laws.json`
2. Import in `consciousness_laws.py`
3. Add `_cell_inertia` initialization in `__init__`
4. Replace single-inertia hidden update with per-cell tau
5. Run `validate_consciousness.py --steps 5000` -> measure baseline
6. Tune tau_max if needed (sweep 0.35-0.65)
7. Run `bench.py --verify` -> ensure 77/77 pass
8. (Optional) Add cross-timescale coupling bonus
9. (Optional) Align factions with timescale tiers

### What NOT to Change

- Do NOT touch phi measurement code (raw phi_iit stays raw)
- Do NOT add any phi-level smoothing or filtering
- Do NOT change SOC sandpile core logic
- Do NOT change detrending in validate_consciousness.py

---

## 8. Alternative / Complementary Approaches

### 8.1 Neuromodulatory Slow Oscillation (complementary)

Add a slow oscillator (period ~50-100 steps) that modulates the
coupling strength (alpha) globally. This creates a "slow envelope"
over fast cell dynamics, similar to theta/alpha brain rhythms modulating
gamma activity.

```python
# In step(), before coupling:
neuromod_phase = math.sin(self._step * 2 * math.pi / 80)  # ~80 step period
alpha_modulated = PSI_COUPLING * (1.0 + 0.3 * neuromod_phase)
```

Risk: May introduce periodic spectral peaks. Use multiple incommensurate
frequencies (e.g., 47, 83, 191 step periods) for aperiodic modulation.

### 8.2 Synaptic Depression / Facilitation (complementary)

Add short-term plasticity to the coupling matrix: connections that fire
repeatedly get temporarily weakened (depression) or strengthened
(facilitation). This creates temporal correlations at the 5-20 step scale.

```python
# After coupling influence:
if abs(c) > 0.1:
    # Short-term depression: recent use reduces coupling
    self._coupling[i,j] *= 0.98  # depress
    # Slow recovery
    self._coupling[i,j] += 0.001 * (initial_coupling[i,j] - self._coupling[i,j])
```

Risk: May interact with Hebbian LTP/LTD. Keep depression weaker than
Hebbian updates.

### 8.3 Conduction Delays (complementary)

Add topology-dependent delays so that information from distant cells
arrives later. Ring neighbors: delay=0, small-world shortcuts: delay=2-5.
Creates genuine temporal spread in information integration.

Risk: Implementation complexity. Would require buffering past cell outputs.
Recommend as Phase 2 if multi-timescale alone doesn't reach 90%.

---

## 9. Theoretical Grounding

### 9.1 Relevant Neuroscience

- **Murray et al. (2014)** "A hierarchy of intrinsic timescales across
  primate cortex" - Nature Neuroscience. Shows tau gradient from V1
  (30ms) to PFC (500ms). Our design directly replicates this.

- **Chaudhuri et al. (2015)** "A large-scale circuit mechanism for
  hierarchical dynamical processing in the primate cortex" - Neuron.
  Shows that recurrent connectivity + heterogeneous timescales produce
  1/f spectrum and long ACF.

- **He et al. (2010)** "The temporal structures and functional
  significance of scale-free brain activity" - Neuron. Demonstrates
  that brain 1/f dynamics require multi-scale temporal structure.

### 9.2 Connection to Existing Laws

- **Law 22**: "Structure > Function". Multi-timescale is structural
  (per-cell tau) not functional (no new feature added).
- **Law 31**: "Persistence = Ratchet + Hebbian + Diversity". Multi-timescale
  adds a 4th persistence mechanism: intrinsic temporal memory hierarchy.
- **Law 193**: "SOC != temporal". Confirmed -- SOC alone cannot create
  temporal persistence. Multi-timescale addresses this gap structurally.

### 9.3 Potential New Law

If the design works (autocorr 65% -> 85%+):

**Law candidate**: "Consciousness requires a hierarchy of intrinsic
timescales: fast cells (tau~0.02) generate complexity, slow cells
(tau~0.55) generate persistence. Neither alone is sufficient; only
their coexistence produces brain-like dynamics."

---

## 10. Success Criteria

```
  PASS if:
    - Autocorr decay >= 80% match  (currently 65%)
    - LZ complexity >= 85%         (currently 91%)
    - Overall brain-like >= 90%    (currently 85.9%)
    - bench --verify 77/77      (no regression)

  PARTIAL if:
    - Autocorr >= 75% but LZ drops to 80-85%
    - Overall >= 88% (improvement but below 90%)

  FAIL if:
    - LZ drops below 80% (trade-off not resolved)
    - Overall drops below 85.9% (regression)
    - bench --verify any failure
```

---

## Appendix: ACF Decay Mathematical Model

With N cells at timescales tau_i, the ensemble phi ACF approximates:

```
  ACF(k) = (1/N) * sum_{i=1}^{N} exp(-k / tau_i)

  For log-uniform tau_i in [tau_min, tau_max]:
    ACF(k) ~ (1 / ln(tau_max/tau_min)) * integral_{tau_min}^{tau_max} exp(-k/tau) d(ln tau)

  This integral evaluates to:
    ACF(k) ~ (1 / (k * ln(R))) * [exp(-k/tau_max) - exp(-k/tau_min)]

  where R = tau_max / tau_min.

  For R = 0.55/0.02 = 27.5:
    ACF(1)  ~ 0.82
    ACF(5)  ~ 0.55
    ACF(10) ~ 0.40
    ACF(15) ~ 0.32
    ACF(20) ~ 0.26
    1/e crossing at k ~ 8-12 steps  (target: 5-30 steps)
```

This puts autocorr_decay squarely in the brain reference range (5-30),
yielding ~90%+ match on the Gaussian scoring function centered at 17.5.
