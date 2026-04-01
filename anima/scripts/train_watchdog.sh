#!/usr/bin/env bash
# train_watchdog.sh — Watchdog for H100 training process
#
# Checks every 60s if the training process (train_v15.py) is alive.
# If dead, auto-resumes from latest checkpoint.
# Designed to survive tmux death via crontab.
#
# Usage:
#   bash train_watchdog.sh --install             # Install to crontab (runs every minute)
#   bash train_watchdog.sh --uninstall           # Remove from crontab
#   bash train_watchdog.sh --check               # Manual one-shot check
#   bash train_watchdog.sh --status              # Show current state
#
# Environment (set these or use defaults):
#   TRAIN_SCRIPT    — training script path (default: /workspace/anima/anima/training/train_v15.py)
#   TRAIN_ARGS      — arguments (default: --data /workspace/anima/anima/data/corpus_v10_ko.txt --scale 100m)
#   CKPT_DIR        — checkpoint directory (default: /workspace/anima/checkpoints/v15_1b)
#   PYTHON          — python path (default: /opt/conda/bin/python3)
#   WATCHDOG_LOG    — log file (default: /workspace/watchdog.log)
#   ALERT_FILE      — alert file for consecutive failures (default: /workspace/watchdog_alert.txt)

set -euo pipefail

# ── Defaults ──
PYTHON="${PYTHON:-/opt/conda/bin/python3}"
TRAIN_SCRIPT="${TRAIN_SCRIPT:-/workspace/anima/anima/training/train_v15.py}"
TRAIN_ARGS="${TRAIN_ARGS:---data /workspace/anima/anima/data/corpus_v10_ko.txt --scale 100m}"
CKPT_DIR="${CKPT_DIR:-/workspace/anima/checkpoints/v15_1b}"
WATCHDOG_LOG="${WATCHDOG_LOG:-/workspace/watchdog.log}"
ALERT_FILE="${ALERT_FILE:-/workspace/watchdog_alert.txt}"
FAIL_COUNT_FILE="/tmp/watchdog_fail_count"
MAX_CONSECUTIVE_FAILS=5

# ── Logging ──
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [watchdog] $1"
    echo "$msg" >> "$WATCHDOG_LOG"
    echo "$msg"
}

# ── Find latest checkpoint ──
find_latest_checkpoint() {
    local latest=""
    local latest_step=-1

    if [ ! -d "$CKPT_DIR" ]; then
        echo ""
        return
    fi

    # Search all subdirs for step_*.pt files
    while IFS= read -r -d '' f; do
        local base
        base=$(basename "$f")
        local step_num
        step_num=$(echo "$base" | sed -n 's/step_\([0-9]*\)\.pt/\1/p')
        if [ -n "$step_num" ] && [ "$step_num" -gt "$latest_step" ]; then
            latest_step=$step_num
            latest="$f"
        fi
    done < <(find "$CKPT_DIR" -name "step_*.pt" -print0 2>/dev/null)

    # Fallback: best.pt
    if [ -z "$latest" ]; then
        while IFS= read -r -d '' f; do
            latest="$f"
            break
        done < <(find "$CKPT_DIR" -name "best.pt" -print0 2>/dev/null)
    fi

    # Fallback: final.pt
    if [ -z "$latest" ]; then
        while IFS= read -r -d '' f; do
            latest="$f"
            break
        done < <(find "$CKPT_DIR" -name "final.pt" -print0 2>/dev/null)
    fi

    echo "$latest"
}

# ── Check if training is running ──
is_training_alive() {
    pgrep -f "train_v15.py" > /dev/null 2>&1
}

# ── GPU check ──
check_gpu() {
    if ! command -v nvidia-smi &> /dev/null; then
        log "WARNING: nvidia-smi not found"
        return 1
    fi
    local gpu_mem
    gpu_mem=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1)
    if [ -z "$gpu_mem" ]; then
        log "WARNING: Could not query GPU memory"
        return 1
    fi
    # Need at least 10GB free (10240 MB)
    if [ "$gpu_mem" -lt 10240 ]; then
        log "WARNING: GPU memory low (${gpu_mem}MB free). Waiting for cleanup."
        return 1
    fi
    return 0
}

# ── Restart training ──
restart_training() {
    local ckpt
    ckpt=$(find_latest_checkpoint)

    local resume_arg=""
    if [ -n "$ckpt" ]; then
        resume_arg="--resume $ckpt"
        log "Resuming from checkpoint: $ckpt"
    else
        log "No checkpoint found. Starting from scratch."
    fi

    # Check GPU before starting
    if ! check_gpu; then
        log "GPU not ready. Will retry next cycle."
        return 1
    fi

    # Kill any zombie training processes
    pkill -f "train_v15.py" 2>/dev/null || true
    sleep 2

    # Start in a new tmux session (survives SSH disconnect)
    local tmux_session="train_v15"
    tmux kill-session -t "$tmux_session" 2>/dev/null || true

    local cmd="PYTHONUNBUFFERED=1 $PYTHON -u $TRAIN_SCRIPT $TRAIN_ARGS $resume_arg 2>&1 | tee -a /workspace/train_v15.log"
    tmux new-session -d -s "$tmux_session" "$cmd"

    log "Training restarted in tmux session '$tmux_session'"
    log "  Command: $PYTHON $TRAIN_SCRIPT $TRAIN_ARGS $resume_arg"

    # Reset fail counter on successful restart
    echo "0" > "$FAIL_COUNT_FILE"
    return 0
}

