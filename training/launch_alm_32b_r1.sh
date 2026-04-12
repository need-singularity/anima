#!/usr/bin/env bash
# launch_alm_32b_r1.sh — ALM 32B r1 LoRA training (RunPod H100 80GB)
#
# Scales 14B r4 → 32B r1:
#   - base:         Qwen/Qwen2.5-14B-Instruct -> Qwen/Qwen2.5-32B-Instruct
#   - lora_r:       64 -> 32    (memory budget; see train_alm_32b_r1.hexa)
#   - lora_alpha:   128 -> 64   (keep 2:1 alpha:r ratio)
#   - target_modules: UNCHANGED (attn q/k/v/o + MLP gate/up/down = 7 modules)
#   - batch/grad_accum: 1 / 8 UNCHANGED (effective batch 8, matches r4)
#   - seq/lr/warmup/steps: 1024 / 5e-6 / 500 / 10000 UNCHANGED
#   - eval_every / save_every: 500 / 2000 UNCHANGED
#   - ckpt_dir:     /workspace/ckpt_alm_32b_r1  (fresh, never reused)
#   - r2_prefix:    r2:anima-models/alm32b/r1/
#   - model_tag:    alm32b   round: 1
#
# Trigger condition (enforced by preflight below):
#   - /workspace/READY_FOR_32B marker MUST exist (created by monitor_alm_r4
#     daemon when 14B r4 best eval_loss drops below 0.02).
#   - Without the marker this script refuses to start, because launching
#     32B while 14B r4 is still training would put both runs in contention
#     on the same H100.
#
# Run on RunPod H100 80GB (87.120.211.206:18709):
#   1. Wait for /workspace/READY_FOR_32B to appear.
#   2. scp this script + train_alm_32b_r1.hexa to /workspace/
#      (train_alm_14b.py is already on the pod from r4).
#   3. bash launch_alm_32b_r1.sh
#
# Expected steady-state:
#   - GPU memory:   ~77 GB / 80 GB (~3 GB headroom)
#   - Throughput:   ~8-9 step/min  (vs 14B r4 @ 18.5 step/min)
#   - ETA:          ~19-21 h for 10000 steps
#
set -euo pipefail

echo "============================================"
echo "  ALM 32B r1 — LoRA r=32 alpha=64, attn+MLP"
echo "============================================"

# ── Preflight: trigger marker ──
MARKER="/workspace/READY_FOR_32B"
if [[ ! -f "$MARKER" ]]; then
    echo "[preflight] ✗ $MARKER missing — 14B r4 has not yet cleared eval<0.02"
    echo "[preflight]   Refusing to launch: would contend with running r4 on the same H100."
    echo "[preflight]   The monitor_alm_r4 daemon creates this marker automatically."
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
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

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

# ── Launch ──
# Reuses train_alm_14b.py (same fwd/bwd loop — only hyperparameters differ).
# When hexa-lang ships native cuBLAS bindings, train_alm_32b_r1.hexa will
# absorb this launch step and the Python trainer will be archived.
python3 /workspace/train_alm_14b.py \
    --base Qwen/Qwen2.5-32B-Instruct \
    --corpus "$CORPUS" \
    --steps 10000 \
    --lr 5e-6 \
    --batch 1 \
    --grad-accum 8 \
    --seq 1024 \
    --warmup 500 \
    --lora-r 32 \
    --lora-alpha 64 \
    --lora-dropout 0.05 \
    --target-modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj \
    --ckpt-dir "$CKPT_DIR" \
    --save-every 2000 \
    --eval-every 500 \
    --model-tag alm32b \
    --round 1 \
    2>&1 | tee "$CKPT_DIR/train_r1.log"

echo "[done] 32B r1 training complete — check $CKPT_DIR"
echo "[next] python3 /workspace/eval_alm_14b.py --ckpt $CKPT_DIR/step_10000"
