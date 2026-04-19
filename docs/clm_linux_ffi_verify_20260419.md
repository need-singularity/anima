# CLM Linux Native FFI Library Verification — 2026-04-19

**Scope:** READ-ONLY audit of Linux native `.so` FFI shims required for CLM
AOT acceleration. Hosts probed: `hetzner` (root), `ubu` (aiden).
No edits to `train_clm.hexa`.

## 1. Host inventory

| Host    | Path probed                               | `libhxblas.so`            | `libhxlmhead.so` |
|---------|-------------------------------------------|---------------------------|------------------|
| hetzner | `/root/anima/training/`                   | **ABSENT** (no dir)       | **ABSENT**       |
| hetzner | `/root/anima` (recursive `find *.so`)     | **ABSENT** (0 matches)    | **ABSENT**       |
| ubu     | `/home/aiden/anima/training/build/`       | **PRESENT** (symlink)     | **ABSENT**       |
| ubu     | canonical: `~/hexa-lang/self/native/build/libhxblas.so` | present  | n/a              |

- `~/anima/training/` itself does not exist on hetzner — there is no `training/`
  subtree under the convergence-synced anima tree on that host.
- ubu `libhxblas.so` is a symlink: `build/libhxblas.so -> ~/hexa-lang/self/native/build/libhxblas.so`.
  The authoritative build lives in `hexa-lang/self/native/build/`.
- `libhxlmhead.so` (the LM-head shim referenced by CLM AOT plans) is not
  present on either host. Only the BLAS shim has been built so far.

## 2. `libhxblas.so` dependency graph (ubu)

```
linux-vdso.so.1
libopenblas.so.0  -> /lib/x86_64-linux-gnu/libopenblas.so.0
libm.so.6, libc.so.6, /lib64/ld-linux-x86-64.so.2
libgomp.so.1      (OpenMP runtime)
libgfortran.so.5  (pulled in by OpenBLAS)
libgcc_s.so.1
```

**No cuBLAS / cuDNN / CUDA linkage.** `libhxblas.so` is a CPU-only OpenBLAS
wrapper. GPU kernels are NOT currently exposed through this `.so`.

## 3. Exported `hxblas_*` symbols (T = defined text)

GEMM / GEMV / batched:
`hxblas_sgemm`, `hxblas_bgemm`, `hxblas_bgemv`, `hxblas_matmul_omp`,
`hxblas_matmul_scalar`

BLAS-1 / optimiser:
`hxblas_sdot`, `hxblas_saxpy`, `hxblas_sscal`, `hxblas_axpy_inplace`,
`hxblas_copy`, `hxblas_sgd_inplace`

Transformer primitives:
`hxblas_rmsnorm_fwd`, `hxblas_rmsnorm_bwd`,
`hxblas_silu_fwd`, `hxblas_silu_bwd`,
`hxblas_attn_softmax_causal`, `hxblas_attn_softmax_bwd`,
`hxblas_embed_lookup`, `hxblas_embed_scatter`,
`hxblas_cross_entropy`

Precision:
`hxblas_f32_to_bf16`, `hxblas_bf16_to_f32`, `hxblas_bf16_version`

Undefined refs (`U`) — resolved at load time from system libs:
`cblas_sgemm`, `cblas_saxpy`, `cblas_sdot`, `cblas_sscal`,
`GOMP_parallel`, `expf`, `__stack_chk_fail`. All available via the ldd list
above, so load-time linking on ubu is clean.

## 4. AOT link feasibility

- **ubu:** AOT-generated C/object code referencing the `hxblas_*` symbols
  above can link against `libhxblas.so` directly (or via the symlink path).
  No unresolved symbols expected for the matmul/rmsnorm/silu/attention/
  cross-entropy/embedding set. Any call to a higher-level `hxlmhead_*`
  symbol will FAIL to link — that shim has not been built.
- **hetzner:** cannot link at all — no shim `.so` present. Any AOT attempt
  there must first build (or rsync) `libhxblas.so` from hexa-lang sources.

## 5. Path D (hetzner build) — viability

Path D = "build the Linux native FFI on hetzner directly" to unblock
hetzner-side AOT for CLM.

- **Feasibility: HIGH for `libhxblas.so`.** The source tree
  `hexa-lang/self/native/` is the canonical producer; hetzner has a full
  anima checkout but `hexa-lang` repo presence was not verified in this
  audit (single-SSH constraint). Dependency surface is trivial on a
  Debian/Ubuntu host: `libopenblas-dev`, `libgomp1`, `libgfortran5`,
  standard glibc — all routinely present or `apt`-installable.
- **Blocker for full CLM AOT: `libhxlmhead.so` does not exist on either
  host.** Path D cannot deliver CLM LM-head AOT until this shim is
  authored. CLM can still AOT-accelerate the BLAS/norm/activation/softmax
  hot path via `libhxblas.so` alone.
- **Recommendation:** (a) stage ubu's `libhxblas.so` onto hetzner
  (`scp` from `hexa-lang/self/native/build/`) OR rebuild in place; (b)
  treat `libhxlmhead.so` as a separate authoring task, not a Path D
  build-out issue.

## 6. Constraints honoured

- `train_clm.hexa` not read, not edited.
- SSH invocations: 1 to hetzner, 2 to ubu (second was required only because
  the first ubu probe found the `.so` under `build/` rather than the
  documented path). Zero P3 drill interference observed.
