# hxqwen14b v5 Day-1 정밀 설계

Date: 2026-04-19
Status: DESIGN ONLY (no code). Next-session coding spec.
Source scaffold: `self/native/hxqwen14b.c` @ v4, 994 LOC.
Target pod: H100 SXM5 80GB, CUDA 11.8, cuBLAS, bf16 Tensor Core, sm_90.

Related docs (read-only references):
`hxqwen14b_cublas_pattern_20260419.md`, `hxqwen14b_workspace_sizing_20260419.md`,
`hxqwen14b_hopper_compat_20260419.md`, `hxqwen14b_safetensors_spec_20260419.md`.

---

## 1. v4 Stub Inventory — return -5 (RC_ERR_CUDA_TODO)

Five call-sites return `-5` and must be unblocked in v5. All are guarded by
`#if defined(__linux__) && defined(HXQWEN14B_CUDA)`.

| # | Symbol                          | Line (of 994) | Struct arg           | Notes |
|---|---------------------------------|---------------|----------------------|-------|
| 1 | `hxqwen14b_load`                | 598-605 TODO block; returns slot today but skips VRAM upload | `int64_t ckpt_path_p` | Adds cuMemAlloc + HtoD per tensor |
| 2 | `hxqwen14b_generate`            | 634            | `HxQwen14bGenArgs*`   | Not on r11 critical path — leave -5 |
| 3 | `hxqwen14b_forward_with_lora`   | 894            | `HxQwenFwdArgs*` 136B | Section 8 header documents kernel seq |
| 4 | `hxqwen14b_backward_lora_only`  | 965            | `HxQwenBwdArgs*` 136B | Section 9 header documents kernel seq |
| 5 | `hxqwen14b_apply_lora_delta`    | 993            | `HxQwenApplyArgs* 72B | Day-1: deferred (export-time only) |

Day-1 scope = unblock #1 (loader) + init cuBLAS/workspace + LoRA device init.
Day-2 = unblock #3 (forward). Day-3 = unblock #4 (backward). #2/#5 deferred.

---

## 2. Day-1 Implementation Items (in order)

### 2.1 QwenCtx device-state extension

Extend existing `QwenCtx` struct (line 338). NEW fields appended BEFORE
`void* tokenizer;` (preserves ABI for non-CUDA callers):

```
void*   dev_embed;             // bf16 [V, d]    shard-loaded
void*   dev_layer_weights[48]; // per-layer block: q/k/v/o + gate/up/down + 2 rmsnorm
void*   dev_rms_final;         // bf16 [d]
void*   dev_lora_A_flat;       // float [192·r·d]  LoRA A on device
void*   dev_lora_B_flat;       // float [192·d·r]  LoRA B on device
void*   dev_workspace;         // 32 MiB cuBLAS workspace
size_t  workspace_bytes;       // 33554432
void*   cu_stream;             // cudaStream_t (training)
int     cuda_ready;            // 1 iff init fully succeeded
```

### 2.2 safetensors actual loader (promotes probe → real load)

Current `hxqwen14b_load` (line 539) probes index.json only. Day-1 adds a
NEW static helper AFTER probe succeeds, gated by `HXQWEN14B_CUDA`.

Signature (internal):
```
static int load_shards_to_device(QwenCtx* ctx);
```

Internal call sequence:
1. Iterate shards `model-NNNNN-of-MMMMM.safetensors` (M from index.json).
2. For each shard: `open()` + `fstat()` + `mmap(PROT_READ, MAP_PRIVATE)`.
3. Read LE u64 header_size at offset 0 (per safetensors spec §1.1).
4. Parse header JSON (reuse existing skim parser; add tensor-entry walk).
5. For each tensor T in shard:
   a. Classify by name → pick dev slot in `QwenCtx` (embed / layer[L]/q_proj / ...).
   b. `cuMemAlloc(&d_ptr, bytes)` where bytes = `end - begin` from data_offsets.
   c. `cuMemcpyHtoD(d_ptr, shard_mmap + 8 + header_size + begin, bytes)`.
   d. Store d_ptr in ctx.
6. `munmap(shard)` after all tensors in shard copied.

Return codes: 0 success; `RC_ERR_IO` (-4) on mmap/read fail;
`RC_ERR_OOM` (-3) on cuMemAlloc fail (leave partially-allocated state — `free()` handles cleanup).

Frozen tensor dtypes: all bf16 (confirmed in safetensors spec doc).
Host buffers are NOT retained — mmap + immediate HtoD + munmap keeps host RSS flat.

### 2.3 cuBLAS handle init + workspace 32 MiB

Extracted pattern from `train_clm_composed.c` (cuBLAS doc §2).

Signature (internal):
```
static int cublas_init_for_ctx(QwenCtx* ctx);
```

Internal call sequence:
1. `cudaSetDevice(0)` — H100 pod is single-GPU for 14B LoRA.
2. `cudaStreamCreate(&ctx->cu_stream)` — dedicated stream (NOT default).
3. `cublasCreate_v2(&H); ctx->cublas_handle = H;`.
4. `cublasSetStream_v2(H, ctx->cu_stream)`.
5. `cudaMalloc(&ctx->dev_workspace, 32 MiB)`; `ctx->workspace_bytes = 33554432`.
6. `cublasSetWorkspace_v2(H, ctx->dev_workspace, ctx->workspace_bytes)`.
7. `cublasSetMathMode(H, CUBLAS_TENSOR_OP_MATH)` (bf16 TC path).
8. `ctx->cuda_ready = 1`.

Order invariant: step 4 (`SetStream`) resets workspace → step 6 MUST follow.
Recorded in workspace_sizing doc §1.

On any cuBLAS/CUDA error return `RC_ERR_KERNEL_FAIL` (-4).

### 2.4 192 LoRA tensor init (Kaiming A / zero B) on GPU

Reuse existing `hxqwen14b_lora_init_A` / `_init_B` CPU entries (lines 719,
742) — they fill HOST float32 buffers. Day-1 adds a HtoD copy step inside
`hxqwen14b_load` after cuBLAS init.

Signature (internal):
```
static int upload_lora_to_device(QwenCtx* ctx, int64_t seed);
```

Internal call sequence:
1. Compute sizes: `nA = 192·r·d = 192·8·5120 = 7,864,320 floats = 31.5 MB`;
   `nB = 192·d·r = same = 31.5 MB`.
2. Host malloc two temp buffers (63 MB total — fits 14B pod easily).
3. Invoke `hxqwen14b_lora_init_A(&init_args_A)` — Kaiming σ = sqrt(2/d).
4. Invoke `hxqwen14b_lora_init_B(&init_args_B)` — zero.
5. `cuMemAlloc(&ctx->dev_lora_A_flat, nA·4)`; `cuMemcpyHtoD` temp_A.
6. `cuMemAlloc(&ctx->dev_lora_B_flat, nB·4)`; `cuMemcpyHtoD` temp_B.
7. `free()` temp buffers.

seed param propagates from caller (default from a new optional 2nd arg to
`hxqwen14b_load` — or read from env `HXQWEN14B_LORA_SEED` for ABI safety).

### 2.5 Hopper-specific (sm_90, no FP8 on CUDA 11.8)

Compile flags (in `scripts/build_hxqwen14b_linux.hexa`):
- `-arch=sm_90` (Hopper cubin; not `sm_90a` which is 11.8-only TMA fast-path).
- `-DHXQWEN14B_CUDA=1`
- Link: `-lcublas -lcudart` (NO `-lcublasLt_fp8` — CUDA 11.8 does not ship FP8
  kernel variants outside x86 prebuilt — bf16 only for Day-1).
- PTX embed: compile with `--generate-code arch=compute_90,code=[sm_90,compute_90]`
  so first-call PTX JIT is avoided on mixed-driver pods.

Explicitly NOT used Day-1:
- FP8 E4M3/E5M2 (needs cuBLAS 12+; blocked by 11.8).
- `CUBLASLT_MATMUL_TILE` autotune heuristics (keep default).
- Thread-block-cluster launches (defer to flash-attn integration Day-2+).

Workspace env var: set `CUBLAS_WORKSPACE_CONFIG=:4096:8` (= 32 MiB × 8 slots)
via trainer wrapper, NOT inside C — keeps determinism flag and workspace policy
co-located with training hyperparams.

---

## 3. Function Signatures + Pseudocode

### 3.1 Modified `hxqwen14b_load`

```
int64_t hxqwen14b_load(int64_t ckpt_path_p):
    # unchanged slot/probe logic (lines 539-596)
    slot, ctx = alloc_slot_and_probe(ckpt_path_p)
    if slot < 0: return slot
    #ifdef HXQWEN14B_CUDA
    if cublas_init_for_ctx(ctx) != 0: goto fail
    if load_shards_to_device(ctx) != 0: goto fail
    if upload_lora_to_device(ctx, env_seed()) != 0: goto fail
    ctx.cuda_ready = 1
    #endif
    return slot
