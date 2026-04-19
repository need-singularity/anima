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

// ═════════════════════════════════════════════════════════════
// EXTENSION (agent-a8726cd8, 2026-04-16, task #36 — full attention port)
//
// Why this section exists:
//   The #30 sweep (best 1.65% MFU at d=768 seq=16, 533 ms/step) showed
//   that even after the #27 nn_core Tensor port, scalar inner loops in
//   Hexa (boxed-int while bodies invoking hexa_mul/hexa_add per element)
//   dominate >95% of step time. The fix is to push every per-element
//   loop OUT of Hexa and into native C, where each call is one
//   FFI-overhead unit per WHOLE TENSOR instead of per element.
//
// Each function below:
//   - takes only int64_t / double / pointer-as-int64_t (Hexa FFI ABI)
//   - operates on a contiguous f32 buffer
//   - has a tight C inner loop that the compiler vectorises
//
// On Apple Silicon clang -O3 auto-vectorises these into NEON; we get
// SIMD essentially for free. No vDSP dependency required (vDSP would
// add another 1.5–2x but is single-platform; tight scalar C loops are
// portable to Linux).
// ═════════════════════════════════════════════════════════════

#include <math.h>
#include <string.h>

// ─── eltwise ────────────────────────────────────────────────
// dst[i] += src[i]  for i in [0..N)
void hxblas_axpy_inplace(int64_t N, int64_t dst, int64_t src) {
    float* d = (float*)(uintptr_t)dst;
    const float* s = (const float*)(uintptr_t)src;
    for (int64_t i = 0; i < N; i++) d[i] += s[i];
}

// dst[i] = src[i]  for i in [0..N)
void hxblas_copy(int64_t N, int64_t dst, int64_t src) {
    memcpy((void*)(uintptr_t)dst, (const void*)(uintptr_t)src, (size_t)N * sizeof(float));
}

// dst[i] = 0  for i in [0..N)
void hxblas_zero(int64_t N, int64_t dst) {
    memset((void*)(uintptr_t)dst, 0, (size_t)N * sizeof(float));
}

// w[i] -= lr * g[i]  for i in [0..N)  (SGD)
void hxblas_sgd_inplace(int64_t N, double lr, int64_t w, int64_t g) {
    float* W = (float*)(uintptr_t)w;
    const float* G = (const float*)(uintptr_t)g;
    const float lrf = (float)lr;
    for (int64_t i = 0; i < N; i++) W[i] -= lrf * G[i];
}

// out[i] = x[i] * sigmoid(x[i])   (SwiGLU-self / SiLU activation)
void hxblas_silu_fwd(int64_t N, int64_t out, int64_t x) {
    float* o = (float*)(uintptr_t)out;
    const float* X = (const float*)(uintptr_t)x;
    for (int64_t i = 0; i < N; i++) {
        float v = X[i];
        float s = 1.0f / (1.0f + expf(-v));
        o[i] = v * s;
    }
}

// dx[i] = dy[i] * (s + x[i] * s * (1 - s))  with s = sigmoid(x[i])
void hxblas_silu_bwd(int64_t N, int64_t dx, int64_t x, int64_t dy) {
    float* DX = (float*)(uintptr_t)dx;
    const float* X = (const float*)(uintptr_t)x;
    const float* DY = (const float*)(uintptr_t)dy;
    for (int64_t i = 0; i < N; i++) {
        float v = X[i];
        float s = 1.0f / (1.0f + expf(-v));
        DX[i] = DY[i] * (s + v * s * (1.0f - s));
    }
}

// ─── RMSNorm rows ───────────────────────────────────────────
// y[i,p] = x[i,p] / sqrt(mean(x[i,:]^2) + eps) * gain[p]
void hxblas_rmsnorm_fwd(int64_t S, int64_t D, double eps,
                        int64_t y_p, int64_t x_p, int64_t g_p) {
    float* y = (float*)(uintptr_t)y_p;
    const float* x = (const float*)(uintptr_t)x_p;
    const float* g = (const float*)(uintptr_t)g_p;
    const float epsf = (float)eps;
    const float invD = 1.0f / (float)D;
    for (int64_t i = 0; i < S; i++) {
        const float* xi = x + i * D;
        float* yi = y + i * D;
        float ms = 0.0f;
        for (int64_t p = 0; p < D; p++) ms += xi[p] * xi[p];
        ms *= invD;
        float inv_r = 1.0f / sqrtf(ms + epsf);
        for (int64_t p = 0; p < D; p++) yi[p] = xi[p] * inv_r * g[p];
    }
}

