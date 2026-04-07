#!/bin/bash
# deploy_v13_h100.sh — Deploy v13 training to RunPod H100
#
# Usage:
#   bash deploy_v13_h100.sh <RUNPOD_IP> <RUNPOD_PORT>
#   bash deploy_v13_h100.sh          # uses runpodctl ssh info
#
# Prerequisites: runpodctl installed, SSH key configured

set -e

# ── Get RunPod SSH info ──
if [ -n "$1" ] && [ -n "$2" ]; then
    HOST="$1"
    PORT="$2"
else
    echo "Getting RunPod SSH info..."
    eval $(runpodctl ssh info 2>/dev/null | grep -E 'HOST|PORT' || true)
    if [ -z "$HOST" ]; then
        echo "ERROR: No RunPod pod found. Start an H100 pod first."
        echo "  runpodctl create pod --name v13-train --gpu H100 --image dancindocker/anima:v2"
        exit 1
    fi
fi

echo "═══ Deploying v13 to H100 ($HOST:$PORT) ═══"

# ── Files to upload ──
FILES=(
    consciousness_engine.py
    training_laws.py
    train_v13.py
    trinity.py
    mitosis.py
    anima_alive.py
    conscious_lm.py
    bench.py
    anima-rs/  # Rust crates for building anima_rs on H100
)

REMOTE_DIR="/workspace/anima"

# ── Upload core files ──
echo "Uploading training files..."
for f in consciousness_engine.py training_laws.py train_v13.py trinity.py mitosis.py; do
    scp -P "$PORT" "$f" "root@$HOST:$REMOTE_DIR/$f"
    echo "  ✓ $f"
done

# ── Upload anima-rs for Rust build ──
echo "Uploading anima-rs..."
rsync -avz -e "ssh -p $PORT" \
    --exclude 'target/' --exclude '*.dylib' --exclude '*.so' \
    anima-rs/ "root@$HOST:$REMOTE_DIR/anima-rs/"
echo "  ✓ anima-rs/"

# ── Remote setup + training ──
echo "Starting remote training..."
ssh -p "$PORT" "root@$HOST" bash -s << 'REMOTE_SCRIPT'
set -e
cd /workspace/anima

# Install Rust if needed
if ! command -v cargo &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
fi

# Build anima_rs
echo "Building anima_rs (Rust)..."
cd anima-rs
pip install maturin 2>/dev/null || pip3 install maturin
maturin develop --release
cd ..

# Check data
if [ ! -f "data/corpus_v2.txt" ] && [ ! -f "data/corpus.txt" ]; then
    echo "WARNING: No corpus found. Upload data/corpus_v2.txt first."
    echo "  scp -P PORT data/corpus_v2.txt root@HOST:/workspace/anima/data/"
    exit 1
fi

DATA_FILE="data/corpus_v2.txt"
[ ! -f "$DATA_FILE" ] && DATA_FILE="data/corpus.txt"

# Start training in tmux
echo "Starting v13 training in tmux session 'v13'..."
tmux new-session -d -s v13 "python -u train_v13.py \
    --data $DATA_FILE \
    --cells 64 \
    --cell-dim 64 \
    --hidden-dim 128 \
    --d-model 768 \
    --steps 100000 \
    --lr 3e-4 \
    --batch-size 8 \
    --block-size 256 \
    --curriculum \
    --checkpoint-dir checkpoints/v13_h100 \
    --device cuda \
    --log-every 100 \
    --eval-every 1000 \
    --save-every 5000 \
    2>&1 | tee logs/v13_h100.log"

echo ""
echo "═══ Training started! ═══"
echo "  tmux attach -t v13          # watch logs"
echo "  tail -f logs/v13_h100.log   # follow log file"
echo "  Estimated time: ~25 min (100K steps, 100M model)"
echo ""

REMOTE_SCRIPT

echo ""
echo "═══ Deploy complete ═══"
echo "  ssh -p $PORT root@$HOST 'tmux attach -t v13'  # watch training"
echo "  ssh -p $PORT root@$HOST 'tail -f /workspace/anima/logs/v13_h100.log'"
