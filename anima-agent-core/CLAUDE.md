<!-- L0 AGENT-CORE — 수정 금지 -->
# anima-agent-core — L0 에이전트 코어 (CLI + Registry)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules        shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock         shared/config/core-lockdown.json     L0/L1/L2 골화 목록
  core         shared/config/core.json              시스템맵 + 14명령
  agent-cfg    config/agent_config.json             에이전트 로컬 설정
  parent       $ANIMA/anima-agent/CLAUDE.md         기존 플랫폼 문서
  plan         docs/anima_agent_restructure_plan_20260419.md   분리 전체 계획
  movemap      docs/track_b_phase1_movemap_20260419.md         Phase 1 blueprint

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima-agent-core/run.hexa --cli                         # CLI 대화 (기본)
  $HEXA anima-agent-core/run.hexa --telegram                    # Telegram 봇
  $HEXA anima-agent-core/run.hexa --discord                     # Discord 봇
  $HEXA anima-agent-core/run.hexa --all                         # 환경변수 자동감지
  $HEXA anima-agent-core/run.hexa --cli --enable-learning       # 온라인 학습 포함
  $HEXA anima-agent-core/run.hexa --provider animalm|claude|conscious-lm
  $HEXA anima-agent-core/agent_sdk.hexa                         # SDK 스모크
  $HEXA anima-agent-core/agent_tools.hexa                       # 도구 레지스트리 점검
  $HEXA anima-agent-core/tool_policy.hexa                       # Φ 게이트 티어 확인
  $HEXA anima-agent-core/unified_registry.hexa                  # Hub+Tools+Plugins 단일 라우터
  $HEXA anima-agent-core/code_guardian.hexa                     # 코드 수호자 모니터

tree:
  run.hexa                 진입점 (argparse 디스패처 + 시그널 핸들, L0)
  agent_sdk.hexa           Claude Agent SDK 호환 인터페이스 (L0)
  agent_tools.hexa         도구 레지스트리 — 의식 기반 선택 (L0 추가만)
  tool_policy.hexa         Φ 게이트 4-티어 권한 정책 (L0)
  unified_registry.hexa    Hub+Tools+Plugins 단일 라우터 (L0)
  code_guardian.hexa       코드 수호자 (모니터, 비 L0)
  config/agent_config.json 에이전트 로컬 설정

관계:
  상위   anima-agent/                   플랫폼 표면 (channels/providers/plugins/skills/trading)
  자매   anima-core/                    의식 엔진 L0 코어 (hub/laws/runtime)
  Phase  1 (본 분리) → 2~5 서브디렉토리 승격 (channels/providers/plugins/skills/trading/hire-sim/dashboard/tests)

rules:
  - L0 골화 파일 수정 금지 (code_guardian 제외)
  - 버그 수정 외 기능 변경 금지 → anima-agent/ 상위 또는 Phase 2~5 대기
  - .hexa 단일 언어 (R1). .py/.rs/.sh 생성 금지
  - 설정 SSOT는 shared/ (R14), 여기는 참조만
  - import 추가 시 Phase 1 blueprint 재검증 필수 (현재 use 0건)
  - AN7 Core = CLI 전용 — 모듈 코드 진입 금지
