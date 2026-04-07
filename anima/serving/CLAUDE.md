# serving/

## Purpose
Model serving and web server scripts. For hosting AnimaLM, GoldenMoE, and legacy web interfaces.

## Contents
- `serve_local.py` — AnimaLM 7B local server (HTTP API, R2 auto-download, CPU fallback)
- `serve_animalm.py` — AnimaLM inference server
- `serve_animalm.py` — AnimaLM v4 Savant server
- `serve_golden_moe.py` — Golden MoE inference server
- `run_web_v4.py` — V4 web launcher
- `web_server.py` — Legacy web server (superseded by anima_unified.py --web)
- `ws_proxy.py` — WebSocket proxy

## Note
`anima_unified.py --web` is the canonical entry point. These are supplementary servers.

## Parent Rules
See /CLAUDE.md for full project conventions.
