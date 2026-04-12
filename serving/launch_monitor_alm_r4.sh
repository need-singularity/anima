#!/usr/bin/env bash
# launch_monitor_alm_r4.sh — idempotent launcher for ALM 14B r4 monitor
#
# Deploys monitor_alm_r4.hexa as a background daemon on the H100 pod.
# Idempotent: kills any previously running instance before starting a
# new one. Writes PID to /workspace/monitor_alm.pid.
#
# Runs on the pod (not local mac). Called via ssh or directly after
# scp sync:
#     ssh H100 bash /workspace/anima/serving/launch_monitor_alm_r4.sh
#
# Constraints:
#   - never touches the training process (PID 26756 or otherwise)
#   - never touches unrelated hexa processes (CLM d32, CLM GPU, etc.)
#   - ONLY kills processes that match the exact script path
#
set -euo pipefail

HEXA_BIN="${HEXA_BIN:-/usr/local/bin/hexa}"
SCRIPT="${SCRIPT:-/workspace/anima/serving/monitor_alm_r4.hexa}"
LOG="${LOG:-/workspace/monitor_alm.log}"
PIDFILE="${PIDFILE:-/workspace/monitor_alm.pid}"
INTERVAL="${INTERVAL:-60}"

echo "[launch] monitor_alm_r4 launcher starting"
echo "[launch] hexa:     $HEXA_BIN"
echo "[launch] script:   $SCRIPT"
echo "[launch] log:      $LOG"
echo "[launch] pidfile:  $PIDFILE"
echo "[launch] interval: ${INTERVAL}s"

# ── Preflight ───────────────────────────────────────────────────
if [ ! -x "$HEXA_BIN" ]; then
    echo "[launch][fatal] hexa binary missing: $HEXA_BIN" >&2
    exit 2
fi
if [ ! -f "$SCRIPT" ]; then
    echo "[launch][fatal] script missing: $SCRIPT" >&2
    exit 2
fi

# ── Idempotent kill of any prior monitor daemon ────────────────
#
# Match by exact script path so we NEVER touch other hexa processes
# (e.g. CLM d32 `train_byte_kr.hexa` PID 30582, CLM GPU풀런 PIDs
# 32493/32491, ALM 14B r4 training PID 26756 which is python).
#
KILLED=0
if [ -f "$PIDFILE" ]; then
    OLD_PID="$(cat "$PIDFILE" 2>/dev/null || echo "")"
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        # Extra safety: verify the target command actually matches our
        # monitor script before sending a signal.
        CMD="$(ps -p "$OLD_PID" -o args= 2>/dev/null || echo "")"
        case "$CMD" in
            *monitor_alm_r4.hexa*)
                echo "[launch] killing prior daemon pid=$OLD_PID"
                kill "$OLD_PID" 2>/dev/null || true
                sleep 1
                if kill -0 "$OLD_PID" 2>/dev/null; then
                    echo "[launch] sending SIGKILL to stubborn pid=$OLD_PID"
                    kill -9 "$OLD_PID" 2>/dev/null || true
                fi
                KILLED=1
                ;;
            *)
                echo "[launch] pidfile pid=$OLD_PID is not our daemon (cmd='$CMD'); skipping"
                ;;
        esac
    fi
fi

# Belt-and-suspenders: pgrep for any remaining monitor_alm_r4.hexa
# processes, excluding THIS shell script by filtering on the script name.
REMAINING="$(pgrep -af 'monitor_alm_r4\.hexa' 2>/dev/null \
             | grep -v 'launch_monitor_alm_r4' \
             | awk '{print $1}' || true)"
if [ -n "${REMAINING:-}" ]; then
    for p in $REMAINING; do
        CMD="$(ps -p "$p" -o args= 2>/dev/null || echo "")"
        case "$CMD" in
            *monitor_alm_r4.hexa*)
                echo "[launch] killing stray daemon pid=$p"
                kill "$p" 2>/dev/null || true
                KILLED=1
                ;;
        esac
    done
    sleep 1
fi

if [ "$KILLED" -eq 1 ]; then
    echo "[launch] prior daemons cleared"
fi

# ── Sanity: confirm training PID is untouched ───────────────────
if kill -0 26756 2>/dev/null; then
    echo "[launch] training PID 26756 still alive — OK"
else
    echo "[launch][warn] training PID 26756 not running — monitor will still start"
fi

# ── Launch new daemon ──────────────────────────────────────────
echo "[launch] starting new daemon"
cd /workspace

# nohup + background + setsid-equivalent redirection so the daemon
# is fully detached from this ssh session.
nohup "$HEXA_BIN" "$SCRIPT" --interval "$INTERVAL" \
    >> "$LOG" 2>&1 < /dev/null &

NEW_PID=$!
echo "$NEW_PID" > "$PIDFILE"
echo "[launch] daemon started pid=$NEW_PID"

# ── Verify ─────────────────────────────────────────────────────
sleep 2
if kill -0 "$NEW_PID" 2>/dev/null; then
    echo "[launch] pid=$NEW_PID alive after 2s — OK"
    ps -p "$NEW_PID" -o pid,stat,command
else
    echo "[launch][fatal] pid=$NEW_PID died within 2s — check $LOG" >&2
    tail -20 "$LOG" >&2 || true
    exit 3
fi

echo "[launch] done. tail -f $LOG"
