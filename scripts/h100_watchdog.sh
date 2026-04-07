#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# h100_watchdog.sh — Restart stale H100 training sessions
#
# Cron: */5 * * * * bash ~/anima/scripts/h100_watchdog.sh >> ~/anima/scripts/watchdog.log 2>&1
#
# Checks heartbeat files written by train_clm.py every 100 steps.
# If heartbeat is older than 600s (10 min), training is assumed stale.
# Kills the tmux session and restarts.
# ═══════════════════════════════════════════════════════════════════════

set -uo pipefail

ANIMA_DIR="${ANIMA_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
STALE_THRESHOLD=600  # seconds

check_session() {
    local session_name="$1"
    local heartbeat_path="$2"
    local restart_cmd="$3"

    if [ ! -f "$heartbeat_path" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$session_name] No heartbeat file at $heartbeat_path"
        return
    fi

    # Get file age (macOS: stat -f %m, Linux: stat -c %Y)
    local mtime
    mtime=$(stat -c %Y "$heartbeat_path" 2>/dev/null || stat -f %m "$heartbeat_path" 2>/dev/null)
    if [ -z "$mtime" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$session_name] Cannot stat heartbeat"
        return
    fi

    local now
    now=$(date +%s)
    local age=$((now - mtime))

    if [ "$age" -gt "$STALE_THRESHOLD" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$session_name] STALE (${age}s > ${STALE_THRESHOLD}s)"

        # Read last heartbeat content for logging
        cat "$heartbeat_path" 2>/dev/null

        # Kill existing tmux session
        if tmux has-session -t "$session_name" 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$session_name] Killing tmux session..."
            tmux kill-session -t "$session_name"
            sleep 2
        fi

        # Restart
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$session_name] Restarting..."
        eval "$restart_cmd"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$session_name] Restarted."
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$session_name] OK (age=${age}s)"
    fi
}

# ── Check v3_train session ──
check_session "v3_train" \
    "$ANIMA_DIR/checkpoints/v3_274M/heartbeat.txt" \
    "tmux new-session -d -s v3_train 'cd $ANIMA_DIR && PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python3 -u anima/training/train_clm.py --data anima/data/corpus_v9.txt --decoder v3 --federated --atoms 8 --cells-per-atom 8 --steps 200000 --checkpoint checkpoints/v3_274M/ --phase-optimal --batch-size 64 --block-size 512 --lr 3e-4 --resume checkpoints/v3_274M/best.pt 2>&1 | tee -a checkpoints/v3_274M/train.log'"

# ── Check v14_128c session ──
check_session "v14_128c" \
    "$ANIMA_DIR/checkpoints/v14_128c/heartbeat.txt" \
    "tmux new-session -d -s v14_128c 'cd $ANIMA_DIR && PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python3 -u anima/training/train_clm.py --data anima/data/corpus_v9.txt --federated --atoms 16 --cells-per-atom 8 --steps 100000 --checkpoint checkpoints/v14_128c/ --phase-optimal --batch-size 32 --block-size 256 --lr 3e-4 --resume checkpoints/v14_128c/best.pt 2>&1 | tee -a checkpoints/v14_128c/train.log'"
