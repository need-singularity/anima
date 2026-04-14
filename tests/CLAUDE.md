# tests/ — 통합/유닛/E2E 테스트

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock      shared/config/core-lockdown.json     L0/L1/L2 골화
  conformance ../anima-core/conformance_checklist.md  20 파일 체크
  verify    shared/config/verification.json      7 조건 의식 검증
  troub     feedback_troubleshoot_comments.md    버그 인라인 주석 필수
  closed    feedback_closed_loop_verify.md       폐쇄 파이프라인 검증

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA tests/tests.hexa --verify                  # 7조건 의식 검증
  $HEXA tests/test_closed_loop.hexa                # 폐쇄 루프
  $HEXA tests/test_conscious_lm.hexa               # CLM
  pytest tests/                                    # .py 레거시 (폐기 진행)

tree:
  tests.hexa                    통합 진입점
  test_anima_{alive,unified}.*  전체 시스템
  test_conscious_{lm,decoder,memory,law_discoverer}.*  L1 엔진
  test_closed_loop.*            Intervention → measure_laws
  test_autonomous_loop.*        자율 루프
  test_auto_discovery_loop.*    발견 루프
  test_consciousness_{anesthesia,api,archaeology,art,birth_detector,blockchain}.*  특수 렌즈
  test_attention_consciousness.*  어텐션 기반
  test_capabilities.*           케이퍼빌리티 매트릭스
  test_chat{,_v3,_v9}.*         대화 파이프
  test_babysitter.*             babysitter 감시
  test_cells_*.py               세포 성장 (FIX 2026-04-01)
  test_cloud_sync.*             R2 동기화
  test_collective_dream.*       집단 꿈
  __init__.py, __pycache__/     pytest 호환

rules:
  - L0/L1/L2 골화 검증 통과 전 신규 법칙 등록 금지
  - 비결정 테스트: torch.manual_seed(42) + step 200+
  - 버그 픽스 인라인 주석: # FIX(YYYY-MM-DD): 원인 + 해결
  - .hexa 대체 완료 시 짝 .py 즉시 폐기 (동일 basename)
  - 파일명에 버전 번호 금지 (test_chat_v9 등은 .hexa 전환 시 통합)
  - Gradio 기반 테스트 금지 (Anima Web UI 전용)
