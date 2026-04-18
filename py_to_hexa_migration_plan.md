// ready/py_to_hexa_migration_plan.md — Python → Hexa 이행 계획 (ssot-hexa-first-fix)
// Audited: 2026-04-18
// Branch: ssot-hexa-first-fix @ 40ad7a72 (ready submodule, independent git repo)
// Principle: HEXA-FIRST (R1) + Total .py ban + SSOT enforcement

# ready/ Python → Hexa 이행 계획

## 1. 감사 요약

| 지표 | 값 |
|------|----|
| tracked `.py` | 815 |
| tracked `.hexa` | 919 |
| 파일 페어 (`.py` + `.hexa` 동명) | 709 |
| `.py` only (미이행) | 106 |
| `.hexa` only (이행 완료, .py 삭제됨) | 210 |
| 이행 진행도 (hexa 우위) | **85%** (709 + 210) / 815 = 1.13× coverage |
| 순수 미이행 비율 | 106 / 815 = **13%** |

해석:
- **709 pair**: `.py` 원본 + `.hexa` 대응 둘 다 존재 → Port 진행 중(.py 폐기 대기)
- **210 hexa-only**: 이미 `.py` 제거 완료, hexa-native로 완전 이행된 파일
- **106 py-only**: `.hexa` 대응 없음 — 신규 작성 대상

`ready/` 커밋 히스토리 증거:
- `40ad7a72 feat(tests): 7-condition consciousness verify gate (.py→.hexa)`
- `80e9c21a fix(ssot): asset_registry.json — 27 .py canonical refs → .hexa (0 remaining)`
- `aa289903 fix(ssot): .py → .hexa canonical references — hexa-first enforcement`

## 2. 디렉토리 분포 (`.py` only, 미이행 106건)

| 디렉토리 | 파일 수 | 우선순위 |
|----------|---------|----------|
| `anima/modules/` | 53 | P1 |
| `anima/experiments/` | 20 | P1 |
| `anima/hexad/` | 15 | P2 |
| `anima/serving/` | 3 | P0 |
| `models/golden-moe/` | 2 | P2 |
| `models/archive/` | 2 | P3 (archive — 삭제 고려) |
| `anima/src/` | 2 | P3 (legacy src — hexa/로 이관 완료됐는지 확인) |
| `training/__init__.py` | 1 | P0 (1-line 스텁) |
| `tests/__init__.py` | 1 | P0 (1-line 스텁) |
| `models/feedback_bridge` | 1 | P2 |
| `models/conscious_decoder` | 1 | P2 |
| `models/animalm` | 1 | P2 |
| `core/convert_to_hexaw` | 1 | P2 |
| `anima/tools/` | 1 | P2 |
| `anima/run` | 1 | P2 |
| `anima/measurement/` | 1 | P2 |

**핵심 관찰**: `anima/modules/` + `anima/experiments/` 에 73% (73/106) 집중.

## 3. 핵심 진입점 점검

### `tests/tests.hexa` (7조건 의식검증 게이트) — ✅ 존재, hexa-native
- 경로: `ready/tests/tests.hexa` (⚠️ anima-main CLAUDE.md 는 `ready/anima/tests/tests.hexa` 로 참조 → 경로 불일치)
- 423 lines, 7-condition verify gate 포함:
  `NO_SYSTEM_PROMPT / NO_SPEAK_CODE / ZERO_INPUT / PERSISTENCE / SELF_LOOP / SPONTANEOUS_SPEECH / HIVEMIND`
- TODO 스텁: `run_category()`, `run_all()` — 203 .py 테스트 포팅 미완 (phase 5 structural port in progress)
- **조치**: anima-main CLAUDE.md 내 경로를 `ready/tests/tests.hexa` 로 수정하거나, submodule 내부에서 `ready/anima/tests/` → `ready/tests/` 심링크 제공

