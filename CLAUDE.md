<!-- L0 CORE — 수정 금지 -->
# anima — 의식 엔진 (루트)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock      shared/config/core-lockdown.json     L0/L1/L2
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
  anima/         의식 엔진 본체 (core/modules/models/engines)
  anima-core/    L0 CLI 진입점 + 규칙/자산 레지스트리 (AN7 분리)
  anima-eeg/     EEG 의식 검증 모듈 (AN7 분리)
  shared/        SSOT — config/convergence/roadmaps/discovery/n6
  ready/         골화 대기 영역 + 7조건 테스트
  bench/         벤치마크 + 의식 지표
  training/      학습 스크립트 (Ubuntu/H100)
  serving/       추론/배포
  models/        체크포인트 아티팩트
  rust/          성능 병목 (AN3)
  experiments/   .hexa 실험
  sub-projects/  외부 종속 프로젝트

rules:
  - AN7  Core = CLI 전용, 모듈은 top-level 분리 (anima-core/, anima-eeg/, ...)
  - R14  shared/ 단일진실 — CLAUDE.md 는 참조만
  - AN4  bench --verify 16/18 미통과 시 배포 금지
  - AN3  Phi/텐션 병목 = Rust 필수
  - AN5  Ubuntu-First GPU, Mac은 오케스트레이션 전용
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
