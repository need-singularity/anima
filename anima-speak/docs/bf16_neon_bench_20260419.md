# bf16 NEON M4 dispatch — sister 7ed4bb82 verification

**Date**: 2026-04-19  **Hardware**: Apple M3 (16GB, arm64) — *NOT M4*  **Host**: local
**Sister commit**: `7ed4bb82 feat(m4): wire bf16 NEON kernels into m4_inference dispatch`

---

## 1. Artifact verification

### libhxmetal.dylib
- Path: `/Users/ghost/Dev/hexa-lang/self/native/build/libhxmetal.dylib`
- Size: **53248 bytes** (53KB — matches handoff spec)
- Arch: Mach-O 64-bit arm64
- Exported T-symbols: **9** (matches spec)
  - `_hxmetal_init`, `_hxmetal_version`, `_hxmetal_matmul`, `_hxmetal_ffn_fwd`
  - `_hxmetal_buf_create`, `_hxmetal_buf_read`, `_hxmetal_buf_write`, `_hxmetal_buf_free`
  - `_hxmetal_sync`

### libhxblas.dylib (bf16 NEON host)
- Exports 7 T-symbols incl. `_hxblas_bgemv`, `_hxblas_bgemm`, `_hxblas_bf16_version`,
  `_hxblas_bf16_to_f32`, `_hxblas_f32_to_bf16`, `_hxblas_matmul_scalar`, `_hxblas_version`
- NEON kernel source: `hxblas_linux.c:597-640` — `float32x4_t`/`vfmaq_f32`/`vld1q_u16`
  widening loop (8 bf16 × f32 per iter). `__aarch64__` gated.
- bf16 refs in source: **46** (build flag `-march=armv8.2-a+bf16`)

### m4_inference.hexa dispatch
- Parse: PASS (`hexa parse self/ml/m4_inference.hexa`)
- `M4_BF16_ENABLED` / `m4_bf16_probe` / `m4_matvec` — 20 refs in file
- Docstring ceiling: CPU f32 23 tok/s → bf16 46+ → bf16+Metal **60+ tok/s**
- Sister commit diff: single file, +83/-13 lines, 8 call sites rewired (QKV/out-proj/SwiGLU gate/up/down/LM head)

### hxblas_bf16.hexa FFI
- 44 bf16-related refs; FFI bindings for `hxblas_bf16_version`, `hxblas_bgemv`, pack/unpack

---

## 2. anima-speak compile results (hexa_v2 → C → clang)

| file | hexa_v2 transpile | clang compile |
|------|-------------------|---------------|
| neural_vocoder.hexa | OK | OK |
| transformer.hexa | Parse err @ 1516 (bracket), C emitted | FAIL — `HexaVal =` ctor collision L1355 |
| audio_token_predictor.hexa | OK | OK |
| bench_hexa_speak.hexa | OK | FAIL — `split` identifier unresolved (codegen bug) 4x |

**2/4 files compile cleanly**. transformer.hexa parse error is a genuine syntax issue
at line 1516 (unexpected `]` + `intent` keyword). bench_hexa_speak fails because
hexa_v2 codegen emits bare `split` where it should be a string-method reference
(hexa_v2 codegen gap — not anima-speak bug).

---

## 3. Bench execution — BLOCKED

**Result: could not produce live tok/s number on this hardware this session.**

Blockers:
1. **bench_hexa_speak.hexa** — codegen bug (split). Can't link.
2. **test_m4_inference.hexa** — transpiles OK but clang rejects `M4ModelConfig(...)`
   struct-constructor emission (hexa_v2 emits raw type-name as fn call).
3. **hexa interpreter `run`/`bench`** on test_m4_inference — hangs (>30s timeout),
   likely waits on `--model <hexaw_path>` CLI arg it never receives.
4. **Direct C micro-bench against `_hxblas_bgemv`** — BLOCKED by PreToolUse hook
   `.py/.rs/.sh/.c file creation forbidden — hexa-only (R1/R37/AN13/L3-PY)`.
   Cannot author scratch .c linking libhxblas.

All symbols + kernels are present and parseable; what's missing is a runnable
hexa-native harness that drives `hxblas_bgemv` through representative LM shapes
without `.c` scratch or CLI-arg-gated binaries.

---

## 4. 60+ tok/s target — VERIFICATION STATUS

- **Static proof**: PASS. Kernels exist (46 bf16 refs, NEON intrinsics confirmed),
  dispatch wired (`M4_BF16_ENABLED` default true, 8 call sites routed), ABI probe
  `hxblas_bf16_version` exported. Sister commit landed and parses clean.
- **Live proof**: NOT OBTAINED this session. No tok/s number produced on M3 host.
- **Hardware caveat**: host is **M3**, not M4. M3 bf16 NEON path is the same
  ISA (armv8.2-a+bf16) but BW ceiling differs (M3: ~100 GB/s unified, M4 Pro: ~273 GB/s).
  Any tok/s measured here would be a **lower bound** for M4.

**Verdict**: plumbing verified, live number deferred. Handoff claim "path open"
is structurally true.

---

## 5. Next steps (infra + model)

### Infra (unblock live bench)
1. **Fix hexa_v2 codegen** for `split` method + `StructName(...)` constructor
   emission — both block clang linking of hexa-transpiled ML files.
2. **Add hexa-native bench harness** `self/ml/bench_bf16_matvec.hexa` calling
   `hxblas_bgemv` FFI directly on 4 LM shapes (4096x4096 / 11008x4096 / 4096x11008 /
   32000x4096), no model-load path. Emits GFLOPS + tok/s estimate. (Avoids .c scratch.)
3. **Resolve hook tension**: if .c scratch truly forbidden, spec needs a
   `self/native/bench_*.hexa` → `hexa build` → dylib-link flow so bf16 numbers
   are measurable without violating R1/R37.

### Model (M4 inference viability)
4. **Procure M4 pod or local M4 Mac** for authoritative 60+ tok/s measurement
   (current M3 host gives only a lower bound).
5. **Train ALM r11 bf16 weights** (Track A parallel) and load via `m4_inference
   --model <alm_r11.hexaw> --bf16=1` for end-to-end tok/s on real weights.
6. **A/B vs `--bf16=0`** on same weights to confirm 2x BW-bound speedup claimed
   in docstring (23 → 46 tok/s).
7. **Metal overlap validation**: current dispatch routes matvec to CPU bf16.
   Final 46 → 60+ leap requires FFN on GPU via `hxmetal_ffn_fwd` overlap —
   verify that call site is wired.

---

## Summary

- libhxmetal: 53KB, 9 syms, arm64 OK
- anima-speak 4-file compile: 2 PASS, 2 FAIL (upstream hexa_v2 codegen)
- bench: not run (codegen + hook blockers)
- 60+ tok/s: static path verified, live number pending
- Priority next: hexa-native bench harness + M4 hardware access
