<!-- Phase 2 AGENT-SKILLS — 플랫폼 표면 -->
# anima-agent-skills — Skill 레지스트리

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules        shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  core         shared/config/core.json              시스템맵
  parent       $ANIMA/anima-agent/CLAUDE.md         플랫폼 표면 루트
  sibling-core $ANIMA/anima-agent-core/CLAUDE.md    CLI + Registry (L0)
  registry     registry.json                         skill index (절대경로 $ANIMA/.anima/skills)
  plan         docs/anima_agent_restructure_plan_20260419.md   분리 전체 계획
  audit        docs/track_b_phase2_5_audit_20260419.md         Phase 2 승격 감사

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima-agent-skills/skill_manager.hexa          # Skill 로더 + 실행기

tree:
  skill_manager.hexa   Skill 로더 + 실행기 (stub)
  registry.json        Skill 인덱스 ($ANIMA/.anima/skills/*.md 절대경로)
  __init__.hexa        패키지 마커

관계:
  상위   anima-agent/                 플랫폼 본체
  코어   anima-agent-core/            agent_tools 가 skill_manager 호출
  자매   anima-agent-channels/        대화 채널
  자매   anima-agent-providers/       LLM 공급자
  자매   anima-agent-plugins/         기능 플러그인
  외부   $ANIMA/.anima/skills/*.md    실제 skill 정의 (markdown)

rules:
  - .hexa 단일 언어 (R1). .py/.rs/.sh 생성 금지
  - 설정 SSOT는 shared/ (R14), registry.json 은 로컬 index
  - use 체인 추가 시 audit 문서의 E3 movemap 재검증 필수 (현재 use 0건)
  - registry.json file_path 는 $ANIMA 절대경로 — 디렉토리 이동에도 무관
  - Skill 정의 자체는 이 디렉토리가 아닌 $ANIMA/.anima/skills/ 에 위치
