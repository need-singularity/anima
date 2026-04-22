# hexa-only 로드맵 (2026-04-22)

원칙: **모든 소스는 hexa · 타 언어는 generated artifact only**. anima raw#9 (no `.py`) 완전 준수 + hexa-lang을 범용 multi-target transpiler로 확장.

---

## Vision

```
┌──────────────────────────────────────────────────────────────┐
│                    SOURCE = hexa only                        │
│  (cert chain · β paradigm · proposal stack · SDK · tools)    │
└──────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
         hexa → C      hexa → Python   hexa → TypeScript
              │             │             │
              ▼             ▼             ▼
         native bin    anima-client-py  anima-client-ts
         (anima tool)    (pip pkg)       (npm pkg)

              │             │             │
              ▼             ▼             ▼
           hexa → Rust   hexa → Go   hexa → WASM
           (future)      (future)    (browser)
```

**anima repo**: `.hexa` + `.bash` + `.md` + `.json` (현 상태 유지)
**anima-client-{py,ts,rs,go}** repo: 100% auto-gen, 수동 edit 금지
**hexa-lang repo**: multi-target backend (C + Python + TS + ...)

---

## 범위 — 7-axis 통합

| axis | hexa-only 반영 |
|---|---|
| A launch 최적화 | 이미 hexa 기반 (완료) |
| B post-H100 연구 | r14 build/paper emit tool 모두 hexa (수정 없음) |
| C memory | hexa 구현 (spec prompt 이미 완료) |
| **D ship API/SDK** | **Python/TS SDK 모두 hexa 소스 → target emit** (core change) |
| E infra fleet/stage3 | hexa stage0/2/3 + cross-lang target backend (확장) |
| F CPU superlimit | 이미 hexa (완료) |
| G meta roadmap | hexa 구현 (spec prompt 완료) |

핵심 변화는 **D axis와 E.2 (hexa stage3)**. 다른 axis는 이미 hexa-native.

---

## Phase 0 — blocker 해소 (W0, 현재)

| # | item | owner | status |
|---|---|---|---|
| 0.1 | hexa stage2 3 bug fix (builtin mangling / reserved keyword / `.find()`) | hexa-lang | spec 작성 완료, 구현 대기 |
| 0.2 | anima-client 별 repo 생성 여부 결정 | user | 제안 단계 |
| 0.3 | E.2.2 critical path 공유 | 양 repo | `docs/upstream_notes/hexa_lang_20260422.md` |

→ Phase 0 끝나야 Phase 1 시작 가능.

---

## Phase 1 — hexa-lang Python emit target (W1-W3)

**owner**: hexa-lang maintainer
**SSOT prompt**: `docs/upstream_notes/hexa_lang_python_emit_target_20260422.md`

### W1 — 기본 backend
- [ ] `hexa build --target python` flag 신규
- [ ] 타입 매핑 (int/float/string/bool/array/dict/struct/enum)
- [ ] 제어 흐름 매핑 (if/while/for/match)
- [ ] smoke test (10줄 hexa → .py → python3 실행)

### W2 — stdlib 매핑
- [ ] `exec_capture`/`exec`/`setenv`/`env` → subprocess/os.environ
- [ ] `read_file`/`write_file` → pathlib
- [ ] HTTP client (B7 선행) → httpx async/sync
- [ ] JSON parse/emit → json module
- [ ] docstring 보존 + typing 완전성 (mypy strict)

### W3 — deterministic + packaging
- [ ] `HEXA_REPRODUCIBLE=1` byte-identical emit
- [ ] `pyproject.toml` auto-generate (PEP 621)
- [ ] `__init__.py` export 자동
- [ ] `python-safe` lint (FFI 금지 등)
- [ ] golden snapshot CI

**완료 verdict**: `hexa build --target python --pyproject sdk/hexa/ -o dist/` → pip install 가능 패키지.

---

## Phase 2 — anima sdk/hexa/ 작성 (W4)

**owner**: anima

```
anima/sdk/hexa/
├─ client.hexa           Client class (api_key, base_url, rate_limit)
├─ persona.hexa          generate() + PersonaResponse struct
├─ types.hexa            shared data types
├─ errors.hexa           AnimaError hierarchy
├─ rate_limit.hexa       token bucket helper
├─ http.hexa             HTTP client wrapper (B7 native http 사용)
├─ auth.hexa             API key validation
└─ version.hexa          //@version "1.0.0"
```

**constraint**:
- FFI 호출 금지 (python-safe subset)
- HTTP만 call (cert verification 등 server-side는 불포함)
- error는 Python native Exception hierarchy로 매핑

**deliverable**:
- [ ] `tool/sdk_py_emit.hexa` 작성 (`hexa build --target python` wrapper)
- [ ] sdk/hexa/ 파일 8개
- [ ] `sdk/hexa/selftest.hexa` (hexa 자체 CI용)

