// hxblas_cuda_smoke.c — bit-match smoke test for libhxblas_cuda.so
//
// Runs one 16×16×16 sgemm twice — once with HXBLAS_CUDA=0, once =1 —
// and verifies max abs diff < 1e-4 (bit-matchish for float32 GEMM with
// fp32 accumulate; exact bit match not guaranteed for column-major
// swap + different BLAS algo choice, but error should be well under
// single-ulp accumulation noise for a 16^3 = 4096-op reduction).
//
// Build (ubu):
//   gcc -O2 training/hxblas_cuda_smoke.c \
//     -L training/build -Wl,-rpath,training/build -lhxblas_cuda \
//     -o training/build/hxblas_cuda_smoke
//
// Run:
//   HXBLAS_CUDA=0 training/build/hxblas_cuda_smoke  # CPU reference
//   HXBLAS_CUDA=1 training/build/hxblas_cuda_smoke  # cuBLAS path
//
// The program prints: backend tag + max |C_ref − C_test| + PASS/FAIL.

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

extern void hxblas_sgemm(int64_t order, int64_t transA, int64_t transB,
                         int64_t M, int64_t N, int64_t K,
                         double alpha,
                         int64_t A, int64_t lda,
                         int64_t B, int64_t ldb,
                         double beta,
                         int64_t C, int64_t ldc);
extern int64_t hxblas_version(void);

int main(void) {
    const int M = 16, N = 16, K = 16;
    float *A = (float*)calloc(M*K, sizeof(float));
    float *B = (float*)calloc(K*N, sizeof(float));
    float *C = (float*)calloc(M*N, sizeof(float));
    float *C_ref = (float*)calloc(M*N, sizeof(float));

    // Deterministic pattern
    for (int i = 0; i < M*K; i++) A[i] = 0.01f * (float)((i * 37) % 131 - 65);
    for (int i = 0; i < K*N; i++) B[i] = 0.01f * (float)((i * 53) % 127 - 63);

    // Scalar reference
    for (int i = 0; i < M; i++)
        for (int j = 0; j < N; j++) {
            float s = 0.0f;
            for (int k = 0; k < K; k++) s += A[i*K+k] * B[k*N+j];
            C_ref[i*N+j] = s;
        }

    // hxblas_sgemm call — CBLAS_ROW_MAJOR=101, CBLAS_NO_TRANS=111
    hxblas_sgemm(101, 111, 111,
                 M, N, K,
                 1.0,
                 (int64_t)(uintptr_t)A, K,
                 (int64_t)(uintptr_t)B, N,
                 0.0,
                 (int64_t)(uintptr_t)C, N);

    float max_err = 0.0f;
    for (int i = 0; i < M*N; i++) {
        float d = fabsf(C[i] - C_ref[i]);
        if (d > max_err) max_err = d;
    }

    const char* backend = getenv("HXBLAS_CUDA");
    int cuda = (backend && backend[0] == '1') ? 1 : 0;
    printf("[smoke] hxblas_version=%ld backend=%s max_err=%.2e\n",
           (long)hxblas_version(), cuda ? "CUDA" : "CPU", max_err);

    int pass = (max_err < 1e-4f) ? 1 : 0;
    printf("[smoke] %s\n", pass ? "PASS" : "FAIL");

    free(A); free(B); free(C); free(C_ref);
    return pass ? 0 : 1;
}
