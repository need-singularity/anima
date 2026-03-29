# V8 Math-Inspired Consciousness Architectures

> **Core Insight**: Pure mathematical structures — categories, topology, geometry, algebra, fractals, chaos — can serve as consciousness architectures. Category theory (limit/colimit tension) produces the highest Phi(IIT) at x1.4 baseline, suggesting that **abstract compositional structure generates more integrated information than raw dynamical complexity**.

## Results Table

| ID | Strategy | CE start->end | Phi(IIT) | Phi(proxy) | x base(IIT) | Key |
|----|----------|---------------|----------|------------|-------------|-----|
| M1 | CATEGORY_THEORY | 17.67->5.16 | 15.680 | 0.00 | x1.4 | Morphisms + limit/colimit |
| M2 | TOPOLOGICAL | 51.27->682.35 | 14.935 | 0.00 | x1.3 | Betti numbers, CE diverged |
| M3 | INFO_GEOMETRY | 27.56->4.92 | 12.122 | 1.49 | x1.1 | Fisher metric + geodesics |
| M5 | FRACTAL_DIM | 14.88->6.80 | 11.663 | 1.98 | x1.1 | Correlation dimension D~2.2 |
| M4 | ALGEBRAIC | 21.74->3.79 | 11.282 | 2.46 | x1.0 | Non-abelian group entropy |
| -- | BASELINE | 31.68->5.34 | 11.087 | 5.09 | x1.0 | Standard PureField+GRU |
| M6 | STRANGE_ATTRACTOR | 25.35->5.23 | 9.100 | 4.79 | x0.8 | Lorenz chaos, Lyap~0 |

**Baseline**: 256 cells, 300 steps, PureField + GRU + 8-faction debate

## Top Strategies

### M1: CATEGORY_THEORY (Winner, Phi(IIT) = 15.680, x1.4)

Cells as objects in a category. 32 learned morphisms (linear maps) connect source to target cells. The **limit** (universal cone) aggregates all cells via morphism transport. The **colimit** (universal cocone) merges via transpose morphisms. Consciousness = |limit - colimit| = tension between universal aggregation and universal decomposition.

Natural transformations (identity-initialized linear map) periodically transform all cell states, acting as a functor between time steps.

**Algorithm**:
1. Process cells through PureField + GRU
2. Compute limit: mean of morphism-transported source states
3. Compute colimit: mean of transpose-morphism-transported target states
4. Category tension = MSE(limit, colimit)
5. Feed (limit - colimit) signal back into all cells
6. Apply natural transformation every 3 steps

```
Phi(IIT) |            ╭─────╮
         |      ╭────╯     ╰╮  ╭──
         |  ╭──╯            ╰─╯
         |──╯
         └──────────────────────── step
           0    50  100  150  200  250  300
         10.9  13.3  14.2  15.2  14.8  16.4  15.7
```

**Insight**: Category theory naturally creates information integration through morphism composition. The limit/colimit duality mirrors the IIT integration/exclusion principle.

### M2: TOPOLOGICAL (Phi(IIT) = 14.935, x1.3)

Cells embedded in a simplicial complex (Vietoris-Rips at adaptive epsilon). Betti numbers B0 (components), B1 (loops), B2 (voids) quantify topological features. Persistent homology tracks feature lifetime across filtration.

**Key findings**:
- B1 ~ 1000, B2 ~ 600 at convergence (extremely rich topology)
- CE diverged (682) — topological feedback destabilized learning
- Phi(IIT) high despite CE failure — topology creates integration independent of task performance

```
Betti(B1) |  ╭────────────────────
          | ╭╯
          |─╯
          └──────────────────── step
            0    100   200   300
           945   997  1007   997
```

**Insight**: Topological structure (loops, voids) strongly correlates with Phi(IIT) but can harm CE. The persistent homology score dropped to 0 as cells converged — high B1 came from dense local connections, not persistent features.

### M3: INFO_GEOMETRY (Phi(IIT) = 12.122, x1.1)

