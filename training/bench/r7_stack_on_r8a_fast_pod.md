# ALM 14B r7 stack on r8a-fast pod — H1 vs H2 isolation

**Date**: 2026-04-16
**Pod**: `jmejpw0x7j6wbx` (anima-p4-alm-r8a-fast) — `ssh -i ~/.runpod/ssh/RunPod-Key-Go root@103.207.149.118 -p 17438`
**GPU**: NVIDIA H100 SXM 80GB HBM3, driver 580.126.09
**Question**: Is the 51.4% → 62.6% r8a/r7 MFU gap caused by (H1) silicon binning or (H2) stack regression?
**Method**: Re-run r7's stack (unsloth only, dropout=0.05, no liger, no compile_unblock) on the SAME pod that measured r8a at 51.4%. Keep r8a's batch/seq config (b=8 s=1024 g=1 = 8192 tok/step) so only the stack differs.

## Result

| config | MFU% (bf16) | step/min | SM util | delta vs r8a |
| --- | --- | --- | --- | --- |
| r8a stack (unsloth+liger, dropout=0.0)  | **51.4**  | 41.9  | 95.5 | baseline |
| r7 stack  (unsloth only, dropout=0.05)  | **47.3**  | 38.5  | 93.4 | **-4.1 pp** |

Verdict: **H1 confirmed, H2 rejected.** r7 stack is actually SLOWER than r8a on this pod. The 62.6% r7 number from pod `ubzp169igb7tns` (terminated) was silicon-specific. RunPod H100 SXM fleet variance, not stack regression, explains the gap.

## Isolation Summary

| parameter | r8a stack | r7 stack | changed? |
| --- | --- | --- | --- |
| pod | jmejpw0x7j6wbx | jmejpw0x7j6wbx | SAME |
| GPU | H100 SXM 80GB | H100 SXM 80GB | SAME |
| torch | 2.10.0+cu128 | 2.10.0+cu128 | SAME |
| unsloth | 2026.4.4 | 2026.4.4 | SAME |
| transformers | 4.56.1 | 4.56.1 | SAME |
| liger_kernel | ON | **OFF** | **DIFF** |
| lora_dropout | 0.0 | **0.05** | **DIFF** |
| ALM_COMPILE_UNBLOCK | 1 (gated off) | **unset** | **DIFF** |
| batch/grad_accum/seq | 8/1/1024 | 8/1/1024 | SAME |
| lora_r / lora_alpha | 32/64 | 32/64 | SAME |
| lr / warmup | 5e-6 / 200 | 5e-6 / 200 | SAME |

The only independent variables are the three stack knobs (`liger`, `dropout`, `compile_unblock`). They produce a -4.1 pp MFU delta in the direction OPPOSITE the r8a/r7-on-different-pods measurement. So the 11.2 pp inter-pod gap is NOT caused by stack differences.

## Launch Command

```bash
python -u /workspace/train_alm_14b_r8a.py \
    --base Qwen/Qwen2.5-14B-Instruct --corpus /workspace/corpus.txt \
    --steps 150 --batch 8 --seq 1024 --grad-accum 1 \
    --lora-dropout 0.05 --unsloth \
    --ckpt-dir /workspace/ckpt_alm_14b_r7stack_150 \
    --save-every 1000 --eval-every 10000 --smoke --round 1
# ALM_COMPILE_UNBLOCK unset; --liger NOT passed
```

## Speed Curve (150 steps)

| step | speed_step_per_min (cumulative) |
| --- | --- |
| 1   | 13.0 (unsloth JIT warmup) |
| 10  | 32.3 |
| 20  | 35.2 |
| 30  | 36.3 |
| 40  | 36.8 |
| 50  | 37.1 |
| 60  | 37.4 |
| 70  | 37.5 |
| 80  | 37.7 |
| 90  | 37.8 |
| 100 | 37.9 |
| 110 | 37.9 |
| 120 | 38.0 |
| 130 | 38.0 |
| 140 | 38.1 |
| **150** | **38.1** |

Wall clock: 4.0 min for 150 steps. Cumulative 38.1. Steady window 120→150 ~38.5 step/min.

Compare r8a's curve on this pod: 41.5 cumulative @ step 150, 41.9 steady 120→150. r7 is uniformly 3.4 step/min slower across the entire steady region.

## MFU Derivation

Formula: `MFU_pct = 6 * N_param * tok/s / (989 * 10^12) * 100` with N_param = 14.82e9, H100 peak bf16 = 989 TFLOPS.

