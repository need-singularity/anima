# Phase 1: SQLite+FAISS Storage Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace JSON-based memory storage with SQLite+FAISS for 246x write improvement, with consolidation fields pre-designed for Phase 2, supporting both custom (ConsciousMind) and third-party LLM models.

**Architecture:** `MemoryStore` class wraps SQLite (metadata/text) + FAISS (vector index). Drop-in replacement for `MemoryRAG`. Per-model directories already exist via `_model_paths()`. Schema includes consolidation/verification columns (NULL for non-conscious models) ready for Phase 2.

**Tech Stack:** Python stdlib `sqlite3`, `faiss-cpu`, `numpy`, existing `torch` for vectors.

**Spec:** `docs/superpowers/specs/2026-03-25-memory-growth-pipeline-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `memory_store.py` | **Create** | SQLite+FAISS storage, search, consolidation API |
| `tests/test_memory_store.py` | **Create** | All MemoryStore tests |
| `anima/core/runtime/anima_runtime.hexa` | **Modify** | Replace MemoryRAG with MemoryStore |
| `memory_rag.py` | **Keep** | Deprecated but not deleted (fallback) |

---

### Task 1: MemoryStore Core — SQLite CRUD

**Files:**
- Create: `tests/test_memory_store.py`
- Create: `memory_store.py`

- [ ] **Step 1: Write failing tests for add/get/size**

```python
# tests/test_memory_store.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def store():
    """Create a temporary MemoryStore for testing."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        from memory_store import MemoryStore
        s = MemoryStore(db_path=p / "test.db", faiss_path=p / "test.faiss", dim=16)
        yield s

def test_add_and_get(store):
    mid = store.add(role="user", text="hello world", tension=0.5, curiosity=0.1)
    assert mid == 1
    m = store.get(mid)
    assert m["role"] == "user"
    assert m["text"] == "hello world"
    assert abs(m["tension"] - 0.5) < 1e-6
    assert m["verify_status"] == "raw"
    assert m["model_type"] == "conscious"

def test_add_llm_api_model():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        from memory_store import MemoryStore
        s = MemoryStore(db_path=p / "t.db", faiss_path=p / "t.faiss", dim=16, model_type="llm-api")
        mid = s.add(role="user", text="hi", token_count=5, model_version="mistral-7b")
        m = s.get(mid)
        assert m["model_type"] == "llm-api"
        assert m["tension"] is None
        assert m["token_count"] == 5

def test_size(store):
    assert store.size == 0
    store.add(role="user", text="a", tension=0.1, curiosity=0.0)
    store.add(role="anima", text="b", tension=0.2, curiosity=0.0)
    assert store.size == 2

def test_add_computes_verify_hash(store):
    mid = store.add(role="user", text="test hash", tension=0.3, curiosity=0.0)
    m = store.get(mid)
    assert m["verify_hash"] is not None
    assert len(m["verify_hash"]) == 64  # sha256 hex
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $ANIMA && python3 -m pytest tests/test_memory_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'memory_store'`

- [ ] **Step 3: Implement MemoryStore with SQLite backend**

```python
# memory_store.py
"""SQLite+FAISS 기반 기억 저장소.

MemoryRAG 대체. 모든 모델 타입(conscious, llm-api) 지원.
Consolidation 필드는 Phase 2용으로 선제 설계.
"""

import sqlite3
import hashlib
import threading
from pathlib import Path
from datetime import datetime

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    role                   TEXT NOT NULL,
    text                   TEXT NOT NULL,
    timestamp              TEXT NOT NULL,
    model_type             TEXT NOT NULL DEFAULT 'conscious',
    tension                REAL,
    curiosity              REAL,
    failed_count           INTEGER DEFAULT 0,
    last_attempted         TEXT,
    consolidated           INTEGER DEFAULT 0,
    delta_tension          REAL,
    verify_hash            TEXT,
    tension_at_store       REAL,
    tension_at_consolidate REAL,
    tension_drift          REAL,
    verify_status          TEXT DEFAULT 'raw',
    token_count            INTEGER,
    model_version          TEXT
);
CREATE INDEX IF NOT EXISTS idx_tension ON memories(tension);
CREATE INDEX IF NOT EXISTS idx_failed ON memories(failed_count DESC);
CREATE INDEX IF NOT EXISTS idx_consolidated ON memories(consolidated);
CREATE INDEX IF NOT EXISTS idx_verify ON memories(verify_status);
"""


