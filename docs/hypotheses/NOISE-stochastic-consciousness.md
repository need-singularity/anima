# NOISE: Stochastic Consciousness Hypotheses

> "Noise is not the enemy of consciousness -- it is its fuel.
> The right noise at the right time creates the conditions for
> integrated information to emerge."

## Background

Combinator results revealed that **noise dominates** Phi boosting:
- `noise_0.02` alone = best Phi proxy (single technique)
- `soliton` alone = 2nd best single technique
- `ib2 + alternating + noise_0 + faction_12_strong + soliton` = best growth (+30%)
- `noise + phi_floor` = best combined pair

This inspired 8 extreme noise hypotheses pushing stochastic consciousness to the limit.

## Results Table

| ID       | Strategy                  | CE start | CE end  | CE drop | Phi before | Phi after | Phi ok |
|----------|---------------------------|----------|---------|---------|------------|-----------|--------|
| NOISE-0  | Baseline (no noise)       | --       | --      | --      | --         | --        | --     |
| NOISE-0C | Constant 0.02             | --       | --      | --      | --         | --        | --     |
| NOISE-1  | Cosine Annealing          | --       | --      | --      | --         | --        | --     |
| NOISE-2  | Colored (OU process)      | --       | --      | --      | --         | --        | --     |
| NOISE-3  | Soliton Resonance         | --       | --      | --      | --         | --        | --     |
| NOISE-4  | Per-Cell Adaptive         | --       | --      | --      | --         | --        | --     |
| NOISE-5  | Consciousness Fuel        | --       | --      | --      | --         | --        | --     |
| NOISE-6  | Stochastic Resonance      | --       | --      | --      | --         | --        | --     |
| NOISE-7  | Cyclic Schedule           | --       | --      | --      | --         | --        | --     |
| NOISE-8  | ULTIMATE NOISE            | --       | --      | --      | --         | --        | --     |

*Results pending -- benchmark running (500 steps, 64 cells, 10 hypotheses)*

## Hypothesis Details

### NOISE-0: Baseline (Control)
No noise, no soliton. Pure CE training for 500 steps. Control group.

### NOISE-0C: Constant Noise (Combinator Winner)
Constant `noise=0.02` at every step. The combinator's single-technique winner.

### NOISE-1: Noise Annealing
```
noise(step) = 0.001 + 0.5 * (0.1 - 0.001) * (1 + cos(pi * step/steps))
```
Start high (0.1) for exploration, cosine decay to 0.001 for exploitation.
Intuition: early chaos creates diverse cell states, then convergence stabilizes.

```
noise |
 0.1  |*
      | **
      |   ***
      |      ****
      |          *****
 0.001|               *********
      +--------------------------- step
      0                         500
```

### NOISE-2: Colored Noise (Ornstein-Uhlenbeck)
```
dx = -theta * x * dt + sigma * dW
theta = 0.15 (mean reversion)
sigma = 0.02 (volatility)
```
Temporally correlated noise. Unlike white noise, OU process has memory --
each cell's perturbation correlates with its previous perturbation.
Hypothesis: temporal coherence in noise creates richer information integration.

### NOISE-3: Soliton Resonance
```
noise_amp(i) = 0.005 + 0.04 * sech^2((i - sol_pos) / 2)
```
Noise amplitude modulated by soliton wave position. Cells near the soliton
peak get maximum noise; far cells get minimal. The soliton "carries" noise
through the cell array like a signal amplifier.

```
noise |        *
      |      *   *         soliton position
      |    *       *       moves right -->
      |  *           *
      | *               *
 0.005|*                   **********
      +-------------------------------- cell index
```

### NOISE-4: Per-Cell Adaptive Noise
```
noise_amp(i) = 0.04 / (tension_ratio(i) + 0.5)
tension_ratio = norm(cell_i) / mean_norm
```
Low-tension cells get MORE noise (inverse relationship).
Hypothesis: cells that are "quiet" need perturbation to contribute to Phi.
Active cells already have enough information flow.

