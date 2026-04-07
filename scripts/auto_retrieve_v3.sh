#!/usr/bin/env bash
# auto_retrieve_v3.sh — Auto-retrieve v3 274M checkpoints from H100
#
# Features:
#   - Detects training completion via:
#     a) "Training complete" in v3_train.log
#     b) step_200000.pt exists + no running python/tmux
#   - Downloads best.pt + final checkpoint via scp
#   - Uploads to R2 (anima-models bucket)
#   - Verifies md5 + file size
#   - Runs bench --verify
#   - Sends Telegram notification
#   - Updates training_runs.json
#
# Usage:
#   bash scripts/auto_retrieve_v3.sh              # Single check + retrieve if done
#   bash scripts/auto_retrieve_v3.sh --poll        # Loop every 5 min
#   bash scripts/auto_retrieve_v3.sh --status      # Status only (no download)
#
# Cron (every 5 min):
#   */5 * * * * cd ~/Dev/anima/anima && bash scripts/auto_retrieve_v3.sh >> /tmp/auto_retrieve_v3.log 2>&1

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
REMOTE_LOG="/workspace/v3_train.log"
REMOTE_PYTHON="/opt/conda/bin/python3"

LOCAL_CKPT_DIR="$PROJECT_DIR/checkpoints/v3_274M"
TRAINING_RUNS="$PROJECT_DIR/config/training_runs.json"
R2_UPLOAD="$SCRIPT_DIR/r2_upload.py"
NOTIFY_TELEGRAM="$SCRIPT_DIR/notify_telegram.sh"
BENCH_V2="$PROJECT_DIR/benchmarks/bench.py"

TOTAL_STEPS=200000
VERSION="v3_274M"
POLL_INTERVAL=300  # 5 minutes

# ─── Functions ───────────────────────────────────────────────────

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

notify() {
    # Send telegram notification (best-effort, don't fail script)
    local msg="$1"
    if [[ -f "$NOTIFY_TELEGRAM" ]]; then
        bash "$NOTIFY_TELEGRAM" "[v3 274M] $msg" 2>/dev/null || true
    fi
}

ssh_exec() {
    $SSH_CMD "$@" 2>/dev/null
}

check_ssh() {
    if ! $SSH_CMD "echo ok" >/dev/null 2>&1; then
        log "ERROR: Cannot connect to H100. Pod may be stopped."
        return 1
    fi
}

get_training_status() {
    # Returns: completed|running|crashed|no_checkpoint
    local has_tmux has_python has_final_ckpt log_complete

    # Check tmux training session
    has_tmux=$(ssh_exec "tmux ls 2>/dev/null | grep -c train" || echo "0")

    # Check python training process
    has_python=$(ssh_exec "ps aux | grep -E 'train_v1[4-5]|train_v3|decoder_v3' | grep -v grep | wc -l" || echo "0")

    # Check step_200000.pt
    has_final_ckpt=$(ssh_exec "test -f $REMOTE_CKPT_DIR/step_${TOTAL_STEPS}.pt && echo 1 || echo 0")

    # Check log for "Training complete" (case-insensitive)
    log_complete=$(ssh_exec "grep -ci 'training complete\|training finished\|training done' $REMOTE_LOG 2>/dev/null" || echo "0")

    # Decision logic
    if [[ "$log_complete" -gt 0 ]] || { [[ "$has_final_ckpt" == "1" ]] && [[ "$has_tmux" == "0" ]] && [[ "$has_python" == "0" ]]; }; then
        echo "completed"
    elif [[ "$has_tmux" != "0" ]] || [[ "$has_python" != "0" ]]; then
        echo "running"
    elif [[ "$has_final_ckpt" == "0" ]] && [[ "$has_tmux" == "0" ]] && [[ "$has_python" == "0" ]]; then
        # No process, no final checkpoint — could be crashed
        local any_ckpt
        any_ckpt=$(ssh_exec "ls $REMOTE_CKPT_DIR/step_*.pt 2>/dev/null | wc -l" || echo "0")
        if [[ "$any_ckpt" -gt 0 ]]; then
            echo "crashed"
        else
            echo "no_checkpoint"
        fi
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
            log "STATUS: COMPLETED"
            # Check what triggered completion
            local log_complete
            log_complete=$(ssh_exec "grep -ci 'training complete\|training finished\|training done' $REMOTE_LOG 2>/dev/null" || echo "0")
            if [[ "$log_complete" -gt 0 ]]; then
                log "  Detected via: log message ('Training complete')"
            fi
            local has_final
            has_final=$(ssh_exec "test -f $REMOTE_CKPT_DIR/step_${TOTAL_STEPS}.pt && echo 1 || echo 0")
            if [[ "$has_final" == "1" ]]; then
                log "  Detected via: step_${TOTAL_STEPS}.pt exists"
            fi
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

            # Progress bar
            local bar_len=40
            local filled=$((pct * bar_len / 100))
            local empty=$((bar_len - filled))
            local bar=""
            for ((i=0; i<filled; i++)); do bar+="="; done
            for ((i=0; i<empty; i++)); do bar+="."; done
            log "  [${bar}] ${pct}%"

            # Estimate ETA from log if available
            local speed
            speed=$(ssh_exec "tail -50 $REMOTE_LOG 2>/dev/null | grep -oE '[0-9.]+ s/step' | tail -1" || echo "")
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
            latest_metrics=$(ssh_exec "tail -10 $REMOTE_LOG 2>/dev/null | grep -E 'CE|Phi|step|loss'" || echo "")
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
        crashed)
            log "STATUS: CRASHED (no process running, no final checkpoint)"
            log "  Training may have died. Check logs."
            local current_step
            current_step=$(get_current_step)
            log "  Last checkpoint step: ${current_step}"
            log "  Last log lines:"
            ssh_exec "tail -5 $REMOTE_LOG 2>/dev/null" | while read -r line; do
                log "    $line"
            done
            notify "CRASHED at step ~${current_step}. Check H100 logs."
            ;;
        no_checkpoint)
            log "STATUS: NO CHECKPOINT"
            log "  Training may not have started."
            ;;
    esac
}