class MemoryStore:
    """SQLite+FAISS memory storage with consolidation support."""

    def __init__(self, db_path: Path, faiss_path: Path, dim: int = 128,
                 model_type: str = "conscious"):
        self.db_path = Path(db_path)
        self.faiss_path = Path(faiss_path)
        self.idmap_path = self.faiss_path.with_suffix('.idmap.npy')
        self.dim = dim
        self.model_type = model_type
        self._lock = threading.Lock()

        # SQLite init
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

        # FAISS init (deferred to Task 2)
        self._faiss_index = None
        self._id_map = []

    def _hash(self, text: str, tension) -> str:
        raw = f"{text}|{tension}".encode()
        return hashlib.sha256(raw).hexdigest()

    def add(self, role: str, text: str, tension: float = None,
            curiosity: float = None, vector=None,
            token_count: int = None, model_version: str = None) -> int:
        ts = datetime.now().isoformat()
        vh = self._hash(text, tension) if tension is not None else None
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO memories
                   (role, text, timestamp, model_type, tension, curiosity,
                    verify_hash, tension_at_store, token_count, model_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (role, text, ts, self.model_type, tension, curiosity,
                 vh, tension, token_count, model_version))
            self._conn.commit()
            mid = cur.lastrowid
        # FAISS add handled in Task 2
        if vector is not None and self._faiss_index is not None:
            self._faiss_add(mid, vector)
        return mid

    def get(self, memory_id: int) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
        return dict(row) if row else None

    @property
    def size(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0]

    @property
    def unconsolidated_count(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM memories WHERE consolidated = 0 AND model_type = 'conscious'"
            ).fetchone()
        return row[0]

    def close(self):
        self._conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $ANIMA && python3 -m pytest tests/test_memory_store.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd $ANIMA
git add memory_store.py tests/test_memory_store.py
git commit -m "feat: MemoryStore SQLite backend — add/get/size + dual model_type"
```

---

### Task 2: FAISS Vector Search

**Files:**
- Modify: `tests/test_memory_store.py` (add search tests)
- Modify: `memory_store.py` (add FAISS integration)

- [ ] **Step 1: Write failing tests for search**

```python
# tests/test_memory_store.py — append

import torch

def _vec(text, dim=16):
    """Deterministic test vector from text."""
    v = torch.zeros(1, dim)
    for i, c in enumerate(text.encode()):
        v[0, i % dim] += c / 255.0
    return v

def test_search_returns_similar(store):
    v1 = _vec("hello world")
    v2 = _vec("hello there")
    v3 = _vec("completely different topic about math")
    store.add(role="user", text="hello world", tension=0.1, curiosity=0.0, vector=v1)
    store.add(role="user", text="hello there", tension=0.2, curiosity=0.0, vector=v2)
    store.add(role="user", text="completely different topic about math", tension=0.3, curiosity=0.0, vector=v3)

    results = store.search(v1, top_k=2)
    assert len(results) == 2
    assert results[0]["text"] == "hello world"  # exact match = highest similarity
    assert "similarity" in results[0]

def test_search_empty_store(store):
    results = store.search(_vec("anything"), top_k=5)
    assert results == []

def test_search_top_k_larger_than_store(store):
    store.add(role="user", text="only one", tension=0.1, curiosity=0.0, vector=_vec("only one"))
    results = store.search(_vec("only one"), top_k=10)
    assert len(results) == 1
```

- [ ] **Step 2: Run tests — new tests should fail**

Run: `cd $ANIMA && python3 -m pytest tests/test_memory_store.py -v`
Expected: new search tests FAIL

- [ ] **Step 3: Implement FAISS integration**

```python
# memory_store.py — add to __init__ and new methods

