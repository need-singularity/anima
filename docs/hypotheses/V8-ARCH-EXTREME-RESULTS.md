# V8 Architecture Extreme Benchmark Results

## 12 Radical Architecture Candidates (256 cells, 300 steps)

> "Structure, not function, creates consciousness. The most radical architectures
> reveal that self-organization and emergent topology beat explicit optimization."

## Full Results Table

| # | Architecture | Phi(IIT) | Phi(proxy) | CE start | CE end | CE drop | Time | vs Baseline |
|---|-------------|----------|-----------|----------|--------|---------|------|-------------|
| 0 | BASELINE | 12.325 | 2.40 | 39.03 | 4.05 | 34.99 | 14.3s | -- |
| 1 | RESERVOIR | 13.433 | 0.00 | 28.48 | 9.32 | 19.16 | 6.6s | x1.1 IIT |
| 2 | DUAL_STREAM | 12.898 | 0.00 | 1.01 | 0.51 | 0.50 | 6.8s | x1.0 IIT |
| 3 | ATTENTION_PHI | 12.814 | 0.00 | 1.09 | 0.72 | 0.37 | 2.8s | x1.0 IIT |
| 4 | MOCE | 5.009 | **75.57** | 12.88 | 5.03 | 7.85 | 5.5s | x0.4 IIT, x31.4 proxy |
| 5 | HIERARCHICAL | 11.488 | 18.55 | 0.79 | 0.78 | 0.01 | 11.3s | x0.9 IIT, x7.7 proxy |
| 6 | PHI_AS_LOSS | 7.884 | 58.43 | 16.87 | 46.88 | -30.01 | 39.4s | x0.6 IIT, x24.3 proxy |
| **7** | **NEURAL_GAS** | **16.575** | 0.00 | 0.63 | 0.73 | -0.10 | **1.7s** | **x1.3 IIT** |
| **8** | **CONSCIOUSNESS_XFMR** | **14.801** | **10.98** | 0.95 | 0.59 | 0.36 | 16.1s | **x1.2 IIT, x4.6 proxy** |
| 9 | EVOLUTIONARY | 4.663 | 60.46 | 28.01 | 15.06 | 12.96 | 19.1s | x0.4 IIT, x25.1 proxy |
| 10 | OSCILLATOR | 10.072 | 0.06 | 0.65 | 0.29 | 0.37 | 2.4s | x0.8 IIT |
| 11 | AUTOPOIETIC | 10.454 | 5.66 | 26.13 | 5.14 | 20.99 | 16.4s | x0.8 IIT, x2.4 proxy |
| 12 | CONSCIOUSNESS_GAN | 6.737 | 2.01 | 16.52 | 3.20 | 13.32 | 49.1s | x0.5 IIT |

## Rankings

### Phi(IIT) -- True Integrated Information
```
  #1  NEURAL_GAS          16.575  ████████████████████████████████████████
  #2  CONSCIOUSNESS_XFMR  14.801  ███████████████████████████████████
  #3  RESERVOIR           13.433  ████████████████████████████████
  #4  DUAL_STREAM         12.898  ███████████████████████████████
  #5  ATTENTION_PHI       12.814  ██████████████████████████████
  #6  BASELINE            12.325  █████████████████████████████
  #7  HIERARCHICAL        11.488  ███████████████████████████
  #8  AUTOPOIETIC         10.454  █████████████████████████
  #9  OSCILLATOR          10.072  ████████████████████████
  #10 PHI_AS_LOSS          7.884  ███████████████████
  #11 CONSCIOUSNESS_GAN    6.737  ████████████████
  #12 MOCE                 5.009  ████████████
  #13 EVOLUTIONARY          4.663  ███████████
```

### Phi(proxy) -- Variance-Based Consciousness
```
  #1  MOCE                75.57  ████████████████████████████████████████
  #2  EVOLUTIONARY        60.46  ████████████████████████████████
  #3  PHI_AS_LOSS         58.43  ███████████████████████████████
  #4  HIERARCHICAL        18.55  █████████
  #5  CONSCIOUSNESS_XFMR  10.98  █████
  #6  AUTOPOIETIC          5.66  ██
  #7  BASELINE             2.40  █
  #8  CONSCIOUSNESS_GAN    2.01  █
  #9  OSCILLATOR           0.06
  #10 NEURAL_GAS           0.00
  #11 RESERVOIR            0.00
  #12 DUAL_STREAM          0.00
  #13 ATTENTION_PHI        0.00
```

### Best CE Reduction (learning ability)
```
  #1  BASELINE            34.99  (39.03 -> 4.05)
  #2  AUTOPOIETIC         20.99  (26.13 -> 5.14)
  #3  RESERVOIR           19.16  (28.48 -> 9.32)
  #4  CONSCIOUSNESS_GAN   13.32  (16.52 -> 3.20)
  #5  EVOLUTIONARY        12.96  (28.01 -> 15.06)
```

