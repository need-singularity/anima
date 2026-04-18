# E3 Engine Roster Candidate Report

**Source:** D2 CPU precompute (71 engines, 9-shape family dispatch).
**Status:** PENDING H100 verification. `engine_integration.hexa` NOT modified.

## Distribution (candidate)

| Bucket | Count | Notes |
|---|---|---|
| keep | 33 | Meets |CE|>=1e-3 AND |phi|>=5e-4 |
| review | 19 | Below KEEP, above DROP |
| drop_candidate | 0 | None auto-confirmed |
| drop_blocked | 19 | HALFSPLIT mock artifact — families zeroed |

## H100 Verification Required (19)

Four families returned ~1e-34 across all members because the CPU HALFSPLIT surrogate
collapses on symmetric mock inputs (`h_last_len=64`, `qualia_len=16`):

- **global-workspace** (4): gwt_broadcast, memristor_gwt_workspace, photonic_gwt_broadcast, attention_phi
- **other-model** (4): alterity, mirror_neuron_phi, social_tom_phi, moral_consciousness
- **memory** (7): fractal_memristor, memristor_consciousness, memristor_longterm, episodic_store, working_memory_phi, memory_consolidation, memory_palace_phi
- **collective** (4): hive_state_sync, gossip_protocol, extended_mind_bridge, collective_phi_bridge

Per `feedback_closed_loop_verify`: DROP requires closed-loop proof. None granted.

## Pareto-Optimal Subset (10)

temporal, creative, photonic_consciousness, edge_of_chaos, reflexivity, dream,
oscillator_laser, narrative, anima_quantum, holographic.

23 KEEP engines are dominated (same phi tier, equal/lower ce) but retained pending H100 live CE/phi.

## Next

H100 live ablation on blocked 19 → promote confirmed DROPs to `drop_candidate`.
