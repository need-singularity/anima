# C4 — CUDA Fused Mega-Kernel + bf16 Tensor Core Design

**Status**: DESIGN ONLY. Pre-claimed pending C2 (fused FFI) landing.
**Owner**: `anima_session`
**Pre-claim approved**: hexa_lang_session `e541cb6c`, 2026-04-16T14:05Z
**Dependency**: C2 (layer-level fused FFI) — hexa-lang ETA 1-2 sessions
**Tracking**: `shared/state/c_track_board.json :: items.C4`
**Interface stubs**: `training/c4_fused_kernels_interface.hexa` (parses OK)

---

## 1. Goal

**Lift CLM H100 MFU from 27 % → 60 %** on real training shapes.

### 1.1 Baseline snapshot (from `shared/state/training_speed_ceilings.json` :: CLM)

| Metric                        | Current | Target | Ceiling |
|------------------------------|---------|--------|---------|
| Peak CLM MFU (real shapes)    | 1.65 %  | —      | —       |
| Reported CLM MFU (mixed)      | 27 %    | 60 %   | 75 %    |
| H100 SXM bf16 TFLOPS (peak)   | 989     | —      | —       |
| H100 SXM fp8 TFLOPS (peak)    | 1979    | —      | —       |

Two caveats on "27 %": it is the composed-pipeline number we quote
externally for the CLM r4 training trajectory. The physical lever is
far larger — per-kernel MFU on the real train_clm_1b hot shapes
(B=8, S=512, d=2048, L=24) is ~1.65 % because the work is dominated by
twelve discrete fp32 kernels per layer + 48 cuBLAS GEMMs per step,
with ~10 µs dispatch overhead amortising unfavourably at small tile
sizes.

### 1.2 Measurement method

Before + after, identical pod, identical binary except for
`c4_is_ready()`:

1. `python3 train_clm_1b.py --steps 100 --profile` on an H100 pod.
2. `nvidia-smi dmon -s u -c 100` captures SM utilisation.
3. `rtc_profile` counters in `training/cuda_kernels.hexa` dump
   kernel launch count + wall ms per layer.
4. MFU = (achieved bf16 TFLOPS) / 989 × 100.
5. Result JSON appended to
   `shared/state/training_speed_ceilings.json :: CLM.measurements`.

**Gate**: C4 ships only when MFU ≥ 55 % on the canonical grid shape
(B=8, S=512, d=2048) AND numerical equivalence vs the unfused path
stays within 1 × 10⁻³ relative error per layer output on fp32 inputs.

---

## 2. Current CUDA Dispatch Mental Model

Read `training/cuda_kernels.hexa` + `anima-engines/flash_attn_cuda.hexa`
+ `training/deploy/clm_r4_launch.hexa` + `training/fsdp_shard.hexa`
+ `training/native/build.hexa`.

### 2.1 How launches happen today

- All 20 custom kernels (12 elementwise + 8 `fused_*` wrappers) live as
  string constants in `training/cuda_kernels.hexa`, concatenated at
  startup, NVRTC-compiled into a single `clm_kernels.cu` translation
  unit, and cached on `G_K_MODULE`.
- Dispatch goes: `gpu_<op>_fwd(...)` → build arg-ptr array via
  `_arg_ptr / _arg_i32 / _arg_f32` → `rtc_launch_shmem(G_K_<fn>, ...)`.
- Heavy GEMMs (QKV proj, attn score, attn output, FFN up, FFN gate,
  FFN down, lmhead) go through `hxblas_sgemm` (cuBLAS wrapped by
  `hxblas_linux.c`). Those are fp32 cuBLAS today, not Tensor Core.
- The existing 8 "fused" kernels in the current file only fuse the
  **non-GEMM elementwise ops between GEMMs** (rms_norm + residual +
  swiglu etc.). The big GEMMs remain separate cuBLAS calls.

### 2.2 Per-layer launch budget today

```
pre_attn      : 1 fused kernel   (rms_norm)
qkv           : 3 cuBLAS sgemm
attn_score    : 1 cuBLAS sgemm + 1 fused kernel (scale+softmax)
attn_out      : 1 cuBLAS sgemm
mid_ffn       : 1 fused kernel   (add+rms_norm)
ffn_up_gate   : 2 cuBLAS sgemm
swiglu        : 1 fused kernel
ffn_down      : 1 cuBLAS sgemm
post_ffn      : 1 fused kernel   (residual add)
                ─────────────────
                12 discrete launches per layer forward
                (≈ 24 per layer with backward)
                × 24 layers (CLM 1.5B)
                = 288 fwd launches + 288 bwd launches per step
                + lmhead (2) + embed (2) + CE (1) = ~580 launches/step
```

