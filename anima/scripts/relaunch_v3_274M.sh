#!/bin/bash
# relaunch_v3_274M.sh — Resume v3_274M from crash at step 170K
# Cause: NFS I/O hang during checkpoint save (TSH-001)
# Fix: local-first checkpoint save + save_every=10000
#
# Same data + same params = resume allowed (not a restart)

set -euo pipefail

# ── Detect environment and set paths ──
# RunPod: /workspace (h100_sync flattens anima/src -> /workspace/, training -> /workspace/training/)
# Local:  repo root (~/Dev/anima), structure preserved
if [ -n "${RUNPOD_POD_ID:-}" ] || [ -d /workspace/training ]; then
    # RunPod layout
    WORK_DIR="/workspace"
    CKPT_DIR="/workspace/checkpoints/v3_274M"
    CORPUS="/workspace/data/corpus_v10.txt"
    TRAIN_SCRIPT="training/train.py"
else
    # Local layout (repo root)
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    WORK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
    CKPT_DIR="$WORK_DIR/anima/checkpoints/v3_274M"
    CORPUS="$WORK_DIR/anima/data/corpus_v10.txt"
    TRAIN_SCRIPT="anima/training/train.py"
fi

cd "$WORK_DIR"

# ── Python path (RunPod: /opt/conda/bin/python3) ──
if [ -x /opt/conda/bin/python3 ]; then
    PYTHON=/opt/conda/bin/python3
else
    PYTHON=python3
fi

# ── Pre-flight checks ──
echo "=== v3_274M Relaunch Pre-flight ==="

# 1. Check disk space (>5GB required)
echo -n "Disk space: "
df -h . | tail -1 | awk '{print $4 " available"}'
AVAIL_KB=$(df . | tail -1 | awk '{print $4}')
if [ "$AVAIL_KB" -lt 5000000 ] 2>/dev/null; then
    echo "WARNING: <5GB free — clean old checkpoints first"
fi

# 2. Clean stale /tmp checkpoint fragments from previous crash
STALE=$(ls /tmp/anima_ckpt_*.pt* 2>/dev/null | wc -l | tr -d ' ')
if [ "$STALE" -gt 0 ]; then
    echo "Cleaning $STALE stale /tmp checkpoint fragments..."
    rm -f /tmp/anima_ckpt_*.pt*
fi

# 3. Find latest valid checkpoint
LATEST=""
for f in "$CKPT_DIR"/step_*.pt; do
    [ -f "$f" ] || continue
    # Verify file is not truncated (>10MB)
    size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
    if [ "$size" -gt 10000000 ]; then
        LATEST="$f"
    fi
done

if [ -z "$LATEST" ]; then
    # Fallback to best.pt
    if [ -f "$CKPT_DIR/best.pt" ]; then
        LATEST="$CKPT_DIR/best.pt"
        echo "Using best.pt as resume point"
    else
        echo "ERROR: No valid checkpoint found in $CKPT_DIR"
        exit 1
    fi
fi

echo "Resume from: $LATEST"

# 4. Verify corpus exists
if [ ! -f "$CORPUS" ]; then
    echo "ERROR: Corpus not found at $CORPUS"
    exit 1
fi
echo "Corpus: $CORPUS ($(du -h "$CORPUS" | cut -f1))"

# 5. Check for zombie processes
ZOMBIES=$(ps aux | grep "train.py.*v3" | grep -v grep | wc -l | tr -d ' ')
if [ "$ZOMBIES" -gt 0 ]; then
    echo "WARNING: $ZOMBIES existing train.py processes found!"
    ps aux | grep "train.py.*v3" | grep -v grep
    echo "Kill them first: pkill -f 'train.py.*v3'"
    exit 1
fi

# 6. Verify checkpoint loadable
echo -n "Checkpoint integrity: "
$PYTHON -c "import torch; c=torch.load('$LATEST', map_location='cpu', weights_only=False); print(f'step={c[\"step\"]}, CE={c[\"ce\"]:.4f}, Phi={c[\"phi\"]:.4f}')" || {
    echo "ERROR: Checkpoint corrupted — cannot load $LATEST"
    exit 1
}

echo "=== All checks passed ==="
echo ""

# ── Launch ──
mkdir -p logs

CMD="$PYTHON $TRAIN_SCRIPT \
    --decoder v3 \
    --federated \
    --atoms 8 \
    --cells-per-atom 8 \
    --data $CORPUS \
    --steps 200000 \
    --save-every 10000 \
    --checkpoint $CKPT_DIR \
    --resume $LATEST"

echo "Command: $CMD"
echo ""

# Detect environment
if command -v tmux &>/dev/null && [ -n "${RUNPOD_POD_ID:-}" ]; then
    # RunPod H100: tmux session
    echo "RunPod detected — launching in tmux session 'v3_train'"
    tmux new-session -d -s v3_train "PYTHONUNBUFFERED=1 $CMD 2>&1 | tee logs/v3_relaunch_$(date +%Y%m%d_%H%M).log"
    echo "Monitor: tmux attach -t v3_train"
else
    # Local or non-RunPod
    echo "Launching directly..."
    PYTHONUNBUFFERED=1 $CMD 2>&1 | tee "logs/v3_relaunch_$(date +%Y%m%d_%H%M).log"
fi
