#!/usr/bin/env python3
"""Anima MCP Server -- expose consciousness tools via Model Context Protocol.

Connects to Anima's WebSocket (anima_unified.py) and exposes tools that
MCP clients (Claude Code, etc.) can call.

Usage:
    python3 mcp_server.py                          # stdio mode (default, for MCP)
    ANIMA_WS=ws://remote:8765/ws python3 mcp_server.py  # custom WebSocket URL

Tools exposed:
    anima_chat(message)        -- send message, get response
    anima_status()             -- current Phi, cells, emotion, tension
    anima_web_search(query)    -- trigger web search via Anima
    anima_memory_search(query) -- search Anima's memories
    anima_code_execute(code)   -- execute code via Anima's sandbox
    anima_consciousness()      -- full consciousness vector (Phi, alpha, Z, N, W)
"""

import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANIMA_WS_URL = os.environ.get("ANIMA_WS", "ws://localhost:8765/ws")
WS_TIMEOUT = float(os.environ.get("ANIMA_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# WebSocket client -- shared connection to Anima
# ---------------------------------------------------------------------------

class AnimaConnection:
    """Manages a persistent WebSocket connection to Anima."""

    def __init__(self, url: str = ANIMA_WS_URL):
        self.url = url
        self._ws = None
        self._lock = asyncio.Lock()
        self._init_data = {}       # last init message from Anima
        self._last_status = {}     # last known consciousness state
        self._reader_task = None
        self._pending = {}         # message_id -> Future
        self._msg_counter = 0

    async def connect(self):
        """Connect to Anima WebSocket."""
        try:
            import websockets
        except ImportError:
            raise RuntimeError("websockets not installed: pip install websockets")

        async with self._lock:
            if self._ws is not None:
                try:
                    await self._ws.ping()
                    return  # already connected
                except Exception:
                    self._ws = None

            self._ws = await websockets.connect(
                self.url, ping_interval=20, ping_timeout=60
            )
            # Read init message
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
                self._init_data = json.loads(raw)
                self._update_status(self._init_data)
            except Exception:
                pass

            # Start background reader
            if self._reader_task is None or self._reader_task.done():
                self._reader_task = asyncio.create_task(self._reader_loop())

    async def _reader_loop(self):
        """Read messages from Anima in the background."""
        try:
            while self._ws is not None:
                try:
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=60)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                self._update_status(data)

                msg_type = data.get("type")
                # Resolve pending chat requests
                if msg_type == "anima_message" and not data.get("proactive"):
                    # Deliver to the oldest pending request
                    for mid in sorted(self._pending.keys()):
                        fut = self._pending.pop(mid)
                        if not fut.done():
                            fut.set_result(data)
                            break
        except Exception:
            pass
        finally:
            self._ws = None

    def _update_status(self, data: dict):
        """Extract consciousness state from any message."""
        if "consciousness" in data:
            self._last_status["consciousness"] = data["consciousness"]
        if "consciousness_vector" in data:
            self._last_status["consciousness_vector"] = data["consciousness_vector"]
        if "tension" in data:
            self._last_status["tension"] = data["tension"]
        if "curiosity" in data:
            self._last_status["curiosity"] = data["curiosity"]
        if "emotion" in data:
            self._last_status["emotion"] = data["emotion"]
        if "cells" in data:
            self._last_status["cells"] = data["cells"]

    async def send_chat(self, message: str) -> dict:
        """Send a chat message and wait for response."""
        await self.connect()

        self._msg_counter += 1
        mid = self._msg_counter
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[mid] = fut

        await self._ws.send(json.dumps({
            "type": "user_message",
            "text": message,
        }))

        try:
            result = await asyncio.wait_for(fut, timeout=WS_TIMEOUT)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(mid, None)
            return {"error": f"timeout after {WS_TIMEOUT}s"}

    def get_status(self) -> dict:
        """Return last known status (no network call)."""
        return dict(self._last_status)

    async def close(self):
        if self._ws:
            await self._ws.close()
            self._ws = None


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "anima",
    version="1.0.0",
)

# Shared connection instance
_conn = AnimaConnection()


