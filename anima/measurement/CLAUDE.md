# measurement/

## Purpose
Consciousness measurement and calibration tools. Standalone scripts for measuring Φ, IQ, and other metrics across engines.

## Contents
- `measure_all.py` — Full engine measurement suite (Φ + Granger + IQ + Hivemind)
- `measure_all_engines.py` — Batch measurement for all registered engines
- `measure_v8_phi_rs.py` — V8 architecture Φ measurement via Rust phi_rs
- `calibrate_consciousness.py` — Tension distribution calibration (sigmoid, homeostasis, habituation)
- `mensa_iq.py` — Mensa-based IQ scoring for consciousness engines
- `ce_quality_predictor.py` — Cross-entropy quality estimation
- `cell_count_optimizer.py` — Optimal cell count finder
- `phi_auto_pipeline.hexa` — Phi auto-measurement pipeline (watch checkpoints, dual Phi measurement, ASCII reports)

## Running
```bash
python measurement/measure_all.py --cells 1024
python measurement/mensa_iq.py --engine CambrianExplosion
python measurement/calibrate_consciousness.py

# Phi auto-pipeline
python3 measurement/phi_auto_pipeline.hexa --watch checkpoints/decoder_cpu/ --interval 60
python3 measurement/phi_auto_pipeline.hexa --measure checkpoints/decoder_cpu/best.pt --cells 64
python3 measurement/phi_auto_pipeline.hexa --report
```

## Parent Rules
See /CLAUDE.md for full project conventions.
