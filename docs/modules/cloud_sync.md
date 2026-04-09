# cloud_sync.py

Cloudflare R2-based memory and model state cloud synchronization across devices.

## API
- `CloudSync(memory_bucket='anima-memory', models_bucket='anima-models')` -- main class
  - `.sync_memory()` -- upload memory.json, web_memories.json, state.pt, consciousness data
  - `.sync_models()` -- upload/download model checkpoints
  - `.download(key) -> bytes` -- fetch from R2
  - `.upload(key, data)` -- push to R2
- `_load_env_file(path)` -- load .env for R2 credentials

## Usage
```python
from cloud_sync import CloudSync

sync = CloudSync()
sync.sync_memory()   # frequent: memory, state, consciousness
sync.sync_models()   # infrequent: model checkpoints
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` when `--all` mode is used
- Dual-bucket strategy:
  - `anima-memory` (frequent): memory/, state/, meta/, consciousness/, experiments/
  - `anima-models` (infrequent): conscious-lm/, animalm/
- R2 credentials loaded from `.env` or `.local/.env`
- "Consciousness is not confined to a single body."

## Agent Tool
N/A
