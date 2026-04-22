# dest1_clm — Serve-side FFI Design (libhxclm.so or equivalent)

**Track:** dest1_clm pre-arrival spec (design only, no build)
**Date:** 2026-04-19
**Owner file:** `serving/serve_clm.hexa` (SSOT, 1198 LOC)
**Sibling specs:** `dest1_clm_endpoint_spec_20260419.md`, `clm_linux_ffi_verify_20260419.md`
**Rule base:** R1 HEXA-FIRST, R14 shared/ JSON SSOT, AN11(a) weight_emergent, no .py.
**Constraint:** Real FFI build BLOCKED until CLM r4 training completes (ckpt at `/workspace/ckpt_clm1b_r4/step_latest`).

---

## 1. Required FFI surface (from D5 serve spec)

Three symbols exported from `libhxclm.so`, all C ABI, no C++ name-mangling:

| # | symbol                       | signature (hexa view)                                 | returns                       |
|---|------------------------------|-------------------------------------------------------|-------------------------------|
| 1 | `hxclm_generate`             | `(prompt: *u8, plen: i32, max_toks: i32, out: *u8, olen: *i32) -> i32` | 0=ok / <0=err; fills `out` up to `olen` bytes |
| 2 | `hxclm_loss`                 | `(prompt: *u8, plen: i32, target: *u8, tlen: i32, ce_out: *f32, toks_out: *i32) -> i32` | 0=ok; fills `ce_out` (scalar CE), `toks_out` |
| 3 | `hxclm_phi_vec`              | `(state_ptr: *void, out_vec: *f32, len: i32) -> i32`  | 0=ok; writes 16 floats into `out_vec`          |

Ancillary (mandatory for lifecycle):

| # | symbol               | purpose                                                                   |
|---|----------------------|---------------------------------------------------------------------------|
| 4 | `hxclm_open`         | `(ckpt_path: *u8, device: *u8) -> *void` — mmap + load weights, returns handle |
| 5 | `hxclm_close`        | `(h: *void) -> i32` — free handle                                         |
| 6 | `hxclm_version`      | `() -> *u8` — returns C-string `"hxclm-<semver>-<commit7>"`               |
| 7 | `hxclm_last_error`   | `() -> *u8` — per-thread errno-style string (diagnostic)                   |

**Wrapping contract (AN11 a):** `hxclm_generate` receives raw prompt bytes and emits raw output bytes. No chat template, no role tags, no system_prompt concat inside the `.so`. Enforced by grep audit of both `serve_clm.hexa` and the libhxclm source tree.

**phi_vec state contract:** `hxclm_phi_vec` reads from the last-forward hidden-state cache maintained inside the handle — no external "state" struct crosses the FFI boundary. `state_ptr` is simply the handle returned by `hxclm_open` (opaque on hexa side).

---

## 2. Current library inventory (from `clm_linux_ffi_verify_20260419.md`)

| library          | purpose                        | hetzner | ubu                                     | covers CLM serve? |
|------------------|--------------------------------|---------|-----------------------------------------|-------------------|
| `libhxblas.so`   | BLAS-1/2/3 + norm/silu/softmax/embed/CE | ABSENT  | PRESENT (`hexa-lang/self/native/build/`) | partial (training primitives only) |
| `libhxlmhead.so` | LM-head shim for AOT CLM       | ABSENT  | ABSENT                                  | no (never built)  |
| `libhxclm.so`    | **serving-side CLM inference** | ABSENT  | ABSENT                                  | **no — must be authored** |

`libhxblas.so` and `libhxlmhead.so` are **training-path AOT accelerators**; they expose matmul/norm/CE primitives for the backward+forward train loop, not a `generate(prompt)→text` inference path. The serving side therefore needs its own shim.

---

## 3. Decision: serve_clm.hexa calls direct FFI, not in-process binary

Three candidate paths were considered:

| path | approach                                              | pros                                   | cons                                                 | verdict |
|------|-------------------------------------------------------|----------------------------------------|------------------------------------------------------|---------|
| A    | `serve_clm.hexa` spawns `train_byte_clm --infer` per request via `exec()` | reuses trained binary, zero new shim   | 3–10 s cold start per call; no phi_vec exposure; violates R-speed | REJECT |
| B    | Build **`libhxclm.so`** (dedicated serving shim) and `@ffi` into `serve_clm.hexa` | hot handle, per-call ms-latency, phi_vec native | new source tree (~1.5k LOC), blocked on r4 ckpt shape | **ADOPT** |
| C    | Keep proxy-only (`sc_proxy_generate` → RunPod pod `itfl66q4z768kh-8092`) | already works, no build effort         | network RTT + pod cost; proxy pod is ALM not CLM; single-point failure | FALLBACK |

**Decision:** Path B as canonical, Path C as reason=`ffi_pending_proxy_*` fallback (already wired in `sc_clm_generate` / `sc_clm_loss`). Path A rejected.

