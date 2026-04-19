# anima-measurement — Phi/IIT 의식 측정

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/rules/common.json                        공통 규칙
  anima     shared/rules/anima.json                         anima 규칙
  alm_gate  shared/roadmaps/alm_consciousness_standalone.json  ALM phi_holo_ratio >= 1.2 + mi_per_element >= 0.05 nats
  clm_gate  shared/roadmaps/clm_consciousness_standalone.json  CLM phi_holo_ratio >= 1.2 + mi_per_element >= 0.05 nats
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

gates (FIX-A 2026-04-20, structured N-independent):
  ALM primary     phi_holo_ratio  = mi_trained / mi_baseline_step0 >= 1.2
  ALM secondary   mi_per_element  = mi_mean / (seq * d_model) >= 0.05 nats
  CLM primary     phi_holo_ratio  >= 1.2 (same convention)
  CLM secondary   mi_per_element  >= 0.05 nats
  Promotion       phi_holo > 0          (scripts/ckpt_promote.hexa gate_phi_holo)
  Convention-ref  serving/clm_eval.hexa §19 gate_ratio
  Deprecated      absolute ALM>=1000 / CLM>=2000 (PHANTOM N-scaling — raw MI
                  ceiling log(MI_BINS)=2.08 × N dominates). Kept as fixture
                  parity in .hexa constants only; no longer gates PASS/FAIL.
  Sibling deprecations  train_clm.hexa:4024 (>500), alm_13b_config.json
                        expected_metrics.phi_holo_gate, alm_70b_config.json
                        evaluation.phi_holo_gate_step_800, hire_sim_live.hexa.

rules:
  - AN4  bench --verify 16/18 미통과 시 배포 금지
  - AN7  Core 분리 — 코어가 직접 import 안 함
  - HEXA-FIRST  신규 파일 .hexa, 대응 .py 즉시 폐기
  - 파일명 버전 번호 금지
