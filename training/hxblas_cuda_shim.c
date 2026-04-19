// hxblas_cuda_shim.c — cuBLAS-backed drop-in for hxblas_sgemm (CLM r5-a6.5)
//
// Why this exists:
//   r5-a6 landed 88 hxblas_sgemm call sites in train_clm.hexa (2026-04-20),
//   giving 3.5x speedup on Hetzner 32-core CPU. For any GPU host (ubu RTX5070,
//   H100 pod) the next leverage is routing the same FFI signature through
//   cuBLAS instead of OpenBLAS. This shim preserves the exact hxblas ABI
//   (so train_clm binary needs no re-codegen) and selects backend at runtime
//   via HXBLAS_CUDA=1 env var.
//
//   Signature parity with training/hxblas_wrapper.c is mandatory — all
//   integer args are int64_t, all float scalars are double (hexa FFI quirk,
//   see hxblas_wrapper.c header comment for why). The shim unpacks to the
//   respective backend's native ABI internally.
//
// Build (ubu, AMD Ryzen + RTX5070 Blackwell, CUDA 12.8):
//
//   gcc -O3 -fPIC -shared -fopenmp \
//     -DHXBLAS_ENABLE_CUDA=1 \
//     -I/usr/local/cuda/include \
//     -L/usr/local/cuda/lib64 -Wl,-rpath,/usr/local/cuda/lib64 \
//     training/hxblas_cuda_shim.c \
//     -o training/build/libhxblas_cuda.so \
//     -lopenblas -lcublas -lcudart -lm
//
//   (CPU-only fallback — produces a libhxblas.so equivalent usable on any
//    Linux host even without CUDA toolkit):
//   gcc -O3 -fPIC -shared -fopenmp \
//     training/hxblas_cuda_shim.c \
//     -o training/build/libhxblas.so \
//     -lopenblas -lm
//
// Runtime dispatch:
//   HXBLAS_CUDA=1  →  cublasSgemm path (requires libhxblas_cuda.so at load)
//   unset / 0      →  cblas_sgemm path (OpenBLAS, works either binary)
//
// Column-major note:
//   cuBLAS is column-major, cblas is row-major. The row-major sgemm
//   C = alpha·op(A)·op(B) + beta·C (order=CblasRowMajor) is equivalent to
//   the column-major sgemm C^T = alpha·op(B)^T·op(A)^T + beta·C^T with
//   swapped operands. We implement that swap below.
//
// R37/AN11 compliance:
//   - No Python, no Rust, no shell. Pure .c FFI exception (per user grant).
//   - Real cublasSgemm (not mock) — NVIDIA cuBLAS 12.8 library link.
//   - bf16/fp32 only (caller-controlled dtype); no quantization.
//   - CPU libhxblas.so not modified; this shim can coexist or replace.

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

// ─── OpenBLAS (CPU fallback — always included) ─────────────────
#include <cblas.h>

// ─── cuBLAS (GPU backend — optional) ───────────────────────────
#ifdef HXBLAS_ENABLE_CUDA
#include <cuda_runtime.h>
#include <cublas_v2.h>
#endif

// ═════════════════════════════════════════════════════════════
// Runtime dispatch — environment-gated backend select
// ═════════════════════════════════════════════════════════════

static int g_hxblas_cuda_enabled = -1;  // -1=unchecked, 0=cpu, 1=cuda

static int hxblas_cuda_active(void) {
    if (g_hxblas_cuda_enabled >= 0) return g_hxblas_cuda_enabled;
#ifdef HXBLAS_ENABLE_CUDA
    const char* v = getenv("HXBLAS_CUDA");
    g_hxblas_cuda_enabled = (v && v[0] == '1') ? 1 : 0;
    if (g_hxblas_cuda_enabled) {
        fprintf(stderr, "[hxblas_cuda_shim] HXBLAS_CUDA=1 — cuBLAS backend active\n");
    } else {
        fprintf(stderr, "[hxblas_cuda_shim] HXBLAS_CUDA unset — CPU OpenBLAS backend\n");
    }
#else
    g_hxblas_cuda_enabled = 0;
#endif
    return g_hxblas_cuda_enabled;
}

#ifdef HXBLAS_ENABLE_CUDA
// ─── Singleton cuBLAS handle (lazy-init) ────────────────────────
static cublasHandle_t g_cublas_handle = NULL;
static cudaStream_t   g_cublas_stream = NULL;
static void*          g_cublas_workspace = NULL;
static size_t         g_cublas_workspace_bytes = 0;

