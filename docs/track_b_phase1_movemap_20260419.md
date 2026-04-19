# Track B · Phase 1 · File Move Map (2026-04-19)

> **상태**: pre-execution blueprint. 실제 이동 금지. 승인 후 별도 커밋에서 실행.
> **레퍼런스**: `docs/anima_agent_restructure_plan_20260419.md` §2 옵션 A, §3 테이블, §5 Phase 1.
> **범위**: 옵션 B 수준 — `anima-agent-core/` 분리만 (6 파일). 옵션 A 의 나머지는 Phase 2~5.

---

## 1. Phase 1 범위 확정

Phase 1 = L0 골화 대상 CLI + registry 6 개 파일을 `anima-agent-core/` 로 분리.
서브디렉토리 승격(channels/providers/plugins/skills/trading/hire-sim/dashboard/tests) 은 Phase 2~5 에서 진행.

### 대상 파일 (6 개)

| # | 현 경로 | LOC | L0 |
|---|---------|-----|----|
| 1 | `anima-agent/run.hexa` | 100 | Y |
| 2 | `anima-agent/unified_registry.hexa` | 131 | Y |
| 3 | `anima-agent/agent_sdk.hexa` | 151 | Y |
| 4 | `anima-agent/agent_tools.hexa` | 795 | Y (추가만) |
| 5 | `anima-agent/tool_policy.hexa` | 175 | Y |
| 6 | `anima-agent/code_guardian.hexa` | 197 | N (모니터) |

총 **1,549 LOC**, 단일 언어 `.hexa`.

### 동반 이동 (설정)

| 현 경로 | 신 경로 |
|---------|---------|
| `anima-agent/config/agent_config.json` | `anima-agent-core/config/agent_config.json` |

---

## 2. 이동 매핑 (현 → 신)

| src | dst |
|-----|-----|
| `anima-agent/run.hexa` | `anima-agent-core/run.hexa` |
| `anima-agent/unified_registry.hexa` | `anima-agent-core/unified_registry.hexa` |
| `anima-agent/agent_sdk.hexa` | `anima-agent-core/agent_sdk.hexa` |
| `anima-agent/agent_tools.hexa` | `anima-agent-core/agent_tools.hexa` |
| `anima-agent/tool_policy.hexa` | `anima-agent-core/tool_policy.hexa` |
| `anima-agent/code_guardian.hexa` | `anima-agent-core/code_guardian.hexa` |
| `anima-agent/config/agent_config.json` | `anima-agent-core/config/agent_config.json` |

신규 생성:

| 경로 | 목적 |
|------|------|
| `anima-agent-core/CLAUDE.md` | L0 선언 + ref/exec (anima-core 패턴) |

---

## 3. Import 영향 Audit

### 3.1 자매 `.hexa` 에서 Phase 1 대상 `use` 참조

`grep -E '^use\s+.*(run\|agent_sdk\|agent_tools\|unified_registry\|tool_policy\|code_guardian)' anima-agent/**/*.hexa` 결과:

- **hexa `use` 구문 기준 → 0 건**
- 서브디렉토리(channels/providers/plugins/skills/trading) 내 `use` 구문 → 0 건
- `cli_agent.hexa:101` 의 문자열 `"(use agent_tools for full list)"` 는 println 문자열 리터럴 (무관)

결론: **hexa 레벨 import cascade 없음**. Phase 1 은 컴파일 그래프 변경 없이 순수 파일 이동만 발생.

### 3.2 문서·설정 참조 (수정 필요)

Grep `anima-agent/(run|agent_sdk|agent_tools|tool_policy|code_guardian|unified_registry)` 결과 36 건, 9 파일:

| 파일 | 건수 | 조치 |
|------|------|------|
| `README.md` | 10 | `anima-agent/run.hexa` → `anima-agent-core/run.hexa` 경로 갱신 |
| `ready/README.md` | 10 | 동일 (legacy, 참조만) |
| `docs/anima_agent_restructure_plan_20260419.md` | 1 | blueprint, 유지 |
| `docs/superpowers/plans/2026-04-02-extreme-accel-roadmap.md` | 3 | `run.py` → `run.hexa` 겸사 정정 |
| `ready/docs/superpowers/plans/2026-04-02-extreme-accel-roadmap.md` | 3 | 동일 |
| `ready/anima/modules/agent/README.md` | 6 | 동일 |
| `training/deploy/smoke_full_ubu2_*.tsv` | 3 | 아카이브(재생성), 수정 불요 |

### 3.3 shared/ 설정 (동기화 필수)

`grep anima-agent shared/` 발견된 JSON 키:

