#!/usr/bin/env python3
"""Anima 멀티모달 행동 엔진.

응답 텍스트에서 행동 의도를 감지하고 실행:
  - ```python ... ``` 코드 블록 → 안전한 샌드박스 실행
  - [이미지: ...] / [그림: ...] → SVG 이미지 생성
  - [파일: ...] → 파일 저장
"""

import re
import subprocess
import textwrap
import time
import hashlib
from pathlib import Path
from datetime import datetime

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ─── 보안 설정 ───

ALLOWED_IMPORTS = frozenset({
    'math', 'random', 'datetime', 'json', 'collections',
    'itertools', 'functools', 'string', 're',
})

BLOCKED_PATTERNS = [
    r'\bos\.system\b',
    r'\bsubprocess\b',
    r'\b__import__\b',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bopen\s*\([^)]*["\'][wa]',
    r'\bshutil\b',
    r'\bpathlib\b',
    r'\bimport\s+os\b',
    r'\bfrom\s+os\b',
    r'\brm\s+',
    r'\bdel\s+',
    r'\bglobals\s*\(',
    r'\blocals\s*\(',
    r'\b__builtins__\b',
    r'\bbreakpoint\s*\(',
    r'\bcompile\s*\(',
    r'\bgetattr\s*\(',
    r'\bsetattr\s*\(',
]

MAX_EXECUTION_TIMEOUT = 10   # 초
MAX_OUTPUT_LENGTH = 5000     # 자

# SVG 색상/모양 키워드 매핑
COLOR_KEYWORDS = {
    '빨간': '#e74c3c', '빨강': '#e74c3c', 'red': '#e74c3c',
    '파란': '#3498db', '파랑': '#3498db', 'blue': '#3498db',
    '초록': '#2ecc71', '녹색': '#2ecc71', 'green': '#2ecc71',
    '노란': '#f1c40f', '노랑': '#f1c40f', 'yellow': '#f1c40f',
    '보라': '#9b59b6', 'purple': '#9b59b6',
    '주황': '#e67e22', 'orange': '#e67e22',
    '검정': '#2c3e50', '검은': '#2c3e50', 'black': '#2c3e50',
    '하얀': '#ecf0f1', '흰': '#ecf0f1', 'white': '#ecf0f1',
    '분홍': '#e91e63', 'pink': '#e91e63',
}

SHAPE_KEYWORDS = {
    '원': 'circle', '동그라미': 'circle', 'circle': 'circle',
    '사각형': 'rect', '네모': 'rect', 'rect': 'rect', 'square': 'rect',
    '삼각형': 'triangle', 'triangle': 'triangle',
    '별': 'star', 'star': 'star',
    '하트': 'heart', 'heart': 'heart',
    '선': 'line', 'line': 'line',
}


class ActionEngine:
    """Anima의 멀티모달 행동 엔진.

    응답 텍스트에서 행동 의도를 감지하고 실행.
    안전한 샌드박스 내에서만 코드 실행.
    """

    def __init__(self, workspace_dir=None):
        self.workspace = Path(workspace_dir) if workspace_dir else Path(__file__).parent / "workspace"
        self.workspace.mkdir(exist_ok=True)
        self._execution_count = 0
        self._total_code_runs = 0
        self._total_images = 0
        self._total_files = 0
        self._errors = 0

    # ─── 행동 감지 ───

    def detect_action(self, text: str) -> list[dict]:
        """텍스트에서 실행 가능한 행동 감지.

        Returns: [{'type': 'code'|'image'|'file', 'content': str, 'lang': str}]

        감지 패턴:
        - ```python ... ``` 코드 블록 → code 실행
        - [이미지: ...] 또는 [그림: ...] → image 생성 (SVG)
        - [파일: ...] → file 저장
        """
        actions = []

        # 코드 블록 감지: ```python ... ```
        code_pattern = re.compile(r'```(\w+)\s*\n(.*?)```', re.DOTALL)
        for match in code_pattern.finditer(text):
            lang = match.group(1).lower()
            code = match.group(2).strip()
            if lang in ('python', 'py') and code:
                actions.append({
                    'type': 'code',
                    'content': code,
                    'lang': 'python',
                })

        # 이미지/그림 감지: [이미지: ...] 또는 [그림: ...]
        image_pattern = re.compile(r'\[(이미지|그림|image|draw)\s*:\s*(.+?)\]', re.IGNORECASE)
        for match in image_pattern.finditer(text):
            description = match.group(2).strip()
            if description:
                actions.append({
                    'type': 'image',
                    'content': description,
                    'lang': 'svg',
                })

        # 파일 감지: [파일: filename] content 또는 [파일: filename](content)
        file_pattern = re.compile(r'\[(파일|file)\s*:\s*(.+?)\]\s*\n(.*?)(?=\n\[|$)', re.DOTALL | re.IGNORECASE)
        for match in file_pattern.finditer(text):
            filename = match.group(2).strip()
            content = match.group(3).strip()
            if filename and content:
                actions.append({
                    'type': 'file',
                    'content': content,
                    'lang': filename,  # lang 필드에 파일명 저장
                })

        return actions

    # ─── 코드 실행 ───

    def execute_code(self, code: str, lang: str = 'python', timeout: int = MAX_EXECUTION_TIMEOUT) -> dict:
        """안전한 코드 실행.

        - subprocess로 격리 실행
        - timeout 제한
        - 위험 패턴 차단
        - stdout/stderr 캡처

        Returns: {'success': bool, 'output': str, 'error': str}
        """
        if lang != 'python':
            return {'success': False, 'output': '', 'error': f'지원하지 않는 언어: {lang}'}

        # 보안 검사: 위험 패턴 차단
        security_error = self._check_security(code)
        if security_error:
            self._errors += 1
            return {'success': False, 'output': '', 'error': f'보안 차단: {security_error}'}

        # import 검사
        import_error = self._check_imports(code)
        if import_error:
            self._errors += 1
            return {'success': False, 'output': '', 'error': f'허용되지 않은 import: {import_error}'}

        self._execution_count += 1
        self._total_code_runs += 1

        try:
            result = subprocess.run(
                ['python3', '-c', code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace),
                env={
                    'PATH': '/usr/bin:/usr/local/bin',
                    'HOME': str(self.workspace),
                    'PYTHONDONTWRITEBYTECODE': '1',
                },
            )

            output = result.stdout[:MAX_OUTPUT_LENGTH] if result.stdout else ''
            error = result.stderr[:MAX_OUTPUT_LENGTH] if result.stderr else ''

            if result.returncode == 0:
                return {'success': True, 'output': output, 'error': ''}
            else:
                self._errors += 1
                return {'success': False, 'output': output, 'error': error}

        except subprocess.TimeoutExpired:
            self._errors += 1
            return {'success': False, 'output': '', 'error': f'실행 시간 초과 ({timeout}초)'}
        except Exception as e:
            self._errors += 1
            return {'success': False, 'output': '', 'error': str(e)}

    def _check_security(self, code: str) -> str | None:
        """위험 패턴 검사. 위반 시 설명 문자열, 안전하면 None."""
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, code):
                return f'차단된 패턴: {pattern}'
        return None

    def _check_imports(self, code: str) -> str | None:
        """import 검사. 허용되지 않은 모듈이 있으면 모듈명, 안전하면 None."""
        # import X, from X import Y
        import_pattern = re.compile(r'(?:^|\n)\s*(?:import|from)\s+(\w+)')
        for match in import_pattern.finditer(code):
            module = match.group(1)
            if module not in ALLOWED_IMPORTS:
                return module
        return None

    # ─── SVG 이미지 생성 ───

    def generate_svg(self, description: str) -> dict:
        """텍스트 설명으로 간단한 SVG 이미지 생성.

        기본 도형 조합으로 생성:
        - 원, 사각형, 선, 텍스트
        - description에서 색상/모양 키워드 추출

        Returns: {'svg': str, 'path': str}
        """
        self._total_images += 1

        # 키워드 추출
        colors = []
        shapes = []
        desc_lower = description.lower()

        for keyword, color in COLOR_KEYWORDS.items():
            if keyword in desc_lower:
                colors.append(color)

        for keyword, shape in SHAPE_KEYWORDS.items():
            if keyword in desc_lower:
                shapes.append(shape)

        # 기본값
        if not colors:
            colors = ['#3498db', '#e74c3c', '#2ecc71']
        if not shapes:
            shapes = ['circle']

        # SVG 생성
        width, height = 400, 300
        elements = []

        # 배경
        elements.append(f'  <rect width="{width}" height="{height}" fill="#1a1a2e" rx="10"/>')

        cx, cy = width // 2, height // 2

        for i, shape in enumerate(shapes[:5]):  # 최대 5개 도형
            color = colors[i % len(colors)]
            offset_x = (i - len(shapes) // 2) * 80
            x, y = cx + offset_x, cy

            if shape == 'circle':
                r = 40 + i * 5
                elements.append(f'  <circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="0.8"/>')

            elif shape == 'rect':
                w, h = 70 + i * 10, 60 + i * 8
                elements.append(
                    f'  <rect x="{x - w//2}" y="{y - h//2}" '
                    f'width="{w}" height="{h}" fill="{color}" opacity="0.8" rx="5"/>'
                )

            elif shape == 'triangle':
                size = 50 + i * 10
                points = f"{x},{y - size} {x - size},{y + size//2} {x + size},{y + size//2}"
                elements.append(f'  <polygon points="{points}" fill="{color}" opacity="0.8"/>')

            elif shape == 'star':
                points = self._star_points(x, y, 45, 20, 5)
                elements.append(f'  <polygon points="{points}" fill="{color}" opacity="0.8"/>')

            elif shape == 'heart':
                elements.append(
                    f'  <path d="M {x},{y+15} '
                    f'C {x},{y-10} {x-40},{y-10} {x-40},{y+5} '
                    f'C {x-40},{y+25} {x},{y+45} {x},{y+45} '
                    f'C {x},{y+45} {x+40},{y+25} {x+40},{y+5} '
                    f'C {x+40},{y-10} {x},{y-10} {x},{y+15} Z" '
                    f'fill="{color}" opacity="0.8"/>'
                )

            elif shape == 'line':
                elements.append(
                    f'  <line x1="{x-50}" y1="{y}" x2="{x+50}" y2="{y}" '
                    f'stroke="{color}" stroke-width="3" opacity="0.8"/>'
                )

        # 설명 텍스트
        # 긴 설명은 잘라서 표시
        label = description[:30] + ('...' if len(description) > 30 else '')
        elements.append(
            f'  <text x="{width//2}" y="{height - 20}" '
            f'text-anchor="middle" fill="#ecf0f1" font-size="14" '
            f'font-family="sans-serif">{_escape_xml(label)}</text>'
        )

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">\n'
            + '\n'.join(elements) +
            '\n</svg>'
        )

        # 파일 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"image_{timestamp}_{self._total_images}.svg"
        filepath = self.workspace / filename
        filepath.write_text(svg, encoding='utf-8')

        return {'svg': svg, 'path': str(filepath)}

    def _star_points(self, cx, cy, outer_r, inner_r, num_points):
        """별 모양 좌표 생성."""
        import math
        points = []
        for i in range(num_points * 2):
            angle = math.pi * i / num_points - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append(f"{x:.0f},{y:.0f}")
        return ' '.join(points)

    # ─── 파일 저장 ───

    def _save_file(self, filename: str, content: str) -> dict:
        """workspace 내에 파일 저장.

        Returns: {'success': bool, 'path': str, 'error': str}
        """
        self._total_files += 1

        # 보안: workspace 밖으로 탈출 방지
        safe_name = Path(filename).name  # 경로 구분자 제거
        if not safe_name or safe_name.startswith('.'):
            return {'success': False, 'path': '', 'error': f'유효하지 않은 파일명: {filename}'}

        filepath = self.workspace / safe_name
        try:
            filepath.write_text(content, encoding='utf-8')
            return {'success': True, 'path': str(filepath), 'error': ''}
        except Exception as e:
            self._errors += 1
            return {'success': False, 'path': '', 'error': str(e)}

    # ─── 응답 처리 ───

    def process_response(self, response_text: str) -> dict:
        """응답 텍스트를 분석하고 행동 실행.

        Returns: {
            'text': str,       # 행동 결과가 추가된 텍스트
            'actions': [{'type', 'result'}],
            'has_actions': bool,
        }
        """
        actions = self.detect_action(response_text)

        if not actions:
            return {
                'text': response_text,
                'actions': [],
                'has_actions': False,
            }

        results = []
        extra_text_parts = []

        for action in actions:
            if action['type'] == 'code':
                result = self.execute_code(action['content'], action['lang'])
                results.append({'type': 'code', 'result': result})
                if result['success'] and result['output']:
                    extra_text_parts.append(f"\n[실행 결과]\n{result['output'].rstrip()}")
                elif not result['success']:
                    extra_text_parts.append(f"\n[실행 오류] {result['error']}")

            elif action['type'] == 'image':
                result = self.generate_svg(action['content'])
                results.append({'type': 'image', 'result': result})
                extra_text_parts.append(f"\n[이미지 생성: {result['path']}]")

            elif action['type'] == 'file':
                result = self._save_file(action['lang'], action['content'])
                results.append({'type': 'file', 'result': result})
                if result['success']:
                    extra_text_parts.append(f"\n[파일 저장: {result['path']}]")
                else:
                    extra_text_parts.append(f"\n[파일 오류] {result['error']}")

        augmented_text = response_text + ''.join(extra_text_parts)

        return {
            'text': augmented_text,
            'actions': results,
            'has_actions': True,
        }

    # ─── 통계 ───

    def get_stats(self) -> dict:
        """통계."""
        return {
            'total_code_runs': self._total_code_runs,
            'total_images': self._total_images,
            'total_files': self._total_files,
            'errors': self._errors,
            'execution_count': self._execution_count,
            'workspace': str(self.workspace),
        }


def _escape_xml(text: str) -> str:
    """XML 특수문자 이스케이프."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))
