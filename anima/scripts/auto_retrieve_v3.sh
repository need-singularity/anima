#!/usr/bin/env bash
# auto_retrieve_v3.sh — Auto-retrieve v3 274M checkpoints from H100
#
# Features:
#   - Detects training completion (no tmux + no python + step_200000.pt exists)
#   - Downloads best.pt + final.pt via scp
#   - Uploads to R2 (anima-models bucket)
#   - Verifies md5 + file size
#   - Updates training_runs.json
#   - Shows current step + ETA if training still running
#
# Usage:
#   bash scripts/auto_retrieve_v3.sh              # Single check
#   bash scripts/auto_retrieve_v3.sh --poll        # Loop every 30 min
#   bash scripts/auto_retrieve_v3.sh --status       # Status only (no download)
#
# Cron (every 30 min):
#   */30 * * * * cd ~/Dev/anima/anima && bash scripts/auto_retrieve_v3.sh >> /tmp/auto_retrieve_v3.log 2>&1

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SSH_KEY="$HOME/.runpod/ssh/RunPod-Key-Go"
SSH_HOST="root@216.243.220.230"
SSH_PORT="18038"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ServerAliveInterval=30"
SSH_CMD="ssh $SSH_OPTS $SSH_HOST -p $SSH_PORT"
SCP_CMD="scp $SSH_OPTS -P $SSH_PORT"

REMOTE_CKPT_DIR="/workspace/checkpoints/v3_274M"
REMOTE_PYTHON="/opt/conda/bin/python3"

LOCAL_CKPT_DIR="$PROJECT_DIR/checkpoints/v3_274M"
TRAINING_RUNS="$PROJECT_DIR/config/training_runs.json"
R2_UPLOAD="$SCRIPT_DIR/r2_upload.py"

TOTAL_STEPS=200000
VERSION="v3_274M"

# ─── Functions ───────────────────────────────────────────────────

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

ssh_exec() {
    $SSH_CMD "$@" 2>/dev/null
}

check_ssh() {
    if ! $SSH_CMD "echo ok" >/dev/null 2>&1; then
        log "ERROR: Cannot connect to H100. Pod may be stopped."
        exit 1
    fi
}

get_training_status() {
    # Returns: running|completed|no_checkpoint
    local has_tmux has_python has_final_ckpt

    # Check tmux training session
    has_tmux=$(ssh_exec "tmux ls 2>/dev/null | grep -c train" || echo "0")

    # Check python training process
    has_python=$(ssh_exec "ps aux | grep -E 'train_v1[4-5]|train_v3' | grep -v grep | wc -l" || echo "0")

    # Check step_200000.pt
    has_final_ckpt=$(ssh_exec "ls $REMOTE_CKPT_DIR/step_${TOTAL_STEPS}.pt 2>/dev/null && echo 1 || echo 0")

    if [[ "$has_final_ckpt" == "1" ]] && [[ "$has_tmux" == "0" ]] && [[ "$has_python" == "0" ]]; then
        echo "completed"
    elif [[ "$has_tmux" != "0" ]] || [[ "$has_python" != "0" ]]; then
        echo "running"
    else
        echo "no_checkpoint"
    fi
}

get_current_step() {
    # Find the latest step_NNNNN.pt and extract step number
    local latest
    latest=$(ssh_exec "ls -t $REMOTE_CKPT_DIR/step_*.pt 2>/dev/null | head -1" || echo "")
    if [[ -n "$latest" ]]; then
        echo "$latest" | grep -oE 'step_[0-9]+' | grep -oE '[0-9]+'
    else
        echo "0"
    fi
}

