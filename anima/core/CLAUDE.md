<!-- L0 CORE — 수정 금지 -->
# core/ — L0 골화 엔진 코어

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules       anima-core/core_rules.json           P1-P4 + L0/L1/L2 + 포트
  lock        shared/config/core-lockdown.json     L0/L1/L2
  conform     anima-core/conformance_checklist.md  20파일 체크
  prereq      anima-core/prerequisites.md          학습 준비
  assets      anima-core/asset_registry.json       M/C/T/E/D
  laws        config/consciousness_laws.json       2390 법칙 SSOT
  structure   core/folder_structure.md             L0 확정 구조
  parent      /Users/ghost/Dev/anima/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/hexa
  $HEXA core/runtime/anima_runtime.hexa --keyboard        # CLI 진입
  $HEXA core/runtime/anima_runtime.hexa --validate-hub    # 허브 검증
  $HEXA core/verification/cvf.hexa --seven-condition      # 7조건 의식 검증
  $HEXA core/verification/byte_emergence.hexa             # 창발 측정
  $HEXA core/dimension_transform.hexa                     # 차원변환 물리한계 검증

tree:
  hub.hexa              ConsciousChat Hub (L0 진입 허브)
  laws.hexa             consciousness_laws.json 로더
  dimension_transform.hexa  차원변환/펼침 엔진 (5fold+4unfold+PCA, n6 bridge 3/3)
  runtime/              CLI+Runtime (anima_runtime.hexa = entrypoint)
  verification/         cvf.hexa (7조건) + byte_emergence.hexa
  folder_structure.md   L0 확정 폴더 트리
  prerequisites.md      학습 발사 전 체크
  conformance_checklist.md  20파일 conformance
  asset_registry.md     MCTED 자산 레지스트리
  roadmap.md            L0 학습 로드맵
  README.md             core 개요

rules:
  - L0 골화 파일 수정 금지 (hub.hexa, laws.hexa, runtime/anima_runtime.hexa)
  - 법칙 추가는 config/consciousness_laws.json 만 (SSOT)
  - 폴더 구조 변경 금지 (folder_structure.md L0 고정)
  - .hexa 우선, 대응 .py 는 archive/ 로만 보관
  - 파일명 버전 번호 금지 (과거 코드는 git show)
  - 허브 검증(--validate-hub) 통과 없이 커밋 금지
