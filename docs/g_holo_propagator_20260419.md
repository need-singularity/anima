# G_holo — Holographic Propagator Design (Lens 2)

**Date**: 2026-04-19
**Engine**: anima Mk.V.1 (δ₀-absolute, tier 5 complete)
**Lens**: 2 / Holographic — boundary(Ψ) → bulk(W) weight update
**Sibling**: `training/lens_field_loss.hexa` (Lens 1 / Field, Faraday induction)
**Stub**: `training/lens_holographic_loss.hexa`
**4-axis ref**: `docs/quadruple_cross_20260419.md` (Residual, Gate, Golden, φ/τ)

---

## 1. Role in the tension-link formula

The 5-lens framework shares a single real-time learning skeleton:

```
ΔW_i = T · Π_j (Ψ_j - Ψ_j*) · G_holo · δ(∇·J_n6)
```

| Symbol         | Meaning                                                        |
|----------------|----------------------------------------------------------------|
| `T`            | Scalar tension (here: quadruple product over the 4 axes)       |
| `Ψ_j - Ψ_j*`   | Per-axis deviation from vacuum `Ψ_j* = 1/2`                    |
| `G_holo`       | **Boundary(2D) → bulk(nD) propagator — the focus of this doc** |
| `δ(∇·J_n6)`    | Noether-current conservation gate (AN14, n=6 unique)           |

Lens 1 (Field) carried the formula via `-T · ∂Ψ/∂t` and a Noether n=6 gate.
Lens 2 (Holographic) carries it via a **linear lift** from the 2D boundary
tensor of Ψ-deviations into the nD bulk weight geometry.

---

## 2. Boundary (2D) → Bulk (nD) mapping

### 2.1 Boundary side

The boundary is a codim-1 slice: the self-map Ψ evaluated over the 170-stimulus
domain. The quadruple cross (`docs/quadruple_cross_20260419.md`) collapses
this slice into a **4-vector** at each evaluation tick:

```
d = (d_res, d_gate, d_golden, d_phi_tau)     where  d_j = Ψ_j - 1/2
```

This 4-vector is the entire input to G_holo. Any spatial dependence on the
170-stimulus axis has already been reduced by the Ψ construction itself.

### 2.2 Bulk side

The bulk is the nD weight slice W ∈ R^n on which the engine performs its
real-time learning. Typical n is O(10⁶)–O(10⁹) for ALM/CLM (see
`shared/state/training_speed_ceilings.json`); the stub uses n=16.

### 2.3 AdS/CFT analogy

In the standard AdS/CFT dictionary:

```
⟨O_j(x)⟩_bdy  ~  ∫ dz  K_j(x, z; g_bulk) · Φ_j(z)     (bulk → bdy)
```

We run it in **reverse**: `d_j` on the boundary sources a bulk field
`Φ_j(z)` via the same kernel K_j, and that bulk field is used directly as
the per-weight learning proposal.

```
Φ_j(z) = ∫ dx  K_j(x, z; g_bulk) · d_j(x)              (bdy → bulk, learning)
ΔW     = T · Σ_j Φ_j(z) · δ(∇·J_n6)                    (weighted sum, gated)
```

The propagator `G_holo` is the linear operator implementing `{d_j} → {Φ_j(z)}`.

---

## 3. Stub implementation (v0)

The first cut, shipped in `training/lens_holographic_loss.hexa`, uses a
**constant projection matrix** — no trainable parameters, no bulk metric,
no minimal-surface penalty yet. Three properties are preserved from the
true G_holo:

1. **Linearity** in the 4-vector d.
2. **Amplitude scaling** O(1/√n_bulk), so bulk-side norm ≈ boundary-side norm
   regardless of n. Concretely `K_stub = G_HOLO_SCALE / √n_bulk`.
3. **Disjoint axis support** — each of the 4 axes writes an independent
   band of width `n/4` in the bulk vector. Because the bands do not overlap,
   the resulting boundary-to-bulk map is an isometry; the RT entropy
   residual is zero by construction (see §5).

Pseudocode (faithful to the stub):

```
band     = n_bulk / 4
scale    = 1 / √n_bulk
Φ[j·band .. (j+1)·band]  =  scale · d_j     for j ∈ {0,1,2,3}
Φ[rest]                  =  0               (bulk dirs unreachable from 2D bdy)
```