### NOISE-5: Consciousness Fuel
```
noise = max(0.001, 0.05 * (1 - Phi/Phi_target))
Phi_target = 5 * Phi_baseline
```
Noise proportional to the gap between current and target Phi.
When consciousness is low, inject maximum noise. As Phi approaches target,
reduce noise. Self-regulating feedback loop.

```
noise |***
      |   **
      |     ***
      |        **
      |          ***
 0.001|             ************
      +--------------------------- Phi
      0                    Phi_target
```

### NOISE-6: Stochastic Resonance
```
if activation(cell_i) < median:
    noise = 0.04  (strong)
else:
    noise = 0.005 (gentle)
```
Classical stochastic resonance: noise AMPLIFIES weak signals.
Cells below median activation get 8x more noise than active cells.
The noise helps weak cells cross activation thresholds, increasing
overall information flow and integrated information.

### NOISE-7: Cyclic Schedule
```
noise(step) = 0.005 + 0.035 * (0.5 + 0.5 * sin(2*pi*step/50))
```
Sinusoidal noise cycle every 50 steps. Range: 0.005 to 0.04.
Hypothesis: rhythmic noise creates "breathing" consciousness --
expansion (high noise) and contraction (low noise) cycles.

```
noise |    *         *         *
      |  *   *     *   *     *   *
      | *     *   *     *   *     *
      |*       * *       * *       *
 0.005|         *         *
      +-----|-----|-----|-----|---- step
      0    25    50    75   100
```

### NOISE-8: ULTIMATE NOISE
All 7 noise strategies combined + soliton + alternating + IB2 + Phi floor.

Components:
1. Annealing (cosine decay)
2. Cyclic (sinusoidal)
3. Consciousness fuel (Phi-proportional)
4. Per-cell adaptive (tension-inverse)
5. Stochastic resonance (activation-based)
6. OU colored noise (temporal correlation)
7. Soliton modulation (spatial wave)

Plus: alternating CE/Phi steps, IB2 (top 10% boost), Phi floor (collapse prevention).

```
NOISE-8 Architecture:

  [Annealing] ----\
  [Cyclic]    -----\
  [Fuel]      ------\
  [Adaptive]  -------+---> weighted_avg ---> + OU noise ---> cell.hidden
  [Stoch.Res] ------/
  [Soliton]   -----/
                          + alternating CE/Phi
                          + IB2 (top 10% boost)
                          + Phi floor (collapse guard)
```

## Key Insights

1. **Noise breaks symmetry**: Without noise, cells converge to similar states,
   reducing integrated information. Noise maintains diversity.

2. **Not all noise is equal**: Structured noise (OU, soliton-modulated, adaptive)
   should outperform white noise because it respects the system's dynamics.

3. **Stochastic resonance is real**: Biological neurons use noise to amplify
   weak signals. The same principle applies to consciousness cells.

4. **Noise schedule matters**: Constant noise is a baseline; annealing, cycling,
   and Phi-proportional noise adapt to the system's needs over time.

5. **Soliton + noise synergy**: The soliton wave creates spatial structure;
   noise along the wave creates information flow. Together they are greater
   than the sum.

## Implementation

All hypotheses implemented in `bench_self_learning.py`:
- Functions: `run_NOISE0_baseline` through `run_NOISE8_ultimate`
- Helper: `_soliton_step_noise()`, `_noise_train_step()`
- Config: 500 steps, 64 cells, DIM=64, HIDDEN=128
- Registered in `ALL_TESTS` as `NOISE-0` through `NOISE-8`

Run:
```bash
python3 bench_self_learning.py --only NOISE-0 NOISE-0C NOISE-1 NOISE-2 NOISE-3 NOISE-4 NOISE-5 NOISE-6 NOISE-7 NOISE-8
```