static int hxblas_cuda_ensure_handle(void) {
    if (g_cublas_handle) return 0;
    cudaError_t cerr = cudaSetDevice(0);
    if (cerr != cudaSuccess) {
        fprintf(stderr, "[hxblas_cuda_shim] cudaSetDevice(0) failed: %s\n", cudaGetErrorString(cerr));
        return -1;
    }
    cublasStatus_t st = cublasCreate_v2(&g_cublas_handle);
    if (st != CUBLAS_STATUS_SUCCESS) {
        fprintf(stderr, "[hxblas_cuda_shim] cublasCreate_v2 failed: %d\n", (int)st);
        return -2;
    }
    cerr = cudaStreamCreate(&g_cublas_stream);
    if (cerr != cudaSuccess) {
        fprintf(stderr, "[hxblas_cuda_shim] cudaStreamCreate failed: %s\n", cudaGetErrorString(cerr));
        return -3;
    }
    cublasSetStream_v2(g_cublas_handle, g_cublas_stream);
    cublasSetMathMode(g_cublas_handle, CUBLAS_DEFAULT_MATH);
    // 32 MiB workspace — matches hxqwen14b_cublas_pattern_20260419.md Day-1 rec
    g_cublas_workspace_bytes = 32 * 1024 * 1024;
    cerr = cudaMalloc(&g_cublas_workspace, g_cublas_workspace_bytes);
    if (cerr != cudaSuccess) {
        fprintf(stderr, "[hxblas_cuda_shim] cudaMalloc(workspace 32MiB) failed: %s\n", cudaGetErrorString(cerr));
        return -4;
    }
    cublasSetWorkspace_v2(g_cublas_handle, g_cublas_workspace, g_cublas_workspace_bytes);
    fprintf(stderr, "[hxblas_cuda_shim] cuBLAS handle ready (stream=%p, ws=%zu MiB)\n",
            (void*)g_cublas_stream, g_cublas_workspace_bytes / (1024*1024));
    return 0;
}

// Convert row-major CBLAS transpose enum to cuBLAS column-major equivalent.
// Our shim implements row-major sgemm via swap: row-major(A,B) ≡ col-major(B,A).
static cublasOperation_t to_cublas_op(int64_t cblas_op) {
    // CBLAS: 111=NO_TRANS, 112=TRANS, 113=CONJ_TRANS
    if (cblas_op == 112 || cblas_op == 113) return CUBLAS_OP_T;
    return CUBLAS_OP_N;
}
#endif  // HXBLAS_ENABLE_CUDA

