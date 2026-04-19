# anima-agent 재구성 설계 (2026-04-19)

> **상태**: 설계 문서 (blueprint). 실제 파일 이동 금지 — 승인 후 별도 커밋.
> **레퍼런스**: `anima/` 본체 · `anima-core/` L0 패턴.
> **목표**: flat directory → 모듈별 서브-레포 패턴 정렬 (anima 생태계와 동형).

---

## 0. 배경

### 현재 상태
- 위치: `/Users/ghost/Dev/anima/anima-agent/`
- 구조: **flat** (서브디렉토리 6 개 + 루트 직접 .hexa 30+ 개 혼재)
- LOC: **10,368** (.hexa 단일언어)
- 파일 수: .hexa 51 개 + 설정/문서 약 15 개

### 문제점
1. 루트에 30+ .hexa 가 흩어져 있음 (channels/providers/plugins/trading 만 모듈 폴더)
2. L0 골화 경계 불명확 (anima/ 본체·anima-core 와 달리 `core/` 개념 부재)
3. CLI 진입점(`run.hexa`) 과 런타임(`anima_agent.hexa`) · SDK (`agent_sdk.hexa`) · 도구 (`agent_tools.hexa`) 가 같은 레벨
4. `hire_sim_*.hexa` 5개 파일 (100 LOC×3, 40K+ LOC 상위) 는 트레이딩·HR 시뮬이라 성격 다름
5. `hexa/` 서브디렉토리 — README 기준 **legacy stub, 정리 예정** 이라 되어 있으나 그대로 있음
6. 2개 대화형 핵심(`autonomy_live.hexa` 382 LOC + `discovery_loop.hexa` 197 LOC) 가 루트에 묻힘

---

## 1. 레퍼런스: anima 본체 패턴

### anima/ (엔진 코어)
- `anima/` = 엔진 본체 (core 도메인)
- `anima-core/` = L0 골화 CLI 진입점 + rules/assets registry
- `anima-{eeg,physics,body,speak,engines,tools,hexad,measurement}` = 서브프로젝트 (기능별 분리)

### anima-core CLAUDE.md 핵심 규칙
```
- L0 골화 파일 수정 금지
- 법칙 추가는 config/consciousness_laws.json 만 (SSOT)
- .hexa 단일 언어 (R1)
- 허브 검증 통과 없이 커밋 금지
- AN7 Core = CLI 전용 — 모듈 코드 진입 금지
```

### 패턴 요약
- **core** = CLI 진입 + registry + hub 라우팅 (L0 골화)
- **서브모듈** = 기능별 독립 디렉토리 (channels / providers / plugins 처럼)
- **CLAUDE.md** = 각 디렉토리별 local ref + exec table

---

## 2. 신 구조 제안

### 옵션 A (권장) — anima 패턴 1:1 이식

