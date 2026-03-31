#!/usr/bin/env bash
# r2_backup.sh — Checkpoint backup to Cloudflare R2
#
# Usage:
#   bash scripts/r2_backup.sh                          # upload v14_128c_final (all)
#   bash scripts/r2_backup.sh --best                   # best.pt only
#   bash scripts/r2_backup.sh --version v14_federated  # specific version
#   bash scripts/r2_backup.sh --list                   # list R2 contents
#   bash scripts/r2_backup.sh --prune --keep 3         # keep latest 3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

# Default: v14_128c_final
VERSION="${VERSION:-v14_128c_final}"
BEST_ONLY=""
LIST_MODE=""
PRUNE_MODE=""
KEEP=3

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version|-v) VERSION="$2"; shift 2 ;;
        --best|-b) BEST_ONLY="--best"; shift ;;
        --list|-l) LIST_MODE="1"; shift ;;
        --prune) PRUNE_MODE="1"; shift ;;
        --keep) KEEP="$2"; shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

echo "=== Anima R2 Checkpoint Backup ==="
echo "Root: $ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -n "$LIST_MODE" ]]; then
    python3 "$SCRIPT_DIR/r2_upload.py" --list --prefix checkpoints/
    exit 0
fi

if [[ -n "$PRUNE_MODE" ]]; then
    python3 "$SCRIPT_DIR/r2_upload.py" --prune --keep "$KEEP"
    exit 0
fi

# Check checkpoint exists
CKPT_DIR="$ROOT/anima/checkpoints/$VERSION"
if [[ ! -d "$CKPT_DIR" ]]; then
    echo "ERROR: Checkpoint dir not found: $CKPT_DIR"
    echo "Available:"
    ls -d "$ROOT/anima/checkpoints"/*/ 2>/dev/null || echo "  (none)"
    exit 1
fi

echo "Checkpoint: $VERSION"
echo "Files:"
ls -lh "$CKPT_DIR"/*.pt 2>/dev/null || echo "  (no .pt files)"
echo ""

# Upload
python3 "$SCRIPT_DIR/r2_upload.py" --checkpoint "$VERSION" $BEST_ONLY

echo ""
echo "=== Backup complete ==="
echo "Verify with: bash scripts/r2_backup.sh --list"
