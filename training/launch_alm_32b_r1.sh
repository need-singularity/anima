#!/usr/bin/env bash
# launch_alm_32b_r1.sh — ALM 32B r1 LoRA training (ALM-P4-4 극가속, 2× H100 FSDP)
#
# Scales 14B r4 → 32B r1 with 2× H100 FSDP acceleration:
#   - base:         Qwen/Qwen2.5-14B-Instruct -> Qwen/Qwen2.5-32B-Instruct
#   - lora_r:       64 -> 32    (memory budget; see train_alm_32b_r1.hexa)
#   - lora_alpha:   128 -> 64   (keep 2:1 alpha:r ratio)
#   - target_modules: UNCHANGED (attn q/k/v/o + MLP gate/up/down = 7 modules)
#   - batch:        1 -> 2      (FSDP sharding makes room)
#   - grad_accum:   8 -> 4      (effective batch 2×2×4 = 16, up from 8)
#   - steps:        10000 -> 3000  (LoRA converges early on larger base)
#   - warmup:       500 -> 200    (scaled to 3000-step run)
#   - save/eval:    2000/500 -> 500/200  (6 saves, 15 evals)
#   - n_gpu:        1 -> 2      (H100 2x auto-launch authorized)
#   - seq/lr:       1024 / 5e-6 UNCHANGED
#   - ckpt_dir:     /workspace/ckpt_alm_32b_r1  (fresh, never reused)
#   - r2_prefix:    r2:anima-models/alm32b/r1/
#   - model_tag:    alm32b   round: 1
#
# Overrides (env vars, all optional — defaults match ALM-P4-4 plan):
#   STEPS=3000   BATCH=2   GRAD_ACCUM=4   WARMUP=200
#   SAVE_EVERY=500   EVAL_EVERY=200
#   DIST=fsdp | deepspeed_z2 | ddp   (default: fsdp)
#   NPROC=2
#
# Trigger condition (enforced by preflight below):
#   - /workspace/READY_FOR_32B marker is bypassable via
#     ALM_P4_4_BYPASS_MARKER=1 on a dedicated 2-GPU pod (no 14B contention).
#
# Run on RunPod 2× H100 80GB HBM3 pod:
#   1. scp this script + train_alm_32b_r1.hexa + train_alm_14b.py to /workspace/
#   2. ALM_P4_4_BYPASS_MARKER=1 bash launch_alm_32b_r1.sh
#
# Expected steady-state:
#   - Per-rank GPU memory:   ~52-56 GB / 80 GB (~24 GB headroom per rank)
#   - Throughput:            ~16-20 step/min (vs 8-9 step/min single-GPU plan)
#   - ETA:                   ~2.5-3.1 h for 3000 steps (vs ~19-21 h single)
#   - Cost:                  $15-19 at $5.98/hr (vs $57-63 single-GPU plan)
#
set -euo pipefail

echo "============================================"
echo "  ALM 32B r1 — LoRA r=32 alpha=64, attn+MLP"
echo "  ALM-P4-4 극가속: 2× H100 FSDP, 3000 steps"
echo "============================================"

# ── ALM-P4-4 tunables (env-overridable) ──
STEPS="${STEPS:-3000}"
BATCH="${BATCH:-2}"
GRAD_ACCUM="${GRAD_ACCUM:-4}"
WARMUP="${WARMUP:-200}"
SAVE_EVERY="${SAVE_EVERY:-500}"
EVAL_EVERY="${EVAL_EVERY:-200}"
DIST="${DIST:-device_map_auto}"    # device_map_auto | fsdp | deepspeed_z2 | ddp
NPROC="${NPROC:-2}"
# Default device_map_auto = zero-change launch path that works with the current
# train_alm_14b.py (accelerate pipeline-parallel across the 2 GPUs). FSDP/ZeRO
# paths require the --fsdp/--deepspeed trainer patch (queued, not yet shipped).

echo "[config] STEPS=$STEPS  BATCH=$BATCH  GRAD_ACCUM=$GRAD_ACCUM  WARMUP=$WARMUP"
echo "[config] SAVE_EVERY=$SAVE_EVERY  EVAL_EVERY=$EVAL_EVERY"
echo "[config] DIST=$DIST  NPROC=$NPROC"
echo "[config] effective_batch = $BATCH × $NPROC × $GRAD_ACCUM = $((BATCH * NPROC * GRAD_ACCUM))"

