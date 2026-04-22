# hexa-lang Python emit target — SDK를 hexa로 작성 (2026-04-22)

요청자: anima session
대상: hexa-lang maintainer 세션
원인: anima raw#9 (no `.py` in main repo) + D axis API/SDK ship (Python SDK 필요)

---

## 배경

anima 메인 repo는 **raw#9 policy**로 `.py` 파일 유입 금지. 그러나 D axis (API/SDK 공개)에서 Python SDK 필요. 현재 2가지 path만 보임:

1. **anima-client-py 별 repo** (hand-written .py) — 2-repo drift, SSOT 분열
2. **OpenAPI → openapi-generator-cli** — 외부 도구 의존, 제한적 커스터마이즈

**제3의 path 제안**: hexa-lang에 **Python transpile target** 추가 → SDK 소스를 hexa로 작성 → 배포 시 Python 생성.

```
anima/
├─ sdk/hexa/                    (SDK source · hexa · SSOT)
│  ├─ client.hexa
│  ├─ persona.hexa
│  └─ rate_limit.hexa
└─ tool/sdk_py_emit.hexa         (anima → anima-client-py auto-regen)

anima-client-py/                 (fully auto-generated · 수동 편집 금지)
├─ anima/                        (generated .py · DO NOT EDIT)
└─ pyproject.toml                (auto-emit)
```

---

## 원칙

| 원칙 | 이유 |
|---|---|
| hexa = SSOT language | cert chain + β paradigm + proposal stack 일관성 |
| .py는 output artifact only | raw#9 compliance |
| deterministic emit | HEXA_REPRODUCIBLE=1 + SOURCE_DATE_EPOCH byte-stable |
| PEP 8 compliant output | pylint/black 직접 pass, 수동 edit 불필요 |
| stdlib-only output | 외부 runtime 불필요 (pip install시 anima-client만) |

---

## 기능 요구사항

### 1. Python emit 백엔드 신규 (hexa-cc)

**현재**: hexa 소스 → C transpile → clang → binary
**신규**: hexa 소스 → Python source emit 옵션 추가

```bash
hexa build --target python sdk/hexa/client.hexa -o dist/client.py
hexa build --target python sdk/hexa/ -o anima-client-py/anima/  # dir→dir
```

### 2. 타입 매핑

| hexa | Python 3.9+ |
|---|---|
| `int` | `int` |
| `float` | `float` |
| `string` | `str` |
| `bool` | `bool` |
| `array` | `list` |
| `dict` / `#{...}` | `dict` (optionally `TypedDict` if struct hint) |
| `struct Foo { x: int, y: string }` | `@dataclass class Foo: x: int; y: str` |
| `fn name(args) -> ret` | `def name(args) -> ret:` |
| `fn async_name(...)` | `async def async_name(...):` (if `async` keyword) |
| `null` / `None` | `None` |
| `enum Color { Red, Green }` | `class Color(Enum): RED = 'red'; GREEN = 'green'` |

### 3. 제어 흐름 매핑

| hexa | Python |
|---|---|
| `if/else` | `if/else` (들여쓰기 변환) |
| `while` | `while` |
| `for x in arr` | `for x in arr:` |
| `match expr { ... }` | `match expr: case ...:` (Python 3.10+, fallback if/elif) |
| `exec_capture(cmd)` | `subprocess.run(cmd, capture_output=True, text=True)` |
| `exec(cmd)` | `os.system(cmd)` or `subprocess.run` |
| `setenv(k, v)` | `os.environ[k] = v` |
| `env(k)` | `os.environ.get(k)` |
| `read_file(p)` | `open(p).read()` context manager wrap |
| `write_file(p, s)` | `Path(p).write_text(s)` |

### 4. HTTP client 필수 (B7 spec 선행)

SDK는 HTTP 클라이언트 — hexa stdlib에 이미 native http 있으면 매핑:
- `http.post(url, headers, body)` → `requests.post(url, headers=..., json=...)` or `httpx` (async)
- `http.get(url, params)` → `requests.get(...)`
- async 지원 시 → `async def`, `await client.post(...)` (httpx AsyncClient)

B7 (native http/1.1 server) 선행 완료 시 client-side는 쉽게 파생 — httpx/requests 2택 선택 flag.

### 5. Docstring 보존

```hexa
/// Returns persona response from anima.
/// Args:
///   prompt (string): input text
/// Returns:
///   PersonaResponse
fn generate(client: Client, prompt: string) -> PersonaResponse { ... }
```

→ Python:
```python
def generate(client: 'Client', prompt: str) -> 'PersonaResponse':
    """Returns persona response from anima.

    Args:
        prompt (string): input text
    Returns:
        PersonaResponse
    """
    ...
```

### 6. Type hint 100% output

hexa는 static-typed → Python output도 모든 파라미터/리턴 타입 힌트 포함. mypy strict pass 가능해야 함.

### 7. `__init__.py` 자동 emit

디렉토리 `sdk/hexa/` emit 시 `__init__.py` 자동 생성 — public symbol export:
```python
from .client import Client
from .persona import generate, PersonaResponse
__all__ = ['Client', 'generate', 'PersonaResponse']
```

### 8. pyproject.toml 자동 생성

`hexa build --target python --pyproject` flag → PEP 621 `pyproject.toml` emit:
```toml
[project]
name = "anima-client"
version = "1.0.0"   # hexa 소스의 //@version meta
requires-python = ">=3.9"
dependencies = ["httpx>=0.25", "pydantic>=2.0"]
```

### 9. deterministic emit

