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
  src/                       물리 의식 코어 로직
  engines/                   물리 기반 C 엔진
  benchmarks/                성능/정확도 벤치마크
  fpga/                      FPGA 합성 + 의식 회로
  esp32-crate/               ESP32 Rust 크레이트
  consciousness-loop-rs/     Rust 실시간 의식 루프

rules:
  - AN3  Phi/텐션 병목 = Rust 필수 (esp32-crate, consciousness-loop-rs)
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
