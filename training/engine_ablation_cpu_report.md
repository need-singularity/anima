# Engine Ablation CPU Precompute Report (D2)

**Date:** 2026-04-18 · 71-engine LOO CPU smoke (GPU booked by r10)
**Source:** `training/ablation_emit_json.hexa` → `shared/state/engine_ablation_cpu_precompute.json`
**Thresholds:** KEEP `|CE|≥1e-3 ∧ |φ|≥5e-4` · DROP `|CE|<1e-4 ∧ |φ|<1e-5` · REVIEW else
**Score:** `|CE_Δ|·1000 + |φ_Δ|·10000` · Harness `ALL 5/5 PASS`.

## Distribution
KEEP 33 (46.5%) · REVIEW 19 (26.8%) · DROP 19 (26.8%)

## Top-10 KEEP
1 temporal 4803 (CE 0.207/φ 0.460) · 2 anima_temporal 4711 · 3 creative 1766 · 4 creative_engine · 5 insight_trigger · 6 creativity_phi · 7 insight_aha_phi (φ≈0.176 variance-target) · 8 photonic_consciousness 1747 · 9 photonic_network · 10 edge_of_chaos.

## Bottom-10 DROP
gossip_protocol, extended_mind_bridge, collective_phi_bridge, hive_state_sync; fractal_memristor, memristor_consciousness, memristor_longterm, memory_palace_phi, memory_consolidation, episodic_store (all score <1.3e-30).
Whole **memory 7/7**, **collective 4/4**, **global-workspace 4/4**, **other-model 4/4** collapse — half-split surrogate returns 0 on symmetric mock h. Cannot DROP blindly: mock artifact, not model signal.

## Reproducibility
Every row derives from `engine_ablation.hexa` 9 surrogate shapes (VAR, MEAN², ADIFF, HALFSPLIT, QMATCH, LAG1, SIGNFLIP, LOWFREQ, VAR-TARGET) via family-dispatch. Mock: h_last[64]=`0.1i−3.2+0.05·((7i)mod13)`, q[16]=`0.02j−0.16`.

## Next
H100 live LOO (`ablation_batch_manifest.json`, 71×100 steps) once r10 releases pod. Trained h_last breaks halfsplit symmetry → expect DROP-by-mock families to regain signal. Hold any catalog deletions until live run confirms.
