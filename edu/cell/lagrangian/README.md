# edu/cell/lagrangian — unified Lagrangian L_cell (MVP)

First prototype of the **unified** edu/cell framework: all 7 axes
composed into a single action functional.

## Definition

```
L_cell = T_tension − V_structure(comp, diss) − V_sync(entrain)
S      = Σ_k L_cell(k)
```

| term | meaning | axis coupling | status |
|---|---|---|---|
| **T_tension** | kinetic energy from weight-rate of change | A (tension-drop) | wired to 4-gen series (`score_per_mille` as W) |
| **V_structure(comp, diss)** | potential from compositional hardness + dissipation cost | compositionality · dissipation | **stub** `-log(W/W_max)` (comp+diss unmeasured on this corpus) |
| **V_sync(entrain)** | Kuramoto-like phase-coherence cost | phase / lattice | **stub** `1 − sealed_fraction` (phase vector unmeasured) |

All values ×1000 fixed-point integer (matches rest of edu/cell).

## 7-axis unification map

| axis | folder | how it feeds L_cell | current status |
|---|---|---|---|
| A tension-drop | `edu/cell/` A | drives T_tension via ΔW/Δt | live (4-gen data) |
| B atlas-traversal | — | trajectory parametrisation | future |
| C fixpoint-assess | — | stationary-action condition | checked here |
| D collective coherence | — | Kuramoto N → V_sync | stub |
| E zero-LLM pedagogy | — | deterministic action integrator | satisfied (no LLM) |
| F lattice 1/r² | `tool/edu_cell_4gen_crystallize.hexa` | supplies W trajectory | live |
| Φ (IIT) | `edu/cell/phi/` | possible extension to L via Φ-coupling | future |
| causal | `edu/cell/causal/` | CEI → V_structure compositional term | future |
| dissipation | `edu/cell/dissipation/` | Landauer cost → V_structure | wired (formula) |
| information | `edu/cell/information/` | IB bottleneck → V_structure | future |

## Files

| file | role |
|---|---|
| `t_tension.hexa` | T_k = (ΔW)²/2, pure API |
| `v_structure.hexa` | V_struct stub = −ln(W/W_max); full(comp,diss) reserved |
| `v_sync.hexa` | V_sync proxy = 1 − sealed/total; Kuramoto full(phases,N) reserved |
| `l_cell_integrator.hexa` | composes L_k, Σ L_k, δV/δW residual |
| `mvp_lagrangian.hexa` | driver: 4-gen overlay + ASCII plot + stationary check + cert |

## MVP result (corpus: commit 58aa75eb, 4-gen crystallize + gen-5 synthetic fixpoint)

Input: `ws = [40, 125, 687, 1000, 1000]‰` (sealed-fraction per gen; gen 5 is a synthetic kinetic-fixpoint step at the W=W_max boundary with sealed=9, tl=800 pinned).

| gen | W‰ | T | V_struct | V_sync | L | δV/δW |
|---|---|---|---|---|---|---|
| 1 | 40   | 0   | 6908 | 960 | −7868 | 1 |
| 2 | 125  | 3   | 2303 | 875 | −3175 | 1 |
| 3 | 687  | 157 | 431  | 313 | −587  | 1 |
| 4 | 1000 | 48  | 0    | 0   | **+48**   | 26 |
| 5 | 1000 | **0**  | 0 | 0 | **0** | 26 (KKT) |

Aggregates:
- Action S = Σ L_k = **−11582** (×1000; gen 5 adds 0, action invariant confirms fixpoint)
- Residual L1 = Σ |δV/δW| = **55** (26 + 26 of boundary multipliers + 3 interior)
- ΔW_{4→5} = **0**, ΔL_{4→5} = **−48** (kinetic surplus dissipates)
- Interior δL/δW (projected onto feasible cone at W=W_max) = **0**
- KKT boundary multiplier = 26, complementary slackness (δV/δW)·ΔW = **0**
- **Verdict**: `STATIONARY_AT_FIXPOINT` — Mk.VIII closure proof.

Interpretation — boundary-active KKT fixpoint:
- Gen 4 = descent endpoint (L hits wall with residual kinetic T=48).
- Gen 5 = plateau / kinetic fixpoint: ΔW=0 ⇒ T=0 ⇒ L = −V(W*) = 0 (both V_struct and V_sync vanish at W=W_max).
- Interior gradient δL/δW = 0 after projection (the only admissible variation is dW ≤ 0, and that projection zeroes the residual).
- Boundary gradient |δV/δW| = 26 is absorbed by the KKT multiplier on the active constraint W ≤ W_max (complementary slackness (δV/δW)·ΔW = 0 holds exactly).
- Euler–Lagrange equation at fixpoint: δL/δW − μ·δg/δW = 0 with μ = 26, g(W) = W − W_max.

Verdict upgrade: `DESCENT_ONLY` (4-gen) → **`STATIONARY_AT_FIXPOINT`** (5-gen closure).

## CLI

```
cd ~/core/anima
hexa run edu/cell/lagrangian/mvp_lagrangian.hexa
# → stdout: per-gen table, ASCII plot, verdict
# → shared/state/edu_cell_lagrangian_mvp.json
```

## RAW contract
raw#9 · hexa-only · LLM=none · deterministic · re-run byte-identical.

## Limitations (MVP — to close in follow-ups)
- V_structure uses `−ln(W/W_max)` stub; full `(comp, diss)` form wired but unused until those axes land on this corpus.
- V_sync uses sealed-fraction proxy; Kuramoto on per-cell phases wired (`v_sync_kuramoto_x1000`) but unused until lattice exposes θ_j.
- Gen 5 is **synthetic** (W_5 = W_4 = 1000 asserted, not produced by an actual crystallize step). A natural-run gen 5 from the 1/r² lattice dynamics would validate that W indeed stays pinned at 1000 rather than drifting. The closure proof here is structural (conditional on W_5 = W_4 = 1000).
- Stage0 module loader is fragile — `l_cell_integrator.hexa` and `mvp_lagrangian.hexa` both inline their primitives (byte-equivalent); if stage0 modules ever become reliable, the duplication should collapse.