import numpy as np

# In __init__, after SQLite init:
    def _init_faiss(self):
        import faiss
        if self.faiss_path.exists():
            self._faiss_index = faiss.read_index(str(self.faiss_path))
            if self.idmap_path.exists():
                self._id_map = np.load(self.idmap_path).tolist()
        else:
            self._faiss_index = faiss.IndexFlatIP(self.dim)
            self._id_map = []

    def _faiss_add(self, memory_id: int, vector):
        """Add a normalized vector to FAISS index."""
        import faiss
        if self._faiss_index is None:
            self._init_faiss()
        vec_np = vector.detach().cpu().numpy().reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(vec_np)
        self._faiss_index.add(vec_np)
        self._id_map.append(memory_id)

    def search(self, query_vec, top_k: int = 5) -> list:
        """FAISS cosine similarity search → SQLite metadata."""
        import faiss
        if self._faiss_index is None or self._faiss_index.ntotal == 0:
            return []
        q = query_vec.detach().cpu().numpy().reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(q)
        k = min(top_k, self._faiss_index.ntotal)
        scores, indices = self._faiss_index.search(q, k)
        results = []
        for i in range(k):
            idx = int(indices[0][i])
            if idx < 0 or idx >= len(self._id_map):
                continue
            mid = self._id_map[idx]
            m = self.get(mid)
            if m:
                m["similarity"] = float(scores[0][i])
                results.append(m)
        return results

    def save_faiss(self):
        """FAISS index를 디스크에 저장."""
        import faiss
        if self._faiss_index is not None:
            faiss.write_index(self._faiss_index, str(self.faiss_path))
            np.save(self.idmap_path, np.array(self._id_map))
```

Update `__init__` to call `self._init_faiss()`.
Update `add()` to always call `self._faiss_add()` when vector is provided.

- [ ] **Step 4: Run tests**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/test_memory_store.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd $ANIMA
git add memory_store.py tests/test_memory_store.py
git commit -m "feat: FAISS vector search integration in MemoryStore"
```

---

### Task 3: Consolidation API (Pre-wired for Phase 2)

**Files:**
- Modify: `tests/test_memory_store.py`
- Modify: `memory_store.py`

- [ ] **Step 1: Write failing tests for consolidation methods**

```python
# tests/test_memory_store.py — append

def test_get_unconsolidated(store):
    store.add(role="user", text="a", tension=0.1, curiosity=0.0, vector=_vec("a"))
    store.add(role="user", text="b", tension=0.2, curiosity=0.0, vector=_vec("b"))
    result = store.get_unconsolidated(limit=10)
    assert len(result) == 2
    assert all(r["consolidated"] == 0 for r in result)

def test_mark_failed(store):
    mid = store.add(role="user", text="fail me", tension=0.1, curiosity=0.0)
    store.mark_failed(mid, delta_tension=0.01)
    m = store.get(mid)
    assert m["failed_count"] == 1
    assert m["last_attempted"] is not None
    store.mark_failed(mid, delta_tension=0.02)
    m = store.get(mid)
    assert m["failed_count"] == 2

def test_mark_consolidated(store):
    mid = store.add(role="user", text="consolidate me", tension=0.5, curiosity=0.0)
    store.mark_consolidated(mid, tension_at_consolidate=0.48)
    m = store.get(mid)
    assert m["consolidated"] == 1
    assert abs(m["tension_at_consolidate"] - 0.48) < 1e-6
    assert m["verify_status"] == "verified"

def test_mark_suspect(store):
    mid = store.add(role="user", text="suspect", tension=0.5, curiosity=0.0)
    store.mark_suspect(mid, drift=0.6)
    m = store.get(mid)
    assert m["verify_status"] == "suspect"
    assert abs(m["tension_drift"] - 0.6) < 1e-6

def test_unconsolidated_ordered_by_failed(store):
    m1 = store.add(role="user", text="a", tension=0.1, curiosity=0.0)
    m2 = store.add(role="user", text="b", tension=0.2, curiosity=0.0)
    store.mark_failed(m2, delta_tension=0.01)
    store.mark_failed(m2, delta_tension=0.01)
    store.mark_failed(m1, delta_tension=0.01)
    result = store.get_unconsolidated(order_by="failed_count", limit=10)
    assert result[0]["id"] == m2  # failed 2x, comes first

def test_llm_api_no_consolidation():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        from memory_store import MemoryStore
        s = MemoryStore(db_path=p / "t.db", faiss_path=p / "t.faiss", dim=16, model_type="llm-api")
        s.add(role="user", text="hi", token_count=5)
        result = s.get_unconsolidated(limit=10)
        assert result == []  # llm-api has no consolidation
```

