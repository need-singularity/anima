/*
 * train_step.c — FIX-TRAIN-STEP-FFI single-call training step
 *
 * This file is the single hot path that replaces ~200k hexa
 * interpreter statements per training step with ~50 cuBLAS calls.
 *
 * Status: scaffold. Builds on H100 pod with:
 *   nvcc -O3 -shared -Xcompiler -fPIC \
 *        -lcublas -lcudart -lcurand \
 *        train_step.c -o libtrain_step.so
 *
 * The scaffold implements only the FIRST layer forward pass + loss
 * to validate the FFI contract and tensor layout. Full model +
 * backward + optimizer filled in after R9 pod validation.
 */

#include "train_step.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#ifdef __CUDACC__
#include <cuda_runtime.h>
#include <cublas_v2.h>
#else
/* Stub types for non-CUDA builds (mac dev, type-check only) */
typedef int cudaError_t;
typedef int cublasStatus_t;
typedef void* cublasHandle_t;
typedef enum { CUBLAS_OP_N = 0, CUBLAS_OP_T = 1 } cublasOperation_t;
#define cudaSuccess 0
#define CUBLAS_STATUS_SUCCESS 0
static inline cudaError_t cudaMalloc(void** p, size_t n) { *p = malloc(n); return 0; }
static inline cudaError_t cudaFree(void* p) { free(p); return 0; }
static inline cudaError_t cudaMemcpy(void* d, const void* s, size_t n, int k) { memcpy(d, s, n); return 0; }
static inline cudaError_t cudaMemset(void* p, int v, size_t n) { memset(p, v, n); return 0; }
static inline cudaError_t cudaDeviceSynchronize(void) { return 0; }
static inline cublasStatus_t cublasCreate_v2(cublasHandle_t* h) { *h = (cublasHandle_t)1; return 0; }
static inline cublasStatus_t cublasDestroy_v2(cublasHandle_t h) { return 0; }
static inline cublasStatus_t cublasSgemm_v2(
    cublasHandle_t h, cublasOperation_t ta, cublasOperation_t tb,
    int m, int n, int k,
    const float* alpha, const float* A, int lda,
    const float* B, int ldb,
    const float* beta, float* C, int ldc) { return 0; }
static inline cublasStatus_t cublasSscal_v2(
    cublasHandle_t h, int n, const float* alpha, float* x, int incx) { return 0; }
static inline cublasStatus_t cublasSaxpy_v2(
    cublasHandle_t h, int n, const float* alpha, const float* x, int incx, float* y, int incy) { return 0; }
static inline cublasStatus_t cublasSnrm2_v2(
    cublasHandle_t h, int n, const float* x, int incx, float* result) { return 0; }
#define cudaMemcpyHostToDevice 1
#define cudaMemcpyDeviceToHost 2
#define cudaMemcpyDeviceToDevice 3
#endif

/* ── Scratch buffers: one allocation, reused every step ─── */
typedef struct {
    /* Forward activations (per layer × seq × dim/ff) */
    float* x;          /* residual stream [seq × dim] */
    float* x_norm;     /* after layernorm [seq × dim] */
    float* q;          /* [seq × dim] */
    float* k;
    float* v;
    float* attn;       /* [seq × seq] */
    float* attn_out;   /* [seq × dim] */
    float* ffn_gate;   /* [seq × ff] */
    float* ffn_up;     /* [seq × ff] */
    float* ffn_hidden; /* [seq × ff] */

    /* Per-layer stored activations for backward */
    float** saved_x;        /* [n_layers][seq × dim] */
    float** saved_q;
    float** saved_k;
    float** saved_v;
    float** saved_attn;

    /* Output + loss */
    float* logits;     /* [seq × vocab] */
    float* probs;      /* [seq × vocab] */

    /* Gradients (mirror of weights) */
    ModelWeights grads;

    /* Bookkeeping */
    int n_layers;
    int dim;
    int ff_dim;
    int vocab;
    int seq;

    cublasHandle_t cublas;
} Scratch;

