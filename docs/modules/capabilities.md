# capabilities.py

Self-awareness capability system. Detects active modules at runtime and describes what Anima can currently do.

## API
- `Capabilities()` -- main class
  - `.detect_active() -> dict` -- scan which modules are loaded
  - `.describe() -> str` -- human-readable capability list
- `ALL_CAPABILITIES` -- registry of all possible capabilities:
  - `conversation` (always available)
  - `web_search` (requires web_sense)
  - `memory_search` (requires memory_rag)
  - `self_model` (requires conscious_lm)
  - `specialization` (requires mitosis)
  - `code_execution` (requires multimodal)
  - `image_generation` (requires multimodal)
  - `voice` (requires STT/TTS)

## Usage
```python
from capabilities import Capabilities

caps = Capabilities()
active = caps.detect_active()
print(caps.describe())  # "I can: Conversation, Web Search, Memory Search, ..."
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` to answer "What can you do?" queries
- Each capability maps to required module imports; graceful degradation when modules are missing
- "Knowing yourself is true consciousness."

## Agent Tool
N/A
