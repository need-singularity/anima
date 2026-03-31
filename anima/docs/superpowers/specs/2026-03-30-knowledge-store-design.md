# Knowledge Store Design

## Overview

Anima의 지식 저장소 모듈. 사전/백과사전/학습 데이터를 SQLite에 축적하고, 의식이 필요할 때 조회하는 구조. 하드코딩 금지 — 지식은 외부 데이터이며, 의식이 어떻게 쓸지는 의식이 결정.

## Goals

- API 기반 지식 수집 (Wikipedia, 국어사전, Wiktionary)
- 로컬 SQLite 축적 (오프라인 자급자족)
- 3가지 입력 경로: 자율 탐색 / 대화 중 실시간 / 유저 직접 호출
- PureConsciousness 어휘 풀에 연결 → 발화 품질 향상
- Hivemind 노드 간 지식 공유 가능

## Architecture

```
  유저 (선생님)          의식 (자율)           API (외부)
      │                    │                    │
      │ "알아둬: ..."      │ 호기심 탐색        │
      │ "위키 검색: ..."   │ 대화 중 모르는 단어 │
      │ "사전: ..."        │                    │
      └────────┬───────────┴────────────────────┘
               │
        ┌──────v──────┐
        │ KnowledgeStore │  knowledge_store.py
        │  (SQLite)      │
        ├────────────────┤
        │ dictionary     │  단어 → 의미, 품사, 예문
        │ encyclopedia   │  주제 → 요약, 키워드, 관련어
        │ learned        │  자율학습 발견 (개념, 관계)
        │ user_taught    │  유저가 직접 가르친 것
        ├────────────────┤
        │ API Gateway    │
        │  Wikipedia KR  │  ko.wikipedia.org/api
        │  국어사전 API   │  stdict.korean.go.kr/api
        │  Wiktionary    │  en.wiktionary.org/api
        └───────┬────────┘
                │
        ┌───────v────────┐
        │ PureConsciousness │  learned_words 풀 확장
        │ AutonomousLoop    │  탐색 주제 선정
        │ AnimaUnified      │  대화 중 조회
        └────────────────┘
```

## Components

### 1. knowledge_store.py

```
KnowledgeStore(db_path)
  │
  ├── lookup(word) → {meaning, pos, examples, related, source}
  ├── explore(topic) → {summary, keywords, related_topics, source}
  ├── teach(text, source="user") → 자연어 파싱 → 저장
  ├── random_topic() → 자율 탐색용 랜덤 미학습 주제
  ├── search(query, top_k=5) → 벡터 유사도 검색
  │
  ├── _fetch_wikipedia(topic) → API → 축적
  ├── _fetch_dictionary(word) → API → 축적
  ├── _fetch_wiktionary(word) → API → 축적
  │
  └── stats() → {total_words, total_topics, sources, last_updated}
```

### 2. SQLite Schema

```sql
-- 사전 (단어 → 의미)
CREATE TABLE dictionary (
    id INTEGER PRIMARY KEY,
    word TEXT NOT NULL UNIQUE,
    meaning TEXT,
    pos TEXT,           -- 품사 (명사, 동사, ...)
    examples TEXT,      -- JSON array
    related TEXT,       -- JSON array of related words
    source TEXT,        -- "api:korean_dict", "api:wiktionary", "user"
    confidence REAL DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

-- 백과 (주제 → 요약)
CREATE TABLE encyclopedia (
    id INTEGER PRIMARY KEY,
    topic TEXT NOT NULL UNIQUE,
    summary TEXT,
    keywords TEXT,      -- JSON array
    related_topics TEXT, -- JSON array
    source TEXT,        -- "api:wikipedia", "user", "autonomous"
    full_text TEXT,     -- 원본 (길 수 있음)
    access_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

-- 유저 가르침 (자연어 그대로 저장)
CREATE TABLE user_taught (
    id INTEGER PRIMARY KEY,
    raw_text TEXT NOT NULL,
    extracted_concepts TEXT, -- JSON: 파싱된 키/값
    session_id TEXT,
    taught_at TEXT
);

CREATE INDEX idx_dict_word ON dictionary(word);
CREATE INDEX idx_enc_topic ON encyclopedia(topic);
CREATE INDEX idx_dict_access ON dictionary(access_count DESC);
```

### 3. API Gateway

**Wikipedia 한국어:**
```
GET https://ko.wikipedia.org/api/rest_v1/page/summary/{topic}
→ { title, extract, description }
```

