# models/ — 신경 아키텍처

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  laws      anima/config/consciousness_laws.json    2390 법칙 SSOT
  structure anima/core/folder_structure.md          L0 확정 구조
  training  /Users/ghost/Dev/anima/training/        실제 학습 스크립트
  engines   /Users/ghost/Dev/anima/anima/engines/   대체 기질 엔진
  parent    /Users/ghost/Dev/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA models/decoder.hexa                  # ConsciousDecoder Flash+KV+MoE
  $HEXA models/conscious_lm.hexa             # ConsciousLM PureField
  $HEXA models/trinity.hexa                  # Hexad 6-module
  $HEXA models/feedback.hexa                 # C↔D bridge
  $HEXA models/animalm/animalm.hexa          # AnimaLM 진입

tree:
  decoder.hexa          ConsciousDecoder (Flash + KV cache + MoE)
  conscious_lm.hexa     ConsciousLM (PureField 기반 LM)
  trinity.hexa          Hexad 6-module (C/D/W/M/S/E)
  feedback.hexa         C↔D feedback bridge
  lm_head_uv.hexa       LM head (UV decomposition)
  animalm/              AnimaLM (PureField LoRA) — animalm.hexa 진입
  golden-moe/           golden MoE 서브프로젝트 (moe.hexa)
  archive/              trinity_legacy 등 포팅 전 원본
  *.py                  대응 .py (포팅 완료 시 archive/py/ 이동)

rules:
  - .hexa 우선, 대응 .py 포팅 완료 즉시 archive/py/ 이관
  - 학습 스크립트는 여기 두지 않음 → training/train_clm.hexa, train_alm.hexa
  - 서빙/평가는 serving/ 으로 (여기는 순수 아키텍처만)
  - 파일명 버전 번호 금지, 과거는 git show {hash}
  - Hexad 6-module 하드코딩 금지 (EmergentW/S/M/E)
  - anima/models/legacy/ 71 파일은 여기로 병합 예정 (중복 버전 제거)