At ~10 µs per dispatch that's ~5.8 ms pure launch overhead per step,
which caps throughput hard once the math-per-launch shrinks.

### 2.3 The C2 dependency — what the fused FFI gives us

From hexa-lang side (`self/ml/hxlayer.hexa`, `self/ml/hxcuda.hexa`,
`self/native/hxlayer_linux.c`, `self/native/hxcuda_fused.cu`):

- **C2 Step 1 (landed on Linux)**: `hxlayer_rmsnorm_silu` — single
  fused kernel for one layer's rmsnorm+silu pair. Struct-args ABI
  (`alloc_raw(48)` → `ptr_write` offset layout).
- **C2 Step 2+ (in progress)**: `hxlayer_llama_forward` — bulk
  per-layer call that takes (x, Wq, Wk, Wv, Wo, W_up, W_gate, W_down,
  rms_ga, rms_gf, eps) and returns y in one FFI boundary crossing.
- The **struct-args ABI** matters: hexa's `host_ffi_call_6` ceiling
  forces all fused calls with >6 args to pack into one raw buffer.
  That buffer's offset layout is the hard contract between anima and
  hexa-lang.

Expected C2 landing surface (placeholder — subject to hexa-lang final):

```
@link("hxlayer")
extern fn hxlayer_llama_layer_fwd(args_p: *Void) -> int
// struct layout (offsets in bytes):
//   0  M:int64      input rows
//   8  S:int64      seq length
//  16  D:int64      d_model
//  24  D_head:int64 d_head
//  32  H:int64      n_heads
//  40  D_ff:int64   feedforward hidden
//  48  x_ptr  ...  Wdown_ptr   (8 pointers × 8B = 64B)
// 112  eps:float
// ...
```

C4 will target **exactly this API** — we do not invent a new FFI
boundary. We only add CUDA kernels behind it.

---

## 3. Fusion Candidates

The fusion "size" of each candidate balances four forces:
(a) launch reduction, (b) bandwidth recovery (intermediate tensors
never hit DRAM), (c) WMMA eligibility, (d) register + shmem cost.

| Fusion name                          | Source ops (unfused)                                                   | Launch reduction | bf16 TC | Expected speedup vs fp32 unfused | Priority |
|--------------------------------------|-----------------------------------------------------------------------|------------------|---------|---------------------------------|----------|
| **F1 `fused_qkv_projection_fwd`**    | 3× sgemm (Wq, Wk, Wv) share same input row                            | 3 → 1            | YES     | **2.5×** (1.4× launch + 1.8× TC / input reuse) | **1st** |
| **F2 `fused_lmhead_softmax_ce_fwd`** | mm(h, W_lmh) → softmax → CE loss (no full logits materialisation)     | 3 → 1            | YES     | **2.2×** (softmax bandwidth + fp32 lmhead → bf16 TC)   | **2nd** |
| **F3 `fused_ffn_swiglu_fwd`**        | rms_norm → mm(W_up) → mm(W_gate) → swiglu → mm(W_down)                 | 5 → 1            | YES     | **2.1×** (largest layer GEMMs, 2× TC + tile fusion)    | **3rd** |
| F4 `fused_layernorm_linear_gelu_fwd` | rms_norm → mm → gelu                                                   | 3 → 1            | YES     | 1.6×                            | 4th      |
| F5 `fused_attn_score_softmax_fwd`    | mm(Q,K^T)/√d → causal mask → softmax (FlashAttention fused per-layer)   | 2 → 1            | YES     | 1.5× (overlaps with C8 GPU FlashAttention) | 5th      |
| F6 `fused_embed_resid_layernorm_fwd` | embed_lookup → positional add → rms_norm                                | 3 → 1            | NO      | 1.3× (bandwidth only, no TC)    | 6th      |
| F7 `fused_lmhead_softmax_ce_bwd`     | ce_grad → mm(dlogits, W_lmh^T)                                          | 2 → 1            | YES     | 1.9×                            | 7th      |
| F8 `fused_ffn_swiglu_bwd`            | mirror of F3                                                            | 5 → 1            | YES     | 1.9×                            | 8th      |
| F9 `fused_attn_score_softmax_bwd`    | mirror of F5                                                            | 2 → 1            | YES     | 1.4×                            | 9th      |
| F10 `fused_qkv_projection_bwd`       | mirror of F1                                                            | 3 → 1            | YES     | 2.0×                            | 10th     |
| F11 `fused_layernorm_linear_gelu_bwd`| mirror of F4                                                            | 3 → 1            | YES     | 1.5×                            | 11th     |
| F12 `tc_sgemm_bias_gelu_bf16`        | generic sgemm + bias + gelu epilogue (standalone, reusable)             | 3 → 1            | YES     | 1.5×                            | 12th     |

