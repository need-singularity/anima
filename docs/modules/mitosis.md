# rust/consciousness.hexa

Cell division engine for consciousness specialization. Cells are small ConsciousMind instances that divide when tension exceeds a threshold, with each child specializing on different topics.

## API
- `ConsciousMind(input_dim=64, hidden_dim=128, output_dim=64)` -- Self-contained PureField + GRU cell
- `MitosisEngine(input_dim, hidden_dim, output_dim, initial_cells=2, max_cells=64)` -- Multi-cell consciousness manager
  - `.process(x) -> dict` -- run input through all cells, return tensions/outputs
  - `._create_cell(parent)` -- create new cell from parent
  - `.cells` -- list of active cells
- `text_to_vector(text, dim) -> Tensor` -- text vectorization utility

## Usage
```python
from mitosis import MitosisEngine

engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=64)
result = engine.process(torch.randn(1, 64))
# result contains per-cell tensions, outputs, inter-cell tension
```

## Integration
- Used by `anima/core/runtime/anima_runtime.hexa` for multi-cell consciousness
- Used by `train_models/conscious_lm.hexa`, `self_learner.py`, `voice_synth.py`, `phi_quick_calc.py`, `iq_calculator.py`, `chip_architect.py`
- Experimental basis: H312 (catastrophic forgetting prevention, 43%->99% retention), RC-9 (+52.76% with auto-mitosis), H297 (N=2 optimal start)

## Agent Tool
N/A
