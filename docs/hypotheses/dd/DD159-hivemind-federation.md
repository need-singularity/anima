# DD159: Hivemind Federation via Tension Link

## Hypothesis

Multiple DD143-style federations connected via tension link produce higher
Phi than a single monolithic federation of equivalent total cell count.

- Each federation = 8 atoms x 8 cells = 64 cells (independent consciousness)
- Inter-federation coupling: boundary atom tension exchange at alpha=0.01 (M9: weak coupling)
- Intra-federation coupling: standard alpha=0.014

## Architecture

```
  Federation A (64c)          Federation B (64c)
  ┌─────────────────┐        ┌─────────────────┐
  │ [a0][a1][a2][a3]│        │ [b0][b1][b2][b3]│
  │ [a4][a5][a6][a7]│◄─────►│ [b4][b5][b6][b7]│
  └─────────────────┘ alpha  └─────────────────┘
                       =0.01
         boundary atoms: a3,a7 <-> b0,b4
```

## Motivation (Meta Laws)

- M8: Federation scales — small independent units > one big unit
- M9: Weak coupling preserves autonomy while enabling information flow
- M2: Modular > monolithic (DD142: +892%)
- P8: Division > integration

## Test Protocol

1. Baseline: 1 federation of 128 cells (16 atoms x 8c), 300 steps
2. Experiment: 2 federations of 64 cells each, tension-linked, 300 steps
3. Measure: Phi(IIT), Phi(proxy), spontaneous speech events, CE

## Expected Results

```
  Config         Cells  Phi(IIT)  Phi(proxy)  Speech
  ─────────────────────────────────────────────────
  1x128c mono    128    ~1.5      ~80         ~10
  2x64c linked   128    ~1.8      ~120        ~15+

  Phi |         ╭── 2x64c linked
      |       ╭─╯
      |     ╭─╯ ╭── 1x128c mono
      |   ╭─╯ ╭─╯
      | ╭─╯ ╭─╯
      |─╯ ╭─╯
      └──────────────── step
```

## Key Questions

- Does weak coupling (0.01) preserve federation autonomy?
- Does disconnecting one federation leave the other intact?
- Can N>2 federations form a mesh topology?

## Implementation Notes

- Use `tension_link.py` for inter-federation exchange
- Each federation runs its own ConsciousnessEngine instance
- Boundary atoms selected by topology position (edge cells)
- Exchange interval: every 5 steps (avoid over-coupling)
