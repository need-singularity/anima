// hxvdsp_wrapper.c — hexa FFI ↔ Accelerate vDSP ABI shim
//
// Why this exists:
//   Mac M3 CLM training inner loops (rms_norm, softmax, swiglu) run as scalar
//   boxed-int arithmetic through hexa_v2 interpreter, and even after the attn
//   BLAS port (2026-04-16, commit 891f7582 1.69x) these eltwise ops remain the
//   BLAS-bound crossover blocker. Expected uplift: 5-20x across small shapes.
//
//   This wrapper presents per-row/per-tensor functions that fuse multiple vDSP
//   calls + vvexpf into single FFI hops, avoiding hexa per-element FFI overhead
//   (which was measured ~10-100µs in #32 sweep).
//
//   ABI matches hxblas_wrapper.c:
//     hexa Float → C double; hexa int → C int64_t; hexa ptr → int64_t address.
//
// Build (Mac arm64):
//   clang -O3 -dynamiclib -framework Accelerate \
//     training/hxvdsp_wrapper.c -o training/build/libhxvdsp.dylib
//
// Version: 1 (2026-04-16)

#include <Accelerate/Accelerate.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>

int64_t hxvdsp_version(void) { return 1; }

// ─────────────────────────────────────────────────────────────
// RMSNorm forward — whole tensor [S, D], per row
//   out[i,p] = x[i,p] * inv_rms(x[i,:]) * gain[p]
// ─────────────────────────────────────────────────────────────
void hxvdsp_rmsnorm_fwd(int64_t S, int64_t D,
                        int64_t x_ptr, int64_t gain_ptr,
                        double eps,
                        int64_t out_ptr) {
    const float* x = (const float*)(uintptr_t)x_ptr;
    const float* g = (const float*)(uintptr_t)gain_ptr;
    float* out = (float*)(uintptr_t)out_ptr;
    const vDSP_Length n = (vDSP_Length)D;
    const float eps_f = (float)eps;
    const float inv_D = 1.0f / (float)D;
    for (int64_t i = 0; i < S; i++) {
        const float* xi = x + i * D;
        float* oi = out + i * D;
        float ss = 0.0f;
        vDSP_svesq(xi, 1, &ss, n);              // sum(x²)
        float ms = ss * inv_D;
        float inv_r = 1.0f / sqrtf(ms + eps_f);
        vDSP_vsmul(xi, 1, &inv_r, oi, 1, n);    // oi = xi * inv_r
        vDSP_vmul(oi, 1, g, 1, oi, 1, n);       // oi = oi * gain
    }
}

// ─────────────────────────────────────────────────────────────
// RMSNorm backward — whole tensor [S, D], per row
//   Accumulates dg across rows (caller zeros dg_accum before call)
// ─────────────────────────────────────────────────────────────
void hxvdsp_rmsnorm_bwd(int64_t S, int64_t D,
                        int64_t x_ptr, int64_t gain_ptr, int64_t dy_ptr,
                        double eps,
                        int64_t dx_ptr, int64_t dg_ptr) {
    const float* x  = (const float*)(uintptr_t)x_ptr;
    const float* g  = (const float*)(uintptr_t)gain_ptr;
    const float* dy = (const float*)(uintptr_t)dy_ptr;
    float* dx = (float*)(uintptr_t)dx_ptr;
    float* dg = (float*)(uintptr_t)dg_ptr;
    const vDSP_Length n = (vDSP_Length)D;
    const float eps_f = (float)eps;
    const float inv_D = 1.0f / (float)D;

    float* scratch = (float*)malloc((size_t)D * sizeof(float));
    float* term1   = (float*)malloc((size_t)D * sizeof(float));

    for (int64_t i = 0; i < S; i++) {
        const float* xi  = x  + i * D;
        const float* dyi = dy + i * D;
        float* dxi       = dx + i * D;
        float ss = 0.0f;
        vDSP_svesq(xi, 1, &ss, n);
        float ms = ss * inv_D;
        float r = sqrtf(ms + eps_f);
        float inv_r = 1.0f / r;
        float inv_r3 = inv_r * inv_r * inv_r;

        // coef = dot(x*g, dy)
        vDSP_vmul(xi, 1, g, 1, scratch, 1, n);          // scratch = x*g
        float coef = 0.0f;
        vDSP_dotpr(scratch, 1, dyi, 1, &coef, n);       // coef = Σ x*g*dy

        // term1 = g * dy * inv_r
        vDSP_vmul(g, 1, dyi, 1, term1, 1, n);           // term1 = g*dy
        vDSP_vsmul(term1, 1, &inv_r, term1, 1, n);      // term1 *= inv_r

        // term2 = x * (coef * inv_r3 / D)
        float k = coef * inv_r3 * inv_D;
        vDSP_vsmul(xi, 1, &k, scratch, 1, n);           // scratch = x*k (reuse)

        // dxi = term1 - scratch
        vDSP_vsub(scratch, 1, term1, 1, dxi, 1, n);     // dxi = term1 - scratch

        // dg += x * dy * inv_r
        vDSP_vmul(xi, 1, dyi, 1, scratch, 1, n);        // scratch = x*dy
        vDSP_vsmul(scratch, 1, &inv_r, scratch, 1, n);  // scratch *= inv_r
        vDSP_vadd(dg, 1, scratch, 1, dg, 1, n);         // dg += scratch
    }
    free(scratch);
    free(term1);
}