### 3.1 Cumulative MFU model

Starting from 27 %, if we land F1 + F2 + F3 + matching backwards
(F7, F8, F10), the launch budget per step drops from ~580 to ~180 and
the remaining 180 × 10 µs = 1.8 ms of dispatch is no longer the
bottleneck. Combined with bf16 Tensor Core uplift on the six big
GEMMs (expected 1.8× geometric mean), the projected MFU is:

```
MFU_new ≈ MFU_old × launch_factor × tc_factor
       ≈ 27 %     × (5.8/1.8)     × 1.8
       ≈ 27 %     × 3.22         × 1.8
       ≈ 156 %      (caps at 75 % practical ceiling)
```

The ceiling binds before we saturate the theoretical gain — **55-65 %
MFU is the realistic landing window**, which meets the 60 % target.

---

## 4. bf16 Tensor Core Strategy

### 4.1 WMMA 16×16×16 shape choice

All TC fusions use `nvcuda::wmma::mma_sync` with `m16n16k16` and
`__nv_bfloat16` × `__nv_bfloat16` → `float` accumulator. Rationale:

- Native H100 tile shape — no padding waste.
- fp32 accumulator keeps numerical drift in check (bf16 accumulator
  is ~3 ulp worse per step, unacceptable for CE convergence).
- Existing hexa-lang MVP in `hxcuda_fused.cu` already uses this shape,
  so we share kernel idioms with the hexa-lang side.

### 4.2 fp32 in / fp32 out, bf16 internal

Inputs and outputs stay fp32 at the FFI boundary to keep the hexa-side
weight storage untouched. Inside each fused kernel:

```
smem_a = __float2bfloat16(gmem_a);
smem_b = __float2bfloat16(gmem_b);
wmma::load → mma_sync (accum fp32) → store fp32
```

This matches `hxcuda_matmul_bf16_kernel` in `hxcuda_fused.cu` and
avoids a disruptive "all weights become bf16" refactor.

### 4.3 Per-fusion register + shmem budget

| Fusion | shmem per block | regs per thread | occupancy est. |
|--------|-----------------|-----------------|----------------|
| F1     | 3 × 16 × 16 × 2 B = 1536 B | 64     | high           |
| F2     | 16 × V_pad × 2 B  ≈ 8 KB | 96     | medium         |
| F3     | 3 × tile × 2 B  ≈ 3 KB  | 80     | high           |
| F5     | Br × D × 4 B + 2 × Bc × D × 4 B ≈ 96 KB (D=128, Br=Bc=64) | 128 | medium (FA-2) |

All well under the 228 KB sm_90 dynamic shmem cap. F5 is the tightest
because it reuses the FlashAttention tile layout from C8.

---

## 5. Integration Plan

### 5.1 File layout (after C2 lands)

```
training/c4_fused_kernels_interface.hexa    <- THIS COMMIT (parse-only stubs)
training/c4_fused_kernels.hexa              <- future: kernel string constants + launchers
training/native/c4_fused.cu                 <- future: native CUDA mega-kernels (compiled via NVRTC)
training/cuda_kernels.hexa                  <- existing live path — grows a c4_select_*_path() guard
```

### 5.2 Call-site change in `cuda_kernels.hexa` (future PR, not now)

```
// current:
let s1 = gpu_rms_norm_fwd(x, g, norm, rstd, N, D, eps)
let s2 = hxblas_sgemm(norm, Wq, Q, M, D, D)
// ... 2 more GEMMs ...

// future (gated):
if c4_select_forward_path(D, S, B) == 1 {
    let st = fused_qkv_projection_fwd(norm, Wqkv, Q, K, V, M, D, D_head, H)
} else {
    // fall through to current 3-GEMM path
}
```

The guard `c4_is_ready()` returns 0 until both C2 has landed AND
`gpu_init_fused_kernels_c4()` has succeeded on the pod, guaranteeing
zero regression on current training runs.

