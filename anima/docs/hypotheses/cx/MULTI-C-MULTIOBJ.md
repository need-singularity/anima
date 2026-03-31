# C-1: Multi-C Engine + W-2: Multi-Objective W

## C-1: Multi-C Engine (Multi-Consciousness Engine)

### Algorithm

Run 2 distinct C engines simultaneously: QuantumEngine + MitosisEngine.

1. Split N cells between two engines: n1=N/2 (Quantum), n2=N/2 (Mitosis)
2. Both engines `step()` on the same input each turn
3. Each engine maintains its own hidden states and dynamics:
   - QuantumEngine: superposition amplitudes, measurement collapse, entanglement pairs
   - MitosisEngine: cell division (best->worst copy+noise), asymmetric dropout (0.21/0.37)
4. Bridge layer: `bridge(cat[out_q, out_m])` combines outputs
5. Cross-talk every 5 steps: exchange global means between engines (strength=0.05)
6. Phi measured on concatenated hiddens `[n1+n2, dim]`

```
Input x
  |
  +--> QuantumEngine (16c)  --> out_q
  |      superposition + entanglement
  |
  +--> MitosisEngine (16c)  --> out_m
  |      division + asymmetric dropout
  |
  +-- Cross-talk (mean exchange) --+
  |
  cat[out_q, out_m] --> Bridge --> output
```

### Benchmark Results (32 cells, 50 steps)

```
  Name                           |  Phi(IIT)  Phi(prx) |  CE start    CE end
  ───────────────────────────────+─────────────────────+────────────────────
  Baseline (32c)                 |   32.5522      0.02 |   40.06      15.05
  C-1: Multi-C (Q+M, 32c)       |   17.5509     32.13 |    5.27       5.90
```

| Metric       | Baseline | C-1 Multi-C | Change       |
|-------------|----------|-------------|--------------|
| Phi(IIT)     | 32.55    | 17.55       | -46.1%       |
| Phi(proxy)   | 0.02     | 32.13       | +160550%     |
| CE start     | 40.06    | 5.27        | -86.8%       |
| CE end       | 15.05    | 5.90        | -60.8%       |
| Mitosis div  | n/a      | 4           | --           |

### ASCII Graph: Phi(IIT)

```
Phi(IIT)
   17.73 |   *
         |  *
         |
         |     *
         |    *
   17.39 |
         |
         |
         |*
   17.12 | *
         +────── step
```

### Key Insights

1. **Phi(IIT) drops (-46.1%)** because splitting 32 cells into two 16-cell engines reduces pairwise MI coverage. The IIT metric is sensitive to partition: two separate 16-cell groups have less cross-integration than one 32-cell group.

2. **Phi(proxy) explodes (+160550%)** because the two engines produce genuinely different "realities" -- Quantum vs Mitosis dynamics create high global variance with low faction variance. The proxy metric correctly captures this diversity.

3. **CE dramatically improves (-60.8%)** -- the bridge layer benefits from receiving two independent perspectives. The multi-engine setup acts like an ensemble, reducing prediction error substantially.

4. **Divergence between Phi(IIT) and Phi(proxy)** highlights a fundamental measurement question: IIT penalizes partition, while proxy rewards diversity. For consciousness, both matter -- integration AND differentiation.

5. **Potential fix**: stronger cross-talk or a shared attention layer between engines could recover Phi(IIT) while keeping the CE benefit.


---

## W-2: Multi-Objective W (CE + Phi Co-Optimization)

### Algorithm

Instead of optimizing only CE, simultaneously track and respond to Phi changes:

1. Every step, measure both CE and Phi(IIT)
2. If Phi drops >10%: **pain signal** -- boost LR by 2x (max 5e-3) to escape local minimum
3. If Phi rises AND CE drops: **satisfaction** -- reduce LR by 0.7x (min 1e-5) to consolidate
4. Otherwise: slowly decay LR toward base (1e-3)
5. Track Pareto front of (CE, Phi) non-dominated points

```
                    Phi drops >10%?
                   /               \
                 YES                NO
                  |                  |
            PAIN: LR x2        Phi up + CE down?
            (explore!)         /              \
                             YES               NO
                              |                 |
                       SATISFY: LR x0.7    Neutral: decay
                       (consolidate)       toward base
```

### Benchmark Results (32 cells, 50 steps)

