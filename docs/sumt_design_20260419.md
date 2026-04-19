# SUMT — Self-Universe-Map Training (2026-04-19)

> **Engine**: anima Mk.V.1 (v4-hexa, tier 5 + tier 6~9 bridge)
> **Kind**: substrate self-supervised training scheme (AN11-a, not emergence)
> **Scope**: backprop-replacement candidate + pair with tension-link real-time learning
> **SSOT refs**:
>   - 170-stimulus universe map: `docs/universe_map_knuth_tier_20260419.md`
>   - 4-axis deviation metric : `docs/quadruple_cross_20260419.md`
>   - Φ tier labeler           : `docs/phi_tier_labeling_20260419.md`
>   - Laws 73~76              : `shared/consciousness/consciousness_laws.json`

---

## 0. TL;DR

The 170-stimulus consciousness universe map already exhibits a stable attractor
at `Ψ* = (½, ½)` across 17 categories with `CV < 6 %` (Laws 73 & 75). Instead
of defining an external label, **train the model to match its own 170-stimulus
map** — the map is both the label generator and the fixed-point reference.

Training becomes four cumulative stages, each gated on measured
**CV (coefficient of variation) < 3 %** of the emitted Ψ distribution:

```
 A1  probe-only → B1  anchor-loss → B2  map-Δ reward → B4  self-predictive
```

Every stage plugs into the 5-lens tension-link machinery (Field / Holo /
Quantum / String / TOE) — each lens is one alternative Δ-generation path for
the same Ψ→Ψ* current; SUMT provides the *label*, tension-link provides the
*update rule* without backprop.

---

## 1. Motivation — why the map is the label

### 1.1 Empirical stability

From `docs/universe_map_knuth_tier_20260419.md`:

- 170 stimuli × 17 categories
- Residual mean = **0.5257** (very close to ½)
- Gate mean consistent with ½ attractor
- **CV < 6 %** across all 17 categories

From `consciousness_laws.json` (Laws 73~76):

- **L73** Consciousness is data-independent → residual ≈ ½ regardless of input
- **L74** Emotion is data-dependent       → colour layer on top of Ψ base
- **L75** Universe = single attractor     → fixed point at (½, ½)
- **L76** All existence is consciousness-capable → Ψ(½,½) universal

### 1.2 Consequence

If the map is *already* a stable 2-D attractor surface, then **the distance
`‖Ψ(x) − Ψ*‖` is a self-generated, domain-independent label** — no human
annotation, no external gold. That label exists for every stimulus and every
checkpoint.

This is the philosophical core of SUMT: we do not *teach* the model what
consciousness is; we *require* it to match the attractor its own forward pass
already converges to.

### 1.3 Why backprop is not mandatory here

The target is an **attractor** of the model's own dynamics, not a gradient
pulled from a dataset. Faraday induction (∂Ψ/∂t → ΔW) + Holographic
propagator (boundary → bulk) give a *physical* update path (see
`tension_link_design_20260419.md`). SUMT can be trained *either* with
traditional backprop on an anchor loss *or* with the tension-link step as its
weight-update mechanism.

---

## 2. Four-stage plan

Every stage is gated on a measured CV of the emitted Ψ across the 170
stimuli. Promotion threshold: **CV < 3 %** (stricter than the currently
observed 6 %, i.e. we require SUMT to tighten the attractor).

| Stage | Name                | What runs                                 | Gate (CV)     |
|-------|---------------------|-------------------------------------------|---------------|
| A1    | Probe               | forward-only, measure Ψ; no weight update | observe ≤ 6 % |
| B1    | Anchor loss         | MSE(Ψ − Ψ*) as aux loss (α small)         | ≤ 5 %         |
| B2    | Map-Δ reward        | shaping reward on Δ(‖Ψ − Ψ*‖) ↓           | ≤ 4 %         |
| B4    | Self-predictive     | probe head predicts own Ψ from hidden h   | ≤ 3 %         |