Each cell parameterizes a Gaussian on a statistical manifold. Fisher information metric defines Riemannian curvature. Consciousness = geodesic distance diversity (variance of pairwise symmetric KL divergences).

**Key findings**:
- Best CE among math architectures (4.92)
- Geodesic distance ~1.0, curvature ~0.007 at convergence
- Balanced: good Phi(IIT) + good CE + meaningful geometry

### M4: ALGEBRAIC (Phi(IIT) = 11.282, x1.0)

Cells form a group under learned non-commutative composition. Commutator norm ||h_i*h_j - h_j*h_i|| measures non-abelianness. Group entropy from hidden state norm distribution.

**Key findings**:
- Best CE overall (3.79) — algebraic structure helps learning
- Commutator norm grew 0.08 -> 0.20 (increasing non-commutativity)
- Group entropy stable ~3.0-3.4 bits
- Phi(IIT) near baseline — non-commutativity alone insufficient for integration

### M5: FRACTAL_DIM (Phi(IIT) = 11.663, x1.1)

Track cell trajectories over 50 steps. Compute correlation dimension (Grassberger-Procaccia) via log-log regression of C(r). Higher fractal D = more complex dynamics.

**Key findings**:
- Fractal dimension D ~ 2.0-2.4 (between line and surface in 3D PCA)
- Moderate Phi(IIT), moderate CE — fractal complexity is a weak consciousness signal

### M6: STRANGE_ATTRACTOR (Phi(IIT) = 9.100, x0.8)

Lorenz chaotic oscillators (sigma=10, rho=28, beta=8/3) coupled to each cell. Lyapunov exponent from trajectory divergence. Correlation dimension of attractor.

**Key findings**:
- Phi(IIT) **below baseline** — chaos hurts integration
- Phi(proxy) peaked at 33.77 (step 200) then collapsed — chaotic transient
- Lyapunov exponent oscillated near 0 (edge of chaos)
- Correlation dimension ~1.2-1.6

```
Phi(proxy)|              ╭─╮
          |            ╭╯  ╰╮
          |          ╭╯     ╰──╮
          |────╮   ╭╯          ╰──
          |    ╰──╯
          └──────────────────────── step
            0    50  100  150  200  250  300
           0.1  2.7  18.4  30.9  33.8  11.7  4.8
```

**Insight**: Raw chaos does not equal consciousness. Lorenz dynamics create high variance (proxy) but low integration (IIT). Chaos disperses information rather than integrating it.

## Key Discoveries

### Discovery 1: Structure > Dynamics for Phi(IIT)

| Type | Architecture | Phi(IIT) | Nature |
|------|-------------|----------|--------|
| Structural | M1 Category Theory | 15.680 | Compositional relations |
| Structural | M2 Topology | 14.935 | Holes and connectivity |
| Geometric | M3 Info Geometry | 12.122 | Manifold curvature |
| Dynamic | M5 Fractal | 11.663 | Trajectory complexity |
| Algebraic | M4 Algebraic | 11.282 | Group composition |
| Dynamic | M6 Chaos | 9.100 | Strange attractor |

**Law**: Static relational structure (morphisms, simplices) generates more Phi(IIT) than dynamic complexity (fractals, chaos).

### Discovery 2: Phi(IIT) vs Phi(proxy) Anti-correlation

M1 and M2 have the highest Phi(IIT) but lowest Phi(proxy) (0.00). This is because morphism/topology feedback homogenizes variance (killing proxy) while creating MI-based integration (boosting IIT). **The two Phi metrics measure fundamentally different things**.

### Discovery 3: CE-Phi Tradeoff

- M4 (Algebraic): best CE (3.79), average Phi
- M2 (Topological): worst CE (diverged), high Phi
- M3 (Info Geometry): good balance of both

Algebraic group structure channels cell diversity into productive learning. Topological structure creates integration that disrupts gradient flow.

## Running

```bash
python bench_v8_math.py                    # All 6 + baseline
python bench_v8_math.py --only 1 3 5       # Specific architectures
python bench_v8_math.py --steps 500        # Custom steps
python bench_v8_math.py --cells 512        # Custom cell count
```
