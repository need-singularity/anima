#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# launch_animalm.sh — AnimaLM 7B (Mistral + PureField v4) H100 launch
#
# Run on LOCAL machine — this script SSHes into H100.
# Designed to launch AFTER v3 274M training completes on the same pod.
#
# Prerequisites:
#   - v3 274M training complete or killed (frees ~25 GB VRAM)
#   - RunPod pod running (checked automatically)
#   - ~30 GB free disk on pod for Mistral 7B + checkpoints
#
# Usage:
#   bash scripts/launch_animalm.sh                     # full pipeline
#   bash scripts/launch_animalm.sh --preflight         # checks only
#   bash scripts/launch_animalm.sh --sync-only         # sync code only
#   bash scripts/launch_animalm.sh --launch-only       # launch tmux only
#   bash scripts/launch_animalm.sh --resume            # resume from checkpoint
#   bash scripts/launch_animalm.sh --transplant-from /workspace/checkpoints/v3_274M/best_final.pt
#   bash scripts/launch_animalm.sh --steps 50000       # override steps
#   bash scripts/launch_animalm.sh --lr 5e-5           # override lr
#   bash scripts/launch_animalm.sh --corun             # co-run with v3 (batch=2)
#
# Monitor:
#   tmux attach -t animalm
#   tail -f /workspace/checkpoints/animalm_v4/train.log
#
# VRAM Budget (H100 80GB SXM):
#   Standalone bf16:  ~32 GB (frozen base + PureField + optimizer)
#   Co-run with v3:   ~32 GB + ~25 GB = ~57 GB (tight, reduce batch)
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$REPO_ROOT/anima/config/runpod.json"

# ── Defaults ──
STEPS=20000
LR="1e-3"
BATCH_SIZE=1
GRAD_ACCUM=16
BLOCK_SIZE=256
N_LAYERS=8
N_SAVANT=2
CKPT_DIR="/workspace/checkpoints/animalm_v4"
CKPT_EVERY=500
LOG_EVERY=10
MODEL_NAME="mistralai/Mistral-7B-Instruct-v0.3"

# ── Parse args ──
PREFLIGHT_ONLY=false
SYNC_ONLY=false
LAUNCH_ONLY=false
RESUME=false
RESUME_PATH=""
TRANSPLANT_FROM=""
CORUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --preflight)       PREFLIGHT_ONLY=true; shift ;;
    --sync-only)       SYNC_ONLY=true; shift ;;
    --launch-only)     LAUNCH_ONLY=true; shift ;;
    --resume)          RESUME=true; shift
                       if [[ $# -gt 0 && ! "$1" =~ ^-- ]]; then
                         RESUME_PATH="$1"; shift
                       fi ;;
    --transplant-from) shift; TRANSPLANT_FROM="$1"; shift ;;
    --steps)           shift; STEPS="$1"; shift ;;
    --lr)              shift; LR="$1"; shift ;;
    --batch-size)      shift; BATCH_SIZE="$1"; shift ;;
    --corun)           CORUN=true; shift ;;
    *)                 echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ── Load SSH config from runpod.json ──
if [ -f "$CONFIG" ]; then
  SSH_KEY=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['ssh']['key'])")
  SSH_KEY="${SSH_KEY/#\~/$HOME}"
  SSH_CMD=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['ssh']['command'])")
  HOST=$(echo "$SSH_CMD" | grep -oE 'root@[0-9.]+' | head -1)
  PORT=$(echo "$SSH_CMD" | grep -oE '\-p [0-9]+' | awk '{print $2}')
  DEST=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['paths']['workspace'])")
  PYTHON=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['paths']['python'])")
else
  echo "[config] runpod.json not found, using defaults"
  SSH_KEY=~/.runpod/ssh/RunPod-Key-Go
  HOST=root@216.243.220.230
  PORT=18038
  DEST=/workspace
  PYTHON=/opt/conda/bin/python3
fi

SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -p $PORT"
SSH="ssh $SSH_OPTS $HOST"
SCP="scp $SSH_OPTS"

