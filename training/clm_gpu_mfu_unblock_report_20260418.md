# CLM GPU MFU Unblock — Patch A+B Applied 2026-04-18

Baseline (SSOT `CLM.measurements.h100_d512_l12_best`): **0.087% MFU, 180 ms/step,
863 GFLOPS** at d=512 ff=2048 nl=12 seq=512. Gap to 80%/791 TFLOPS = **916×**.
Mission target ≥10% (100×).

---

## 1. Five blockers (ranked)

1. **STALE `USE_FUSED` / `USE_FUSED_BATCH = false`** — `train_clm_gpu.hexa:1247,1251`.
   Comment `// disabled until gpu_train fused functions land` is stale;
   hexa-lang `5dde6b7f` landed `gpu_layer_{fwd,bwd}_fused`, `gpu_forward_full_fused`,
   `gpu_backward_full_with_embed_fused` + 8 NVRTC fused kernels. Anima runs the
   non-fused fallback — ~96 extra kernel launches/step at NL=12.

2. **DEAD `G_MULTI_STREAM` BRANCH** — `train_clm_gpu.hexa:1388` calls
   `gpu_train_step_overlapped(...)` which **is not defined in hexa-lang/self/ml**.
   With `CLM_MULTI_STREAM=1` default, this unreachable branch shadows the
   `USE_FUSED_BATCH && GRAD_ACC > 1` dispatch.

3. **`NH=0` FORCES SEQ² MATERIALISATION** — `cfg = GpuClmConfig { ... }` at
   line 1174 omits `NH`/`NKV` (default 0). `gpu_layer_fwd_fused` line 1012
   falls into legacy branch doing `gpu_sgemm_nt(q,k,probs,SEQ,SEQ,D)` +
   softmax over full SEQ² = 262K f32/layer at SEQ=512. Blocks hxflash O(S·D).

4. **QKV = 3 SEPARATE SGEMMs** — `gpu_layer_fwd` 486-488 / 1006-1008. Three
   `[SEQ×D]×[D×D]` GEMMs vs one `[SEQ×D]×[D×3D]`. ~60 µs × NL × GRAD_ACC =
   ~6 ms/step cuBLAS handshake.

5. **PER-LAYER `gpu_zeros` + `gpu_saxpy` GRAD ACCUM** — `gpu_layer_bwd_fused`
   still allocates + saxpies `dW{q,k,v,o,ff1,ff2}` scratch per micro-batch.
   ~960 extra dispatches at GRAD_ACC=8 × NL=12. Replace with `beta=1.0`
   in-place GEMM (new `gpu_sgemm_tn_acc` variant).

---

## 2. Applied patch A+B (`training/train_clm_gpu.hexa`)

**A — flip `USE_FUSED`/`USE_FUSED_BATCH` to env-gated default ON:**

```diff
-let USE_FUSED = false  // disabled until gpu_train fused functions land
-let USE_FUSED_BATCH = false
+let USE_FUSED = env_or("CLM_FUSED", "1") == "1"
+let USE_FUSED_BATCH = env_or("CLM_FUSED_BATCH", "1") == "1"
```

**B — drop dead `gpu_train_step_overlapped` branch (line ~1388):**

```diff
-    } else if G_MULTI_STREAM && GRAD_ACC > 1 {
-        loss = gpu_train_step_overlapped(...)   // UNDEFINED FN
-        let _ = gpu_sgd_step(weights, grad, effective_lr, cfg)
-
-    } else if USE_FUSED_BATCH && GRAD_ACC > 1 {
+    } else if USE_FUSED_BATCH && GRAD_ACC > 1 {
```

**C — fallback branch gains fused hot-swap** so `CLM_FUSED=1 / CLM_FUSED_BATCH=0`
still uses fused layer kernels:

```diff
-            let logits = gpu_forward_full(batch_tok_dev, weights, acts, cfg)
-            let raw_loss = gpu_backward_full_with_embed(logits, ...)
+            let logits = if USE_FUSED { gpu_forward_full_fused(...) } else { gpu_forward_full(...) }
+            let raw_loss = if USE_FUSED { gpu_backward_full_with_embed_fused(...) } else { gpu_backward_full_with_embed(...) }
```

Validation (Mac, no GPU): `hexa parse` OK for both `train_clm_gpu.hexa` and
`$HEXA_LANG/self/ml/gpu_train.hexa`.

---

## 3. Expected improvement (THEORETICAL)

Launch savings (fused vs non-fused, GRAD_ACC=8 NL=12):
- fwd: 96 fewer launches → ~0.5 ms saved at 5 µs each
- bwd: 84 fewer launches → ~0.4 ms saved
- batched-GEMM fwd: 688 → 86 cuBLAS calls (~600 saved × 20 µs = ~12 ms)

Projected step time: **180 ms → ~160 ms**, MFU **0.087% → ~0.10%** (THEORETICAL).
**This is an unblock, not the 100× jump alone.** Levers #3/#4/#5 were hiding
behind #1+#2 — all further MFU work must now go through the fused path.

---

## 4. Next levers (post-A/B measurement on H100)

- **Wire `cfg.NH = scale.n_head`** → unlocks hxflash O(S·D), 2–4× at seq=512.
- **Fused QKV weight `[D,3D]`** → 1.3–1.5×.
- **bf16 Tensor-Core GEMM** via `cublasGemmEx(CUDA_R_16BF)` — ALM r7 on same
  H100 SXM hit 70.9% at bf16. Biggest single lever, expected 3–5×.
- **In-place bwd GEMM (`beta=1.0`)** → 1.2–1.5×.
- **Async D2H of loss_buf** — `tensor_from_gpu(loss_buf, 1)` per step blocks
  GPU on 4-byte copy. Buffer device-side, D2H every `LOG_EVERY` → 1.1×.

Stacked ceiling (#1..#5 + bf16): 0.087% × (1.15 × 3.0 × 1.4 × 1.3 × 4.0) ≈
**2.2%** projected. Still short of 10% target — additional levers needed:
GRAD_ACC strided-batched fwd+bwd, AdamW kernel landing, CUDA-graph replay
unlock at GRAD_ACC>1.

---

## 5. Files touched + SSOT

- `training/train_clm_gpu.hexa` — 3 edits (A flags + B dead-branch + C fallback fused).

SSOT `shared/state/training_speed_ceilings.json` **not updated** — per rule
"실측 있을 때만". H100 smoke on pod `qwtjsbw6vbtkpr` produces the next entry
`h100_d512_l12_fused_20260418` with `ms_per_step`, `mfu_pct`,
`delta_vs_h100_d512_l12_best_pct`.
