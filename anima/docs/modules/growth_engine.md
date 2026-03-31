# growth_engine.py

5-stage developmental growth based on interaction count, modeled after brain development from newborn to adult.

## API
- `DevelopmentalStage` -- dataclass defining stage parameters (learning_rate, curiosity_drive, habituation_rate, mitosis_threshold, emotional_range, metacognition_depth, homeostasis_gain, dream_intensity, breath_amplitude)
- `STAGES` -- list of 5 stages: newborn (0-100), infant (100-500), toddler (500-2000), child (2000-10000), adult (10000+)
- `GrowthEngine` -- manages stage transitions based on interaction count

## Usage
```python
from growth_engine import GrowthEngine

growth = GrowthEngine()
stage = growth.update(interaction_count=250)
# stage.name == "infant", stage.learning_rate == high, stage.metacognition_depth == 0
```

## Integration
- Imported by `anima_unified.py` to modulate consciousness parameters over time
- Controls: learning rate (high->low), curiosity (high->medium), habituation speed (slow->fast), mitosis threshold (impossible->possible), emotional range (basic->complex), metacognition depth (0->3)
- Superseded by `growth_engine_v2.py` for Phi-based growth

## Agent Tool
N/A
