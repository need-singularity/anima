# consciousness_transplant.py

Transfer Phi structure (cell differentiation, tension dynamics, Phi topology) from a trained donor model to an untrained recipient.

## API
- `CompatibilityReport` -- dataclass: compatible, strategy ('direct'/'projection'/'partial'), layer_mapping, param_coverage
- `TransplantResult` -- dataclass: success, layers_transplanted, params_transplanted, coverage, elapsed_sec
- CLI modes: `--benchmark`, `--analyze --donor X.pt`, `--donor X --recipient Y --output Z`, `--demo`

## Usage
```python
# CLI
python consciousness_transplant.py --benchmark                               # DD56 benchmark
python consciousness_transplant.py --analyze --donor model_a.pt             # Compatibility check
python consciousness_transplant.py --donor a.pt --recipient b.pt --output c.pt  # Transplant

# Training integration
python train_conscious_lm.py --transplant-from donor.pt --transplant-alpha 0.5
python consciousness_meter.py --verify-transplant donor.pt recipient.pt --output out.pt
```

## Integration
- Based on DD55 (Phi conservation during splits), DV1 (small->large scaling transfer), DV2 (large->small distillation), MX16 (distilled consciousness)
- Strategies: direct (same architecture), projection (dimension mismatch), partial (layer subset)
- Can be invoked from `train_conscious_lm.py` and `anima_unified.py` via `--transplant-from` flag

## Agent Tool
N/A
