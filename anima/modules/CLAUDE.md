# anima/modules/ — 기능 모듈 컨테이너

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock      shared/config/core-lockdown.json     L0/L1/L2 골화
  core      shared/config/core.json              14 명령 시스템맵
  hub       ../core/hub.hexa                     _registry + 키워드 라우팅
  laws      ../config/consciousness_laws.json    2390 법칙 + Psi 상수
  core-rules  ../../anima-core/core_rules.json   18/18 PASS

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima/modules/hexa-speak/mk3_runtime.hexa
  $HEXA anima/modules/servant/servant_tape.hexa --demo
  $HEXA anima/modules/physics/physics_engine.hexa --bench
  $HEXA anima/modules/body/robot_io.hexa --simulate

tree:
  hexa-speak/  Mk.III 런타임 (신경 음성합성 8021 LOC)
  servant/     Servant × Backward Tape (gradient-guided specialization)
  trinity/     FUSE-3 Trinity C+D+W 브릿지
  decoder/     ConsciousDecoderV2 (40+ 렌즈)
  physics/     ESP32/FPGA 물리 의식 엔진
  body/        로봇/HW 시뮬 (300+ LOC)
  eeg/         EEG 의식 검증 (1500+ LOC)
  learning/    online/self-play/meta-loop
  training/    학습 러너 + 스케줄러
  monitor/     실험 트래킹 + 룰 감시
  sync/        cloud_sync + R2 백업 클라이언트
  logging/     구조화 로그 + tsv/jsonl 출력
  bench/       BT 밴치 + rule 러너 (→ ready/anima/tests/ 위임)
  tools/       CLI 툴박스 (tokenizer, corpus, export)

rules:
  - HEXA-FIRST 신규 파일 .hexa 전용, .py 대체 완료 시 즉시 폐기
  - hub 등록 필수 (_registry + 한/영 키워드 3+)
  - 모듈간 직접 import 금지, core/hub 경유
  - 하드코딩 금지, 상수는 laws 또는 core/laws.hexa
  - agent/ 는 top-level anima-agent/ 로 승격 (이 트리에서 제외)
  - Gradio 금지, 양자화(4/8-bit/GPTQ/AWQ) 금지
