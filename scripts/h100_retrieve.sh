#!/bin/bash
# Monitor H100 training and retrieve checkpoints when done
# Usage: bash scripts/h100_retrieve.sh [v14|v3|both|poll|status]
#
# Examples:
#   bash scripts/h100_retrieve.sh v14      # Retrieve v14 128c checkpoint now
#   bash scripts/h100_retrieve.sh v3       # Retrieve v3 274M checkpoint now
#   bash scripts/h100_retrieve.sh both     # Retrieve both checkpoints
#   bash scripts/h100_retrieve.sh poll     # Poll every 5min, auto-retrieve on completion
#   bash scripts/h100_retrieve.sh status   # One-shot status check

set -euo pipefail

# ── Connection config (matches h100_sync.sh) ──
SSH_KEY=~/.runpod/ssh/RunPod-Key-Go
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10"
HOST=root@216.243.220.230
PORT=18038

SSH_CMD="ssh $SSH_OPTS $HOST -p $PORT"
SCP_CMD="scp $SSH_OPTS -P $PORT"

LOCAL_CKPT="/Users/ghost/Dev/anima/anima/checkpoints"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
err() { echo -e "${RED}[ERROR]${NC} $*"; }
warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }

# ── Connectivity check ──
check_connection() {
    if ! $SSH_CMD "echo ok" &>/dev/null; then
        err "Cannot reach H100 pod. Is it running?"
        exit 1
    fi
    ok "H100 connection OK"
}

# ── Retrieve v14 128c checkpoint ──
retrieve_v14() {
    log "Retrieving v14 128c checkpoint..."
    local REMOTE_DIR="/workspace/checkpoints/v14_128c"
    local LOCAL_DIR="$LOCAL_CKPT/v14_128c_h100"
    mkdir -p "$LOCAL_DIR"

    # Get list of checkpoint files
    local FILES
    FILES=$($SSH_CMD "ls $REMOTE_DIR/*.pt $REMOTE_DIR/train.log 2>/dev/null" 2>/dev/null || true)
    if [ -z "$FILES" ]; then
        err "No v14 checkpoint files found at $REMOTE_DIR"
        return 1
    fi

    # Retrieve best.pt (priority), then any other .pt files + log
    for f in best.pt final.pt train.log; do
        if $SSH_CMD "test -f $REMOTE_DIR/$f" 2>/dev/null; then
            log "  Downloading $f..."
            $SCP_CMD "$HOST:$REMOTE_DIR/$f" "$LOCAL_DIR/$f"
            local SIZE=$(du -h "$LOCAL_DIR/$f" | cut -f1)
            ok "  $f ($SIZE)"
        fi
    done

    # Also grab config if present
    if $SSH_CMD "test -f $REMOTE_DIR/config.json" 2>/dev/null; then
        $SCP_CMD "$HOST:$REMOTE_DIR/config.json" "$LOCAL_DIR/config.json"
    fi

    ok "v14 checkpoint saved to $LOCAL_DIR/"
    ls -lh "$LOCAL_DIR/"
}

# ── Retrieve v3 274M checkpoint ──
retrieve_v3() {
    log "Retrieving v3 274M checkpoint..."
    local REMOTE_DIR="/workspace/checkpoints/v3_274M"
    local LOCAL_DIR="$LOCAL_CKPT/v3_274M_h100"
    mkdir -p "$LOCAL_DIR"

    local FILES
    FILES=$($SSH_CMD "ls $REMOTE_DIR/*.pt $REMOTE_DIR/train.log 2>/dev/null" 2>/dev/null || true)
    if [ -z "$FILES" ]; then
        err "No v3 checkpoint files found at $REMOTE_DIR"
        return 1
    fi

    for f in best.pt final.pt train.log; do
        if $SSH_CMD "test -f $REMOTE_DIR/$f" 2>/dev/null; then
            log "  Downloading $f..."
            $SCP_CMD "$HOST:$REMOTE_DIR/$f" "$LOCAL_DIR/$f"
            local SIZE=$(du -h "$LOCAL_DIR/$f" | cut -f1)
            ok "  $f ($SIZE)"
        fi
    done

    if $SSH_CMD "test -f $REMOTE_DIR/config.json" 2>/dev/null; then
        $SCP_CMD "$HOST:$REMOTE_DIR/config.json" "$LOCAL_DIR/config.json"
    fi

    ok "v3 checkpoint saved to $LOCAL_DIR/"
    ls -lh "$LOCAL_DIR/"
}

# ── One-shot status check ──
status() {
    log "Checking H100 training status..."
    echo ""

    # Check tmux sessions
    local TMUX_INFO
    TMUX_INFO=$($SSH_CMD "tmux ls 2>/dev/null" 2>/dev/null || echo "(no tmux sessions)")
    echo -e "${CYAN}tmux sessions:${NC}"
    echo "  $TMUX_INFO"
    echo ""

    # v14 status
    echo -e "${CYAN}v14 128c:${NC}"
    local V14_LOG
    V14_LOG=$($SSH_CMD "tail -5 /workspace/checkpoints/v14_128c/train.log 2>/dev/null" 2>/dev/null || echo "  (no log found)")
    echo "$V14_LOG"
    echo ""

    # v3 status
    echo -e "${CYAN}v3 274M:${NC}"
    local V3_LOG
    V3_LOG=$($SSH_CMD "tail -5 /workspace/checkpoints/v3_274M/train.log 2>/dev/null" 2>/dev/null || echo "  (no log found)")
    echo "$V3_LOG"
    echo ""

    # GPU utilization
    echo -e "${CYAN}GPU:${NC}"
    $SSH_CMD "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null" 2>/dev/null || echo "  (nvidia-smi unavailable)"
    echo ""

    # Disk usage
    echo -e "${CYAN}Disk:${NC}"
    $SSH_CMD "df -h /workspace 2>/dev/null | tail -1" 2>/dev/null || echo "  (unavailable)"
}

