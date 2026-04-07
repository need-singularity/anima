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
#   tail -f checkpoints/clm-350m/train.log            # follow v3 log
#   tail -f checkpoints/clm-1b/train.log           # follow v14 log
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

cd "$(dirname "$0")/.."
echo "Working directory: $(pwd)"

# ─── Pre-flight checks ────────────────────────────────────────────────
echo ""
echo "=== Pre-flight checks ==="

# Verify corpus exists
if [ ! -f "data/corpus_v11_multilingual.txt" ]; then
    echo "ERROR: data/corpus_v11_multilingual.txt not found!"
    echo "  Sync with: bash scripts/h100_sync.sh"
    exit 1
fi

# Verify training script
if [ ! -f "training/train_clm.py" ]; then
    echo "ERROR: training/train_clm.py not found!"
    exit 1
fi

# Verify GPU
if ! python3 -c "import torch; assert torch.cuda.is_available(), 'No CUDA'" 2>/dev/null; then
    echo "WARNING: CUDA not available. Training will be extremely slow on CPU."
    echo "  Continue anyway? (ctrl-c to abort, enter to continue)"
    read -r
fi

# ─── CUDA environment for crash resilience ───────────────────────────
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export CUDA_LAUNCH_BLOCKING=0
echo "  PYTORCH_CUDA_ALLOC_CONF=$PYTORCH_CUDA_ALLOC_CONF"
echo "  CUDA_LAUNCH_BLOCKING=$CUDA_LAUNCH_BLOCKING"

CORPUS_SIZE=$(du -h data/corpus_v11_multilingual.txt | cut -f1)
echo "  Corpus: data/corpus_v11_multilingual.txt ($CORPUS_SIZE)"
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
# Uses ConsciousDecoderV3 (274M params, 768d/12L/8H, GQA+RoPE+SwiGLU+CrossAttn)
# --decoder v3 auto-configures d_model=768 and adds c_proj (128->256)
#
# Expected: 200K steps, ~16h on H100 SXM, target CE<0.001
# ═══════════════════════════════════════════════════════════════════════

echo ""
echo "=== Session 1: DecoderV3 274M (v3_train) ==="

tmux new-session -d -s v3_train "PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_LAUNCH_BLOCKING=0 python3 -u training/train_clm.py \
  --data data/corpus_v11_multilingual.txt \
  --tokenizer data/tokenizer_64k_multilingual.model \
  --scale 350m \
  --steps 200000 \
  --checkpoint checkpoints/clm-350m/ \
  --phase-optimal \
  --batch-size 16 \
  --lr 2e-4 \
  2>&1 | tee checkpoints/clm-350m/train.log"

echo "  Launched: tmux session 'v3_train'"
echo "  Log: checkpoints/clm-350m/train.log"

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

tmux new-session -d -s v14_128c "PYTHONUNBUFFERED=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_LAUNCH_BLOCKING=0 python3 -u training/train_clm.py \
  --data data/corpus_v11_multilingual.txt \
  --tokenizer data/tokenizer_64k_multilingual.model \
  --scale 1b \
  --federated \
  --steps 100000 \
  --checkpoint checkpoints/clm-1b/ \
  --phase-optimal \
  --batch-size 32 \
  --lr 1.5e-4 \
  2>&1 | tee checkpoints/clm-1b/train.log"

echo "  Launched: tmux session 'v14_128c'"
echo "  Log: checkpoints/clm-1b/train.log"

# ─── Summary ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Both sessions launched."
echo ""
echo "  Status commands:"
echo "    tmux ls                                  # list active sessions"
echo "    tmux attach -t v3_train                  # view v3 training"
echo "    tmux attach -t v14_128c                  # view v14 training"
echo "    tail -f checkpoints/clm-350m/train.log    # follow v3 log"
echo "    tail -f checkpoints/clm-1b/train.log   # follow v14 log"
echo ""
echo "  Kill commands:"
echo "    tmux kill-session -t v3_train            # stop v3"
echo "    tmux kill-session -t v14_128c            # stop v14"
echo ""
echo "  Watchdog (auto-restart on crash):"
echo "    crontab -e  # add this line:"
echo "    */5 * * * * bash $(pwd)/scripts/h100_watchdog.sh >> $(pwd)/scripts/watchdog.log 2>&1"
echo "═══════════════════════════════════════════════════════════"