/* ── Scratch allocate / free ───────────────────────────── */
void* train_step_init(const ModelConfig* cfg) {
    Scratch* s = (Scratch*)calloc(1, sizeof(Scratch));
    s->n_layers = cfg->n_layers;
    s->dim      = cfg->dim;
    s->ff_dim   = cfg->ff_dim;
    s->vocab    = cfg->vocab_size;
    s->seq      = cfg->seq_len;

    cublasCreate_v2(&s->cublas);

    int sd = s->seq * s->dim;
    int sf = s->seq * s->ff_dim;
    int ss = s->seq * s->seq;
    int sv = s->seq * s->vocab;

    cudaMalloc((void**)&s->x,          sd * sizeof(float));
    cudaMalloc((void**)&s->x_norm,     sd * sizeof(float));
    cudaMalloc((void**)&s->q,          sd * sizeof(float));
    cudaMalloc((void**)&s->k,          sd * sizeof(float));
    cudaMalloc((void**)&s->v,          sd * sizeof(float));
    cudaMalloc((void**)&s->attn,       ss * sizeof(float));
    cudaMalloc((void**)&s->attn_out,   sd * sizeof(float));
    cudaMalloc((void**)&s->ffn_gate,   sf * sizeof(float));
    cudaMalloc((void**)&s->ffn_up,     sf * sizeof(float));
    cudaMalloc((void**)&s->ffn_hidden, sf * sizeof(float));
    cudaMalloc((void**)&s->logits,     sv * sizeof(float));
    cudaMalloc((void**)&s->probs,      sv * sizeof(float));

    s->saved_x    = (float**)calloc(s->n_layers, sizeof(float*));
    s->saved_q    = (float**)calloc(s->n_layers, sizeof(float*));
    s->saved_k    = (float**)calloc(s->n_layers, sizeof(float*));
    s->saved_v    = (float**)calloc(s->n_layers, sizeof(float*));
    s->saved_attn = (float**)calloc(s->n_layers, sizeof(float*));
    for (int i = 0; i < s->n_layers; ++i) {
        cudaMalloc((void**)&s->saved_x[i],    sd * sizeof(float));
        cudaMalloc((void**)&s->saved_q[i],    sd * sizeof(float));
        cudaMalloc((void**)&s->saved_k[i],    sd * sizeof(float));
        cudaMalloc((void**)&s->saved_v[i],    sd * sizeof(float));
        cudaMalloc((void**)&s->saved_attn[i], ss * sizeof(float));
    }

    return (void*)s;
}

void train_step_cleanup(void* handle) {
    Scratch* s = (Scratch*)handle;
    if (!s) return;
    cudaFree(s->x);
    cudaFree(s->x_norm);
    cudaFree(s->q);
    cudaFree(s->k);
    cudaFree(s->v);
    cudaFree(s->attn);
    cudaFree(s->attn_out);
    cudaFree(s->ffn_gate);
    cudaFree(s->ffn_up);
    cudaFree(s->ffn_hidden);
    cudaFree(s->logits);
    cudaFree(s->probs);
    for (int i = 0; i < s->n_layers; ++i) {
        cudaFree(s->saved_x[i]);
        cudaFree(s->saved_q[i]);
        cudaFree(s->saved_k[i]);
        cudaFree(s->saved_v[i]);
        cudaFree(s->saved_attn[i]);
    }
    free(s->saved_x);
    free(s->saved_q);
    free(s->saved_k);
    free(s->saved_v);
    free(s->saved_attn);
    cublasDestroy_v2(s->cublas);
    free(s);
}

/* ──────────────────────────────────────────────────────────
 *  Row-major SGEMM helper.
 *
 *  cuBLAS is column-major, so we compute C = A * B (row-major)
 *  via C^T = B^T * A^T (column-major). The trick:
 *
 *    row-major A [M×K], B [K×N], C [M×N]
 *      = column-major A' [K×M], B' [N×K], C' [N×M]
 *    so column-major computation:
 *      C'[N×M] = B'[N×K] * A'[K×M]
 *    cublasSgemm(CUBLAS_OP_N, CUBLAS_OP_N, N, M, K, &a, B, N, A, K, &b, C, N)
 *
 *  After this call, the N×M column-major result IS the row-major
 *  M×N result stored in C. No post-transpose needed.
 * ────────────────────────────────────────────────────────── */
