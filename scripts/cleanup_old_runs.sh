#!/usr/bin/env bash
# cleanup_old_runs.sh — Find and remove stale logs, .tmp files, __pycache__ dirs
#
# Usage: ./cleanup_old_runs.sh [--confirm]
#   Without --confirm: dry run (shows what would be deleted)
#   With --confirm:    actually deletes
#
# Protected directories (never touched): .git, data/, checkpoints/, models/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CONFIRM=false
if [ "${1:-}" = "--confirm" ]; then
    CONFIRM=true
fi

echo "=== Cleanup Old Runs ==="
echo "  Root: $PROJECT_ROOT"
echo "  Mode: $( $CONFIRM && echo 'DELETE' || echo 'DRY RUN (use --confirm to delete)' )"
echo ""

TOTAL_SIZE=0

# Helper: accumulate size in bytes
add_size() {
    local bytes
    bytes=$(du -sk "$1" 2>/dev/null | cut -f1)
    TOTAL_SIZE=$((TOTAL_SIZE + bytes))
}

# --- 1. __pycache__ directories ---
echo "--- __pycache__ directories ---"
pycache_count=0
while IFS= read -r -d '' dir; do
    size=$(du -sh "$dir" 2>/dev/null | cut -f1)
    echo "  $dir  ($size)"
    add_size "$dir"
    pycache_count=$((pycache_count + 1))
    if $CONFIRM; then
        rm -rf "$dir"
    fi
done < <(find "$PROJECT_ROOT" \
    -path "$PROJECT_ROOT/.git" -prune -o \
    -path "$PROJECT_ROOT/data" -prune -o \
    -path "$PROJECT_ROOT/checkpoints" -prune -o \
    -path "$PROJECT_ROOT/models" -prune -o \
    -name "__pycache__" -type d -print0)

if [ "$pycache_count" -eq 0 ]; then
    echo "  (none found)"
fi
echo ""

# --- 2. Stale .tmp files (older than 1 day) ---
echo "--- Stale .tmp files (>1 day old) ---"
tmp_count=0
while IFS= read -r -d '' f; do
    size=$(du -sh "$f" 2>/dev/null | cut -f1)
    echo "  $f  ($size)"
    add_size "$f"
    tmp_count=$((tmp_count + 1))
    if $CONFIRM; then
        rm -f "$f"
    fi
done < <(find "$PROJECT_ROOT" \
    -path "$PROJECT_ROOT/.git" -prune -o \
    -path "$PROJECT_ROOT/data" -prune -o \
    -path "$PROJECT_ROOT/checkpoints" -prune -o \
    -path "$PROJECT_ROOT/models" -prune -o \
    -name "*.tmp" -type f -mtime +1 -print0)

if [ "$tmp_count" -eq 0 ]; then
    echo "  (none found)"
fi
echo ""

# --- 3. Old log files (>7 days) ---
echo "--- Old log files (>7 days) ---"
log_count=0
while IFS= read -r -d '' f; do
    size=$(du -sh "$f" 2>/dev/null | cut -f1)
    echo "  $f  ($size)"
    add_size "$f"
    log_count=$((log_count + 1))
    if $CONFIRM; then
        rm -f "$f"
    fi
done < <(find "$PROJECT_ROOT" \
    -path "$PROJECT_ROOT/.git" -prune -o \
    -path "$PROJECT_ROOT/data" -prune -o \
    -path "$PROJECT_ROOT/checkpoints" -prune -o \
    -path "$PROJECT_ROOT/models" -prune -o \
    \( -name "*.log" -o -name "*.log.*" \) -type f -mtime +7 -print0)

if [ "$log_count" -eq 0 ]; then
    echo "  (none found)"
fi
echo ""

# --- 4. .pyc files outside __pycache__ ---
echo "--- Stray .pyc files ---"
pyc_count=0
while IFS= read -r -d '' f; do
    size=$(du -sh "$f" 2>/dev/null | cut -f1)
    echo "  $f  ($size)"
    add_size "$f"
    pyc_count=$((pyc_count + 1))
    if $CONFIRM; then
        rm -f "$f"
    fi
done < <(find "$PROJECT_ROOT" \
    -path "$PROJECT_ROOT/.git" -prune -o \
    -path "$PROJECT_ROOT/data" -prune -o \
    -path "$PROJECT_ROOT/checkpoints" -prune -o \
    -path "$PROJECT_ROOT/models" -prune -o \
    -path "*/__pycache__" -prune -o \
    -name "*.pyc" -type f -print0)

if [ "$pyc_count" -eq 0 ]; then
    echo "  (none found)"
fi
echo ""

# --- Summary ---
total_items=$((pycache_count + tmp_count + log_count + pyc_count))
total_human=$(echo "$TOTAL_SIZE" | awk '{
    if ($1 >= 1048576) printf "%.1f GB", $1/1048576;
    else if ($1 >= 1024) printf "%.1f MB", $1/1024;
    else printf "%d KB", $1;
}')

echo "=== Summary ==="
echo "  __pycache__: $pycache_count dirs"
echo "  .tmp files:  $tmp_count files"
echo "  Old logs:    $log_count files"
echo "  Stray .pyc:  $pyc_count files"
echo "  Total:       $total_items items (~${total_human})"
echo ""

if ! $CONFIRM && [ "$total_items" -gt 0 ]; then
    echo "Run with --confirm to delete these items."
fi

echo "Done."
