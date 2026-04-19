# hxqwen14b RMSNorm Reference (Day-2 forward)

Status: READ-ONLY spec, no code. Consumer = hxqwen14b hexa forward kernels.
Date: 2026-04-19.

## 1. Formula

Root Mean Square Layer Normalization (Zhang & Sennrich, 2019):

```
rms(x) = sqrt( mean(x_i^2) + eps )        // i = 1..d (hidden dim)
y_i    = (x_i / rms(x)) * gamma_i
```

Per-token, per-row operation over the hidden dimension `d`.

- Input:  x       shape [B, T, d]    bf16 / fp16 activations
- Weight: gamma   shape [d]          fp32 scale (learnable)
- Output: y       shape [B, T, d]

No mean subtraction. No bias. No centering.

## 2. LayerNorm vs RMSNorm

| Property              | LayerNorm                                  | RMSNorm                         |
|-----------------------|--------------------------------------------|---------------------------------|
| Centering (mean sub)  | yes: `x - mean(x)`                         | **no**                          |
| Scale statistic       | `var(x) = mean((x-mean)^2)`                | `mean(x^2)` (second moment)     |
| Learnable bias beta   | yes                                        | **no**                          |
| Learnable gain gamma  | yes                                        | yes                             |
| Reductions per row    | 2 (mean, var)                              | **1** (sum of squares)          |
| FLOPs / row           | ~8d                                        | ~4d                             |
| Invariance            | shift + scale                              | scale only                      |

RMSNorm is ~1.4x-1.7x faster in the norm step and saves one pass of the hidden
vector. Qwen2 / Llama / Mistral / Gemma all adopt RMSNorm.

## 3. Qwen 14B specifics (Qwen2.5-14B / Qwen2.5-14B-Instruct)

- `hidden_size          = 5120`
- `num_hidden_layers    = 48`       (2 RMSNorms per block => 96 + 1 final = 97)
- `rms_norm_eps         = 1e-6`     (config.json; same for all Qwen2/Qwen2.5 sizes)
- `gamma` stored as fp32, activations bf16
- No Qwen-specific variant: plain RMSNorm, identical to Llama2RMSNorm.
  (Qwen1 legacy used `1e-5`; Qwen2 family standardized to `1e-6`.)
- Placement: pre-norm. Two sites per decoder block:
    1. `input_layernorm`          before self-attention
    2. `post_attention_layernorm` before MLP
  Plus a final `model.norm` before `lm_head`.

Numerical note: eps is added **inside** the sqrt (`sqrt(ms + eps)`), not
outside. Adding it outside degrades fp16 stability near zero.

## 4. CUDA kernel pattern (warp-level reduce + broadcast)

Target: one CUDA block per (batch, token) row of length d = 5120.

```
Step 1  each thread loads its strided slice of x_row, accumulates partial ss
Step 2  warp-level reduce:   __shfl_xor_sync down-sweep over 32 lanes
Step 3  block-level merge:   one shared-mem slot per warp, then final warp
Step 4  lane-0 computes      rrms = rsqrtf(ss / d + eps)
Step 5  broadcast rrms       __shfl_sync(0xffffffff, rrms, 0)  (or via smem)
Step 6  each thread writes   y_i = (x_i * rrms) * gamma_i
```

Layout rules for hxqwen14b:

- Block size = 1024 threads, each handles d/1024 = 5 elements for d=5120.
- Compute accumulator in fp32 even when x is bf16; cast gamma once.
- Fuse with residual-add and cast (`add_rmsnorm_cast`) to halve HBM traffic.
- Keep eps as a compile-time `float` constant so the compiler folds it.
- Prefer `__frsqrt_rn` (fp32 rsqrt) over `1.f / sqrtf` for latency.

## 5. Backward derivative (gamma-only learnable)

Let `ms = mean(x^2) + eps`, `rrms = 1/sqrt(ms)`, `y = x * rrms * gamma`.

Per-row gradients w.r.t. x (closed form, single reduction):

```
dL/dx_i =  rrms * ( gamma_i * g_i
                    -  (x_i / (d * ms)) * sum_j ( gamma_j * g_j * x_j ) )
```

where `g = dL/dy`.

Per-row gradient w.r.t. gamma (no reduction over d, reduce over tokens):

```
dL/dgamma_i = sum_over_tokens ( g_i * x_i * rrms )
```

Implementation notes:

- One reduction over `d` per row (the `sum_j gamma_j * g_j * x_j` term);
  recomputing `rrms` from `x` is cheaper than caching it when HBM-bound.
- `dL/dgamma` is accumulated in fp32 across the batch, then cast on write.
- No gradient w.r.t. eps (constant), no gradient w.r.t. bias (no bias).

## 6. hxqwen14b integration checklist

1. Forward kernel: fused `rmsnorm(x, gamma, eps) -> y` with in-place option.
2. Fused variant: `add_rmsnorm(residual, x, gamma, eps) -> (residual+x, y)`
   matches Qwen2 pre-norm block where residual is consumed next layer.
3. Epsilon constant wired from model config (`rms_norm_eps = 1e-6`), not
   hard-coded per call site.
4. Unit test against PyTorch `Qwen2RMSNorm` reference, tol = 1e-3 bf16 / 1e-5 fp32.
5. Backward kernel only needed for ALM LoRA base-freeze path if gamma unfrozen;
   forward-only sufficient for LoRA-style training where norm weights are frozen.
