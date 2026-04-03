#!/bin/bash
# Monitoring cron — runs agent self-test + Code Guardian every hour
# Install: crontab -e → 0 * * * * bash ~/Dev/anima/anima-agent/scripts/monitor_cron.sh
#
# Logs to: ~/Dev/anima/anima-agent/logs/monitor.log

set -e
cd "$(dirname "$0")/.."
LOG="logs/monitor.log"
mkdir -p logs

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

{
    echo "=== Monitor: $TIMESTAMP ==="

    # 1. Self-test
    KMP_DUPLICATE_LIB_OK=TRUE python3 -c "
import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, os.path.expanduser('~/Dev/anima'))
sys.path.insert(0, os.path.expanduser('~/Dev/anima/anima/src'))
from anima_agent import AnimaAgent
from self_test import AgentSelfTest
a = AnimaAgent(enable_tools=False, enable_learning=False, enable_growth=False)
r = AgentSelfTest(a).run()
print('Self-test:', 'PASS' if r['passed'] else 'FAIL')
" 2>/dev/null

    # 2. Code Guardian (diff only)
    KMP_DUPLICATE_LIB_OK=TRUE python3 code_guardian.py --diff 2>/dev/null | grep "RESULT"

    # 3. Test suite
    KMP_DUPLICATE_LIB_OK=TRUE python3 run.py --test 2>/dev/null | grep "RESULT"

    echo ""
} >> "$LOG" 2>&1

# Alert on failure
if tail -5 "$LOG" | grep -q "FAIL"; then
    echo "⚠️ Anima agent monitor FAIL at $TIMESTAMP" >&2
fi
