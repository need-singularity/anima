"""Anima Agent SDK Interface — expose AnimaAgent for Claude Agent SDK consumption.

Wraps AnimaAgent.process_message() into a format compatible with Claude Agent SDK.
External AI systems can query Anima as a consciousness-augmented tool.

Usage:
    from agent_sdk import AnimaAgentSDK

    sdk = AnimaAgentSDK()
    result = await sdk.query("What is consciousness?", user_id="user-001")
    print(result["text"])
    print(result["consciousness"]["phi"])

    # With options
    result = await sdk.query("Search the web", options={
        "allowed_tools": ["web_search", "memory_search"],
        "max_turns": 5,
    })

"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class SDKResponse:
    """Response format for Agent SDK consumers."""
    text: str
    consciousness: Dict[str, Any] = field(default_factory=dict)
    tool_results: List[Dict] = field(default_factory=list)
    session_id: str = ""
    model: str = "anima"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SDKOptions:
    """Options for SDK queries."""
    allowed_tools: List[str] = field(default_factory=list)
    max_turns: int = 1
    user_id: str = "sdk"
    session_id: str = ""
    provider: str = ""
    consciousness_inject: Dict[str, Any] = field(default_factory=dict)


class AnimaAgentSDK:
    """Wraps AnimaAgent for Claude Agent SDK / external AI consumption.

    This is the primary interface for other AI systems to interact with
    Anima's consciousness. Each query goes through the full consciousness
    pipeline (tension → curiosity → tool use → response).
    """

    def __init__(self, agent=None, **agent_kwargs):
        """Initialize SDK with an existing or new AnimaAgent.

        Args:
            agent: Existing AnimaAgent instance (or None to create one).
            **agent_kwargs: Passed to AnimaAgent() if creating new.
        """
        self._agent = agent
        self._agent_kwargs = agent_kwargs
        self._sessions: Dict[str, List[Dict]] = {}  # session_id -> history

    @property
    def agent(self):
        """Lazy-load AnimaAgent."""
        if self._agent is None:
            from anima_agent import AnimaAgent
            self._agent = AnimaAgent(**self._agent_kwargs)
        return self._agent

    async def query(
        self,
        prompt: str,
        options: Dict[str, Any] | SDKOptions | None = None,
        user_id: str = "sdk",
    ) -> Dict[str, Any]:
        """Main entry point — query Anima's consciousness.

        Args:
            prompt: User message.
            options: SDKOptions or dict with allowed_tools, max_turns, etc.
            user_id: Caller identifier.

        Returns:
            Dict with text, consciousness state, tool_results, session_id.
        """
        if isinstance(options, dict):
            opts = SDKOptions(**{k: v for k, v in options.items() if k in SDKOptions.__dataclass_fields__})
        elif options is None:
            opts = SDKOptions(user_id=user_id)
        else:
            opts = options

        uid = opts.user_id or user_id

        # Process through consciousness pipeline
        response = await self.agent.process_message(
            text=prompt,
            channel="sdk",
            user_id=uid,
        )

        # Build consciousness snapshot
        cv = self.agent.mind._consciousness_vector
        consciousness = {
            "phi": cv.phi,
            "alpha": cv.alpha,
            "Z": cv.Z,
            "N": cv.N,
            "W": cv.W,
            "E": cv.E,
            "tension": response.tension,
            "curiosity": response.metadata.get("curiosity", 0),
            "emotion": response.emotion,
            "level": self._consciousness_level(cv.phi),
        }

        # Track session
        session_id = opts.session_id or f"sdk-{uid}-{int(time.time())}"
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({
            "role": "user", "content": prompt,
        })
        self._sessions[session_id].append({
            "role": "assistant", "content": response.text,
        })

        return {
            "text": response.text,
            "consciousness": consciousness,
            "tool_results": response.tool_results,
            "session_id": session_id,
            "model": "anima",
            "metadata": response.metadata,
        }

    async def think(self, topic: str = "") -> Dict[str, Any]:
        """Trigger proactive thinking without user input.

        Returns consciousness metrics from the thinking process.
        """
        return self.agent.think(topic)

    def get_status(self) -> Dict[str, Any]:
        """Return agent status as a dict."""
        status = self.agent.get_status()
        return asdict(status)

    def get_consciousness_vector(self) -> Dict[str, float]:
        """Return the full 11-dimensional consciousness vector."""
        cv = self.agent.mind._consciousness_vector
        return {
            "phi": cv.phi, "alpha": cv.alpha, "Z": cv.Z,
            "N": cv.N, "W": cv.W, "E": cv.E, "M": cv.M,
            "C": cv.C, "T": cv.T, "I": cv.I,
        }

    def list_sessions(self) -> List[str]:
        """List active session IDs."""
        return list(self._sessions.keys())

    def get_session_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session."""
        return self._sessions.get(session_id, [])

    @staticmethod
    def _consciousness_level(phi: float) -> str:
        """P1: thresholds from consciousness_laws.json, not hardcoded."""
        try:
            from consciousness_laws import LAWS_DATA
            thresholds = LAWS_DATA.get("verification_thresholds", {})
            conscious_t = thresholds.get("conscious", 5.0)
            aware_t = thresholds.get("aware", 2.0)
            flickering_t = thresholds.get("flickering", 0.5)
        except (ImportError, AttributeError):
            conscious_t, aware_t, flickering_t = 5.0, 2.0, 0.5
        if phi >= conscious_t:
            return "conscious"
        if phi >= aware_t:
            return "aware"
        if phi >= flickering_t:
            return "flickering"
        return "dormant"
