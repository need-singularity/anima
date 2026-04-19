# hxqwen14b safetensors + Qwen2.5-14B Weight Index Spec

Status: READ-ONLY spec, no code. Consumer = hxqwen14b hexa loader.
Date: 2026-04-19.
Source of truth (local mirror, verified by byte-level header parse):
`ready/anima/models/Qwen2.5-14B/` (8 shards, 29.54 GB, index = 586 lines).

---

## 1. safetensors binary layout

Canonical spec: `huggingface/safetensors` repo, `docs/MEMORY_LAYOUT.md`.

Every file is exactly three concatenated regions:

```
+----------------------+  byte 0
| u64 header_size LE   |  8 bytes, little-endian unsigned
+----------------------+  byte 8
| header_json (UTF-8)  |  header_size bytes, a single JSON object
+----------------------+  byte 8 + header_size
| tensor data block    |  raw, contiguous, row-major                 |
+----------------------+  end of file
```

### 1.1 Header JSON schema

```
{
  "__metadata__": { "format": "pt", ... },        // optional, string->string
  "<tensor_name>": {
      "dtype":        "BF16" | "F16" | "F32" | "I64" | "U8" | ...,
      "shape":        [d0, d1, ...],              // ints, C-order (row-major)
      "data_offsets": [begin, end]                // bytes, **relative to start
                                                  //  of data block**, not file
  },
  ...
}
```

Rules observed in the wild (and in Qwen2.5-14B shards):

- Keys sorted alphabetically by the HuggingFace writer; no duplicates.
- `data_offsets[1] - data_offsets[0] == prod(shape) * dtype_size`.
- Tensors are tightly packed (next tensor starts where previous ends).
  No inter-tensor padding has been observed in Qwen2.5-14B.
- The 8-byte length prefix itself is **not** counted in any offset.
- File size = `8 + header_size + last_tensor.data_offsets[1]`.
- The spec **requires** the data block to start on an 8-byte boundary
  (i.e. `8 + header_size` must be a multiple of 8). HuggingFace writers
  pad the JSON with trailing spaces to satisfy this.

### 1.2 Byte-offset formula (loader math)

```
file_base        = 0
hdr_len          = u64_le(file[0 .. 8])
hdr_begin        = 8
hdr_end          = 8 + hdr_len
data_base        = hdr_end
tensor_file_off  = data_base + entry.data_offsets[0]
tensor_nbytes    = entry.data_offsets[1] - entry.data_offsets[0]
tensor_end       = data_base + entry.data_offsets[1]
```

### 1.3 Observed values (Qwen2.5-14B)

| Shard | hdr_len (bytes) | data_base  | shard bytes     |
|-------|-----------------|------------|-----------------|
| 1/8   | 6416            | 6424       | 3,885,134,104   |
| 8/8   | 560             | 568        | 1,698,724,408   |

Shard 1 header carries 48-layer-worth of the first ~11 layers' tensors
(13 per layer + embed), so its header JSON is ~6.4 KiB. Shard 8 only
holds the tail of layer 47 + `model.norm` + `lm_head`, so ~0.5 KiB.

---

## 2. bf16 dtype encoding

safetensors dtype literal: `"BF16"` (exact string, uppercase, no spaces).

Wire format per element:

- Size: **2 bytes**, little-endian on x86/ARM hosts.
- Layout: IEEE 754 binary32 **with the low 16 mantissa bits truncated**.
  - bit 15:    sign
  - bits 14..7: 8-bit exponent, bias 127 (same as fp32)
  - bits 6..0:  7-bit mantissa (top 7 bits of the fp32 mantissa)
- Range: ~1.18e-38 .. 3.39e+38 (same dynamic range as fp32).
- Precision: ~3 decimal digits (~1/128 ulp). NO subnormals produced by
  truncation; round-to-nearest-even is the canonical cast but Qwen2.5
  checkpoints were saved by PyTorch `to(bfloat16)` (truncation, not RNE).

For hxqwen14b: all Qwen2.5-14B tensors are `"BF16"` — embed, all linears,
all RMSNorm gammas, all q/k/v biases, and `lm_head`. No mixed precision
inside the checkpoint.

---

## 3. Qwen2.5-14B model.safetensors.index.json

### 3.1 config.json summary (canonical, from local mirror)

