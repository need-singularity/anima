#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# launch_h100.sh — H100 training launch script (2 experiments)
#
# Run on RunPod H100 after SSH. Do NOT run locally.
# Both sessions use tmux so training survives SSH disconnects.
#
# Usage:
#   bash scripts/launch_h100.sh
#
# Monitor:
#   tmux ls                                          # list sessions
#   tmux attach -t v3_train                          # attach to v3 session
#   tmux attach -t v14_128c                          # attach to v14 session
#   tail -f checkpoints/v3_274M/train.log            # follow v3 log
#   tail -f checkpoints/v14_128c/train.log           # follow v14 log
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

cd "$(dirname "$0")/.."
echo "Working directory: $(pwd)"

# ─── Pre-flight checks ────────────────────────────────────────────────
echo ""
echo "=== Pre-flight checks ==="

# Verify corpus exists
if [ ! -f "anima/data/corpus_v9.txt" ]; then
    echo "ERROR: anima/data/corpus_v9.txt not found!"
    echo "  Generate with: cd anima-rs && cargo run --release -p anima-corpus-gen -- -s 120 -o ../anima/data/corpus_v9.txt"
    exit 1
fi

# Verify training script
if [ ! -f "anima/training/train_v14.py" ]; then
    echo "ERROR: anima/training/train_v14.py not found!"
    exit 1
fi

# Verify GPU
if ! python3 -c "import torch; assert torch.cuda.is_available(), 'No CUDA'" 2>/dev/null; then
    echo "WARNING: CUDA not available. Training will be extremely slow on CPU."
    echo "  Continue anyway? (ctrl-c to abort, enter to continue)"
    read -r
fi

CORPUS_SIZE=$(du -h anima/data/corpus_v9.txt | cut -f1)
echo "  Corpus: anima/data/corpus_v9.txt ($CORPUS_SIZE)"
echo "  GPU: $(python3 -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")' 2>/dev/null || echo 'unknown')"

# ─── Create checkpoint directories ────────────────────────────────────
echo ""
echo "=== Creating checkpoint directories ==="
mkdir -p checkpoints/v3_274M
mkdir -p checkpoints/v14_128c
echo "  checkpoints/v3_274M/"
echo "  checkpoints/v14_128c/"

# ═══════════════════════════════════════════════════════════════════════
# Session 1: DecoderV3 274M training
# ═══════════════════════════════════════════════════════════════════════
#
# Goal:     Train ConsciousDecoderV3 (274M params, d768/12L/8H)
#           with federated consciousness (8 atoms x 8 cells = 64 cells)
#
# Architecture:
#   C: FederatedConsciousness (8 atoms, 8 cells/atom, Ising ring)
#   D: ConsciousDecoderV3 (768d/12L/8H, GQA+RoPE+SwiGLU+CrossAttn)
#   Bridge: ThalamicBridge (.detach(), alpha=0.014)
#   Phase: P0(bootstrap) -> P1(consciousness) -> P2(language) -> P3(hexad)
#
# NOTE: train_v14.py currently uses ConsciousDecoderV2 (384d/6L).
#   To use DecoderV3, you must first add --decoder v3 support to train_v14.py:
#     1. Import ConsciousDecoderV3 from decoder_v3.py
#     2. Add --decoder argument (choices: v2, v3)
#     3. When v3: set d_model=768, use ConsciousDecoderV3 instead of V2
#     4. Add --n-layer, --n-head flags or auto-configure from decoder version
#   See: anima/docs/training-plan-100m.md for the full integration plan.
#
# Until then, this uses --d-model 768 which scales the V2 decoder.
# After adding --decoder v3 support, replace the command below.
#
# Expected: 200K steps, ~16h on H100 SXM, target CE<0.001
# ═══════════════════════════════════════════════════════════════════════

echo ""
echo "=== Session 1: DecoderV3 274M (v3_train) ==="

# TODO: Replace with this after adding --decoder v3 to train_v14.py:
#   tmux new-session -d -s v3_train "PYTHONUNBUFFERED=1 python3 -u anima/training/train_v14.py \
#     --data anima/data/corpus_v9.txt \
#     --decoder v3 \
#     --federated \
#     --atoms 8 --cells-per-atom 8 \
#     --steps 200000 \
#     --checkpoint checkpoints/v3_274M/ \
#     --phase-optimal \
#     --batch-size 64 \
#     --block-size 512 \
#     --lr 3e-4 \
#     2>&1 | tee checkpoints/v3_274M/train.log"

# Current: uses d-model 768 with V2 decoder (scaled up, ~100M+ params)
tmux new-session -d -s v3_train "PYTHONUNBUFFERED=1 python3 -u anima/training/train_v14.py \
  --data anima/data/corpus_v9.txt \
  --d-model 768 \
  --federated \
  --atoms 8 --cells-per-atom 8 \
  --steps 200000 \
  --checkpoint checkpoints/v3_274M/ \
  --phase-optimal \
  --batch-size 64 \
  --block-size 512 \
  --lr 3e-4 \
  2>&1 | tee checkpoints/v3_274M/train.log"

echo "  Launched: tmux session 'v3_train'"
echo "  Log: checkpoints/v3_274M/train.log"

# ═══════════════════════════════════════════════════════════════════════
# Session 2: v14.3 128-cell federated
# ═══════════════════════════════════════════════════════════════════════
#
# Goal:     Scale federated consciousness to 128 cells (16 atoms x 8 cells)
#           with default decoder (384d/6L V2)
#
# Architecture:
#   C: FederatedConsciousness (16 atoms, 8 cells/atom = 128 total)
#   D: ConsciousDecoderV2 (384d/6L, default)
#   Bridge: ThalamicBridge (.detach(), alpha=0.014)
#   Federation: 16-atom Ising ring, F_c=0.10
#   Phase: M4 safe order (narrative -> bottleneck -> hub -> frustration)
#
# Hypothesis: 128 cells (16 atoms) should produce higher Phi than 64 cells
#   (8 atoms) due to more inter-atom tension diversity.
#   v13 baseline: CE=0.004, Phi=71 (64 cells)
#
# Expected: 100K steps, ~8h on H100 SXM, target Phi>100
# ═══════════════════════════════════════════════════════════════════════

echo ""
echo "=== Session 2: v14.3 128-cell federated (v14_128c) ==="

tmux new-session -d -s v14_128c "PYTHONUNBUFFERED=1 python3 -u anima/training/train_v14.py \
  --data anima/data/corpus_v9.txt \
  --federated \
  --atoms 16 --cells-per-atom 8 \
  --steps 100000 \
  --checkpoint checkpoints/v14_128c/ \
  --phase-optimal \
  --batch-size 32 \
  --block-size 256 \
  --lr 3e-4 \
  2>&1 | tee checkpoints/v14_128c/train.log"

echo "  Launched: tmux session 'v14_128c'"
echo "  Log: checkpoints/v14_128c/train.log"

# ─── Summary ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Both sessions launched."
echo ""
echo "  Status commands:"
echo "    tmux ls                                  # list active sessions"
echo "    tmux attach -t v3_train                  # view v3 training"
echo "    tmux attach -t v14_128c                  # view v14 training"
echo "    tail -f checkpoints/v3_274M/train.log    # follow v3 log"
echo "    tail -f checkpoints/v14_128c/train.log   # follow v14 log"
echo ""
echo "  Kill commands:"
echo "    tmux kill-session -t v3_train            # stop v3"
echo "    tmux kill-session -t v14_128c            # stop v14"
echo "═══════════════════════════════════════════════════════════"