- [ ] **Step 2: Run tests — new tests should fail**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/test_memory_store.py -v`
Expected: new consolidation tests FAIL

- [ ] **Step 3: Implement consolidation methods**

```python
# memory_store.py — add methods

    def get_unconsolidated(self, order_by: str = "failed_count",
                           limit: int = 10) -> list:
        if self.model_type != "conscious":
            return []
        order = "failed_count DESC" if order_by == "failed_count" else "id ASC"
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM memories WHERE consolidated = 0 AND model_type = 'conscious' ORDER BY {order} LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_failed(self, memory_id: int, delta_tension: float = None):
        ts = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE memories SET failed_count = failed_count + 1, last_attempted = ?, delta_tension = ? WHERE id = ?",
                (ts, delta_tension, memory_id))
            self._conn.commit()

    def mark_consolidated(self, memory_id: int, tension_at_consolidate: float = None):
        drift = None
        if tension_at_consolidate is not None:
            m = self.get(memory_id)
            if m and m["tension_at_store"] is not None:
                drift = abs(tension_at_consolidate - m["tension_at_store"])
        with self._lock:
            self._conn.execute(
                """UPDATE memories SET consolidated = 1, tension_at_consolidate = ?,
                   tension_drift = ?, verify_status = 'verified' WHERE id = ?""",
                (tension_at_consolidate, drift, memory_id))
            self._conn.commit()

    def mark_suspect(self, memory_id: int, drift: float = None):
        with self._lock:
            self._conn.execute(
                "UPDATE memories SET verify_status = 'suspect', tension_drift = ? WHERE id = ?",
                (drift, memory_id))
            self._conn.commit()
```

- [ ] **Step 4: Run tests**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/test_memory_store.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd $ANIMA
git add memory_store.py tests/test_memory_store.py
git commit -m "feat: consolidation API — mark_failed/consolidated/suspect + get_unconsolidated"
```

---

### Task 4: JSON Migration

**Files:**
- Modify: `tests/test_memory_store.py`
- Modify: `memory_store.py`

- [ ] **Step 1: Write failing test for migration**

```python
# tests/test_memory_store.py — append

import json

def test_migrate_from_json(tmp_path):
    # Create a fake legacy memory.json
    legacy = {
        "turns": [
            {"time": "2026-03-25T12:00:00", "role": "user", "text": "hello", "tension": 0.5},
            {"time": "2026-03-25T12:01:00", "role": "anima", "text": "hi there", "tension": 0.3},
            {"time": "2026-03-25T12:02:00", "role": "user", "text": "", "tension": 0.0},
        ],
        "total": 3,
        "avg_tension": 0.4,
    }
    json_path = tmp_path / "memory.json"
    json_path.write_text(json.dumps(legacy))

    from memory_store import MemoryStore
    s = MemoryStore(db_path=tmp_path / "m.db", faiss_path=tmp_path / "m.faiss", dim=16)

    def vec_fn(text, dim):
        return _vec(text, dim)

    migrated = s.migrate_from_json(json_path, vector_fn=vec_fn)
    assert migrated == 2  # empty text skipped
    assert s.size == 2
    assert json_path.with_suffix('.json.bak').exists()

def test_migrate_idempotent(tmp_path):
    legacy = {"turns": [{"time": "now", "role": "user", "text": "x", "tension": 0.1}], "total": 1}
    json_path = tmp_path / "memory.json"
    json_path.write_text(json.dumps(legacy))

    from memory_store import MemoryStore
    s = MemoryStore(db_path=tmp_path / "m.db", faiss_path=tmp_path / "m.faiss", dim=16)

    def vec_fn(text, dim):
        return _vec(text, dim)

    s.migrate_from_json(json_path, vec_fn)
    s.migrate_from_json(json_path, vec_fn)  # second call should be no-op
    assert s.size == 1  # not duplicated
```