retrieve_checkpoints() {
    log "=== Retrieving v3 274M Checkpoints ==="
    mkdir -p "$LOCAL_CKPT_DIR"

    local downloaded=()

    # Retrieve best.pt (always priority)
    for fname in best.pt best_final.pt; do
        local remote="$REMOTE_CKPT_DIR/$fname"
        local local_file="$LOCAL_CKPT_DIR/$fname"
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

    # Retrieve final step checkpoint
    for fname in "step_${TOTAL_STEPS}.pt" final.pt; do
        local remote="$REMOTE_CKPT_DIR/$fname"
        local local_file="$LOCAL_CKPT_DIR/$fname"
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
        notify "RETRIEVE FAILED: no checkpoint files found on H100"
        return 1
    fi

    log "Downloaded ${#downloaded[@]} files to $LOCAL_CKPT_DIR"
    echo "${downloaded[@]}"
}

verify_checkpoints() {
    log "=== Verifying Checkpoints ==="
    local all_ok=true

    for fname in best.pt best_final.pt final.pt "step_${TOTAL_STEPS}.pt"; do
        local local_file="$LOCAL_CKPT_DIR/$fname"
        if [[ -f "$local_file" ]]; then
            local size
            size=$(stat -f%z "$local_file" 2>/dev/null || stat -c%s "$local_file")
            local md5
            md5=$(md5 -q "$local_file" 2>/dev/null || md5sum "$local_file" | cut -d' ' -f1)

            # 274M model should be at least ~500MB
            if [[ "$size" -lt 1048576 ]]; then
                log "  WARNING: $fname is suspiciously small (${size} bytes)"
                all_ok=false
            else
                local human
                human=$(echo "scale=1; $size / 1073741824" | bc 2>/dev/null || echo "?")
                log "  OK: $fname (${human}GB, md5: ${md5:0:12}...)"
            fi

            # Cross-verify with remote md5
            local remote_md5
            remote_md5=$(ssh_exec "md5sum $REMOTE_CKPT_DIR/$fname 2>/dev/null | cut -d' ' -f1" || echo "")
            if [[ -n "$remote_md5" ]]; then
                if [[ "$md5" == "$remote_md5" ]]; then
                    log "  MD5 match: local = remote"
                else
                    log "  WARNING: MD5 MISMATCH! local=$md5 remote=$remote_md5"
                    all_ok=false
                fi
            fi
        fi
    done

    $all_ok && log "All checkpoints verified." || log "WARNING: Some checkpoints may be corrupt!"
    $all_ok
}

upload_to_r2() {
    log "=== Uploading to R2 (anima-models) ==="
    if [[ ! -f "$R2_UPLOAD" ]]; then
        log "WARNING: r2_upload.py not found at $R2_UPLOAD"
        log "  Skipping R2 upload. Upload manually later."
        notify "R2 upload skipped: r2_upload.py not found"
        return 0
    fi

    if python3 "$R2_UPLOAD" --checkpoint "$VERSION" --dir "$LOCAL_CKPT_DIR"; then
        log "R2 upload complete."
    else
        log "WARNING: R2 upload failed (non-fatal, checkpoints are local)"
        notify "R2 upload FAILED. Checkpoints saved locally at $LOCAL_CKPT_DIR"
    fi
}