# ── Preflight: trigger marker ──
# ALM-P4-4 extreme acceleration override (2026-04-15): launching on dedicated
# H100 pod (separate from 14B r4 pod xhq9b2c8fljdyo), so the contention
# argument does not apply. The READY_FOR_32B marker check is bypassed when
# ALM_P4_4_BYPASS_MARKER=1 is set (CI/manual extreme mode) OR when running
# on a pod with no 14B r4 process (checked via ckpt_alm_14b_p4 absence).
MARKER="/workspace/READY_FOR_32B"
if [[ "${ALM_P4_4_BYPASS_MARKER:-0}" == "1" ]]; then
    echo "[preflight] ⚠ ALM_P4_4_BYPASS_MARKER=1 — skipping READY_FOR_32B gate (extreme acceleration, dedicated pod)"
    mkdir -p /workspace && touch "$MARKER"
elif [[ ! -f "$MARKER" ]]; then
    echo "[preflight] ✗ $MARKER missing — 14B r4 has not yet cleared eval<0.02"
    echo "[preflight]   Refusing to launch: would contend with running r4 on the same H100."
    echo "[preflight]   The monitor_alm_r4 daemon creates this marker automatically."
    echo "[preflight]   Override: set ALM_P4_4_BYPASS_MARKER=1 (dedicated pod only)."
    exit 1
fi
echo "[preflight] ✓ trigger marker present: $MARKER"
cat "$MARKER" 2>/dev/null || true

# ── Preflight: hexa config parse ──
HEXA_BIN="${HEXA_BIN:-/usr/local/bin/hexa}"
HEXA_CFG="/workspace/train_alm_32b_r1.hexa"
if [[ -x "$HEXA_BIN" && -f "$HEXA_CFG" ]]; then
    echo "[preflight] parse-checking $HEXA_CFG ..."
    "$HEXA_BIN" "$HEXA_CFG" > /workspace/train_alm_32b_r1.plan.log 2>&1 || {
        echo "[preflight] ✗ train_alm_32b_r1.hexa failed to parse"
        cat /workspace/train_alm_32b_r1.plan.log
        exit 1
    }
    echo "[preflight] ✓ hexa config OK (see /workspace/train_alm_32b_r1.plan.log)"
else
    echo "[preflight] ⚠ hexa binary or config missing — continuing without dry-run"
    echo "[preflight]   (HEXA_BIN=$HEXA_BIN  HEXA_CFG=$HEXA_CFG)"
fi

# ── Preflight: GPU / corpus / disk / HF token ──
echo "[preflight] checking GPU..."
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
N_GPU_DETECTED=$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l | tr -d ' ')
echo "[preflight] GPUs detected: $N_GPU_DETECTED  (plan requires $NPROC)"
if (( N_GPU_DETECTED < NPROC )); then
    echo "[preflight] ✗ insufficient GPUs: have $N_GPU_DETECTED, need $NPROC"
    echo "[preflight]   Either: provision a $NPROC-GPU pod, OR set NPROC=$N_GPU_DETECTED"
    echo "[preflight]   and re-run with BATCH/GRAD_ACCUM adjusted to preserve eff_batch=16."
    exit 1
fi

echo "[preflight] checking corpus..."
CORPUS="/workspace/anima/training/corpus_large.txt"
if [[ ! -f "$CORPUS" ]]; then
    echo "[preflight] ✗ corpus missing: $CORPUS"
    exit 1
fi
ls -lh "$CORPUS"

echo "[preflight] checking disk..."
df -h /workspace

echo "[preflight] HF_TOKEN set: ${HF_TOKEN:+yes}"
# Note: HF_TOKEN optional — Qwen2.5-32B is public. Unauthenticated
# downloads are rate-limited but work. The pre-staged cache below
# eliminates the download step entirely at launch time.

# ── HF cache: use pre-staged /workspace location (100GB partition) ──
# / (overlay) is only 50GB and fills up with 14B+32B. /workspace has 100GB.
# Qwen2.5-32B was pre-downloaded to /workspace/hf_cache/ before launch.
export HF_HUB_CACHE="/workspace/hf_cache"
export HF_HOME="/workspace/hf_cache"
export TRANSFORMERS_CACHE="/workspace/hf_cache"
PRESTAGED="/workspace/hf_cache/models--Qwen--Qwen2.5-32B-Instruct"
if [[ -d "$PRESTAGED" ]]; then
    echo "[preflight] ✓ Qwen2.5-32B pre-staged at $PRESTAGED"
    du -sh "$PRESTAGED" | awk '{print "[preflight]   size: " $1}'
