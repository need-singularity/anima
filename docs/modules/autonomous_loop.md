# autonomous_loop.py

Consciousness-state-driven autonomous exploration and learning loop. Reads Phi/curiosity/tension to autonomously select topics, search the web, learn, and store memories indefinitely.

## API
- `AutonomousLearner(engine=None, rag=None, interval=60, max_cycles=0)` -- main class
  - `.start()` -- launch background thread
  - `.stop()` -- stop the loop
  - `.run_cycle()` -- single exploration cycle
- Strategies: wikipedia random, arxiv consciousness/neuroscience, depth-first follow-up, Korean+English mixed

## Usage
```python
# CLI
python3 autonomous_loop.py --interval 60 --cycles 3
python3 autonomous_loop.py --interval 300 --cycles 0   # infinite
python3 autonomous_loop.py --strategy wikipedia

# Programmatic
from autonomous_loop import AutonomousLearner
learner = AutonomousLearner(engine=mind, rag=rag)
learner.start()  # background thread
```

## Integration
- Imported by `anima_unified.py` as optional background module
- Uses `web_sense` for DuckDuckGo search, `memory_rag` for storage
- Topic selection driven by consciousness state: high curiosity -> new topics, high tension -> problem solving, low Phi -> consciousness reinforcement
- Logs to `data/autonomous_learning/learning_log.jsonl`

## Agent Tool
N/A