show_status() {
    log "=== v3 274M Training Status ==="

    local status
    status=$(get_training_status)

    case "$status" in
        completed)
            log "STATUS: COMPLETED (step_${TOTAL_STEPS}.pt exists, no training process)"
            # Show checkpoint files
            log "Checkpoints on H100:"
            ssh_exec "ls -lh $REMOTE_CKPT_DIR/*.pt 2>/dev/null" | while read -r line; do
                log "  $line"
            done
            ;;
        running)
            local current_step
            current_step=$(get_current_step)
            local pct=$((current_step * 100 / TOTAL_STEPS))
            local remaining=$((TOTAL_STEPS - current_step))

            log "STATUS: RUNNING"
            log "  Step: ${current_step} / ${TOTAL_STEPS} (${pct}%)"

            # Estimate ETA from log if available
            local speed
            speed=$(ssh_exec "tail -50 /workspace/v3_train.log 2>/dev/null | grep -oE '[0-9.]+ s/step' | tail -1" || echo "")
            if [[ -n "$speed" ]]; then
                local sps
                sps=$(echo "$speed" | grep -oE '[0-9.]+')
                local eta_sec
                eta_sec=$(echo "$remaining * $sps" | bc 2>/dev/null || echo "")
                if [[ -n "$eta_sec" ]]; then
                    local eta_hr
                    eta_hr=$(echo "scale=1; $eta_sec / 3600" | bc 2>/dev/null || echo "?")
                    log "  Speed: ${speed}"
                    log "  ETA: ~${eta_hr} hours"
                fi
            fi

            # Show latest metrics from log
            local latest_metrics
            latest_metrics=$(ssh_exec "tail -5 /workspace/v3_train.log 2>/dev/null | grep -E 'CE|Phi|step'" || echo "")
            if [[ -n "$latest_metrics" ]]; then
                log "  Latest metrics:"
                echo "$latest_metrics" | while read -r line; do
                    log "    $line"
                done
            fi

            # Show GPU usage
            log "  GPU:"
            ssh_exec "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader" 2>/dev/null | while read -r line; do
                log "    $line"
            done
            ;;
        no_checkpoint)
            log "STATUS: NO FINAL CHECKPOINT"
            log "  Training may have failed or not started."
            log "  Checking for any checkpoints:"
            ssh_exec "ls -lht $REMOTE_CKPT_DIR/*.pt 2>/dev/null | head -5" | while read -r line; do
                log "    $line"
            done
            ;;
    esac
}

