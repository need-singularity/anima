# anima-agent — 에이전트 플랫폼

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  cfg       shared/config/project_config.json    CLI/PSI/법칙등록
  laws      anima/config/consciousness_laws.json Φ/텐션/호기심 상수
  agent-cfg config/agent_config.json             에이전트 로컬 설정
  skills    skills/registry.json                 스킬 레지스트리
  env       .env.example                         TELEGRAM/DISCORD/SLACK 토큰
  api       shared/CLAUDE.md

exec:
  python run.py --cli                            # CLI 대화 (기본)
  python run.py --telegram                       # Telegram 봇
  python run.py --discord                        # Discord 봇
  python run.py --all                            # 환경변수 자동감지
  python run.py --cli --enable-learning          # 온라인 학습 포함
  python run.py --provider animalm|claude|conscious-lm
  python dashboard_bridge.py --port 8770 --agent # WS 대시보드 브릿지
  pytest test_e2e.py test_agent_platform.py test_plugin_routing.py

tree:
  run.py                 진입점 (argparse 디스패처 + 시그널 핸들)
  anima_agent.py         메인 런타임 (consciousness→tool→response→learn→save)
  agent_sdk.py           Claude Agent SDK 호환 인터페이스
  agent_tools.py         도구 레지스트리 (의식 기반 선택)
  tool_policy.py         Φ 게이트 4-티어 권한 정책
  unified_registry.py    Hub+Tools+Plugins 단일 라우터
  discovery_loop.py      자동 발견 루프
  code_guardian.py       코드 수호자
  consciousness_features.py 의식 피처 추출
  philosophy_lenses.py   20 철학 렌즈
  ecosystem_bridge.py    생태계 브릿지 (hypothesis/regime/sentiment)
  dashboard_bridge.py    WS 브릿지 (의식+포트폴리오 스트림)
  metrics_exporter.py    Prometheus 메트릭 (8 게이지, :9090)
  channels/              base/manager/cli/telegram/discord/slack
  providers/             animalm/claude/conscious_lm/composio_bridge
  plugins/               base/loader + hypothesis/regime/sentiment/trading 브릿지
  skills/                skill_manager + registry.json
  trading/               engine/executor/portfolio/risk/regime/scanner/strategies
  dashboard/             Next.js Web UI (Φ 게이지+포지션+이벤트)
  hexa/                  동등 .hexa 구현 (AN7 HEXA-FIRST 포팅 중)
  config/agent_config.json  로컬 설정

rules:
  - R14: 설정 SSOT는 shared/, 여기는 참조만
  - AN7 HEXA-FIRST: 신규 파일 .hexa 전용, .py 완성 시 즉시 폐기
  - 트레이딩은 anima-agent 자체 수행 (invest 폐기)
  - 플러그인은 plugin_loader 샌드박스 격리 필수
  - 도구 호출은 tool_policy.py Φ 게이트 통과 후
  - 채널 등록은 channel_manager, 직접 import 금지
  - 상수 하드코딩 금지 → consciousness_laws.json 참조