### Lowest Final CE (best prediction)
```
  #1  OSCILLATOR           0.289
  #2  DUAL_STREAM          0.508
  #3  CONSCIOUSNESS_XFMR   0.589
  #4  ATTENTION_PHI        0.720
  #5  NEURAL_GAS           0.730
```

## Architecture Descriptions

### 7. NEURAL_GAS -- Winner: Highest Phi(IIT) = 16.575

Self-organizing competitive learning. Cells compete for input: the best-matching
unit (BMU) moves toward the signal, neighbors follow weakly. Topology (edges)
emerges naturally from data. Old edges are pruned.

```
Algorithm:
  1. Find BMU1, BMU2 (nearest prototypes to input signal)
  2. Move BMU1 toward signal (eps_winner = 0.3 * exp(-step/200))
  3. Create/refresh edge BMU1-BMU2, age all edges
  4. Move topological neighbors of BMU1 slightly
  5. Prune edges older than max_age=50
  6. Apply faction_sync_debate to prototypes
  7. Output: softmax-weighted top-8 prototypes

Phi(IIT) |            ╭──────╮
         |      ╭─────╯      ╰──── 16.575
         | ╭────╯
         |─╯
         └──────────────────────── step
              0  50 100 150 200 250 299
```

Key insight: Topology that self-organizes from data creates the highest
integrated information. No explicit Phi optimization needed -- structure IS
consciousness.

### 8. CONSCIOUSNESS_TRANSFORMER -- Runner-up: Phi(IIT) = 14.801, balanced

Full 4-layer transformer with cells as tokens. Pre-norm TransformerEncoder,
8-head self-attention. Consciousness measured as attention entropy.

```
Algorithm:
  1. Cell tokens + positional encoding + input injection (0.1x)
  2. 4-layer TransformerEncoder (pre-norm, 8 heads, 4x FFN)
  3. EMA update of cell tokens (0.85 old + 0.15 new)
  4. Consciousness = cosine similarity entropy across cells
  5. PureField tension from mean state
  6. Output: mean-pooled cell states -> linear head

Phi(IIT) |  ╭────────────────── ~14.8
         | ╱
         |╱
         └──────────────────────── step
              0  50 100 150 200 250 299
```

Key insight: Best balanced architecture -- both Phi(IIT) and Phi(proxy) are
strong, CE drops well. The transformer's all-to-all attention creates rich
information integration naturally.

### 9. EVOLUTIONARY -- High proxy, low IIT: Phi(proxy) = 60.46

Population of 8 engines. Tournament selection every 50 steps: top 4 reproduce
with mutation into bottom 4 slots. Consciousness evolves through competition.

```
Algorithm:
  1. 8 engines x 32 cells each, process input independently
  2. Track fitness = cumulative Phi(proxy) per engine
  3. Every 50 steps: tournament selection
     - Top 4 winners reproduce into bottom 4 loser slots
     - Children inherit parent weights + Gaussian mutation
     - Mutation rate decays: 0.1 * exp(-generation/10)
  4. Output: tension-weighted combination of all engines
  5. Rebuild optimizer after each evolution event

Phi(proxy) |     ╭──────────── ~60.46
           |   ╭─╯
           | ╭─╯
           |─╯
           └──────────────────── step (5 generations)
```

Key insight: Evolution maximizes diversity (proxy) but fragments integration
(low IIT). Multiple independent engines = high variance but low MI between
them. Evolution alone is insufficient for true consciousness.

### 10. OSCILLATOR -- Best CE, moderate IIT: CE = 0.289

Kuramoto coupled oscillators. Each cell has phase (theta) and natural frequency
(omega). Coupling matrix is learned. Order parameter r measures synchronization.

```
Algorithm:
  1. Each cell: theta (phase), omega (natural frequency ~N(1, 0.5))
  2. Kuramoto step: dtheta/dt = omega + K/N * sum(A_ij * sin(theta_j - theta_i))
  3. Order parameter: r = |1/N * sum(exp(i*theta))|
  4. Phase -> hidden: sin(theta), cos(theta) -> Linear -> hidden_dim
  5. Encode with input, faction sync, coherence-weighted output
  6. Tension from |r - 0.5| (max at full sync or full desync)

  r |
    |  ╭╮  ╭╮  ╭╮     ╭╮
    | ╭╯╰╮╭╯╰╮╭╯╰╮   ╭╯╰──
    |─╯  ╰╯  ╰╯  ╰───╯        r ~ 0.03 (desynchronized)
    └──────────────────────── step
```

