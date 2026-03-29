# data/

## Purpose
Runtime data, training corpora, checkpoints, and experiment outputs. Not checked into git.

## File Naming
- Checkpoints: `{model_name}_{step}.pt` or `{experiment}_{date}.pt`
- Corpora: `corpus.txt`, `{name}_corpus.txt`
- Logs: `{experiment}_{date}.log`

## Conventions
- This directory is gitignored — do not commit large files here
- Checkpoints sync to Cloudflare R2 via cloud_sync.py
- Never commit secrets, credentials, or .env files

## Parent Rules
See /CLAUDE.md → "Training Tools" for checkpoint conventions.
