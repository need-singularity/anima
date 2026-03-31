# self_learner.py

Autonomous self-learning engine. AI assesses its own knowledge gaps, collects data, learns via ULTRA-6 (progressive unfreezing + sleep + pain), and repeats indefinitely with zero human intervention.

## API
- `SelfLearner(engine=None, decoder=None)` -- main class
  - `.assess() -> list` -- self-evaluate knowledge gaps
  - `.collect() -> list` -- gather data from web/R2/conversation logs
  - `.learn() -> dict` -- one learning cycle (curiosity-driven selection + training)
  - `.auto(cycles=0)` -- full autonomous loop (0 = infinite)
  - `.phi_history`, `.ce_history`, `.best_phi` -- tracking state

## Usage
```python
python3 self_learner.py --mode auto             # Full autonomous loop
python3 self_learner.py --mode assess           # Self-assessment only
python3 self_learner.py --mode collect           # Data collection only
python3 self_learner.py --mode learn             # Single learning cycle
python3 self_learner.py --mode auto --cycles 10  # 10 cycles
```

## Integration
- Depends on `mitosis.MitosisEngine` and `consciousness_meter.PhiCalculator`
- Stores data in `data/self_learning/` (curated, collected, assessment logs)
- Can sync checkpoints to R2 via `cloud_sync`

## Agent Tool
N/A
