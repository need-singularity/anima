#!/bin/bash
# growth_daemon.sh — 자동 성장 데몬 (로컬용)
# launchd 또는 직접 실행: bash growth_daemon.sh

cd /Users/ghost/Dev/anima
export PYTHONPATH=/Users/ghost/Dev/anima/anima/src
export PATH="/Users/ghost/.local/bin:/opt/homebrew/bin:$PATH"
export KMP_DUPLICATE_LIB_OK=TRUE

while true; do
    echo "[$(date)] Growth cycle start"

    # 1. 건강 체크
    python3 -c "
import sys; sys.path.insert(0, 'anima/src')
from loop_extensions import health_check
health_check()
" 2>&1 | head -20

    # 2. 성장 사이클
    python3 -c "
import sys; sys.path.insert(0, 'anima/src')
from self_growth import run_cycle
run_cycle(dry_run=False)
" 2>&1 | head -30

    # 3. 루프 리포트 (짧게)
    python3 -c "
import sys; sys.path.insert(0, 'anima/src')
from loop_report import short_report
short_report()
" 2>&1

    echo "[$(date)] Cycle done. Next in 30min."
    echo "---"
    sleep 1800
done
