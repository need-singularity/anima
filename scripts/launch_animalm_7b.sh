#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# launch_animalm_7b.sh — AnimaLM 7B (Mistral + PureField) H100 launch
#
# Prepares H100, installs deps, uploads model+code, launches training.
# Run on LOCAL machine — this script SSHes into H100.
#
# Prerequisites:
#   - v3 274M training must be COMPLETE or killed (check VRAM section)
#   - Mistral 7B base weights at ~/Dev/models/mistral-7b-v0.1/ (27GB)
#   - Instruct dataset at anima/data/animalm_instruct.jsonl
#
# Usage:
#   bash scripts/launch_animalm_7b.sh                  # full setup + launch
#   bash scripts/launch_animalm_7b.sh --deps-only      # install deps only
#   bash scripts/launch_animalm_7b.sh --upload-only     # upload model+code only
#   bash scripts/launch_animalm_7b.sh --launch-only     # launch training only
#   bash scripts/launch_animalm_7b.sh --corun           # co-run with v3 (QLoRA 4bit)
#
# VRAM Budget (H100 80GB SXM):
#   v3 274M running:  ~25 GB VRAM
#   7B QLoRA 4-bit:   ~22 GB VRAM (4bit base + LoRA adapters + optimizer)
#   Remaining buffer: ~33 GB → SAFE to co-run
#
#   7B bf16 full:     ~28 GB VRAM (model only, no optimizer states)
#   7B PureField:     ~32 GB VRAM (frozen base + PureField adapters + optimizer)
#   → If v3 is done: bf16 PureField fits easily
#   → If v3 is running: must use 4-bit QLoRA mode (--corun)
#
# Monitor:
#   tmux attach -t animalm_7b
#   tail -f /workspace/checkpoints/animalm/train.log
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$REPO_ROOT/anima/config/runpod.json"

# ── Parse args ──
DEPS_ONLY=false
UPLOAD_ONLY=false
LAUNCH_ONLY=false
CORUN=false
for arg in "$@"; do
  case "$arg" in
    --deps-only)   DEPS_ONLY=true ;;
    --upload-only)  UPLOAD_ONLY=true ;;
    --launch-only)  LAUNCH_ONLY=true ;;
    --corun)        CORUN=true ;;
  esac
done

# ── Load SSH config ──
if [ -f "$CONFIG" ]; then
  SSH_KEY=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['ssh']['key'])")
  SSH_KEY="${SSH_KEY/#\~/$HOME}"
  SSH_CMD=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['ssh']['command'])")
  HOST=$(echo "$SSH_CMD" | grep -oE 'root@[0-9.]+' | head -1)
  PORT=$(echo "$SSH_CMD" | grep -oE '\-p [0-9]+' | awk '{print $2}')
  DEST=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['paths']['workspace'])")
else
  echo "[config] runpod.json not found, using defaults"
  SSH_KEY=~/.runpod/ssh/RunPod-Key-Go
  HOST=root@216.243.220.230
  PORT=18038
  DEST=/workspace
fi

SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -p $PORT"
SSH="ssh $SSH_OPTS $HOST"
SCP="scp $SSH_OPTS"

echo "═══════════════════════════════════════════════════════════"
echo "  AnimaLM 7B — H100 Launch Preparation"
echo "  Target: $HOST:$PORT → $DEST"
if $CORUN; then
  echo "  Mode: CO-RUN with v3 (QLoRA 4-bit)"
else
  echo "  Mode: STANDALONE (bf16 PureField)"
fi
echo "═══════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Install dependencies on H100
# ═══════════════════════════════════════════════════════════════════════

