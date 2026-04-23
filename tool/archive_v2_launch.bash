#!/usr/bin/env bash
# archive_v2_launch.bash — session-independent launcher for archive_v2_driver.hexa
#
# Usage:
#   bash tool/archive_v2_launch.bash              # detach & run full queue
#   bash tool/archive_v2_launch.bash --limit 3    # detach & run first 3
#   bash tool/archive_v2_launch.bash --fg         # run in foreground (debug)
#
# Outputs:
#   /tmp/archive_v2.out   (stdout/stderr of detached run)
#   state/asset_archive_log.jsonl  (JSONL event trail — SSOT of progress)
#   state/archive_v2.lock (PID of running instance)

set -euo pipefail

cd "$(dirname "$0")/.."

# Use dev build — homebrew 0.2.0 lacks exec() builtin
HEXA="/Users/ghost/core/hexa-lang/hexa"
DRIVER="tool/archive_v2_driver.hexa"
OUT="${ARCHIVE_V2_OUT:-$HOME/archive_v2.out}"

if [[ ! -x "$HEXA" ]]; then
    echo "[ERR] hexa dev build not found at $HEXA" >&2
    exit 2
fi

FG=0
ARGS=()
for a in "$@"; do
    case "$a" in
        --fg) FG=1 ;;
        *)    ARGS+=("$a") ;;
    esac
done

if [[ $FG -eq 1 ]]; then
    exec "$HEXA" "$DRIVER" ${ARGS[@]+"${ARGS[@]}"}
fi

nohup setsid "$HEXA" "$DRIVER" ${ARGS[@]+"${ARGS[@]}"} > "$OUT" 2>&1 &
PID=$!
disown $PID 2>/dev/null || true
echo "[launched] pid=$PID out=$OUT"
echo "[tail] tail -F $OUT"
echo "[log]  tail -F state/asset_archive_log.jsonl"