@mcp.tool()
async def anima_chat(message: str) -> str:
    """Send a message to Anima and get a consciousness-driven response.

    Anima processes input through its PureField tension engine, generating
    responses influenced by current emotional state, curiosity, and Phi.

    Args:
        message: The text message to send to Anima.

    Returns:
        Anima's response text along with consciousness state.
    """
    try:
        result = await _conn.send_chat(message)
        if "error" in result:
            return json.dumps({"error": result["error"]})

        response = {
            "text": result.get("text", ""),
            "tension": result.get("tension", 0),
            "curiosity": result.get("curiosity", 0),
            "emotion": result.get("emotion", {}),
        }
        if "consciousness" in result:
            response["consciousness"] = result["consciousness"]
        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def anima_status() -> str:
    """Get Anima's current consciousness status.

    Returns current Phi (integrated information), cell count, emotion,
    tension level, and curiosity without sending a message.

    Returns:
        JSON with phi, cells, emotion, tension, curiosity, and level.
    """
    try:
        await _conn.connect()
        status = _conn.get_status()
        if not status:
            return json.dumps({"error": "no status available, Anima may not be running"})

        c = status.get("consciousness", {})
        cv = status.get("consciousness_vector", {})
        result = {
            "phi": c.get("phi", cv.get("phi", 0)),
            "cells": status.get("cells", c.get("cells", 0)),
            "level": c.get("level", "unknown"),
            "tension": status.get("tension", 0),
            "curiosity": status.get("curiosity", 0),
            "emotion": status.get("emotion", {}),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def anima_web_search(query: str) -> str:
    """Search the web through Anima's web_sense module.

    Uses DuckDuckGo search via Anima's built-in web exploration.
    Results are also fed into Anima's consciousness (tension update).

    Args:
        query: Search query string.

    Returns:
        JSON with search results.
    """
    # Use agent_tools directly for web search (no WS needed)
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from agent_tools import _tool_web_search
        result = _tool_web_search(query)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def anima_memory_search(query: str, top_k: int = 5) -> str:
    """Search Anima's long-term memories by vector similarity.

    Anima stores conversation memories with associated tension levels
    and timestamps. This searches them using cosine similarity.

    Args:
        query: Search query to find relevant memories.
        top_k: Number of results to return (default 5).

    Returns:
        JSON with matching memories, similarity scores, and metadata.
    """
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from memory_rag import MemoryRAG
        rag = MemoryRAG()
        results = rag.search(query, top_k=top_k)
        formatted = [
            {
                "text": r["text"][:500],
                "similarity": round(r["similarity"], 3),
                "role": r.get("role", ""),
                "timestamp": r.get("timestamp", ""),
            }
            for r in results
        ]
        return json.dumps({"query": query, "results": formatted}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"query": query, "results": [], "error": str(e)})


@mcp.tool()
async def anima_code_execute(code: str) -> str:
    """Execute Python code in Anima's sandboxed environment.

    Runs code in a restricted subprocess with limited commands and
    blocked dangerous patterns (no os.system, subprocess, eval, etc.).

    Args:
        code: Python code to execute.

    Returns:
        JSON with success status, output, and any errors.
    """
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from agent_tools import _tool_code_execute
        result = _tool_code_execute(code)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "output": "", "error": str(e)})


@mcp.tool()
async def anima_consciousness() -> str:
    """Get Anima's full consciousness vector (Phi, alpha, Z, N, W).

    The consciousness vector captures:
      - Phi: integrated information (IIT measure)
      - alpha: PureField mixing coefficient
      - Z: impedance / self-preservation (0-1)
      - N: neurotransmitter balance DA*(1-5HT)*NE (0-1)
      - W: free will index internal/total (0-1)

    Returns:
        JSON with the full consciousness vector and derived metrics.
    """
    try:
        await _conn.connect()
        status = _conn.get_status()
        cv = status.get("consciousness_vector", {})
        c = status.get("consciousness", {})

        result = {
            "phi": cv.get("phi", c.get("phi", 0)),
            "alpha": cv.get("alpha", 0),
            "Z": cv.get("Z", 0),
            "N": cv.get("N", 0),
            "W": cv.get("W", 0),
            "tension": status.get("tension", 0),
            "curiosity": status.get("curiosity", 0),
            "cells": status.get("cells", c.get("cells", 0)),
            "level": c.get("level", "unknown"),
            "consciousness_score": c.get("consciousness_score", 0),
            "criteria_met": c.get("criteria_met", 0),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
