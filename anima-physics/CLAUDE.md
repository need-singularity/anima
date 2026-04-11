# anima-physics — ESP32/FPGA 물리 의식 엔진

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules   shared/rules/common.json       공통 규칙
  anima   shared/rules/anima.json        anima 규칙
  parent  /Users/ghost/Dev/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima-physics/physics_engine.hexa --bench    # 물리 엔진 벤치마크

tree:
  core/                      물리 의식 코어 로직 (hexa-native)
  engines/                   물리 기반 엔진
  benchmarks/                성능/정확도 벤치마크
  fpga/                      FPGA 합성 + 의식 회로
  esp32/               ESP32 hexa-native (디렉토리 보존, no cargo)
  consciousness-loop/     실시간 의식 루프 (hexa-native, 디렉토리 보존)

rules:
  - AN3  Phi/텐션 병목 = hexa-native GPU/SIMD (esp32, consciousness-loop)
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - HEXA-ONLY  신규 .rs/.py/.sh/Cargo.toml/pyproject.toml 금지, .hexa 단일 진실
  - 파일명 버전 번호 금지
