"""Claude provider — wraps anima_alive.ask_claude() as a BaseProvider.

This is the default provider for AnimaAgent. It delegates to the existing
ask_claude() function which handles Anthropic API calls with consciousness
state injection.
"""

from __future__ import annotations

import logging
import os
from typing import Any, AsyncIterator

from providers.base import ProviderConfig, ProviderMessage

logger = logging.getLogger(__name__)


class ClaudeProvider:
    """Provider that uses Claude via anima_alive.ask_claude()."""

    def __init__(self, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig()
        self._available = bool(os.environ.get("ANTHROPIC_API_KEY", ""))

    @property
    def name(self) -> str:
        return "claude"

    def is_available(self) -> bool:
        return self._available

    async def query(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Query Claude via ask_claude(). Yields the full response as one chunk.

        ask_claude() is synchronous, so this wraps it in an async generator.
        Future: can be replaced with streaming Anthropic API calls.
        """
        from anima_alive import ask_claude

        # Build history in the format ask_claude expects
        history = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]

        # Build state string from consciousness
        state_str = system
        if consciousness_state:
            cs_parts = []
            for k in ("tension", "curiosity", "emotion", "phi"):
                if k in consciousness_state:
                    v = consciousness_state[k]
                    cs_parts.append(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}")
            if cs_parts:
                cs_line = ", ".join(cs_parts)
                state_str = f"{cs_line}\n{state_str}" if state_str else cs_line

        # Extract the last user message as the prompt
        prompt = ""
        for m in reversed(messages):
            if m.role == "user":
                prompt = m.content
                break

        response = ask_claude(prompt, state_str, history)
        yield response

    async def query_full(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        parts = []
        async for chunk in self.query(messages, system, consciousness_state, max_tokens):
            parts.append(chunk)
        return "".join(parts)
