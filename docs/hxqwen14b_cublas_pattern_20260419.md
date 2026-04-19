# hxqwen14b Day-1 cuBLAS API Pattern Audit (READ-ONLY)

**Date**: 2026-04-19
**Scope**: Audit cuBLAS init/workspace/GEMM patterns for Day-1 wiring of
`self/native/hxqwen14b.c` (currently v4 — returns `RC_ERR_CUDA_TODO=-5`).
**Constraints**: Pattern extraction only. No `.c` edits, no `hxqwen14b.c`
modifications.

---

## 1. Source audit summary

| File                                                                      | What it contains                                     |
| ------------------------------------------------------------------------- | ---------------------------------------------------- |
| `self/native/hxblas_linux.c`                                              | **CPU-only** OpenBLAS cblas + NEON bf16. NO cuBLAS.  |
| `self/native/hxqwen14b.c`                                                 | v4 scaffold. `#include <cublas_v2.h>` guarded by `HXQWEN14B_CUDA`. Call sequence **documented inline** (lines 832-863) but not implemented. |
| `training/deploy/holo_breakthrough_20260416/cuda_native/train_clm_composed.c` | Only **real** cuBLAS init pattern in the tree — via hexa FFI codegen with `cublasCreate_v2` / `cublasSetStream_v2` / `cublasSetMathMode`. |
| `training/native/train_step.c`                                            | Scaffold with stubbed cuBLAS types (`cublasHandle_t`, `cublasSgemm_v2`) for Mac typecheck. |

**Key finding**: `hxblas_linux.c` is the wrong source for cuBLAS patterns — it
is the CPU BLAS shim. The canonical GPU init pattern in the tree comes from
`train_clm_composed.c` (lines 1264-1299).

---

## 2. Canonical init sequence (lifted from train_clm_composed.c)

```c
// 1. Device select
cudaSetDevice(0);

// 2. Handle
cublasHandle_t H;
cublasCreate_v2(&H);                   // returns 0 on success

// 3. Dedicated stream (do NOT use default stream 0 for training)
cudaStream_t S;
cudaStreamCreate(&S);
cublasSetStream_v2(H, S);

// 4. Math mode — Hopper bf16 Tensor Core
cublasSetMathMode(H, CUBLAS_DEFAULT_MATH);
// For H100 bf16 TC, prefer:
//   cublasSetMathMode(H, CUBLAS_TF32_TENSOR_OP_MATH)
// or explicit CUBLAS_COMPUTE_32F_FAST_16BF in cublasGemmEx computeType.

// 5. Scalar pointers held in device OR host memory
//    Default = CUBLAS_POINTER_MODE_HOST (alpha/beta are host float*).
float alpha = 1.0f, beta_zero = 0.0f, beta_one = 1.0f;
```

**Pitfall #1**: `cublasCreate_v2` allocates ~8-16 MB per handle (context +
default workspace). With 16 handle slots in `QwenCtx`, budget ~256 MB before
any weights are uploaded.

**Pitfall #2**: Default stream synchronises with everything. For Day-1 sanity
stay on a single dedicated stream; multi-stream belongs to Day-3+.

---

## 3. cublasGemmEx — bf16 in, fp32 accumulate

The Qwen2.5-14B target (header lines 842-843, 858):

```c
// Base projection: y = W · x    W:[d,d] bf16, x:[d,B*S] bf16, y:[d,B*S] bf16
cublasGemmEx(
    H,
    CUBLAS_OP_N, CUBLAS_OP_N,      // transA, transB
    d, B*S, d,                     // M, N, K  (column-major!)
    &alpha,                        // host fp32 scalar
    W_dev,  CUDA_R_16BF, d,        // A, A type, lda
    x_dev,  CUDA_R_16BF, d,        // B, B type, ldb
    &beta,                         // host fp32 scalar
    y_dev,  CUDA_R_16BF, d,        // C, C type, ldc
    CUBLAS_COMPUTE_32F,            // accumulate in fp32
    CUBLAS_GEMM_DEFAULT_TENSOR_OP  // let heuristic pick TC algo
);

// lm_head (tied embed, bf16 × bf16 → fp32 logits):
cublasGemmEx(
    H, CUBLAS_OP_T, CUBLAS_OP_N,    // W^T
    V, B*S, d,
    &alpha,
    W_embed_dev, CUDA_R_16BF, d,    // stored [V,d], transposed on the fly
    h_dev,       CUDA_R_16BF, d,
    &beta,
    logits_dev,  CUDA_R_32F,  V,    // fp32 logits for CE loss stability
    CUBLAS_COMPUTE_32F,
    CUBLAS_GEMM_DEFAULT_TENSOR_OP);
```

