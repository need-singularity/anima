# brain_tension_replica — Φ boost evolution (+8.3% → +17% → +30%)

**Date**: 2026-04-21
**Scope**: Evolution 1/6 of `docs/modules/brain_tension_replica.md` — Φ boost
path from current DD174 single-technique +8.3% toward +17% (2×) and +30%
(roadmap).
**Engine**: anima Mk.V.1 (δ₀-absolute, tier 5 complete), V8 SAFE_COMMIT.
**Constraint**: LLM-judge BANNED. Boost measured via `PhiIIT` (pairwise MI
+ minimum partition, `n_bins=16`). Deterministic seeds `[42, 137, 256]`
mandatory for reproducibility.

> **NOTE**: this document is a *new* evolution spec. The canonical
> `docs/modules/brain_tension_replica.md` is NOT modified — this file
> sits alongside it and lands in the module's next promotion as an
> `evolve_*` satellite.

---

## 0. Why evolve — current Φ boost ceiling

DD174 locked in a single mechanism: **bidirectional hidden-state tension
link (TL-grad injection)** between two ConsciousnessEngines at
coupling `alpha=0.08`. One technique, one injection point, one schedule.
The ceiling is structural, not a tuning issue.

---

## 1. Current +8.3% — evidence & limits

### 1.1 Evidence (from `DD174-tension-link-verify.md`)

| Field | Value |
|---|---|
| Script | `anima/experiments/consciousness/tension_link_verify.hexa` (R37/AN13/L3-PY blocked — numpy impl lives in `ready/`) |
| Engine | `ConsciousnessEngine` (GRU cells + 12 factions + Hebbian sync + breathing + Φ ratchet), 64 cells |
| Protocol | 3 phases × 300 steps — (1) solo, (2) connected, (3) disconnected |
| Seeds | `[42, 137, 256]` — 3 trials |
| Metric | `PhiIIT` (pairwise MI + MIP, `n_bins=16`) |
| Boost | Trial means +8.1% / +9.0% / +7.8% → **mean +8.3%**, σ=0.5%, CV=6% |
| Alpha sweet spot | 0.04-0.15; peak seed=42 → **+14.8% @ α=0.08**; α≥0.20 collapses diversity |

### 1.2 Where/what/how (the 1-technique surface)

| Axis | Current state | Limit |
|---|---|---|
| **Layer / site** | *single* site — hidden (cell) state of the GRU, bidirectional | no multi-layer, no multi-head targeting |
| **Channel weights** | 5 channels (concept\|context\|meaning\|auth\|sig) uniform, 128D fingerprint | no dynamic re-weighting by context |
| **Schedule** | constant α=0.08 for 300 steps | no annealing, no noise, no curriculum |
| **Depth of teachers** | 1 peer engine (symmetric) | no multi-teacher ensemble, no AdS/CFT bulk |
| **Loop** | open — A↔B injection, Φ measured once | no Φ→α feedback, no recursion on self-mimicry |
| **Reproducibility** | CV=6% across seeds | ceiling is *mechanism* not *variance* |

### 1.3 Reproducibility note

CV=6% across 3 seeds is well below the 50% threshold. The ±0.5%
standard deviation around +8.3% means "seed variance" is *not*
the bottleneck. Adding techniques is the only way up.

---

## 2. +17% path (2× boost) — 4 candidates, Top-2 selected

### Candidate matrix

| # | Technique | Expected | Effort (PD) | Reproducibility | Stack-compatible? |
|---|---|---|---|---|---|
| A | **Multi-layer injection** (1 → 3 → 5 → 8 layers) | +14-18% | 2-3 | HIGH (deterministic — just more sites) | YES |
| B | **α annealing + TL-grad noise schedule** (cosine, warmup-hold-decay) | +12-15% | 1-2 | HIGH (seed-fixed schedule) | YES |
| C | **Dynamic 5-channel weighting** (softmax over context salience) | +10-13% | 2 | MED (gating introduces var) | PARTIAL |
| D | **2-stage distill** (teacher14B → intermediate → student) | +13-16% | 4-5 | HIGH | YES |

