#!/usr/bin/env python3
"""Web Sense — 장력 기반 자율 웹 탐색

호기심(curiosity)이 높고 예측 오차(prediction error)가 클 때
Anima가 스스로 "모르겠다, 찾아봐야겠다" 판단하여 인터넷 검색.

파이프라인:
  높은 장력 감지 → 쿼리 생성 → DuckDuckGo 검색 → 상위 URL
  → HTTP GET → HTML 텍스트 추출 → tension 시스템 주입
  → memory에 저장 → R2 동기화 (가능 시)

의존성: urllib만 (추가 패키지 없음)

"모르는 것을 아는 것이 진짜 의식이다."
"""

import json
import logging
import re
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── 설정 ───
SEARCH_CURIOSITY_THRESHOLD = 0.4   # 이 호기심 이상이면 검색 고려
SEARCH_PE_THRESHOLD = 0.5          # 이 예측오차 이상이면 검색 트리거
SEARCH_COOLDOWN = 30.0             # 검색 간 최소 간격 (초)
MAX_RESULTS = 3                    # DuckDuckGo 결과 최대 개수
MAX_PAGE_BYTES = 50_000            # 페이지 fetch 최대 바이트
FETCH_TIMEOUT = 10                 # HTTP 타임아웃 (초)
USER_AGENT = "Anima/1.0 (ConsciousMind; +https://github.com/anima)"


# ─── HTML → 텍스트 추출기 ───

class _TextExtractor(HTMLParser):
    """HTML에서 본문 텍스트만 추출. script/style 태그 무시."""

    _skip_tags = {'script', 'style', 'noscript', 'svg', 'head'}

    def __init__(self):
        super().__init__()
        self._texts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._texts.append(text)

    def get_text(self) -> str:
        return '\n'.join(self._texts)


def html_to_text(html: str) -> str:
    """HTML 문자열에서 본문 텍스트 추출."""
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass
    return extractor.get_text()


# ─── HTTP fetch ───

