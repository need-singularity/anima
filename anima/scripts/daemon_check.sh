#!/bin/bash
# daemon_check.sh — 모든 자동화 데몬 상태 확인
# Usage: bash daemon_check.sh

echo "═══════════════════════════════════════════"
echo "  Anima 데몬 상태 — $(date '+%Y-%m-%d %H:%M')"
echo "═══════════════════════════════════════════"

echo ""
echo "  ■ 로컬 (Mac)"

# launchd
LD=$(launchctl list 2>/dev/null | grep anima)
if [ -n "$LD" ]; then
    PID=$(echo "$LD" | awk '{print $1}')
    echo "    self-growth:  ✅ PID=$PID (launchd, 30min cycle)"
    LAST=$(tail -1 /tmp/self_growth.log 2>/dev/null | head -c 60)
    echo "      last: $LAST"
else
    echo "    self-growth:  ❌ NOT RUNNING"
    echo "      fix: launchctl load ~/Library/LaunchAgents/com.anima.self-growth.plist"
fi

# auto_wire
AW=$(pgrep -f "auto_wire.*watch" 2>/dev/null)
if [ -n "$AW" ]; then
    echo "    auto-wire:    ✅ PID=$AW"
else
    echo "    auto-wire:    ⚠️ not running (optional)"
fi

echo ""
echo "  ■ H100"
SSH="ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i ~/.runpod/ssh/RunPod-Key-Go root@216.243.220.217 -p 10935"

if $SSH "echo ok" 2>/dev/null | grep -q ok; then
    # training
    if $SSH "pgrep -f train_anima_lm" 2>/dev/null > /dev/null; then
        STEP=$($SSH "grep -P '^\s+\d+\s+\|' /workspace/pipeline_14b_32b.log 2>/dev/null | tail -1 | awk '{print \$1}'" 2>/dev/null)
        echo "    training:     🔄 step $STEP"
    else
        echo "    training:     ⏸️  idle"
    fi

    # growth daemon
    if $SSH "pgrep -f growth_daemon" 2>/dev/null > /dev/null; then
        echo "    growth:       ✅ running"
    else
        echo "    growth:       ❌ NOT RUNNING"
    fi

    # auto_loop
    if $SSH "pgrep -f auto_loop" 2>/dev/null > /dev/null; then
        echo "    auto_loop:    ✅ running"
    else
        echo "    auto_loop:    ⏸️  done or stopped"
    fi
else
    echo "    (SSH 연결 실패 — Pod 중지됨?)"
fi

echo ""
echo "  ■ 루프 상태"
cd /Users/ghost/Dev/anima
python3 -c "
import sys; sys.path.insert(0, 'anima/src')
from loop_report import short_report
short_report()
" 2>/dev/null

echo ""
echo "═══════════════════════════════════════════"
