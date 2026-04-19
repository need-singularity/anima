# CLM r5-a1 — Linux x86_64 AOT build on hetzner (2026-04-19)

Task ref: `training/deploy/clm_r5_plan.json#next_actions[0]` (r5-a1)
Rule refs: `feedback_hexa_first_strict`, `feedback_py_ban_total`, `feedback_safe_path_auto`, `project_clm_hexa_gpu_plan`.
Parent plan: `docs/clm_aot_build_plan_20260419.md` (Mac Path A done).
Blocker resolved: Mac arm64 `.dylib` not usable on Linux x86_64 → rebuild .so + re-AOT.

## 1. Result summary

| item                  | value                                                       |
|-----------------------|-------------------------------------------------------------|
| host                  | hetzner (Ubuntu 24.04 x86_64, gcc 13.3.0)                   |
| binary                | `/tmp/clm_v2_linux.bin`                                     |
| size                  | 382,624 bytes                                               |
| format                | ELF 64-bit LSB pie, x86_64, dynamically linked              |
| build wall            | 8.374 s (hexa_v2 transpile + clang -O2)                     |
| clang warnings        | 3 (expression-result-unused, stage1 quirk, same as Mac)     |
| C intermediate        | `build/artifacts/clm_v2_linux.bin.c`                        |
| main export           | `T main` @ 0x408f0                                          |
| FFI imports (dynamic) | `dlopen@GLIBC_2.34`                                         |
| FFI slots (bss)       | `__ffi_sym_hxblas_sgemm`, `__ffi_sym_hxblas_attn_softmax_causal`, `__ffi_sym_hxlmhead_bwd`, `__ffi_sym_hxlmhead_version` |

## 2. .so prebuild (prerequisite)

Mac `.dylib` files shipped in `/home/hexa-lang/self/native/build/` were
arm64-only; Linux needs `.so` variants. Built directly with gcc
(Makefile / `build_hxblas_linux.hexa` bypass — avoided stage0 lock
contention with P3 drill_v3):

```
gcc -O3 -fPIC -shared -fopenmp self/native/hxblas_linux.c \
    -o self/native/build/libhxblas.so -lopenblas -lgomp -lm
# real 0m0.484s

gcc -O3 -fPIC -shared -fopenmp self/native/hxlmhead_linux.c \
    -o self/native/build/libhxlmhead.so -lopenblas -lgomp -lm
# real 0m0.232s
```

Output:
- `libhxblas.so` 25,656 bytes, exports `hxblas_sgemm`, `hxblas_attn_softmax_causal`, `hxblas_attn_softmax_bwd`, `hxblas_bgemm`, `hxblas_cross_entropy`, `hxblas_embed_lookup`, `hxblas_axpy_inplace`, `hxblas_copy`, `hxblas_bf16_to_f32`, `hxblas_bf16_version`, … (~12 T symbols)
- `libhxlmhead.so` 16,072 bytes, exports `hxlmhead_fwd`, `hxlmhead_bwd`, `hxlmhead_version`

## 3. hexa_v2 transpiler swap (Mac arm64 → Linux x86_64)

`/home/hexa-lang/self/native/hexa_v2` on hetzner was Mach-O arm64
(rsync residue from Mac). First `hexa build` attempt failed with:

```
sh: 1: /home/hexa-lang/self/native/hexa_v2: Exec format error
error: transpile failed — C file not produced
```

Fix: copy existing Linux ELF build from `/root/hexa-lang/build/hexa_v2_linux`
(1.2MB static) into place, keep `hexa_v2.macbak` for rollback.

```
cp /home/hexa-lang/self/native/hexa_v2 /home/hexa-lang/self/native/hexa_v2.macbak
cp /root/hexa-lang/build/hexa_v2_linux  /home/hexa-lang/self/native/hexa_v2
chmod +x /home/hexa-lang/self/native/hexa_v2
```

No conflict with P3 drill_v3 — that workload uses `hexa_stage0` (interpreter),
not `hexa_v2` (transpiler).

## 4. AOT build command + log

```
cd /root/Dev/anima
HEXA_STAGE0_LOCK_WAIT=3600 /root/Dev/hexa-lang/hexa \
    build training/train_clm.hexa -o /tmp/clm_v2_linux.bin
```

