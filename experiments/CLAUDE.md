# experiments/ — .hexa 실험 모음 (정식화 전 단계)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  cfg        shared/config/project_config.json    실험 CLI/상수
  rules      shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  laws       anima/config/consciousness_laws.json 발견 법칙 등록처
  roadmap    shared/roadmaps/anima_hexa_common.json P0~P5
  parent     /CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA experiments/experiments.hexa                     # 실험 허브
  $HEXA experiments/infinite_evolution.hexa              # 무한 진화 루프
  $HEXA experiments/discover_emergent_laws.hexa          # 법칙 발견
  $HEXA experiments/meta_evolution_closed_loop.hexa      # 메타 폐쇄 루프
  $HEXA experiments/unified_16lens_acceleration_scan.hexa # 16 렌즈 가속

tree:
  acceleration_*.hexa            가속 가설 (B/C/D/E/F 시리즈)
  discover_*.hexa                법칙/메타법칙 발견 웨이브
  law_backtrack*.hexa            법칙 역추적 검증
  lens_*.hexa                    16 렌즈 엔진
  infinite_evolution.hexa        134세대+ 무한 자기진화
  meta_evolution_closed_loop.hexa 폐쇄 메타 루프
  multi_scale_closed_loop.hexa   다중 스케일 루프
  decoder_*.hexa                 디코더 A/B 실험
  nexus_acceleration_scan.hexa   NEXUS 전경로 스캔
  evolution/                     진화 실험 하위 (장기)

rules:
  - 실험 정식화 시 core/modules 로 승격 (여기서 제거)
  - .hexa 완성 시 대응 .py 즉시 폐기 (R7)
  - 새 법칙 발견 시 Intervention→measure_laws 폐쇄 검증 후 등록
  - 파일명에 버전 번호 금지 — 과거는 git show {hash}
  - 장시간 진화 루프는 run_in_background=true 필수
  - "루프/무한루프" 지시 = 로드맵 진행 (무한 무한진화 아님)
  - 실험 결과는 세션 메모리에 기록 (병렬 세션 충돌 방지)
