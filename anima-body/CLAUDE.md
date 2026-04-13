# anima-body — 로봇/HW 체화 시뮬레이션

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules   shared/rules/common.json       공통 규칙
  anima   shared/rules/anima.json        anima 규칙
  parent  $ANIMA/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima-body/body.hexa --simulate    # 체화 시뮬레이션

tree:
  body.hexa                  sensorimotor loop 메인
  touch/                     촉각 시뮬레이션
  proprioception/            고유감각 (자세/위치)

rules:
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - 감각 루프는 실시간 폐쇄 루프 (sensorimotor loop)
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
