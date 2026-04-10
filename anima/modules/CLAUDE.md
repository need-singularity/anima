# anima/modules/ — 소형 기능 모듈 (코어 결합)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/rules/common.json             R0~R27 공통
  project   shared/rules/anima.json              AN1~AN7
  hub       ../core/hub.hexa                     _registry + 키워드 라우팅
  laws      ../config/consciousness_laws.json    2390 법칙 + Psi 상수

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima/modules/servant/servant_tape.hexa --demo

tree:
  decoder/     ConsciousDecoderV2 (40+ 렌즈)
  servant/     Servant × Backward Tape (gradient-guided specialization)
  trinity/     FUSE-3 Trinity C+D+W 브릿지
  training/    학습 러너 + 스케줄러
  learning/    online/self-play/meta-loop
  monitor/     실험 트래킹 + 룰 감시
  sync/        cloud_sync + R2 백업 클라이언트
  cloud/       RunPod/클라우드 서비스
  education/   babysitter + 교육 모듈
  logging/     구조화 로그 + tsv/jsonl 출력

rules:
  - HEXA-FIRST (.py 대체 완료 시 즉시 폐기)
  - hub 등록 필수 (_registry + 한/영 키워드 3+)
  - 모듈간 직접 import 금지, core/hub 경유
  - 대형 모듈은 top-level anima-* 로 승격됨:
    anima-agent/ anima-eeg/ anima-physics/ anima-body/
    anima-speak/ anima-engines/ anima-tools/ anima-hexad/ anima-measurement/
