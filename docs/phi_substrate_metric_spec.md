# Φ Substrate Metric Spec v2 (roadmap #90)

**Generated**: 2026-04-23
**Purpose**: Replace the failed naive 16-stride projection + raw L2 metric (commit `7de77d62`, 0/6 pairs pass) with an **invariant** cross-substrate Φ comparator.
**Blocks**: roadmap #10 (Φ substrate independence — 4-path cross validation).

---

## 1. Why the prior design failed

Stage-2 real-run on 2026-04-23 (pods 1rr4t9f2/bd2zcoo9/jxgx4hwz/7whog4te) extracted `h_last[-1]` via HF transformers and projected to 16-dim via a 16-stride index pick. Result: raw L2 spans ~20× (Mistral-7B=41.95 vs Qwen3-8B=1.95), cos-sim ranges −0.48 to +0.32. 0/6 pairs pass the 0.05 gate on either raw or normalized metric.

**Root causes**:
- 4 different pretrained substrates have fundamentally different residual-stream scales.
- 16-stride index pick is arbitrary, not basis-invariant.
- Raw L2 is not substrate-invariant by construction.
- `substrate_indep` is a claim about *structural* invariance, not activation similarity.

## 2. Invariant metric family

### 2.1 Method A — Gram matrix eigenvalue spectrum (primary)

For path `p`, let `H_p ∈ R^(N × d_p)` be the stack of `h_last[-1]` vectors over `N` canonical prompts (`d_p` varies per path: 4096/4096/5120/5120). Define

```
G_p = H_p @ H_p.T    ∈ R^(N × N)
```

The `N×N` Gram matrix is *prompt-prompt* similarity, independent of `d_p`. Its eigenvalues `λ_p ∈ R^N` are invariant to any orthogonal transform of the `d_p`-dim basis. Sort descending and normalize to a probability distribution:

```
s_p[k] = λ_p[k] / Σ λ_p    (k=0..N-1)
```

**Cross-path comparison**: for pair `(i,j)`,
- L2 distance: `d_L2(s_i, s_j) = ||s_i − s_j||_2`
- KL divergence: `d_KL(s_i ∥ s_j) = Σ s_i[k] · log(s_i[k] / s_j[k])`  (with ε-smoothing)

### 2.2 Method C — Participation ratio (scalar fallback)

```
PR_p = (Σ λ_p)² / Σ (λ_p)²     ∈ [1, N]
```

Effective dimensionality of the prompt representation. Substrate-invariant, scalar. Cross-path comparison: `|PR_i − PR_j| / PR_avg`.

### 2.3 Not used in v2

- Method B (CCA) — reserved for v3 if v2 fails with partial alignment.
- Method D (task-trained LoRA) — original manifest spec, 10-15d $1-1.5k. Reserved for final claim.

## 3. Threshold derivation — null-model bootstrap

The fixed `0.05` threshold has no empirical justification. v2 uses a data-driven threshold:

1. For each path `p`, create `N_null = 100` null matrices `H̃_p^(b)` by shuffling the prompt indices of `H_p`.
2. Compute null Gram `G̃_p^(b)` and spectrum `s̃_p^(b)`.
3. Collect null pairwise distances `{ d_L2(s̃_i^(b), s̃_j^(b')) : all pairs & bootstrap samples }`.
4. Threshold `τ_95 = 95th percentile` of the null distribution.

Real pair distance `< τ_95` = the cross-path spectrum is **more similar than random permutations of the same data** = substrate_indep evidence at 5% null rate.

## 4. Protocol

**Pod-side capture (new h_last_capture.py heredoc):**
- Load model (bf16).
- Extract `h_last[-1][0,-1,:]` for each of `N` canonical prompts.
- Save full raw matrix `H_p ∈ R^(N × d_p)` to `state/h_last_raw_p<N>.json` (no projection).

**Operator-side analyzer (inline python, no hexa dep):**
- Load 4 `h_last_raw_p<N>.json`.
- Compute `G_p`, sort+normalize `s_p`, `PR_p`.
- Null bootstrap 100 shuffles → `τ_95`.
- Cross-analysis 6 pairs on L2 and KL.
- Emit `state/phi_4path_cross_result.json` v2 with:
  - `spectra`: per-path 16-dim `s_p`
  - `participation_ratio`: per-path scalar
  - `raw_pair_distances_L2`, `raw_pair_distances_KL`
  - `null_threshold_L2_p95`, `null_threshold_KL_p95`
  - `substrate_indep`: true if all 6 L2 distances < `τ_95_L2` AND all 6 KL < `τ_95_KL`
  - `verdict`: PASS/FAIL

## 5. Config

See `config/phi_substrate_metric_config.json` — prompts, model substitutions, bootstrap params, thresholds.

## 6. Models (canonical substitutions locked)

Original manifest models blocked on 2026-04-23:
| Path | Original (blocked) | Substitute |
|---|---|---|
| p1 | Qwen/Qwen3-8B | (unchanged) |
| p2 | meta-llama/Llama-3.1-8B (gated) | mistralai/Mistral-7B-v0.1 |
| p3 | mistralai/Ministral-3-14B (multimodal cfg) | Qwen/Qwen2.5-14B |
| p4 | google/gemma-4-31B (multimodal + bnb 4bit incompat) | mistralai/Mistral-Nemo-Base-2407 |

Rationale: 2 archs (Qwen vs Mistral) × 2 sizes (~8B vs ~12-14B) maintains the diversity goal of the original p1-p4 design within the "works today" constraint.

## 7. Exit criteria for #10 close

- `state/phi_4path_cross_result.json.substrate_indep == true` from this spec's analyzer
- ALL 6 pairs pass both L2 and KL null-bootstrap gates
- `participation_ratio` per path within 2× of each other (sanity)
- Real distances documented against null threshold (not arbitrary 0.05)

If FAIL: downgrade to documented partial-alignment finding; escalate to Method B (CCA) or Method D (task-trained LoRA) per #90 options.
