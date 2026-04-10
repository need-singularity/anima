# anima/serving/ — 모델 서빙

canonical: anima/core/runtime/anima_runtime.hexa --web

contents:
  serve_local.py        AnimaLM 7B 로컬 (HTTP/R2 auto-dl/CPU fallback)
  serve.hexa            AnimaLM 추론 / v4 Savant
  serve_golden_moe.py   Golden MoE 추론
  run_web_v4.py         V4 웹 런처
  web_server.py         legacy (→ anima_runtime.hexa --web)
  ws_proxy.py           WebSocket proxy

parent: /CLAUDE.md