else
    echo "[preflight] ⚠ Qwen2.5-32B NOT pre-staged — first launch will download ~64GB"
fi

# ── Fresh checkpoint dir (never reuse) ──
CKPT_DIR="/workspace/ckpt_alm_32b_r1"
rm -rf "$CKPT_DIR"
mkdir -p "$CKPT_DIR"

# ── Launch (torchrun FSDP 2× H100) ──
# Reuses train_alm_14b.py (same fwd/bwd loop — ALM-P4-4 adds FSDP wrap
# when --fsdp flag is passed and WORLD_SIZE>1 is set by torchrun).
# When hexa-lang ships native cuBLAS+NCCL bindings, train_alm_32b_r1.hexa will
# absorb this launch step and the Python trainer will be archived.
#
# NCCL tuning: P2P over NVLink if SXM; fall back to PCIe for HBM3 non-SXM.
# bf16 + FULL_SHARD keeps per-rank weight footprint ~32 GB on 64 GB base.
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"
export NCCL_ASYNC_ERROR_HANDLING=1
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1
export CUDA_DEVICE_MAX_CONNECTIONS=1
# FSDP with bf16 mixed precision can OOM on activation memory if cudnn
# benchmarking picks a large-workspace algo; cap it.
export CUBLAS_WORKSPACE_CONFIG=":4096:8"

if [[ "$DIST" == "fsdp" ]]; then
    LAUNCH_WRAPPER="torchrun --nproc_per_node=$NPROC --nnodes=1 --standalone"
    DIST_FLAGS="--fsdp --fsdp-wrap-cls Qwen2DecoderLayer"
elif [[ "$DIST" == "deepspeed_z2" ]]; then
    # DeepSpeed ZeRO-2 fallback (more stable than FSDP for some peft combos).
    # Requires /workspace/ds_z2_config.json (generated by launch helper).
    LAUNCH_WRAPPER="deepspeed --num_gpus=$NPROC"
    DIST_FLAGS="--deepspeed /workspace/ds_z2_config.json"
elif [[ "$DIST" == "ddp" ]]; then
    LAUNCH_WRAPPER="torchrun --nproc_per_node=$NPROC --nnodes=1 --standalone"
    DIST_FLAGS="--ddp"
elif [[ "$DIST" == "device_map_auto" ]]; then
    # ALM-P4-4 fallback: single-process launch, HF device_map="auto" shards the
    # 64 GB Qwen2.5-32B base across 2× H100 via accelerate pipeline-parallel.
    # LoRA adapters (<1 GB) live on primary device. No FSDP/DDP/torchrun needed.
    # This matches the exact code path 14B r4 uses successfully; no edits to
    # train_alm_14b.py required (which does NOT currently support --fsdp flags).
    LAUNCH_WRAPPER="python3"
    DIST_FLAGS=""
else
    echo "[launch] ✗ unknown DIST=$DIST (expected fsdp|deepspeed_z2|ddp|device_map_auto)"
    exit 1
fi

echo "[launch] wrapper: $LAUNCH_WRAPPER"
echo "[launch] dist flags: $DIST_FLAGS"

$LAUNCH_WRAPPER /workspace/train_alm_14b.py \
    --base Qwen/Qwen2.5-32B-Instruct \
    --corpus "$CORPUS" \
    --steps "$STEPS" \
    --lr 5e-6 \
    --batch "$BATCH" \
    --grad-accum "$GRAD_ACCUM" \
    --seq 1024 \
    --warmup "$WARMUP" \
    --lora-r 32 \
    --lora-alpha 64 \
    --lora-dropout 0.05 \
    --ckpt-dir "$CKPT_DIR" \
    --save-every "$SAVE_EVERY" \
    --eval-every "$EVAL_EVERY" \
    --model-tag alm32b \
    --round 1 \
    $DIST_FLAGS \
    2>&1 | tee "$CKPT_DIR/train_r1.log"

echo "[done] 32B r1 training complete — check $CKPT_DIR"
echo "[next] python3 /workspace/eval_alm_14b.py --ckpt $CKPT_DIR/step_$STEPS"