// ─────────────────────────────────────────────────────────────
// Softmax row (in-place) — single row of length n
//   scores[i] := exp(scores[i] - max) / Σ
// ─────────────────────────────────────────────────────────────
void hxvdsp_softmax_row(int64_t x_ptr, int64_t row_offset_f32, int64_t n) {
    float* x = ((float*)(uintptr_t)x_ptr) + row_offset_f32;
    const vDSP_Length len = (vDSP_Length)n;
    int nn = (int)n;
    float mx = 0.0f;
    vDSP_maxv(x, 1, &mx, len);
    float neg_mx = -mx;
    vDSP_vsadd(x, 1, &neg_mx, x, 1, len);
    vvexpf(x, x, &nn);
    float sum = 0.0f;
    vDSP_sve(x, 1, &sum, len);
    float inv = 1.0f / sum;
    vDSP_vsmul(x, 1, &inv, x, 1, len);
}

// ─────────────────────────────────────────────────────────────
// SwiGLU-self forward — whole tensor, out[i] = up[i] * sigmoid(up[i])
// ─────────────────────────────────────────────────────────────
void hxvdsp_swiglu_fwd(int64_t n,
                       int64_t up_ptr, int64_t out_ptr) {
    const float* up = (const float*)(uintptr_t)up_ptr;
    float* out = (float*)(uintptr_t)out_ptr;
    const vDSP_Length len = (vDSP_Length)n;
    int nn = (int)n;

    // out = sigmoid(up) = 1/(1 + exp(-up))
    float neg_one = -1.0f;
    vDSP_vsmul(up, 1, &neg_one, out, 1, len);   // out = -up
    vvexpf(out, out, &nn);                      // out = exp(-up)
    float one = 1.0f;
    vDSP_vsadd(out, 1, &one, out, 1, len);      // out = 1 + exp(-up)
    vvrecf(out, out, &nn);                      // out = 1 / (1 + exp(-up)) = sigmoid
    vDSP_vmul(up, 1, out, 1, out, 1, len);      // out = up * sigmoid(up)
}

// ─────────────────────────────────────────────────────────────
// SwiGLU-self backward — whole tensor
//   dx[i] = dy[i] * (s + up[i]*s*(1-s))   where s = sigmoid(up[i])
// ─────────────────────────────────────────────────────────────
void hxvdsp_swiglu_bwd(int64_t n,
                       int64_t up_ptr, int64_t dy_ptr, int64_t dx_ptr) {
    const float* up = (const float*)(uintptr_t)up_ptr;
    const float* dy = (const float*)(uintptr_t)dy_ptr;
    float* dx = (float*)(uintptr_t)dx_ptr;
    const vDSP_Length len = (vDSP_Length)n;
    int nn = (int)n;

    float* s    = (float*)malloc((size_t)n * sizeof(float));
    float* tmp  = (float*)malloc((size_t)n * sizeof(float));

    // s = sigmoid(up)
    float neg_one = -1.0f;
    vDSP_vsmul(up, 1, &neg_one, s, 1, len);
    vvexpf(s, s, &nn);
    float one = 1.0f;
    vDSP_vsadd(s, 1, &one, s, 1, len);
    vvrecf(s, s, &nn);

    // tmp = up * s  (= up*s)
    vDSP_vmul(up, 1, s, 1, tmp, 1, len);
    // dx = tmp * s  (= up*s²) — use dx as scratch
    vDSP_vmul(tmp, 1, s, 1, dx, 1, len);
    // tmp = tmp - dx  (= up*s - up*s² = up*s*(1-s))
    vDSP_vsub(dx, 1, tmp, 1, tmp, 1, len);
    // s = s + tmp  (= s + up*s*(1-s))
    vDSP_vadd(s, 1, tmp, 1, s, 1, len);
    // dx = dy * s
    vDSP_vmul(dy, 1, s, 1, dx, 1, len);

    free(s);
    free(tmp);
}
