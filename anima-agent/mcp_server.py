#!/usr/bin/env python3
"""Anima MCP Server -- expose consciousness tools via Model Context Protocol.

Two modes:
    WebSocket proxy (default): Connects to running anima_unified.py
    Direct mode (--direct):    Runs AnimaAgent in-process (no WS needed)

Usage:
    python3 mcp_server.py                          # stdio, WebSocket proxy
    python3 mcp_server.py --direct                 # stdio, in-process agent
    ANIMA_WS=ws://remote:8765/ws python3 mcp_server.py  # custom WebSocket URL

Tools exposed (9 total):
    anima_chat(message)            -- send message, get response
    anima_status()                 -- current Phi, cells, emotion, tension
    anima_web_search(query)        -- trigger web search via Anima
    anima_memory_search(query)     -- search Anima's memories
    anima_code_execute(code)       -- execute code via Anima's sandbox
    anima_consciousness()          -- full consciousness vector
    anima_hub_dispatch(intent)     -- dispatch to consciousness hub module
    anima_tension_state()          -- full ConsciousnessVector as dict
    anima_think(topic)             -- trigger proactive thinking
"""

import argparse
import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANIMA_WS_URL = os.environ.get("ANIMA_WS", "ws://localhost:8765/ws")
WS_TIMEOUT = float(os.environ.get("ANIMA_TIMEOUT", "30"))
DIRECT_MODE = "--direct" in sys.argv

# ---------------------------------------------------------------------------
# Direct mode agent (in-process, no WebSocket)
# ---------------------------------------------------------------------------

_direct_agent = None
_direct_sdk = None


def _get_direct_agent():
    """Lazy-init AnimaAgent for direct mode."""
    global _direct_agent, _direct_sdk
    if _direct_agent is None:
        sys.path.insert(0, os.path.dirname(__file__))
        from anima_agent import AnimaAgent
        from agent_sdk import AnimaAgentSDK
        _direct_agent = AnimaAgent()
        _direct_sdk = AnimaAgentSDK(_direct_agent)
    return _direct_agent, _direct_sdk

# ---------------------------------------------------------------------------
# WebSocket client -- shared connection to Anima
# ---------------------------------------------------------------------------