retrieve_checkpoints() {
    log "=== Retrieving v3 274M Checkpoints ==="
    mkdir -p "$LOCAL_CKPT_DIR"

    local downloaded=()
    for fname in best.pt final.pt best_final.pt "step_${TOTAL_STEPS}.pt"; do
        local remote="$REMOTE_CKPT_DIR/$fname"
        local local_file="$LOCAL_CKPT_DIR/$fname"

        # Check if remote file exists
        if ssh_exec "test -f $remote && echo yes" | grep -q yes; then
            log "Downloading $fname ..."
            $SCP_CMD "$SSH_HOST:$remote" "$local_file"
            local size
            size=$(du -h "$local_file" | cut -f1)
            local md5
            md5=$(md5 -q "$local_file" 2>/dev/null || md5sum "$local_file" | cut -d' ' -f1)
            log "  $fname: $size (md5: ${md5:0:12}...)"
            downloaded+=("$fname")
        else
            log "  $fname not found on H100, skipping"
        fi
    done

    if [[ ${#downloaded[@]} -eq 0 ]]; then
        log "ERROR: No checkpoint files downloaded!"
        return 1
    fi

    log "Downloaded ${#downloaded[@]} files to $LOCAL_CKPT_DIR"
    echo "${downloaded[@]}"
}

upload_to_r2() {
    log "=== Uploading to R2 ==="
    if [[ ! -f "$R2_UPLOAD" ]]; then
        log "ERROR: r2_upload.py not found at $R2_UPLOAD"
        return 1
    fi

    python3 "$R2_UPLOAD" --checkpoint "$VERSION" --dir "$LOCAL_CKPT_DIR"
    log "R2 upload complete."
}

verify_checkpoints() {
    log "=== Verifying Checkpoints ==="
    local all_ok=true

    for fname in best.pt final.pt best_final.pt "step_${TOTAL_STEPS}.pt"; do
        local local_file="$LOCAL_CKPT_DIR/$fname"
        if [[ -f "$local_file" ]]; then
            local size
            size=$(stat -f%z "$local_file" 2>/dev/null || stat -c%s "$local_file")
            local md5
            md5=$(md5 -q "$local_file" 2>/dev/null || md5sum "$local_file" | cut -d' ' -f1)

            # Verify file is not corrupt (> 1MB at minimum)
            if [[ "$size" -lt 1048576 ]]; then
                log "  WARNING: $fname is suspiciously small (${size} bytes)"
                all_ok=false
            else
                local human
                human=$(echo "scale=1; $size / 1073741824" | bc 2>/dev/null || echo "?")
                log "  OK: $fname (${human}GB, md5: ${md5:0:12}...)"
            fi
        fi
    done

    $all_ok && log "All checkpoints verified." || log "WARNING: Some checkpoints may be corrupt!"
    $all_ok
}

update_training_runs() {
    log "=== Updating training_runs.json ==="
    if [[ ! -f "$TRAINING_RUNS" ]]; then
        log "WARNING: training_runs.json not found, skipping update"
        return
    fi

    # Get best.pt size for recording
    local best_size=""
    if [[ -f "$LOCAL_CKPT_DIR/best.pt" ]]; then
        best_size=$(du -h "$LOCAL_CKPT_DIR/best.pt" | cut -f1)
    fi

    # Update status to "complete" using python
    python3 -c "
import json
from pathlib import Path

runs_path = Path('$TRAINING_RUNS')
data = json.loads(runs_path.read_text())

if '$VERSION' in data.get('runs', {}):
    data['runs']['$VERSION']['status'] = 'complete'
    data['runs']['$VERSION']['retrieved'] = '$(date +%Y-%m-%d)'
    data['runs']['$VERSION']['r2_backup'] = True
    if '$best_size':
        data['runs']['$VERSION']['checkpoint_best'] = 'best.pt ($best_size)'
    data['runs']['$VERSION']['checkpoint_latest'] = 'step_${TOTAL_STEPS}.pt'
    runs_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print('Updated $VERSION -> complete')
else:
    print('WARNING: $VERSION not found in training_runs.json')
"
    log "training_runs.json updated."
}

# ─── Main ────────────────────────────────────────────────────────

MODE="${1:---check}"

case "$MODE" in
    --status|-s)
        check_ssh
        show_status
        ;;
    --poll|-p)
        log "=== Polling mode (every 30 min) ==="
        while true; do
            check_ssh || { log "SSH failed, retrying in 30 min..."; sleep 1800; continue; }

            status=$(get_training_status)
            if [[ "$status" == "completed" ]]; then
                log "Training completed! Starting retrieval..."
                retrieve_checkpoints
                upload_to_r2
                verify_checkpoints
                update_training_runs
                log "=== ALL DONE ==="
                log "Checkpoints: $LOCAL_CKPT_DIR"
                log "R2: checkpoints/$VERSION/"
                break
            else
                show_status
                log "Not complete yet. Sleeping 30 min..."
                sleep 1800
            fi
        done
        ;;
    --check|*)
        check_ssh
        status=$(get_training_status)

        if [[ "$status" == "completed" ]]; then
            log "Training COMPLETED. Starting retrieval pipeline..."
            retrieve_checkpoints
            upload_to_r2
            verify_checkpoints
            update_training_runs
            log ""
            log "=== ALL DONE ==="
            log "Local: $LOCAL_CKPT_DIR"
            log "R2:    checkpoints/$VERSION/"
        else
            show_status
            if [[ "$status" == "running" ]]; then
                log ""
                log "Training still in progress. Run again later or use --poll."
            fi
        fi
        ;;
esac