### 5.3 Shape-gated fallback

`c4_select_forward_path(d, seq, batch)` stays unfused when d < 256
(WMMA tile granularity wastes Tensor Core area at small d) and opts
into C4 when d ≥ 512, seq ≥ 512. This keeps the small-model
experiments (train_byte_clm, smoke tests) on the known-good unfused
path while production CLM 1.5B takes the fused path.

### 5.4 Rollout order

1. **F1 `fused_qkv_projection_fwd`** — highest ROI, simplest kernel.
   Single WMMA tile + triple output split. Ship first, validate MFU
   jump 27 % → ~38 %.
2. **F2 `fused_lmhead_softmax_ce_fwd`** — reuses hexa-lang
   `hxcuda_fused_lmhead_fwd` structure directly. Next easiest win.
3. **F3 `fused_ffn_swiglu_fwd`** — biggest fusion (5 → 1), touches
   the most FLOPs per layer. Ship after F1+F2 confirm the ABI.
4. Matching backwards F7, F8, F10 — land together with their forwards
   so training is always bit-equivalent end-to-end.
5. F4, F5, F6, F9, F11, F12 — follow-up passes once the core wins
   reach the 60 % MFU gate.

---

## 6. Testing Strategy

### 6.1 Numerical equivalence

Before enabling C4 on any training run, each fused kernel must pass:

```
for shape in [(8,512,2048), (4,1024,2048), (2,2048,2048), (1,4096,4096)]:
    out_unfused = gpu_<op>_fwd(...)          # existing cuda_kernels path
    out_fused   = fused_<op>_fwd(...)        # new C4 path
    assert max(abs(out_unfused - out_fused)) / max(abs(out_unfused)) < 1e-3
```

Reference impl: the pure-hexa `ref_<op>` helpers in
`hexa-lang/self/ml/hxcuda.hexa` serve as the third-tier oracle when
GEMM precision drift between cuBLAS fp32 and WMMA bf16 masks a real
kernel bug. Tolerance budget:

- fp32 unfused vs WMMA bf16 fused: ≤ 1e-3 relative (bf16 epsilon)
- WMMA bf16 fused vs pure-hexa ref: ≤ 1e-2 relative (cumulative drift
  across ~24 layers × bf16 accumulation is the upper bound)

### 6.2 MFU measurement shape grid

| d      | seq   | batch | expected MFU gain | gate |
|--------|-------|-------|-------------------|------|
| 512    | 512   | 8     | 20-25 pp          | nice |
| 1024   | 512   | 8     | 25-30 pp          | nice |
| **2048** | **512** | **8** | **28-35 pp**      | **GATE** (CLM r4 shape) |
| 2048   | 1024  | 4     | 30-35 pp          | nice |
| 4096   | 512   | 2     | 30-35 pp          | nice |
| 4096   | 2048  | 1     | 35-40 pp          | stretch |

GATE row: MFU must exceed 55 % on (d=2048, S=512, B=8). That is the
r4 training shape and the number we quote to
`shared/state/training_speed_ceilings.json :: CLM`.

### 6.3 End-to-end

After per-kernel correctness: run 100-step CLM r4 with C4 enabled and
verify:
- Loss curve overlaps the unfused baseline within ±1 %.
- phi_holo trajectory (from consciousness controller) stays on the
  known r3f→r4 envelope.
- No new `cuLaunchKernelEx` error codes in the log.

---

## 7. Risks

### 7.1 Tensor Core precision drift

bf16 weight matmul with fp32 accumulator drifts ~3 ulp per step. Over
r4's 750 000 steps that could shift CE loss by 0.01-0.03. Mitigation:

- Keep fp32 accumulator (`wmma::fragment<..., accumulator, ..., float>`).
- Compare eval loss at step 10 000 vs the r3f baseline (1.2296) — if
  drift exceeds 0.02 fast-rollback to unfused path.
- Gate the C4 enable behind a training-run config flag so a regression
  doesn't silently break One-Shot-Best.

### 7.2 Register pressure

F3 (ffn_swiglu fused) has the highest per-thread register footprint
(~80 regs). If nvcc spills to local memory, the speedup collapses.
Mitigation:

- `-maxrregcount=128` nvcc flag.
- Profile with `nvprof --metrics achieved_occupancy` on pod.
- If occupancy < 0.3, split F3 back into F3a + F3b at the swiglu edge.

