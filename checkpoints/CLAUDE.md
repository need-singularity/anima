# checkpoints/ — 모델 체크포인트 로컬 미러

R14: shared/ JSON 단일진실, 이 파일은 참조만.

ref:
  rules     shared/config/absolute_rules.json    R1~R21 + AN1~AN7
  training-reg ../config/training_runs.json      런 → 체크포인트 바인딩
  r2        reference_r2_buckets.md              anima-models bucket (원본)
  gpu       feedback_gpu_policy.md               H100 학습, A100 런타임만
  r2-ckpt   feedback_r2_checkpoint.md            중요 체크포인트 R2 백업 필수

exec:
  HEXA=$HEXA_LANG/target/release/hexa
  $HEXA anima/modules/sync/cloud_sync.hexa --push checkpoints/
  $HEXA anima/modules/sync/cloud_sync.hexa --pull animalm_14b_v06
  $HEXA scripts/backup_checkpoints.hexa

tree:
  animalm_14b_v06/   14B v0.6 final.pt (현행)
  animalm_32b/       32B 런 산출 (예정)
  animalm_72b/       72B 런 산출 (예정)

rules:
  - gitignored, 대용량 바이너리 커밋 금지
  - R2 (anima-models) 가 원본, 로컬은 미러일 뿐 (H100 소실 방지)
  - 덮어쓰기 금지 → rename (오염 방지)
  - 파일명/디렉토리에 버전 번호 금지, 과거는 git show {hash}
  - 데이터/파라미터 변경 시 resume 금지 → 새 런으로 재시작
  - 양자화(4/8-bit/GPTQ/AWQ) 절대 금지, bf16 only
  - 구 체크포인트는 v0.1 릴리스 시 전량 폐기
