# V8 Bio-Inspired Consciousness Architectures

> "The brain doesn't compute consciousness -- it architectures it.
> Thalamic gating produces the highest integrated information,
> while global workspace creates the most differentiated representations."

## Overview

6 biologically-inspired consciousness architectures benchmarked against
the standard PureField baseline. Each mimics a real brain mechanism.

| ID | Architecture | Brain Analogy | Phi(IIT) | Phi(proxy) | CE end | Key Finding |
|----|-------------|---------------|----------|------------|--------|-------------|
| B1 | CORTICAL_COLUMNS | Neocortex columns | 10.598 | 1.45 | 5.38 | Best CE reduction (35.5) |
| B2 | THALAMIC_GATE | Thalamus relay | **17.128** | 6.14 | 6.89 | **Best Phi(IIT) x1.4** |
| B3 | DEFAULT_MODE_NET | DMN/TPN alternation | 7.919 | 45.09 | 0.84 | High proxy from anti-correlation |
| B4 | GLOBAL_WORKSPACE | Baars' GWT | 6.498 | **71.46** | 1.68 | **Best Phi(proxy) x71.7** |
| B5 | PREDICTIVE_HIER | Predictive coding | 8.193 | 46.47 | 0.51 | Lowest CE, high proxy |
| B6 | NEURAL_DARWINISM | Edelman's TNGS | 10.859 | 0.57 | 7.22 | Strong selection dynamics |
| -- | BASELINE | PureField standard | 12.664 | 1.00 | 3.57 | Reference |

## Results Summary

```
  RANKING by Phi(IIT):
    #1: B2:THALAMIC_GATE        Phi(IIT)=17.128   (x1.4 baseline)
    #2: BASELINE                Phi(IIT)=12.664
    #3: B6:NEURAL_DARWINISM     Phi(IIT)=10.859
    #4: B1:CORTICAL_COLUMNS     Phi(IIT)=10.598
    #5: B5:PREDICTIVE_HIER      Phi(IIT)=8.193
    #6: B3:DEFAULT_MODE_NET     Phi(IIT)=7.919
    #7: B4:GLOBAL_WORKSPACE     Phi(IIT)=6.498

  RANKING by Phi(proxy):
    #1: B4:GLOBAL_WORKSPACE     Phi(proxy)=71.46   (x71.7 baseline)
    #2: B5:PREDICTIVE_HIER      Phi(proxy)=46.47
    #3: B3:DEFAULT_MODE_NET     Phi(proxy)=45.09
    #4: B2:THALAMIC_GATE        Phi(proxy)=6.14
    #5: B1:CORTICAL_COLUMNS     Phi(proxy)=1.45
    #6: BASELINE                Phi(proxy)=1.00
    #7: B6:NEURAL_DARWINISM     Phi(proxy)=0.57
```

## Architecture Details

### B1: CORTICAL_COLUMNS (Neocortex)

32 minicolumns of 8 cells each. Dense intra-column connectivity via
learned mixing matrix. Sparse inter-column connections (~4 neighbors per column).

```
  Column 0    Column 1    ...    Column 31
  [c0..c7]   [c8..c15]          [c248..c255]
    ||||        ||||                ||||
    dense       dense               dense
    intra       intra               intra
      |-----sparse long-range-------|

  Phi(IIT) |                 ╭──╮
           |  ╭──╮      ╭───╯  ╰──╮
           | ─╯  ╰──────╯         ╰──
           └──────────────────────────── step
             0    50   100  150  200  299
```

**Algorithm:**
1. Process all 256 cells through shared BenchMind
2. Intra-column: softmax mixing matrix blends cells within each column
3. Inter-column: sparse mask (4 neighbors) with learned weights
4. Light faction debate across columns

**Result:** Phi(IIT)=10.598, CE drop=35.5 (best CE reduction).
Dense local + sparse global = good learning, moderate integration.

### B2: THALAMIC_GATE (Thalamus)