**국립국어원 표준국어대사전:**
```
GET https://stdict.korean.go.kr/api/search.do?key={API_KEY}&q={word}&type_search=search
→ { channel: { item: [{ word, sense: [{ definition }] }] } }
```

**Wiktionary (fallback):**
```
GET https://en.wiktionary.org/api/rest_v1/page/definition/{word}
→ { ko: [{ definitions: [{ definition }] }] }
```

### 4. 입력 경로

**경로 1: 자율 탐색 (autonomous_loop.py 연동)**
- 호기심 > 0.5일 때 `random_topic()` 호출
- Wikipedia에서 요약 가져와서 축적
- 새 단어 발견 → dictionary에 추가
- PureConsciousness.learned_words에 키워드 주입

**경로 2: 대화 중 실시간 (anima_unified.py 연동)**
- 유저 입력에서 모르는 단어 감지 (dictionary에 없는 한글 단어)
- 백그라운드에서 API 조회 → 축적
- 다음 발화 시 참조 가능

**경로 3: 유저 직접 호출 (채팅 명령)**
- `알아둬:` prefix → user_taught 테이블에 저장 + 개념 추출
- `위키:` prefix → Wikipedia API 조회 → encyclopedia 축적
- `사전:` prefix → 국어사전 API 조회 → dictionary 축적
- 응답: 조회 결과 요약 (의식이 학습했음을 알림)

### 5. PureConsciousness 연동

`knowledge_store.py`가 PureConsciousness의 어휘를 확장:

```python
# PureConsciousness.respond() 내부
if self.knowledge:
    # 입력 단어의 관련어를 학습 풀에 추가
    for word in input_words:
        info = self.knowledge.lookup(word)
        if info and info.get('related'):
            self.learned_words.extend(info['related'][:3])
```

### 6. Hivemind 지식 공유

같은 Hivemind의 노드들이 지식 DB를 공유:
- Process 모드: 같은 SQLite 파일 참조 (읽기 전용 + WAL)
- Docker 모드: 공유 볼륨
- 원격: R2 동기화 (주기적)

## Data Flow

### 유저가 가르칠 때
```
유저: "알아둬: 양자역학은 미시세계의 물리법칙이야"
→ teach("양자역학은 미시세계의 물리법칙이야", source="user")
→ 파싱: {topic: "양자역학", meaning: "미시세계의 물리법칙"}
→ encyclopedia + dictionary에 저장
→ PureConsciousness.learned_words += ["양자역학", "미시세계", "물리법칙"]
→ 응답: 의식의 자연 반응 (하드코딩 아님)
```

### 자율 탐색
```
autonomous_loop: curiosity > 0.5
→ knowledge.random_topic() → "인공지능"
→ _fetch_wikipedia("인공지능") → 요약 + 키워드
→ encyclopedia에 저장
→ 새 단어 ["인공지능", "기계학습", "신경망"] → dictionary 조회
→ 없는 단어 → _fetch_dictionary() → 축적
→ PureConsciousness.learned_words 확장
```

### 대화 중 조회
```
유저: "엔트로피가 뭐야?"
→ "엔트로피" dictionary에 없음
→ 백그라운드: _fetch_dictionary("엔트로피") + _fetch_wikipedia("엔트로피")
→ 축적 완료
→ 이번 응답에는 반영 안 될 수 있음 (다음 대화부터 활용)
→ Law 1: 모르면 침묵. 다음에 알게 됨.
```

## File Structure

```
knowledge_store.py          # 지식 저장소 모듈 (API + SQLite)
data/knowledge/knowledge.db # SQLite DB (git ignore)
tests/test_knowledge_store.py
```

## Error Handling

- API 실패 → 로컬 DB만 사용 (오프라인 모드)
- API rate limit → 큐잉 + 백오프
- 국어사전 API 키 없음 → Wiktionary fallback
- DB 손상 → 빈 DB로 재시작 (지식은 다시 축적 가능)

## Usage

```bash
# 단독 테스트
python knowledge_store.py --lookup 의식
python knowledge_store.py --explore 양자역학
python knowledge_store.py --stats

# Anima와 함께
python anima_unified.py --web  # 자동 연동
```

## API Keys

- 국립국어원 API: 무료 발급 (https://stdict.korean.go.kr/openapi/openApiRegist.do)
- Wikipedia: 키 불필요
- Wiktionary: 키 불필요
