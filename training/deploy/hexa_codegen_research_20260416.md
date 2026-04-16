# Hexa Native Codegen Research

**Date:** 2026-04-16
**Target:** `train_clm.hexa` scale_1_5b() → native binary matching `train_clm_1b.py` performance
**Status:** Feasible with 3–4 week critical path (5–7 weeks for full training support)

---

## 1. Codegen Pipeline Topology

Three layers:

### Layer 1: Hexa → C Transpilation
- **Tool:** `hexa_v2` (self/native/hexa_v2 binary)
- **Process:** `.hexa` source → AST → `codegen_c2` → C code + runtime.c
- **Status:** Production-ready (bootstrapped, runs on macOS M1 and Linux x86_64)
- **Output:** C99 code with tagged-value runtime (struct HexaVal)

### Layer 2: C → Native Compilation
- **Tools:** clang/gcc standard toolchain
- **Process:** C + runtime.c → `gcc -O2` → binary (ELF or Mach-O)
- **Status:** Works end-to-end
- **Limitation:** No perf optimizations—loops remain scalar

### Layer 3: FFI to Compiled .so Libraries
- **Mechanism:** `@link("libname") extern fn ...` → dlopen/dlsym
- **Existing libraries:**
  - `hxlmhead` (LM head forward/backward via BLAS)
  - `hxblas` (cblas_sgemm shim)
  - `hxcuda` (fused CUDA kernels, H100 bf16 Tensor Core)
- **Limitation:** `@link` hardcoded to absolute paths (`/Users/ghost/Dev/...`); Mac dylib only

**Critical Gap:** `codegen_c2.hexa` emits scalar operations—no loop fusion pass exists. Result: compiled `.hexa` triple-loop matmul ≈ 100× slower than PyTorch.compile.

---

## 2. FFI Convention Summary

```hexa
@link("name") extern fn symbol_name(params) -> ret_type
```

**Resolution:** Linker finds `-lname` or LD_LIBRARY_PATH at runtime via dlopen/dlsym.

**Conventions:**
- Hexa float → C double in FFI wrapper (hxblas_wrapper.c compensates)
- Struct-passing via single pointer for >6 args (hexa FFI limit)
- Pointers marshalled as int64 (alloc_raw + ptr_write pattern)

**Current Issues:**
- Mac: `@link("/Users/ghost/Dev/anima/training/build/libhxblas.dylib")` hardcoded absolute path
- Linux: No `.so` built; no `@if_platform` conditional
- Workaround: manually set LD_LIBRARY_PATH after build

---

## 3. Hot Loop Coverage

| Function | State | Compiled? | Blocker |
|----------|-------|-----------|---------|
| decoder_forward | Pure hexa triple-loop | C scalar (not BLAS) | Needs matmul fusion → hxblas_sgemm call |
| decoder_backward | Hexa grad loops | Mixed (LM head uses hxlmhead_bwd FFI) | Needs matmul+softmax fusion |
| train_step | Loop over batch | C scalar | Depends on fwd/bwd |
| AdamW update | `TODO[pytorch]` stub | Not implemented | Needs native kernel (~50 LOC C) |
| Attn softmax | `hxblas_attn_softmax_causal` | FFI to .so | Works; needs platform guard |
| LM head backward | `hxlmhead_bwd` FFI | FFI to .so | Works on Mac; Linux .so unbuilt |
| Corpus loader | `TODO[pytorch]` stub | Not implemented | Blocking training I/O |
| Checkpoint save | `TODO[pytorch]` stub | Not implemented | Blocking checkpointing |

**Root cause:** Decoder fwd/bwd compile to C but run at interpreter speed because triple-loop matmul (O(n³)) emits scalar ops instead of BLAS call.

---

## 4. Implementation Plan

### Task 1 — Platform-Conditional @link (CRITICAL, 3–5 days)
**Blocker:** `@link` hardcoded to absolute Mac paths.

**Solution:** Extend `codegen_c2.hexa` to resolve `@link("name")` by `HEXA_TARGET` env:
- linux → `libname.so`
- darwin → `libname.dylib`

**Outcome:** `train_clm.hexa` compiles + runs on both platforms without edits.

