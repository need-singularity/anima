#!/usr/bin/env python3
"""Comprehensive tests for MemoryStore (SQLite + FAISS)."""

import json
import hashlib

import numpy as np
import pytest

from memory_store import MemoryStore

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def _vec(text: str, dim: int = 16) -> np.ndarray:
    """Deterministic pseudo-vector from text hash."""
    h = hashlib.sha256(text.encode()).digest()
    v = np.frombuffer(h[:dim * 4], dtype=np.float32).copy()
    if len(v) < dim:
        v = np.pad(v, (0, dim - len(v)))
    return v[:dim]


def _controlled_vec(base: np.ndarray, noise: float = 0.0, dim: int = 16) -> np.ndarray:
    """Create a vector close to base with controlled noise."""
    rng = np.random.RandomState(42)
    v = base.copy() + rng.randn(dim).astype(np.float32) * noise
    return v


# ── 1. add and get (conscious) ─────────────────────────────────

def test_add_and_get_conscious(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid = store.add("user", "hello world", tension=0.5, curiosity=0.3,
                     vector=_vec("hello world"), token_count=5, model_version="v1")
    row = store.get(mid)
    assert row is not None
    assert row["role"] == "user"
    assert row["text"] == "hello world"
    assert row["tension"] == 0.5
    assert row["curiosity"] == 0.3
    assert row["model_type"] == "conscious"
    assert row["token_count"] == 5
    assert row["model_version"] == "v1"
    assert row["tension_at_store"] == 0.5
    assert row["consolidated"] == 0
    assert row["verify_status"] == "raw"
    store.close()


# ── 2. add llm-api model ──────────────────────────────────────

def test_add_llm_api(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16,
                        model_type="llm-api")
    mid = store.add("assistant", "response text", token_count=12,
                     model_version="mistral-7b")
    row = store.get(mid)
    assert row["tension"] is None
    assert row["model_type"] == "llm-api"
    assert row["token_count"] == 12
    assert row["verify_hash"] is None  # no hash for llm-api
    store.close()


# ── 3. size property ──────────────────────────────────────────

def test_size(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    assert store.size == 0
    store.add("user", "a", tension=0.1)
    store.add("user", "b", tension=0.2)
    assert store.size == 2
    store.close()


# ── 4. verify_hash is 64-char hex ─────────────────────────────

def test_verify_hash(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid = store.add("user", "test text", tension=0.42)
    row = store.get(mid)
    h = row["verify_hash"]
    assert h is not None
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
    # Verify it matches expected
    expected = hashlib.sha256("test text|0.42".encode()).hexdigest()
    assert h == expected
    store.close()


# ── 5. get nonexistent returns None ───────────────────────────

def test_get_nonexistent(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    assert store.get(9999) is None
    store.close()


# ── 6. search returns similar items ordered by similarity ─────

def test_search_ordered(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    base = np.ones(16, dtype=np.float32)
    # exact match, small noise, large noise
    store.add("user", "exact", tension=0.1, vector=_controlled_vec(base, noise=0.0))
    store.add("user", "close", tension=0.2, vector=_controlled_vec(base, noise=0.1))
    store.add("user", "far", tension=0.3, vector=_controlled_vec(base, noise=10.0))

    results = store.search(base, top_k=3)
    assert len(results) == 3
    # First result should be most similar (exact match)
    assert results[0]["text"] == "exact"
    assert "similarity" in results[0]
    # Similarities should be descending
    sims = [r["similarity"] for r in results]
    assert sims == sorted(sims, reverse=True)
    store.close()


# ── 7. search on empty store ──────────────────────────────────

def test_search_empty(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    results = store.search(_vec("anything"), top_k=5)
    assert results == []
    store.close()


# ── 8. search top_k > store size ──────────────────────────────

def test_search_topk_exceeds(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    store.add("user", "only one", tension=0.1, vector=_vec("only one"))
    results = store.search(_vec("only one"), top_k=100)
    assert len(results) == 1
    store.close()


# ── 9. FAISS persistence round-trip ───────────────────────────

def test_faiss_persistence(tmp_path):
    db = tmp_path / "m.db"
    fp = tmp_path / "m.faiss"
    base = np.ones(16, dtype=np.float32)
    far = np.zeros(16, dtype=np.float32); far[0] = 1.0

    store1 = MemoryStore(db, fp, dim=16)
    store1.add("user", "persist me", tension=0.5, vector=base)
    store1.add("user", "also me", tension=0.6, vector=far)
    store1.close()  # saves faiss

    store2 = MemoryStore(db, fp, dim=16)
    results = store2.search(base, top_k=2)
    assert len(results) == 2
    assert results[0]["text"] == "persist me"
    store2.close()


# ── 10. get_unconsolidated returns only unconsolidated ────────

def test_get_unconsolidated(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid1 = store.add("user", "a", tension=0.1)
    mid2 = store.add("user", "b", tension=0.2)
    store.mark_consolidated(mid1, tension_at_consolidate=0.15)

    uncons = store.get_unconsolidated()
    assert len(uncons) == 1
    assert uncons[0]["id"] == mid2
    store.close()


# ── 11. get_unconsolidated ordered by failed_count desc ───────

def test_get_unconsolidated_order(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid1 = store.add("user", "low fail", tension=0.1)
    mid2 = store.add("user", "high fail", tension=0.2)
    store.mark_failed(mid2)
    store.mark_failed(mid2)
    store.mark_failed(mid1)

    uncons = store.get_unconsolidated(order_by="failed_count", limit=10)
    assert len(uncons) == 2
    assert uncons[0]["id"] == mid2  # 2 failures > 1 failure
    assert uncons[0]["failed_count"] == 2
    assert uncons[1]["failed_count"] == 1
    store.close()


# ── 12. llm-api returns empty from get_unconsolidated ─────────

def test_llm_api_no_unconsolidated(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16,
                        model_type="llm-api")
    store.add("user", "something")
    assert store.get_unconsolidated() == []
    store.close()


# ── 13. mark_failed increments and sets last_attempted ────────

def test_mark_failed(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid = store.add("user", "fail me", tension=0.5)
    store.mark_failed(mid, delta_tension=0.05)
    store.mark_failed(mid, delta_tension=0.03)

    row = store.get(mid)
    assert row["failed_count"] == 2
    assert row["last_attempted"] is not None
    assert row["delta_tension"] == 0.03  # last update
    store.close()


# ── 14. mark_consolidated computes drift correctly ────────────

def test_mark_consolidated_drift(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid = store.add("user", "consolidate me", tension=0.5)

    store.mark_consolidated(mid, tension_at_consolidate=0.48)
    row = store.get(mid)
    assert row["consolidated"] == 1
    assert row["verify_status"] == "verified"
    assert row["tension_at_consolidate"] == 0.48
    assert abs(row["tension_drift"] - 0.02) < 1e-9  # abs(0.48 - 0.5) = 0.02
    store.close()


# ── 15. mark_suspect ──────────────────────────────────────────

def test_mark_suspect(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid = store.add("user", "suspicious", tension=0.5)
    store.mark_suspect(mid, drift=0.15)

    row = store.get(mid)
    assert row["verify_status"] == "suspect"
    assert row["tension_drift"] == 0.15
    store.close()


# ── 16. unconsolidated_count property ─────────────────────────

def test_unconsolidated_count(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    store.add("user", "a", tension=0.1)
    store.add("user", "b", tension=0.2)
    assert store.unconsolidated_count == 2

    mid = store.add("user", "c", tension=0.3)
    store.mark_consolidated(mid, tension_at_consolidate=0.3)
    assert store.unconsolidated_count == 2  # c is now consolidated
    store.close()


# ── 17. failed_count_stats property ───────────────────────────

def test_failed_count_stats(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    mid1 = store.add("user", "a", tension=0.1)
    mid2 = store.add("user", "b", tension=0.2)
    store.mark_failed(mid1)
    store.mark_failed(mid2)
    store.mark_failed(mid2)
    store.mark_failed(mid2)

    stats = store.failed_count_stats
    assert stats["total_failed"] == 4  # 1 + 3
    assert stats["max_failed"] == 3
    assert stats["avg_failed"] == 2.0  # 4 / 2 entries
    store.close()


# ── 18. migrate_from_json ─────────────────────────────────────

def test_migrate_from_json(tmp_path):
    # Create test JSON (3 turns, one with empty text)
    json_path = tmp_path / "memory.json"
    data = {
        "turns": [
            {"time": "2026-01-01T00:00:00", "role": "user", "text": "hello", "tension": 0.5},
            {"time": "2026-01-01T00:01:00", "role": "assistant", "text": "", "tension": 0.6},
            {"time": "2026-01-01T00:02:00", "role": "assistant", "text": "world", "tension": 0.7},
        ],
        "total": 3,
        "avg_tension": 0.6,
    }
    json_path.write_text(json.dumps(data))

    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    count = store.migrate_from_json(json_path, lambda text: _vec(text))

    assert count == 2  # empty text skipped
    assert store.size == 2
    assert (tmp_path / "memory.json.bak").exists()
    store.close()


# ── 19. migrate_from_json idempotent ──────────────────────────

def test_migrate_idempotent(tmp_path):
    json_path = tmp_path / "memory.json"
    data = {"turns": [
        {"role": "user", "text": "hi", "tension": 0.5},
    ]}
    json_path.write_text(json.dumps(data))

    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    count1 = store.migrate_from_json(json_path, lambda t: _vec(t))
    count2 = store.migrate_from_json(json_path, lambda t: _vec(t))

    assert count1 == 1
    assert count2 == 0  # no-op second call
    assert store.size == 1
    store.close()


# ── 20. Vector dimension mismatch raises error ────────────────

def test_dim_mismatch(tmp_path):
    store = MemoryStore(tmp_path / "m.db", tmp_path / "m.faiss", dim=16)
    bad_vec = np.ones(32, dtype=np.float32)  # dim=32 != 16
    with pytest.raises(AssertionError, match="dim"):
        store.add("user", "bad", tension=0.1, vector=bad_vec)
    store.close()
