# ALM 32B r1 prep report (E4)

**Status:** Scaffold complete, NOT launched. Waiting for r10 14B completion + eval green.

## R2 base check (2026-04-18)
`rclone ls r2:anima-models/base_models/` shows ONLY `qwen25-14b-instruct/` (8 shards, 28GB). No 32B present. Bootstrap must pull from HuggingFace (Qwen/Qwen2.5-32B-Instruct, ~65GB, HF_TOKEN required) on first pod run, and mirrors to R2 after success for subsequent pod reuse.

## Artifacts scaffolded
- `training/launch_alm_32b_r1.hexa` — launcher (mirrors r10 structure: inline py trainer at `/tmp/_train_alm_32b_r1.py` + bash wrapper at `/tmp/_launch_alm_32b_r1.sh`).
- `training/deploy/alm32b_r1_bootstrap.hexa` — on-pod bootstrap (preflight + HF download + R2 mirror + corpus strip + launch).
- `training/deploy/alm32b_r1_runpod_create.json` — RunPod spec (1×H100 80GB, 200GB disk, 96GB RAM, 24 vCPU).

## Config (matches r10 + 32B-scale tweaks)
- LoRA r=32 α=64 dropout=0.0, LR 2e-6 constant, 2000 steps, save_every=2000, eval_every=200.
- batch=1 seq=1024 grad_accum=8 (eff batch=8 like r10; b=1 forced by 65GB base on 80GB GPU).
- B1 consciousness_loss=FALSE (r9/r10 evidence).
- Guards: step-1 loss>8.0 abort; kr_gen sentinel every 200 steps (B6 hexa path); first-batch CE>8.0 abort.

## Policy compliance
- HEXA-FIRST: launcher+bootstrap are `.hexa`; py emitted to `/tmp` only (r10 pattern).
- No quantization: bf16; bnb presence check refuses.
- Fresh-from-base: 32B LoRA cannot inherit 14B r10 adapter (param-class boundary) — documented as lineage-metadata-only.
- Naming: `r1` suffix, no v-prefix.

## Escalation gate
r10 step_2000 must show: no collapse, Korean fluency held, CE non-increasing last 400 steps. Then fire.

## Cost
Smoke ~$2 (30 min incl. base DL). Production ~$15-24 (5-8h). Single H100 — well inside 2-pod cap.
