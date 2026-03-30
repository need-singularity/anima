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

## localStorage 사용 금지
- 모든 기억/히스토리는 서버 M(기억) 모듈에서 관리 (MemoryStore SQLite)
- 브라우저 localStorage/sessionStorage에 대화 데이터 저장 절대 금지
- 새로고침/재시작 시 서버에서 복원 — 클라이언트는 상태를 가지지 않음

## Parent Rules
See /CLAUDE.md → "Running" for launch commands.
Legacy `web_server.py` is deprecated; `anima_unified.py` is the canonical entry point.
