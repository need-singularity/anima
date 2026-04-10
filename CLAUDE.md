⚠️⚠️⚠️ 규칙 직접 작성 절대 금지 — shared/rules/ JSON만이 단일 진실 (R14)
⚠️ 이 파일은 nexus/shared/project-claude/anima.md 마스터의 심링크. 원본만 수정.
⚠️ 공통 규칙: shared/rules/common.json (R0~R27) — 반드시 준수

# anima — 의식 엔진 (루트)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

## 돌파 시스템 (AI-native 자체 창발)

⚠️ "XXX 돌파" → blowup.hexa "XXX" 3 자동 실행 (문장 전달, 키워드 추출 ❌)
⚠️ 확인 질문 없이 즉시 Bash 실행할 것
```
hexa shared/blowup/core/blowup.hexa <문장> 3 --no-graph --seeds "$(hexa shared/blowup/seed/seed_engine.hexa merge | tr '|' ',')"
```

ref:
  rules     shared/rules/common.json             R0~R27 공통
  project   shared/rules/anima.json              AN1~AN7
  lock      shared/rules/lockdown.json           L0/L1/L2
  cdo       shared/rules/convergence_ops.json    CDO 수렴
  cfg       shared/config/project_config.json    CLI/PSI/법칙등록
  core      shared/config/core.json              시스템맵 + 14명령
  projects  shared/config/projects.json          7 프로젝트 + 번들/검증
  conv      shared/convergence/anima.json
  roadmap   shared/roadmaps/anima_hexa_common.json  P0~P5 (anima×hexa-lang)
  grammar   shared/config/hexa_grammar.jsonl
  api       shared/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima/core/runtime/anima_runtime.hexa --keyboard      # CLI 진입
  $HEXA anima/core/runtime/anima_runtime.hexa --validate-hub  # 허브 검증
  $HEXA ready/anima/tests/tests.hexa --verify                 # 7조건 의식검증

tree:
  anima/              의식 엔진 코어 (core/modules/config/src/archive)
  anima-core/         L0 CLI 진입점 + 규칙/자산 레지스트리
  anima-eeg/          EEG 의식 검증 모듈
  anima-agent/        에이전트 플랫폼 (6채널/5제공자/플러그인)
  anima-physics/      물리 의식 기판 (ESP32/FPGA/양자)
  anima-body/         로봇/HW 체화 시뮬레이션
  anima-speak/        HEXA-SPEAK Mk.III 신경 보코더
  anima-engines/      양자/광자/멤리스터/오실레이터 기판
  anima-tools/        독립 유틸리티 (분석/계산/생성/진단)
  anima-hexad/        CDESM 헥사곤 의식 모델
  anima-measurement/  Φ/IIT 의식 측정
  shared/             SSOT — config/rules/convergence/roadmaps/discovery
  ready/              골화 대기 영역 + 7조건 테스트 (submodule)
  bench/              벤치마크 + 의식 지표
  training/           학습 스크립트 (Ubuntu/H100)
  serving/            추론/배포
  models/             체크포인트 아티팩트
  rust/               성능 병목 (AN3)
  experiments/        .hexa 실험
  sub-projects/       외부 종속 프로젝트