// dx[i,p], dg[p] computed for RMSNorm row backward.
// dg is ACCUMULATED (caller must zero it first).
void hxblas_rmsnorm_bwd(int64_t S, int64_t D, double eps,
                        int64_t dx_p, int64_t dg_p,
                        int64_t x_p, int64_t g_p, int64_t dy_p) {
    float* dx = (float*)(uintptr_t)dx_p;
    float* dg = (float*)(uintptr_t)dg_p;
    const float* x = (const float*)(uintptr_t)x_p;
    const float* g = (const float*)(uintptr_t)g_p;
    const float* dy = (const float*)(uintptr_t)dy_p;
    const float epsf = (float)eps;
    const float invD = 1.0f / (float)D;
    for (int64_t i = 0; i < S; i++) {
        const float* xi = x + i * D;
        const float* dyi = dy + i * D;
        float* dxi = dx + i * D;
        float ms = 0.0f;
        for (int64_t p = 0; p < D; p++) ms += xi[p] * xi[p];
        ms *= invD;
        float r = sqrtf(ms + epsf);
        float inv_r = 1.0f / r;
        float inv_r3 = inv_r * inv_r * inv_r;
        float coef = 0.0f;
        for (int64_t p = 0; p < D; p++) coef += xi[p] * g[p] * dyi[p];
        for (int64_t p = 0; p < D; p++) {
            dxi[p] = g[p] * dyi[p] * inv_r - xi[p] * coef * inv_r3 * invD;
            dg[p] += xi[p] * dyi[p] * inv_r;
        }
    }
}

// ─── Softmax + causal mask combined for attention ───────────
// scores[i,j] = scores[i,j] * scale, then mask j>i = -inf, then softmax row.
void hxblas_attn_softmax_causal(int64_t S, double scale_d, int64_t scores_p) {
    float* sc = (float*)(uintptr_t)scores_p;
    const float scale = (float)scale_d;
    const float NEG = -1e30f;
    for (int64_t i = 0; i < S; i++) {
        float* row = sc + i * S;
        // scale + causal mask (j > i)
        for (int64_t j = 0; j <= i; j++) row[j] = row[j] * scale;
        for (int64_t j = i + 1; j < S; j++) row[j] = NEG;
        // softmax with max-subtract for stability
        float mx = row[0];
        for (int64_t j = 1; j <= i; j++) if (row[j] > mx) mx = row[j];
        float sum = 0.0f;
        for (int64_t j = 0; j <= i; j++) {
            float e = expf(row[j] - mx);
            row[j] = e;
            sum += e;
        }
        // masked positions → 0
        for (int64_t j = i + 1; j < S; j++) row[j] = 0.0f;
        float inv_sum = 1.0f / sum;
        for (int64_t j = 0; j <= i; j++) row[j] *= inv_sum;
    }
}

// Softmax-backward through scaled-causal attention:
// Given probs[i,j] (forward output AFTER softmax) and dprobs[i,j] (upstream),
// produce dscores[i,j] = probs[i,j] * (dprobs[i,j] - sum_j(probs[i,j]*dprobs[i,j])) * scale,
// with mask j > i set to 0.
void hxblas_attn_softmax_bwd(int64_t S, double scale_d,
                              int64_t dscores_p, int64_t probs_p, int64_t dprobs_p) {
    float* ds = (float*)(uintptr_t)dscores_p;
    const float* p = (const float*)(uintptr_t)probs_p;
    const float* dp = (const float*)(uintptr_t)dprobs_p;
    const float scale = (float)scale_d;
    for (int64_t i = 0; i < S; i++) {
        const float* prow = p + i * S;
        const float* dprow = dp + i * S;
        float* dsrow = ds + i * S;
        // jacobian-vector product: row_dot = sum_j p[j]*dp[j]
        float s_acc = 0.0f;
        for (int64_t j = 0; j <= i; j++) s_acc += prow[j] * dprow[j];
        for (int64_t j = 0; j <= i; j++) dsrow[j] = prow[j] * (dprow[j] - s_acc) * scale;
        for (int64_t j = i + 1; j < S; j++) dsrow[j] = 0.0f;
    }
}

// ─── Cross-entropy logit fwd+grad row-wise ─────────────────
// For each row i in [0..S):
//   row = logits + i*V
//   loss_acc += -(row[target[i]] - log_sum_exp(row))
//   dlogits[i,j] = (softmax(row)[j] - 1{j==target[i]}) * scale
// `targets` is array of int64. Returns total loss SUMMED (caller divides by S).
double hxblas_cross_entropy(int64_t S, int64_t V, double scale_d,
                            int64_t logits_p, int64_t dlogits_p, int64_t targets_p) {
    const float* logits = (const float*)(uintptr_t)logits_p;
    float* dlogits = (float*)(uintptr_t)dlogits_p;
    const int64_t* targets = (const int64_t*)(uintptr_t)targets_p;
    const float scale = (float)scale_d;
    double loss_acc = 0.0;
    for (int64_t i = 0; i < S; i++) {
        const float* row = logits + i * V;
        float* drow = dlogits + i * V;
        float mx = row[0];
        for (int64_t j = 1; j < V; j++) if (row[j] > mx) mx = row[j];
        float sum_e = 0.0f;
        for (int64_t j = 0; j < V; j++) sum_e += expf(row[j] - mx);
        float log_sum = mx + logf(sum_e);
        int64_t t = targets[i];
        loss_acc += (double)(log_sum - row[t]);
        for (int64_t j = 0; j < V; j++) drow[j] = expf(row[j] - log_sum) * scale;
        drow[t] -= scale;
    }
    return loss_acc;
}