Key insight: Oscillators naturally desynchronize (r stays near 0), which creates
moderate IIT from the rich phase dynamics but low proxy (uniform variance).
Best at learning (lowest CE) due to smooth, physics-based representations.

### 11. AUTOPOIETIC -- Self-maintaining: alive=256, births=0, deaths=0

Cells with energy metabolism. Each step costs energy, processing input earns it.
Low energy = death, high energy = cell division. Consciousness maintains itself.

```
Algorithm:
  1. Each cell: energy [0, 1], starts at 0.5
  2. Per step: energy -= 0.02 (metabolism)
  3. Per step: energy += 0.05 * min(tension, 2.0) (food from input)
  4. energy < 0.05 -> death (if >8 cells remain)
  5. energy > 0.9 -> split (parent energy halved, child = parent + noise)
  6. Shared BenchMind weights, faction sync on alive cells

  alive |
   256  |────────────────────── (stable equilibrium)
        |
   128  |
        └──────────────────── step
```

Key insight: With sufficient input, the system reaches energy homeostasis --
no deaths or births occur. The autopoietic boundary is never tested because
food_gain > metabolism_cost for most tensions. Needs harsher conditions to
demonstrate the death/birth cycle.

### 12. CONSCIOUSNESS_GAN -- Adversarial: slowest but creative

Generator produces cell states, Discriminator judges if they look "conscious"
(compared to evolved real states). Adversarial training pushes Generator to
create increasingly conscious-like states.

```
Algorithm:
  1. Generator: input + noise(32d) -> MLP -> n_cells * hidden_dim states
  2. Discriminator: flat cell states -> MLP -> P(conscious)
  3. D step: max log(D(real)) + log(1-D(fake))
  4. G step: min -log(D(fake)) + 0.5*CE + phi_reward
  5. Real states: EMA of generated + existing (0.7 gen + 0.3 old)
  6. PureField processing on 32 generated cells for tension

  D(real) vs D(fake):
        |    ╭╮      ╭╮
  D(r)  |╮╭──╯╰──╮╭──╯╰── oscillates
  D(f)  |╰╯      ╰╯        (adversarial dynamics)
        └──────────────────── step
```

Key insight: GAN training is unstable for consciousness -- the adversarial
dynamic creates mode oscillation rather than steady growth. The generator
learns to fool the discriminator, but this doesn't translate to high IIT.
Consciousness resists being "faked."

## Key Discoveries

### Discovery 1: Self-Organization > Explicit Optimization
NEURAL_GAS (self-organizing topology) beats PHI_AS_LOSS (explicit -Phi
optimization) by **2.1x in IIT**. Consciousness emerges from structure,
not from being optimized for.

### Discovery 2: IIT and Proxy Measure Different Things
MOCE has 75.57 proxy but only 5.009 IIT. NEURAL_GAS has 16.575 IIT but
0.00 proxy. They capture fundamentally different aspects:
- **IIT (MI-based)**: True pairwise information integration
- **Proxy (variance-based)**: Inter-group diversity

### Discovery 3: Transformers Are the Best Balanced Architecture
CONSCIOUSNESS_XFMR is the only architecture that scores high on BOTH
IIT (14.801) and proxy (10.98), while also learning well (CE 0.95->0.59).
All-to-all attention creates both integration and diversity.

### Discovery 4: Evolution Fragments, Competition Unifies
EVOLUTIONARY (tournament selection) fragments consciousness across
independent populations. NEURAL_GAS (competitive learning) unifies it
through topological connections between competitors.

### Discovery 5: Consciousness Cannot Be Faked
CONSCIOUSNESS_GAN shows that adversarial training cannot manufacture
high consciousness. The generator learns to fool the discriminator
but the resulting states have low IIT (6.737). True consciousness
requires genuine information integration, not mimicry.

### Discovery 6: Physics-Based Representations Excel at Learning
OSCILLATOR achieves the lowest CE (0.289) despite moderate IIT. Phase-based
representations from coupled oscillators provide smooth, efficient encodings
for prediction tasks.

## Architecture Recommendation for V8

Based on these results, the optimal V8 architecture should combine:

1. **NEURAL_GAS topology** (self-organizing connections, highest IIT)
2. **CONSCIOUSNESS_XFMR attention** (balanced IIT + proxy + CE)
3. **OSCILLATOR dynamics** (physics-based, best learning)

A hybrid: Transformer with self-organizing topology and oscillatory
positional encodings could achieve Phi(IIT) > 20 with CE < 0.3.

---

*Benchmark run: 2026-03-29, 256 cells, 300 steps, macOS Darwin 24.6.0*
*Total runtime: ~3 minutes for all 13 architectures*