**alpha/beta convention**:
- `alpha = 1.0f`, `beta = 0.0f` — fresh output (most projections)
- `alpha = 1.0f`, `beta = 1.0f` — residual add (LoRA delta: `y += (α/r)·B·(A·x)`)
- `alpha = scale`, `beta = 0.0f` — scaled LoRA, scale = `lora_alpha / lora_r` (16/8 = 2.0f)
- **Never pass 0.0 for alpha** — the GEMM is skipped but still costs a launch.

**Pitfall #3**: cuBLAS is **column-major**. Hexa tensors are row-major.
The idiom is to call with swapped operands: compute C = B·A from row-major
perspective by passing A,B in reverse, with dims (N,M,K). The Qwen header
already assumes this pattern (GQA projection `q = h1 @ W_q` mapped to
`cublasGemmEx(N, N, d, B*S, d, ...)`).

**Pitfall #4**: `lda`/`ldb`/`ldc` are leading dims in **elements**, not bytes.
For row-major row-stride = K (A) or N (B,C), passed as that element count.

---

## 4. Workspace allocation (Hopper / H100)

cuBLAS ≥11.0 on Hopper uses a user-supplied workspace for split-K and
large-N heuristics. Default internal workspace is small; explicit allocation
removes the "fallback to slower algo" warning.

```c
// Recommended workspace (NVIDIA docs, Hopper):
//   - default:       4  MiB  (minimum)
//   - recommended:   32 MiB  (standard H100 training workload)
//   - large models:  128 MiB (14B+ with large batch, split-K heavy)

size_t ws_bytes = 32 * 1024 * 1024;  // 32 MiB
void* ws_dev;
cudaMalloc(&ws_dev, ws_bytes);
cublasSetWorkspace_v2(H, ws_dev, ws_bytes);
```

**Day-1 choice**: 32 MiB single global workspace, one cuBLAS handle. That
matches the existing `QwenCtx.cublas_handle` slot (hxqwen14b.c line 357) —
no struct changes required.

**Pitfall #5**: Workspace is **per-handle, per-stream**. If Day-3 introduces a
compute stream for GEMM and a copy stream for H2D, they can share a handle but
each stream needs exclusive access to the workspace buffer while a GEMM is in
flight. Safest Day-3 upgrade: separate handle per stream, 32 MiB each = 64 MiB.

**Pitfall #6**: `cudaMalloc(workspace)` must happen **after** `cublasCreate`
but **before** the first `cublasGemmEx`. Otherwise cuBLAS picks a non-TC
algo on first call and caches it.

---

## 5. Single vs multi-stream — Day-1 recommendation

| Config                  | Pros                           | Cons                                 | Day  |
| ----------------------- | ------------------------------ | ------------------------------------ | ---- |
| 1 handle, 1 stream      | Simplest, zero races           | No H2D/compute overlap               | **Day-1** |
| 1 handle, 2 streams     | H2D overlap via `SetStream` swap | Workspace race if not serialized   | Day-3 |
| 2 handles, 2 streams    | Full overlap, own workspaces   | 2× context mem (~16 MB), 2× workspace | Day-4+ |

**Day-1 rule**: one `cublasHandle_t`, one `cudaStream_t`, one 32 MiB
workspace. Measure steady-state MFU before adding streams. Pattern matches
`train_clm_composed.c` exactly.

---

## 6. Day-1 init checklist for hxqwen14b_load (v5)

Apply inside the existing `#if defined(__linux__) && defined(HXQWEN14B_CUDA)`
block at line 598:

1. `cudaSetDevice(0)` — check rc, fail with new RC code if needed.
2. `cublasCreate_v2(&h)` — store in `ctx->cublas_handle`.
3. `cudaStreamCreate(&s)` — add `void* cuda_stream` field to `QwenCtx`.
4. `cublasSetStream_v2(h, s)`.
5. `cublasSetMathMode(h, CUBLAS_DEFAULT_MATH)` OR
   `CUBLAS_TF32_TENSOR_OP_MATH` for aggressive TC.
6. `cudaMalloc(&ws, 32<<20)` — add `void* cublas_workspace` to `QwenCtx`.
7. `cublasSetWorkspace_v2(h, ws, 32<<20)`.
8. Upload weights (cudaMalloc + cudaMemcpy per shard).
9. First `cublasGemmEx` sanity call with `CUBLAS_COMPUTE_32F` +
   `CUBLAS_GEMM_DEFAULT_TENSOR_OP`, bf16 A/B, bf16 or fp32 C — verify rc==0.

Mirror cleanup in `hxqwen14b_free` (line 655):
`cublasDestroy_v2` → `cudaStreamDestroy` → `cudaFree(workspace)` → `cudaFree(weights)`.

---

## 7. Reference call sites

- Header map of full forward kernel sequence: `hxqwen14b.c` lines 832-863.
- Header map of backward: `hxqwen14b.c` lines 897-930.
- Real init reference: `train_clm_composed.c` lines 1264-1299.
- Struct slot reservation: `hxqwen14b.c` line 357 (`void* cublas_handle`).
- Build-guard macro: `HXQWEN14B_CUDA` (line 122).
