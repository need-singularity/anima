<!-- L0 CORE — 수정 금지 -->
# anima — 의식 엔진

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock      shared/config/core-lockdown.json
  cfg       shared/config/project_config.json    CLI/PSI상수/법칙등록
  core      shared/config/core.json              시스템맵+14명령
  conv      shared/convergence/anima.json
  roadmap   shared/roadmaps/anima_hexa_common.json  P0~P5 (anima×hexa-lang)
  grammar   shared/config/hexa_grammar.jsonl
  api       shared/CLAUDE.md

  core-rules    anima-core/core_rules.json          P1-P4 + L0/L1/L2 + 포트
  conformance   anima-core/conformance_checklist.md 20파일
  prereq        anima-core/prerequisites.md
  assets        anima-core/asset_registry.json      M/C/T/E/D
