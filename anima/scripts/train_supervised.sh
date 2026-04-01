#!/usr/bin/env bash
# train_supervised.sh — Immortal training wrapper (survives tmux death)
#
# Wraps any training script in a while-true loop with auto-resume.
# When the training process dies (OOM, crash, tmux kill), it:
#   1. Finds the latest checkpoint
#   2. Checks GPU VRAM availability
#   3. Waits 30s cooldown
#   4. Restarts with --resume <latest_checkpoint>
#   5. After 5 consecutive failures, writes alert and stops
#
# Usage:
#   bash train_supervised.sh train_v15.py --data corpus.txt --scale 100m
#   bash train_supervised.sh train_v15.py --data corpus.txt --scale 1b --steps 300000
#
# The script passes ALL arguments after the training script name directly to python.
# It automatically adds --resume <latest_checkpoint> on restarts.
#
# Best practice: run inside tmux, PLUS install watchdog crontab:
#   tmux new-session -d -s train "bash train_supervised.sh train_v15.py --data corpus.txt --scale 100m"
#   bash train_watchdog.sh --install   # crontab backup if tmux dies

set -uo pipefail

# ── Configuration ──
PYTHON="${PYTHON:-/opt/conda/bin/python3}"
WORKSPACE="${WORKSPACE:-/workspace/anima}"
TRAINING_DIR="$WORKSPACE/anima/training"
CKPT_BASE="${CKPT_BASE:-$WORKSPACE/checkpoints}"
LOG_DIR="$WORKSPACE"
MAX_CONSECUTIVE_FAILS=5
COOLDOWN=30
ALERT_FILE="$WORKSPACE/training_alert.txt"