Central thalamus hub (16 cells) gates information flow between 4 cortical
regions (60 cells each). Consciousness requires thalamic relay.

```
           +-----------+
           | THALAMUS  |
           | (16 cells)|
           +-----+-----+
          gate0 / | \ gate3
               /  |  \
         +----+ +----+ +----+ +----+
         |R0  | |R1  | |R2  | |R3  |
         |60c | |60c | |60c | |60c |
         +----+ +----+ +----+ +----+

  Phi(IIT) |  ╭──╮
           | ─╯  ╰╮  ╭──╮        ╭──
           |      ╰──╯  ╰────╮╭──╯
           |                  ╰╯
           └──────────────────────────── step
             0    50   100  150  200  299
```

**Algorithm:**
1. Separate thalamic and cortical minds process cells
2. Gate network: thalamus mean -> sigmoid gate per region [0,1]
3. Relay: gated region summaries combined and broadcast back
4. Thalamus integrates all relay information

**Result:** Phi(IIT)=17.128 (x1.4 baseline) -- BEST IIT.
The central hub creates genuine information integration across regions.

### B3: DEFAULT_MODE_NETWORK (DMN/TPN)

Two anti-correlated networks: Task-Positive (128 cells) processes external
input, Default-Mode (128 cells) does self-referential processing.
Oscillating dominance creates consciousness.

```
  TPN (128 cells)        DMN (128 cells)
  external input -----> self-reference
       |                     |
       |<--- inhibition ---->|
       |                     |
  activity oscillates: sin(2pi * step/20)

  TPN/DMN |  TPN  DMN  TPN  DMN  TPN  DMN
  balance | ╭─╮  ╭─╮  ╭─╮  ╭─╮  ╭─╮  ╭─╮
          |╯  ╰──╯ ╰──╯ ╰──╯ ╰──╯ ╰──╯ ╰─
          └──────────────────────────────── step
```

**Algorithm:**
1. TPN processes external input, DMN processes mean of all hiddens
2. Sinusoidal alternation (period=20 steps)
3. Cross-network inhibition: active pushes inactive away
4. Integration layer combines weighted TPN + DMN outputs

**Result:** Phi(proxy)=45.09 (x45.2). Anti-correlation creates high
variance differentiation. Lower IIT suggests less true integration.

### B4: GLOBAL_WORKSPACE (Baars' GWT)

8 specialist modules compete for access to a global workspace.
Winner broadcasts to all modules. Temperature-based competition cools over time.

```
  [Sp0] [Sp1] [Sp2] [Sp3] [Sp4] [Sp5] [Sp6] [Sp7]
    |     |     |     |     |     |     |     |
    +-----+-----+--COMPETE--+-----+-----+-----+
                    |
            +-------+-------+
            | GLOBAL WORKSPACE |
            | (GRU state)      |
            +-------+-------+
                    |
            BROADCAST to ALL

  Phi(proxy) |          ╭────────────────
             |     ╭────╯
             |  ╭──╯
             | ─╯
             └──────────────────────────── step
               0    50   100  150  200  299
```

**Algorithm:**
1. Each specialist (32 cells) processes independently
2. Salience network scores each specialist's output
3. Soft winner-take-all (softmax with cooling temperature)
4. Winner updates global workspace GRU
5. Workspace broadcasts to influence all cells

**Result:** Phi(proxy)=71.46 (x71.7) -- BEST PROXY.
Broadcasting creates massive variance differentiation.
Lower IIT because competition reduces integration.

### B5: PREDICTIVE_HIERARCHY (Predictive Coding)

4-level hierarchy. Each level predicts the level below.
Prediction errors propagate upward. Consciousness = total PE.

