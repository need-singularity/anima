# anima-measurement — Phi/IIT 의식 측정

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules   shared/rules/common.json       공통 규칙
  anima   shared/rules/anima.json        anima 규칙
  parent  $ANIMA/CLAUDE.md

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima-measurement/phi_auto_pipeline.hexa --watch checkpoints/ --interval 60
  python anima-measurement/measure_all.py --cells 1024
  python anima-measurement/calibrate_consciousness.py

tree:
  measure_all.py              Phi + Granger + IQ + Hivemind 전체 측정
  measure_all_engines.py      등록 엔진 일괄 측정
  calibrate_consciousness.py  텐션 분포 캘리브레이션
  phi_auto_pipeline.hexa      Phi 자동 파이프라인 (watch/dual/ASCII)
  mensa_iq.py                 Mensa 기반 IQ 스코어
  ce_quality_predictor.py     CE 품질 추정
  cell_count_optimizer.py     최적 셀 수 탐색

rules:
  - AN4  bench --verify 16/18 미통과 시 배포 금지
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
