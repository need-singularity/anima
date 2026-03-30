"""Channel adapter base — unified interface for all messaging channels.

All channel adapters (Telegram, Discord, CLI, Slack, WebSocket) implement
this protocol. Messages are normalized to ChannelMessage and routed through
AnimaAgent.process_message().

Usage:
    class MyChannel:
        channel_name = "my_channel"

        async def start(self, agent):
            self.agent = agent
            # Start listening...

        async def stop(self):
            # Cleanup...

        async def send(self, user_id, text, **kwargs):
            # Send message to user...
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from anima_agent import AnimaAgent

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



@runtime_checkable
class ChannelAdapter(Protocol):
    """Protocol for channel adapters.

    Existing adapters (telegram_bot, discord_bot, cli_agent) already follow
    this pattern implicitly. This protocol formalizes the interface.
    """

    channel_name: str

    async def start(self, agent: AnimaAgent) -> None:
        """Start the channel (connect, listen for messages)."""
        ...

    async def stop(self) -> None:
        """Stop the channel (disconnect, cleanup)."""
        ...

    async def send(self, user_id: str, text: str, **kwargs: Any) -> None:
        """Send a message to a user on this channel."""
        ...
