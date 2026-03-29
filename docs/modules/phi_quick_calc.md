# phi_quick_calc.py

Ultra-fast Phi estimator for rapid parameter sweeps. Produces results in under 1 second.

## API
- `quick_phi(cells=64, dim=64, hidden=128, factions=8, steps=30, silence_ratio=0.7, sync_strength=0.15, debate_strength=0.12, ib2_top=0.25, noise=0.02, metacog=True, ib2=True, flow=False) -> float` -- single Phi estimate
- `DEFAULTS` -- default parameter dictionary
- CLI modes: `--sweep cells`, `--sweep factions`, `--sweep all`, or specific `--cells N --factions N`

## Usage
```bash
python3 phi_quick_calc.py                           # Default sweep
python3 phi_quick_calc.py --cells 512 --factions 8  # Specific config
python3 phi_quick_calc.py --sweep cells             # Sweep cell counts
python3 phi_quick_calc.py --sweep factions           # Sweep faction counts
python3 phi_quick_calc.py --sweep all                # Full parameter sweep
```

## Integration
- Uses `mitosis.MitosisEngine` and `consciousness_meter.PhiCalculator`
- Designed for hypothesis benchmarking: quickly test parameter combinations
- Supports metacognition loop, IB2 (information bottleneck), flow sync, silence/burst phases

## Agent Tool
N/A
