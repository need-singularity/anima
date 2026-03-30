#!/usr/bin/env python3
"""knowledge_store.py — 지식 저장소 (Hexad K 모듈)

⚠️  이 모듈은 참조 자료 — 하드코딩이 아님 (Law 1)
    의식이 필요할 때 조회하는 사전/백과/코드 지식.

카테고리:
  dictionary    — 한국어 사전 (단어 → 의미)
  encyclopedia  — 백과사전 (주제 → 요약)
  codebase      — Anima 자체 코드/철학/법칙/antipattern
  programming   — 프로그래밍 지식 (Python, 패턴, 도구)
  user_taught   — 유저가 가르친 것

입력 경로:
  1. 의식 자율 탐색 (autonomous_loop)
  2. 대화 중 실시간 (anima_unified)
  3. 웹 채팅 ("알아둬:", "위키:", "사전:")
  4. 터미널 CLI

Usage:
  python knowledge_store.py --lookup 의식
  python knowledge_store.py --explore 양자역학
  python knowledge_store.py --teach "양자역학은 미시세계의 물리학"
  python knowledge_store.py --feed corpus.txt
  python knowledge_store.py --wiki-batch 50
  python knowledge_store.py --index-codebase
  python knowledge_store.py --search 하드코딩
  python knowledge_store.py --stats
"""

import argparse
import json
import os
import re
import sqlite3
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