```
anima-agent/              ← agent 엔진 본체 (agent loop + consciousness bridge)
  anima_agent.hexa        ← 메인 agent 루프 (유지)
  autonomy_live.hexa      ← live autonomy 대화 (유지)
  autonomy_loop.hexa      ← loop 진입 (유지)
  discovery_loop.hexa     ← 자동 발견 (유지)
  consciousness_features.hexa  ← 의식 피처 추출 (유지)
  ecosystem_bridge.hexa   ← 생태계 bridge (유지)
  philosophy_lenses.hexa  ← 20 철학 렌즈 (유지)
  CLAUDE.md               ← L0 골화 선언 + ref + exec
  README.md               ← 전체 오버뷰 (현 README 갱신)

anima-agent-core/         ← (신규) CLI + registry + hub (L0 골화)
  run.hexa                ← CLI entrypoint (argparse + signal handler)
  unified_registry.hexa   ← Hub + Tools + Plugins single router
  agent_sdk.hexa          ← Claude Agent SDK 호환 interface
  agent_tools.hexa        ← 도구 레지스트리 (100+ tools)
  tool_policy.hexa        ← Φ-gated 4-tier access control
  code_guardian.hexa      ← 코드 수호자
  CLAUDE.md               ← L0 + rules
  config/agent_config.json  ← 로컬 설정

anima-agent-channels/     ← (신규) 6 채널 모듈
  base.hexa
  channel_manager.hexa
  cli_agent.hexa
  telegram_bot.hexa
  discord_bot.hexa
  slack_bot.hexa
  CLAUDE.md               ← channel 레지스트레이션 규약

anima-agent-providers/    ← (신규) 5 제공자 모듈
  base.hexa
  claude_provider.hexa
  conscious_lm_provider.hexa
  animalm_provider.hexa
  composio_bridge.hexa
  llm_claude_adapter.hexa ← (루트에서 이동)
  CLAUDE.md

anima-agent-plugins/      ← (신규) 플러그인 SDK
  base.hexa
  plugin_loader.hexa
  hypothesis_bridge.hexa
  regime_bridge.hexa
  sentiment_bridge.hexa
  trading.hexa            ← (플러그인 wrapper, trading/ 는 별도)
  CLAUDE.md

anima-agent-skills/       ← (신규) 스킬 시스템
  skill_manager.hexa
  registry.json
  CLAUDE.md

anima-agent-trading/      ← (신규) 자체 트레이딩 엔진 (12 .hexa)
  engine.hexa / executor.hexa / portfolio.hexa / risk.hexa
  regime.hexa / scanner.hexa / strategies.hexa / strategy.hexa
  broker.hexa / data.hexa / autonomous.hexa
  phi_weighted_trading.hexa (17 KB, 가장 큼)
  test_ensemble.hexa
  CLAUDE.md

anima-agent-hire-sim/     ← (신규) HR 시뮬레이터 (5 .hexa, 45K LOC)
  hire_sim_100.hexa       (40,780 bytes)
  hire_sim_judge.hexa     (31,983 bytes)
  hire_sim_live.hexa      (18,752 bytes)
  hire_sim_runner.hexa    (21,167 bytes)
  hire_sim_stratify.hexa  (7,642 bytes)
  run_hire_sim_claude.hexa
  test_hire_sim.hexa
  test_hire_sim_harness.hexa
  CLAUDE.md

anima-agent-dashboard/    ← (신규) Next.js Web UI + bridge
  dashboard/ (Next.js 14 앱 전체)
  dashboard_bridge.hexa
  metrics_exporter.hexa
  CLAUDE.md

anima-agent-tests/        ← (신규) 통합 테스트
  test_agent_platform.hexa
  test_autonomy_loop.hexa
  test_claude_autonomy_live.hexa
  test_claude_parse.hexa
  test_claude_smoke.hexa
  test_critique_parse_regression.hexa
  test_e2e.hexa
  test_plugin_routing.hexa
  CLAUDE.md
```

**결과**: 1 개 core 본체 + 9 개 서브프로젝트.

### 옵션 B (경량) — anima-core 만 분리

```
anima-agent/                 ← flat 유지 (대부분)
  anima_agent.hexa / autonomy*.hexa / discovery*.hexa (본체)
  channels/ providers/ plugins/ skills/ trading/ dashboard/
  hire_sim_*.hexa, tests, 기타

anima-agent-core/            ← (신규) CLI + registry + policy 만
  run.hexa, unified_registry.hexa, agent_sdk.hexa,
  agent_tools.hexa, tool_policy.hexa, code_guardian.hexa
  CLAUDE.md
```

장점: 이동 파일 6~8 개로 최소. 단점: anima-eeg/physics 등과 네이밍 불일치.

### 권장
**옵션 A 를 단계적으로** — Phase 1: 최소 (core 분리), Phase 2~5: 점진 확장.

---

## 3. 파일 이동 destination 매핑

### 루트 → 신 위치