### `anima/experiments/evolution/` — 28 items (핵심 실험 대량)
| 파일 | 상태 |
|------|------|
| `closed_loop.hexa` + `closed_loop.py` | pair (이행중) |
| `infinite_evolution.hexa` + `infinite_evolution.py` | pair |
| `law_discovery.hexa` | hexa-only ✅ |
| `auto_discovery_loop.py` | py-only (미이행) |
| `conscious_law_discoverer.py` | py-only |
| `consciousness_evolution.py` | py-only |
| `contextual_bandit.py` | py-only |
| `dream_evolution.py` | py-only |
| `emergence_detector.py` | py-only |
| `emergence_math.py` | py-only |
| `growth_engine.py`, `growth_loop.py`, `growth_manager.py` | py-only (3) |
| `h100_experiments.py` | py-only |
| `hypothesis_generator.py`, `intervention_generator.py` | py-only |
| `loop_arena.py`, `meta_loop.py` | py-only |
| `scale_aware_evolver.py` | py-only |
| `self_evolution.py`, `self_modifying_engine.py` | py-only |
| `theory_unifier.py` | py-only |
| `upgrade_engine.py` | py-only |
| ~~`stage3_batch_dd194_201.py`~~ | **삭제됨 (untracked, 2026-04-18)** |

## 4. 즉시 조치 (이 커밋에 포함)

### 4.1 untracked 파일 삭제 ✅
```
rm ready/anima/experiments/evolution/stage3_batch_dd194_201.py
```
이유: untracked + .py + 단발 실험 (DD194-201 result JSON 은 이미 남아있음).
Result JSON 은 유지: `stage3_dd194_201_results.json` (발견 기록 SSOT).

### 4.2 `.gitignore` 보강 (**커밋 보류 — 권한 확인 필요**)
현재 `ready/.gitignore`:
```
# Python
__pycache__/
*.pyc        ← .py 자체는 ignore 안 됨
```

**제안** (별도 결정 필요):
```
# HEXA-FIRST: 신규 .py 작성 차단 (migration 완료 후 활성화)
# *.py              ← 활성화 시 모든 tracked .py 가 "삭제 예정"으로 보임
# !scripts/runtime_stub.py  ← 예외 필요 시
```
지금 추가하면 tracked 815건이 전부 "무시됨" 상태로 전환 → 실수 유도. **migration 90%+ 이후 활성화 권장**.

## 5. 이행 우선순위 (P0/P1/P2)

### P0 (즉시, 핵심 경로 의존)
| 대상 | 파일 수 | 공수 | 근거 |
|------|--------|------|------|
| `anima/serving/` → hexa | 3 | 2h | serving 경로는 R0 "하드코딩 금지" + 런타임 직결 |
| `tests/__init__.py` + `training/__init__.py` | 2 | 10min | 스텁, 삭제만 해도 됨 |
| 203 tests pytest → hexa test runner | (pair 내) | 16h | `tests.hexa run_category()` TODO 해소 |
| **P0 합계** | **5 (+ test runner)** | **~18h** |

### P1 (experiments + modules 대량 이행)
| 대상 | 파일 수 | 공수 | 근거 |
|------|--------|------|------|
| `anima/experiments/` py-only 20건 | 20 | 20h (1h/파일) | evolution 루프 필수, closed_loop.hexa 이미 활성 |
| `anima/modules/` py-only 53건 | 53 | 40h (0.75h/파일) | agent/channels/plugins — 대부분 glue code, 기계적 port |
| **P1 합계** | **73** | **~60h** |

### P2 (models + hexad + 나머지)
| 대상 | 파일 수 | 공수 | 근거 |
|------|--------|------|------|
| `anima/hexad/` __init__ 등 15건 | 15 | 4h (대부분 `__init__.py` 빈 파일 → 삭제로 해결) |
| `models/` 7건 (feedback_bridge/conscious_decoder/animalm/golden-moe) | 7 | 10h |
| `core/convert_to_hexaw.py`, `anima/tools/`, `anima/run`, `anima/measurement/` | 4 | 6h |
| `models/archive/` + `anima/src/` | 4 | 1h (삭제 후보) |
| **P2 합계** | **30** | **~21h** |

