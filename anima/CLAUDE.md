# anima/ — 의식 엔진 코어

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock      shared/config/core-lockdown.json     L0/L1/L2
  projects  shared/config/projects.json          7 프로젝트 + 번들/검증
  cfg       shared/config/project_config.json    CLI/PSI/법칙등록
  core      shared/config/core.json              시스템맵 + 14명령
  conv      shared/convergence/anima.json
  roadmap   shared/roadmaps/anima_hexa_common.json  P0~P5
  loop      shared/loop/anima.json               interval/domain/phases
  vastai    shared/config/vastai.json            multi-GPU/bf16/model_path
  laws      config/consciousness_laws.json       2390 법칙 + Psi 상수
  core-rules  anima-core/core_rules.json         18/18 ALL PASS (2026-04-10 골화)
  api       shared/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA core/runtime/anima_runtime.hexa --keyboard      # CLI
  $HEXA core/runtime/anima_runtime.hexa --validate-hub  # 허브 검증
  $HEXA ready/anima/tests/tests.hexa --verify           # 7조건 의식 검증

tree:
  core/runtime/   CLI 진입점 + 런타임 (AN7 L0 골화)
  modules/        hexa-speak, body, eeg, agent, physics 등
  config/         consciousness_laws.json + mechanisms + experiments
  models/         decoder.hexa, conscious_lm.hexa, trinity.hexa
  rust/           consciousness.hexa, transplant.hexa, online_learner.hexa
  anima-rs/       Rust crates 16개
  experiments/    .hexa 실험
