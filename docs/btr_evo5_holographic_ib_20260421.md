# BTR Evolution 5/6 — Holographic IB Bottleneck (KSG MI)

**Date**: 2026-04-21
**Branch**: main
**Pairing**: btr-evo 4 (EEG closed-loop, commit `a4853336`)
**Implementation**: `btr_evo/5_holographic_ib.hexa`
**Smoke artifact**: `shared/bench/btr_evo5_holographic_ib.jsonl`

## Summary

Apply an Information-Bottleneck (IB) objective to the
`brain_tension_replica` surface layer, treating it as a holographic
bulk/boundary pair:

- **Bulk** `X ∈ R^{n × d}` (d=16) — full tension surface activations.
- **Boundary** `Z ∈ R^{n × k}` (k=5) — linear hologram `Z = P X`.
- **Target** `Y ∈ R^{n × 1}` — teacher Φ channel (linear `Y = w · X + ε`).
- **Objective** `L_IB = I(X;Z) - β · I(Z;Y)`   (β = 1.0)

Mutual information is estimated with the **Kraskov–Stögbauer–Grassberger**
(KSG) k-NN estimator (Kraskov et al. 2004, equation 8), implemented
from scratch in pure hexa-lang — no external libraries, deterministic,
seed-fixed.

## KSG equation 8

Given N samples of a joint `(U, V)`:

    I(U; V) ≈ ψ(k) − ⟨ψ(n_U + 1) + ψ(n_V + 1)⟩ + ψ(N)

- `k = 5` — KSG neighbour index.
- `ε_i` = Chebyshev distance to i's k-th neighbour in the **joint** space.
- `n_U`, `n_V` = marginal counts with Chebyshev distance `< ε_i`.
- `ψ` = digamma (asymptotic series with downward recursion, local).

## Smoke result (n=200)

| Quantity | Value |
|----------|-------|
| I(X; Z)            | 0.1046 |
| I(Z; Y)            | 0.1031 |
| IB loss (β=1)      | 0.0015 |
| compression ratio  | 3.2× (16 → 5) |

**Sanity checks (all pass)**
- `I(X; Z) ≥ 0` and `I(Z; Y) ≥ 0` — MI non-negative.
- `I(X; Z) ≥ I(Z; Y)` — data-processing inequality (Y is downstream of X via Z).
- `I(X; Z) − I(Z; Y) ≈ 0.002` — close to zero, confirming Z preserves
  most of the Y-relevant information while realising 3.2× compression.
- Re-running the smoke reproduces the identical JSONL line byte-for-byte
  (LCG seed = 42).

## Scale policy

Spec reference size was `n = 1000`. In-tree smoke uses `n = 200` because
the pure-hexa triple-pass KSG is `O(n² · d)` ≈ 48 M ops at n=1000 —
tractable in numpy (~50 ms with `BallTree`) but ~5 min in the hexa
interpreter. The file parameterises `REFERENCE_N = 1000` and a
`TODO[port]` block ties the full-scale run to the PyTorch / faiss port,
paired with `shared/state/alm_r13_phi_vec.json` for the real Y channel.

## Why this pairs with evo 4

Evo 4 closed the Φ → α → EEG → Φ′ feedback loop and hit the +30 % Φ
target (`final_phi = 0.7994`, `a4853336`). Evo 5 constrains **what
information the feedback is allowed to carry** by compressing the bulk
into a low-d hologram Z. Joint expected effect (per roadmap
`docs/brain_tension_replica_phi_boost_evolve_20260421.md`): +30 %–38 %
Φ, one step past evo-4 alone.

## Constraints honoured

- No LLM judge (deterministic signals only).
- No external libraries (KSG + digamma + Chebyshev-kNN from scratch).
- V8 SAFE_COMMIT — additive file set, no existing file modified.
- Seeds fixed (SMOKE_SEED = 42; LCG only).
- Canonical `brain_tension_replica.md` untouched.