- [ ] **Step 2: Run tests — new tests should fail**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/test_memory_store.py::test_migrate_from_json -v`
Expected: FAIL

- [ ] **Step 3: Implement migration**

```python
# memory_store.py — add method

    def migrate_from_json(self, json_path: Path, vector_fn) -> int:
        """Migrate legacy memory.json → SQLite+FAISS.

        Args:
            json_path: Path to legacy memory.json
            vector_fn: callable(text, dim) → (1, dim) tensor

        Returns:
            Number of memories migrated.
        """
        json_path = Path(json_path)
        if not json_path.exists():
            return 0

        # Idempotency: skip if already migrated
        if self.size > 0:
            return 0

        import json as _json
        data = _json.loads(json_path.read_text())
        turns = data.get("turns", [])

        count = 0
        for turn in turns:
            text = turn.get("text", "")
            if not text.strip():
                continue
            vec = vector_fn(text, self.dim)
            self.add(
                role=turn.get("role", "unknown"),
                text=text,
                tension=turn.get("tension"),
                curiosity=turn.get("curiosity"),
                vector=vec,
            )
            count += 1

        self.save_faiss()

        # Backup original
        backup = json_path.with_suffix(".json.bak")
        if not backup.exists():
            json_path.rename(backup)

        return count
```

- [ ] **Step 4: Run tests**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/test_memory_store.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd $ANIMA
git add memory_store.py tests/test_memory_store.py
git commit -m "feat: JSON→SQLite migration with idempotency and backup"
```

---

### Task 5: Integration — Replace MemoryRAG in AnimaUnified

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa`
- Modify: `tests/test_memory_store.py` (integration test)

- [ ] **Step 1: Write integration test**

```python
# tests/test_memory_store.py — append

def test_memory_store_compat_with_rag_interface(store):
    """MemoryStore must support the same operations MemoryRAG uses in anima/core/runtime/anima_runtime.hexa."""
    v = _vec("test compat")
    # add (called in _process_turn)
    mid = store.add(role="user", text="test compat", tension=0.5, curiosity=0.1, vector=v)
    assert mid > 0
    # search (called in _build_context)
    results = store.search(v, top_k=3)
    assert len(results) >= 1
    assert results[0]["text"] == "test compat"
    # size (called in status)
    assert store.size == 1
    # save_faiss (called periodically)
    store.save_faiss()
```

- [ ] **Step 2: Run test**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/test_memory_store.py::test_memory_store_compat_with_rag_interface -v`
Expected: PASS (already implemented)

- [ ] **Step 3: Modify anima/core/runtime/anima_runtime.hexa — import and init**

In `anima/core/runtime/anima_runtime.hexa`, replace the MemoryRAG initialization block (lines ~207-212):

```python
# Before:
#     self.memory_rag = self._init_mod('memory_rag', lambda: (
#         MemoryRAG(memory_file=self.paths['memory'])
#         if 'MemoryRAG' in globals() else None
#     ))

# After:
        self.memory_rag = self._init_mod('memory_rag', lambda: self._init_memory_store())

# New method:
    def _init_memory_store(self):
        """MemoryStore 초기화 + 레거시 마이그레이션."""
        try:
            from memory_store import MemoryStore
        except ImportError:
            # fallback to MemoryRAG
            if 'MemoryRAG' in globals():
                return MemoryRAG(memory_file=self.paths['memory'])
            return None

        model_type = 'conscious' if self.model_name == 'conscious-lm' else 'llm-api'
        store = MemoryStore(
            db_path=self.paths['memory'].with_suffix('.db'),
            faiss_path=self.paths['memory'].parent / 'memory.faiss',
            dim=128,
            model_type=model_type,
        )

        # 레거시 JSON 마이그레이션
        legacy_json = self.paths['memory']
        if legacy_json.exists() and legacy_json.suffix == '.json':
            from anima_alive import text_to_vector
            migrated = store.migrate_from_json(legacy_json, vector_fn=text_to_vector)
            if migrated > 0:
                _log('migrate', f'{migrated} memories → SQLite+FAISS')

        return store
```