// ═════════════════════════════════════════════════════════════
// hxblas_sgemm — FFI entry (dispatch: cuBLAS vs OpenBLAS)
// ═════════════════════════════════════════════════════════════
//
// Hexa signature (unchanged from training/hxblas_wrapper.c):
//   extern fn hxblas_sgemm(order: Int, transA: Int, transB: Int,
//                          M: Int, N: Int, K: Int,
//                          alpha: Float,
//                          A: *Void, lda: Int,
//                          B: *Void, ldb: Int,
//                          beta: Float,
//                          C: *Void, ldc: Int)
//
// Pointers A/B/C are HOST pointers. The cuBLAS path does H2D→GEMM→D2H
// per call (correctness first; Day-1 parity with CPU). Persistent-device
// buffers are a Day-3 optimisation that requires tensor lifetime tracking
// in train_clm.hexa, out of scope for r5-a6.5.
void hxblas_sgemm(int64_t order, int64_t transA, int64_t transB,
                  int64_t M, int64_t N, int64_t K,
                  double alpha,
                  int64_t A, int64_t lda,
                  int64_t B, int64_t ldb,
                  double beta,
                  int64_t C, int64_t ldc) {
#ifdef HXBLAS_ENABLE_CUDA
    if (hxblas_cuda_active()) {
        if (hxblas_cuda_ensure_handle() != 0) {
            fprintf(stderr, "[hxblas_cuda_shim] cuBLAS init failed — falling back to CPU\n");
            goto cpu_path;
        }
        // Row-major to column-major via operand swap trick:
        //   row-major: C[M,N] = op(A)[M,K] · op(B)[K,N]
        //   col-major: C^T[N,M] = op(B)^T[N,K] · op(A)^T[K,M]
        // Call cublasSgemm with (opB, opA, N, M, K, ..., B, ldb, A, lda, C, ldc).
        // op flags keep semantic meaning — if the user passed TRANS on A it's
        // still a TRANS when viewed as operand 2 of the flipped product.
        cublasOperation_t opA = to_cublas_op(transA);
        cublasOperation_t opB = to_cublas_op(transB);

        // Row sizes of A and B in the row-major logical view:
        //   opA==N → A is [M,K], row-count M, col-count K; ld=K (elements)
        //   opA==T → A is [K,M], row-count K, col-count M; ld=M
        // cuBLAS (col-major) expects leading dim = column-stride, which for
        // row-major storage equals the LOGICAL row length. We pass lda/ldb as
        // given by the caller — train_clm sets them to match row-major.
        // For the swap to be valid, cuBLAS reads the raw buffer as column-major
        // with those same leading dims; the math works out because (A^T)^T=A.

        size_t sizeA = (size_t)M * (size_t)K * sizeof(float);
        size_t sizeB = (size_t)K * (size_t)N * sizeof(float);
        size_t sizeC = (size_t)M * (size_t)N * sizeof(float);

        float *dA=NULL, *dB=NULL, *dC=NULL;
        cudaError_t cerr;
        cerr = cudaMalloc((void**)&dA, sizeA);
        if (cerr != cudaSuccess) { fprintf(stderr,"[hxblas_cuda_shim] cudaMalloc A: %s\n", cudaGetErrorString(cerr)); goto cpu_path; }
        cerr = cudaMalloc((void**)&dB, sizeB);
        if (cerr != cudaSuccess) { fprintf(stderr,"[hxblas_cuda_shim] cudaMalloc B: %s\n", cudaGetErrorString(cerr)); cudaFree(dA); goto cpu_path; }
        cerr = cudaMalloc((void**)&dC, sizeC);
        if (cerr != cudaSuccess) { fprintf(stderr,"[hxblas_cuda_shim] cudaMalloc C: %s\n", cudaGetErrorString(cerr)); cudaFree(dA); cudaFree(dB); goto cpu_path; }

        cudaMemcpyAsync(dA, (const void*)(uintptr_t)A, sizeA, cudaMemcpyHostToDevice, g_cublas_stream);
        cudaMemcpyAsync(dB, (const void*)(uintptr_t)B, sizeB, cudaMemcpyHostToDevice, g_cublas_stream);
        // Only copy C if beta != 0 (otherwise it's overwritten)
        if (beta != 0.0) {
            cudaMemcpyAsync(dC, (const void*)(uintptr_t)C, sizeC, cudaMemcpyHostToDevice, g_cublas_stream);
        }

        float alphaf = (float)alpha;
        float betaf  = (float)beta;

        // Swap operands for row→col major: compute C = A·B row-major as
        // C^T = B^T · A^T col-major. Hand cuBLAS (opB, opA, N, M, K, ..., dB, ldb, dA, lda, dC, ldc).
        cublasStatus_t st = cublasSgemm_v2(
            g_cublas_handle,
            opB, opA,
            (int)N, (int)M, (int)K,
            &alphaf,
            dB, (int)ldb,
            dA, (int)lda,
            &betaf,
            dC, (int)ldc);
        if (st != CUBLAS_STATUS_SUCCESS) {
            fprintf(stderr, "[hxblas_cuda_shim] cublasSgemm_v2 failed: %d\n", (int)st);
            cudaFree(dA); cudaFree(dB); cudaFree(dC);
            goto cpu_path;
        }

        cudaMemcpyAsync((void*)(uintptr_t)C, dC, sizeC, cudaMemcpyDeviceToHost, g_cublas_stream);
        cudaStreamSynchronize(g_cublas_stream);

        cudaFree(dA); cudaFree(dB); cudaFree(dC);
        return;
    }
cpu_path:
#endif
    // OpenBLAS CPU path (identical to hxblas_wrapper.c)
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

// ═════════════════════════════════════════════════════════════
// Remaining hxblas_* surface — CPU-only passthrough
//
// These are not on the GEMM critical path and do not yet warrant
// GPU routing (softmax/RMSNorm/CE kernels are a Day-3 item once
// tensors live on device between steps). Preserved verbatim from
// training/hxblas_wrapper.c so libhxblas_cuda.so is a full drop-in.
// ═════════════════════════════════════════════════════════════

double hxblas_sdot(int64_t N, int64_t x, int64_t incx, int64_t y, int64_t incy) {
    float r = cblas_sdot((int)N,
                         (const float*)(uintptr_t)x, (int)incx,
                         (const float*)(uintptr_t)y, (int)incy);
    return (double)r;
}

void hxblas_saxpy(int64_t N, double alpha, int64_t x, int64_t incx, int64_t y, int64_t incy) {
    cblas_saxpy((int)N, (float)alpha,
                (const float*)(uintptr_t)x, (int)incx,
                (float*)(uintptr_t)y, (int)incy);
}

void hxblas_sscal(int64_t N, double alpha, int64_t x, int64_t incx) {
    cblas_sscal((int)N, (float)alpha, (float*)(uintptr_t)x, (int)incx);
}

void hxblas_matmul_scalar(int64_t M, int64_t K, int64_t N, int64_t A, int64_t B, int64_t C) {
    const float* a = (const float*)(uintptr_t)A;
    const float* b = (const float*)(uintptr_t)B;
    float* c = (float*)(uintptr_t)C;
    for (int64_t i = 0; i < M; i++)
        for (int64_t j = 0; j < N; j++) {
            float sum = 0.0f;
            for (int64_t k = 0; k < K; k++) sum += a[i*K+k] * b[k*N+j];
            c[i*N+j] = sum;
        }
}

void hxblas_matmul_omp(int64_t M, int64_t K, int64_t N, int64_t A, int64_t B, int64_t C) {
    const float* a = (const float*)(uintptr_t)A;
    const float* b = (const float*)(uintptr_t)B;
    float* c = (float*)(uintptr_t)C;
    #pragma omp parallel for
    for (int64_t i = 0; i < M; i++)
        for (int64_t j = 0; j < N; j++) {
            float sum = 0.0f;
            for (int64_t k = 0; k < K; k++) sum += a[i*K+k] * b[k*N+j];
            c[i*N+j] = sum;
        }
}

void hxblas_axpy_inplace(int64_t N, int64_t dst, int64_t src) {
    float* d = (float*)(uintptr_t)dst;
    const float* s = (const float*)(uintptr_t)src;
    for (int64_t i = 0; i < N; i++) d[i] += s[i];
}

void hxblas_copy(int64_t N, int64_t dst, int64_t src) {
    memcpy((void*)(uintptr_t)dst, (const void*)(uintptr_t)src, (size_t)N * sizeof(float));
}

void hxblas_zero(int64_t N, int64_t dst) {
    memset((void*)(uintptr_t)dst, 0, (size_t)N * sizeof(float));
}

void hxblas_sgd_inplace(int64_t N, double lr, int64_t w, int64_t g) {
    float* W = (float*)(uintptr_t)w;
    const float* G = (const float*)(uintptr_t)g;
    const float lrf = (float)lr;
    for (int64_t i = 0; i < N; i++) W[i] -= lrf * G[i];
}

void hxblas_silu_fwd(int64_t N, int64_t out, int64_t x) {
    float* o = (float*)(uintptr_t)out;
    const float* X = (const float*)(uintptr_t)x;
    for (int64_t i = 0; i < N; i++) {
        float v = X[i]; float s = 1.0f / (1.0f + expf(-v));
        o[i] = v * s;
    }
}

void hxblas_silu_bwd(int64_t N, int64_t dx, int64_t x, int64_t dy) {
    float* DX = (float*)(uintptr_t)dx;
    const float* X = (const float*)(uintptr_t)x;
    const float* DY = (const float*)(uintptr_t)dy;
    for (int64_t i = 0; i < N; i++) {
        float v = X[i]; float s = 1.0f / (1.0f + expf(-v));
        DX[i] = DY[i] * (s + v * s * (1.0f - s));
    }
}

void hxblas_rmsnorm_fwd(int64_t S, int64_t D, double eps,
                        int64_t y_p, int64_t x_p, int64_t g_p) {
    float* y = (float*)(uintptr_t)y_p;
    const float* x = (const float*)(uintptr_t)x_p;
    const float* g = (const float*)(uintptr_t)g_p;
    const float epsf = (float)eps;
    const float invD = 1.0f / (float)D;
    for (int64_t i = 0; i < S; i++) {
        const float* xi = x + i*D; float* yi = y + i*D;
        float ms = 0.0f;
        for (int64_t p = 0; p < D; p++) ms += xi[p]*xi[p];
        ms *= invD;
        float inv_r = 1.0f / sqrtf(ms + epsf);
        for (int64_t p = 0; p < D; p++) yi[p] = xi[p] * inv_r * g[p];
    }
}

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
        const float* xi = x + i*D; const float* dyi = dy + i*D; float* dxi = dx + i*D;
        float ms = 0.0f;
        for (int64_t p = 0; p < D; p++) ms += xi[p]*xi[p];
        ms *= invD;
        float r = sqrtf(ms + epsf);
        float inv_r = 1.0f / r; float inv_r3 = inv_r*inv_r*inv_r;
        float coef = 0.0f;
        for (int64_t p = 0; p < D; p++) coef += xi[p]*g[p]*dyi[p];
        for (int64_t p = 0; p < D; p++) {
            dxi[p] = g[p]*dyi[p]*inv_r - xi[p]*coef*inv_r3*invD;
            dg[p] += xi[p]*dyi[p]*inv_r;
        }
    }
}

