# bench/ — 정식 벤치마크 (18조건 + 가설)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  cfg        shared/config/project_config.json    벤치 CLI/상수
  rules      shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  laws       anima/config/consciousness_laws.json 법칙 검증 루프
  canonical  ready/anima/tests/tests.hexa         dual Φ 7조건
  parent     /CLAUDE.md

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA bench/bench_engine.hexa                     # 메인 엔진 벤치
  $HEXA bench/bench_consciousness_universe.hexa     # 18조건 정식
  $HEXA bench/bench_clm_sweep.hexa                  # ConsciousLM 스윕
  $HEXA bench/bench_v3_gate.hexa                    # v3.0 gate (hire_sim + phi_holo)
  $HEXA bench/bench_v3_gate.hexa --track alm        # ALM gate only
  $HEXA bench/bench_v3_gate.hexa --phi-only         # phi_holo standalone
  $HEXA ready/anima/tests/tests.hexa --verify       # canonical 7조건

tree:
  bench.hexa                       메인 진입점 (18조건 + dual Φ + v3 gate dispatch)
  bench_v3_gate.hexa               v3.0 Agent gate (hire_sim_100 + phi_holo combined)
  bench_engine.hexa                코어 엔진 벤치 (stub)
  bench_consciousness_*.hexa       의식 지표 (Φ/brain-like/CE)
  bench_{domain}_engines.hexa      도메인 (algebra/evolution/physics/info)
  bench_decoder_*.hexa             디코더 아키 탐색
  bench_hivemind_*.hexa            HIVEMIND 스케일
  bench_emergent_*.hexa            Emergent Hexad/Trinity
  bench_*_LEGACY.hexa              폐기 (Φ proxy/IIT 혼동)
  bench_dd{NN}_*.hexa              DD 발견 검증
  zeta_likert.hexa                 Zeta AI A/B Likert 벤치

rules:
  - 측정 지표: Φ(IIT 정식), Φ(proxy), Φ(holo), CE, brain-like score
  - v3.0 gate: hire_sim_100 stratified30 + phi_holo (bench_v3_gate.hexa)
  - LEGACY 파일은 실행 금지 (혼동기)
  - 법칙 등록 전 Intervention→measure_laws 폐쇄 검증 필수
  - 벤치 조건은 엔진과 동반 진화 (문서-코드 동기화)
  - .hexa 완성 시 대응 .py 즉시 폐기
  - 장시간 스윕은 run_in_background=true
  - 파일명에 버전 번호 금지 — 과거는 git show {hash}