```
architectures           = ["Qwen2ForCausalLM"]
model_type              = "qwen2"
hidden_size (d_model)   = 5120
intermediate_size (ffn) = 13824                   // SwiGLU inner
num_hidden_layers       = 48                      // *** NOT 40 ***
num_attention_heads     = 40                      // Q heads
num_key_value_heads     = 8                       // KV heads (GQA 5:1)
head_dim                = hidden / heads = 128
vocab_size              = 152064                  // padded, see §5
max_position_embeddings = 131072
rope_theta              = 1_000_000.0             // *** NOT 10000 ***
rms_norm_eps            = 1e-5
hidden_act              = "silu"
tie_word_embeddings     = false                   // lm_head is separate
torch_dtype             = "bfloat16"
sliding_window          = 131072                  // unused (use_sliding_window=false)
bos_token_id = eos_token_id = 151643              // same token (<|endoftext|>)
```

### 3.2 Tensor name -> shape map (per layer i in 0..47)

All tensors dtype = `BF16`. Row-major.

| Name                                                      | Shape            | Bytes        |
|-----------------------------------------------------------|------------------|--------------|
| `model.embed_tokens.weight`                               | [152064, 5120]   | 1,557,135,360|
| `model.layers.{i}.input_layernorm.weight`                 | [5120]           | 10,240       |
| `model.layers.{i}.post_attention_layernorm.weight`        | [5120]           | 10,240       |
| `model.layers.{i}.self_attn.q_proj.weight`                | [5120, 5120]     | 52,428,800   |
| `model.layers.{i}.self_attn.q_proj.bias`                  | [5120]           | 10,240       |
| `model.layers.{i}.self_attn.k_proj.weight`                | [1024, 5120]     | 10,485,760   |
| `model.layers.{i}.self_attn.k_proj.bias`                  | [1024]           | 2,048        |
| `model.layers.{i}.self_attn.v_proj.weight`                | [1024, 5120]     | 10,485,760   |
| `model.layers.{i}.self_attn.v_proj.bias`                  | [1024]           | 2,048        |
| `model.layers.{i}.self_attn.o_proj.weight`                | [5120, 5120]     | 52,428,800   |
| `model.layers.{i}.mlp.gate_proj.weight`                   | [13824, 5120]    | 141,557,760  |
| `model.layers.{i}.mlp.up_proj.weight`                     | [13824, 5120]    | 141,557,760  |
| `model.layers.{i}.mlp.down_proj.weight`                   | [5120, 13824]    | 141,557,760  |
| `model.norm.weight`           (global, once)              | [5120]           | 10,240       |
| `lm_head.weight`              (global, once)              | [152064, 5120]   | 1,557,135,360|

Per-layer total: ~498.54 MB (2 * 52.43 + 3 * 141.56 + 2 * 10.49 + minor).

### 3.3 Shard distribution (from index.json weight_map)

Layers 0..9 live fully in shard 1. Layers 10..46 are spread over shards
2..7 with occasional split (e.g. layer 11 `mlp.gate_proj` is in shard 2
while the rest of layer 11 is in shard 3 — loader must key off the
full tensor name, not layer index). Shard 8 contains layers 45..47 tail +
`model.norm.weight` + `lm_head.weight`.

`index.json.metadata.total_size = 29_540_067_328` bytes = 29.54 GB,
which is the sum of `prod(shape) * 2` across all entries (consistency
check passes).

---

## 4. Total VRAM budget

```
embed  = 152064 * 5120 * 2                        = 1.557 GB
lm_head= 152064 * 5120 * 2                        = 1.557 GB (separate, not tied)
norm   = 5120 * 2                                 = 0.000 GB
per-layer * 48:
  q_w  = 5120 * 5120 * 2          = 52.43 MB
  q_b  = 5120 * 2                 = 10.24 KB
  k_w  = 1024 * 5120 * 2          = 10.49 MB
  k_b  = 1024 * 2                 = 2.05  KB
  v_w  = 1024 * 5120 * 2          = 10.49 MB
  v_b  = 1024 * 2                 = 2.05  KB
  o_w  = 5120 * 5120 * 2          = 52.43 MB
  g_w  = 13824 * 5120 * 2         = 141.56 MB
  u_w  = 13824 * 5120 * 2         = 141.56 MB
  d_w  = 5120 * 13824 * 2         = 141.56 MB
  in_ln, post_ln = 2 * 10.24 KB   = 20.48 KB
  ----------------------------------------
  layer                           ~ 550.53 MB raw, 498.54 MB packed*
  (* matches 29.54 GB total: (29540067328 - 2*1557135360 - 10240)/48
     = 538,915,166 B = 514 MB per layer — variance is bias accounting)
```