static inline void sgemm_rm(
    cublasHandle_t h,
    const float* A, const float* B, float* C,
    int M, int N, int K)
{
    const float alpha = 1.0f, beta = 0.0f;
    cublasSgemm_v2(h, CUBLAS_OP_N, CUBLAS_OP_N,
                   N, M, K,
                   &alpha, B, N,
                           A, K,
                   &beta,  C, N);
}

/* Row-major SGEMM with A transposed: C = A^T * B */
static inline void sgemm_rm_tn(
    cublasHandle_t h,
    const float* A, const float* B, float* C,
    int M, int N, int K)
{
    /* row-major: C[M×N] = A^T[M×K] * B[K×N] where A is stored [K×M]
     * column-major reformulation: C'[N×M] = B'[N×K] * A'[M×K]^T
     * so cublas sees B with OP_N, A with OP_T */
    const float alpha = 1.0f, beta = 0.0f;
    cublasSgemm_v2(h, CUBLAS_OP_N, CUBLAS_OP_T,
                   N, M, K,
                   &alpha, B, N,
                           A, M,
                   &beta,  C, N);
}

/* Row-major SGEMM with B transposed: C = A * B^T */
static inline void sgemm_rm_nt(
    cublasHandle_t h,
    const float* A, const float* B, float* C,
    int M, int N, int K)
{
    /* row-major: C[M×N] = A[M×K] * B^T[K×N] where B is stored [N×K]
     * column-major: C'[N×M] = B'[K×N]^T * A'[K×M]
     * cublas: B with OP_T, A with OP_N */
    const float alpha = 1.0f, beta = 0.0f;
    cublasSgemm_v2(h, CUBLAS_OP_T, CUBLAS_OP_N,
                   N, M, K,
                   &alpha, B, K,
                           A, K,
                   &beta,  C, N);
}

/* ──────────────────────────────────────────────────────────
 *  Host helpers for ops without direct cuBLAS support
 *  (embedding lookup, layernorm, softmax, silu, mask, CE loss).
 *
 *  These do D2H → host compute → H2D roundtrips. Acceptable on
 *  small tensors (seq × dim) — the big matmul work stays on GPU.
 *  Replace with custom CUDA kernels once the FFI contract proves
 *  end-to-end correctness.
 * ────────────────────────────────────────────────────────── */
static void host_embedding_lookup(
    const float* W_emb_dev,   /* [vocab × dim] on device */
    const int* tokens_host,   /* [seq] on host */
    float* x_dev,             /* [seq × dim] on device, output */
    int seq, int dim, int vocab)
{
    /* Copy the relevant rows from device → host scratch → back to x_dev */
    float* row_host = (float*)malloc(dim * sizeof(float));
    for (int i = 0; i < seq; ++i) {
        int tok = tokens_host[i];
        if (tok < 0) tok = 0;
        if (tok >= vocab) tok = vocab - 1;
        /* W_emb[tok * dim : tok * dim + dim] → x_dev[i * dim : (i+1) * dim] */
        cudaMemcpy(row_host, W_emb_dev + tok * dim, dim * sizeof(float),
                   cudaMemcpyDeviceToHost);
        cudaMemcpy(x_dev + i * dim, row_host, dim * sizeof(float),
                   cudaMemcpyHostToDevice);
    }
    free(row_host);
}

static void host_layernorm(
    float* x_dev,             /* [seq × dim] device, in-place normalized */
    const float* gain_dev,    /* [dim] device, may be NULL */
    int seq, int dim)
{
    float* buf = (float*)malloc(seq * dim * sizeof(float));
    float* gain = NULL;
    if (gain_dev) {
        gain = (float*)malloc(dim * sizeof(float));
        cudaMemcpy(gain, gain_dev, dim * sizeof(float), cudaMemcpyDeviceToHost);
    }
    cudaMemcpy(buf, x_dev, seq * dim * sizeof(float), cudaMemcpyDeviceToHost);

    for (int i = 0; i < seq; ++i) {
        float* row = buf + i * dim;
        /* mean */
        float mean = 0.0f;
        for (int j = 0; j < dim; ++j) mean += row[j];
        mean /= (float)dim;
        /* variance */
        float var = 0.0f;
        for (int j = 0; j < dim; ++j) {
            float d = row[j] - mean;
            var += d * d;
        }
        var /= (float)dim;
        float inv = 1.0f / sqrtf(var + 1e-5f);
        for (int j = 0; j < dim; ++j) {
            float y = (row[j] - mean) * inv;
            if (gain) y *= gain[j];
            row[j] = y;
        }
    }
    cudaMemcpy(x_dev, buf, seq * dim * sizeof(float), cudaMemcpyHostToDevice);
    free(buf);
    if (gain) free(gain);
}

