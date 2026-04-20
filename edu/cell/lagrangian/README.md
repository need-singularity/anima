# edu/cell/lagrangian — unified Lagrangian L_cell (Mk.VIII) + L_IX (Mk.IX)

First prototype of the **unified** edu/cell framework: all 7 axes
composed into a single action functional.  Mk.IX (2026-04-21, raw#30)
extends the action with an embedded irreversibility term and pluggable
Kuramoto V_sync / RG V_potential modules.

## Mk.VIII — L_cell

```
L_cell = T_tension − V_structure(comp, diss) − V_sync(entrain)
S      = Σ_k L_cell(k)
```

## Mk.IX — L_IX (raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN)

```
L_IX  =  T_tension − V_structure − V_sync_eff − V_RG_eff  +  λ · I_irr
S_IX  =  Σ_k L_IX(k)
```

Backwards-compatibility: `HEXA_USE_KURAMOTO_SYNC=0 ∧ HEXA_USE_RG_POTENTIAL=0 ∧ λ=0` ⇒ L_IX ≡ L_cell byte-exact on the gen-5 KKT fixture (action = −11582, STATIONARY_AT_FIXPOINT 유지).

| new term | physical meaning | source axis | default (stub) |
|---|---|---|---|
| **V_sync_eff** | Kuramoto order-param `K · mean_{i<j}(1−cos Δθ)/2`, min at phase-lock | D-axis coherence (hash-only phase projection) | `1 − sealed_fraction` (Mk.VIII stub) when `HEXA_USE_KURAMOTO_SYNC=0` |
| **V_RG_eff** | `α·\|ν−ν*\|² + β·(1−\|Δφ\|) + γ·exp(−ξ/N)`, min at Ising-2D critical point | RG axis (`edu/cell/rg/`) | `0` when `HEXA_USE_RG_POTENTIAL=0` |
| **λ · I_irr** | per-gen irreversibility signal (`\|ΔW\| / (\|ΔW\| + jitter)`, arrow-of-time clamp) | temporal axis (`edu/cell/temporal/`) | `λ = 0` disables coupling |

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

| file | role | Mk | commit |
|---|---|---|---|
| `t_tension.hexa` | T_k = (ΔW)²/2, pure API | VIII | — |
| `v_structure.hexa` | V_struct stub = −ln(W/W_max); full(comp,diss) reserved | VIII | — |
| `v_sync.hexa` | V_sync proxy = 1 − sealed/total (Mk.VIII stub) | VIII | — |
| `l_cell_integrator.hexa` | composes L_k, Σ L_k, δV/δW residual | VIII | — |
| `mvp_lagrangian.hexa` | driver: 4-gen overlay + ASCII plot + stationary check + cert | VIII | — |
| **`v_sync_kuramoto.hexa`** | Kuramoto order-param `r(θ)` + pairwise `V_sync(θ)`; D-axis hash-only phase projection | **IX** | **`d072bb16`** |
| **`v_rg.hexa`** | V_RG = α·\|ν−ν*\|² + β·(1−\|Δφ\|) + γ·exp(−ξ/N); Ising-2D bowl, 22-assertion selftest | **IX** | **`57acda7b`** |
| **`l_ix_integrator.hexa`** | L_IX = T − V_struct − V_sync_eff − V_RG_eff + λ·I_irr; 462 lines; env-gated Mk.VIII ↔ Mk.IX switching; byte-exact back-compat regression | **IX** | **`226bb780`** |

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

## Mk.IX validation (2026-04-21)

### V_sync Kuramoto fixture (`d072bb16`)
3/5/10-node D-axis fixture (phases = poly_hash projection on D-axis coherence node lists):

| N | r (×1000) | V_sync (×1000) | verdict |
|---|---|---|---|
| 3  | **932** | 97  | F3 ≥ 0.85 pre-reg ✓ (near phase-lock) |
| 5  | 361     | **543** | intermediate |
| 10 | 287     | 508     | maximum desync in fixture |

`r` monotone desync; V_sync peaks at F5 then plateaus. 3 seeds byte-identical.

### V_RG 3-level coarse-grain chain (`57acda7b`)
Driver: `v_rg_demo.hexa`, consumes `shared/state/edu_cell_rg_symmetry.json` (ISING_2D_VERIFIED cert, `ba29b6c1`). Pre-registered α=β=γ=1.0, ν* = 1000 ppm (Onsager exact).

| level | N | ν (ppm) | V_RG (×1000) |
|---|---|---|---|
| L0 | 16 | 750  | 1592 |
| L1 | 8  | 1000 | 1293 |
| L2 | 4  | 1000 | 1043 |

Hierarchical Σ V_RG = **3928** (×1000). 22-assertion selftest PASS. P1 min@Ising ✓ / P2 convex-bowl ✓ / P3 hier-sum ✓ / P4 regression ✓.

### L_IX regression (`226bb780`)
`ws = [40, 125, 687, 1000, 1000]`, phases_g5 locked at π/2, gates=0, λ=0:

| # | check | result |
|---|---|---|
| R1 | action_sum_x1000_ix ≡ action_sum_x1000 (Mk.VIII) | **−11582 byte-exact** |
| R2 | STATIONARY_AT_FIXPOINT verdict preserved | **PASS** |
| R3 | gen-5 I_irr under synthetic fixpoint (ΔW = 0) | **I_irr₅ = 0** (arrow-of-time collapse, raw#30 prediction) |
| R4 | L_kura[5] at perfect phase-lock | **0** (V_sync vanishes, plateau) |

## Arrow cusp (Mk.IX first empirical signature)

From `l_ix_eom_table()` on the gen-5 closure fixture:

| gen | ΔW | I_irr (×1000) |
|---|---|---|
| 3 | +562 | — |
| 4 | +313 | **996** |
| 5 | 0    | **0**   |

**Cusp**: I_irr collapses from 996 → 0 in a single step at the fixpoint. This is a structural prediction of raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN — at the fixpoint ΔW = 0, there is no signal, hence no direction, hence no arrow of time. The discontinuous drop is not a numerical artefact: `I_irr = |ΔW| / (|ΔW| + jitter)` is clamped to 0 when the signed part is ≤ 0 (temporal_emergence.hexa arrow clamp). First empirical signature of Mk.IX at the basin.

## Cross-links

- `../causal/` — CEI / IR / CD / MB (re-verify `696d1665`, CAUSAL_FAILED 0/3 MB-only, IR+CD strong-PASS for UNIVERSAL_4)
- `../information/` — Shannon H / IB / KSG (re-verify `d52135ed`, INFORMATION_FAILED 0/3 O2-directional, ΔIB ×39)
- `../rg/` — ν critical exponent (ISING_2D_VERIFIED cert consumed by `v_rg.hexa`)
- `../temporal/` — `I_irr`, τ_mem, Hurst (temporal_emergence.hexa arrow clamp reused by `l_ix_integrator.hexa`)
- `../composition/` — V_structure compositional term source (future wiring)
- `../dissipation/` — V_structure Landauer term source
- `../../mk_ix/` — Mk.IX drill result (top 3 angles landed as three files above)
- `../../mk_viii/` — 7-axis unified Lagrangian fixpoint validator (Mk.VIII skeleton)

## Limitations (MVP — to close in follow-ups)
- V_structure uses `−ln(W/W_max)` stub; full `(comp, diss)` form wired but unused until those axes land on this corpus.
- V_sync (Mk.VIII) uses sealed-fraction proxy; Kuramoto landed in Mk.IX (`v_sync_kuramoto.hexa`) but default path still stub until `HEXA_USE_KURAMOTO_SYNC=1` enabled by the surrounding sweep harness.
- V_RG default disabled (`HEXA_USE_RG_POTENTIAL=0`); consumes pre-registered ISING_2D_VERIFIED cert — chain requires that cert present for enablement.
- Gen 5 is **synthetic** (W_5 = W_4 = 1000 asserted, not produced by an actual crystallize step). A natural-run gen 5 from the 1/r² lattice dynamics would validate that W indeed stays pinned at 1000 rather than drifting. The closure proof here is structural (conditional on W_5 = W_4 = 1000).
- Arrow cusp signature (gen 4→5 I_irr 996→0) derives from the synthetic gen-5 fixture; natural-run reproduction pending full-scale crystallize re-run.
- scaling sweep (task #16) on (N, K, β, γ) **in-flight** — will provide critical-behavior map of L_IX.
- Stage0 module loader is fragile — `l_cell_integrator.hexa` and `mvp_lagrangian.hexa` both inline their primitives (byte-equivalent); if stage0 modules ever become reliable, the duplication should collapse.
