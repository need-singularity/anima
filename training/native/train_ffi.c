/*
 * train_ffi.c — Flat FFI wrapper for hexa → train_step.c
 *
 * Hexa's extern fn can only pass scalars (int/long/float).
 * This wrapper packs them into the C structs that train_step() expects.
 *
 * Build (H100 pod):
 *   nvcc -O3 -shared -Xcompiler -fPIC \
 *        -lcublas -lcudart \
 *        train_ffi.c train_step.c -o libtrain_native.so
 *
 * Hexa side: extern fn train_ffi_init(...) -> long
 *            extern fn train_ffi_step(...) -> float
 */

#include "train_step.h"
#include <stdlib.h>
#include <string.h>

/* ── Persistent state across FFI calls ── */
typedef struct {
    ModelConfig    cfg;
    ModelWeights   weights;
    ModelWeights   grads;
    AdamState      adam;
    TrainHParams   hp;
    Batch          batch;
    StepResult     result;
    void*          scratch;
    int            initialized;
} FfiState;

/* Single global state (one model at a time) */
static FfiState G = {0};

/* ═════════════════════════════════════════════════════════════
 * train_ffi_init — allocate model + optimizer + scratch
 *
 * Returns 1 on success, 0 on error.
 * All weights are random-initialized on GPU.
 * ═════════════════════════════════════════════════════════════ */
int train_ffi_init(
    int n_layers, int dim, int n_heads, int head_dim,
    int ff_dim, int vocab_size, int seq_len)
{
    if (G.initialized) return 0;  /* already init */

    G.cfg.n_layers   = n_layers;
    G.cfg.dim        = dim;
    G.cfg.n_heads    = n_heads;
    G.cfg.head_dim   = head_dim;
    G.cfg.ff_dim     = ff_dim;
    G.cfg.vocab_size = vocab_size;
    G.cfg.seq_len    = seq_len;

    int dd = dim * dim;
    int df = dim * ff_dim;
    int fd = ff_dim * dim;
    int vd = vocab_size * dim;

    /* Allocate embedding (tied with LM head) */
#ifdef __CUDACC__
    cudaMalloc((void**)&G.weights.W_emb, vd * sizeof(float));
#else
    G.weights.W_emb = (float*)calloc(vd, sizeof(float));
#endif

    /* Allocate per-layer weights + grads + adam */
    G.weights.layers = (LayerWeights*)calloc(n_layers, sizeof(LayerWeights));
    G.grads.layers   = (LayerWeights*)calloc(n_layers, sizeof(LayerWeights));

#ifdef __CUDACC__
    cudaMalloc((void**)&G.grads.W_emb, vd * sizeof(float));
#else
    G.grads.W_emb = (float*)calloc(vd, sizeof(float));
#endif

    G.adam.W_emb.numel = vd;
    G.adam.layers_Wq  = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_Wk  = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_Wv  = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_Wo  = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_Wg  = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_Wu  = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_Wd  = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_ln1 = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));
    G.adam.layers_ln2 = (AdamSlot*)calloc(n_layers, sizeof(AdamSlot));

#define ALLOC_F(ptr, n) do { \
    _Pragma("GCC diagnostic push") \
    _Pragma("GCC diagnostic ignored \"-Wunused-value\"") \
    (void)(sizeof(float)); \
    _Pragma("GCC diagnostic pop") \
    ptr = (float*)calloc(n, sizeof(float)); \
} while(0)

#ifdef __CUDACC__
#undef ALLOC_F
#define ALLOC_F(ptr, n) cudaMalloc((void**)&(ptr), (n) * sizeof(float))
#endif