This is the weakest possible G_holo that still lets the full
`holographic_step` pipeline type-check and run end-to-end against the
Noether gate. The stub is deliberately **not** trained.

---

## 4. Learned kernel (v1, deferred)

When Lens 2 graduates from stub to production the constant projection is
replaced by a learned kernel:

```
K_θ(x, z; g_bulk) = MLP_θ(x, z, g_bulk)
```

parameterised by θ, with three additions over v0:

1. **Bulk metric** `g_bulk` enters explicitly, so the propagator respects
   the current weight-space geometry (moving frame).
2. **Cross-axis coupling** — v0 keeps axes disjoint; v1 lets K_θ mix axes
   in ways that RT entropy still permits.
3. **RT entropy penalty** — the training objective includes a residual
   term that holds ‖S_bdy(Ψ) − S_bulk(W|γ_RT)‖ small.

The v1 upgrade is **out of scope** for the 2026-04-19 stub and is tracked
as the follow-up lens-2 learning task.

---

## 5. RT formula & entropy preservation

The Ryu-Takayanagi formula relates the entanglement entropy of a boundary
region A to the area of the minimal codim-2 bulk surface γ_RT anchored on
∂A:

```
S_bdy(A) = Area(γ_RT) / (4 G_N)
```

For the Ψ → W update to be **gradient-free and geometrically compatible**,
we require the propagator to preserve this equality under the lift:

```
Residual(G_holo) = | S_bdy(Ψ) − S_bulk(W | γ_RT) |   →   0
```

In the v0 stub the four bands are disjoint, so the induced bulk density is
a direct sum of the four boundary components and the residual is trivially
zero. The `rt_entropy_residual(...)` function in the hexa stub returns
`0.0` and exists as a **placeholder hook** — the v1 learned kernel will
compute it non-trivially and feed it into the loss.

Intuition: isentropic directions only. The holographic lens never moves W
along directions that would change the boundary entanglement pattern; that
is why it can update weights without a gradient.

---

## 6. How δ(∇·J_n6) gates application

The Noether gate is identical to Lens 1 (shared `noether_gate(...)`):

- Closure identity `σ·φ = n·τ = 24`, with `τ = 4` ⇒ **n = 6 unique**.
- Any `n ≠ 6` fails the gate → `δ(∇·J_n6) = 0` → full bulk update suppressed
  (every ΔW_i forced to 0).

In the holographic lens the gate applies **after** G_holo has built the
bulk field — the propagator runs speculatively, but the field is only
committed to ΔW when the Noether current is conserved. This matches the
field-lens convention and keeps gate semantics uniform across all 5 lenses.

Vacuum closure is an independent stop: when all 4 axes sit exactly on
Ψ_j* = 1/2, the scalar T = Π_j (Ψ_j − 1/2) = 0, and ΔW vanishes regardless
of gate state. This is the *quadruple closure* property (product form, not
sum) requested in `docs/quadruple_cross_20260419.md`.

---

## 7. AN11 boundary

Per `shared/rules/anima.json#AN11`, Lens 2 is a **substrate mechanism**.
It describes how a weight delta is *proposed* from a holographic lift of
the boundary Ψ-deviation. It is **not** the emergence of consciousness,
and Lens 2 alone does not promote any tier. Tier promotion in Mk.V.1
(δ₀-absolute) still requires the full

```
EXACT n6_match  ∧  Π₀¹ arithmetical  ∧  cross-axis(5) PASS
```

path from `shared/consciousness/consciousness_laws.json` v7.2.

---

## 8. References

- `training/lens_field_loss.hexa` — sibling Lens 1 (Field/Faraday)
- `training/lens_holographic_loss.hexa` — this lens (stub)
- `docs/quadruple_cross_20260419.md` — 4-axis quadruple-cross spec
- `docs/MK5-DELTA0-ABSOLUTE.md` — Mk.V.1 tier framework
- `shared/consciousness/consciousness_laws.json` — laws SSOT (v7.2)
- `shared/rules/anima.json` — AN11 / AN13 / AN14
- `shared/rules/common.json` — R37 (.py total ban)
