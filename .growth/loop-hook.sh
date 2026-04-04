#!/usr/bin/env bash
# 매 프롬프트마다 growth_loop.py 실행 → systemMessage로 리포트 (접히지 않음)
set +e

PROMPT="${USER_PROMPT:-}"

# "루프", "check", "loop", "로드맵", "진행" 등 패턴 매칭
if echo "$PROMPT" | grep -qiE '(루프|loop|로드맵|check|진행|계속|next)'; then
  REPORT=$(cd /Users/ghost/Dev/anima && PYTHONUNBUFFERED=1 python3 anima/src/growth_loop.py 2>&1)

  if [ -n "$REPORT" ]; then
    # python3으로 JSON 안전 이스케이프 → systemMessage
    python3 -c "
import sys, json
report = sys.stdin.read()
msg = '로드맵 리포트:\\n' + report
print(json.dumps({'systemMessage': msg}))
" <<< "$REPORT"
  fi
fi
