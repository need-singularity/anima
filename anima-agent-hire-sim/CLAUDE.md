<!-- L0 HIRE-SIM — 100-task corpus + judge 수정 금지 -->
# anima-agent-hire-sim — hire-sim 벤치 스위트 (Phase 3)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules      shared/config/absolute_rules.json          R1~R21 + AN1~AN7
  lock       shared/config/core-lockdown.json           L0 골화 목록
  parent     $ANIMA/anima-agent/CLAUDE.md               에이전트 플랫폼
  core       $ANIMA/anima-agent-core/CLAUDE.md          L0 에이전트 코어
  plan       docs/anima_agent_restructure_plan_20260419.md  분리 전체 계획
  phase3     docs/track_b_phase3_hire_sim_design_20260419.md  본 Phase 설계

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA run anima-agent-hire-sim/test_hire_sim.hexa              # smoke (100 task mock)
  $HEXA run anima-agent-hire-sim/test_hire_sim_harness.hexa      # harness (runner+stratify+judge)
  $HEXA run anima-agent-hire-sim/hire_sim_runner.hexa            # endpoint runner (stratified-30)
  $HEXA run anima-agent-hire-sim/hire_sim_live.hexa              # E1 live (S1 HTTP) — parse err 선재
  $HEXA run anima-agent-hire-sim/run_hire_sim_claude.hexa        # Claude baseline depth=1

tree:
  hire_sim_100.hexa           100-task × 6-domain corpus SSOT (L0, 수정 금지)
  hire_sim_judge.hexa         per-domain deterministic judge (L0)
  hire_sim_stratify.hexa      stratified-30 샘플러
  hire_sim_runner.hexa        endpoint runner (stratified-30)
  hire_sim_live.hexa          E1 live runner (S1 HTTP, parse err 144:28 선재)
  run_hire_sim_claude.hexa    Claude adapter entry
  test_hire_sim.hexa          smoke test
  test_hire_sim_harness.hexa  harness test (runner+stratify+judge)

관계:
  상위    anima-agent/                   플랫폼 표면 (autonomy_loop, llm_claude_adapter)
  자매    anima-agent-core/              L0 에이전트 코어 (CLI + Registry)
  cross   training/deploy/hire_sim_*.hexa   Z-path 러너 (training 소유, 경로 const 참조)
  cross   serving/hire_sim_judge_lenient.hexa  D6 lenient judge (serving 소유)

use chain (cross-package — `../anima-agent/` 프리픽스로 해결):
  hire_sim_100       → use "../anima-agent/autonomy_loop"
  test_hire_sim      → use "../anima-agent/autonomy_loop" + "hire_sim_100"
  run_hire_sim_claude → use "../anima-agent/autonomy_loop" + "hire_sim_100" + "../anima-agent/llm_claude_adapter"
  내부 (same dir):    hire_sim_stratify/judge/runner → use "hire_sim_100" (no prefix)

rules:
  - L0: hire_sim_100.hexa (corpus SSOT) + hire_sim_judge.hexa 수정 금지
  - 새 task 추가 시 expected_counts 갱신 + test_hire_sim T1 PASS 유지
  - .hexa 단일 언어 (R1). .py/.rs/.sh 생성 금지
  - 설정 SSOT는 shared/ (R14), 여기는 참조만
  - cross-package use 는 `../anima-agent/` 또는 `../anima-agent-hire-sim/` 경로 프리픽스 필수
  - hire_sim_live.hexa parse error 144:28 선재 — Phase 3 범위 외 (별도 bugfix)
