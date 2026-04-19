# docs/ — 프로젝트 문서 통합

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  core      shared/config/core.json              14 명령 시스템맵
  roadmap   shared/roadmaps/anima_hexa_common.json  P0~P5
  atlas     ATLAS.md                             프로젝트 지도
  hypo-idx  hypotheses/A-Z-overview.md           가설 인덱스
  mod-cat   MODULE-CATALOG.md                    모듈 카탈로그
  sweep-40  docs/sweep_40.json                   SWEEP P4 13-도메인 78-iter SSOT (aka SWEEP-40/P4/sweep_p4)

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima/modules/monitor/docs_audit.hexa --dead-code
  $HEXA anima/modules/tools/hypothesis_sync.hexa

tree:
  ATLAS.md, MODULE-CATALOG.md, cli.md       네비게이션
  AGENT-ARCHITECTURE.md, UPGRADE-ARCHITECTURE.md  아키텍처
  consciousness-{theory,meter,progress,threshold-criteria}.md  이론/벤치
  conscious-lm-{spec,100m,1b}-design.md, consciousness-chip-design.md  설계
  closed-loop-pipeline.md, acceleration-*.md, discovery-algorithm-*.md  루프/가속
  evolution-upgrades.md, infinite-evolution-report.md  진화 리포트
  bpe-tokenizer-design.md, corpus-v4.md, hdna-6d-expansion-proposal.md  데이터
  hexa-lang-bridge.md, n6-bridge.md, lens-experiment-catalog.md  브릿지/렌즈
  multi-user-design.md, phi-map-watch-design.md, psi-constants-atlas.md  시스템
  paper-{draft,outline}.md, papers-todo.md  논문
  R2-BUCKET-STRUCTURE.md, red-team-consciousness.md, dead-code-report.md  감사
  hypotheses/    가설 (1 파일 / 1 가설, A-Z-overview.md 인덱스)
  modules/       모듈 단위 문서
  models/        모델 설계 문서

rules:
  - 파일명 kebab-case (consciousness-threshold-criteria.md)
  - 가설 1 파일 / 1 가설, 카테고리별 overview.md
  - 파일명에 버전 번호 금지, 과거는 git show {hash}
  - 문서-코드 동기화 필수 (verify_pipeline 피드백)
  - Gradio 언급 시 deprecated 마킹