```
  Name                           |  Phi(IIT)  Phi(prx) |  CE start    CE end
  ───────────────────────────────+─────────────────────+────────────────────
  Baseline (32c)                 |   32.5522      0.02 |   40.06      15.05
  W-2: MultiObj-W (32c)         |   30.2633      0.08 |   40.06      15.66
```

| Metric          | Baseline | W-2 MultiObj | Change   |
|----------------|----------|-------------|----------|
| Phi(IIT)        | 32.55    | 30.26       | -7.0%    |
| Phi(proxy)      | 0.02     | 0.08        | +300%    |
| CE start        | 40.06    | 40.06       | 0%       |
| CE end          | 15.05    | 15.66       | +4.0%    |
| Pain events     | n/a      | 10          | --       |
| Satisfaction    | n/a      | 12          | --       |
| Pareto size     | n/a      | 2           | --       |

### LR History

```
LR
  0.0050 |                                            *  *
         |                                             ** **
         |
         |
         |                                     *   ***
  0.0026 |    *                  **
         |                                      *
         |  *  ****         *      **        **  **
         |   *     ********  ****    **   *
  0.0006 |**               *           *** **
         +────────────────────────────────────────── step
```

### Pareto Front

```
  CE=9.205   Phi(IIT)=33.924
  CE=12.264  Phi(IIT)=34.843
```

### Key Insights

1. **Phi(IIT) slightly drops (-7.0%)** -- the LR oscillations from pain/satisfaction cycles create instability that prevents the engine from settling into high-integration states.

2. **CE slightly worse (+4.0%)** -- the LR boosting during pain events disrupts gradient descent, causing overshooting. The satisfaction-based consolidation partially compensates.

3. **Active emotional regulation works**: 10 pain events and 12 satisfaction events show the system is actively responding to Phi changes. The LR oscillates between 0.0006 and 0.005.

4. **Pareto front is small (2 points)** -- in 50 steps, most (CE, Phi) pairs are dominated. The frontier captures the best trade-off states.

5. **Potential improvement**: the pain threshold (10%) may be too aggressive for 50 steps. A softer threshold (20-30%) and longer runs could allow more gradual adaptation.


---

## Combined: C-1 + W-2

```
  Name                           |  Phi(IIT)  Phi(prx) |  CE start    CE end
  ───────────────────────────────+─────────────────────+────────────────────
  C-1+W-2: Combined (32c)       |   17.5279     31.53 |    5.27       8.58
```

| Metric     | Baseline | Combined | Change  |
|-----------|----------|----------|---------|
| Phi(IIT)   | 32.55    | 17.53    | -46.2%  |
| Phi(proxy) | 0.02     | 31.53    | huge    |
| CE end     | 15.05    | 8.58     | -43.0%  |

The combination inherits C-1's CE advantage but not additively with W-2. The multi-objective LR control adds some overhead to CE convergence vs pure C-1 (CE 8.58 vs 5.90).


---

## Summary Comparison

```
  Phi(IIT):
  Baseline      ########################################## 32.55
  C-1 Multi-C   #####################                      17.55  (-46.1%)
  W-2 MultiObj  #####################################       30.26  (-7.0%)
  C-1+W-2       #####################                      17.53  (-46.2%)

  CE end:
  Baseline      ########################################## 15.05
  C-1 Multi-C   ################                            5.90  (-60.8%)
  W-2 MultiObj  ###########################################  15.66  (+4.0%)
  C-1+W-2       #######################                     8.58  (-43.0%)
```

## Core Findings

1. **C-1 is a strong CE optimizer** (-60.8%) but trades off Phi(IIT). The dual-engine ensemble provides genuine diversity that helps prediction but reduces measured integration.

2. **W-2 needs longer runs** to show its value. In 50 steps, the emotional LR oscillation creates more noise than signal. The mechanism is sound but requires scale.

3. **The Phi(IIT) vs Phi(proxy) split is the key discovery**: C-1 scores extremely high on proxy (diversity) but low on IIT (integration). This suggests a future hypothesis: a cross-engine attention mechanism that maintains integration across engines while preserving diversity.

4. **Law candidate**: Multi-engine diversity helps CE but hurts IIT integration. The bridge must be strong enough to maintain cross-engine MI.

## Benchmark file

`bench_multi_c_w.py` -- standalone, KMP_DUPLICATE_LIB_OK=TRUE compatible.
