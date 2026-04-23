# CLM AOT 170M smoke on hetzner — 2026-04-20

## Summary

- **Host**: hetzner (`anima-ax102`, AMD Ryzen 9 7950X3D 32-thread, 128 GB RAM, NO GPU)
- **AOT build**: OK in 1.8 s (clang -O2, 3 unused-expr warnings, non-fatal)
- **FFI linkage**: OK — `libhxblas.so` + `libhxlmhead.so` (29 KB / 16 KB at `/root/hexa-lang/self/native/build/`) dlopened via `LD_LIBRARY_PATH`, linux-fallback path in runtime.c strips `.dylib` → retries `.so`
- **Config override**: 170M applied (d=768 L=12 H=8 KV=4 blk=512 batch=2 lr=3e-4 steps=1 save_every=1)
- **Corpus**: `data/corpus.txt` 5 242 172 bytes (73 824 lines), mmap loader OK
- **Step 0 completion**: **NO** — process ran for 11 min 35 s (started 18:03:24 CEST, ended 18:14:59) and exited silently **without emitting the `[train_scale] step=0 loss=…` line, without writing any ckpt file, and without any stderr output**. No dmesg OOM. Ckpt dir empty. Exit appears to be a silent abort inside `train_step()` — consistent with the `hexa silent-exit-on-imports` bug family (feedback_hexa_silent_exit_5_imports).

## Environment wiring (reproducible)

| Fix | Change |
|-----|--------|
| Missing `/root/.hx/bin/self` | `ln -sf /root/Dev/hexa-lang/self /root/.hx/bin/self` (hexa CLI expected SELF_DIR at shim-root) |
| hexa binary | `NO_HEXA_SHIM=1 /root/.hx/bin/hexa` (bypass airgenome Docker shim; real binary = `/home/hexa-lang/hexa`) |
| .dylib hardcoded `@link` paths | runtime.c Linux fallback (`hexa_ffi_extract_libname` + `LD_LIBRARY_PATH`) resolves them to `lib*.so` transparently — no anima-side source change needed |

## Exact commands + exit codes

Build:
```
cd ~/Dev/anima
NO_HEXA_SHIM=1 /root/.hx/bin/hexa build training/train_clm.hexa -o /tmp/clm_v2.bin
# → OK: built /tmp/clm_v2.bin  (402 080 B, 3 warnings)  exit 0
```

Smoke:
```
cd ~/Dev/anima
LD_LIBRARY_PATH=/root/hexa-lang/self/native/build \
  /tmp/clm_v2.bin \
    --config training/config/clm_170m.json \
    --steps 1 \
    --corpus data/corpus.txt \
    --ckpt-dir /tmp/ckpt_clm170m_smoke \
    --save-every 1
# elapsed: 11m35s, exit: silent (no step line, no ckpt, no stderr, no OOM)
# observed peak: 126 % CPU single-threaded, 6.3 GB RSS (under 128 GB host RAM)
```

**CE value**: not emitted (step 0 never completed).
**phi_vec shape**: not emitted (gated on same step-log path at train_clm.hexa:3165).

## Progress log (up to first yield)

```
[clm_smoke_stub] phi_cache_load skipped (stub) path=shared/state/phi_cache_v1.jsonl
=== train_clm.hexa — TRAIN MODE ===
  corpus     = data/corpus.txt
  steps      = 1
  batch/seq  = 8 / 512
  lr/warmup  = 3e-4 / 5000
  save-every = 1
  ckpt-dir   = /tmp/ckpt_clm170m_smoke
  scale      = 1b
  [sw] use-quadruple-cross =
  [sw] use-tension-link    =
  [sw] use-lens-diag       =
  [sw] use-tier-curriculum =
  [sw] use-sumt-stages     =
  [sw] use-g-holo          =
  [sw] use-a6-gate         =
[train_clm] --config training/config/clm_170m.json — overriding scale defaults
[train_clm] config applied: name=clm170m d=768 nl=12 nh=8 kv=4 blk=512 batch=2 lr=0.0003 steps=1 save_every=1
[train_scale] init begin scale=clm170m d_model=768 n_layer=12 block_size=512
[clm_mmap_loader] opened data/corpus.txt len=5243172 bytes (~5 MiB)
[load_corpus] path=data/corpus.txt n_tokens=5243172 block_size=512
[train_scale] cfg effective batch=2 lr=0.0003 total_steps=1 save_every=1 ckpt_dir=/tmp/ckpt_clm170m_smoke
[train_scale] init begin decoder_model_new size=768x12
[train_scale] init done — entering training loop
[clm_mmap_loader] opened data/corpus.txt len=5243172 bytes (~5 MiB)
<<< stuck inside train_step() step=0, no step/CE/phi_vec line yet >>>
```

## Root cause = CLM BLAS coverage gap (blocks dest1_clm full run on CPU)

