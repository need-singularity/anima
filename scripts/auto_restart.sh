#!/usr/bin/env bash
# auto_restart.sh — Monitor and restart a process on crash (max 5 restarts)
#
# Usage: ./auto_restart.sh "python3 anima_unified.py --web"
#        ./auto_restart.sh "python3 anima/run.py --web" [max_restarts]
#
# Logs restart events to auto_restart.log in the script directory.
# Sends SIGTERM on Ctrl+C to the child process cleanly.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 \"<command>\" [max_restarts]"
    echo ""
    echo "Examples:"
    echo "  $0 \"python3 anima_unified.py --web\""
    echo "  $0 \"python3 anima/run.py --web\" 10"
    exit 1
fi

COMMAND="$1"
MAX_RESTARTS="${2:-5}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGFILE="$SCRIPT_DIR/auto_restart.log"
RESTART_COUNT=0
CHILD_PID=""

# --- Cleanup on exit ---
cleanup() {
    echo ""
    log_event "Received shutdown signal. Stopping child process..."
    if [ -n "$CHILD_PID" ] && kill -0 "$CHILD_PID" 2>/dev/null; then
        kill -TERM "$CHILD_PID" 2>/dev/null
        wait "$CHILD_PID" 2>/dev/null || true
    fi
    log_event "Auto-restart stopped. Total restarts: $RESTART_COUNT"
    exit 0
}

trap cleanup SIGINT SIGTERM

# --- Logging ---
log_event() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOGFILE"
}

# --- Main loop ---
echo "=== Auto Restart ==="
echo "  Command:       $COMMAND"
echo "  Max restarts:  $MAX_RESTARTS"
echo "  Log file:      $LOGFILE"
echo ""

log_event "Starting auto-restart for: $COMMAND"

while true; do
    log_event "Launching process (restart #$RESTART_COUNT)..."

    # Run the command in the background so we can track its PID
    eval "$COMMAND" &
    CHILD_PID=$!

    log_event "Process started with PID $CHILD_PID"

    # Wait for the process to finish
    set +e
    wait "$CHILD_PID"
    EXIT_CODE=$?
    set -e
    CHILD_PID=""

    # Exit code 0 = clean shutdown, don't restart
    if [ "$EXIT_CODE" -eq 0 ]; then
        log_event "Process exited cleanly (code 0). Not restarting."
        break
    fi

    # Signal-killed (128+signal) by us = don't restart
    if [ "$EXIT_CODE" -eq 143 ] || [ "$EXIT_CODE" -eq 130 ]; then
        log_event "Process killed by signal (code $EXIT_CODE). Not restarting."
        break
    fi

    RESTART_COUNT=$((RESTART_COUNT + 1))
    log_event "Process crashed with exit code $EXIT_CODE (restart $RESTART_COUNT/$MAX_RESTARTS)"

    if [ "$RESTART_COUNT" -ge "$MAX_RESTARTS" ]; then
        log_event "ERROR: Max restarts ($MAX_RESTARTS) reached. Giving up."
        exit 1
    fi

    # Brief cooldown before restart to avoid tight crash loops
    COOLDOWN=$((RESTART_COUNT * 2))
    if [ "$COOLDOWN" -gt 10 ]; then
        COOLDOWN=10
    fi
    log_event "Waiting ${COOLDOWN}s before restart..."
    sleep "$COOLDOWN"
done

log_event "Auto-restart finished. Total restarts: $RESTART_COUNT"
