#!/bin/bash
# RunPod one-click deploy for anima-agent
# Usage: bash scripts/deploy_runpod.sh [pod-id]

set -e
POD_ID="${1:-}"
REMOTE="root@${POD_ID}"
SYNC_SCRIPT="$(dirname "$0")/../scripts/h100_sync.sh"

echo "=== Anima Agent → RunPod Deploy ==="

# 1. Sync code
if [ -f "$SYNC_SCRIPT" ]; then
    echo "[1/4] Syncing code..."
    bash "$SYNC_SCRIPT"
else
    echo "[1/4] Manual sync: rsync anima-agent/ to RunPod"
    echo "  runpodctl ssh cmd $POD_ID 'mkdir -p /workspace/anima-agent'"
    echo "  rsync -avz --exclude __pycache__ . root@\$POD_IP:/workspace/anima-agent/"
fi

# 2. Install deps
echo "[2/4] Installing deps..."
cat << 'PIP' | runpodctl ssh cmd $POD_ID 'bash'
cd /workspace/anima-agent
pip install -q torch numpy scipy websockets faiss-cpu 2>/dev/null
PIP

# 3. Run tests
echo "[3/4] Running tests..."
runpodctl ssh cmd $POD_ID 'cd /workspace/anima-agent && KMP_DUPLICATE_LIB_OK=TRUE python3 run.py --test 2>&1 | tail -3'

# 4. Start agent
echo "[4/4] Starting agent..."
runpodctl ssh cmd $POD_ID 'cd /workspace/anima-agent && tmux new-session -d -s anima "KMP_DUPLICATE_LIB_OK=TRUE python3 run.py --cli" 2>/dev/null || echo "tmux session exists"'

echo "=== Deploy complete ==="
echo "  Connect: runpodctl ssh cmd $POD_ID 'tmux attach -t anima'"