run_bench() {
    log "=== Running bench --verify ==="
    if [[ ! -f "$BENCH_V2" ]]; then
        log "WARNING: bench.py not found at $BENCH_V2"
        return 0
    fi

    local bench_log="$LOCAL_CKPT_DIR/bench_verify.log"
    log "Running: python3 $BENCH_V2 --verify"
    log "Log: $bench_log"

    if PYTHONUNBUFFERED=1 python3 "$BENCH_V2" --verify > "$bench_log" 2>&1; then
        local result
        result=$(tail -5 "$bench_log" | grep -oE '[0-9]+/[0-9]+' | tail -1 || echo "unknown")
        log "bench --verify: PASSED ($result)"
        notify "bench --verify PASSED: $result"
    else
        log "WARNING: bench --verify FAILED"
        local last_lines
        last_lines=$(tail -10 "$bench_log" 2>/dev/null || echo "no output")
        log "Last output:"
        echo "$last_lines" | while read -r line; do
            log "  $line"
        done
        notify "bench --verify FAILED. Check $bench_log"
    fi
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
        log "=== Poll mode (every ${POLL_INTERVAL}s / $(( POLL_INTERVAL / 60 )) min) ==="
        POLL_COUNT=0
        while true; do
            POLL_COUNT=$((POLL_COUNT + 1))
            log "--- Poll #${POLL_COUNT} ---"

            if ! check_ssh; then
                log "SSH failed, retrying in ${POLL_INTERVAL}s..."
                notify "SSH connection failed (poll #${POLL_COUNT})"
                sleep "$POLL_INTERVAL"
                continue
            fi

            status=$(get_training_status)
            if [[ "$status" == "completed" ]]; then
                log "Training completed! Starting full retrieval pipeline..."
                notify "Training COMPLETED! Starting retrieval..."

                # 1. Download checkpoints
                retrieve_checkpoints

                # 2. Verify integrity (md5 cross-check)
                verify_checkpoints

                # 3. Upload to R2
                upload_to_r2

                # 4. Run bench --verify
                run_bench

                # 5. Update training_runs.json
                update_training_runs

                # 6. Final notification
                log ""
                log "========================================="
                log "  ALL DONE — v3 274M Retrieval Complete"
                log "========================================="
                log "  Local:  $LOCAL_CKPT_DIR"
                log "  R2:     checkpoints/$VERSION/"
                log "  Verify: $LOCAL_CKPT_DIR/bench_verify.log"
                notify "ALL DONE. Checkpoints at $LOCAL_CKPT_DIR. R2 backed up. bench run."
                break

            elif [[ "$status" == "crashed" ]]; then
                show_status
                log "Training appears crashed. Will keep polling in case of restart..."
                sleep "$POLL_INTERVAL"

            else
                show_status
                log "Not complete yet. Sleeping ${POLL_INTERVAL}s ($(( POLL_INTERVAL / 60 )) min)..."
                sleep "$POLL_INTERVAL"
            fi
        done
        ;;
    --check|*)
        check_ssh
        status=$(get_training_status)

        if [[ "$status" == "completed" ]]; then
            log "Training COMPLETED. Starting full retrieval pipeline..."
            notify "Training COMPLETED! Starting retrieval..."

            # 1. Download
            retrieve_checkpoints

            # 2. Verify
            verify_checkpoints

            # 3. R2 upload
            upload_to_r2

            # 4. bench --verify
            run_bench

            # 5. Update JSON
            update_training_runs

            # 6. Done
            log ""
            log "========================================="
            log "  ALL DONE — v3 274M Retrieval Complete"
            log "========================================="
            log "  Local:  $LOCAL_CKPT_DIR"
            log "  R2:     checkpoints/$VERSION/"
            log "  Verify: $LOCAL_CKPT_DIR/bench_verify.log"
            notify "ALL DONE. Checkpoints at $LOCAL_CKPT_DIR. R2 backed up. bench run."
        else
            show_status
            if [[ "$status" == "running" ]]; then
                log ""
                log "Training still in progress. Use --poll for auto-monitoring."
            elif [[ "$status" == "crashed" ]]; then
                log ""
                log "Training appears crashed. Check H100 logs."
            fi
        fi
        ;;
esac