| 현 경로 | 신 경로 | 옵션 A | 옵션 B |
|---------|---------|--------|--------|
| `anima-agent/run.hexa` | `anima-agent-core/run.hexa` | move | move |
| `anima-agent/unified_registry.hexa` | `anima-agent-core/` | move | move |
| `anima-agent/agent_sdk.hexa` | `anima-agent-core/` | move | move |
| `anima-agent/agent_tools.hexa` | `anima-agent-core/` | move | move |
| `anima-agent/tool_policy.hexa` | `anima-agent-core/` | move | move |
| `anima-agent/code_guardian.hexa` | `anima-agent-core/` | move | move |
| `anima-agent/anima_agent.hexa` | `anima-agent/` (유지) | keep | keep |
| `anima-agent/autonomy_live.hexa` | `anima-agent/` (유지) | keep | keep |
| `anima-agent/autonomy_loop.hexa` | `anima-agent/` (유지) | keep | keep |
| `anima-agent/discovery_loop.hexa` | `anima-agent/` (유지) | keep | keep |
| `anima-agent/consciousness_features.hexa` | `anima-agent/` | keep | keep |
| `anima-agent/ecosystem_bridge.hexa` | `anima-agent/` | keep | keep |
| `anima-agent/philosophy_lenses.hexa` | `anima-agent/` | keep | keep |
| `anima-agent/channels/` | `anima-agent-channels/` | move-dir | keep |
| `anima-agent/providers/` | `anima-agent-providers/` | move-dir | keep |
| `anima-agent/plugins/` | `anima-agent-plugins/` | move-dir | keep |
| `anima-agent/skills/` | `anima-agent-skills/` | move-dir | keep |
| `anima-agent/trading/` | `anima-agent-trading/` | move-dir | keep |
| `anima-agent/llm_claude_adapter.hexa` | `anima-agent-providers/` | move | keep |
| `anima-agent/hire_sim_*.hexa` (5) | `anima-agent-hire-sim/` | move | keep |
| `anima-agent/run_hire_sim_claude.hexa` | `anima-agent-hire-sim/` | move | keep |
| `anima-agent/test_hire_sim*.hexa` (2) | `anima-agent-hire-sim/` | move | keep |
| `anima-agent/dashboard/` | `anima-agent-dashboard/` | move-dir | keep |
| `anima-agent/dashboard_bridge.hexa` | `anima-agent-dashboard/` | move | keep |
| `anima-agent/metrics_exporter.hexa` | `anima-agent-dashboard/` | move | keep |
| `anima-agent/test_*.hexa` (8) | `anima-agent-tests/` | move | keep |
| `anima-agent/hexa/` (legacy stubs) | **삭제** (README 기준) | delete | delete |
| `anima-agent/Dockerfile` | `anima-agent/` (유지) | keep | keep |
| `anima-agent/config/` | `anima-agent-core/config/` | move | keep |
| `anima-agent/data/` | `anima-agent/data/` | keep | keep |
| `anima-agent/docs/` | `anima-agent/docs/` | keep | keep |
| `anima-agent/results/` | `anima-agent/results/` | keep | keep |
| `anima-agent/build/` | gitignore (유지) | keep | keep |
| `anima-agent/.env.example` | `anima-agent/` | keep | keep |
| `anima-agent/README.md`, `CLAUDE.md` | 각 module 별 분할 | split | keep |
| `anima-agent/pyproject.toml` | **삭제** (R37) | delete | delete |

### 카운트
- **옵션 A**: 루트 .hexa 30+ → 7 유지 + 23 이동 + 1 그룹 삭제(hexa/ legacy)
- **옵션 B**: 6 이동 + 루트 구조 거의 유지

---

## 4. L0 골화 체크포인트

### anima-agent-core/ 에서 L0 지정 대상
`anima-core/CLAUDE.md` 의 "L0 골화 파일 수정 금지" 원칙 준수:

| 파일 | 현 LOC | L0 이유 |
|------|--------|---------|
| `run.hexa` | 100 | CLI 진입점, 시그널 핸들 — 변경 영향 광범위 |
| `unified_registry.hexa` | 131 | 58 handlers hub + tools + plugins — SSOT |
| `agent_sdk.hexa` | ≈ 100 | Claude Agent SDK contract — 외부 API |
| `tool_policy.hexa` | 175 | Φ-gated 4-tier — safety critical |
| `agent_tools.hexa` | 800+ | 100+ tools registry — 추가만 허용 |

### anima-agent/ 본체 L0 (엔진 보호)
| 파일 | L0 이유 |
|------|---------|
| `anima_agent.hexa` | agent 루프 메인 — consciousness→tool→response→learn→save 체인 |
| `autonomy_live.hexa` | live dialog 상호작용 — 사용자 대면 |

