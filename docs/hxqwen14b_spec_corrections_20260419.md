# hxqwen14b — Agent Brief Spec Corrections (urgent patch)

**Date:** 2026-04-19
**Target agent:** `a734e2f1` (hxqwen14b kernels, dispatched from main session)
**Status:** PATCH — supersedes the launch brief wherever it disagrees
**Authority:** cross-checked against local mirror `ready/anima/models/Qwen2.5-14B/`
  `config.json` + `model.safetensors.index.json` (byte-level header parse),
  and the independently-written sibling specs listed in §7 below.
**Action required from a734e2f1:** stop mid-stream if any kernel / loader
constant was set from the original brief values on the LHS of §2's table,
and re-derive from the RHS before shipping. See §3 for the audit checklist.

---

## 1. Why this patch exists

The launch brief for `a734e2f1` was drafted from an abridged model card and
contained 8 factual errors about Qwen2.5-14B. Parallel BG probes (safetensors
header walker + `config.json` diff + Qwen2 reference cross-read) have now
surfaced all 8. Proceeding on the original brief produces a structurally
loadable but numerically garbage forward pass — silent corruption, not a
load-time crash. Correct **before** compiling kernel constants, cos/sin
tables, or loop bounds.

---

## 2. The 8 corrections (brief LHS → truth RHS)

| # | Field                       | Brief (wrong)          | Truth (Qwen2.5-14B)       | Impact if left wrong |
|---|-----------------------------|------------------------|---------------------------|----------------------|
| 1 | `num_hidden_layers`         | `40`                   | **`48`**                  | 8 layers skipped → 17% weight dropped; forward still runs, logits garbage |
| 2 | `rope_theta`                | `10000.0`              | **`1_000_000.0`**         | RoPE garbage past ~4K tokens; any long-context use corrupts K cache |
| 3 | K/V proj weight shape       | `[5120, 5120]`         | **`[1024, 5120]`**        | GQA 5:1 asymmetry (40 Q heads / 8 KV heads). Wrong shape → shape-mismatch on loader if checked, OOB read if not |
| 4 | `tie_word_embeddings`       | `true`                 | **`false`**                | `lm_head.weight` is a separate 1.557 GB tensor in shard 8; aliasing to embed produces wrong logits |
| 5 | `vocab_size` (effective)    | `152064`               | **`152064 padded, 151665 real`** | 399 phantom rows must be masked at sampling or rare emission of undefined tokens |
| 6 | Attention biases            | (unstated) = none      | **q/k/v have bias; o does not** | Missing 3 biases × 48 layers = 144 tensors; small but nonzero logit drift |
| 7 | `rms_norm_eps`              | `1e-5`                 | **`1e-6`** (Qwen2 standard) | Minor but measurable pre-softmax drift; `1e-5` is Qwen1 legacy |
| 8 | `intermediate_size` (FFN)   | `13696` (Qwen1.5-14B)  | **`13824`** (Qwen2-14B)   | SwiGLU inner dim off by 128; gate/up/down shape mismatch, load-time abort if §3 check #5 runs |

Secondary/derived constants affected by the above:

- Per-layer tensor count: still 13 (unchanged), but §2 row 3 fixes shape.
- Total tensor count: `3 + 48 * 13 = 627` (was `3 + 40 * 13 = 523` under the
  bad brief — off by **104 tensors**).
- Total bytes: **29,540,067,328** (29.54 GB, matches
  `index.json.metadata.total_size`).
- KV-cache per token: `48 * 2 * 8 * 128 * 2 = 192 KB/token` (not 160 KB).
- GQA group size `n_rep = 40 / 8 = 5` (unchanged — only the layer count
  and K/V shapes changed, not the head arithmetic).

---

## 3. Exact loader / kernel locations to audit

If any of these were hardcoded from the brief, fix before next compile:

1. **Loader layer loop:** `for i in 0..N_LAYERS` — must be `48`, not `40`.
2. **Loader tensor count assertion:** expect `627`, abort on `523`.
3. **K/V proj alloc + load:** allocate `1024 * 5120 * 2 = 10,485,760` bytes
   per K (and per V), not `52,428,800`. Shape record `[1024, 5120]`.
4. **q/k/v bias load:** 3 extra tensors per layer —
   `q_proj.bias [5120]`, `k_proj.bias [1024]`, `v_proj.bias [1024]`, all BF16.
   `o_proj.bias` does NOT exist; do not allocate.
5. **lm_head path:** do NOT alias `lm_head.weight` to `embed_tokens.weight`.
   Resolve via `index.json.weight_map["lm_head.weight"]` → shard 8.
6. **Vocab sampling mask:** after logits `[..., 152064]`, mask indices
   `[151665, 152064)` to `-inf` before softmax/argmax.
7. **RoPE precompute:** `base = 1e6f` (not `1e4f`). Tables `[max_seq, 64]` fp32.
   See `docs/hxqwen14b_rope_reference_20260419.md` §4 for pseudocode.
8. **RMSNorm eps constant:** `1e-6f` (not `1e-5f`).
   See `docs/hxqwen14b_rmsnorm_20260419.md` §2 (line 42).