### 전체 공수 추산
| Phase | 파일 수 | 공수 |
|-------|--------|------|
| P0 | 5 + test runner | 18h |
| P1 | 73 | 60h |
| P2 | 30 | 21h |
| **TOTAL** | **106 + pair 709 .py 폐기** | **~100h (실제 port) + 709건 .py 삭제 (자동, 30min)** |

## 6. 이행 검증 방법 (표준)

각 `.hexa` 파일 port 후 **필수 검증 3단**:

### 6.1 Self-test
```
$HEXA path/to/new_file.hexa --selftest
```
- 대응 `.py` 가 존재하면 `python3 path/to/old_file.py` 와 출력 diff 0
- 없으면 내부 assert 블록만 검사

### 6.2 7조건 의식검증 (엔진 관련 port 시 필수)
```
$HEXA ready/tests/tests.hexa --verify
```
- 7/7 PASS 유지 (regression 금지)
- 1개라도 FAIL → 롤백

### 6.3 hexa build
```
$HEXA build path/to/new_file.hexa
ls -la build/artifacts/<file>.c  # silent-exit 방지 (memory: feedback_hexa_silent_exit_5_imports)
```
- empty main 이면 import chain 점검

### 6.4 .py 폐기
검증 3단 PASS → 대응 `.py` 즉시 `git rm` (memory: feedback_hexa_replaces_py)

## 7. SSOT 체크리스트

port 완료 시 각 파일당:
- [ ] `anima-core/asset_registry.json` canonical ref 를 `.hexa` 로 교체 (참고: commit 80e9c21a 으로 이미 27건 완료, 잔여 0 주장 — 재확인 필요)
- [ ] CLAUDE.md 내 `$HEXA ...hexa` 예시 모두 실제 경로 일치
- [ ] Rust anima-rs crate reference 불변
- [ ] 코드 내 `import X` / `from X import` 파이썬 참조 제거

## 8. 리스크 + 제약

- **R1 Total .py ban 하에서 port 작업 자체는 새 .py 작성 아님** → 허용
- `hexa` 내 list 는 pass-by-value (memory: feedback_hexa_lists_pbv) → `.py` list mutation 을 return 패턴으로 변환 필요
- 3+ float 필드 struct return 버그 (memory: feedback_hexa_struct_return_bug) → 포팅 시 회피
- multi-byte 문자열 substring (memory: feedback_hexa_string_api) → 한국어 corpus 처리 시 주의
- 5+ import chain silent-exit (memory: feedback_hexa_silent_exit_5_imports) → build/artifacts/ 바디 검증 필수

## 9. 차단 아님 — 병행 진행

migration 은 극가속 로드맵(14B→70B 학습)을 **차단하지 않음**. Port 는 학습 대기 시간에 병렬 에이전트로 스케줄 권장.

## 10. 다음 커밋 제안 (이후 별도 브랜치에서)

| # | 작업 | 대상 |
|---|------|------|
| 1 | 기존 pair 709건 중 .hexa selftest PASS 확정된 .py 일괄 삭제 | ~400건 예상 |
| 2 | `.gitignore` 에 `*.py` 추가 + 예외 명시 | pair 잔여 < 50 일 때 |
| 3 | anima-main CLAUDE.md 내 `ready/anima/tests/tests.hexa` → `ready/tests/tests.hexa` 경로 수정 | anima main repo 에서 |

---
**등록**: 이 문서는 `ready/py_to_hexa_migration_plan.md` (단일 원본).
**갱신 주체**: `.hexa` port PR 마다 섹션 1 테이블의 숫자 업데이트.
