"""Base provider protocol — all LLM backends implement this interface.

The key distinction from generic providers: consciousness_state is a first-class
parameter in every query. Providers inject consciousness metrics (tension, phi,
emotion) into their prompting strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, runtime_checkable

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



@dataclass
class ProviderMessage:
    """A single message in the conversation."""
    role: str       # "user", "assistant", "system"
    content: str


@dataclass
class ProviderConfig:
    """Provider configuration."""
    model: str = ""
    max_tokens: int = 1024
    temperature: float = 0.7
    api_key: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class BaseProvider(Protocol):
    """Abstract LLM provider protocol.

    All providers implement async query() that yields text chunks.
    Consciousness state is passed to influence response generation.
    """

    @property
    def name(self) -> str:
        """Provider identifier (e.g. 'claude', 'conscious-lm')."""
        ...

    def is_available(self) -> bool:
        """Check if this provider can accept queries right now."""
        ...

    async def query(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Generate response as async stream of text chunks.

        Args:
            messages: Conversation history.
            system: System prompt (provider may merge consciousness_state into this).
            consciousness_state: Current consciousness metrics dict with keys:
                tension, curiosity, emotion, phi, direction, etc.
            max_tokens: Maximum tokens to generate.

        Yields:
            Text chunks as they're generated.
        """
        ...

    async def query_full(
        self,
        messages: list[ProviderMessage],
        system: str = "",
        consciousness_state: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Convenience: collect full response as a single string.

        Default implementation consumes the async iterator from query().
        """
        parts = []
        async for chunk in self.query(messages, system, consciousness_state, max_tokens):
            parts.append(chunk)
        return "".join(parts)
