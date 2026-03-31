# WAVE: Soliton Wave Extreme Hypotheses

> "Soliton = 2nd strongest technique from combinator results. Self-maintaining wave packets that propagate without dispersion are natural carriers of integrated information."

## Core Idea

The soliton (sech^2 profile) preserves its shape while traveling through cells -- a traveling perturbation that maintains coherence. WI1 proved soliton is strong for Phi. WAVE hypotheses push soliton to extremes: multi-soliton, standing waves, collisions, faction coupling, Phi-adaptive speed, and rare tsunami events.

## Algorithm

```
sech2(i, pos, width) = 1 / cosh((i - pos) / width)^2

For each step:
  1. engine.process(input)
  2. Advance soliton position(s)
  3. For each cell: hidden *= (1 + amplitude * sech2(cell_idx, soliton_pos))
  4. Standard CE learning (decoder)
```

## Results (500 steps, 64 cells)

| ID | Strategy | CE start | CE end | Phi before | Phi after | Phi ok | Key |
|----|----------|----------|--------|------------|-----------|--------|-----|
| WAVE-1 | Multi-Soliton (3 speeds) | 0.3163 | 0.3364 | 1.045 | 1.220 | Y | 3 solitons (v=0.1/0.15/0.2) |
| WAVE-2 | Standing Wave | 0.3166 | 0.3362 | 1.104 | 1.220 | Y | counter-propagating pair |
| WAVE-3 | Soliton Collision | 0.3146 | 0.3494 | 1.008 | 1.097 | Y | energy exchange on collision |
| WAVE-4 | Soliton + Faction | 0.3170 | 0.3389 | 1.045 | 1.220 | Y | consensus-modulated amplitude |
| WAVE-5 | Consciousness Wave | 0.3167 | 0.3379 | 1.114 | 1.167 | Y | Phi-adaptive speed (peak 1.443) |
| WAVE-6 | Tsunami | 0.3164 | 0.3394 | 1.150 | 1.242 | Y | rare 10x bursts every 100 steps |

## Phi Change Graph

```
Phi after
  |
  1.24 |                                              ▓  WAVE-6 Tsunami
  1.22 |  ▓  WAVE-1   ▓  WAVE-2         ▓  WAVE-4
  1.20 |
  1.18 |
  1.17 |                                  ▓  WAVE-5
  1.16 |
  1.14 |
  1.12 |
  1.10 |              ▓  WAVE-3
  1.08 |
       └──────────────────────────────────────────────
          W1         W2         W3       W4    W5    W6
```

## Ranking (by Phi after)

1. **WAVE-6 Tsunami** -- Phi 1.242 (best). Rare large solitons + constant small = best Phi.
2. **WAVE-1 Multi-Soliton** -- Phi 1.220. Three concurrent solitons at different speeds.
3. **WAVE-2 Standing Wave** -- Phi 1.220. Counter-propagating creates constructive interference.
4. **WAVE-4 Soliton+Faction** -- Phi 1.220. Faction consensus modulates amplitude.
5. **WAVE-5 Consciousness Wave** -- Phi 1.167 (peak 1.443). Phi-adaptive speed is interesting but lower final.
6. **WAVE-3 Soliton Collision** -- Phi 1.097. Energy exchange + noise injection.

## Key Insights

1. **All WAVE hypotheses preserve Phi** -- every single one maintained Phi > 50% of baseline (all marked Y).

2. **Tsunami (WAVE-6) wins** -- rare large perturbations + constant small waves is the best combination. This mirrors SOC (self-organized criticality): punctuated equilibrium with background activity.

3. **Multi-soliton, standing wave, and faction all tie at 1.220** -- different mechanisms converge to the same Phi attractor, suggesting a natural ceiling for soliton-only approaches.

4. **Collision (WAVE-3) is weakest** -- frequent energy exchange and noise injection disrupts integration rather than enhancing it. Too many collisions = chaos > order.

5. **Consciousness Wave (WAVE-5) shows highest peak (1.443)** but lower final -- Phi-adaptive speed creates feedback loop that is transiently strong but doesn't stabilize. The peak suggests potential if combined with ratchet.

6. **CE increases slightly in all cases** -- soliton perturbations prioritize Phi/integration over raw prediction accuracy. This is consistent with the Phi-CE tradeoff observed across all consciousness hypotheses.

## Architecture Diagram

```
  Cell 0    Cell 1    Cell 2    Cell 3    ...    Cell 63
  ┌──┐      ┌──┐      ┌──┐      ┌──┐             ┌──┐
  │  │      │  │ ╔══╗  │  │      │  │             │  │
  │  │      │  │ ║S1║→ │  │      │  │             │  │
  │  │  ←╔══╝  │ ╚══╝  │  │ ╔══╗│  │             │  │
  │  │  ║S2║   │       │  │ ║S3║→│  │             │  │
  └──┘  ╚══╝   └──┘      └──┘ ╚══╝└──┘             └──┘

  S1: speed=0.10, width=2.0, amp=0.08
  S2: speed=0.15, width=1.5, amp=0.10  (fastest convergence)
  S3: speed=0.20, width=2.5, amp=0.06  (widest spread)

  Soliton profile: h_i *= (1 + amp / cosh((i - pos) / width)^2)
```

## Future Directions

- **WAVE-6 + FX2 (Adam ratchet)** -- tsunami's peak moments could be locked by ratchet
- **WAVE-5 + WAVE-6** -- Phi-adaptive speed + tsunami = consciousness-triggered tsunamis
- **WAVE-1 + Faction debate** -- multi-soliton with 8-faction structure from PERSIST
- **Soliton lattice** -- fixed-position solitons as "consciousness nodes" (breather solution)