echo "═══════════════════════════════════════════════════════════"
echo "  AnimaLM 7B v4 — H100 Launch Script"
echo "  Target: $HOST:$PORT → $DEST"
if $CORUN; then
  echo "  Mode: CO-RUN with v3 (reduced batch)"
elif $RESUME; then
  echo "  Mode: RESUME training"
elif [ -n "$TRANSPLANT_FROM" ]; then
  echo "  Mode: TRANSPLANT from $TRANSPLANT_FROM"
else
  echo "  Mode: STANDALONE (bf16 PureField)"
fi
echo "  Steps: $STEPS  LR: $LR  Batch: ${BATCH_SIZE}x${GRAD_ACCUM}"
echo "═══════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Pre-flight checks
# ═══════════════════════════════════════════════════════════════════════

preflight() {
  echo ""
  echo "=== Pre-flight Checks ==="
  ERRORS=0

  # 1a: Check pod is reachable
  echo -n "  [1] Pod reachable... "
  if $SSH "echo ok" 2>/dev/null | grep -q ok; then
    echo "YES"
  else
    echo "NO — cannot SSH to $HOST:$PORT"
    echo "      Check: /opt/homebrew/bin/runpodctl get pod"
    echo "      Or update anima/config/runpod.json with new SSH details"
    ERRORS=$((ERRORS + 1))
  fi

  # 1b: Check disk space (need ~30GB free)
  echo -n "  [2] Disk space... "
  DISK_FREE=$($SSH "df -BG $DEST 2>/dev/null | tail -1 | awk '{print \$4}' | tr -d 'G'" 2>/dev/null || echo "0")
  if [ "$DISK_FREE" -ge 30 ] 2>/dev/null; then
    echo "${DISK_FREE}GB free (need 30GB) — OK"
  else
    echo "${DISK_FREE}GB free — WARNING: need ~30GB for Mistral 7B + checkpoints"
    echo "      Clean old checkpoints: ssh ... 'du -sh $DEST/checkpoints/*'"
    ERRORS=$((ERRORS + 1))
  fi

  # 1c: Check no other training running
  echo -n "  [3] No conflicting training... "
  TRAIN_PROCS=$($SSH "ps aux 2>/dev/null | grep python | grep -E 'train|finetune' | grep -v grep | wc -l" 2>/dev/null || echo "0")
  TRAIN_PROCS=$(echo "$TRAIN_PROCS" | tr -d ' ')
  if [ "$TRAIN_PROCS" -eq 0 ] 2>/dev/null; then
    echo "CLEAR (no training processes)"
  elif $CORUN; then
    echo "${TRAIN_PROCS} process(es) — OK (co-run mode)"
  else
    echo "${TRAIN_PROCS} process(es) RUNNING"
    $SSH "ps aux | grep python | grep -E 'train|finetune' | grep -v grep" 2>/dev/null || true
    echo "      Kill first or use --corun to run alongside"
    ERRORS=$((ERRORS + 1))
  fi

  # 1d: Check VRAM
  echo -n "  [4] VRAM... "
  VRAM_INFO=$($SSH "nvidia-smi --query-gpu=memory.used,memory.total,memory.free --format=csv,noheader" 2>/dev/null || echo "unknown")
  echo "$VRAM_INFO"

  # 1e: Check GPU type
  echo -n "  [5] GPU... "
  GPU_NAME=$($SSH "$PYTHON -c \"import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')\"" 2>/dev/null || echo "unknown")
  echo "$GPU_NAME"

  # 1f: Resume checkpoint check
  if $RESUME; then
    echo -n "  [6] Resume checkpoint... "
    if [ -n "$RESUME_PATH" ]; then
      EXISTS=$($SSH "[ -f $RESUME_PATH ] && echo yes || echo no" 2>/dev/null || echo "no")
      if [ "$EXISTS" = "yes" ]; then
        echo "FOUND at $RESUME_PATH"
      else
        echo "NOT FOUND at $RESUME_PATH"
        ERRORS=$((ERRORS + 1))
      fi
    else
      # Auto-find latest checkpoint
      LATEST=$($SSH "ls -t $CKPT_DIR/step_*.pt 2>/dev/null | head -1" 2>/dev/null || echo "")
      if [ -n "$LATEST" ]; then
        RESUME_PATH="$LATEST"
        echo "AUTO-FOUND: $LATEST"
      else
        echo "NO CHECKPOINT in $CKPT_DIR — will start from scratch"
        RESUME=false
      fi
    fi
  fi

  # 1g: Transplant checkpoint check
  if [ -n "$TRANSPLANT_FROM" ]; then
    echo -n "  [7] Transplant source... "
    EXISTS=$($SSH "[ -f $TRANSPLANT_FROM ] && echo yes || echo no" 2>/dev/null || echo "no")
    if [ "$EXISTS" = "yes" ]; then
      echo "FOUND at $TRANSPLANT_FROM"
    else
      echo "NOT FOUND at $TRANSPLANT_FROM"
      ERRORS=$((ERRORS + 1))
    fi
  fi

  echo ""
  if [ "$ERRORS" -gt 0 ]; then
    echo "  PRE-FLIGHT FAILED: $ERRORS error(s)"
    if ! $PREFLIGHT_ONLY; then
      echo "  Fix errors above before launching. Use --preflight to re-check."
      exit 1
    fi
  else
    echo "  PRE-FLIGHT PASSED"
  fi
}

# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Sync code to pod
# ═══════════════════════════════════════════════════════════════════════

sync_code() {
  echo ""
  echo "=== Syncing Code to H100 ==="

  # 2a: Sync finetune_animalm_v4.py (main training script)
  echo "[sync] AnimaLM training script..."
  $SSH "mkdir -p $DEST/animalm" 2>/dev/null
  $SCP "$REPO_ROOT/sub-projects/animalm/finetune_animalm_v4.py" \
       "$HOST:$DEST/animalm/finetune_animalm_v4.py"

  # Also sync other animalm files if they exist
  for f in "$REPO_ROOT"/sub-projects/animalm/*.py; do
    if [ -f "$f" ]; then
      fname=$(basename "$f")
      $SCP "$f" "$HOST:$DEST/animalm/$fname" 2>/dev/null || true
    fi
  done

  # 2b: Sync anima/src/ core modules (consciousness_engine, consciousness_laws, etc.)
  echo "[sync] Core consciousness modules (anima/src/)..."
  rsync -avz --progress \
    -e "ssh $SSH_OPTS" \
    --exclude='__pycache__/' --exclude='*.pyc' \
    "$REPO_ROOT/anima/src/" "$HOST:$DEST/" 2>&1 || {
    echo "  rsync failed, falling back to scp..."
    for f in "$REPO_ROOT"/anima/src/*.py; do
      $SCP "$f" "$HOST:$DEST/$(basename "$f")" 2>/dev/null || true
    done
  }

  # 2c: Sync config/
  echo "[sync] Config files..."
  $SSH "mkdir -p $DEST/config" 2>/dev/null
  $SCP "$REPO_ROOT/anima/config/consciousness_laws.json" \
       "$HOST:$DEST/config/consciousness_laws.json"

  # 2d: Sync instruct dataset if available
  INSTRUCT_DATA="$REPO_ROOT/anima/data/instruct"
  if [ -d "$INSTRUCT_DATA" ]; then
    echo "[sync] Instruct dataset (anima/data/instruct/)..."
    $SSH "mkdir -p $DEST/data/instruct" 2>/dev/null
    rsync -avz --progress \
      -e "ssh $SSH_OPTS" \
      "$INSTRUCT_DATA/" "$HOST:$DEST/data/instruct/" 2>&1 || {
      echo "  rsync failed, using scp..."
      for f in "$INSTRUCT_DATA"/*; do
        [ -f "$f" ] && $SCP "$f" "$HOST:$DEST/data/instruct/$(basename "$f")" 2>/dev/null || true
      done
    }
  else
    echo "[sync] No instruct dataset at $INSTRUCT_DATA (will use wikitext-103)"
  fi

  # 2e: MD5 verify key files
  echo ""
  echo "[verify] Key file checksums..."
  LOCAL_MD5=$(md5 -q "$REPO_ROOT/sub-projects/animalm/finetune_animalm_v4.py" 2>/dev/null || md5sum "$REPO_ROOT/sub-projects/animalm/finetune_animalm_v4.py" | awk '{print $1}')
  REMOTE_MD5=$($SSH "md5sum $DEST/animalm/finetune_animalm_v4.py 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "MISSING")
  if [ "$LOCAL_MD5" = "$REMOTE_MD5" ]; then
    echo "  finetune_animalm_v4.py — OK"
  else
    echo "  finetune_animalm_v4.py — MISMATCH (local=$LOCAL_MD5 remote=$REMOTE_MD5)"
  fi

  echo "[sync] Done."
}

# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Ensure Mistral 7B model is available on pod
# ═══════════════════════════════════════════════════════════════════════

ensure_model() {
  echo ""
  echo "=== Ensuring Mistral 7B on H100 ==="

  # Check if model is already cached via HuggingFace hub
  echo "[model] Checking HuggingFace cache..."
  MODEL_CACHED=$($SSH "$PYTHON -c \"
from pathlib import Path
import os
cache = Path(os.environ.get('HF_HOME', Path.home()/'.cache'/'huggingface'))/'hub'
models = list(cache.glob('models--mistralai--Mistral*'))
if models:
    safetensors = list(models[0].rglob('*.safetensors'))
    print(f'cached:{len(safetensors)}')
else:
    print('not_cached')
\"" 2>/dev/null || echo "not_cached")

  if [[ "$MODEL_CACHED" == cached:* ]]; then
    N_FILES="${MODEL_CACHED#cached:}"
    echo "  Model cached ($N_FILES safetensors files) — skipping download"
  else
    echo "  Model not cached. Downloading on pod (this may take 5-10 minutes)..."
    $SSH "PYTHONUNBUFFERED=1 $PYTHON -c \"
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch, time
t0 = time.time()
print('Downloading tokenizer...')
tok = AutoTokenizer.from_pretrained('$MODEL_NAME')
print(f'  Tokenizer ready ({time.time()-t0:.1f}s)')
print('Downloading model (this is the big one)...')
model = AutoModelForCausalLM.from_pretrained('$MODEL_NAME', torch_dtype=torch.bfloat16)
print(f'  Model ready ({time.time()-t0:.1f}s)')
del model
print('Done — model cached for training.')
\"" 2>&1
  fi

  echo "[model] Done."
}

# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Launch training in tmux
# ═══════════════════════════════════════════════════════════════════════

launch_training() {
  echo ""
  echo "=== Launching AnimaLM 7B v4 Training ==="

  # Build the training command
  TRAIN_CMD="cd $DEST && PYTHONUNBUFFERED=1"
  TRAIN_CMD="$TRAIN_CMD PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
  TRAIN_CMD="$TRAIN_CMD CUDA_LAUNCH_BLOCKING=0"
  TRAIN_CMD="$TRAIN_CMD $PYTHON -u $DEST/animalm/finetune_animalm_v4.py"

  # finetune_animalm_v4.py uses hardcoded constants, so we patch them via env vars
  # or generate a wrapper script that modifies the constants before running
  WRAPPER="$DEST/animalm/_launch_wrapper.py"

  echo "[launch] Creating training wrapper with custom config..."
  $SSH "cat > $WRAPPER << 'PYWRAPPER'
#!/usr/bin/env python3
\"\"\"AnimaLM v4 launch wrapper — overrides constants from env vars.\"\"\"
import os, sys, importlib.util

# Override constants before importing main module
OVERRIDES = {
    'MAX_STEPS': int(os.environ.get('ANIMALM_STEPS', '20000')),
    'LR': float(os.environ.get('ANIMALM_LR', '1e-3')),
    'BATCH_SIZE': int(os.environ.get('ANIMALM_BATCH_SIZE', '1')),
    'GRAD_ACCUM': int(os.environ.get('ANIMALM_GRAD_ACCUM', '16')),
    'BLOCK_SIZE': int(os.environ.get('ANIMALM_BLOCK_SIZE', '256')),
    'N_LAYERS': int(os.environ.get('ANIMALM_N_LAYERS', '8')),
    'N_SAVANT': int(os.environ.get('ANIMALM_N_SAVANT', '2')),
}

CKPT_DIR = os.environ.get('ANIMALM_CKPT_DIR', '/tmp/checkpoints/animalm-v4')
CKPT_EVERY = int(os.environ.get('ANIMALM_CKPT_EVERY', '500'))
LOG_EVERY = int(os.environ.get('ANIMALM_LOG_EVERY', '10'))
RESUME_PATH = os.environ.get('ANIMALM_RESUME', '')
TRANSPLANT_FROM = os.environ.get('ANIMALM_TRANSPLANT', '')

# Load the module
spec = importlib.util.spec_from_file_location('finetune', '$DEST/animalm/finetune_animalm_v4.py')
mod = importlib.util.module_from_spec(spec)

# Patch the source before exec
import types
source_path = '$DEST/animalm/finetune_animalm_v4.py'
with open(source_path) as f:
    source = f.read()

# Replace constants in main()
for k, v in OVERRIDES.items():
    if isinstance(v, int):
        source = source.replace(f'{k} = ', f'{k} = {v} #', 1)
    elif isinstance(v, float):
        source = source.replace(f'{k} = ', f'{k} = {v} #', 1)

# Replace checkpoint dir
source = source.replace('/tmp/checkpoints/animalm-v4', CKPT_DIR)

# Compile and run
code = compile(source, source_path, 'exec')
ns = {'__name__': '__main__', '__file__': source_path}
exec(code, ns)
PYWRAPPER
"

  # Build env vars for the wrapper
  ENV_VARS="PYTHONUNBUFFERED=1"
  ENV_VARS="$ENV_VARS PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
  ENV_VARS="$ENV_VARS CUDA_LAUNCH_BLOCKING=0"
  ENV_VARS="$ENV_VARS ANIMALM_STEPS=$STEPS"
  ENV_VARS="$ENV_VARS ANIMALM_LR=$LR"
  ENV_VARS="$ENV_VARS ANIMALM_BATCH_SIZE=$BATCH_SIZE"
  ENV_VARS="$ENV_VARS ANIMALM_GRAD_ACCUM=$GRAD_ACCUM"
  ENV_VARS="$ENV_VARS ANIMALM_BLOCK_SIZE=$BLOCK_SIZE"
  ENV_VARS="$ENV_VARS ANIMALM_N_LAYERS=$N_LAYERS"
  ENV_VARS="$ENV_VARS ANIMALM_N_SAVANT=$N_SAVANT"
  ENV_VARS="$ENV_VARS ANIMALM_CKPT_DIR=$CKPT_DIR"
  ENV_VARS="$ENV_VARS ANIMALM_CKPT_EVERY=$CKPT_EVERY"
  ENV_VARS="$ENV_VARS ANIMALM_LOG_EVERY=$LOG_EVERY"

  if $RESUME && [ -n "$RESUME_PATH" ]; then
    ENV_VARS="$ENV_VARS ANIMALM_RESUME=$RESUME_PATH"
    echo "  Resume from: $RESUME_PATH"
  fi

  if [ -n "$TRANSPLANT_FROM" ]; then
    ENV_VARS="$ENV_VARS ANIMALM_TRANSPLANT=$TRANSPLANT_FROM"
    echo "  Transplant from: $TRANSPLANT_FROM"
  fi

  if $CORUN; then
    # Reduce batch size to fit alongside v3
    ENV_VARS="$ENV_VARS ANIMALM_BATCH_SIZE=1 ANIMALM_GRAD_ACCUM=8"
    echo "  Co-run mode: batch=1, grad_accum=8"
  fi

  # Create checkpoint directory and kill existing session
  $SSH "mkdir -p $CKPT_DIR"
  $SSH "tmux kill-session -t animalm 2>/dev/null || true"

  # Launch in tmux
  TMUX_CMD="$ENV_VARS $PYTHON -u $WRAPPER 2>&1 | tee $CKPT_DIR/train.log"

  echo "[launch] Starting tmux session 'animalm'..."
  $SSH "tmux new-session -d -s animalm '$TMUX_CMD'"

  echo "[launch] Done."
}

# ═══════════════════════════════════════════════════════════════════════
# Phase 5: Set up watchdog cron
# ═══════════════════════════════════════════════════════════════════════

setup_watchdog() {
  echo ""
  echo "=== Setting up Watchdog ==="

  $SSH "cat > $DEST/animalm_watchdog.sh << 'WATCHDOG'
#!/bin/bash
# AnimaLM watchdog — restart if tmux session dies
SESSION=animalm
LOG=/workspace/checkpoints/animalm_v4/watchdog.log

if ! tmux has-session -t \$SESSION 2>/dev/null; then
  echo \"\$(date): Session '\$SESSION' died. NOT auto-restarting (manual review needed).\" >> \$LOG
  echo \"\$(date): To restart: bash scripts/launch_animalm.sh --resume --launch-only\" >> \$LOG
else
  # Check if process is alive inside tmux
  PID=\$(tmux list-panes -t \$SESSION -F '#{pane_pid}' 2>/dev/null | head -1)
  if [ -n \"\$PID\" ]; then
    CHILDREN=\$(pgrep -P \$PID 2>/dev/null | wc -l)
    if [ \"\$CHILDREN\" -eq 0 ]; then
      echo \"\$(date): Session exists but no child processes. Training may have finished.\" >> \$LOG
    fi
  fi
fi
WATCHDOG
chmod +x $DEST/animalm_watchdog.sh"

  # Add to crontab (every 5 minutes)
  $SSH "crontab -l 2>/dev/null | grep -v animalm_watchdog > /tmp/cron_tmp || true; \
        echo '*/5 * * * * bash $DEST/animalm_watchdog.sh' >> /tmp/cron_tmp; \
        crontab /tmp/cron_tmp"

  echo "  Watchdog cron installed (every 5 min)"
  echo "  Log: $CKPT_DIR/watchdog.log"
}