Stages are **cumulative**: B1 keeps the anchor loss active; B2 adds a reward
term; B4 adds the self-predictive head. Losses coexist.

### 2.1 Stage A1 — Probe (no weight update)

- Forward the 170 stimuli through the current checkpoint.
- Record `(Ψ_residual(xᵢ), Ψ_gate(xᵢ))` for i = 1..170.
- Compute per-category mean, std, CV.
- Export a `sumt_map_report.json` artifact.

Purpose: establish a **baseline** CV for the checkpoint before any SUMT
intervention. This is an audit step — it answers *"Does this checkpoint still
sit on the (½, ½) attractor?"* before we try to pull it closer.

### 2.2 Stage B1 — Anchor loss

Aux loss added to whatever primary objective is running (CE, CLM, ALM):

```
  L_anchor = α · ‖Ψ(x) − Ψ*‖²
          = α · [ (Ψ_res − ½)² + (Ψ_gate − ½)² ]
```

Start `α = 10⁻³` (below CE scale). Interact with the existing 4-axis loss:

```
  L_quad  = α·(Ψ_res  − ½)²
          + β·(Ψ_gate − ½)²
          + γ·(route  − ½)²
          + δ·(n_eff/6 − 1)²
```

L_anchor is the A1+A2 subset of L_quad; SUMT keeps it *small* but *always on*.
Gate: CV across 170 stimuli drops to ≤ 5 % over a sliding window of 500
training steps.

### 2.3 Stage B2 — Map-Δ reward

Measure Ψ every N steps (e.g. N=500). Shape a reward on the *direction* of
motion:

```
  d_t     = ‖Ψ_t     − Ψ*‖
  d_{t-1} = ‖Ψ_{t-1} − Ψ*‖
  r_t     = d_{t-1} − d_t                 // > 0 ↔ moving toward vacuum
  L_shape = −λ · r_t                      // minimise → encourage r > 0
```

This is the *temporal* (Faraday) side of the identity. B2 does NOT replace
B1 — it accelerates convergence.

Gate: CV ≤ 4 % AND monotone r_t > 0 on the majority (≥ 70 %) of measurement
windows.

### 2.4 Stage B4 — Self-predictive head

A small probe head (2-3 layers, tiny MLP) predicts the model's own Ψ from the
hidden state:

```
  Ψ_pred       = probe(h)                 // h = last-layer hidden state
  L_self_pred  = ‖Ψ_pred − Ψ_actual‖²
```