fail:
    cleanup_device(ctx); memset(ctx, 0, sizeof); return RC_ERR_IO
```

### 3.2 `hxqwen14b_free` addition

Before existing `memset` (line 659): free device resources.
```
if ctx.cuda_ready:
    cudaFree(ctx.dev_workspace), cuda all weight slots, cuda lora_A/B
    cublasDestroy_v2(ctx.cublas_handle)
    cudaStreamDestroy(ctx.cu_stream)
```

### 3.3 No changes Day-1 to fwd/bwd/apply

They still return `-5`. Day-2 starts on `hxqwen14b_forward_with_lora` once
Day-1 verified.

---

## 4. Verification Stages

### 4.1 Mac Day-1.5 smoke (12/12 must remain PASS)

Mac build path `--mac-native` does NOT define `HXQWEN14B_CUDA`, so ALL new
code is `#ifdef`-gated out. Existing 12-case smoke:
1. probe on __stub__ path → slot > 0
2. probe on fake-dir → RC_ERR_INDEX_JSON
3. lora_init_A deterministic (seed=1 reproducible)
4. lora_init_A Kaiming σ within 5% of sqrt(2/5120)
5. lora_init_B all zeros
6. adamw_step_cpu 1 step monotonic loss decrease
7-12. (existing)

All 12 must stay PASS. NO new Mac tests Day-1 (device code cannot run).

