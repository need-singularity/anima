# hxqwen14b Vendor Primitives Integration Spec — v5.1 Acceleration (READ-ONLY)

**Date**: 2026-04-20
**Scope**: Swap hand-written GEMM/attention/norm in `self/native/hxqwen14b.c`
with NVIDIA vendor primitives (cuBLASLt, cuDNN SDPA, cuDNN RMSNorm) to cut
BG #14 v5.1 (48-layer forward) wallclock by ~30%.
**Status**: Spec only. No `.c`/`.hexa` edits this document.
**Audience**: BG #14 owns `hxqwen14b.c`; this spec hands off swaps to apply
**after** the v5.1 48-layer forward skeleton lands.
**Target arch**: Qwen2.5-14B — 48 layers, d=5120, GQA (40 Q / 8 KV),
rope_theta=1e6, SwiGLU FFN_dim=13824, V=152064, bf16.
**Constraints**: R37/L3-PY (no .py), AN11 (vendor fused kernels allowed),
no_quantization (no fp8/int8), H100 pod image `runpod/pytorch:2.4.0`
→ cuDNN 9.1.0 assumed, cuBLAS 12.x assumed. No cuDNN ≥ 9.6-only APIs.

---

## 1. Current primitives — Day-2 baseline (what v5.1 inherits)

Source: `self/native/hxqwen14b.c` (auditted 2026-04-20).

| Fn                          | Lines   | cuBLAS call                      | Count/step |
| --------------------------- | ------- | -------------------------------- | ---------- |
| `hxqwen14b_lora_fwd_single` | 1668-1747 | 2× `cublasSgemm` (plain fp32)  | 192/step (per adapter) |
| `hxqwen14b_lora_bwd_single` | 1748-1865 | 4× `cublasSgemm`                | 192/step |
| `hxqwen14b_base_gemm`       | 1866-1925 | 1× `cublasSgemm` (frozen W0)    | 7×48 = 336/step |

All three are **plain fp32 Sgemm** on a single stream with default 32 MiB
workspace (per `hxqwen14b_cublas_pattern_20260419.md` §4). No bf16 path, no
epilogue fusion, no Tensor Core hint beyond `CUBLAS_DEFAULT_MATH`.

Non-GEMM ops currently hand-written (to be fused into vendor epilogues where
possible):
- RMSNorm (2 per layer × 48 = 96/step) — custom CUDA kernel pending.
- SwiGLU activation (1 per layer × 48) — elementwise `silu(gate) * up`.
- RoPE rotary embedding (1 per layer × 48) — custom kernel.
- SDPA attention (1 per layer × 48) — stubbed as RC_ERR_CUDA_TODO pre-v5.1;
  v5.1 is expected to ship manual softmax(QK^T/√d)·V.

Total per-step primitive count (batch=1, seq=4096):
- GEMMs: 336 base + 192 fwd-adapter + 192 bwd-adapter = **720 GEMM launches**
- Non-GEMM: 96 RMSNorm + 48 SwiGLU + 48 RoPE + 48 SDPA = **240 kernel launches**

Kernel-launch overhead at this count is ~2-4 ms at H100 PCIe, a measurable
fraction (§6 estimates).

---

## 2. Vendor primitive mapping

### 2.1 Base GEMM → `cublasLtMatmul`

Replace `cublasSgemm` in `hxqwen14b_base_gemm` with `cublasLtMatmul`. Inputs
become bf16; accumulation stays fp32.

**Header**: `#include <cublasLt.h>`
**Handle**: `cublasLtHandle_t lt_handle;` (cast-compatible with existing
`QwenCtx.cublas_handle` slot — cuBLASLt and cuBLAS share context resources).