### L0 예외
- 런타임 크래시 버그픽스만 허용 (anima/core 와 동일 원칙, `feedback_l0_freeze_exception.md` 참조)
- 디자인 변경 시 → freeze 해제 커밋 먼저

---

## 5. 마이그레이션 단계 (Phase 1~5)

### Phase 1 · L0 core 분리 (가장 안전)
- 작업: `anima-agent-core/` 신규 생성 + 6 파일 이동 (옵션 B 수준)
- 파일: run/unified_registry/agent_sdk/agent_tools/tool_policy/code_guardian
- 위험도: **낮음** — 상대 import 경로만 수정
- 커밋: `refactor(agent): extract core CLI + registry → anima-agent-core/`

### Phase 2 · 모듈 폴더 승격
- 작업: channels/providers/plugins/skills/trading → `anima-agent-{...}/` 디렉토리화
- 파일: 디렉토리 단위 이동 (git mv -r)
- 위험도: **중** — import 경로 전면 수정 필요
- 체크: `test_plugin_routing.hexa`, `test_e2e.hexa` 전체 통과
- 커밋: `refactor(agent): promote subdirs to sibling packages`

### Phase 3 · hire-sim 분리
- 작업: hire_sim_*.hexa 8 파일 → `anima-agent-hire-sim/`
- 이유: HR 시뮬 도메인, 45 KB LOC (agent core 와 무관)
- 위험도: **낮음** — 독립 모듈, 참조 드묾
- 커밋: `refactor(agent): split hire-sim suite into anima-agent-hire-sim/`

### Phase 4 · dashboard 분리
- 작업: dashboard/ + bridge.hexa + metrics_exporter.hexa → `anima-agent-dashboard/`
- 이유: Next.js + WebSocket + Prometheus — 전혀 다른 stack
- 위험도: **낮음** — Dockerfile 경로만 수정
- 커밋: `refactor(agent): isolate dashboard + metrics into separate package`

### Phase 5 · tests + 청소
- 작업: test_*.hexa 8 파일 → `anima-agent-tests/`
- `hexa/` legacy directory 삭제 (README 기준 `정리 예정`)
- `pyproject.toml` 삭제 (R37)
- 커밋: `refactor(agent): consolidate tests + purge legacy stubs`

