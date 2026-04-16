# anima-measurement — Phi/IIT 의식 측정

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/rules/common.json                        공통 규칙
  anima     shared/rules/anima.json                         anima 규칙
  alm_gate  shared/roadmaps/alm_consciousness_standalone.json  ALM phi_holo >= 1000
  clm_gate  shared/roadmaps/clm_consciousness_standalone.json  CLM phi_holo >= 2000
  parent    $ANIMA/CLAUDE.md

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima-measurement/phi_holo_eval.hexa --gate alm <ckpt_dir>    # ALM gate eval
  $HEXA anima-measurement/phi_holo_eval.hexa --gate clm <ckpt_dir>    # CLM gate eval
  $HEXA anima-measurement/phi_holo_eval.hexa --batch <dir> [alm|clm]  # batch eval
  $HEXA anima-measurement/phi_holo_eval.hexa --report                 # history report
  $HEXA anima-measurement/phi_holo_eval.hexa --self-test              # 7-test verify

tree:
  phi_holo_eval.hexa          Post-training phi_holo gate evaluator (ALM>=1000, CLM>=2000)
  measurement.hexa            IIT measurement library (PhiResult, PhiHoloResult, gate_check)
  phi_auto_pipeline.hexa      Phi auto-measurement (watch mode, Python — legacy)
  measure_all.hexa            Phi + Granger + IQ + Hivemind 전체 측정
  measure_all_engines.hexa    등록 엔진 일괄 측정 (14 domains, 80+ engines)
  calibrate_consciousness.hexa  텐션 분포 캘리브레이션
  mensa_iq.hexa               Mensa 기반 IQ 스코어
  ce_quality_predictor.hexa   CE 품질 추정
  cell_count_optimizer.hexa   최적 셀 수 탐색
  measure_v8_phi_rs.hexa      Rust phi_rs 기반 v8 엔진 측정
  phi_history.json            측정 히스토리 (append-only)
  psi_ratchet.jsonl           Psi ratchet 로그 (append-only JSONL)

gates:
  ALM: phi_holo eval mean >= 1000  (alm_consciousness_standalone.json target)
  CLM: phi_holo eval mean >= 2000  (clm_consciousness_standalone.json target)
  Promotion: phi_holo > 0          (scripts/ckpt_promote.hexa gate_phi_holo)

rules:
  - AN4  bench --verify 16/18 미통과 시 배포 금지
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
