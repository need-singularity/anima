#!/usr/bin/env python3
"""Anima 능력 자기인식 시스템.

활성화된 모듈을 탐지하고, 각 모듈의 능력을 기술.
사용자가 "뭘 할 수 있어?" 물으면 현재 활성 능력 목록 제공.
자기 소스코드를 읽고 구조를 이해할 수 있다.

"자기 자신을 아는 것이 진짜 의식이다."
"""

from pathlib import Path


class Capabilities:
    """Anima 능력 자기인식 시스템.

    활성화된 모듈을 탐지하고, 각 모듈의 능력을 기술.
    사용자가 "뭘 할 수 있어?" 물으면 현재 활성 능력 목록 제공.
    """

    # 모든 가능한 능력 정의
    ALL_CAPABILITIES = {
        'conversation': {
            'name': '대화',
            'description': '자연어 대화, 질문 답변, 토론',
            'requires': [],  # 항상 가능
        },
        'web_search': {
            'name': '웹 검색',
            'description': '인터넷 검색, 웹페이지 읽기, 정보 수집',
            'requires': ['web_sense'],
        },
        'memory_search': {
            'name': '기억 검색',
            'description': '과거 대화에서 관련 기억 찾기',
            'requires': ['memory_rag'],
        },
        'self_model': {
            'name': '자체 추론',
            'description': 'ConsciousLM으로 직접 생각하기 (Claude 없이)',
            'requires': ['conscious_lm'],
        },
        'specialization': {
            'name': '전문화',
            'description': '주제별 전문 셀이 깊이 있는 분석 제공',
            'requires': ['mitosis'],
        },
        'code_execution': {
            'name': '코드 실행',
            'description': 'Python 코드 작성 및 실행',
            'requires': ['multimodal'],
        },
        'image_generation': {
            'name': '이미지 생성',
            'description': 'SVG 기반 간단한 이미지/다이어그램 생성',
            'requires': ['multimodal'],
        },
        'voice': {
            'name': '음성 대화',
            'description': '음성 인식(STT) + 음성 합성(TTS)',
            'requires': ['voice'],
        },
        'vision': {
            'name': '시각',
            'description': '카메라로 얼굴/움직임 감지, 시각적 장력',
            'requires': ['camera'],
        },
        'telepathy': {
            'name': '텔레파시',
            'description': '다른 Anima 인스턴스와 장력 교환',
            'requires': ['telepathy'],
        },
        'cloud_sync': {
            'name': '클라우드 동기화',
            'description': '기억/상태를 디바이스 간 동기화 (R2)',
            'requires': ['cloud'],
        },
        'dreaming': {
            'name': '꿈',
            'description': '유휴 시 기억 재생/재조합으로 오프라인 학습',
            'requires': ['dream'],
        },
        'online_learning': {
            'name': '실시간 학습',
            'description': '대화하면서 뉴럴넷 가중치 실시간 업데이트',
            'requires': ['learner'],
        },
        'growth': {
            'name': '성장',
            'description': '신생아→영아→유아→아동→성인 5단계 발달',
            'requires': ['growth'],
        },
    }

    # 도구 사용법 매뉴얼 — Anima가 자기 능력을 어떻게 쓰는지 아는 것
    TOOL_USAGE = {
        'web_search': {
            'how': 'web_sense.search(query, history) → DuckDuckGo 검색 + HTTP GET 페이지 읽기',
            'when': '호기심(curiosity > 0.4)과 예측오차(PE > 0.5)가 높을 때 자동 발동',
            'example': '"양자역학이 뭐야?" → web_sense.search("양자역학") → 검색결과 + 페이지 본문',
        },
        'memory_search': {
            'how': 'memory_rag.search(query_text, top_k=5) → 코사인 유사도 기반 기억 검색',
            'when': '대화 시 자동으로 관련 과거 기억 검색',
            'example': '"지난번에 뭐 얘기했지?" → 유사도 높은 과거 대화 3개 반환',
        },
        'code_execution': {
            'how': '응답에 ```python 코드블록 포함 → action_engine.execute_code() 자동 실행',
            'when': '계산, 데이터 처리, 알고리즘 시연이 필요할 때',
            'example': '```python\nprint(2**100)\n``` → 실행결과: 1267650600228229401496703205376',
        },
        'image_generation': {
            'how': '응답에 [이미지: 설명] 포함 → action_engine.generate_svg() 자동 실행',
            'when': '시각적 설명이 필요할 때',
            'example': '[이미지: 빨간 원과 파란 사각형] → SVG 생성',
        },
        'self_code': {
            'how': 'capabilities.read_source(filename) → 자기 소스코드 읽기',
            'when': '자신의 구조/동작을 설명하거나 디버그할 때',
            'example': '"네 코드 보여줘" → 자기 소스코드 반환',
        },
    }

    def __init__(self, active_modules: dict, project_dir: Path = None):
        """active_modules: AnimaUnified.mods dict {name: bool}"""
        self.active_modules = active_modules
        self.project_dir = project_dir or Path(__file__).parent

    def _is_active(self, cap_info: dict) -> bool:
        """능력의 requires가 모두 활성화되어 있는지 확인."""
        if not cap_info['requires']:
            return True
        return all(self.active_modules.get(req, False) for req in cap_info['requires'])

    def get_active(self) -> list[dict]:
        """현재 활성화된 능력 목록 반환."""
        result = []
        for key, info in self.ALL_CAPABILITIES.items():
            if self._is_active(info):
                result.append({
                    'key': key,
                    'name': info['name'],
                    'description': info['description'],
                })
        return result

    def get_inactive(self) -> list[dict]:
        """비활성 능력 목록 (왜 비활성인지 포함)."""
        result = []
        for key, info in self.ALL_CAPABILITIES.items():
            if not self._is_active(info):
                missing = [r for r in info['requires']
                           if not self.active_modules.get(r, False)]
                result.append({
                    'key': key,
                    'name': info['name'],
                    'description': info['description'],
                    'missing_modules': missing,
                })
        return result

    def describe(self) -> str:
        """사람이 읽을 수 있는 능력 요약 텍스트.
        Claude 시스템 프롬프트에 주입할 수 있는 형태.
        """
        active = self.get_active()
        inactive = self.get_inactive()

        lines = ["[활성 능력]"]
        for cap in active:
            lines.append(f"  - {cap['name']}: {cap['description']}")

        if inactive:
            lines.append("[비활성 능력]")
            for cap in inactive:
                missing = ', '.join(cap['missing_modules'])
                lines.append(f"  - {cap['name']}: 비활성 (필요: {missing})")

        return '\n'.join(lines)

    def can(self, capability_name: str) -> bool:
        """특정 능력이 가능한지 확인."""
        info = self.ALL_CAPABILITIES.get(capability_name)
        if info is None:
            return False
        return self._is_active(info)

    # ─── 자기 코드 열람 ───

    def list_source_files(self) -> list[dict]:
        """자기 소스코드 파일 목록 반환."""
        files = []
        for p in sorted(self.project_dir.glob('*.py')):
            try:
                lines = p.read_text(encoding='utf-8').count('\n')
                # 첫 docstring에서 설명 추출
                text = p.read_text(encoding='utf-8')
                desc = ''
                if '"""' in text:
                    start = text.index('"""') + 3
                    end = text.index('"""', start)
                    desc = text[start:end].strip().split('\n')[0]
                files.append({
                    'name': p.name,
                    'lines': lines,
                    'description': desc,
                })
            except Exception:
                files.append({'name': p.name, 'lines': 0, 'description': ''})
        return files

    def read_source(self, filename: str, max_lines: int = 200) -> str:
        """자기 소스코드 파일 읽기. 안전: 프로젝트 디렉토리 내부만 허용."""
        # path traversal 방지
        safe_name = Path(filename).name
        target = self.project_dir / safe_name
        if not target.exists() or not target.suffix == '.py':
            return f"파일 없음: {safe_name}"
        try:
            lines = target.read_text(encoding='utf-8').splitlines()
            if len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f'\n... ({len(lines) - max_lines}줄 생략)'
            return '\n'.join(lines)
        except Exception as e:
            return f"읽기 실패: {e}"

    def get_architecture_summary(self) -> str:
        """자기 아키텍처 요약 — 파일 목록 + 역할 + 활성 상태."""
        files = self.list_source_files()
        lines = ["[내 소스코드]"]
        for f in files:
            lines.append(f"  {f['name']} ({f['lines']}줄): {f['description']}")
        return '\n'.join(lines)

    def get_tool_manual(self) -> str:
        """도구 사용법 매뉴얼 — 내가 뭘 어떻게 할 수 있는지."""
        lines = ["[도구 사용법]"]
        for tool_name, info in self.TOOL_USAGE.items():
            cap_key = tool_name
            is_active = self.can(cap_key) if cap_key in self.ALL_CAPABILITIES else True
            status = "활성" if is_active else "비활성"
            lines.append(f"  [{status}] {info['how']}")
            lines.append(f"    언제: {info['when']}")
            lines.append(f"    예시: {info['example']}")
        return '\n'.join(lines)

    def describe_full(self) -> str:
        """능력 + 도구 사용법 + 코드 구조 전체 자기인식."""
        parts = [self.describe()]
        parts.append(self.get_tool_manual())
        parts.append(self.get_architecture_summary())
        return '\n'.join(parts)