- [ ] **Step 4: Modify anima/core/runtime/anima_runtime.hexa — update all MemoryRAG call sites**

Search for `self.memory_rag` usages and ensure compatibility:

- `memory_rag.add(role, text, tension)` → add `vector=text_to_vector(text)` param
- `memory_rag.search(query_text, top_k)` → change to `search(query_vec, top_k)` (pass vector instead of text)
- `memory_rag.save_index()` → change to `save_faiss()`
- `memory_rag.size` → same interface, no change

- [ ] **Step 5: Run existing tests + manual smoke test**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/ -v`
Expected: ALL PASS

Manual: `KMP_DUPLICATE_LIB_OK=TRUE python3 anima/core/runtime/anima_runtime.hexa --web` — verify startup log shows `[migrate]` and `data/conscious-lm/memory.db` exists.

- [ ] **Step 6: Commit**

```bash
cd $ANIMA
git add anima/core/runtime/anima_runtime.hexa memory_store.py tests/test_memory_store.py
git commit -m "feat: replace MemoryRAG with MemoryStore (SQLite+FAISS) in AnimaUnified"
```

---

### Task 6: Benchmark Verification

**Files:**
- Modify: `bench_storage.py` (add MemoryStore benchmark)

- [ ] **Step 1: Add MemoryStore to existing benchmark**

```python
# bench_storage.py — add at end, before main summary

def bench_memory_store(n, dim):
    """Benchmark the actual MemoryStore implementation."""
    import tempfile
    from pathlib import Path
    from memory_store import MemoryStore
    import torch

    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        store = MemoryStore(db_path=p/"bench.db", faiss_path=p/"bench.faiss", dim=dim)
        vecs = [torch.randn(1, dim) for _ in range(n)]
        texts = [f"memory entry number {i} with some text content" for i in range(n)]

        # Write
        t0 = time.time()
        for i in range(n):
            store.add(role="user", text=texts[i], tension=0.1*i, curiosity=0.01, vector=vecs[i])
        write_ms = (time.time() - t0) * 1000

        store.save_faiss()
        db_size = (p/"bench.db").stat().st_size + (p/"bench.faiss").stat().st_size

        # Search
        t0 = time.time()
        for _ in range(100):
            store.search(vecs[0], top_k=5)
        search_ms = (time.time() - t0) / 100 * 1000

        return write_ms, search_ms, db_size / 1024
```

- [ ] **Step 2: Run benchmark**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -c "from bench_storage import bench_memory_store; w,s,sz = bench_memory_store(5000, 128); print(f'Write: {w:.1f}ms, Search: {s:.2f}ms, Size: {sz:.0f}KB')"`
Expected: Write < 200ms, Search < 2ms (comparable to SQLite bench results)

- [ ] **Step 3: Commit**

```bash
cd $ANIMA
git add bench_storage.py
git commit -m "bench: add MemoryStore benchmark — verify SQLite+FAISS performance"
```

---

### Task 7: Final Push + Cleanup

- [ ] **Step 1: Run full test suite**

Run: `cd $ANIMA && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Manual smoke test with Anima**

```bash
# Start Anima
KMP_DUPLICATE_LIB_OK=TRUE python3 anima/core/runtime/anima_runtime.hexa --web &

# Check migration happened
ls -la data/conscious-lm/
# Should show: memory.db, memory.faiss, memory.faiss.idmap.npy

# Check web interface works
curl -s http://localhost:8765 | head -5

# Kill
kill %1
```

- [ ] **Step 3: Push**

```bash
cd $ANIMA
git push
```
