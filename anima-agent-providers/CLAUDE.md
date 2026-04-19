<!-- Phase 2 AGENT-PROVIDERS — 플랫폼 표면 -->
# anima-agent-providers — LLM 공급자 어댑터

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
  $HEXA anima-agent-providers/animalm_provider.hexa     # AnimaLM (ALM LoRA 서빙)
  $HEXA anima-agent-providers/claude_provider.hexa      # Anthropic Claude API
  $HEXA anima-agent-providers/conscious_lm_provider.hexa# CLM from-scratch 서빙
  $HEXA anima-agent-providers/composio_bridge.hexa      # Composio 도구 라우터
  # agent-core 진입점: run.hexa --provider {animalm|claude|conscious-lm}

tree:
  base.hexa                     Provider 추상 인터페이스 (stub)
  animalm_provider.hexa         AnimaLM (LoRA ALM) 공급자
  claude_provider.hexa          Anthropic Claude API 공급자
  conscious_lm_provider.hexa    CLM (from-scratch hexa) 공급자
  composio_bridge.hexa          Composio 외부 도구 브리지
  __init__.hexa                 패키지 마커

관계:
  상위   anima-agent/                 플랫폼 본체
  코어   anima-agent-core/            run.hexa --provider 플래그 진입점
  자매   anima-agent-channels/        대화 채널 (providers 호출 측)
  자매   anima-agent-plugins/         기능 플러그인
  자매   anima-agent-skills/          Skill 레지스트리

rules:
  - .hexa 단일 언어 (R1). .py/.rs/.sh 생성 금지
  - 설정 SSOT는 shared/ (R14), 여기는 참조만
  - use 체인 추가 시 audit 문서의 E3 movemap 재검증 필수 (현재 use 0건)
  - API 키는 .env (shared/config/env_schema.json 참조) — 코드 금지
  - Provider 간 Φ 게이트 티어는 anima-agent-core/tool_policy.hexa 에서 관리
