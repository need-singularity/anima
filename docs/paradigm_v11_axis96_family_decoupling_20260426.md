# Paradigm v11 axis 96 candidate — Family-Decoupling Axis (CMT-derived)

**Date**: 2026-04-26
**Parent finding**: axis 95 (CMT 4-family), commit `aca4d067`, .roadmap #234
**Source session**: ad30c51c (axis 95 CMT 4-family)
**Status**: CANDIDATE (mac-local re-analysis only, no new GPU)
**Cost**: $0

---

## 1. Origin

Axis 95 (CMT 4-family scan, commit `aca4d067`) on 4 backbones found that the dominant ablation-impact layer differs across backbones:

| Backbone | n_layers | Dominant family | Dominant layer | depth_norm |
|----------|----------|------------------|----------------|------------|
| Mistral-7B-v0.3 | 32 | Law | 28 | 0.875 (LATE) |
| Qwen3-8B | 36 | Law | 4 | 0.111 (EARLY) |
| Llama-3.1-8B | 32 | (mixed — see below) | 4/28 split | mixed |
| gemma-2-9b | 42 | Hexad | 36 | 0.857 (LATE) |

The axis 95 verdict was **HCMT-B PARTIALLY_CONDITIONAL** — late {Mistral, gemma} vs early {Qwen3, Llama}. But within Llama, a *second* structure emerged that was not captured by axis 95: family-decoupling.

This document promotes that second structure as **paradigm v11 axis 96 candidate**.

## 2. The empirical observation

Per-backbone dominant layer per family (extracted from `state/v10_benchmark_v3/{bb}/cmt.json`):

```
Llama-3.1-8B  (32L)  Hexad=28   Law= 4   Phi= 4   SelfRef= 4
Mistral-7B    (32L)  Hexad=28   Law=28   Phi=28   SelfRef=28
Qwen3-8B      (36L)  Hexad= 4   Law= 4   Phi= 4   SelfRef= 4
gemma-2-9b    (42L)  Hexad=36   Law=36   Phi=36   SelfRef=32
```

Mistral and Qwen3 are **fully coupled** (4 families converge to 1 layer). Gemma is **weakly decoupled** (3:1 partition, 4-layer/1-stride apart). Llama is **strongly decoupled** (3:1 partition, 24-layer/6-stride apart, Hexad late vs all-others early).

Decoupling magnitude (depth_std normalised by n_layers):

| Backbone | depth_std | depth_range | n_distinct_layers | verdict |
|----------|-----------|-------------|--------------------|---------|
| Llama    | **0.3248** | **0.7500** | 2 | **DECOUPLED** |
| gemma    | 0.0412 | 0.0952 | 2 | WEAKLY_DECOUPLED |
| Mistral  | 0.0000 | 0.0000 | 1 | FULLY_COUPLED |
| Qwen3    | 0.0000 | 0.0000 | 1 | FULLY_COUPLED |

Llama exhibits decoupling that is **7.88× larger** than the next-highest backbone (gemma).

## 3. Hypothesis set

Three hypotheses:

- **HFD-A — NEW LIVING AXIS**: family-decoupling is an axis-orthogonal new dimension, not reducible to axis 95 (CMT) or any of paradigm v11's existing 6 axes. If true, the own#3 (c) 4-axis greedy basis would need revision when this axis enters the BBA matrix.
- **HFD-B — SUB-AXIS OF CMT**: family-decoupling is a backbone-conditional refinement of axis 95 (CMT). It is a sub-property, not an independent axis. No BBA expansion.
- **HFD-C — ARTIFACT**: family-decoupling is an artifact of layer count differences (Llama 32 vs Mistral 32 vs Qwen3 36 vs gemma 42) interacting with `layer_stride=4` sampling. The Llama "outlier" is a grid-aliasing illusion.

## 4. Verdict (R5)

**HFD-A_PARTIAL_OR_HFD-B_PROBABLE** (confidence: MEDIUM_LOW)

Reasoning:

