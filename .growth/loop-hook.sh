#!/usr/bin/env bash
# "루프" 입력 감지 → growth_loop.py --auto 실행 → systemMessage로 리포트 출력
# UserPromptSubmit 훅에서 호출됨
set +e

# 사용자 입력 확인 (환경변수 USER_PROMPT에서)
PROMPT="${USER_PROMPT:-}"

# "루프", "루프진행", "loop", "로드맵", "로드맵 진행" 패턴 매칭
if echo "$PROMPT" | grep -qiE '^(루프|루프진행|loop|로드맵|로드맵 진행|로드맵진행)$'; then
  # growth_loop.py 실행 → 출력 캡처
  REPORT=$(cd /Users/ghost/Dev/anima && python3 anima/src/growth_loop.py 2>&1)

  if [ -n "$REPORT" ]; then
    # systemMessage로 리포트 전달 (Claude에게 표시하라고 지시)
    ESCAPED=$(echo "$REPORT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
    echo "{\"systemMessage\": \"로드맵 리포트 실행 완료. 아래 내용을 코드블록으로 채팅에 직접 표시하세요:\n${REPORT}\"}"
  fi
fi