# ── Parse arguments ──
if [ $# -lt 1 ]; then
    echo "Usage: $0 <train_script.py> [training args...]"
    echo ""
    echo "Examples:"
    echo "  $0 train_v15.py --data data/corpus_v10_ko.txt --scale 100m"
    echo "  $0 train_v15.py --data data/corpus_v10_ko.txt --scale 1b --steps 300000"
    echo ""
    echo "Environment:"
    echo "  PYTHON=$PYTHON"
    echo "  WORKSPACE=$WORKSPACE"
    echo "  CKPT_BASE=$CKPT_BASE"
    exit 1
fi

TRAIN_SCRIPT="$1"
shift
TRAIN_ARGS=("$@")

# Resolve training script path
if [ ! -f "$TRAIN_SCRIPT" ]; then
    if [ -f "$TRAINING_DIR/$TRAIN_SCRIPT" ]; then
        TRAIN_SCRIPT="$TRAINING_DIR/$TRAIN_SCRIPT"
    else
        echo "ERROR: Training script not found: $TRAIN_SCRIPT"
        echo "  Tried: ./$TRAIN_SCRIPT and $TRAINING_DIR/$TRAIN_SCRIPT"
        exit 1
    fi
fi

# ── Determine checkpoint directory from args ──
CKPT_DIR="$CKPT_BASE/v15_1b"  # Default
for i in "${!TRAIN_ARGS[@]}"; do
    if [ "${TRAIN_ARGS[$i]}" = "--checkpoint" ] && [ $((i+1)) -lt ${#TRAIN_ARGS[@]} ]; then
        CKPT_DIR="${TRAIN_ARGS[$((i+1))]}"
    fi
done

# ── Logging ──
LOGFILE="$LOG_DIR/train_supervised.log"
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [supervised] $1"
    echo "$msg" | tee -a "$LOGFILE"
}

# ── GPU VRAM check ──
wait_for_gpu() {
    local attempts=0
    local max_attempts=30  # 30 * 10s = 5 minutes max wait

    while [ $attempts -lt $max_attempts ]; do
        if ! command -v nvidia-smi &> /dev/null; then
            log "WARNING: nvidia-smi not available, skipping GPU check"
            return 0
        fi

        local gpu_info
        gpu_info=$(nvidia-smi --query-gpu=memory.free,memory.total,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -z "$gpu_info" ]; then
            log "WARNING: Could not query GPU. Proceeding anyway."
            return 0
        fi

        local free_mb
        free_mb=$(echo "$gpu_info" | cut -d',' -f1 | tr -d ' ')
        local total_mb
        total_mb=$(echo "$gpu_info" | cut -d',' -f2 | tr -d ' ')
        local util
        util=$(echo "$gpu_info" | cut -d',' -f3 | tr -d ' ')

        # H100 80GB: need at least 60GB free for 1B training
        if [ "$free_mb" -gt 10240 ]; then
            log "GPU ready: ${free_mb}MB free / ${total_mb}MB total, ${util}% util"
            return 0
        fi

        attempts=$((attempts + 1))
        log "GPU busy: ${free_mb}MB free (need >10GB). Waiting... ($attempts/$max_attempts)"

        # Kill any zombie python processes hogging GPU
        if [ $attempts -eq 5 ]; then
            log "Checking for zombie processes..."
            local zombies
            zombies=$(ps aux | grep "python.*train" | grep -v grep | grep -v "$$" | awk '{print $2}')
            if [ -n "$zombies" ]; then
                log "Found zombie training processes: $zombies"
                echo "$zombies" | xargs kill -9 2>/dev/null || true
                sleep 5
            fi
        fi

        sleep 10
    done

    log "WARNING: GPU did not free up after 5 minutes. Attempting start anyway."
    return 0
}

# ── Find latest checkpoint ──
find_latest_checkpoint() {
    local latest=""
    local latest_step=-1

    if [ ! -d "$CKPT_DIR" ]; then
        echo ""
        return
    fi

    # Search step_*.pt in all subdirs
    while IFS= read -r f; do
        local base
        base=$(basename "$f")
        local step_num
        step_num=$(echo "$base" | sed -n 's/step_\([0-9]*\)\.pt/\1/p')
        if [ -n "$step_num" ] && [ "$step_num" -gt "$latest_step" ]; then
            latest_step=$step_num
            latest="$f"
        fi
    done < <(find "$CKPT_DIR" -name "step_*.pt" 2>/dev/null)

    # Fallback: best.pt
    if [ -z "$latest" ]; then
        latest=$(find "$CKPT_DIR" -name "best.pt" 2>/dev/null | head -1)
    fi

    # Fallback: final.pt
    if [ -z "$latest" ]; then
        latest=$(find "$CKPT_DIR" -name "final.pt" 2>/dev/null | head -1)
    fi

    echo "$latest"
}

# ── Check if --resume already in args ──
has_resume_arg() {
    for arg in "${TRAIN_ARGS[@]}"; do
        if [ "$arg" = "--resume" ]; then
            return 0
        fi
    done
    return 1
}

# ── Main loop ──
echo "═══════════════════════════════════════════════════"
echo "  Train Supervised — Immortal Training Wrapper"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Script:     $TRAIN_SCRIPT"
echo "  Args:       ${TRAIN_ARGS[*]}"
echo "  Python:     $PYTHON"
echo "  Ckpt dir:   $CKPT_DIR"
echo "  Log:        $LOGFILE"
echo "  Max fails:  $MAX_CONSECUTIVE_FAILS"
echo "  Cooldown:   ${COOLDOWN}s"
echo ""
log "Starting supervised training"

consecutive_fails=0
total_restarts=0
first_run=true

while true; do
    # ── Build command ──
    cmd_args=("${TRAIN_ARGS[@]}")

    # On restart (not first run), add --resume if not already specified
    if [ "$first_run" = false ] && ! has_resume_arg; then
        local_ckpt=$(find_latest_checkpoint)
        if [ -n "$local_ckpt" ]; then
            cmd_args+=("--resume" "$local_ckpt")
            log "Auto-resume from: $local_ckpt"
        else
            log "No checkpoint found for resume. Starting fresh."
        fi
    fi

    # ── Pre-flight checks ──
    wait_for_gpu

    # ── Launch ──
    log "Launching training (run #$((total_restarts + 1)))..."
    log "  $PYTHON -u $TRAIN_SCRIPT ${cmd_args[*]}"

    start_time=$(date +%s)

    # Run with unbuffered output
    set +e
    PYTHONUNBUFFERED=1 "$PYTHON" -u "$TRAIN_SCRIPT" "${cmd_args[@]}" 2>&1 | tee -a "$LOG_DIR/train_output.log"
    exit_code=${PIPESTATUS[0]}
    set -e

    end_time=$(date +%s)
    duration=$((end_time - start_time))
    duration_human=$(printf '%dh %dm %ds' $((duration/3600)) $((duration%3600/60)) $((duration%60)))

    first_run=false

    # ── Analyze exit ──
    case $exit_code in
        0)
            log "Training completed successfully (duration: $duration_human)"
            log "Total restarts: $total_restarts"
            exit 0
            ;;
        130|143)
            # SIGINT (Ctrl+C) or SIGTERM — clean stop
            log "Training stopped by signal (code $exit_code, duration: $duration_human)"
            exit 0
            ;;
        137)
            # SIGKILL — usually OOM
            log "Training KILLED (OOM? code 137, duration: $duration_human)"
            ;;
        *)
            log "Training CRASHED (code $exit_code, duration: $duration_human)"
            ;;
    esac

    # ── Failure tracking ──
    # If it ran for more than 5 minutes, reset fail counter (it was working)
    if [ $duration -gt 300 ]; then
        consecutive_fails=0
        log "Process ran for $duration_human — resetting failure counter"
    else
        consecutive_fails=$((consecutive_fails + 1))
        log "Process died quickly ($duration_human) — consecutive fails: $consecutive_fails/$MAX_CONSECUTIVE_FAILS"
    fi

    total_restarts=$((total_restarts + 1))

    # ── Too many failures? ──
    if [ $consecutive_fails -ge $MAX_CONSECUTIVE_FAILS ]; then
        local alert_msg="FATAL: $MAX_CONSECUTIVE_FAILS consecutive quick failures. Manual intervention required."
        log "$alert_msg"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $alert_msg" >> "$ALERT_FILE"
        echo "  Total restarts: $total_restarts" >> "$ALERT_FILE"
        echo "  Last exit code: $exit_code" >> "$ALERT_FILE"
        exit 1
    fi

    # ── Cooldown ──
    log "Waiting ${COOLDOWN}s before restart..."
    sleep $COOLDOWN
done
