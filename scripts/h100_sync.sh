#!/bin/bash
# Sync local code to H100 RunPod pod
# Usage: bash scripts/h100_sync.sh

set -euo pipefail

SSH_KEY=~/.runpod/ssh/RunPod-Key-Go
HOST=root@216.243.220.230
PORT=18038
SRC=/Users/ghost/Dev/anima/anima/src/
DEST=/workspace/

echo "Syncing src/ to H100..."
rsync -avz --progress \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no -p $PORT" \
  --include='*.py' --include='*.json' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  $SRC $DEST

# Also sync config
echo "Syncing config/..."
rsync -avz --progress \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no -p $PORT" \
  /Users/ghost/Dev/anima/anima/config/ $DEST/config/

# Also sync training
echo "Syncing train_v14.py..."
rsync -avz --progress \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no -p $PORT" \
  /Users/ghost/Dev/anima/anima/training/train_v14.py $DEST/train_v14.py

echo "Done. Files synced to $HOST:$DEST"
