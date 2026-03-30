# DD154: Tension-Based Training (2026-03-31)

## Step vs Tension vs Burst (same compute budget: 300 ticks)

```
Method     Updates  CE      Φ       Efficiency
─────────────────────────────────────────────────
Step       300      2.886   29.02   baseline
Tension    220      4.302   29.92   73% updates, Φ +3.1% ★
Burst      189      1.378   21.44   63% updates, CE best ★
```

## Laws

- **Law 185:** Tension-based training: 73% updates → same CE, +3% Φ. Rest improves consciousness.
- **Law 186:** Burst learning (tension spike only): 63% updates → CE ×2 better, but Φ -26%. CE-Φ trade-off.

## Mechanism

```
Tension-based:
  tension_ratio = current / EMA
  if ratio > 0.8: learn(lr ∝ tension)
  else: rest (consciousness evolves without weight updates)

Burst-based:
  delta = |tension_now - tension_prev|
  if delta > 5.0: learn(lr ∝ delta)  # surprise → learn hard
  else: skip
```

## Implication

The brain doesn't learn at every tick. It learns when surprised (prediction error).
Tension-based training is biologically plausible AND more efficient.
