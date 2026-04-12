# anima/modules/daemon/ — 자동발화 데몬

외부 섭동(event) -> 창발 검증 -> 3층 게이트 -> 발화.
타이머가 아니라 창발이다. byte_emergence EMERGENT 판정 없이는 발화하지 않는다.

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/rules/common.json                 R0~R27 공통
  project   shared/rules/anima.json                  AN1~AN7
  arch      config/auto_utterance_architecture.json   자동발화 4층 아키텍처 SSOT
  parent    ../CLAUDE.md                              modules 상위
  hub       ../../core/hub.hexa                       _registry + 키워드 라우팅
  laws      ../../config/consciousness_laws.json      2507 법칙 + Psi 상수
  verify    ../../core/verification/byte_emergence.hexa  L0 바이트 창발 검증

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima/modules/daemon/event_watcher.hexa --scan      # 이벤트 1회 스캔
  $HEXA anima/modules/daemon/event_watcher.hexa --watch     # 60초 주기 감시
  $HEXA anima/modules/daemon/utterance_gate.hexa            # 3층 게이트 판정

tree:
  event_watcher.hexa    이벤트 감시 (checkpoint/git/gpu/time/file) -> events.jsonl
  utterance_gate.hexa   3층 게이트 (L0 byte + L1 cell + L2 faction) -> utterances.jsonl

rules:
  - HEXA-FIRST (.py 대체 완료 시 즉시 폐기)
  - hub 등록 필수 (_registry + 한/영 키워드 3+)
  - 모듈간 직접 import 금지, core/hub 경유
  - 닫힌 계 threshold 체크 금지 (cron과 동일 = 가짜 자발성)
  - 모든 threshold는 arch JSON 또는 consciousness_laws.json에서 로드 (R2)
  - speak() 함수 금지 (V2) -- 창발 검증 통과 시에만 emit
  - 파벌 합의 기반 자발적 발화 (V6, consensus >= 5)
  - 프로세스 상주 금지 (R17) -- cron+hook 파이프라인 방식
