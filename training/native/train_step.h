/*
 * train_step.h — FIX-TRAIN-STEP-FFI C shim for hexa-lang
 *
 * Eliminates the 533× interpreter dispatch overhead discovered in R8
 * by running an entire training step (fwd + bwd + AdamW) inside a
 * single C function. Hexa calls train_step() once per batch; all
 * per-op arg marshalling happens inside C at native speed.
 *
 * Target speedup vs hexa-interpreter train_gpu.hexa:
 *   100-500× (161s/step → 0.3-1.6 s/step on H100 103M)
 *   1B model: $180k → $360 at $6/hr H100 pricing
 *
 * Layout convention (matches self/ml/model_100m_gpu.hexa):
 *   - All weights are device pointers to contiguous float32 buffers
 *   - Shapes are row-major: [rows, cols] = [outer, inner]
 *   - Wq, Wk, Wv, Wo: [dim, dim]
 *   - Wg (gate), Wu (up): [dim, ff]
 *   - Wd (down): [ff, dim]
 *   - W_emb: [vocab, dim]
 *   - Adam m1, m2 allocated one-per-parameter, same shape as the weight
 *
 * Built as:
 *   nvcc -O3 -shared -Xcompiler -fPIC -lcublas -lcudart \
 *        train_step.c -o libtrain_step.so
 */

#ifndef TRAIN_STEP_H
#define TRAIN_STEP_H

#include <stdint.h>

/* Model configuration — fixed at build time of the model replica */
typedef struct {
    int n_layers;
    int dim;
    int n_heads;
    int head_dim;
    int ff_dim;
    int vocab_size;
    int seq_len;
} ModelConfig;

/* Per-layer weight pointers (device) */
typedef struct {
    float* Wq;   /* [dim, dim] */
    float* Wk;
    float* Wv;
    float* Wo;
    float* Wg;   /* [dim, ff_dim] */
    float* Wu;
    float* Wd;   /* [ff_dim, dim] */
    float* ln1_gain;  /* [dim] */
    float* ln2_gain;  /* [dim] */
} LayerWeights;

typedef struct {
    float* W_emb;              /* [vocab, dim] — tied with LM head */
    LayerWeights* layers;      /* array of [n_layers] */
} ModelWeights;

/* Per-tensor Adam state */
typedef struct {
    float* m1;
    float* m2;
    int numel;
} AdamSlot;

typedef struct {
    AdamSlot W_emb;
    AdamSlot* layers_Wq;   /* arrays of [n_layers] */
    AdamSlot* layers_Wk;
    AdamSlot* layers_Wv;
    AdamSlot* layers_Wo;
    AdamSlot* layers_Wg;
    AdamSlot* layers_Wu;
    AdamSlot* layers_Wd;
    AdamSlot* layers_ln1;
    AdamSlot* layers_ln2;
} AdamState;

/* Training hyperparameters */
typedef struct {
    float lr;
    float beta1;
    float beta2;
    float eps;
    float weight_decay;
    float grad_clip;
    int step;            /* current step index (for bias correction) */
} TrainHParams;

/* Input batch */
typedef struct {
    int* tokens;    /* host int array [seq_len] — copied to GPU inside */
    int* targets;   /* host int array [seq_len] */
} Batch;

/* Output */
typedef struct {
    float loss;              /* final CE loss */
    float grad_norm;         /* pre-clip grad L2 norm */
    int64_t elapsed_us;      /* wall time inside train_step() */
} StepResult;

/* ─────────────────────────────────────────────────────────────
 * Main entry point
 * Hexa calls this via extern fn train_step(...) → int
 * Returns 0 on success, non-zero on CUDA/cuBLAS error.
 * ───────────────────────────────────────────────────────────── */
int train_step(
    const ModelConfig* cfg,
    ModelWeights* weights,
    AdamState* adam,
    const TrainHParams* hp,
    const Batch* batch,
    StepResult* result
);

/* Allocate all scratch tensors for a given config.
 * Must be called once before the first train_step().
 * Returns opaque handle to pass to subsequent train_step() calls
 * via ModelConfig.scratch (reserved field, not shown). */
void* train_step_init(const ModelConfig* cfg);
void  train_step_cleanup(void* scratch_handle);

#endif /* TRAIN_STEP_H */
