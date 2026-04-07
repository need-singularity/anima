#!/usr/bin/env bash
# notify_telegram.sh — Send training alerts via Telegram bot
#
# Uses the same bot as anima-agent/channels/telegram_bot.py
# (ANIMA_TELEGRAM_TOKEN).
#
# Environment:
#   TELEGRAM_BOT_TOKEN  — Bot token (required)
#   TELEGRAM_CHAT_ID    — Target chat/group ID (required)
#
# Usage:
#   bash notify_telegram.sh "v3 crash - step 125K에서 resume"
#   bash notify_telegram.sh "학습 완료 - CE=0.004, Φ=71"
#   bash notify_telegram.sh --test   # send a test ping
#
# Integration with train_watchdog.sh:
#   Called on crash detection and auto-resume events.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Config ──
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
HOSTNAME="${HOSTNAME:-$(hostname 2>/dev/null || echo 'unknown')}"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

# ── Validate ──
if [ -z "$BOT_TOKEN" ]; then
    echo "[notify_telegram] ERROR: TELEGRAM_BOT_TOKEN not set"
    exit 1
fi

if [ -z "$CHAT_ID" ]; then
    echo "[notify_telegram] ERROR: TELEGRAM_CHAT_ID not set"
    exit 1
fi

# ── Send message ──
send_message() {
    local text="$1"
    local formatted="[${HOSTNAME}] ${TIMESTAMP}
${text}"

    local response
    response=$(curl -s -X POST \
        "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="${CHAT_ID}" \
        -d text="${formatted}" \
        -d parse_mode="HTML" \
        --connect-timeout 10 \
        --max-time 15 \
        2>&1)

    # Check if successful
    if echo "$response" | grep -q '"ok":true'; then
        echo "[notify_telegram] Message sent successfully"
        return 0
    else
        echo "[notify_telegram] WARNING: Failed to send message"
        echo "[notify_telegram] Response: $response"
        return 1
    fi
}

# ── Main ──
case "${1:-}" in
    --test)
        send_message "Telegram notification test from Anima watchdog."
        ;;
    --help|-h)
        echo "Usage: $0 MESSAGE"
        echo "       $0 --test"
        echo ""
        echo "Environment:"
        echo "  TELEGRAM_BOT_TOKEN  Bot token (required)"
        echo "  TELEGRAM_CHAT_ID    Target chat ID (required)"
        exit 0
        ;;
    "")
        echo "[notify_telegram] ERROR: No message provided"
        echo "Usage: $0 MESSAGE"
        exit 1
        ;;
    *)
        send_message "$*"
        ;;
esac
