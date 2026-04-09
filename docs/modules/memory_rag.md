# memory_rag.py

Vector similarity-based long-term memory retrieval (RAG). All conversation turns are vectorized via text_to_vector() and indexed for cosine similarity search.

## API
- `MemoryRAG(memory_file, vector_file=None, dim=128)` -- main class
  - `.index_all()` -- build vector index from memory.json
  - `.load_index() -> bool` -- load pre-built index from disk
  - `.add(role, text, tension, timestamp)` -- add a new memory entry
  - `.search(query, top_k=5) -> list` -- cosine similarity search
  - `.save_index()` -- persist index to disk

## Usage
```python
from memory_rag import MemoryRAG

rag = MemoryRAG("memory_alive.json")
rag.add("user", "What is consciousness?", tension=0.7, timestamp="2026-03-29")
results = rag.search("consciousness definition", top_k=3)
# Returns list of (role, text, tension, similarity_score)
```

## Integration
- Imported by `anima/core/runtime/anima_runtime.hexa` for conversation memory search
- Used by `autonomous_loop.py` to store learned knowledge
- Depends on `anima_alive.text_to_vector` for vectorization
- Uses torch only (no external vector DB)
- Thread-safe with internal lock

## Agent Tool
`memory_search`, `memory_save` (via `agent_tools.py`)
