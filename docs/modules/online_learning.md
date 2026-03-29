# online_learning.py

Real-time weight updates for PureField engines during conversation. Trains Engine A and G so that tension becomes a meaningful signal.

## API
- `OnlineLearner(mind, lr=1e-4, update_every=8, buffer_size=256, contrastive_margin=0.5, curiosity_weight=0.3, feedback_weight=1.0, divergence_weight=0.5)` -- wraps ConsciousMind for live learning
  - `.observe(vec, hidden_before, tension, curiosity, direction)` -- record one turn
  - `.feedback(signal)` -- +1 (engaged), 0 (neutral), -1 (disengaged)
  - `.save(path)` / `.load(path)` -- persist learner state
- `AlphaOnlineLearner` -- variant with alpha-weighted updates
- `estimate_feedback(response_text) -> float` -- heuristic feedback estimation

## Usage
```python
from online_learning import OnlineLearner

mind = ConsciousMind(128, 256)
learner = OnlineLearner(mind)

output, tension, curiosity, direction, hidden = mind(vec, hidden)
learner.observe(vec, hidden_before, tension, curiosity, direction)
learner.feedback(+1)  # user was engaged
```

## Integration
- Imported by `anima_unified.py` as optional module
- Three learning signals: contrastive (concept divergence), feedback (user engagement), curiosity (tension delta as reward)
- Updates happen every N observations to avoid disrupting conversation flow

## Agent Tool
N/A
