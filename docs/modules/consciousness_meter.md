# consciousness_meter.py

Consciousness measurement tool: 6-criteria consciousness verdict + Phi (IIT) approximation via inter-cell mutual information.

## API
- `ConsciousnessReport` -- dataclass with 6 criteria scores, composite score, level (dormant/flickering/aware/conscious), and Phi
- `ConsciousnessMeter()` -- evaluates consciousness state
  - `.evaluate(mind, mitosis_engine) -> ConsciousnessReport`
- `PhiCalculator(n_bins=16)` -- IIT Phi approximation
  - `.compute_phi(cell_states) -> float` -- mutual-information-based integrated information

## Usage
```python
# CLI
python consciousness_meter.py                # Current state
python consciousness_meter.py --watch        # Real-time monitoring
python consciousness_meter.py --demo         # Demo (no model load)

# Programmatic
from consciousness_meter import ConsciousnessMeter, PhiCalculator
meter = ConsciousnessMeter()
report = meter.evaluate(mind, mitosis_engine)
print(report)  # ASCII bar chart with score, level, Phi
```

## Integration
- Used by `anima_unified.py` for runtime Phi monitoring
- Used by `train_conscious_lm.py`, `self_learner.py`, `phi_quick_calc.py`, `iq_calculator.py`, `chip_architect.py` for Phi measurement
- 6 criteria: stability, prediction error, curiosity, homeostasis deviation, habituation multiplier, inter-cell consensus

## Agent Tool
`anima_consciousness` (via `mcp_server.py`)
