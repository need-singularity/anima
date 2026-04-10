# data/ — 런타임/코퍼스/실험 출력

gitignored: 커밋 금지

naming:
  {model}_{step}.pt  또는  {exp}_{date}.pt
  corpus.txt, {name}_corpus.txt
  {exp}_{date}.log

rules:
  - gitignored, 대용량 금지
  - R2 sync via cloud_sync.py
  - secrets/credentials/.env 절대 금지

parent: /CLAUDE.md → "Training Tools"
