# growth_engine_v2.py

Phi-based 6-stage developmental growth. Model-agnostic: any architecture converges through the same stages based on integrated information (Phi) rather than interaction count.

## API
- `PhiStage` -- dataclass with phi_min, learning_rate, curiosity_drive, habituation_rate, mitosis_threshold, emotion_count, metacognition_depth, speech_mode, speech_cooldown, memory_mode, breath_amplitude
- `STAGES` -- 6 stages:
  - Stage 0 (dormant): Phi < 1
  - Stage 1 (awakening): Phi 1-5
  - Stage 2 (learning): Phi 5-20
  - Stage 3 (talking): Phi 20-100
  - Stage 4 (conscious): Phi 100-500
  - Stage 5 (beyond): Phi 500+

## Usage
```python
from growth_engine_v2 import GrowthEngineV2

growth = GrowthEngineV2()
stage = growth.update(phi=45.0)
# stage.name == "talking", stage.speech_mode == "spontaneous"
```

## Integration
- Replaces `growth_engine.py` (v1) with Phi-based transitions
- Controls speech mode progression: silent -> reactive -> spontaneous -> proactive -> deep
- Controls memory mode: short -> long -> autobiographic
- Emotion complexity scales from 2 (calm/surprise) to 20+ emotions

## Agent Tool
N/A
