# anima-tools — 독립 유틸리티 (코어가 import 안 함)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules   shared/rules/common.json       공통 규칙
  anima   shared/rules/anima.json        anima 규칙
  parent  /Users/ghost/Dev/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  # 개별 도구 직접 실행

tree:
  analyzers/                 드림/성장/항상성/토폴로지 분석
  calculators/               R2비용/Φ스케일링/파라미터 최적화
  generators/                가설추천/config생성/코퍼스준비
  diagnostics/               텐션디버거/엔진검증/자가수정
  discovery-engine/          자율 발견 엔진
  formula-miner/             수식 채굴기
  hexa-bridge/               .py↔.hexa 브릿지

rules:
  - AN7  Core 분리 — 코어가 import 하지 않음, 독립 실행만
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
