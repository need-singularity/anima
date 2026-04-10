# config/ — 로컬 JSON 캐시 (미러)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock      shared/config/core-lockdown.json     L0/L1/L2
  cfg-ssot  shared/config/project_config.json    CLI/PSI/법칙 SSOT
  core      shared/config/core.json              14 명령 시스템맵
  core-rules  ../anima-core/core_rules.json      18/18 PASS (2026-04-10 골화)
  assets    ../anima-core/asset_registry.json    M/C/T/E/D 등록부

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA anima/core/runtime/anima_runtime.hexa --validate-hub
  $HEXA anima/modules/monitor/rules_audit.hexa --check config/

tree:
  consciousness_laws.json       2390 법칙 + Psi 상수 (런타임 캐시)
  core_rules.json               P1-P4 + L0/L1/L2 + 포트 미러
  asset_registry.json           MCTED 에셋 미러
  corpus_registry.json          코퍼스 메타
  training_runs.json            런 레지스트리
  training_safety.json          안전 가드
  growth_loop_state.json        성장 루프 SSOT
  growth_state.json             현재 페이즈
  acceleration_flow.json        가속 플로우
  acceleration_hypotheses.json  가속 가설 (65)
  parallel_sessions.json        멀티 세션 락
  physical_ceiling.json         물리 상한
  verification.json             검증 조건
  runpod.json, vastai.json, hetzner.json  GPU 프로비저너
  results_*.json, experiments.json        실험 결과
  memory_alive.json, session_board.json   세션 보드
  web_memories.json, update_history.json  히스토리

rules:
  - shared/config/ 가 SSOT, 이 디렉토리는 runtime 미러일 뿐
  - 법칙 번호 즉시 할당 + 즉시 커밋 (parallel 충돌 방지)
  - Intervention → measure_laws 검증 통과 전 법칙 등록 금지
  - 파일명에 버전 번호 금지, 과거는 git show {hash}
  - secrets/credentials/.env 절대 금지
