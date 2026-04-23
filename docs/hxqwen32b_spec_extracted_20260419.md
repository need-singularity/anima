# hxqwen32b Spec Extracted (2026-04-19)

Forward-looking READ-ONLY prep for `hxqwen32b.c` stub (dest2_alm 차단 해소).
**No .c file is written here** — only spec + ABI signature draft.

## Sources

- `training/train_alm_32b_r1.hexa` §166-178 — Qwen2.5-32B-Instruct BaseModel
- `training/train_alm_32b_r1.hexa` §124-147 — LoRA r/α/steps/GPUs constants
- `hexa-lang/self/native/hxqwen14b.c` §136-163 — 14B ABI & error codes (template)
- `training/alm32b_r1_prep_report.md` — R2 base status
- `nexus/shared/convergence/dest1_dest2_ship.convergence` §14 — dest2 gate

## 32B Spec (from `base_qwen_32b()`)

| Field | Value | Source |
|---|---|---|
| `name` | `qwen2.5-32b-instruct` | train_alm_32b_r1.hexa:168 |
| `hf_id` | `Qwen/Qwen2.5-32B-Instruct` | :169 |
| `n_params_b` | 32 | :170 |
| `hidden_size` | **5120** (same as 14B) | :171 |
| `intermediate_size` | **27648** (vs 14B 13824, 2.0x) | :172 |
| `num_hidden_layers` | **64** (vs 14B 48, 1.33x) | :173 |
| `num_attention_heads` | 40 (same as 14B) | :174 |
| `num_key_value_heads` | 8 (GQA, same as 14B) | :175 |
| `head_dim` | 128 (same as 14B) | :176 |
| `vocab_size` | 152064 (assumed — same Qwen2 tokenizer as 14B) | hxqwen14b.c:142 |
| `max_position` | 32768 (RoPE, same family) | hxqwen14b.c:147 |
| `ffn` | SwiGLU (same family) | — |

**Δ vs 14B:** +16 layers (+33%), FFN intermediate doubled. hidden / heads / KV-heads / head_dim / vocab identical. Tokenizer reusable.

**LoRA r1 targets (7 modules):** `q k v o gate_proj up_proj down_proj` × 64 layers = **448 adapters** (vs 14B 192). r=32, α=64, dropout=0.05. Total ≈ 285 M trainable params @ bf16.

## R2 base-weight upload status

Per `training/alm32b_r1_prep_report.md` §5 (2026-04-18):
> `rclone ls r2:anima-models/base_models/` shows ONLY `qwen25-14b-instruct/` (8 shards, 28GB). **No 32B present.**

Plan: first-pod bootstrap pulls from HuggingFace (HF_TOKEN, ~65GB), then mirrors to `r2:anima-models/base/Qwen2.5-32B-Instruct/` per launch_alm_r11_a.hexa:69.

**Status: R2 MISS → HF pull required on first launch. dest2 hard gate.**

## dest2_alm blocker chain (current)

1. `hxqwen14b_forward_with_lora` / `backward_lora_only` / `apply_lora_delta` — return `-5 CUDA_TODO` (v4). Day-2 CUDA kernels pending.
2. `hxqwen32b.c` — **does not exist**. Required because shard count / layer count / FFN-dim embedded at compile time in 14B header (`QWEN14B_N_LAYER 48` etc.). A 32B variant cannot re-use the 14B `.so`.
3. 32B base weights not yet on R2 (external blocker, HF pull).

## Draft ABI signature for `hxqwen32b.c` (reference only — DO NOT WRITE .c)

Mirror 14B ABI verbatim; only the arch constants and the safetensors shape-validation differ. Struct layouts (HxQwenFwdArgs/BwdArgs/ApplyArgs/AdamArgs) are identical — single-pointer packed marshalling convention is shared.

```c
// hxqwen32b.c — FROZEN arch constants
#define QWEN32B_N_LAYER     64       // vs 14B 48
#define QWEN32B_D_MODEL     5120     // SAME
#define QWEN32B_VOCAB       152064   // SAME
#define QWEN32B_N_HEAD      40       // SAME
#define QWEN32B_N_KV_HEAD   8        // SAME  (GQA)
#define QWEN32B_HEAD_DIM    128      // SAME
#define QWEN32B_FFN_DIM     27648    // vs 14B 13824
#define QWEN32B_MAX_POS     32768    // SAME

#define LORA_N_TARGETS_32B  7        // q k v o + gate up down  (r1 plan)
#define LORA_N_ADAPTERS_32B (QWEN32B_N_LAYER * LORA_N_TARGETS_32B)  // 448

// Stable 5-symbol ABI (matches hxqwen14b):
int64_t hxqwen32b_load(int64_t ckpt_path_p);
int64_t hxqwen32b_version(void);                         // -> 1
int64_t hxqwen32b_free(int64_t h);
int64_t hxqwen32b_generate(int64_t args_p);              // HxQwenGenArgs*
double  hxqwen32b_compute_phi_holo(int64_t h);

// Day-2 LoRA training (return -5 CUDA_TODO until kernels land):
int hxqwen32b_forward_with_lora(void* args);             // HxQwenFwdArgs*
int hxqwen32b_backward_lora_only(void* args);            // HxQwenBwdArgs*
int hxqwen32b_apply_lora_delta(void* args);              // HxQwenApplyArgs*

// LIVE CPU helpers (portable to Mac):
int hxqwen32b_lora_init_A(void* args);                   // Kaiming(fan_in=5120)
int hxqwen32b_lora_init_B(void* args);                   // zero-init
int hxqwen32b_adamw_step_cpu(void* args);                // identical to 14B
int hxqwen32b_safetensors_probe(int64_t path_p, void* out_dims);
```

Error codes unchanged (-1..-5). `RC_ERR_SHAPE_MISMATCH` (-3) trips when probe finds `n_layer != 64` or `ffn_dim != 27648` (the two deltas vs 14B).

## Dest2 unblock path (recommended order)

1. Port `hxqwen14b.c` → `hxqwen32b.c` by copying + swapping the 8 arch constants + adding 3-extra MLP target handling in LoRA adapter idx math (448 adapters, not 192).
2. Update `scripts/build_hxqwen32b_linux.hexa` mirror of build_hxqwen14b_linux.hexa.
3. Bootstrap `/workspace/models/Qwen2.5-32B-Instruct` via HF; mirror to R2.
4. Validate via `--mac-xverify` (safetensors probe + LoRA init + AdamW CPU).
5. When CUDA kernels land for 14B v5, port same kernels to 32B (only dims change — 64 layers vs 48, FFN 27648 vs 13824). Launch command unchanged (torchrun 2× H100 FSDP FULL_SHARD).

## File & path refs

- `/Users/ghost/Dev/anima/training/train_alm_32b_r1.hexa`
- `/Users/ghost/Dev/anima/training/launch_alm_r11_a.hexa`
- `/Users/ghost/Dev/anima/training/alm32b_r1_prep_report.md`
- `/Users/ghost/Dev/hexa-lang/self/native/hxqwen14b.c`
- `/Users/ghost/Dev/nexus/shared/convergence/dest1_dest2_ship.convergence`