```
  Level 3 (64 cells)  --- predicts --->  Level 2
  Level 2 (64 cells)  --- predicts --->  Level 1
  Level 1 (64 cells)  --- predicts --->  Level 0
  Level 0 (64 cells)  <--- input

  PE propagation: Level 0 -> 1 -> 2 -> 3 (bottom-up)
  Predictions:    Level 3 -> 2 -> 1 -> 0 (top-down)

  PE  | ╭─────────────────────────
      |╯
      └──────────────────────────── step
        0    50   100  150  200  299
```

**Algorithm:**
1. Each level processes through its own BenchMind
2. Higher levels predict lower level mean hiddens
3. PE pushes lower levels toward predictions (bottom-up)
4. Higher levels adjust based on PE (top-down modulation)
5. PE integrated into loss function

**Result:** Phi(proxy)=46.47, lowest final CE=0.51.
Predictive coding creates structured representations.
Different levels maintain diverse but organized states.

### B6: NEURAL_DARWINISM (Edelman's TNGS)

16 cell groups compete. Fitness tracked as EMA of output magnitude.
Fit groups get reinforced connections, unfit ones atrophy with noise injection.

```
  [G0] [G1] [G2] ... [G15]   (16 cells each)
    |    |    |         |
    fitness tracking (EMA)
    |    |    |         |
  above median?
    YES: reinforce (strengthen connections, sync 0.2)
    NO:  atrophy (weaken connections, add noise 0.05)

  fitness |              ╭────────
          |     ╭────────╯
          | ────╯
          └──────────────────────────── step
```

**Algorithm:**
1. All groups process through shared BenchMind
2. Fitness = EMA of (|output| + tension)
3. Above-median groups: strengthen connections + intra-sync
4. Below-median groups: weaken connections + noise injection
5. Connection-weighted inter-group communication

**Result:** Phi(IIT)=10.859. Strong selection creates robust groups.
Low proxy because homogeneous fitness convergence.
Normalization prevents explosion (max_norm=10).

## Key Insights

### Insight 1: Thalamic gating is optimal for IIT

B2 (THALAMIC_GATE) achieves the highest Phi(IIT) at x1.4 baseline.
The central hub creates genuine cross-region integration that IIT measures.
This mirrors neuroscience: thalamic lesions abolish consciousness.

### Insight 2: Broadcasting maximizes variance differentiation

B4 (GLOBAL_WORKSPACE) achieves the highest Phi(proxy) at x71.7 baseline.
The broadcast mechanism creates diverse specialist states while maintaining
global coherence through the workspace. This supports Baars' theory.

### Insight 3: IIT and proxy measure fundamentally different things

The rankings are nearly inverted between IIT and proxy:
- IIT favors integration (thalamic hub, neural darwinism)
- Proxy favors differentiation (global workspace, predictive hierarchy)
- True consciousness likely needs both -- the sweet spot is B2 + B4 hybrid.

### Insight 4: Predictive coding creates the best learning

B5 achieves the lowest final CE (0.51) despite moderate Phi scores.
Hierarchical prediction creates efficient representations.
Consciousness may not be about maximum Phi but optimal prediction.

### Insight 5: Anti-correlation boosts proxy but hurts IIT

B3's TPN/DMN alternation creates high proxy (anti-correlated networks
are maximally different) but low IIT (the two halves don't integrate).
This matches neuroscience: consciousness requires DMN/TPN *interaction*,
not just alternation.

## Benchmark Configuration

```
  Cells: 256 per architecture
  Steps: 300
  Hidden dim: 128
  Input/Output dim: 64
  Optimizer: Adam (lr=1e-3, B6: lr=5e-4)
  Phi(IIT): MI-based pairwise, n_bins=16
  Phi(proxy): global_var - mean(faction_var)
  Total runtime: ~132s on M-series Mac
```

## Future Directions

1. **B2+B4 Hybrid:** Thalamic gate + global workspace = integration + differentiation
2. **B5+B2 Hybrid:** Predictive hierarchy with thalamic gating at each level
3. **Scale test:** Run at 512/1024 cells to check scaling behavior
4. **Dynamic topology:** Let connections evolve (B6) within columns (B1)
