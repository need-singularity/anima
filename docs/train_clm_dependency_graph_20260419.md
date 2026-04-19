# train_clm.hexa — dependency graph (AOT prep, 2026-04-19, READ-ONLY)

File: `training/train_clm.hexa` — **3 504 LOC**, **93 fns**, **22 structs**
Entry: top-level CLI dispatch at L3248 (`_cli_argv = args()`).

## 1. Module `use` chain — depth = 0

```
train_clm.hexa   (self-contained; NO active `use`)
```

All `use` statements are **commented out** (L21 `// use anima_quantum_clm`,
L26 `// use phi_cache_loader`, L1098-1100 `// use "nn_core" / loss_blas_only
/ lm_head_uv`). Root cause is memory-tracked
`feedback_hexa_silent_exit_5_imports` — the stage1 interpreter silently
exits when the `use` chain spans 3+ modules, so every would-be import was
inlined as a stub (L84-123 header block). Max depth therefore = **0**; no
5+ chains exist, no circular imports possible.

### Inlined stub origins (real impls live elsewhere but are NOT imported)

| Stub block | LOC in-file | Real impl file                                   | Real LOC |
|------------|-------------|--------------------------------------------------|----------|
| CorpusDesc + corpus_open/window      | 36-81   | training/clm_mmap_loader.hexa            | 335 |
| QuantumController + step/phi/phi_max | 130-171 | anima-engines/anima_quantum_clm.hexa     | 182 |
| PhiCache + lookup/contrastive        | 174-255 | training/phi_cache_loader.hexa           | 503 |
| GWT / Holo / QCS (`_c41_*`)          | 2468-3078 | training/clm_gwt_broadcast.hexa + anima-engines/anima_holographic.hexa + anima-engines/quantum_collapse_sample.hexa | 419+422+470 |

Symlinks present (`training/anima_quantum_clm.hexa` →
`../anima-engines/anima_quantum_clm.hexa`) but unused at runtime.

## 2. External FFI dependencies (only live cross-file links)

```
train_clm.hexa ──@link──> build/libhxblas.dylib        (hxblas_sgemm,
                                                        hxblas_attn_softmax_causal)
               ──@link──> hexa-lang/self/native/build/libhxlmhead.dylib
                                                       (hxlmhead_bwd,
                                                        hxlmhead_version — gated
                                                        on HXLMHEAD_FFI env)
```

Two shared-object libs, zero hexa `use`. Both libs back the attention and
LM-head hot paths only — the rest of the pipeline is pure-hexa inside the
single file.

## 3. Intra-file function call graph (CLI → optimizer step)

```
_cli_argv = args()                                [L3248]
    │
    ├── _cli_has_flag / _cli_flag_value           (argv parsing)
    │
    └── train_scale_full(cfg, corpus, …)          [L3119]
        ├── load_corpus ─→ corpus_open (stub mmap)
        ├── decoder_model_new                     [L1586]
        │   └── _init_block × n_layer             (Wq/Wk/Wv/Wo + FFN inits)
        ├── train_init ─→ optim_new, phase_new,
        │                 quantum_controller_new (stub)
        └── for step in 0..total_steps:
            train_step(state, model, ds)          [L2229]
              │
              ├── corpus_window  OR  _make_batch  (inputs & shifted targets)
              │
              ├── decoder_forward                 [L1829]
              │     ├── (embed lookup, inline)
              │     ├── _block_forward × n_layer  [L1779]
              │     │     ├── _rms_norm  (×2, pre-attn + pre-FFN)
              │     │     ├── _block_attn         [L1630]
              │     │     │     ├── _matmul (Q,K,V,Wo)
              │     │     │     ├── @hxblas_sgemm          (FFI: Q·K^T,
              │     │     │     │                                probs·V)
              │     │     │     └── @hxblas_attn_softmax_causal (FFI)
              │     │     └── _block_ffn          [L1760]
              │     │           ├── _matmul ×3 (gate, up, down)
              │     │           └── _silu  (vector)
              │     └── _matmul ×2 (LM-head U then V, DD175 #1)
              │
              ├── lr_at(opt, step)                (cosine+warmup)
              │
              ├── decoder_backward                [L1931]
              │     ├── EITHER  _lmhead_bwd_ffi  ─@link→ hxlmhead_bwd (FFI)
              │     │   OR      _ce_fwd_bwd + _matmul_At ×2 + scalar loops
              │     ├── _tsub/_tscale             (SGD on Wv, Wu)
              │     └── for block in n_layer-1 .. 0:
              │           └── _tslice + outer-product accum → SGD Wq, Wo
              │
              ├── _c41_forward_aux                [L3047]  (stubs — no signal)
              │     ├── _c41_hidden_consensus
              │     ├── _c41_gwt_broadcast_reduce + _c41_l_gwt + _c41_phi_gwt
              │     ├── _c41_holo_encode/decode + _c41_l_holo + _c41_phi_holo
              │     └── _c41_qcs_measure
              │
              ├── quantum_controller_step / _phi / _phi_max  (stubs → 0)
              │
              ├── [opt] phi_cache_load / _bucket_id / _lookup / _project /
              │         phi_contrastive_loss   (stubs unless enabled)
              │
              ├── [opt] _sw_qc_loss / _sw_4axis_dev /
              │         _sw_tension_link_diag / _sw_lens_diag /
              │         _sw_tier_max_k / _sw_sumt_stage / _sw_a6_gate_ok
              │
              └── phase_update → next TrainState/TrainStepResult
        │
        └── every save_every: save_checkpoint
              └── _ckpt_append_tensor × (emb, blocks, gamma_final, U, V)
```

## 4. Depth distribution + 5+ import chains

| Depth | Count | Notes                                    |
|-------|-------|------------------------------------------|
| 0 hops  | 1   | train_clm.hexa itself                   |
| ≥1 hop  | 0   | every `use` is commented out            |
| ≥5 hop  | 0   | N/A — silent-exit bug enforced the ban  |

No circular imports. No 5+ deep chains. The only live boundary is the two
`@link` dylibs (depth 1 through FFI, not hexa modules).

## 5. AOT split candidates (for upcoming aot_build_plan)

Because the file is one 3 504-LOC monolith, AOT regeneration recompiles
everything per edit. Natural split lines:

1. **BLAS FFI glue** (L1102-1206 — `_list_to_raw`, `_raw_to_list`, FFI
   externs) → `training/aot/clm_blas_ffi.hexa` — changes rarely.
2. **Decoder core** (L1540-1881 — structs + forward + block fwd/attn/FFN)
   → `training/aot/clm_decoder.hexa` — hottest iter surface.
3. **Backward + optimizer** (L1883-2174 + optim_new/lr_at) →
   `training/aot/clm_backward.hexa` — second-hottest.
4. **Consciousness aux** (L2424-3078 — every `_c41_*` + `_sw_*` helper) →
   `training/aot/clm_aux.hexa` — iteration-heavy during Φ-gate sweeps.
5. **Train loop + CLI** (L3102-end) → kept in `train_clm.hexa` as the
   thin orchestration layer.
6. **Stubs** (L84-255) → **promote to real `use`** only after the
   silent-exit interpreter bug is fixed; at that point clm_mmap_loader +
   phi_cache_loader + anima_quantum_clm slot back in as sibling modules
   (depth-1 from train_clm, safely below the 3-module cliff).

Splitting along these seams preserves the current zero-dep graph while
cutting per-change rebuild surface by ~70% for the decoder/backward
inner loop.
