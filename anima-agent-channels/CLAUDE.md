<!-- Phase 2 AGENT-CHANNELS — 플랫폼 표면 -->
# anima-agent-channels — 대화 채널 어댑터

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules        shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  core         shared/config/core.json              시스템맵
  parent       $ANIMA/anima-agent/CLAUDE.md         플랫폼 표면 루트
  sibling-core $ANIMA/anima-agent-core/CLAUDE.md    CLI + Registry (L0)
  plan         docs/anima_agent_restructure_plan_20260419.md   분리 전체 계획
  audit        docs/track_b_phase2_5_audit_20260419.md         Phase 2 승격 감사

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima-agent-channels/cli_agent.hexa
  $HEXA anima-agent-channels/telegram_bot.hexa
  $HEXA anima-agent-channels/discord_bot.hexa
  $HEXA anima-agent-channels/slack_bot.hexa
  $HEXA anima-agent-channels/channel_manager.hexa     # 채널 라우터

tree:
  base.hexa              채널 추상 인터페이스 (stub)
  channel_manager.hexa   다중 채널 라우터
  cli_agent.hexa         로컬 CLI 어댑터
  telegram_bot.hexa      Telegram Bot API 어댑터
  discord_bot.hexa       Discord Gateway 어댑터
  slack_bot.hexa         Slack Events API 어댑터
  __init__.hexa          패키지 마커 (flat-package 전환 후 삭제 예정)

관계:
  상위   anima-agent/                 플랫폼 본체 (hire-sim/autonomy 등)
  코어   anima-agent-core/            CLI 디스패처 (--telegram/--discord 플래그 진입점)
  자매   anima-agent-providers/       LLM 공급자 (channels → providers 호출)
  자매   anima-agent-plugins/         기능 플러그인
  자매   anima-agent-skills/          Skill 레지스트리

rules:
  - .hexa 단일 언어 (R1). .py/.rs/.sh 생성 금지
  - 설정 SSOT는 shared/ (R14), 여기는 참조만
  - use 체인 추가 시 audit 문서의 E3 movemap 재검증 필수 (현재 use 0건)
  - TODO[python-sdk] 마커 파일은 본격 배선 대기 상태 — 함부로 제거 금지
  - 채널별 시크릿은 .env (shared/config/env_schema.json 참조), 코드에 직접 박지 말 것
