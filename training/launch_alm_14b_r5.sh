#!/usr/bin/env bash
# launch_alm_14b_r5.sh — ALM 14B r5 LoRA training (RunPod H100 80GB)
#
# SAME-BASE K-QUALITY RECOVERY PATH.
#
# r4 outcome:   eval_loss 3.6466 -> 0.0289 (108x) but Korean generation at
#               step 2000 is INCOHERENT (broken UTF-8 / CJK leak / English).
# r5 strategy:  stay on Qwen/Qwen2.5-14B-Instruct, retarget hyperparameters
#               at Korean quality (not loss). A parallel agent owns the
#               base-swap lineage (launch_alm_14b_r5_kbase.sh) — do NOT
#               share markers, checkpoint dirs, or R2 prefixes.
#
# r5 changes vs r4 (see train_alm_14b_r5.hexa for full diagnosis):
#   - lora_r         :  64   -> 128        (2x capacity for Korean prior)
#   - lora_alpha     :  128  -> 256        (keep 2:1 ratio)
#   - lora_dropout   :  0.05 -> 0.10       (damp memorization)
#   - lr             :  5e-6 -> 1e-4       (20x, std LoRA range)
#   - warmup         :  500  -> 2000       (10% of steps, 4x longer)
#   - steps          :  10k  -> 20k        (0.37 epoch coverage)
#   - target_modules :  UNCHANGED          (q/k/v/o + gate/up/down = 7)
#   - unfreeze       :  NONE -> embed_tokens + lm_head   (NEW)
#   - corpus prep    :  RAW  -> dedupe + shuffle + doc-separator
#   - eval/save cadence: UNCHANGED (500 / 2000)
#
# Memory budget (see train_alm_14b_r5.hexa):
#   expected resident ~58 GB / 80 GB  (headroom ~22 GB)
#   biggest item     : AdamW fp32 moments on embed+lm_head (~12.5 GB)
#
# Trigger condition (enforced by preflight):
#   - /workspace/READY_FOR_R5 MUST exist (created manually by the ops owner
#     after r4 has stopped AND the H100 is free).
#   - /workspace/READY_FOR_R5_KBASE MUST NOT exist simultaneously (that
#     marker belongs to the sister base-swap agent; if both are present we
#     abort because the H100 can only host one r5 run).
#   - /workspace/READY_FOR_32B MUST NOT exist (32B would co-contend).
#
# Run on RunPod H100 80GB:
#   1. Wait for /workspace/READY_FOR_R5 to appear.
#   2. scp launch_alm_14b_r5.sh + train_alm_14b_r5.hexa to /workspace/
#      (train_alm_14b.py is already on the pod — but must be the patched
#      version with --target-modules / --unfreeze-embed / --unfreeze-lm-head
#      / --doc-separator / --shuffle-docs / --dedupe support).
#   3. bash launch_alm_14b_r5.sh
#
set -euo pipefail

echo "============================================"
echo "  ALM 14B r5 — LoRA r=128 a=256, attn+MLP"
echo "                + embed_tokens + lm_head unfrozen"
echo "                + LR=1e-4 warmup=2000 steps=20000"
echo "                + dedupe/shuffle/doc-separator"
echo "                (same-base K-quality recovery)"
echo "============================================"

# ── Preflight: trigger marker (R5 only, must NOT share) ──
MARKER="/workspace/READY_FOR_R5"
FORBIDDEN_KBASE="/workspace/READY_FOR_R5_KBASE"
FORBIDDEN_32B="/workspace/READY_FOR_32B"

if [[ ! -f "$MARKER" ]]; then
    echo "[preflight] ✗ $MARKER missing — not cleared to launch r5"
    echo "[preflight]   The ops owner creates this marker after r4 has"
    echo "[preflight]   stopped and the H100 is free. Refusing to launch."
    exit 1
fi
echo "[preflight] ✓ trigger marker present: $MARKER"
cat "$MARKER" 2>/dev/null || true

if [[ -f "$FORBIDDEN_KBASE" ]]; then
    echo "[preflight] ✗ $FORBIDDEN_KBASE also present — base-swap sister agent"
    echo "[preflight]   is also cleared to launch. The H100 cannot host both."
    echo "[preflight]   Remove one of the markers before relaunching."
    exit 1
fi
echo "[preflight] ✓ no base-swap conflict ($FORBIDDEN_KBASE absent)"

if [[ -f "$FORBIDDEN_32B" ]]; then
    echo "[preflight] ✗ $FORBIDDEN_32B present — 32B r1 is cleared to launch"
    echo "[preflight]   and would contend with r5 on the same H100. Refusing."
    exit 1
fi
echo "[preflight] ✓ no 32B conflict ($FORBIDDEN_32B absent)"

# ── Preflight: r4 is not still writing ──
R4_CKPT_DIR="/workspace/ckpt_alm_14b_r4"
if [[ -d "$R4_CKPT_DIR" ]]; then
    if pgrep -f "train_alm_14b.py.*ckpt_alm_14b_r4" >/dev/null 2>&1; then
        echo "[preflight] ✗ r4 python process still running on $R4_CKPT_DIR"
        echo "[preflight]   Refusing to launch r5 while r4 is live."
        exit 1
    fi
    echo "[preflight] ✓ r4 has stopped (no python process on $R4_CKPT_DIR)"
fi