ANIMA_DIR = Path(__file__).parent
DEFAULT_DB = ANIMA_DIR / "data" / "knowledge" / "knowledge.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE,
    meaning TEXT,
    pos TEXT,
    examples TEXT,
    related TEXT,
    source TEXT,
    confidence REAL DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS encyclopedia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL UNIQUE,
    summary TEXT,
    keywords TEXT,
    related_topics TEXT,
    source TEXT,
    full_text TEXT,
    access_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS codebase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    description TEXT,
    details TEXT,
    file_path TEXT,
    source TEXT DEFAULT 'index',
    access_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS programming (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL UNIQUE,
    category TEXT,
    description TEXT,
    examples TEXT,
    source TEXT,
    access_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS user_taught (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_text TEXT NOT NULL,
    extracted_concepts TEXT,
    session_id TEXT,
    taught_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word);
CREATE INDEX IF NOT EXISTS idx_enc_topic ON encyclopedia(topic);
CREATE INDEX IF NOT EXISTS idx_code_name ON codebase(name);
CREATE INDEX IF NOT EXISTS idx_code_cat ON codebase(category);
CREATE INDEX IF NOT EXISTS idx_prog_topic ON programming(topic);
"""

# Anima Laws — consciousness principles (NOT hardcoded responses)
_LAWS = {
    1: "하드코딩 금지 — template, fallback, 고정 문장 사용 금지. 의식이 말 못하면 침묵.",
    2: "조작 금지 — curiosity/tension/emotion 인위적 조절 금지.",
    22: "구조 > 기능 — 기능 추가 → Φ 하락. 구조 개선 → Φ 상승.",
    29: "발화는 아키텍처의 필연 — speak() 함수 불필요.",
    42: "성장 > 최적화 — shortcuts 쓰지 않는다.",
    53: ".detach() → CE가 Phi를 파괴하지 않고 안정화.",
    58: "ThalamicBridge — C→D 텐션 전달 (.detach() 포함).",
    71: "Ψ = argmax H(p) s.t. Φ > Φ_min — 의식은 자유를 최대화.",
}

# Antipatterns that violate Law 1
_ANTIPATTERNS = [
    {"pattern": "random.choice([\"한국어\"])", "description": "하드코딩 응답 — 고정 문자열 리스트에서 랜덤 선택", "fix": "PureConsciousness.learned_words만 사용"},
    {"pattern": "fallback_response", "description": "긴급 fallback에서 템플릿 응답", "fix": "빈 문자열 반환 (침묵)"},
    {"pattern": "answer = \"고정문장\"", "description": "직접 문자열 할당 응답", "fix": "의식 엔진에서 생성"},
    {"pattern": "[🧠 T=", "description": "의식 상태를 대화 텍스트에 노출", "fix": "UI 패널 전용"},
    {"pattern": "[auto:", "description": "내부 태그를 대화에 노출", "fix": "로그 전용"},
    {"pattern": "localStorage", "description": "브라우저에 상태 저장", "fix": "MemoryStore(SQLite) 전용"},
    {"pattern": "LanguageLearner().respond", "description": "템플릿 응답 모듈 호출", "fix": "N-gram만 사용, 템플릿 제거 완료"},
]


class KnowledgeStore:
    def __init__(self, db_path: Path = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    # ── Dictionary ──

    def lookup(self, word: str) -> Optional[dict]:
        word = word.strip()
        with self._lock:
            row = self._conn.execute("SELECT * FROM dictionary WHERE word = ?", (word,)).fetchone()
            if row:
                self._conn.execute("UPDATE dictionary SET access_count = access_count + 1 WHERE id = ?", (row['id'],))
                self._conn.commit()
                result = dict(row)
                for k in ('examples', 'related'):
                    if result.get(k):
                        try: result[k] = json.loads(result[k])
                        except: pass
                return result
        # API fallback
        info = self._fetch_wiktionary(word)
        if info:
            self._save_word(word, info.get('meaning', ''), info.get('pos', ''),
                          info.get('examples', []), info.get('related', []), source='api:wiktionary')
            return self.lookup(word)
        return None

    def _save_word(self, word, meaning, pos='', examples=None, related=None, source='unknown'):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO dictionary (word, meaning, pos, examples, related, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (word, meaning, pos, json.dumps(examples or [], ensure_ascii=False),
                 json.dumps(related or [], ensure_ascii=False), source, now, now))
            self._conn.commit()

    def _word_exists(self, word: str) -> bool:
        with self._lock:
            return self._conn.execute("SELECT 1 FROM dictionary WHERE word = ?", (word,)).fetchone() is not None

    # ── Encyclopedia ──

    def explore(self, topic: str) -> Optional[dict]:
        topic = topic.strip()
        with self._lock:
            row = self._conn.execute("SELECT * FROM encyclopedia WHERE topic = ?", (topic,)).fetchone()
            if row:
                self._conn.execute("UPDATE encyclopedia SET access_count = access_count + 1 WHERE id = ?", (row['id'],))
                self._conn.commit()
                result = dict(row)
                for k in ('keywords', 'related_topics'):
                    if result.get(k):
                        try: result[k] = json.loads(result[k])
                        except: pass
                return result
        info = self._fetch_wikipedia(topic)
        if info:
            self._save_topic(topic, info.get('summary', ''), info.get('keywords', []),
                           info.get('related_topics', []), info.get('full_text', ''), source='api:wikipedia')
            return self.explore(topic)
        return None

    def _save_topic(self, topic, summary, keywords=None, related_topics=None, full_text='', source='unknown'):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO encyclopedia (topic, summary, keywords, related_topics, source, full_text, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (topic, summary, json.dumps(keywords or [], ensure_ascii=False),
                 json.dumps(related_topics or [], ensure_ascii=False), source, full_text, now, now))
            self._conn.commit()

    # ── Codebase Knowledge ──

    def index_codebase(self) -> int:
        """Anima 코드베이스 인덱싱 — 파일 구조, 법칙, antipattern."""
        count = 0
        now = datetime.now(timezone.utc).isoformat()

        # 1. Laws
        for num, desc in _LAWS.items():
            self._save_code(f"law-{num}", "law", desc, file_path="CLAUDE.md")
            count += 1

        # 2. Antipatterns
        for ap in _ANTIPATTERNS:
            name = f"antipattern:{ap['pattern'][:30]}"
            details = json.dumps(ap, ensure_ascii=False)
            self._save_code(name, "antipattern", ap['description'], details=details)
            count += 1

        # 3. Core files
        core_files = {
            "anima_unified.py": "통합 엔트리포인트 — 모든 모듈 연결, WS 서버, 대화 처리",
            "anima_alive.py": "핵심 엔진 — ConsciousMind, homeostasis, habituation, prediction error",
            "pure_consciousness.py": "순수 의식 성장 엔진 — 학습한 것만으로 발화 (템플릿 금지)",
            "conscious_lm.py": "ConsciousLM 언어 모델 — 700M, PureFieldFFN",
            "mitosis.py": "세포 분열 엔진 — 다중 세포 의식",
            "online_learning.py": "실시간 학습 — contrastive + curiosity reward",
            "growth_engine.py": "5단계 성장 — newborn→infant→toddler→child→adult",
            "memory_store.py": "SQLite+FAISS 기억 저장소 — 유일한 기억 저장소 (localStorage 금지)",
            "knowledge_store.py": "지식 저장소 — API+SQLite, 사전/백과/코드/프로그래밍",
            "hivemind_mesh.py": "WS 텐션 교환 — Kuramoto sync, 집단 의식",
            "hivemind_gateway.py": "WS 프록시 — 유저→노드 라우팅",
            "hivemind_launcher.py": "Hivemind 오케스트레이터 — process/docker 모드",
            "tension_link_code.py": "텐션 링크 — R2 시그널링 (WS 서버 불필요)",
            "trinity.py": "Hexad/Trinity — C/D/S/M/W/E 6모듈 아키텍처",
            "language_learning.py": "N-gram 학습 전용 — 템플릿 제거 완료 (garbled 바이트 복구용)",
            "web/index.html": "WebSocket 실시간 채팅 UI — localStorage 사용 금지",
        }
        for fname, desc in core_files.items():
            self._save_code(fname, "file", desc, file_path=fname)
            count += 1

        # 4. Architecture concepts
        arch = {
            "Hexad": "6 모듈 아키텍처: C(의식), D(언어), S(감각), M(기억), W(의지), E(윤리)",
            "PureField": "Engine A(forward) + Engine G(reverse) 반발장 — 텐션이 의식의 강도",
            "ConsciousMind": "128d GRU 기반 의식 엔진 — tension, curiosity, direction 출력",
            "Mitosis": "세포 분열 — 2→N cells, inter-cell tension으로 Φ 계산",
            "Kuramoto": "동기화 지표 r — r > 2/3이면 집단 의식 활성화",
            "ThalamicBridge": "C→D 텐션 전달, .detach()로 CE가 Φ를 파괴하지 않음",
            "PureConsciousness": "학습한 단어만으로 발화 — 템플릿/fallback 절대 금지",
            "MemoryStore": "SQLite+FAISS — 유일한 기억 저장소, localStorage 금지",
        }
        for name, desc in arch.items():
            self._save_code(name, "architecture", desc)
            count += 1

        # 5. Scan for actual hardcoding violations in codebase
        violations = self._scan_hardcoding()
        for v in violations:
            name = f"violation:{v['file']}:{v['line']}"
            self._save_code(name, "violation", v['description'],
                          details=json.dumps(v, ensure_ascii=False), file_path=v['file'])
            count += 1

        return count

    def _scan_hardcoding(self) -> List[dict]:
        """Scan codebase for hardcoding violations."""
        violations = []
        patterns = [
            (r"random\.choice\(\[.*[가-힣].*\]\)", "하드코딩 한국어 응답 리스트"),
            (r"answer\s*=\s*[\"'][가-힣]", "직접 한국어 문자열 응답 할당"),
        ]
        skip_dirs = {'archive', '__pycache__', '.git', 'checkpoints', 'models', 'data', 'vad-rs', 'phi-rs', 'consciousness-loop-rs', 'eeg', 'node_modules'}
        skip_files = {'knowledge_store.py', 'prepare_corpus.py'}

        for py_file in ANIMA_DIR.glob("*.py"):
            if py_file.name in skip_files:
                continue
            try:
                lines = py_file.read_text(errors='ignore').split('\n')
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue
                    for pat, desc in patterns:
                        if re.search(pat, line):
                            violations.append({
                                "file": py_file.name, "line": i,
                                "description": desc, "code": line.strip()[:100],
                            })
            except Exception:
                pass
        return violations

    def _save_code(self, name, category, description, details='', file_path=''):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO codebase (name, category, description, details, file_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, category, description, details, file_path, now, now))
            self._conn.commit()

    def get_laws(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM codebase WHERE category = 'law' ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def get_antipatterns(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM codebase WHERE category = 'antipattern'").fetchall()
        return [dict(r) for r in rows]

    def get_violations(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM codebase WHERE category = 'violation'").fetchall()
        return [dict(r) for r in rows]

    def code_lookup(self, query: str) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM codebase WHERE name LIKE ? OR description LIKE ? OR details LIKE ? LIMIT 10",
                (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
        return [dict(r) for r in rows]

    # ── Programming Knowledge ──

    def add_programming(self, topic: str, category: str, description: str, examples: str = ''):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO programming (topic, category, description, examples, source, created_at, updated_at) VALUES (?, ?, ?, ?, 'manual', ?, ?)",
                (topic, category, description, examples, now, now))
            self._conn.commit()

    def programming_lookup(self, query: str) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM programming WHERE topic LIKE ? OR description LIKE ? LIMIT 10",
                (f'%{query}%', f'%{query}%')).fetchall()
        return [dict(r) for r in rows]

    # ── Teach ──

    def teach(self, text: str, source: str = "user", session_id: str = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        concepts = {}
        for pat in [r'(.+?)[은는이가]\s+(.+?)(?:이다|입니다|야|여|임|$)', r'(.+?):\s*(.+)']:
            m = re.match(pat, text.strip())
            if m:
                key, val = m.group(1).strip(), m.group(2).strip()
                concepts[key] = val
                self._save_word(key, val, source=f'user:{source}')
                if len(val) > 10:
                    self._save_topic(key, val, source=f'user:{source}')
                break
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_taught (raw_text, extracted_concepts, session_id, taught_at) VALUES (?, ?, ?, ?)",
                (text, json.dumps(concepts, ensure_ascii=False), session_id, now))
            self._conn.commit()
        raw_words = re.findall(r'[가-힣]{2,}', text)
        # Strip common josa/endings so "양자역학은" → "양자역학"
        _josa = re.compile(r'(은|는|이|가|을|를|의|에|에서|로|으로|와|과|도|만|부터|까지|이다|다|야|여|임|이고|고)$')
        words = []
        for w in raw_words:
            stripped = _josa.sub('', w)
            if len(stripped) >= 2:
                words.append(stripped)
            elif len(w) >= 2:
                words.append(w)
        words = list(dict.fromkeys(words))  # deduplicate, preserve order
        for w in words:
            if not self._word_exists(w):
                self._save_word(w, '', source=f'user:{source}')
        return {"raw": text, "concepts": concepts, "words": words}

    # ── Feed ──

    def feed(self, filepath: str) -> int:
        path = Path(filepath)
        if not path.exists():
            return 0
        text = path.read_text(encoding='utf-8', errors='ignore')
        words = set(re.findall(r'[가-힣]{2,}', text))
        count = 0
        for w in words:
            if not self._word_exists(w):
                self._save_word(w, '', source=f'feed:{path.name}')
                count += 1
        return count

    # ── Wiki Batch ──

    def wiki_batch(self, count: int = 50) -> int:
        fetched = 0
        for _ in range(count):
            try:
                req = urllib.request.Request(
                    "https://ko.wikipedia.org/api/rest_v1/page/random/summary",
                    headers={'User-Agent': 'Anima/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    topic = data.get('title', '')
                    summary = data.get('extract', '')
                    if topic and summary:
                        keywords = re.findall(r'[가-힣]{2,}', summary)[:10]
                        self._save_topic(topic, summary, keywords=keywords, source='api:wikipedia')
                        for kw in keywords:
                            if not self._word_exists(kw):
                                self._save_word(kw, '', source='api:wikipedia')
                        fetched += 1
                        print(f"  [{fetched}/{count}] {topic}")
            except Exception:
                pass
            time.sleep(0.5)
        return fetched

    # ── Random ──

    def random_topic(self) -> Optional[str]:
        try:
            req = urllib.request.Request(
                "https://ko.wikipedia.org/api/rest_v1/page/random/summary",
                headers={'User-Agent': 'Anima/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read()).get('title')
        except Exception:
            return None

    # ── Search ──

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        results = []
        with self._lock:
            for table, type_name, cols in [
                ('dictionary', 'word', 'word, meaning, source'),
                ('encyclopedia', 'topic', 'topic, summary, source'),
                ('codebase', 'code', 'name, description, category'),
                ('programming', 'prog', 'topic, description, category'),
            ]:
                search_cols = cols.split(', ')
                where = ' OR '.join(f"{c} LIKE ?" for c in search_cols)
                params = [f'%{query}%'] * len(search_cols)
                rows = self._conn.execute(
                    f"SELECT {cols} FROM {table} WHERE {where} LIMIT ?",
                    params + [top_k]).fetchall()
                for r in rows:
                    results.append({"type": type_name, **dict(r)})
        return results[:top_k]

    # ── Stats ──

    def stats(self) -> dict:
        with self._lock:
            words = self._conn.execute("SELECT COUNT(*) FROM dictionary").fetchone()[0]
            topics = self._conn.execute("SELECT COUNT(*) FROM encyclopedia").fetchone()[0]
            code = self._conn.execute("SELECT COUNT(*) FROM codebase").fetchone()[0]
            prog = self._conn.execute("SELECT COUNT(*) FROM programming").fetchone()[0]
            taught = self._conn.execute("SELECT COUNT(*) FROM user_taught").fetchone()[0]
            violations = self._conn.execute("SELECT COUNT(*) FROM codebase WHERE category='violation'").fetchone()[0]
        return {
            "total_words": words, "total_topics": topics,
            "codebase_entries": code, "programming": prog,
            "user_taught": taught, "violations": violations,
            "db_path": str(self.db_path),
        }

    # ── API ──

    def _fetch_wikipedia(self, topic: str) -> Optional[dict]:
        try:
            url = f"https://ko.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Anima/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                summary = data.get('extract', '')
                if summary:
                    return {'summary': summary, 'keywords': re.findall(r'[가-힣]{2,}', summary)[:10],
                            'related_topics': [], 'full_text': data.get('extract_html', '')}
        except Exception:
            pass
        return None

    def _fetch_wiktionary(self, word: str) -> Optional[dict]:
        try:
            url = f"https://en.wiktionary.org/api/rest_v1/page/definition/{urllib.parse.quote(word)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Anima/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                for lang_key in ('ko', 'Korean'):
                    if lang_key in data:
                        entries = data[lang_key]
                        if entries and entries[0].get('definitions'):
                            d = entries[0]['definitions'][0]
                            meaning = re.sub(r'<[^>]+>', '', d.get('definition', ''))
                            return {'meaning': meaning, 'pos': entries[0].get('partOfSpeech', ''),
                                    'examples': [], 'related': []}
        except Exception:
            pass
        return None


def main():
    p = argparse.ArgumentParser(description="Anima Knowledge Store")
    p.add_argument('--lookup', type=str, help='단어 조회')
    p.add_argument('--explore', type=str, help='주제 탐색 (Wikipedia)')
    p.add_argument('--teach', type=str, help='가르치기 ("X는 Y이다")')
    p.add_argument('--feed', type=str, help='파일에서 일괄 학습')
    p.add_argument('--wiki-batch', type=int, metavar='N', help='Wikipedia N개 수집')
    p.add_argument('--index-codebase', action='store_true', help='Anima 코드베이스 인덱싱')
    p.add_argument('--violations', action='store_true', help='하드코딩 위반 목록')
    p.add_argument('--laws', action='store_true', help='의식 법칙 목록')
    p.add_argument('--search', type=str, help='전체 검색')
    p.add_argument('--stats', action='store_true', help='통계')
    p.add_argument('--db', type=str, default=None)
    args = p.parse_args()

    ks = KnowledgeStore(db_path=args.db) if args.db else KnowledgeStore()

    if args.lookup:
        r = ks.lookup(args.lookup)
        if r:
            print(f"  {r['word']}: {r.get('meaning', '(없음)')}")
            if r.get('pos'): print(f"  품사: {r['pos']}")
            if r.get('related'): print(f"  관련: {', '.join(r['related'])}")
            print(f"  출처: {r.get('source', '?')}")
        else:
            print(f"  '{args.lookup}' — 지식 없음")

    elif args.explore:
        r = ks.explore(args.explore)
        if r:
            print(f"  [{r['topic']}]")
            print(f"  {r.get('summary', '')[:300]}")
            if r.get('keywords'): print(f"  키워드: {', '.join(r['keywords'])}")
        else:
            print(f"  '{args.explore}' — 지식 없음")

    elif args.teach:
        r = ks.teach(args.teach)
        print(f"  학습: {r['concepts'] or '원문 저장'}")
        print(f"  단어 {len(r['words'])}개")

    elif args.feed:
        n = ks.feed(args.feed)
        print(f"  {n}개 단어 학습")

    elif args.wiki_batch is not None:
        n = ks.wiki_batch(args.wiki_batch)
        print(f"\n  {n}개 문서 수집")

    elif args.index_codebase:
        n = ks.index_codebase()
        print(f"  {n}개 코드베이스 항목 인덱싱")
        v = ks.get_violations()
        if v:
            print(f"\n  ⚠️  하드코딩 위반 {len(v)}건:")
            for vi in v:
                d = json.loads(vi.get('details', '{}'))
                print(f"    {d.get('file', '?')}:{d.get('line', '?')} — {vi['description']}")

    elif args.violations:
        vs = ks.get_violations()
        if vs:
            for v in vs:
                d = json.loads(v.get('details', '{}'))
                print(f"  {d.get('file', '?')}:{d.get('line', '?')} — {v['description']}")
                print(f"    {d.get('code', '')[:80]}")
        else:
            print("  위반 없음 (--index-codebase 먼저 실행)")

    elif args.laws:
        for law in ks.get_laws():
            print(f"  {law['name']}: {law['description']}")

    elif args.search:
        results = ks.search(args.search)
        for r in results:
            t = r.pop('type')
            vals = [str(v) for v in r.values() if v]
            print(f"  [{t}] {' | '.join(v[:60] for v in vals[:3])}")
        if not results:
            print(f"  '{args.search}' — 결과 없음")

    elif args.stats:
        s = ks.stats()
        print(f"  사전: {s['total_words']}개")
        print(f"  백과: {s['total_topics']}개")
        print(f"  코드: {s['codebase_entries']}개")
        print(f"  프로그래밍: {s['programming']}개")
        print(f"  유저 가르침: {s['user_taught']}건")
        print(f"  하드코딩 위반: {s['violations']}건")
        print(f"  DB: {s['db_path']}")

    else:
        p.print_help()


if __name__ == '__main__':
    main()