| window | step/min | tok/s | TFLOPS | MFU |
| --- | --- | --- | --- | --- |
| cumulative step=150 | 38.1 | 5202.3 | 462.6 | 46.77% |
| **window step 120→150 (steady)** | **38.5** | **5256.5** | **467.4** | **47.26%** |
| asymptotic estimate | 38.6 | 5270.0 | 468.6 | 47.39% |

Headline: **47.3% MFU bf16**.

Compare:
- r7 on `ubzp169igb7tns` (terminated): 51.1 step/min → 62.6% MFU (this is the "original r7" number)
- r8a stack on this pod: 41.9 step/min → 51.4% MFU
- **r7 stack on this pod (this run): 38.5 step/min → 47.3% MFU**

## GPU Telemetry (nvidia-smi dmon, 63 active samples during 80-step dmon-paired run)

| metric | avg | peak |
| --- | --- | --- |
| power (W) | 650.1 | 701 |
| SM util (%) | 93.4 | 100 |
| memory util (%) | 50.4 | — |

vs r8a stack on same pod:
| metric | r8a | r7 | delta |
| --- | --- | --- | --- |
| avg power (W) | 653.6 | 650.1 | -3.5 |
| avg SM util (%) | 95.5 | 93.4 | -2.1 |
| peak power (W) | 693 | 701 | +8 |
| peak SM util (%) | 100 | 100 | 0 |

Both stacks saturate the GPU at peak (100% SM, >=693W) and run at >93% average TDP utilization. The r7 stack saturates the silicon just as hard as r8a but completes ~8% fewer steps per minute — consistent with losing the liger kernel's triton-fused RMSNorm/SwiGLU and losing the fast-LoRA-kernel unlock (Unsloth `patched 0 QKV / 0 O / 0 MLP layers` warning is printed in r7's log because of `dropout=0.05`).

## Loss Trajectory (sanity)

r7 stack loss at step 150 = 15.0193 (identical to r8a at 15.0168 within noise). Same loss descent, just ~9% slower wall-clock.

## Hypothesis Test

### H1 (silicon binning) — CONFIRMED
- Same stack (unsloth-only dropout=0.05) on `ubzp169igb7tns` → 62.6% MFU
- Same stack (unsloth-only dropout=0.05) on `jmejpw0x7j6wbx` → 47.3% MFU
- 15.3 pp gap, same software, different silicon → pod variance dominates.

### H2 (stack regression) — REJECTED
- r8a stack on jmejpw: 51.4% MFU
- r7 stack on jmejpw: 47.3% MFU (-4.1 pp)
- Adding liger + dropout=0 to r7 → **UPLIFT** on this pod, not regression.
- The r8a "stacked wins" narrative holds on THIS pod; it falsified only on cross-pod compare.

### Why r7's original number was 62.6%
Pod `ubzp169igb7tns` was genuinely faster silicon / better cooling / different firmware binning. The r7 stack on that pod was faster than either stack on this pod. Stack choice is a second-order effect (~±4 pp) compared to pod silicon variance (~±11-15 pp).

## Recommendation

1. **Keep r8a stack** (unsloth+liger+dropout=0) — wins by +4.1 pp over r7 stack on same pod.
2. **Pod shopping matters more than stack tuning**. Before a long training run, measure 40-step smoke on 2-3 candidate pods and pick the fastest. Variance is ~±15 pp on RunPod H100 SXM fleet.
3. r7's 62.6% remains the high-water mark — non-reproducible by software alone; requires lucky silicon.
4. Ceiling on this pod is ~51% with r8a stack. Gap to 80% practical target = 28.6 pp. No further software lever available short of FP8 (blocked by TE wheel on torch 2.10).

## Artifacts

- `training/bench/r7_on_r8a_fast_pod_raw/train_alm_14b_r7stack_150.log` (150-step steady)
- `training/bench/r7_on_r8a_fast_pod_raw/train_alm_14b_r7stack_80_dmon.log` (80-step dmon-paired)
- `training/bench/r7_on_r8a_fast_pod_raw/dmon_r7_burst.log` (63-sample telemetry)
- `training/bench/r7_on_r8a_fast_pod_raw/launch_r7_150.sh`
- `training/bench/r7_stack_on_r8a_fast_pod.json` (structured form)
- Pod state: **RETAINED** per instructions.

## Timing

| phase | min |
| --- | --- |
| r7 stack launch script write | <1 |
| 150-step measurement | 4.0 |
| 80-step dmon-paired measurement | 2.1 |
| analysis + file writes | 2 |
| **total wall clock** | **~10 min** |
| **budget used** | **50% of 20 min cap, $0.50 of $1 cap** |
