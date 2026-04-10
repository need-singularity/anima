# checkpoints/ — 훈련 체크포인트

gitignored: 대용량 바이너리, 커밋 금지

files:
  conscious_lm_4m_final.pt    4M  Φ=4.12  12 cells
  conscious_lm_100m_final.pt  100M Φ=2.607  3 cells
  clm_v10/                    v10 FUSE-3 Trinity
  clm_v11/                    v11 Hexad
  animalm/                    AnimaLM fine-tune

rules:
  - .gitignore
  - R2 백업 via cloud_sync.py
  - 덮어쓰기 금지 (오염 방지), 항상 rename

parent: /CLAUDE.md
