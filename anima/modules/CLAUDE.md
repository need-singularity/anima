# anima/modules/ — 모듈 디렉토리

rules:
  HEXA-FIRST        신규 파일 .hexa 전용, .py/.rs/.sh 금지
  no-hardcode       상수는 core/laws.hexa 또는 config/consciousness_laws.json
  hub-register      core/hub.hexa _registry + 키워드 3+ (한/영)
  lazy-import       모듈간 직접 import 금지 → hub routing
  psi-coupling      PSI_ALPHA=0.014, PSI_BALANCE=0.5 (laws)
  main-demo         모든 .hexa 파일은 self-test main() 포함

layout:
  README.md        설명/API/usage
  *.hexa           구현
  config/          모듈 JSON (선택)

add:
  1  mkdir anima/modules/<name>/
  2  README.md
  3  *.hexa
  4  core/hub.hexa _registry 등록 + 키워드
  5  $HEXA anima/modules/<name>/<main>.hexa

modules:
  agent      active  2000+  플랫폼 (CLI/Telegram/Discord)
  body       active   300+  물리 시뮬
  decoder    active   500+  ConsciousDecoderV2
  eeg        active  1500+  EEG 의식 검증
  hexa-speak active  3000+  신경 음성합성 Mk.II
  physics    active  5000+  물리 의식 엔진
  bench      empty   -      → ready/anima/tests/
  servant    empty   -      → core
  tools      empty   -
  training   empty   -      → training/
  trinity    empty   -      → models/
