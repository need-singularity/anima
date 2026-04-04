#!/usr/bin/env bash
# loop-cron.sh — launchd/cron wrapper for growth_loop.py --auto (single run)
#
# - flock prevents overlapping runs
# - log rotation keeps only last 1000 lines
# - exits silently on lock conflict (previous run still active)
set -euo pipefail

LOCK_FILE="$HOME/.growth/loop.lock"
LOG_FILE="$HOME/.growth/loop.log"
ANIMA_DIR="$HOME/Dev/anima"
PYTHON="/opt/homebrew/bin/python3"
SCRIPT="$ANIMA_DIR/anima/src/growth_loop.py"

# ── flock: skip if already running ──
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SKIP] previous run still active" >> "$LOG_FILE"
    exit 0
fi

# ── run growth loop ──
echo "$(date '+%Y-%m-%d %H:%M:%S') [START] growth_loop --auto" >> "$LOG_FILE"

cd "$ANIMA_DIR"
"$PYTHON" "$SCRIPT" --auto >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "$(date '+%Y-%m-%d %H:%M:%S') [END] exit=$EXIT_CODE" >> "$LOG_FILE"

# ── log rotation: keep last 1000 lines ──
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE")
    if [ "$LINE_COUNT" -gt 1200 ]; then
        tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp"
        mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
fi

exit 0