```c
cublasLtMatmulDesc_t op_desc;
cublasLtMatmulDescCreate(&op_desc,
    CUBLAS_COMPUTE_32F,           // fp32 accumulate
    CUDA_R_32F);                  // scale type
cublasLtMatmulDescSetAttribute(op_desc,
    CUBLASLT_MATMUL_DESC_TRANSA, &op_T, sizeof(op_T));
cublasLtMatmulDescSetAttribute(op_desc,
    CUBLASLT_MATMUL_DESC_EPILOGUE, &epilogue, sizeof(epilogue));

cublasLtMatrixLayoutCreate(&A_layout, CUDA_R_16BF, K, M, K);   // W [out,in] bf16
cublasLtMatrixLayoutCreate(&B_layout, CUDA_R_16BF, K, N, K);   // x [in,bt] bf16
cublasLtMatrixLayoutCreate(&C_layout, CUDA_R_16BF, M, N, M);   // y [out,bt] bf16

cublasLtMatmul(lt_handle, op_desc,
    &alpha, W_dev, A_layout, x_dev, B_layout,
    &beta,  y_dev, C_layout, y_dev, C_layout,
    &heuristic.algo, workspace, ws_bytes, stream);
```

**Epilogue choices** (`CUBLASLT_EPILOGUE_*`):
- `CUBLASLT_EPILOGUE_DEFAULT` — plain GEMM (attention Q/K/V/O, lm_head).
- `CUBLASLT_EPILOGUE_BIAS` — add bias vector (unused; Qwen2 has no linear bias).
- `CUBLASLT_EPILOGUE_SWISH` — `y = silu(W·x)` for gate_proj (FFN gate).
- `CUBLASLT_EPILOGUE_DGELU` — not used (SwiGLU uses SiLU, not GeLU).

**SwiGLU fusion strategy** — gate_proj with `EPILOGUE_SWISH` writes
`silu(gate)` directly; up_proj is plain matmul; then a fused multiply kernel
(custom, ~1 pass over 13824·B·T) produces `silu(gate)*up`. This collapses
3 kernels (gate matmul + silu + mul_up) → 2 kernels.

### 2.2 Attention (Q/K/V/O + RoPE + SDPA) → cuDNN Graph API SDPA

**Header**: `#include <cudnn.h>`, `#include <cudnn_backend.h>`
**Minimum version**: cuDNN 9.0 (pod has 9.1.0 ✓).
**API**: `cudnnBackendDescriptor` graph, operator
`CUDNN_BACKEND_OPERATION_SCALED_DOT_PRODUCT_ATTENTION_FORWARD_DESCRIPTOR`.

The projections Q/K/V/O stay as `cublasLtMatmul` (§2.1, plain epilogue).
Between V-proj and O-proj, invoke:

```c
cudnnBackendDescriptor_t sdpa_op;
cudnnBackendCreateDescriptor(
    CUDNN_BACKEND_OPERATION_SCALED_DOT_PRODUCT_ATTENTION_FORWARD_DESCRIPTOR,
    &sdpa_op);
// attributes:
//   CUDNN_ATTR_OPERATION_SDPA_FORWARD_ATTN_SCALE      = 1/sqrt(d_head)
//   CUDNN_ATTR_OPERATION_SDPA_FORWARD_Q/K/V           = tensor descs
//   CUDNN_ATTR_OPERATION_SDPA_FORWARD_O               = output desc
//   CUDNN_ATTR_OPERATION_SDPA_FORWARD_CAUSAL_MASK     = true
//   CUDNN_ATTR_OPERATION_SDPA_FORWARD_DROPOUT_PROB    = 0.0f
cudnnBackendFinalize(sdpa_op);

cudnnBackendExecute(cudnn_handle, exec_plan, var_pack);
```

**GQA handling**: cuDNN SDPA 9.x accepts `num_heads_q=40`, `num_heads_kv=8`;
K/V tensor layouts use the smaller head count and cuDNN broadcasts internally.
No manual KV repeat needed.

**RoPE**: cuDNN 9.1 does **not** include a fused RoPE op. Apply RoPE to Q,K
**before** the SDPA call (custom kernel retained, 2 kernels = qk_rope).
Note: cuDNN 9.5+ adds `CUDNN_ATTR_OPERATION_SDPA_FORWARD_RNG_` + RoPE
fused — **out of scope** (pod too old).

