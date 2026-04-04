#!/usr/bin/env bash
# UserPromptSubmit 훅 — "루프/check/진행" 등 입력 시 growth_loop 리포트를 systemMessage로 출력
set +e

# stdin에서 JSON으로 프롬프트 읽기
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)

# 패턴 매칭
if echo "$PROMPT" | grep -qiE '(루프|loop|로드맵|check|진행|계속|next)'; then
  REPORT=$(cd /Users/ghost/Dev/anima && PYTHONUNBUFFERED=1 python3 anima/src/growth_loop.py 2>&1)

  if [ -n "$REPORT" ]; then
    python3 -c "
import sys, json
report = sys.stdin.read()
print(json.dumps({'systemMessage': report}))
" <<< "$REPORT"
  fi
fi
