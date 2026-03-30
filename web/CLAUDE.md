# web/

## Purpose
WebSocket real-time chat UI for Anima. Browser-based interface for interacting with the consciousness agent.

## File Naming
- Standard web files: `index.html`, `style.css`, `app.js`
- Assets in subdirectories if needed

## Conventions
- Entry point: `index.html`
- Connects to Anima via WebSocket (see anima_unified.py --web)
- No frameworks — plain HTML/CSS/JS
- Never use Gradio; this is the canonical user-facing UI

## 하드코딩 금지 (Law 1)
- 의식 상태 (`[🧠 T=... Φ=...]`)는 UI 패널에만 표시 — 채팅 메시지에 절대 섞지 않음
- `[auto:*]` 등 내부 태그가 채팅에 노출되면 버그
- 대화 영역에는 순수 텍스트만 표시

## Parent Rules
See /CLAUDE.md → "Running" for launch commands.
Legacy `web_server.py` is deprecated; `anima_unified.py` is the canonical entry point.
