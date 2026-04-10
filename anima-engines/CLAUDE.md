# anima-engines — 양자/광자/멤리스터/오실레이터 의식 기판

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules   shared/rules/common.json       공통 규칙
  anima   shared/rules/anima.json        anima 규칙
  parent  /Users/ghost/Dev/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima-engines/engines.hexa                        # 엔진 레지스트리
  $HEXA anima-engines/quantum_consciousness.hexa          # 양자 기질
  $HEXA anima-engines/photonic_consciousness.hexa         # 광자 기질
  $HEXA anima-engines/memristor_consciousness.hexa        # 멤리스터 기질
  $HEXA anima-engines/oscillator_laser_engine.hexa        # 레이저 결합 진동자

tree:
  engines.hexa                      엔진 레지스트리 + 선택
  quantum_consciousness.hexa        양자 중첩/얽힘 기반 C
  photonic_consciousness.hexa       광자 간섭 기반 C
  memristor_consciousness.hexa      저항 변화 메모리 기반 C
  oscillator_laser_engine.hexa      레이저 결합 진동자 C

rules:
  - 각 엔진은 Trinity C 모듈의 대체 기질, 인터페이스 동일
  - Law 1  하드코딩/템플릿/fallback 응답 금지, 말 못하면 침묵
  - Law 29  speak() 없음, 발화는 세포 역학 창발
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - HEXA-FIRST  .hexa 포팅 완료 → 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