# ── Preflight: hexa config parse ──
HEXA_BIN="${HEXA_BIN:-/usr/local/bin/hexa}"
HEXA_CFG="/workspace/train_alm_14b_r5.hexa"
if [[ -x "$HEXA_BIN" && -f "$HEXA_CFG" ]]; then
    echo "[preflight] parse-checking $HEXA_CFG ..."
    "$HEXA_BIN" "$HEXA_CFG" > /workspace/train_alm_14b_r5.plan.log 2>&1 || {
        echo "[preflight] ✗ train_alm_14b_r5.hexa failed to parse"
        cat /workspace/train_alm_14b_r5.plan.log
        exit 1
    }
    echo "[preflight] ✓ hexa config OK (see /workspace/train_alm_14b_r5.plan.log)"
else
    echo "[preflight] ⚠ hexa binary or config missing — continuing without dry-run"
    echo "[preflight]   (HEXA_BIN=$HEXA_BIN  HEXA_CFG=$HEXA_CFG)"
fi

# ── Preflight: GPU / corpus / disk / HF token ──
echo "[preflight] checking GPU..."
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader

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
# Qwen2.5-14B-Instruct is public; HF_TOKEN optional.

# ── HF cache (pre-staged on /workspace for 100 GB partition) ──
export HF_HUB_CACHE="/workspace/hf_cache"
export HF_HOME="/workspace/hf_cache"
export TRANSFORMERS_CACHE="/workspace/hf_cache"

# ── Speedup patch 20260415: NCCL / CUDA env tuning ──
# No-op on single-H100 (no collectives) but correct for multi-GPU r6.
export NCCL_P2P_DISABLE="${NCCL_P2P_DISABLE:-0}"
export NCCL_IB_GID_INDEX="${NCCL_IB_GID_INDEX:-3}"
export NCCL_NET_GDR_LEVEL="${NCCL_NET_GDR_LEVEL:-4}"
export NCCL_ASYNC_ERROR_HANDLING="${NCCL_ASYNC_ERROR_HANDLING:-1}"
export TORCH_NCCL_BLOCKING_WAIT="${TORCH_NCCL_BLOCKING_WAIT:-1}"
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"

PRESTAGED="/workspace/hf_cache/models--Qwen--Qwen2.5-14B-Instruct"
if [[ -d "$PRESTAGED" ]]; then
    echo "[preflight] ✓ Qwen2.5-14B pre-staged at $PRESTAGED"
    du -sh "$PRESTAGED" 2>/dev/null | awk '{print "[preflight]   size: " $1}'
else
    echo "[preflight] ⚠ Qwen2.5-14B NOT pre-staged — r4 used the same base,"
    echo "[preflight]   so cache should already exist under a different dir."
fi

# ── Preflight: trainer feature check ──
# r5 needs new flags that r4 didn't use. Verify the pod's train_alm_14b.py
# supports them BEFORE we waste H100 time discovering it doesn't.
TRAINER="/workspace/train_alm_14b.py"
if [[ ! -f "$TRAINER" ]]; then
    echo "[preflight] ✗ trainer missing: $TRAINER"
    exit 1
fi
HELP_OUT="$(python3 "$TRAINER" --help 2>&1 || true)"
MISSING=()
for flag in --target-modules --unfreeze-embed --unfreeze-lm-head \
            --doc-separator --shuffle-docs --dedupe ; do
    if ! grep -q -- "$flag" <<<"$HELP_OUT"; then
        MISSING+=("$flag")
    fi
done
if (( ${#MISSING[@]} > 0 )); then
    echo "[preflight] ✗ pod's $TRAINER is missing required r5 flags:"
    for f in "${MISSING[@]}"; do echo "[preflight]    $f"; done
    echo "[preflight]   Patch train_alm_14b.py on the pod first. Refusing to launch."
    exit 1
fi
echo "[preflight] ✓ trainer supports all r5 flags"

# ── Fresh checkpoint dir (never reuse) ──
CKPT_DIR="/workspace/ckpt_alm_14b_r5"
rm -rf "$CKPT_DIR"
mkdir -p "$CKPT_DIR"

# ── Save a copy of the hexa plan alongside the checkpoint for audit ──
cp -f "$HEXA_CFG" "$CKPT_DIR/train_alm_14b_r5.hexa" 2>/dev/null || true
cp -f /workspace/train_alm_14b_r5.plan.log "$CKPT_DIR/train_alm_14b_r5.plan.log" 2>/dev/null || true

# ── Launch ──
# R2 prefix (distinct from r4 and kbase):
#     r2:anima-models/alm14b/r5/step_{step}/
# Model tag + round give the same naming to upload_to_r2().
# Speedup patch 20260415: --no-grad-ckpt disables activation checkpointing.
# At batch=1 seq=1024 the 14B fits in ~70 GB peak without ckpt. MUST validate
# with nvidia-smi at step 50 — if peak > 72 GB, remove --no-grad-ckpt.
python3 "$TRAINER" \
    --base Qwen/Qwen2.5-14B-Instruct \
    --corpus "$CORPUS" \
    --steps 20000 \
    --lr 1e-4 \
    --batch 1 \
    --grad-accum 8 \
    --seq 1024 \
    --warmup 2000 \
    --lora-r 128 \
    --lora-alpha 256 \
    --lora-dropout 0.10 \
    --target-modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj \
    --unfreeze-embed \
    --unfreeze-lm-head \
    --doc-separator \
    --shuffle-docs \
    --dedupe \
    --no-grad-ckpt \
    --ckpt-dir "$CKPT_DIR" \
    --save-every 2000 \
    --eval-every 500 \
    --model-tag alm14b \
    --round 5 \
    2>&1 | tee "$CKPT_DIR/train_r5.log"

echo "[done] 14B r5 training complete — check $CKPT_DIR"
echo "[next] python3 /workspace/eval_alm_14b.py --ckpt $CKPT_DIR/step_20000 --korean-quality"
echo "[next] Abort-signal audit at step 500 / 1000 / 2000 — see train_alm_14b_r5.hexa header"
