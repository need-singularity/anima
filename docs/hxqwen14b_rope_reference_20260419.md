# hxqwen14b RoPE Reference (READ-ONLY, Day-2 Forward)

2026-04-19 — Rotary Positional Embedding for Qwen 2.x 14B under hxqwen14b.c.
Source-only reference. Do **not** edit hxqwen14b.c from this note.

## 1. Math (RoFormer, Su et al. 2021)

RoPE encodes absolute position `m` by rotating consecutive dim pairs
`(x[2i], x[2i+1])` of the per-head Q/K vector by angle `m · θ_i`:

```
θ_i     = base^(-2i/d_head),            i = 0 .. d_head/2 - 1
angle   = m * θ_i
(y0,y1) = (x0*cos - x1*sin, x0*sin + x1*cos)
```

Equivalent complex form (used by HuggingFace Qwen2):

```
z  = x0 + i·x1                          (pair as complex)
e  = cos(mθ) + i·sin(mθ)
y  = z · e                              (complex multiply)
```

HF variant (used by hxqwen14b reference Python path) splits halves
`x = [x_a | x_b]` and applies:

```
rotated = [x_a*cos - x_b*sin | x_a*sin + x_b*cos]
```

Both forms are algebraically identical; the "halved-split" form matches
`transformers.models.qwen2.modeling_qwen2.apply_rotary_pos_emb` and is
the one loaded ckpts expect. Day-2 C kernel must use the halved-split
form or ckpt compatibility breaks.

## 2. Qwen 2.x 14B RoPE base

Canonical values from `config.json` of `Qwen/Qwen2-14B` / `Qwen/Qwen2.5-14B`:

| field | value |
|---|---|
| `rope_theta` (= base) | **1000000.0** |
| `max_position_embeddings` | 32768 (Qwen2.5: 131072 with YARN) |
| `hidden_size` | 5120 |
| `num_attention_heads` (Q heads) | 40 |
| `num_key_value_heads` (KV heads) | 8 |
| `head_dim` | 128 (= 5120/40) |
| `n_rep` (GQA group size) | 5 (= 40/8) |

Note: pre-Qwen2 (Qwen1 / Qwen1.5 7B) used `base=10000.0`. The existing
hexa decoders in `models/decoder.hexa` and `training/nn_core.hexa`
hard-code `10000.0` — those are CLM / toy paths and are **not** Qwen
14B compatible. Day-2 must use `1000000.0` for hxqwen14b.

## 3. GQA + RoPE per-head application

RoPE is applied to **Q and K only** (never V), **per head**, **before**
the Q·K^T dot product, with the **same θ schedule** across all heads
(θ depends only on within-head dim index `i`, not on head index `h`).

Tensor layout after Q/K projection:

```
Q : [seq, n_q_heads  * head_dim]   = [seq, 40 * 128]
K : [seq, n_kv_heads * head_dim]   = [seq,  8 * 128]
V : [seq, n_kv_heads * head_dim]   = [seq,  8 * 128]
```

Per-token, per-head rotation:

```
for t in 0..seq:
    for h in 0..n_heads_this_tensor:
        x_head = tensor[t, h*128 : (h+1)*128]
        apply_rope(x_head, pos=t, base=1e6)   # halved-split form
```

After RoPE, K/V are repeated (`repeat_kv`, n_rep=5) to match 40 Q heads
before attention — see `modules/decoder/decoder.hexa:284` for the hexa
reference impl; C kernel can fuse repeat_kv into the attention read
address (no physical copy needed).

KV cache stores **post-RoPE** K (so rotation runs once per token, not
once per decode step) and **pre-RoPE-free** V (V never rotates).

## 4. C pseudocode (CUDA kernel sketch)

Precompute cos/sin tables once per context length (host or first-step
device kernel). Tables shape: `[max_seq, head_dim/2]`.

