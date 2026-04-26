#!/bin/bash
# _audio_worker_call.sh — IPC adapter for anima_audio.hexa persistent worker.
#
# Usage: _audio_worker_call.sh <ppid> <code_b64> <expect_path>
#
# Spawns worker on first call (per ppid), reuses across subsequent calls.
# Sends one NDJSON request, prints worker's NDJSON response on stdout.
#
# State files (per-PPID isolation):
#   /tmp/anima_audio_worker_${ppid}/
#     pid          — worker pid
#     keepalive    — sleep-pid (writer-keeper for FIFO_IN)
#     in           — FIFO: hexa -> worker
#     out          — FIFO: worker -> hexa
#     log          — worker stderr
#
# Why keepalive: a FIFO with zero open writers returns EOF on next read; the
# worker would then exit. We spawn a `sleep infinity > FIFO_IN &` to hold the
# writer side open across all per-call shell invocations.

set -u

PPID_HEXA="$1"
CODE_B64="$2"
EXPECT_PATH="${3:-}"

WD="/tmp/anima_audio_worker_${PPID_HEXA}"
PID_FILE="$WD/pid"
KEEP_FILE="$WD/keepalive"
FIFO_IN="$WD/in"
FIFO_OUT="$WD/out"
LOG_FILE="$WD/log"
WORKER_PY="$(dirname "$0")/anima_audio_worker.py"
PYTHON_BIN="${ANIMA_AUDIO_PYTHON:-/opt/homebrew/bin/python3}"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python3"

_alive() {
  local pid=$1
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

_spawn_worker() {
  mkdir -p "$WD"
  rm -f "$FIFO_IN" "$FIFO_OUT"
  mkfifo "$FIFO_IN" "$FIFO_OUT"
  # 1) keepalive: holds FIFO_IN open for write so worker doesn't see EOF
  #    when caller shells exit between requests.
  ( exec sleep 86400 > "$FIFO_IN" ) &
  local kpid=$!
  disown $kpid 2>/dev/null
  echo "$kpid" > "$KEEP_FILE.tmp"
  mv "$KEEP_FILE.tmp" "$KEEP_FILE"
  # 2) worker — tell it which pid to watch (hexa's pid, passed as $1 = $PPID_HEXA)
  ANIMA_AUDIO_PARENT_PID="$PPID_HEXA" nohup "$PYTHON_BIN" "$WORKER_PY" \
    < "$FIFO_IN" > "$FIFO_OUT" 2>>"$LOG_FILE" &
  local wpid=$!
  disown $wpid 2>/dev/null
  echo "$wpid" > "$PID_FILE.tmp"
  mv "$PID_FILE.tmp" "$PID_FILE"
  # 3) consume the "ready" event
  local ready=""
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if read -t 1 -r ready < "$FIFO_OUT" 2>/dev/null; then
      break
    fi
    if ! _alive "$wpid"; then
      return 1
    fi
  done
}

# Decide if worker needs spawning
WPID=""
if [ -f "$PID_FILE" ]; then
  WPID=$(cat "$PID_FILE" 2>/dev/null || true)
fi
KPID=""
if [ -f "$KEEP_FILE" ]; then
  KPID=$(cat "$KEEP_FILE" 2>/dev/null || true)
fi

if ! _alive "$WPID" || ! _alive "$KPID"; then
  # tear down stale state
  _alive "$WPID" && kill "$WPID" 2>/dev/null
  _alive "$KPID" && kill "$KPID" 2>/dev/null
  rm -f "$PID_FILE" "$KEEP_FILE"
  if ! _spawn_worker; then
    echo '{"id":null,"ok":false,"err":"spawn_failed","elapsed_ms":0,"bytes_out":0}'
    exit 1
  fi
  WPID=$(cat "$PID_FILE")
fi

# id = nanoseconds (unique enough)
REQ_ID=$(date +%s%N 2>/dev/null || echo 0)

# Build request — code is already base64; expect_path is plain path string
REQ='{"id":'$REQ_ID',"kind":"exec","code_b64":"'$CODE_B64'","expect_path":"'$EXPECT_PATH'"}'

# Send request to FIFO_IN (will succeed because keepalive holds reader present)
echo "$REQ" > "$FIFO_IN"

# Read one response line
RESP=""
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if read -t 1 -r RESP < "$FIFO_OUT" 2>/dev/null; then
    break
  fi
  if ! _alive "$WPID"; then
    echo "{\"id\":$REQ_ID,\"ok\":false,\"err\":\"worker_died_during_call\",\"elapsed_ms\":0,\"bytes_out\":0}"
    exit 1
  fi
done

if [ -z "$RESP" ]; then
  echo "{\"id\":$REQ_ID,\"ok\":false,\"err\":\"timeout_20s\",\"elapsed_ms\":0,\"bytes_out\":0}"
  exit 1
fi

echo "$RESP"