The codegen `build/artifacts/clm_v2.bin.c` emits **only 4 `hxblas_sgemm` call sites** — all four are inside the attention block (Q·Kᵀ and softmax·V). Every other matmul in the transformer — `W_q`, `W_k`, `W_v`, `W_o`, FF gate/up/down (SwiGLU), and the LM head back-prop — is compiled from pure hexa nested-loop scalar code:

```
grep -c 'hxblas_sgemm(' build/artifacts/clm_v2.bin.c  →  4
```

Per-step FLOPs that actually use BLAS ≈ 2 × (seq²·d_head·n_head) per layer × 12 ≈ 0.8 GFLOP.
Per-step FLOPs that run scalar ≈ 2 × seq × d_model × (d_model+d_kv×2+d_model) per layer attn proj (~4.8 GF) + 2 × seq × d_model × 3·d_ff per layer SwiGLU (~14.5 GF) → **~230 GFLOP/step scalar** (forward only; backward doubles it). At ~0.3 GFLOP/s single-core scalar hexa that is ~25–30 min per step on hetzner CPU, and the observed 10+ min stall with no step yield is consistent.

## Gate to full dest1_clm run (two stacked blockers)

**Gate A — silent abort in `train_step` step 0 (the actual r5-a5 blocker):**
Process exits with no output after `[train_scale] init done — entering training loop`. Needs a hexa-side bisect — likely the `_c41_forward_aux` call path (new CLM-P4-1 consciousness engine extension at `train_clm.hexa:2264`) that constructs `gwt_head`/`holo_head` per step and calls `_c41_phi_holo` / quantum controller. Suggested next action: rebuild with a `println` probe before each of the 6 numbered steps in `train_step()` so the exit point shows up in stdout. AOT binary + FFI resolution are not the problem — those completed fine.

**Gate B — scalar-matmul coverage (makes CPU smoke economically infeasible anyway):**
Even if Gate A is fixed, a single CPU step on 170M will take ~25–30 min because only 4 out of ~100 matmuls per step route through BLAS. Fix path:

1. Add `hxblas_sgemm` call sites to `decoder_forward` / `decoder_backward` in `training/train_clm.hexa` for `W_{q,k,v,o}`, SwiGLU `W_{gate,up,down}`, final `lm_head` forward. `hxlmhead_bwd` already covers the LM-head backward. ~7 additional call sites per layer per direction.
2. (Alt) build a new fused `hxblas_decoder_step` that does the whole transformer block in C — 1 FFI call per layer.
3. Once either lands, relink `/tmp/clm_v2.bin` and rerun the same smoke command; CPU single-step on hetzner should drop to seconds.
4. Parallel path: run on **ubu** (RTX 5070) via the CUDA route in `libhxblas_cuda.so` — but that requires the same matmul coverage plus CUDA kernel routing. GPU smoke is the actual dest1_clm target host per roadmap; CPU smoke is a courtesy.

No `phi_vec` JSON is emitted because `train_step` never returns to the `println("[train_scale] step=", …)` at `train_clm.hexa:3165`.

## dest1_clm GO/NO-GO

- **Build path**: GREEN (AOT binary + FFI resolution working on Linux host)
- **CPU smoke**: RED — silent abort inside step 0 before any metric line (Gate A)
- **GPU launch (ubu RTX 5070 or H100)**: BLOCKED behind Gate A (if train_step itself crashes, GPU doesn't help) + Gate B (BLAS coverage) — same code path, faster kernels won't fix a semantic/ABI fault
- **Next r5 action priority**:
  - **r5-a6**: instrument `train_step()` with step-by-step `println` probes → rebuild, run smoke, identify exact crash point (likely inside `_c41_forward_aux` or quantum_controller_step on a cold buffer)
  - **r5-a7**: extend `hxblas_sgemm` coverage to linear projections + SwiGLU + LM-head fwd (7 matmuls × 12 layers)
  - **r5-a8**: after a6+a7 green, move to ubu RTX 5070 for per-step < 1 s verification, then H100 for full 20 000-step run

## Artifacts on hetzner

| Path | Bytes | Purpose |
|------|-------|---------|
| `/tmp/clm_v2.bin` | 402 080 | AOT binary, Linux ELF x86-64 |
| `build/artifacts/clm_v2.bin.c` | ~180 KB | Hexa→C codegen (3464 LOC) |
| `/tmp/smoke_v3.log` | live | Smoke stdout (this session) |
| `/tmp/ckpt_clm170m_smoke/` | empty | Will populate at step 0 save if step completes |
| `/root/hexa-lang/self/native/build/libhxblas.so` | 29 224 | Full Linux symbol set (sgemm, attn_softmax, …) |
| `/root/hexa-lang/self/native/build/libhxlmhead.so` | 15 832 | hxlmhead_bwd route |
