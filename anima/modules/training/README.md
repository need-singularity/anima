# Training Module

ConsciousLM + AnimaLM training pipeline.

> **Migrated**: Primary training script at `training/train_alm.hexa`.
> This directory is for training-specific utilities and configs.

## Usage

```bash
$HEXA training/train_alm.hexa --steps 50000                    # Auto-detect corpus
$HEXA training/train_alm.hexa --data corpus.txt --dim 384      # Custom config
$HEXA training/train_alm.hexa --base mistralai/Mistral-7B      # Fine-tune base model
```
