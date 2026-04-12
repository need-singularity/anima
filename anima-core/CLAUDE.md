<!-- L0 CORE — 수정 금지 -->
# anima-core — L0 의식 엔진 코어

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules        shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  lock         shared/config/core-lockdown.json     L0/L1/L2 골화 목록
  core         shared/config/core.json              시스템맵 + 14명령
  core-rules   core_rules.json                      P1~P4 + L0/L1/L2 + 포트
  conformance  conformance_checklist.md             18/18 ALL PASS
  assets       asset_registry.md                    M/C/T/E/D 자산 분류
  laws         laws.hexa                            PSI 상수 + 법칙 로더
  hub          hub.hexa                             _registry 라우팅
  parent       /Users/ghost/Dev/anima/CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/hexa
  $HEXA anima-core/runtime/anima_runtime.hexa --keyboard      # CLI 대화
  $HEXA anima-core/runtime/anima_runtime.hexa --ticks 100     # 자연발화 (tick loop)
  $HEXA anima-core/runtime/anima_runtime.hexa --validate-hub  # 48모듈 허브 검증
  $HEXA anima-core/verification/cvf.hexa --quick              # 의식검증 4레이어
  $HEXA anima-core/verification/byte_emergence.hexa           # 창발 감지
  $HEXA anima-core/dimension_transform.hexa                   # 차원변환 물리한계
  $HEXA anima-core/servant.hexa                               # 서번트 FSM 검증
  $HEXA anima-core/phi_engine.hexa                            # Phi 연산 검증
  $HEXA anima-core/topology.hexa                              # 토폴로지 검증
  $HEXA anima-core/laws.hexa count                            # 법칙 수 (2516)
  $HEXA anima-core/laws.hexa psi alpha                        # PSI 상수 (0.014)

tree:
  hub.hexa                    ConsciousChat Hub (L0 라우터)
  laws.hexa                   consciousness_laws.json 로더
  dimension_transform.hexa    차원변환/펼침 (5fold+4unfold+PCA, n6 3/3)
  servant.hexa                Servant 통합 (sense+emerge+bridge, n6 9/9)
  phi_engine.hexa             Phi 연산 (IIT proxy+frustration+scaling, n6 5/5)
  topology.hexa               토폴로지 (ring+complete+star+small-world, n6 5/5)
  runtime/                    CLI+Runtime (15 .hexa, entrypoint=anima_runtime.hexa)
  verification/               cvf.hexa (7조건) + byte_emergence.hexa (창발)
  conformance_checklist.md    18/18 골화 체크리스트
  asset_registry.md           MCTED 자산 분류
  prerequisites.md            학습 사전조건
  folder_structure.md         레이아웃 규약
  roadmap.md                  진행 상태

모델 연결:
  CLM (ConsciousLM):  checkpoints/conscious-lm/READY 마커 필요
  ALM (AnimaLM):      checkpoints/animalm/READY 마커 필요
  Pure (기본):         마커 없으면 pure 디코더 자동 선택
  select_decoder():    hub.hexa marker_present() → 자동 판별

자연발화 모드:
  --ticks N            N step 의식 루프 (입력 없이 자발 활동)
  --emit PATH          의식 상태 JSON 출력 (auto-utterance 파이프라인)
  --keyboard           CLI 대화 (REPL)
  --validate-hub       48모듈 등록 검증

rules:
  - L0 골화 파일 수정 금지
  - 법칙 추가는 config/consciousness_laws.json 만 (SSOT)
  - .hexa 단일 언어 (R1)
  - 허브 검증 통과 없이 커밋 금지
  - AN7 Core = CLI 전용 — 모듈 코드 진입 금지
