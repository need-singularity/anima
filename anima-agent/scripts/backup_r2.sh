#!/bin/bash
# R2 backup — checkpoints + memory + state to Cloudflare R2
# Usage: bash scripts/backup_r2.sh
# Requires: AWS CLI configured with R2 credentials

set -e
BUCKET="anima-models"
AGENT_DIR="$(dirname "$0")/.."
TIMESTAMP=$(date '+%Y%m%d_%H%M')

echo "=== R2 Backup: $TIMESTAMP ==="

# 1. Agent state
echo "[1/3] Agent state..."
if [ -f "$AGENT_DIR/data/default/agent_state.pt" ]; then
    aws s3 cp "$AGENT_DIR/data/default/agent_state.pt" \
        "s3://$BUCKET/agent/state_$TIMESTAMP.pt" \
        --endpoint-url "$R2_ENDPOINT" 2>/dev/null && echo "  OK" || echo "  SKIP (no R2)"
fi

# 2. Memory database
echo "[2/3] Memory..."
if [ -f "$AGENT_DIR/data/default/memory.db" ]; then
    aws s3 cp "$AGENT_DIR/data/default/memory.db" \
        "s3://$BUCKET/agent/memory_$TIMESTAMP.db" \
        --endpoint-url "$R2_ENDPOINT" 2>/dev/null && echo "  OK" || echo "  SKIP"
fi
if [ -f "$AGENT_DIR/data/default/memory.json" ]; then
    aws s3 cp "$AGENT_DIR/data/default/memory.json" \
        "s3://$BUCKET/agent/memory_rag_$TIMESTAMP.json" \
        --endpoint-url "$R2_ENDPOINT" 2>/dev/null && echo "  OK" || echo "  SKIP"
fi

# 3. Auth (encrypted)
echo "[3/3] Auth..."
if [ -f "$AGENT_DIR/data/auth.json" ]; then
    aws s3 cp "$AGENT_DIR/data/auth.json" \
        "s3://$BUCKET/agent/auth_$TIMESTAMP.json" \
        --endpoint-url "$R2_ENDPOINT" 2>/dev/null && echo "  OK" || echo "  SKIP"
fi

echo "=== Backup complete ==="
