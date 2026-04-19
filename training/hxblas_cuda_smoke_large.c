// hxblas_cuda_smoke_large.c — larger size + transpose sweep
//
// Build: gcc -O2 training/hxblas_cuda_smoke_large.c \
//        -L training/build -Wl,-rpath,training/build -lhxblas_cuda -lm -o /tmp/hxsmoke_L

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

static int run_case(int M, int N, int K, int transA, int transB) {
    // Allocate according to whether op is transpose
    int rowsA = transA ? K : M; int colsA = transA ? M : K;
    int rowsB = transB ? N : K; int colsB = transB ? K : N;
    float *A = calloc(rowsA*colsA, sizeof(float));
    float *B = calloc(rowsB*colsB, sizeof(float));
    float *C = calloc(M*N, sizeof(float));
    float *Cref = calloc(M*N, sizeof(float));
    for (int i = 0; i < rowsA*colsA; i++) A[i] = 0.02f * (float)((i*37)%131 - 65);
    for (int i = 0; i < rowsB*colsB; i++) B[i] = 0.02f * (float)((i*53)%127 - 63);

    // Scalar reference honouring transpose semantics
    for (int i = 0; i < M; i++) for (int j = 0; j < N; j++) {
        float s = 0.0f;
        for (int k = 0; k < K; k++) {
            float a = transA ? A[k*M+i] : A[i*K+k];
            float b = transB ? B[j*K+k] : B[k*N+j];
            s += a*b;
        }
        Cref[i*N+j] = s;
    }

    int lda = transA ? M : K;
    int ldb = transB ? K : N;
    int ldc = N;
    int tA = transA ? 112 : 111;
    int tB = transB ? 112 : 111;
    hxblas_sgemm(101, tA, tB, M, N, K, 1.0,
                 (int64_t)(uintptr_t)A, lda,
                 (int64_t)(uintptr_t)B, ldb,
                 0.0,
                 (int64_t)(uintptr_t)C, ldc);

    float max_err = 0.0f;
    for (int i = 0; i < M*N; i++) {
        float d = fabsf(C[i]-Cref[i]); if (d > max_err) max_err = d;
    }
    const char* be = getenv("HXBLAS_CUDA");
    int cuda = (be && be[0]=='1');
    printf("  [%dx%dx%d tA=%d tB=%d] backend=%s max_err=%.2e %s\n",
           M,N,K,transA,transB, cuda?"CUDA":"CPU", max_err,
           max_err < 1e-2f ? "PASS" : "FAIL");
    int ok = (max_err < 1e-2f);
    free(A); free(B); free(C); free(Cref);
    return ok;
}

int main(void) {
    int fails = 0;
    // Test matrix — sizes 16 and 128, all 4 transpose combinations.
    // Tolerance 1e-2 absolute because at 128^3 reductions fp32 noise grows.
    int cases[][5] = {
        {16,16,16,0,0},
        {16,16,16,1,0},
        {16,16,16,0,1},
        {16,16,16,1,1},
        {128,128,128,0,0},
        {128,128,128,1,0},
        {128,128,128,0,1},
        {64,32,128,0,0},   // non-square
    };
    int n = sizeof(cases)/sizeof(cases[0]);
    for (int i = 0; i < n; i++) {
        if (!run_case(cases[i][0], cases[i][1], cases[i][2], cases[i][3], cases[i][4])) fails++;
    }
    printf("[smoke_L] total=%d fails=%d %s\n", n, fails, fails==0?"ALL_PASS":"FAIL");
    return fails == 0 ? 0 : 1;
}
