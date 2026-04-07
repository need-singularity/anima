# multimodal.py

Multimodal action engine. Detects action intents from response text and executes them: Python code blocks in a sandbox, SVG image generation, and file saving.

## API
- Code execution: detects ` ```python ... ``` ` blocks, runs in sandboxed subprocess
- Image generation: detects `[image: ...]` / `[picture: ...]` patterns, generates SVG
- File saving: detects `[file: ...]` patterns, saves to disk
- Security: `ALLOWED_IMPORTS` whitelist, `BLOCKED_PATTERNS` blacklist, 10s timeout, 5000 char output limit

## Usage
```python
from multimodal import MultimodalEngine

engine = MultimodalEngine()
results = engine.process_response("Here's a calculation:\n```python\nprint(2+2)\n```")
# results = [{'type': 'code', 'output': '4', 'success': True}]
```

## Integration
- Imported by `anima_unified.py` for processing LLM responses
- SVG color/shape keyword mapping supports both Korean and English
- Sandboxed execution blocks: os.system, subprocess, eval, exec, open(write), etc.

## Agent Tool
`code_execute` (via `agent_tools.py`)