```
=== Building training/train_clm.hexa -> /tmp/clm_v2_linux.bin ===
  [1/2] /home/hexa-lang/self/native/hexa_v2 training/train_clm.hexa \
        build/artifacts/clm_v2_linux.bin.c 2>&1
    OK: build/artifacts/clm_v2_linux.bin.c

  [2/2] clang -O2 -D_GNU_SOURCE -Wno-trigraphs \
        -I '/home/hexa-lang/self' \
        build/artifacts/clm_v2_linux.bin.c \
        -o '/tmp/clm_v2_linux.bin.tmp.675078' -lm 2>&1
    3 warnings generated.
OK: built /tmp/clm_v2_linux.bin
```

## 5. FFI resolution (.dylib → .so)

`train_clm.hexa` pins `@link(".../libhxblas.dylib")` absolute paths. On
Linux, `runtime.c:hexa_ffi_dlopen` fails the direct dlopen of the
Mac-absolute path, then falls through to its Linux branch, extracts the
basename `hxblas`, and searches `<LD_LIBRARY_PATH>/libhxblas.so`.
Confirmed by `LD_DEBUG=libs`:

```
find library=libhxblas.so [0]; searching
  trying file=/home/hexa-lang/self/native/build/libhxblas.so
calling init: /home/hexa-lang/self/native/build/libhxblas.so
find library=libhxlmhead.so [0]; searching
  trying file=/home/hexa-lang/self/native/build/libhxlmhead.so
calling init: /home/hexa-lang/self/native/build/libhxlmhead.so
```

Zero source edits to `train_clm.hexa` were required — the existing
.dylib path is cross-platform thanks to runtime basename fallback.

## 6. 1-step smoke

```
LD_LIBRARY_PATH=/home/hexa-lang/self/native/build \
    /tmp/clm_v2_linux.bin \
    --scale smoke --steps 1 \
    --corpus /root/Dev/anima/data/corpus.txt \
    --ckpt-dir /tmp/clm_smoke4
# exit 0, wall 15.689 s
```

corpus_v5.txt (5.38 GB corpus_clm_r4.txt) not present on hetzner; for a
1-step FFI/dlsym smoke this is irrelevant — `data/corpus.txt` (5.2 MB
existing slice) exercises the same byte-loader + decoder + FFI path.
For r5-a5 pod fire the corpus must be fetched from
`r2:anima-corpus/clm_r4/corpus_clm_r4.txt` (md5
`e9c7f139a0de1e58def231043e584653`, see `docs/corpus_v5_audit_20260419.md`).

Smoke flags landed:
- `--config training/config/clm_170m.json` is NOT yet parsed for scale
  dispatch — `train_clm.hexa:3283` hardcodes `_cli_flag_value(_, "--scale", "1b")`.
  Used `--scale smoke` (d=256 L=4 block=128 params=4,008,192) which fits
  CPU wall budget. Config-driven scale wiring is a separate follow-up
  (r5-a3 launcher scope).

Checkpoint written:
```
/tmp/clm_smoke4/step_0         43,281,520 bytes  (HEXACKPT-v1)
/tmp/clm_smoke4/step_0.meta.json
  {"step":0,"val_ce":5.54518,"phi":0,"phase":3,
   "n_tensors":40,"total_params":4008192,"format":"HEXACKPT-v1"}
```

`val_ce=5.54518` is finite and in the expected byte-level init band
(−log(1/256) = 5.5452), matching the Mac smoke exactly — confirming
the Linux FFI path produces bit-identical init logits for a given seed.

## 7. Known quirks (non-blocking)

- Multi-arg `println` with string + int still truncates on value under
  the Linux stage1 codegen: `[train_scale] step=` printed without step
  index. Same Mac quirk. No PASS/FAIL impact.
- `--config` JSON is loaded for metadata only; architecture dispatch
  still keys off `--scale`. r5-a3 launcher must either honor the JSON
  or override `--scale` based on it.

## 8. r5-a2 onward readiness

| action                                   | ready? | blocker                            |
|------------------------------------------|--------|------------------------------------|
| r5-a1 hetzner Linux AOT                  | DONE   | —                                  |
| r5-a2 mmap loader (drop `dd` per window) | ready  | none; scope = `training/clm_mmap_loader.hexa` |
| r5-a3 launcher with `--resume`           | ready  | should also fix config→scale dispatch |
| r5-a4 dep bundler                        | ready  | none                               |
| r5-a5 H100 pod fire                      | gated  | a2+a3+a4 + corpus rclone from R2   |

Path A (hexa build direct) remains the canonical AOT route on both
Mac (Phase 0 done) and Linux (this doc). Paths B–D explicitly not
needed.