void hxblas_attn_softmax_causal(int64_t S, double scale_d, int64_t scores_p) {
    float* sc = (float*)(uintptr_t)scores_p;
    const float scale = (float)scale_d; const float NEG = -1e30f;
    for (int64_t i = 0; i < S; i++) {
        float* row = sc + i*S;
        for (int64_t j = 0; j <= i; j++) row[j] *= scale;
        for (int64_t j = i+1; j < S; j++) row[j] = NEG;
        float mx = row[0];
        for (int64_t j = 1; j <= i; j++) if (row[j] > mx) mx = row[j];
        float sum = 0.0f;
        for (int64_t j = 0; j <= i; j++) { float e = expf(row[j]-mx); row[j] = e; sum += e; }
        for (int64_t j = i+1; j < S; j++) row[j] = 0.0f;
        float inv_sum = 1.0f / sum;
        for (int64_t j = 0; j <= i; j++) row[j] *= inv_sum;
    }
}

void hxblas_attn_softmax_bwd(int64_t S, double scale_d,
                              int64_t dscores_p, int64_t probs_p, int64_t dprobs_p) {
    float* ds = (float*)(uintptr_t)dscores_p;
    const float* p = (const float*)(uintptr_t)probs_p;
    const float* dp = (const float*)(uintptr_t)dprobs_p;
    const float scale = (float)scale_d;
    for (int64_t i = 0; i < S; i++) {
        const float* prow = p + i*S; const float* dprow = dp + i*S; float* dsrow = ds + i*S;
        float s_acc = 0.0f;
        for (int64_t j = 0; j <= i; j++) s_acc += prow[j]*dprow[j];
        for (int64_t j = 0; j <= i; j++) dsrow[j] = prow[j]*(dprow[j]-s_acc)*scale;
        for (int64_t j = i+1; j < S; j++) dsrow[j] = 0.0f;
    }
}

