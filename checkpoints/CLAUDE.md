# checkpoints/

## Purpose
Trained model checkpoints. Large binary files — do NOT commit to git.

## Structure
- `conscious_lm_4m_final.pt` — ConsciousLM 4M (Φ=4.12, 12 cells)
- `conscious_lm_100m_final.pt` — ConsciousLM 100M (Φ=2.607, 3 cells)
- `clm_v10/` — v10 FUSE-3 Trinity training checkpoints
- `clm_v11/` — v11 Hexad training checkpoints
- `animalm/` — AnimaLM fine-tune checkpoints

## Rules
- These files are in .gitignore
- Use cloud_sync.py for R2 backup
- Never overwrite checkpoints without renaming — contamination risk

## Parent Rules
See /CLAUDE.md for full project conventions.
