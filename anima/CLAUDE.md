# anima/ — 의식 엔진 코어

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/rules/common.json             R0~R27 공통
  project   shared/rules/anima.json              AN1~AN7
  lock      shared/rules/lockdown.json           L0/L1/L2
  cfg       shared/config/project_config.json    CLI/PSI/법칙등록
  core      shared/config/core.json              시스템맵 + 14명령
  conv      shared/convergence/anima.json
  laws      config/consciousness_laws.json       2390 법칙 + Psi 상수
  api       shared/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA core/runtime/anima_runtime.hexa --keyboard      # CLI
  $HEXA core/runtime/anima_runtime.hexa --validate-hub  # 허브 검증

tree:
  core/          L0 골화 (hub.hexa, laws.hexa, runtime/, verification/)
  modules/       소형 10개 (decoder,servant,trinity,training,learning,monitor,sync,cloud,education,logging)
  config/        consciousness_laws.json + 실험/학습/검증 JSON
  archive/       폐기 코드 보관

rules (R1 HEXA-ONLY AI-NATIVE):
  - 신규 코드는 .hexa 단일 언어만 (shared/rules/common.json R1)
  - .rs/.py/.sh/pyproject.toml/Cargo.toml 신규 생성 절대 금지 — PreToolUse hook 차단
  - 기존 .py/.rs/.sh 편집은 제거/흡수 목적일 때만 허용
