# Phase 2 — Smoke 20-step (TCLM-P1-1 NL=8)

## Result: PASS

## Build Pipeline
- compose: concat cuda_ffi + cuda_rtc + cuda_kernels + gpu_train + corpus_loader + train_clm_d64_kr_nl8 (strip `use ` lines) → 5050 hexa lines
- transpile: `./hexa_v2 composed.hexa composed.c` → 4803 C lines
- emitted C patches (post-transpile, via `patch_composed.py`):
  1. `hexa_call1(env, ...)` in `env_or` → `hexa_env_var(...)` (env builtin dispatch)
  2. In `int main()` body: `return hexa_void();` → `return 0;` (4 occurrences — FATAL bailouts)
  3. `tensor_from_gpu` body rewritten — materialize hexa float array via `cuda_memcpy_d2h` + `hexa_ptr_read_f32` + `hexa_array_push(hexa_float(...))` (identical to prior TCLM-P1-1 fix)
- compile: `clang -O2 -D_GNU_SOURCE -std=gnu11 -Wno-trigraphs ... -lcuda -lcudart -lcublas -lnvrtc -lm -ldl`
- binary: `train_clm_nl8` 645848 bytes

## Important runtime note — LD_LIBRARY_PATH
- First run with `export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64/stubs:...` → `cuInit failed: 34`
- Removing LD_LIBRARY_PATH (letting libcuda.so.1 resolve from /lib/x86_64-linux-gnu) → works
- Root cause: the `lib64/stubs/libcuda.so` shadowed the real driver lib; stubs fail at runtime
- Mitigation: run training with `unset LD_LIBRARY_PATH` (inherited from shell)

## 20-step Run
- env: `CLM_STEPS=20 CLM_LOG_EVERY=1 CLM_SAVE_EVERY=20 CLM_EVAL_EVERY=10 CLM_WARMUP=5`
- NVRTC cache MISS on first run (PTX 49032 bytes, 20 entry points) — compiled in ~0.3s
- CUBLAS_TENSOR_OP_MATH enabled (H100 tensor cores)

## Metrics
- step range: 1..20
- loss range: 5.71 → 5.46 (−0.25 delta at WARMUP=5, 20 steps — learning confirmed)
- eval@20: PPL=234.77 kr_acc=-1/16 (stub)
- phi_proxy@20: 100.93 (post-init baseline = INIT_SCALE=0.1 → var≈0.01 → ×10000 = 100, trivially advanced)
- total wall: 6.77s (includes NVRTC compile + init ~1s)
- **steady-state s/step (last 10): ~0.041** (identical to NL=6 baseline — per-step time unchanged by +2 layers)
- NL=8 tensor count: **67 tensors** per checkpoint (vs. NL=6 baseline 51 tensors; delta +16 = 8 layer extras: Q/K/V/O_low+high × 2 new layers)
- checkpoint size: 4.22 MB (vs. baseline 3.2 MB — +32% for NL=8)
- kernel launch errors: **0**
- R2 upload verified: `r2:anima-models/clm-d64-kr/r2-nl8/step_20/{step_20,final}.hexackpt`

## GATE
- step time > 500ms OR kernel launch error > 0 → ABORT
- 41 ms/step steady-state (<< 500ms), 0 launch errors → **APPROVED**
- Phase 3 entry: skipped per spec (smoke-style run; go direct to 50K)
