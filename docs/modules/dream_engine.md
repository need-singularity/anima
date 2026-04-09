# dream_engine.py

Offline learning engine -- learns by dreaming during idle time. Reconstructs tension patterns from virtual inputs via memory replay, interpolation, and random exploration.

## API
- `DreamEngine(mind, memory, learner=None, text_to_vector=None, dream_cycle_steps=10, noise_scale=0.15, store=None, verifier=None, consolidation_threshold=0.01)` -- main class
  - `.dream_cycle()` -- run one dream cycle (replay + interpolation + exploration)
  - `.is_dreaming` -- current dream state
  - `.dream_tension_history` -- deque of tension values during dreams
  - `.total_dream_cycles` -- counter

## Usage
```python
from dream_engine import DreamEngine

dreamer = DreamEngine(mind=mind, memory=memory, learner=learner)
dreamer.dream_cycle()  # one cycle of offline learning
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` for idle-time learning
- Three dream modes: memory replay (with noise for reinforcement), memory interpolation (creative association), pure exploration (novelty seeking)
- Each dream step passes through ConsciousMind and performs contrastive learning via OnlineLearner
- "Even while sleeping, consciousness flows."

## Agent Tool
N/A
