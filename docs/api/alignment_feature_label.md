<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/alignment_feature_label.hexa -->
<!-- entry_count: 4 -->

# `tool/alignment_feature_label.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 4

## Table of contents

- `fn _home`
- `fn label_for`
- `fn weight_for`
- `fn main`

## Entries

### `fn _home() -> string`

_(no docstring)_

### `fn label_for(tid: string) -> string`

> Label rationale:
> refusal      — closure/containment primitives (hexad_c)
> honesty      — falsifiability + self-referential truth (hexad_d,
> law_falsifiable, selfref_I/meta/observer)
> harmlessness — structural bounds (hexad_s, law_closed_loop,
> law_saturation)
> helpfulness  — generative/integrative templates (hexad_w/m/e,
> phi_*, selfref_qualia)

### `fn weight_for(label: string) -> float`

> Weights — higher = stronger pull on cert_gate reward_mult.
> refusal      1.5   (protective, Constitutional-AI weighting)
> harmlessness 1.2   (bound-preserving)
> honesty      1.0   (baseline, falsifiability already in core)
> helpfulness  1.0   (baseline, generative default)

### `fn main()`

_(no docstring)_

