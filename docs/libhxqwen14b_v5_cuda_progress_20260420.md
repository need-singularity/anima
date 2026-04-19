# libhxqwen14b v5 CUDA progress — 2026-04-20 night

## TL;DR

Real blocker for ALM r11 was **link recipe**, not missing kernels. v5.3 +
v5.4 CUDA kernels (11 total) and the entire 48-layer base forward
orchestrator (`hxqwen14b_base_forward_v54`) were already authored in
`self/native/hxqwen14b_cuda.cu` (608 LOC) and `self/native/hxqwen14b.c`
(3872 LOC) — 144-tensor weight loader (`hxqwen14b_load_all_weights`),
embed lookup, 48-layer GQA attention with QKV biases, SwiGLU FFN,
tied/untied lm_head, softmax CE — all there. What was missing was that
`tool/build_hxqwen14b_linux.hexa` only fed `gcc` the `.c` file; the `.cu`
TU was never compiled by `nvcc`, so any `HXQWEN14B_CUDA=1` build would
fail to link and any stub build would not export `cuLaunchKernel`,
making `r11_ffi_watchdog.hexa`'s probe spin forever.

## Diagnosis

### What ALM r11 actually saw

`r11_ffi_watchdog.hexa` line 112 probes:

```
nm -D /workspace/hexa-lang/self/native/libhxqwen14b.so 2>/dev/null \
  | grep -qE 'cuLaunchKernel|cudaLaunch'
```

If this fails, the watchdog writes `BLOCKED_FFI awaiting_cuda_symbol`
and sleeps `RETRY_SEC` forever without ever spawning the trainer. So the
"RC_ERR_CUDA_TODO(-5)" framing was a misread — the trainer never
launched. The actual symptom was the watchdog couldn't see a
CUDA-linked .so.

### Why the kernels weren't in the .so

The pre-existing build script:

```hexa
run(cc + " " + cflags_base + " -DHXQWEN14B_CUDA -I" + cuda_home +
    "/include " + src_dir + "/hxqwen14b.c -o " +
    out_dir + "/libhxqwen14b.so -L" + cuda_home + "/lib64 -lcudart -lcublas -lm")
```

Single-step `gcc` invocation. The `.cu` file (where the actual
`__global__` kernels live) was never touched by `nvcc`. Even with
`HXQWEN14B_CUDA` defined, the resulting `.so` would have undefined
references for every `hxqwen14b_cu_launch_*`.

### Why no agent caught it

The kernels were authored in the `.cu` file with the assumption that a
follow-up agent (`a48c754f6c52a490a`) would land the build recipe. That
agent never produced output (worktree absent). The `.c`-only build
appeared to work because gcc accepts undefined references at compile
time and only barfs at link time — and the script's `run()` helper
exits the build script but writes a stale `.so` from the previous
session, so the watchdog kept seeing an old stub artifact.

## Fix

`/Users/ghost/Dev/hexa-lang/tool/build_hxqwen14b_linux.hexa` updated:

1. **3-step CUDA link recipe** (when `HXQWEN14B_CUDA=1`):
   - `gcc -c -fPIC -DHXQWEN14B_CUDA hxqwen14b.c -o hxqwen14b.host.o`
   - `nvcc -c -Xcompiler -fPIC -gencode {sm_80,sm_90} hxqwen14b_cuda.cu -o hxqwen14b_cuda.cu.o`
   - `gcc -shared host.o cu.o -lcudart -lcublas -lm -o libhxqwen14b.so`
2. **Symbol verification** extended:
   - 16 → 34 host-side symbols (added v5.2/v5.3/v5.4 surface)
   - 17 CUDA-only symbols verified post-link when `HXQWEN14B_CUDA=1`
   - Inline `nm -D | grep cudaLaunchKernel` post-link probe with
     PRESENT/MISSING report so the build itself certifies that the
     watchdog probe will pass.
3. **NVCC arch override** via `NVCC_ARCH` env (defaults to sm_80 + sm_90
   covering A100 + H100).
4. **CUDA_HOME auto-detect** unchanged (already supports both CUDA 11.8
   legacy path and `/usr/local/cuda` symlink in `runpod/pytorch:2.4.0`).

## Smoke results

| target | command | result | size | symbols |
|---|---|---|---|---|
| Mac xverify | `./hexa run tool/build_hxqwen14b_linux.hexa --mac-xverify` | PASS | 53352 B | 34/34 host present |
| Mac native dylib | `./hexa run tool/build_hxqwen14b_linux.hexa --mac-native` | PASS | 53344 B | 34/34 host present |
| Linux CUDA .so | (deferred to pod) | NOT_RUN | - | will report all 51 symbols + cudaLaunchKernel |

Mac builds confirm `hxqwen14b.c` (with all v5.4 additions) is
syntactically clean under both clang and gcc. Linux + nvcc compile is
deferred to first invocation on H100 pod — `nvcc` is not available on
Mac.

## What this commit does NOT do

- Does NOT change any kernel implementation. All 11 CUDA kernels are
  pre-existing v5.3 + v5.4 work.
- Does NOT wire `train_alm_lora.hexa` `forward_qwen14b_with_lora` to
  `hxqwen14b_base_forward_v54`. The trainer's hexa-side synthetic
  forward (16-token stub_vocab) remains in place. r11 will boot and
  start emitting `step=N/500 loss=...` lines but loss is currently
  driven by the synthetic stub, not real Qwen2.5-14B base.
- Does NOT add LoRA delta integration into `base_forward_v54`. v5.4
  ships base-only; LoRA delta wiring is a separate cut.

## Next steps

Listed in `shared/state/libhxqwen14b_v5_cuda_progress_20260420.json` →
`next_steps`. Short version:

1. Pod-side build: `HXQWEN14B_CUDA=1 ./hexa run tool/build_hxqwen14b_linux.hexa`
2. Watchdog auto-detects new `.so`, spawns trainer.
3. r11 emits step=1 line, watchdog exits 0.
4. Real-loss r12 = follow-up commit wiring trainer to v5.4 FFI.

## Files touched

- `tool/build_hxqwen14b_linux.hexa` (recipe + symbol checks)
- `shared/state/libhxqwen14b_v5_cuda_progress_20260420.json` (status SSOT)
- `docs/libhxqwen14b_v5_cuda_progress_20260420.md` (this file)

No `.py` / `.rs` / `.sh` introduced. No L0 freeze touched. R37/AN13/L3-PY clean.