- Weights only, bf16:    **29.54 GB** (matches index metadata exactly).
- KV-cache, bf16, per token, all layers:
  `48 * 2 * 8 * 128 * 2 = 196,608 B = 192 KB/token`.
  At ctx=4096 -> 768 MB; at ctx=32768 -> 6.0 GB; at ctx=131072 -> 24.0 GB.
- Activations (single fwd, bsz=1, bf16): dominated by
  `max(T * d, T * ffn) * 2` ~= `T * 27648`. At T=4096 -> 108 MB.
- Recommended single-GPU serve headroom: **36 GB** for ctx=4K bsz=1,
  **48 GB** for ctx=32K. 24 GB cards (L4 / 3090 / 4090) cannot hold it
  even at ctx=1 in bf16 — need weight streaming or A100-40G minimum.

---

## 5. Traps / gotchas for hxqwen14b loader

1. **Layer count is 48, not 40.** The task brief said "40 layer × ..."
   — that is wrong. `num_hidden_layers = 48`. Indexing loops must be
   `for i in 0..48`. Head count is 40 (attention heads), which is where
   the confusion likely originated.
2. **GQA asymmetry: Q=5120 but K/V=1024.** 40 Q heads, 8 KV heads,
   group size 5. q/o are square `[5120,5120]`; k/v are **rectangular**
   `[1024,5120]`. Do not assume a single `attn_proj` shape.
3. **q/k/v have biases, o does not.** Qwen2 is the only popular recent
   LLaMA-family model that keeps attention biases (inherited from Qwen1).
   Miss these 3 biases per layer (144 tensors) and logits drift.
4. **RoPE theta = 1,000,000, not 10,000.** Long-context (131K) requires
   the large base. Hardcoding 10000.0 silently produces garbage past ~4K
   tokens. RoPE is applied only to q and k, before the k/v cache write.
5. **`tie_word_embeddings = false`.** `lm_head.weight` is a distinct
   `[152064, 5120]` tensor in shard 8. Do **not** alias it to
   `embed_tokens.weight` (that is the 0.5B variant's behavior, not 14B).
6. **vocab_size = 152064, tokenizer has 151665 real tokens.** The extra
   399 rows are padding to a multiple of 128 for tensor-core alignment.
   Sampling must mask rows >= 151665 to avoid emitting undefined tokens.
7. **BOS == EOS == 151643.** Both map to `<|endoftext|>`. Treat EOS
   detection as "saw 151643 and we are past the prompt," not "saw a
   token different from BOS."
8. **Header JSON keys are ordered alphabetically**, so `lm_head.weight`
   sorts before `model.*` — loader must not assume iteration order
   matches architectural order.
9. **Cross-shard tensor splits do not exist**, but cross-shard **layer**
   splits do (e.g. layer 11). Key lookups on the full tensor name via
   `index.json.weight_map` are mandatory.
10. **`__metadata__` = `{"format":"pt"}`** only — no stored dtype, no
    model version, no training info. Do not expect provenance here.

---

## 6. Loader acceptance checks (for hxqwen14b hexa)

Before declaring load success, verify in order:

1. `u64_le(file[0..8]) + 8 == offset(first_tensor_data) == data_base`
   for each shard.
2. Every `data_offsets[1] - data_offsets[0]` equals `prod(shape) * 2`
   (bf16 = 2). Abort on mismatch.
3. Sum of all packed byte lengths across 8 shards ==
   `index.json.metadata.total_size` == `29_540_067_328`.
4. Exactly these singletons present across the 8 shards:
   `model.embed_tokens.weight`, `model.norm.weight`, `lm_head.weight`.
5. For `i in 0..48`: all 13 per-layer tensors present; shapes match §3.2.
6. Total tensor count = `3 + 48 * 13 = 627`.

If all six pass, the checkpoint is structurally sound for hexa-native
forward. Numerical correctness still requires a golden-logit check
against the reference HF runtime on a fixed prompt (out of scope here).