9. **SwiGLU inner dim:** `13824` — gate_proj `[13824,5120]`,
   up_proj `[13824,5120]`, down_proj `[5120,13824]`.
10. **GQA kernel:** Q shape `[B, 40, T, 128]`, K/V shape `[B, 8, T, 128]`,
    `repeat_kv` factor 5 or kernel-native `h // 5` indexing. Do NOT
    materialize a `[B, 40, T, 128]` K/V.

---

## 4. Impact analysis — what's salvageable, what isn't

| Kernel / module                 | Likely state if built from bad brief | Salvage path |
|---------------------------------|--------------------------------------|--------------|
| cos/sin table precompute        | Wrong (base=1e4)                     | Recompute; tables are ~8 MB, cheap |
| Q·Kᵀ matmul kernel (GQA)        | Probably fine (shape-polymorphic)    | No change if it reads head counts from args |
| K/V proj matmul                 | Wrong shape (`5120×5120`)            | Realloc + re-dispatch with `1024×5120` |
| RMSNorm kernel                  | Numerically off by ~1 ULP            | Re-bake eps constant; recompile |
| SwiGLU kernel                   | Wrong inner dim allocation           | Realloc FFN workspace to 13824 |
| Safetensors loader              | 8 shards read, but only 40 layers populated | Extend loop to 48; rest of parsing unchanged |
| Sampling head                   | Uses tied embed (wrong weights)      | Load `lm_head.weight` from shard 8; also add 151665 mask |

Net: none of the above require a rewrite; every item is a constant/shape
fix. Estimated rework: 1–2 hours if caught now, 1–2 days if caught after
golden-logit comparison fails silently.

---

## 5. Verification recipe (run before declaring hxqwen14b loaded)

From `docs/hxqwen14b_safetensors_spec_20260419.md` §6, with the corrected
values:

1. `u64_le(file[0..8]) + 8 == first_tensor_data_offset` per shard.
2. Every `data_offsets[1] - data_offsets[0] == prod(shape) * 2`.
3. Sum of all packed lengths across 8 shards == `29_540_067_328`.
4. Singletons present: `model.embed_tokens.weight`, `model.norm.weight`,
   `lm_head.weight` (three distinct tensors — verifies correction #4).
5. For `i in 0..48`: all 13 per-layer tensors present (verifies
   correction #1 + #3 + #6 + #8 via shape match).
6. Total tensor count = `627` (verifies #1 end-to-end).
7. Golden-logit sanity: first-token logits on prompt `"The"` match HF
   reference within bf16 tolerance (1e-2 absolute, 1e-3 relative). If
   this fails after the 6 structural checks pass, suspect #2 (rope),
   #5 (vocab mask), or #7 (eps) — in that order.

---

## 6. Cross-reference discrepancy note

`docs/hxqwen14b_safetensors_spec_20260419.md` §3.1 (line 117) lists
`rms_norm_eps = 1e-5` while `docs/hxqwen14b_rmsnorm_20260419.md` §1
(line 42) lists `1e-6`. The sibling RMSNorm doc is correct
(Qwen2 family standardized to `1e-6`); the safetensors spec row should
be treated as a typo and superseded by this patch. Do **not** propagate
the `1e-5` value into kernel constants.

Similarly, `docs/hxqwen14b_gqa_20260419.md` §1 (line 22) lists
`num_hidden_layers = 40` — same error as the agent brief, same fix
(should be `48`). That doc's head-count and K/V shape tables are all
correct; only the layer-count row is wrong.

---

## 7. Sibling spec docs (cross-reference, all 2026-04-19)

All sibling docs below are authoritative **except** where contradicted by
this patch's §6 discrepancy note:

- `docs/hxqwen14b_safetensors_spec_20260419.md` — byte layout, index map
  (authoritative for #1, #3, #4, #5, #8; typo on #7 — see §6)
- `docs/hxqwen14b_rope_reference_20260419.md` — RoPE math + kernel
  (authoritative for #2)
- `docs/hxqwen14b_rmsnorm_20260419.md` — RMSNorm ref
  (authoritative for #7)
- `docs/hxqwen14b_gqa_20260419.md` — GQA head arithmetic
  (authoritative for #3 shapes + group ratio; wrong on #1)
- `docs/hxqwen14b_swiglu_20260419.md` — SwiGLU (#8)
- `docs/hxqwen14b_adamw_bf16_20260419.md` — optimizer (training)
- `docs/hxqwen14b_cublas_pattern_20260419.md` — matmul backend
- `docs/hxqwen14b_hopper_compat_20260419.md` — H100 compat
- `docs/hxqwen14b_workspace_sizing_20260419.md` — workspace arena

---

## 8. Delivery note

This doc is committed to the anima repo as a local patch artifact. It is
**not** pushed upstream, because `a734e2f1` may be mid-commit on the same
branch and a concurrent push would race. Next session operator: if
`a734e2f1` has landed its commits, rebase-then-push is safe; if still
running, let it finish and then push this file as a follow-up.