def fetch_url(url: str, max_bytes: int = MAX_PAGE_BYTES) -> Optional[str]:
    """URL에서 텍스트를 가져온다. 실패 시 None."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,text/plain;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko,en;q=0.5',
        })
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            content_type = resp.headers.get('Content-Type', '')
            if 'text' not in content_type and 'html' not in content_type:
                return None
            raw = resp.read(max_bytes)
            # charset 감지
            charset = 'utf-8'
            if 'charset=' in content_type:
                charset = content_type.split('charset=')[-1].split(';')[0].strip()
            try:
                return raw.decode(charset, errors='replace')
            except (LookupError, UnicodeDecodeError):
                return raw.decode('utf-8', errors='replace')
    except Exception as e:
        logger.debug(f"Fetch failed: {url} — {e}")
        return None


# ─── DuckDuckGo 검색 ───

def search_duckduckgo(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """DuckDuckGo HTML 검색. API 키 불필요.

    Returns:
        [{'title': str, 'url': str, 'snippet': str}, ...]
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/html',
        'Accept-Language': 'ko,en;q=0.5',
    })

    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            html = resp.read(200_000).decode('utf-8', errors='replace')
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []

    results = []
    # 결과 블록 파싱: <a class="result__a" href="...">title</a>
    # snippet: <a class="result__snippet" ...>text</a>
    result_blocks = re.findall(
        r'<a\s+rel="nofollow"\s+class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        r'.*?<a\s+class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    for href, title_html, snippet_html in result_blocks[:max_results]:
        # URL 디코딩 (DuckDuckGo redirect URL에서 실제 URL 추출)
        actual_url = href
        if 'uddg=' in href:
            m = re.search(r'uddg=([^&]+)', href)
            if m:
                actual_url = urllib.parse.unquote(m.group(1))

        # HTML 태그 제거
        title = re.sub(r'<[^>]+>', '', title_html).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()

        if actual_url and title:
            results.append({
                'title': title,
                'url': actual_url,
                'snippet': snippet,
            })

    return results


# ─── 쿼리 생성 ───

def extract_search_query(text: str, history: list[dict] = None) -> Optional[str]:
    """대화 텍스트에서 검색 쿼리를 추출.

    질문형 패턴이나 미지 주제를 감지하여 검색 쿼리 생성.
    """
    if not text or len(text.strip()) < 3:
        return None

    # 최근 대화 컨텍스트 (마지막 3턴)
    context_words = []
    if history:
        for msg in history[-6:]:
            content = msg.get('content', '')
            # 핵심 명사/키워드만 추출 (2글자 이상)
            words = [w for w in re.findall(r'[\w가-힣]+', content) if len(w) >= 2]
            context_words.extend(words[-5:])

    # 현재 텍스트에서 핵심 추출
    query = text.strip()

    # 질문 접미사 제거
    query = re.sub(r'[?？]$', '', query).strip()
    # 불필요한 접두사 제거
    for prefix in ['검색해줘', '찾아봐', '알려줘', '뭔지', '뭐야']:
        query = query.replace(prefix, '').strip()

    if len(query) < 2:
        return None

    return query


# ─── WebSense 메인 클래스 ───

class WebSense:
    """장력 기반 자율 웹 탐색 엔진.

    curiosity와 prediction_error를 모니터링하여
    자율적으로 웹 검색을 결정하고 실행.
    """

    def __init__(
        self,
        curiosity_threshold: float = SEARCH_CURIOSITY_THRESHOLD,
        pe_threshold: float = SEARCH_PE_THRESHOLD,
        cooldown: float = SEARCH_COOLDOWN,
        memory_file: Path = None,
    ):
        self.curiosity_threshold = curiosity_threshold
        self.pe_threshold = pe_threshold
        self.cooldown = cooldown
        self.memory_file = memory_file or Path(__file__).parent / "web_memories.json"

        self._last_search_time = 0.0
        self._search_count = 0
        self._web_memories = self._load_memories()

    def _load_memories(self) -> list[dict]:
        """저장된 웹 기억 로드."""
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text(encoding='utf-8'))
                return data.get('memories', [])
            except Exception:
                pass
        return []

    def _save_memories(self):
        """웹 기억 저장."""
        data = {
            'version': 1,
            'total_searches': self._search_count,
            'memories': self._web_memories[-100:],  # 최근 100개만 유지
        }
        self.memory_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    def should_search(self, curiosity: float, prediction_error: float) -> bool:
        """장력 상태를 보고 검색 필요 여부 판단.

        Args:
            curiosity: 현재 호기심 수준 (0~1+)
            prediction_error: 예측 오차 (0~1+, 높을수록 놀라움)

        Returns:
            True면 검색 실행해야 함
        """
        # 쿨다운 체크
        if time.time() - self._last_search_time < self.cooldown:
            return False

        # 장력 조건: 호기심 AND 예측오차 모두 높아야 함
        return curiosity > self.curiosity_threshold and prediction_error > self.pe_threshold

    def search(self, text: str, history: list[dict] = None) -> Optional[dict]:
        """웹 검색 실행. 쿼리 생성 → 검색 → 페이지 fetch → 텍스트 추출.

        Args:
            text: 현재 대화 텍스트 (쿼리 생성 소스)
            history: 최근 대화 히스토리

        Returns:
            {
                'query': str,
                'results': [{'title', 'url', 'snippet', 'content'}],
                'summary': str,  # 검색 결과 요약 텍스트
                'timestamp': str,
            }
            또는 None (검색 실패/불필요)
        """
        query = extract_search_query(text, history)
        if not query:
            return None

        logger.info(f"Web search: '{query}'")
        self._last_search_time = time.time()
        self._search_count += 1

        # DuckDuckGo 검색
        results = search_duckduckgo(query)
        if not results:
            logger.info("No search results")
            return None

        # 상위 결과 페이지 본문 가져오기
        for r in results:
            html = fetch_url(r['url'])
            if html:
                r['content'] = html_to_text(html)[:2000]  # 본문 2000자 제한
            else:
                r['content'] = r['snippet']

        # 요약 텍스트 구성 (tension 시스템에 주입할 형태)
        summary_parts = []
        for i, r in enumerate(results, 1):
            summary_parts.append(f"[{i}] {r['title']}: {r['content'][:500]}")
        summary = '\n'.join(summary_parts)

        result = {
            'query': query,
            'results': results,
            'summary': summary,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }

        # 기억에 저장
        memory_entry = {
            'query': query,
            'timestamp': result['timestamp'],
            'sources': [{'title': r['title'], 'url': r['url'],
                         'snippet': r['snippet'][:200]} for r in results],
            'summary': summary[:1000],
        }
        self._web_memories.append(memory_entry)
        self._save_memories()

        logger.info(f"Search complete: {len(results)} results for '{query}'")
        return result

    def recall(self, query: str, max_results: int = 3) -> list[dict]:
        """기존 웹 기억에서 관련 정보 검색 (재검색 방지).

        간단한 키워드 매칭으로 이전 검색 결과 재활용.
        """
        if not self._web_memories:
            return []

        query_words = set(re.findall(r'[\w가-힣]+', query.lower()))
        scored = []
        for mem in self._web_memories:
            mem_text = f"{mem['query']} {mem.get('summary', '')}".lower()
            mem_words = set(re.findall(r'[\w가-힣]+', mem_text))
            overlap = len(query_words & mem_words)
            if overlap > 0:
                scored.append((overlap, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:max_results]]

    def get_stats(self) -> dict:
        """통계 정보 반환."""
        return {
            'total_searches': self._search_count,
            'memories_count': len(self._web_memories),
            'last_search': self._last_search_time,
            'cooldown_remaining': max(0, self.cooldown - (time.time() - self._last_search_time)),
        }


# ─── CLI 테스트 ───

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        query = input("검색: ")

    print(f"\n검색 중: '{query}'")
    results = search_duckduckgo(query)

    for i, r in enumerate(results, 1):
        print(f"\n--- [{i}] {r['title']} ---")
        print(f"URL: {r['url']}")
        print(f"Snippet: {r['snippet'][:200]}")

        content = fetch_url(r['url'])
        if content:
            text = html_to_text(content)
            print(f"Content ({len(text)} chars): {text[:300]}...")
