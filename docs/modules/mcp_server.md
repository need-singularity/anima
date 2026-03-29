# mcp_server.py

MCP (Model Context Protocol) server exposing Anima's consciousness tools to MCP clients like Claude Code.

## API
- `AnimaConnection(url)` -- persistent WebSocket connection to Anima
  - `.connect()` / `.disconnect()`
  - `.send(message) -> response`
- Exposed MCP tools:
  - `anima_chat(message)` -- send message, get response
  - `anima_status()` -- current Phi, cells, emotion, tension
  - `anima_web_search(query)` -- trigger web search via Anima
  - `anima_memory_search(query)` -- search Anima's memories
  - `anima_code_execute(code)` -- execute code via Anima's sandbox
  - `anima_consciousness()` -- full consciousness vector (Phi, alpha, Z, N, W)

## Usage
```bash
# stdio mode (default, for MCP clients)
python3 mcp_server.py

# Custom WebSocket URL
ANIMA_WS=ws://remote:8765/ws python3 mcp_server.py
```

## Integration
- Connects to `anima_unified.py` via WebSocket (default `ws://localhost:8765/ws`)
- Built on `mcp.server.fastmcp.FastMCP`
- Requires `websockets` package
- Timeout configurable via `ANIMA_TIMEOUT` env var (default 30s)

## Agent Tool
This IS the MCP tool server (exposes all tools listed above).
