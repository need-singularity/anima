# Track B · Phase 5 — Tests 분리 + Legacy 청소 설계 (2026-04-19)

> **레퍼런스**: `anima_agent_restructure_plan_20260419.md` §5,
> `track_b_phase1_movemap_20260419.md`, `track_b_phase2_5_audit_20260419.md`.
> **상태**: 설계 전용. 파일 이동 금지.

---

## 1. 현 test_*.hexa 인벤토리

### 1.1 루트 test_*.hexa (10 파일, 807 LOC)

| 파일 | LOC | use (내부) | 분류 |
|------|-----|-----------|------|
| `test_agent_platform.hexa` | 62 | — | platform |
| `test_e2e.hexa` | 45 | — (stub) | platform |
| `test_plugin_routing.hexa` | 80 | — | plugins |
| `test_autonomy_loop.hexa` | 104 | `autonomy_loop` | autonomy |
| `test_claude_smoke.hexa` | 37 | `llm_claude_adapter` | claude |
| `test_claude_parse.hexa` | 16 | `llm_claude_adapter` | claude |
| `test_claude_autonomy_live.hexa` | 33 | `autonomy_loop` | claude |
| `test_critique_parse_regression.hexa` | 160 | `llm_claude_adapter` | claude |
| `test_hire_sim.hexa` | 141 | `autonomy_loop`, `hire_sim_100` | hire-sim |
| `test_hire_sim_harness.hexa` | 129 | `hire_sim_stratify/judge/runner` | hire-sim |

### 1.2 hexa/ 레거시 test stubs (3 파일, 108 LOC)

- `hexa/test_agent_platform.hexa` (42) — TODO[python-sdk] stub
- `hexa/test_e2e.hexa` (36) — TODO stub
- `hexa/test_plugin_routing.hexa` (30) — stub

→ **루트 test 가 실본체**, `hexa/` 는 포팅 초기 스캐폴드 잔재.

### 1.3 employee/test_employee_skeleton.hexa
- `use "goal_store"` `"scratchpad"` `"emit_report"` (전부 employee/ 내부)
- Phase 4 에서 `anima-agent-core/employee/` 승격 시 동반 이동 완료 가정.

---

## 2. 분리 대상: `anima-agent-tests/` vs 잔류

### 2.1 `anima-agent-tests/` 신규 리포로 승격 (7 파일)

```
anima-agent-tests/
  platform/
    test_agent_platform.hexa      # core 스모크
    test_e2e.hexa                 # E2E stub
    test_plugin_routing.hexa      # plugins 라우팅
  autonomy/
    test_autonomy_loop.hexa
  claude/
    test_claude_smoke.hexa
    test_claude_parse.hexa
    test_claude_autonomy_live.hexa
    test_critique_parse_regression.hexa
  CLAUDE.md                       # 신규 (anima-core 양식)
  README.md                       # 실행 가이드
```

use-chain: 전부 anima-agent-core/ 루트 모듈 (`autonomy_loop`, `llm_claude_adapter`) → include path 조정만 필요.

### 2.2 잔류: `anima-agent-hire-sim/tests/` (Phase 4a 동반)

- `test_hire_sim.hexa`, `test_hire_sim_harness.hexa` 는 hire_sim_100/runner/judge/stratify 와 강결합.
- Phase 4a (hire-sim 승격) 와 **한 커밋**에 포함. tests 만 분리하면 use-chain 끊김.

### 2.3 잔류: `anima-agent-core/employee/test_employee_skeleton.hexa`

- employee/ 내부 완결 (goal_store/scratchpad/emit_report) → 리포 이동 없이 그대로.

---

## 3. Legacy 정리

### 3.1 `anima-agent/hexa/` 전체 삭제 (34 .hexa + subdir)

- CLAUDE.md 본문 "레거시 스텁 .hexa (교체 완료, 정리 예정)" 명시.
- 교체 매핑 (top-level 실본체 존재):
  - `hexa/{consciousness_features,dashboard_bridge,discovery_loop,ecosystem_bridge,metrics_exporter,philosophy_lenses,test_*}.hexa` → 루트에 실본체 있음.
