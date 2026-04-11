#!/bin/bash
# serve_http.sh — bridge eval_serve.hexa to HTTP via socat
#
# P5c-1: minimal HTTP serving endpoint for hexa model.
# Each TCP connection forks a new eval_serve.hexa process that
# reads its stdin (the request body) and writes plaintext to stdout
# (the response body). socat handles the HTTP framing.
#
# Usage:
#   ./serve_http.sh                       # default port 8080, no checkpoint
#   ./serve_http.sh 9000                  # custom port
#   ./serve_http.sh 8080 model.hexackpt   # custom port + checkpoint
#
# Test (in another shell):
#   curl -s -d 'GEN 16 0' http://localhost:8080
#   curl -s -d 'HEALTH'   http://localhost:8080
#   curl -s -d 'INFO'     http://localhost:8080
#
# Note: this is line-protocol, NOT real HTTP request parsing. socat
# strips the HTTP headers via SYSTEM/EXEC stdin pipe — the body of the
# POST request is what eval_serve.hexa reads. For real HTTP semantics
# (path routing, headers, etc), wrap this in nginx or use a hexa
# extern fn binding to a real http library.

set -e

PORT="${1:-8080}"
CKPT="${2:-}"

HEXA="${HEXA:-$HOME/Dev/hexa-lang/hexa}"
EVAL_SERVE="$(dirname "$0")/eval_serve.hexa"

if [ ! -x "$HEXA" ]; then
    echo "ERR: hexa binary not found at $HEXA" >&2
    exit 1
fi
if [ ! -f "$EVAL_SERVE" ]; then
    echo "ERR: eval_serve.hexa not found at $EVAL_SERVE" >&2
    exit 1
fi
if ! command -v socat >/dev/null 2>&1; then
    echo "ERR: socat not installed (brew install socat / apt install socat)" >&2
    exit 1
fi

if [ -n "$CKPT" ]; then
    CMD="$HEXA $EVAL_SERVE $CKPT"
else
    CMD="$HEXA $EVAL_SERVE"
fi

echo "═══ eval_serve HTTP bridge ═══"
echo "  port  : $PORT"
echo "  hexa  : $HEXA"
echo "  serve : $EVAL_SERVE"
echo "  ckpt  : ${CKPT:-(default shift-by-1 model)}"
echo ""
echo "  Test:  curl -s -d 'GEN 16 0' http://localhost:$PORT"
echo "         curl -s -d 'HEALTH'   http://localhost:$PORT"
echo ""
echo "  Listening..."

exec socat \
    TCP-LISTEN:"$PORT",fork,reuseaddr \
    SYSTEM:"$CMD"
