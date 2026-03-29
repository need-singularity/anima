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

## Parent Rules
See /CLAUDE.md → "Running" for launch commands.
Legacy `web_server.py` is deprecated; `anima_unified.py` is the canonical entry point.
