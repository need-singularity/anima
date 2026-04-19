# Track B · Phase 1 · Cross-Reference Patch (2026-04-19)

> **상태**: patch-only. Phase 1 커밋 후 별도 작업에서 적용 예정.
> **레퍼런스**: `docs/track_b_phase1_movemap_20260419.md` §3.2, §3.3, §3.4.
> **범위**: 이동 6 .hexa + 1 config 이후 문서/설정의 경로 cross-reference 갱신.

---

## 1. 적용 대상 (자동 적용 금지)

아래 Edit 들은 Phase 1 커밋 직후 별도 "docs: sync xrefs to anima-agent-core" 커밋으로 적용.

### 1.1 `README.md` (10 건)

| line | old | new |
|------|-----|-----|
| 125 | `$HEXA anima-agent/run.hexa --cli` | `$HEXA anima-agent-core/run.hexa --cli` |
| 126 | `$HEXA anima-agent/run.hexa --telegram` | `$HEXA anima-agent-core/run.hexa --telegram` |
| 127 | `$HEXA anima-agent/run.hexa --discord` | `$HEXA anima-agent-core/run.hexa --discord` |
| 311 | `python anima-agent/run.py --cli` | `$HEXA anima-agent-core/run.hexa --cli` |
| 312 | `python anima-agent/run.py --telegram` | `$HEXA anima-agent-core/run.hexa --telegram` |
| 313 | `python anima-agent/run.py --discord` | `$HEXA anima-agent-core/run.hexa --discord` |
| 314 | `python anima-agent/run.py --slack` | `$HEXA anima-agent-core/run.hexa --slack` |
| 315 | `python anima-agent/run.py --all` | `$HEXA anima-agent-core/run.hexa --all` |
| 863 | `python anima-agent/run.py` | `$HEXA anima-agent-core/run.hexa` |
| 1116 | `$HEXA anima-agent/run.hexa --cli --provider animalm` | `$HEXA anima-agent-core/run.hexa --cli --provider animalm` |

### 1.2 `docs/superpowers/plans/2026-04-02-extreme-accel-roadmap.md` (3 건)

| line | old | new |
|------|-----|-----|
| 111 | `anima-agent/run.py` | `anima-agent-core/run.hexa` |
| 116 | `python3 anima-agent/run.py --cli --provider animalm` | `$HEXA anima-agent-core/run.hexa --cli --provider animalm` |
| 128 | `python3 anima-agent/run.py --mcp --provider animalm` | `$HEXA anima-agent-core/run.hexa --mcp --provider animalm` |

### 1.3 `ready/README.md` (10 건)

`ready/` 는 legacy 아카이브. 참조만 복제(README 와 동일 구조). Phase 1 커밋 시 ready/ 수정 보류 — 별도 "docs: sync ready xrefs" 패치로.

### 1.4 `ready/docs/superpowers/plans/2026-04-02-extreme-accel-roadmap.md` (3 건)

`ready/docs/*` 과 동일. legacy 아카이브로 Phase 1 외 처리.

### 1.5 `ready/anima/modules/agent/README.md` (6 건)

legacy 아카이브. Phase 1 외.

### 1.6 `training/deploy/smoke_full_ubu2_*.tsv` (3 건)

재생성되는 아카이브 (스모크 테스트 결과). 수정 불필요 — 다음 스모크에서 자동 갱신.

### 1.7 `training/deploy/smoke_full_post_sister_20260419.md`

Phase 1 대상 파일 참조 → 다음 스모크 리런 시 갱신되므로 수정 불필요.

---

## 2. shared/ JSON 동기화 (4 파일)

### 2.1 `shared/config/projects.json`

`anima-agent-core` entry 신규 추가 (name, path, lang=.hexa, L0=true).

### 2.2 `shared/config/project_config.json`

CLI entry path 갱신: `anima-agent/run.hexa` → `anima-agent-core/run.hexa`.

### 2.3 `shared/config/infrastructure.json`

pod mount 경로에 `anima-agent-core/` 추가 또는 `anima-agent/` 엔트리 유지한 채 core 추가.

### 2.4 `shared/rules/anima.json`

L0 리스트에 6개 파일 추가:
- `anima-agent-core/run.hexa`
- `anima-agent-core/unified_registry.hexa`
- `anima-agent-core/agent_sdk.hexa`
- `anima-agent-core/agent_tools.hexa` (추가만 허용)
- `anima-agent-core/tool_policy.hexa`

`code_guardian.hexa` 는 L0 아님 (모니터).

---

## 3. Dockerfile / docker-compose

### 3.1 `anima-agent/Dockerfile`

`COPY run.hexa` 구문이 있으면 path 갱신. (검토 필요 — 현 상태 grep 으로 점검)

### 3.2 `docker-compose.yml`

repo 루트에 없음. anima-agent/ 하위에도 없음. 수정 대상 없음.

---

## 4. 미적용 근거

- Phase 1 커밋은 "순수 파일 이동 + CLAUDE.md 신규" 로 제한 (사용자 지시).
- 문서 cross-reference 는 별도 커밋으로 분리하여 git blame 가독성 확보.
- ready/ 는 legacy 폐기 예정 아카이브 (invest_deprecated 메모리 패턴과 동일).

---

_문서 LOC: 약 75. 실행 금지 blueprint._