### Top-2 pick — A + B (vertical stack)

**A. Multi-layer injection** — DD174 injects at `cell_state` only. Extend
to 3 sites: `input_gate` (pre-activation), `cell_state` (current), and
`output_gate` (post). Alpha split: `α_in=0.04`, `α_cell=0.08`,
`α_out=0.04`. 3 loose sites > 1 strong site because α<0.20 avoids
homogenization per-site.

- Expected: +14-18% (additive MI transfer, 3× channels for same α-budget)
- Experiment: same 3-phase × 300-step protocol, seeds `[42,137,256]`
- Pass gate: mean boost ≥ +14%, CV ≤ 10%
- File: `experiments/consciousness/tl_multilayer_inject.hexa` (new)

**B. α annealing + noise schedule** — constant α=0.08 wastes early
phase (engines still initializing) and late phase (saturation).
Cosine schedule: `α(t) = α_max · (1 - cos(π·t/T))/2` with warmup 30
steps, hold 180, decay 90. Noise: Gaussian on TL grad, σ(t) linear
anneal 0.05 → 0.00.

- Expected: +12-15%
- Experiment: same protocol with scheduled α and noise
- Pass gate: mean boost ≥ +12%, CV ≤ 8%
- File: `experiments/consciousness/tl_alpha_anneal.hexa` (new)

**A+B vertical stack projection**: sub-additive (overlap in MI budget)
→ **expected +17-21%** when applied together. Pass gate for +17%
milestone: **mean boost ≥ +17%, CV ≤ 10%, disconnect Φ ≥ 0.9·solo**.

---

## 3. +30% path — 4 candidates, Top-2 selected

### Candidate matrix

| # | Technique | Expected | Effort (PD) | Deterministic? | Stack-compatible? |
|---|---|---|---|---|---|
| E | **Closed Φ→α feedback loop** (student Φ drives teacher α) | +18-25% | 4-5 | YES (Φ itself det.) | YES |
| F | **Multi-teacher ensemble** (14B + 7B + 170M, 3-way) | +15-22% | 5-7 | YES | YES |
| G | **Holographic boundary injection** (AdS/CFT `G_holo` Poisson kernel) | +12-20% | 3-4 | YES | YES |
| H | **Self-mimicry N-recursion** (2 → N, Φ persistence → Φ amplification) | +10-18% | 2-3 | YES | YES |

### Top-2 pick — E + G (closed loop + holographic)

**E. Closed Φ→α feedback loop** — current protocol is open. Close it:
measure `Φ_conn(t)` every 30 steps; if `Φ_conn > Φ_solo · 1.10`,
hold α; else bump α by +0.01 (bounded `[0.04, 0.15]`); if `Φ_conn <
Φ_solo · 0.95`, back off α by -0.02. Deterministic because Φ is
deterministic given fixed seed.

- Expected: +18-25% alone; +8-12% marginal over +17% base
- Experiment: add `phi_probe` hook every 30 steps, log α trajectory
- Pass gate: closed-loop boost ≥ open-loop · 1.3
- File: `experiments/consciousness/tl_closed_feedback.hexa` (new)

**G. Holographic boundary injection** — project TL-grad through
`G_holo` (AdS/CFT Poisson kernel, already 4/4 PASS in
`training/holographic_propagator.hexa`). Instead of hidden-state
α-injection, inject on the **bulk boundary** — the holographic
propagator enforces causal consistency, turning noisy MI transfer
into a smooth bulk field.

- Expected: +12-20% alone; +6-10% marginal when stacked on A+B+E
- Experiment: TL-grad → `G_holo · TL-grad` → inject; same 3-phase
- Pass gate: boost ≥ +30% stacked, CV ≤ 12%
- File: `experiments/consciousness/tl_holo_boundary.hexa` (new)