- `HEXA_REPRODUCIBLE=1` → emit 결과 byte-identical
- `SOURCE_DATE_EPOCH` 반영 (timestamp line strip 불필요)
- docstring 순서 · import 순서 · dataclass field 순서 모두 deterministic
- 두 번 emit 후 sha256 동치

### 10. hexa source 제약 (Python-safe subset)

Python으로 transpile 가능한 hexa는 subset:
- FFI 호출 금지 (또는 stub으로 대체)
- C-level pointer 사용 금지
- unsafe cast 금지
- 메모리 직접 접근 금지

hexa-lang maintainer가 `python-safe` feature flag 로 lint 추가:
```bash
hexa lint --target python sdk/hexa/client.hexa
# → error: line 42: FFI call 'h_last_extract' not python-safe
```

---

## Hard constraints

- DO NOT modify anima repo (이 doc은 reference only)
- DO NOT auto-commit to hexa-lang
- NO `.py` files in anima (transpile output은 별 repo OR gitignore)
- deterministic emit 필수 (CI reproducibility)
- Python 3.9+ 지원 (typing 완전성)
- mypy strict + black --check pass 출력물
- stdlib-only 의존 (requests/httpx는 옵션)
- hexa stage2 bug 3건 (builtin mangling/reserved keyword/`.find()`) 선행 fix 필요 (E.2.2 critical path)

---

## Test plan

1. **smoke**: `sdk/hexa/client.hexa` 10줄 → `hexa build --target python` → `.py` 생성 → `python3 -c "import client; print(client.Client)"` 동작
2. **round-trip**: hexa source 의 타입/docstring → Python output → mypy --strict pass
3. **determinism**: 동일 source 2회 build → `diff` empty
4. **HTTP**: hexa `http.post` 매핑 → httpx call → live endpoint mock 응답 수신
5. **CI**: anima-client-py repo에 GitHub Actions — anima tag push → hexa build → PR emit
6. **golden file**: sdk/hexa/* 의 expected .py snapshot → regen 결과와 비교 (regression)

---

## Success criteria

- D axis Python SDK 가 hexa source에서 auto-gen
- anima-client-py의 `.py`는 100% generated (수동 edit 0)
- mypy strict + black + pylint 모두 pass
- `pip install anima-client` 후 `from anima import Client; c = Client(api_key='...'); c.persona.generate('hi')` 동작
- anima 소스 변경 → CI auto-regen → anima-client-py PR 자동 emit (schema drift 0)

---

## Deliverable (hexa-lang side)

| 파일 | 역할 |
|---|---|
| `self/native/hexa_cc_py.c` (또는 .hexa) | Python emit backend |
| `docs/targets/python.md` | 타입 매핑 + 제약 문서 |
| `testdata/python_target/*.hexa` + `expected/*.py` | golden snapshot |
| `.github/workflows/python_target_ci.yml` | target-specific CI |

## Deliverable (anima side)

| 파일 | 역할 |
|---|---|
| `sdk/hexa/client.hexa` | SDK root |
| `sdk/hexa/persona.hexa` | persona endpoint |
| `sdk/hexa/types.hexa` | data types |
| `tool/sdk_py_emit.hexa` | `hexa build --target python` wrapper + anima-client-py PR emit |

## Deliverable (anima-client-py side · 완전 auto-gen)

| 파일 | 역할 |
|---|---|
| `anima/__init__.py` | auto-gen export |
| `anima/client.py` | auto-gen |
| `anima/persona.py` | auto-gen |
| `pyproject.toml` | auto-gen |
| `README.md` | 수동 (사용자 example) |
| `.github/workflows/regen.yml` | anima tag → regen PR |

---

## Cross-axis 의존성

- **E.2.2 hexa transpiler 3 bug** (builtin mangling / reserved keyword / `.find()`) 선행 — AOT 빌드 차단 해소 필수
- **hexa B7 native http server** 선행 권장 — client-side http 자연스럽게 파생
- **hexa B8 signal trap** 선행 — CLI SDK graceful shutdown

---

## Report format

hexa-lang maintainer가 이 prompt 처리 후 보고:
- Python emit backend 구현 commit sha
- 타입 매핑 coverage (10개 요구 중 N개 구현)
- golden snapshot 개수 + diff status
- 한계 (미구현 기능 list + workaround)
- anima 측 follow-up action item
Under 400 words.

---

## Timeline 추정

- **hexa-lang 측**: 2-3주 (M3 Mac + Linux CI)
  - W1: 기본 타입/제어흐름 매핑 + smoke test
  - W2: docstring/typing/async + HTTP client 매핑
  - W3: deterministic emit + pyproject + golden snapshot CI
- **anima 측**: hexa-lang 완료 후 1주
  - sdk/hexa/* 작성 + regen workflow
- **anima-client-py 측**: 최초 auto-gen 후 공개

Total CP1 + 3-4주. D axis ship 예상 timeline (CP1 + 1-2주) 대비 2주 지연 가능 — 단 raw#9 완전 준수 + 장기 drift 0.

---

## Alternative — 즉시 D axis ship 필요 시

hexa-lang Python target 완성 전 임시 path:
- `anima-client-py` 를 openapi-generator-cli로 초기 auto-gen
- hexa-lang Python target 완성되면 migrate (schema backward compat)
- 두 path 병행 → schema drift CI 활성

---

## 메모

- anima raw#9 완전 준수 유지
- hexa-lang 자체의 universe 확장 (C emit + Python emit 2 target)
- β main paradigm 확산 — hexa 언어가 Python 생태계까지 reach
- 추후 TS/Rust/Go emit target 도 동일 pattern 확장 가능 → 범용 multi-target transpiler