---

## Phase 3 — anima-client-py repo 생성 (W5)

**owner**: anima + external session

### 3.1 repo 초기화
- [ ] GitHub repo `need-singularity/anima-client-py` 생성
- [ ] README.md (수동 · 사용자 facing)
- [ ] examples/ (수동 · .py 예제)
- [ ] 나머지 모든 파일 .gitignore로 덮고 CI에서만 생성

### 3.2 auto-regen CI
- [ ] `.github/workflows/regen.yml` — anima tag push 감지
- [ ] CI step:
  1. clone anima main
  2. `hexa build --target python sdk/hexa/ -o anima/`
  3. mypy strict + black + pylint pass 확인
  4. commit + PR to anima-client-py main
- [ ] maintainer review + merge

### 3.3 PyPI 등록
- [ ] `twine` or `hatch` build config
- [ ] `pip install anima-client` 동작

---

## Phase 4 — anima-client-ts repo (W6)

**owner**: hexa-lang Phase 1 완료 후 TS emit target 추가 (추가 1-2주)

Phase 1과 동일한 패턴으로 TS target:
- `hexa build --target typescript sdk/hexa/ -o anima-client-ts/src/`
- ESM/CJS dual
- `npm install @anima/client`

---

## Phase 5 — 확장 (W7+)

- [ ] Rust target (hexa-lang · raw 성능)
- [ ] Go target (hexa-lang · CLI tool 친화)
- [ ] WASM target (hexa-lang · browser demo)
- [ ] 각 target마다 SDK 자동 emit (anima-client-rs, anima-client-go, anima-client-wasm)

---

## hexa-lang 측 deliverable 요약

| phase | 산출 |
|---|---|
| 0 | stage2 3 bug fix |
| 1 | `self/native/hexa_cc_py.{c,hexa}` Python backend |
| 1 | `docs/targets/python.md` |
| 1 | `testdata/python_target/` golden snapshot |
| 4 | `self/native/hexa_cc_ts.{c,hexa}` TypeScript backend |
| 5+ | Rust / Go / WASM backend |

## anima 측 deliverable 요약

| phase | 산출 |
|---|---|
| 2 | `sdk/hexa/` 8 파일 |
| 2 | `tool/sdk_py_emit.hexa` (regen wrapper) |
| 2 | `tool/sdk_ts_emit.hexa` (phase 4) |
| 3 | CI workflow 연동 |

## anima-client-{py,ts,rs,go,wasm} 측 deliverable 요약

| phase | repo | 산출 |
|---|---|---|
| 3 | anima-client-py | README, examples/ 만 manual. 나머지 100% auto-gen |
| 4 | anima-client-ts | 동일 |
| 5+ | anima-client-rs/go/wasm | 동일 |

---

## 성공 기준

### Phase 0
- hexa stage2 bug fix commit된 상태
- anima AOT 빌드 (serve_alm_persona, h100_post_launch_ingest) workaround 없이 성공

### Phase 1
- hexa 10줄 → `.py` → `python3 module.py` 실행
- mypy strict + black 통과
- byte-SHA stable (2번 emit diff empty)

### Phase 2
- sdk/hexa/client.hexa 로 persona.generate("hi") 호출 가능 (anima serve_alm_persona live)
- `hexa run sdk/hexa/selftest.hexa` exit 0

### Phase 3
- `pip install anima-client` 후 `python3 -c "import anima; anima.Client(api_key='x').persona.generate('hi')"` 동작
- CP1 도달 이후 실 endpoint 테스트 가능

### Phase 4
- `npm install @anima/client` 후 `import {Client} from '@anima/client'` 동작

---

## Hard constraints