```c
// --- host-side precompute, called once ------------------------------
void rope_precompute(float *cos_tbl, float *sin_tbl,
                     int max_seq, int head_dim, float base /*=1e6f*/) {
    int half = head_dim / 2;
    for (int m = 0; m < max_seq; ++m) {
        for (int i = 0; i < half; ++i) {
            float inv_freq = powf(base, -(2.0f * i) / (float)head_dim);
            float angle    = (float)m * inv_freq;
            cos_tbl[m*half + i] = cosf(angle);
            sin_tbl[m*half + i] = sinf(angle);
        }
    }
}

// --- device kernel: in-place rotate Q or K --------------------------
// x shape: [seq, n_heads, head_dim] (row-major), halved-split form.
// grid  : (seq, n_heads), block: head_dim/2 threads.
__global__ void rope_apply_halved(
        float *x,                 // [seq * n_heads * head_dim]
        const float *cos_tbl,     // [seq * (head_dim/2)]
        const float *sin_tbl,     // [seq * (head_dim/2)]
        int n_heads, int head_dim) {
    int t    = blockIdx.x;                  // position m
    int h    = blockIdx.y;                  // head index
    int i    = threadIdx.x;                 // pair index, 0..head_dim/2-1
    int half = head_dim >> 1;
    if (i >= half) return;

    int row  = (t * n_heads + h) * head_dim;
    float xa = x[row + i];                  // first half
    float xb = x[row + i + half];           // second half
    float c  = cos_tbl[t * half + i];
    float s  = sin_tbl[t * half + i];

    x[row + i]        = xa * c - xb * s;
    x[row + i + half] = xa * s + xb * c;
}
```

Launch (Day-2 forward, per layer, on already-projected Q and K):

```c
dim3 grid_q(seq, 40), grid_k(seq, 8);
rope_apply_halved<<<grid_q, 64>>>(Q, cos_tbl, sin_tbl, 40, 128);
rope_apply_halved<<<grid_k, 64>>>(K, cos_tbl, sin_tbl,  8, 128);
// V: skipped intentionally
```

Fused variant (better) folds RoPE into the QK matmul epilogue so Q/K
are rotated as they stream into shared memory, avoiding one HBM round
trip. Day-2 can ship the non-fused version above and defer the fusion.

## 5. Day-2 application cautions

1. **base = 1e6f, not 1e4f.** Cross-check `config.json`'s `rope_theta`
   at ckpt load; abort if mismatched. All existing hexa RoPE code
   (`nn_core.hexa:582`, `transformer.hexa:53`, `decoder.hexa:18`) uses
   10000.0 — copying those constants breaks Qwen14B ckpt compatibility.
2. **Halved-split, not interleaved pairs.** HF Qwen2 ckpt weights
   assume the halved-split form. The interleaved-pair form
   (`(x[2i], x[2i+1])`) used in `nn_core.hexa::rotary_embedding` is
   mathematically equivalent only if the Q/K projection weights are
   permuted accordingly — the HF ckpt is not permuted, so the halved
   form is mandatory.
3. **Rotate Q and K, skip V.** Rotating V silently degrades quality
   without crashing; add a selftest that asserts V is byte-identical
   pre/post rope_apply.
4. **Per-head, shared θ.** θ depends on `i ∈ [0, head_dim/2)` only,
   not on head index `h`. One cos/sin table serves all 40 Q heads and
   all 8 KV heads.
5. **Precompute once, reuse.** Cos/sin table is `[max_seq, 64]` floats
   = 32K · 64 · 4B = 8 MB; fits L2. Recompute only if seq grows past
   precomputed length.
6. **KV cache stores post-RoPE K.** On decode step N, fetch cached K
   (already rotated with its own original pos), rotate only the new
   token's Q/K with pos=N, and proceed. Never re-rotate cached K.
7. **dtype.** Cos/sin in fp32 always (tiny, precision-critical).
   Rotate Q/K in the compute dtype (bf16 for hxqwen14b); accumulate
   the 2-term rotation in fp32 then cast back to avoid bf16 mantissa
   bleed at long positions (m > 8192).
8. **Qwen2.5 YARN extension (131072 ctx).** hxqwen14b Day-2 targets
   native 32768; YARN scaling factor (`factor`, `low_freq_factor`,
   `high_freq_factor` from `rope_scaling`) is out of scope for Day-2.
   Refuse to run if `rope_scaling != null` in config.json until Day-3.

## 6. Cross-references (no edits, reference only)

- `modules/decoder/decoder.hexa:284` — `repeat_kv` reference impl
- `training/nn_core.hexa:571-597` — interleaved-pair hexa RoPE (CLM,
  base=1e4) — **do not copy** for Qwen 14B
- `anima-speak/transformer.hexa:333-354` — same, speak vocoder
- `models/decoder.hexa:18`, `serving/http_server.hexa:55` — CLM
  `ROPE_BASE = 10000.0` constant (CLM-only, not 14B)
- HuggingFace upstream: `transformers/models/qwen2/modeling_qwen2.py`
  `apply_rotary_pos_emb` — canonical halved-split reference
