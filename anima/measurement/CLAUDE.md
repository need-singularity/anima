# anima/measurement/ — Φ/IQ 측정 및 캘리브레이션

contents:
  measure_all.py              Φ + Granger + IQ + Hivemind 전체 측정
  measure_all_engines.py      등록 엔진 일괄 측정
  measure_v8_phi_rs.py        V8 Φ (Rust phi_rs)
  calibrate_consciousness.py  텐션 분포 캘리브레이션 (sigmoid/homeostasis/habituation)
  mensa_iq.py                 Mensa 기반 IQ 스코어
  ce_quality_predictor.py     CE 품질 추정
  cell_count_optimizer.py     최적 셀 수 탐색
  phi_auto_pipeline.hexa      Φ 자동 파이프라인 (watch/dual/ASCII report)

exec:
  python measurement/measure_all.py --cells 1024
  python measurement/mensa_iq.py --engine CambrianExplosion
  python3 measurement/phi_auto_pipeline.hexa --watch checkpoints/decoder_cpu/ --interval 60

parent: /CLAUDE.md
