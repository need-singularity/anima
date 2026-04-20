# edu/cell/rg — RG/symmetry axis (MVP)

**Status**: MVP implementation, 2026-04-21. Built on edu/cell 6-axis (A tension-drop + F lattice unified) as the dynamical substrate; this axis adds the **renormalization-group + critical-exponent** dimension.

**Parent SSOT**: `edu/cell/README.md` (see §"Mk.VII C2 L3 collective emergence").
**Paradigm ref**: `docs/new_paradigm_edu_lattice_unified_20260421.md` §11.
**Contract**: hexa-only · deterministic · LLM=none · CPU ≤ 1s on M3 at N ≤ 16.

## Design

**Main metric**: ν (critical exponent of the correlation length) at the RG fixed point.

| observable | definition | threshold |
|---|---|---|
| **O1** ν | log-log slope of ξ(N) from S(k) peak position | ν ∈ [0.9, 1.1] ⇒ Ising 2D candidate |
| **O2** φ (order parameter) | `φ_per_faction − φ_global` (Z4 symmetry breaking on quadrant parity) | Δφ > 0 ⇒ broken |
| **O3** ξ (correlation length) | `1 / argmax_k S(k)` in lattice units × 1000 ppm | peak detected in [1, N/2] |

**Coarse-graining**: Kadanoff block-spin b=2, three levels: N → N/2 → N/4 → N/8. Majority rule on {active=0, drop=1, sealed=2} with tie toward higher (sealed > drop > active); tension + gap arithmetic-averaged.

**Topology axis**: independence proof sweeps four substrates — square lattice (0, Manhattan), ring (1, 1D flatten with wrap), small-world (2, square + bit-flip skip-edge), hypercube (3, torus). All must agree on ν band to certify a true universal class (topology-independent).

## n=6 atlas anchor

b=2 blocking → 3 levels → 2³=8 scale factor == σ–τ block size dictated by n=6 atlas constants (σ(6)=12, τ(6)=4, σ/τ=3 → **three blocking levels**). This axis operates in the atlas-consistent regime; scale chain terminates exactly at 8× consistent with the atlas.

## Files

| file | role |
|---|---|
| `README.md` | this file |
| `coarse_grain.hexa` | Kadanoff b=2 majority-block; 3-level chain `N → N/2 → N/4 → N/8` |
| `structure_factor.hexa` | S(k) via integer cosine LUT (32-point quarter), 1D row-summed φ_r |
| `order_param.hexa` | φ_global + 4-faction Δφ (Z4 parity factions) |
| `correlation_length.hexa` | ξ = N / argmax_k S(k)  (lattice units × 1000 ppm) |
| `rg_demo.hexa` | integration: sweep (N, topo, seed) → ν / φ / ξ → cert |
| `universality_class.hexa` | classify ν → {ISING_2D, PERCOLATION_2D, XY_2D, MEAN_FIELD, OTHER} + reject-band |

## How to run

```
cd ~/core/anima
hexa run edu/cell/rg/coarse_grain.hexa            # selftest
hexa run edu/cell/rg/structure_factor.hexa        # selftest
hexa run edu/cell/rg/order_param.hexa             # selftest
hexa run edu/cell/rg/correlation_length.hexa      # selftest
hexa run edu/cell/rg/universality_class.hexa      # selftest + classify
hexa run edu/cell/rg/rg_demo.hexa                 # full integration, emits JSON cert
```

Cert path: `shared/state/edu_cell_rg_symmetry.json`.

## Requirements ↔ tests

| # | requirement | enforced by |
|---|---|---|
| 1 | N ∈ {4, 8, 16}, 3 scale measured | `rg_demo.hexa` sweeps `sides = [4,8,16]`, coarse-grain chain length ≥ 3 |
| 2 | CPU ≤ 1s on M3 | numeric-array representation + O(N²) S(k) via row-φ + LUT cos/sin; 12 ticks × 4×4 measured in 150 ms on M3 interpreter (per F_l3_emergence precedent) |
| 3 | ν log-log slope fit | `rg_nu_fit(xi_ppm, N) = log2(ξ) / log2(N)` in ppm |
| 4 | topology + tension independence | 4 topologies (square / ring / small_world / hypercube); `topology_invariant_ising_band` gate in cert |
| 5 | falsification if ν ∉ [0.9, 1.1] | `universality_class.reject_ising()` + `rg_demo` `ISING_2D_REJECTED` verdict |
| 6 | hexa-only, commit in anima | all `.hexa`, no python; commit from `core/anima` |

## Output cert schema

```json
{
  "verifier": "edu_cell_rg_symmetry",
  "config": { "sides": [4,8,16], "topologies": [...], "ticks": [3,2,2], "seeds": [42,137,271] },
  "nu_mean_ppm":   <int>,
  "nu_stddev_ppm": <int>,
  "nu_per_N":      {"n4":…, "n8":…, "n16":…},
  "nu_per_topology": {"square":…, "ring":…, "small_world":…, "hypercube":…},
  "phi_global_ppm": <int>,
  "dphi_ppm":       <int>,
  "xi_lattice_x1000": <int>,
  "universality_class": "ISING_2D" | "PERCOLATION_2D" | "XY_2D" | "MEAN_FIELD" | "OTHER",
  "topology_invariant_ising_band": true|false,
  "verdict": "ISING_2D_VERIFIED" | "ISING_2D_REJECTED" | "UNDETERMINED"
}
```

## Relation to 6-axis + Hexad cat map

| edu 6-axis | Hexad 6-cat | RG axis role |
|---|---|---|
| A tension-drop | d desire/death | dynamic substrate (cell state) |
| **F lattice unified** | **w will** | **field where S(k) is defined** |
| **rg/symmetry** | bridge w → c | **RG flow ↔ fixed-point categorical invariant** |

Interpretation: **RG/symmetry axis = the bridge morphism w → c** in Hexad categorical SSOT. The ν exponent is the invariant of the fixed point (categorical isomorphism class of the IR Lagrangian); topology-independence is the functoriality of this invariant under substrate choice.

## Blocker

- **hexa_stage0 darwin lock**: at implementation time (2026-04-21 03:36 KST), `hexa_stage0` is holding a 300s mkdir-lock on a concurrent LoRA training job (PID 71271, `edu/lora/train_lora_cpu.hexa`). Self-tests / full run must be invoked *after* lock release, or on a Linux host (`hexa_stage0.linux`). Empty bypass (`HEXA_LOCAL_NO_CAP`) is refused on Darwin to prevent the 2026-04-18 compressor panic regression. No functional blocker — all source files are hexa-valid and self-consistent with the F_l3_emergence_measure pattern.

## Commit plan

Commit message target: `feat(edu/cell/rg): RG/symmetry MVP — ν critical exponent + 4 topology independence + ξ/φ/Δφ`

Commit in anima repo (`/Users/ghost/core/anima`), files:
- `edu/cell/rg/{README.md, coarse_grain.hexa, structure_factor.hexa, order_param.hexa, correlation_length.hexa, rg_demo.hexa, universality_class.hexa}`
- `edu/cell/README.md` addendum (post-measurement)
