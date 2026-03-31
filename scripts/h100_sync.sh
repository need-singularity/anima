#!/bin/bash
# Sync local code to H100 RunPod pod
# Usage: bash scripts/h100_sync.sh [--dry-run] [--verify-only]
#
# Transfer strategy (3-tier fallback):
#   1. rsync  — fast, incremental, delta transfer
#   2. scp    — file-by-file, works when rsync fails (read-only fs issue)
#   3. cat|ssh cat > — always works, last resort (pipe transfer)
#
# Reads SSH config from anima/config/runpod.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$REPO_ROOT/anima/config/runpod.json"

# ── Parse args ──
DRY_RUN=false
VERIFY_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --verify-only) VERIFY_ONLY=true ;;
  esac
done

# ── Load SSH config from runpod.json ──
if [ -f "$CONFIG" ]; then
  # Extract values using python (available on macOS, no jq dependency)
  SSH_KEY=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['ssh']['key'])")
  SSH_KEY="${SSH_KEY/#\~/$HOME}"
  SSH_CMD=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['ssh']['command'])")
  # Parse host and port from ssh command: ssh -i KEY -o ... root@HOST -p PORT
  HOST=$(echo "$SSH_CMD" | grep -oE 'root@[0-9.]+' | head -1)
  PORT=$(echo "$SSH_CMD" | grep -oE '\-p [0-9]+' | awk '{print $2}')
  DEST=$(python3 -c "import json; c=json.load(open('$CONFIG')); print(c['paths']['workspace'])")
  echo "[config] Loaded from $CONFIG"
  echo "  HOST=$HOST  PORT=$PORT  DEST=$DEST"
else
  echo "[config] runpod.json not found, using defaults"
  SSH_KEY=~/.runpod/ssh/RunPod-Key-Go
  HOST=root@216.243.220.230
  PORT=18038
  DEST=/workspace
fi

SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -p $PORT"

# ── Define sync groups ──
# Each group: LOCAL_DIR REMOTE_DIR INCLUDE_PATTERN LABEL
declare -a SYNC_GROUPS=(
  "$REPO_ROOT/anima/src/|$DEST/|*.py *.json|src/"
  "$REPO_ROOT/anima/config/|$DEST/config/|*|config/"
  "$REPO_ROOT/anima/training/train_v14.py|$DEST/train_v14.py|single|train_v14.py"
)

# ── Helper: collect files from a directory with includes ──
collect_files() {
  local dir="$1"
  local includes="$2"
  if [ "$includes" = "*" ]; then
    find "$dir" -maxdepth 3 -type f ! -name '*.pyc' ! -path '*__pycache__*' 2>/dev/null
  else
    for pat in $includes; do
      find "$dir" -maxdepth 3 -type f -name "$pat" ! -path '*__pycache__*' 2>/dev/null
    done
  fi
}

# ── Transfer method 1: rsync ──
try_rsync() {
  local src="$1" dst="$2" label="$3"
  echo "  [rsync] $label"
  if rsync -avz --progress \
    -e "ssh $SSH_OPTS" \
    --exclude='__pycache__/' --exclude='*.pyc' \
    "$src" "$dst" 2>&1; then
    return 0
  else
    echo "  [rsync] FAILED for $label"
    return 1
  fi
}

# ── Transfer method 2: scp ──
try_scp() {
  local src="$1" dst="$2" label="$3"
  echo "  [scp] $label"

  # Single file
  if [ -f "$src" ]; then
    if scp $SSH_OPTS "$src" "$HOST:$dst" 2>&1; then
      return 0
    else
      echo "  [scp] FAILED for $label"
      return 1
    fi
  fi

  # Directory: file-by-file
  local dir="$src"
  local base_dir="${dir%/}"
  local remote_base="${dst%/}"
  local count=0
  local failed=0

  # Ensure remote directory exists
  ssh $SSH_OPTS "$HOST" "mkdir -p '$remote_base'" 2>/dev/null || true

  while IFS= read -r file; do
    local rel="${file#$base_dir/}"
    local remote_dir
    remote_dir=$(dirname "$remote_base/$rel")
    ssh $SSH_OPTS "$HOST" "mkdir -p '$remote_dir'" 2>/dev/null || true
    if scp $SSH_OPTS "$file" "$HOST:$remote_base/$rel" 2>/dev/null; then
      count=$((count + 1))
    else
      failed=$((failed + 1))
    fi
  done < <(collect_files "$base_dir" "*")

  echo "  [scp] $count files transferred, $failed failed"
  [ "$failed" -eq 0 ] && return 0 || return 1
}

# ── Transfer method 3: cat | ssh cat > (always works) ──
try_pipe() {
  local src="$1" dst="$2" label="$3"
  echo "  [pipe] $label (cat | ssh cat >)"

  # Single file
  if [ -f "$src" ]; then
    ssh $SSH_OPTS "$HOST" "mkdir -p '$(dirname "$dst")'" 2>/dev/null || true
    if cat "$src" | ssh $SSH_OPTS "$HOST" "cat > '$dst'"; then
      return 0
    else
      echo "  [pipe] FAILED for $label"
      return 1
    fi
  fi

  # Directory: file-by-file
  local dir="${src%/}"
  local remote_base="${dst%/}"
  local count=0
  local failed=0

  while IFS= read -r file; do
    local rel="${file#$dir/}"
    local remote_path="$remote_base/$rel"
    ssh $SSH_OPTS "$HOST" "mkdir -p '$(dirname "$remote_path")'" 2>/dev/null || true
    if cat "$file" | ssh $SSH_OPTS "$HOST" "cat > '$remote_path'"; then
      count=$((count + 1))
    else
      failed=$((failed + 1))
    fi
  done < <(collect_files "$dir" "*")

  echo "  [pipe] $count files transferred, $failed failed"
  [ "$failed" -eq 0 ] && return 0 || return 1
}