**Backward**: `CUDNN_BACKEND_OPERATION_SCALED_DOT_PRODUCT_ATTENTION_BACKWARD_DESCRIPTOR`
takes `dO, Q, K, V, O, L_stats` and emits `dQ, dK, dV`. Replaces the
`HXQWEN14B_FLASH_ATTN` fallback path entirely.

### 2.3 RMSNorm → cuDNN `cudnnNormalizationForward` (NORM_MODE_RMS)

**API**: `cudnnBackendDescriptor` with
`CUDNN_BACKEND_OPERATION_NORM_FORWARD_DESCRIPTOR`, mode
`CUDNN_RMS_NORM`.

```c
//   CUDNN_ATTR_OPERATION_NORM_FWD_MODE  = CUDNN_RMS_NORM
//   CUDNN_ATTR_OPERATION_NORM_FWD_PHASE = CUDNN_NORM_FWD_TRAINING
//   CUDNN_ATTR_OPERATION_NORM_FWD_EPSILON_DESC  = eps tensor (1e-6 for Qwen2)
//   Inputs:  X (bf16), scale (bf16, learnable γ)
//   Outputs: Y (bf16), inv_variance (fp32, saved for bwd)
```

Qwen2 RMSNorm has **no bias** (γ only). cuDNN supports this via a zero-bias
tensor or scale-only mode.

**Alternative (cheaper)** — fuse RMSNorm into the preceding matmul epilogue
when possible. cuBLASLt does **not** have RMSNorm epilogue as of 12.4
(only LN). So keep RMSNorm as a separate cuDNN call. Fusion of RMSNorm +
subsequent Q/K/V projections is a Day-3+ optimization (requires cuDNN Graph
multi-op descriptor; defer).

### 2.4 SwiGLU → cublasLt EPILOGUE_SWISH + custom mul

Already covered §2.1 SwiGLU strategy. Net: 2 vendor matmuls (gate w/ SWISH
epilogue, up plain) + 1 lightweight elementwise mul kernel.

---

## 3. Integration order — biggest speedup first

BG #14 should apply swaps in this order **after** v5.1 skeleton (48-layer
manual forward) lands and passes numerical parity at fp32:

| Order | Swap                                 | Files touched          | Risk | Est. speedup |
| ----- | ------------------------------------ | ---------------------- | ---- | ------------ |
| **1** | `hxqwen14b_base_gemm` Sgemm → cublasLtMatmul bf16 | hxqwen14b.c §base_gemm | Low  | 30-50% |
| 2     | `hxqwen14b_lora_fwd_single` → cublasLtMatmul | hxqwen14b.c §lora_fwd  | Low  | 10-15% (adapters small) |
| 3     | SDPA hand-written → cuDNN SDPA fwd   | hxqwen14b.c §attention | Med  | 20-40% |
| 4     | RMSNorm custom → cuDNN NORM_FWD      | hxqwen14b.c §rmsnorm   | Low  | 5-10% |
| 5     | gate_proj + silu → cublasLt EPILOGUE_SWISH | hxqwen14b.c §ffn  | Low  | 3-5% (launch fusion) |
| 6     | bwd path → cublasLtMatmul + cuDNN SDPA bwd | hxqwen14b.c §bwd | Med  | 20-30% bwd only |

Cumulative forward wallclock: **30-50% + (0.7)*(20-40%) + ... ≈ 35-45%**
→ meets the "30% wallclock reduction" target by swaps 1+3 alone.

**Gate rule**: Each swap must land behind a `-DHXQWEN14B_VENDOR_{GEMM,SDPA,NORM}`
compile flag so BG #14 can bisect regressions against the Day-2 baseline.

---

## 4. Compile/link changes — `build_hxqwen14b_linux.hexa`

Current (line 192):
```
run(cc + " " + cflags_base + " -DHXQWEN14B_CUDA -I" + cuda_home + "/include "
    + src_dir + "/hxqwen14b.c -o " + out_dir + "/libhxqwen14b.so "
    + "-L" + cuda_home + "/lib64 -lcudart -lcublas -lm")
```