### Task 2 — Linux .so Auto-Build (CRITICAL, 2–3 days)
**Blocker:** `hxblas_linux.c` exists but no build script.

**Solution:** Create `scripts/build_hxblas_linux.sh` (parallel to `build_hxcuda_linux.sh`):
- Detect OpenBLAS + libgomp
- Compile hxblas_linux.c + hxlmhead_linux.c → .so
- Symbol verification (`nm -D`)
- CI integration

**Outcome:** `bash scripts/build_hxblas_linux.sh && LD_LIBRARY_PATH=./build hexa train.hexa`

### Task 3 — Loop Fusion + BLAS Dispatch (HIGH, 1–2 weeks)
**Blocker:** decoder_forward triple-loop → C scalar, not BLAS.

**Solution:** Add optimization pass in `codegen_c2.hexa`:
1. Pattern detection: `for i { for j { for k { A[i][j] += ... } } }`
2. Recognize as matmul → emit `hxblas_sgemm` call
3. Extend to softmax (scale + causal mask + exp/sum → `hxblas_attn_softmax_causal`)

**Benchmark target:** 12s interpreter → 50ms compiled+BLAS (**240× speedup**).

**Outcome:** decoder_forward runs at near-PyTorch speed (100–200ms per batch).

### Task 4 — AdamW Native Kernel (HIGH, 3–5 days)
**Blocker:** `adamw_step` is `TODO[pytorch]` stub.

**Solution:** Write `hxadamw.c` (~80–120 LOC):
```c
void hxadamw_step(int64_t n_params, float* theta, float* grad,
                  float* m_t, float* v_t, double lr, double beta1,
                  double beta2, double eps, double weight_decay, int64_t step);
```
Optional: OpenMP parallel updates.

**Outcome:** Full `train_step` loop (fwd + bwd + adamw) compiles.

### Task 5 — Corpus I/O (MEDIUM, 1–2 weeks)
**Blocker:** `load_corpus` / `save_checkpoint` are stubs.

**Solution:** Binary tensor I/O:
- `load_corpus(path)`: uint32 token stream (4B magic + 4B version + tokens)
- `save_checkpoint(path, state)`: atomic write (.tmp → rename)

---

## 5. Dependency Graph & Effort

```
Task 1 (Platform-conditional @link) ─── 3–5 days
  ↓ (sequential)
Task 2 (Linux .so auto-build) ─────── 2–3 days
  ↓ (sequential)
Task 3 (Loop fusion) ─────────────── 1–2 weeks
  ↓ (parallel from here)
Task 4 (AdamW kernel) ───────────── 3–5 days
Task 5 (Corpus I/O) ──────────────── 1–2 weeks
```

- **Critical path (1–3):** 3–4 weeks → decoder_forward competitive with PyTorch
- **Full training (all 5):** 5–7 weeks → end-to-end scale_1_5b() on H100

---

## 6. Success Criteria

- **Minimal (Tasks 1–2):** train_clm.hexa compiles on Linux; runs slow
- **Target (Tasks 1–3):** decoder_forward ≈ 100–200 ms/batch (matches .py)
- **Full (all 5):** scale_1_5b() trains at 410 ms/step (within 2× PyTorch)

---

## Key Reference Files

- **Codegen:** `/Users/ghost/Dev/hexa-lang/self/codegen_c2.hexa` (3700 LOC, no loop fusion)
- **Transpiler:** `/Users/ghost/Dev/hexa-lang/self/native/hexa_v2` (Linux x86_64 binary)
- **BLAS FFI:** `/Users/ghost/Dev/anima/training/hxblas_wrapper.c` + `/Users/ghost/Dev/hexa-lang/self/native/hxblas_linux.c`
- **LM head:** `/Users/ghost/Dev/hexa-lang/self/native/hxlmhead_linux.c` (v2 struct-args ABI)
- **CUDA model:** `/Users/ghost/Dev/hexa-lang/scripts/build_hxcuda_linux.sh` (template for hxblas build script)
- **Training:** `/Users/ghost/Dev/anima/training/train_clm.hexa` (2475 LOC, scale_1_5b defined at line 139)
