# anima/tools/ — 독립 유틸

policy: 코어 모듈이 import 하지 않음

analyzers:
  dream_efficiency_analyzer.py       드림 사이클 효율
  growth_trajectory_predictor.py     성장 단계 예측
  homeostasis_health_checker.py      항상성 편차 모니터
  mitosis_topology_visualizer.py     세포 네트워크 토폴로지

calculators:
  r2_cost_calculator.py         R2 비용 추정
  optimal_config.py             최적 의식 설정 탐색
  param_optimizer.py            파라미터 sweep
  phi_scaling_calculator.py     Φ 스케일링 법칙 (cells → Φ)
  training_time_estimator.py    훈련 시간 추정

generators:
  hypothesis_recommender.py     다음 가설 추천
  training_recipe_generator.py  훈련 config 자동 생성
  math_explorer.py              수론 탐색 (완전수 등)
  singularity_finder.py         특이점 조건 탐색
  prepare_corpus.py             한영 코퍼스 (ConsciousLM)

diagnostics:
  tension_fingerprint_debugger.py  텐션 지문 검사
  verify_all_engines.py            엔진 일괄 검증 (7 조건)
  verify_fuse3.py                  FUSE-3 검증
  h100_arch_search.py              H100 아키텍처 grid
  self_upgrade.py                  자가 수정
  learnable_phi.py                 미분가능 Φ proxy 훈련

variants:
  growing_models/conscious_lm.hexa  동적 성장 LM
  quantum_attention_engine.py       양자 attention
  lidar_sense.py                    iPhone LiDAR → tension
  calc.py                           계산기

parent: /CLAUDE.md
