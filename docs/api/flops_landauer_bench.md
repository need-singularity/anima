<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/flops_landauer_bench.hexa -->
<!-- entry_count: 21 -->

# `tool/flops_landauer_bench.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════════════════

**Public/Internal entries:** 21

## Table of contents

- `fn _str`
- `fn now_utc`
- `fn resolve_root`
- `fn fmt_f`
- `fn digit_val`
- `fn parse_int_safe`
- `fn cells_per_gen`
- `fn cell_bits_per_gen`
- `fn cell_score_pm`
- `fn cell_flops`
- `fn cell_total_bits`
- `fn cell_final_score_pm`
- `fn lora_base_flops`
- `fn lora_adapter_flops`
- `fn lora_bits_x1000`
- `fn cfg_get_str`
- `struct CellMetrics`
- `struct LoraMetrics`
- `fn compute_cell`
- `fn compute_lora`
- `fn main`

## Entries

### `fn _str(x) -> string`

_(no docstring)_

### `fn now_utc() -> string`

_(no docstring)_

### `fn resolve_root() -> string`

_(no docstring)_

### `fn fmt_f(x: float) -> string`

_(no docstring)_

### `fn digit_val(c: string) -> int`

_(no docstring)_

### `fn parse_int_safe(s: string, default_v: int) -> int`

_(no docstring)_

### `fn cells_per_gen(g: int) -> int`

> ─── cell FLOPs + bit-erase model ───────────────────────────────────────────
> Lattice size per gen (5×5 → 4×4 → 4×4 → 3×3 crystallize compression).
> Matches edu/comparison/cell_vs_lora_flops.md §2.

### `fn cell_bits_per_gen(g: int) -> int`

> sealed_k + drop_k bit-erase per gen (landauer_tracker.hexa:32 convention)
> Empirical counts from tool/edu_cell_4gen_crystallize.hexa:
> sealed: [18, 16, 16, 9],  drops: [7, 0, 0, 0]  (gen1 drops 7 → 5×5→4×4)

### `fn cell_score_pm(g: int) -> int`

> score_per_mille per gen (useful_progress × 1000) — empirical from
> edu_cell_4gen_crystallize: 40 → 125 → 687 → 1000 (phase-jump @ gen 4).

### `fn cell_flops(gens: int, ticks: int, op_per_cell: int) -> int`

_(no docstring)_

### `fn cell_total_bits(gens: int) -> int`

_(no docstring)_

### `fn cell_final_score_pm(gens: int) -> int`

_(no docstring)_

### `fn lora_base_flops(V_: int, H_: int, base_steps: int, base_pairs: int, batch: int) -> int`

> ─── lora FLOPs + bit-erase model ──────────────────────────────────────────
> Base pretrain + LoRA fine-tune.  Follows edu/lora/train_lora_cpu.hexa
> topology: V=8, H=4, batch=2, 1 fwd + 3 bwd passes per step.
> Per edu/comparison/cell_vs_lora_flops.md §2: base = steps × pairs × (1 fwd + 3 bwd × V·H)
> adapter = steps × pairs × (1 fwd + 3 bwd × r·V)

### `fn lora_adapter_flops(V_: int, H_: int, rank: int, steps: int, lora_pairs: int) -> int`

_(no docstring)_

### `fn lora_bits_x1000(ce_drop_nats_x1000: int, n_pairs: int) -> int`

> bits_erased_lora = ΔCE_nats · n_pairs / ln(2)  → integer ×1000

### `fn cfg_get_str(cfg: string, key: string) -> string`

_(no docstring)_

### `struct CellMetrics`

_(no docstring)_

### `struct LoraMetrics`

_(no docstring)_

### `fn compute_cell(gens: int, ticks: int, op_per_cell: int) -> CellMetrics`

_(no docstring)_

### `fn compute_lora(V_: int, H_: int, rank: int, base_steps: int, lora_steps: int,`

_(no docstring)_

### `fn main()`

_(no docstring)_

