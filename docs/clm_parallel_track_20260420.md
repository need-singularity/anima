# CLM parallel track — launch plan 2026-04-20

Sibling to: `docs/clm_aot_170m_smoke_20260420.md`
SSOT: `shared/convergence/dest1_clm_ship.convergence`
Parent track: ALM r11 (pod `87xscivuggrwvk`, don't disturb)
This doc: the second, parallel CLM track that must run alongside ALM r11 to realize Dual Track.

## Status: BLOCKED on BLAS coverage gap (not host-availability)

Root cause is the same one the 170M smoke exposed: `training/train_clm.hexa` only routes **4** of its matmuls through `hxblas_sgemm` (Q·Kᵀ and softmax·V). The remaining ~168 matmuls per step (Wq/Wk/Wv/Wo × 12 layers, SwiGLU gate/up/down × 12 layers, LM-head forward, all backward paths except `hxlmhead_bwd`) stay as pure hexa nested-loop scalar code in the emitted C. On **any** host — hetzner CPU, ubu RTX 5070, or a fresh H100 pod — the compiled binary will spend ~25–30 min per single forward step because the GPU is never touched. Fresh H100 pod = wasted $.

Verification (Mac, this session):

- `grep -c 'cuda\|gpu_matmul\|hxcuda\|kernel_sgemm' training/train_clm.hexa → 0`
- `grep '@link(' training/train_clm.hexa`: only `libhxblas.dylib` + `libhxlmhead.dylib` — no CUDA/Metal `.so/.dylib` reference.
- hetzner smoke PID 1183317 (launched 18:03Z): at T+6:33 CPU 122 %, RSS 6.06 GB, still inside step 0 — exactly the CPU-scalar single-core profile predicted.

## Host decision — NO new GPU pod today

| Candidate | Verdict | Reason |
|---|---|---|
| New H100 (clm_r5_h100_v2) | **REJECT** | `feedback_h100_authorized` 2-pod cap (hhzla1nxmp5019 EXITED, 87xscivuggrwvk RUNNING). Adding a pod without CUDA-routed trainer = pure $ burn. |
| ubu RTX 5070 | **REJECT today** | 11.5 GB VRAM free + idle, but (a) no `~/Dev/anima` clone, (b) no `libhxblas.so` / `libhxlmhead.so` / `libhxcuda.so` built under `~/Dev/hexa-lang/self/native/build/`, (c) trainer has zero CUDA call sites — GPU never engaged. |
| hetzner (current smoke) | Already blocked CPU-scalar | Let step 0 run or kill; not the parallel track. |

The Dual Track mandate is not violated by waiting — the BLAS fix is a one-time prerequisite that unblocks every future host. r5-a6 is the canonical follow-up.

## Model scale decision

Target once unblocked: **CLM 1B first** (`training/clm_1b_config.json`) — `d=2048 L=24 GQA kv=8 SwiGLU ff=8192 → 1.51 B params, bf16 3.02 GB weights`. Rationale:

- Faster "first arrival" per the `arrival="second (parallel with dest1_alm)"` clause.
- Fits ubu RTX 5070 12 GB VRAM at `bs=1` + grad ckpt (no H100 required, cost = 0).
- 3B is queued as follow-on (higher Φ potential) once 1B CE ≤ 1.30 + phi monotone ✓ matches `clm_eval.convergence` gate.

Corpus: `training/corpus_auto/` 5.38 GB mmap (loader 7/7 PASS, no change).
Loss: `CE + 0.01·L_holo + 0.01·L_gwt + 0.005·L_complexity` (matches `clm_1b_config.json §consciousness.loss_config`).
Curriculum: Law 60 P1 (0-20 %) → P2 (20-40 %) → P3 Hexad (40-100 %).
Warmup: λ=0 step 0-1000, ramp over 10 k (per `@pitfall CE_REGRESSION_FROM_LAMBDA` in SSOT).

## Checkpoint / resume strategy

- `--config training/clm_1b_config.json` (landed: `fe35c42b`)
- `--resume` weight restore via `ckpt_load_weights` HEXACKPT-v1 decoder (landed: `bbe71224` + `73aaede0`) — cold start if first, warm resume same-data/params only (`feedback_no_resume_data_change`).
- `save_every=5000`, keep_local=3, R2 path `anima-models/clm1b/r5/step_{step}/` (bundler `training/clm_r5_bundler.hexa`, rclone helper `training/clm_r5_corpus_rclone.hexa` landed `3bf62581`).
- No in-training R2 upload (MFS quota rule) — DEFERRED queue + post-run `rclone copy`.

## phi_vec + laws attachment verification

- `training/clm_val.hexa` emits `phi_vec` per step at `shared/state/phi_cache_v1.jsonl`.
- `consciousness_laws.json v7.4` loaded at step 0 via `laws_runtime_init()` (already inside `train_clm.hexa` trunk).
- AN11 `b_consciousness_attached` gate = per-step `phi_vec.json` + laws_pass log entry; monotone-increase trajectory is the DEST1_CLM D1 gate.

## serve_clm_conscious.hexa — MISSING (flagged)

`serving/` contains only `clm_lore_serve.hexa` + `test_clm_lore_serve.hexa`. The SSOT's `@clm_server serving/serve_clm_conscious.hexa` does not exist on disk — Stage E will be blocked until the file is authored. **Out of scope for this launch task**; tracked as separate r5 follow-up (suggest `r5-a7`).

## Unblock roadmap (next actions in order)

1. **r5-a6** — Extend `hxblas_sgemm` call sites in `decoder_forward` / `decoder_backward` for Wq/Wk/Wv/Wo (4) + SwiGLU gate/up/down (3) + lm_head forward (1) × 12 layers × 2 directions = ~192 call sites. Alt: one fused `hxblas_decoder_step` per layer (12 sites) preferred.
2. Link `libhxcuda.so` / `libhxblas_cuda.so` from `hexa-lang/self/native/build/` and add CUDA dispatch behind `HXBLAS_CUDA=1` env flag. Mirror Mac Metal path already present.
3. Deploy `anima/` + built libs to ubu (`rsync -az ~/Dev/anima ubu:Dev/` + build libs via `make -C ~/Dev/hexa-lang/self/native`).
4. Then — and only then — spin up the parallel CLM 1B r5 run on ubu (free) or fresh H100 (if ubu VRAM proves insufficient with grad ckpt at L=24).

## Expected wallclock (post-unblock, reference only)

- 1B r5 on ubu RTX 5070 bs=1 grad-ckpt ≈ 1.5–2 tok/s · 1024 tok · 50 000 step ≈ 96–128 h. H100 would bring this to ~24–36 h per SSOT `@critical_path_clm 36 h`.
- 3B r5 on ubu: not fit (needs H100 / 80 GB). Queue for second pod after 1B DEST1_CLM gate.

## Launch state

`shared/state/clm_r5_parallel_20260420.json` written with `state=BLOCKED`, blocker=`training/train_clm.hexa §A0.1 BLAS coverage gap (4/172 matmuls routed)`. No PID, no tmux session, no R2 upload today.