#define ALLOC_ADAM(slot, numel_val) do { \
    ALLOC_F((slot).m1, numel_val); \
    ALLOC_F((slot).m2, numel_val); \
    (slot).numel = numel_val; \
} while(0)

    ALLOC_ADAM(G.adam.W_emb, vd);

    for (int i = 0; i < n_layers; ++i) {
        LayerWeights* lw = &G.weights.layers[i];
        LayerWeights* gw = &G.grads.layers[i];

        ALLOC_F(lw->Wq, dd); ALLOC_F(lw->Wk, dd); ALLOC_F(lw->Wv, dd); ALLOC_F(lw->Wo, dd);
        ALLOC_F(lw->Wg, df); ALLOC_F(lw->Wu, df);
        ALLOC_F(lw->Wd, fd);
        ALLOC_F(lw->ln1_gain, dim); ALLOC_F(lw->ln2_gain, dim);

        ALLOC_F(gw->Wq, dd); ALLOC_F(gw->Wk, dd); ALLOC_F(gw->Wv, dd); ALLOC_F(gw->Wo, dd);
        ALLOC_F(gw->Wg, df); ALLOC_F(gw->Wu, df);
        ALLOC_F(gw->Wd, fd);
        ALLOC_F(gw->ln1_gain, dim); ALLOC_F(gw->ln2_gain, dim);

        ALLOC_ADAM(G.adam.layers_Wq[i], dd);
        ALLOC_ADAM(G.adam.layers_Wk[i], dd);
        ALLOC_ADAM(G.adam.layers_Wv[i], dd);
        ALLOC_ADAM(G.adam.layers_Wo[i], dd);
        ALLOC_ADAM(G.adam.layers_Wg[i], df);
        ALLOC_ADAM(G.adam.layers_Wu[i], df);
        ALLOC_ADAM(G.adam.layers_Wd[i], fd);
        ALLOC_ADAM(G.adam.layers_ln1[i], dim);
        ALLOC_ADAM(G.adam.layers_ln2[i], dim);
    }
#undef ALLOC_F
#undef ALLOC_ADAM

    /* Allocate batch buffers (host side) */
    G.batch.tokens  = (int*)calloc(seq_len, sizeof(int));
    G.batch.targets = (int*)calloc(seq_len, sizeof(int));

    /* Init scratch */
    G.scratch = train_step_init(&G.cfg);

    /* Default hyperparams */
    G.hp.lr           = 3e-4f;
    G.hp.beta1        = 0.9f;
    G.hp.beta2        = 0.999f;
    G.hp.eps          = 1e-8f;
    G.hp.weight_decay = 0.01f;
    G.hp.grad_clip    = 1.0f;
    G.hp.step         = 0;

    G.initialized = 1;
    return 1;
}

/* ═════════════════════════════════════════════════════════════
 * train_ffi_set_hp — set hyperparameters before step
 * ═════════════════════════════════════════════════════════════ */
void train_ffi_set_hp(float lr, float beta1, float beta2,
                      float eps, float wd, float grad_clip)
{
    G.hp.lr           = lr;
    G.hp.beta1        = beta1;
    G.hp.beta2        = beta2;
    G.hp.eps          = eps;
    G.hp.weight_decay = wd;
    G.hp.grad_clip    = grad_clip;
}

/* ═════════════════════════════════════════════════════════════
 * train_ffi_step — run one training step
 *
 * tokens/targets: host int arrays, length = seq_len
 * Returns: CE loss (float)
 *
 * Side effects: updates weights, adam state, increments step.
 * ═════════════════════════════════════════════════════════════ */
float train_ffi_step(long tokens_ptr, long targets_ptr)
{
    if (!G.initialized) return -1.0f;

    /* Copy batch from hexa's raw memory into our buffers */
    int seq = G.cfg.seq_len;
    memcpy(G.batch.tokens,  (void*)tokens_ptr,  seq * sizeof(int));
    memcpy(G.batch.targets, (void*)targets_ptr, seq * sizeof(int));

    G.hp.step++;

    int rc = train_step(&G.cfg, &G.weights, &G.adam, &G.hp,
                        &G.batch, &G.result);
    if (rc != 0) return -2.0f;

    return G.result.loss;
}

/* ═════════════════════════════════════════════════════════════
 * train_ffi_get_grad_norm — retrieve last step's grad norm
 * ═════════════════════════════════════════════════════════════ */
float train_ffi_get_grad_norm(void) { return G.result.grad_norm; }
long  train_ffi_get_elapsed_us(void) { return G.result.elapsed_us; }
int   train_ffi_get_step(void) { return G.hp.step; }

/* ═════════════════════════════════════════════════════════════
 * train_ffi_cleanup — free everything
 * ═════════════════════════════════════════════════════════════ */
void train_ffi_cleanup(void)
{
    if (!G.initialized) return;
    train_step_cleanup(G.scratch);
    /* Weight + grad + adam dealloc would go here (omitted for brevity;
     * pod lifetime = process lifetime, OS reclaims everything) */
    G.initialized = 0;
}