- **anima repo**: .py 영원히 0 (raw#9)
- **anima-client-py**: 100% auto-gen, 수동 edit 금지 (README + examples/ 제외)
- **hexa source**: FFI 제외 subset만 allowed (python-safe)
- **schema drift 0**: anima sdk/hexa/ 변경 → CI auto regen → PR 자동 emit
- **deterministic**: 모든 emit byte-stable (`HEXA_REPRODUCIBLE=1`)
- **multi-repo uchg**: anima .roadmap, hexa-lang .roadmap 모두 uchg 존중
- **no auto-commit cross-repo**: maintainer review 필수
- **stdlib-only output**: generated .py/.ts는 표준 deps만 (httpx, requests, fetch)

---

## Timeline

```
2026-04-22 (today) — Phase 0 start (hexa stage2 bug fix spec 완료)
    │
    ├─ W0: blocker 해소 (hexa-lang 1주)
    │
2026-04-29 — CP1 도달 (예상)
    │
    ├─ W1-W3: Phase 1 (hexa Python emit target, 3주) 병렬 가능
    │
2026-05-13 — Phase 1 완료 (예상)
    │
    ├─ W4: Phase 2 (anima sdk/hexa/ 작성, 1주)
    ├─ W5: Phase 3 (anima-client-py repo + CI, 1주)
    │
2026-05-27 — Phase 2+3 완료 · 최초 pip install anima-client 가능
    │
    ├─ W6: Phase 4 (TypeScript target + anima-client-ts, 2주)
    │
2026-06-10 — Phase 4 완료 · npm install @anima/client 가능
    │
    ├─ W7+: Phase 5 (Rust/Go/WASM · optional)
```

**핵심 마일스톤**: CP1 + 4주 = **pip install anima-client** (2026-05-27 예상).

---

## 대안 경로 비교

| 경로 | 장점 | 단점 |
|---|---|---|
| **hexa-only (본 문서)** | SSOT hexa · 장기 drift 0 · 범용 SDK emit 가능 | hexa Python backend 구현 필요 (3주 delay) |
| openapi-generator-cli | 즉시 사용 가능 | spec drift 위험 · 외부 tool 종속 |
| 수동 .py SDK | 빠름 | maintain 지옥 · hand-write vs schema drift |

**추천**: hexa-only 경로 (장기 + cert chain 일관성 + 다언어 확장성).

---

## roadmap 추가 후보 (anima .roadmap)

Phase 별 신규 entry (user approval 시):

- `#90 hexa-only SDK Phase 0` — hexa-lang stage2 bug fix wait
- `#91 hexa-only SDK Phase 1` — hexa Python emit target landing
- `#92 hexa-only SDK Phase 2` — anima sdk/hexa/ 작성
- `#93 hexa-only SDK Phase 3` — anima-client-py repo + pip 등록
- `#94 hexa-only SDK Phase 4` — TypeScript target + npm 등록
- `#95 hexa-only SDK Phase 5` — Rust/Go/WASM target (optional)

(실 append 전 user 확인 필수. `.roadmap uchg` 유지.)

---

## roadmap 추가 후보 (hexa-lang .roadmap · 별 세션 의뢰)

- `HXA-#11` — Python emit target backend (W1-W3)
- `HXA-#12` — TypeScript emit target backend
- `HXA-#13` — deterministic emit 검증 CI
- `HXA-#14` — python-safe lint rule
- `HXA-#15` — multi-target golden snapshot testdata

---

## 리스크

| 리스크 | 완화 |
|---|---|
| hexa Python backend 구현 지연 | Phase 0 openapi-generator 임시 bridge 사용 후 migrate |
| python typing 완전성 미달 | mypy strict CI gate · 미달 시 golden snapshot diff로 차단 |
| schema drift (anima sdk/hexa/ ↔ anima-client-py) | auto-regen CI + tag-based sync |
| anima-client-py 수동 edit 유입 | CI에서 auto-gen 영역은 pre-commit block · .gitattributes로 linguist-generated=true |
| cross-repo tag 동기화 실패 | anima v1.x → anima-client-py v1.x.y pinning + compat CI |
| PyPI 이름 충돌 | 사전 등록 (CP1 전) |

---

## 메모

- 본 문서는 anima 내부 plan · `hexa-lang` 및 `anima-client-*` repo 는 외부 세션에서 각자 구현
- `docs/upstream_notes/hexa_lang_python_emit_target_20260422.md` 와 연동 (세부 spec)
- `docs/upstream_notes/d_axis_api_sdk_ship_20260422.md` 의 D.2 Python SDK 부분 **대체 경로** (auto-regen from hexa source)
- `docs/upstream_notes/e_axis_compute_fleet_hexa_stage3_20260422.md` 의 E.2 stage3 와 연동

---

## 단일 명령 요약

```bash
# Phase 1 hexa-lang 완료 후:
hexa build --target python --pyproject sdk/hexa/ -o /tmp/anima-client-py-dist/
# → 완성된 pip 패키지 tree

# anima-client-py repo CI:
hexa build --target python sdk/hexa/ -o anima/
mypy --strict anima/
black --check anima/
pytest tests/
twine upload dist/*
```

---

## 완성 후 사용자 경험 (target)

```python
# pip install anima-client
import anima

client = anima.Client(api_key="...")
resp = client.persona.generate("안녕")
print(resp.text)  # "안녕하세요, anima 입니다..."
```

내부적으로 이 `.py` 는 전부 `sdk/hexa/*.hexa` 에서 transpile된 artifact. 수정하려면 **hexa source만** 수정 → CI regen → PR → merge → 자동 release.

**이것이 hexa-only 의 최종 형태**: "사용자는 Python, 우리는 hexa".