double hxblas_cross_entropy(int64_t S, int64_t V, double scale_d,
                            int64_t logits_p, int64_t dlogits_p, int64_t targets_p) {
    const float* logits = (const float*)(uintptr_t)logits_p;
    float* dlogits = (float*)(uintptr_t)dlogits_p;
    const int64_t* targets = (const int64_t*)(uintptr_t)targets_p;
    const float scale = (float)scale_d;
    double loss_acc = 0.0;
    for (int64_t i = 0; i < S; i++) {
        const float* row = logits + i*V; float* drow = dlogits + i*V;
        float mx = row[0];
        for (int64_t j = 1; j < V; j++) if (row[j] > mx) mx = row[j];
        float sum_e = 0.0f;
        for (int64_t j = 0; j < V; j++) sum_e += expf(row[j]-mx);
        float log_sum = mx + logf(sum_e);
        int64_t t = targets[i];
        loss_acc += (double)(log_sum - row[t]);
        for (int64_t j = 0; j < V; j++) drow[j] = expf(row[j]-log_sum) * scale;
        drow[t] -= scale;
    }
    return loss_acc;
}

void hxblas_embed_lookup(int64_t S, int64_t D, int64_t h_p, int64_t embed_p, int64_t tokens_p) {
    float* h = (float*)(uintptr_t)h_p;
    const float* embed = (const float*)(uintptr_t)embed_p;
    const int64_t* tokens = (const int64_t*)(uintptr_t)tokens_p;
    for (int64_t i = 0; i < S; i++) {
        int64_t t = tokens[i];
        memcpy(h + i*D, embed + t*D, (size_t)D * sizeof(float));
    }
}

void hxblas_embed_scatter(int64_t S, int64_t D, int64_t dembed_p, int64_t dh_p, int64_t tokens_p) {
    float* dembed = (float*)(uintptr_t)dembed_p;
    const float* dh = (const float*)(uintptr_t)dh_p;
    const int64_t* tokens = (const int64_t*)(uintptr_t)tokens_p;
    for (int64_t i = 0; i < S; i++) {
        int64_t t = tokens[i]; float* row = dembed + t*D; const float* src = dh + i*D;
        for (int64_t p = 0; p < D; p++) row[p] += src[p];
    }
}

// Version probe — bump when hxblas surface changes.
// v2 = hxblas_wrapper.c baseline; v3 = +cuda-shim dispatch.
int64_t hxblas_version(void) {
    return 3;
}