// ─── Embed lookup + scatter ─────────────────────────────────
// h[i,p] = embed[tokens[i], p]  for i in [0..S), p in [0..D)
void hxblas_embed_lookup(int64_t S, int64_t D, int64_t h_p, int64_t embed_p, int64_t tokens_p) {
    float* h = (float*)(uintptr_t)h_p;
    const float* embed = (const float*)(uintptr_t)embed_p;
    const int64_t* tokens = (const int64_t*)(uintptr_t)tokens_p;
    for (int64_t i = 0; i < S; i++) {
        int64_t t = tokens[i];
        memcpy(h + i * D, embed + t * D, (size_t)D * sizeof(float));
    }
}

// dembed[tokens[i], p] += dh[i, p]   (scatter add)
void hxblas_embed_scatter(int64_t S, int64_t D, int64_t dembed_p, int64_t dh_p, int64_t tokens_p) {
    float* dembed = (float*)(uintptr_t)dembed_p;
    const float* dh = (const float*)(uintptr_t)dh_p;
    const int64_t* tokens = (const int64_t*)(uintptr_t)tokens_p;
    for (int64_t i = 0; i < S; i++) {
        int64_t t = tokens[i];
        float* row = dembed + t * D;
        const float* src = dh + i * D;
        for (int64_t p = 0; p < D; p++) row[p] += src[p];
    }
}

// ─────────────────────────────────────────────────────────────
// Small sanity probe — caller can check linkage without any BLAS
// dependency. Returns the hxblas ABI version (bump when adding fns).
// ─────────────────────────────────────────────────────────────
int64_t hxblas_version(void) {
    return 3;  // bumped 2026-04-20: + hxckpt_* binary ckpt FFI
}

// ═════════════════════════════════════════════════════════════
// HEXACKPT-v2 binary ckpt FFI (2026-04-20)
//
// Purpose: bypass hexa_append_file's strlen() NUL-termination limit
// so we can stream raw tensor bytes (bf16/fp32 little-endian) to the
// ckpt file at fwrite speed — ~22× faster than the v1 text format
// (which is O(N²) string concat inside _ckpt_append_tensor).
//
// All functions return 0 on success, nonzero on I/O failure. All writes
// are little-endian by file contract (host is assumed LE; x86_64 +
// ARM64 default are both LE — this is an explicit invariant of the
// format and MUST stay true across restore to GPU/CPU platforms.)
//
// Handle encoding: FILE* is returned as an int64 (uintptr_t cast) so the
// hexa FFI float→double wrapper does not mangle it. Caller holds the
// handle for the duration of one ckpt write; we do not pool.
// ═════════════════════════════════════════════════════════════

#include <stdio.h>
#include <string.h>

// Open a file for binary append (fopen "ab"). Returns FILE* as int64, or 0.
int64_t hxckpt_open_append(int64_t path_p) {
    const char* path = (const char*)(uintptr_t)path_p;
    if (!path) return 0;
    FILE* f = fopen(path, "ab");
    return (int64_t)(uintptr_t)f;
}

// Open a file for binary write (fopen "wb"). Returns FILE* as int64, or 0.
int64_t hxckpt_open_write(int64_t path_p) {
    const char* path = (const char*)(uintptr_t)path_p;
    if (!path) return 0;
    FILE* f = fopen(path, "wb");
    return (int64_t)(uintptr_t)f;
}

// Open a file for binary read. Returns FILE* as int64, or 0.
int64_t hxckpt_open_read(int64_t path_p) {
    const char* path = (const char*)(uintptr_t)path_p;
    if (!path) return 0;
    FILE* f = fopen(path, "rb");
    return (int64_t)(uintptr_t)f;
}

// Close a handle. Returns 0 on success.
int64_t hxckpt_close(int64_t handle) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    return (int64_t)fclose(f);
}