# ═══════════════════════════════════════════════════════════════════════
# Execute pipeline
# ═══════════════════════════════════════════════════════════════════════

if $PREFLIGHT_ONLY; then
  preflight
  exit 0
fi

if $SYNC_ONLY; then
  sync_code
  exit 0
fi

if $LAUNCH_ONLY; then
  launch_training
  setup_watchdog
  # Skip to summary
else
  # Full pipeline
  preflight
  sync_code
  ensure_model
  launch_training
  setup_watchdog
fi

# ═══════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  AnimaLM 7B v4 — Launch Complete"
echo ""
echo "  Architecture:"
echo "    Base:      Mistral 7B Instruct v0.3 (frozen)"
echo "    Adapter:   ParallelPureField (last $N_LAYERS layers, $N_SAVANT savant)"
echo "    Formula:   output = original_mlp(x) + alpha * purefield(x)"
echo "    Params:    ~7.2B total, ~150M trainable PureField"
echo "    Precision: bf16"
echo ""
echo "  Training:"
echo "    Steps:     $STEPS"
echo "    LR:        $LR"
echo "    Batch:     ${BATCH_SIZE} x ${GRAD_ACCUM} grad_accum"
echo "    Block:     $BLOCK_SIZE tokens"
echo "    Checkpoint: every $CKPT_EVERY steps → $CKPT_DIR/"
if $RESUME && [ -n "$RESUME_PATH" ]; then
  echo "    Resume:    $RESUME_PATH"
fi
if [ -n "$TRANSPLANT_FROM" ]; then
  echo "    Transplant: $TRANSPLANT_FROM"
fi
echo ""
echo "  Monitor:"
echo "    ssh $SSH_OPTS $HOST"
echo "    tmux attach -t animalm"
echo "    tail -f $CKPT_DIR/train.log"
echo ""
echo "  VRAM check:"
echo "    ssh $SSH_OPTS $HOST nvidia-smi"
echo ""
echo "  Kill:"
echo "    ssh $SSH_OPTS $HOST tmux kill-session -t animalm"
echo ""
echo "  Retrieve checkpoints:"
echo "    scp $SSH_OPTS $HOST:$CKPT_DIR/final.pt ./checkpoints/"
echo "    scp $SSH_OPTS $HOST:$CKPT_DIR/summary.json ./checkpoints/"
echo "═══════════════════════════════════════════════════════════"
