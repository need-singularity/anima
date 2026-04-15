# H100 CLM hexa-native — cuLaunchKernelEx INVALID_VALUE root cause + fix

**Date**: 2026-04-16  **Pod**: xhq9b2c8fljdyo (H100 SXM 80GB, CUDA 12.4)
**Budget**: ~40 min / $1.50  **Outcome**: BREAKTHROUGH — 20-step 완주, SM util peak 27%

## TL;DR

The bug was NOT in `cuLaunchKernelEx` args marshaling or the `CUlaunchConfig` byte layout. Both are correct. The root cause was a **hexa codegen_c2 implicit-return quirk** that emitted `<expr>; return hexa_void();` for any fn whose last line was an expression — silently dropping the return value.

This manifested as:
- `_ceil_div(a, b)` → returned VOID instead of `(a+b-1)/b` → `gx = VOID` → downstream `write_i32(cfg, 0, gx)` wrote 0 → `cuLaunchKernelEx` got `gridDimX = 0` → `CUDA_ERROR_INVALID_VALUE (=1)` on every one of 112+ launches.
- `rtc_launch` / `rtc_launch_1d` → same pattern, dropped the delegated launch status.
- `tensor_from_gpu` → returned TAG_INT (opaque pointer from `hexa_tensor_from_ptr`) where callers used `hexa_index_get(host, 0)` expecting TAG_ARRAY → panic `array[0]: container is not an array (tag=0)`.

## Diagnostic method (10 min)

1. Verified `CUlaunchConfig` struct layout on pod with a C sizeof/offsetof probe — exactly matches hexa's hand-coded 56-byte layout (fields at off 0, 4, 8, 12, 16, 20, 24, 32, 40, 48 ; sizeof = 56).
2. Ran a pure-C minimal smoke (`/tmp/minlaunch.c`) replicating hexa's exact param-buffer pattern (`void** params; params[i] = &arg_slot`). All three paths worked: `cuLaunchKernel`, `cuLaunchKernelEx` with C-struct `CUlaunchConfig`, and `cuLaunchKernelEx` with hand-packed 56-byte struct. → Struct layout and marshaling not the bug.
3. Injected a **one-shot fprintf** into the emitted `rtc_launch_shmem` in `train_clm_composed.c` to dump the actual bytes of `cfg` and the contents of `params_buf[i]` at the first launch:
   ```
   cfg bytes: 00 00 00 00 01 00 00 00 01 00 00 00 00 01 00 00 ...
              └ gridDimX=0 ┘ └ gridDimY=1 ┘ └ gridDimZ=1 ┘ └ blockDimX=256 ┘
   ```
4. `gridDimX = 0` ⇒ traced back to `_ceil_div(N=131072, 256)` which should yield 512 but returned VOID.

## Root cause analysis

In `train_clm_composed.c` (emitted by `hexa_cc.c` → `codegen_c2`), fn bodies ending in a bare expression produced:

```c
HexaVal _ceil_div(HexaVal a, HexaVal b) {
    hexa_div(hexa_sub(hexa_add(a, b), hexa_int(1)), b);   // <-- value computed & discarded
    return hexa_void();                                   // <-- returns VOID
}
```

Hexa source was ambiguous about this:
```hexa
fn _ceil_div(a, b) {
    (a + b - 1) / b     // implicit-return last expression
}
```

The prior session's patch #2 (`<expr>; return hexa_void();` → `return <expr>;`) only caught some cases because its regex was narrow. The three functions that mattered most (`_ceil_div`, `rtc_launch`, `rtc_launch_1d`) slipped through.

Additional bug: `tensor_from_gpu(dev, n)` calls `hexa_tensor_from_ptr(host, 1, n)` which returns an opaque `TAG_INT` pointer to a `HexaTensorStub` — but every caller does `hexa_index_get(host, 0)` expecting a real array. The interpreter must resolve tensor-indexing via some overload; native codegen does not.

## Fix

Applied to `/workspace/cuda_native/train_clm_composed.c` on the pod:

1. Regex-sweep emitted C to convert `    <Fn>(<args>);\n    return hexa_void();\n}` → `    return <Fn>(<args>);\n}`, skipping void-only sinks (`cudaMemset`, `hexa_println`, `fprintf`, `cudaStream*`, `*_set`, `write_*`, `free*`, etc.). 4 functions rewritten: `_ceil_div`, `rtc_launch`, `rtc_launch_1d`, `rtc_cache_path`.

2. Rewrite `tensor_from_gpu` body to materialize a real hexa array of floats (reading f32 from the host buffer via a plain C for-loop and pushing `hexa_float(...)` into a new hexa array).

Locally updated `~/Dev/hexa-lang/self/ml/cuda_rtc.hexa` with explicit `return` on `rtc_launch` / `rtc_launch_1d` as a workaround until codegen_c2 learns implicit-return. (NOT committed to hexa main per instructions.)

## Results

```
[train_clm_kr] training start — STEPS=20
[train_clm_kr] step=1  loss=5.5449 lr=7.5e-08 elapsed=0.27s
[train_clm_kr] step=20 loss=5.5467 lr=1.5e-06 elapsed=4.18s
[train_clm_kr] s/step = 0.209
```

`nvidia-smi dmon -s u` during a 20-step run:

```
#  sm  mem
   0    0
  24    2
  25    2
  27    2    ← peak
  25    2
  27    2
   0    0
```

SM peak = 27%. Loss flat — **expected** — because `lr` at step 20 with `WARMUP=500 LR_MAX=3e-4` is `1.5e-6`, far too low to see any drop in 20 steps. This is a schedule artifact, not a training-correctness bug.

## Final summary table

| 지표 | 값 |
|---|---|
| root cause | codegen_c2 implicit-return drop (NOT args_array, NOT CUlaunchConfig) |
| 수정 방식 | emitted C regex patch + tensor_from_gpu body rewrite; hexa source explicit `return` workaround on rtc_launch/_1d |
| kernel launch status | PASS (100% — every launch across init + 20 training steps) |
| 20-step run | PASS |
| step 평균 (ms) | 209 |
| GPU SM util peak | 27% |
| 판정 | BREAKTHROUGH |

## Artifacts

- `/Users/ghost/Dev/hexa-lang/self/ml/cuda_rtc.hexa` — rtc_launch/_1d explicit return (uncommitted)
- Pod `/workspace/cuda_native/train_clm_native_final` — working 825KB binary
- Pod `/workspace/cuda_native/train_clm_composed.c` — patched composed C
- Pod `/workspace/ckpt_clm_byte_kr/final.hexackpt` — saved 99-tensor checkpoint

## Remaining follow-ups (outside this window)

1. **codegen_c2** proper fix: teach `hexa_cc.c` / `codegen_c2.hexa` to emit `return <expr>;` for fns whose body's last statement is a bare expression. The regex workaround is brittle across future kernel additions.
2. **tensor_from_gpu native semantics**: either `hexa_tensor_from_ptr` should return a TAG_ARRAY-equivalent (with `hexa_array_get` dispatch on tensor) OR `tensor_from_gpu` should always materialize as hexa array (current fix).
3. **Loss convergence sanity**: run STEPS=2000+ to verify that with real warmup, loss actually drops (Hexa-native path produces mathematically-equivalent gradients to interpreter path). Not attempted in this window.
4. **MFU**: 27% SM util at D=512 SEQ=512 is modest. Compared to the 989 TFLOPS bf16 ceiling and our ~209ms/step at ~60M params, actual MFU is probably ~5-10%. Headroom comes from (a) cuBLAS sgemm vs bf16 Tensor Core (CUBLAS_TENSOR_OP_MATH is set but fp32 compute throughput is only ~67 TFLOPS bf16 equivalent on H100), (b) many small kernel launches instead of fused mega-kernels.

## Budget

- Elapsed: ~40 min (under 45-min cap)
- Pod cost: ~$1.50 additional (pod preserved per directive)
- No new pods created, no pod deleted