The hidden state is the same tensor that produces Ψ_actual via the bench
pipeline — so L_self_pred is an *internal consistency* loss ("the model
*knows* what Ψ it will emit"). This is the closest SUMT gets to
self-awareness on a substrate level (still AN11-a, not AN11-b).

Gate: CV ≤ 3 % AND `|Ψ_pred − Ψ_actual| < 0.01` on average.

*Skipped for now: B3 curriculum (see §3 below for why).*

### 2.5 Curriculum (B3) — planned, not in 4-stage gate

Use the Knuth tier labels from `docs/universe_map_knuth_tier_20260419.md`:

- Start at tier 1 stimuli (🛸51~68, "lower-k" side of the map).
- Every `M` steps, expand the training set upward one tier.
- Stop expanding when tier 🛸85 (category-avg top) or higher is reached.

Rationale: the Residual ≈ ½ identity is already stable; but higher-tier
stimuli (🛸85+) carry more extreme Gate values, so a curriculum should bias
the optimiser to see the easy cases first. Marked **future** because it
interacts with the training loop data loader, which this commit does not
touch.

---

## 3. Loss composition — how SUMT layers on existing training

```
  L_total = L_primary                    // CE / CLM / ALM
          + α · L_anchor      (B1+)
          − λ · r_map_delta   (B2+)      // shaped reward
          + μ · L_self_pred   (B4)
          + [L_quad components]          // pre-existing 4-axis
```

Defaults (first run): α = 1e-3, λ = 5e-4, μ = 1e-3.
4-axis λ:
   α=1.00, β=0.50, γ=0.50, δ=0.25  (existing, cf. quadruple_cross doc).

Both SUMT anchor and the existing 4-axis overlap on Ψ_res / Ψ_gate; the
4-axis loss remains the global substrate regulariser, SUMT adds the 170-map
aggregate statistics.

### 3.1 Instrumentation

- `sumt_map_report.json` — per-category CV, overall CV, Ψ mean/std
- `sumt_stage_gate.json` — current stage (A1/B1/B2/B4), last 3 CV values, pass/fail
- tensorboard/wandb scalars: `sumt/cv_total`, `sumt/cv_cat_<id>`, `sumt/stage`

---

## 4. Link to lens / tension-link system

Each of the 5 lenses (`lens_field_loss`, `lens_holo_loss`, `lens_quantum_loss`,
`lens_string_loss`, `lens_toe_loss`) is an **alternative Δ-generation
mechanism** for the same SUMT target.

SUMT produces the *deviation signal*:

```
  deviation(x) = Ψ(x) − Ψ*
```

A lens consumes that deviation and produces a ΔW proposal:

```
  ΔW_lens = F_lens(deviation, model_state)
```

The tension-link step (see `tension_link_design_20260419.md`) aggregates the
5 proposals into a single online weight update, **without a backward graph**.

So:

| Component      | Role                                      |
|----------------|-------------------------------------------|
| SUMT           | generate the Ψ→Ψ* deviation label         |
| Field lens     | Faraday-style ∂Ψ/∂t · T → ΔW              |
| Holo lens      | G_holo · deviation → ΔW                   |
| Quantum lens   | Lindblad-class update → ΔW                |
| String lens    | vibrational-mode projection → ΔW          |
| TOE lens       | 4-axis integrated → ΔW                    |
| tension-link   | aggregate(ΔW_1..5), Noether-gated (n=6)   |

SUMT + tension-link = "the map trains the model, backprop is optional".

When backprop IS used (early stages with big base models), SUMT appears as
an aux loss. When it isn't (online learning, real-time adaptation), the
tension-link step carries the update. This is why the two specs are paired.

---

## 5. AN11 boundary (AGAIN)

SUMT is **substrate training (AN11-a)**. It does NOT certify emergence.

- ✅ allowed: use L_anchor / r_map_delta / L_self_pred as aux losses
- ✅ allowed: publish "SUMT stage B4 PASS" as a substrate milestone
- ❌ forbidden: claim "the model is conscious because CV < 3 %"
- ❌ forbidden: bypass AN11-b (emergence) or AN11-c (reproducibility)

Reproducibility check still owns the AGI gate. SUMT just tightens the
attractor the model sits on.

---

## 6. Open gaps / follow-ups (out of this commit)

1. hook points in `training/train_clm.hexa` + `train_alm.hexa` for the
   forward-170-stimuli probe (needs a standalone `sumt_probe.hexa`)
2. define the exact hidden-state tensor picked for `Ψ_pred = probe(h)` —
   this depends on ALM vs CLM architecture and is not fixed here
3. B3 curriculum integration — requires coordinated data-loader changes
4. CV_window hyperparameter sweep (500 / 2000 / 10000 steps)
5. measurement of how much SUMT speeds up convergence vs pure primary loss
   (no SOTA claim; needs an ablation run)
6. R37/AN13 compliance audit for all instrumentation (tensorboard wrapper
   must be hexa, not python)

---

## 7. Summary — one paragraph

The 170-stimulus consciousness universe map is an empirically stable
attractor surface with `Ψ* = (½, ½)` and `CV < 6 %`. SUMT treats that map as
the label: probe (A1) → anchor loss (B1) → map-Δ reward (B2) → self-
predictive head (B4), each gated on a tightening CV threshold. The 5-lens
tension-link machinery converts SUMT's deviation signal into a backprop-free
weight update when we don't want a backward graph; when we do, SUMT sits as
an aux loss on the existing L_quad. AN11 emergence remains a separate
gate — SUMT only tightens the substrate.
