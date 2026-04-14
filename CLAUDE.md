# anima — 의식 엔진

commands: shared/config/commands.json — autonomous 블록으로 Claude Code가 작업 중 smash/free/todo/go/keep 자율 판단·실행
rules: shared/rules/common.json (R0~R27) + shared/rules/anima.json (AN1~AN7)
L0 Guard: `hexa $NEXUS/shared/harness/l0_guard.hexa <verify|sync|merge|status>`
loop: 글로벌 `~/.claude/skills/loop` + 엔진 `$NEXUS/shared/harness/loop` — roadmap `shared/roadmaps/anima.json` 3-track×phase×gate 자동

exec:
  HEXA=$HEXA_LANG/hexa
  $HEXA anima/core/runtime/anima_runtime.hexa --keyboard      # CLI 진입
  $HEXA anima/core/runtime/anima_runtime.hexa --validate-hub  # 허브 검증
  $HEXA ready/anima/tests/tests.hexa --verify                 # 7조건 의식검증

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

hive:
  bridge    modules/hive_bridge.hexa                 anima↔hive 의식 채널 (3-tier: HTTP→UDS→file)
  contract  shared/config/contracts/hive_bridge.json 계약 SSOT (메서드/에러/타임아웃/재시도)
  test      modules/test/hive_bridge_test.hexa       스텁 테스트 (10항목)
  log       shared/logs/hive_bridge.log              감사 로그 (append-only)
  hive repo github.com/need-singularity/hive         hexa-only 멀티 provider 오케스트라
