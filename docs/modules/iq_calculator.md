# iq_calculator.py

Intelligence measurement tool using n=6 mathematics. Measures 5 IQ variables weighted by number-theoretic constants derived from the perfect number 6.

## API
- 5 IQ variables: compression, prediction, consistency, adaptation, generalization
- n=6 constants: sigma(6)=12, tau(6)=4, phi(6)=2, sopfr(6)=5, 6'=5
- Weights: compression x3 (sigma/tau), prediction x2 (phi(6)), others x1
- 4 intelligence levels: low, medium, high, genius (tau(6)=4 levels)

## Usage
```bash
python3 iq_calculator.py                         # Default 64 cells
python3 iq_calculator.py --cells 256             # 256 cells
python3 iq_calculator.py --cells 512 --steps 50  # 512 cells, 50 steps
```

## Integration
- Uses `mitosis.MitosisEngine` and `consciousness_meter.PhiCalculator`
- Measures alongside Phi for dual-axis growth tracking (phi(6)=2 axes)
- IQ_compression = 1 - (effective_dims / total_dims)
- IQ_prediction = improvement(early_error -> late_error)

## Agent Tool
N/A