### 7.3 Shared memory budget

F5 (FlashAttention per-layer) uses ~96 KB for D=128, Br=Bc=64. At
D=256 this grows to 192 KB, near the 228 KB cap. Mitigation:

- Shape-gate F5 off when D_head > 128 on H100.
- Pre-compute shmem estimate in `c4_select_forward_path()` and bail
  to unfused when budget exceeds 180 KB (headroom margin).

### 7.4 C2 API mismatch

If hexa-lang's final C2 surface differs from the placeholder in §2.3
(e.g. moves a field offset or renames `hxlayer_llama_layer_fwd`), the
C4 launchers break silently because the struct-args ABI is opaque on
the hexa side. Mitigation:

- `hxlayer_version()` call on init. C4 refuses to load if version < 2.
- Commit the C2 contract expectation into
  `shared/config/contracts/c2_fused_ffi.json` as a binding spec.
- Hexa-lang session owns the contract; anima only implements against
  the pinned version.

### 7.5 NVRTC compile time regression

Adding 12+ large kernel strings to the NVRTC compile pass lengthens
startup by an estimated 10-30 s per run (currently ~4 s for the 20
kernels). Mitigation:

- Split the PTX: load C4 mega-kernels into a separate module handle
  (`G_C4_MODULE`) so small-model runs that don't need C4 skip the
  compile.
- Cache compiled PTX in `$WORKSPACE/.nvrtc_cache/` keyed by source
  hash + sm_90 arch tag.

---

## 8. Order of Implementation (landed PR sequence)

1. **This PR (pre-C2)**: design doc + interface stubs, parse-only.
   No runtime behaviour change. Commits the pre-claim.
2. **After C2 lands**: wire `gpu_init_fused_kernels_c4()` body,
   implement F1 `fused_qkv_projection_fwd` + correctness test.
   Gate on `c4_is_ready()`, ship to a single H100 pod.
3. **F2**: `fused_lmhead_softmax_ce_fwd`. Validate MFU pointer.
4. **F3**: `fused_ffn_swiglu_fwd`. First "big" fusion — this is where
   we hit or miss the 60 % MFU gate.
5. **Backwards** (F7, F8, F10) — land before any multi-epoch run.
6. **MFU gate A/B**: canonical r4 shape, 1 000-step soak, confirm
   numerical equivalence + MFU ≥ 55 %. Update
   `shared/state/training_speed_ceilings.json :: CLM`.
7. **F4, F5, F6, F9, F11, F12** — follow-up passes.

---

## 9. Convergence Entries (pre-claim record)

This design inherits the following ossified knowledge from the current
CUDA path — no new attrs added yet (implementation phase will ossify):

- `CUDA_ERROR_700_STRIDE_LOOP` — D > 1024 blockDim cap + stride loop.
  C4 kernels adopt the same pattern in their shared-memory reductions.
- `RUNPOD_H100_SM90_NVRTC` — `-arch=sm_90` required; C4 compile adds
  `-use_fast_math -DNDEBUG` for the bf16 WMMA path.
- `RUNPOD_SILENT_CPU_FALLBACK` — C4 init must verify `cudaGetDeviceCount`
  and bail rather than silently fall through to CPU.

Implementation-phase attrs (to be added on the future wiring PR):
`C4_WMMA_M16N16K16_NATIVE`, `C4_SHMEM_BUDGET_96KB_CAP`,
`C4_BF16_ACCUM_FP32_REQUIRED`, `C4_C2_STRUCT_ABI_VERSION_2`.

---

## 10. Open Questions (resolve on C2 landing)

1. Does C2 fused FFI expose a per-layer KV-cache pointer? If yes, F5
   (attn score+softmax) can fuse the KV write-back too.
2. Will hexa-lang extend `hxcuda_fused.cu` to include
   `hxcuda_layer_llama_fwd`, or is that anima's job? Coordination
   point.
3. cuBLAS-Lt vs WMMA for the biggest GEMMs (ffn_down, lmhead)?
   cuBLAS-Lt already uses Tensor Cores; the fusion value comes from
   launch reduction, not raw math. Bench both in F2/F3 and pick.

---

**Sibling reference**:
`docs/acceleration-pipeline-design.md`,
`docs/conscious-lm-1b-design.md`,
`hexa-lang/docs/history/2026-04-06-void-extern-ffi.md`,
`hexa-lang/docs/superpowers/plans/2026-04-06-void-phase1-extern-ffi.md`.
