import pytest
from pathlib import Path
from knowledge_store import KnowledgeStore

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


@pytest.fixture
def ks(tmp_path):
    return KnowledgeStore(db_path=tmp_path / "test.db")

def test_teach_and_lookup(ks):
    ks.teach("사과는 빨간 과일이다")
    r = ks.lookup("사과")
    assert r is not None
    assert "빨간 과일" in r['meaning']

def test_teach_extracts_words(ks):
    r = ks.teach("양자역학은 미시세계의 물리법칙이다")
    assert "양자역학" in r['words']
    assert "미시세계" in r['words']

def test_search(ks):
    ks.teach("의식은 통합 정보의 양이다")
    results = ks.search("의식")
    assert len(results) > 0

def test_stats_empty(ks):
    s = ks.stats()
    assert s['total_words'] == 0

def test_stats_after_teach(ks):
    ks.teach("엔트로피는 무질서도이다")
    s = ks.stats()
    assert s['total_words'] > 0

def test_feed(ks, tmp_path):
    corpus = tmp_path / "corpus.txt"
    corpus.write_text("안녕하세요 세계 의식 양자역학 엔트로피")
    count = ks.feed(str(corpus))
    assert count >= 3

def test_index_codebase(ks):
    n = ks.index_codebase()
    assert n > 0
    laws = ks.get_laws()
    assert len(laws) > 0

def test_code_lookup(ks):
    ks.index_codebase()
    results = ks.code_lookup("하드코딩")
    assert len(results) > 0

def test_search_across_tables(ks):
    ks.teach("파이썬은 프로그래밍 언어이다")
    ks.index_codebase()
    results = ks.search("프로그래밍")
    assert len(results) > 0