# ── Track consecutive failures ──
increment_fail_count() {
    local count=0
    if [ -f "$FAIL_COUNT_FILE" ]; then
        count=$(cat "$FAIL_COUNT_FILE" 2>/dev/null || echo "0")
    fi
    count=$((count + 1))
    echo "$count" > "$FAIL_COUNT_FILE"

    if [ "$count" -ge "$MAX_CONSECUTIVE_FAILS" ]; then
        local alert_msg="ALERT: Training has failed to restart $count consecutive times. Manual intervention required."
        log "$alert_msg"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $alert_msg" >> "$ALERT_FILE"
        # Could add telegram/webhook notification here
        return 1
    fi
    return 0
}

# ── Actions ──
do_check() {
    if is_training_alive; then
        log "Training is ALIVE (PID: $(pgrep -f train_v15.py | head -1))"
        # Reset fail counter
        echo "0" > "$FAIL_COUNT_FILE" 2>/dev/null || true
    else
        log "Training is DEAD. Attempting restart..."
        if increment_fail_count; then
            restart_training
        else
            log "Too many consecutive failures. Stopping watchdog attempts."
        fi
    fi
}

do_status() {
    echo "=== Train Watchdog Status ==="
    echo ""
    if is_training_alive; then
        echo "  Training: ALIVE (PID: $(pgrep -f train_v15.py | head -1))"
    else
        echo "  Training: DEAD"
    fi
    echo ""

    local ckpt
    ckpt=$(find_latest_checkpoint)
    if [ -n "$ckpt" ]; then
        echo "  Latest checkpoint: $ckpt"
        echo "  Checkpoint time:   $(stat -c '%Y' "$ckpt" 2>/dev/null | xargs -I{} date -d @{} 2>/dev/null || stat -f '%Sm' "$ckpt" 2>/dev/null || echo 'unknown')"
    else
        echo "  Latest checkpoint: (none found)"
    fi
    echo ""

    local fail_count=0
    if [ -f "$FAIL_COUNT_FILE" ]; then
        fail_count=$(cat "$FAIL_COUNT_FILE" 2>/dev/null || echo "0")
    fi
    echo "  Consecutive failures: $fail_count / $MAX_CONSECUTIVE_FAILS"
    echo ""

    if command -v nvidia-smi &> /dev/null; then
        echo "  GPU:"
        nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu --format=csv,noheader 2>/dev/null | while read -r line; do
            echo "    $line"
        done
    fi
    echo ""

    # Crontab status
    if crontab -l 2>/dev/null | grep -q "train_watchdog.sh"; then
        echo "  Crontab: INSTALLED"
    else
        echo "  Crontab: NOT INSTALLED (run --install)"
    fi

    echo ""
    echo "  Log: $WATCHDOG_LOG"
    if [ -f "$WATCHDOG_LOG" ]; then
        echo "  Last 5 log entries:"
        tail -5 "$WATCHDOG_LOG" | while read -r line; do
            echo "    $line"
        done
    fi
}

do_install() {
    local script_path
    script_path="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

    # Build crontab entry with environment
    local cron_line="* * * * * PYTHON=$PYTHON TRAIN_SCRIPT=$TRAIN_SCRIPT TRAIN_ARGS=\"$TRAIN_ARGS\" CKPT_DIR=$CKPT_DIR WATCHDOG_LOG=$WATCHDOG_LOG bash $script_path --check >> $WATCHDOG_LOG 2>&1"

    # Add to crontab (preserving existing entries)
    (crontab -l 2>/dev/null | grep -v "train_watchdog.sh"; echo "$cron_line") | crontab -

    echo "Watchdog installed to crontab (runs every minute)."
    echo "  Script: $script_path"
    echo "  Log:    $WATCHDOG_LOG"
    echo ""
    echo "Current crontab:"
    crontab -l 2>/dev/null | grep "train_watchdog" || echo "  (none)"
    log "Watchdog crontab installed"
}

do_uninstall() {
    crontab -l 2>/dev/null | grep -v "train_watchdog.sh" | crontab -
    echo "Watchdog removed from crontab."
    log "Watchdog crontab removed"
}

# ── Main ──
case "${1:-}" in
    --install)   do_install ;;
    --uninstall) do_uninstall ;;
    --check)     do_check ;;
    --status)    do_status ;;
    *)
        echo "Usage: $0 {--install|--uninstall|--check|--status}"
        echo ""
        echo "  --install    Install to crontab (checks every minute)"
        echo "  --uninstall  Remove from crontab"
        echo "  --check      Manual one-shot check + restart if dead"
        echo "  --status     Show training status, checkpoint, GPU"
        echo ""
        echo "Environment variables:"
        echo "  PYTHON=$PYTHON"
        echo "  TRAIN_SCRIPT=$TRAIN_SCRIPT"
        echo "  TRAIN_ARGS=\"$TRAIN_ARGS\""
        echo "  CKPT_DIR=$CKPT_DIR"
        echo "  WATCHDOG_LOG=$WATCHDOG_LOG"
        exit 1
        ;;
esac