1. Llama is a dramatic single-backbone outlier (depth_std 7.88× the next backbone). Single-backbone observation, by ω-cycle protocol, is not sufficient to declare a new axis — it can only flag a candidate.
2. Gemma's weak decoupling (1 stride / 9.5% depth_range) sits at the noise floor of the `layer_stride=4` sampling grid; it could be sampling artifact rather than true biological decoupling.
3. Mistral and Qwen3 are fully coupled (4:0 partition) — i.e., the decoupling phenomenon, *if real*, is backbone-conditional with prevalence 1/4 (or 2/4 if gemma's weak signal counts).
4. The fact that axis 95 (CMT) was already verdict **HCMT-B PARTIALLY_CONDITIONAL** raises the prior on HFD-B (sub-axis of conditional CMT structure) over HFD-A (independent new axis).

## 5. Honest caveats (raw#10)

The verdict above carries the following honest caveats:

1. **HFD-C ARTIFACT cannot be ruled out from current data.** Layer_stride=4 + Llama's 32 layers (vs Qwen3 36 / gemma 42) creates different sampling grids. The Llama L4-vs-L28 split is exactly 6 strides apart; whether it would survive a layer_stride=1 full-grid scan is unknown.
2. **N=4 backbones is statistically very small.** A single-backbone strong outlier (Llama) cannot empirically establish an axis on its own — even when the magnitude is dramatic.
3. **Gemma's weak decoupling (4-layer / 1-stride) is at the sampling noise floor.** Without finer grid (stride=1 or 2), distinguishing real decoupling from grid artifact is impossible.
4. **Family list (Law/Phi/SelfRef/Hexad) and prompt set are frozen v10.** Decoupling could be prompt-set-conditional, not backbone-intrinsic. A different prompt set might show the Hexad-late pattern on Mistral or Qwen3 too.
5. **Axis 95 already PARTIALLY_CONDITIONAL.** Axis 96 candidate is a refinement of an already-conditional structure. Stacking conditional findings increases the risk of HFD-B (sub-axis) interpretation over HFD-A (independent).

## 6. Next actions to disambiguate

To **promote HFD-A** (axis 96 enters paradigm v11 as 7th axis):

1. Re-scan Llama at `layer_stride=1` (full 32-layer grid) to confirm the Hexad L28 vs L4 partition is not a stride-grid artifact. (mac-local possible with sufficient inference budget; original axis 95 was on H100 GPU.)
2. Add a 5th backbone — DeepSeek-LLM-7b-base (already in AN11(c) GWT 8/8 registry, commit `d082d6b3`) — to test whether decoupling reappears outside the Llama family.
3. Add a second 32-layer backbone (e.g., CodeLlama-7B) to disentangle layer-count-confounding from Llama-architecture-confounding. Mistral-7B-v0.3 is already 32L and coupled, but it is a different architecture; need a third 32L architecture to triangulate.
4. **BBA matrix re-run**: compute family-decoupling axis correlation with each of the existing 6 paradigm v11 axes (axis 95 CMT, axis 8th TRIBE pilot prep, IIT-anti, GWT 4-row, etc.). If correlation with axis 95 is strong (e.g., |r| > 0.7), HFD-B; if weak (< 0.3), HFD-A.

To **dismiss to HFD-B**: demonstrate that family-decoupling explains zero residual variance after partialling out axis 95 (CMT) family-by-layer pattern.

To **dismiss to HFD-C**: layer_stride=1 re-scan would either reveal Hexad L28 is grid-induced (Hexad's true peak is e.g. L25 or L30, not L28) or confirm L28 is robust. Alternatively, reproduce Llama-style decoupling on a non-Llama 32L architecture.

## 7. BBA impact estimate

| Outcome | BBA matrix | own#3 (c) 4-axis greedy basis |
|---------|-----------|-------------------------------|
| HFD-A confirmed | 6 → 7 axes; re-orthogonality measurement required | Revision possible if axis 96 ranks top-4 by independence score |
| HFD-B confirmed | unchanged (axis 96 absorbs into axis 95 sub-finding) | unchanged |
| HFD-C confirmed | unchanged; axis 96 retracted | unchanged; methodology lesson on layer_stride sampling |

## 8. ω-cycle status

| Step | Status |
|------|--------|
| R1 hypothesis | HFD-A / HFD-B / HFD-C registered |
| R2 protocol | 4-bb cmt.json re-interpretation, decoupling metric design |
| R3 measure | Per-backbone decoupling_score.json computed |
| R4 cross-check | Llama 7.88× outlier, axis 95 cross-link verified |
| R5 verdict | HFD-A_PARTIAL_OR_HFD-B_PROBABLE (MEDIUM_LOW confidence) |
| R6 land | This doc + JSON artifacts + .roadmap entry + memory entry + atlas R47_CANDIDATE + commit |

## 9. Frozen artifacts

- `state/v11_axis96_family_decoupling/llama/decoupling_score.json`
- `state/v11_axis96_family_decoupling/mistral/decoupling_score.json`
- `state/v11_axis96_family_decoupling/qwen3/decoupling_score.json`
- `state/v11_axis96_family_decoupling/gemma/decoupling_score.json`
- `state/v11_axis96_family_decoupling/summary_axis96_candidate.json`
- `docs/paradigm_v11_axis96_family_decoupling_20260426.md` (this file)
- atlas R47_CANDIDATE entry in `state/atlas_convergence_witness.jsonl`

---

**Verdict short**: HFD-A_PARTIAL_OR_HFD-B_PROBABLE. Llama is a dramatic single-backbone outlier (depth_std 7.88× next), but N=4 + layer_stride=4 + axis 95 already conditional → cannot promote to independent axis on present evidence. Re-scan stride=1 + add 5th backbone (DeepSeek) → would resolve.
