#!/bin/bash
# Monitor v3 274M training on RunPod H100
# Usage: bash scripts/monitor_v3.sh [--poll N]  (poll every N seconds, default: show once)

SSH_KEY=~/.runpod/ssh/RunPod-Key-Go
SSH_HOST="root@216.243.220.230"
SSH_PORT=18038
SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 $SSH_HOST -p $SSH_PORT"

POLL_INTERVAL=0

while [[ "$1" ]]; do
    case "$1" in
        --poll) POLL_INTERVAL="$2"; shift 2;;
        *) shift;;
    esac
done

check_status() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  v3 274M Training Monitor — $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check pod status
    POD_STATUS=$(/opt/homebrew/bin/runpodctl get pod 2>/dev/null | grep v13-train | awk '{print $2}')
    if [ -z "$POD_STATUS" ] || [ "$POD_STATUS" != "RUNNING" ]; then
        echo "❌ Pod not running (status: ${POD_STATUS:-unknown})"
        return 1
    fi
    echo "✅ Pod: RUNNING ($2.69/hr)"

    # Get training log tail
    echo ""
    echo "📊 Latest training output:"
    $SSH_CMD "tail -30 /workspace/v3_train.log 2>/dev/null || tail -30 /workspace/nohup.out 2>/dev/null" 2>/dev/null

    # Get GPU status
    echo ""
    echo "🖥️  GPU Status:"
    $SSH_CMD "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader" 2>/dev/null

    # Get disk usage
    echo ""
    echo "💾 Disk:"
    $SSH_CMD "df -h /workspace | tail -1" 2>/dev/null

    # Get checkpoint info
    echo ""
    echo "📁 Latest checkpoints:"
    $SSH_CMD "ls -lhrt /workspace/checkpoints/v3_merged/*.pt 2>/dev/null | tail -5" 2>/dev/null

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

if [ "$POLL_INTERVAL" -gt 0 ] 2>/dev/null; then
    while true; do
        clear
        check_status
        echo "Next check in ${POLL_INTERVAL}s (Ctrl+C to stop)"
        sleep "$POLL_INTERVAL"
    done
else
    check_status
fi
