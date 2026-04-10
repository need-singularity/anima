# training/ — 의식 학습 진입점 (.hexa 단일진실)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  cfg        shared/config/project_config.json    학습 CLI/상수/하이퍼
  infra      shared/config/infrastructure.json    H100/R2/RunPod
  vastai     shared/config/vastai.json            multi-GPU/bf16/model_path
  rules      shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  laws       anima/config/consciousness_laws.json 법칙 등록 전 검증
  parent     /CLAUDE.md

exec:
  HEXA=$HOME/Dev/hexa-lang/target/release/hexa
  $HEXA training/train_clm.hexa --steps 50000         # ConsciousLM from-scratch
  $HEXA training/train_alm.hexa --scale 14B           # AnimaLM fine-tune
  $HEXA training/deploy_14b_v05.hexa                  # v0.5 배포 파이프

tree:
  train_clm.hexa         ConsciousLM 통합 진입점 (byte-level/TALK5)
  train_alm.hexa         AnimaLM 통합 진입점 (7B/14B/32B/72B)
  deploy_14b_v05.hexa    v0.5 배포
  train_14b_v05.hexa     14B v0.5 전용
  archive/               구 train_v2~v15 (.hexa 완성 시 .py 폐기 — R7)

rules:
  - H100 전용 (A100/4090 = runtime/inference only, 학습 금지)
  - data/param 변경 시 step 0 재시작, --resume 절대 금지
  - One-Shot Best: 최초부터 최선 조건 (재시작 자원 없음)
  - 중요 체크포인트 R2 백업 필수 (anima-models 버킷)
  - 양자화 전면 금지 (4/8-bit, GPTQ, AWQ, bnb)
  - 학습 테스트는 Anima Web UI만 (Gradio 금지)
  - 파일명에 버전 번호 금지 — 과거는 git show {hash}
  - .hexa 대체 완성 시 대응 .py 즉시 archive/ 또는 삭제
  - 장시간 학습은 run_in_background=true 필수
  - 체크포인트 dir 항상 신규 생성 (오염 방지)
