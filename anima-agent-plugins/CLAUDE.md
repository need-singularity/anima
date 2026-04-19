<!-- Phase 2 AGENT-PLUGINS — 플랫폼 표면 -->
# anima-agent-plugins — 기능 플러그인

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
  $HEXA anima-agent-plugins/plugin_loader.hexa         # 동적 플러그인 디스커버리
  $HEXA anima-agent-plugins/hypothesis_bridge.hexa     # ouroboros 가설 브리지
  $HEXA anima-agent-plugins/regime_bridge.hexa         # 시장 레짐 브리지
  $HEXA anima-agent-plugins/sentiment_bridge.hexa      # 뉴스 감성 브리지
  $HEXA anima-agent-plugins/trading.hexa               # 트레이딩 플러그인 (thin shim)

tree:
  base.hexa                 Plugin 추상 인터페이스 (stub)
  plugin_loader.hexa        동적 디스커버리 (TODO[python-sdk])
  hypothesis_bridge.hexa    ouroboros 가설 발견 브리지
  regime_bridge.hexa        시장 레짐 감지 브리지
  sentiment_bridge.hexa     뉴스 감성 분석 브리지
  trading.hexa              트레이딩 플러그인 shim (본체는 anima-agent/trading/ → Phase 3)
  __init__.hexa             패키지 마커

관계:
  상위   anima-agent/                 플랫폼 본체
  코어   anima-agent-core/            unified_registry 가 plugins 라우팅
  자매   anima-agent-channels/        대화 채널
  자매   anima-agent-providers/       LLM 공급자
  자매   anima-agent-skills/          Skill 레지스트리
  Phase  3               anima-agent/trading/ 승격 후 trading.hexa shim 갱신

rules:
  - .hexa 단일 언어 (R1). .py/.rs/.sh 생성 금지
  - 설정 SSOT는 shared/ (R14), 여기는 참조만
  - use 체인 추가 시 audit 문서의 E3 movemap 재검증 필수 (현재 use 0건)
  - TODO[python-sdk] 마커 파일은 본격 배선 대기 상태 — 함부로 제거 금지
  - tool-name 문자열(예: trading_backtest) 은 agent-core 레지스트리 키이므로 변경 시 동기화 필수
