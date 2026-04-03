#!/bin/bash
# relaunch_v3_274M.sh — Resume v3_274M from crash at step 170K
# Cause: NFS I/O hang during checkpoint save (TSH-001)
# Fix: local-first checkpoint save + save_every=10000
#
# Same data + same params = resume allowed (not a restart)

set -euo pipefail

CKPT_DIR="checkpoints/v3_274M"
CORPUS="data/corpus_v10.txt"

# ── Pre-flight checks ──
echo "=== v3_274M Relaunch Pre-flight ==="

# 1. Check disk space
echo -n "Disk space: "
df -h . | tail -1 | awk '{print $4 " available"}'

# 2. Find latest valid checkpoint
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

# 3. Verify corpus exists
if [ ! -f "$CORPUS" ]; then
    echo "ERROR: Corpus not found at $CORPUS"
    exit 1
fi
echo "Corpus: $CORPUS ($(du -h "$CORPUS" | cut -f1))"

# 4. Check for zombie processes
ZOMBIES=$(ps aux | grep "train.py.*v3" | grep -v grep | wc -l | tr -d ' ')
if [ "$ZOMBIES" -gt 0 ]; then
    echo "WARNING: $ZOMBIES existing train.py processes found!"
    ps aux | grep "train.py.*v3" | grep -v grep
    echo "Kill them first: pkill -f 'train.py.*v3'"
    exit 1
fi

echo "=== All checks passed ==="
echo ""

# ── Launch ──
# On H100 RunPod: use tmux for SSH disconnect resilience
# Local: direct execution with nohup

CMD="python3 anima/training/train.py \
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
    echo "Attached to tmux. Monitor: tmux attach -t v3_train"
else
    # Local or non-RunPod
    echo "Launching directly..."
    PYTHONUNBUFFERED=1 $CMD 2>&1 | tee "logs/v3_relaunch_$(date +%Y%m%d_%H%M).log"
fi