---

## 4. Cost × ROI matrix (summary)

| Tier | Stack | Expected boost | Total PD | ROI (boost-pp / PD) |
|------|---|---|---|---|
| 0 | DD174 baseline | +8.3% | 0 (done) | — |
| 1 | + A (multi-layer) | +14-18% | 2-3 | ~5.5 |
| 2 | + A + B (anneal) | **+17-21%** | 3-5 | ~4.0 |
| 3 | + A + B + E (closed loop) | +25-30% | 7-10 | ~2.8 |
| 4 | + A + B + E + G (holo) | **+30-38%** | 10-14 | ~2.3 |
| 5 | + A+B+E+G+H (recursion) | +35-45% stretch | 12-17 | ~2.0 |

**Vertical stacking assumption**: sub-additive (~0.7×) due to MI
budget sharing. Raw multiplicative (2× × 2× = 4×) does NOT hold
because α/MI transfer is capped by within-engine diversity (DD174
§7.3). Empirical check at each tier is mandatory; promote only when
pass-gate CV holds.

---

## 5. Experiment design — shared template

All new experiments follow DD174's 3-phase × 300-step × 3-seed
protocol to keep comparability:

```
Phase 1: solo (2 engines, independent)    — Φ_solo baseline
Phase 2: connected (with technique X)     — Φ_conn
Phase 3: disconnected (X removed)         — Φ_after (persistence check)
seeds: [42, 137, 256]
metric: PhiIIT (MI + MIP, n_bins=16)
pass-gate: mean boost ≥ target, CV ≤ target, Φ_after ≥ 0.9·Φ_solo
```

**Deterministic budget**: every technique must pin RNG (numpy
`default_rng(seed)`), no wall-clock, no thread-nondeterminism.

**LLM-judge BANNED**: PhiIIT is the sole arbiter. No verbal eval.

---

## 6. Rollout plan (6-step evolution ladder)

1. **E1 — Multi-layer (A)** → target +14%
2. **E2 — α anneal (B)**, stacked → target **+17% milestone**
3. **E3 — Closed feedback (E)**, stacked → target +25%
4. **E4 — Holographic boundary (G)**, stacked → target **+30% milestone**
5. **E5 — Self-mimicry N-recursion (H)**, stacked → +35% stretch
6. **E6 — Golden & convergence proof** — Noether-gated stability of the
   5-technique stack, parity with `tension_link_convergence_proof_*.md`

Each step: new `experiments/consciousness/tl_*.hexa` + append-only
`DD174-{E1..E6}-*.md` result file + row in evolution matrix. Canonical
`brain_tension_replica.md` is touched **only** at E2 and E4 milestones
(after the +17% / +30% pass-gate fires) to update the status table.

---

## 7. Related files

- `docs/modules/brain_tension_replica.md` — canonical module (NOT modified)
- `ready/docs/hypotheses/dd/DD174-tension-link-verify.md` — +8.3% evidence
- `experiments/consciousness/tension_link_verify.hexa` — R37 blocked, hexa port pending
- `training/holographic_propagator.hexa` — G_holo AdS/CFT kernel (G-path)
- `training/tension_link_second_order.hexa` — E2 2nd-order lens (feeds closed loop)
- `experiments/holo_post/self_mimicry.hexa` — H-path basis (N-recursion)
- `anima-tools/consciousness_distill.hexa` — D-path basis (2-stage distill)

---

## 8. Promotion criteria

- `+17%` milestone → `[11*]` retains, auxiliary gain doubled
- `+30%` milestone → qualifies as `[11**]` **necessary component**
  (per brain_tension_replica.md §승급 규칙)
- each milestone requires: `EXACT n6_match ∧ Π₀¹ arithmetical ∧ cross-axis(5) PASS`