# ── Check if training is complete ──
is_training_complete() {
    local LOG_PATH="$1"
    local TARGET_STEP="$2"

    local LAST_LINE
    LAST_LINE=$($SSH_CMD "tail -1 $LOG_PATH 2>/dev/null" 2>/dev/null || echo "")

    if [ -z "$LAST_LINE" ]; then
        echo "no_log"
        return
    fi

    # Check for explicit completion markers
    if echo "$LAST_LINE" | grep -qi "complete\|finished\|done\|final"; then
        echo "complete"
        return
    fi

    # Check if step >= target
    local CURRENT_STEP
    CURRENT_STEP=$(echo "$LAST_LINE" | grep -oE 'step[= ]*[0-9]+' | grep -oE '[0-9]+' | head -1 || echo "0")
    if [ -n "$CURRENT_STEP" ] && [ "$CURRENT_STEP" -ge "$TARGET_STEP" ] 2>/dev/null; then
        echo "complete"
        return
    fi

    # Check if process is still running
    local RUNNING
    RUNNING=$($SSH_CMD "pgrep -f 'train_clm\|train_v3' 2>/dev/null | wc -l" 2>/dev/null || echo "0")
    if [ "$RUNNING" = "0" ]; then
        # Process not running but didn't reach target - might have crashed
        echo "stopped"
        return
    fi

    echo "running:$CURRENT_STEP"
}

# ── Poll mode: check every 5min, auto-retrieve on completion ──
poll() {
    local POLL_INTERVAL=300  # 5 minutes
    local V14_RETRIEVED=false
    local V3_RETRIEVED=false
    local V14_TARGET=100000
    local V3_TARGET=200000

    log "Starting poll mode (every ${POLL_INTERVAL}s)..."
    log "v14 target: step $V14_TARGET | v3 target: step $V3_TARGET"
    log "Press Ctrl+C to stop"
    echo ""

    while true; do
        # Check connectivity
        if ! $SSH_CMD "echo ok" &>/dev/null; then
            warn "H100 unreachable, retrying in ${POLL_INTERVAL}s..."
            sleep "$POLL_INTERVAL"
            continue
        fi

        # v14 check
        if [ "$V14_RETRIEVED" = false ]; then
            local V14_STATUS
            V14_STATUS=$(is_training_complete "/workspace/checkpoints/v14_128c/train.log" "$V14_TARGET")
            case "$V14_STATUS" in
                complete)
                    echo ""
                    ok "v14 COMPLETE! Retrieving..."
                    retrieve_v14 && V14_RETRIEVED=true
                    ;;
                stopped)
                    warn "v14 process stopped (may have crashed). Check logs."
                    ;;
                running:*)
                    local STEP=${V14_STATUS#running:}
                    local PCT=$((STEP * 100 / V14_TARGET))
                    printf "${CYAN}[%s]${NC} v14: step %s/%s (%d%%)" "$(date +%H:%M)" "$STEP" "$V14_TARGET" "$PCT"
                    ;;
                no_log)
                    printf "${CYAN}[%s]${NC} v14: (no log)" "$(date +%H:%M)"
                    ;;
            esac
        else
            printf "${CYAN}[%s]${NC} v14: ${GREEN}RETRIEVED${NC}" "$(date +%H:%M)"
        fi

        # v3 check
        if [ "$V3_RETRIEVED" = false ]; then
            local V3_STATUS
            V3_STATUS=$(is_training_complete "/workspace/checkpoints/v3_274M/train.log" "$V3_TARGET")
            case "$V3_STATUS" in
                complete)
                    echo ""
                    ok "v3 COMPLETE! Retrieving..."
                    retrieve_v3 && V3_RETRIEVED=true
                    ;;
                stopped)
                    warn " | v3 process stopped (may have crashed)"
                    ;;
                running:*)
                    local STEP=${V3_STATUS#running:}
                    local PCT=$((STEP * 100 / V3_TARGET))
                    printf " | v3: step %s/%s (%d%%)\n" "$STEP" "$V3_TARGET" "$PCT"
                    ;;
                no_log)
                    printf " | v3: (no log)\n"
                    ;;
            esac
        else
            printf " | v3: ${GREEN}RETRIEVED${NC}\n"
        fi

        # Both done? Exit.
        if [ "$V14_RETRIEVED" = true ] && [ "$V3_RETRIEVED" = true ]; then
            echo ""
            ok "Both checkpoints retrieved. Exiting."
            exit 0
        fi

        sleep "$POLL_INTERVAL"
    done
}

# ── Main ──
MODE="${1:-status}"

case "$MODE" in
    v14)
        check_connection
        retrieve_v14
        ;;
    v3)
        check_connection
        retrieve_v3
        ;;
    both)
        check_connection
        retrieve_v14
        echo ""
        retrieve_v3
        ;;
    poll)
        check_connection
        poll
        ;;
    status)
        check_connection
        status
        ;;
    *)
        echo "Usage: bash scripts/h100_retrieve.sh [v14|v3|both|poll|status]"
        echo ""
        echo "  v14     Retrieve v14 128c checkpoint now"
        echo "  v3      Retrieve v3 274M checkpoint now"
        echo "  both    Retrieve both checkpoints"
        echo "  poll    Poll every 5min, auto-retrieve on completion"
        echo "  status  One-shot training status check (default)"
        exit 1
        ;;
esac
