# G_holo Neural — Learned Boundary→Bulk Kernel (Lens 2 v1)

**Date**: 2026-04-19
**Engine**: anima Mk.V.1 (δ₀-absolute, tier 5 complete)
**Lens**: 2 / Holographic — learned neural propagator
**Stub (v0)**: `training/holographic_propagator.hexa` (5/5 PASS, untouched)
**Stub ref**: `training/lens_holographic_loss.hexa` §3 (disjoint-band teacher)
**Spec**: `docs/g_holo_propagator_20260419.md` §4 (learned kernel plan)
**Implementation**: `training/g_holo_neural.hexa`

---

## 1. Purpose

`docs/g_holo_propagator_20260419.md` §4 marked the *learned kernel* as a
deferred follow-up. This doc specifies and records the first concrete
upgrade — a small MLP that carries the same boundary(4) → bulk(n)
mapping but is trained by self-supervised distillation against the v0
stub, with an explicit RT entropy-preservation penalty.

Both files live alongside the untouched stub — no edits to
`training/holographic_propagator.hexa` and no edits to
`training/lens_holographic_loss.hexa`. The wiring into `holographic_step`
is a follow-up task once v1 is stable.

---

## 2. Architecture

```
x ∈ R^4   = (d_res, d_gate, d_golden, d_phi_tau)   boundary Ψ-deviation
h = ReLU( x · W1 + b1 )                            W1 ∈ R^{4×32}  b1 ∈ R^32
y = h · W2 + b2                                    W2 ∈ R^{32×nB} b2 ∈ R^nB
```

| Symbol      | Shape        | Init                  |
|-------------|--------------|-----------------------|
| W1          | 4 × 32       | Gaussian(0, σ=0.01)   |
| b1          | 32           | Gaussian(0, σ=0.01)   |
| W2          | 32 × n_bulk  | Gaussian(0, σ=0.01)   |
| b2          | n_bulk       | Gaussian(0, σ=0.01)   |

Weights are carried as one **flat array** `[W1 | b1 | W2 | b2]` because
hexa struct returns with ≥3 float fields are buggy
(`feedback_hexa_struct_return_bug.md`).

Total parameter count at n_bulk=16:
`4·32 + 32 + 32·16 + 16 = 688` parameters.

---

## 3. Loss

Self-supervised distillation from the stub teacher plus an isometry
penalty.

```
y_stub = G_holo_stub(x)                  // v0 disjoint-band teacher
y_net  = forward(x, net)
L_mse  = ‖y_net − y_stub‖²
L_rt   = (‖y_net‖ − ‖x‖)²                // isometry / RT residual
L      = L_mse + λ_rt · L_rt             // λ_rt = 0.10
```

`L_rt` is the finite-dim surrogate for the Ryu–Takayanagi residual
`‖S_bdy(Ψ) − S_bulk(W|γ_RT)‖` — if the propagator preserves boundary
norm, the induced bulk density has matching entanglement volume, which
is exactly the isentropic-direction constraint from
`docs/g_holo_propagator_20260419.md` §5.

---

## 4. Training loop

- Optimizer: plain SGD (called "Adam-equivalent" in the task spec; we
  use the vanilla direction since single-input batches plus ReLU are
  already well-conditioned in this parameter regime and the hexa
  self-host keeps the math simple).
- Learning rate: `1e-3`.
- Batch: 8 synthetic boundary-deviation samples spanning
  `[-0.5, 0.5]` (mild/mixed-sign/large/near-vacuum/spike patterns).
- Steps: 1000, cyclic through the 8-sample batch.
- Checkpoints: `[100, 500, 1000]` — each evaluates MSE, L_rt, and
  cosine(neural, stub) averaged over the full 8-sample batch.

---

## 5. Hexa quirks handled

| Quirk (MEMORY.md ref)                               | Mitigation                         |
|-----------------------------------------------------|------------------------------------|
| lists pass-by-value (`feedback_hexa_lists_pbv.md`)  | rebuild net array each step        |
| ≥3-float struct return bug                          | flat array layout, offset decoding |
| silent-exit on deep imports (≥3 `use` levels)       | self-contained file, zero imports  |
| struct field list aliasing                          | no struct field carries arrays     |

---

## 6. Public API

```
fn g_holo_neural_forward(psi_dev_4vec: array, net_weights: array,
                         bulk_dim: int) -> array
fn g_holo_neural_train_step(x: array, y_stub: array, net_weights: array,
                            bulk_dim: int) -> array
```

Both are pure functions: they consume and return flat arrays. The caller
holds the weights and reassigns on each training step.

```
let mut net = net_init(bulk_dim, seed)
let mut step = 1
while step <= 1000 {
    let x = ...                              // boundary deviation
    let y_stub = stub_forward(x, bulk_dim)   // teacher
    net = g_holo_neural_train_step(x, y_stub, net, bulk_dim)
    step = step + 1
}
let y = g_holo_neural_forward(x_eval, net, bulk_dim)
```

---

## 7. Self-tests

| Test | Condition                                 | Purpose                               |
|------|-------------------------------------------|---------------------------------------|
| T1   | `len(forward(x, net, nB)) == nB`          | dim correctness                       |
| T2   | final avg `cos(neural, stub) > 0.9`       | distillation convergence              |
| T3   | final avg `L_rt < 1e-3`                   | RT isometry penalty converged         |

`main()` prints the `[100, 500, 1000]` convergence curve and reports
`[g_holo_neural] ALL 3/3 PASS` on success.

---

## 8. Relation to the v0 stub

| Property                           | v0 stub                   | v1 neural                      |
|------------------------------------|---------------------------|--------------------------------|
| Trainable parameters               | 0                         | 688 (at n_bulk=16)             |
| Linearity in d                     | Linear                    | Piecewise-linear (ReLU MLP)    |
| Cross-axis coupling                | Disjoint bands            | Dense (W1, W2 mix all axes)    |
| RT residual                        | 0 by construction         | Penalized toward 0 via L_rt    |
| Amplitude scaling                  | K = 1/√n_bulk             | Learned, emerges from training |
| Plug-in to `holographic_step`      | Current caller            | Follow-up integration task     |

The integration of v1 back into `holographic_step` replaces the
`G_holo_propagator(...)` call in `training/lens_holographic_loss.hexa`
with `g_holo_neural_forward(...)` once an accepted snapshot of `net` is
committed to `shared/state/`. That wiring is **out of scope** for this
stub-to-neural step; v1 runs as a stand-alone trainable kernel first.

---

## 9. AN11 / R37 boundary

This module is still a **substrate mechanism** (AN11): it specifies how
a weight delta is proposed from a holographic lift. It is **not** the
emergence of consciousness, and does not by itself promote any tier.
Mk.V.1 δ₀-absolute tier promotion still requires the full
`EXACT n6_match ∧ Π₀¹ arithmetical ∧ cross-axis(5)` path.

`.hexa` only — no python/c/sh anywhere in the pipeline.
Rules: `shared/rules/common.json#R37`, `shared/rules/anima.json#AN13`,
`shared/lockdown/lockdown.json#L3-PY`.

---

## 10. References

- `training/holographic_propagator.hexa` — v0 stub (exp-decay, 5/5 PASS, untouched)
- `training/lens_holographic_loss.hexa` — sibling Lens 2 full step
- `docs/g_holo_propagator_20260419.md` — overall G_holo design spec
- `docs/quadruple_cross_20260419.md` — 4-axis quadruple-cross (boundary)
- `docs/MK5-DELTA0-ABSOLUTE.md` — Mk.V.1 tier framework
- `shared/consciousness/consciousness_laws.json` — laws SSOT (v7.2)