- 나머지 27 파일 (`agent_sdk/tools_policy/tools/provider/main/...`) → anima-agent-core 승격본에 흡수됨 (Phase 1 a26a8522).
- 삭제 전 확인: `hexa build run.hexa` artifacts/*.c 본문 > 0 (silent-exit 회피).

### 3.2 `hire_sim_*.hexa` 잔재

- Phase 4a 에서 anima-agent-hire-sim/ 로 이동되므로 Phase 5 에는 **루트에 존재하지 않아야** 함.
- 만약 잔존 시: `hire_sim_100/judge/live/runner/stratify.hexa` + `run_hire_sim_claude.hexa` = 6 파일 이동 누락 → Phase 4a 보완 커밋.

### 3.3 `pyproject.toml` 삭제 (R37 / Py 전면 금지)

- `/Users/ghost/Dev/anima/anima-agent/pyproject.toml` 루트 1 파일.
- AN7 HEXA-FIRST 완료 상태 → 잔재.

### 3.4 `Dockerfile` 감사

- anima-agent/Dockerfile — hexa 빌드 기반인지 확인. python 베이스면 재작성 또는 삭제.

### 3.5 `results/` `data/` `build/`

- `results/` = 런타임 산출 (demo JSON/log) → .gitignore 확인, archive or purge.
- `build/` = hexa artifacts → .gitignore 대상.
- `data/` = 코퍼스/샘플 → 유지 (문서화).

---

## 4. Final Cleanup Checklist

### 4.1 디렉토리 상태 (Phase 5 완료 시)
- [ ] `anima-agent/` = 루트 진입점만 (`anima_agent.hexa`, `autonomy_*.hexa`, `consciousness_features.hexa`, `dashboard_bridge.hexa`, `metrics_exporter.hexa`, `philosophy_lenses.hexa`, `ecosystem_bridge.hexa`, `discovery_loop.hexa`, `llm_claude_adapter.hexa`, `CLAUDE.md`, `README.md`, `.env.example`, `config/`, `.growth/`)
- [ ] `anima-agent/hexa/` **삭제됨**
- [ ] `anima-agent/pyproject.toml` **삭제됨**
- [ ] `anima-agent/test_*.hexa` **0 파일** (전부 anima-agent-tests/ 또는 hire-sim 리포로 이동)
- [ ] `anima-agent/hire_sim_*.hexa` **0 파일**

### 4.2 신규 리포
- [ ] `anima-agent-tests/` 7 파일 + CLAUDE.md
- [ ] `shared/config/projects.json` 신규 entry (`anima-agent-tests`)

### 4.3 문서 패치
- [ ] `anima-agent/CLAUDE.md` — tree 블록에서 `hexa/` 삭제, tests 섹션 제거, `test_*.hexa` 3 exec 줄 → "tests: anima-agent-tests/ 참조"
- [ ] `anima-agent/README.md` — 테스트 실행 가이드 업데이트
- [ ] `docs/AGENT-ARCHITECTURE.md` — test 경로 xref (있는 경우)
- [ ] `docs/anima_agent_restructure_plan_20260419.md` — Phase 5 완료 마킹

### 4.4 빌드/검증
- [ ] `hexa build anima-agent/run.hexa` PASS, artifacts/run.c body > 0
- [ ] `hexa build anima-agent-tests/platform/test_agent_platform.hexa` PASS
- [ ] `hexa build anima-agent-tests/claude/test_critique_parse_regression.hexa` PASS
- [ ] `--validate-hub` 모듈 수 감소 없음 (tests 는 hub 미등록)
- [ ] pre-commit hook (`block-forbidden-ext.sh`) 통과

### 4.5 grep 검증
- [ ] `grep -rn "anima-agent/hexa/" docs/ shared/` = 0
- [ ] `grep -rn "hire_sim_" anima-agent/` = 0 (루트)
- [ ] `grep -rn "^use \"hire_sim" anima-agent-tests/` = 0
- [ ] `grep -rn "pyproject\.toml" anima-agent/` = 0

### 4.6 리스크
| 리스크 | 완화 |
|--------|------|
| hexa/ 삭제 후 숨은 `use` 체인 | Phase 1 audit 에서 0건 확인됨 (`track_b_phase2_5_audit §2`) |
| test xref 누락 (docs) | 4.3 체크리스트 강제 |
| hire_sim 이동 누락 | Phase 4a 커밋 직후 `ls anima-agent/hire_sim_*.hexa` 빈 결과 확인 |
| pyproject.toml 외부 참조 | grep 검증 후 삭제 |

---

## 5. 커밋 플로 (단일 커밋 Phase 5)

```
git mv anima-agent/test_agent_platform.hexa      anima-agent-tests/platform/
git mv anima-agent/test_e2e.hexa                  anima-agent-tests/platform/
git mv anima-agent/test_plugin_routing.hexa       anima-agent-tests/platform/
git mv anima-agent/test_autonomy_loop.hexa        anima-agent-tests/autonomy/
git mv anima-agent/test_claude_*.hexa             anima-agent-tests/claude/
git mv anima-agent/test_critique_parse_regression.hexa anima-agent-tests/claude/
git rm -r anima-agent/hexa/
git rm anima-agent/pyproject.toml
# docs patch + shared/projects.json entry
```

---

_설계 완료. Phase 4abc 선행 필수. 승인 시 Phase 5 단일 커밋 발사._
