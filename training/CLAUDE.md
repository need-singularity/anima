# training/ — AnimaLM/GoldenMoE fine-tune

root: 메인 (train_models/conscious_lm.hexa, train_v9-v11.py, train_anima_lm.py) 는 프로젝트 루트

contents:
  finetune_animalm.py     오리지널 (LoRA)
  finetune_animalm_v2.py  V2 tension-verified
  finetune_animalm_v3.py  V3 Instruct + last 8 layers
  finetune_animalm_v4.py  V4 Savant + parallel PureField
  finetune_golden_moe.py  Golden MoE (1/e zone ratio)

rules:
  - H100 전용 (A100 = runtime/inference)
  - data/param 변경 → step 0 재시작, --resume 금지
  - 체크포인트 디렉토리 신규 (오염 방지)

parent: /CLAUDE.md