| 파일 | 항목 |
|------|------|
| `shared/config/projects.json` | anima-agent entry (신규 `anima-agent-core` 추가) |
| `shared/config/project_config.json` | CLI entry path |
| `shared/config/infrastructure.json` | pod mount path |
| `shared/rules/anima.json` | L0 리스트에 `anima-agent-core/*` 추가 |
| `shared/state/*.json` (zeta_ab, alm_a2, d8_*, ...) | Phase 1 대상 파일은 미참조 (무관) |

**Phase 1 에서 실제 수정 필요한 shared/ 파일: 4 개** (projects/project_config/infrastructure/rules.anima).

### 3.4 Docker / 배포

| 파일 | 조치 |
|------|------|
| `anima-agent/Dockerfile` | `COPY run.hexa ...` 경로가 있으면 `anima-agent-core/run.hexa` 로 수정 |
| `docker-compose.yml` (있다면) | volume 마운트 경로 갱신 |

---

## 4. 안전 실행 절차 (git mv 시퀀스, 실행 X)

> **실행 금지**. 아래는 승인 후 단일 커밋에서 사용할 시퀀스.

```bash
# 0. safety: 작업 브랜치 + 현 상태 스냅샷
git checkout -b refactor/agent-phase1-core
git status && git log -1 --oneline

# 1. 목적지 디렉토리 생성
mkdir -p anima-agent-core/config

# 2. 6 .hexa 파일 이동 (git mv → rename 추적)
git mv anima-agent/run.hexa              anima-agent-core/run.hexa
git mv anima-agent/unified_registry.hexa anima-agent-core/unified_registry.hexa
git mv anima-agent/agent_sdk.hexa        anima-agent-core/agent_sdk.hexa
git mv anima-agent/agent_tools.hexa      anima-agent-core/agent_tools.hexa
git mv anima-agent/tool_policy.hexa      anima-agent-core/tool_policy.hexa
git mv anima-agent/code_guardian.hexa    anima-agent-core/code_guardian.hexa

# 3. config 이동
git mv anima-agent/config/agent_config.json anima-agent-core/config/agent_config.json
rmdir anima-agent/config 2>/dev/null || true

# 4. CLAUDE.md 신규 (anima-core 패턴)
# — Write tool 로 별도 생성, git add 만 여기서

# 5. 참조 경로 갱신 (grep 으로 전수 점검 후 Edit)
#   README.md, docs/superpowers/plans/*.md, ready/README.md,
#   shared/config/projects.json, shared/config/project_config.json,
#   shared/config/infrastructure.json, shared/rules/anima.json

# 6. 검증
$HEXA anima-agent-core/run.hexa --cli       # 기동 확인
$HEXA anima-agent/test_agent_platform.hexa  # 기존 테스트 통과
$HEXA anima-agent/test_e2e.hexa             # E2E 통과
grep -rE '^use\s+.*(run|agent_sdk|agent_tools|unified_registry|tool_policy|code_guardian)\b' anima-agent*/
# → 0 매치 유지 확인 (Phase 1 은 import cascade 없음이 전제)

# 7. 커밋
git commit -m "refactor(agent): extract core CLI + registry → anima-agent-core/"
```

### Dry-run 검증 (사전 실행 가능)

- `git mv -n <src> <dst>` — 실제 이동 없이 rename 유효성만 확인
- `git diff --stat HEAD` — 이동 전후 변경 규모 점검
- `hexa build anima-agent-core/run.hexa` — 빌드 성공 여부 (import 없음 확인)

---

## 5. 영향 요약

| 항목 | 수치 |
|------|------|
| 이동 파일 (.hexa) | 6 |
| 이동 파일 (config .json) | 1 |
| 신규 CLAUDE.md | 1 |
| 자매 hexa `use` 참조 수정 | **0** |
| 문서 경로 수정 (README 등) | 6 파일 / 약 32 건 |
| shared/ JSON 동기화 | 4 파일 |
| Docker 경로 수정 | 1~2 파일 |
| 삭제 파일 | 0 (Phase 1 범위 외) |

### 위험도
**낮음**. Phase 1 은 hexa `use` 의존성이 없는 독립 6 파일 이동이므로 컴파일 그래프 영향 없음.
유일 리스크는 문서/설정 경로 참조 누락 → grep 전수 점검으로 해소.

---

## 6. 다음 단계

- [ ] 본 문서 검토 및 승인
- [ ] Phase 1 실행 (별도 커밋 1 건)
- [ ] 검증 체크리스트 통과 후 Phase 2 착수 (서브디렉토리 승격 — import cascade 존재, 영향 재측정 필요)

---

_문서 LOC: 약 165. 실행 금지 blueprint._
