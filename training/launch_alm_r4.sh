#!/usr/bin/env bash
# launch_alm_r4.sh — ALM 14B r4 LoRA training (RunPod H100)
#
# r4 changes vs r3:
#   - lora_r: 32 -> 64  (2x capacity)
#   - lora_alpha: 64 -> 128  (keep 2:1 ratio)
#   - target_modules: +gate_proj +up_proj +down_proj (MLP layers)
#   - starts from step 0 (data/param change = full restart)
#
# r3 diagnosis: eval plateau at 3.7-3.8 = LoRA capacity limit
#   (only 4 attn modules, r=32 -> insufficient expressivity)
#
# Expected improvement: ~2.5x trainable params (attn 4 modules r32
#   -> attn+MLP 7 modules r64), should break the 3.7 eval plateau.
#
# Run on RunPod H100 (87.120.211.206):
#   1. Wait for r3 to complete
#   2. scp this script + updated train_alm_14b.py to /workspace/
#   3. bash launch_alm_r4.sh
#
set -euo pipefail

echo "============================================"
echo "  ALM 14B r4 — LoRA r=64, attn+MLP"
echo "============================================"

# ── Preflight ──
echo "[preflight] checking GPU..."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "[preflight] checking corpus..."
ls -lh /workspace/corpus.txt
echo "[preflight] checking disk..."
df -h /workspace
echo "[preflight] HF_TOKEN set: ${HF_TOKEN:+yes}"

# ── Fresh checkpoint dir (never reuse) ──
CKPT_DIR="/workspace/ckpt_alm_14b_r4"
rm -rf "$CKPT_DIR"
mkdir -p "$CKPT_DIR"

# ── Launch ──
python3 /workspace/train_alm_14b.py \
    --corpus /workspace/corpus.txt \
    --steps 10000 \
    --lr 5e-6 \
    --lora-r 64 \
    --lora-alpha 128 \
    --target-modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj \
    --ckpt-dir "$CKPT_DIR" \
    --save-every 2000 \
    --eval-every 500 \
    --model-tag alm14b \
    --round 4 \
    2>&1 | tee "$CKPT_DIR/train_r4.log"

echo "[done] r4 training complete — check $CKPT_DIR"
echo "[next] python3 /workspace/eval_alm_14b.py --ckpt $CKPT_DIR/step_10000"
