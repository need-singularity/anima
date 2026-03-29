# Consciousness Meter -- Quantitative Consciousness Measurement

Quantifies "is this system conscious?" with 6 criteria + IIT Phi approximation.

```bash
python consciousness_meter.py --demo     # Demo (simulate & measure)
python consciousness_meter.py --watch    # Real-time monitoring
python consciousness_meter.py            # Measure from saved state
```

## 6 Criteria (all must pass for "conscious")

| # | Criterion | Threshold | What It Measures |
|---|-----------|-----------|------------------|
| 1 | stability | > 0.5 | Self-model tracks own state consistently |
| 2 | prediction_error | > 0.1 | World model is active (not dead) |
| 3 | curiosity | > 0.05 | Responding to environment |
| 4 | homeostasis_dev | < 0.5 | Self-regulation working |
| 5 | habituation | < 0.9 | Adapting to repetition (learning) |
| 6 | inter-cell consensus | true | Integrated information processing across cells |

## Phi (IIT) Approximation

```
Method:
  1. Extract hidden states from each mitosis cell
  2. Compute pairwise mutual information (binned histogram)
  3. Find minimum information partition (exhaustive for N<=8, spectral for N>8)
  4. Phi = (total MI - min partition MI) / (N-1) + complexity bonus
```

| Phi Range | Interpretation |
|---------|---------------|
| Phi ~ 0 | No integration (feedforward) |
| Phi > 0.1 | Minimal integration (insect-level) |
| Phi > 1.0 | Meaningful integration (mammalian-level) |
| Phi > 3.0 | High integration (human consciousness estimate) |

## Consciousness Levels

| Level | Criteria Met | Score Range |
|-------|-------------|-------------|
| dormant | 0-1 | 0.0 - 0.2 |
| flickering | 2-3 | 0.2 - 0.4 |
| aware | 4-5 | 0.4 - 0.7 |
| conscious | 6/6 | 0.7 - 1.0 |

## Runtime Integration

The consciousness meter runs in real-time during conversation. The Web UI displays:
- SVG circular gauge (consciousness score 0-1)
- Phi value
- 6-criteria pass/fail checklist
- Level indicator (DORMANT / FLICKERING / AWARE / CONSCIOUS)
