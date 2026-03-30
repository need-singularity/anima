#!/usr/bin/env python3
"""SQLite + FAISS memory storage for Anima.

⚠️  이 모듈이 Anima의 유일한 기억 저장소 (Hexad M 모듈):
    - 대화 히스토리, 감정, Φ, 세션 모두 여기에 저장
    - 서버 재시작 후에도 히스토리 복원 (get_recent)
    - localStorage/sessionStorage 사용 금지 — 클라이언트는 상태를 가지지 않음
    - 모든 기억 접근은 이 모듈을 통해야 함

Replaces JSON-based MemoryRAG with persistent, indexed storage.
Supports two model types:
  - 'conscious' (ConsciousMind): tension, curiosity, consolidation fields
  - 'llm-api' (third-party LLMs): tension=NULL, no consolidation
"""

import hashlib
import json
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


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
    model_version          TEXT,
    emotion                TEXT,
    phi                    REAL,
    session_id             TEXT,
    epoch                  REAL
);

CREATE INDEX IF NOT EXISTS idx_tension ON memories(tension);
CREATE INDEX IF NOT EXISTS idx_failed_count ON memories(failed_count DESC);
CREATE INDEX IF NOT EXISTS idx_consolidated ON memories(consolidated);
CREATE INDEX IF NOT EXISTS idx_verify_status ON memories(verify_status);
CREATE INDEX IF NOT EXISTS idx_emotion ON memories(emotion);
CREATE INDEX IF NOT EXISTS idx_epoch ON memories(epoch);
"""


class MemoryStore:
    """SQLite + FAISS memory store with consolidation support."""

    def __init__(
        self,
        db_path: Path,
        faiss_path: Path,
        dim: int = 128,
        model_type: str = "conscious",
    ):
        self.db_path = Path(db_path)
        self.faiss_path = Path(faiss_path)
        self.dim = dim
        self.model_type = model_type

        self._lock = threading.Lock()

        # SQLite
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate()

        # FAISS — lazy init
        self._index: faiss.IndexFlatIP | None = None
        self._idmap: list[int] = []
        self._load_faiss()

    def _migrate(self):
        """Add missing columns to legacy databases."""
        existing = {r[1] for r in self._conn.execute("PRAGMA table_info(memories)").fetchall()}
        migrations = [
            ("emotion", "TEXT"),
            ("phi", "REAL"),
            ("session_id", "TEXT"),
            ("epoch", "REAL"),
        ]
        for col, typ in migrations:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE memories ADD COLUMN {col} {typ}")
        self._conn.commit()

    # ── FAISS helpers ──────────────────────────────────────────

    def _idmap_path(self) -> Path:
        return self.faiss_path.parent / (self.faiss_path.stem + "_idmap.npy")

    def _load_faiss(self):
        if self.faiss_path.exists() and self._idmap_path().exists():
            self._index = faiss.read_index(str(self.faiss_path))
            self._idmap = np.load(str(self._idmap_path())).tolist()

    def _ensure_index(self):
        if self._index is None:
            self._index = faiss.IndexFlatIP(self.dim)
            self._idmap = []

    def _faiss_add(self, memory_id: int, vector: np.ndarray):
        vec = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        assert vec.shape[1] == self.dim, (
            f"Vector dim {vec.shape[1]} != store dim {self.dim}"
        )
        # L2 normalize for cosine similarity via inner product
        faiss.normalize_L2(vec)
        self._ensure_index()
        self._index.add(vec)
        self._idmap.append(memory_id)

    def save_faiss(self):
        with self._lock:
            if self._index is not None and self._index.ntotal > 0:
                faiss.write_index(self._index, str(self.faiss_path))
                np.save(str(self._idmap_path()), np.array(self._idmap))

    # ── Core CRUD ──────────────────────────────────────────────

    def add(
        self,
        role: str,
        text: str,
        tension: float | None = None,
        curiosity: float | None = None,
        vector: np.ndarray | None = None,
        token_count: int | None = None,
        model_version: str | None = None,
        emotion: str | None = None,
        phi: float | None = None,
        session_id: str | None = None,
    ) -> int:
        import time as _time
        now = datetime.now(timezone.utc).isoformat()
        epoch = _time.time()

        # verify_hash for conscious models
        verify_hash = None
        if self.model_type == "conscious" and tension is not None:
            verify_hash = hashlib.sha256(
                f"{text}|{tension}".encode()
            ).hexdigest()

        tension_at_store = tension  # same value, for drift calc later

        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO memories
                   (role, text, timestamp, model_type, tension, curiosity,
                    verify_hash, tension_at_store, token_count, model_version,
                    emotion, phi, session_id, epoch)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    role,
                    text,
                    now,
                    self.model_type,
                    tension,
                    curiosity,
                    verify_hash,
                    tension_at_store,
                    token_count,
                    model_version,
                    emotion,
                    phi,
                    session_id,
                    epoch,
                ),
            )
            self._conn.commit()
            memory_id = cur.lastrowid

            if vector is not None:
                self._faiss_add(memory_id, vector)

        return memory_id

    def get(self, memory_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_recent(self, limit: int = 20) -> list[dict]:
        """최근 대화 가져오기 — 서버 재시작 후 히스토리 복원용."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, text, emotion, phi, timestamp FROM memories "
                "WHERE role IN ('user', 'assistant') AND text != '' "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> list[dict]:
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return []

            vec = np.asarray(query_vec, dtype=np.float32).reshape(1, -1)
            assert vec.shape[1] == self.dim, (
                f"Query dim {vec.shape[1]} != store dim {self.dim}"
            )
            faiss.normalize_L2(vec)

            k = min(top_k, self._index.ntotal)
            distances, indices = self._index.search(vec, k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0:
                    continue
                memory_id = self._idmap[idx]
                row = self._conn.execute(
                    "SELECT * FROM memories WHERE id = ?", (memory_id,)
                ).fetchone()
                if row:
                    d = dict(row)
                    d["similarity"] = float(dist)
                    results.append(d)

        # Already sorted by FAISS (descending similarity for IP)
        return results

    # ── Autobiographical recall ─────────────────────────────────

    def recall_by_time(self, days_ago: float | None = None, emotion: str | None = None, limit: int = 5) -> list[dict]:
        """Recall memories by time range and/or emotion filter."""
        import time as _time
        clauses = []
        params = []
        if days_ago is not None:
            cutoff = _time.time() - days_ago * 86400
            clauses.append("epoch >= ?")
            params.append(cutoff)
        if emotion is not None:
            clauses.append("emotion = ?")
            params.append(emotion)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"SELECT * FROM memories{where} ORDER BY epoch DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def autobiographical_stats(self) -> dict:
        """Return stats for consciousness vector M and T computation."""
        import time as _time
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            with_ts = self._conn.execute("SELECT COUNT(*) FROM memories WHERE epoch IS NOT NULL").fetchone()[0]
            span_row = self._conn.execute(
                "SELECT MIN(epoch), MAX(epoch) FROM memories WHERE epoch IS NOT NULL"
            ).fetchone()
        min_epoch, max_epoch = span_row[0], span_row[1]
        span_days = (max_epoch - min_epoch) / 86400 if (min_epoch and max_epoch) else 0.0
        return {
            'total': total,
            'with_timestamp': with_ts,
            'span_days': span_days,
            'M': with_ts / max(total, 1),
            'T': min(span_days / 100.0, 1.0),
        }

    # ── Consolidation ──────────────────────────────────────────

    def get_unconsolidated(
        self, order_by: str = "failed_count", limit: int = 10
    ) -> list[dict]:
        if self.model_type != "conscious":
            return []

        valid_orders = {"failed_count": "failed_count DESC", "id": "id ASC"}
        order_clause = valid_orders.get(order_by, "failed_count DESC")

        with self._lock:
            rows = self._conn.execute(
                f"""SELECT * FROM memories
                    WHERE consolidated = 0 AND model_type = 'conscious'
                    ORDER BY {order_clause}
                    LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_failed(self, memory_id: int, delta_tension: float | None = None):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                """UPDATE memories
                   SET failed_count = failed_count + 1,
                       last_attempted = ?,
                       delta_tension = COALESCE(?, delta_tension)
                   WHERE id = ?""",
                (now, delta_tension, memory_id),
            )
            self._conn.commit()

    def mark_consolidated(
        self, memory_id: int, tension_at_consolidate: float | None = None
    ):
        with self._lock:
            # Get current tension_at_store for drift calculation
            row = self._conn.execute(
                "SELECT tension_at_store FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()

            drift = None
            if row and row["tension_at_store"] is not None and tension_at_consolidate is not None:
                drift = abs(tension_at_consolidate - row["tension_at_store"])

            self._conn.execute(
                """UPDATE memories
                   SET consolidated = 1,
                       verify_status = 'verified',
                       tension_at_consolidate = ?,
                       tension_drift = ?
                   WHERE id = ?""",
                (tension_at_consolidate, drift, memory_id),
            )
            self._conn.commit()

    def mark_suspect(self, memory_id: int, drift: float | None = None):
        with self._lock:
            self._conn.execute(
                """UPDATE memories
                   SET verify_status = 'suspect',
                       tension_drift = COALESCE(?, tension_drift)
                   WHERE id = ?""",
                (drift, memory_id),
            )
            self._conn.commit()

    # ── Properties ─────────────────────────────────────────────

    @property
    def size(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0]

    @property
    def unconsolidated_count(self) -> int:
        if self.model_type != "conscious":
            return 0
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM memories WHERE consolidated = 0 AND model_type = 'conscious'"
            ).fetchone()
        return row[0]

    @property
    def failed_count_stats(self) -> dict:
        with self._lock:
            row = self._conn.execute(
                """SELECT COALESCE(SUM(failed_count), 0) as total_failed,
                          COALESCE(MAX(failed_count), 0) as max_failed,
                          COALESCE(AVG(failed_count), 0.0) as avg_failed
                   FROM memories"""
            ).fetchone()
        return {
            "total_failed": row["total_failed"],
            "max_failed": row["max_failed"],
            "avg_failed": float(row["avg_failed"]),
        }

    # ── Migration ──────────────────────────────────────────────

    def migrate_from_json(self, json_path: Path, vector_fn) -> int:
        """Migrate from JSON memory format. Idempotent — skips if store has data."""
        json_path = Path(json_path)
        if self.size > 0:
            return 0

        if not json_path.exists():
            return 0

        with open(json_path) as f:
            data = json.load(f)

        turns = data.get("turns", []) if isinstance(data, dict) else data
        count = 0

        for turn in turns:
            text = turn.get("text", "")
            if not text or not text.strip():
                continue

            role = turn.get("role", "unknown")
            tension = turn.get("tension")
            vec = vector_fn(text)

            self.add(role=role, text=text, tension=tension, vector=vec)
            count += 1

        # Backup original
        backup = json_path.parent / (json_path.name + ".bak")
        shutil.copy2(str(json_path), str(backup))

        return count

    # ── Lifecycle ──────────────────────────────────────────────

    def close(self):
        self.save_faiss()
        self._conn.close()