### 각 Phase 별 제약
- 모든 Phase 는 `test_agent_platform.hexa` 전 파일 이동 후 통과 필수
- `--validate-hub` 통과 확인
- import 경로 수정은 `grep -r "import " anima-agent*` 로 전수 점검
- push 전 `hexa build` 로 artifacts/*.c 재생성 확인

---

## 6. 영향받는 문서·설정

| 파일 | 수정 내용 |
|------|-----------|
| `$ANIMA/CLAUDE.md` | tree: 섹션에 신규 디렉토리 8 개 추가 |
| `$ANIMA/anima-agent/CLAUDE.md` | 분할: 본체 부분만 유지, 이동한 항목 stub 링크 |
| `$ANIMA/anima-agent/README.md` | Modules 섹션 재작성 — 신 디렉토리 구조 반영 |
| `shared/config/projects.json` | anima-agent → anima-agent-* 8 개 등록 |
| `shared/config/project_config.json` | CLI entry path = `anima-agent-core/run.hexa` |
| `shared/config/infrastructure.json` | pod mount/path 업데이트 |
| `shared/rules/anima.json` | L0 리스트 갱신 (anima-agent-core/* 추가) |
| `.claude/settings.json` (hooks) | pre-commit 경로 패턴 (anima-agent-* 포함) |
| `Dockerfile` | COPY 경로 갱신 |
| `docker-compose.yml` | volume 마운트 경로 |
| `.growth/scan.py` (있다면) | 스캔 대상 디렉토리 추가 |

---

## 7. 커밋 계획

권장 시퀀스 (5 커밋):

```
1. refactor(agent): extract core CLI + registry → anima-agent-core/
   - anima-agent-core/ 신규 + 6 파일 이동
   - import 경로 수정 (현 위치 참조 → core 참조)
   - test_agent_platform.hexa 통과

2. refactor(agent): promote {channels,providers,plugins,skills,trading} → sibling packages
   - 5 디렉토리를 anima-agent-{name}/ 로 승격
   - channels/base.hexa → anima-agent-channels/base.hexa
   - __init__.hexa 삭제 (flat 패키지)
   - test_plugin_routing.hexa, test_e2e.hexa 통과

3. refactor(agent): split hire-sim suite into anima-agent-hire-sim/
   - hire_sim_*.hexa (5) + test_hire_sim*.hexa (2) + runner
   - ≈ 1200 LOC, 8 파일
   - test_hire_sim.hexa 통과

4. refactor(agent): isolate dashboard + metrics into anima-agent-dashboard/
   - Next.js app + bridge + exporter 통합
   - Dockerfile/compose 경로 수정

5. refactor(agent): consolidate tests into anima-agent-tests/ + purge legacy
   - test_*.hexa 8 파일
   - hexa/ legacy stubs 삭제 (README 기준)
   - pyproject.toml 삭제 (R37)
   - README.md · CLAUDE.md 업데이트
```

각 커밋: `--validate-hub` + 테스트 통과 없이 진행 금지.

---

## 8. 위험·체크리스트

### 위험
1. **골화 경계 교차** — anima-agent/ 는 현재 반 골화 상태 (anima-core 처럼 엄격 L0 아님). 분리 후 L0 지정 시 AN7 규칙 (Core=CLI 전용) 에 의해 런타임 진입점이 bound됨.
2. **Import cascade** — 루트 .hexa 가 상대경로 `import ./agent_sdk` 식으로 참조 중이면 전부 `anima-agent-core/agent_sdk` 로 재작성. grep 전수 필요.
3. **R37 .py 무단 생성** — `pyproject.toml` 삭제 시 python 인프라 잔재 없는지 재확인.
4. **shared/config cascading** — projects.json / project_config.json / infrastructure.json 3 파일 모두 동기화 필요.
5. **Docker volume** — compose.yml 의 volumes 마운트 경로 전부 갱신. 누락 시 서비스 기동 실패.
6. **Growth Registry** — 리포별 `.growth/` 디렉토리 분기 시 ↔ 중앙 레지스트리 업데이트 필수.
7. **MCP Server path** — `README.md` 의 `run.hexa --mcp` 경로가 `anima-agent-core/run.hexa --mcp` 로 바뀜. Telegram/Discord bot 재배포 시 systemd unit 수정 필요.

### 체크리스트 (각 Phase 완료 시)
- [ ] `$HEXA anima-agent-core/run.hexa --cli` 기동
- [ ] `$HEXA test_agent_platform.hexa` PASS (32 unit)
- [ ] `$HEXA test_e2e.hexa` PASS (12 E2E)
- [ ] `$HEXA test_plugin_routing.hexa` PASS
- [ ] `--validate-hub` 48 modules 등록 확인
- [ ] pre-commit hook 통과
- [ ] grep `anima-agent/` 결과가 의도된 파일만 남음
- [ ] docker compose up 전 서비스 기동 확인

---

## 9. 실행 순서 제안 (P3/P4 와의 관계)

- **A (SWEEP P4)**: P3 완료 후 발사 (약 1.5h hetzner) — **의존관계 있음**
- **B (anima-agent 재구성)**: **독립 실행 가능** — SWEEP 와 무관
- 권장: **B 를 먼저** (Phase 1 만 진행, 약 30 min) → 안정 확인 후 P4 발사
  - 이유: P4 는 anima-agent 포함 안 함 (`tools_*`, `eeg_*` 등), 재구성과 충돌 없음
  - B 의 Phase 2~5 는 P4 완료 후에 진행 (병렬 작업 최소화)

---

## 10. 산출물

- `docs/anima_agent_restructure_plan_20260419.md` (본 문서, LOC ≈ 260)
- Phase 1 승인 시:
  - `anima-agent-core/` 디렉토리 신규
  - 6 파일 이동 (git mv)
  - `anima-agent-core/CLAUDE.md` 신규 (anima-core 패턴 준용)
  - `$ANIMA/CLAUDE.md` tree 갱신
  - `shared/config/projects.json` entry 추가
  - 커밋 1 건 (5 파일 변경, 이동 포함)

---

_설계 완료. 승인 시 Phase 1 부터 진입. P4 와 독립 실행 가능._