# ── Transfer with 3-tier fallback ──
transfer() {
  local src="$1" dst="$2" label="$3"

  if $DRY_RUN; then
    echo "  [dry-run] Would transfer: $src -> $HOST:$dst"
    return 0
  fi

  # Tier 1: rsync
  if try_rsync "$src" "$HOST:$dst" "$label"; then
    return 0
  fi

  echo "  >> rsync failed, falling back to scp..."

  # Tier 2: scp
  if try_scp "$src" "$dst" "$label"; then
    return 0
  fi

  echo "  >> scp failed, falling back to pipe transfer..."

  # Tier 3: cat | ssh cat >
  if try_pipe "$src" "$dst" "$label"; then
    return 0
  fi

  echo "  [ERROR] All 3 transfer methods failed for $label"
  return 1
}

# ── MD5 verification ──
verify_md5() {
  local src="$1" dst="$2" label="$3"
  echo ""
  echo "[verify] $label — md5 comparison"

  local mismatches=0
  local checked=0

  # Single file
  if [ -f "$src" ]; then
    local local_md5
    local_md5=$(md5 -q "$src" 2>/dev/null || md5sum "$src" | awk '{print $1}')
    local remote_md5
    remote_md5=$(ssh $SSH_OPTS "$HOST" "md5sum '$dst' 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "MISSING")

    if [ "$local_md5" = "$remote_md5" ]; then
      echo "  OK  $(basename "$src")"
    else
      echo "  MISMATCH  $(basename "$src")  local=$local_md5  remote=$remote_md5"
      mismatches=$((mismatches + 1))
    fi
    checked=1
  else
    # Directory
    local dir="${src%/}"
    local remote_base="${dst%/}"

    while IFS= read -r file; do
      local rel="${file#$dir/}"
      local local_md5
      local_md5=$(md5 -q "$file" 2>/dev/null || md5sum "$file" | awk '{print $1}')
      local remote_md5
      remote_md5=$(ssh $SSH_OPTS "$HOST" "md5sum '$remote_base/$rel' 2>/dev/null | awk '{print \$1}'" 2>/dev/null || echo "MISSING")

      if [ "$local_md5" = "$remote_md5" ]; then
        checked=$((checked + 1))
      else
        echo "  MISMATCH  $rel  local=$local_md5  remote=$remote_md5"
        mismatches=$((mismatches + 1))
        checked=$((checked + 1))
      fi
    done < <(collect_files "$dir" "*")
  fi

  if [ "$mismatches" -eq 0 ]; then
    echo "  All $checked files verified OK"
  else
    echo "  WARNING: $mismatches/$checked files mismatched!"
  fi
  return "$mismatches"
}

# ── Main ──
echo "========================================"
echo " H100 Sync — 3-tier fallback + md5"
echo "========================================"
echo ""

TOTAL_ERRORS=0

if ! $VERIFY_ONLY; then
  # Transfer: src/
  echo "[1/3] Syncing src/ to H100..."
  transfer "$REPO_ROOT/anima/src/" "$DEST/" "src/" || TOTAL_ERRORS=$((TOTAL_ERRORS + 1))

  # Transfer: config/
  echo ""
  echo "[2/3] Syncing config/..."
  transfer "$REPO_ROOT/anima/config/" "$DEST/config/" "config/" || TOTAL_ERRORS=$((TOTAL_ERRORS + 1))

  # Transfer: train_v14.py
  echo ""
  echo "[3/3] Syncing train_v14.py..."
  transfer "$REPO_ROOT/anima/training/train_v14.py" "$DEST/train_v14.py" "train_v14.py" || TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
fi

# MD5 verification (sample key files)
echo ""
echo "========================================"
echo " MD5 Verification"
echo "========================================"

VERIFY_ERRORS=0
verify_md5 "$REPO_ROOT/anima/src/consciousness_engine.py" "$DEST/consciousness_engine.py" "consciousness_engine.py" || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
verify_md5 "$REPO_ROOT/anima/src/trinity.py" "$DEST/trinity.py" "trinity.py" || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
verify_md5 "$REPO_ROOT/anima/src/decoder_v2.py" "$DEST/decoder_v2.py" "decoder_v2.py" || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
verify_md5 "$REPO_ROOT/anima/training/train_v14.py" "$DEST/train_v14.py" "train_v14.py" || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
verify_md5 "$REPO_ROOT/anima/config/consciousness_laws.json" "$DEST/config/consciousness_laws.json" "consciousness_laws.json" || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))

echo ""
echo "========================================"
if [ "$TOTAL_ERRORS" -eq 0 ] && [ "$VERIFY_ERRORS" -eq 0 ]; then
  echo " DONE — All files synced and verified"
else
  echo " DONE — $TOTAL_ERRORS transfer errors, $VERIFY_ERRORS verification mismatches"
fi
echo " Target: $HOST:$DEST"
echo "========================================"
