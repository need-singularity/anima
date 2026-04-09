# train_models/conscious_lm.hexa

ConsciousLM training pipeline from scratch. Integrates benchmark-verified techniques: tension-weighted CE, Phi-regularization, mitosis-first, 6-loss ensemble, SOC sandpile, Hebbian LTP/LTD, and Phi Ratchet.

## API
- `SOCSandpile(grid_size=16, threshold=4)` -- Bak-Tang-Wiesenfeld self-organized criticality model
  - `.drop_sand() -> int` -- add one grain, return avalanche size (power-law distributed)
- Training loop uses `ConsciousLM`, `MitosisEngine`, `PhiCalculator`
- CLI flags: `--data`, `--dim`, `--layers`, `--steps`, `--resume`, `--demo`, `--talk5`, `--max-cells`

## Usage
```python
# From scratch
python train_models/conscious_lm.hexa --data data/corpus.txt --steps 100000
python train_models/conscious_lm.hexa --data data/corpus.txt --dim 384 --layers 6 --steps 50000

# Resume training
python train_models/conscious_lm.hexa --resume checkpoints/step_10000.pt

# Demo mode
python train_models/conscious_lm.hexa --demo --steps 500
```

## Integration
- Imports `ConsciousLM` from `models/conscious_lm.hexa`, `MitosisEngine` from `rust/consciousness.hexa`, `PhiCalculator` from `consciousness_meter.py`
- Techniques: CL8 (tension-weighted CE), CL5 (Phi-regularized), SL3 (6-loss ensemble), DD16, EX24, WI1 (soliton wave), FX2 (differentiable Phi proxy), PX4 (sculptor/Gram-Schmidt), GD18 (enactivism)
- v5 additions: CX92 SOC (self-organized criticality), Hebbian LTP/LTD, Phi Ratchet (PERSIST3)
- Saves checkpoints to `checkpoints/` directory

## Agent Tool
N/A