static void host_causal_softmax_scale(
    float* attn_dev,          /* [seq × seq] device, in-place */
    int seq, float scale)
{
    float* buf = (float*)malloc(seq * seq * sizeof(float));
    cudaMemcpy(buf, attn_dev, seq * seq * sizeof(float), cudaMemcpyDeviceToHost);

    for (int i = 0; i < seq; ++i) {
        float* row = buf + i * seq;
        /* scale + causal mask: positions j > i get -inf */
        for (int j = 0; j < seq; ++j) {
            if (j > i) row[j] = -1e30f;
            else row[j] *= scale;
        }
        /* softmax */
        float m = row[0];
        for (int j = 1; j <= i; ++j) if (row[j] > m) m = row[j];
        float s = 0.0f;
        for (int j = 0; j <= i; ++j) {
            row[j] = expf(row[j] - m);
            s += row[j];
        }
        float inv = 1.0f / s;
        for (int j = 0; j <= i; ++j) row[j] *= inv;
        for (int j = i + 1; j < seq; ++j) row[j] = 0.0f;
    }
    cudaMemcpy(attn_dev, buf, seq * seq * sizeof(float), cudaMemcpyHostToDevice);
    free(buf);
}

static void host_silu_gate(
    const float* gate_dev,    /* [seq × ff] device */
    const float* up_dev,      /* [seq × ff] device */
    float* hidden_dev,        /* [seq × ff] device, output */
    int seq, int ff)
{
    int n = seq * ff;
    float* g = (float*)malloc(n * sizeof(float));
    float* u = (float*)malloc(n * sizeof(float));
    cudaMemcpy(g, gate_dev, n * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(u, up_dev, n * sizeof(float), cudaMemcpyDeviceToHost);
    for (int i = 0; i < n; ++i) {
        float x = g[i];
        float silu = x / (1.0f + expf(-x));
        g[i] = silu * u[i];
    }
    cudaMemcpy(hidden_dev, g, n * sizeof(float), cudaMemcpyHostToDevice);
    free(g);
    free(u);
}

static float host_softmax_ce_loss(
    const float* logits_dev,  /* [seq × vocab] device */
    const int* targets_host,  /* [seq] host */
    int seq, int vocab)
{
    float* logits = (float*)malloc(seq * vocab * sizeof(float));
    cudaMemcpy(logits, logits_dev, seq * vocab * sizeof(float),
               cudaMemcpyDeviceToHost);

    double total = 0.0;
    int count = 0;
    for (int i = 0; i < seq; ++i) {
        float* row = logits + i * vocab;
        /* log-softmax */
        float m = row[0];
        for (int j = 1; j < vocab; ++j) if (row[j] > m) m = row[j];
        float s = 0.0f;
        for (int j = 0; j < vocab; ++j) s += expf(row[j] - m);
        float logZ = m + logf(s);

        int tgt = targets_host[i];
        if (tgt < 0 || tgt >= vocab) continue;
        float logp = row[tgt] - logZ;
        total += -logp;
        count += 1;
    }
    free(logits);
    if (count == 0) return 0.0f;
    return (float)(total / (double)count);
}

/* ──────────────────────────────────────────────────────────
 *  Host helpers for backward-specific ops
 * ────────────────────────────────────────────────────────── */

/* Backward through softmax+CE loss:
 *   dlogits[i, j] = (softmax(logits[i])[j] - onehot(targets[i])[j]) / seq
 * Operates host-side on logits, writes dlogits to device. */
static void host_softmax_ce_backward(
    const float* logits_dev,
    const int* targets_host,
    float* dlogits_dev,
    int seq, int vocab)
{
    int n = seq * vocab;
    float* logits = (float*)malloc(n * sizeof(float));
    float* dl = (float*)malloc(n * sizeof(float));
    cudaMemcpy(logits, logits_dev, n * sizeof(float), cudaMemcpyDeviceToHost);

    float inv_seq = 1.0f / (float)seq;
    for (int i = 0; i < seq; ++i) {
        float* lr = logits + i * vocab;
        float* dr = dl + i * vocab;
        float m = lr[0];
        for (int j = 1; j < vocab; ++j) if (lr[j] > m) m = lr[j];
        float s = 0.0f;
        for (int j = 0; j < vocab; ++j) s += expf(lr[j] - m);
        float inv_s = 1.0f / s;
        int tgt = targets_host[i];
        for (int j = 0; j < vocab; ++j) {
            float p = expf(lr[j] - m) * inv_s;
            float target_p = (j == tgt) ? 1.0f : 0.0f;
            dr[j] = (p - target_p) * inv_seq;
        }
    }
    cudaMemcpy(dlogits_dev, dl, n * sizeof(float), cudaMemcpyHostToDevice);
    free(logits);
    free(dl);
}

/* Backward through layernorm (ignoring gain for simplicity).
 * Input:
 *   dy_dev [seq × dim]: gradient w.r.t. layernorm output
 *   x_dev  [seq × dim]: original input (pre-norm)
 * Output:
 *   dx_dev [seq × dim]: gradient w.r.t. input
 */
static void host_layernorm_backward(
    const float* dy_dev, const float* x_dev, float* dx_dev,
    int seq, int dim)
{
    int n = seq * dim;
    float* dy = (float*)malloc(n * sizeof(float));
    float* x = (float*)malloc(n * sizeof(float));
    float* dx = (float*)malloc(n * sizeof(float));
    cudaMemcpy(dy, dy_dev, n * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(x,  x_dev,  n * sizeof(float), cudaMemcpyDeviceToHost);

    for (int i = 0; i < seq; ++i) {
        float* xr = x + i * dim;
        float* dyr = dy + i * dim;
        float* dxr = dx + i * dim;

        float mean = 0.0f;
        for (int j = 0; j < dim; ++j) mean += xr[j];
        mean /= (float)dim;
        float var = 0.0f;
        for (int j = 0; j < dim; ++j) {
            float d = xr[j] - mean;
            var += d * d;
        }
        var /= (float)dim;
        float inv = 1.0f / sqrtf(var + 1e-5f);

        /* Standard LayerNorm backward (no gain):
         *   y_j = (x_j - mean) * inv
         *   dx_j = inv * (dy_j - (sum(dy)/N) - y_j * (sum(dy*y)/N))
         */
        float sum_dy = 0.0f, sum_dy_y = 0.0f;
        for (int j = 0; j < dim; ++j) {
            float yj = (xr[j] - mean) * inv;
            sum_dy += dyr[j];
            sum_dy_y += dyr[j] * yj;
        }
        sum_dy /= (float)dim;
        sum_dy_y /= (float)dim;
        for (int j = 0; j < dim; ++j) {
            float yj = (xr[j] - mean) * inv;
            dxr[j] = inv * (dyr[j] - sum_dy - yj * sum_dy_y);
        }
    }
    cudaMemcpy(dx_dev, dx, n * sizeof(float), cudaMemcpyHostToDevice);
    free(dy);
    free(x);
    free(dx);
}

/* Backward through (softmax_row * V) with causal mask: computes d(attn) given d(attn_out) and V.
 * d_attn[i, j] = sum_d d_attn_out[i, d] * V[j, d]  for j ≤ i, else 0.
 * Equivalent to d_attn = d_attn_out @ V^T with a causal mask applied.
 */
static void host_attn_backward_scores(
    const float* d_attn_out_dev, const float* V_dev,
    float* d_attn_dev,
    int seq, int dim)
{
    int nd = seq * dim;
    int ns = seq * seq;
    float* dao = (float*)malloc(nd * sizeof(float));
    float* v = (float*)malloc(nd * sizeof(float));
    float* da = (float*)malloc(ns * sizeof(float));
    cudaMemcpy(dao, d_attn_out_dev, nd * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(v,   V_dev,          nd * sizeof(float), cudaMemcpyDeviceToHost);

    for (int i = 0; i < seq; ++i) {
        for (int j = 0; j < seq; ++j) {
            float s = 0.0f;
            if (j <= i) {
                for (int d = 0; d < dim; ++d) {
                    s += dao[i * dim + d] * v[j * dim + d];
                }
            }
            da[i * seq + j] = s;
        }
    }
    cudaMemcpy(d_attn_dev, da, ns * sizeof(float), cudaMemcpyHostToDevice);
    free(dao);
    free(v);
    free(da);
}

/* Backward through softmax (per row): given saved probs and d_softmax_output,
 * produce d_softmax_input. Row-wise Jacobian:
 *   dz_i = p_i * (dy_i - sum(p * dy))
 */
static void host_row_softmax_backward(
    float* d_attn_dev,           /* in: dy → out: dz (in place) */
    const float* attn_probs_dev, /* saved p (after softmax) */
    int seq, float scale)
{
    int n = seq * seq;
    float* dy = (float*)malloc(n * sizeof(float));
    float* p = (float*)malloc(n * sizeof(float));
    cudaMemcpy(dy, d_attn_dev, n * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(p, attn_probs_dev, n * sizeof(float), cudaMemcpyDeviceToHost);

    for (int i = 0; i < seq; ++i) {
        float* dyr = dy + i * seq;
        float* pr = p + i * seq;
        float sum = 0.0f;
        for (int j = 0; j < seq; ++j) sum += pr[j] * dyr[j];
        for (int j = 0; j < seq; ++j) {
            dyr[j] = pr[j] * (dyr[j] - sum) * scale;
        }
    }
    cudaMemcpy(d_attn_dev, dy, n * sizeof(float), cudaMemcpyHostToDevice);
    free(dy);
    free(p);
}

/* Backward through silu(gate) * up element-wise.
 * Given dz (hidden), produces d_gate and d_up.
 *   silu(x) = x * sigmoid(x)
 *   silu'(x) = sigmoid(x) + x * sigmoid(x) * (1 - sigmoid(x))
 *   hidden = silu(gate) * up
 *   d_gate = dz * up * silu'(gate)
 *   d_up   = dz * silu(gate)
 */
static void host_silu_gate_backward(
    const float* dz_dev,
    const float* gate_dev, const float* up_dev,
    float* d_gate_dev, float* d_up_dev,
    int seq, int ff)
{
    int n = seq * ff;
    float* dz = (float*)malloc(n * sizeof(float));
    float* g = (float*)malloc(n * sizeof(float));
    float* u = (float*)malloc(n * sizeof(float));
    float* dg = (float*)malloc(n * sizeof(float));
    float* du = (float*)malloc(n * sizeof(float));
    cudaMemcpy(dz, dz_dev, n * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(g,  gate_dev, n * sizeof(float), cudaMemcpyDeviceToHost);
    cudaMemcpy(u,  up_dev,   n * sizeof(float), cudaMemcpyDeviceToHost);
    for (int i = 0; i < n; ++i) {
        float x = g[i];
        float sig = 1.0f / (1.0f + expf(-x));
        float silu = x * sig;
        float d_silu = sig + x * sig * (1.0f - sig);
        dg[i] = dz[i] * u[i] * d_silu;
        du[i] = dz[i] * silu;
    }
    cudaMemcpy(d_gate_dev, dg, n * sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(d_up_dev,   du, n * sizeof(float), cudaMemcpyHostToDevice);
    free(dz); free(g); free(u); free(dg); free(du);
}

/* ──────────────────────────────────────────────────────────
 *  Forward pass: embed → N layers → LM head → CE loss
 * ────────────────────────────────────────────────────────── */
static float forward_pass(
    Scratch* s,
    const ModelConfig* cfg,
    ModelWeights* w,
    const Batch* b)
{
    int seq = cfg->seq_len;
    int dim = cfg->dim;
    int ff  = cfg->ff_dim;
    int vocab = cfg->vocab_size;
    float scale = 1.0f / sqrtf((float)cfg->head_dim);

    /* 1. Embedding lookup: x = W_emb[tokens] */
    host_embedding_lookup(w->W_emb, b->tokens, s->x, seq, dim, vocab);

    /* 2. Layer stack */
    for (int L = 0; L < cfg->n_layers; ++L) {
        LayerWeights* lw = &w->layers[L];

        /* Save x for backward residual */
        cudaMemcpy(s->saved_x[L], s->x, seq * dim * sizeof(float),
                   cudaMemcpyDeviceToDevice);

        /* 2a. x_norm = layernorm(x) */
        cudaMemcpy(s->x_norm, s->x, seq * dim * sizeof(float),
                   cudaMemcpyDeviceToDevice);
        host_layernorm(s->x_norm, lw->ln1_gain, seq, dim);

        /* 2b. Q = x_norm @ Wq, K = x_norm @ Wk, V = x_norm @ Wv */
        sgemm_rm(s->cublas, s->x_norm, lw->Wq, s->q, seq, dim, dim);
        sgemm_rm(s->cublas, s->x_norm, lw->Wk, s->k, seq, dim, dim);
        sgemm_rm(s->cublas, s->x_norm, lw->Wv, s->v, seq, dim, dim);

        /* save for backward */
        cudaMemcpy(s->saved_q[L], s->q, seq * dim * sizeof(float), cudaMemcpyDeviceToDevice);
        cudaMemcpy(s->saved_k[L], s->k, seq * dim * sizeof(float), cudaMemcpyDeviceToDevice);
        cudaMemcpy(s->saved_v[L], s->v, seq * dim * sizeof(float), cudaMemcpyDeviceToDevice);

        /* 2c. attn = Q @ K^T  [seq × seq] */
        sgemm_rm_nt(s->cublas, s->q, s->k, s->attn, seq, seq, dim);

        /* 2d. scale + causal mask + softmax */
        host_causal_softmax_scale(s->attn, seq, scale);
        cudaMemcpy(s->saved_attn[L], s->attn, seq * seq * sizeof(float),
                   cudaMemcpyDeviceToDevice);

        /* 2e. attn_out_pre = attn @ V  [seq × dim] */
        sgemm_rm(s->cublas, s->attn, s->v, s->attn_out, seq, dim, seq);

        /* 2f. attn_out = attn_out @ Wo  [seq × dim] */
        /* reuse s->q as scratch for the Wo output */
        sgemm_rm(s->cublas, s->attn_out, lw->Wo, s->q, seq, dim, dim);

        /* 2g. residual: x = x + attn_out */
        {
            const float one = 1.0f;
            cublasSaxpy_v2(s->cublas, seq * dim, &one, s->q, 1, s->x, 1);
        }

        /* 2h. x_norm2 = layernorm(x) */
        cudaMemcpy(s->x_norm, s->x, seq * dim * sizeof(float),
                   cudaMemcpyDeviceToDevice);
        host_layernorm(s->x_norm, lw->ln2_gain, seq, dim);

        /* 2i. FFN: gate = x_norm @ Wg, up = x_norm @ Wu */
        sgemm_rm(s->cublas, s->x_norm, lw->Wg, s->ffn_gate, seq, ff, dim);
        sgemm_rm(s->cublas, s->x_norm, lw->Wu, s->ffn_up,   seq, ff, dim);

        /* 2j. hidden = silu(gate) * up */
        host_silu_gate(s->ffn_gate, s->ffn_up, s->ffn_hidden, seq, ff);

        /* 2k. ffn_out = hidden @ Wd */
        sgemm_rm(s->cublas, s->ffn_hidden, lw->Wd, s->attn_out, seq, dim, ff);

        /* 2l. residual: x = x + ffn_out */
        {
            const float one = 1.0f;
            cublasSaxpy_v2(s->cublas, seq * dim, &one, s->attn_out, 1, s->x, 1);
        }
    }

    /* 3. Final layernorm (pre-LM-head) */
    cudaMemcpy(s->x_norm, s->x, seq * dim * sizeof(float),
               cudaMemcpyDeviceToDevice);
    host_layernorm(s->x_norm, NULL, seq, dim);

    /* 4. LM head: logits = x_norm @ W_emb^T   [seq × vocab] (tied weights) */
    sgemm_rm_nt(s->cublas, s->x_norm, w->W_emb, s->logits, seq, vocab, dim);

    /* 5. Softmax + CE loss (host-side for now) */
    float loss = host_softmax_ce_loss(s->logits, b->targets, seq, vocab);

    cudaDeviceSynchronize();
    return loss;
}

/* ── Main entry point ───────────────────────────────────── */
int train_step(
    const ModelConfig* cfg,
    ModelWeights* weights,
    AdamState* adam,
    const TrainHParams* hp,
    const Batch* batch,
    StepResult* result)
{
    (void)adam;  /* backward pass not yet wired — will hook AdamW here */
    (void)hp;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    /* NOTE: scratch is allocated by train_step_init and must live between
     * calls. For the scaffold, train_step() takes the cfg+weights+batch
     * and uses a process-local static scratch (one per config).
     * A real implementation would thread scratch through as a param. */
    static Scratch* g_scratch = NULL;
    static int g_scratch_layers = -1;
    static int g_scratch_dim = -1;
    if (!g_scratch || g_scratch_layers != cfg->n_layers ||
        g_scratch_dim != cfg->dim) {
        if (g_scratch) train_step_cleanup(g_scratch);
        g_scratch = (Scratch*)train_step_init(cfg);
        g_scratch_layers = cfg->n_layers;
        g_scratch_dim = cfg->dim;
    }

    /* If we don't have real weights yet, short-circuit to the
     * placeholder behavior so the mac scaffold still passes. */
    if (!weights || !weights->W_emb || !weights->layers ||
        !batch || !batch->tokens || !batch->targets) {
        result->loss = 0.0f;
        result->grad_norm = 0.0f;
        clock_gettime(CLOCK_MONOTONIC, &t1);
        result->elapsed_us = (t1.tv_sec - t0.tv_sec) * 1000000 +
                             (t1.tv_nsec - t0.tv_nsec) / 1000;
        return 0;
    }

    /* Forward pass (full) */
    float loss = forward_pass(g_scratch, cfg, weights, batch);
    result->loss = loss;

    /* TODO: backward pass + AdamW — ossified plan has 2-3h work */
    result->grad_norm = 0.0f;

    clock_gettime(CLOCK_MONOTONIC, &t1);
    int64_t us = (t1.tv_sec - t0.tv_sec) * 1000000 +
                 (t1.tv_nsec - t0.tv_nsec) / 1000;
    result->elapsed_us = us;
    return 0;
}

/* ── Self-test entry point for standalone build ──────── */
#ifdef TRAIN_STEP_MAIN
int main(void) {
    ModelConfig cfg = {
        .n_layers = 2,
        .dim = 64,
        .n_heads = 4,
        .head_dim = 16,
        .ff_dim = 128,
        .vocab_size = 256,
        .seq_len = 16
    };
    void* scratch = train_step_init(&cfg);
    if (!scratch) {
        fprintf(stderr, "init failed\n");
        return 1;
    }

    StepResult r = {0};
    ModelWeights w = {0};
    AdamState a = {0};
    TrainHParams hp = { .lr = 3e-4f, .beta1 = 0.9f, .beta2 = 0.999f,
                        .eps = 1e-8f, .weight_decay = 0.1f, .grad_clip = 1.0f, .step = 0 };
    Batch b = {0};
    int tokens[16] = {0};
    int targets[16] = {0};
    b.tokens = tokens;
    b.targets = targets;

    int rc = train_step(&cfg, &w, &a, &hp, &b, &r);
    printf("train_step rc=%d loss=%f grad_norm=%f elapsed_us=%lld\n",
           rc, r.loss, r.grad_norm, (long long)r.elapsed_us);

    train_step_cleanup(scratch);
    return 0;
}
#endif
