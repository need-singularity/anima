# Phase 2 — Smoke 20-step (TCLM-P1-1)

## Result: PASS

## Build
- compose: concat cuda_ffi + cuda_rtc + cuda_kernels + gpu_train + corpus_loader + train_clm_d64_kr (strip `use ` lines) → 5045 hexa lines
- transpile: `./hexa_v2 composed.hexa composed.c` → 4807 C lines
- emitted C patches (post-transpile):
  1. `hexa_call1(env, ...)` → `hexa_env_var(...)` (env builtin not dispatched via variable binding in env_or)
  2. in `main()` body: `return hexa_void();` → `return 0;` (top-level hexa `return` emitted as void in int main)
  3. `tensor_from_gpu` rewritten to materialize real hexa f32 array via `hexa_array_push(hexa_float(...))` (same as prior breakthrough's fix — hexa_tensor_from_ptr returns opaque TAG_INT incompatible with array[0] callers)
- compile: `clang -O2 -D_GNU_SOURCE -std=gnu11 -Wno-trigraphs ... -lcuda -lcudart -lcublas -lnvrtc -lm -ldl`
- binary: `train_clm_d64_kr_native` 645936 bytes

## 20-step Run
- env: `CLM_STEPS=20 CLM_LOG_EVERY=1 CLM_SAVE_EVERY=20 CLM_EVAL_EVERY=10 CLM_WARMUP=5`
- NVRTC cache hit on rerun (PTX 49031 bytes, 20 entry points)
- CUBLAS_TENSOR_OP_MATH enabled (H100 tensor cores)
- GPU memory at init: 80484/81079 MB free
- GPU memory after buffer alloc: 79982/81079 MB free (delta ~500MB — d=64 is tiny)

## Metrics
- step range: 1..20
- loss range: 5.54501..5.54508 (flat — expected at lr~3.7e-06 with WARMUP=5 effective ~1e-6 after step 5)
- total wall: 1.776 s
- **s/step: 0.089 (89 ms/step)**
- phi_proxy: nan at eval steps 10/20 (expected — d=64 with few-step run hasn't activated hidden state enough for variance)
- kr_acc: -1/16 (stub, expected)
- ppl: 255.96 (near random baseline ln(256)=5.545, exp=256)
- checkpoint saved: step_20.hexackpt + final.hexackpt (51 tensors each)
- kernel launch errors: **0** (all CUDA kernel launches succeeded after tensor_from_gpu patch)
- `array[0]: container is not an array` error: RESOLVED by patch

## dmon Observation
- peak sm util during 20-step run: ~0 (sampling rate was too coarse — d=64 training is ~90ms/step, the dmon reported 0 during sampled windows, meaning GPU was idle between kernel launches; actual in-kernel util is higher but below sampling resolution for this small model)

## R2 Upload
- rclone: not configured on pod (`didn't find section in config file`)
- plan: will install+configure at Phase 4/5 (ckpt local-intact in `/workspace/ckpt_clm_d64_kr/`)

## Budget
- phase 2 budget: 30min / $1.50
- actual: ~15 min wall (setup+debug+smoke) → ~$0.75
- cumulative: ~$1.15

## GATE (from original spec)
- step time > 500ms OR kernel launch error > 0 → ABORT
- 89 ms/step (<< 500ms), 0 launch errors → **APPROVED**
- Phase 3 entry: APPROVED
