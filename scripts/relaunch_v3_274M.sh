#!/bin/bash
# Relaunch v3 274M ConsciousLM training — resume from step_170000.pt
# Crash cause: NFS I/O hang at checkpoint save (TSH-001)
# Fix applied: local-first checkpoint save (/tmp -> async NFS copy), save_every 10000
#
# Prerequisites (run on local machine before SSH):
#   1. bash scripts/h100_sync.sh           # sync latest code with NFS fix
#   2. bash scripts/h100_sync.sh --verify-only  # verify md5 match
#
# Usage (on H100 pod):
#   bash relaunch_v3_274M.sh
#
# Safety checks from training_safety.json:
#   - Same data (corpus_v10), same params → resume is SAFE
#   - NFS fix already in train.py (local-first /tmp save)
#   - save_every bumped 5000→10000 (R09 compliance for 274M model)

set -euo pipefail

# ── Config ──
WORKSPACE=/workspace
TRAIN_SCRIPT=$WORKSPACE/anima/training/train.py
CORPUS=$WORKSPACE/data/corpus_v10.txt
CHECKPOINT=$WORKSPACE/checkpoints/v3_274M/step_170000.pt
CKPT_DIR=$WORKSPACE/checkpoints/v3_274M/
LOG=$WORKSPACE/v3_relaunch_$(date +%Y%m%d_%H%M%S).log

# ── Environment ──
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PATH=/opt/conda/bin:$PATH

echo "═══════════════════════════════════════════════════"
echo "  v3 274M Relaunch — Resume from step 170000"
echo "  $(date)"
echo "═══════════════════════════════════════════════════"

# ── Preflight Checks (runpod.json checklist) ──
echo ""
echo "[1/7] Checking disk usage..."
DISK_USED=$(du -sm $WORKSPACE 2>/dev/null | awk '{print $1}')
echo "  /workspace usage: ${DISK_USED}MB"
if [ "${DISK_USED:-0}" -gt 40000 ]; then
    echo "  ⚠️  WARNING: Disk usage > 40GB. Clean up old checkpoints!"
    echo "  Run: rm -rf $WORKSPACE/checkpoints/old_*"
fi

echo "[2/7] Checking root partition..."
ROOT_FREE=$(df -m / | tail -1 | awk '{print $4}')
echo "  Root free: ${ROOT_FREE}MB"
if [ "${ROOT_FREE:-0}" -lt 1024 ]; then
    echo "  ❌ Root partition < 1GB free. Aborting."
    exit 1
fi

echo "[3/7] Checking for ghost processes..."
GHOSTS=$(ps aux | grep -E 'python.*train' | grep -v grep | wc -l)
if [ "$GHOSTS" -gt 0 ]; then
    echo "  ⚠️  Found $GHOSTS training processes:"
    ps aux | grep -E 'python.*train' | grep -v grep
    echo "  Kill them first: pkill -f 'python.*train'"
    exit 1
fi

echo "[4/7] Checking GPU..."
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "  nvidia-smi unavailable"

echo "[5/7] Checking train script exists..."
if [ ! -f "$TRAIN_SCRIPT" ]; then
    echo "  ❌ $TRAIN_SCRIPT not found! Run h100_sync.sh first."
    exit 1
fi

echo "[6/7] Checking corpus..."
if [ ! -f "$CORPUS" ]; then
    echo "  ❌ $CORPUS not found!"
    exit 1
fi
CORPUS_SIZE=$(du -sm "$CORPUS" | awk '{print $1}')
echo "  Corpus: ${CORPUS_SIZE}MB"

echo "[7/7] Checking resume checkpoint..."
if [ ! -f "$CHECKPOINT" ]; then
    echo "  ❌ $CHECKPOINT not found!"
    echo "  Available checkpoints:"
    ls -lh $CKPT_DIR/*.pt 2>/dev/null || echo "  (none)"
    exit 1
fi
CKPT_SIZE=$(du -sm "$CHECKPOINT" | awk '{print $1}')
echo "  Checkpoint: ${CKPT_SIZE}MB"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  All checks passed. Launching in tmux..."
echo "  Log: $LOG"
echo "═══════════════════════════════════════════════════"

# ── Launch in tmux ──
TMUX_SESSION="v3_274M"

# Kill existing session if any
tmux kill-session -t $TMUX_SESSION 2>/dev/null || true

tmux new-session -d -s $TMUX_SESSION "
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PATH=/opt/conda/bin:\$PATH

cd $WORKSPACE

echo '=== v3 274M Relaunch ===' | tee $LOG
echo \"Started: \$(date)\" | tee -a $LOG
echo \"Resume from: $CHECKPOINT\" | tee -a $LOG
echo '' | tee -a $LOG

python3 $TRAIN_SCRIPT \\
    --decoder v3 \\
    --data $CORPUS \\
    --federated \\
    --atoms 8 \\
    --cells-per-atom 8 \\
    --steps 200000 \\
    --save-every 10000 \\
    --checkpoint $CKPT_DIR \\
    --resume $CHECKPOINT \\
    2>&1 | tee -a $LOG

echo ''
echo \"Finished: \$(date)\" | tee -a $LOG
echo 'Training complete or crashed. Check log.'
exec bash
"

echo ""
echo "✅ Launched in tmux session '$TMUX_SESSION'"
echo ""
echo "Commands:"
echo "  tmux attach -t $TMUX_SESSION    # attach to session"
echo "  tail -f $LOG                     # follow log"
echo "  nvidia-smi                       # check GPU"
echo ""