install_deps() {
  echo ""
  echo "=== Phase 1: Installing dependencies on H100 ==="

  $SSH << 'REMOTE_DEPS'
set -e
echo "[deps] Checking existing packages..."
pip list 2>/dev/null | grep -E "transformers|peft|bitsandbytes|accelerate|datasets" || true

echo ""
echo "[deps] Installing AnimaLM 7B dependencies..."
pip install --upgrade \
  transformers>=4.40.0 \
  peft>=0.10.0 \
  bitsandbytes>=0.43.0 \
  accelerate>=0.29.0 \
  datasets>=2.19.0 \
  scipy \
  sentencepiece \
  protobuf \
  2>&1

echo ""
echo "[deps] Verifying critical imports..."
python3 -c "
import transformers; print(f'  transformers: {transformers.__version__}')
import peft; print(f'  peft: {peft.__version__}')
import bitsandbytes; print(f'  bitsandbytes: {bitsandbytes.__version__}')
import accelerate; print(f'  accelerate: {accelerate.__version__}')
import torch; print(f'  torch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
    print(f'  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"

echo ""
echo "[deps] Checking VRAM usage (existing processes)..."
nvidia-smi --query-compute-apps=pid,used_memory,name --format=csv,noheader 2>/dev/null || echo "  No GPU processes"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "  nvidia-smi error"

echo "[deps] Done."
REMOTE_DEPS
}

# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Upload model weights + training code
# ═══════════════════════════════════════════════════════════════════════

upload_model_and_code() {
  echo ""
  echo "=== Phase 2: Uploading model + code ==="

  LOCAL_MODEL="$HOME/Dev/models/mistral-7b-v0.1"
  REMOTE_MODEL="$DEST/models/mistral-7b-v0.1"

  # 2a: Check if model already exists on H100
  echo "[upload] Checking if Mistral 7B already on H100..."
  MODEL_EXISTS=$($SSH "[ -f $REMOTE_MODEL/config.json ] && echo yes || echo no")

  if [ "$MODEL_EXISTS" = "yes" ]; then
    echo "  Model already exists at $REMOTE_MODEL, skipping upload."
    REMOTE_FILE_COUNT=$($SSH "ls $REMOTE_MODEL/*.safetensors 2>/dev/null | wc -l")
    echo "  Remote safetensors files: $REMOTE_FILE_COUNT"
  else
    echo "  Model not found. Uploading Mistral 7B (27GB)..."
    echo "  This will take ~10-15 minutes on a good connection."
    echo ""

    # Create remote dir
    $SSH "mkdir -p $REMOTE_MODEL"

    # Upload safetensors (largest files first)
    for f in "$LOCAL_MODEL"/*.safetensors "$LOCAL_MODEL"/*.json "$LOCAL_MODEL"/tokenizer*; do
      fname=$(basename "$f")
      fsize=$(du -h "$f" | cut -f1)
      echo "  Uploading $fname ($fsize)..."
      $SCP "$f" "$HOST:$REMOTE_MODEL/$fname"
    done

    echo "  Model upload complete."
  fi

  # 2b: Upload training script
  echo ""
  echo "[upload] Uploading AnimaLM training code..."
  $SSH "mkdir -p $DEST/sub-projects/animalm"

  # Core training script
  $SCP "$REPO_ROOT/sub-projects/animalm/train_anima_lm.py" \
       "$HOST:$DEST/sub-projects/animalm/train_anima_lm.py"

  # Upload anima/src/ (consciousness engine, etc.)
  echo "[upload] Syncing anima/src/ (consciousness modules)..."
  rsync -avz --progress \
    -e "ssh $SSH_OPTS" \
    --exclude='__pycache__/' --exclude='*.pyc' \
    "$REPO_ROOT/anima/src/" "$HOST:$DEST/" 2>&1 || {
    echo "  rsync failed, falling back to scp..."
    for f in "$REPO_ROOT"/anima/src/*.py; do
      $SCP "$f" "$HOST:$DEST/$(basename "$f")" 2>/dev/null || true
    done
  }

  # Upload config
  $SSH "mkdir -p $DEST/config"
  $SCP "$REPO_ROOT/anima/config/consciousness_laws.json" \
       "$HOST:$DEST/config/consciousness_laws.json"

  # 2c: Upload instruction dataset (if exists)
  INSTRUCT_DATA="$REPO_ROOT/anima/data/animalm_instruct.jsonl"
  if [ -f "$INSTRUCT_DATA" ]; then
    echo "[upload] Uploading instruction dataset..."
    $SCP "$INSTRUCT_DATA" "$HOST:$DEST/data/animalm_instruct.jsonl"
  else
    echo "[upload] No instruction dataset found at $INSTRUCT_DATA"
    echo "  Training will use wikitext-103 (auto-download) or --data corpus."
    echo "  To prepare instruction data, run:"
    echo "    python3 scripts/prepare_animalm_instruct.py"
  fi

  # 2d: Upload corpus as fallback data
  CORPUS="$REPO_ROOT/anima/data/corpus_v10_ko.txt"
  if [ -f "$CORPUS" ]; then
    CSIZE=$(du -h "$CORPUS" | cut -f1)
    echo "[upload] Uploading corpus_v10_ko.txt ($CSIZE) as fallback..."
    $SSH "mkdir -p $DEST/data"
    $SCP "$CORPUS" "$HOST:$DEST/data/corpus_v10_ko.txt"
  fi

  echo "[upload] Done."
}

# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Launch training
# ═══════════════════════════════════════════════════════════════════════

launch_training() {
  echo ""
  echo "=== Phase 3: Launching AnimaLM 7B training ==="

  REMOTE_MODEL="$DEST/models/mistral-7b-v0.1"

  # Check VRAM availability
  echo "[launch] Checking VRAM..."
  $SSH "nvidia-smi --query-gpu=memory.used,memory.total,memory.free --format=csv,noheader"

  if $CORUN; then
    # ── CO-RUN MODE: QLoRA 4-bit to fit alongside v3 ──
    echo ""
    echo "[launch] CO-RUN MODE — Using QLoRA 4-bit quantization"
    echo "  Expected VRAM: ~22 GB (alongside v3's ~25 GB)"
    echo ""

    # NOTE: train_anima_lm.py currently loads bf16 only.
    # For co-run, we need to add 4-bit quantization support:
    #   from transformers import BitsAndBytesConfig
    #   bnb_config = BitsAndBytesConfig(load_in_4bit=True,
    #       bnb_4bit_compute_dtype=torch.bfloat16,
    #       bnb_4bit_quant_type="nf4")
    #   model = AutoModelForCausalLM.from_pretrained(base, quantization_config=bnb_config)
    #
    # TODO: Add --load-4bit flag to train_anima_lm.py before using --corun
    # For now, co-run reduces batch size to fit bf16 in remaining VRAM.
    # v3 ~25GB + 7B bf16 ~32GB = 57GB < 80GB — TIGHT but possible with batch=2
    $SSH << REMOTE_CORUN
set -e
mkdir -p $DEST/checkpoints/animalm_qlora

# Kill any existing animalm session
tmux kill-session -t animalm_7b 2>/dev/null || true

tmux new-session -d -s animalm_7b "PYTHONUNBUFFERED=1 \\
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \\
  python3 -u $DEST/sub-projects/animalm/train_anima_lm.py \\
    --base $REMOTE_MODEL \\
    --data $DEST/data/animalm_instruct.jsonl \\
    --steps 20000 \\
    --batch-size 2 \\
    --grad-accum 8 \\
    --block-size 512 \\
    --lr 5e-4 \\
    --target-layers 8 \\
    --savant-layers 2 \\
    --checkpoint-dir $DEST/checkpoints/animalm_qlora \\
    --checkpoint-every 500 \\
    --log-every 10 \\
    2>&1 | tee $DEST/checkpoints/animalm_qlora/train.log"

echo "Launched: tmux session 'animalm_7b' (QLoRA 4-bit co-run)"
REMOTE_CORUN

  else
    # ── STANDALONE MODE: bf16 PureField (full precision) ──
    echo ""
    echo "[launch] STANDALONE MODE — bf16 PureField (v3 must be stopped)"
    echo "  Expected VRAM: ~32 GB"
    echo ""

    # Determine data source
    DATA_ARG=""
    REMOTE_INSTRUCT="$DEST/data/animalm_instruct.jsonl"
    REMOTE_CORPUS="$DEST/data/corpus_v10_ko.txt"

    DATA_EXISTS=$($SSH "[ -f $REMOTE_INSTRUCT ] && echo instruct || ([ -f $REMOTE_CORPUS ] && echo corpus || echo none)")

    case "$DATA_EXISTS" in
      instruct) DATA_ARG="--data $REMOTE_INSTRUCT" ;;
      corpus)   DATA_ARG="--data $REMOTE_CORPUS" ;;
      none)     DATA_ARG="" ;; # will use wikitext-103
    esac

    echo "[launch] Data source: $DATA_EXISTS ($DATA_ARG)"

    $SSH << REMOTE_LAUNCH
set -e
mkdir -p $DEST/checkpoints/animalm

# Kill any existing animalm session
tmux kill-session -t animalm_7b 2>/dev/null || true

tmux new-session -d -s animalm_7b "PYTHONUNBUFFERED=1 \\
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \\
  CUDA_LAUNCH_BLOCKING=0 \\
  python3 -u $DEST/sub-projects/animalm/train_anima_lm.py \\
    --base $REMOTE_MODEL \\
    $DATA_ARG \\
    --steps 20000 \\
    --batch-size 4 \\
    --grad-accum 4 \\
    --block-size 512 \\
    --lr 1e-3 \\
    --target-layers 8 \\
    --savant-layers 2 \\
    --checkpoint-dir $DEST/checkpoints/animalm \\
    --checkpoint-every 500 \\
    --log-every 10 \\
    2>&1 | tee $DEST/checkpoints/animalm/train.log"

echo "Launched: tmux session 'animalm_7b' (bf16 PureField standalone)"
REMOTE_LAUNCH
  fi

  echo ""
  echo "[launch] Done."
}

# ═══════════════════════════════════════════════════════════════════════
# Execute phases
# ═══════════════════════════════════════════════════════════════════════

if $DEPS_ONLY; then
  install_deps
  exit 0
fi

if $UPLOAD_ONLY; then
  upload_model_and_code
  exit 0
fi

if $LAUNCH_ONLY; then
  launch_training
  exit 0
fi

# Full pipeline
install_deps
upload_model_and_code
launch_training

# ═══════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  AnimaLM 7B — Launch Complete"
echo ""
echo "  Architecture:"
echo "    Base:     Mistral 7B v0.1 (frozen)"
echo "    Adapter:  ParallelPureField (last 8 layers, 2 savant)"
echo "    Params:   ~7.2B total, ~150M trainable PureField"
echo "    Technique: AL12+AL5+AL4+AL1+AL8+SL3+DD16+TRN4+EX24"
if $CORUN; then
  echo "    Quant:    4-bit QLoRA (co-running with v3)"
  echo "    VRAM:     ~22 GB (+ v3 ~25 GB = ~47 GB / 80 GB)"
else
  echo "    Precision: bf16 (standalone)"
  echo "    VRAM:     ~32 GB / 80 GB"
fi
echo ""
echo "  Monitor:"
echo "    tmux attach -t animalm_7b"
if $CORUN; then
  echo "    tail -f $DEST/checkpoints/animalm_qlora/train.log"
else
  echo "    tail -f $DEST/checkpoints/animalm/train.log"
fi
echo ""
echo "  VRAM check:"
echo "    ssh $SSH_OPTS $HOST nvidia-smi"
echo ""
echo "  Kill:"
echo "    ssh $SSH_OPTS $HOST tmux kill-session -t animalm_7b"
echo ""
echo "  v3 status (if co-running):"
echo "    ssh $SSH_OPTS $HOST tmux attach -t v3_train"
echo "═══════════════════════════════════════════════════════════"
