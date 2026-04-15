# Phase 3 — 500-step initial learning (TCLM-P1-1)

## Result: PASS

## Diagnostic + Fix

Initial 500-step run with `LR_MAX=3e-4 INIT_SCALE=0.02 WARMUP=100` saw loss stuck at 5.545 (= ln(256), random baseline). Effective peak LR after `/GRAD_ACC=8` was `3.75e-5` — too small for d=64 byte-level model to escape uniform logits.

**Fix applied** (updated `training/train_clm_d64_kr.hexa`):
- `LR_MAX` 3e-4 → 3e-3 (10x)
- `LR_MIN` 3e-5 → 3e-4
- `INIT_SCALE` 0.02 → 0.1 (matches CPU reference `train_byte_kr.hexa`)

Reference: `train_byte_kr.hexa` uses `LR=0.05 INIT_SCALE=0.1` at D=16-64, which is where the d=64 byte-level path is known to converge on CPU.

## Run Metrics (after fix)

| step | loss | lr | ppl | phi_proxy |
|---:|---:|---:|---:|---|
| 1 | 5.7105 | 3.75e-06 | — | — |
| 50 | 5.4682 | 1.875e-04 | — | — |
| 100 | 5.1715 | 3.750e-04 | 168.87 | nan |
| 150 | 4.7440 | 3.622e-04 | — | — |
| 200 | 4.5459 | 3.256e-04 | 88.81 | nan |
| 250 | 4.3923 | 2.708e-04 | — | — |
| 300 | 4.1359 | 2.063e-04 | 63.12 | nan |
| 350 | 4.1266 | 1.417e-04 | — | — |
| 400 | 3.9037 | 8.693e-05 | 54.27 | nan |
| 450 | 3.8948 | 5.035e-05 | — | — |
| 500 | 4.0937 | 3.750e-05 | 51.48 | nan |

- loss_initial = 5.7105 → loss_final = 4.0937 (Δ = **-1.617**)
- ppl 168 → 51 (3.3x reduction)
- ckpt `step_500.hexackpt` saved (51 tensors)
- wall_time = 19.0 s, **s/step = 0.040 (40 ms/step)**
- OOM / crash: 0
- kernel launch errors: 0

## phi_proxy=nan (known bug, Phase 4 focus)

`measure_phi_proxy` reads from `eval_acts.layers[NL-1].y` and computes variance via 1MB D2H sample. With d=64 NL=6 SEQ=128, sample is 32KB = 8192 f32, well under cap. Reports `-nan`/`nan` consistently across all eval points. Likely causes:
1. sample tensor not populated during eval forward (eval is separate from training acts)
2. NaN propagation from a kernel (softmax saturation, rms zero variance)
3. indexing bug in `measure_phi_proxy` emitting for the wrong pointer

Decision: defer diagnosis to Phase 4. The CE path is clearly working (loss drops from 5.71 → 4.1, unambiguous convergence). Phi_proxy is the measurement layer, not training. Phase 4 will either fix phi_proxy or fall back to CE-only gate for TCLM-P1-1 PASS judgment.

## Budget
- phase 3 budget: 30min / $1.50
- actual: ~18 min wall (diagnose + 2× 500-step runs + fix) → ~$0.90
- cumulative: ~$2.05

## GATE (from original spec)
- loss_500 (4.09) < loss_50 (5.47) → PASS
- OOM/crash: 0 → PASS
- **Phase 4 entry: APPROVED**