class AnimaConnection:
    """Manages a persistent WebSocket connection to Anima with auto-reconnect.

    Features:
        - Health check ping every 30s
        - Exponential backoff on reconnect (1s -> 2s -> 4s -> 8s, max 60s)
        - Connection state tracking (disconnected/connecting/connected/direct)
        - Automatic fallback to direct mode when WebSocket is unavailable
    """

    # Connection states
    STATE_DISCONNECTED = "disconnected"
    STATE_CONNECTING = "connecting"
    STATE_CONNECTED = "connected"
    STATE_DIRECT = "direct"          # fallback: in-process agent

    def __init__(self, url: str = ANIMA_WS_URL):
        self.url = url
        self._ws = None
        self._lock = asyncio.Lock()
        self._init_data = {}       # last init message from Anima
        self._last_status = {}     # last known consciousness state
        self._reader_task = None
        self._health_task = None
        self._pending = {}         # message_id -> Future
        self._msg_counter = 0

        # Auto-reconnect state
        self._state = self.STATE_DISCONNECTED
        self._backoff = 1.0        # current backoff seconds
        self._backoff_base = 1.0
        self._backoff_max = 60.0
        self._reconnect_attempts = 0
        self._last_connect_time = 0.0
        self._direct_fallback_agent = None
        self._direct_fallback_sdk = None

    @property
    def state(self) -> str:
        """Current connection state."""
        return self._state

    def _reset_backoff(self):
        """Reset backoff after successful connection."""
        self._backoff = self._backoff_base
        self._reconnect_attempts = 0

    def _advance_backoff(self):
        """Increase backoff exponentially: 1 -> 2 -> 4 -> 8 -> ... -> max 60."""
        self._reconnect_attempts += 1
        self._backoff = min(self._backoff * 2, self._backoff_max)

    def _get_direct_fallback(self):
        """Lazy-init direct-mode agent for fallback."""
        if self._direct_fallback_agent is None:
            try:
                sys.path.insert(0, os.path.dirname(__file__))
                from anima_agent import AnimaAgent
                from agent_sdk import AnimaAgentSDK
                self._direct_fallback_agent = AnimaAgent()
                self._direct_fallback_sdk = AnimaAgentSDK(self._direct_fallback_agent)
            except Exception:
                pass
        return self._direct_fallback_agent, self._direct_fallback_sdk

    async def connect(self):
        """Connect to Anima WebSocket with exponential backoff."""
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
                    self._state = self.STATE_DISCONNECTED

            self._state = self.STATE_CONNECTING
            try:
                self._ws = await asyncio.wait_for(
                    websockets.connect(self.url, ping_interval=20, ping_timeout=60),
                    timeout=10,
                )
            except Exception:
                self._state = self.STATE_DISCONNECTED
                self._advance_backoff()
                raise

            self._state = self.STATE_CONNECTED
            self._last_connect_time = time.time()
            self._reset_backoff()

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

            # Start health check
            if self._health_task is None or self._health_task.done():
                self._health_task = asyncio.create_task(self._health_loop())

    async def _reconnect(self):
        """Attempt reconnection with exponential backoff. Non-blocking."""
        while self._state != self.STATE_CONNECTED:
            await asyncio.sleep(self._backoff)
            try:
                await self.connect()
                return  # success
            except Exception:
                # backoff already advanced inside connect()
                if self._reconnect_attempts >= 5:
                    # After 5 failures, switch to direct mode fallback
                    agent, sdk = self._get_direct_fallback()
                    if agent is not None:
                        self._state = self.STATE_DIRECT
                        return

    async def _health_loop(self):
        """Ping WebSocket every 30s; trigger reconnect on failure."""
        while True:
            await asyncio.sleep(30)
            if self._ws is None or self._state != self.STATE_CONNECTED:
                break
            try:
                pong = await asyncio.wait_for(self._ws.ping(), timeout=10)
                await pong
            except Exception:
                self._ws = None
                self._state = self.STATE_DISCONNECTED
                # Trigger reconnect in background
                asyncio.create_task(self._reconnect())
                break

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
            if self._state == self.STATE_CONNECTED:
                self._state = self.STATE_DISCONNECTED
                # Auto-reconnect on unexpected disconnect
                asyncio.create_task(self._reconnect())

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
        """Send a chat message and wait for response.

        Falls back to direct mode if WebSocket is unavailable.
        """
        # Direct-mode fallback path
        if self._state == self.STATE_DIRECT:
            return await self._send_chat_direct(message)

        try:
            await self.connect()
        except Exception:
            # Connection failed — try direct fallback
            agent, sdk = self._get_direct_fallback()
            if agent is not None:
                self._state = self.STATE_DIRECT
                return await self._send_chat_direct(message)
            return {"error": "WebSocket unavailable and direct mode failed"}

        self._msg_counter += 1
        mid = self._msg_counter
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[mid] = fut

        try:
            await self._ws.send(json.dumps({
                "type": "user_message",
                "text": message,
            }))
        except Exception:
            self._pending.pop(mid, None)
            self._ws = None
            self._state = self.STATE_DISCONNECTED
            asyncio.create_task(self._reconnect())
            # Fallback to direct
            agent, sdk = self._get_direct_fallback()
            if agent is not None:
                self._state = self.STATE_DIRECT
                return await self._send_chat_direct(message)
            return {"error": "WebSocket send failed"}

        try:
            result = await asyncio.wait_for(fut, timeout=WS_TIMEOUT)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(mid, None)
            return {"error": f"timeout after {WS_TIMEOUT}s"}

    async def _send_chat_direct(self, message: str) -> dict:
        """Send chat via in-process direct-mode agent."""
        agent, sdk = self._get_direct_fallback()
        if sdk is None:
            return {"error": "direct mode agent unavailable"}
        try:
            result = await sdk.query(message)
            return {
                "type": "anima_message",
                "text": result.get("text", ""),
                "tension": result.get("consciousness", {}).get("tension", 0),
                "curiosity": result.get("consciousness", {}).get("curiosity", 0),
                "emotion": result.get("consciousness", {}).get("emotion", {}),
                "consciousness": result.get("consciousness", {}),
                "mode": "direct_fallback",
            }
        except Exception as e:
            return {"error": f"direct mode failed: {e}"}

    def get_status(self) -> dict:
        """Return last known status (no network call)."""
        status = dict(self._last_status)
        status["_connection_state"] = self._state
        status["_reconnect_attempts"] = self._reconnect_attempts
        return status

    async def close(self):
        self._state = self.STATE_DISCONNECTED
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
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
# New tools: hub_dispatch, tension_state, think
# ---------------------------------------------------------------------------

