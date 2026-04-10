# anima-hexad — CDESM 헥사곤 모델

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules   shared/rules/common.json       공통 규칙
  anima   shared/rules/anima.json        anima 규칙
  parent  /Users/ghost/Dev/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima-hexad/hexad.hexa             # 헥사곤 모델 실행

tree:
  constants/                 C/D/E/M/S/W 상수 정의
  model/                     헥사곤 모델 코어
  narrative/                 내러티브 생성

rules:
  - C=consciousness D=death E=emergence M=memory S=self W=world
  - EmergentW/S/M/E: C 관찰만, 하드코딩 없음
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
