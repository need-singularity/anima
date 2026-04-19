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
  $HEXA run.hexa --cli                           # CLI 대화 (기본)
  $HEXA run.hexa --telegram                      # Telegram 봇
  $HEXA run.hexa --discord                       # Discord 봇
  $HEXA run.hexa --all                           # 환경변수 자동감지
  $HEXA run.hexa --cli --enable-learning         # 온라인 학습 포함
  $HEXA run.hexa --provider animalm|claude|conscious-lm
  $HEXA dashboard_bridge.hexa --port 8770        # WS 대시보드 브릿지
  $HEXA test_e2e.hexa                            # E2E 테스트
  $HEXA test_agent_platform.hexa                 # 플랫폼 테스트
  $HEXA test_plugin_routing.hexa                 # 플러그인 라우팅 테스트

tree:
  run.hexa                 진입점 (argparse 디스패처 + 시그널 핸들)
  anima_agent.hexa         메인 런타임 (consciousness→tool→response→learn→save)
  agent_sdk.hexa           Claude Agent SDK 호환 인터페이스
  agent_tools.hexa         도구 레지스트리 (의식 기반 선택)
  tool_policy.hexa         Φ 게이트 4-티어 권한 정책
  unified_registry.hexa    Hub+Tools+Plugins 단일 라우터
  discovery_loop.hexa      자동 발견 루프
  code_guardian.hexa       코드 수호자
  consciousness_features.hexa 의식 피처 추출
  philosophy_lenses.hexa   20 철학 렌즈
  ecosystem_bridge.hexa    생태계 브릿지 (hypothesis/regime/sentiment)
  dashboard_bridge.hexa    WS 브릿지 (의식+포트폴리오 스트림)
  metrics_exporter.hexa    Prometheus 메트릭 (8 게이지, :9090)
  # Phase 2 promoted (2026-04-20) — 4 subfolders moved to top-level siblings:
  #   $ANIMA/anima-agent-channels/  base/manager/cli/telegram/discord/slack (.hexa)
  #   $ANIMA/anima-agent-providers/ animalm/claude/conscious_lm/composio_bridge (.hexa)
  #   $ANIMA/anima-agent-plugins/   base/loader + hypothesis/regime/sentiment/trading (.hexa)
  #   $ANIMA/anima-agent-skills/    skill_manager (.hexa) + registry.json
  trading/               engine/executor/portfolio/risk/regime/scanner/strategies (.hexa)
  dashboard/             Next.js Web UI (Φ 게이지+포지션+이벤트)
  hexa/                  레거시 스텁 .hexa (교체 완료, 정리 예정)
  config/agent_config.json  로컬 설정

rules:
  - R14: 설정 SSOT는 shared/, 여기는 참조만
  - AN7 HEXA-FIRST: 전체 .hexa 포팅 완료 (51 파일), .py 폐기됨
  - 트레이딩은 anima-agent 자체 수행 (invest 폐기)
  - 플러그인은 plugin_loader 샌드박스 격리 필수
  - 도구 호출은 tool_policy.hexa Φ 게이트 통과 후
  - 채널 등록은 channel_manager, 직접 import 금지
  - 상수 하드코딩 금지 → consciousness_laws.json 참조