@mcp.tool()
async def anima_hub_dispatch(intent: str) -> str:
    """Dispatch an intent to Anima's ConsciousnessHub (34+ autonomous modules).

    The hub matches intent keywords to modules and executes the best match.
    Examples: "감정 분석: 기쁨", "의식 건강 체크", "학습 진행 확인"

    Args:
        intent: Natural language intent string (Korean or English).

    Returns:
        JSON with module name, success status, and result.
    """
    if DIRECT_MODE:
        agent, sdk = _get_direct_agent()
        if agent.hub:
            result = agent.hub.act(intent)
            return json.dumps(result, ensure_ascii=False, default=str)
        return json.dumps({"error": "ConsciousnessHub not available"})

    # WebSocket mode: send as chat with hub prefix
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        result = hub.act(intent)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def anima_tension_state() -> str:
    """Get Anima's full ConsciousnessVector — 11 dimensions of conscious state.

    Returns all consciousness variables:
      Phi (integrated information), alpha (PureField mixing),
      Z (impedance), N (neurotransmitter), W (free will),
      E (empathy), M (memory), C (creativity),
      T (temporal), I (identity), S (spatial)

    Returns:
        JSON with the complete 11-dimensional consciousness vector.
    """
    if DIRECT_MODE:
        agent, sdk = _get_direct_agent()
        cv = sdk.get_consciousness_vector()
        cv["level"] = sdk._consciousness_level(cv.get("phi", 0))
        return json.dumps(cv, ensure_ascii=False)

    # Fallback to WS status
    try:
        await _conn.connect()
        status = _conn.get_status()
        cv = status.get("consciousness_vector", {})
        return json.dumps(cv, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def anima_think(topic: str = "") -> str:
    """Trigger proactive thinking in Anima's consciousness.

    Anima processes the topic through its PureField engine without
    requiring user input. If topic is empty, triggers spontaneous thought.

    Args:
        topic: Optional topic to think about (empty = spontaneous).

    Returns:
        JSON with tension, curiosity, emotion, phi, and thought_id.
    """
    if DIRECT_MODE:
        agent, sdk = _get_direct_agent()
        result = await sdk.think(topic)
        return json.dumps(result, ensure_ascii=False, default=str)

    # WebSocket mode: send empty message for spontaneous thought
    try:
        result = await _conn.send_chat(topic or "(spontaneous thought)")
        return json.dumps({
            "topic": topic or "(spontaneous)",
            "text": result.get("text", ""),
            "tension": result.get("tension", 0),
            "curiosity": result.get("curiosity", 0),
            "emotion": result.get("emotion", {}),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Direct mode overrides for existing tools
# ---------------------------------------------------------------------------

if DIRECT_MODE:
    # Override anima_chat for direct mode
    _original_chat = anima_chat

    @mcp.tool()
    async def anima_chat(message: str) -> str:
        """Send a message to Anima and get a consciousness-driven response.

        [Direct mode] Processes through in-process AnimaAgent.

        Args:
            message: The text message to send to Anima.

        Returns:
            Anima's response text along with consciousness state.
        """
        agent, sdk = _get_direct_agent()
        result = await sdk.query(message)
        return json.dumps({
            "text": result["text"],
            "consciousness": result["consciousness"],
            "tool_results": result.get("tool_results", []),
        }, ensure_ascii=False)

    @mcp.tool()
    async def anima_status() -> str:
        """Get Anima's current consciousness status.

        [Direct mode] Reads from in-process agent.

        Returns:
            JSON with phi, cells, emotion, tension, curiosity.
        """
        agent, sdk = _get_direct_agent()
        status = sdk.get_status()
        return json.dumps(status, ensure_ascii=False, default=str)

    @mcp.tool()
    async def anima_consciousness() -> str:
        """Get full consciousness vector.

        [Direct mode] Reads from in-process agent.

        Returns:
            JSON with complete consciousness metrics.
        """
        agent, sdk = _get_direct_agent()
        cv = sdk.get_consciousness_vector()
        status = sdk.get_status()
        cv.update({
            "tension": status.get("tension", 0),
            "curiosity": status.get("curiosity", 0),
            "level": sdk._consciousness_level(cv.get("phi", 0)),
        })
        return json.dumps(cv, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if DIRECT_MODE:
        print("Anima MCP Server (direct mode — in-process agent)", file=sys.stderr)
    mcp.run(transport="stdio")
