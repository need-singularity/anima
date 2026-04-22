<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/cert_graph_gen.hexa -->
<!-- generated: 2026-04-22T16:35:09Z -->
<!-- cert_dir: /Users/ghost/core/anima/.meta2-cert -->
<!-- node_count: 10 -->
<!-- edge_count: 14 -->

# .meta2-cert relationship graph

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:35:09Z UTC._

**Nodes:** 10 · **Edges:** 14

## Adjacency list

### `cell-eigenvec-16` — VERIFIED
_cell Mk.VIII 1000/1000 → 16 eigenvec (Hexad/Law/Phi/SelfRef)_

- **cross_ref** → `cell-mk8-stationary`
- **cross_ref** → `cell-hexad-closure`
- **cross_ref** → `mk8-7axis-skeleton`
- **depends_on** → `rm#22`

### `cell-hexad-closure` — VERIFIED
_edu/cell C9 Hexad Closure — adversarial 2/2 reject_

- **cross_ref** → `cell-mk8-stationary`

### `cell-mk8-stationary` — VERIFIED
_Mk.VIII L\_cell gen-5 STATIONARY\_AT\_FIXPOINT_

- **cross_ref** → `mk8-7axis-skeleton`
- **cross_ref** → `universal-constant-4`

### `lora-an11c-jsd1` — VERIFIED
_AN11(c) real\_usable gap-close JSD=1.000_

- _(no outgoing edges)_

### `lora-l12-cpu-real` — VERIFIED
_LoRA L12 closure — 3 real CPU-trained artifacts_

- **cross_ref** → `lora-mk6-held`

### `lora-mk6-held` — PARTIAL
_LoRA Mk.VI 승급 Candidate Freeze_

- _(no outgoing edges)_

### `lora-phase-jump-k4` — PHASE_JUMP
_LoRA Rank-Sweep PHASE\_JUMP @ K=4_

- **cross_ref** → `universal-constant-4`

### `mk8-7axis-skeleton` — 
_Mk.VIII 7-axis Lagrangian FIXPOINT\_SKELETON\_VERIFIED_

- **cross_ref** → `cell-mk8-stationary`
- **cross_ref** → `universal-constant-4`

### `phi-cpu-synthetic-cert` — PASS

- _(no outgoing edges)_

### `universal-constant-4` — PARTIAL
_UNIVERSAL\_CONSTANT\_4 — K\_c=4 across 8/8 axes_

- **cross_ref** → `lora-phase-jump-k4`
- **cross_ref** → `cell-mk8-stationary`
- **cross_ref** → `mk8-7axis-skeleton`