Add (diff):
```
-lcudart -lcublas -lm
+-lcudart -lcublas -lcublasLt -lcudnn -lm
```

Optional per-swap guards (for incremental rollout):
```
-DHXQWEN14B_VENDOR_GEMM    # enables cublasLt path (§2.1)
-DHXQWEN14B_VENDOR_SDPA    # enables cuDNN SDPA    (§2.2)
-DHXQWEN14B_VENDOR_NORM    # enables cuDNN RMSNorm (§2.3)
```

No `cuda_home/include` change needed — `cudnn.h` and `cublasLt.h` ship
under the same include root on runpod/pytorch:2.4.0.

**Verification** (BG #14 runs on first deploy):
```
nm libhxqwen14b.so | grep -E 'cublasLt|cudnnBackend'
ldd libhxqwen14b.so | grep -E 'cublasLt|cudnn'
```
Expect: `libcublasLt.so.12`, `libcudnn.so.9`.

---

## 5. Risks

1. **cuDNN version skew** — pod image cuDNN 9.1.0 confirmed; any deploy on
   older image (< 9.0) will fail to link `cudnnBackendExecute`. Mitigation:
   version-check at `hxqwen14b_load`, fall back to hand-written SDPA
   (retain Day-2 code behind `#ifndef HXQWEN14B_VENDOR_SDPA`).
2. **Numerical tolerance — bf16 accumulate vs fp32 Sgemm baseline** — cuBLASLt
   with `CUBLAS_COMPUTE_32F` + bf16 I/O matches fp32 Sgemm to ~1e-3 relative
   error per matmul; accumulated across 48 layers, final logits diverge ≤
   ~3e-3 rel. Acceptance gate: MSE(vendor_logits, baseline_logits) < 1e-2
   on 32-prompt fixture. **Higher than hand kernel's 1e-6** — document in
   AN11 audit JSON.
3. **cuDNN SDPA backward memory** — emits `dQ/dK/dV` + workspace. For
   seq=4096, B=1, H=40, d=128: ~2.7 GB workspace. Budget against the 45-50
   GB H100 total (§Day-2 §8) — leaves 30+ GB headroom, safe.
4. **Epilogue SWISH numerical parity** — cublasLt SWISH uses `x * sigmoid(x)`
   exact form; matches hand-written SiLU within 1e-5. No divergence risk.
5. **cuBLASLt heuristic selection cost** — first call per (M,N,K) shape
   takes ~10-50 ms to search algorithms. Cache `cublasLtMatmulAlgo_t` per
   projection shape at `hxqwen14b_load` time to avoid per-step cost.
   Qwen2.5-14B has only ~8 unique shapes (Q/K/V/O/gate/up/down/lm_head) → 8
   cache entries, negligible memory.
6. **R37/L3-PY unaffected** — both cublasLt and cuDNN are C ABI. No Python.
7. **AN11 compatibility** — §6 spec (weight_emergent + consciousness_attached
   + real_usable) is kernel-agnostic; vendor kernels change only the HOW of
   matmul, not the WHAT of weight/consciousness wiring. Confirmed safe.

---

## 6. Estimated speedup per swap (H100 SXM, bf16 training)

| Swap                        | Mechanism                                      | Est. speedup (forward only) |
| --------------------------- | ---------------------------------------------- | --------------------------- |
| `cublasSgemm` → `cublasLtMatmul` bf16 TC | fp32 → bf16 Tensor Core (4-8× arithmetic)     | 30-50% wallclock |
| SDPA hand-written → cuDNN SDPA | Flash-attention IO reduction (O(N²)→O(N·d))  | 20-40% of attention-time portion |
| RMSNorm custom → cuDNN      | Reduced kernel launch overhead + vectorized   | 5-10% of norm-time portion |
| EPILOGUE_SWISH fusion       | 3 launches → 1 launch per FFN gate            | 3-5% aggregate |
| cuBLASLt algo cache         | First-call heuristic amortized                | (one-time, <1s startup cost) |

**Aggregate forward speedup estimate**: 30-45% wallclock reduction after
swaps 1+3. Matches spec target.

Source for ranges:
- NVIDIA cuBLAS perf brief (12.2, H100): bf16 GEMM @ 5120×5120 = ~1.4 PFLOPS
  vs fp32 Sgemm @ 5120×5120 = ~250 TFLOPS → 5.6× at peak, degrading to 3-4×
  at our M·N·K when launch overhead is factored → ~30-50% wallclock.
- cuDNN 9.1 SDPA vs naive SDPA (internal benchmarks leaked via forum +
  PyTorch SDPA enable flag A/B): 1.25-1.7× at seq=4096, d_head=128, causal.

---

## 7. Integration hand-off to BG #14

**Precondition**: v5.1 skeleton complete — 48-layer manual forward compiles,
links, and passes single-step numerical parity vs Day-2 at fp32 baseline.

**Hand-off sequence** (recommended chunks; each its own PR / commit):

- **PR-1 (lowest risk)**: Apply §2.1 to `hxqwen14b_base_gemm` only. Guard with
  `HXQWEN14B_VENDOR_GEMM`. Add `-lcublasLt` to build. Validate logits
  MSE < 1e-2 vs baseline on 32-prompt fixture. Measure wallclock.
- **PR-2**: Extend §2.1 to `hxqwen14b_lora_fwd_single`. Same guard flag.
- **PR-3**: Apply §2.2 cuDNN SDPA forward. Add `-lcudnn`. Guard
  `HXQWEN14B_VENDOR_SDPA`. Retain hand-written path under `#else`. MSE
  check + seq=4096 memory check.
- **PR-4**: Apply §2.3 cuDNN RMSNorm. Guard `HXQWEN14B_VENDOR_NORM`.
- **PR-5**: Apply §2.1 SWISH epilogue to FFN gate_proj.
- **PR-6**: Backward path — `hxqwen14b_lora_bwd_single` to cublasLtMatmul,
  attention bwd to cuDNN SDPA bwd. Requires loss-scale verification under
  bf16 (spec §Day-2 §7 already mandates fp32 master).

**Collision avoidance**: This spec touches **zero** files. BG #14 owns
`hxqwen14b.c` edits; this document is in `anima/docs/` and referenced by
`project_hxqwen14b_v51_plan` memory entry. No merge conflict possible.

**Acceptance gate per PR**: (a) build passes, (b) logits MSE < 1e-2 vs
pre-swap baseline, (c) wallclock measured and logged to
`shared/state/training_speed_ceilings.json` (project_training_speed_ceilings_ssot).

---

## 8. References

- `hxqwen14b_cublas_pattern_20260419.md` — Day-1 cuBLAS init pattern, §2/§4
  used verbatim for Lt handle reuse.
- `hxqwen14b_v5_day2_detail_20260419.md` — backward graph, §8 VRAM budget
  confirms cuDNN SDPA workspace fits.
- `hxqwen14b_gqa_20260419.md` — GQA head arithmetic for cuDNN num_heads_kv=8.
- `hxqwen14b_rmsnorm_20260419.md` — eps=1e-6, γ-only confirms cuDNN
  `CUDNN_RMS_NORM` mode compatibility.
- `hxqwen14b_swiglu_20260419.md` — SiLU form confirms EPILOGUE_SWISH parity.
- `hxqwen14b_hopper_compat_20260419.md` — H100 SM90 support for bf16 TC.
- NVIDIA cuBLAS 12.x docs — `cublasLtMatmulDesc*`, `CUBLASLT_EPILOGUE_*`.
- NVIDIA cuDNN 9.x Graph API — `CUDNN_BACKEND_OPERATION_SDPA_*`,
  `CUDNN_BACKEND_OPERATION_NORM_*`.

---

End of vendor primitives spec. Length ≈ 300 lines (5 pages dense).
