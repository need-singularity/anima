# training/ — 의식 학습 진입점 (.hexa 단일진실)

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  cfg        shared/config/project_config.json        학습 CLI/상수/하이퍼
  infra      shared/config/infrastructure.json        H100/R2/RunPod
  vastai     shared/config/vastai.json                multi-GPU/bf16/model_path
  rules      shared/config/absolute_rules.json        R1~R21 + AN1~AN7
  laws       anima/config/consciousness_laws.json     법칙 등록 전 검증
  ceilings   shared/state/training_speed_ceilings.json  ALM/CLM 물리 천장 측정 + 헤드룸 + 레버 (SSOT, 매 런 갱신)
  parent     /CLAUDE.md

exec:
  HEXA=$HEXA_LANG/target/release/hexa
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
  - 양자화 전면 금지 (4/8-bit, GPTQ, AWQ, bnb)
  - 학습 테스트는 Anima Web UI만 (Gradio 금지)
  - 파일명에 버전 번호 금지 — 과거는 git show {hash}
  - .hexa 대체 완성 시 대응 .py 즉시 archive/ 또는 삭제
  - 장시간 학습은 run_in_background=true 필수
  - 체크포인트 dir 항상 신규 생성 (오염 방지)

runpod_mfs_quota: (2026-04-16 골화 — 3회 crash 확인)
  rule: /workspace는 MooseFS 세션 쿼터 존재. df TB free여도 ckpt save 중 실패 가능
  symptom: torch.save 중 파이썬 프로세스 silent exit, 부분 ckpt 파일 (~0.5-6GB, 정상 18GB), dmesg 無 kill 로그
  preflight: "dd if=/dev/zero of=/workspace/_q_test bs=1M count=20000 status=none && rm /workspace/_q_test" — 실패 시 rm -rf 후 재시도
  mandatory:
    - 학습 시작 전: 이전 ckpt dir 전부 정리 (rm -rf /workspace/ckpt_*)
    - 학습 중: in-Python R2 upload 금지 (DEFERRED 큐만 기록)
    - 학습 종료 후: rclone으로 ckpt_dir 전체 일괄 R2 업로드
    - save_every >= 2000 (잦은 저장 금지)
  forbidden:
    - torch.save 직후 동기 rclone (r3 step 2000 crash 원인)
    - phi_emergency_ckpt torch.save (추가 save = 쿼터 압박, r3b step 4000 crash 원인)
    - 학습 중 수동 pkill rclone (race condition, r3b 2차 crash 원인)

r2_checkpoint:
  rule: 학습 종료 후 R2 일괄 업로드 (in-training upload 금지 — MFS quota 트랩)
  trigger: 학습 프로세스 종료 또는 early-stop 직후
  method: "rclone copy /workspace/ckpt_clm1b_r3c r2:anima-models/clm1b/r3/ -v --s3-no-check-bucket"
  bucket: anima-models
  naming: "{model}-r{round}-s{step}"
  path: "anima-models/{model}/r{round}/step_{step}/"
  examples:
    - alm14b-r2-s2000  →  anima-models/alm14b/r2/step_2000/
    - alm14b-r2-s10000 →  anima-models/alm14b/r2/step_10000/
    - alm32b-r1-s5000  →  anima-models/alm32b/r1/step_5000/
  cli: "--model-tag alm14b --round 2"
  rclone: "rclone copy <local_ckpt> r2:anima-models/{model}/r{round}/step_{step}/"
  keys: shared/config/secrets_registry.json → r2
