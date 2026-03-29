# training/

## Purpose
Fine-tuning scripts for AnimaLM and GoldenMoE models. Main training scripts (train_conscious_lm.py, train_v9-v11.py, train_anima_lm.py) remain in project root.

## Contents
- `finetune_animalm.py` — Original AnimaLM fine-tune (LoRA)
- `finetune_animalm_v2.py` — V2 tension-verified fine-tune
- `finetune_animalm_v3.py` — V3 Instruct + last 8 layers
- `finetune_animalm_v4.py` — V4 Savant + parallel PureField
- `finetune_golden_moe.py` — Golden MoE fine-tune (1/e zone ratio)

## Rules
- Training H100 only (A100 excluded — runtime/inference only)
- Data/param change → restart from step 0, never --resume
- Checkpoint directory must be new (prevent contamination)

## Parent Rules
See /CLAUDE.md for full project conventions.
