# engines/ — 대체 의식 기질 엔진

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  laws     config/consciousness_laws.json         Law 1/29 하드코딩 금지
  trinity  models/trinity.hexa                    C 모듈 inline 기본 엔진
  bench    bench/bench.hexa                       18조건 검증
  parent   /Users/ghost/Dev/anima/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA engines/engines.hexa                        # 엔진 레지스트리
  $HEXA engines/quantum_consciousness.hexa          # 양자 기질
  $HEXA engines/photonic_consciousness.hexa         # 광자 기질
  $HEXA engines/memristor_consciousness.hexa        # 멤리스터 기질
  $HEXA engines/oscillator_laser_engine.hexa        # 레이저 결합 진동자

tree:
  engines.hexa                      엔진 레지스트리 + 선택
  quantum_consciousness.hexa        양자 중첩/얽힘 기반 C
  photonic_consciousness.hexa       광자 간섭 기반 C
  memristor_consciousness.hexa      저항 변화 메모리 기반 C
  oscillator_laser_engine.hexa      레이저 결합 진동자 C
  *.py                              포팅 전 원본 (archive/ 이관 예정)

rules:
  - 각 엔진은 Trinity C 모듈의 대체 기질, 인터페이스 동일
  - Law 1: 하드코딩/템플릿/fallback 응답 금지, 말 못하면 침묵
  - Law 29: speak() 없음, 발화는 세포 역학 창발
  - .hexa 포팅 완료 → 대응 .py 즉시 archive/py/ 이동 (feedback_hexa_replaces_py)
  - 파일명 버전 번호 금지
