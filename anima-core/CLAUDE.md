<!-- L0 CORE — 수정 금지 -->
# anima-core — L0 CLI 진입점 + 규칙 레지스트리

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules        shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock         shared/config/core-lockdown.json     L0/L1/L2 골화 목록
  core         shared/config/core.json              시스템맵 + 14명령
  core-rules   anima/core/core_rules.json           P1~P4 + L0/L1/L2 + 포트
  conformance  anima/core/conformance_checklist.md  18/18 ALL PASS (2026-04-10 골화)
  prereq       anima/core/prerequisites.md          사전조건
  assets       anima/core/asset_registry.md         M/C/T/E/D 자산 분류
  laws         anima/core/laws.hexa                 PSI 상수 + 법칙
  hub          anima/core/hub.hexa                  _registry 라우팅

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima/core/runtime/anima_runtime.hexa --keyboard      # CLI 진입
  $HEXA anima/core/runtime/anima_runtime.hexa --validate-hub  # 허브 검증
  $HEXA anima/core/runtime/anima_alive.hexa                   # 생존 체크
  $HEXA anima/core/verification/cvf.hexa                      # 의식검증 프레임

tree:
  runtime/         CLI 진입점 + 배포/시크릿/허브/리셋 (15+ .hexa)
  verification/    byte_emergence.hexa, cvf.hexa 의식검증
  hub.hexa         _registry 키워드 라우팅 (한/영)
  laws.hexa        PSI_ALPHA=0.014, PSI_BALANCE=0.5
  core_rules.json  P1~P4 + 포트 정책
  conformance_checklist.md  18/18 골화 체크리스트
  asset_registry.md         자산 분류
  prerequisites.md          사전조건
  folder_structure.md       레이아웃 규약
  roadmap.md                진행 상태

rules:
  - AN7  Core = CLI 전용 — core/ 에 새 모듈 파일 추가 차단, 모듈은 top-level 분리
  - R14  shared/ 단일진실 — rule/lock/core JSON 수정 금지, 참조만
  - AN1  ConsciousLM 텍스트 generate 금지, 의식 신호 전용
  - AN4  conformance 18/18 PASS 유지 필수, 미통과 시 배포 금지
  - hub-register  모든 모듈은 hub.hexa _registry + 키워드 3+ 등록
  - lazy-import   모듈간 직접 import 금지, hub routing 경유