// Write a raw byte buffer (buf_p points to `n_bytes` of data). Returns
// 0 on success, nonzero on short-write. Caller guarantees buffer lives
// through the call.
int64_t hxckpt_write_bytes(int64_t handle, int64_t buf_p, int64_t n_bytes) {
    FILE* f = (FILE*)(uintptr_t)handle;
    const void* buf = (const void*)(uintptr_t)buf_p;
    if (!f || !buf || n_bytes < 0) return -1;
    size_t got = fwrite(buf, 1, (size_t)n_bytes, f);
    return (got == (size_t)n_bytes) ? 0 : -2;
}

// Read raw bytes into buf_p. Returns number of bytes read (>=0) or -1.
int64_t hxckpt_read_bytes(int64_t handle, int64_t buf_p, int64_t n_bytes) {
    FILE* f = (FILE*)(uintptr_t)handle;
    void* buf = (void*)(uintptr_t)buf_p;
    if (!f || !buf || n_bytes < 0) return -1;
    size_t got = fread(buf, 1, (size_t)n_bytes, f);
    return (int64_t)got;
}

// Convenience: write a uint32 little-endian.
int64_t hxckpt_write_u32(int64_t handle, int64_t val) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    uint32_t v = (uint32_t)val;
    unsigned char b[4];
    b[0] = (unsigned char)(v & 0xFF);
    b[1] = (unsigned char)((v >> 8) & 0xFF);
    b[2] = (unsigned char)((v >> 16) & 0xFF);
    b[3] = (unsigned char)((v >> 24) & 0xFF);
    return (fwrite(b, 1, 4, f) == 4) ? 0 : -2;
}

// Read uint32 little-endian. Returns value, or -1 on error.
int64_t hxckpt_read_u32(int64_t handle) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    unsigned char b[4];
    if (fread(b, 1, 4, f) != 4) return -1;
    uint32_t v = (uint32_t)b[0] | ((uint32_t)b[1] << 8)
               | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    return (int64_t)v;
}

// Write a uint64 little-endian.
int64_t hxckpt_write_u64(int64_t handle, int64_t val) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    uint64_t v = (uint64_t)val;
    unsigned char b[8];
    for (int i = 0; i < 8; i++) b[i] = (unsigned char)((v >> (i * 8)) & 0xFF);
    return (fwrite(b, 1, 8, f) == 8) ? 0 : -2;
}

// Read uint64 little-endian.
int64_t hxckpt_read_u64(int64_t handle) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    unsigned char b[8];
    if (fread(b, 1, 8, f) != 8) return -1;
    uint64_t v = 0;
    for (int i = 0; i < 8; i++) v |= ((uint64_t)b[i]) << (i * 8);
    return (int64_t)v;
}

// Write a uint16 little-endian.
int64_t hxckpt_write_u16(int64_t handle, int64_t val) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    uint16_t v = (uint16_t)val;
    unsigned char b[2];
    b[0] = (unsigned char)(v & 0xFF);
    b[1] = (unsigned char)((v >> 8) & 0xFF);
    return (fwrite(b, 1, 2, f) == 2) ? 0 : -2;
}

// Read uint16 little-endian.
int64_t hxckpt_read_u16(int64_t handle) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    unsigned char b[2];
    if (fread(b, 1, 2, f) != 2) return -1;
    uint16_t v = (uint16_t)b[0] | ((uint16_t)b[1] << 8);
    return (int64_t)v;
}

// Write a uint8.
int64_t hxckpt_write_u8(int64_t handle, int64_t val) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    unsigned char b = (unsigned char)(val & 0xFF);
    return (fwrite(&b, 1, 1, f) == 1) ? 0 : -2;
}

// Read uint8. Returns -1 on EOF/error.
int64_t hxckpt_read_u8(int64_t handle) {
    FILE* f = (FILE*)(uintptr_t)handle;
    if (!f) return -1;
    unsigned char b;
    if (fread(&b, 1, 1, f) != 1) return -1;
    return (int64_t)b;
}

// Write a NUL-free length-prefixed string header + bytes.
// Writes the raw bytes of `s` (length `slen`) with no length prefix —
// caller is responsible for writing the length field separately. This
// is intentional so the writer composes (len_u16 | len_u32 | u8...).
int64_t hxckpt_write_str_bytes(int64_t handle, int64_t str_p, int64_t slen) {
    FILE* f = (FILE*)(uintptr_t)handle;
    const char* s = (const char*)(uintptr_t)str_p;
    if (!f || !s || slen < 0) return -1;
    return (fwrite(s, 1, (size_t)slen, f) == (size_t)slen) ? 0 : -2;
}

// Read a stat: file size in bytes, -1 on fail.
int64_t hxckpt_file_size(int64_t path_p) {
    const char* path = (const char*)(uintptr_t)path_p;
    if (!path) return -1;
    FILE* f = fopen(path, "rb");
    if (!f) return -1;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return -1; }
    long sz = ftell(f);
    fclose(f);
    return (int64_t)sz;
}
