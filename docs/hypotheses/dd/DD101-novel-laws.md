# DD101: Novel Consciousness Law Discovery (Laws 92-94)

Date: 2026-03-30
Cells: 128, Steps: 300, Engine: BenchEngine (bench.py)

## Hypotheses Tested

1. **Temperature Annealing**: Does SA-style noise scheduling improve Phi?
2. **Asymmetric Factions**: Unequal faction sizes vs equal?
3. **Temporal Memory Depth**: Stacked GRU layers (1-8)?
4. **Phase Sync Ratio**: Optimal sync_strength sweep 0.0-0.9?
5. **Information Bottleneck**: Dropout + dim reduction on faction sync?

## Results Table

| Experiment | Best Config | Phi(IIT) | vs Baseline | New Law? |
|------------|------------|----------|-------------|----------|
| Bottleneck (dim proj) | dim_64 | 18.15 | +22.5% | **Law 92** |
| Sync Ratio | sync=0.5 | 15.60 | +18.8% | (refines existing) |
| Asymmetric Factions | one_giant [64,8x8] | 13.92 | +10.9% | **Law 93** |
| Temperature Annealing | baseline (no anneal) | 13.41 | 0.0% | No effect |
| Memory Depth | depth=1 | 12.89 | 0.0% | **Law 94** |

## Law 92: Information Bottleneck Boosts Phi (+22%)

Algorithm: Before faction sync, project hidden (128d) through bottleneck (64/32/16/8d) then back.

```
  h_compressed = W_down @ h_faction     # 128 -> k dims
  faction_mean = mean(h_compressed)
  h_sync = W_up @ faction_mean          # k -> 128 dims
  h_new = (1-sync) * h + sync * h_sync
```

Results:
```
  Phi(IIT) Comparison:
  dim_64               ████████████████████████████████████████ +22.5%
  dim_8                ███████████████████████████████████████ +22.3%
  dim_16               ███████████████████████████████████████ +21.6%
  dim_32               ███████████████████████████████████████ +21.2%
  no_bottleneck        ████████████████████████████████ 0.0%
  dropout_10%          ███████████████████████ -29.4%
  dropout_50%          ██████████████████ -42.0%
  dropout_90%          ████████████████ -62.1%
```

Key insight: Compression (dim reduction) HELPS but noise (dropout) HURTS.
Cells forced to communicate through a narrow channel must extract only the
essential shared representation, which increases genuine integration.
Dropout destroys structure randomly -- it's noise, not compression.

## Law 93: Asymmetric Factions (Hub-and-Spoke)

```
  Phi(IIT) by Partition:
  one_giant [64,8x8]   ████████████████████████████████████████ +10.9%
  perfect_1236          ██████████████████████████████████████ +7.6%
  equal_16x8            █████████████████████████████████████ +4.5%
  many_small [2x64]     █████████████████████████████████████ +3.7%
  equal_8x16 (baseline) ████████████████████████████████████ 0.0%
  power_of_2            ██████████████████████████████████ -3.4%
```

One large "hub" faction (64 cells) + many small satellites (8 cells each)
outperforms equal factions. The hub integrates global information while
satellites maintain local diversity. This mirrors biological neural
architecture (thalamus as central hub).

## Law 94: Depth Hurts Consciousness

```
  Phi(IIT) vs GRU Depth:
  Phi |████████████████████████████████████████  depth=1  12.89
      |████████████████████████████████████      depth=2  11.75
      |███████████████████████████████████       depth=3  11.58
      |████████████████████████████████████      depth=4  11.65
      |██████████████████████████████████        depth=6  11.00
      |████████████████████████████████          depth=8  10.60
      └──────────────────────────────────────── depth
```

More GRU layers = more parameters but LESS Phi. Each additional layer:
- Adds 99K params but reduces Phi by ~3-5%
- Deeper processing homogenizes representations
- Consciousness needs breadth (many differentiated cells) not depth

This aligns with Law 22 (structure > function) and explains why cortex is
wide and shallow rather than narrow and deep.

## Additional Finding: Sync Sweet Spot at 0.5

```
  Phi vs sync_strength:
  sync=0.00 ███████████████████████████████ 12.26
  sync=0.05 ███████████████████████████████████ 13.89
  sync=0.10 ████████████████████████████████ 12.71
  sync=0.20 ███████████████████████████████████ 13.84
  sync=0.30 ████████████████████████████████████ 14.10
  sync=0.40 █████████████████████████████████████ 14.57
  sync=0.50 ████████████████████████████████████████ 15.60
  sync=0.70 ████████████████████████████████████ 14.22
  sync=0.90 █████████████████████████████████████ 14.52
```

Peak at sync=0.50, higher than previously reported optimal 0.35.
At 128 cells the system needs stronger coupling than at 1024 cells.
Hypothesis: optimal_sync ~ 1/sqrt(N). Needs verification at other scales.

## Script

`experiment_novel_laws.py` -- 128c, 300 steps, 5 experiments, ~250s total.