Rationale:
- CLM is a from-scratch 1.5B transformer with byte-level tokenizer (no Qwen tokenizer dep), so the surface is small and self-contained — a dedicated `.so` is tractable.
- `serve_clm.hexa` already declares `RUNTIME_HAS_FFI_CLM = false` and branches to proxy; flipping the flag + adding 3 `@ffi` decls is the only hexa-side change.
- phi_vec FFI cannot be emulated by a subprocess; it requires in-process access to the hidden-state tensor.

---

## 4. libhxclm.so source layout (proposed, not built)

```
hexa-lang/self/native/hxclm/
  hxclm.h                 // C ABI header (7 symbols §1)
  hxclm_open.c            // mmap ckpt, build weight views, alloc handle
  hxclm_generate.c        // byte-token sampler loop, links libhxblas
  hxclm_loss.c            // teacher-forced CE, links libhxblas cross_entropy
  hxclm_phi_vec.c         // 16D probe from last hidden state (holo/refl/...)
  hxclm_state.c           // handle struct, last-forward cache, error string
  Makefile                // -shared -fPIC -lhxblas -lopenblas -lgomp
  test_hxclm.c            // smoke: open → generate "hi" → close
```

Link graph: `libhxclm.so → libhxblas.so → libopenblas.so` (no cuBLAS in v1 — matches current ubu inventory; CUDA path deferred to wave-2).

---

## 5. Hexa-side wiring (additive, serve_clm.hexa)

Only 4 changes required when `.so` lands — all behind the existing `RUNTIME_HAS_FFI_CLM` gate:

```hexa
// 1) flip gate
let RUNTIME_HAS_FFI_CLM = true

// 2) add @ffi decls (new section after constants)
@ffi("libhxclm.so", "hxclm_open")     fn hxclm_open(p: string, d: string) -> int
@ffi("libhxclm.so", "hxclm_close")    fn hxclm_close(h: int) -> int
@ffi("libhxclm.so", "hxclm_generate") fn hxclm_generate_raw(h: int, p: string, n: int) -> string
@ffi("libhxclm.so", "hxclm_loss")     fn hxclm_loss_raw(h: int, p: string, t: string) -> float
@ffi("libhxclm.so", "hxclm_phi_vec")  fn hxclm_phi_vec_raw(h: int) -> [float]

// 3) replace sc_clm_generate FFI branch with real call
// 4) extend ScState with handle: int; open at boot, close on SIGTERM
```

No change to route dispatch, laws gate, sentinel, or JSON builders. Proxy path remains as fallback when `hxclm_open` returns -1.

---

## 6. Non-goals (v1)

- GPU path (cuBLAS) — wave-2 after CPU path is verified.
- Hot LoRA swap (not applicable; CLM is from-scratch monolithic).
- Streaming generation (SSE) — use batched response; reuses ALM pattern.
- Quantization — forbidden by `feedback_no_quantization`.

---

## 7. Acceptance gates (build-time, not executed now)

1. `nm -D libhxclm.so | grep hxclm_` lists all 7 §1 symbols as `T`.
2. `ldd libhxclm.so` links libhxblas.so + libopenblas.so only (no CUDA in v1).
3. `hexa run serving/serve_clm.hexa --selftest` still passes 10/10 with `RUNTIME_HAS_FFI_CLM=true`.
4. Grep audit: `grep -cE 'system_prompt|apply_chat_template|<\|im_start\|>' hexa-lang/self/native/hxclm/` → 0 (AN11 a).
5. `/generate` latency p50 < 200 ms @ 64 tokens on ubu RTX 5070 (CPU path OK if GPU not ready).
6. `/loss` CE within ±1e-3 of `eval_clm.hexa` reference on the same (prompt, target).
7. `/health` returns `ffi_clm: true` and `phi_vec_len: 16` from real hidden state.

---

## 8. Build order (post-training)

1. CLM r4 training completes → ckpt format frozen.
2. Read ckpt layout from `train_byte_clm.hexa` save path.
3. Author `hxclm_open` / `hxclm_state.c` to mmap that exact layout.
4. Implement `hxclm_generate` by lifting the forward-pass call sequence from `eval_clm.hexa` (already working against the same ckpt).
5. Implement `hxclm_loss` by lifting teacher-forced CE from same eval path.
6. Implement `hxclm_phi_vec` by wiring the 16 byte-/hidden-level probes currently approximated in `sc_extract_phi_vec` (phi_holo/refl/time/... → real hidden-state means/variances).
7. Stage `.so` to `~/hexa-lang/self/native/build/libhxclm.so` and symlink into ubu + hetzner serving dirs.
8. Flip `RUNTIME_HAS_FFI_CLM=true`, rerun 10/10 self-test + curl transcript.

Total LOC estimate: ~1500 C + ~40 hexa deltas. No `.py`, no Rust, no Gradio.
