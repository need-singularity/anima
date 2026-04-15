// hxblas_wrapper.c — hexa FFI ↔ BLAS/OpenMP ABI shim
//
// Why this exists:
//   The live hexa_v2 compiler (self/native/hexa_v2) maps Hexa `float` → C
//   `double` in its FFI wrapper typedef (see codegen_c2.hexa
//   `gen2_ffi_c_type`). Calling `cblas_sgemm` directly — whose real signature
//   uses C `float` for `alpha`/`beta` — fails silently on ARM64 because the
//   caller materialises `d0`/`d1` (double) while the callee reads `s0`/`s1`
//   (float) registers.
//
//   A parallel fix in the compiler path is in flight (agent #18 is rebuilding
//   hexa_v2). Until that lands, this thin C stub presents a Hexa-FFI-shaped
//   interface (all ints as `int64_t`, all floats as `double`, pointers
//   marshalled as `int64_t` via `alloc_raw`) and narrows to the real cblas
//   float ABI internally.
//
//   Every function here is intentionally call-through — no business logic, no
//   hot loops beyond the one OMP reference kernel used for benchmark
//   parity. Replace with direct `extern fn cblas_sgemm` as soon as the
//   compiler emits correct `float` FFI typedefs.
//
// Build:
//   clang -O3 -Xpreprocessor -fopenmp \
//     -I/opt/homebrew/opt/openblas/include -I/opt/homebrew/opt/libomp/include \
//     -L/opt/homebrew/opt/openblas/lib   -L/opt/homebrew/opt/libomp/lib \
//     -dynamiclib training/hxblas_wrapper.c \
//     -o training/build/libhxblas.dylib \
//     -lopenblas -lomp
//
//   Linux:
//   clang -O3 -fopenmp -shared -fPIC training/hxblas_wrapper.c \
//     -o training/build/libhxblas.so -lopenblas
//
// Spike measurements (2026-04-15, M-series ARM64, 128²/256²/512² row-major
// f32 matmul, all ones inputs):
//
//   | size  | C-scalar  | OMP (naive) | BLAS sgemm | OMP×  | BLAS× |
//   |-------|-----------|-------------|------------|-------|-------|
//   | 128^2 | 1.2 ms    | 0.46 ms     | 0.08 ms    |  2.6x |  15x  |
//   | 256^2 | 12.0 ms   | 2.76 ms     | 0.20 ms    |  4.3x |  60x  |
//   | 512^2 | 114.9 ms  | 23.28 ms    | 0.98 ms    |  4.9x | 117x  |
//
//   Against hexa's *linked-list array* matmul (as used by nn_core.hexa's
//   current matmul fn, see training/nn_core.hexa lines 203-221), the
//   apples-to-apples speedup is ~1,400x at 256² — because the hexa list
//   path allocates O(N²) intermediate nodes, not just FLOPs.

#include <Accelerate/Accelerate.h>
#include <stdint.h>
#include <stddef.h>

// ─────────────────────────────────────────────────────────────
// cblas_sgemm shim — C = alpha * A · B + beta * C
// Hexa signature:
//   @link("libhxblas")
//   extern fn hxblas_sgemm(order: Int, transA: Int, transB: Int,
//                          M: Int, N: Int, K: Int,
//                          alpha: Float,
//                          A: *Void, lda: Int,
//                          B: *Void, ldb: Int,
//                          beta: Float,
//                          C: *Void, ldc: Int)
// ─────────────────────────────────────────────────────────────
void hxblas_sgemm(int64_t order, int64_t transA, int64_t transB,
                  int64_t M, int64_t N, int64_t K,
                  double alpha,
                  int64_t A, int64_t lda,
                  int64_t B, int64_t ldb,
                  double beta,
                  int64_t C, int64_t ldc) {
    cblas_sgemm((enum CBLAS_ORDER)order,
                (enum CBLAS_TRANSPOSE)transA,
                (enum CBLAS_TRANSPOSE)transB,
                (int)M, (int)N, (int)K,
                (float)alpha,
                (const float*)(uintptr_t)A, (int)lda,
                (const float*)(uintptr_t)B, (int)ldb,
                (float)beta,
                (float*)(uintptr_t)C, (int)ldc);
}

// ─────────────────────────────────────────────────────────────
// cblas_sdot shim — dot(x, y) with strides
// Returns a double so the Hexa float→double FFI wrapper just works.
// ─────────────────────────────────────────────────────────────
double hxblas_sdot(int64_t N, int64_t x, int64_t incx, int64_t y, int64_t incy) {
    float r = cblas_sdot((int)N,
                         (const float*)(uintptr_t)x, (int)incx,
                         (const float*)(uintptr_t)y, (int)incy);
    return (double)r;
}

// ─────────────────────────────────────────────────────────────
// cblas_saxpy shim — y := alpha*x + y
// ─────────────────────────────────────────────────────────────
void hxblas_saxpy(int64_t N, double alpha,
                  int64_t x, int64_t incx,
                  int64_t y, int64_t incy) {
    cblas_saxpy((int)N, (float)alpha,
                (const float*)(uintptr_t)x, (int)incx,
                (float*)(uintptr_t)y, (int)incy);
}

// ─────────────────────────────────────────────────────────────
// cblas_sscal shim — x := alpha*x
// ─────────────────────────────────────────────────────────────
void hxblas_sscal(int64_t N, double alpha, int64_t x, int64_t incx) {
    cblas_sscal((int)N, (float)alpha, (float*)(uintptr_t)x, (int)incx);
}

// ─────────────────────────────────────────────────────────────
// Reference kernels — one scalar, one OMP — used for benchmark
// triangulation only (training/accelerate_bench.hexa). BLAS is
// always the production path; these exist so the spike can isolate
// (a) naive scalar over raw pointers (b) OMP parallel without BLAS.
// ─────────────────────────────────────────────────────────────
void hxblas_matmul_scalar(int64_t M, int64_t K, int64_t N,
                          int64_t A, int64_t B, int64_t C) {
    const float* a = (const float*)(uintptr_t)A;
    const float* b = (const float*)(uintptr_t)B;
    float* c = (float*)(uintptr_t)C;
    for (int64_t i = 0; i < M; i++) {
        for (int64_t j = 0; j < N; j++) {
            float sum = 0.0f;
            for (int64_t k = 0; k < K; k++) {
                sum += a[i * K + k] * b[k * N + j];
            }
            c[i * N + j] = sum;
        }
    }
}

void hxblas_matmul_omp(int64_t M, int64_t K, int64_t N,
                       int64_t A, int64_t B, int64_t C) {
    const float* a = (const float*)(uintptr_t)A;
    const float* b = (const float*)(uintptr_t)B;
    float* c = (float*)(uintptr_t)C;
    #pragma omp parallel for
    for (int64_t i = 0; i < M; i++) {
        for (int64_t j = 0; j < N; j++) {
            float sum = 0.0f;
            for (int64_t k = 0; k < K; k++) {
                sum += a[i * K + k] * b[k * N + j];
            }
            c[i * N + j] = sum;
        }
    }
}

// ─────────────────────────────────────────────────────────────
// Small sanity probe — caller can check linkage without any BLAS
// dependency. Returns the hxblas ABI version (bump when adding fns).
// ─────────────────────────────────────────────────────────────
int64_t hxblas_version(void) {
    return 1;
}
