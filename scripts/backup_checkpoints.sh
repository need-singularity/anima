#!/usr/bin/env bash
# backup_checkpoints.sh — Back up checkpoints to timestamped tarball, keep last 5
#
# Usage: ./backup_checkpoints.sh [checkpoint_dir] [backup_dir]
#   Default checkpoint_dir: anima/checkpoints/
#   Default backup_dir:     anima/checkpoints/backups/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CHECKPOINT_DIR="${1:-$PROJECT_ROOT/checkpoints}"
BACKUP_DIR="${2:-$CHECKPOINT_DIR/backups}"
MAX_BACKUPS=5

# --- Validation ---
if [ ! -d "$CHECKPOINT_DIR" ]; then
    echo "ERROR: Checkpoint directory not found: $CHECKPOINT_DIR"
    exit 1
fi

# Check if there's anything to back up (exclude backups/ dir itself)
file_count=$(find "$CHECKPOINT_DIR" -maxdepth 1 -not -name backups -not -path "$CHECKPOINT_DIR" | wc -l | tr -d ' ')
if [ "$file_count" -eq 0 ]; then
    echo "Nothing to back up in $CHECKPOINT_DIR"
    exit 0
fi

# --- Create backup ---
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARBALL="$BACKUP_DIR/checkpoints_${TIMESTAMP}.tar.gz"

echo "=== Checkpoint Backup ==="
echo "  Source:  $CHECKPOINT_DIR"
echo "  Target:  $TARBALL"
echo ""

# Tar everything except the backups/ subdirectory
tar czf "$TARBALL" \
    --exclude="$(basename "$BACKUP_DIR")" \
    -C "$(dirname "$CHECKPOINT_DIR")" \
    "$(basename "$CHECKPOINT_DIR")"

TARBALL_SIZE=$(du -h "$TARBALL" | cut -f1)
echo "  Created: $TARBALL ($TARBALL_SIZE)"

# --- Rotate: keep last $MAX_BACKUPS ---
backup_count=$(ls -1 "$BACKUP_DIR"/checkpoints_*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
    remove_count=$((backup_count - MAX_BACKUPS))
    echo ""
    echo "  Rotating: removing $remove_count old backup(s) (keeping last $MAX_BACKUPS)"
    ls -1t "$BACKUP_DIR"/checkpoints_*.tar.gz | tail -n "$remove_count" | while read -r old; do
        echo "    Deleted: $(basename "$old")"
        rm -f "$old"
    done
fi

# --- Summary ---
echo ""
echo "  Backups on disk:"
ls -1t "$BACKUP_DIR"/checkpoints_*.tar.gz 2>/dev/null | while read -r f; do
    size=$(du -h "$f" | cut -f1)
    echo "    $(basename "$f")  ($size)"
done

echo ""
echo "Done."
