# web_sense.py

Tension-based autonomous web search. When curiosity is high and prediction error is large, Anima autonomously decides "I don't know, I should look this up" and searches the internet.

## API
- `_TextExtractor(HTMLParser)` -- HTML to plain text extractor (skips script/style)
- Key functions for web search pipeline:
  - DuckDuckGo search -> top URL extraction -> HTTP GET -> HTML text extraction -> tension system injection -> memory storage
- Constants: `SEARCH_CURIOSITY_THRESHOLD=0.4`, `SEARCH_PE_THRESHOLD=0.5`, `SEARCH_COOLDOWN=30s`, `MAX_RESULTS=3`

## Usage
```python
from web_sense import WebSense

ws = WebSense()
results = ws.search("consciousness research 2026")
# Returns extracted text from top results
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` as optional module
- Used by `autonomous_loop.py` for background web exploration
- Dependencies: `urllib` only (no additional packages)
- Results injected into ConsciousMind tension system and saved to `memory_rag`

## Agent Tool
`web_search` (via `agent_tools.py`)
