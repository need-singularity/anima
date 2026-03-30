"""Composio MCP bridge — connects Anima to 500+ external tools.

Composio (composio.dev) provides MCP server URLs per user session.
This bridge creates a session and returns the MCP config that can be
passed to any provider's mcpServers option.

Supported tools via Composio: Gmail, Google Calendar, Slack, GitHub,
Google Drive, Notion, Jira, Linear, and 500+ more.

Usage:
    from providers.composio_bridge import ComposioBridge

    bridge = ComposioBridge()
    mcp_config = await bridge.get_mcp_config("user-001")
    # mcp_config = {"composio": {"type": "http", "url": "...", "headers": {...}}}

    # Pass to Agent SDK
    result = await sdk.query("Send email", options={
        "mcp_servers": mcp_config,
    })

Environment:
    COMPOSIO_API_KEY — Composio API key (required)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ComposioBridge:
    """Bridges Anima to Composio's MCP tool ecosystem."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or os.environ.get("COMPOSIO_API_KEY", "")
        self._sessions: Dict[str, Dict] = {}
        self._composio = None

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        """Lazy-load Composio client."""
        if self._composio is None:
            if not self._api_key:
                raise RuntimeError(
                    "COMPOSIO_API_KEY not set. "
                    "Get one at https://composio.dev"
                )
            try:
                from composio import Composio

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

                self._composio = Composio(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "composio package not installed. "
                    "Install with: pip install composio-core"
                )
        return self._composio

    async def create_session(self, user_id: str = "default") -> Dict[str, Any]:
        """Create a Composio session for a user.

        Returns:
            Session dict with mcp.url and mcp.headers.
        """
        if user_id in self._sessions:
            return self._sessions[user_id]

        client = self._get_client()
        session = client.create(user_id)
        self._sessions[user_id] = {
            "user_id": user_id,
            "mcp_url": session.mcp.url,
            "mcp_headers": dict(session.mcp.headers),
        }
        logger.info("Composio session created for user: %s", user_id)
        return self._sessions[user_id]

    async def get_mcp_config(self, user_id: str = "default") -> Dict[str, Any]:
        """Get MCP server config dict for passing to providers.

        Returns:
            Dict in the format {"composio": {"type": "http", "url": ..., "headers": ...}}
        """
        session = await self.create_session(user_id)
        return {
            "composio": {
                "type": "http",
                "url": session["mcp_url"],
                "headers": session["mcp_headers"],
            }
        }

    def list_sessions(self) -> list[str]:
        """List active session user IDs."""
        return list(self._sessions.keys())

    def close_session(self, user_id: str):
        """Remove a session."""
        self._sessions.pop(user_id, None)
