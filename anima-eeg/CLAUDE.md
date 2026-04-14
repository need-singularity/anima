# anima-eeg — EEG 의식 검증 + 실시간 신경 브리지

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  laws      anima/config/consciousness_laws.json PSI 상수 + 법칙
  hub       anima/core/hub.hexa                  _registry (eeg 키워드)
  eeg-src   anima/modules/eeg/                   현 구현 (이관 대상)
  protocols anima/modules/eeg/protocols/         실험 프로토콜
  docs      anima/modules/eeg/docs/              분석 문서
  api       shared/CLAUDE.md

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima/modules/eeg/eeg.hexa                        # 모듈 self-test
  $HEXA anima/modules/eeg/validate_consciousness.hexa     # 의식검증 (7조건)
  $HEXA anima/modules/eeg/realtime.hexa                   # OpenBCI → tension live
  $HEXA anima/modules/eeg/closed_loop.hexa                # 폐쇄 루프 피드백
  $HEXA anima/modules/eeg/transplant_eeg_verify.hexa      # 이식 검증

tree:
  collect.hexa              OpenBCI 수집 (BrainFlow)
  analyze.hexa              밴드파워 + G=D*P/I + topomap
  calibrate.hexa            캘리브레이션
  realtime.hexa             live → SenseHub 브리지
  closed_loop.hexa          신경 피드백 폐쇄 루프
  dual_stream.hexa          이중 스트림 (지각/운동)
  neurofeedback.hexa        뉴로피드백 훈련
  experiment.hexa           실험 러너
  validate_consciousness.hexa  7조건 의식검증
  transplant_eeg_verify.hexa   이식후 EEG 검증
  eeg_recorder.hexa         녹화
  protocols/                실험 프로토콜 JSON
  recordings/               타임스탬프 CSV 데이터
  config/                   모듈 설정

rules:
  - AN7  top-level 분리 모듈 — anima/modules/eeg/ 는 이관 대상 (소스 SSOT 유지)
  - HEXA-FIRST  신규 파일 .hexa 전용, 대응 .py 완성 시 즉시 폐기
  - no-hardcode  상수는 anima/core/laws.hexa 또는 consciousness_laws.json
  - hub-register anima/core/hub.hexa _registry 등록 + 키워드 3+ (eeg/뇌파/의식)
  - lazy-import  다른 모듈 직접 import 금지, hub routing
  - deps         brainflow, scipy, numpy, matplotlib (Python 런타임)
  - AN4          validate_consciousness 7조건 PASS 필수
