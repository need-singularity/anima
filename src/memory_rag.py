#!/usr/bin/env python3
"""벡터 유사도 기반 장기 기억 검색 (RAG).

모든 대화 턴을 text_to_vector()로 벡터화하고 저장.
검색 시 코사인 유사도로 가장 관련 있는 기억 반환.
추가 패키지 없이 torch만 사용.
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime

import torch
import torch.nn.functional as F

from anima_alive import text_to_vector

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


try:
    from hexad.narrative import NarrativeTracker
except ImportError:
    NarrativeTracker = None


class MemoryRAG:
    """벡터 유사도 기반 장기 기억 검색.

    모든 대화 턴을 text_to_vector()로 벡터화하고 저장.
    검색 시 코사인 유사도로 가장 관련 있는 기억 반환.
    """

    def __init__(self, memory_file, vector_file=None, dim=128):
        self.memory_file = Path(memory_file)
        self.vector_file = Path(vector_file) if vector_file else self.memory_file.parent / "memory_vectors.pt"
        self.dim = dim

        # 메타데이터 리스트 (role, text, tension, timestamp) — 벡터와 1:1 매핑
        self.entries = []
        # 벡터 인덱스 (N x dim tensor)
        self.vectors = torch.zeros(0, dim)

        self._lock = threading.Lock()
        self._dirty = False  # 저장 필요 여부

        # 인덱스 로드 시도 → 없으면 전체 구축
        if not self.load_index():
            self.index_all()

    def index_all(self):
        """memory.json의 모든 턴을 벡터화하여 인덱스 구축."""
        if not self.memory_file.exists():
            return

        try:
            with open(self.memory_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        turns = data.get('turns', [])
        if not turns:
            return

        entries = []
        vecs = []
        for turn in turns:
            text = turn.get('text', '')
            if not text.strip():
                continue
            vec = text_to_vector(text, self.dim)  # (1, dim)
            entries.append({
                'role': turn.get('role', 'unknown'),
                'text': text,
                'tension': turn.get('tension', 0.0),
                'timestamp': turn.get('time', ''),
            })
            vecs.append(vec)

        with self._lock:
            if vecs:
                self.vectors = torch.cat(vecs, dim=0)  # (N, dim)
            else:
                self.vectors = torch.zeros(0, self.dim)
            self.entries = entries
            self._dirty = True

        self.save_index()

    def add(self, role, text, tension, timestamp=None, emotion=None, phi=None, session_id=None,
            curiosity=None, vector=None):
        """새 기억 추가 (벡터 즉시 계산)."""
        if not text.strip():
            return

        vec = text_to_vector(text, self.dim)  # (1, dim)
        entry = {
            'role': role,
            'text': text,
            'tension': tension,
            'timestamp': timestamp or datetime.now().isoformat(),
            'epoch': time.time(),
            'emotion': emotion,
            'phi': phi,
            'session_id': session_id,
        }

        with self._lock:
            self.entries.append(entry)
            if self.vectors.shape[0] == 0:
                self.vectors = vec
            else:
                self.vectors = torch.cat([self.vectors, vec], dim=0)
            self._dirty = True

    def search(self, query_text, top_k=5):
        """쿼리와 가장 유사한 기억 top_k개 반환.

        Returns:
            list of {'role', 'text', 'tension', 'timestamp', 'similarity'}
        """
        if not query_text.strip():
            return []
        query_vec = text_to_vector(query_text, self.dim)  # (1, dim)
        return self.search_by_vector(query_vec, top_k)

    def search_by_vector(self, query_vec, top_k=5):
        """벡터로 직접 검색.

        Args:
            query_vec: (1, dim) tensor
            top_k: 반환할 결과 수

        Returns:
            list of {'role', 'text', 'tension', 'timestamp', 'similarity'}
        """
        with self._lock:
            if self.vectors.shape[0] == 0:
                return []

            # 코사인 유사도 계산
            # query_vec: (1, dim), self.vectors: (N, dim)
            sims = F.cosine_similarity(query_vec, self.vectors, dim=1)  # (N,)

        k = min(top_k, sims.shape[0])
        top_vals, top_ids = torch.topk(sims, k)

        results = []
        for i in range(k):
            idx = top_ids[i].item()
            entry = self.entries[idx].copy()
            entry['similarity'] = top_vals[i].item()
            results.append(entry)

        return results

    def save_index(self):
        """벡터 인덱스를 파일로 저장 (memory_vectors.pt)."""
        with self._lock:
            if not self._dirty:
                return
            data = {
                'vectors': self.vectors.clone(),
                'entries': list(self.entries),
            }
            self._dirty = False

        try:
            torch.save(data, self.vector_file)
        except Exception:
            pass

    def load_index(self):
        """저장된 벡터 인덱스 로드.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if not self.vector_file.exists():
            return False

        try:
            data = torch.load(self.vector_file, weights_only=False)
            with self._lock:
                self.vectors = data['vectors']
                self.entries = data['entries']
                self._dirty = False

            # memory.json과 동기화 확인 — 새로 추가된 턴이 있으면 증분 인덱싱
            self._sync_with_memory()
            return True
        except Exception:
            return False

    def _sync_with_memory(self):
        """memory.json에 인덱스에 없는 새 턴이 있으면 증분 추가."""
        if not self.memory_file.exists():
            return

        try:
            with open(self.memory_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        turns = data.get('turns', [])
        indexed_count = len(self.entries)

        # memory.json의 턴이 인덱스보다 많으면 새 턴만 추가
        if len(turns) > indexed_count:
            new_turns = turns[indexed_count:]
            for turn in new_turns:
                text = turn.get('text', '')
                if text.strip():
                    self.add(
                        role=turn.get('role', 'unknown'),
                        text=text,
                        tension=turn.get('tension', 0.0),
                        timestamp=turn.get('time', ''),
                    )

    def recall_by_time(self, days_ago=None, emotion=None, limit=5):
        """Recall memories by time range and/or emotion filter."""
        results = []
        now = time.time()
        with self._lock:
            for mem in self.entries:
                if days_ago is not None and (now - mem.get('epoch', 0)) > days_ago * 86400:
                    continue
                if emotion is not None and mem.get('emotion') != emotion:
                    continue
                results.append(mem)
        return sorted(results, key=lambda m: m.get('epoch', 0), reverse=True)[:limit]

    def autobiographical_stats(self):
        """Return stats for consciousness vector M and T computation."""
        with self._lock:
            total = len(self.entries)
            with_ts = sum(1 for e in self.entries if e.get('epoch'))
            epochs = [e['epoch'] for e in self.entries if e.get('epoch')]
        if len(epochs) >= 2:
            span_days = (max(epochs) - min(epochs)) / 86400
        else:
            span_days = 0.0
        return {
            'total': total,
            'with_timestamp': with_ts,
            'span_days': span_days,
            'M': with_ts / max(total, 1),
            'T': min(span_days / 100.0, 1.0),
        }

    @property
    def size(self):
        """인덱스된 기억 수."""
        return len(self.entries)
