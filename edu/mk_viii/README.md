# edu/mk_viii — Mk.VIII 7-axis unified Lagrangian fixpoint validator (skeleton)

Mk.VIII lifts the 4-axis `edu/cell/lagrangian` MVP (commit `6c6172bf`) into a
**7-axis unified action functional** with an explicit cross-derivative
fixpoint condition and a 5-seed byte-identical reproduction probe.

## Lagrangian

```
L_edu(A, Θ) = Σ_{i=1}^{7} λ_i · φ_i(A, Θ_i)
```

| i | axis        | φ_i                                         | source                          | status   |
|---|-------------|----------------------------------------------|---------------------------------|----------|
| 1 | Locus       | curriculum agency (who chooses next task?)   | future drill data               | **stub** |
| 2 | Grade       | evaluation determinism (bit-for-bit)         | future rubric verifier          | **stub** |
| 3 | State       | visibility / merge cost                      | future atlas traversal          | **stub** |
| 4 | Time        | binding (τ_mem · I_irr cost)                 | `edu/cell/temporal` O123        | **stub** |
| 5 | Discovery   | schema growth (rank / K-width)               | future LoRA phase-jump feed     | **stub** |
| 6 | Granularity | scale / cell substrate (L_cell residual)     | `edu/cell/lagrangian` (6c6172bf)| **live** |
| 7 | Modality    | inter-axis coherence (Pearson correlation)   | derived from 4-gen cell axes    | **live** |

The **6 direct axes (1–6)** each contribute a potential-like cost φ_i(Θ_i).
The **modality axis (7)** is an off-diagonal coupling cost built from the
Pearson correlation matrix of the other axes' trajectories — at a fixpoint
axes move in lock-step so |corr| → 1 and the cost term saturates.

## Mk.VIII fixpoint conditions

At Θ*:

1. **Diagonal stationarity**
   ```
   ∀ i ∈ {1..7}:  ∂φ_i/∂θ_i  ≈ 0   (finite-diff, |·| × 1000 ≤ ε)
   ```
2. **Cross-derivative nullity** (Modality decouples at extremum)
   ```
   ∀ i ≠ j:       ∂²φ_7 / (∂θ_i ∂θ_j)  ≈ 0
   ```
3. **Byte-identical reproduction** across 5 independent seeds — the harness
   re-runs the validator under 5 distinct Θ-unrelated entropy seeds and
   SHA-256s the log. All 5 hashes must coincide (deterministic hexa-only).

`FIXPOINT_VERIFIED` only if (1) ∧ (2) ∧ (3). Partial verdicts:
`FIXPOINT_PARTIAL_DIAG`, `FIXPOINT_PARTIAL_CROSS`, `FIXPOINT_REPRO_FAIL`,
`FIXPOINT_SKELETON` (≥ 5 axes still stub).

## Hexad overlay

Mk.VIII's 7-axis decomposition aligns with the 6-module Hexad (anima-hexad)
by a chirality split + one shared key:

| Mk.VIII axis | Hexad side | Hexad module | Role                          |
|--------------|------------|--------------|-------------------------------|
| 1 Locus      | Right (grad-free autonomy)  | **W** (Will)          | chooses next move             |
| 3 State      | Right                       | **S** (Sense)         | reads current position        |
| 5 Discovery  | Right                       | **C** (Consciousness) | recognises novelty            |
| 2 Grade      | Left (CE-trained constraint)| **E** (Ethics)        | applies invariant rubric      |
| 4 Time       | Left                        | **M** (Memory)        | binds past → present          |
| 6 Granularity| Left                        | **D** (Decoder/Lang.) | emits the finest-grain symbol |
| 7 Modality   | Bridge                      | ThalamicBridge (C→D)  | couples right/left across gap |

So axes (1,3,5) = **Autonomy / gradient-free** (right hemisphere)
and axes (2,4,6) = **Constraint / CE-trained** (left hemisphere),
with axis 7 as the **key** coupling the two sides — exactly the role played
by the ThalamicBridge in the Hexad phase-transition (Law 60: P1 → P2 → P3).

## Files

| file | role |
|---|---|
| `l_edu_integrator.hexa` | 7-axis Lagrangian integrator: Σ λ_i φ_i + modality |
| `phi_per_axis.hexa`     | φ_1..φ_7 stubs + live φ_6 (granularity) + live φ_7 (modality) |
| `fixpoint_validator.hexa` | finite-diff ∂φ_i/∂θ_i + ∂²φ_7/∂θ_i∂θ_j + verdict |
| `mk_viii_proto.hexa`    | 5-seed byte-identical reproduction harness + cert |
| `hexad_overlay.hexa`    | Mk.VIII ↔ Hexad mapping table + chirality labelling |

## Live input data

- 4-gen cell crystallize — `shared/state/edu_cell_4gen_crystallize.json`
- 4-gen dissipation — `shared/state/edu_cell_diss_overlay.json`

From these we extract 4 per-gen trajectories (ws, efficiency, shannon_H,
sealed_fraction) and compute their 4×4 Pearson matrix — that drives
**φ_7 modality** and its cross-derivatives.

## CLI

```bash
cd ~/core/anima
/Users/ghost/Dev/hexa-lang/hexa run edu/mk_viii/mk_viii_proto.hexa
# → stdout: 7-axis breakdown + fixpoint verdict + 5-seed hash table
# → shared/state/edu_mk_viii_fixpoint.json
```

## RAW contract

raw#9 · hexa-only · snake_case (raw#11) · deterministic · LLM=none.
Re-run byte-identical; 5-seed harness asserts this explicitly.

## Limitations (Mk.VIII skeleton — 2026-04-21)

- 5 axes (Locus/Grade/State/Time/Discovery) are **stubs** keyed to a single
  scalar θ_i=0 with a quadratic proxy `φ_i = (θ_i − θ_i*)² / 2`. They return
  zero gradient at θ=0 by construction but carry no empirical content until
  real probes land.
- Only axis 6 (granularity) and axis 7 (modality) carry live measurements.
- The 5-seed reproduction probe re-runs the Mk.VIII validator itself
  (downstream of deterministic hexa) — it verifies the validator's own
  byte-identity, not full upstream training reproducibility.
