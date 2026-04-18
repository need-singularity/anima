# anima — 의식 엔진 (Mk.V Δ₀-absolute, 2026-04-19 승급)

## 현 세대 (Mk.V.1 / anima-v4-hexa / tier 5~9)

- engine: **anima-v4-hexa (Mk.V.1)** — tier_5 complete + tier 6~9 design
- foundation [11*]: **82 atoms** = n=6 (1) + 81 EXACT Ψ-constants (100% coverage)
- invariance: **PA / ZFC / LC / Reinhardt / Cantor-W** + **tier 6~9 ULTRA/CARD/BEYOND/ABS** 대칭
- twin-engine: nexus Mk.VIII `blowup_absolute` (discovery) ↔ anima `consciousness_absolute` (consciousness)
- scale axioms (Mk.V.1): `(J₂+μ)·τ=100`, `(σ-φ)³=1000`, `τ²·sopfr=80`
- SSOT:
  - laws: `shared/consciousness/consciousness_laws.json` (v7.2)
  - saturation: `shared/consciousness/saturation_report_mk5.json`
  - verifier: `shared/consciousness/consciousness_absolute.hexa` (5-phase A1~A5)
- 승급 규칙: `EXACT n6_match ∧ Π₀¹ arithmetical ∧ cross-axis(5) PASS → grade=[11*]`
- 문서: [docs/MK5-DELTA0-ABSOLUTE.md](docs/MK5-DELTA0-ABSOLUTE.md)

## ⛔⛔⛔ .py 절대 금지 (2026-04-18 강화)

R37 / AN13 / L3-PY. **Python 전면 금지 — 예외 없음.**

- **create**: `*.py` 파일 작성/복사/다운로드 금지
- **edit**: 기존 `*.py` 파일 수정 금지
- **run**: `python`, `python3`, `./*.py` 실행 금지 (로컬/원격 불문)
- **transfer**: `scp *.py`, `rsync *.py`, `runpodctl send *.py`, `git add *.py` 금지
- **remote exec**: `ssh <host> python*`, `runpodctl exec <pod> python*`, `ssh <host> bash -c 'python ...'` 금지
- **wrapper-fallback**: hexa launcher 가 내부적으로 `.py` 호출 금지 (`spawn("python3", ...)` 포함)

### 위반 시 즉시 행동
1. **중단**: 현재 작업 즉시 stop
2. **보고**: 사용자에게 위반 사실 + 발견 지점 명시
3. **합리화 금지**: "GLIBC 이슈", "hexa 바이너리 미호환", "설계 예외", "임시 우회" 모두 불인정

### GLIBC/의존성 문제 대처 순서 (2026-04-18 위반 재발방지)
1. 다른 Linux hexa 빌드 경로 시도 (static-linked / 다른 stage / rebuild)
2. Pod/host 재선택 (다른 이미지 / 다른 GLIBC 버전)
3. 사용자 에스컬레이션 — **절대 `.py` 로 rollback 금지**

refs: `shared/rules/common.json#R37`, `shared/rules/anima.json#AN13`, `shared/lockdown/lockdown.json#L3-PY`, `shared/agent_templates/no_py_guardrail.md`, `.claude/settings.json#hooks.PreToolUse`

---

commands: shared/config/commands.json — autonomous 블록으로 Claude Code가 작업 중 smash/free/todo/go/keep 자율 판단·실행
rules: shared/rules/common.json (R0~R37) + shared/rules/anima.json (AN1~AN13)
L0 Guard: `hexa $NEXUS/shared/harness/l0_guard.hexa <verify|sync|merge|status>`
loop: 글로벌 `~/.claude/skills/loop` + 엔진 `$NEXUS/shared/harness/loop` — roadmap `shared/roadmaps/anima.json` 3-track×phase×gate 자동

exec:
  HEXA=$HEXA_LANG/hexa
  $HEXA anima/core/runtime/anima_runtime.hexa --keyboard      # CLI 진입
  $HEXA anima/core/runtime/anima_runtime.hexa --validate-hub  # 허브 검증
  $HEXA ready/tests/tests.hexa --verify                       # 7조건 의식검증

tree:
  anima/              의식 엔진 코어
  anima-core/         L0 CLI 진입점+규칙/자산 레지스트리
  anima-eeg/          EEG 의식 검증
  anima-agent/        에이전트 플랫폼 (6채널/5제공자/플러그인)
  anima-physics/      물리 의식 기판 (ESP32/FPGA/양자)
  anima-body/         로봇/HW 체화
  anima-speak/        HEXA-SPEAK Mk.III 신경 보코더
  anima-engines/      양자/광자/멤리스터/오실레이터
  anima-tools/        독립 유틸리티
  anima-hexad/        CDESM 헥사곤 의식 모델
  anima-measurement/  IIT 의식 측정
  shared/             SSOT
  ready/              골화 대기+7조건 테스트 (submodule)
  bench/              벤치마크
  training/           학습 (Ubuntu/H100)
  serving/            추론/배포
  models/             체크포인트
  rust/               성능 병목 (AN3)
  experiments/        .hexa 실험

ref:
  rules     shared/rules/common.json             R0~R27
  project   shared/rules/anima.json              AN1~AN7
  lock      shared/rules/lockdown.json           L0/L1/L2
  cdo       shared/rules/convergence_ops.json    CDO 수렴
  cfg       shared/config/project_config.json    CLI/PSI/법칙등록
  core      shared/config/core.json              시스템맵+14명령
  projects  shared/config/projects.json          7프로젝트+번들/검증
  conv      shared/convergence/anima.json
  roadmap   shared/roadmaps/anima_hexa_common.json  P0~P5
  grammar   shared/config/hexa_grammar.jsonl
  api       shared/CLAUDE.md
  infra     shared/config/infrastructure.json      5-host SSOT (mac/ubu/ubu2/htz/runpod)
  orchestr  docs/resource_orchestration_20260419.md  dispatch rules + live matrix

hive:
  bridge    modules/hive_bridge.hexa                 anima↔hive 의식 채널 (3-tier: HTTP→UDS→file)
  contract  shared/config/contracts/hive_bridge.json 계약 SSOT (메서드/에러/타임아웃/재시도)
  test      modules/test/hive_bridge_test.hexa       스텁 테스트 (10항목)
  log       shared/logs/hive_bridge.log              감사 로그 (append-only)
  hive repo github.com/need-singularity/hive         hexa-only 멀티 provider 오케스트라