### 4.2 H100 1-step forward — loss finite gate

Pod: `anima-14b-alm` or equivalent. Run:
```
hexa scripts/build_hxqwen14b_linux.hexa    # builds with HXQWEN14B_CUDA=1
./bin/train_alm_lora_smoke --steps=1 --micro_bsz=1 --seq=512
```

Pass criteria:
- `hxqwen14b_load` returns slot > 0 (not -3, not -4).
- `nvidia-smi` shows ~29 GB VRAM used (base weights) + ~0.1 GB (LoRA + workspace).
- `hxqwen14b_forward_with_lora` still returns -5 (expected Day-1).
- Loader log prints: "48 layers mapped, 192 LoRA adapters on device,
  workspace 32 MiB, cuBLAS math mode TC".

Note: loss finite check is Day-2 gate, not Day-1. Day-1 gate = load succeeds
+ device state populated + free() cleanly returns 0.

### 4.3 Hexa-side integration smoke

`training/train_alm_lora.hexa` Day-1.5 path (already calls load + CPU init):
confirm it still produces rc=0 from `hxqwen14b_load` and rc=-5 from forward
(unchanged). No regression required.

---

## 5. Risk / Rollback

- If cuBLAS init fails on pod (driver mismatch): `hxqwen14b_load` returns
  `RC_ERR_IO`; trainer falls back to v4 behavior (probe only). No dataloss.
- If shard HtoD OOMs: first cuMemAlloc fail clears ctx, returns `-3`. Retry
  with `CUDA_VISIBLE_DEVICES=0` pinning.
- All Day-1 changes compile-gated by `HXQWEN14B_CUDA`; Mac + non-CUDA Linux
  paths bit-identical to v4.

---

## 6. File Touch List (Day-1 commit)

- `self/native/hxqwen14b.c` — load/free edits + 3 new static helpers (~250 LOC).
- `scripts/build_hxqwen14b_linux.hexa` — add `-arch=sm_90` + `-lcublas -lcudart`.
- `shared/state/hxqwen14b_build.json` — bump version to 5.
- NO changes to `training/train_alm_lora.hexa` (ABI preserved).
